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
    return list(merged.values())


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
