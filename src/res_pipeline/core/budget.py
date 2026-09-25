"""Spend accounting and the guard that stops a run before the balance does.

Three consecutive runs in September 2026 were killed by `insufficient_quota`, twice at the
same study. Each death happened mid-extraction, which is the expensive place to die: the
study being processed had already been cleared by `--refresh` but not yet rewritten, so
recovery cost a study on top of the money already spent.

`config/models.yaml` declared `budget.max_usd_per_full_run` from the first architecture
draft and left it `null` — the guard the design describes was never switched on. This module
switches it on. It estimates spend from `token_usage` (which the pipeline already writes) and
raises at a study boundary once the run passes `warn_fraction` of the budget, so the run ends
somewhere `res extract --resume` can pick up cheaply.

The estimate is not a bill. Provider pricing changes and the dashboard is authoritative; the
point is to stop early enough that the difference never matters.
"""

from __future__ import annotations

from res_pipeline.core.config import load_yaml_config
from res_pipeline.core.db import get_connection


class BudgetExceeded(RuntimeError):
    """Raised at a safe boundary when a run has spent its allowance."""


def _cfg() -> dict:
    return load_yaml_config("models")


def estimate_usd(prompt_tokens: int, cached_tokens: int, completion_tokens: int,
                 model: str) -> float:
    """Approximate cost of one call. Unknown models are priced at the most expensive tier.

    Cached input tokens are billed at a fraction of the input rate, so counting them at the
    full rate would overstate spend and halt a run early — which is its own kind of failure.
    """
    pricing = _cfg().get("pricing_usd_per_mtok", {})
    rates = pricing.get(model)
    if rates is None:
        rates = max(pricing.values(), key=lambda r: r.get("output", 0)) if pricing else {}
    fresh = max(prompt_tokens - cached_tokens, 0)
    raw = (
        fresh * rates.get("input", 0.0)
        + cached_tokens * rates.get("cached_input", rates.get("input", 0.0))
        + completion_tokens * rates.get("output", 0.0)
    ) / 1_000_000
    # List prices applied to our own counts under-report against the actual account; the
    # factor is pessimistic on purpose. See budget.cost_calibration_factor in models.yaml.
    return raw * _cfg().get("budget", {}).get("cost_calibration_factor", 1.0)


def run_spend_usd(run_id: str) -> float:
    """What this run has cost so far, from the usage rows it has already written."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT model, sum(prompt_tokens) AS p, sum(coalesce(cached_tokens, 0)) AS c, "
            "sum(completion_tokens) AS o FROM token_usage WHERE run_id = %s GROUP BY model",
            (run_id,),
        ).fetchall()
    return sum(estimate_usd(r["p"], r["c"], r["o"], r["model"]) for r in rows)


def budget_usd() -> float | None:
    return _cfg().get("budget", {}).get("max_usd_per_full_run")


def check(run_id: str, *, where: str = "") -> float:
    """Raise :class:`BudgetExceeded` if this run has spent its allowance.

    Call only at points where stopping is cheap — between studies, not inside one. Returns the
    spend so far so a caller can report progress.
    """
    spent = run_spend_usd(run_id)
    cap = budget_usd()
    if cap is None:
        return spent
    fraction = _cfg().get("budget", {}).get("warn_fraction", 0.9)
    if spent >= cap * fraction:
        raise BudgetExceeded(
            f"run {run_id} has spent an estimated ${spent:.2f} of its ${cap:.2f} budget"
            f"{' at ' + where if where else ''}. Stopping here so the run ends at a clean "
            f"boundary — resume with `res extract --resume {run_id}` after raising "
            f"budget.max_usd_per_full_run in config/models.yaml or topping up the account."
        )
    return spent


def preflight() -> tuple[bool, str]:
    """Is the API key funded? Costs one token, and answers before an hour of work does.

    A 429 with `insufficient_quota` at study 18 of 28 is the same information as a 429 now,
    bought an hour later and several dollars more expensively.
    """
    from res_pipeline.core.llm import _get_client

    try:
        _get_client().chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": "ok"}],
            max_tokens=1,
        )
        return True, "API key is funded."
    except Exception as exc:  # noqa: BLE001 — any failure here should stop the run
        text = str(exc)
        if "insufficient_quota" in text or "credit_balance_exhausted" in text:
            return False, "No API credit remaining — top up before starting a run."
        return False, f"Pre-flight API check failed: {text[:200]}"
