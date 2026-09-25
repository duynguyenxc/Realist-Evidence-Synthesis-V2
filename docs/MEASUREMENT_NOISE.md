# How noisy is our own measurement?

> Ten verification runs over **one frozen knowledge graph**. The pipeline did not change; only
> the judge ran again. This document reports what moved anyway, and what that means for every
> claim this project can make.
>
> Measured 2026-09-25 on graph `extract-fb045429` (547 entity instances, 94 CMOCs, 459
> relations). Reproduce with `res verify` ten times and aggregate the reports.

---

## 1. The result

| Metric | Range over 10 runs | SD | As percentage points |
|---|---|---|---|
| Concept coverage, same realist role (/46) | **31 – 37** | 1.96 | **13 pp spread** |
| Concept coverage, role-tolerant (/46) | **37 – 45** | 2.26 | **17 pp** |
| Relation, anchored (/40) | **24 – 31** | 2.31 | **17 pp** |
| Relation, strict (/40) | 4 – 7 | 0.97 | 8 pp |
| Emergent mechanisms (/28) | **16 – 21** | 1.32 | **18 pp** |
| Programme theory, independent judge | 0.79 – 0.87 | 0.024 | — |
| Programme theory, same-family judge | 0.48 – 0.53 | 0.015 | — |
| **Screening sensitivity** | **identical every run** | 0 | — |
| **Verbatim grounding (tier counts)** | **identical every run** | 0 | — |

The deterministic metrics returned byte-identical values ten times out of ten. Everything a
language model judged moved.

---

## 2. What it costs us

### 2.1 The framework cannot be shown to beat a single LLM call on concept coverage

| | Concepts matched (of 46) |
|---|---|
| One LLM call over the same 28 papers — no ontology, no per-study extraction, no span grounding, no graph, no checkpoints | **32** |
| The full pipeline, ten scorings of one graph | **31 – 37** (mean 33.5) |

**32 falls inside the pipeline's own range.** The difference we previously reported — 37 against
32 — was one draw from a distribution whose spread is wider than the difference itself. On this
metric the two are indistinguishable, and no amount of further tuning would change that, because
the measurement cannot resolve it.

This does **not** mean the pipeline contributes nothing. It means **concept coverage is the wrong
place to look for the contribution.** The single call produces no character-anchored quotes, no
per-study attribution, no typed relations, no algorithmically-derived mechanisms and no human
checkpoints — and those are differences in kind, not in degree, which no coverage statistic
measures.

### 2.2 The minimum difference a single comparison can detect

With SD ≈ 1.96 items, a one-run-per-arm comparison resolves a difference of roughly

> **7.8 items ≈ 17 percentage points.**

Replication tightens it as `SD/√K`:

| Replicates per arm | Smallest resolvable difference |
|---|---|
| 1 | 7.8 items (17 pp) |
| 3 | 4.5 items (10 pp) |
| 5 | 3.5 items (8 pp) |
| 10 | **2.5 items (5 pp)** |

Any intervention expected to move coverage by a few items must therefore be scored **at least
five times per arm**, or it cannot be evaluated at all. This is the operational form of the rule
that no change ships on a single before/after run.

### 2.3 The retraction this forces

An earlier report in this project claimed the HITL feedback loop reduced checker disagreement
from 77% to 50% on three studies. That claim is withdrawn twice over: the loop was not connected
at the time (an agent-key mismatch meant the few-shot block was always empty), **and** a
three-study sample cannot separate anything from noise of this size. The retraction is recorded
in `WALKTHROUGH.md` M35.

---

## 3. One thing that is *not* noise

| Judge | Mean | SD |
|---|---|---|
| Independent family (`gpt-4.1-mini`) | **0.827** | 0.024 |
| Composer's own family (`gpt-5.5`) | **0.508** | 0.015 |

The gap is **0.319 — thirteen times either standard deviation.** It is perfectly reproducible.

So the programme-theory score is not unstable; it is **judge-determined**. Which model grades the
theory decides the number, and the choice is not a detail of the evaluation — it *is* the
evaluation. Reporting either figure alone would be misleading, whichever one was chosen.

Note also that the direction runs opposite to self-preference: the *independent* judge is the
generous one. Judge family is confounded with judge capability here (a 4.1-mini against a 5.5),
so this cannot be read as evidence about bias. It is evidence that the measure needs a human
anchor.

---

## 4. What follows for the paper

1. **Report ranges, never point estimates**, for concept coverage, relation recovery and
   mechanism alignment — and state that the range is judge variance on a fixed graph, not
   pipeline variance.
2. **State the resolution limit.** "This design resolves differences of about 17 percentage
   points on a single comparison; smaller differences are reported descriptively and are not
   claimed." That sentence forecloses the most obvious line of attack.
3. **Do not claim superiority over the trivial baseline on coverage.** Claim what the baseline
   demonstrably cannot do, and show it: quotes with character offsets, per-study provenance, 459
   typed relations, eight algorithmically-derived mechanisms, four logged human checkpoints.
4. **Never quote one programme-theory number.** Report both judges and the gap.
5. **Lead with the deterministic metrics.** Screening and verbatim grounding reproduced exactly
   ten times out of ten. They are the numbers that carry no asterisk.

---

## 5. Why this is a contribution rather than an embarrassment

Very little published work using LLM judges measures the judge's own variance before reporting
differences against it. Doing so here changed four conclusions this project had already drawn —
including one it had reported as a success — and it is the reason the evaluation can now state
what it is and is not able to see.

The honest headline is not a score. It is: **we measured our own instrument, found it moves by up
to 18 percentage points with the system held constant, and report every model-judged figure
accordingly.**
