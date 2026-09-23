"""Export the run's results from the database to readable files in outputs/exports/.

The pipeline's real output is the PostgreSQL database (the single source of truth).
This script dumps the key tables to CSV so the results can be read without the database
or the web console — open them in Excel. Re-runnable any time after a run.

    python scripts/export_outputs.py

Writes: outputs/exports/{entities,relationships,cmocs,big_concepts}.csv
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from res_pipeline.core.db import get_connection

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "exports"

QUERIES = {
    "entities": """
        SELECT study_id, cmoc_id, entity_type, label, canonical_id,
               verbatim_quote, char_start, char_end, quote_resolved, confidence
        FROM entity_instances ORDER BY study_id, cmoc_id""",
    "relationships": """
        SELECT tr.study_id, tr.cmoc_id, se.label AS subject, se.entity_type AS subject_type,
               tr.predicate, oe.label AS object, oe.entity_type AS object_type, tr.constraint_valid
        FROM typed_relations tr
        JOIN entity_instances se ON se.entity_id = tr.subject_entity_id
        JOIN entity_instances oe ON oe.entity_id = tr.object_entity_id
        ORDER BY tr.study_id""",
    "cmocs": """
        SELECT study_id, cmoc_id, polarity, narrative_statement,
               verifier_support, checker_agrees
        FROM cmocs ORDER BY study_id""",
    "big_concepts": """
        SELECT community_label, realist_role, entity_type, member_count,
               definition, description, member_labels, study_ids
        FROM conceptual_entities ORDER BY member_count DESC""",
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with get_connection() as conn:
        for name, sql in QUERIES.items():
            # NOTE: do not use pandas.read_sql here. get_connection() sets psycopg's
            # row_factory=dict_row, and pandas' DBAPI path turns each dict row into its
            # keys — which silently wrote a CSV whose every row repeated the header.
            with conn.cursor() as cur:
                cur.execute(sql)
                rows = cur.fetchall()          # list[dict], column order preserved
                columns = [d.name for d in cur.description or []]
            df = pd.DataFrame(rows, columns=columns)
            # utf-8-sig so Excel opens the quotes/accents correctly
            df.to_csv(OUT / f"{name}.csv", index=False, encoding="utf-8-sig")
            print(f"  {name}.csv — {len(df)} rows")
    print(f"exported to {OUT}")


if __name__ == "__main__":
    main()
