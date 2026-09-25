# Improvement Plan — toward an output that stands beside Richmond

> **The standard this plan is written against.** Richmond et al. spent months and five expert
> reviewers producing their review. For our output to be placed on the same scale, it is not
> enough that it exists — it has to be defensible on the operations that define a realist
> synthesis, and honest about where it is not. This plan is ordered by **measured weakness**,
> not by technology.
>
> Written 2026-09-24, against baseline run `verify-91a39a5c`.

---

## 0. The baseline this plan has to beat

Everything below targets a number we have already measured, twice, with intervals. Nothing here
is motivated by "this library is popular".

| # | Measured weakness | Current | Where it hurts |
|---|---|---|---|
| **W1** | **Concept over-granularity** — 218 canonical concepts against Richmond's 46; **130 appear exactly once** | 4.7× too fine | Depresses every concept- and relation-level comparison, and is the failure mode the realist literature names outright ("fragmented catalogues" rather than structure) |
| **W2** | **Realist typing errors** — our own consistency checker disputes 54% of CMOCs, with substantive reasons (observed results coded as learner responses; intervention exposure coded as context) | 54% flagged | This is the distinction that *defines* realist method; RAMESES lists exactly these confusions under "Inadequate" |
| **W3** | **Concept coverage, same role** | 37/46 (66–91%) | The headline like-for-like comparison with Richmond |
| **W4** | **Strict relation recovery** | 5/40 | The honest floor under any claim about causal structure |
| **W5** | **Run-to-run instability** — anchored recall moved **80.0% → 67.5%** between two identical runs | ±12 points | Makes any single-run improvement claim meaningless |
| **W6** | **Cost and wall-clock** — ~$40 and ~60 min per run; 81% of tokens are gpt-5.5 reading each full paper twice | $40 / 60 min | Limits how often we can iterate, which is itself a research constraint |
| **W7** | **No human coding baseline** | 0 papers coded by a human | **Blocks the comparison with Richmond more than any technical gap** |

### The rule that governs every item below

**W5 is the reason this plan has a rule.** Two runs of identical code differed by 12.5 points with
fully overlapping confidence intervals. Therefore:

> **No change ships as an improvement until a paired test on the same studies shows it, with the
> difference reported as an interval.** Before/after on two whole runs is not evidence — we already
> made that mistake once this month, reporting a feedback-loop improvement that turned out to be
> noise from a loop that was not even connected.

---

## Phase 0 — The apparatus that makes the rest measurable

*No API cost to build. Nothing else in this plan is trustworthy without it.*

### 0.1 Paired A/B harness (`res ab`)

Run variant A and variant B **over the same studies in the same invocation**, and report the
per-study paired difference with a bootstrap interval, clustered by study (91 CMOCs from 26 papers
are not 91 independent observations — Miller 2024, arXiv:2411.00640).

Outcome measures per variant: checker-disagreement rate, concept count, concept coverage within
role, anchored relation recall, verbatim resolution rate, token cost.

### 0.2 Response cache

An on-disk cache keyed by `(model, system_prompt, user_prompt, schema, seed)`. Re-running an
unchanged variant during development then costs nothing, which is what makes a paired design
affordable at all.

**This is the one place LangChain earns its keep** — `langchain-community`'s SQLite cache is a
drop-in for exactly this. It can also be ~60 lines of our own code against the same key. Either is
defensible; the library saves a day.

### 0.3 Honesty debt

`ARCHITECTURE.md` still describes LangGraph orchestration, embeddings and GraphRAG search that do
not exist. It carries a warning banner today; it must be rewritten before any manuscript is drafted
from it. A reviewer who opens the repository and finds a different system than the paper describes
will not read the rest charitably.

---

## Phase 1 — The concept layer (attacks W1, W3, and indirectly W4)

*This is where GraphRAG's actual contribution lives, and where our largest measured gap is.*

### 1.1 Why we are 4.7× too granular — the mechanical cause

`normalization._batched_cluster` sorts all labels **alphabetically**, splits them into batches of
40, clusters each batch with an LLM, and merges across batches **only when two batches independently
emit a byte-identical canonical label**.

So *"novice learners"* (batch 3) and *"students with low prior knowledge"* (batch 7) can never
merge — they are not adjacent alphabetically, and the two batches would have to invent the same
canonical string by coincidence. **That is the mechanism producing 130 singleton concepts.**

### 1.2 Embedding-based concept resolution

Replace alphabetical batching with the standard approach:

1. Embed every entity label together with its verbatim evidence quote (`text-embedding-3-small`).
2. Cluster in embedding space **within realist role** (agglomerative with a cosine threshold, or
   HDBSCAN), so a Context never merges with an Outcome.
3. Use the LLM only to **name** each cluster and to adjudicate borderline pairs — not to discover
   the clusters.

This is what the `embeddings` tier in `models.yaml` was declared for and never used. It attacks W1
directly and W3 through it.

**Expected effect:** concept count falls toward Richmond's granularity; singletons collapse.
**Test:** paired, on the same extraction. Report concept count, coverage within role, and
`community_alignment` before and after. Cheap — embeddings cost cents.

### 1.3 Hierarchical community summarisation

This is **the** contribution of Microsoft GraphRAG (Edge et al., 2024, arXiv:2404.16130) and the
part we have never had. Today we run Leiden once and label each community from its member labels
alone — the summariser never sees the underlying text.

Implement properly:
- Leiden at **multiple resolutions**, producing a hierarchy (fine → coarse).
- A community report at each level, generated from **member concepts plus their verbatim quotes and
  their relations**, not from labels.
- Richmond's five student contexts and ~14 mechanisms sit at a *coarse* level; our current single
  flat level sits far below it. A hierarchy lets us compare **at the level Richmond worked at**,
  instead of forcing a comparison across granularities.

**Expected effect:** `community_alignment` rises from 17/28; the coarse level becomes directly
comparable to Richmond's Figure 2/3 structure.
**Test:** paired on the same graph — the partition is deterministic given a seed, so only the
report generation varies.

### 1.4 What NOT to do

**Do not adopt the `graphrag` package wholesale.** Its pipeline carries its own generic
entity/relation schema with **no realist ontology, no mandatory verbatim quote, and no character
spans**. Migrating to it would cost us the single strongest asset we have — 532/547 claims resolved
to an exact span in the source. Implement the *mechanisms* on our ontology; do not import the
*pipeline*.

---

## Phase 2 — Orchestration (attacks W5, W6, and a real fragility)

*This is where LangGraph earns its keep — and it earns it for reasons that have nothing to do with
being fashionable.*

### 2.1 The fragility that is costing real money

`core/llm.py` has **no retry**. A single 429 kills the run. That is not hypothetical: credit
exhaustion ended three runs this week, and only the hand-built `--resume` saved the spend.

LangGraph gives, as first-class primitives, what we have been re-implementing by hand:

| What we built by hand | LangGraph equivalent |
|---|---|
| `--resume <run-id>`, `_clear_study_cmocs`, `*_bak` snapshot tables | Durable checkpointer (Postgres-backed — the same database we already run) |
| Four HITL checkpoints as separate CLI commands and web forms | `interrupt()` / `Command(resume)` at a node |
| Sequential loop over studies | Fan-out with bounded concurrency |
| Nothing | Per-node retry policy with backoff |

### 2.2 Parallel extraction

Extraction is **per-study and stateless** — 28 independent units, currently run in series for ~60
minutes. With bounded concurrency (say 5), wall-clock falls to roughly 12–15 minutes. That does not
reduce cost, but it changes how often we can afford to iterate, which is the real constraint on
everything else in this plan.

### 2.3 Honest scope

LangGraph will **not move a single quality metric**. It buys robustness, resumability as a
property rather than a patch, and wall-clock. Worth doing — after Phase 1, and only if Phase 1's
paired tests show the concept layer is settled.

---

## Phase 3 — Retrieval (attacks W6; highest risk in this plan)

Today the programme-theory composer receives `json.dumps(evidence_pack)` — every demi-regularity,
contradiction, CMOC and community, inline. That is context stuffing, not retrieval. Likewise the
Self-Refine revision re-sends the entire paper.

GraphRAG's local/global search would replace both with targeted retrieval over the graph and its
text units.

**Expected effect:** substantial cost reduction (the two full-paper calls per study are 81% of all
tokens).
**Risk:** high — retrieval can miss the passage that evidences a CMOC, trading cost for recall.
**Therefore:** paired A/B only, and the acceptance criterion is *no loss* in CMOC count or verbatim
resolution, not merely a cost win.

---

## Phase 4 — The part that decides whether we can stand beside Richmond at all

*No library contributes anything here. It matters more than Phases 1–3 combined.*

### 4.1 Two human coders, 8–10 papers, blind (attacks W7)

Without a human–human ceiling, every agreement-style number we report is uninterpretable. The
literature is unambiguous: GPT-3 at κ = 0.61 reads as a success until you see the expert–expert
ceiling of κ = 0.88 on the same items (Xiao et al., 2023).

- Two coders, blind to machine output, on a **design-based random sample** of 8–10 of the 28 papers.
- Compute **human–human agreement first**, then machine-vs-each-human.
- **Not Cohen's κ** for the CMOC extraction: with no defined number of negative cases, Hripcsak &
  Rothschild (2005, *JAMIA*) prove positive specific agreement (= F) is the correct statistic. Use
  Krippendorff's α with a bootstrap CI, alongside Gwet's AC1, for the fixed-category role
  assignment.
- Tooling exists and is unused: `res gold-template`.

### 4.2 Fix the typing errors at their source (attacks W2)

The HITL feedback loop is now genuinely connected (`agent_feedback`, with a guard that raises on an
agent key nothing reads). The two corrections the checker raises most often are seeded. **But its
effect is unmeasured** — the one pilot that appeared to show an effect was noise from a loop that
was not connected at all.

Run it properly: paired A/B, feedback on vs off, same studies, outcome = checker-disagreement rate,
difference reported as an interval.

### 4.3 Judge panel and statistical correction

- Programme-theory correspondence currently swings **0.51 → 0.94** depending only on which model
  judges. Replace the single judge with a panel of disjoint families (Verga et al., 2024) and report
  the spread.
- Human-label a probability sample of the machine-judged items and apply **prediction-powered
  inference** (Angelopoulos et al., 2023, *Science*) so the reported estimates carry valid intervals
  **regardless of judge bias**. Cite the ceiling pre-emptively: when the judge is no more accurate
  than the system being judged, no debiasing halves the required human labels by more than a factor
  of two (Dorner et al., 2025).

---

## Sequencing, cost, and what each phase actually buys

| Phase | Effort | API cost | Moves which metric | Confidence it helps |
|---|---|---|---|---|
| **0** Test harness + cache + doc honesty | ~1 day | ~0 | none directly — **makes every later claim provable** | Certain |
| **1.2** Embedding concept resolution | ~1 day | ~$1 | W1 concept count, W3 coverage | **High** — the mechanical cause is identified |
| **1.3** Hierarchical community summarisation | ~1–2 days | ~$5 | W1 granularity, `community_alignment` | **Medium-high** |
| **4.2** Feedback loop, properly measured | ~0.5 day | ~$15 (A/B) | W2 typing errors | Unknown — that is the point of measuring |
| **2** LangGraph orchestration | ~2–3 days | ~0 | **No quality metric.** Robustness + 4× faster wall-clock | Certain for what it claims |
| **3** Retrieval | ~2 days | ~$15 (A/B) | W6 cost | **Medium, with real downside risk** |
| **4.1** Human coders | weeks (human time) | ~0 | **W7 — unblocks the entire comparison** | Certain |

### The order I recommend

**0 → 1.2 → 1.3 → 4.2 → 2 → 3**, with **4.1 started in parallel immediately**, because it needs
human calendar time and nothing technical substitutes for it.

### The honest summary of the three libraries

- **GraphRAG** — two real mechanisms we lack (hierarchical summarisation, retrieval) that attack two
  measured weaknesses. Take the mechanisms; do **not** take the package, or we lose span grounding.
- **LangGraph** — buys robustness, durable checkpointing and parallelism. Will not move a quality
  number. Worth doing for engineering reasons after Phase 1.
- **LangChain** — contributes one useful thing: a response cache for affordable A/B testing.
  Everything else it offers, we already have more directly through OpenAI structured outputs.

**And the thing to keep in view:** the strongest claim this project can make is not that it uses
these libraries. It is that **no one has automated realist synthesis, that our mechanisms emerge
from the data where Richmond's were authored by hand, and that we report what is deterministic,
what is model-judged, and what remains unverified.** Phases 1 and 4 strengthen that claim. Phase 2
protects it. Phase 3 makes iterating on it affordable.
