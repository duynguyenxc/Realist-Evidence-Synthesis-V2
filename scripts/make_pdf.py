#!/usr/bin/env python3
"""Build one PDF holding every written document in the submission.

WHY THIS EXISTS
---------------
The handover documents are Markdown. A Markdown file attached to an email is a trap: the
recipient double-clicks it, the operating system opens it in a plain text editor, and they
are looking at `**bold**` and `|---|---|`. These documents are mostly tables, and a
Markdown table rendered as plain text is unreadable — the one format where the fallback is
worse than no formatting at all.

One PDF rather than nine files, because nine attachments is a filing job for the reader.
A PDF opens the same way on every device, can be annotated, and needs no decision from the
reader about what to open first.

HOW, GIVEN WHAT IS INSTALLED
----------------------------
No `pandoc`, no `weasyprint`. `markdown-it-py` is already a dependency and Chrome is on
this machine, so: Markdown -> HTML with markdown-it, then HTML -> PDF with headless
Chrome's own print engine. That is the same renderer the reader would get by pressing
Cmd-P, so what the PDF shows is what the page is.

**The HTML is a build artefact and is written to a temporary directory, not into
`submission/`.** Only the PDF belongs in the folder the supervisor receives; shipping both
would mean two files that say the same thing and a reader wondering which is current.

The Markdown files stay in the package for anyone who wants to grep or diff them.

USAGE
-----
    python scripts/make_pdf.py
    # -> submission/2-UPLOAD-TO-DRIVE/Emotional_regulation_review.pdf
"""

from __future__ import annotations

import html
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SUBMISSION = PROJECT_ROOT / "submission" / "2-UPLOAD-TO-DRIVE"

# Reading order, not alphabetical order. The progress report answers "what did you do",
# which is the question the supervisor opens the file with.
DOCS = [
    ("handover/6_PROGRESS_REPORT.md", "Progress report",
     "What is finished, what the limitations are, what comes next, and three decisions on scope"),
    ("handover/1_WHAT_WE_BUILT.md", "The existing pipeline",
     "Architecture, all ten agent prompts, schemas, configurations, evaluation results"),
    ("handover/2_WHAT_THE_NEW_TOPIC_NEEDS.md", "What the new topic needs",
     "Your seven questions answered, with a step-by-step plan"),
    ("reports/SEARCH_REPORT.md", "The search",
     "The ten queries, coverage dates and deduplication — enough to repeat it"),
    ("reports/EVIDENCE_MAP.md", "What the studies are about",
     "The 1,863 records coded against the theoretical frameworks. Not what works"),
    ("reports/ACQUISITION_REPORT.md", "Full-text acquisition",
     "How many full texts are held, why the rest could not be fetched"),
    ("reports/CATALOGUE_OVERLAP.md", "Is the search broad enough",
     "What four further databases would have added, measured"),
    ("reports/SOURCE_AUDIT.md", "How the search infrastructure failed",
     "Thirteen failures, nine of them silent"),
    ("reports/COST_MODEL.md", "Cost of every remaining stage",
     "Measured from the real prompts, not estimated"),
]

CSS = """
:root{--ink:#1a1a1a;--soft:#555;--line:#d8d8d8;--bg:#fff;--accent:#8a1c1c;--mark:#fffbe6}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font:16px/1.65 Georgia,"Iowan Old Style","Times New Roman",serif}
.wrap{max-width:46rem;margin:0 auto;padding:3rem 1.25rem 6rem}
h1,h2,h3,h4{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;
  line-height:1.25;margin:2.2rem 0 .7rem}
h1{font-size:1.85rem;letter-spacing:-.02em}
h2{font-size:1.3rem;border-bottom:1px solid var(--line);padding-bottom:.3rem}
h3{font-size:1.08rem}
h4{font-size:.98rem;color:var(--soft)}
p,li{margin:.7rem 0}
a{color:var(--accent)}
code{font:.88em/1.4 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  background:#f4f4f4;padding:.1em .35em;border-radius:3px}
pre{background:#f7f7f7;border:1px solid var(--line);border-radius:5px;
  padding:.85rem 1rem;overflow-x:auto}
pre code{background:none;padding:0}
blockquote{margin:1rem 0;padding:.6rem 1rem;border-left:3px solid var(--accent);
  background:var(--mark);color:#3a3a3a}
blockquote p{margin:.35rem 0}
table{border-collapse:collapse;width:100%;margin:1.1rem 0;font-size:.9rem;
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif}
th,td{border:1px solid var(--line);padding:.45rem .6rem;text-align:left;vertical-align:top}
th{background:#f2f2f2;font-weight:600}
tr:nth-child(even) td{background:#fbfbfb}
hr{border:0;border-top:1px solid var(--line);margin:2.5rem 0}
/* The cover and its table of contents. */
.cover{border-bottom:2px solid var(--ink);padding-bottom:1.5rem;margin-bottom:1rem}
.cover .sub{color:var(--soft);font-size:1.02rem;margin:.3rem 0 0}
.toc{margin:1.5rem 0 0;padding:0;list-style:none;counter-reset:toc}
.toc li{counter-increment:toc;margin:.5rem 0;padding-left:2.1rem;position:relative}
.toc li::before{content:counter(toc);position:absolute;left:0;top:.05rem;
  font-family:-apple-system,BlinkMacSystemFont,sans-serif;font-size:.78rem;font-weight:600;
  color:var(--accent);border:1px solid var(--accent);border-radius:50%;
  width:1.5rem;height:1.5rem;display:grid;place-items:center}
.toc a{font-weight:600;text-decoration:none}
.toc a:hover{text-decoration:underline}
.toc .what{display:block;color:var(--soft);font-size:.88rem;font-weight:400}
.doc{padding-top:1rem}
.doc > h1:first-child{margin-top:1rem}
.back{font-family:-apple-system,BlinkMacSystemFont,sans-serif;font-size:.8rem;
  color:var(--soft);text-decoration:none}
.back:hover{color:var(--accent)}
/* This block decides what the PDF looks like, so it is the important one. */
@page{size:A4;margin:18mm 16mm}
@media print{
  .wrap{max-width:none;padding:0}
  .doc{break-before:page}
  .back{display:none}
  body{font-size:10.5pt;line-height:1.5}
  h1{font-size:17pt}h2{font-size:13pt}h3{font-size:11.5pt}
  /* A heading stranded at the foot of a page, or one row of a table carried over,
     is the usual way an automatically produced PDF looks automatic. */
  h1,h2,h3,h4{break-after:avoid}
  table,pre,blockquote,li{break-inside:avoid}
  tr{break-inside:avoid}
  thead{display:table-header-group}
  table{font-size:8.6pt}
  a{color:var(--ink);text-decoration:none}
  .toc a{color:var(--accent)}
}
"""


def _slug(path: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", path.lower()).strip("-")


def main() -> int:
    try:
        from markdown_it import MarkdownIt
    except ImportError:
        print("markdown-it-py is not installed", file=sys.stderr)
        return 1

    # `table` is the whole point of this script; `linkify` is off so that a bare DOI in a
    # citation is not turned into a link to somewhere it does not resolve.
    md = MarkdownIt("commonmark").enable(["table", "strikethrough"])

    missing = [p for p, _, _ in DOCS if not (SUBMISSION / p).exists()]
    if missing:
        print(f"Not in the package: {missing}\nRun make_submission.py first.", file=sys.stderr)
        return 1

    toc, bodies = [], []
    for rel, title, what in DOCS:
        anchor = _slug(rel)
        toc.append(
            f'<li><a href="#{anchor}">{html.escape(title)}</a>'
            f'<span class="what">{html.escape(what)}</span></li>')
        text = (SUBMISSION / rel).read_text(encoding="utf-8")
        # Relative links between the Markdown files cannot work inside one HTML file, and
        # a link that silently goes nowhere is worse than plain text. Keep the words.
        text = re.sub(r"\[([^\]]+)\]\((?!https?:|#)[^)]+\)", r"\1", text)
        bodies.append(
            f'<section class="doc" id="{anchor}">\n'
            f'<a class="back" href="#contents">&uarr; contents</a>\n'
            f'{md.render(text)}\n</section>')

    page = f"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Emotional regulation review — handover</title>
<style>{CSS}</style>
<div class="wrap">
  <header class="cover" id="contents">
    <h1>Emotional regulation review</h1>
    <p class="sub">Handover and progress report &middot; prepared for Prof. Wei Zheng</p>
    <ol class="toc">
      {chr(10).join("      " + x for x in toc)}
    </ol>
  </header>
  {chr(10).join(bodies)}
</div>
</html>
"""
    out = SUBMISSION / "Emotional_regulation_review.pdf"
    tmp = Path(tempfile.mkdtemp(prefix="res-reading-copy-"))
    try:
        src = tmp / "reading_copy.html"
        src.write_text(page, encoding="utf-8")
        if not print_pdf(src, out):
            return 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"{out.relative_to(PROJECT_ROOT)}  —  {len(DOCS)} documents, "
          f"{out.stat().st_size/1024:,.0f} KB")

    # Everything the supervisor receives is a PDF. The package also holds two HTML pages
    # produced elsewhere — the exported benchmark review and the knowledge-graph report —
    # and an .html attachment is the same trap as a .md one: it may open in an editor, it
    # looks like something to be wary of in a mail client, and on a phone it is awkward.
    # They are converted and the HTML removed, so there is one format in the folder.
    for page_path in sorted(SUBMISSION.rglob("*.html")):
        pdf = page_path.with_suffix(".pdf")
        if print_pdf(page_path, pdf, budget_ms=25_000):
            page_path.unlink()
            print(f"{pdf.relative_to(PROJECT_ROOT)}  —  converted from HTML, "
                  f"{pdf.stat().st_size/1024:,.0f} KB")
        else:
            # Leave the HTML rather than lose the content; say so loudly.
            print(f"!! {page_path.name} could not be converted and is still HTML",
                  file=sys.stderr)
    return 0


def _browser() -> str | None:
    return next((c for c in (
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    ) if Path(c).exists()), None)


def print_pdf(src: Path, dst: Path, budget_ms: int = 10_000) -> bool:
    """Render one local HTML file to PDF with the browser's own print engine."""
    chrome = _browser()
    if chrome is None:
        # Falling back to HTML would put the format back that this script exists to
        # remove. Say what is wrong instead and change nothing.
        print("No Chrome, Chromium or Edge found — cannot produce a PDF.", file=sys.stderr)
        return False
    r = subprocess.run(
        [chrome, "--headless=new", "--disable-gpu", "--no-sandbox",
         # Without this, every sheet carries Chrome's own URL-and-date furniture.
         "--no-pdf-header-footer",
         # Static pages, but Chrome still needs time to lay out large tables.
         f"--virtual-time-budget={budget_ms}",
         f"--print-to-pdf={dst}", src.as_uri()],
        capture_output=True, text=True, timeout=300)
    if not dst.exists() or dst.stat().st_size < 10_000:
        print(f"Chrome produced no PDF for {src.name}.\n{r.stderr[-500:]}", file=sys.stderr)
        return False
    return True


if __name__ == "__main__":
    raise SystemExit(main())
