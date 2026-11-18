# Handover

Everything so far: the three documents you asked for, the first half of the literature
collection, and a matrix that goes through your email point by point so you can see at a
glance what is finished and what is not.

| | |
|---|---|
| [`0_REQUIREMENTS_MATRIX.md`](0_REQUIREMENTS_MATRIX.md) | **Start here.** Everything you asked for, in your order, each with a status and the file that backs it up — three scope decisions we took with the reasoning shown, and the one question that needs you |
| [`1_WHAT_WE_BUILT.md`](1_WHAT_WE_BUILT.md) | Then here. Where the project stands, what the system does, where every item you listed lives, and what it cannot do |
| [`2_WHAT_THE_NEW_TOPIC_NEEDS.md`](2_WHAT_THE_NEW_TOPIC_NEEDS.md) | Your seven questions answered against code that exists, what the literature says about doing this with AI, and a step-by-step plan |
| [`6_PROGRESS_REPORT.md`](6_PROGRESS_REPORT.md) | Completed, limitations, next steps |
| [`pipeline.svg`](pipeline.svg) | The six stages, and the five points where the system stops and asks a person |

Three more files report the new topic. All three are produced from the data by a script
rather than written by hand, so they cannot drift from what the pipeline actually holds:

| | |
|---|---|
| [`outputs-emotion/SEARCH_REPORT.md`](../outputs-emotion/SEARCH_REPORT.md) | The search, reported well enough to repeat: queries, coverage dates, deduplication, and a validity check registered before the search ran |
| [`outputs-emotion/EVIDENCE_MAP.md`](../outputs-emotion/EVIDENCE_MAP.md) | What the 1,863 records are *about*, coded against Pekrun's and Gross's categories. **Not** what works |
| [`outputs-emotion/COST_MODEL.md`](../outputs-emotion/COST_MODEL.md) | What each remaining stage would cost, from the real prompts and prices |
| [`outputs-emotion/ACQUISITION_REPORT.md`](../outputs-emotion/ACQUISITION_REPORT.md) | How many full texts we actually hold, why the rest could not be fetched, and what that constrains |

## Where things stand

The literature search for the new topic has been run, and it cost nothing: **1,863
candidate records**, 89% with an abstract, 68% with an open-access PDF link — of which 572
full texts were actually downloadable, for the reasons in `ACQUISITION_REPORT.md`. That is the
first half of your third output. We had reported all of outputs 3, 4 and 5 as needing
budget, and that was partly wrong — three of the pipeline's stages call no model at all.

What still needs budget is screening and extraction, and with them your outputs 4 and 5 and
the second half of 3: a screened evidence database, the extracted CMOCs and the knowledge
graph, and the preliminary synthesis. The cost is now calculated rather than guessed, and it
is smaller than we had assumed. `COST_MODEL.md` has the figures; the short version is that
screening the whole pool costs about $5.

## Five things worth seeing before anything else

Two of them are about our own system, and both lower what we are entitled to claim.

**The 32 recurring patterns we have been reporting do not survive a test against chance.** A
permutation null model expects 32.3 by chance against 32 observed, and no individual pattern
survives correction for multiple testing. They are candidates for adjudication rather than
findings.

**The system reconstructs your causal chains but under-recovers your context labels.** Three
of your five programme-theory statements come back with the chain almost wholly recovered
and the population it applies to unnamed. A hand-written comparison had called one of those
a corpus gap; computed, its chain returns 3/3 interventions, 4/4 mechanism-responses and 5/5
outcomes.

Three are about the literature rather than about us, and each one bears on what the review
should be.

**The field has studied anxiety and left the rest of the taxonomy alone.** Of 678 records
carrying an achievement-emotion tag, 578 mention anxiety. Pekrun's other eight emotions sit
between 11 and 79 — boredom, the emotion that arises during learning rather than about its
result, appears 68 times.

**Three of the five interventions you named by example are nearly absent**: self-regulation
activities 7 records, emotional awareness prompts 6, learning plans 17. Mindfulness, which
you did not name, has 291. We widened the dictionary deliberately to test whether the
near-zeros were our own fault, and they survived it.

**STEM is barely served.** Engineering, computing and the natural sciences account for 51
records between them, fewer than the 93 that are explicitly outside STEM. Mathematics has
108, and it is almost all maths and statistics anxiety.

Those last three were questions rather than conclusions. They are now **Decisions 1 to 3**
in the requirements matrix: each is taken, with the evidence, the reasoning, and the
threshold that would reverse it. Your email asks us to exercise judgment on routine
decisions and document them, and on reflection these were answerable from the pool rather
than things to hand back.

## One near miss worth knowing about

Before running the search we checked the code against the live catalogues, which turned up
four defects. The worst would have silently dropped **Durlak et al. 2011 — one of the four
references you gave us** — because OpenAlex classifies it as a `review` and our default kept
only `article`. The search would have completed, looked entirely normal, and omitted it. The
progress report lists all four.

## On the figures

Some numbers here are **lower** than in reports sent before. That is deliberate. A defect in
the scoring code had been accepting matches whose own written rationale stated a non-match,
and recounting exposed a second arithmetic error on top of it. An earlier report also
understated our own evidence, by saying that only one of the two gold-standard coders was
human when both were. Both corrections are explained where they appear, and the previously
published value is printed beside each corrected one.

Every figure resolves to a table and a row in `outputs/raw_export/`, which is the database
exported with nothing summarised.
