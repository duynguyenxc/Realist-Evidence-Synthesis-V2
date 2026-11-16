#!/usr/bin/env python3
"""Run the literature search that the active protocol defines — and nothing else.

WHY THIS EXISTS
---------------
`res search` takes queries as command-line arguments. For a ten-query blocked boolean
search that is a 2,000-character shell command, and a shell command is not a research
record: it lives in one terminal's history, it drifts every time somebody retypes it,
and six months later nobody can say whether the search reported in the paper is the
search that was run.

So the queries live in `<CONFIG_DIR>/protocol.yaml` under `search_strategy`, which is a
versioned, reviewable protocol decision, and this script is the only thing that executes
them. Editing the search means editing the protocol. That is the intended order: RAMESES
II item 8 asks a realist review to report its search well enough to repeat, and a search
generated from the protocol is repeatable by construction.

WHAT IT DOES NOT DO
-------------------
It does not screen, decide eligibility, or spend a cent of model credit. The two
catalogues it queries are free (OpenAlex bills $0.001 a search request and anonymous use
shares $0.10/day per network IP, which a run of this size fits inside). Everything it
produces is a CANDIDATE POOL. No record in it has been judged against the protocol's
eligibility criteria by anything, human or model.

ISOLATION
---------
It inherits whatever `RES_CONFIG_DIR`, `RES_DATA_DIR` and `POSTGRES_DB` are set to and
calls `res search`, which refuses to overwrite Richmond's corpus definition and refuses
to write a second review's rows into Richmond's database. It adds one check of its own:
it will not run unless the active protocol actually has a `search_strategy` block, so
that pointing it at `config/` by accident fails loudly instead of searching Richmond's
topic with the emotion review's queries.

USAGE
-----
    export RES_CONFIG_DIR=config-emotion RES_DATA_DIR=data-emotion \\
           RES_OUTPUTS_DIR=outputs-emotion POSTGRES_DB=realist_emotion
    python scripts/run_protocol_search.py --dry-run     # queries issued, no file written
    python scripts/run_protocol_search.py               # writes the corpus definition
    python scripts/run_protocol_search.py --crossref    # the separate cross-check pool
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true",
                    help="Issue the queries and report; write no corpus file.")
    ap.add_argument("--crossref", action="store_true",
                    help="Run the Crossref cross-check queries into their own file "
                         "instead of the OpenAlex corpus of record.")
    ap.add_argument("--limit", type=int, default=None,
                    help="Override the protocol's limit_per_query_per_source.")
    args = ap.parse_args()

    import yaml

    from res_pipeline.core.config import CONFIG_DIR, DATA_DIR

    protocol_path = CONFIG_DIR / "protocol.yaml"
    protocol = yaml.safe_load(protocol_path.read_text(encoding="utf-8"))
    strategy = (protocol or {}).get("search_strategy")
    if not strategy:
        print(f"No `search_strategy` in {protocol_path}.\n"
              f"The search is a protocol decision; write it there first. Refusing to "
              f"invent queries at run time.", file=sys.stderr)
        return 1

    limit = args.limit or strategy.get("limit_per_query_per_source", 200)
    from_year = ((protocol.get("eligibility") or {}).get("timeframe") or {}).get(
        "published_from", 1998)

    if args.crossref:
        queries = list(strategy.get("crossref_crosscheck_queries") or [])
        sources, types = "crossref", ""
        out = DATA_DIR / "crossref_crosscheck.jsonl"
        label = "Crossref cross-check"
    else:
        queries = [q["q"] for q in strategy.get("queries") or []]
        sources = "openalex"
        types = ",".join((strategy.get("databases") or [{}])[0].get("work_types")
                         or ["article", "review"])
        out = None  # the command's default, i.e. <DATA_DIR>/studies_metadata.jsonl
        label = "OpenAlex corpus of record"

    if not queries:
        print(f"{label}: the protocol lists no queries.", file=sys.stderr)
        return 1

    cmd = ["res", "search", *queries,
           "--from-year", str(from_year), "--limit", str(limit), "--sources", sources]
    if types:
        cmd += ["--types", types]
    if out is not None:
        cmd += ["--out", str(out)]
    if args.dry_run:
        cmd.append("--dry-run")

    print(f"{label}: {len(queries)} queries from {protocol_path.relative_to(PROJECT_ROOT)} "
          f"(protocol version {protocol.get('version')!r}), "
          f"limit {limit}, from {from_year}{', DRY RUN' if args.dry_run else ''}\n")
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
