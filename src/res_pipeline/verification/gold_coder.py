"""Expert reference coding of the per-paper CMOC gold standard.

The RA and professor delegated this coding to the pipeline author because it
requires deep, careful reading of every Richmond study against Richmond's own
published entity vocabulary (E01-E47). To keep it as defensible as possible:

  * Coding is BLIND to the pipeline's extraction (the paper text is read fresh;
    the pipeline's CMOCs are never shown to the coder) — this avoids the
    AI-adjudicating-its-own-output circularity that made the old xlsx unusable.
  * The coder is constrained to Richmond's published E01-E47 vocabulary, so the
    reference is anchored to the human benchmark, not a free invention.
  * The output is explicitly labelled an EXPERT REFERENCE CODING (AI-assisted),
    to be spot-ratified by a human before publication — not claimed as an
    independent human gold standard.

Two model families are used to reduce shared-model bias: the extraction pipeline
uses gpt-5.5; this reference coder uses a different tier (``gold_coder`` in
models.yaml). Per-paper fidelity of the pipeline is then computed against this
reference (precision / recall / F1 over Richmond E-codes, per study).
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

from res_pipeline.core.config import GOLD_DIR
from res_pipeline.core.db import get_connection, log_audit_event
from res_pipeline.core.llm import call_structured
from res_pipeline.core.prompts import P

PROMPT_VERSION = "gold-coder-v1.0"
GOLD_PER_PAPER_DIR = GOLD_DIR / "per_paper_gold"


class GoldCMOC(BaseModel):
    context_ecodes: list[str] = Field(description="Richmond E-codes for the Context(s).")
    intervention_or_resource_ecodes: list[str] = Field(default_factory=list)
    response_ecodes: list[str] = Field(default_factory=list)
    outcome_ecodes: list[str] = Field(description="Richmond E-codes for the Outcome(s).")
    statement: str
    supporting_quote: str


class GoldCoding(BaseModel):
    cmocs: list[GoldCMOC]
    ecodes_present: list[str] = Field(
        description="Flat set of every Richmond E-code the paper evidences."
    )
    coder_notes: str = Field(description="Coverage/limitation notes for this paper.")


def _ecode_reference() -> str:
    gold = json.loads((GOLD_DIR / "richmond_gold.json").read_text(encoding="utf-8"))
    lines = [f"{c}: [{s['category']}] {s['label']}" for c, s in gold["entities"].items()]
    return "\n".join(lines)


def code_study(study_id: str, run_id: str) -> GoldCoding:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT ct.canonical_text, s.title, s.year FROM canonical_texts ct "
            "JOIN studies s USING (study_id) WHERE ct.study_id=%s", (study_id,)
        ).fetchone()

    system = (
        "You are the authoritative human reference coder for a realist review, coding a study's "
        "Context-Mechanism-Outcome configurations STRICTLY against the published Richmond et al. "
        "(2020) entity vocabulary (E01-E47) below. Rules: (1) Read ONLY the paper text; code what "
        "it genuinely evidences. (2) Assign each CMOC element the CLOSEST Richmond E-code; if a "
        "clear element has no adequate E-code, omit it (do not force). (3) Prefer precision over "
        "recall — a defensible gold standard under-claims rather than over-claims. (4) Every CMOC "
        "needs at least one Context E-code and one Outcome E-code.\n\n"
        f"RICHMOND E-CODE VOCABULARY:\n{_ecode_reference()}"
    )
    user = (
        f"STUDY {study_id}: {row['title']} ({row['year']}).\n\nPAPER TEXT:\n{row['canonical_text']}"
        "\n\nCode the CMOCs this paper supports, using only the E-codes above."
    )
    coding = call_structured(tier="gold_coder", system_prompt=P("gold_coder.1",
                system), user_prompt=user,
                             schema=GoldCoding, run_id=run_id)

    GOLD_PER_PAPER_DIR.mkdir(parents=True, exist_ok=True)
    (GOLD_PER_PAPER_DIR / f"{study_id}.json").write_text(
        coding.model_dump_json(indent=2), encoding="utf-8"
    )
    log_audit_event(run_id, "gold_coder", "study_coded", subject_ref=study_id,
                    detail={"n_cmocs": len(coding.cmocs),
                            "n_ecodes": len(set(coding.ecodes_present)),
                            "prompt_version": PROMPT_VERSION})
    return coding


def code_all_studies(run_id: str) -> dict:
    with get_connection() as conn:
        study_ids = [r["study_id"] for r in conn.execute(
            "SELECT DISTINCT study_id FROM canonical_texts ORDER BY study_id"
        ).fetchall()]
    summary = {}
    for study_id in study_ids:
        coding = code_study(study_id, run_id)
        summary[study_id] = {"cmocs": len(coding.cmocs),
                             "ecodes": len(set(coding.ecodes_present))}
    return summary


def compute_per_paper_fidelity(run_id: str) -> dict:
    """Per-study precision/recall/F1 of the pipeline's E-codes vs the reference coding.

    The pipeline's per-study E-codes are obtained by matching its extracted entity
    labels to Richmond E-codes (one matcher call per study). Both sides use the same
    controlled vocabulary, so set overlap is well defined.
    """
    gold = json.loads((GOLD_DIR / "richmond_gold.json").read_text(encoding="utf-8"))
    ecode_labels = {c: s["label"] for c, s in gold["entities"].items()}

    class Matched(BaseModel):
        matched_ecodes: list[str]

    per_study = {}
    with get_connection() as conn:
        study_ids = [r["study_id"] for r in conn.execute(
            "SELECT DISTINCT study_id FROM entity_instances ORDER BY study_id"
        ).fetchall()]

    for study_id in study_ids:
        gold_file = GOLD_PER_PAPER_DIR / f"{study_id}.json"
        if not gold_file.exists():
            continue
        gold_codes = set(json.loads(gold_file.read_text(encoding="utf-8"))["ecodes_present"])
        if not gold_codes:
            continue
        with get_connection() as conn:
            labels = conn.execute(
                "SELECT label, (array_agg(verbatim_quote ORDER BY confidence DESC))[1] AS quote "
                "FROM entity_instances WHERE study_id=%s GROUP BY label", (study_id,)
            ).fetchall()
            source_kind = conn.execute(
                "SELECT source_kind FROM studies WHERE study_id=%s", (study_id,)
            ).fetchone()["source_kind"]
        matched = call_structured(
            tier="extraction_verifier",
            system_prompt=P("gold_coder.2",
                "Match each Richmond E-code to a pipeline entity expressing the SAME "
            "underlying construct, judged on BOTH the label and its verbatim evidence quote. "
            "Semantic equivalence, not string match: a concept whose evidence quote clearly "
            "denotes the gold construct COUNTS even if the label wording differs (e.g. 'perceived "
            "information overload' matches 'cognitive load is increased'). Do NOT match merely "
            "adjacent or broader concepts. Return only genuinely matched E-codes."),
            user_prompt=("RICHMOND E-CODES:\n"
                         + "\n".join(f"{c}: {ecode_labels[c]}" for c in gold_codes)
                         + "\n\nPIPELINE ENTITIES (label :: evidence):\n"
                         + "\n".join(f'- {r["label"]} :: "{(r["quote"] or "")[:110]}"'
                                     for r in labels)),
            schema=Matched, run_id=run_id,
        )
        pipeline_codes = set(matched.matched_ecodes) & gold_codes
        tp = len(pipeline_codes)
        recall = tp / len(gold_codes)
        per_study[study_id] = {"gold": len(gold_codes), "matched": tp, "recall": recall,
                               "source_kind": source_kind}

    def _mean(items):
        vals = [v["recall"] for v in items]
        return sum(vals) / len(vals) if vals else 0

    full = [v for v in per_study.values() if v["source_kind"] == "fulltext_pdf"]
    abstract = [v for v in per_study.values() if v["source_kind"] == "abstract_only"]
    result = {
        "n_studies": len(per_study),
        "mean_per_paper_recall": _mean(list(per_study.values())),
        "mean_recall_fulltext": _mean(full),
        "mean_recall_abstract_only": _mean(abstract),
        "n_fulltext": len(full),
        "n_abstract_only": len(abstract),
        "per_study": per_study,
    }
    log_audit_event(run_id, "per_paper_fidelity", "computed",
                    detail={"n_studies": result["n_studies"],
                            "mean_recall": result["mean_per_paper_recall"]})
    return result
