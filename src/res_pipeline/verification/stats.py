"""Interval estimates for the verification metrics.

A bare proportion — "39 of 40", "26 of 28" — tells a reviewer nothing about how much
of it is sampling accident. Every count-based metric in this harness is a proportion
over a small denominator (28 studies, 40 relations, 46 concepts), which is exactly the
regime where the Wald interval misbehaves: it produces zero-width intervals at 0/40 and
28/28, and overshoots [0, 1] near the boundaries.

We therefore use the **Clopper-Pearson exact interval** (Clopper & Pearson, 1934,
*Biometrika* 26(4), 404-413) for every proportion reported here. It is conservative —
coverage is at least the nominal level, never below — and it is well defined at p = 0
and p = 1, which matters because two of our headline numbers sit exactly there
(screening 28/28 after adjudication, strict relation recall 0/40). Brown, Cai &
DasGupta (2001, *Statistical Science* 16(2), 101-133) recommend Wilson or Agresti-Coull
for larger denominators; at our sizes the difference is small and being conservative is
the defensible direction, so one method is used throughout for comparability.

What the interval does and does not cover: it quantifies sampling variation in the
*counting*, given the benchmark. It says nothing about whether the benchmark itself is
right, and nothing about judge variance in the model-judged metrics — that is reported
separately as the per-sample range across K judge samples.
"""

from __future__ import annotations

from scipy.stats import beta


def clopper_pearson(successes: int, total: int, confidence: float = 0.95) -> dict:
    """Exact binomial confidence interval for `successes` out of `total`.

    Returns the point estimate with its interval, plus the strings a report can print
    directly. At 0 successes the lower bound is 0; at `total` successes the upper bound
    is 1 — both correct, and both a reason to prefer this method over Wald here.
    """
    if total <= 0:
        return {"successes": successes, "total": total, "proportion": None,
                "ci_low": None, "ci_high": None, "confidence": confidence,
                "method": "clopper-pearson", "display": "n/a"}

    alpha = 1.0 - confidence
    low = 0.0 if successes == 0 else beta.ppf(alpha / 2, successes, total - successes + 1)
    high = 1.0 if successes == total else beta.ppf(
        1 - alpha / 2, successes + 1, total - successes
    )
    point = successes / total
    return {
        "successes": successes,
        "total": total,
        "proportion": round(point, 4),
        "ci_low": round(float(low), 4),
        "ci_high": round(float(high), 4),
        "confidence": confidence,
        "method": "clopper-pearson",
        "display": f"{point:.1%} (95% CI {low:.1%}–{high:.1%}; {successes}/{total})",
    }


def describe(successes: int, total: int) -> str:
    """One-line human-readable form, for report prose."""
    return clopper_pearson(successes, total)["display"]
