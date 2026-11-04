"""Title/abstract screening agent: recall-first, dual-model vote, HITL-routed.

Design (ARCHITECTURE D4, SOTA_REPORT Q2/Q4):
  * The rubric is rendered from ``config/protocol.yaml`` — researcher-defined
    decision logic, never free-styled by the model (professor requirement).
  * Posture is recall-first: the system prompt instructs the model that missing
    a relevant study is far worse than a false include; borderline → 'uncertain'.
  * Two model families vote (``screening_primary`` + ``screening_second_vote``).
    Combination rule: any 'include' vote → include; both 'exclude' → exclude;
    anything else → 'uncertain' routed to HITL-1.
  * Every decision (each voter's and the combined one) is persisted with its
    rationale and confidence for the audit trail.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from res_pipeline.core.config import load_yaml_config
from res_pipeline.core.db import get_connection, log_audit_event
from res_pipeline.core.llm import call_structured
from res_pipeline.core.prompts import P
from res_pipeline.core.registry import StudyRecord

PROMPT_VERSION = "screening-v1.0"


class ScreeningVote(BaseModel):
    """Structured output required from each screening model."""

    decision: str = Field(pattern=r"^(include|exclude|uncertain)$")
    rationale: str = Field(
        min_length=20,
        description="2-4 sentences citing the specific eligibility criteria applied.",
    )
    confidence: float = Field(ge=0.0, le=1.0)


def _system_prompt() -> str:
    protocol = load_yaml_config("protocol")
    e = protocol["eligibility"]
    return f"""You are a systematic-review screening specialist performing TITLE/ABSTRACT \
screening for a realist synthesis, following RAMESES standards.

REVIEW QUESTION: {protocol["review_question"]}

ELIGIBILITY CRITERIA:
- Population — include: {e["population"]["include"]} Exclude: {e["population"]["exclude"]}
- Intervention — include: {e["intervention"]["include"]} Exclude: {e["intervention"]["exclude"]}
- Focus — include: {e["focus"]["include"]}
- Outcomes — include: {e["outcomes"]["include"]}
- Timeframe: published in or after {e["timeframe"]["published_from"]}.
- Realist relevance test: {e["relevance_test"]}

DECISION POLICY (STRICT):
- This screening is RECALL-FIRST: wrongly excluding a relevant study is far more \
costly than wrongly including an irrelevant one.
- 'include' if the study plausibly meets the criteria and could contribute to theory \
building about how educational interventions develop clinical reasoning.
- 'exclude' ONLY when the study clearly fails a criterion (wrong population AND no \
undergraduate component, no educational intervention/technique, or no relation to \
clinical reasoning development).
- 'uncertain' whenever the title/abstract gives insufficient information — a human \
adjudicator will resolve these. Do not guess.
Cite the specific criteria in your rationale."""


def _user_prompt(study: StudyRecord) -> str:
    return (
        f"STUDY {study.study_id}\n"
        f"TITLE: {study.title}\n"
        f"YEAR: {study.year or 'unknown'}\n"
        f"JOURNAL: {study.journal or 'unknown'}\n"
        f"ABSTRACT: {study.abstract or '(no abstract available — judge from title only)'}\n\n"
        "Screen this record."
    )


def _combine(primary: ScreeningVote, second: ScreeningVote) -> str:
    votes = {primary.decision, second.decision}
    if "include" in votes:
        return "include"  # union-of-includes: recall-first
    if votes == {"exclude"}:
        return "exclude"
    return "uncertain"


def _store_decision(
    study_id: str, decider: str, vote_decision: str, rationale: str,
    confidence: float | None, run_id: str,
) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO screening_decisions (study_id, stage, decider, decision, rationale, "
            "confidence, run_id) VALUES (%s,'title_abstract',%s,%s,%s,%s,%s)",
            (study_id, decider, vote_decision, rationale, confidence, run_id),
        )


def screen_study(study: StudyRecord, run_id: str) -> dict:
    """Screen one study with the dual-model vote; returns the combined outcome."""
    system = _system_prompt()
    user = _user_prompt(study)

    primary = call_structured(
        tier="screening_primary", system_prompt=P("screening.1",
                system), user_prompt=user,
        schema=ScreeningVote, run_id=run_id,
    )
    second = call_structured(
        tier="screening_second_vote", system_prompt=P("screening.2",
                system), user_prompt=user,
        schema=ScreeningVote, run_id=run_id,
    )
    combined = _combine(primary, second)

    _store_decision(study.study_id, f"model:{PROMPT_VERSION}:primary",
                    primary.decision, primary.rationale, primary.confidence, run_id)
    _store_decision(study.study_id, f"model:{PROMPT_VERSION}:second_vote",
                    second.decision, second.rationale, second.confidence, run_id)
    _store_decision(study.study_id, f"combined:{PROMPT_VERSION}", combined,
                    f"Union-of-includes combination of ({primary.decision}, {second.decision}).",
                    None, run_id)
    log_audit_event(
        run_id, "screening_agent", "study_screened", subject_ref=study.study_id,
        detail={
            "primary": primary.decision, "second": second.decision, "combined": combined,
            "prompt_version": PROMPT_VERSION,
        },
    )
    return {
        "study_id": study.study_id,
        "primary": primary,
        "second": second,
        "combined": combined,
    }
