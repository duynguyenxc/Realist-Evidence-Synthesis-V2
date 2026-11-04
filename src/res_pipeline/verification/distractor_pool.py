"""Build a distractor pool and run the screening precision/specificity test.

Richmond assessed 149 full texts and included 28; the 121 excluded records would be
the ideal distractors but are not published. To test whether the screening agent is
DISCRIMINATING (rejects irrelevant papers) rather than merely sensitive (recall on
the 28), this module assembles a controlled distractor pool from Europe PMC — real
papers that are topically adjacent to clinical-reasoning education but violate a
KNOWN eligibility criterion, so "correct rejection" is well defined.

Distractor categories (each with the criterion it violates):
  * postgraduate     — residents/fellows (violates 'undergraduate' population)
  * non_reasoning    — medical education not about clinical reasoning (violates focus)
  * no_intervention  — descriptive/observational, no educational intervention
  * off_topic        — clearly outside scope (violates focus/population)

Ground truth: every distractor is expected 'exclude'. The screening agent runs on the
mixed pool (28 benchmark + distractors); we report recall on the 28 and specificity /
precision on the distractors. Caveat (reported, not hidden): a small number of
distractors may be genuinely eligible-but-missed-by-Richmond; flagged for human check.
"""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request

from res_pipeline.core.db import get_connection, log_audit_event
from res_pipeline.core.llm import call_structured
from res_pipeline.core.prompts import P
from res_pipeline.core.registry import StudyRecord
from res_pipeline.core.screening import ScreeningVote, _combine, _system_prompt, _user_prompt

_EPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest/search?"

# Query per category, restricted to Richmond's timeframe + having an abstract.
_CATEGORIES = {
    "postgraduate": 'clinical reasoning education residents postgraduate specialty training',
    "non_reasoning": 'undergraduate medical education anatomy OR professionalism OR communication skills teaching',
    "no_intervention": 'clinical reasoning assessment observational survey medical students',
    "off_topic": 'surgical outcomes randomized trial epidemiology hospital mortality',
}
_DATE_FILTER = ' AND (FIRST_PDATE:[2000-01-01 TO 2017-12-31]) AND (HAS_ABSTRACT:y) AND (LANG:eng)'


def _fetch(query: str, page_size: int = 25) -> list[dict]:
    url = _EPMC + urllib.parse.urlencode(
        {"query": query + _DATE_FILTER, "format": "json",
         "pageSize": page_size, "resultType": "core"}
    )
    with urllib.request.urlopen(url, timeout=45) as resp:  # noqa: S310 — fixed trusted host
        return json.load(resp)["resultList"]["result"]


def build_distractor_pool(per_category: int = 20) -> int:
    """Fetch distractors, dedup against the 28 benchmark studies, persist."""
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS distractor_studies (
                distractor_id TEXT PRIMARY KEY,
                title TEXT NOT NULL, year INT, doi TEXT, journal TEXT, abstract TEXT,
                category TEXT NOT NULL, expected_decision TEXT NOT NULL DEFAULT 'exclude',
                created_at TIMESTAMPTZ NOT NULL DEFAULT now());
            CREATE TABLE IF NOT EXISTS distractor_decisions (
                id BIGSERIAL PRIMARY KEY,
                distractor_id TEXT NOT NULL REFERENCES distractor_studies(distractor_id),
                decider TEXT NOT NULL, decision TEXT NOT NULL, rationale TEXT,
                run_id TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now());
            """
        )
        benchmark_dois = {r["doi"] for r in conn.execute(
            "SELECT lower(doi) AS doi FROM studies WHERE doi IS NOT NULL"
        ).fetchall()}
        benchmark_titles = {(r["title"] or "").lower()[:60] for r in conn.execute(
            "SELECT title FROM studies"
        ).fetchall()}

    seen_dois: set[str] = set()
    count = 0
    with get_connection() as conn:
        conn.execute("DELETE FROM distractor_decisions")
        conn.execute("DELETE FROM distractor_studies")
        for category, query in _CATEGORIES.items():
            for rec in _fetch(query, per_category + 10):
                doi = (rec.get("doi") or "").lower()
                title = (rec.get("title") or "").strip()
                if not title or not rec.get("abstractText"):
                    continue
                if doi and (doi in benchmark_dois or doi in seen_dois):
                    continue
                if title.lower()[:60] in benchmark_titles:
                    continue
                if doi:
                    seen_dois.add(doi)
                count += 1
                conn.execute(
                    "INSERT INTO distractor_studies (distractor_id, title, year, doi, "
                    "journal, abstract, category) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                    (f"D{count:03d}", title,
                     int(rec["pubYear"]) if rec.get("pubYear", "").isdigit() else None,
                     doi or None, rec.get("journalTitle"), rec.get("abstractText"), category),
                )
                # Stop this category once we have enough non-duplicate hits.
                if count % (per_category) == 0:
                    break
            time.sleep(0.5)
    log_audit_event("distractor-build", "distractor_pool", "pool_built",
                    detail={"n_distractors": count, "per_category": per_category})
    return count


def _screen_distractor(row: dict, run_id: str) -> str:
    """Run the same dual-model recall-first screener on one distractor."""
    pseudo = StudyRecord(
        study_id="S999", record_id=row["distractor_id"], doi=row["doi"],
        title=row["title"], authors=[], year=row["year"], journal=row["journal"],
        abstract=row["abstract"], source_kind="abstract_only", pdf_path=None,
        metadata_confidence=1.0,
    )
    system, user = _system_prompt(), _user_prompt(pseudo)
    primary = call_structured(tier="screening_primary", system_prompt=P("distractor_pool.1",
                system),
                              user_prompt=user, schema=ScreeningVote, run_id=run_id)
    second = call_structured(tier="screening_second_vote", system_prompt=P("distractor_pool.2",
                system),
                             user_prompt=user, schema=ScreeningVote, run_id=run_id)
    combined = _combine(primary, second)
    with get_connection() as conn:
        for decider, vote in (("primary", primary), ("second", second)):
            conn.execute(
                "INSERT INTO distractor_decisions (distractor_id, decider, decision, "
                "rationale, run_id) VALUES (%s,%s,%s,%s,%s)",
                (row["distractor_id"], decider, vote.decision, vote.rationale, run_id),
            )
        conn.execute(
            "INSERT INTO distractor_decisions (distractor_id, decider, decision, rationale, "
            "run_id) VALUES (%s,'combined',%s,%s,%s)",
            (row["distractor_id"], combined,
             f"union({primary.decision},{second.decision})", run_id),
        )
    return combined


def run_precision_test(run_id: str) -> dict:
    """Screen the distractor pool and compute precision/specificity vs the benchmark."""
    with get_connection() as conn:
        distractors = conn.execute(
            "SELECT distractor_id, title, year, doi, journal, abstract, category "
            "FROM distractor_studies ORDER BY distractor_id"
        ).fetchall()

    per_cat: dict[str, dict[str, int]] = {}
    for row in distractors:
        decision = _screen_distractor(dict(row), run_id)
        cat = per_cat.setdefault(row["category"], {"total": 0, "excluded": 0,
                                                    "included": 0, "uncertain": 0})
        cat["total"] += 1
        cat[{"exclude": "excluded", "include": "included",
             "uncertain": "uncertain"}[decision]] += 1

    n = len(distractors)
    excluded = sum(c["excluded"] for c in per_cat.values())
    included = sum(c["included"] for c in per_cat.values())
    uncertain = sum(c["uncertain"] for c in per_cat.values())

    # Benchmark recall (the 28 are all gold-includes).
    with get_connection() as conn:
        bench_included = conn.execute(
            "SELECT count(*) AS n FROM (SELECT DISTINCT ON (study_id) decision "
            "FROM screening_decisions WHERE decider LIKE 'combined:%' "
            "ORDER BY study_id, created_at DESC) t WHERE decision='include'"
        ).fetchone()["n"]

    tp = bench_included            # benchmark studies correctly included
    fp = included                  # distractors wrongly included
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    specificity = excluded / n if n else 0.0

    result = {
        "n_distractors": n,
        "distractor_excluded": excluded,
        "distractor_included": included,
        "distractor_uncertain": uncertain,
        "specificity": specificity,
        "benchmark_included": bench_included,
        "precision_proxy": precision,
        "per_category": per_cat,
        "caveat": "Distractors wrongly included may be genuinely eligible papers missed "
                  "by Richmond; each such case should be human-checked before being "
                  "counted as a false positive.",
    }
    log_audit_event(run_id, "precision_test", "precision_computed", detail=result)
    return result
