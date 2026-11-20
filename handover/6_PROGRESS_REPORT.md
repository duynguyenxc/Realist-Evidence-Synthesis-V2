# Progress report

## The short version

Three of the six outputs are finished and attached: the documentation of the existing
pipeline, the assessment of what the new topic needs, and this report.

The literature search has also been run, at no cost. We have 1,863 studies that may be
relevant and the full text of 662 of them. That is the collection half of the literature
output you asked for; what is missing is deciding which studies are eligible.

That decision is the first step that sends text to the AI model, so it costs money. There
is no budget, so it has not been run. The same blocks the extracted CMOCs, the knowledge
graph and the preliminary synthesis.

Most of these three weeks went into making the existing system fit to hand over. That was
not tidying. Checking it turned up four errors in figures we had already reported, and one
of them was a whole category of studies the search was not counting.

---

## Completed

### The assignment's first instruction
You asked us to *"begin by reviewing the existing pipeline with AI and determining what we need to
prepare"*. That review is deliverables 1 and 2. It found more than expected, recorded below.

### The pipeline gained three capabilities it did not have
- **Literature search.** Until recently the pipeline had no search of any kind — Richmond's 28
  papers had been supplied by hand. It now searches OpenAlex and Crossref, deduplicates by DOI and
  title as a reportable stage, and logs every query so the search can be repeated by a reader.
- **Full-text acquisition**, restricted to open-access copies the catalogue itself links.
- **Reaching a concept that is not written down.** Richmond's reviewers arrived at four
  concepts by reasoning from theory rather than by reading them in the papers. The words
  *emotion* and *self-efficacy* appear **zero times** across all 28 papers, so no amount of
  text extraction could have found them. The system can now propose a concept this way, under
  three restrictions. It goes in a separate table that cannot feed the evidence graph. It must
  name the words it claims are absent, and those words are then checked against the corpus. And
  it stays a proposal until a person approves it.

### The literature search has been run, and it found four defects first
We established that three pipeline stages — search, full-text acquisition and
ingestion — call no model and therefore cost nothing. Deliverable 3 had been filed as
budget-blocked in its entirety; half of it was not.

Before running anything we checked the search code against the live catalogues, and that check
is the reason this paragraph reports a usable pool rather than a plausible-looking one:

| What we found | Why it mattered |
|---|---|
| The query was matched against **full text**, not title and abstract | The same query matches 2,843 works in title and abstract and **124,175** with full text. The pipeline keeps only the top 200, so the sample was being drawn from a pool that is 44× larger and mostly incidental mentions |
| OpenAlex work type `review` was **excluded by default** | 274 of the 1,863 records are reviews — including **Durlak et al. 2011, which you named by DOI** (11,017 citations). OpenAlex types it `review`, so the old default would have discarded it silently |
| Crossref **lost relevance ranking** under our paging code | Before the fix the cross-check returned 501 records published 1999–2002 with **zero** abstracts; after it, 529 records with a median year of 2023 and 40% abstracts |
| The open-access PDF link was **dropped** when writing the corpus | `res acquire` fell back to the DOI landing page, so it would have reported **100%** of records as having an obtainable full text. The true figure is **68%** — and that ratio is a finding about the evidence base, which this command's own documentation says it exists to report |

Three of the four now have regression tests. A fifth was fixed on the way: a single failed query
used to discard an entire multi-query run, so the command now records each failure and refuses to
write a corpus file that is missing protocol queries while looking complete.

**We wrote the search strategy into the protocol before running the search.** It records the
ten search queries, which years each catalogue covers, and the date we last searched.

It also states plainly that this is a selected, relevance-ranked sample and not an attempt to
retrieve everything. That is the normal convention for a realist review, not an excuse for
missing studies.

The search report is generated from the query log and the collection itself. Nobody types the
numbers in, so they cannot drift from what the system actually holds.

We also wrote down in advance which of your four references the search **had** to find, and
which it should **not**.

Brackett 2012 and Durlak 2011 are intervention studies, so they had to appear. Pekrun 2006 and
Gross 1998 are theory papers with no intervention and no sample, so for them absence is the
correct result, not a failure.

All four came out as predicted. We mention it because an automatic check would have reported the
search as broken when it did not return the two theory papers.

### Three findings about the literature, from reading the pool without a model
We read the title and abstract of every record and tagged it against a fixed list of terms.

That list comes from the frameworks your own references point to. Gross's five families of
emotion regulation, as adapted for achievement settings by Harley, Pekrun, Taxer and Gross
(2019). Pekrun's categories of achievement emotions. And your own lists of interventions and
contexts, word for word.

No AI model was involved — it is term matching, which is why it cost nothing.
[`outputs-emotion/EVIDENCE_MAP.md`](../outputs-emotion/EVIDENCE_MAP.md) is generated from it.

**This map says what the literature talks about. It does not say what works**, and we have been
careful nowhere to imply otherwise. With that stated, three things came out of it that bear
directly on what the review should be:

1. **The field has studied anxiety and little else.** Of 678 records carrying an achievement-emotion
   tag, **578 mention anxiety**. Pekrun's other eight emotions sit between 11 and 79. Boredom —
   the activity emotion, the one that arises *during* learning — appears 68 times.
2. **Three of the five interventions you named are nearly absent**: self-regulation activities 7
   records, emotional awareness prompts 6, learning plans 17. Mindfulness, which you did not name,
   has 291. We widened the dictionary deliberately to test whether the near-zeros were our fault —
   self-regulation activities moved from 0 to 7, awareness prompts from 3 to 6 — so the scarcity is
   in the literature, not in our coding.
3. **STEM is barely served.** Of 1,088 higher-education records, engineering, computing and the
   natural sciences account for **51 between them**; mathematics accounts for 108 and is almost
   entirely maths and statistics anxiety.

Each of these changes what the review should be, so each is a question for you rather than a
decision we took. They are Questions 1–3 in
[`0_REQUIREMENTS_MATRIX.md`](0_REQUIREMENTS_MATRIX.md).

### The search was missing an entire arm, and the theory it needs most
Every one of the ten search queries requires an intervention term. That is correct for finding
intervention studies and it means the search **cannot** reach the theory literature — and a
realist review tests intervention evidence *against* a programme theory, so it needs both.

The finding that exposed it: Harley, Pekrun, Taxer & Gross (2019), *"Emotion Regulation in
Achievement Situations: An Integrated Model"* (*Educational Psychologist*, 387 citations) is the
paper that joins your two theoretical references — Pekrun's control-value theory with Gross's
process model, for achievement settings. It was in neither pool. We checked why rather than
assuming: its title and abstract contain no intervention term and no population term, so no query
could have retrieved it. Three theory-only queries were added, pooled separately (445 records,
now including Pekrun 2006 at 7,582 citations and ERAS), and theory papers are kept out of the
corpus of record because they inform the programme theory rather than being evidence in it.

### The prompts were lifted out of the code
You asked for the prompts by name. All 24 were buried across ten source files. Ten are now plain text in
`config/prompts/`; eleven more are built from `protocol.yaml` and `agents.yaml`, so **21 of 24 can
be rewritten for a new topic without editing code**. The remaining three are assembled at run time
from the batch being processed. The extraction was verified byte-identical by hashing every prompt
before and after.

### The review checkpoints were performed
All 20 contradictions are resolved and the programme theory is signed. They were performed by the
AI under your section 5 delegation and have now each been **countersigned by Duy** at the review
console; none was disputed. The record keeps both actors — `ai-ra:claude(…) + countersigned
human:duy` — so it stays visible which decisions a model drafted and which a person stood behind.

### Two errors were found in our own reports and corrected
- **The verification figures were too high.** The scoring code accepted matches whose own written
  rationale stated a non-match; recounting found a second, unrelated arithmetic error. Concept
  recovery moved from 34/46 to **32/46**, and the figure comparable to a human coder from 28/46 to
  **26/46**. The report package now prints the previous value beside each corrected one.
- **We had understated our own evidence.** A report stated that only one coder was human and that
  0.785 was therefore not a reliability figure. Both halves were wrong: two people coded all 28
  papers, so **0.785 is a genuine inter-rater reliability figure**.

### A draft configuration for the new topic
`config-emotion/` — review protocol, initial programme theory built from your four references, and
rewritten agent personas. The ontology was not changed and did not need to be.

---

## Limitations

Four things on the first draft of this list were limitations only because nobody had done the
work. They were done rather than reported, and what they found is below. What remains is
separated by *why* it remains — money, or an act only a person can perform — because those need
different answers from you.

### Closed since the first draft

**The comparison with your conclusions is now computed.** It had been four hand-typed verdicts in
the console's source code, reading neither the benchmark nor the system's output: it could not
change when the system changed, and nobody could check it. It is now derived from your five
programme-theory statements and our own entity matching, with the verdict following a stated rule.

The computation immediately corrected the prose. The hand-written page had called your fifth
statement — students with different levels of knowledge within a group — a corpus gap. Computed,
its chain comes back **3/3 interventions, 4/4 mechanism-responses, 5/5 outcomes**: every causal
element recovered, and only the context *label* missed. Three of your five statements show that
same shape. **The system reconstructs the mechanism and fails to name the population it applies
to.** That is a specific, actionable weakness, and no amount of rereading the prose would have
produced it.

| Your statement | Verdict |
|---|---|
| PTS1 · low knowledge | partial |
| PTS2 · high knowledge | chain recovered, context label not |
| PTS3 · positive coping | **reproduced** |
| PTS4 · negative coping | chain recovered, context label not |
| PTS5 · mixed-knowledge groups | chain recovered, context label not |

**The recurring patterns were tested against chance, and they do not survive it.** We had reported
32 demi-regularities on the rule that a pattern counts if it appears in two or more studies — a
threshold someone chose, never tested. A degree-preserving permutation null (Milo et al.,
*Science* 2002) with Benjamini–Hochberg correction, 1,000 permutations, two variants:

| | observed | expected by chance | surviving q<0.05 |
|---|---|---|---|
| Global shuffle | 32 | **32.3** (22–44) | **0** |
| Within-study shuffle (stricter) | 32 | 27.6 (18–37) | **0** |

**The count of 32 is exactly what a graph of this shape produces by chance, and no individual
pattern survives correction.** This must change how demi-regularities are reported: as candidates
for human adjudication, not as findings. It is the most consequential thing in this report and it
cost nothing to discover.

A first run showed two survivors. They were an artifact of a bug in our own shuffle, caught by the
regression test written alongside it. The corrected result is above.

**The graph was checked for internal contradictions: one defect in 547 entities, 459 relations and
94 configurations.** A context both enabling and constraining the same outcome: none. A relation
spanning two configurations: none. A configuration missing C, M or O: none. One cycle, which means
normalisation left three near-synonyms as separate concepts.

One check we had written turned out to be measuring the wrong thing.

It flagged any case where the same factor was reported as both helping and hindering within a
single study, on the assumption that this was a contradiction. All 29 cases turned out to be
two-arm experiments. In one of your studies, for example, one group is taught a reasoning
strategy and the other is told to work however comes naturally.

The difference between the two arms is the study's finding, not an error in ours. Had we counted
these as errors we would have thrown away the best evidence about mechanisms in the whole
collection.

**What is measurable about precision, without budget, has been measured.** Of our 183 concepts,
**31 have a counterpart in your 46 and 152 do not**; of those 152, **98 appear in a single study**
and **72 are a single mention in a single study**. This is *not* a precision figure — your 46 are
what you chose to report, so a concept outside your frame is not thereby wrong — but it bounds the
question and says where to look. Those 72 are where a sample should be drawn when there is budget
to adjudicate one.

### Open, and blocked by budget

5. **The screening has never been tested on papers it should reject.** We show the system finds
   all 28 included papers; a system that accepted everything would score the same. You screened
   149 to reach 28. The test module exists and its results were lost in a database restore;
   re-running needs roughly $3 of API credit.
6. **One model vendor.** Whether a different model family reaches the same configurations is
   untested. Roughly $8 for a sample, and it is the first question a methods reviewer will ask.
7. **Verification figures date from 25 September.** The corrected concept and relation figures
   were recomputed deterministically from the stored verdicts, so they are right; the rest of the
   report would need a re-run (~$3).
8. **One benchmark.** Richmond alone cannot separate "performs realist synthesis" from "fits
   Richmond". This needs a second published review and a full run.
9. ~~**No cost history.**~~ **Closed.** The claim was that a run's cost "can be
   measured but not estimated". The first half is true — `token_usage` was emptied by a database
   restore — but a projection needs the prompt, the text and the prices, and all three are in the
   repository. [`outputs-emotion/COST_MODEL.md`](../outputs-emotion/COST_MODEL.md) now prices
   every remaining stage from the system prompt the pipeline actually renders. **Screening the
   whole pool is $5.44.** We had been treating screening as blocked alongside extraction; the $45
   figure is for extracting 28 full papers, a different stage. A 3-paper pilot (~$5) would replace
   the projection with a measurement, which is why it is the first paid step and not the last.
10. **OpenAlex stopped being free to query without an account on 13 February 2026.** Anonymous
    requests now share a $0.10 daily budget per network address, and the catalogue paused ours
    once in the middle of a ten-query run. The search above completed anonymously and cost about
    two cents of that shared allowance. A key is free but requires an account in your or Duy's
    name, so we have not created one: **if you would like the searches to run without
    interruption, say so and we will set one up.** This also qualifies a claim in the manuscript —
    that a reader can repeat our search without credentials is no longer strictly true.

### Open, and not something we can solve for you

10. **~~No human has countersigned the review checkpoints.~~ Closed.** All 20 contradictions and
    the programme theory have now been countersigned by Duy, none disputed. Two defects had to be
    fixed first, and they are worth stating because they change what the earlier reports meant:
    the countersignature route crashed on every submission, and every button a person was meant to
    press rendered with its label in its own background colour. **The checkpoints had not been
    left unsigned for want of a human — signing had never been possible.** Your section 4 asks us
    to *preserve* human verification; it is now exercised rather than merely available.

---

## What should be done next

**Without budget** — ordered by how much each would improve the result:

1. Sample and adjudicate the 72 single-mention single-study concepts, to convert the bound above
   into an estimate of how much of the extraction is spurious.
2. Investigate why Richmond's context labels are under-recovered when the chains are not. The
   computed comparison localises this; 22 of 94 configurations also have a context with no graph
   edge, which is probably the same defect.
3. Fix the normalisation cycle, which marks three concepts that should be one.
4. Countersign the review checkpoints.

**With a modest budget**, in order of what each buys:

5. Re-run verification so every figure reflects the corrected scoring (~$3).
6. The rejection test — does the screening discriminate, or is it merely permissive (~$3).
7. A second model family on a sample — are these findings one vendor's opinion (~$8).
8. ~~The literature search~~ — **done, at no cost.** What remains is the
   10–15 paper pilot: screening and extraction on a sample, reporting measured cost before going
   further. 1,222 of the 1,863 records have both an abstract to screen and an open-access PDF to
   extract from, so the pilot can be drawn without buying anything but model calls.

**Requiring your decision:**

- **The scope question in deliverable 2 §2** — whether studies that measure emotion as an outcome
  of ordinary teaching are in scope, or only studies that intervene on emotion deliberately. This
  roughly triples the corpus and changes what the review is.
- **The AERA paper.** Accepted 6 November. It carries the superseded figures and the coder error
  described above. Reviewer comments are on the All Academic portal and have not been read.
  The deadline for programme changes is 5 March 2027.
