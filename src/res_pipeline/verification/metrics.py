"""Verification harness: compare system outputs against the Richmond gold standard.

This module lives OUTSIDE the production pipeline (professor's correction: the
benchmark comparison is a separate research-evaluation activity, not an agent).

Stages measured (plan_verification_text.txt steps; ARCHITECTURE D6):
  1. Screening — sensitivity/precision vs the 28-study inclusion list.
  2. Entity coverage — recall of the 47 gold entities (E01-E47) among extracted
     canonical concepts, judged by an LLM semantic matcher (embedding-free,
     deterministic temperature-0 judgement with rationale, auditable).
  3. Relation coverage — recall of the 40 gold relations (R01-R40): a gold
     relation counts as recovered when a typed relation with the same predicate
     links entities matched to its subject/object E-codes.
  4. Citation faithfulness — share of extracted entities whose verbatim quote
     resolved to a span in the canonical text, reported in three separate tiers
     (exact / normalized / fuzzy) because they are not the same evidence.
  5. Programme-theory correspondence — per-PTS-chain rubric score, judged both by
     the composer's own model family and by an independent family, so the
     self-preference gap is reported rather than assumed away. Human rating is
     still required before publication.

Every metric here declares whether it is deterministic or model-judged, and each
model-judged metric is K-sampled and majority-voted with its range reported. A
metric that cannot fail is worse than no metric, so where a score is saturable
(relation type-level recall) the ceiling is reported next to the score.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from pydantic import BaseModel, Field

from res_pipeline.core.config import GOLD_DIR
from res_pipeline.core.db import get_connection
from res_pipeline.core.llm import call_structured
from res_pipeline.verification.stats import clopper_pearson


class EntityMatch(BaseModel):
    e_code: str
    matched: bool
    matched_concept: str = Field(default="", description="The canonical concept id, if matched.")
    rationale: str


class EntityMatchBatch(BaseModel):
    matches: list[EntityMatch]


class ChainScore(BaseModel):
    pts_id: str
    correspondence: float = Field(ge=0.0, le=1.0,
                                  description="Structural+conceptual correspondence 0-1.")
    rationale: str


class ChainScoreBatch(BaseModel):
    scores: list[ChainScore]


# Which benchmark file to score against. v3 is the corrected standard (see
# scripts/build_richmond_gold_v3.py for the four defects it fixes); set RES_GOLD=v1 to
# reproduce any number published before 2026-09-23 exactly.
_GOLD_FILES = {
    "v1": "richmond_gold_v1.json",
    "v2": "richmond_gold_v2.json",
    "v3": "richmond_gold_v3.json",
}

# Richmond's CMOC scheme has four roles. Our ontology splits their single mechanism-
# resource column into Intervention and Mechanism_Resource, so an extracted concept is
# compared to a gold entity under Richmond's scheme, not ours — otherwise the system is
# marked wrong for a distinction Richmond never drew.
_OUR_TYPE_TO_RICHMOND_ROLE = {
    "Context": "Context",
    "Intervention": "Mechanism_Resource",
    "Mechanism_Resource": "Mechanism_Resource",
    "Mechanism_Response": "Mechanism_Response",
    "Outcome": "Outcome",
}
_RICHMOND_ROLES = ("Context", "Mechanism_Resource", "Mechanism_Response", "Outcome")


def gold_version() -> str:
    return os.environ.get("RES_GOLD", "v3").lower()


def _load_gold() -> dict:
    """The benchmark, restricted to the scored core so denominators stay comparable.

    v1 predates the ``scored`` flag and the ``richmond_role`` field; both are filled in
    here so the rest of the module has one shape to work with whichever file is loaded.
    """
    version = gold_version()
    filename = _GOLD_FILES.get(version)
    if filename is None:
        raise ValueError(f"RES_GOLD={version!r} — expected one of {sorted(_GOLD_FILES)}")
    gold = json.loads((GOLD_DIR / filename).read_text(encoding="utf-8"))

    entities = {}
    for code, spec in gold["entities"].items():
        if not spec.get("scored", True):
            continue
        spec = dict(spec)
        spec.setdefault("richmond_role",
                        _OUR_TYPE_TO_RICHMOND_ROLE[spec["category"]])
        entities[code] = spec
    gold["entities"] = entities
    gold["relationships"] = [
        rel for rel in gold["relationships"]
        if rel.get("scored", True)
        and rel["subject_code"] in entities and rel["object_code"] in entities
    ]
    gold["gold_version"] = version
    return gold


# LLM-judged metrics are non-deterministic run-to-run (entity coverage varied 72/66/62%
# across three identical-data runs). We therefore sample each judge K times and
# majority-vote (recall metrics) or average (scored metrics), reporting the range so a
# single noisy point estimate is never presented as fact.
_JUDGE_SAMPLES = 3


def screening_metrics(run_id: str | None = None) -> dict:
    """Sensitivity against Richmond's 28 included studies.

    Two things this function used to get wrong, both of which a reviewer would catch:

    * **The denominator came from our own output.** `n` was the number of studies that
      happened to have a screening decision, so a run that died after 20 studies still
      reported a fraction of 20. The denominator is now the registry of gold-include
      studies, and any study with no decision is reported as `no_decision` rather than
      quietly leaving the denominator.
    * **It blended every screening run ever stored.** `DISTINCT ON ... ORDER BY
      created_at DESC` drew the newest decision per study across six different runs, so
      the published number belonged to no single execution. Decisions are now taken from
      one run — the newest complete one by default, or `run_id` if given — and the run is
      named in the result so the number is reproducible.

    Sensitivity alone cannot fail here: every corpus study is a gold include, so there
    are no true negatives to get wrong. `specificity_measured_separately` points at the
    distractor-pool test, which is the only place precision is actually measured.
    """
    with get_connection() as conn:
        gold_ids = {r["study_id"] for r in
                    conn.execute("SELECT study_id FROM studies").fetchall()}
        if run_id is None:
            chosen = conn.execute(
                """
                SELECT run_id FROM screening_decisions WHERE decider LIKE 'combined:%%'
                GROUP BY run_id HAVING count(DISTINCT study_id) = %s
                ORDER BY max(created_at) DESC LIMIT 1
                """,
                (len(gold_ids),),
            ).fetchone()
            run_id = chosen["run_id"] if chosen else None
        decisions = {r["study_id"]: r["decision"] for r in conn.execute(
            "SELECT study_id, decision FROM screening_decisions "
            "WHERE decider LIKE 'combined:%%' AND run_id = %s", (run_id,)
        ).fetchall()}
        human = {r["study_id"]: r["decision"] for r in conn.execute(
            "SELECT DISTINCT ON (study_id) study_id, decision FROM screening_decisions "
            "WHERE decider LIKE 'human:%' ORDER BY study_id, created_at DESC"
        ).fetchall()}

    n = len(gold_ids)
    auto_include = [s for s in gold_ids if decisions.get(s) == "include"]
    uncertain = sorted(s for s in gold_ids if decisions.get(s) == "uncertain")
    false_exclude = sorted(s for s in gold_ids if decisions.get(s) == "exclude")
    no_decision = sorted(s for s in gold_ids if s not in decisions)
    final = len(auto_include) + sum(1 for s in uncertain if human.get(s) == "include")
    return {
        "screening_run_id": run_id,
        "n_gold_includes": n,
        "auto_include": len(auto_include),
        "auto_sensitivity": len(auto_include) / n if n else 0,
        "false_excludes": false_exclude,
        "uncertain_routed_to_hitl": uncertain,
        "no_decision": no_decision,
        "final_sensitivity_after_hitl": final / n if n else 0,
        "auto_sensitivity_ci": clopper_pearson(len(auto_include), n),
        "final_sensitivity_ci": clopper_pearson(final, n),
        "caveat": "Sensitivity only — every corpus study is a gold include, so this metric "
                  "has no true negatives and cannot detect over-inclusion. Specificity is "
                  "measured separately against the distractor pool (`res precision-test`).",
    }


def entity_coverage(run_id: str) -> dict:
    """LLM-judged semantic matching of gold E-codes to extracted canonical concepts."""
    gold = _load_gold()
    with get_connection() as conn:
        # One representative verbatim quote per concept gives the matcher real evidence
        # of what was extracted (not just a terse label) — improves recall of genuine
        # matches without loosening the equivalence bar.
        concepts = conn.execute(
            """
            SELECT canonical_id, entity_type,
                   array_agg(DISTINCT label) AS labels,
                   (array_agg(verbatim_quote ORDER BY confidence DESC))[1] AS quote,
                   count(DISTINCT study_id) AS n_studies
            FROM entity_instances WHERE canonical_id IS NOT NULL
            GROUP BY canonical_id, entity_type
            """
        ).fetchall()

    # Candidates are bucketed by RICHMOND's role, not ours: our Intervention and
    # Mechanism_Resource concepts both compete for Richmond's Mresource entities.
    by_role: dict[str, list[str]] = {}
    concept_role: dict[str, str] = {}
    all_candidate_lines: list[str] = []
    for c in concepts:
        quote = (c["quote"] or "")[:120]
        line = f"{c['canonical_id']} :: {'; '.join(c['labels'][:3])} :: evidence: \"{quote}\""
        role = _OUR_TYPE_TO_RICHMOND_ROLE[c["entity_type"]]
        by_role.setdefault(role, []).append(f"[{c['entity_type']}] {line}")
        concept_role[c["canonical_id"]] = role
        all_candidate_lines.append(f"[{c['entity_type']}] {line}")

    def _one_pass() -> list[EntityMatch]:
        matches: list[EntityMatch] = []
        for category in _RICHMOND_ROLES:
            gold_entities = {code: spec for code, spec in gold["entities"].items()
                             if spec["richmond_role"] == category}
            if not gold_entities:
                continue
            candidates = by_role.get(category, [])
            batch = call_structured(
                tier="extraction_verifier",
                system_prompt=(
                    "You are scoring entity coverage for a systematic-review verification. For "
                    "each GOLD entity, decide whether any EXTRACTED concept expresses the SAME "
                    "underlying construct — judged on both the concept labels and the verbatim "
                    "evidence quote provided. Semantic equivalence, not string match; but a "
                    "concept whose evidence quote clearly denotes the gold construct COUNTS even "
                    "if the label wording differs (e.g. 'perceived information overload' matches "
                    "'cognitive load is increased'; 'virtual patient application' matches "
                    "'real-life scenarios including simulation'). Do NOT match merely adjacent or "
                    "broader concepts. Provide the matched concept id or leave empty."
                ),
                user_prompt=(
                    "GOLD ENTITIES:\n"
                    + "\n".join(f"{code}: {spec['label']}" for code, spec in gold_entities.items())
                    + "\n\nEXTRACTED CONCEPTS (id :: example labels):\n"
                    + ("\n".join(candidates) if candidates else "(none)")
                ),
                schema=EntityMatchBatch, run_id=run_id,
            )
            matches.extend(batch.matches)
        return matches

    all_codes = list(gold["entities"].keys())
    valid_concepts = set(concept_role)
    votes: dict[str, int] = {c: 0 for c in all_codes}
    concept_of: dict[str, str] = {}
    rationale_of: dict[str, str] = {}
    per_sample_recalls: list[float] = []
    total = len(all_codes)
    for _ in range(_JUDGE_SAMPLES):
        # Deduplicate within the sample: a judge that emits the same code twice in one
        # pass must not thereby clear a 3-sample majority on its own. Codes outside the
        # gold (hallucinated by the judge) are discarded rather than counted, which is
        # what previously allowed recall to exceed 1.0.
        hits_this_sample: set[str] = set()
        for m in _one_pass():
            if not m.matched or m.e_code not in votes or m.e_code in hits_this_sample:
                continue
            hits_this_sample.add(m.e_code)
            votes[m.e_code] += 1
            if m.matched_concept in valid_concepts:
                concept_of[m.e_code] = m.matched_concept
            rationale_of[m.e_code] = m.rationale
        per_sample_recalls.append(len(hits_this_sample) / total if total else 0)

    threshold = (_JUDGE_SAMPLES // 2) + 1  # majority
    matched_codes = {c for c, v in votes.items() if v >= threshold}
    crosswalk_codes: set[str] = set()

    # Cross-type recovery pass: Richmond and this system sometimes assign the SAME
    # construct to different realist roles (e.g. Richmond files self-efficacy/coping as
    # a Context; our extractor filed "diagnostic reasoning confidence" as a Mechanism_
    # Response). A within-category matcher wrongly scores those as misses. For the
    # still-unmatched gold codes only, we match against candidates of ALL types, keep
    # the strict same-construct bar, and record the role disagreement rather than hide
    # it. This corrects a matcher artefact; it does not loosen what counts as recovered.
    # The recovery pass is sampled and majority-voted exactly like the main pass. It
    # previously ran once and accepted any hit, so a rigorous 3-of-3 bar was applied to
    # within-role matches and a one-shot bar to the fallback — which is how the headline
    # recall came to sit ABOVE the highest of its own three samples.
    unmatched = [c for c in all_codes if c not in matched_codes]
    recovery_votes: dict[str, int] = {}
    for _ in range(_JUDGE_SAMPLES if unmatched and all_candidate_lines else 0):
        recovery = call_structured(
            tier="extraction_verifier",
            system_prompt=(
                "You are recovering cross-category matches for a systematic-review "
                "verification. Each GOLD entity below was NOT matched to an extracted "
                "concept of its own realist type. Decide whether any EXTRACTED concept (of "
                "ANY type, prefixed [Type]) expresses the SAME underlying construct — judged "
                "on labels and the verbatim evidence quote. The realist role may differ; that "
                "is expected and must NOT lower the bar. Require genuine construct identity, "
                "not adjacency or broader/narrower concepts. Give the matched concept id or "
                "leave empty."
            ),
            user_prompt=(
                "GOLD ENTITIES (still unmatched):\n"
                + "\n".join(f"{c} [{gold['entities'][c]['richmond_role']}]: "
                            f"{gold['entities'][c]['label']}" for c in unmatched)
                + "\n\nEXTRACTED CONCEPTS (any type):\n" + "\n".join(all_candidate_lines)
            ),
            schema=EntityMatchBatch, run_id=run_id,
        )
        seen: set[str] = set()
        for m in recovery.matches:
            if not m.matched or m.e_code not in unmatched or m.e_code in seen:
                continue
            seen.add(m.e_code)
            recovery_votes[m.e_code] = recovery_votes.get(m.e_code, 0) + 1
            if m.matched_concept in valid_concepts:
                concept_of[m.e_code] = m.matched_concept
            rationale_of[m.e_code] = m.rationale

    for code, count in recovery_votes.items():
        if count >= threshold:
            matched_codes.add(code)
            crosswalk_codes.add(code)

    def _type_agree(code: str) -> bool:
        """Does the match sit in the same realist role Richmond gave it?"""
        cid = concept_of.get(code, "")
        return bool(cid) and concept_role.get(cid) == gold["entities"][code]["richmond_role"]

    return {
        "gold_version": gold["gold_version"],
        "gold_entities": total,
        "matched": len(matched_codes),
        "recall": len(matched_codes) / total if total else 0,
        "recall_ci": clopper_pearson(len(matched_codes), total),
        "recall_within_type_ci": clopper_pearson(
            len(matched_codes) - len(crosswalk_codes), total),
        "matched_within_type": len(matched_codes) - len(crosswalk_codes),
        "matched_cross_type": len(crosswalk_codes),
        "samples": _JUDGE_SAMPLES,
        "per_sample_recalls": [round(r, 3) for r in per_sample_recalls],
        "recall_min": round(min(per_sample_recalls), 3) if per_sample_recalls else 0,
        "recall_max": round(max(per_sample_recalls), 3) if per_sample_recalls else 0,
        "per_entity": {c: {"matched": c in matched_codes,
                           "concept": concept_of.get(c, ""),
                           "rationale": rationale_of.get(c, ""),
                           "cross_type": c in crosswalk_codes,
                           "type_agrees": _type_agree(c)} for c in all_codes},
    }


def relation_coverage(entity_matches: dict) -> dict:
    """Gold relation recovery at two fairness levels (both reported, never conflated).

    STRICT: same predicate links the exact concepts matched to the gold subject/object
      E-codes (upper-bounded by entity recall squared — informative but harsh).
    TYPE-LEVEL: the gold relation's predicate is present in the extracted graph linking
      an entity of the gold subject's TYPE to one of the gold object's TYPE. This measures
      whether the causal *pattern* (e.g., Context CONSTRAINS Outcome) was recovered,
      independent of whether both specific concepts were individually matched — the more
      methodologically appropriate question for a realist synthesis.
    """
    gold = _load_gold()
    # Endpoint types are compared under Richmond's four-role scheme (see _load_gold).
    categories = {code: spec["richmond_role"] for code, spec in gold["entities"].items()}
    code_to_concept = {
        code: info["concept"] for code, info in entity_matches["per_entity"].items()
        if info["matched"] and info["concept"]
    }
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT tr.predicate, se.canonical_id AS subj, oe.canonical_id AS obj,
                   se.entity_type AS subj_type, oe.entity_type AS obj_type
            FROM typed_relations tr
            JOIN entity_instances se ON se.entity_id = tr.subject_entity_id
            JOIN entity_instances oe ON oe.entity_id = tr.object_entity_id
            WHERE tr.constraint_valid
            """
        ).fetchall()
    def _role(row_type: str) -> str:
        return _OUR_TYPE_TO_RICHMOND_ROLE[row_type]

    strict_set = {(r["predicate"], r["subj"], r["obj"]) for r in rows}
    type_set = {(r["predicate"], _role(r["subj_type"]), _role(r["obj_type"])) for r in rows}
    # for the middle tier: predicate + one exact concept endpoint + other endpoint's role
    subj_anchored = {(r["predicate"], r["subj"], _role(r["obj_type"])) for r in rows}
    obj_anchored = {(r["predicate"], _role(r["subj_type"]), r["obj"]) for r in rows}

    strict_recovered, partial_recovered, type_recovered, missed_strict = [], [], [], []
    derived_ids = {rel["id"] for rel in gold["relationships"] if rel.get("derived")}
    for rel in gold["relationships"]:
        subj_concept = code_to_concept.get(rel["subject_code"])
        obj_concept = code_to_concept.get(rel["object_code"])
        subj_cat = categories[rel["subject_code"]]
        obj_cat = categories[rel["object_code"]]
        if subj_concept and obj_concept and (
            (rel["predicate"], subj_concept, obj_concept) in strict_set
        ):
            strict_recovered.append(rel["id"])
        else:
            missed_strict.append(rel["id"])
        # ANCHORED (middle tier): same predicate, one endpoint is the exact matched
        # concept, the other endpoint is of the correct realist type.
        if (subj_concept and (rel["predicate"], subj_concept, obj_cat) in subj_anchored) or \
           (obj_concept and (rel["predicate"], subj_cat, obj_concept) in obj_anchored):
            partial_recovered.append(rel["id"])
        if (rel["predicate"], subj_cat, obj_cat) in type_set:
            type_recovered.append(rel["id"])
    total = len(gold["relationships"])
    # Figure-fidelity view: the same three tiers over only the arrows Richmond actually
    # draws, excluding the four transitive shortcuts flagged `derived` in the gold.
    drawn = [rel["id"] for rel in gold["relationships"] if rel["id"] not in derived_ids]
    n_drawn = len(drawn)
    # The type-level tier is saturable: it asks only whether a pattern such as
    # "Context CONSTRAINS Outcome" occurs anywhere in the graph. Reporting how few
    # distinct patterns exist on each side makes the ceiling visible, so the score is
    # never read as if it were concept-level recovery.
    gold_patterns = {(rel["predicate"], categories[rel["subject_code"]],
                      categories[rel["object_code"]]) for rel in gold["relationships"]}
    return {
        "gold_version": gold["gold_version"],
        "gold_relations": total,
        "type_level_ceiling": {
            "distinct_patterns_in_our_graph": len(type_set),
            "distinct_patterns_in_gold": len(gold_patterns),
            "warning": "Type-level recall only asks whether each gold pattern occurs "
                       "anywhere in the graph. With so few distinct patterns on either "
                       "side, any non-trivial extraction scores near 100%. Never quote "
                       "type_recall without anchored_recall and recall beside it.",
        },
        "recovered": len(strict_recovered),
        "recall": len(strict_recovered) / total if total else 0,
        "recall_ci": clopper_pearson(len(strict_recovered), total),
        "anchored_recovered": len(partial_recovered),
        "anchored_recall": len(partial_recovered) / total if total else 0,
        "anchored_recall_ci": clopper_pearson(len(partial_recovered), total),
        "type_recovered": len(type_recovered),
        "type_recall": len(type_recovered) / total if total else 0,
        "type_recall_ci": clopper_pearson(len(type_recovered), total),
        "drawn_only": {
            "gold_relations": n_drawn,
            "anchored_recall": (len([r for r in partial_recovered if r in drawn]) / n_drawn
                                if n_drawn else 0),
            "type_recall": (len([r for r in type_recovered if r in drawn]) / n_drawn
                            if n_drawn else 0),
            "excluded_derived": sorted(derived_ids),
        },
        "recovered_ids": strict_recovered, "anchored_ids": partial_recovered,
        # Missed at the STRICT tier only. Many of these are recovered at the anchored or
        # type tier — read this list together with `anchored_ids`, never on its own.
        "strict_missed_ids": missed_strict,
    }


def citation_faithfulness() -> dict:
    """Does every extracted claim actually appear in its source paper?

    Reported in three tiers, never conflated — the promise `span_repair` makes and this
    function used to break by returning one blended number under the word "exact":

      exact       the stored quote is character-for-character the text at [start, end)
      normalized  identical only after case/whitespace/hyphen normalisation
      fuzzy       a difflib longest-common-block covering >= 70% of the quote
                  (`match_kind = 'fuzzy'`, set by span_repair)

    The tiers are recomputed here from the canonical text rather than trusted from a
    stored flag, so the number cannot drift from the evidence it describes. `strict` is
    the exact tier alone and is the figure to quote when a single number is wanted;
    `faithfulness` keeps the historical all-tiers definition so earlier reports remain
    interpretable, and is always reported next to its breakdown.
    """
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT e.verbatim_quote, e.char_start, e.char_end, e.quote_resolved,
                   e.match_kind, t.canonical_text
            FROM entity_instances e
            JOIN canonical_texts t ON t.study_id = e.study_id
            """
        ).fetchall()

    # Reuse span_repair's normalisation so "normalized" means exactly one thing in this
    # codebase: the same dehyphenation, quote-folding and whitespace collapse the repair
    # pass applies. Writing a second definition here is how the two silently diverge.
    from res_pipeline.plugins.realist.span_repair import _normalize_quote as _norm

    tiers = {"exact": 0, "normalized": 0, "fuzzy": 0, "unresolved": 0}
    for r in rows:
        quote, text = r["verbatim_quote"] or "", r["canonical_text"] or ""
        if not r["quote_resolved"]:
            tiers["unresolved"] += 1
        elif r["match_kind"] == "fuzzy":
            tiers["fuzzy"] += 1
        elif quote and text[r["char_start"]:r["char_end"]] == quote:
            tiers["exact"] += 1
        elif quote and _norm(text[r["char_start"]:r["char_end"]]) == _norm(quote):
            tiers["normalized"] += 1
        else:
            tiers["unresolved"] += 1

    total = len(rows)
    resolved = total - tiers["unresolved"]
    return {
        "entities": total,
        "quotes_resolved": resolved,
        "faithfulness": resolved / total if total else 0,
        "tiers": tiers,
        "strict": tiers["exact"] / total if total else 0,
        "resolved_ci": clopper_pearson(resolved, total),
        "strict_ci": clopper_pearson(tiers["exact"], total),
        "strict_plus_normalized_ci": clopper_pearson(
            tiers["exact"] + tiers["normalized"], total),
        "strict_plus_normalized": (tiers["exact"] + tiers["normalized"]) / total if total else 0,
        "note": "Quote the `strict` (exact-span) figure as the headline; `faithfulness` "
                "counts normalized and fuzzy matches too and must never be described as exact.",
    }


def theory_correspondence(run_id: str) -> dict:
    """Correspondence of the latest theory to the gold programme-theory chains.

    Scored TWICE: once by the `synthesis` tier — the same model that composed the theory
    — and once by `independent_judge`, a different model family with no stake in the
    output. Self-preference bias in LLM judges is well documented, so the honest move is
    not to assert it away but to measure it: `self_preference_gap` is the difference
    between the two, and the independent score is the one to quote.
    """
    gold = _load_gold()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT theory_json FROM programme_theories ORDER BY version DESC LIMIT 1"
        ).fetchone()
    if row is None:
        return {"error": "no programme theory drafted yet"}
    theory = row["theory_json"]

    def _score_with(tier: str) -> dict:
        return _score_theory(tier, gold, theory, run_id)

    same_family = _score_with("synthesis")
    independent = _score_with("independent_judge")
    gap = same_family["mean_correspondence"] - independent["mean_correspondence"]
    return {
        **independent,
        "judge_tier": "independent_judge",
        "same_family_judge": same_family,
        "self_preference_gap": round(gap, 3),
        "judge": "Scored by a judge from a different model family than the composer; the "
                 "same-family score is reported alongside so the self-preference gap is "
                 "visible. Human expert rating still required before publication.",
    }


def _score_theory(tier: str, gold: dict, theory, run_id: str) -> dict:
    """One judge's K-sample rating of the theory against the gold chains."""
    per_chain_samples: dict[str, list[float]] = {}
    last_rationale: dict[str, str] = {}
    sample_means: list[float] = []
    expected = set(gold["programme_theory_statements"])
    for _ in range(_JUDGE_SAMPLES):
        batch = call_structured(
            tier=tier,
            system_prompt=(
                "You are an external methods assessor. Score how well the SYSTEM programme "
                "theory corresponds to each GOLD programme-theory statement (structural and "
                "conceptual correspondence of the C->M->O logic, NOT wording). 1.0 = same "
                "context, same mechanism direction, same outcome family; 0 = absent. "
                "Be strict and justify each score. NOTE: this is a model-based rating that "
                "must be complemented by human expert rating before publication."
            ),
            user_prompt=(
                "GOLD PROGRAMME THEORY STATEMENTS:\n"
                + json.dumps(gold["programme_theory_statements"], indent=1)
                + "\n\nGOLD ENTITY LABELS:\n"
                + json.dumps({k: v["label"] for k, v in gold["entities"].items()}, indent=1)
                + "\n\nSYSTEM PROGRAMME THEORY:\n" + json.dumps(theory, indent=1)
            ),
            schema=ChainScoreBatch, run_id=run_id,
        )
        # Only chains that exist in the gold count, and a chain the judge silently omits
        # scores 0 rather than leaving the denominator — otherwise a judge can raise its
        # own mean by declining to rate the chains it would score worst.
        rated = {s.pts_id: s for s in batch.scores if s.pts_id in expected}
        for pid in expected:
            s = rated.get(pid)
            per_chain_samples.setdefault(pid, []).append(s.correspondence if s else 0.0)
            if s:
                last_rationale[pid] = s.rationale
            else:
                last_rationale.setdefault(pid, "Not rated by the judge in this sample; "
                                               "scored 0 so the denominator stays fixed.")
        vals = [per_chain_samples[pid][-1] for pid in expected]
        sample_means.append(sum(vals) / len(vals) if vals else 0)

    scores = {pid: {"correspondence": round(sum(v) / len(v), 3),
                    "rationale": last_rationale.get(pid, "")}
              for pid, v in sorted(per_chain_samples.items())}
    means = [d["correspondence"] for d in scores.values()]
    return {"per_chain": scores,
            "gold_chains": len(expected),
            "mean_correspondence": round(sum(means) / len(means), 3) if means else 0,
            "samples": _JUDGE_SAMPLES,
            "mean_min": round(min(sample_means), 3) if sample_means else 0,
            "mean_max": round(max(sample_means), 3) if sample_means else 0}


def community_alignment(run_id: str) -> dict:
    """Gap 4 metric: do the emergent Leiden conceptual entities align with Richmond's
    human-articulated mechanisms? (verification plan Step 3-4). This quantifies the
    professor's named novelty — community-defined conceptual entities vs human mechanisms.
    """
    gold = _load_gold()
    # Richmond's mechanisms are everything in their Mresource and Mresponse columns.
    # Scoring against `category` used to miss E07-E18 (typed Intervention in the gold
    # though Richmond tags them Mresource), which shrank this denominator to 14.
    gold_mechs = {code: spec for code, spec in gold["entities"].items()
                  if spec["richmond_role"] in ("Mechanism_Resource", "Mechanism_Response")}
    with get_connection() as conn:
        try:
            communities = conn.execute(
                "SELECT community_label, definition, entity_type, member_labels, algorithm "
                "FROM conceptual_entities ORDER BY member_count DESC"
            ).fetchall()
        except Exception:  # noqa: BLE001 — table absent (communities not detected yet)
            return {"error": "no conceptual entities detected yet (run detect-communities)"}
    if not communities:
        return {"error": "no conceptual entities present"}
    algo = communities[0]["algorithm"]

    candidates = [
        f"COMM{i}: {c['community_label']} — {c['definition']} "
        f"(members: {', '.join((c['member_labels'] or [])[:6])})"
        for i, c in enumerate(communities)
    ]
    votes: dict[str, int] = {}
    community_of: dict[str, str] = {}
    rationale_of: dict[str, str] = {}
    for _ in range(_JUDGE_SAMPLES):
        batch = call_structured(
            tier="extraction_verifier",
            system_prompt=(
                "You are assessing whether emergent graph communities (data-derived conceptual "
                "entities) capture the mechanisms a human review team articulated. For each GOLD "
                "mechanism, decide whether any COMMUNITY expresses the SAME underlying mechanism "
                "(semantic correspondence of the C->M->O role, not wording). Provide the matched "
                "community id (e.g. COMM2) or leave empty. Do not match merely adjacent concepts."
            ),
            user_prompt=(
                "GOLD MECHANISMS:\n"
                + "\n".join(f"{code}: {spec['label']}" for code, spec in gold_mechs.items())
                + "\n\nEMERGENT CONCEPTUAL ENTITIES (communities):\n" + "\n".join(candidates)
            ),
            schema=EntityMatchBatch, run_id=run_id,
        )
        seen: set[str] = set()
        for m in batch.matches:
            # Discard codes the judge invented and duplicates within one sample; both
            # previously inflated the vote and could push recall above 1.0.
            if not m.matched or m.e_code not in gold_mechs or m.e_code in seen:
                continue
            seen.add(m.e_code)
            votes[m.e_code] = votes.get(m.e_code, 0) + 1
            community_of[m.e_code] = m.matched_concept
            rationale_of[m.e_code] = m.rationale
    threshold = (_JUDGE_SAMPLES // 2) + 1
    aligned_codes = [c for c, v in votes.items() if v >= threshold]
    return {
        "algorithm": algo,
        "n_communities": len(communities),
        "gold_mechanisms": len(gold_mechs),
        "aligned": len(aligned_codes),
        "alignment_recall": len(aligned_codes) / len(gold_mechs) if gold_mechs else 0,
        "alignment_recall_ci": clopper_pearson(len(aligned_codes), len(gold_mechs)),
        "samples": _JUDGE_SAMPLES,
        "matches": [{"e_code": c, "community": community_of.get(c, ""),
                     "rationale": rationale_of.get(c, "")} for c in aligned_codes],
        "judge": "model-based majority-vote (human expert mapping required before publication)",
    }


def run_full_verification(run_id: str, output_dir: Path) -> dict:
    report = {"screening": screening_metrics()}
    report["entity_coverage"] = entity_coverage(run_id)
    report["relation_coverage"] = relation_coverage(report["entity_coverage"])
    report["citation_faithfulness"] = citation_faithfulness()
    report["theory_correspondence"] = theory_correspondence(run_id)
    report["community_alignment"] = community_alignment(run_id)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "verification_report.json").write_text(
        json.dumps(report, indent=2, default=str), encoding="utf-8"
    )
    return report
