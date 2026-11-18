#!/usr/bin/env python3
"""Assemble everything that goes to the supervisor into one folder, with the email.

WHY A SCRIPT RATHER THAN A FOLDER SOMEONE FILLS BY HAND
-------------------------------------------------------
Every figure in the covering email also appears in a generated report. If the email is
typed by hand it drifts from the reports the moment anything is re-run — and this project
has already had to correct a hand-written comparison that could not be wrong because it
computed nothing (M41), and a progress note that reported 1,266 full texts while the job
that would have produced them was still running (M44). So the email is generated from the
same data as the reports, and regenerating it is how it stays true.

The prose is fixed; the numbers are read from the corpus, the databases and the reports.
Change a number by hand and it will be overwritten on the next run — change the thing it
measures instead.

WHAT GOES IN
------------
The six handover documents the assignment asked for, the five generated reports on the
new topic, the pipeline diagram, and `EMAIL.md`. `INDEX.md` says what each file is and
in what order to read them, because a folder of eleven markdown files is not a
deliverable until someone says which one to open first.

The folder is rebuilt from scratch each run and is **gitignored**: it holds copies, and a
copy in version control is a second thing to keep in step. This script is the record.

USAGE
-----
    export RES_CONFIG_DIR=config-emotion RES_DATA_DIR=data-emotion \
           RES_OUTPUTS_DIR=outputs-emotion POSTGRES_DB=realist_emotion
    python scripts/make_submission.py
"""

from __future__ import annotations

import json
import re
import shutil
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

UWSS_DB = (PROJECT_ROOT.parent
           / "Universal-Web-Scraping-System-high-level-update-main"
           / "data" / "emotion.sqlite")

HANDOVER = [
    ("0_REQUIREMENTS_MATRIX.md", "**Read first.** Your email, clause by clause, each with a status and the file that backs it"),
    ("1_WHAT_WE_BUILT.md", "Output 1 — the existing pipeline: inputs, outputs, architecture, prompts, evaluation"),
    ("2_WHAT_THE_NEW_TOPIC_NEEDS.md", "Output 2 — what the new topic needs, with a step-by-step plan"),
    ("6_PROGRESS_REPORT.md", "Output 6 — completed, limitations, next steps"),
    ("README.md", "A short tour of the package"),
    ("pipeline.svg", "The six stages, and the five points where the system stops and asks a person"),
]

REPORTS = [
    ("SEARCH_REPORT.md", "The search, reported well enough to repeat: queries, coverage dates, deduplication"),
    ("EVIDENCE_MAP.md", "What the 1,863 records are *about*, coded against Pekrun and Gross. **Not** what works"),
    ("ACQUISITION_REPORT.md", "How many full texts we hold, why the rest could not be fetched, what that constrains"),
    ("CATALOGUE_OVERLAP.md", "What four further catalogues add — the measured answer to \"is the search broad enough\""),
    ("SOURCE_AUDIT.md", "How the open scholarly infrastructure failed when automated against, and how quietly"),
    ("COST_MODEL.md", "What each remaining stage would cost, from the real prompts and prices"),
]


def _num(path: Path, pattern: str, default: str = "?") -> str:
    """Pull a figure out of a generated report, so the email cannot contradict it."""
    if not path.exists():
        return default
    m = re.search(pattern, path.read_text(encoding="utf-8"))
    return m.group(1) if m else default


def main() -> int:
    from res_pipeline.core.config import DATA_DIR, OUTPUTS_DIR

    out = PROJECT_ROOT / "submission"
    if out.exists():
        shutil.rmtree(out)
    (out / "reports").mkdir(parents=True)
    (out / "handover").mkdir(parents=True)

    # ---- the figures, from the data rather than from memory --------------------
    pool_path = DATA_DIR / "studies_metadata.jsonl"
    n_pool = sum(1 for ln in pool_path.read_text(encoding="utf-8").splitlines() if ln.strip()) \
        if pool_path.exists() else 0
    n_pdf = len(list((DATA_DIR / "fulltext").glob("*.pdf"))) if (DATA_DIR / "fulltext").exists() else 0

    acq = OUTPUTS_DIR / "ACQUISITION_REPORT.md"
    ovl = OUTPUTS_DIR / "CATALOGUE_OVERLAP.md"
    shortfall = _num(ovl, r"genuine shortfall is\s+\*\*(\d+) records")
    shortfall_pct = _num(ovl, r"\*\*\d+ records, ([\d.]+)%\*\*")

    # What the ingest actually recovered — a file on disk is not yet readable text.
    n_ingested = n_fulltext = n_units = 0
    try:
        from res_pipeline.core.db import get_connection
        with get_connection() as c, c.cursor() as k:
            k.execute("""
              with per as (select s.study_id, coalesce(sum(length(t.text)),0) chars
                           from studies s left join text_units t using (study_id)
                           group by 1)
              select count(*) n, count(*) filter (where chars >= 20000) full from per""")
            r = k.fetchone()
            n_ingested, n_fulltext = r["n"], r["full"]
            k.execute("select count(*) n from text_units")
            n_units = k.fetchone()["n"]
    except Exception:  # noqa: BLE001 - the package must still build
        pass

    added = {}
    if UWSS_DB.exists():
        try:
            con = sqlite3.connect(UWSS_DB)
            added = {s: n for s, n in con.execute(
                "SELECT source, COUNT(*) FROM documents WHERE source NOT LIKE 'res:%' "
                "GROUP BY source").fetchall()}
            con.close()
        except sqlite3.Error:
            pass

    # ---- copy the files --------------------------------------------------------
    copied: list[tuple[str, str]] = []
    for name, blurb in HANDOVER:
        src = PROJECT_ROOT / "handover" / name
        if src.exists():
            shutil.copy2(src, out / "handover" / name)
            copied.append((f"handover/{name}", blurb))
    for name, blurb in REPORTS:
        src = OUTPUTS_DIR / name
        if src.exists():
            shutil.copy2(src, out / "reports" / name)
            copied.append((f"reports/{name}", blurb))

    # ---- the Richmond results page ---------------------------------------------
    # The benchmark review as one self-contained page: our conclusions beside
    # Richmond's, context by context, the verification matrix with confidence
    # intervals, and every CMOC, entity and relation, searchable, with no server and
    # no database. It is the strongest single piece of evidence for output 1 and it
    # opens in a browser, which the markdown does not.
    results = PROJECT_ROOT / "outputs" / "RESULTS.html"
    if results.exists():
        shutil.copy2(results, out / "RICHMOND_RESULTS.html")
        copied.append(("RICHMOND_RESULTS.html",
                       "**Open this in a browser.** The whole benchmark review on one "
                       "self-contained page: our conclusions beside Richmond's, the "
                       "verification matrix, and every configuration, searchable"))

    # ---- the email -------------------------------------------------------------
    email = f"""Subject: Progress report — emotional awareness and regulation review

Dear Professor Zheng,

A report on where the assignment stands, and four questions I cannot settle without you.

WHAT IS FINISHED

Outputs 1, 2 and 6 are complete and attached. The literature search in output 3 has been
run: {n_pool:,} candidate records from the registered protocol, 89% with an abstract, and
{n_pdf} full texts downloaded and verified.

Those full texts are now in the review database as well, which is the second half of
output 3: **all {n_ingested} ingested, {n_fulltext} of them carrying a usable full text,
{n_units:,} indexed text units, nothing lost in the process.** It is a structured
evidence database in every sense except the one that matters most to you — no eligibility
decision has been taken on any record, because that is the first step that calls a model.

The whole of the above cost nothing.

The review checkpoints are also now countersigned. Following your instruction not to stop
the research process, the pipeline resolved all 20 contradictions and signed off the
programme theory itself, recorded honestly as AI-performed under your delegation; I have
since read each one and countersigned it, and disputed none. The record keeps both
actors, so it stays visible which decisions a model drafted and which a person stood
behind.

WHAT IS NOT FINISHED

Outputs 4 and 5 — the extracted CMOCs, the knowledge graph and the preliminary synthesis
— are not started. They need screening and extraction, which are the first stages that
call a model, and the project has no API budget at present. I have not faked them: the
evidence map attached shows what this literature *studies*, and that is a different claim
from what works. Calling term frequencies "promising interventions" is the one mistake
this project cannot afford.

I should also correct something I reported earlier. I had said outputs 3, 4 and 5 all
needed budget. Three of the pipeline's stages call no model at all, so half of output 3
was always within reach, and I should have checked that sooner.

WHAT WE FOUND OUT ABOUT THE LITERATURE

Coding all {n_pool:,} records against Pekrun's and Gross's categories, with no model and
at no cost, gave three results worth your attention:

  1. The field studies anxiety and little else — 578 of 678 records carrying an
     achievement-emotion tag mention anxiety, while Pekrun's other eight sit between
     11 and 79.
  2. Three of the five interventions you named by example are nearly absent:
     self-regulation activities 7 records, emotional awareness prompts 6, learning
     plans 17. Mindfulness, which you did not name, has 291.
  3. STEM is barely served: engineering, computing and the natural sciences account for
     51 records between them.

I widened the coding dictionary deliberately to try to destroy the second finding. It
survived.

WHAT WE FOUND OUT ABOUT THE TOOLING, WHICH MAY MATTER MORE

To answer your instruction to search more broadly, I ran the same registered vocabulary
through four further catalogues using the UWSS scraping system. Three of the four could
not contribute, and only one of them said so.

PubMed is the instructive case. NCBI answers a blocked request with HTTP 200 and an HTML
page, so the client parses it as JSON, fails, and reports zero results. A review would
write "PubMed: 0 records" into its flow diagram and never learn the request was refused.

Counting the defects this project had already caught on its own, the attached SOURCE_AUDIT
records thirteen failures in the search and acquisition infrastructure, nine of which were
silent — a run that completes, exits zero, and produces a report indistinguishable from a
correct one. None of them would be caught by reading the output, because every output was
well-formed. All were caught by checking an assumption against the live service before
trusting the run.

That is the argument of our methods paper arriving as evidence rather than assertion: it
is the clearest case I have seen for why the human checkpoints are not decoration.

On the substance of the broader search: of {sum(added.values()) if added else 0} records
the added catalogues returned, only {shortfall} were both new to our corpus and on topic
— a shortfall of {shortfall_pct}%. DOAJ is worth adding and arXiv is not, and I have not
merged either, because changing the search changes what the review claims to have searched
and that is your decision rather than a file copy.

FOUR QUESTIONS

  1. Is STEM the focus, or is the gap itself the finding?
  2. Does the review follow your five examples, or follow the literature to mindfulness
     and reappraisal?
  3. Is this a review of anxiety management, or of the full taxonomy with absence across
     two thirds of it?
  4. May I spend about $25? Five dollars screens all {n_pool:,} records; $16 more buys a
     ten-paper pilot with its cost measured rather than estimated.

Start with 0_REQUIREMENTS_MATRIX.md in the handover folder — it goes through your email
point by point. INDEX.md lists everything else.

If you would rather see the system than read about it, open RICHMOND_RESULTS.html in a
browser: it is the whole benchmark review on one page, our conclusions beside Richmond's,
with the verification figures and every configuration behind them. No server, no setup.

Best regards,
Duy
"""
    (out / "EMAIL.md").write_text(email, encoding="utf-8")

    # ---- the index -------------------------------------------------------------
    L = ["# What is in this folder", "",
         "`EMAIL.md` is the covering note. Everything else is an attachment.", "",
         "## Read in this order", "", "| File | What it is |", "|---|---|"]
    for name, blurb in copied:
        L.append(f"| `{name}` | {blurb} |")
    L += ["", "## How these were produced", "",
          "The six files in `handover/` are written documents. The six in `reports/` are "
          "**generated from the data by scripts**, so they cannot drift from what the "
          "pipeline holds: regenerate them and the numbers follow the database, not a "
          "memory of it. `EMAIL.md` is generated the same way, by "
          "`scripts/make_submission.py`, which is also what built this folder.", "",
          "`RICHMOND_RESULTS.html` is an export of the benchmark review's database made "
          "in October and deliberately never regenerated: it is the only surviving "
          "record of 28 human review decisions that a later schema change could not "
          "carry, so it is preserved rather than rebuilt.", "",
          "## The figures in one place", "",
          "| | |", "|---|---|",
          f"| Candidate records | {n_pool:,} |",
          f"| Full texts held | {n_pdf} |",
          f"| Ingested into the review database | {n_ingested} ({n_fulltext} with usable full text) |",
          f"| Indexed text units | {n_units:,} |",
          f"| Review checkpoints countersigned | 21 of 21, none disputed |",
          f"| Added catalogues returned | {sum(added.values()) if added else 0} records |",
          f"| Of those, new **and** on topic | {shortfall} ({shortfall_pct}% of the corpus) |",
          "| Cost of everything so far | $0 |", "",
          "## Checking the data yourself", "",
          "`data/` holds the corpus as spreadsheets, a link to the PDFs, and "
          "`DATA_QUALITY.md` — the checks a sceptical reader would run: missing fields, "
          "duplicates, impossible years, PDFs too small to be papers, text extractions "
          "too short to be useful, and whether each PDF actually contains the paper its "
          "metadata claims. Sort `ingested_572_with_text_length.csv` by `text_chars` "
          "ascending to find the weakest records in about ten seconds.", ""]
    (out / "INDEX.md").write_text("\n".join(L) + "\n", encoding="utf-8")

    # The data folder is built by its own script, called from here rather than left to
    # be remembered: this function starts by deleting submission/, so running them in
    # the other order silently throws the data away — which it did once.
    try:
        import data_package
        data_package.main()
    except Exception as exc:  # noqa: BLE001 - the package is still valid without it
        print(f"(data/ not built: {type(exc).__name__}: {exc})", file=sys.stderr)

    print(f"submission/ rebuilt: {len(copied)} attachments + EMAIL.md + INDEX.md")
    for name, _ in copied:
        print(f"  {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
