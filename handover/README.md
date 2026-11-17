# Handover — 17 November 2026

Deliverables 1, 2 and 6 of the assignment of 2026-10-30, the first half of deliverable 3,
and a clause-by-clause matrix of the assignment itself.

| | |
|---|---|
| [`0_REQUIREMENTS_MATRIX.md`](0_REQUIREMENTS_MATRIX.md) | **Start here.** Your email clause by clause, in your order, each with a status and the file that substantiates it — and four questions that need your decision |
| [`1_WHAT_WE_BUILT.md`](1_WHAT_WE_BUILT.md) | Then here. Where the project stands today, what the system does, where every item you listed lives, and what it cannot do |
| [`2_WHAT_THE_NEW_TOPIC_NEEDS.md`](2_WHAT_THE_NEW_TOPIC_NEEDS.md) | Your seven questions answered against code that exists, what the literature says about doing this with AI, and a step-by-step plan |
| [`6_PROGRESS_REPORT.md`](6_PROGRESS_REPORT.md) | Completed, limitations, next steps |
| [`pipeline.svg`](pipeline.svg) | The six stages and the five points where the system stops and asks a person |

**Generated outputs for the new topic** — all three are produced from the data by a script, not written, so they cannot drift from what the pipeline actually holds:

| | |
|---|---|
| [`outputs-emotion/SEARCH_REPORT.md`](../outputs-emotion/SEARCH_REPORT.md) | The search, reportable well enough to repeat: queries, coverage dates, deduplication, and a validity check registered before the search ran |
| [`outputs-emotion/EVIDENCE_MAP.md`](../outputs-emotion/EVIDENCE_MAP.md) | What the 1,863 records are *about*, coded against Pekrun's and Gross's categories. **Not** what works |
| [`outputs-emotion/COST_MODEL.md`](../outputs-emotion/COST_MODEL.md) | What each remaining stage would cost, from the real prompts and prices |

**Deliverable 3, first half: done.** The literature search for the new topic ran on 16 November
and cost nothing — **1,863 candidate records**, 89% with an abstract, 68% with a free open-access
PDF. `outputs-emotion/SEARCH_REPORT.md` reports it and is generated from the query log rather than
written. We had filed all of deliverable 3 as budget-blocked; three of the pipeline's stages call
no model, so half of it was not.

**Deliverables 4 and 5, and the second half of 3** — a screened evidence database, the extracted
CMOCs and knowledge graph, and the preliminary synthesis — need screening and extraction, which is
where the pipeline begins to spend API credit.

## Two findings you should see before anything else

**The 32 recurring patterns we have been reporting do not survive a test against chance.** A
permutation null model expects 32.3 by chance against 32 observed, and no individual pattern
survives correction for multiple testing. They are candidates for adjudication, not findings.

**The system reconstructs your causal chains but under-recovers your context labels.** Three of
your five programme-theory statements come back with the chain almost wholly recovered and the
population it applies to unnamed. A hand-written comparison had called one of those a corpus gap;
computed, its chain returns 3/3 interventions, 4/4 mechanism-responses and 5/5 outcomes.

Both were found in the past week by work that cost nothing, and both change what the paper may
claim. Neither would have surfaced from reading the earlier reports.

**And three from 17 November, all from the literature itself rather than from the system.**
The field has studied **anxiety** (578 of 678 emotion-tagged records) and left Pekrun's other
eight achievement emotions at the margins. **Three of the five interventions you named by
example are nearly absent** — self-regulation activities 7 records, emotional awareness prompts
6, learning plans 17 — while mindfulness, which you did not name, has 291. And **STEM is barely
served**: engineering, computing and the natural sciences account for 51 records between them.
Each of those changes what the review should be, so each is a question for you rather than a
decision we made. They are Questions 1–3 in the requirements matrix.

**And one from 16 November.** Checking the search code against the live catalogues before running
it found four defects, the worst of which would have silently dropped **Durlak et al. 2011 — a
reference you named by DOI** — because OpenAlex classifies it as a `review` and our default kept
only `article`. The search would have completed, looked entirely normal, and omitted it.

## On the figures

Some numbers here are **lower** than in reports sent before. That is deliberate: a defect in the
scoring code had been accepting matches whose own written rationale stated a non-match, and
recounting exposed a second arithmetic error. An earlier report also understated our own evidence
by saying only one of the two gold-standard coders was human. Both corrections are explained where
they appear, and the previously published value is printed beside each corrected one.

Every figure resolves to a table and row in `outputs/raw_export/`, which is the database exported
with nothing summarised.
