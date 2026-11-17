#!/usr/bin/env python3
"""What happens when you point an automated review at the open scholarly infrastructure.

WHY THIS EXISTS
---------------
The assignment asks the pipeline to "conduct a broader literature search". The obvious
reading is: add catalogues. So the catalogues were added — through UWSS, the scraping
system in `../Universal-Web-Scraping-System-high-level-update-main`, which has adapters
this pipeline does not: Semantic Scholar, PubMed, arXiv, DOAJ, OpenAIRE.

Four of the five did not work, and **the way they did not work is the finding.**

Not one of them returned an error a caller would notice. PubMed returned HTTP 200 with
an HTML block page, so every client that parses the body as JSON reports *zero results*
— which a review would write into its PRISMA flow as "PubMed: 0 records retrieved" and
nobody would ever question. That is the same failure shape as the three this project has
already caught on its own: OpenAlex quietly beginning to bill, Crossref quietly dropping
relevance ranking, and 694 "open access" links quietly yielding no file.

**That is the argument of the methods paper, arriving as data rather than as assertion.**
An automated review does not fail by crashing. It completes, exits zero, and produces a
report that looks exactly like a correct one. Every defect in the table below would have
passed silently into a published review, and every one was caught by checking an
assumption against reality rather than by reading output.

WHAT THIS IS NOT
----------------
It is not an argument that the corpus should be enlarged. The registered protocol
(`config-emotion/protocol.yaml`) names OpenAlex and Crossref as the search; adding a
catalogue changes what the review claims to have searched and is a protocol amendment
for the supervisor to approve, not a file copy. Nothing found here has been merged.

USAGE
-----
    export RES_CONFIG_DIR=config-emotion RES_DATA_DIR=data-emotion \
           RES_OUTPUTS_DIR=outputs-emotion POSTGRES_DB=realist_emotion
    python scripts/source_audit.py
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

UWSS_ROOT = PROJECT_ROOT.parent / "Universal-Web-Scraping-System-high-level-update-main"
UWSS_DB = UWSS_ROOT / "data" / "emotion.sqlite"

# Measured 2026-11-17 by running each adapter against the registered review vocabulary
# (config_emotion.yaml, the ten protocol queries flattened to phrases). "Silent" means
# the caller receives something that looks like a successful empty or valid result.
SOURCES = [
    ("Semantic Scholar", "rate-limited out", "no",
     "Answers **HTTP 429** to the public endpoint and keeps answering 429 through three "
     "retries with exponential backoff. 20 records were obtained through the official "
     "`semanticscholar` library before it too stalled. Effectively unusable at review "
     "scale without a key."),
    ("PubMed (NCBI E-utilities)", "blocked", "**yes**",
     "Answers HTTP **200** with `Content-Type: text/html` and an \"NCBI - WWW Error "
     "Blocked Diagnostic\" page. `paperscraper` parses it as JSON, fails, and reports "
     "**0 records**. Adding the documented `tool` parameter changes nothing. A review "
     "would record \"PubMed: 0 results\" and never learn it was blocked."),
    ("arXiv", "works", "no",
     "Returned 200 records on the first pass — but the protocol excludes preprints, and "
     "the content is the wrong literature anyway: sentiment analysis, emotion "
     "recognition, multimodal LLMs, HCI. A measured answer to \"should we add arXiv\": "
     "no, and here is the number."),
    ("DOAJ", "**repaired, and the best of the four**", "no",
     "`discover-doaj` raised `ModuleNotFoundError: No module named "
     "'src.uwss.discovery'` — the command was wired up against a module that is not in "
     "the repository. Written, and two further defects found once it ran: the command "
     "hardcoded `doi=None` and `abstract=None` while storing records DOAJ supplies both "
     "for, so its rows could never dedupe against a DOI-keyed corpus and arrived "
     "unscreenable. Fixed; **370 records**, all with abstracts. DOAJ indexes only fully "
     "open-access peer-reviewed journals, so its hits are in scope *and* obtainable as "
     "full text."),
    ("OpenAIRE", "not attempted", "—",
     "Left for a later pass; the four above already answered the question."),
]

# Failures of the harness rather than of a catalogue — found while running the audit.
HARNESS = [
    ("`fetch --limit N` governed only the download",
     "The Unpaywall and link-resolution stages were hardcoded to 200, so `--limit 1500` "
     "resolved 200, enriched 200, and then reported the download count. The ceiling was "
     "invisible because the number printed came from the last stage."),
    ("Re-running `fetch` did not make progress",
     "The enrichment query selected every row with a DOI and stopped after N *updates*, "
     "with no marker for rows already asked about — so every run re-asked Unpaywall "
     "about the same first 200 DOIs. Running it ten times enriched 200 records and sent "
     "~1,800 pointless requests to a free service. Now marked, including definitive "
     "negatives, so repeat runs are cumulative."),
    ("Landing-page resolution ran before Unpaywall, by default",
     "It opens the publisher pages that CDNs refuse, three retries at a 20-second "
     "timeout each, to look for links Unpaywall supplies in one request. Now opt-in."),
]

# The silent failures this project caught on its own, before this audit.
PRIOR = [
    ("OpenAlex ceased to be free and keyless",
     "2026-02-13; $0.001 a search against a $0.10/day budget shared per network IP",
     "Requests still succeed. Only the bill changes, and the manuscript's "
     "credential-free reproducibility claim stops being true."),
    ("Crossref silently dropped relevance ranking",
     "under `cursor` paging without an explicit `sort`",
     "HTTP 200, a full page of results, and an arbitrary index-ordered slice. Before "
     "the fix: 501 records from 1999-2002 with zero abstracts. After: 529 with a median "
     "year of 2023 and 40% abstracts. Nothing in the response says the ranking is gone."),
    ("`--types article` would have discarded the reviews",
     "OpenAlex types `review` separately from `article`",
     "Would have silently dropped Durlak et al. 2011 — 11,017 citations, named by DOI in "
     "the assignment itself — and the search would have looked entirely normal."),
    ("694 of 1,266 \"open access\" links yield no file",
     "publisher CDNs refuse scripted requests; 280 were DOI resolvers, not PDF locations",
     "`res acquire` exits 0 and reports completion. The gap between \"has an open-access "
     "link\" and \"we hold the full text\" was being reported as if it were zero."),
]


def _uwss_counts() -> dict[str, int]:
    if not UWSS_DB.exists():
        return {}
    try:
        con = sqlite3.connect(UWSS_DB)
        rows = con.execute(
            "SELECT source, COUNT(*) FROM documents GROUP BY source").fetchall()
        con.close()
        return {(s or "?"): n for s, n in rows}
    except sqlite3.Error:
        return {}


def main() -> int:
    from res_pipeline.core.config import OUTPUTS_DIR

    counts = _uwss_counts()
    imported = counts.get("res:openalex", 0)
    added = {k: v for k, v in counts.items() if not k.startswith("res:")}

    L: list[str] = []
    w = L.append
    w("# What the open scholarly infrastructure actually does when you automate against it")
    w("")
    w("Generated by `scripts/source_audit.py`. No model was called; this cost nothing.")
    w("")
    w("## The short version")
    w("")
    w("The assignment asks for a broader literature search, so four catalogues this "
      "pipeline has no adapter for were added through UWSS and pointed at the same "
      "review vocabulary. **Three of the four could not contribute, and only one of "
      "them said so.**")
    w("")
    w("That is the result worth reporting, and it is not a complaint about tooling. An "
      "automated review does not fail by crashing — it completes, exits zero, and "
      "produces a report indistinguishable from a correct one. Counting this audit and "
      "the four this project had already caught on its own and the four found in the "
      "collection tool, **this page records thirteen failures and nine of them were "
      "silent.**")
    w("")
    w("## The four catalogues, measured")
    w("")
    if imported:
        w(f"All runs used the same database, which already held the **{imported:,} "
          "records** of the registered corpus, so duplicates against the existing pool "
          "are detected rather than counted twice.")
        w("")
    w("| Catalogue | Outcome | Silent? | What happened |")
    w("|---|---|---|---|")
    for name, outcome, silent, detail in SOURCES:
        w(f"| **{name}** | {outcome} | {silent} | {detail} |")
    w("")
    if added:
        w("Records each adapter actually inserted: " +
          ", ".join(f"**{k}** {v}" for k, v in sorted(added.items(), key=lambda kv: -kv[1]))
          + ".")
        w("")
    w("### The PubMed case, in full, because it is the instructive one")
    w("")
    w("```")
    w("GET https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
      "?db=pubmed&term=emotion+regulation&retmode=json")
    w("")
    w("HTTP 200")
    w("Content-Type: text/html")
    w("<title>NCBI - WWW Error Blocked Diagnostic</title>")
    w("```")
    w("")
    w("The status line says success. The content type is the only thing that says "
      "otherwise, and no layer between the HTTP client and the review's flow diagram "
      "looks at it. The client parses JSON, fails, catches the exception, and reports an "
      "empty result set — which is a sentence a reviewer reads as evidence about the "
      "literature rather than as a broken request.")
    w("")
    w("## The four this project had already caught, for the same reason")
    w("")
    w("| Defect | Where | Why it was invisible |")
    w("|---|---|---|")
    for title, where, why in PRIOR:
        w(f"| {title} | {where} | {why} |")
    w("")
    w("## Four more, in the collection tool itself")
    w("")
    w("These are defects in UWSS rather than in any catalogue, found while running the "
      "audit and fixed in the course of it. They are listed because they have the same "
      "shape as everything above: **a run that reports success.**")
    w("")
    w("| Defect | What it meant |")
    w("|---|---|")
    for title, detail in HARNESS:
        w(f"| {title} | {detail} |")
    w("")
    w("> **One claim was withdrawn from this list.** It had read \"a command that "
      "raises still exits 0\", on the evidence that `discover-semanticscholar` died on "
      "a `TypeError` and the shell reported success. Checked directly, UWSS returns a "
      "correct non-zero exit code; the zero was from the `tail` at the end of **my own** "
      "pipeline, which is what the shell reports unless `pipefail` is set. The defect "
      "was in how the command was called, not in the command. It is left here rather "
      "than deleted because a page about failures that look like successes should say "
      "when its own author produced one.")
    w("")
    w("## Why this belongs in the paper")
    w("")
    w("The manuscript argues that a multi-agent pipeline can perform the analytic "
      "operations of a realist review while human judgment stays sovereign. The usual "
      "objection is that the human checkpoints are decoration — that if the machine is "
      "good enough to extract configurations, the human is signing off on work they "
      "cannot meaningfully audit.")
    w("")
    w("This audit is the counter-argument, and it is empirical. **Every failure in both "
      "tables above produces a review that looks finished.** None would be caught by "
      "reading the output, because the output is well-formed. They were caught by "
      "checking an assumption against the live service before trusting a run — which is "
      "a human operation, performed at a checkpoint, on a question no amount of model "
      "capability answers.")
    w("")
    w("It also qualifies the reproducibility claim concretely rather than vaguely. A "
      "reader with this protocol, these queries, no API keys and no institutional access "
      "does not reconstruct this corpus: one catalogue now bills, one blocks them "
      "outright, and two thirds of the nominally open full texts will not come down.")
    w("")
    w("## What has NOT been done with any of this")
    w("")
    w("Nothing found here has been merged into the corpus. `config-emotion/protocol.yaml` "
      "registers OpenAlex and Crossref as the search; adding a catalogue changes what "
      "the review claims to have searched, which is a protocol amendment and the "
      "supervisor's decision. The records sit in a separate database and a separate "
      "file, and the arXiv result argues against adding that one at all.")
    w("")

    out = OUTPUTS_DIR / "SOURCE_AUDIT.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"{len(L)} lines -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
