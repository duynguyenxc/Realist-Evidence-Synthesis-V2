"""Is a demi-regularity a real pattern, or what a graph this shape produces by chance?

``find_demi_regularities`` calls a motif real when it appears in two or more studies.
Two is a threshold somebody chose; nothing in the pipeline has ever asked how many
(context, driver, outcome, polarity) motifs would reach two studies by chance given the
concepts the corpus happens to contain. Reporting "32 recurring patterns" without that
number is reporting a count, not a finding — and a realist review's demi-regularities are
the finding.

**Method.** The standard answer to exactly this question is a degree-preserving null
model: randomise the network while holding fixed everything that is not the hypothesis,
then see how often the observed structure survives (Milo et al., *Science* 298:824-827,
2002, "Network motifs: simple building blocks of complex networks"; Maslov & Sneppen,
*Science* 296:910-913, 2002).

Here the structure is tripartite — each CMOC carries a set of contexts, a set of drivers
and a set of outcomes — so the shuffle redeals concepts within each role, holding constant:

* how many contexts / drivers / outcomes each CMOC has;
* how often each concept is used in each role across the corpus;
* which study each CMOC belongs to, and its polarity.

What it destroys is the only thing left: **which concepts co-occur in the same CMOC.**
That is precisely the claim a demi-regularity makes, so the null is the right one.

**Reading the output.** ``p_empirical`` is the fraction of permutations in which this exact
motif reached at least its observed study count. ``q_value`` is that p after
Benjamini-Hochberg correction, which matters because dozens of motifs are tested at once
and roughly one in twenty would clear p < 0.05 on noise alone.

Deterministic given ``seed``, pure computation, no model call and no API cost.
"""

from __future__ import annotations

import random
from collections import Counter, defaultdict

from res_pipeline.plugins.realist.synthesis import _cmoc_concept_rows, find_demi_regularities


def _motif_study_counts(rows: list[dict]) -> dict[tuple, set[str]]:
    """Every (context, driver, outcome, polarity) motif -> the studies containing it."""
    out: dict[tuple, set[str]] = defaultdict(set)
    for row in rows:
        for ctx in row["contexts"] or []:
            for drv in row["drivers"] or []:
                for outc in row["outcomes"] or []:
                    out[(ctx, drv, outc, row["polarity"])].add(row["study_id"])
    return out


def _shuffled(rows: list[dict], rng: random.Random) -> list[dict]:
    """Redeal concepts within each role, preserving every marginal except co-occurrence."""
    pools = {role: [] for role in ("contexts", "drivers", "outcomes")}
    for row in rows:
        for role in pools:
            pools[role].extend(row[role] or [])
    for role in pools:
        rng.shuffle(pools[role])

    new_rows = []
    for row in rows:
        new = {"cmoc_id": row["cmoc_id"], "study_id": row["study_id"],
               "polarity": row["polarity"]}
        for role in pools:
            k = len(row[role] or [])
            # A CMOC cannot list the same concept twice in one role, so deal DISTINCT
            # values — but a duplicate drawn from the pool is set aside and returned,
            # never consumed. An earlier version advanced past duplicates permanently,
            # which starved later CMOCs and shrank the pool: the marginals the null is
            # supposed to hold fixed were not held fixed, and the null came out weaker
            # than the data it was modelling. Caught by
            # test_null_model_preserves_every_marginal_except_co_occurrence.
            pool, taken, held = pools[role], [], []
            while len(taken) < k and pool:
                v = pool.pop()
                (taken if v not in taken else held).append(v)
            pool.extend(held)
            rng.shuffle(pool)
            new[role] = taken
        new_rows.append(new)
    return new_rows


def _shuffled_within_study(rows: list[dict], rng: random.Random) -> list[dict]:
    """The stricter null: redeal concepts only among the CMOCs of the SAME study.

    The global shuffle lets a concept move between studies, so it also destroys the fact
    that a study about ECG interpretation talks about ECG concepts. That is not the
    hypothesis under test and keeping it makes the test harder to pass, so this variant
    holds each study's own vocabulary fixed and breaks only which concepts are bundled
    into the same configuration. A motif surviving BOTH nulls is the strong case.
    """
    by_study: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_study[row["study_id"]].append(row)
    out = []
    for study_rows in by_study.values():
        out.extend(_shuffled(study_rows, rng))
    return out


def motif_null_test(n_permutations: int = 1000, seed: int = 42,
                    min_studies: int = 2, within_study: bool = False) -> dict:
    """Test every reported demi-regularity against a degree-preserving null model."""
    shuffle = _shuffled_within_study if within_study else _shuffled
    rows = _cmoc_concept_rows()
    observed = find_demi_regularities(min_studies=min_studies)
    obs_counts = {(m.context_concept, m.driver_concept, m.outcome_concept, m.polarity):
                  len(m.study_ids) for m in observed}

    rng = random.Random(seed)
    at_least: Counter[tuple] = Counter()        # permutations reaching the observed count
    null_totals: list[int] = []                 # how many motifs clear the threshold at all
    for _ in range(n_permutations):
        shuffled = _motif_study_counts(shuffle(rows, rng))
        null_totals.append(sum(1 for s in shuffled.values() if len(s) >= min_studies))
        for key, obs in obs_counts.items():
            if len(shuffled.get(key, ())) >= obs:
                at_least[key] += 1

    # Benjamini-Hochberg: dozens of simultaneous tests, so the raw p is not the answer.
    ranked = sorted(obs_counts, key=lambda k: (at_least[k] + 1) / (n_permutations + 1))
    m = len(ranked)
    q_of, running = {}, 1.0
    for i in range(m - 1, -1, -1):
        key = ranked[i]
        p = (at_least[key] + 1) / (n_permutations + 1)
        running = min(running, p * m / (i + 1))
        q_of[key] = running

    results = []
    for key, obs in sorted(obs_counts.items(), key=lambda kv: -kv[1]):
        p = (at_least[key] + 1) / (n_permutations + 1)
        results.append({
            "context": key[0], "driver": key[1], "outcome": key[2], "polarity": key[3],
            "studies_observed": obs,
            "permutations_matching_or_exceeding": at_least[key],
            "p_empirical": round(p, 4),
            "q_value": round(q_of[key], 4),
            "survives_q05": q_of[key] < 0.05,
        })

    mean_null = sum(null_totals) / len(null_totals) if null_totals else 0.0
    return {
        "null": "within-study" if within_study else "global",
        "method": ("degree-preserving permutation null (Milo et al. 2002); concepts redealt "
                   + ("among the CMOCs of the same study" if within_study
                      else "across the whole corpus")
                   + ", preserving per-CMOC cardinality, per-concept role frequency, study "
                     "membership and polarity"),
        "permutations": n_permutations,
        "seed": seed,
        "min_studies": min_studies,
        "observed_motifs": len(observed),
        "null_motifs_mean": round(mean_null, 1),
        "null_motifs_min": min(null_totals) if null_totals else 0,
        "null_motifs_max": max(null_totals) if null_totals else 0,
        "surviving_q05": sum(1 for r in results if r["survives_q05"]),
        "motifs": results,
    }
