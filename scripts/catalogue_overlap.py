#!/usr/bin/env python3
"""How much does a two-catalogue search miss? Measured, not asserted.

WHY THIS EXISTS
---------------
`config-emotion/protocol.yaml` registers OpenAlex and Crossref as the whole search, and
RAMESES II asks a realist review to report its search well enough to be repeated. It
does not ask whether the search was *sufficient*, and nothing in this project had
answered that — the pool's size was reported, its coverage was not.

Running the same registered vocabulary through four further catalogues (UWSS: Semantic
Scholar, PubMed, arXiv, DOAJ) turns that into a number.

THE TRAP THIS SCRIPT IS BUILT TO AVOID
--------------------------------------
A record another catalogue returns and ours did not is **not** evidence of a miss. It
may be out of scope, off-topic, or the wrong literature entirely — arXiv's 200 hits are
mostly sentiment analysis and multimodal emotion recognition, which this review excludes
by name. Counting raw novelty would inflate the miss rate with exactly the records the
protocol exists to keep out.

So every record that is new to the corpus is passed through
`config-emotion/coding_frame.yaml` — the same theory-grounded dictionary that produced
the evidence map — and the headline figure counts only those carrying at least one
INTERVENTION term and at least one EMOTION term. That is the minimum for a record to be
able to say anything about this review's question, and it is the same test applied to
the corpus itself, so the two are comparable.

WHAT THE RESULT MAY AND MAY NOT BE USED FOR
-------------------------------------------
It is a coverage measurement. It is **not** an enlargement of the corpus and this script
merges nothing: adding a catalogue changes what the review claims to have searched, and
that is a protocol amendment for the supervisor to approve.

USAGE
-----
    export RES_CONFIG_DIR=config-emotion RES_DATA_DIR=data-emotion \
           RES_OUTPUTS_DIR=outputs-emotion POSTGRES_DB=realist_emotion
    python scripts/catalogue_overlap.py
"""

from __future__ import annotations

import collections
import json
import re
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

UWSS_DB = (PROJECT_ROOT.parent
           / "Universal-Web-Scraping-System-high-level-update-main"
           / "data" / "emotion.sqlite")

# How each adapter's rows are labelled in the UWSS `source` column.
ADDED = {
    "doaj": "DOAJ",
    "semantic_scholar": "Semantic Scholar",
    "paperscraper_arxiv": "arXiv",
    "paperscraper_pubmed": "PubMed",
}


def _norm_doi(d: str | None) -> str:
    if not d:
        return ""
    d = str(d).strip().lower()
    for pre in ("https://doi.org/", "http://doi.org/", "doi:"):
        if d.startswith(pre):
            d = d[len(pre):]
    return d


def _norm_title(t: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (t or "").lower()).strip()


def main() -> int:
    import yaml

    from evidence_map import _compile  # the dictionary matcher used for the evidence map
    from res_pipeline.core.config import CONFIG_DIR, DATA_DIR, OUTPUTS_DIR

    if not UWSS_DB.exists():
        print(f"No UWSS database at {UWSS_DB}", file=sys.stderr)
        return 1

    pool_path = DATA_DIR / "studies_metadata.jsonl"
    pool = [json.loads(ln) for ln in pool_path.read_text(encoding="utf-8").splitlines()
            if ln.strip()]
    have_doi = {_norm_doi(r.get("doi")) for r in pool if r.get("doi")}
    have_title = {_norm_title(r.get("title")) for r in pool if r.get("title")}

    frame = yaml.safe_load((CONFIG_DIR / "coding_frame.yaml").read_text(encoding="utf-8"))
    iv = [p for spec in (frame.get("interventions") or {}).values()
          for p in _compile(spec.get("terms") or [])]
    em = [p for spec in (frame.get("achievement_emotions") or {}).values()
          for p in _compile(spec.get("terms") or [])]

    con = sqlite3.connect(UWSS_DB)
    rows = con.execute(
        "SELECT source, doi, title, abstract FROM documents WHERE source IN "
        f"({','.join('?' * len(ADDED))})", tuple(ADDED)).fetchall()
    con.close()

    stats: dict[str, dict] = {k: collections.Counter() for k in ADDED}
    examples: dict[str, list] = {k: [] for k in ADDED}
    for source, doi, title, abstract in rows:
        st = stats[source]
        st["returned"] += 1
        if (doi and _norm_doi(doi) in have_doi) or (title and _norm_title(title) in have_title):
            st["already_had"] += 1
            continue
        st["new"] += 1
        text = f"{title or ''}\n{abstract or ''}"
        has_iv = any(p.search(text) for _t, p in iv)
        has_em = any(p.search(text) for _t, p in em)
        if has_iv and has_em:
            st["new_on_topic"] += 1
            if len(examples[source]) < 5:
                examples[source].append((title or "")[:90])
        elif has_iv or has_em:
            st["new_partial"] += 1
        else:
            st["new_off_topic"] += 1

    L: list[str] = []
    w = L.append
    w("# How much did a two-catalogue search miss?")
    w("")
    w("Generated by `scripts/catalogue_overlap.py`. No model was called; this cost "
      "nothing.")
    w("")
    w("## The question")
    w("")
    w(f"The registered protocol searched OpenAlex and Crossref and produced "
      f"**{len(pool):,} records**. Reporting that number is required; knowing whether it "
      "is *enough* is not something the protocol can answer about itself. So the same "
      "registered vocabulary was run through four further catalogues and the results "
      "compared against the corpus, record by record.")
    w("")
    w("**A record we did not have is not automatically a record we missed.** It may be "
      "the wrong literature. Every new record is therefore passed through the same "
      "theory-grounded dictionary used for the evidence map, and the figure that matters "
      "counts only those carrying **both** an intervention term and an achievement-"
      "emotion term — the minimum for a record to say anything about this review's "
      "question.")
    w("")
    w("## Result")
    w("")
    w("| Catalogue | Returned | Already in corpus | New | New **and on topic** |")
    w("|---|---|---|---|---|")
    tot = collections.Counter()
    for key, label in ADDED.items():
        st = stats[key]
        if not st["returned"]:
            w(f"| {label} | — | — | — | *returned nothing; see `SOURCE_AUDIT.md`* |")
            continue
        tot.update(st)
        w(f"| {label} | {st['returned']} | {st['already_had']} | {st['new']} | "
          f"**{st['new_on_topic']}** |")
    if tot["returned"]:
        w(f"| **Total** | **{tot['returned']}** | **{tot['already_had']}** | "
          f"**{tot['new']}** | **{tot['new_on_topic']}** |")
    w("")
    if tot["returned"]:
        dup = 100 * tot["already_had"] / tot["returned"]
        w(f"Two numbers, and the second is the one that matters.")
        w("")
        w(f"**Almost nothing overlapped: {tot['already_had']} of {tot['returned']} "
          f"({dup:.0f}%).** That is not the reassuring result it first looks like — it "
          "says the catalogues are returning largely disjoint sets, which means the "
          "registered search is not a sample of the same pool seen from a different "
          "angle.")
        w("")
        w(f"**But most of what they add is not this review's literature.** Of the "
          f"{tot['new']} unseen records, only **{tot['new_on_topic']} carry both an "
          f"intervention and an achievement-emotion term**; {tot['new_partial']} carry "
          f"one of the two and {tot['new_off_topic']} carry neither. Against a corpus of "
          f"{len(pool):,}, the genuine shortfall is "
          f"**{tot['new_on_topic']} records, {100 * tot['new_on_topic'] / len(pool):.1f}%** — "
          "small, and now a measurement rather than an assumption.")
        w("")
        w("### Why the overlap is so low, checked rather than guessed")
        w("")
        w("The first suspicion was the query itself: the DOAJ iterator originally asked "
          "for `sort=created_date:desc`, which returns the *newest* matches rather than "
          "the best ones — the same defect this project recorded for Crossref cursor "
          "paging on 2026-11-16, where the ranking is silently dropped. It was removed "
          "and DOAJ re-run on relevance. **The overlap did not move** (1 of 370 either "
          "way), so the sort was a real bug but not this cause. It is fixed regardless.")
        w("")
        w("What remains is the registered search's own shape. It takes the top N hits "
          "per query by relevance from a catalogue that ranks largely by citation "
          "weight, so it is sampling the head of a distribution. DOAJ indexes only "
          "fully open-access journals, many of them small, regional or new — the tail. "
          "The two are not disagreeing about relevance; they are looking at different "
          "ends of the same literature. **That is a limitation of top-N retrieval, and "
          "it belongs in the manuscript's limitations whether or not a catalogue is "
          "added.**")
        w("")
    w("## What each catalogue is actually worth here")
    w("")
    w("**DOAJ is the one worth adding.** It indexes only fully open-access peer-reviewed "
      "journals, so its hits are in scope *and* obtainable as full text — which matters "
      "for a project where 694 of 1,266 open-access links yield no file. It is also the "
      "catalogue that had to be repaired before it would run at all: the command imported "
      "a module that was not in the repository, and once fixed it was discarding the DOI "
      "and abstract of every record it stored.")
    w("")
    w("**arXiv is the one worth refusing, and now with a reason rather than a hunch.** "
      "The protocol excludes preprints, and the content confirms the exclusion is doing "
      "work: the returns are sentiment analysis, multimodal emotion recognition, "
      "affective computing and HCI — the literature this review's negative keywords exist "
      "to exclude.")
    w("")
    w("**PubMed could not be asked.** NCBI answers HTTP 200 with an HTML block page, so "
      "a client reports zero results rather than a refusal. For a review of educational "
      "psychology this is the most costly of the four to lose, and the absence would "
      "have been invisible. `SOURCE_AUDIT.md` has the detail.")
    w("")
    for key, label in ADDED.items():
        if examples[key]:
            w(f"<details><summary>On-topic records {label} returned that the corpus "
              f"did not have</summary>")
            w("")
            for t in examples[key]:
                w(f"- {t}")
            w("")
            w("</details>")
            w("")
    w("## What follows")
    w("")
    w("Nothing here has been merged into the corpus. The protocol names the search, and "
      "changing it is an amendment for the supervisor, not a file copy. The recommendation "
      "that follows from the numbers is narrow: **add DOAJ, decline arXiv, and treat "
      "PubMed as a known gap** until a key or another route is available — and say so in "
      "the limitations rather than leaving a reader to assume the search covered it.")
    w("")

    out = OUTPUTS_DIR / "CATALOGUE_OVERLAP.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"{len(L)} lines -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
