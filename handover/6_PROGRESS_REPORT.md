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

Ordered by how much they constrain what can be claimed.

1. **The comparison with your conclusions is hand-written, not computed.** The page that places
   Richmond's findings beside ours contains four hand-typed verdicts. Both sides exist as
   structured data, so this can and should be a computation — a comparison that cannot be
   recomputed cannot be checked. **This is the most serious item here** and the next thing to fix.
2. **Precision has never been measured**, on any topic. Every figure is recall.
3. **No human has countersigned the checkpoints.** Your section 4 asks us to *preserve* human
   verification; a feature never exercised cannot be preserved.
4. **The recurring patterns have no significance test.** A pattern counts as recurring if it
   appears in two or more studies — an arbitrary threshold. We report 32 patterns without knowing
   how many would appear by chance in a graph of this shape.
5. **The screening has never been tested on papers that should be rejected.** We show the system
   finds all 28 included papers; we have never shown it excludes irrelevant ones. Richmond screened
   149 to reach 28. A system that accepted everything would also score 100% recall. The test module
   exists; its results were lost when the database was restored.
6. **One model vendor.** Whether a different model family reaches the same configurations is
   untested, and is the first question a methods reviewer will ask.
7. **One benchmark.** Richmond alone cannot separate "performs realist synthesis" from "fits
   Richmond".
8. **Verification figures date from 25 September** and predate the scoring fix.
9. **No cost history.** The usage records were lost in a database restore, so the cost of a new run
   can be measured but not estimated.

---

## What should be done next

**Without budget** — these are the items that most improve the eventual result, and all cost nothing:

1. Make the Richmond comparison a computation rather than prose (limitation 1).
2. Test the recurring patterns against a null model, so "32 patterns" becomes "N patterns that
   occur more than chance" (limitation 4).
3. Countersign the review checkpoints (limitation 3).
4. Check the extracted graph for internal logical contradictions.

**With a modest budget**, in order of how much each would tell us:

5. Re-run verification, so every reported figure reflects the corrected scoring (~$3).
6. Run the rejection test, which answers whether the screening discriminates or is merely
   permissive (~$3).
7. Re-extract a sample with a second model family and measure agreement. If two independent models
   reach the same configurations, the findings are not one vendor's opinion; if they diverge, that
   is the most important limitation to report (~$8).
8. The literature search and a 10–15 paper pilot for the new topic, reporting measured cost before
   going further.

**Requiring your decision:**

- **The scope question in deliverable 2 §2** — whether studies that measure emotion as an outcome
  of ordinary teaching are in scope, or only studies that intervene on emotion deliberately. This
  roughly triples the corpus and changes what the review is.
- **The AERA paper.** Accepted 6 November. It carries the superseded figures and the coder error
  described above. Reviewer comments are on the All Academic portal and have not been read.
  The deadline for programme changes is 5 March 2027.
