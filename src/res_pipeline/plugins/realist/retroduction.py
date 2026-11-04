"""The retroduction loop (Gap 2) — realist synthesis's defining iterative rhythm.

Richmond: "studies identified earlier were re-analysed in light of theories arising
from papers included later in the review" (L253-255); the professor: "a seed, then
an iterative modifier, then the human exam."

Each round:
  1. REFINE — an LLM reflection compares the current programme theory to the IPT
     hypotheses and records which were confirmed / refined / rejected (a new IPT
     version — the "modifier"), which then feeds back into extraction prompts.
  2. RE-READ — the studies the Consistency Checker flagged or the verifier scored
     low are re-extracted under the refined theory (the "re-analysis of earlier
     studies"); optional (paid) via ``reextract``.
  3. RE-SYNTHESISE — normalisation, community detection, demi-regularities, and the
     programme theory are recomputed.
Converges when the flagged set is empty (or unchanged) or ``max_iter`` is reached.
The human still signs off the final theory (HITL-4) — sovereignty is preserved.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from res_pipeline.core.agents import persona
from res_pipeline.core.db import get_connection
from res_pipeline.core.llm import call_structured
from res_pipeline.core.prompts import P
from res_pipeline.plugins.realist.ipt import record_refinement, register_seed


class IPTReflection(BaseModel):
    confirmed: list[str] = Field(description="IPT hypotheses the corpus supports.")
    refined: list[str] = Field(description="Hypotheses the corpus qualifies/modifies (how).")
    rejected: list[str] = Field(description="Hypotheses the corpus does not support.")
    summary: str = Field(description="One-line statement of the theory's current state.")


def _flagged_studies(max_studies: int | None = None) -> list[str]:
    """Studies the second reviewer flagged, WORST first (most disagreements / lowest support).

    Ordered so a bounded retroduction re-reads the genuinely weakest studies first; the
    ``verifier<0.6`` clause alone flags ~half the corpus, so a cap keeps the loop a targeted
    re-read (Richmond's "re-analyse earlier studies") rather than a full re-extraction.
    """
    with get_connection() as conn:
        try:
            rows = conn.execute(
                "SELECT study_id, "
                "  count(*) FILTER (WHERE checker_agrees = false) AS disagreements, "
                "  avg(verifier_support) AS avg_support "
                "FROM cmocs WHERE checker_agrees = false OR verifier_support < 0.6 "
                "GROUP BY study_id ORDER BY disagreements DESC, avg_support ASC"
            ).fetchall()
        except Exception:  # noqa: BLE001 — checker column may not exist on legacy data
            rows = conn.execute(
                "SELECT study_id FROM cmocs WHERE verifier_support < 0.6 "
                "GROUP BY study_id ORDER BY avg(verifier_support) ASC"
            ).fetchall()
    ids = [r["study_id"] for r in rows]
    return ids[:max_studies] if max_studies else ids


def _latest_theory_json() -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT theory_json FROM programme_theories ORDER BY version DESC LIMIT 1"
        ).fetchone()
    if not row:
        return None
    import json
    tj = row["theory_json"]
    return tj if isinstance(tj, dict) else json.loads(tj)


def _reflect(run_id: str) -> str:
    """Compare the latest theory to the IPT; record confirmed/refined/rejected."""
    import json

    from res_pipeline.plugins.realist.ipt import load_ipt

    theory = _latest_theory_json() or {"overview": "(no theory yet)", "sections": []}
    ipt = load_ipt()
    reflection = call_structured(
        tier="synthesis",
        system_prompt=P("retroduction.1",
                persona("ipt_manager") + "\n\n"
        "You are auditing the programme theory against the hypotheses you seeded. For each "
        "hypothesis, state whether the accumulated evidence CONFIRMS, REFINES, or REJECTS it. "
        "Be evidence-led; do not defend the seed."),
        user_prompt=(
            "SEEDED HYPOTHESES:\n"
            + json.dumps({k: ipt[k] for k in ("hypothesised_context_dimensions",
                                              "context_levels_to_investigate",
                                              "hypothesised_mechanism_resources")}, indent=1)
            + "\n\nCURRENT PROGRAMME THEORY:\n"
            + json.dumps(theory, default=str, indent=1)[:6000]
        ),
        schema=IPTReflection, run_id=run_id,
    )
    return record_refinement(reflection.confirmed, reflection.refined, reflection.rejected,
                             reflection.summary, run_id)


def _reextract_study(study_id: str, run_id: str) -> None:
    """Delete a study's CMOC layer and re-extract it under the refined theory."""
    from res_pipeline.plugins.realist.cmoc_extraction import extract_study_cmocs

    with get_connection() as conn:
        conn.execute("DELETE FROM typed_relations WHERE study_id=%s", (study_id,))
        conn.execute("DELETE FROM entity_instances WHERE study_id=%s", (study_id,))
        conn.execute("DELETE FROM cmocs WHERE study_id=%s", (study_id,))
    extract_study_cmocs(study_id, run_id)


def _resynthesise(run_id: str) -> None:
    from res_pipeline.graph.communities import detect_communities
    from res_pipeline.plugins.realist.normalization import (
        build_concept_families,
        normalize_entities,
    )
    from res_pipeline.plugins.realist.programme_theory import compose_programme_theory
    from res_pipeline.plugins.realist.span_repair import fuzzy_repair_spans, repair_spans
    from res_pipeline.plugins.realist.synthesis import persist_synthesis

    # Span-repair the freshly re-extracted studies BEFORE normalisation, so the graph and
    # faithfulness reflect true grounding (retroduction re-extraction previously skipped this).
    repair_spans(run_id)
    fuzzy_repair_spans(run_id)
    normalize_entities(run_id)
    build_concept_families(run_id)
    detect_communities(run_id)
    persist_synthesis(run_id)
    compose_programme_theory(run_id)


def run_retroduction(run_id: str, *, max_iter: int = 2, reextract: bool = True,
                     max_studies: int | None = None, console=None) -> dict:
    def say(msg: str) -> None:
        if console:
            console.print(msg, markup=False)

    register_seed(run_id)
    restudied_total = 0
    last_flagged: set[str] = set()
    ipt_version = "0.1-seed"
    iterations = 0

    for i in range(1, max_iter + 1):
        iterations = i
        say(f"— Retroduction round {i} —")
        ipt_version = _reflect(run_id)
        say(f"  theory refined → IPT {ipt_version}")

        flagged = _flagged_studies(max_studies)
        say(f"  re-reading {len(flagged)} weakest studies: {', '.join(flagged) or '(none)'}")
        if not flagged or set(flagged) == last_flagged:
            say("  converged — flagged set empty or stable.")
            break
        last_flagged = set(flagged)

        if reextract:
            for sid in flagged:
                _reextract_study(sid, run_id)
                restudied_total += 1
                say(f"    re-read {sid}")
            _resynthesise(run_id)
            say("  re-synthesised under the refined theory.")
        else:
            say("  (reextract disabled — logged refinement only, no paid re-read)")
            break

    return {"iterations": iterations, "restudied": restudied_total, "ipt_version": ipt_version}
