"""Extraction guidance — the professor's three emphasised mechanisms, kept LIGHT.

The professor repeatedly asks for three things around the Literature Knowledge Graph:

  A. **Seed-guided extraction** — the researcher supplies seed examples of big concepts
     (from the IPT); the extractor uses them as few-shot *naming* references.
  B. **GraphRAG-in-extraction** — the big concepts / frequent concepts ALREADY in the
     LKG are retrieved during extraction so a new study's labels stay consistent with
     earlier studies (e.g. a fresh "novice overload" aligns to the existing "Cognitive
     load overwhelm" instead of spawning a near-duplicate node).
  C. **HITL feedback → few-shot → re-run** — human corrections recorded at any checkpoint
     are stored and replayed to the agent as few-shot examples, so the agent LEARNS from
     the human and its next run reflects the correction.

CRITICAL EMPIRICAL CONSTRAINT: a heavy theory block injected into per-paper extraction was
measured to SUPPRESS CMOC yield and quote-support (a MetaGPT-style dilution). Everything
here is therefore ADDITIVE, BOUNDED, and explicitly NON-RESTRICTIVE — it steers naming and
cross-study consistency, never what a paper is allowed to yield. All of it is gated by
``config/guidance.yaml`` so a cheap 2-3 paper pilot can A/B each mechanism before a full run.
"""

from __future__ import annotations

from functools import lru_cache

from res_pipeline.core.config import CONFIG_DIR
from res_pipeline.core.db import get_connection

_DEFAULTS = {
    "seed_guided": True,       # Gap A — few-shot big-concept seeds from the IPT
    "graphrag_in_loop": True,  # Gap B — retrieve existing LKG concepts for consistency
    "hitl_few_shot": True,     # Gap C — replay stored human corrections as few-shot
    "max_known_concepts": 24,
    "max_feedback_examples": 5,
}


@lru_cache(maxsize=1)
def guidance_config() -> dict:
    """Load config/guidance.yaml, falling back to conservative defaults."""
    import yaml

    path = CONFIG_DIR / "guidance.yaml"
    cfg = dict(_DEFAULTS)
    if path.exists():
        loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        cfg.update({k: v for k, v in loaded.items() if k in cfg})
    return cfg


# ── Gap A: seed-guided (light few-shot from the IPT) ──────────────────────────────
def _seed_names() -> dict[str, list[str]]:
    """A handful of big-concept SEED names per realist role, drawn from the public IPT.

    Deliberately short — these are *examples of the granularity/naming* we want, not a
    checklist to fill. Contamination-safe: the IPT holds only public theory, never gold.
    """
    from res_pipeline.plugins.realist.ipt import load_ipt

    ipt = load_ipt()
    ctx = [lv["level"] for lv in ipt.get("context_levels_to_investigate", [])][:3]
    dims = [d["id"].replace("_", " ") for d in ipt.get("hypothesised_context_dimensions", [])][:3]
    resources = ipt.get("hypothesised_mechanism_resources", [])[:4]
    return {
        "Context": (ctx + dims)[:4],
        "Mechanism_Resource": resources,
    }


def _seed_block() -> str:
    seeds = _seed_names()
    parts = [f"{role}: {', '.join(v)}" for role, v in seeds.items() if v]
    if not parts:
        return ""
    return (
        "SEED EXAMPLES (big-concept naming references from the review's public theory — "
        "examples of the RIGHT granularity, NOT a checklist and NOT a restriction):\n  "
        + "\n  ".join(parts)
    )


# ── Gap B: GraphRAG-in-extraction (retrieve existing LKG concepts) ────────────────
def _known_concepts_block(limit: int) -> str:
    """Retrieve big concepts + frequent labels already in the LKG for naming consistency.

    During a fresh run the graph is empty for study 1 and fills as studies are processed,
    so this genuinely operates in-the-loop: later studies align to concepts the earlier
    studies established. Uses only labels already extracted — no gold, no invention.
    """
    with get_connection() as conn:
        big: list[str] = []
        try:
            big = [r["community_label"] for r in conn.execute(
                "SELECT community_label FROM conceptual_entities "
                "ORDER BY member_count DESC LIMIT %s", (limit,)
            ).fetchall()]
        except Exception:  # noqa: BLE001 — communities not built yet on a first run
            big = []
        rows = conn.execute(
            "SELECT entity_type, label, count(*) n FROM entity_instances "
            "GROUP BY entity_type, label ORDER BY n DESC LIMIT %s", (limit,)
        ).fetchall()
    if not big and not rows:
        return ""
    lines = []
    if big:
        lines.append("Existing big concepts: " + "; ".join(big[:limit]))
    if rows:
        by_type: dict[str, list[str]] = {}
        for r in rows:
            by_type.setdefault(r["entity_type"], []).append(r["label"])
        for t, labs in by_type.items():
            lines.append(f"{t}: {', '.join(labs[:8])}")
    return (
        "KNOWN CONCEPTS ALREADY IN THE KNOWLEDGE GRAPH (reuse an existing name when this "
        "paper expresses the SAME concept, so the graph stays consistent; still add genuinely "
        "new concepts this paper introduces):\n  " + "\n  ".join(lines)
    )


# ── Gap C: HITL feedback → few-shot store ─────────────────────────────────────────
def ensure_feedback_store() -> None:
    """Create the few-shot correction store if it is missing.

    This used to reuse ``hitl_feedback``, which is a different thing: that table records the
    human decisions taken at the four checkpoints and has ``checkpoint``, ``subject_ref`` and
    ``action`` as NOT NULL. Writing a correction into it therefore violated a constraint on
    every call, so the documented "human correction becomes a few-shot example" loop had
    never stored a single row. Corrections now live in ``agent_feedback``, their own table.
    """
    from res_pipeline.core.db import init_schema

    init_schema()


# The agent keys that any part of the pipeline actually reads corrections back under.
# Storing against anything else is a silent no-op: the correction is written, nothing ever
# looks it up, and the loop appears to work while teaching nobody. That happened — two
# corrections were filed under "cmoc_extractor" while the extractor reads "cmoc_extraction",
# and an improvement was reported that the feedback could not have caused.
CONSUMING_AGENT_KEYS = frozenset({"cmoc_extraction"})


def record_feedback(agent_key: str, correct: str, *, wrong: str = "",
                    note: str = "", study_id: str = "", run_id: str = "") -> None:
    """Persist one human correction so it can be replayed as a few-shot example later.

    Raises on an agent key nothing reads, rather than storing a correction that will never
    be delivered.
    """
    if agent_key not in CONSUMING_AGENT_KEYS:
        raise ValueError(
            f"agent_key {agent_key!r} is not read by any agent, so this correction would "
            f"never reach one. Known keys: {sorted(CONSUMING_AGENT_KEYS)}"
        )
    ensure_feedback_store()
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO agent_feedback (agent_key, study_id, wrong, correct, note, run_id) "
            "VALUES (%s,%s,%s,%s,%s,%s)",
            (agent_key, study_id or None, wrong or None, correct, note or None, run_id or None),
        )


def _feedback_block(agent_key: str, limit: int) -> str:
    ensure_feedback_store()
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT wrong, correct, note FROM agent_feedback WHERE agent_key=%s "
            "ORDER BY created_at DESC LIMIT %s", (agent_key, limit)
        ).fetchall()
    if not rows:
        return ""
    ex = []
    for r in rows:
        line = "- "
        if r["wrong"]:
            line += f"AVOID: {r['wrong']} → "
        line += f"DO: {r['correct']}"
        if r["note"]:
            line += f" ({r['note']})"
        ex.append(line)
    return (
        "LEARNED FROM HUMAN REVIEW (apply these corrections from earlier checkpoints):\n  "
        + "\n  ".join(ex)
    )


# ── Composed block for the extractor ──────────────────────────────────────────────
def extraction_guidance_block(agent_key: str = "cmoc_extraction") -> str:
    """Assemble the LIGHT, non-restrictive guidance block for CMOC extraction.

    Returns '' when everything is disabled or nothing is available yet, so the extractor
    prompt is unchanged from its pristine form in that case.
    """
    cfg = guidance_config()
    blocks: list[str] = []
    if cfg.get("seed_guided"):
        blocks.append(_seed_block())
    if cfg.get("graphrag_in_loop"):
        blocks.append(_known_concepts_block(int(cfg.get("max_known_concepts", 24))))
    if cfg.get("hitl_few_shot"):
        blocks.append(_feedback_block(agent_key, int(cfg.get("max_feedback_examples", 5))))
    blocks = [b for b in blocks if b]
    if not blocks:
        return ""
    return (
        "\n\n--- NAMING & CONSISTENCY GUIDANCE (advisory only) ---\n"
        + "\n\n".join(blocks)
        + "\n\nThis guidance affects only HOW you NAME and align concepts for cross-study "
        "consistency. It does NOT limit WHAT you extract: still capture every configuration "
        "this paper evidences, including new and negative/backfiring pathways."
    )
