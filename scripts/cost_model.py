#!/usr/bin/env python3
"""Project what the paid stages would cost, from the real prompts and the real corpus.

WHY THIS EXISTS
---------------
`handover/6_PROGRESS_REPORT.md` has carried this limitation since it was written:

    "No cost history. The usage records were lost in a database restore, so a new run's
     cost can be measured but not estimated."

Half of that is true and half was never checked. The `token_usage` table is indeed empty
(M39), so there is no *history*. But a projection does not need history: it needs the
prompt that will be sent, the text it will be sent about, and the provider's prices. All
three are in the repository — `core/screening.py` renders the system prompt from the
active protocol, the corpus is on disk, and `config/models.yaml` carries per-million-token
prices and the tier assignments. So the limitation was partly a matter of nobody having
done the arithmetic.

This turns "we have no budget" into "this is what each stage costs", which is the only
form in which a budget question can be answered.

HOW HONEST IT IS
----------------
- Tokens are estimated at **4 characters per token**, the usual English approximation. No
  tokeniser is installed and adding a dependency to improve a projection by a few percent
  is not worth it. Stated, not hidden.
- **No prompt caching is assumed.** The system prompt is re-sent per record, which is what
  the code does today. Caching it would cut the screening input cost by roughly the
  prompt's share, and `models.yaml` already lists cached-input prices, so the projection is
  an upper bound on that dimension.
- Output length is **assumed**, not measured, because nothing has been run on this corpus.
  The assumption is printed next to every figure that depends on it.
- Every total is multiplied by the project's own `cost_calibration_factor`, which
  `config/models.yaml` sets to 2.0 with this reason: summed over all history, list prices
  gave $26 where the account had spent appreciably more. **An over-estimate stops a run
  early, which is recoverable; an under-estimate ran the balance out mid-extraction three
  times in September 2026.** The raw figure is shown beside the calibrated one.
- The extraction projection also reports the **observed** Richmond rate, because a measured
  number from a comparable run beats a model of one. Where the two disagree, the report
  says so instead of choosing.

USAGE
-----
    export RES_CONFIG_DIR=config-emotion RES_DATA_DIR=data-emotion \\
           RES_OUTPUTS_DIR=outputs-emotion POSTGRES_DB=realist_emotion
    python scripts/cost_model.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

CHARS_PER_TOKEN = 4
ASSUMED_SCREEN_OUTPUT_TOKENS = 150     # decision + confidence + a short rationale
RICHMOND_OBSERVED_USD = (35.0, 45.0)   # config/models.yaml: "~$35-45 observed" for 28 papers
RICHMOND_PAPERS = 28


def _tok(chars: int) -> float:
    return chars / CHARS_PER_TOKEN


def main() -> int:
    import yaml

    from res_pipeline.core.config import CONFIG_DIR, DATA_DIR, OUTPUTS_DIR, PROJECT_ROOT as PR
    from res_pipeline.core.screening import _system_prompt

    models = yaml.safe_load((PR / "config" / "models.yaml").read_text(encoding="utf-8"))
    price = models["pricing_usd_per_mtok"]
    tiers = models["tiers"]
    budget = models["budget"]
    factor = float(budget.get("cost_calibration_factor", 1.0))
    ceiling = float(budget.get("max_usd_per_full_run", 0))

    pool = [json.loads(ln) for ln in
            (DATA_DIR / "studies_metadata.jsonl").read_text(encoding="utf-8").splitlines() if ln.strip()]
    n = len(pool)

    sys_prompt = _system_prompt()           # rendered from the ACTIVE protocol
    sys_tok = _tok(len(sys_prompt))
    rec_chars = sum(len(r.get("title") or "") + len(r.get("abstract") or "") + 120 for r in pool)

    def screen_cost(count: int) -> tuple[float, dict]:
        share = count / n
        inp = _tok(rec_chars) * share + count * sys_tok
        out = count * ASSUMED_SCREEN_OUTPUT_TOKENS
        per = {}
        total = 0.0
        for tier in ("screening_primary", "screening_second_vote"):
            m = tiers[tier]["model"]
            c = inp / 1e6 * price[m]["input"] + out / 1e6 * price[m]["output"]
            per[f"{tier} ({m})"] = c
            total += c
        return total, per

    L: list[str] = []
    w = L.append
    w("# What the paid stages would cost")
    w("")
    w(f"Generated {datetime.now(timezone.utc):%Y-%m-%d %H:%M UTC} by `scripts/cost_model.py` "
      "from the system prompt the pipeline actually renders, the corpus on disk, and the "
      "prices in `config/models.yaml`. Nothing was run and nothing was spent to produce this.")
    w("")
    w("## Why this file exists")
    w("")
    w("The progress report has carried the limitation *\"no cost history, so a new run's cost "
      "can be measured but not estimated\"*. The first half is true — the `token_usage` table "
      "was emptied by a database restore. The second half was never checked: a projection "
      "needs the prompt, the text and the prices, and all three are in the repository. "
      "**The limitation was partly arithmetic nobody had done.**")
    w("")
    w("## The three numbers everything rests on")
    w("")
    w("| | |")
    w("|---|---|")
    w(f"| Records in the pool | **{n}** |")
    w(f"| System prompt, rendered from `{CONFIG_DIR.name}/protocol.yaml` | **{len(sys_prompt):,} "
      f"characters ≈ {sys_tok:,.0f} tokens**, re-sent per record |")
    w(f"| Titles + abstracts in the pool | **{rec_chars:,} characters ≈ {_tok(rec_chars) / 1e6:.2f}M tokens** |")
    w("")
    w(f"Tokens are estimated at {CHARS_PER_TOKEN} characters each; no tokeniser is installed. "
      f"Output is assumed at {ASSUMED_SCREEN_OUTPUT_TOKENS} tokens per screening decision. "
      "No prompt caching is assumed, although the code re-sends an identical system prompt "
      f"{n} times and `models.yaml` prices cached input at a tenth — so the screening figures "
      "below are an upper bound that a caching change would cut substantially.")
    w("")
    w("## Screening")
    w("")
    w("Dual-model vote, recall-first: every record is read by both tiers and any *include* "
      "wins. Both are cheap tiers, deliberately.")
    w("")
    w("| Scenario | Records | Raw | ×%.1f calibration | Verdict |".replace("%.1f", f"{factor:.1f}"))
    w("|---|---|---|---|---|")
    scenarios = [
        ("Whole pool", n, "the full search, screened"),
        ("Higher-education records only", None, "if the scope narrows to HE"),
        ("Top 200 by dictionary relevance", 200, "a focused first round"),
        ("The 32 records touching all four roles", 32, "mechanism-first pilot"),
    ]
    # Reuse the evidence map's matcher rather than rewriting it. A first version of this
    # file compiled its own patterns and reported 307 higher-education records where the
    # evidence map reported 1,088 -- two files disagreeing about one number, which is the
    # failure this project has already had once in its figures. One definition, imported.
    he_count = None
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from evidence_map import _compile  # noqa: PLC0415

        he_terms = yaml.safe_load((CONFIG_DIR / "coding_frame.yaml").read_text(
            encoding="utf-8"))["settings"]["higher_education"]["terms"]
        pats = _compile(he_terms)
        he_count = sum(1 for r in pool
                       if any(pat.search(f"{r.get('title') or ''} \n {r.get('abstract') or ''}")
                              for _term, pat in pats))
    except Exception as exc:  # noqa: BLE001 - a missing scenario row is not worth failing over
        print(f"  (higher-education scenario skipped: {exc})", file=sys.stderr)
        he_count = None
    for name, count, note in scenarios:
        if count is None:
            count = he_count
            if count is None:
                continue
        total, _per = screen_cost(count)
        w(f"| {name} | {count} | ${total:.2f} | **${total * factor:.2f}** | {note} |")
    w("")
    total_all, per_all = screen_cost(n)
    w("Per tier, whole pool, before calibration: " +
      "; ".join(f"{k} **${v:.2f}**" for k, v in per_all.items()) + ".")
    w("")
    w(f"**Screening the entire pool costs about ${total_all * factor:.2f}.** That is the single "
      "most consequential number in this file, because the project has been treating screening "
      f"as budget-blocked alongside extraction. The ${ceiling:.0f} ceiling in `models.yaml` is "
      f"for EXTRACTING {RICHMOND_PAPERS} full papers — a different stage with a different model "
      "tier and roughly a hundred times the text per study.")
    w("")
    w("## Extraction")
    w("")
    w("Extraction cannot be projected the same way: it reads full texts, which have not been "
      "downloaded, and it makes several calls per study — chunked extraction, a verifier pass, "
      "normalisation and synthesis. Modelling that from abstracts would be a guess dressed as "
      "arithmetic. So the figure below is **observed, from the Richmond run**, which used the "
      "same tiers on comparable papers.")
    w("")
    lo, hi = RICHMOND_OBSERVED_USD
    w(f"| | |")
    w(f"|---|---|")
    w(f"| Richmond: {RICHMOND_PAPERS} papers, end to end | **${lo:.0f}–${hi:.0f}** "
      "(`models.yaml`: \"~$35-45 observed\") |")
    w(f"| Implied per paper | **${lo / RICHMOND_PAPERS:.2f}–${hi / RICHMOND_PAPERS:.2f}** |")
    w("")
    w("| Pilot size | Projected extraction | Why that size |")
    w("|---|---|---|")
    for k, why in ((3, "`pilot_paper_count` in `models.yaml`"),
                   (10, "enough to see whether CMOCs are coherent"),
                   (32, "every record touching all four roles"),
                   (RICHMOND_PAPERS, "a Richmond-sized run, for comparability")):
        w(f"| {k} papers | **${lo / RICHMOND_PAPERS * k:.0f}–${hi / RICHMOND_PAPERS * k:.0f}** | {why} |")
    w("")
    w("These are **not** calibrated upward: they are already an observation of real spend, and "
      "multiplying an observation by a factor meant for list-price estimates would double-count "
      "the correction.")
    w("")
    w("## What a decision actually costs")
    w("")
    screen_all, _ = screen_cost(n)
    w("| Package | Cost | What you get |")
    w("|---|---|---|")
    w(f"| Screen the whole pool | **${screen_all * factor:.2f}** | Every record judged against the "
      "protocol by two models, uncertain cases queued for a human. Turns 1,863 candidates into "
      "an included corpus — the professor's deliverable 3, second half |")
    w(f"| Screen + 3-paper pilot extraction | **${screen_all * factor + hi / RICHMOND_PAPERS * 3:.0f}** "
      "| The above, plus the first CMOCs on this topic and a measured per-paper cost to replace "
      "every estimate in this file |")
    w(f"| Screen + 10-paper pilot | **${screen_all * factor + hi / RICHMOND_PAPERS * 10:.0f}** | "
      "Enough configurations to see whether a programme theory is forming — deliverables 4 and 5 "
      "in preliminary form |")
    w(f"| Screen + all 32 four-role records | **${screen_all * factor + hi / RICHMOND_PAPERS * 32:.0f}** "
      "| A defensible small realist review on its own terms |")
    w("")
    w("## What would make these numbers real")
    w("")
    w("One stage, run once, with the provider dashboard read afterwards. `models.yaml` says so "
      "itself: *\"TO CALIBRATE: run one stage, read the true cost from the dashboard, set factor "
      "= true/estimate.\"* A 3-paper pilot costs a few dollars and replaces every projection here "
      "with a measurement — which is why it is the first paid step in the plan and not the last.")
    w("")

    out = OUTPUTS_DIR / "COST_MODEL.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"{len(L)} lines -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
