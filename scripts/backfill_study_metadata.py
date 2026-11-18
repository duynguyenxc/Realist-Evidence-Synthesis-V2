#!/usr/bin/env python3
"""Give the ingested studies their real titles back.

THE PROBLEM
-----------
`res ingest --source <folder of PDFs>` builds its registry from the filenames, because a
folder of PDFs carries no metadata. The emotion corpus names each file after its DOI, so
every study arrived with `title = "10.1007 s12144 020 00957 0"` and no authors, year or
journal — while the real metadata sat in `studies_metadata.jsonl`, keyed by the same DOI,
a few directories away.

This was invisible until the data-quality check compared each study's title against the
first page of its own PDF and 252 of 572 could not be checked at all: there was no title
to compare. A screening agent reading those records would be deciding eligibility on a
DOI string.

WHAT IT DOES
------------
Matches on DOI — the filename the PDF was saved under is the DOI, so the join is exact
rather than fuzzy — and fills `title`, `authors`, `year` and `journal` where the study
row has none. It does **not** overwrite a title the ingest recovered from the document
itself: a title read out of the PDF is first-hand evidence and a catalogue record is not.

Idempotent. Run it after any ingest from a PDF folder.

USAGE
-----
    export RES_CONFIG_DIR=config-emotion RES_DATA_DIR=data-emotion \
           RES_OUTPUTS_DIR=outputs-emotion POSTGRES_DB=realist_emotion
    python scripts/backfill_study_metadata.py [--dry-run]
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

# A title that is really a DOI: "10.1007 s12144 020 00957 0", or an OpenAlex work id.
_DOI_TITLE = re.compile(r"^\s*(10[.\s]\d{4,}|W\d{6,})", re.IGNORECASE)


def _is_placeholder(title: str | None) -> bool:
    if not title or not title.strip():
        return True
    if _DOI_TITLE.match(title):
        return True
    # No word of three or more letters: not a title in any language we can screen.
    return not re.search(r"[^\W\d_]{3,}", title)


def main() -> int:
    from res_pipeline.core.config import DATA_DIR
    from res_pipeline.core.db import get_connection

    dry = "--dry-run" in sys.argv

    meta_path = DATA_DIR / "studies_metadata.jsonl"
    if not meta_path.exists():
        print(f"No metadata at {meta_path}", file=sys.stderr)
        return 1
    # Keyed on the DOI with every separator removed.
    #
    # `res acquire` saves a PDF as the DOI with "/" replaced by "_", which is lossy for
    # any DOI containing more than one "/" — 10.1027/1618-3169/a000495 comes back as
    # 10.1027_1618-3169_a000495 and cannot be reversed, because nothing says which "_"
    # was a slash. Stripping all separators from both sides sidesteps the question: DOIs
    # are unique enough that 10.1027.1618.3169.a000495 collides with nothing.
    def key(doi: str) -> str:
        return re.sub(r"[^a-z0-9]", "", (doi or "").lower())

    by_doi: dict[str, dict] = {}
    by_source_id: dict[str, dict] = {}
    for ln in meta_path.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        r = json.loads(ln)
        if r.get("doi"):
            by_doi[key(str(r["doi"]))] = r
        # A record with no DOI is saved under its catalogue id (an OpenAlex "W…"),
        # so that is the only handle those 46 files have.
        if r.get("source_id"):
            by_source_id[str(r["source_id"]).strip().lower()] = r

    filled = skipped = unmatched = already = 0
    with get_connection() as c, c.cursor() as k:
        k.execute("select study_id, doi, title, authors, year, journal, pdf_path "
                  "from studies")
        rows = [dict(r) for r in k.fetchall()]

        for row in rows:
            if not _is_placeholder(row["title"]):
                already += 1
                continue
            doi = key(row["doi"] or "")
            if not doi:
                # Recover it from the FILENAME, not from the title.
                #
                # `res acquire` saves each PDF as the DOI with "/" replaced by "_", so
                # the filename is a lossless encoding of the DOI. The title is not: the
                # registry builder turns both "_" and "-" into spaces, which destroys
                # the hyphens that most modern DOI suffixes contain. Reading the title
                # matched 392 of 572; reading the filename is exact.
                stem = Path(row["pdf_path"]).stem if row.get("pdf_path") else ""
                doi = key(stem) if stem.lower().startswith("10.") else ""
            src = by_doi.get(doi)
            if src is None and row.get("pdf_path"):
                src = by_source_id.get(Path(row["pdf_path"]).stem.strip().lower())
            if not src:
                unmatched += 1
                continue
            # `studies.authors` is a JSON column, not text: a bare "Paul, Ling" is
            # rejected as invalid JSON. The corpus already stores a list, so pass it
            # through as JSON and leave the column alone when there is none.
            authors = src.get("authors")
            authors = json.dumps(authors, ensure_ascii=False) if authors else None
            if dry:
                filled += 1
                continue
            k.execute(
                "update studies set title = %s, authors = coalesce(%s, authors), "
                "year = coalesce(%s, year), journal = coalesce(%s, journal), "
                "doi = coalesce(doi, %s) where study_id = %s",
                (src.get("title"), authors, src.get("year"), src.get("journal"),
                 src.get("doi"), row["study_id"]))
            filled += 1

    print(f"{'would fill' if dry else 'filled'}: {filled}")
    print(f"already had a real title: {already}")
    print(f"placeholder with no matching DOI in the corpus: {unmatched}")
    if skipped:
        print(f"skipped: {skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
