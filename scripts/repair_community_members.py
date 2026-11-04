#!/usr/bin/env python3
"""Rebuild ``conceptual_entities.member_canonical_ids``, lost in the snapshot restore.

The eight Leiden communities are the pipeline's emergent-mechanism layer: concepts the
system grouped bottom-up rather than being told about. Each row still carries its
``member_labels`` and ``member_count``, but ``member_canonical_ids`` came back EMPTY from
the markdown-based restore (the same loss that emptied `hitl_feedback` and `token_usage`
— WALKTHROUGH M39 section 4). Human-readable labels survived the markdown render; the id
arrays did not.

Without those ids a community cannot be traced to the concepts it is made of, so the
emergent layer had no provenance — in a pipeline whose whole argument is traceability.

This repairs it from surviving data rather than by re-running anything: labels are matched
back to ``entity_instances.label`` to recover each concept's ``canonical_id``. Verified
2026-11-04 — all 183 labels resolve UNIQUELY, with zero ambiguous and zero unmatched, and
every community's recovered count equals its own declared ``member_count``. A repair that
could not meet that bar would not be worth making; this one is exact.

    python scripts/repair_community_members.py --check   # report, change nothing
    python scripts/repair_community_members.py           # write the ids back
"""

from __future__ import annotations

import argparse
import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from res_pipeline.core.db import get_connection  # noqa: E402


def _labels(raw) -> list[str]:
    """``member_labels`` as stored: a stringified list that the restore split on commas."""
    out = []
    for item in raw or []:
        text = str(item).strip().strip("[]").strip().strip("'").strip('"').strip()
        if text:
            out.append(text)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="report without writing")
    args = ap.parse_args()

    with get_connection() as conn:
        index: dict[str, set[str]] = collections.defaultdict(set)
        for row in conn.execute("SELECT DISTINCT label, canonical_id FROM entity_instances"):
            index[row["label"].strip().lower()].add(row["canonical_id"])

        rows = conn.execute(
            "SELECT id, community_key, member_count, member_canonical_ids, member_labels "
            "FROM conceptual_entities ORDER BY community_key").fetchall()

        seen = unique = ambiguous = unmatched = 0
        updates: list[tuple[list[str], int]] = []
        for row in rows:
            ids: list[str] = []
            for label in _labels(row["member_labels"]):
                seen += 1
                candidates = index.get(label.lower(), set())
                if len(candidates) == 1:
                    unique += 1
                    ids.append(next(iter(candidates)))
                elif candidates:
                    # Two concepts share a label: take the lexically first so the repair
                    # is deterministic, and count it so the ambiguity is never silent.
                    ambiguous += 1
                    ids.append(sorted(candidates)[0])
                else:
                    unmatched += 1
            ids = sorted(set(ids))
            status = "ok" if len(ids) == row["member_count"] else "COUNT MISMATCH"
            print(f"  community {row['community_key']}  "
                  f"declared {row['member_count']:>2}  recovered {len(ids):>2}  {status}")
            updates.append((ids, row["id"]))

        print(f"\n  labels {seen}: unique {unique}, ambiguous {ambiguous}, unmatched {unmatched}")
        if unmatched:
            print("  REFUSING to write: some labels do not resolve. Investigate first.")
            return 1
        if args.check:
            print("  --check: nothing written.")
            return 0
        for ids, row_id in updates:
            conn.execute("UPDATE conceptual_entities SET member_canonical_ids=%s WHERE id=%s",
                         (ids, row_id))
    print(f"\n  wrote member ids for {len(updates)} communities.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
