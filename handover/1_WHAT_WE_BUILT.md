# What we built, and where everything is

**Duy Nguyen — 13 November 2026.** Deliverable 1 of the 2026-10-30 assignment.

This answers your first request: organise and provide everything developed for the Richmond
benchmark. It assumes no familiarity with the system. Section 1 explains what the thing does,
section 2 says where each item you listed lives, and section 3 states plainly what it cannot do
yet — including two errors we found in our own earlier reports and corrected last week.

---

## 1. What the system does

A realist review asks what works, **for whom, in what circumstances, and why**. Its unit of
analysis is the Context–Mechanism–Outcome Configuration: *in this context, this resource triggers
this response, producing this outcome*. Building those by hand across dozens of papers takes a
team months, and afterwards the reasoning is hard to audit because it lives in reviewers' notes.

The pipeline does the mechanical part of that work and keeps a record of the reasoning. Six stages:

| Stage | What it does | On Richmond's 28 papers |
|---|---|---|
| Ingest | Extract text from each PDF | 28 papers, 165 text units |
| Screen | Two models vote on eligibility; disagreements go to a human | 86 decisions |
| Extract | Pull out configurations, **each element tied to a verbatim quote** | 94 CMOCs, 547 quoted elements, 459 typed relations |
| Consolidate | Collapse repeated mentions into shared concepts | 547 mentions → 183 concepts |
| Find patterns | Detect recurring configurations and contradictions | 32 recurring patterns, 20 contradictions |
| Compose | Write the programme theory | 9 context-based sections |

**The one design decision that matters most.** Every element the system extracts carries the exact
sentence it came from and that sentence's character position in the source paper. A claim without
a quote cannot enter the graph. One row, as stored:

```
study_id        S018
entity_type     Context
label           incomplete and error-prone knowledge
char_start      23737     char_end  23825
verbatim_quote  "The other 24 had basic relevant knowledge that was, however,
                 incomplete and error-prone."
```

Checked on 11 November against the source texts: **546 of 547 quotes (99.8%) occur in the paper
they are attributed to** — 414 exactly, 104 more once PDF extraction artefacts (ligatures,
hyphenation) are normalised, 28 as partial matches. One cannot be located and is recorded as such.

**Where the model is used, and where it is not.** The language model reads papers and proposes
typed, quoted elements. It does **not** decide the review's findings. The recurring patterns and
the contradictions are computed by database queries over the extracted graph — the model is never
asked "is there a contradiction here". Of 36 Python modules, **24 make no model call at all.**

---

## 2. Where each item you asked for lives

Everything is in one repository: **https://github.com/duynguyenxc/Realist-Evidence-Synthesis-V2**
(48 commits, 13,286 lines of Python, 20 automated tests passing).

### The pipeline, source code and architecture
| | |
|---|---|
| `src/res_pipeline/` | The pipeline. `core/` is infrastructure, `plugins/realist/` is the realist method, `verification/` is the scoring harness — deliberately separate, so scoring cannot influence the pipeline |
| `docs/ARCHITECTURE.md` | The design decisions and why each was made |
| `README.md` | Start here. Rewritten 10 November; the previous version described a stack we never built, which is corrected in §3 below |

### Agents, prompts, schemas, configurations
| | |
|---|---|
| `config/agents.yaml` | The 8 agents and the 5 human checkpoints |
| `config/prompts/` | **The prompts.** Until 4 November all 24 were buried in ten source files. Ten are now plain text in YAML here; another eleven are built from `protocol.yaml` and `agents.yaml`, so **21 of 24 can be rewritten for a new topic without editing code**. Three are assembled at run time from the batch being processed and remain in code |
| `config/ontology.yaml` | The 5 entity types and 5 relation predicates — the grammar the extractor must obey |
| `config/protocol.yaml` | Review question and eligibility criteria |
| `config/initial_programme_theory.yaml` | The theory the review sets out to test |
| `config/models.yaml` | Which model does which stage, and the cost ceiling |

### Input data, intermediate results, outputs, knowledge graph
| | |
|---|---|
| `data/` | The 28 papers |
| **`outputs/raw_export/`** | **Every row of every database table, as JSON and CSV.** 18 tables, 2,736 rows, nothing summarised. If you want to check any figure in any report, it resolves here |
| `outputs/lkg/` | The knowledge graph as Parquet files |
| `outputs/RESULTS.html` | The full review as one searchable page |
| `res webui` | A local console: the graph with every node clickable to its source quote, the raw tables, the review checkpoints |

### Evaluation procedures and results
| | |
|---|---|
| `gold/richmond_gold_v3.json` | Your benchmark: Richmond's 46 concepts, 40 relations, 5 programme-theory statements, encoded for scoring |
| `docs/VERIFICATION_PROTOCOL.md` | Why each statistic was chosen, with citations, and what is still missing |
| `docs/MACHINE_VS_HUMAN.md` | **The central comparison** — the system against the two human coders |
| `outputs/SEND_TO_PROFESSOR/` | The report package, corrected 10 November |

### The conference paper
Accepted to **AERA 2027** on 6 November (Division D, roundtable "AI as a Methodological Tool",
Toronto, 14–18 April). **The reviewer comments on the All Academic portal have not been read yet** —
they may bear on everything below, and they are the first thing I will read once you can access them.

### The instructions given to AI, and the decisions that followed
| | |
|---|---|
| `WALKTHROUGH.md` | A dated log of every working session: what was done, what was verified and how, what was found and left unfixed. ~1,900 lines |
| `docs/DECISION_LOG.md` | Each architectural decision with its rationale |
| `docs/IMPROVEMENT_PLAN.md` | Options considered **and rejected**, with the evidence for rejecting them |
| `PLAN.md` | The work currently in progress |

---

## 3. What it cannot do, and what we got wrong

Stated here rather than at the end, because this is the part that decides how much weight the rest
can carry.

### Results on your benchmark

| What is compared | Result | 95% CI |
|---|---|---|
| Found the 28 papers | 28/28 | — |
| Concepts recovered, same realist role | 32/46 (69.6%) | 54.2–82.3 |
| Concepts, role-crossing allowed | 39/46 (84.8%) | 71.1–93.7 |
| Concepts, **one-to-one — comparable to a human coder** | **26/46 (56.5%)** | 41.1–71.1 |
| Causal relations, anchored | 28/40 (70.0%) | 53.5–83.4 |
| Quotes matching source after normalisation | 509/547 (93.1%) | 90.6–95.0 |

Two people coded all 28 papers independently as a human reference: they found 30/46 and 28/46, and
their agreement is **0.785** (positive specific agreement). **The system is below both of them on
the comparable measure.** The claim this supports is *non-inferiority* — overlapping confidence
intervals — not superiority. We have been careful that the word "exceeds" appears nowhere.

### Two errors in our own earlier reports, found and corrected last week

**The figures were too high.** A defect in the scoring code accepted a match whose own written
rationale stated a non-match — two concepts, each matched to its *opposite* ("high knowledge"
matched to "knowledge deficits"). Recounting exposed a second, unrelated arithmetic error. Figures
above are post-correction; the report package now prints the previous value beside each.

**We understated our own evidence.** An earlier report said only one coder was human and that 0.785
was therefore not a reliability figure. Both halves were wrong — two people coded all 28 papers, so
0.785 is a genuine inter-rater reliability figure. **The accepted AERA paper still carries both the
old figures and this error.** The deadline for programme changes is 5 March 2027.

### Limitations that remain

1. **Precision has never been measured.** Every figure above is recall — how much of Richmond we
   recovered. Nothing establishes how many of our 547 extractions are spurious. This is half of
   "is it as good as a human", and it is missing.
2. **No human has yet countersigned the review checkpoints.** All 20 contradictions are resolved
   and the programme theory is signed, but recorded as AI-performed under your §5 delegation and
   awaiting Duy's countersignature. Your assignment asks us to *preserve* human verification; a
   feature never exercised cannot be preserved, and closing this is the next thing I will do.
3. **The side-by-side comparison with your conclusions is currently hand-written prose**, not
   computed. Both sides exist as structured data — your 5 programme-theory statements in the gold
   standard, our 9 sections in the database — but nothing yet aligns them automatically. A
   comparison that cannot be recomputed cannot be checked, and fixing this is the top item on the
   current plan.
4. **Everything rests on one benchmark.** One benchmark cannot distinguish "performs realist
   synthesis" from "fits Richmond".
5. **A single model vendor.** All extraction runs on one provider. Whether a different model family
   would reach the same configurations is untested, and it is the first question a methods reviewer
   will ask.
6. **The verification figures were last computed on 25 September** and predate the scoring fix.
   Re-running costs API credit, which the project does not currently have.

---

## 4. What the pipeline needs as input, to answer your question directly

For a new topic it needs four things, and only the fourth is substantial:

1. **A review question and eligibility criteria** — `protocol.yaml`.
2. **An initial programme theory** — the hypotheses to test, from established theory.
3. **A corpus.** Since 6 November the pipeline can build this itself: `res search` queries OpenAlex
   and Crossref, deduplicates, and writes the corpus definition. Previously papers were supplied by
   hand.
4. **Domain expertise in the prompts** — the agent personas currently describe clinical reasoning
   and must be rewritten.

**The ontology needs no change.** Its five entity types are domain-neutral, intervention is already
a first-class type, and the mechanism-response type is already defined as "the cognitive **or
emotional** reaction". Deliverable 2 covers what the emotional-regulation topic needs in detail.
