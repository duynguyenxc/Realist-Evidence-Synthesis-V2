#!/usr/bin/env python3
"""Correct the superseded figures on the copy of RESULTS.html that is sent out.

THE PROBLEM
-----------
`outputs/RESULTS.html` was exported before the matcher defect was fixed on 2026-11-04, so
it carries four figures that have since been corrected, and **every one of them is wrong
in the direction that flatters the system**:

    same realist role   34/46 -> 32/46
    anchored relations  29/40 -> 28/40
    strict relations     6/40 ->  5/40
    (type-level 39/40 is unchanged)

Worse than any single number is the comparison table. It puts the system's *role-tolerant*
score beside the two human coders' *one-to-one* scores:

    Coder A (human)      30/46   Coder B (human)    28/46
    Both humans agreed   28/46   THE SYSTEM         34/46

which reads as the machine beating both humans by a clear margin. The humans worked under
a frame giving one code per element, so their matching is one-to-one by construction. The
system's like-for-like figure is **26/46** — below both — and it does not appear on the
page at all.

WHY NOT JUST REGENERATE IT
--------------------------
`res export-results` must never be run again. The page reports 28 human review decisions
that live in a table a later snapshot restore could not carry, so re-exporting silently
reports zero of them and overwrites the only surviving record. The page is preserved, not
rebuilt.

SO THIS PATCHES THE COPY, NOT THE RECORD
----------------------------------------
`outputs/RESULTS.html` is never touched. `make_submission.py` copies it into the package
on every build, and this script edits that copy afterwards. Nothing is deleted: each
superseded figure stays visible with the corrected one beside it, because the conference
paper was accepted carrying those numbers and a reader comparing the two needs to see
both. The missing like-for-like row is added.

Idempotent, and it fails loudly if the page it is given does not contain what it expects —
a silent no-op here would put the uncorrected page in front of the supervisor.

USAGE
-----
    python scripts/patch_richmond_page.py            # patches the submission copy
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PAGE = PROJECT_ROOT / "submission" / "2-UPLOAD-TO-DRIVE" / "Our_results_vs_Richmond.html"

MARKER = "<!-- corrected-2026-11-04 -->"

BANNER = """<!-- corrected-2026-11-04 -->
<div style="max-width:52rem;margin:1.5rem auto;padding:1rem 1.25rem;border:2px solid #8a1c1c;
     border-radius:6px;background:#fff6f6;font:15px/1.6 -apple-system,BlinkMacSystemFont,
     'Segoe UI',Helvetica,Arial,sans-serif;color:#1a1a1a">
  <strong style="color:#8a1c1c">Four figures on this page were superseded on 4 November 2026.</strong>
  This page was exported in October. A defect in the concept-matching code was accepting a
  match whose own written rationale stated the two concepts did <em>not</em> match; fixing it
  and recounting also surfaced a second, independent arithmetic error. Every correction moves
  a number <em>down</em>.
  <table style="border-collapse:collapse;margin:.75rem 0 .5rem;font-size:14px">
    <tr><th style="text-align:left;padding:.2rem 1.2rem .2rem 0">Measure</th>
        <th style="text-align:left;padding:.2rem 1.2rem .2rem 0">On this page</th>
        <th style="text-align:left;padding:.2rem 0">Corrected</th></tr>
    <tr><td style="padding:.2rem 1.2rem .2rem 0">Concepts, same realist role</td>
        <td style="padding:.2rem 1.2rem .2rem 0"><s>34/46</s></td>
        <td style="padding:.2rem 0"><strong>32/46</strong></td></tr>
    <tr><td style="padding:.2rem 1.2rem .2rem 0">Concepts, one-to-one (comparable to a human coder)</td>
        <td style="padding:.2rem 1.2rem .2rem 0"><em>not shown</em></td>
        <td style="padding:.2rem 0"><strong>26/46</strong></td></tr>
    <tr><td style="padding:.2rem 1.2rem .2rem 0">Relations, anchored</td>
        <td style="padding:.2rem 1.2rem .2rem 0"><s>29/40</s></td>
        <td style="padding:.2rem 0"><strong>28/40</strong></td></tr>
    <tr><td style="padding:.2rem 1.2rem .2rem 0">Relations, strict</td>
        <td style="padding:.2rem 1.2rem .2rem 0"><s>6/40</s></td>
        <td style="padding:.2rem 0"><strong>5/40</strong></td></tr>
    <tr><td style="padding:.2rem 1.2rem .2rem 0">Relations, type-level</td>
        <td style="padding:.2rem 1.2rem .2rem 0">39/40</td>
        <td style="padding:.2rem 0">39/40 &mdash; unchanged</td></tr>
  </table>
  <strong>And the comparison with the human coders was not like-for-like.</strong> The table
  below sets the system's role-tolerant score against the two coders' one-to-one scores. Under
  the constraint the humans actually worked under &mdash; one code per element &mdash; the
  system scores <strong>26/46, which is below both of them</strong>. The defensible claim is
  non-inferiority resting on overlapping confidence intervals, not superiority.
  <div style="margin-top:.6rem;font-size:13.5px;color:#555">
    The page is left otherwise as exported, because it is the only surviving record of 28
    human review decisions. <code>MACHINE_VS_HUMAN.md</code> &sect;5.1 has the arithmetic.
  </div>
</div>
"""

# (needle, replacement). Each must appear exactly once.
EDITS: list[tuple[str, str]] = [
    # The comparison table: correct the system's row and add the row that was missing.
    ("<tr><td><strong>THE SYSTEM</strong></td><td class='num'>34/46 &nbsp;(74%)</td>"
     "<td class='small'>same realist role as Richmond assigned</td></tr>",
     "<tr><td><strong>THE SYSTEM</strong>, same role</td>"
     "<td class='num'><s>34/46</s> &rarr; 32/46 &nbsp;(70%)</td>"
     "<td class='small'>corrected 2026-11-04. Role-tolerant: <em>not</em> comparable with the "
     "rows above</td></tr>"
     "<tr><td><strong>THE SYSTEM</strong>, one-to-one</td>"
     "<td class='num'>26/46 &nbsp;(57%)</td>"
     "<td class='small'><strong>Compare this row with the humans.</strong> Same constraint "
     "they worked under &mdash; and it is below both</td></tr>"),

    ("<strong>73.9%</strong><br><span class='small'>95% CI 58.9%\u201385.7%<br>34/46</span>",
     "<strong>69.6%</strong><br><span class='small'>95% CI 54.2\u201382.3%<br>"
     "32/46 &nbsp;<s>was 73.9%, 34/46</s></span>"),

    ("it recovers 29 of 40 of\nRichmond's causal links",
     "it recovers 28 of 40 of\nRichmond's causal links"),

    ("<strong>72.5%</strong><br><span class='small'>95% CI 56.1%\u201385.4%<br>29/40</span>",
     "<strong>70.0%</strong><br><span class='small'>95% CI 53.5\u201383.4%<br>"
     "28/40 &nbsp;<s>was 72.5%, 29/40</s></span>"),

    ("<strong>15.0%</strong><br><span class='small'>95% CI 5.7%\u201329.8%<br>6/40</span>",
     "<strong>12.5%</strong><br><span class='small'>5/40 &nbsp;<s>was 15.0%, 6/40</s><br>"
     "interval not restated</span>"),
]


def main() -> int:
    if not PAGE.exists():
        print(f"Not in the package: {PAGE}", file=sys.stderr)
        return 1
    s = PAGE.read_text(encoding="utf-8")
    if MARKER in s:
        print("Our_results_vs_Richmond.html already corrected")
        return 0

    for needle, repl in EDITS:
        n = s.count(needle)
        if n != 1:
            # Loud, not silent: the alternative is shipping the uncorrected page.
            print(f"Expected exactly one of:\n  {needle[:90]}…\nfound {n}. "
                  f"The export format changed; fix this script before shipping.",
                  file=sys.stderr)
            return 1
        s = s.replace(needle, repl, 1)

    # Put the banner immediately after the page's own opening <body>.
    at = s.lower().find("<body")
    at = s.find(">", at) + 1 if at != -1 else 0
    s = s[:at] + "\n" + BANNER + s[at:]

    PAGE.write_text(s, encoding="utf-8")
    print(f"Our_results_vs_Richmond.html corrected: {len(EDITS)} figures + banner")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
