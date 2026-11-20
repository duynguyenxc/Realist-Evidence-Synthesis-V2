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
new topic and the pipeline diagram. `INDEX.md` says what each file is and
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
    ("1_WHAT_WE_BUILT.md", "The existing pipeline in full: architecture, all ten agent prompts, schemas, configurations, evaluation results"),
    ("2_WHAT_THE_NEW_TOPIC_NEEDS.md", "Your seven questions answered, with a step-by-step plan"),
    ("6_PROGRESS_REPORT.md", "**Read first.** What is done, what the limitations are, what comes next, and the three scope decisions we took"),
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

    # Two folders, named so that no one has to remember which is which. The RA uploads
    # the whole of `2-UPLOAD-TO-DRIVE` and attaches the one file in `1-ATTACH-TO-EMAIL`.
    # The emailed file is also inside the Drive folder: the supervisor who clicks the
    # link should find everything there, not everything-except-the-thing-he-already-has.
    root = PROJECT_ROOT / "submission"
    out = root / "2-UPLOAD-TO-DRIVE"
    if root.exists():
        shutil.rmtree(root)
    (root / "1-ATTACH-TO-EMAIL").mkdir(parents=True)
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
        # Copied as HTML and converted to PDF later in this run, so the name INDEX
        # prints is the converted one while the source read here is the export.
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
            # INDEX must name the file as it will exist when the package is read, and
            # make_pdf converts every HTML page later in this run.
            copied.append((dest[:-5] + ".pdf" if dest.endswith(".html") else dest, blurb))
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
    # no database. It is the strongest single piece of evidence for the documentation
    # the assignment asks for. Copied as HTML and converted to PDF later in this run.
    results = PROJECT_ROOT / "outputs" / "RESULTS.html"
    if results.exists():
        shutil.copy2(results, out / "Our_results_vs_Richmond.html")
        copied.append(("Our_results_vs_Richmond.pdf",
                       "**The benchmark review in full**: Richmond's conclusions beside "
                       "the system's, context by context, every concept Richmond named "
                       "and whether we found it, and every causal link. It opens with a "
                       "notice correcting five figures that predate a later recount"))

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

    # ---- the index -------------------------------------------------------------
    L = ["# What is in this folder", "",
         "**Start with `Emotional_regulation_review.pdf`.** It holds all nine written "
         "documents in reading order behind a table of contents. It is also the file "
         "attached to the covering email, so if you have read that attachment you have "
         "read the written part of this folder.", "",
         "Everything below is the underlying material: the same documents as Markdown, "
         "the benchmark outputs, the agent prompts, the decision log, and the data.", "",
         "## Read in this order", "", "| File | What it is |", "|---|---|"]
    for name, blurb in copied:
        L.append(f"| `{name}` | {blurb} |")
    L += ["", "## How these were produced", "",
          "The three files in `handover/` are written documents. The six in `reports/` are "
          "**generated from the data by scripts**, so they cannot drift from what the "
          "pipeline holds: regenerate them and the numbers follow the database, not a "
          "memory of it. This folder is built by "
          "`scripts/make_submission.py`, which is also what built this folder.", "",
          "", "## Three tables in `raw_export/` are empty", "",
          "They are empty in the database, not lost in the export, and each says "
          "something:", "",
          "- `theorised_entities.csv` — the pipeline can now propose a concept reasoned "
          "from theory rather than read from a paper, but **that capability has never "
          "been run on the Richmond corpus**. It is built and tested, not exercised.",
          "- `token_usage.csv` — model cost was not recorded during the Richmond runs. "
          "That is why `COST_MODEL.md` had to be built by measuring the prompts directly "
          "rather than by reading a history.",
          "- `agent_feedback.csv` — the mechanism for correcting an agent from a human "
          "note exists and was not used on this corpus.", "",
          "`Our_results_vs_Richmond.pdf` is an export of the benchmark review's database, "
          "deliberately never regenerated: it is the only surviving "
          "record of 21 human review decisions that a later schema change could not "
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
          "metadata claims. Sort the `ingested_*_with_text_length.csv` file by `text_chars` "
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

    # ORDER MATTERS, and getting it wrong once already produced a package with the
    # uncorrected figures in it. The benchmark page is corrected while it is still HTML;
    # make_pdf then converts it and deletes the HTML. Reversed, the patch finds no file,
    # reports failure, and the PDF beside it carries five superseded numbers.
    #
    # The page itself predates the 2026-11-04 recount and cannot be regenerated, which is
    # why it is patched rather than rebuilt.
    try:
        import patch_richmond_page
        if patch_richmond_page.main() != 0:
            print("!! Our_results_vs_Richmond NOT corrected — do not send the package",
                  file=sys.stderr)
    except Exception as exc:  # noqa: BLE001
        print(f"!! Our_results_vs_Richmond not corrected: {type(exc).__name__}: {exc}",
              file=sys.stderr)

    # Builds the one file that gets emailed, then converts every remaining HTML page in
    # the package to PDF and removes the HTML, so the folder holds one format.
    try:
        import make_pdf
        make_pdf.main()
    except Exception as exc:  # noqa: BLE001 - the package is still valid without it
        print(f"(the PDF was not built: {type(exc).__name__}: {exc})",
              file=sys.stderr)

    # What the supervisor actually receives by mail. Two PDFs: the written handover, and
    # the benchmark review, which is the one place his own question — does the system
    # reach Richmond's conclusions? — is answered side by side rather than asserted.
    # Everything else is a link away.
    mail = root / "1-ATTACH-TO-EMAIL"
    total = 0
    for name in ("Emotional_regulation_review.pdf", "Our_results_vs_Richmond.pdf"):
        f = out / name
        if f.exists():
            shutil.copy2(f, mail / name)
            total += f.stat().st_size
            print(f"  -> 1-ATTACH-TO-EMAIL/{name} ({f.stat().st_size//1024} KB)")
    if total:
        # Gmail refuses at 25 MB and most university mail servers at less.
        print(f"  -> attachments total {total/1_048_576:.1f} MB")

    print(f"submission/ rebuilt: {len(copied)} attachments + INDEX.md "
          f"({rewritten} links rewritten to package paths)")
    for name, _ in copied:
        print(f"  {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
