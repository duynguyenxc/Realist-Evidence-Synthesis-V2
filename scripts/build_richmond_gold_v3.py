"""Build gold/richmond_gold_v3.json — the corrected, scored benchmark.

Why v3 exists
-------------
A line-by-line re-audit of Richmond et al. (2020) against the gold files found four
defects in what the verification harness was actually scoring. `metrics.py` loaded
`gold/richmond_gold.json`, which is byte-identical to `richmond_gold_v1.json`
(MD5 c3edd836964f107ad34de2a80ebc7b35) — so the corrections that `RICHMOND_CONCLUSIONS.md`
§6 claimed were applied had never reached the scorer. The defects:

1. **All five v1 programme-theory chains are cross-context contaminated**, and every one
   routes through ``E19`` ("multiple relevant resources"), a Figure-2 placeholder that
   belongs to the low-knowledge row alone and carries no relation in either version.
   §6 admitted only PTS2 and PTS5. v2's chains are correct and are adopted here.

2. **Richmond's own role tags were overwritten.** E07–E18 are each tagged
   "(Mresource)" in the CMOC statements at §§3.2.2–3.2.5, or sit in Figure 3's column
   headed MECHANISM RESOURCE; the gold typed them ``Intervention``. Our ontology
   legitimately splits Richmond's single Mresource column into ``Intervention`` and
   ``Mechanism_Resource`` — so the fix is not to overwrite one label with the other but
   to record **Richmond's own role** alongside ours, and to let the scorer judge role
   agreement against the scheme Richmond actually used. Without this the system was
   penalised for a distinction Richmond never drew.

3. **Two entities contradict the paper's explicit tags.** §3.2.2 reads "leading to
   insight (Mresponse)" (E21, typed Outcome) and §3.2.5 reads "development of complete
   illness scripts (Mresponse)" (E43, typed Outcome). Both are corrected to
   Mechanism_Response.

4. **E01 is not one of Richmond's contexts.** It is the review population, taken from
   the Conclusions sentence (p. 717); it appears in neither figure and in no relation.
   Scoring it inflated the entity denominator from 46 to 47. It is retained for
   continuity but marked ``scored: false``.

Also corrected: ``reference_to_study_id["28"]`` mapped Eva 2007 to both S004 and S005,
but S005 is Ark 2007 = reference 29, already mapped. R37–R40 are kept in the scored set
for continuity with every published number, but flagged ``derived: true`` — Figure 3
never draws a resource straight to an outcome, it always routes through a reaction, so
these four are transitive shortcuts rather than drawn arrows.

E01–E47 keep their codes and labels; R01–R40 keep their codes, predicates and endpoints.
Nothing is renumbered, so every earlier score remains reproducible by pointing the
scorer back at v1 (``RES_GOLD=v1``).

Run:  python scripts/build_richmond_gold_v3.py
Reads gold/richmond_gold_v2.json; writes gold/richmond_gold_v3.json.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V2 = ROOT / "gold" / "richmond_gold_v2.json"
V3 = ROOT / "gold" / "richmond_gold_v3.json"

# The scored core: the codes every published number is computed over. Kept fixed so a
# score from any version of this file is comparable with any other.
SCORED_ENTITIES = [f"E{i:02d}" for i in range(1, 48)]
SCORED_RELATIONS = [f"R{i:02d}" for i in range(1, 41)]

# Defect 4 — the review population, not one of the five contexts (p. 717 Conclusions).
UNSCORED_ENTITIES = {"E01": "Review population/scope from the Conclusions (p.717); "
                            "not one of the five contexts, absent from Figures 2 and 3 "
                            "and from every relation."}

# Defect 3 — Richmond tags both of these "(Mresponse)" in the CMOC statements.
ROLE_CORRECTIONS = {
    "E21": ("Mechanism_Response",
            "Results 3.2.2 p.714: 'leading to insight (Mresponse) into the reasoning process'."),
    "E43": ("Mechanism_Response",
            "Results 3.2.5 p.716: 'promote development of complete illness scripts (Mresponse)'."),
}

# Defect 2 — our ontology splits Richmond's single mechanism-resource column in two.
# Richmond's scheme has four roles; this maps ours onto theirs.
OUR_TYPE_TO_RICHMOND_ROLE = {
    "Context": "Context",
    "Intervention": "Mechanism_Resource",
    "Mechanism_Resource": "Mechanism_Resource",
    "Mechanism_Response": "Mechanism_Response",
    "Outcome": "Outcome",
}

# Figure 3 routes every resource through a reaction; these four skip it.
DERIVED_RELATIONS = {"R37", "R38", "R39", "R40"}

# Defect in the reference table — ref 28 is Eva 2007 (S004) alone; S005 is Ark 2007 = ref 29.
REFERENCE_CORRECTIONS = {"28": ["S004"]}


def build() -> dict:
    gold = json.loads(V2.read_text(encoding="utf-8"))

    entities: dict[str, dict] = {}
    for code, spec in gold["entities"].items():
        spec = dict(spec)
        category = spec["category"]
        if code in ROLE_CORRECTIONS:
            category, why = ROLE_CORRECTIONS[code]
            spec["category"] = category
            spec["correction"] = why
        spec["richmond_role"] = OUR_TYPE_TO_RICHMOND_ROLE[category]
        spec["scored"] = code in SCORED_ENTITIES and code not in UNSCORED_ENTITIES
        if code in UNSCORED_ENTITIES:
            spec["unscored_reason"] = UNSCORED_ENTITIES[code]
        entities[code] = spec

    relationships = []
    for rel in gold["relationships"]:
        rel = dict(rel)
        rel["scored"] = rel["id"] in SCORED_RELATIONS
        if rel["id"] in DERIVED_RELATIONS:
            rel["derived"] = True
            rel["derived_reason"] = (
                "Transitive shortcut: Figure 3 (p.715) routes every mechanism resource "
                "through a mechanism reaction and never draws resource -> outcome. Kept "
                "in the scored set for continuity with published numbers; exclude it for "
                "a strict figure-fidelity score."
            )
        relationships.append(rel)

    reference_to_study_id = dict(gold.get("reference_to_study_id", {}))
    reference_to_study_id.update(REFERENCE_CORRECTIONS)

    return {
        "source": gold["source"],
        "schema_version": "3.0",
        "derived_from": "gold/richmond_gold_v2.json",
        "scored_entities": sum(1 for s in entities.values() if s["scored"]),
        "scored_relations": sum(1 for r in relationships if r["scored"]),
        "notes": [
            *gold.get("notes", []),
            "v3: adopts v2's corrected programme-theory chains for scoring (all five v1 "
            "chains were cross-context contaminated and routed through E19).",
            "v3: records Richmond's own four-role scheme in `richmond_role`. Our ontology "
            "splits Richmond's Mresource column into Intervention and Mechanism_Resource; "
            "role agreement is judged against Richmond's scheme, not ours.",
            "v3: E21 and E43 re-typed to Mechanism_Response, following Richmond's explicit "
            "(Mresponse) tags at 3.2.2 and 3.2.5.",
            "v3: E01 marked unscored — it is the review population, not a context. Scored "
            "entity denominator is therefore 46, not 47.",
            "v3: R37-R40 flagged derived (transitive shortcuts absent from Figure 3); still "
            "scored so published numbers stay comparable.",
            "v3: reference 28 maps to S004 only (S005 is Ark 2007 = reference 29).",
            "Codes and labels are unchanged from v1/v2; set RES_GOLD=v1 to reproduce any "
            "earlier published score exactly.",
        ],
        "entities": entities,
        "programme_theory_statements": gold["programme_theory_statements"],
        "relationships": relationships,
        "context_study_membership": gold.get("context_study_membership", {}),
        "reference_to_study_id": reference_to_study_id,
    }


def main() -> None:
    data = build()
    V3.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    roles: dict[str, int] = {}
    for spec in data["entities"].values():
        if spec["scored"]:
            roles[spec["richmond_role"]] = roles.get(spec["richmond_role"], 0) + 1
    print(f"wrote {V3}")
    print(f"  scored entities : {data['scored_entities']} (E01 excluded as review population)")
    print(f"  scored relations: {data['scored_relations']} "
          f"({len(DERIVED_RELATIONS)} flagged derived)")
    print("  Richmond roles  : " + ", ".join(f"{k} {v}" for k, v in sorted(roles.items())))


if __name__ == "__main__":
    main()
