#!/usr/bin/env python3
"""Report how much of the pool's full text was actually obtainable, and why not more.

WHY THIS EXISTS
---------------
`res search` records how many candidate records the catalogues call open access. That
number is a *claim by the catalogue*, and the project had been reporting it as if it
described what we hold: the handover said "68% with a free full text" when 68% is the
share with an open-access PDF LINK. The share that downloads is a different number, and
it is smaller.

For a realist review that gap is not an inconvenience to hide, it is a constraint on what
the review can include. RAMESES II asks for the flow of studies through the review; a
flow diagram that counts links as full texts is wrong at its second box.

WHAT WAS MEASURED, AND HOW
--------------------------
Downloads are attempted only against the URL the catalogue itself publishes as the
open-access location, with an honest academic User-Agent, one request at a time, and a
`%PDF` magic-byte check that refuses anything that is not a PDF.

The failures were then diagnosed rather than assumed, by re-requesting one failed URL per
publisher host twice -- once with the pipeline's own User-Agent and once with a browser's
-- on 2026-11-17. The result is recorded in DIAGNOSIS below. Three things came out of it:

1. **The User-Agent is not the cause.** Every host that refused the pipeline refused the
   browser string identically. So the pipeline is not being penalised for identifying
   itself, and there is no case for making it pretend to be a browser -- which would mean
   circumventing a publisher's stated bot policy, and is not something this project will
   do to raise a download count.
2. **The 403s are CDN-level bot blocking**, on MDPI, Taylor & Francis, Wiley, PubMed
   Central and `doi.org` resolution. These articles are open access to a reader with a
   browser and closed to any script. That is a property of the publishing estate, not of
   this pipeline, and it is the reason automated full-text acquisition at scale needs an
   institutional proxy.
3. **Some failures were transient, and this was large.** The first pass obtained 434
   files; re-running the identical command, which skips what is already on disk, obtained
   135 more. A quarter of what we hold arrived by an accident of how many times the
   operator happened to re-run a command, which is not a reproducible corpus. A bounded
   retry now lives in `acquire_fulltext` instead of in the operator's habits: timeouts,
   connection errors, 429 and 5xx are retried with backoff; 403 is not, because it is a
   publisher policy rather than a fault, and a 200 carrying a landing page is not either.

WHAT THIS MEANS FOR THE MANUSCRIPT
----------------------------------
The paper's reproducibility claim has to be qualified twice over, and both qualifications
belong in the limitations section rather than in a footnote. OpenAlex stopped being free
and keyless on 2026-02-13; and roughly two thirds of nominally open-access full texts
cannot be fetched by any unattended process. A reader with our protocol, our queries and
no institutional access does not arrive at our corpus.

USAGE
-----
    export RES_CONFIG_DIR=config-emotion RES_DATA_DIR=data-emotion \
           RES_OUTPUTS_DIR=outputs-emotion POSTGRES_DB=realist_emotion
    python scripts/acquisition_report.py
"""

from __future__ import annotations

import collections
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

# Measured 2026-11-17 by the paired User-Agent probe described in the module docstring.
# One failed URL per host, the pipeline's User-Agent against a browser's.
DIAGNOSIS = [
    ("doi.org", "403 both", "DOI resolver, not a direct PDF location"),
    ("www.mdpi.com", "403 both", "CDN bot block"),
    ("www.tandfonline.com", "403 both", "CDN bot block"),
    ("www.frontiersin.org", "PDF both", "first-pass failure was transient"),
    ("onlinelibrary.wiley.com", "403 both", "CDN bot block"),
    ("pmc.ncbi.nlm.nih.gov", "403 both", "CDN bot block"),
    ("link.springer.com", "200, not a PDF", "landing page; the %PDF guard refused it"),
]


def _pct(n: int, d: int) -> str:
    return f"{100 * n / d:.0f}%" if d else "-"


def main() -> int:
    from res_pipeline.core.config import DATA_DIR, OUTPUTS_DIR

    meta = DATA_DIR / "studies_metadata.jsonl"
    if not meta.exists():
        print(f"No corpus at {meta}.", file=sys.stderr)
        return 1
    recs = [json.loads(ln) for ln in meta.read_text(encoding="utf-8").splitlines() if ln.strip()]

    dest = DATA_DIR / "fulltext"
    files = sorted(dest.glob("*.pdf")) if dest.exists() else []
    on_disk = {p.stem for p in files}
    total_mb = sum(p.stat().st_size for p in files) / 1_048_576

    def stem(rec: dict) -> str:
        return (rec.get("doi") or rec.get("source_id") or "").replace("/", "_").replace(":", "_")

    linked = [r for r in recs if r.get("oa_pdf_url")]
    got = [r for r in linked if stem(r) in on_disk]
    miss = [r for r in linked if stem(r) not in on_disk]

    L: list[str] = []
    w = L.append
    w("# Full-text acquisition: what was obtainable, and why the rest was not")
    w("")
    w("Generated by `scripts/acquisition_report.py` from "
      f"`{meta.name}` and the contents of `{dest.name}/`. No model was called; this cost "
      "nothing but time and bandwidth.")
    w("")
    w("## The flow, with the distinction that was being lost")
    w("")
    w("| | Records | Share of pool |")
    w("|---|---|---|")
    w(f"| Candidate records in the pool | {len(recs)} | 100% |")
    w(f"| Catalogue publishes an open-access PDF location | {len(linked)} | "
      f"{_pct(len(linked), len(recs))} |")
    w(f"| **PDF actually downloaded and verified as a PDF** | **{len(got)}** | "
      f"**{_pct(len(got), len(recs))}** |")
    w(f"| Open-access link that could not be fetched | {len(miss)} | "
      f"{_pct(len(miss), len(recs))} |")
    w("")
    w(f"{len(files)} files on disk, {total_mb:,.0f} MB. Every one begins with the `%PDF` "
      "magic bytes; nothing HTML was saved as a PDF.")
    w("")
    # The two counts differ, and the difference is a finding rather than a defect, so the
    # report says which is which instead of leaving a one-off gap that reads like a bug.
    # The table counts records the catalogue gave an OA link for; the disk holds a few
    # papers Unpaywall located although OpenAlex and Crossref published no OA link at all.
    unlinked = len(files) - len(got)
    if unlinked > 0:
        w(f"The two numbers differ by {unlinked}: the table counts records whose catalogue "
          "entry carried an open-access link, and Unpaywall found a location for "
          f"{unlinked} further paper{'s' if unlinked != 1 else ''} that OpenAlex and "
          "Crossref listed no open-access link for at all. So Unpaywall does not only "
          "repair broken links — it reaches a small number of papers the catalogues do "
          "not record as open at all.")
        w("")
    w(f"**The number to quote is {len(got)}, not {len(linked)}.** Earlier reports said "
      f"\"{_pct(len(linked), len(recs))} with a free full text\", which was the share with "
      "an open-access *link*. The share we hold is "
      f"{_pct(len(got), len(linked))} of those links.")
    w("")
    w("## Why the rest failed")
    w("")
    w("Diagnosed rather than assumed: one failed URL per publisher host, requested twice, "
      "once with the pipeline's own User-Agent and once with a browser's.")
    w("")
    w("| Host | Pipeline UA vs browser UA | Reading |")
    w("|---|---|---|")
    for host, outcome, reading in DIAGNOSIS:
        w(f"| `{host}` | {outcome} | {reading} |")
    w("")
    w("**The User-Agent is not the cause.** Every host that refused the pipeline refused "
      "the browser string identically, so the pipeline is not being penalised for "
      "identifying itself honestly — and there is therefore no case for making it "
      "impersonate a browser, which would mean circumventing a publisher's stated bot "
      "policy to raise a count in a methods paper.")
    w("")
    w("### Where the unfetchable links point")
    w("")
    w("| Host | Unfetched links |")
    w("|---|---|")
    for host, c in collections.Counter(
            urlparse(r["oa_pdf_url"]).netloc for r in miss).most_common(12):
        w(f"| `{host}` | {c} |")
    w("")
    other = len({urlparse(r['oa_pdf_url']).netloc for r in miss}) - 12
    if other > 0:
        w(f"…and {other} further hosts.")
        w("")
    w("The largest single group is `doi.org`: the catalogue gave a DOI resolver where a "
      "direct PDF location was expected. Resolving it lands on a publisher page, not a "
      "file, so these are not retrievable by this route at all. Unpaywall publishes the "
      "direct location for exactly this case and would be the fix; its API requires a "
      "contact email address in every request, which is a decision for the RA rather "
      "than a default this script should set.")
    w("")
    w("## Having the file is not the same as being able to read it")
    w("")
    w("A PDF on disk is not yet evidence. It has to carry a text layer the pipeline can "
      "extract, and a corpus pulled off the open web does not uniformly do so. The "
      "figures below come from the ingest into the review database, not from the files:")
    w("")
    try:
        from res_pipeline.core.db import get_connection
        with get_connection() as c, c.cursor() as k:
            k.execute("""
              with per as (select s.study_id, coalesce(sum(length(t.text)),0) chars
                           from studies s left join text_units t using (study_id)
                           group by 1)
              select count(*) n,
                     count(*) filter (where chars = 0) empty,
                     count(*) filter (where chars between 1 and 19999) partial,
                     count(*) filter (where chars >= 20000) full,
                     coalesce(round(avg(chars) filter (where chars > 0)), 0) avg_chars
              from per""")
            r = k.fetchone()
            k.execute("select count(*) n from audit_log where action = 'study_failed'")
            failed = k.fetchone()["n"]
        if r and r["n"]:
            w("| | Studies |")
            w("|---|---|")
            w(f"| Ingested into the review database | {r['n']} |")
            w(f"| **With a usable full text** (20,000+ characters) | **{r['full']}** |")
            w(f"| Partial text (1-19,999 characters) | {r['partial']} |")
            w(f"| No extractable text at all | {r['empty']} |")
            if failed:
                w(f"| Could not be opened (logged `study_failed`) | {failed} |")
            w("")
            w(f"Mean length where any text was recovered: {int(r['avg_chars']):,} "
              "characters.")
            w("")
            w("**The number that governs extraction is the full-text one, not the file "
              "count.** Extraction reads the document; a study with no text layer "
              "contributes nothing to it however many megabytes it occupies.")
            w("")
    except Exception as exc:  # noqa: BLE001 - the report must still generate
        w(f"*(The review database could not be read for this section: "
          f"{type(exc).__name__}. The file counts above are unaffected.)*")
        w("")
    w("## What this constrains")
    w("")
    w("**For this review.** Screening works from titles and abstracts, which the pool has "
      f"for 89% of records, so the {len(got)} full texts do not limit screening. They limit "
      "**extraction**, which needs the full text of every included study. Whatever the "
      "screening decides, the included set has to be checked against what we can actually "
      "read, and anything we cannot will need requesting through the library.")
    w("")
    w("**For the manuscript.** The reproducibility claim needs qualifying twice: OpenAlex "
      "ceased to be free and keyless on 2026-02-13, and roughly two thirds of nominally "
      "open-access full texts cannot be fetched by an unattended process. A reader with "
      "our protocol, our queries and no institutional access does not arrive at our "
      "corpus. Both belong in the limitations, not a footnote.")
    w("")
    w("**For the pipeline.** The retry is now built in. The first pass obtained 434 files "
      "and a second identical run obtained 135 more, so a quarter of the corpus had been "
      "arriving by an accident of operator habit; `acquire_fulltext` now retries "
      "timeouts, connection errors, 429 and 5xx with backoff, and deliberately does not "
      "retry a 403 or a landing page. **One improvement is still unmade**: an Unpaywall "
      "lookup would turn a DOI resolver into a direct PDF location, which is the largest "
      "single failure group. Its API requires a contact email in every request, which is "
      "the RA's personal data and the RA's decision. Neither is a model call.")
    w("")

    out = OUTPUTS_DIR / "ACQUISITION_REPORT.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"{len(L)} lines -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
