"""Does the extracted graph contradict itself?

`ontology.py` makes a *type* error impossible: a relation whose subject or object is the
wrong entity type cannot be constructed. Nothing checks whether the graph, though
well-typed throughout, says incompatible things — and a well-typed graph can be
incoherent in several ways that matter to a realist review:

* the same context both ENABLES and CONSTRAINS the same outcome;
* a cycle in the concept graph, which a C→M→O chain cannot contain and which in practice
  means normalisation left near-synonyms as separate concepts;
* a relation whose two endpoints sit in different CMOCs, which the configuration model
  does not allow;
* a CMOC missing one of context, mechanism or outcome, so it is not a configuration;

Checked against the data on 2026-11-13, and one intended check was **reclassified rather
than kept**: "the same driver asserted both positive and negative inside one study" was
written as a defect detector and is not one. All 29 hits are two-arm experimental
designs — S004 instructs one group in a combined reasoning strategy and tells the other
to use "whatever strategy comes naturally", and the contrast between those arms is the
study's finding. Flagging that as an error would have thrown away the best mechanism
evidence in the corpus. It is reported below as a signal, under its own name.

Each check is a query over stored rows: deterministic, reproducible, no model call, no
API cost. A finding here is an extraction defect worth fixing, not a statistical nuance,
and the checks are cheap enough to run after every extraction.
"""

from __future__ import annotations

from collections import defaultdict

from res_pipeline.core.db import get_connection


def _rows() -> tuple[list[dict], list[dict]]:
    with get_connection() as conn:
        ents = [dict(r) for r in conn.execute(
            "SELECT entity_id, study_id, cmoc_id, entity_type, label, canonical_id "
            "FROM entity_instances").fetchall()]
        rels = [dict(r) for r in conn.execute(
            "SELECT relation_id, study_id, cmoc_id, predicate, subject_entity_id, "
            "object_entity_id FROM typed_relations").fetchall()]
    return ents, rels


def check() -> dict:
    ents, rels = _rows()
    by_id = {e["entity_id"]: e for e in ents}
    findings: dict[str, list] = defaultdict(list)

    # 1. The same context concept both enabling and constraining the same outcome concept.
    enables, constrains = set(), set()
    for r in rels:
        s, o = by_id.get(r["subject_entity_id"]), by_id.get(r["object_entity_id"])
        if not s or not o or not s["canonical_id"] or not o["canonical_id"]:
            continue
        pair = (s["canonical_id"], o["canonical_id"])
        if r["predicate"] == "ENABLES":
            enables.add(pair)
        elif r["predicate"] == "CONSTRAINS":
            constrains.add(pair)
    for pair in sorted(enables & constrains):
        findings["context_both_enables_and_constrains"].append(
            {"context": pair[0], "outcome": pair[1]})

    # 2. A relation whose endpoints belong to different CMOCs.
    for r in rels:
        s, o = by_id.get(r["subject_entity_id"]), by_id.get(r["object_entity_id"])
        if s and o and s["cmoc_id"] != o["cmoc_id"]:
            findings["relation_spans_two_cmocs"].append(
                {"relation_id": r["relation_id"], "from": s["cmoc_id"], "to": o["cmoc_id"]})

    # 3. A CMOC that is not a configuration — missing C, M or O.
    types_of: dict[str, set[str]] = defaultdict(set)
    study_of: dict[str, str] = {}
    for e in ents:
        types_of[e["cmoc_id"]].add(e["entity_type"])
        study_of[e["cmoc_id"]] = e["study_id"]
    MECH = {"Mechanism_Resource", "Mechanism_Response"}
    for cmoc, types in sorted(types_of.items()):
        missing = [n for n, ok in (("Context", "Context" in types),
                                   ("Mechanism", bool(types & MECH)),
                                   ("Outcome", "Outcome" in types)) if not ok]
        if missing:
            findings["cmoc_not_a_configuration"].append(
                {"cmoc_id": cmoc, "missing": missing})

    # 4. A cycle in the causal graph. C -> M -> O should be acyclic at concept level.
    edges: dict[str, set[str]] = defaultdict(set)
    for r in rels:
        s, o = by_id.get(r["subject_entity_id"]), by_id.get(r["object_entity_id"])
        if s and o and s["canonical_id"] and o["canonical_id"]:
            edges[s["canonical_id"]].add(o["canonical_id"])
    WHITE, GREY, BLACK = 0, 1, 2
    colour: dict[str, int] = defaultdict(int)
    cycles: list[list[str]] = []

    def walk(node: str, path: list[str]) -> None:
        colour[node] = GREY
        for nxt in sorted(edges.get(node, ())):
            if colour[nxt] == GREY and len(cycles) < 20:
                cycles.append(path[path.index(nxt):] + [nxt] if nxt in path else [node, nxt])
            elif colour[nxt] == WHITE:
                walk(nxt, path + [nxt])
        colour[node] = BLACK

    import sys as _sys
    limit = _sys.getrecursionlimit()
    _sys.setrecursionlimit(max(limit, 10000))
    try:
        for node in sorted(edges):
            if colour[node] == WHITE:
                walk(node, [node])
    finally:
        _sys.setrecursionlimit(limit)
    for c in cycles:
        findings["causal_cycle"].append({"cycle": c})

    # 5. NOT A DEFECT — a signal. The same driver asserted both positive and negative
    #    inside one study is almost always a two-arm experimental design, and the
    #    contrast between the arms is the mechanism evidence a realist review is after.
    #    Verified on all 29 hits (2026-11-13): every one is a design contrast, none an
    #    extraction error. Counted separately from the defect checks so the distinction
    #    cannot be lost by whoever reads the output next.
    with get_connection() as conn:
        pol = conn.execute(
            "SELECT e.study_id, e.canonical_id, array_agg(DISTINCT c.polarity) pols "
            "FROM entity_instances e JOIN cmocs c USING (cmoc_id) "
            "WHERE e.entity_type IN ('Intervention','Mechanism_Resource') "
            "AND e.canonical_id IS NOT NULL "
            "GROUP BY 1,2 HAVING count(DISTINCT c.polarity) > 1").fetchall()
    for r in pol:
        findings["same_driver_both_polarities_within_one_study"].append(
            {"study_id": r["study_id"], "concept": r["canonical_id"],
             "polarities": list(r["pols"])})

    return {
        "entities": len(ents),
        "relations": len(rels),
        "cmocs": len(types_of),
        "checks": {
            "context_both_enables_and_constrains": len(findings["context_both_enables_and_constrains"]),
            "relation_spans_two_cmocs": len(findings["relation_spans_two_cmocs"]),
            "cmoc_not_a_configuration": len(findings["cmoc_not_a_configuration"]),
            "causal_cycle": len(findings["causal_cycle"]),
        },
        "signals": {
            # Not errors. Within-study experimental contrasts — valuable, not defective.
            "within_study_experimental_contrasts":
                len(findings["same_driver_both_polarities_within_one_study"]),
        },
        "defects_total": sum(len(findings[k]) for k in (
            "context_both_enables_and_constrains", "relation_spans_two_cmocs",
            "cmoc_not_a_configuration", "causal_cycle")),
        "findings": dict(findings),
    }
