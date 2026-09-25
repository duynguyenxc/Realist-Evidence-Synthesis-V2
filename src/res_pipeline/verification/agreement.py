"""Inter-coder agreement between two human coders.

This computes the number the project has been missing: what two trained people agree on when
they read the same papers. Until it exists, every machine-vs-Richmond agreement figure is
uninterpretable, because there is no human ceiling to read it against — a machine at κ = 0.61
looks like a success until you learn the two experts reached κ = 0.88 on the same items
(Xiao et al., IUI 2023).

**Why not Cohen's κ for the extraction layer.** κ needs a fixed number of opportunities, so
that "both coders agreed this is not X" is countable. When coders mark spans of text there is
no defined set of negatives, and κ is undefined. Hripcsak & Rothschild (*JAMIA* 12(3):296-298,
2005) prove that in exactly this situation the mean F-measure between coder pairs equals
**positive specific agreement**, and that this is the correct reliability statistic. So the
element layer is scored with positive specific agreement, and κ-family statistics are used only
for the **role** assignment, where the category set genuinely is fixed.

**Why two coefficients for the role layer.** Realist roles are unevenly distributed, and κ
behaves badly at skewed prevalence — the well-documented "high agreement, low kappa" paradox
(Feinstein & Cicchetti, *J Clin Epidemiol* 43:543-549, 1990). Krippendorff's α is reported for
its tolerance of missing data, and Gwet's AC1 (*Br J Math Stat Psychol* 61:29-48, 2008) beside
it because it is robust where κ is not.
"""

from __future__ import annotations

import itertools
from collections import Counter
from pathlib import Path
from typing import Any

ELEMENT_COLUMNS = ("cmoc", "element_type", "ecode", "label", "quote", "page", "polarity")
ROLES = ("Context", "Intervention", "Mechanism_Resource", "Mechanism_Response", "Outcome")


def read_workbook(path: Path) -> dict[str, list[dict[str, Any]]]:
    """Read one coder's workbook into {study_id: [row, ...]}.

    Only the per-study sheets are read; the instruction and reference sheets are skipped by
    name, so a coder adding notes to them cannot corrupt the parse.
    """
    from openpyxl import load_workbook

    skip = {"Instructions", "E-code reference", "R-code reference", "Model candidates"}
    wb = load_workbook(path, data_only=True)
    out: dict[str, list[dict[str, Any]]] = {}
    for name in wb.sheetnames:
        if name in skip:
            continue
        ws = wb[name]
        rows = []
        for r in ws.iter_rows(min_row=4, values_only=True):
            values = list(r[: len(ELEMENT_COLUMNS)])
            values += [None] * (len(ELEMENT_COLUMNS) - len(values))
            row = dict(zip(ELEMENT_COLUMNS, values))
            # A row counts as coded when it names an element type and says something about it.
            if row["element_type"] and (row["label"] or row["ecode"]):
                rows.append(row)
        if rows:
            out[name] = rows
    return out


def _key(row: dict[str, Any]) -> tuple[str, str]:
    """What counts as 'the same element' across two coders.

    Two coders will not phrase a label identically, so matching on the label would measure
    wording. Matching on (element type, E-code) measures the judgement the coding frame asks
    for. Rows coded 'NEW' are keyed by a normalised label instead, since no E-code exists.
    """
    etype = str(row["element_type"]).strip()
    code = str(row["ecode"] or "").strip().upper()
    if code and code != "NEW":
        return etype, code
    return etype, " ".join(str(row["label"] or "").lower().split())[:60]


def positive_specific_agreement(a: dict[str, list[dict]], b: dict[str, list[dict]]) -> dict:
    """Agreement on *which elements exist*, per Hripcsak & Rothschild (2005).

    PSA = 2|A ∩ B| / (|A| + |B|), which is the F-measure between the two coders and is what κ
    would converge to if the negatives were countable. Reported overall and per study, because
    a mean over papers hides the paper where the two coders read entirely different stories.
    """
    per_study, both_total, a_total, b_total = {}, 0, 0, 0
    for study in sorted(set(a) | set(b)):
        ka = Counter(_key(r) for r in a.get(study, []))
        kb = Counter(_key(r) for r in b.get(study, []))
        shared = sum((ka & kb).values())
        na, nb = sum(ka.values()), sum(kb.values())
        per_study[study] = {
            "coder_a": na, "coder_b": nb, "agreed": shared,
            "psa": round(2 * shared / (na + nb), 3) if (na + nb) else None,
        }
        both_total, a_total, b_total = both_total + shared, a_total + na, b_total + nb
    overall = 2 * both_total / (a_total + b_total) if (a_total + b_total) else None
    return {
        "statistic": "positive specific agreement (= mean pairwise F-measure)",
        "why": "Cohen's kappa is undefined for span marking — no fixed count of negatives "
               "(Hripcsak & Rothschild, JAMIA 2005).",
        "overall": round(overall, 3) if overall is not None else None,
        "elements_coder_a": a_total, "elements_coder_b": b_total, "elements_agreed": both_total,
        "per_study": per_study,
    }


def _chance_corrected(pairs: list[tuple[str, str]]) -> dict:
    """Krippendorff's α and Gwet's AC1 over aligned categorical judgements."""
    if not pairs:
        return {"n": 0, "percent_agreement": None, "krippendorff_alpha": None, "gwet_ac1": None}
    n = len(pairs)
    observed = sum(x == y for x, y in pairs) / n
    cats = sorted({c for pair in pairs for c in pair})

    # Krippendorff's alpha for nominal data with two coders: 1 - (1 - Ao)/(1 - Ae),
    # with Ae from the pooled marginal distribution and the small-sample correction.
    pooled = Counter(itertools.chain.from_iterable(pairs))
    total = 2 * n
    ae = sum(c * (c - 1) for c in pooled.values()) / (total * (total - 1)) if total > 1 else 0.0
    alpha = 1 - (1 - observed) / (1 - ae) if ae != 1 else 1.0

    # Gwet's AC1: chance agreement from the mean marginal, which does not collapse when one
    # category dominates — the case where kappa misbehaves.
    q = len(cats)
    pis = {c: pooled[c] / total for c in cats}
    ae_gwet = sum(p * (1 - p) for p in pis.values()) / (q - 1) if q > 1 else 0.0
    ac1 = (observed - ae_gwet) / (1 - ae_gwet) if ae_gwet != 1 else 1.0

    return {
        "n": n,
        "percent_agreement": round(observed, 3),
        "krippendorff_alpha": round(alpha, 3),
        "gwet_ac1": round(ac1, 3),
        "interpretation": ("alpha >= .800 firm; .667-.800 tentative only; below .667 unreliable "
                           "(Krippendorff). Report AC1 alongside because realist roles are "
                           "unevenly distributed and kappa-family statistics behave badly there."),
    }


def role_agreement(a: dict[str, list[dict]], b: dict[str, list[dict]]) -> dict:
    """Agreement on the *role* assigned, over elements both coders identified.

    Restricted to elements both found, because a role disagreement is only meaningful when both
    coders saw the same thing. Elements only one coder found are an existence disagreement and
    belong to positive specific agreement, not here.
    """
    pairs: list[tuple[str, str]] = []
    confusion: Counter[tuple[str, str]] = Counter()
    for study in sorted(set(a) | set(b)):
        by_code_a: dict[str, str] = {}
        for r in a.get(study, []):
            code = str(r["ecode"] or "").strip().upper()
            if code and code != "NEW":
                by_code_a[code] = str(r["element_type"]).strip()
        for r in b.get(study, []):
            code = str(r["ecode"] or "").strip().upper()
            if code and code != "NEW" and code in by_code_a:
                pair = (by_code_a[code], str(r["element_type"]).strip())
                pairs.append(pair)
                confusion[pair] += 1
    result = _chance_corrected(pairs)
    result["confusion"] = {f"{x} -> {y}": n for (x, y), n in confusion.most_common() if x != y}
    return result


def compare(path_a: Path, path_b: Path) -> dict:
    a, b = read_workbook(path_a), read_workbook(path_b)
    shared = sorted(set(a) & set(b))
    return {
        "coder_a_file": str(path_a), "coder_b_file": str(path_b),
        "studies_coded_by_both": shared,
        "studies_only_a": sorted(set(a) - set(b)),
        "studies_only_b": sorted(set(b) - set(a)),
        "element_agreement": positive_specific_agreement(a, b),
        "role_agreement": role_agreement(a, b),
    }
