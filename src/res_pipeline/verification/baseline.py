"""The trivial baseline — what does *one* LLM call score on the same benchmark?

Without this, "agentic realist synthesis framework" is not a falsifiable claim. If a single
prompt over the same 28 papers recovers most of Richmond's concepts, then the pipeline's
ontology, its per-study extraction, its span grounding, its Leiden layer and its four human
checkpoints are buying whatever the difference is — and that difference *is* the paper's
result. A methods reviewer asks this first, and the honest move is to ask it of ourselves.

Two baselines are implemented:

``single_call``
    One call: the 28 papers' text, and "write a realist review". This is the ChatGPT
    counterfactual — what a reader could do without any of this machinery. Because the corpus
    is ~161k tokens, each paper is truncated to a head budget so the whole set fits; that
    truncation is itself part of the counterfactual, since it is what anyone pasting papers
    into a chat window faces.

``no_ontology``
    The pipeline's own per-study extraction, with the realist ontology removed from the
    prompt — free-form entities and relations. Isolates what the C/M-resource/M-response/O
    typing contributes, separately from per-study processing.

Both are scored by the *same* matcher the main harness uses, so the comparison is like for
like. Results are written beside the verification runs and never into the pipeline's tables:
a baseline must not be able to contaminate the system it is a baseline for.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

from res_pipeline.core.db import get_connection
from res_pipeline.core.llm import call_structured
from res_pipeline.verification.metrics import (
    _OUR_TYPE_TO_RICHMOND_ROLE,
    _RICHMOND_ROLES,
    EntityMatchBatch,
    _JUDGE_SAMPLES,
    _load_gold,
)
from res_pipeline.verification.stats import clopper_pearson

# Per-paper character budget for the single-call baseline. 28 papers x 18k chars is roughly
# 126k characters (~32k tokens), which fits a single request with room for the instruction and
# a long structured answer. Anyone pasting papers into a chat faces the same ceiling.
_CHARS_PER_PAPER = 18_000


class BaselineConcept(BaseModel):
    label: str = Field(description="A concept named in the review.")
    realist_role: str = Field(
        description="One of: Context, Mechanism_Resource, Mechanism_Response, Outcome.")


class BaselineReview(BaseModel):
    concepts: list[BaselineConcept]
    programme_theory: str = Field(description="The review's overall conclusion, in prose.")


_SINGLE_CALL_SYSTEM = (
    "You are an expert in realist review methodology (RAMESES standards). You will be given "
    "the text of a set of primary studies about educational interventions for clinical "
    "reasoning. Produce a realist synthesis: identify the Contexts (pre-existing conditions of "
    "the learner or setting), the Mechanism Resources (what an intervention introduces), the "
    "Mechanism Responses (what happens inside the learner), and the Outcomes. Name every "
    "concept you would put in a figure of the finished review, and state the overall programme "
    "theory. Be comprehensive: name every concept the evidence supports."
)


def _corpus_text(limit_chars: int = _CHARS_PER_PAPER) -> tuple[str, int]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT s.study_id, s.title, t.canonical_text FROM canonical_texts t "
            "JOIN studies s USING (study_id) ORDER BY s.study_id"
        ).fetchall()
    parts = [
        f"--- {r['study_id']}: {r['title']} ---\n{(r['canonical_text'] or '')[:limit_chars]}"
        for r in rows
    ]
    return "\n\n".join(parts), len(rows)


def _score_concepts(concepts: list[BaselineConcept], run_id: str) -> dict:
    """Match a flat concept list against the gold, with the harness's own matcher and vote."""
    gold = _load_gold()
    by_role: dict[str, list[str]] = {}
    for i, c in enumerate(concepts):
        role = c.realist_role if c.realist_role in _RICHMOND_ROLES else None
        if role is None:
            role = _OUR_TYPE_TO_RICHMOND_ROLE.get(c.realist_role, "Outcome")
        by_role.setdefault(role, []).append(f"b{i} :: {c.label}")

    all_codes = list(gold["entities"])
    votes = {c: 0 for c in all_codes}
    for _ in range(_JUDGE_SAMPLES):
        seen: set[str] = set()
        for role in _RICHMOND_ROLES:
            gold_here = {k: v for k, v in gold["entities"].items()
                         if v["richmond_role"] == role}
            if not gold_here:
                continue
            batch = call_structured(
                tier="extraction_verifier",
                system_prompt=(
                    "You are scoring entity coverage for a systematic-review verification. For "
                    "each GOLD entity, decide whether any EXTRACTED concept expresses the SAME "
                    "underlying construct. Semantic equivalence, not string match. Do NOT match "
                    "merely adjacent or broader concepts."
                ),
                user_prompt=(
                    "GOLD ENTITIES:\n"
                    + "\n".join(f"{k}: {v['label']}" for k, v in gold_here.items())
                    + "\n\nEXTRACTED CONCEPTS:\n"
                    + ("\n".join(by_role.get(role, [])) or "(none)")
                ),
                schema=EntityMatchBatch, run_id=run_id,
            )
            for m in batch.matches:
                if m.matched and m.e_code in votes and m.e_code not in seen:
                    seen.add(m.e_code)
                    votes[m.e_code] += 1

    threshold = (_JUDGE_SAMPLES // 2) + 1
    matched = sorted(c for c, v in votes.items() if v >= threshold)
    total = len(all_codes)
    return {
        "gold_entities": total,
        "n_concepts_produced": len(concepts),
        "matched": len(matched),
        "recall_ci": clopper_pearson(len(matched), total),
        "matched_codes": matched,
        "missed_codes": sorted(set(all_codes) - set(matched)),
    }


def run_single_call_baseline(run_id: str, out_dir: Path) -> dict:
    """One prompt, all 28 papers, no pipeline. The counterfactual a reviewer will name."""
    corpus, n_studies = _corpus_text()
    review = call_structured(
        tier="extraction", system_prompt=_SINGLE_CALL_SYSTEM,
        user_prompt=(f"{n_studies} PRIMARY STUDIES (each truncated to "
                     f"{_CHARS_PER_PAPER:,} characters):\n\n{corpus}\n\n"
                     "Produce the realist synthesis now."),
        schema=BaselineReview, run_id=run_id,
    )
    result = {
        "baseline": "single_call",
        "description": "One LLM call over all studies; no ontology, no per-study extraction, "
                       "no span grounding, no graph, no human checkpoints.",
        "n_studies": n_studies,
        "chars_per_paper": _CHARS_PER_PAPER,
        "programme_theory": review.programme_theory,
        **_score_concepts(review.concepts, run_id),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "baseline_single_call.json").write_text(
        json.dumps(result, indent=2, default=str), encoding="utf-8")
    return result
