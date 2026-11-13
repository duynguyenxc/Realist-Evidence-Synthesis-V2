"""Richmond's conclusions beside ours — computed, not written.

Until 2026-11-13 the page that put the two reviews side by side contained four
hand-typed comparisons and four hand-assigned verdicts, in `webui.py`. It read neither
the benchmark nor the system's output. The problem was not that it was inaccurate; it
was that **it could not be wrong**, because nothing computed it. It could not change
when the system changed, and a comparison nobody can recompute is an opinion about the
evidence rather than a reading of it. For a review whose entire argument is auditability,
that was the wrong thing to be hand-written.

Both sides are already structured data, so the comparison is arithmetic:

* Richmond's five programme-theory statements (`gold/richmond_gold_v3.json`) each name a
  context E-code and the interventions, mechanism-responses and outcomes expected under
  it, with the number of studies Richmond reported behind it.
* The system's entity matching says, per E-code, whether we recovered that concept and
  which of our concepts matched it.
* The system's own programme theory holds nine context-based sections with their
  supporting study ids.

So for each of Richmond's five statements this reports: did we recover the context; what
fraction of its expected interventions, mechanism-responses and outcomes did we recover;
and which of our sections carries the matched concepts. **The verdict is derived from
those fractions by a stated rule, not chosen.**

The rule, fixed here so it is arguable rather than invisible:

    reproduced            context recovered AND >=50% of each of I, M and O
    chain without context the CHAIN is reproduced but Richmond's context label was not
                          recovered — the causal claim is there, the grouping is not
    partial               context recovered, some but not all of the chain
    corpus gap            neither the context nor the chain

**The second verdict was added after the first run of this module, and it is the reason
the module was worth writing.** The hand-written page called Richmond's PTS5 a corpus
gap. Computed, PTS5's chain comes back 3/3 interventions, 4/4 mechanism-responses and
5/5 outcomes — every causal element recovered — and only the context *label* E06
("students with different levels of knowledge within a group") was missed. Calling that
a corpus gap is wrong in a way that matters: the system reconstructed the whole
mechanism and failed to name the population it applies to, which is a different finding
with a different fix. Prose could hide that distinction; arithmetic could not.

Reads stored rows. No model call, no API cost.
"""

from __future__ import annotations

import glob
import json
import os

from res_pipeline.core.config import GOLD_DIR, OUTPUTS_DIR
from res_pipeline.core.db import get_connection

# E03 and E24 were accepted by a matcher defect fixed on 2026-11-04; the stored
# verification report predates the fix, so they are refused here too. Named rather than
# silently filtered, because a correction that leaves no trace is how the first error
# survived six weeks.
REFUSED_BY_MATCHER_FIX = {"E03", "E24"}


def _latest_entity_matches() -> tuple[dict, str]:
    reports = sorted(glob.glob(str(OUTPUTS_DIR / "runs" / "verify-*" / "verification_report.json")),
                     key=os.path.getmtime)
    if not reports:
        raise FileNotFoundError("No verification report found — run `res verify` first.")
    data = json.load(open(reports[-1], encoding="utf-8"))
    per = dict(data["entity_coverage"]["per_entity"])
    for code in REFUSED_BY_MATCHER_FIX:
        if code in per:
            per[code] = {**per[code], "matched": False, "concept": "",
                         "refused_by": "matcher polarity guard, 2026-11-04"}
    return per, os.path.basename(os.path.dirname(reports[-1]))


def _system_sections() -> list[dict]:
    with get_connection() as conn:
        row = conn.execute("SELECT theory_json FROM programme_theories "
                           "ORDER BY version DESC LIMIT 1").fetchone()
    return (row or {}).get("theory_json", {}).get("sections", []) if row else []


def _fraction(codes: list[str], per: dict) -> tuple[int, int, list[str]]:
    found = [c for c in codes if per.get(c, {}).get("matched")]
    return len(found), len(codes), found


def compare() -> dict:
    gold = json.loads((GOLD_DIR / "richmond_gold_v3.json").read_text(encoding="utf-8"))
    per, run_id = _latest_entity_matches()
    sections = _system_sections()

    # Which of our concepts matched anything in each statement — used to say which of our
    # sections carries it, so a reader can go and read our version of the same claim.
    rows = []
    for key, pts in sorted(gold["programme_theory_statements"].items()):
        ctx = pts["context_code"]
        ctx_hit = bool(per.get(ctx, {}).get("matched"))
        i_n, i_d, i_found = _fraction(pts.get("expected_interventions", []), per)
        m_n, m_d, m_found = _fraction(pts.get("expected_mechanism_responses", []), per)
        o_n, o_d, o_found = _fraction(pts.get("expected_outcomes", []), per)

        def half(n: int, d: int) -> bool:
            return d > 0 and n / d >= 0.5

        chain_ok = half(i_n, i_d) and half(m_n, m_d) and half(o_n, o_d)
        chain_any = half(i_n, i_d) or half(m_n, m_d) or half(o_n, o_d)
        if ctx_hit and chain_ok:
            verdict = "reproduced"
        elif chain_ok:
            verdict = "chain without context"
        elif ctx_hit and chain_any:
            verdict = "partial"
        elif chain_any:
            verdict = "chain only, partial"
        else:
            verdict = "corpus gap"

        matched_concepts = {per[c]["concept"] for c in i_found + m_found + o_found
                            if per.get(c, {}).get("concept")}
        if ctx_hit and per.get(ctx, {}).get("concept"):
            matched_concepts.add(per[ctx]["concept"])
        carried_by = [s["context_label"] for s in sections
                      if any(mc.split(":")[-1][:18] in json.dumps(s).lower()
                             for mc in matched_concepts)]

        rows.append({
            "statement": key,
            "richmond_context_code": ctx,
            "richmond_context": pts["context_label"],
            "richmond_source": pts.get("source"),
            "richmond_n_studies": pts.get("n_studies_stated"),
            "context_recovered": ctx_hit,
            "context_matched_to": per.get(ctx, {}).get("concept") or None,
            "interventions": {"recovered": i_n, "expected": i_d},
            "mechanism_responses": {"recovered": m_n, "expected": m_d},
            "outcomes": {"recovered": o_n, "expected": o_d},
            "verdict": verdict,
            "our_sections_carrying_it": carried_by[:3],
        })

    tally: dict[str, int] = {}
    for r in rows:
        tally[r["verdict"]] = tally.get(r["verdict"], 0) + 1
    return {
        "computed_from": {"gold": gold.get("schema_version", "v3"), "verification_run": run_id,
                          "system_sections": len(sections),
                          "matcher_corrections_applied": sorted(REFUSED_BY_MATCHER_FIX)},
        "rule": ("reproduced = context recovered AND >=50% of each of interventions, "
                 "mechanism-responses and outcomes; 'chain without context' = the chain "
                 "meets that bar but Richmond's context label was not recovered; partial = "
                 "context recovered, chain only in part; corpus gap = neither"),
        "tally": tally,
        "statements": rows,
    }
