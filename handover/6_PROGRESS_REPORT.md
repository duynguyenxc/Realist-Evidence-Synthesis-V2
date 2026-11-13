# Progress report

**Duy Nguyen — 13 November 2026.** Deliverable 6 of the 2026-10-30 assignment.

Covering 30 October to 13 November. Short version: deliverables 1, 2 and 6 are complete and
attached. Deliverables 3, 4 and 5 require running the pipeline on a new corpus, which needs API
budget the project does not currently have. The two weeks were spent making the existing system
and its record fit to hand over, and that turned out to be necessary rather than tidying.

---

## Completed

### The assignment's first instruction
You asked us to *"begin by reviewing the existing pipeline with AI and determining what we need to
prepare"*. That review is deliverables 1 and 2. It found more than expected, recorded below.

### The pipeline gained three capabilities it did not have
- **Literature search.** Before 6 November the pipeline had no search of any kind — Richmond's 28
  papers had been supplied by hand. It now searches OpenAlex and Crossref, deduplicates by DOI and
  title as a reportable stage, and logs every query so the search can be repeated by a reader.
- **Full-text acquisition**, restricted to open-access copies the catalogue itself links.
- **Retroduction without a quote.** Richmond's reviewers reached four concepts by inference from
  theory, not from the text — the words *emotion* and *self-efficacy* occur **zero times** in the
  28 papers, so no extractor could have found them. The system can now make such a proposal, but
  only in a separate table that cannot enter the evidence graph, only when it names words it
  claims are absent and those words are checked against the corpus, and only as a proposal until a
  human ratifies it.

### The prompts were lifted out of the code
You asked for the prompts by name. All 24 were buried across ten source files. Ten are now plain text in
`config/prompts/`; eleven more are built from `protocol.yaml` and `agents.yaml`, so **21 of 24 can
be rewritten for a new topic without editing code**. The remaining three are assembled at run time
from the batch being processed. The extraction was verified byte-identical by hashing every prompt
before and after.

### The review checkpoints were performed
All 20 contradictions are resolved and the programme theory is signed. They are recorded as
AI-performed under your section 5 delegation and **await Duy's countersignature** — see Open below.

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

One intended check was reclassified rather than kept. "The same driver asserted both positive and
negative within one study" was written as a defect detector and is not one: all 29 hits are
two-arm experimental designs — one of your studies instructs one group in a reasoning strategy and
tells the other to use whatever comes naturally — and the contrast between arms is the study's
finding. Counting it as an error would have discarded the best mechanism evidence in the corpus.

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
9. **No cost history.** The usage records were lost in a database restore, so a new run's cost can
   be measured but not estimated. This is why the plan has a pilot step.

### Open, and not something we can solve for you

10. **No human has countersigned the review checkpoints.** All 20 contradictions are resolved and
    the programme theory signed, with the reasoning recorded — but signed `ai-ra:claude`, honestly,
    because writing a person's name against a decision they have not read would put a false entry
    in the research record. Your section 4 asks us to *preserve* human verification; a feature
    never exercised cannot be preserved. The console now presents each decision with the evidence
    for confirming or disputing it, which makes this about fifteen minutes of Duy's time. **It is
    the one limitation on this list that no amount of further work by us can close.**

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
8. The literature search and a 10–15 paper pilot for the new topic, reporting measured cost
   before going further.

**Requiring your decision:**

- **The scope question in deliverable 2 §2** — whether studies that measure emotion as an outcome
  of ordinary teaching are in scope, or only studies that intervene on emotion deliberately. This
  roughly triples the corpus and changes what the review is.
- **The AERA paper.** Accepted 6 November. It carries the superseded figures and the coder error
  described above. Reviewer comments are on the All Academic portal and have not been read.
  The deadline for programme changes is 5 March 2027.
