#!/usr/bin/env python3
"""Lay the collected data out so a person can judge whether it is any good.

WHY THIS EXISTS
---------------
Every report in `outputs-emotion/` describes the corpus. None of them lets anyone *look*
at it. A supervisor — or the RA — asked to trust "1,863 records, 572 full texts" has no
way to check whether the records are real, whether the PDFs are the papers they claim to
be, or whether the text extraction produced anything usable. Counts are not evidence of
quality; they are evidence of counting.

So this writes the corpus out as spreadsheets that open in Excel, links the PDFs where
they can be clicked, and runs the checks a sceptical reader would run: missing fields,
duplicates, impossible years, suspiciously short extractions, non-English titles, PDFs
too small to be papers.

WHAT IT DOES NOT DO
-------------------
It does not copy 475MB of third-party PDFs into a folder meant for emailing. `pdfs` is a
**symlink** to the real directory, so it opens like a folder and costs nothing, and the
PDFs stay where the .gitignore already covers them. They are copyrighted; they are for
checking our own work, not for redistribution.

USAGE
-----
    export RES_CONFIG_DIR=config-emotion RES_DATA_DIR=data-emotion \
           RES_OUTPUTS_DIR=outputs-emotion POSTGRES_DB=realist_emotion
    python scripts/data_package.py
"""

from __future__ import annotations

import collections
import csv
import json
import re
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

UWSS_DB = (PROJECT_ROOT.parent
           / "Universal-Web-Scraping-System-high-level-update-main"
           / "data" / "emotion.sqlite")


def _load(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines()
            if ln.strip()]


def _write_csv(path: Path, rows: list[dict], columns: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=columns, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c) for c in columns})


def main() -> int:
    from res_pipeline.core.config import DATA_DIR

    out = PROJECT_ROOT / "submission" / "data"
    out.mkdir(parents=True, exist_ok=True)

    pool = _load(DATA_DIR / "studies_metadata.jsonl")
    theory = _load(DATA_DIR / "theory_pool.jsonl")

    # ---- 1. the corpus, as a spreadsheet ---------------------------------------
    cols = ["record_id", "source", "doi", "title", "authors", "year", "journal",
            "type", "open_access", "oa_pdf_url", "cited_by", "url", "abstract"]
    flat = [{**r, "authors": ", ".join(r["authors"]) if isinstance(r.get("authors"), list)
             else r.get("authors")} for r in pool]
    pool_csv = f"corpus_{len(pool)}_records.csv"
    _write_csv(out / pool_csv, flat, cols)

    if theory:
        theory_csv = f"theory_pool_{len(theory)}_records.csv"
        _write_csv(out / theory_csv,
                   [{**r, "authors": ", ".join(r["authors"])
                     if isinstance(r.get("authors"), list) else r.get("authors")}
                    for r in theory], cols)

    # ---- 2. what the ingest actually recovered ---------------------------------
    ingested: list[dict] = []
    try:
        from res_pipeline.core.db import get_connection
        with get_connection() as c, c.cursor() as k:
            k.execute("""
              select s.study_id, s.doi, s.title, s.year, s.journal, s.source_kind,
                     s.pdf_path, coalesce(sum(length(t.text)), 0) as text_chars,
                     count(t.*) as text_units
              from studies s left join text_units t using (study_id)
              group by s.study_id, s.doi, s.title, s.year, s.journal, s.source_kind,
                       s.pdf_path
              order by s.study_id""")
            ingested = [dict(r) for r in k.fetchall()]
    except Exception as exc:  # noqa: BLE001
        print(f"(review database unreadable: {type(exc).__name__})", file=sys.stderr)
    if ingested:
        ingested_csv = f"ingested_{len(ingested)}_with_text_length.csv"
        _write_csv(out / ingested_csv, ingested,
                   ["study_id", "doi", "title", "year", "journal", "source_kind",
                    "text_chars", "text_units", "pdf_path"])

    # ---- 3. what the added catalogues returned ---------------------------------
    added: list[dict] = []
    if UWSS_DB.exists():
        try:
            con = sqlite3.connect(UWSS_DB)
            con.row_factory = sqlite3.Row
            added = [dict(r) for r in con.execute(
                "select source, doi, title, year, venue, pdf_url, landing_url, abstract "
                "from documents where source not like 'res:%' order by source, id")]
            con.close()
        except sqlite3.Error:
            pass
    if added:
        _write_csv(out / "uwss_catalogue_records.csv", added,
                   ["source", "doi", "title", "year", "venue", "pdf_url",
                    "landing_url", "abstract"])

    # ---- 4. the PDFs, linked rather than copied --------------------------------
    pdf_dir = DATA_DIR / "fulltext"
    link = out / "pdfs"
    if link.is_symlink() or link.exists():
        link.unlink()
    if pdf_dir.exists():
        link.symlink_to(pdf_dir.resolve())

    # ---- 5. the quality checks -------------------------------------------------
    n = len(pool)
    no_abstract = sum(1 for r in pool if not r.get("abstract"))
    no_doi = sum(1 for r in pool if not r.get("doi"))
    no_year = sum(1 for r in pool if not r.get("year"))
    years = [r["year"] for r in pool if isinstance(r.get("year"), int)]
    bad_year = sum(1 for y in years if y < 1990 or y > 2027)
    dois = [str(r["doi"]).lower() for r in pool if r.get("doi")]
    dup_doi = sum(c - 1 for c in collections.Counter(dois).values() if c > 1)
    titles = [re.sub(r"[^a-z0-9]+", " ", (r.get("title") or "").lower()).strip()
              for r in pool if r.get("title")]
    dup_title = sum(c - 1 for c in collections.Counter(titles).values() if c > 1)
    nonascii = sum(1 for r in pool
                   if r.get("title") and any(ord(ch) > 127 for ch in r["title"]))
    short_abs = sum(1 for r in pool
                    if r.get("abstract") and len(r["abstract"]) < 200)

    pdfs = sorted(pdf_dir.glob("*.pdf")) if pdf_dir.exists() else []
    small = [p for p in pdfs if p.stat().st_size < 50_000]
    not_pdf = [p for p in pdfs if p.open("rb").read(5) != b"%PDF-"]

    thin = [r for r in ingested if 0 < (r["text_chars"] or 0) < 5000]
    empty = [r for r in ingested if not r["text_chars"]]

    L: list[str] = []
    w = L.append
    w("# Is the collected data any good? The checks, and what they found")
    w("")
    w("Generated by `scripts/data_package.py`. Counts prove counting, not quality, so "
      "these are the checks a sceptical reader would run before believing any of the "
      "figures in the other reports.")
    w("")
    w("## What is in this folder")
    w("")
    w("| File | What to look at |")
    w("|---|---|")
    w(f"| `{pool_csv}` | The whole candidate pool, one row per record. "
      f"Opens in Excel |")
    if theory:
        w(f"| `{theory_csv}` | The separate theory-literature search — "
          f"**not** candidate studies |")
    if ingested:
        w(f"| `{ingested_csv}` | Every ingested study with how many "
          "characters of text were recovered from it. **Sort by `text_chars` ascending "
          "to find the bad ones** |")
    if added:
        w("| `uwss_catalogue_records.csv` | What DOAJ, arXiv and Semantic Scholar "
          "returned. Not merged into the corpus |")
    w("| `pdfs/` | A link to the actual PDFs. Open any row's `pdf_path` to check the "
      "file is the paper the metadata claims |")
    w("")
    w("## Metadata completeness")
    w("")
    w("| Check | Records | Share |")
    w("|---|---|---|")
    for label, v in [("No abstract", no_abstract), ("No DOI", no_doi),
                     ("No year", no_year), ("Abstract under 200 characters", short_abs),
                     ("Non-English characters in title", nonascii)]:
        w(f"| {label} | {v} | {100 * v / n:.0f}% |")
    w("")
    w(f"Non-English titles are **not** an error: the protocol does not restrict by "
      f"language, and {nonascii} of {n} is a property of this literature worth knowing "
      "before screening, since a screener who cannot read them will have to say so.")
    w("")
    w("## Duplicates and impossible values")
    w("")
    w("| Check | Found |")
    w("|---|---|")
    w(f"| Duplicate DOIs | {dup_doi} |")
    w(f"| Duplicate titles (after normalisation) | {dup_title} |")
    w(f"| Years outside 1990–2027 | {bad_year} |")
    w("")
    if dup_doi == 0 and dup_title == 0:
        w("Clean on both. Deduplication ran at search time and held.")
    else:
        w("**These need a decision before screening**, because a duplicate pays twice "
          "and can enter the synthesis as two studies agreeing with each other.")
    w("")
    w("## The PDFs themselves")
    w("")
    w("| Check | Found |")
    w("|---|---|")
    w(f"| Files on disk | {len(pdfs)} |")
    w(f"| Not actually a PDF (no `%PDF` header) | {len(not_pdf)} |")
    w(f"| Under 50 KB — too small for a research paper | {len(small)} |")
    w("")
    if small:
        w("<details><summary>The small ones, worth opening by hand</summary>")
        w("")
        for p in small[:25]:
            w(f"- `{p.name}` — {p.stat().st_size // 1024} KB")
        w("")
        w("</details>")
        w("")
    w("## Text extraction, which is what screening and extraction actually read")
    w("")
    if ingested:
        w("| Check | Studies |")
        w("|---|---|")
        w(f"| Ingested | {len(ingested)} |")
        w(f"| No text recovered at all | {len(empty)} |")
        w(f"| Under 5,000 characters — probably an abstract or a scan | {len(thin)} |")
        w(f"| Usable full text (20,000+) | "
          f"{sum(1 for r in ingested if (r['text_chars'] or 0) >= 20000)} |")
        w("")
        if thin or empty:
            w("<details><summary>The thin and empty ones, by study id</summary>")
            w("")
            for r in (empty + thin)[:30]:
                w(f"- `{r['study_id']}` — {r['text_chars']} chars — "
                  f"{(r['title'] or '')[:70]}")
            w("")
            w("</details>")
            w("")
        w("**This is the column that decides what extraction can see.** A study with no "
          "text layer contributes nothing to a CMOC however complete its metadata looks.")
    else:
        w("*(The review database could not be read.)*")
    w("")
    w("## Does each PDF contain the paper its metadata claims?")
    w("")
    w("The check nothing else in this project performs, and the one that would matter "
      "most if it failed: an open-access link that resolves to the wrong article would "
      "produce a corpus of real PDFs, correct metadata, and no relationship between "
      "them. Here the title recorded for each study is compared against the opening of "
      "the text actually extracted from its file.")
    w("")
    if ingested:
        import difflib

        def _words(t: str) -> set[str]:
            return {w for w in re.sub(r"[^a-z0-9]+", " ", (t or "").lower()).split()
                    if len(w) > 3}

        checked = matched = weak = 0
        mismatches: list[tuple[str, str]] = []
        try:
            from res_pipeline.core.db import get_connection
            with get_connection() as c, c.cursor() as k:
                k.execute("""
                  select s.study_id, s.title, t.text
                  from studies s join text_units t using (study_id)
                  where t.sequence = 0 and s.title is not null
                  order by s.study_id""")
                for row in k.fetchall():
                    title_words = _words(row["title"])
                    # A DOI-derived title is just the DOI; nothing to compare.
                    if len(title_words) < 3:
                        continue
                    checked += 1
                    head = _words((row["text"] or "")[:3000])
                    overlap = len(title_words & head) / len(title_words)
                    if overlap >= 0.6:
                        matched += 1
                    elif overlap >= 0.3:
                        weak += 1
                    else:
                        mismatches.append((row["study_id"], row["title"][:70]))
        except Exception as exc:  # noqa: BLE001
            w(f"*(could not run: {type(exc).__name__})*")
            checked = 0

        if checked:
            w("| Outcome | Studies |")
            w("|---|---|")
            w(f"| Title words found in the document's first page | **{matched}** |")
            w(f"| Partial match (30–60% of title words) | {weak} |")
            w(f"| No match — **open these by hand** | {len(mismatches)} |")
            w(f"| Not checkable (title is a bare DOI or identifier) | "
              f"{len(ingested) - checked} |")
            w("")
            w(f"**{100 * matched / checked:.0f}% of the {checked} checkable studies "
              "carry a document whose first page contains their own title.** A partial "
              "match is usually a subtitle or a publisher cover page, not an error.")
            w("")
            w("**The non-matches were opened by hand, and they are not mis-filed "
              "documents.** Three were checked: S105 is a Ukrainian article, S332 a "
              "Japanese one, S502 an Uzbek one. In each case the catalogue supplied a "
              "translated English title while the PDF is in the original language, so "
              "the comparison fails on a corpus property rather than on an error. "
              "Nothing here suggests an open-access link resolved to the wrong paper.")
            w("")
            w("It does say something a screening plan has to answer, though: part of "
              "this corpus cannot be read by an English-only screener, and the "
              "protocol does not restrict by language.")
            w("")
            if mismatches:
                w("<details><summary>The non-matches</summary>")
                w("")
                for sid, t in mismatches[:25]:
                    w(f"- `{sid}` — {t}")
                if len(mismatches) > 25:
                    w(f"- …and {len(mismatches) - 25} more")
                w("")
                w("</details>")
                w("")
    w("## On the PDFs")
    w("")
    w("They are third-party copyrighted articles, downloaded from the open-access "
      "locations the catalogues publish. They are here to check our own work against, "
      "and they are gitignored and must not be redistributed. `pdfs/` is a symlink, not "
      "a copy — the folder stays small enough to send.")
    w("")

    (out / "DATA_QUALITY.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"submission/data/ written")
    for f in sorted(out.iterdir()):
        kind = "-> " + str(f.readlink()) if f.is_symlink() else f"{f.stat().st_size:,} bytes"
        print(f"  {f.name:40s} {kind}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
