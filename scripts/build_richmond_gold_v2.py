"""Build gold/richmond_gold_v2.json from v1 plus a direct re-reading of Richmond et al. (2020).

Why v2 exists (see gold/RICHMOND_CONCLUSIONS.md §6): the v1 programme-theory chains PTS2 and
PTS5 cited interventions Richmond assigns to other contexts, nine Figure-3 elements had no
E-code, and Richmond's per-context study lists (reference numbers, pp. 714-716) were never
transcribed. E01-E47 and R01-R40 are kept byte-identical so every earlier score stays
reproducible; additions are flagged ``figure3_supplement``.

Run:  python scripts/build_richmond_gold_v2.py
Reads gold/richmond_gold_v1.json and the ``studies`` table; writes gold/richmond_gold_v2.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from res_pipeline.core.db import get_connection  # noqa: E402

V1 = ROOT / "gold" / "richmond_gold_v1.json"
V2 = ROOT / "gold" / "richmond_gold_v2.json"

# Results 3.2.1-3.2.5 (p. 714-716) and Figure 2 (p. 713), transcribed in RICHMOND_CONCLUSIONS.md §4.
PTS = {
    "PTS1": {
        "context_code": "E02",
        "context_label": "Students with 'low knowledge', low clinical domain-specific knowledge, "
                         "or inability to use knowledge in a reasoning situation",
        "canonical_chain": "E13/E15/E17/E18/E48 -> E53/E54/E55/E56 -> E46 ; "
                           "E16/E49/E50/E51/E52 -> E57/E58/E59/E23/E45 -> E47",
        "expected_interventions": ["E13", "E15", "E17", "E18", "E48", "E16", "E49", "E50", "E51", "E52"],
        "expected_mechanism_responses": ["E53", "E54", "E55", "E56", "E57", "E58", "E59", "E23", "E45"],
        "expected_outcomes": ["E46", "E47"],
        "source": "Results 3.2.1 p.714; Figure 3 p.715", "n_studies_stated": 22,
    },
    "PTS2": {
        "context_code": "E03",
        "context_label": "Students with high clinical domain-specific knowledge",
        "canonical_chain": "E07 -> E20 -> E21/E22 ; E08 -> E23/E24 -> E25",
        "expected_interventions": ["E07", "E08"],
        "expected_mechanism_responses": ["E20", "E23", "E24"],
        "expected_outcomes": ["E21", "E22", "E25"],
        "source": "Results 3.2.2 p.714; Figure 2 rows 2-3", "n_studies_stated": 7,
    },
    "PTS3": {
        "context_code": "E04",
        "context_label": "Positive coping strategies or appropriate self-confidence/self-efficacy",
        "canonical_chain": "E09/E10 -> E26 -> E27 -> E28/E29/E30 ; E11 -> E31 -> E22",
        "expected_interventions": ["E09", "E10", "E11"],
        "expected_mechanism_responses": ["E26", "E27", "E31"],
        "expected_outcomes": ["E28", "E29", "E30", "E22"],
        "source": "Results 3.2.3 p.714; Figure 2 row 4", "n_studies_stated": 5,
    },
    "PTS4": {
        "context_code": "E05",
        "context_label": "Negative coping strategies or lacking self-confidence/self-efficacy",
        "canonical_chain": "E10 -> E32/E33/E34 -> E35 -> E36/E37/E38",
        "expected_interventions": ["E10"],
        "expected_mechanism_responses": ["E32", "E33", "E34", "E35"],
        "expected_outcomes": ["E36", "E37", "E38"],
        "source": "Results 3.2.4 p.716; Figure 2 row 5", "n_studies_stated": 4,
    },
    "PTS5": {
        "context_code": "E06",
        "context_label": "Students with different levels of knowledge within a group",
        "canonical_chain": "E12 -> E39/E20 -> E40/E41 ; E13 -> E42 -> E43/E44 ; E14 -> E45 -> E38",
        "expected_interventions": ["E12", "E13", "E14"],
        "expected_mechanism_responses": ["E39", "E20", "E42", "E45"],
        "expected_outcomes": ["E40", "E41", "E43", "E44", "E38"],
        "source": "Results 3.2.5 p.716; Figure 2 rows 6-7", "n_studies_stated": 9,
    },
}

# Figure 3 (p. 715) elements that had no E-code in v1.
SUPPLEMENT_ENTITIES = {
    "E48": ("Intervention", "promotion of analytical or step-wise approach as a reasoning scaffold"),
    "E49": ("Intervention", "inducing or imposing time constraint to deliberately force non-analytical reasoning"),
    "E50": ("Intervention", "listening to experts explain their reasoning, which may skip steps or use pattern recognition"),
    "E51": ("Intervention", "increased case difficulty or case with significant reasoning challenge"),
    "E52": ("Intervention", "listening to peer reasoning as a passive recipient when that self-explanation includes mistakes"),
    "E53": ("Mechanism_Response", "assume similar level prior knowledge resulting in sense of 'feeling at ease'"),
    "E54": ("Mechanism_Response", "empowered to trust in their 'sense of familiarity' and developing ability"),
    "E55": ("Mechanism_Response", "sense of clarity and developing understanding; affirmation the individual "
                                  "possesses sufficient knowledge for reasoning"),
    "E56": ("Mechanism_Response", "relieves the tension of not immediately knowing the answer; learner feels "
                                  "comfortable, supported and at ease"),
    "E57": ("Mechanism_Response", "spontaneous outputs from non-analytical reasoning (including guessing) with "
                                  "resultant frustration and potential distress"),
    "E58": ("Mechanism_Response", "resentment or panic at not recalling or 'knowing' immediately"),
    "E59": ("Mechanism_Response", "difficulty understanding non-analytical thought processes; discordance "
                                  "between illness scripts"),
}
SUPPLEMENT_RELATIONS = [  # Figure 3 rows, left to right
    ("E17", "TRIGGERS", "E53"), ("E18", "TRIGGERS", "E54"), ("E13", "TRIGGERS", "E55"),
    ("E15", "TRIGGERS", "E55"), ("E48", "TRIGGERS", "E56"),
    ("E53", "LEADS_TO", "E46"), ("E54", "LEADS_TO", "E46"), ("E55", "LEADS_TO", "E46"), ("E56", "LEADS_TO", "E46"),
    ("E49", "TRIGGERS", "E57"), ("E16", "TRIGGERS", "E58"), ("E50", "TRIGGERS", "E59"),
    ("E51", "TRIGGERS", "E23"), ("E52", "TRIGGERS", "E45"),
    ("E57", "LEADS_TO", "E47"), ("E58", "LEADS_TO", "E47"), ("E59", "LEADS_TO", "E47"),
    ("E23", "LEADS_TO", "E47"), ("E45", "LEADS_TO", "E47"),
    ("E02", "ENABLES", "E53"), ("E02", "CONSTRAINS", "E47"),
]

# Richmond's reference numbers (reference list pp. 718-719) -> first author, year.
REFS = {
    8: ("Sherbino", 2014), 9: ("Chamberland", 2013), 26: ("Kulatunga-Moruzi", 2001), 27: ("Ark", 2006),
    28: ("Eva", 2007), 29: ("Ark", 2007), 30: ("Myung", 2013), 31: ("Evered", 2013), 35: ("Linn", 2012),
    36: ("Bender", 2011), 37: ("Graafland", 2014), 38: ("Nendaz", 2011), 39: ("Borleffs", 2003),
    40: ("Klamen", 2011), 41: ("Jacobson", 2010), 42: ("Mamede", 2012), 43: ("Blissett", 2012),
    44: ("Chamberland", 2011), 45: ("Coderre", 2010), 46: ("Pinnock", 2012), 47: ("Adams", 2011),
    48: ("Chamberland", 2015), 49: ("Chamberland", 2015), 50: ("McGregor", 2012), 51: ("Bloice", 2014),
    56: ("Kopp", 2008), 57: ("Boshuizen", 2012), 58: ("Raupach", 2016),
}
# Title fragments to split the two Chamberland 2015 papers and the two Ark papers.
TITLE_HINTS = {48: "examples and prompts", 49: "peers or experts", 27: "best of both worlds", 29: "flexibility"}
# "N studies contributed to this theory" citations, per context (pp. 714-716).
CONTEXT_REFS = {
    "E02": [9] + list(range(26, 32)) + list(range(35, 50)),
    "E03": [8, 9, 30, 38, 44, 50, 51],
    "E04": [36, 37, 46, 50, 51],
    "E05": [36, 46, 50, 51],
    "E06": [29, 40, 43, 46, 47, 51, 56, 57, 58],
}


def map_refs_to_study_ids() -> dict[int, list[str]]:
    with get_connection() as conn:
        studies = conn.execute("SELECT study_id, title, authors, year FROM studies ORDER BY study_id").fetchall()
    out: dict[int, list[str]] = {}
    for ref, (surname, year) in REFS.items():
        hits = [s for s in studies if surname.lower() in str(s["authors"] or "").lower()
                and str(s["year"]) == str(year)]
        if len(hits) > 1 and ref in TITLE_HINTS:
            hits = [h for h in hits if TITLE_HINTS[ref].lower() in (h["title"] or "").lower()] or hits
        if ref == 35 and not hits:  # Linn 2012: metadata record is a broken reprint header
            hits = [s for s in studies if "Australian Family Physician" in (s["title"] or "")]
        out[ref] = [h["study_id"] for h in hits]
    return out


def build() -> dict:
    g = json.loads(V1.read_text(encoding="utf-8"))
    g["programme_theory_statements"] = PTS
    for code, (cat, label) in SUPPLEMENT_ENTITIES.items():
        g["entities"][code] = {"category": cat, "label": label, "location": "Figure 3, p.715",
                               "figure3_supplement": True}
    next_id = len(g["relationships"]) + 1
    for i, (s, p, o) in enumerate(SUPPLEMENT_RELATIONS):
        g["relationships"].append({"id": f"R{next_id + i:02d}", "subject_code": s, "predicate": p,
                                   "object_code": o, "figure3_supplement": True,
                                   "location": "Figure 3, p.715"})
    ref_to_s = map_refs_to_study_ids()
    g["context_study_membership"] = {
        code: {"richmond_refs": refs, "n_studies_stated": len(refs),
               "study_ids": sorted({sid for r in refs for sid in ref_to_s.get(r, [])}),
               "unmapped_refs": [r for r in refs if not ref_to_s.get(r)]}
        for code, refs in CONTEXT_REFS.items()}
    g["reference_to_study_id"] = {str(k): v for k, v in ref_to_s.items()}
    g["schema_version"] = "2.0"
    g["notes"] = [n for n in g["notes"] if "implementation_plan" not in n] + [
        "v2.0 (2026-09-10): PTS1-5 rebuilt from Results 3.2.1-3.2.5 and Figure 2; v1 PTS2/PTS5 cited "
        "interventions Richmond assigns to other contexts.",
        "v2.0: E48-E59 and R41-R61 are Figure-3 elements absent from v1, flagged figure3_supplement=true; "
        "report coverage on the original 47/40 AND on the complete set.",
        "v2.0: context_study_membership transcribes the reference numbers Richmond cites per context "
        "(pp. 714-716) mapped to our study ids; unmapped_refs need a manual check.",
        "v1 preserved unchanged as gold/richmond_gold_v1.json.",
    ]
    return g


def self_check(g: dict) -> None:
    ents = g["entities"]
    assert len(ents) == 59 and len(g["relationships"]) == 61, (len(ents), len(g["relationships"]))
    for pts in g["programme_theory_statements"].values():
        for k in ("expected_interventions", "expected_mechanism_responses", "expected_outcomes"):
            assert all(c in ents for c in pts[k]), (pts["context_code"], k)
    for r in g["relationships"]:
        assert r["subject_code"] in ents and r["object_code"] in ents, r["id"]
    included = {r for refs in CONTEXT_REFS.values() for r in refs}
    assert included <= set(REFS), included - set(REFS)
    assert len(set(REFS)) == 28, "Richmond includes exactly 28 studies"


if __name__ == "__main__":
    gold = build()
    self_check(gold)
    V2.write_text(json.dumps(gold, indent=2, ensure_ascii=False), encoding="utf-8")
    for ref, ids in gold["reference_to_study_id"].items():
        flag = "" if len(ids) == 1 else "  <-- CHECK"
        print(f"ref {ref:>2} {REFS[int(ref)][0]:18}{REFS[int(ref)][1]} -> {ids}{flag}")
    for code, m in gold["context_study_membership"].items():
        print(f"{code}: {m['n_studies_stated']} stated -> {len(m['study_ids'])} mapped; unmapped={m['unmapped_refs']}")
    print(f"wrote {V2} ({len(gold['entities'])} entities, {len(gold['relationships'])} relations)")
