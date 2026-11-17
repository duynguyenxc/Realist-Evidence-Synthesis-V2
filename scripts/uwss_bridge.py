#!/usr/bin/env python3
"""Move records between this pipeline and UWSS, without either one lying to the other.

WHY THIS EXISTS
---------------
The emotion search ran on OpenAlex and Crossref, which is what
`config-emotion/protocol.yaml` records as the whole search. Two things that pair cannot
do are worth having, and UWSS — the scraping system in
`../Universal-Web-Scraping-System-high-level-update-main` — can do both at no cost:

1. **Reach catalogues this pipeline has no adapter for**: Semantic Scholar, PubMed,
   arXiv, DOAJ, OpenAIRE. What those add over OpenAlex + Crossref is a *measurement* of
   how much a two-catalogue search misses, which is the kind of number a methods
   reviewer asks for and this project has so far asserted rather than measured.
2. **Resolve open-access locations through Unpaywall.** M45 found that 694 of the 1,266
   "open access" links yield no file, the largest group being 280 `doi.org` resolvers
   that were never direct PDF locations. Unpaywall publishes the direct location for
   exactly that case. It was listed as the one improvement left unmade; UWSS already
   implements it.

WHAT THIS DOES NOT DO
---------------------
It does not merge UWSS's records into the corpus of record. `--to-uwss` writes a copy
out; `--from-uwss` writes what came back into a **separate** file for inspection.
Nothing here touches `data-emotion/studies_metadata.jsonl`. A search that has been
reported under a registered protocol does not get silently enlarged: adding a catalogue
is a protocol amendment, it changes what the review claims to have searched, and it is
recorded as such or not done.

FIELD MAPPING, AND THE ONE THAT MATTERS
---------------------------------------
UWSS reads `pdf_url`; this pipeline writes `oa_pdf_url`. They are the same thing, and
getting this wrong is how the project previously came to report a DOI landing page as an
obtainable full text (M42). `url` is the landing page and is mapped to `landing_url`,
never to `pdf_url`.

USAGE
-----
    python scripts/uwss_bridge.py --to-uwss      # corpus  -> UWSS import file
    python scripts/uwss_bridge.py --from-uwss    # UWSS export -> a file to inspect
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

UWSS_ROOT = PROJECT_ROOT.parent / "Universal-Web-Scraping-System-high-level-update-main"


def _load(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def to_uwss(data_dir: Path, out: Path) -> int:
    """Write the pool in the field names UWSS's `import-jsonl` reads."""
    recs = _load(data_dir / "studies_metadata.jsonl")
    if not recs:
        print(f"No pool at {data_dir / 'studies_metadata.jsonl'}", file=sys.stderr)
        return 1
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fh:
        for r in recs:
            authors = r.get("authors")
            fh.write(json.dumps({
                "doi": r.get("doi"),
                "title": r.get("title"),
                "abstract": r.get("abstract"),
                "year": r.get("year"),
                "authors": ", ".join(authors) if isinstance(authors, list) else authors,
                "venue": r.get("journal"),
                "source": f"res:{r.get('source', '?')}",
                # `url` is the DOI landing page. It is NOT a pdf_url, and treating it as
                # one is the defect of M42 that made every record look obtainable.
                "landing_url": r.get("url"),
                "source_url": r.get("url"),
                "pdf_url": r.get("oa_pdf_url"),
                "topic": "emotion-regulation",
            }, ensure_ascii=False) + "\n")
    print(f"{len(recs)} records -> {out}")
    return 0


def from_uwss(src: Path, out: Path, data_dir: Path) -> int:
    """Report what UWSS found, against what the corpus already had.

    Writes a separate file. The corpus of record is not touched; see the module
    docstring for why.
    """
    got = _load(src)
    if not got:
        print(f"Nothing at {src} — run the UWSS export first.", file=sys.stderr)
        return 1
    have = _load(data_dir / "studies_metadata.jsonl")
    known_doi = {(r.get("doi") or "").lower() for r in have if r.get("doi")}
    known_title = {(r.get("title") or "").strip().lower() for r in have if r.get("title")}

    new, overlap = [], 0
    for r in got:
        doi = (r.get("doi") or "").lower()
        title = (r.get("title") or "").strip().lower()
        if (doi and doi in known_doi) or (title and title in known_title):
            overlap += 1
        else:
            new.append(r)

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in new) + "\n",
                   encoding="utf-8")
    pct = 100 * len(new) / len(got) if got else 0
    print(f"UWSS returned {len(got)}: {overlap} already in the corpus, "
          f"{len(new)} new ({pct:.0f}%)")
    print(f"the new ones -> {out}  (NOT merged into the corpus; that is a protocol "
          f"amendment, not a file copy)")
    return 0


def main() -> int:
    from res_pipeline.core.config import DATA_DIR

    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--to-uwss", action="store_true")
    g.add_argument("--from-uwss", action="store_true")
    ap.add_argument("--src", type=Path,
                    default=UWSS_ROOT / "data" / "emotion_uwss_export.jsonl")
    args = ap.parse_args()

    if args.to_uwss:
        return to_uwss(DATA_DIR, UWSS_ROOT / "data" / "emotion_corpus_for_uwss.jsonl")
    return from_uwss(args.src, DATA_DIR / "uwss_new_records.jsonl", DATA_DIR)


if __name__ == "__main__":
    raise SystemExit(main())
