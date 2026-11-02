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
