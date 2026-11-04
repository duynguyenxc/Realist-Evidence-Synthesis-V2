#!/usr/bin/env python3
"""Dump every table in the database, exactly as stored, to JSON and CSV.

WHY THIS EXISTS, AND WHAT IT IS NOT
-----------------------------------
Everything the RA and the professor have seen so far has been *written about* the run:
`outputs/RESULTS.html`, `docs/MACHINE_VS_HUMAN.md`, the report package, and every summary
produced in conversation. All of those involve a choice of what to show. The RA asked, on
2026-11-04, for the thing underneath:

    "tôi muốn xem cái raw mà hệ thống thu được ... chứ ko phải cái thứ mà đã bị bạn xào
     nấu lại và nhìn đẹp tươm tất rồi"

So this script interprets nothing. It selects every row of every table and writes it out.
No filtering, no ranking, no prose, no derived figures. If a column is empty in the
database it is empty here; if a count looks wrong it is wrong in the database too. That is
the point — it is the evidence against which every claim in the documents can be checked.

THIS IS NOT `res export-results`, WHICH MUST NEVER BE RUN (see CLAUDE.md and WALKTHROUGH
M39 §4). That command REGENERATES outputs/RESULTS.html, which is irreplaceable because
`hitl_feedback` is empty and a re-export would silently report 0 human decisions over the
only surviving record of 28. This script only READS the database and only WRITES into a
new directory, so it cannot destroy anything.

    python scripts/export_raw.py              # -> outputs/raw_export/
    python scripts/export_raw.py --out DIR    # anywhere else
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from res_pipeline.core.config import OUTPUTS_DIR  # noqa: E402
from res_pipeline.core.db import get_connection  # noqa: E402


def _plain(value):
    """JSON-safe, without changing what the value says."""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (bytes, memoryview)):
        return f"<{len(bytes(value))} bytes>"
    return value


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(OUTPUTS_DIR / "raw_export"),
                    help="directory to write into (created if absent)")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    with get_connection() as c:
        tables = [r["table_name"] for r in c.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema='public' AND table_type='BASE TABLE' "
            "ORDER BY table_name").fetchall()]

        manifest = {"exported_at": datetime.now().isoformat(timespec="seconds"),
                    "database": c.info.dbname, "tables": []}

        for t in tables:
            cols = [r["column_name"] for r in c.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name=%s ORDER BY ordinal_position", (t,)).fetchall()]
            rows = [{k: _plain(v) for k, v in dict(r).items()}
                    for r in c.execute(f'SELECT * FROM "{t}"').fetchall()]

            (out / f"{t}.json").write_text(
                json.dumps(rows, indent=1, ensure_ascii=False, default=str), encoding="utf-8")

            with (out / f"{t}.csv").open("w", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
                w.writeheader()
                for r in rows:
                    w.writerow({k: ("" if v is None else
                                    json.dumps(v, ensure_ascii=False)
                                    if isinstance(v, (list, dict)) else v)
                                for k, v in r.items()})

            manifest["tables"].append({"table": t, "rows": len(rows), "columns": cols})
            print(f"  {t:28} {len(rows):>6} rows")

    (out / "_manifest.json").write_text(
        json.dumps(manifest, indent=1, ensure_ascii=False), encoding="utf-8")

    total = sum(t["rows"] for t in manifest["tables"])
    print(f"\n{len(manifest['tables'])} tables, {total} rows -> {out}")
    print("Nothing here is summarised or ranked. It is the database as it stands.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
