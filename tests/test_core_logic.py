"""Unit tests for pure pipeline logic (no API / no DB required)."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def test_screening_combine_is_recall_first():
    from res_pipeline.core.screening import ScreeningVote, _combine

    def vote(d):
        return ScreeningVote(decision=d, rationale="x" * 25, confidence=0.9)

    # Any include -> include (union-of-includes).
    assert _combine(vote("include"), vote("uncertain")) == "include"
    assert _combine(vote("exclude"), vote("include")) == "include"
    # Both exclude -> exclude.
    assert _combine(vote("exclude"), vote("exclude")) == "exclude"
    # Otherwise uncertain (routed to HITL-1).
    assert _combine(vote("uncertain"), vote("exclude")) == "uncertain"
    assert _combine(vote("uncertain"), vote("uncertain")) == "uncertain"


def test_span_normalization_dehyphenates_and_maps_offsets():
    from res_pipeline.plugins.realist.span_repair import _normalize_quote, _normalize_with_map

    text = "The diag-\nnostic accuracy improved   significantly across the cohort."
    norm, index_map = _normalize_with_map(text)
    assert "diagnostic accuracy improved significantly" in norm
    assert len(norm) == len(index_map)  # every normalized char maps back
    # Offsets are monotonically non-decreasing into the original text.
    assert all(index_map[i] <= index_map[i + 1] for i in range(len(index_map) - 1))

    quote = "diagnostic accuracy improved significantly"
    pos = norm.find(_normalize_quote(quote))
    assert pos != -1
    original_start = index_map[pos]
    assert text[original_start:original_start + 4].lower() == "diag"


def test_relation_demotion_preserves_untyped_candidate():
    from res_pipeline.plugins.realist.ontology import (
        EntityInstance,
        EntityType,
        Predicate,
        Provenance,
        TypedRelation,
    )

    prov = Provenance(
        study_id="S001", text_unit_id="S001-tu-0001", char_start=0, char_end=10,
        verbatim_quote="evidence", extractor_model="t", prompt_version="v", confidence=0.8,
    )
    outcome = EntityInstance(entity_id="a", entity_type=EntityType.OUTCOME,
                             label="accuracy", provenance=prov)
    context = EntityInstance(entity_id="b", entity_type=EntityType.CONTEXT,
                             label="novice", provenance=prov)
    # Outcome PROVIDES Context is nonsense under the ontology, but as UNTYPED_CANDIDATE
    # it must be preservable (surfaced for HITL-2, never silently dropped).
    rel = TypedRelation(relation_id="r", predicate=Predicate.UNTYPED_CANDIDATE,
                        subject=outcome, object=context, provenance=prov)
    assert rel.predicate is Predicate.UNTYPED_CANDIDATE


# ---------------------------------------------------------------------------
# Review isolation. Richmond's corpus, gold standard and published outputs live
# at the default paths; a second review on a new topic must be able to go
# somewhere else. Before 2026-11-02 only POSTGRES_DB was overridable, so a new
# review had nowhere to write but over `outputs/RESULTS.html` — the artefact of
# record, which M38 found had already been silently overwritten once.
# ---------------------------------------------------------------------------
def _reload_config(monkeypatch, **env):
    """Re-import config under a patched environment; paths resolve at import."""
    import importlib

    for key in ("RES_CONFIG_DIR", "RES_DATA_DIR", "RES_GOLD_DIR", "RES_OUTPUTS_DIR"):
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    import res_pipeline.core.config as cfg

    return importlib.reload(cfg)


def test_paths_default_to_the_project_root(monkeypatch):
    cfg = _reload_config(monkeypatch)
    assert cfg.CONFIG_DIR == cfg.PROJECT_ROOT / "config"
    assert cfg.OUTPUTS_DIR == cfg.PROJECT_ROOT / "outputs"
    assert cfg.GOLD_DIR == cfg.PROJECT_ROOT / "gold"


def test_a_second_review_can_be_pointed_away_from_richmond(monkeypatch):
    cfg = _reload_config(
        monkeypatch, RES_CONFIG_DIR="config-emotion", RES_OUTPUTS_DIR="outputs-emotion"
    )
    assert cfg.CONFIG_DIR == cfg.PROJECT_ROOT / "config-emotion"
    assert cfg.OUTPUTS_DIR == cfg.PROJECT_ROOT / "outputs-emotion"
    # Richmond's gold standard is not dragged along by an unrelated override.
    assert cfg.GOLD_DIR == cfg.PROJECT_ROOT / "gold"
    # And nothing the second review writes lands under the first review's outputs.
    assert cfg.PROJECT_ROOT / "outputs" not in cfg.OUTPUTS_DIR.parents


def test_absolute_override_is_honoured_and_blank_falls_back(monkeypatch):
    cfg = _reload_config(monkeypatch, RES_OUTPUTS_DIR="/tmp/res-out", RES_CONFIG_DIR="   ")
    assert str(cfg.OUTPUTS_DIR) == "/tmp/res-out"
    # A blank value must mean "unset", not resolve to the project root itself —
    # which would make CONFIG_DIR/"ontology.yaml" silently miss.
    assert cfg.CONFIG_DIR == cfg.PROJECT_ROOT / "config"


def test_active_paths_marks_what_was_overridden(monkeypatch):
    cfg = _reload_config(monkeypatch, RES_OUTPUTS_DIR="outputs-emotion")
    shown = cfg.active_paths()
    assert "[overridden]" in shown["outputs"]
    assert "[overridden]" not in shown["config"]


# --- the matcher guard (found 2026-09-30, fixed 2026-11-04) -------------------------
#
# These two rationales are VERBATIM from the stored verification in outputs/RESULTS.html,
# where both are recorded as `matched: true`. E24 sits inside the published headline of
# 34/46. They are the regression test: if either ever counts as a match again, the headline
# is wrong again.

E03_RATIONALE = (
    "Matches the same construct of students' domain knowledge level; the extracted context "
    "explicitly refers to learners with incomplete/underdeveloped knowledge, which aligns "
    "with high clinical domain-specific knowledge as the opposite end of the same knowledge "
    "construct."
)
E24_RATIONALE = (
    "This concept covers reliance on analytic reasoning and similarity-based processes; the "
    "evidence mentions novices relying on conscious, analytic reasoning, which is the "
    "opposite of non-analytical reasoning, so it does not match the gold construct."
)


def test_guard_refuses_the_two_known_defects():
    from res_pipeline.verification.metrics import _rationale_refutes

    assert "opposite polarity" in _rationale_refutes(E03_RATIONALE)
    # E24 states a non-match outright, which is the stronger of the two reasons.
    assert "non-match" in _rationale_refutes(E24_RATIONALE)


def test_guard_leaves_genuine_matches_alone():
    from res_pipeline.verification.metrics import _rationale_refutes

    genuine = [
        # E02 — the correct half of the E02/E03 pair that over-merged onto one concept.
        "The evidence explicitly says students had 'basic relevant knowledge' that was "
        "'incomplete and error-prone,' which denotes low or insufficient clinical "
        "domain-specific knowledge.",
        # A cross-role match, which is expected and must not be penalised.
        "This extracted mechanism captures student affect/self-confidence in reasoning, "
        "including feeling cocooned and challenged; it is the closest same-construct match "
        "for positive coping/self-efficacy.",
        # "not" appearing for an unrelated reason must not trip the guard.
        "The construct is the same even though the wording is not identical.",
    ]
    for rationale in genuine:
        assert _rationale_refutes(rationale) == "", rationale


def test_every_stored_rationale_except_those_two_survives_the_guard():
    """The guard was calibrated on all 46 stored rationales and flags exactly two.

    A guard that also refused honest matches would lower the headline for the wrong
    reason, so the false-positive count is part of the contract, not an incidental.
    """
    import html
    import re

    from res_pipeline.core.config import OUTPUTS_DIR
    from res_pipeline.verification.metrics import _rationale_refutes

    results = OUTPUTS_DIR / "RESULTS.html"
    if not results.exists():  # pragma: no cover - artefact absent on a fresh checkout
        return
    page = results.read_text(encoding="utf-8")
    flagged = set()
    for match in re.finditer(r'<td class="num">(E\d\d)</td>(.*?)</tr>', page, re.S):
        cells = re.findall(r"<td[^>]*>(.*?)</td>", match.group(2), re.S)
        if len(cells) < 4:
            continue
        rationale = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", cells[3])))
        if _rationale_refutes(rationale):
            flagged.add(match.group(1))
    assert flagged == {"E03", "E24"}, flagged


# --- retroduction without a quote (P1.2, 2026-11-04) --------------------------------
#
# The one place the pipeline is allowed to assert something the corpus does not say. The
# tests below are about the fences around it, not the inference itself.


def test_theorised_concepts_are_not_stored_as_evidence():
    """`theorised_entities` must be a separate table from `entity_instances`.

    The temptation is to add a nullable `verbatim_quote` and keep one table. That would
    make every existing query — coverage, faithfulness, the exports, RESULTS.html —
    silently count inference as evidence, which is the single failure this project
    cannot absorb. The separation is the safety property, so it is asserted here.
    """
    from res_pipeline.core.db import SCHEMA_DDL

    assert "CREATE TABLE IF NOT EXISTS theorised_entities" in SCHEMA_DDL
    # entity_instances still refuses anything ungrounded.
    entity_block = SCHEMA_DDL.split("CREATE TABLE IF NOT EXISTS entity_instances")[1]
    entity_block = entity_block.split("CREATE TABLE")[0]
    assert "verbatim_quote  TEXT NOT NULL" in entity_block
    # And a theorised row is a proposal until a human says otherwise.
    theorised = SCHEMA_DDL.split("CREATE TABLE IF NOT EXISTS theorised_entities")[1]
    theorised = theorised.split("CREATE TABLE")[0]
    assert "DEFAULT 'proposed'" in theorised
    assert "ratified_by" in theorised


def test_a_theorised_proposal_must_be_falsifiable(monkeypatch):
    """A proposal claims certain words are absent; those words are checked.

    Without this, retroduction degrades into restating what the papers already say, which
    is extraction's job and would inflate coverage with nothing new.
    """
    from res_pipeline.plugins.realist import theorised

    class _Conn:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def execute(self, *a, **k):
            return self

        def fetchall(self):
            return [{"canonical_text": "Students improved their diagnostic reasoning."}]

    monkeypatch.setattr(theorised, "get_connection", lambda: _Conn())

    missing, present = theorised._absent(["emotion", "self-efficacy", "reasoning"])
    assert "reasoning" in present, "a word that IS in the corpus must be caught"
    assert set(missing) == {"emotion", "self-efficacy"}
    # No checkable claim at all is not a free pass either.
    assert theorised._absent([]) == ([], [])


# --- P2: search, retrieval, and the isolation guard (2026-11-06) --------------------


def test_second_review_cannot_write_into_richmonds_database(monkeypatch):
    """Isolated directories plus a shared database is the one silently fatal combination.

    RES_*_DIR gives a new topic somewhere to put its corpus and outputs, but the
    entities, relations and CMOCs live in Postgres. A run with RES_CONFIG_DIR set and
    POSTGRES_DB left alone would write a different topic's extractions into the tables
    every published Richmond figure was computed from — no error, no symptom, until
    someone recounted.
    """
    cfg = _reload_config(monkeypatch, RES_CONFIG_DIR="config-emotion")
    import pytest

    with pytest.raises(cfg.IsolationError):
        cfg.assert_isolated()
    assert "NOT ISOLATED" in cfg.active_paths()["database"]

    # With both overridden it is allowed, and with neither (Richmond) it is allowed.
    cfg = _reload_config(monkeypatch, RES_CONFIG_DIR="config-emotion",
                         POSTGRES_DB="realist_emotion")
    cfg.assert_isolated()
    cfg = _reload_config(monkeypatch)
    cfg.assert_isolated()


def test_retrieval_is_inert_below_the_cap():
    """Richmond's evidence pack must be byte-identical, or published figures move."""
    from res_pipeline.core.retrieval import select

    items = [{"t": f"statement {i}"} for i in range(94)]
    same, report = select(items, "any query", text_key="t", cap=400)
    assert same == items
    assert report["retrieved"] is False


def test_retrieval_ranks_by_term_overlap_above_the_cap():
    from res_pipeline.core.retrieval import select

    items = [
        {"t": "reflective writing improves emotional awareness in undergraduates"},
        {"t": "spaced retrieval practice and long-term retention of facts"},
        {"t": "worked examples reduce cognitive load for novice diagnosticians"},
    ]
    chosen, report = select(items, "emotional awareness", text_key="t", cap=1)
    assert report["retrieved"] is True and report["dropped"] == 2
    assert "emotional awareness" in chosen[0]["t"]


def test_deduplication_prefers_the_first_source_and_keeps_the_fuller_record():
    """Crossref often has the DOI where OpenAlex has the abstract; neither should be lost."""
    from res_pipeline.core.literature import Candidate, deduplicate

    a = Candidate(source="openalex", source_id="W1", doi="10.1/x", title="Emotion in STEM")
    b = Candidate(source="crossref", source_id="10.1/X", doi="10.1/X",
                  title="Emotion in STEM", abstract="An abstract.")
    c = Candidate(source="crossref", source_id="z", doi=None,
                  title="emotion  in   stem!!", abstract="Same paper, messy title.")
    kept, stats = deduplicate([a, b, c])
    assert len(kept) == 1 and kept[0].source == "openalex"
    assert kept[0].abstract == "An abstract.", "the abstract must be carried across"
    assert stats["removed_by_doi"] == 1 and stats["removed_by_title"] == 1


# --- the inference layer gained three tests of itself (2026-11-13) ------------------


def test_null_model_preserves_every_marginal_except_co_occurrence():
    """The shuffle must destroy ONLY the hypothesis, or the test proves nothing.

    If it also changed how many concepts a CMOC has, or how often a concept is used, the
    null would be easier to beat and every motif would look significant.
    """
    import random
    from collections import Counter

    from res_pipeline.verification.motif_significance import _shuffled

    rows = [
        {"cmoc_id": "c1", "study_id": "S1", "polarity": "positive",
         "contexts": ["a", "b"], "drivers": ["d1"], "outcomes": ["o1"]},
        {"cmoc_id": "c2", "study_id": "S2", "polarity": "negative",
         "contexts": ["b"], "drivers": ["d1", "d2"], "outcomes": ["o1", "o2"]},
    ]
    out = _shuffled(rows, random.Random(1))
    for before, after in zip(rows, out):
        assert after["study_id"] == before["study_id"]
        assert after["polarity"] == before["polarity"]
        for role in ("contexts", "drivers", "outcomes"):
            assert len(after[role]) == len(before[role]), role
            assert len(set(after[role])) == len(after[role]), "no concept twice in one role"
    for role in ("contexts", "drivers", "outcomes"):
        assert (Counter(c for r in rows for c in r[role])
                == Counter(c for r in out for c in r[role])), role


def test_graph_consistency_separates_defects_from_design_contrasts():
    """A two-arm experiment is evidence, not an error, and must not be counted as one.

    The first version of this check called "same driver, both polarities, one study" a
    defect. All 29 hits were two-arm designs — S004 instructs one group and tells the
    other to use whatever comes naturally — and that contrast is the study's finding.
    """
    from res_pipeline.verification import graph_consistency as gc

    src = gc.__doc__ or ""
    assert "reclassified" in src.lower()
    import inspect

    body = inspect.getsource(gc.check)
    assert '"signals"' in body and '"defects_total"' in body
    assert "same_driver_both_polarities_within_one_study" not in body.split('"checks"')[1].split("}")[0]


def test_theory_comparison_verdict_is_derived_not_typed():
    """The comparison must come from the data. It used to be four hand-typed verdicts."""
    import inspect

    from res_pipeline.verification import theory_comparison as tc

    body = inspect.getsource(tc.compare)
    # the verdict is computed from recovered/expected fractions
    assert "chain_ok" in body and "half(" in body
    # and the two concepts the matcher fix refused are excluded by name, not silently
    assert tc.REFUSED_BY_MATCHER_FIX == {"E03", "E24"}
