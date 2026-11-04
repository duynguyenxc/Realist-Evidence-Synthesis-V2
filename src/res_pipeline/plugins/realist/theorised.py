"""Retroduction that does not need a quote (Gap 3).

The pipeline can only extract what the corpus says. Realist synthesis is not limited
that way: RAMESES II explicitly allows that responses "can be theorised from existing
theories of learning", and Richmond's reviewers used that licence to introduce negative
coping, low self-efficacy, fear and pressure (gold E05, E31, E32, E34) — none of which
the 28 papers state. Measured 2026-11-04: ``emotion`` and ``self-efficacy`` occur **zero**
times across the whole corpus. Those four were not missed by a weak extractor; they were
structurally unreachable by any extractor bound to verbatim grounding.

This module adds the missing move, under three conditions that keep it honest:

1. **A theorised concept is never evidence.** It is written to ``theorised_entities``,
   not ``entity_instances``, so no existing query, metric or export can mistake it for a
   grounded extraction. Nothing is relaxed in the evidence graph.
2. **Absence is checked, not assumed.** Each proposal names the terms it claims are
   missing, and ``_absent()`` verifies them against the canonical texts. A proposal whose
   terms DO appear is rejected on the spot — if the corpus says it, extraction's job is
   to find it, not inference's job to invent it.
3. **It stays a proposal until a human ratifies it.** ``status`` starts ``proposed``.
   This is the one place in the pipeline where the machine asserts something the text
   does not support, so it is the last place that should be automatic.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

from res_pipeline.core.agents import persona
from res_pipeline.core.db import get_connection, log_audit_event
from res_pipeline.core.llm import call_structured
from res_pipeline.core.prompts import P


class TheorisedEntity(BaseModel):
    entity_type: str = Field(description="One of Context, Intervention, Mechanism_Resource, "
                                         "Mechanism_Response, Outcome.")
    label: str = Field(description="The concept, in the vocabulary of the theory.")
    rationale: str = Field(description="Why the programme theory requires it even though "
                                       "no study states it.")
    theory_source: str = Field(description="The IPT hypothesis or named theory it follows from.")
    motivating_studies: list[str] = Field(default_factory=list)
    absent_terms: list[str] = Field(
        default_factory=list,
        description="Words that would appear in the corpus if this were stated outright. "
                    "These are CHECKED; a proposal whose terms are present is discarded.")


class TheorisedBatch(BaseModel):
    entities: list[TheorisedEntity]


def _absent(terms: list[str]) -> tuple[list[str], list[str]]:
    """Split ``terms`` into those genuinely missing from the corpus and those present."""
    if not terms:
        return [], []
    with get_connection() as conn:
        corpus = " ".join(
            (r["canonical_text"] or "").lower()
            for r in conn.execute("SELECT canonical_text FROM canonical_texts").fetchall())
    missing, present = [], []
    for term in terms:
        t = (term or "").strip().lower()
        if not t:
            continue
        (present if re.search(rf"\b{re.escape(t)}", corpus) else missing).append(term)
    return missing, present


def propose_theorised(run_id: str, *, max_proposals: int = 8) -> dict:
    """Ask what the theory needs that the corpus never says, then verify the silence."""
    with get_connection() as conn:
        row = conn.execute("SELECT theory_json FROM programme_theories "
                           "ORDER BY version DESC LIMIT 1").fetchone()
        theory = (row or {}).get("theory_json") or {}
        narratives = [r["narrative_statement"] for r in conn.execute(
            "SELECT narrative_statement FROM cmocs ORDER BY cmoc_id LIMIT 60").fetchall()]
        existing = [r["label"] for r in conn.execute(
            "SELECT DISTINCT label FROM entity_instances ORDER BY label").fetchall()]

    batch = call_structured(
        tier="synthesis",
        system_prompt=P("theorised.1", persona("synthesis_lead") + (
            "\n\nYou are performing RETRODUCTION, the realist move of inferring what must be "
            "true for the observed pattern to hold, rather than reporting what the studies "
            "state. Propose ONLY configurations the programme theory requires and the corpus "
            "does NOT state anywhere. Do not restate an existing extracted concept in other "
            "words; do not propose something a study plainly says — that belongs to "
            "extraction, not to inference. For each, give the theory it follows from and the "
            "words that WOULD appear in the papers if it were stated outright; those words "
            "are checked against the full corpus and your proposal is discarded if they are "
            "found. Fewer, better-warranted proposals are worth more than many.")),
        user_prompt=(
            "CURRENT PROGRAMME THEORY:\n" + str(theory.get("overview", "(none recorded)"))
            + "\n\nCONFIGURATIONS THE CORPUS SUPPORTS:\n" + "\n".join(f"- {n}" for n in narratives)
            + "\n\nCONCEPTS ALREADY EXTRACTED (do not restate these):\n"
            + "; ".join(existing[:400])
            + f"\n\nPropose at most {max_proposals}."),
        schema=TheorisedBatch, run_id=run_id,
    )

    kept, discarded = [], []
    with get_connection() as conn:
        for e in batch.entities[:max_proposals]:
            missing, present = _absent(e.absent_terms)
            if present or not missing:
                # Either the corpus does say it, or the model offered no falsifiable claim.
                discarded.append({"label": e.label,
                                  "why": f"terms present in corpus: {present}" if present
                                         else "no checkable absent_terms given"})
                continue
            conn.execute(
                "INSERT INTO theorised_entities (entity_type,label,rationale,theory_source,"
                "motivating_studies,absent_terms,proposed_by,run_id) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                (e.entity_type, e.label, e.rationale, e.theory_source,
                 e.motivating_studies, missing, "ai-ra:claude", run_id))
            kept.append(e.label)

    log_audit_event(run_id, "ai-ra:claude", "retroduction_proposed",
                    subject_ref=f"{len(kept)} kept / {len(discarded)} discarded")
    return {"proposed": kept, "discarded": discarded}


def ratify(entity_id: int, reviewer: str, *, accept: bool = True) -> None:
    """HITL: a human accepts or rejects one theorised concept. Nothing else may."""
    with get_connection() as conn:
        conn.execute(
            "UPDATE theorised_entities SET status=%s, ratified_by=%s, ratified_at=now() "
            "WHERE id=%s", ("ratified" if accept else "rejected", reviewer, entity_id))


def ratified() -> list[dict]:
    """The theorised concepts a human has accepted — the only ones a theory may use."""
    with get_connection() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM theorised_entities WHERE status='ratified' ORDER BY id").fetchall()]
