#!/usr/bin/env python3
"""Generate the search report for the active review from the record, not from memory.

WHY IT IS GENERATED AND NOT WRITTEN
-----------------------------------
On 2026-11-13 this project found that its comparison against Richmond's conclusions had
been twenty-two lines of hand-typed prose in `webui.py`: it read neither the benchmark
nor the system's output, so it could not change when the system changed, and nobody could
check it. Computing it corrected three of five verdicts (WALKTHROUGH M41 section 3).

A search report is the same kind of claim. RAMESES II item 8 asks a realist review to
report how its searching was done — databases, terms, coverage dates, date last searched,
what was retrieved, what was removed as duplicates — and every one of those numbers exists
in `search_log` and in the corpus file. Typing them into a document by hand creates a
second, unverifiable copy that silently goes stale after the next search round. So this
script reads the protocol, the log and the corpus, and writes the report.

WHAT IT DELIBERATELY DOES NOT SAY
---------------------------------
It does not call anything "included". Screening has not been run; `res screen` is the
first stage that spends model credit. Every number below describes a CANDIDATE POOL that
no eligibility criterion has yet been applied to, and the report says so in those words,
because a pool reported as a corpus is how a review ends up claiming it screened
literature it never read.

USAGE
-----
    export RES_CONFIG_DIR=config-emotion RES_DATA_DIR=data-emotion \\
           RES_OUTPUTS_DIR=outputs-emotion POSTGRES_DB=realist_emotion
    python scripts/search_report.py
"""

from __future__ import annotations

import collections
import json
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))


def _title_key(title: str) -> str:
    t = unicodedata.normalize("NFKD", title or "").lower()
    t = re.sub(r"[^a-z0-9 ]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def _load(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _pct(n: int, d: int) -> str:
    return f"{n / d:.0%}" if d else "n/a"


def main() -> int:
    import yaml

    from res_pipeline.core.config import CONFIG_DIR, DATA_DIR, OUTPUTS_DIR
    from res_pipeline.core.db import get_connection

    protocol = yaml.safe_load((CONFIG_DIR / "protocol.yaml").read_text(encoding="utf-8"))
    strategy = (protocol or {}).get("search_strategy") or {}
    if not strategy:
        print(f"No search_strategy in {CONFIG_DIR / 'protocol.yaml'}", file=sys.stderr)
        return 1

    pool = _load(DATA_DIR / "studies_metadata.jsonl")
    cross = _load(DATA_DIR / "crossref_crosscheck.jsonl")
    if not pool:
        print(f"No corpus at {DATA_DIR / 'studies_metadata.jsonl'} — run the search first.",
              file=sys.stderr)
        return 1

    with get_connection() as conn:
        rows = conn.execute(
            "SELECT run_id, source, query, n_returned, n_after_dedup, filters, searched_at "
            "FROM search_log ORDER BY searched_at").fetchall()
    # `get_connection` uses psycopg's dict_row, so a row is already a mapping and jsonb
    # already a dict. Zipping column names over it would zip over its KEYS.
    log = [dict(r) for r in rows]
    for r in log:
        if isinstance(r.get("filters"), str):
            r["filters"] = json.loads(r["filters"])

    def outcome(r: dict) -> str:
        return (r["filters"] or {}).get("outcome") or "unstamped"

    of_record = [r for r in log if outcome(r) in ("written", "partial_written")]
    discarded = [r for r in log if outcome(r) not in ("written", "partial_written")]

    n = len(pool)
    abstracts = sum(1 for r in pool if r.get("abstract"))
    dois = sum(1 for r in pool if r.get("doi"))
    oa_pdf = [r for r in pool if r.get("oa_pdf_url")]
    ready = [r for r in pool if r.get("abstract") and r.get("oa_pdf_url")]
    types = collections.Counter(r.get("type") for r in pool)
    years = sorted(r["year"] for r in pool if r.get("year"))
    by5 = collections.Counter((y // 5) * 5 for y in years)

    pool_dois = {(r.get("doi") or "").lower() for r in pool if r.get("doi")}
    pool_titles = {_title_key(r.get("title")) for r in pool}
    cross_new = [r for r in cross
                 if (r.get("doi") or "").lower() not in pool_dois
                 and _title_key(r.get("title")) not in pool_titles]

    L: list[str] = []
    w = L.append
    w("# Search report — " + str((protocol or {}).get("review_question", "")).strip().split("\n")[0])
    w("")
    # No generation timestamp: the RA asked that these documents not carry one. The dates
    # that are METHOD -- coverage searched, date last searched -- stay, because RAMESES II
    # item 8 requires them and they describe the search, not the file.
    w("Generated by `scripts/search_report.py` from `search_log` and the corpus file. Every "
      "figure here is computed; none is typed. Re-run the script after any further search "
      "round.")
    w("")
    w(f"Protocol: `{CONFIG_DIR.name}/protocol.yaml` version **{(protocol or {}).get('version')}**")
    w("")
    w("## What this is, and what it is not")
    w("")
    w(f"**{n} candidate records.** Not {n} included studies, and not a corpus. No eligibility "
      "criterion in the protocol has been applied to any record in it: screening is the first "
      "stage that calls a model, and it has not been run. Every count below describes a pool "
      "awaiting screening.")
    w("")
    w("The search is **purposive and relevance-ranked, not exhaustive** — the realist "
      "convention (RAMESES II item 8; Pawson, Greenhalgh, Harvey & Walshe 2004). Each query "
      "retrieves its top-ranked results rather than every match, so this is a theory-driven "
      "sample of the literature, and the protocol states that in those words.")
    w("")
    w("## Databases")
    w("")
    w("| Database | Role | Coverage searched | Date last searched | Matched in |")
    w("|---|---|---|---|---|")
    for db in strategy.get("databases") or []:
        matched = strategy.get("field_matched", "-") if db.get("role") == "primary" else "bibliographic"
        w(f"| {db.get('name')} | {db.get('role')} | {db.get('coverage_searched')} "
          f"| {db.get('date_last_searched')} | {matched} |")
    w("")
    w("## Queries of record")
    w("")
    # Two sets of queries wrote two different files. Listing them in one table and calling
    # them all "the queries that produced the pool" would be false for three of them, so
    # they are grouped by the file they actually wrote.
    corpus_file = str((DATA_DIR / "studies_metadata.jsonl").resolve())
    pool_q = [r for r in of_record
              if (r["filters"] or {}).get("written_to", "").endswith("studies_metadata.jsonl")]
    other_q = [r for r in of_record if r not in pool_q]
    w(f"**{len(pool_q)} queries produced the pool** (`{Path(corpus_file).name}`). Each is "
      "logged with its parameters, its result count and the field it was matched in.")
    w("")
    w("| # | Source | Returned | Query |")
    w("|---|---|---|---|")
    for i, r in enumerate(pool_q, 1):
        q = r["query"].replace("|", "\\|")
        q = q if len(q) <= 150 else q[:147] + "…"
        w(f"| {i} | {r['source']} | {r['n_returned']} | `{q}` |")
    w("")
    if other_q:
        by_file = collections.defaultdict(list)
        for r in other_q:
            by_file[Path((r["filters"] or {}).get("written_to") or "?").name].append(r)
        for fname, grp in sorted(by_file.items()):
            w(f"**{len(grp)} further queries wrote a separate file** (`{fname}`) and did NOT "
              "contribute to the pool above:")
            w("")
            w("| # | Source | Returned | Query |")
            w("|---|---|---|---|")
            for i, r in enumerate(grp, 1):
                q = r["query"].replace("|", "\\|")
                w(f"| {i} | {r['source']} | {r['n_returned']} | `{q}` |")
            w("")
    if discarded:
        w(f"**{len(discarded)} further queries are in the log and are NOT part of this report.** "
          "They are stamped with why, so the record can distinguish an abandoned attempt from "
          "the search of record:")
        w("")
        w("| Source | Outcome | Queries |")
        w("|---|---|---|")
        for (src, out), grp in sorted(collections.Counter(
                (r["source"], outcome(r)) for r in discarded).items()):
            w(f"| {src} | `{out}` | {grp} |")
        w("")
    w("## Deduplication")
    w("")
    returned = sum(r["n_returned"] for r in pool_q)
    w(f"- Records returned by the {len(pool_q)} queries that produced the pool: **{returned}**")
    w(f"- Unique records after deduplication by DOI then normalised title: **{n}**")
    w(f"- Removed as duplicates: **{returned - n}**")
    w("")
    w("## What is in the pool")
    w("")
    w("| | n | share |")
    w("|---|---|---|")
    w(f"| Records | {n} | 100% |")
    w(f"| With an abstract (screenable as-is) | {abstracts} | {_pct(abstracts, n)} |")
    w(f"| With a DOI | {dois} | {_pct(dois, n)} |")
    w(f"| With an open-access PDF link (acquirable free) | {len(oa_pdf)} | {_pct(len(oa_pdf), n)} |")
    w(f"| With **both** an abstract and a PDF | {len(ready)} | {_pct(len(ready), n)} |")
    w("")
    w("Work types: " + ", ".join(f"**{k}** {v}" for k, v in types.most_common()) + ".")
    w("")
    w(f"Publication years {years[0]}–{years[-1]}, median {years[len(years) // 2]}. "
      "By five-year band: " + ", ".join(f"{k}–{k + 4}: {v}" for k, v in sorted(by5.items())) + ".")
    w("")
    w("## Validity check")
    w("")
    w("A search that cannot retrieve the references the review was handed is broken. The "
      "protocol states the expected result for each one **before** the search was run, and "
      "distinguishes a reference that must appear from one that should not.")
    w("")
    w("| Reference | Expected | Found | Verdict |")
    w("|---|---|---|---|")
    by_doi = {(r.get("doi") or "").lower(): r for r in pool}
    for doi, name, must in (strategy.get("validity_check_references") or []):
        hit = by_doi.get(doi.lower())
        expected = "must appear" if must else "should not appear"
        found = "yes" if hit else "no"
        ok = "as predicted" if bool(hit) == bool(must) else "**UNEXPECTED**"
        w(f"| {name} | {expected} | {found} | {ok} |")
    w("")
    w("## What a second catalogue adds")
    w("")
    if cross:
        w(f"The Crossref cross-check ran {len([r for r in of_record if r['source'] == 'crossref'])} "
          f"queries and returned **{len(cross)}** unique records, of which **{len(cross) - len(cross_new)}** "
          f"are already in the pool and **{len(cross_new)}** are not "
          f"({sum(1 for r in cross_new if r.get('abstract'))} of those have an abstract).")
        w("")
        w("**This is not a measure of catalogue coverage.** The cross-check used different, "
          "simpler queries, because Crossref supports no boolean syntax and no field "
          "restriction. The figure therefore mixes what Crossref indexes that OpenAlex does "
          "not with what three phrase queries find that ten boolean ones do not, and it must "
          "not be reported as the former.")
    else:
        w("No cross-check pool present.")
    w("")
    w("## Not done, and why")
    w("")
    for item in strategy.get("not_done_and_why") or []:
        w(f"- {str(item).strip()}")
    w("")

    out_path = OUTPUTS_DIR / "SEARCH_REPORT.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"{len(L)} lines -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
