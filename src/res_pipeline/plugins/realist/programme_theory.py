"""Programme Theory Composer: from motifs + contradictions to a realist theory.

Produces the final realist artifact in the same genre as Richmond et al. (2020):
context-indexed theory sections, each with an italicisable CMOC statement, the
supporting demi-regularities, study counts, and explicit handling of
contradictions (with their interpretive resolutions from HITL-3).

The composer LLM is constrained to the evidence it is given: every claim must
cite study IDs from the supplied motifs; the schema rejects sections without
citations. Human sign-off (HITL-4) is recorded before the theory is marked final.
"""

from __future__ import annotations

import os

import json

from pydantic import BaseModel, Field

from res_pipeline.core.agents import persona
from res_pipeline.core.config import load_yaml_config
from res_pipeline.core.db import get_connection, log_audit_event
from res_pipeline.core.llm import call_structured
from res_pipeline.core.prompts import P
from res_pipeline.core.retrieval import select
from res_pipeline.plugins.realist.ipt import ipt_prompt_block

PROMPT_VERSION = "programme-theory-v2.0-ipt"


class TheorySection(BaseModel):
    context_label: str = Field(description="Human-readable label of the student context.")
    cmoc_statement: str = Field(
        min_length=50,
        description="The italicisable realist statement: When <context> ... (Mresource) ... "
        "(Mresponse) ... leading to <outcome> (O).",
    )
    explanation: str = Field(min_length=100)
    supporting_study_ids: list[str] = Field(min_length=1)
    contradiction_note: str = Field(
        default="", description="How conflicting evidence within this context is explained."
    )


class ProgrammeTheory(BaseModel):
    overview: str = Field(min_length=100, description="What the synthesis found overall.")
    sections: list[TheorySection] = Field(min_length=1)
    boundary_statement: str = Field(
        description="What this automated synthesis does NOT claim (human judgment boundary)."
    )


# Above this many CMOC statements the composer stops being given all of them and gets
# the BM25-ranked top slice instead. 400 is chosen to sit well above Richmond's 94, so
# the published run is byte-identical and no figure moves; retrieval engages only on the
# larger corpus `res search` produces, which is the only place it is needed. Tune with
# RES_EVIDENCE_CAP rather than by editing this.
_STATEMENT_CAP = int(os.getenv("RES_EVIDENCE_CAP", "400"))


def _evidence_pack() -> dict:
    """Assemble the evidence the composer is allowed to use (and nothing else).

    Everything aggregated — demi-regularities, contradictions, communities — is passed
    whole, because those layers are already summaries of the corpus and are small by
    construction. Only the per-study CMOC statements grow with the corpus, so only they
    are retrieved against, and the pack records whether that happened."""
    with get_connection() as conn:
        motifs = conn.execute(
            "SELECT context_concept, driver_concept, outcome_concept, polarity, study_ids "
            "FROM demi_regularities ORDER BY array_length(study_ids,1) DESC"
        ).fetchall()
        conflicts = conn.execute(
            "SELECT driver_concept, positive_studies, negative_studies, positive_contexts, "
            "negative_contexts, resolution FROM contradictions"
        ).fetchall()
        statements = conn.execute(
            "SELECT c.study_id, c.polarity, c.narrative_statement "
            "FROM cmocs c WHERE c.verifier_support >= 0.6 ORDER BY c.study_id"
        ).fetchall()
        # Conceptual entities from graph community detection (Gap 4), when available.
        try:
            communities = conn.execute(
                "SELECT community_label, definition, entity_type, member_count, study_ids "
                "FROM conceptual_entities ORDER BY member_count DESC"
            ).fetchall()
        except Exception:  # noqa: BLE001 — table absent until communities are detected
            communities = []
    question = load_yaml_config("protocol").get("review_question", "")
    chosen, report = select([dict(s) for s in statements], question,
                            text_key="narrative_statement", cap=_STATEMENT_CAP)
    return {
        "conceptual_entities": [dict(c) for c in communities],
        "demi_regularities": [dict(m) for m in motifs],
        "contradictions": [dict(c) for c in conflicts],
        "cmoc_statements": chosen,
        # Carried so a synthesis built on a subset can SAY so. A realist review that
        # silently dropped evidence would be unreportable.
        "_retrieval": report,
    }


def compose_programme_theory(run_id: str) -> ProgrammeTheory:
    evidence = _evidence_pack()
    theory = call_structured(
        tier="synthesis",
        system_prompt=(
            P("programme_theory.1",
                persona("synthesis_lead") + "\n\n"
            "Compose a programme theory about how educational interventions develop "
            "analytical and non-analytical clinical reasoning in undergraduate health "
            "professions students.\n\nHARD RULES:\n"
            "1. Organize sections BY STUDENT CONTEXT (group related context concepts).\n"
            "2. Every section's supporting_study_ids must come from the study_ids in the "
            "supplied demi-regularities/statements — never cite a study not in the evidence.\n"
            "3. Contradictions must be explained via differing contexts (realist logic), "
            "not smoothed over; use the 'resolution' text when present.\n"
            "4. CMOC statements must explicitly mark (C), (Mresource), (Mresponse), (O).\n"
            "5. Where the conceptual_entities (emergent graph communities) name a mechanism "
            "family, use it as the mechanism vocabulary — they are your data-derived concepts.\n"
            "6. The boundary_statement must state that final interpretive judgement and "
            "normative theory choice remain with human researchers.")
        ),
        user_prompt=(
            ipt_prompt_block() + "\n\n"
            "You are now REFINING that theory against the accumulated cross-study evidence. "
            "EVIDENCE PACK:\n" + json.dumps(evidence, default=str, indent=1)
        ),
        schema=ProgrammeTheory,
        run_id=run_id,
    )

    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS programme_theories (
                id BIGSERIAL PRIMARY KEY,
                version INT NOT NULL,
                theory_json JSONB NOT NULL,
                signed_off_by TEXT,
                run_id TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
        version_row = conn.execute(
            "SELECT coalesce(max(version),0)+1 AS v FROM programme_theories"
        ).fetchone()
        conn.execute(
            "INSERT INTO programme_theories (version, theory_json, run_id) VALUES (%s,%s,%s)",
            (version_row["v"], theory.model_dump_json(), run_id),
        )
    log_audit_event(run_id, "programme_theory_composer", "theory_drafted",
                    detail={"version": version_row["v"], "n_sections": len(theory.sections),
                            "prompt_version": PROMPT_VERSION})
    return theory


def sign_off_theory(version: int, signer: str, run_id: str) -> None:
    """HITL-4: record human (or delegate) sign-off of a theory version."""
    with get_connection() as conn:
        conn.execute(
            "UPDATE programme_theories SET signed_off_by=%s WHERE version=%s",
            (signer, version),
        )
        conn.execute(
            "INSERT INTO hitl_feedback (checkpoint, subject_ref, action, feedback, payload, "
            "run_id) VALUES ('HITL-4',%s,'approve',%s,'{}',%s)",
            (f"theory-v{version}", f"Signed off by {signer}", run_id),
        )
    log_audit_event(run_id, signer, "hitl4_theory_signoff", subject_ref=f"theory-v{version}")
