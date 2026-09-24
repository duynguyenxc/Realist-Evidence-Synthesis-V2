"""Fill the numbers in docs/FOR_THE_PROFESSOR.md from the live database and the newest run.

The document answers five questions the professor asked; the prose is written by hand, but every
figure in it is a placeholder that this script replaces from the database and the most recent
verification run. Hand-typed numbers in a document that is emailed onward is exactly how a project
ends up quoting a figure it can no longer reproduce.

    python scripts/fill_professor_answers.py

Idempotent: it rewrites the same placeholders each time, so run it after every pipeline run.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from res_pipeline.core.db import get_connection  # noqa: E402

# The template carries the prose and the placeholder tokens; the rendered file is generated
# and must never be edited by hand. Keeping the two separate is what makes this idempotent —
# rendering twice from the template gives the same result, whereas substituting in place only
# ever works the first time.
TEMPLATE = ROOT / "docs" / "FOR_THE_PROFESSOR.template.md"
DOC = ROOT / "docs" / "FOR_THE_PROFESSOR.md"


def _latest_verification() -> tuple[str, dict]:
    runs = sorted((ROOT / "outputs" / "runs").glob("verify-*/verification_report.json"),
                  key=lambda p: p.stat().st_mtime)
    if not runs:
        raise SystemExit("no verification run found — run `res verify` first")
    return runs[-1].parent.name, json.loads(runs[-1].read_text(encoding="utf-8"))


def _pct(block: dict | None, fallback: float | None = None) -> str:
    if block and block.get("proportion") is not None:
        return f"{block['proportion']:.1%} (95% CI {block['ci_low']:.1%}–{block['ci_high']:.1%})"
    return f"{fallback:.1%}" if fallback is not None else "—"


def main() -> None:
    run_id, v = _latest_verification()
    ent, rel = v["entity_coverage"], v["relation_coverage"]
    fai, com, the = v["citation_faithfulness"], v["community_alignment"], v["theory_correspondence"]

    with get_connection() as conn:
        counts = {
            row["label"]: row["n"] for row in conn.execute("""
                SELECT 'cmocs' AS label, count(*) AS n FROM cmocs
                UNION ALL SELECT 'entities', count(*) FROM entity_instances
                UNION ALL SELECT 'relations', count(*) FROM typed_relations
                UNION ALL SELECT 'communities', count(*) FROM conceptual_entities
            """).fetchall()
        }
        untyped = conn.execute(
            "SELECT count(*) AS n FROM typed_relations WHERE predicate = 'UNTYPED_CANDIDATE'"
        ).fetchone()["n"]

    gap = abs(the.get("self_preference_gap", 0))
    subs = {
        "RUN_ID_PLACEHOLDER": run_id,
        "N_CMOCS": f"{counts['cmocs']:,}",
        "N_ENTITIES": f"{counts['entities']:,}",
        "N_RELATIONS": f"{counts['relations']:,}",
        "N_COMMUNITIES": f"{counts['communities']:,}",
        "N_UNTYPED": f"{untyped}",
        "PCT_VERBATIM": _pct(fai.get("strict_plus_normalized_ci"), fai.get("strict_plus_normalized")),
        "N_CONCEPTS": f"{ent.get('matched_within_type', 0)}",
        "N_ANCHORED": f"{rel.get('anchored_recovered', 0)}",
        "N_STRICT": f"{rel.get('recovered', 0)}",
        "N_MECH": f"{com.get('aligned', 0)}/{com.get('gold_mechanisms', 0)}",
        "JUDGE_GAP": f"{gap:.2f}",
    }

    text = TEMPLATE.read_text(encoding="utf-8")
    for token, value in subs.items():
        text = text.replace(token, value)
    leftover = sorted(set(re.findall(r"(?:N_[A-Z_]+|PCT_[A-Z_]+|RUN_ID_PLACEHOLDER)", text)))
    if leftover:
        raise SystemExit(f"unfilled placeholders in the template: {leftover}")
    header = (
        "<!-- GENERATED from FOR_THE_PROFESSOR.template.md by "
        "scripts/fill_professor_answers.py.\n"
        "     Edit the template, never this file. -->\n\n"
    )
    DOC.write_text(header + text, encoding="utf-8")

    print(f"filled {DOC.relative_to(ROOT)} from {run_id}")
    for k, val in subs.items():
        print(f"  {k:20s} -> {val}")


if __name__ == "__main__":
    main()
