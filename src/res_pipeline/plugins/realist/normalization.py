"""Entity Normalization Agent: cluster synonymous entity labels across studies.

Cross-study synthesis requires knowing that "self-efficacy", "self-confidence
calibrated to performance" and "confidence" refer to one concept. This agent
canonicalizes entity instances per entity type:

  * exact/near-exact string matches are merged mechanically;
  * remaining labels are clustered by an LLM pass constrained to the labels it is
    given (it may only group and name, never invent members);
  * every instance receives a ``canonical_id``; the mapping is persisted and
    audited (a merge is an analytic decision under RAMESES II transparency).

Canonical concepts are the nodes of the cross-study knowledge graph;
per-study instances (with their quotes/spans) remain the provenance layer.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

from res_pipeline.core.db import get_connection, log_audit_event
from res_pipeline.core.llm import call_structured
from res_pipeline.core.prompts import P

PROMPT_VERSION = "normalization-v1.0"


class ConceptCluster(BaseModel):
    canonical_label: str = Field(description="Short canonical noun phrase for the concept.")
    member_labels: list[str] = Field(
        min_length=1,
        description="Labels from the provided list belonging to this concept. Copy exactly.",
    )


class ClusteringResult(BaseModel):
    clusters: list[ConceptCluster]


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60]


def _norm_key(text: str) -> str:
    """Aggressive normalisation for mechanical exact-match pre-merge."""
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


_BATCH = 40  # labels per LLM clustering call — keeps each response small and bounded

_STOPWORDS = frozenset("a an and the of to for with in on at by or as into".split())

# Words that set the DIRECTION of a claim. They are mostly stopwords, which is exactly
# why `_tokens` must not be used when comparing a canonical name against its members.
_RELATIONAL = frozenset("""
than with without versus vs compared comparison relative above below over under
against instead rather despite than's beyond
""".split())


def _tokens(label: str) -> frozenset[str]:
    return frozenset(_norm_key(label).split()) - _STOPWORDS


# The guard list lives in code as well as in config, and this is deliberate. A
# missing optional config must never stop a run -- but it must also never silently
# DISABLE a safety check. Reading the guards from config alone meant that a second
# review whose config directory had no `concept_merges.yaml` would run the subset
# rule with an empty guard set, and quietly merge "prior knowledge" into "low prior
# knowledge". A config file can only ADD to this floor, never remove from it.
_GUARDS_FLOOR = frozenset("""
high low higher lower increased decreased reduced improved poorer poor better worse
greater less fewer more novice expert experienced inexperienced positive negative
absent present with without no non un familiar unfamiliar correct incorrect
""".split())


def _merge_config() -> dict:
    """Researcher-declared merges and the words that block an automatic one.

    Absent or unreadable is a supported state: the deterministic rule still runs,
    nothing is declared, and the guard floor above still applies.
    """
    try:
        from res_pipeline.core.config import load_yaml_config

        return load_yaml_config("concept_merges") or {}
    except Exception:  # noqa: BLE001 - optional config
        return {}


def _reconcile_clusters(clusters: list[tuple[str, list[str]]], entity_type: str | None,
                        log=None) -> list[tuple[str, list[str]]]:
    """Fold clusters that batching left apart, deterministically and with a guard.

    WHY. ``_batched_cluster`` unions clusters across batches only when their
    canonical labels match EXACTLY. Two synonymous labels that land in different
    batches and are named slightly differently therefore survive as two concepts,
    each with one instance — and the cross-study graph then shows two rare
    concepts where there is one ordinary one. Measured consequences in the
    Richmond run: its single causal cycle (three near-synonyms of self-explanation)
    and five of the thirteen defects found by adjudicating the 79 single-mention
    concepts one by one.

    TWO RULES, IN THIS ORDER.

    1. Declared merges from ``config/concept_merges.yaml``, which a person wrote
       and gave a reason for. These can join labels that share no words, which no
       mechanical rule can do.

    2. A subset rule: fold A into B when A's content words are a proper subset of
       B's. "self explanation" folds into "active reasoning and self explanation".

    THE GUARD ON RULE 2 IS THE IMPORTANT PART. If one label carries a polarity or
    degree word the other lacks — high/low, improved/poorer, familiar/unfamiliar —
    the merge is REFUSED however much the labels overlap, because "prior
    knowledge" and "low prior knowledge" are different concepts and collapsing
    them would destroy the distinction the whole review rests on. This is the same
    error, in a different stage, as the verification matcher that accepted "high
    clinical knowledge" as a match for "knowledge deficits" until 2026-11-04.
    """
    cfg = _merge_config()
    guards = _GUARDS_FLOOR | frozenset(
        str(w).lower() for w in (cfg.get("polarity_and_degree_guards") or ()))
    by_norm = {_norm_key(label): i for i, (label, _m) in enumerate(clusters)}
    members = [list(m) for _label, m in clusters]
    labels = [label for label, _m in clusters]
    dead: set[int] = set()
    folded: list[tuple[str, str, str]] = []

    # --- rule 1: declared
    for entry in cfg.get("merges") or ():
        if entity_type and entry.get("entity_type") not in (None, entity_type):
            continue
        keep_i = by_norm.get(_norm_key(str(entry.get("keep", ""))))
        if keep_i is None:
            continue
        for fold_label in entry.get("fold") or ():
            fold_i = by_norm.get(_norm_key(str(fold_label)))
            if fold_i is None or fold_i == keep_i or fold_i in dead:
                continue
            members[keep_i].extend(members[fold_i])
            dead.add(fold_i)
            folded.append((labels[fold_i], labels[keep_i], "declared"))

    # --- rule 2: subset, guarded. Longest labels first so the fullest name wins.
    order = sorted(range(len(clusters)), key=lambda i: -len(_tokens(labels[i])))
    for bi in order:
        if bi in dead:
            continue
        bt = _tokens(labels[bi])
        for ai in order:
            if ai == bi or ai in dead:
                continue
            at = _tokens(labels[ai])
            if not at or not at < bt:
                continue
            if (at ^ bt) & guards:
                continue  # a polarity or degree word differs — these are not synonyms
            members[bi].extend(members[ai])
            dead.add(ai)
            folded.append((labels[ai], labels[bi], "subset"))

    if folded and log:
        for src, dst, how in folded:
            log(f"    merged ({how}): {src!r} -> {dst!r}")
    kept = [(labels[i], members[i]) for i in range(len(clusters)) if i not in dead]
    _warn_on_inverted_names(kept, guards, log)
    return kept


def _warn_on_inverted_names(clusters: list[tuple[str, list[str]]],
                            guards: frozenset[str], log=None) -> list[tuple[str, str]]:
    """Flag a canonical name that contradicts the labels it was built from.

    The clustering agent is allowed to NAME each concept, and nothing checked that the
    name it chose agrees with its members. In the Richmond run it renamed an outcome whose
    instance label was "lower accuracy THAN explicit combined instruction" to
    "lower accuracy WITH explicit instruction", which asserts the opposite of the study's
    finding — S005 instructed one arm and left the other to reason spontaneously, and the
    instructed arm did better. The extraction was correct and the quote supported it; the
    name inverted it, and the inversion was only visible by reading the source paper.

    This cannot be repaired automatically without guessing which side is right, so it is
    reported rather than corrected. A warning that a human reads beats a silent rename.
    """
    # NOT `_tokens`. That strips stopwords, and in the case this check exists for the
    # inversion is carried BY a stopword: "lower accuracy THAN explicit instruction"
    # against "lower accuracy WITH explicit instruction". Removing "with" and "than"
    # deletes the only evidence of the contradiction, so the comparison is made on the
    # raw normalised words plus a set of relational words that change a claim's direction.
    relational = guards | _RELATIONAL
    suspects: list[tuple[str, str]] = []
    for label, members in clusters:
        lt = frozenset(_norm_key(label).split()) & relational
        for m in members:
            mt = frozenset(_norm_key(m).split()) & relational
            if mt and lt != mt:
                suspects.append((label, m))
                break
    if suspects and log:
        for label, m in suspects:
            log(f"    [check] canonical name {label!r} differs in polarity/degree from "
                f"member {m!r} — read the source before trusting the name")
    return suspects


def _batched_cluster(items: list[str], system_prompt: str, run_id: str,
                     noun: str = "LABELS") -> list[tuple[str, list[str]]]:
    """Cluster ``items`` in bounded batches, then merge clusters that share a
    canonical label across batches.

    A single call over ~100+ items can send the model into a degenerate
    repetition loop that hits the completion-token ceiling. We instead sort
    (so near-duplicate strings sit adjacent and land in the same batch), split
    into batches of ``_BATCH``, cluster each, and union members whose canonical
    label matches across batches — recovering cross-batch synonyms.
    """
    ordered = sorted(items)
    merged: dict[str, tuple[str, list[str]]] = {}  # norm(canonical) -> (display, members)
    for start in range(0, len(ordered), _BATCH):
        batch = ordered[start:start + _BATCH]
        result = call_structured(
            tier="normalization",
            system_prompt=P("normalization.1",
                system_prompt),
            user_prompt=f"{noun}:\n" + "\n".join(f"- {x}" for x in batch),
            schema=ClusteringResult,
            run_id=run_id,
        )
        batch_set = set(batch)
        for cluster in result.clusters:
            members = [m for m in cluster.member_labels if m in batch_set]
            if not members:
                continue
            key = _norm_key(cluster.canonical_label)
            if key in merged:
                merged[key][1].extend(members)
            else:
                merged[key] = (cluster.canonical_label, list(members))
    return _reconcile_clusters(list(merged.values()), entity_type=None)


def build_concept_families(run_id: str) -> dict[str, int]:
    """Second-level clustering: canonical concepts -> broader concept FAMILIES.

    Richmond's analysis operates at family granularity (5 broad student contexts,
    ~12 intervention types). Demi-regularity detection therefore runs over
    families; the concept and instance layers below remain intact for provenance.
    """
    stats: dict[str, int] = {}
    with get_connection() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS concept_families ("
            " canonical_id TEXT PRIMARY KEY, entity_type TEXT NOT NULL,"
            " family_id TEXT NOT NULL, family_label TEXT NOT NULL,"
            " run_id TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now())"
        )
        conn.execute("DELETE FROM concept_families")
        types = [r["entity_type"] for r in conn.execute(
            "SELECT DISTINCT entity_type FROM entity_instances"
        ).fetchall()]

    for entity_type in types:
        with get_connection() as conn:
            concepts = [r["canonical_id"] for r in conn.execute(
                "SELECT DISTINCT canonical_id FROM entity_instances "
                "WHERE entity_type=%s AND canonical_id IS NOT NULL ORDER BY 1",
                (entity_type,),
            ).fetchall()]
        if not concepts:
            continue
        clusters = _batched_cluster(
            concepts,
            system_prompt=(
                P("normalization.2",
                f"You are grouping {entity_type} concepts from a realist synthesis of "
                "clinical-reasoning education into BROAD analytic families, at the "
                "granularity a published realist review would use for cross-study "
                "patterns (e.g., contexts like 'low prior knowledge' vs 'high prior "
                "knowledge' vs 'confidence/coping'; interventions like 'simulation/"
                "virtual patients', 'self-explanation', 'reasoning-strategy instruction', "
                "'feedback', 'worked examples', 'test-enhanced learning'). Rules: every "
                "provided concept id appears in exactly one family; copy ids exactly; "
                "prefer 4-12 families; name each family with a short analytic label.")
            ),
            run_id=run_id, noun="CONCEPT IDS",
        )
        assigned: dict[str, tuple[str, str]] = {}
        concept_set = set(concepts)
        for canonical_label, members in clusters:
            family_id = f"fam:{entity_type[:4].lower()}:{_slug(canonical_label)}"
            for member in members:
                if member in concept_set:
                    assigned[member] = (family_id, canonical_label)
        for concept in concepts:
            assigned.setdefault(concept, (f"fam:{concept}", concept))
        with get_connection() as conn:
            for canonical_id, (family_id, family_label) in assigned.items():
                conn.execute(
                    "INSERT INTO concept_families (canonical_id, entity_type, family_id, "
                    "family_label, run_id) VALUES (%s,%s,%s,%s,%s) "
                    "ON CONFLICT (canonical_id) DO UPDATE SET family_id=EXCLUDED.family_id, "
                    "family_label=EXCLUDED.family_label",
                    (canonical_id, entity_type, family_id, family_label, run_id),
                )
        stats[entity_type] = len({v[0] for v in assigned.values()})
        log_audit_event(run_id, "normalization_agent", "families_built",
                        subject_ref=entity_type,
                        detail={"n_concepts": len(concepts),
                                "n_families": stats[entity_type]})
    return stats


def normalize_entities(run_id: str) -> dict[str, int]:
    """Assign canonical_id to every entity instance, per entity type."""
    stats: dict[str, int] = {}
    with get_connection() as conn:
        types = [r["entity_type"] for r in conn.execute(
            "SELECT DISTINCT entity_type FROM entity_instances"
        ).fetchall()]

    for entity_type in types:
        with get_connection() as conn:
            labels = [r["label"] for r in conn.execute(
                "SELECT DISTINCT label FROM entity_instances WHERE entity_type=%s "
                "ORDER BY label",
                (entity_type,),
            ).fetchall()]
        if not labels:
            continue

        # Mechanical pre-merge: labels with identical normalised keys are the same
        # concept (case/punctuation/whitespace variants). Cluster one representative
        # per key with the LLM, then fan the canonical_id back to all variants.
        key_to_variants: dict[str, list[str]] = {}
        for label in labels:
            key_to_variants.setdefault(_norm_key(label), []).append(label)
        reps = [variants[0] for variants in key_to_variants.values()]

        clusters = _batched_cluster(
            reps,
            system_prompt=(
                P("normalization.3",
                "You are canonicalizing concept labels for a realist-synthesis knowledge "
                f"graph. All labels below are of type {entity_type}. Group labels that refer "
                "to the SAME underlying concept (synonyms, paraphrases, granularity variants) "
                "into clusters and give each cluster a short canonical label. Rules: every "
                "provided label appears in EXACTLY one cluster; copy member labels exactly; "
                "do NOT invent labels; when unsure, keep labels in separate clusters "
                "(over-merging corrupts the analysis, under-merging is recoverable).")
            ),
            run_id=run_id,
        )

        # Build mapping with safety: unassigned/hallucinated labels fall back to themselves.
        rep_set = set(reps)
        rep_to_canon: dict[str, str] = {}
        for canonical_label, members in clusters:
            canonical_id = f"{entity_type[:4].lower()}:{_slug(canonical_label)}"
            for member in members:
                if member in rep_set:
                    rep_to_canon[member] = canonical_id
        assigned: dict[str, str] = {}
        for key, variants in key_to_variants.items():
            rep = variants[0]
            canonical_id = rep_to_canon.get(rep, f"{entity_type[:4].lower()}:{_slug(rep)}")
            for variant in variants:
                assigned[variant] = canonical_id
        for label in labels:
            assigned.setdefault(label, f"{entity_type[:4].lower()}:{_slug(label)}")

        with get_connection() as conn:
            for label, canonical_id in assigned.items():
                conn.execute(
                    "UPDATE entity_instances SET canonical_id=%s "
                    "WHERE entity_type=%s AND label=%s",
                    (canonical_id, entity_type, label),
                )
        stats[entity_type] = len(set(assigned.values()))
        log_audit_event(
            run_id, "normalization_agent", "entity_type_normalized",
            subject_ref=entity_type,
            detail={"n_labels": len(labels), "n_concepts": len(set(assigned.values())),
                    "prompt_version": PROMPT_VERSION},
        )
    return stats
