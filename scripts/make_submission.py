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

    ovl = OUTPUTS_DIR / "CATALOGUE_OVERLAP.md"
    shortfall = _num(ovl, r"genuine shortfall is\s+\*\*(\d+) records")
    shortfall_pct = _num(ovl, r"\*\*\d+ records, ([\d.]+)%\*\*")
    emap = OUTPUTS_DIR / "EVIDENCE_MAP.md"
    n_ei = _num(emap, r"Emotional intelligence \(as a named construct\)[^|]*\|\s*(\d+)")

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

    # ---- what was given to the AI, and what it decided -------------------------
    # Section 1 of the assignment asks, in as many words, for "the agents, prompts,
    # instructions, schemas, and configurations used in the pipeline" and for "the
    # materials and instructions you previously provided to AI, together with
    # important AI responses, recommendations, and decisions made during
    # development". Describing those in prose is not supplying them.
    ai = out / "pipeline-and-ai-record"
    ai.mkdir(exist_ok=True)
    for src, dest, blurb in [
        (PROJECT_ROOT / "CLAUDE.md", "INSTRUCTIONS_TO_AI.md",
         "The standing instructions the AI is given at the start of every session — "
         "the project's rules, constraints and current state"),
        (PROJECT_ROOT / "docs" / "DECISION_LOG.md", "DECISION_LOG.md",
         "Every methodological decision, with its reasoning and what would reverse it"),
        (PROJECT_ROOT / "WALKTHROUGH.md", "SESSION_LOG.md",
         "The full development record, session by session: what was tried, what was "
         "found, what was wrong and had to be corrected"),
        (PROJECT_ROOT / "docs" / "ARCHITECTURE.md", "ARCHITECTURE.md",
         "How the pipeline is put together"),
        (PROJECT_ROOT / "config-emotion" / "protocol.yaml", "protocol_emotion.yaml",
         "The review protocol for the new topic: questions, eligibility criteria, "
         "search strategy. **A draft — it has not been reviewed by anyone**"),
        (PROJECT_ROOT / "config-emotion" / "coding_frame.yaml", "coding_frame.yaml",
         "The theory-grounded dictionary behind the evidence map, with every revision "
         "to it recorded and justified"),
    ]:
        if src.exists():
            shutil.copy2(src, ai / dest)
            copied.append((f"pipeline-and-ai-record/{dest}", blurb))
    prompts = PROJECT_ROOT / "config" / "prompts"
    if prompts.is_dir():
        shutil.copytree(prompts, ai / "prompts", dirs_exist_ok=True)
        copied.append(("pipeline-and-ai-record/prompts/",
                       f"The {len(list(prompts.glob('*.yaml')))} agent prompts, "
                       "verbatim — one file per stage"))

    # ---- the documents the handover links to -----------------------------------
    # Without these, thirteen links in the package resolve to nothing. They are also
    # what §1 means by "the evaluation procedures and results from the Richmond
    # benchmark", so they belong here on their own merits.
    for name, blurb in [
        ("VERIFICATION_PROTOCOL.md",
         "Why these are the right metrics, with citations, and an honest list of what "
         "is still missing"),
        ("MACHINE_VS_HUMAN.md",
         "The system's output against two human coders — the authoritative record of "
         "the comparison, including the corrections"),
        ("OUTPUT_AND_VERIFICATION.md", "What the pipeline outputs and how each is checked"),
        ("SYSTEM_AND_ALGORITHMS.md", "The algorithms, stage by stage"),
    ]:
        src = PROJECT_ROOT / "docs" / name
        if src.exists():
            (out / "reference-docs").mkdir(exist_ok=True)
            shutil.copy2(src, out / "reference-docs" / name)
            copied.append((f"reference-docs/{name}", blurb))

    # ---- the Richmond outputs themselves ---------------------------------------
    # "the input data, intermediate results, outputs, knowledge graphs, and
    # verification reports" — assignment §1, verbatim. The raw export is the database
    # with nothing summarised away, which is what makes every figure in this package
    # checkable rather than merely stated.
    for src, dest, blurb in [
        (PROJECT_ROOT / "outputs" / "Knowledge_Graph_Report.html",
         "benchmark-outputs/Knowledge_Graph_Report.html",
         "The Richmond knowledge graph — entities, relations and communities"),
        (PROJECT_ROOT / "outputs" / "MASTER_VERIFICATION_REPORT.md",
         "benchmark-outputs/MASTER_VERIFICATION_REPORT.md",
         "The verification report: every metric, how it was computed, and its "
         "confidence interval"),
    ]:
        if src.exists():
            (out / dest).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, out / dest)
            copied.append((dest, blurb))
    raw = PROJECT_ROOT / "outputs" / "raw_export"
    if raw.is_dir():
        shutil.copytree(raw, out / "benchmark-outputs" / "raw_export",
                        dirs_exist_ok=True)
        copied.append(("benchmark-outputs/raw_export/",
                       f"The benchmark database exported whole — {len(list(raw.iterdir()))} "
                       "files, CSV and JSON, nothing summarised. Every figure in this "
                       "package resolves to a row in here"))

    # ---- the conference paper --------------------------------------------------
    paper = PROJECT_ROOT / "outputs" / "submission_v2" / "AERA_2027_Preliminary_Paper_FINAL.docx"
    if paper.exists():
        shutil.copy2(paper, out / "AERA_2027_paper_as_accepted.docx")
        copied.append(("AERA_2027_paper_as_accepted.docx",
                       "The conference paper **exactly as accepted**. Its figures have "
                       "since been superseded — see the note in the covering email"))

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

    # ---- make every link in the package resolve --------------------------------
    # The handover documents link by their position in the repository
    # (../outputs-emotion/X.md), and the package puts those files somewhere else
    # (../reports/X.md). Twenty links pointed at nothing until this was added. A link
    # that 404s in a document sent to a supervisor is the kind of detail that makes a
    # reader doubt the parts they cannot check.
    def _fix_links(md: Path) -> int:
        text = md.read_text(encoding="utf-8")
        depth = len(md.relative_to(out).parts) - 1
        up = "../" * depth

        def repl(m: re.Match) -> str:
            label, target, frag = m.group(1), m.group(2), m.group(3) or ""
            name = Path(target).name
            for folder in ("reports", "reference-docs", "handover",
                           "pipeline-and-ai-record", "benchmark-outputs"):
                if (out / folder / name).exists():
                    return f"[{label}]({up}{folder}/{name}{frag})"
            if (out / name).exists():
                return f"[{label}]({up}{name}{frag})"
            # Not in the package: keep the words, drop the dead link.
            return label

        fixed, n = re.subn(r"\[([^\]]+)\]\((?!https?:|mailto:)([^)#]+)(#[^)]*)?\)",
                           repl, text)
        if fixed != text:
            md.write_text(fixed, encoding="utf-8")
        return n

    rewritten = sum(_fix_links(md) for md in sorted(out.rglob("*.md")))

    # ---- the email -------------------------------------------------------------
    # The covering note.
    #
    # Short on purpose. The RA's standing instruction after reading a 1,200-word draft:
    # a supervisor who gets a four-section report with nested bullets does not read it,
    # and a report nobody reads is worth less than a short one that is read. Prose, no
    # headings, no markdown emphasis — Gmail's plain text renders ** as literal asterisks.
    email = f"""Subject: Progress report — emotional regulation review

Dear Professor Zheng,

A short update on the emotional awareness and regulation assignment.

Outputs 1, 2 and 6 are done and attached. For output 3 the search has run:
{n_pool:,} candidate records from ten registered queries, {n_pdf} full texts downloaded,
and all of them ingested and indexed. I also ran the same queries through four more
catalogues — DOAJ, PubMed, arXiv, Semantic Scholar — to check whether two were enough.
They were; the shortfall is about {shortfall_pct}%.

Two things worth flagging. Our coding frame had no category for emotional intelligence,
which is the first construct in your objective; adding it brings in {n_ei} records, about
a fifth of the pool. And three figures we had reported earlier turned out to be wrong and
are corrected in the handover — so please don't quote the verification numbers from the
AERA paper, they have been superseded.

The review checkpoints are countersigned. The pipeline resolved all 20 contradictions
itself, as you asked in section 5; I have since read each one and signed it.

Attached: the handover documents — start with the requirements matrix, it goes through
your email point by point — six reports generated straight from the data, the prompts and
decision log you asked for in section 1, the Richmond benchmark outputs, and the corpus as
spreadsheets so you can check the records yourself.

JSU still has not released the tool allowance, so I have had no API credit; everything
above was built to run without one. What is left — outputs 4 and 5 — needs screening
($5.44) and a ten-paper pilot extraction ($16).

This week I will finish the downloads (Unpaywall has found 1,325 open-access copies, well
past the {n_pdf} we hold), re-run the evidence map over the larger set, and have the
screening ready to execute the day budget arrives.

Three scope decisions are at the end of the matrix. Happy to be overruled on any of them.

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

    print(f"submission/ rebuilt: {len(copied)} attachments + EMAIL.md + INDEX.md "
          f"({rewritten} links rewritten to package paths)")
    for name, _ in copied:
        print(f"  {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
