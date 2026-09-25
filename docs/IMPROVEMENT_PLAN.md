# Improvement Plan v2 — stop tuning, start reporting

> **This replaces v1 (2026-09-24, same day).** An adversarial review of v1 and an independent
> literature search both concluded that v1's load-bearing claims were wrong. v1 is preserved in git
> history as `docs/IMPROVEMENT_PLAN.md@2c486a7`. What follows is what the evidence actually
> supports, including the parts that say *do less, not more*.

---

## 0. Why v1 was withdrawn

Four claims carried v1. All four are false, and each was falsifiable from artifacts already in this
repository.

| v1 claimed | The evidence |
|---|---|
| "218 canonical concepts against Richmond's 46 — we are 4.7× too granular" | The live export gives **183** concepts, **79** singletons. And the comparison is at the wrong layer: `concept_families` gives **47 against Richmond's 46**. The layer built for this comparison already matches, is used by `synthesis.py` and `programme_theory.py`, and v1 never mentioned it. |
| "Merging synonyms will raise concept coverage" | **It cannot.** Coverage recall asks "does *any* of my items match each gold item". The 183 concepts are a strict superset of the discriminative content of the 47 families, so coarsening can only hold recall constant or lower it. This is arithmetic (Bagga & Baldwin 1998; Luo 2005; Amigó et al. 2009). |
| "Run-to-run instability of 12.5 points comes from the pipeline" | Two verification runs scored a **byte-identical graph** (517 entities; tiers `{exact 48, normalized 432, fuzzy 19, unresolved 18}` in both) and returned **entity 41 vs 45**, **anchored 25/40 vs 29/40 — 10 points**, community 21 vs 22. The instability is overwhelmingly **the verification judge**, not the pipeline. |
| "`core/llm.py` has no retry; a 429 kills the run" | Every 429 traceback in `outputs/logs/` shows `max_retries = 2`, `retries_taken = 2`. The SDK retried. The failures were `insufficient_quota` — a **billing** failure no retry policy recovers from. |

A fifth error, in v1's argument for *not* adopting GraphRAG: v1 wrote *"532/547 claims resolved to an
exact span"*. The exact tier is **53/547 (9.7%)**; 532 is the all-tiers figure. The 93% verbatim
figure is sound and defensible — v1 simply called it by the wrong name, which is the same class of
mistake this project spent the week correcting elsewhere.

**A concrete near-miss.** v1's flagship intervention was embedding-based concept clustering. In the
current run, gold **E02** ("students with *low* clinical domain-specific knowledge") and **E03**
("students with *high* clinical domain-specific knowledge") already both match the single concept
`cont:knowledge-deficits`. Cosine similarity over short noun phrases places antonyms close
together; embedding clustering would make this collapse *systematic*, and v1 relegated the LLM to
"adjudicating borderline pairs" — but antonym pairs do not look borderline, they look nearly
identical. **Richmond's entire finding — "the student is key", the expertise-reversal effect — rests
on exactly the distinction v1 proposed to dissolve.**

---

## 1. The number that governs everything below

The verification judge has a standard error of roughly **9.7 percentage points** on the LLM-judged
metrics (a 95% interval spanning ~38 points). If a pipeline is evaluated *k* times against this
benchmark and the best result is reported, the expected optimism of that reported maximum is
approximately `SE × √(2 ln k)`:

| tuning rounds against the 28-paper benchmark | expected "improvement" from selection alone |
|---|---|
| 3 | ≈ 14 points |
| 5 | ≈ 17 points |
| **10** | **≈ 21 points** |
| 20 | ≈ 24 points |

**After ten rounds of tuning we would expect to report a ~20-point improvement even if every
variant were identical in true quality.** No bootstrap, no confidence interval and no paired design
removes this; it is a property of repeatedly selecting against a noisy measurement (Dwork et al.,
*Science* 349:636–638, 2015, on adaptive data analysis and the reusable holdout).

The reassuring counter-literature does not apply. Recht et al. (ICML 2019) and Roelofs et al.
(NeurIPS 2019) found little adaptive overfitting on ImageNet/CIFAR and Kaggle — but on test sets of
thousands of items with crisp automatic metrics, where per-query noise is small relative to the
effects being chased. At n = 28 with a 38-point interval the ratio is inverted. Say so explicitly
if a reviewer cites Recht.

### Therefore the strategy changes

> **The Richmond comparison is concurrent-validity evidence, reported once. It is not an objective
> function.**

That is both the methodologically correct position and the rhetorically stronger one: *"our system
reproduces a human review's analytic operations, and here is honestly how far"* is a more
interesting claim for a realist-review audience than *"our system scores 0.82"*.

### And the power ceiling must be stated in the paper

With 28 paired documents, an exact McNemar test at 80% power detects only a **≈40-point
per-document difference**. At the unit level (~94 CMOCs nested in 26 papers, measured ICC ≈ 0.02,
design effect ≈ 1.06) the minimum detectable effect is roughly **16–21 points**. Miller (2024,
arXiv:2411.00640) recommends **n ≥ 1000 items** for an eval with good signalling ability; we have
46 gold entities and 40 gold relations.

**Pre-state this.** A sentence of the form *"this design had 80% power to detect only a ≈40-point
difference; the observed difference was X (95% CI …) and is reported as inconclusive"* does more
for the manuscript than any further pipeline tuning.

---

## 2. What we will do — ordered by cost, cheapest and most certain first

### Step 1 — Measure the instrument before using it (~$5)

Freeze one graph. Run `res verify` **K = 10 times**. Publish the judge's own variance component for
every model-judged metric. **That number becomes the decision threshold for every later comparison,
and no comparison is interpretable without it.**

Two runs on a byte-identical graph already gave 10 points of spread on anchored recall; K = 10 turns
that anecdote into a reportable variance.

### Step 2 — Make a scored result traceable to what was scored ($0)

`verification_report.json` records `screening_run_id` and nothing else. Add a **content fingerprint**
of `entity_instances` + `typed_relations` + `conceptual_entities`. Without it, a changed number
cannot be attributed to a pipeline change rather than a judge draw — which is precisely the mistake
v1 made.

### Step 3 — Diagnose W2 before treating it ($0, ~4 hours)

Read the 51 CMOCs where `checker_agrees = false` and classify **why**. The RAMESES *Inadequate*
descriptors give a ready-made coding frame. v1 asserted the reasons were substantive from two
examples; nobody has built the taxonomy. Until it exists, any intervention aimed at the typing
errors is a treatment chosen without a diagnosis.

### Step 4 — Score at both concept layers, and report both (~$1, one query change)

This tests v1's entire W1 hypothesis before a line of new code is written.

Multi-granularity reporting is **standard practice**, not a fudge: the OAEI runs coarse- and
fine-grained modalities over the same test case; the Bio-ML track evaluates every system under two
protocols simultaneously because reference alignments are incomplete; SemEval-2013 defines four
schemas (strict / exact / partial / type) and reporting all four is routine; hierarchical
classification reports per-level scores (Kosmopoulos et al., *DMKD* 29:820–865, 2015).

**Pre-declare the family layer (47) as primary**, on the stated ground that Richmond's published
figures contain 46 nodes, so that is the reference's own resolution. Report the 183-concept layer as
the finer decomposition, for transparency.

### Step 5 — Replace the metrics this project's own protocol already condemns (~$2)

`VERIFICATION_PROTOCOL.md` §2.5 calls community alignment *"the weakest thing in the harness"* and
prescribes B-cubed. v1 proposed spending 1–2 days raising a number its own methods document says to
delete. Do the deletion instead:

- **B³ precision and recall, reported separately** (Amigó et al., *Information Retrieval*
  12:461–486, 2009, prove B³ is the only extrinsic clustering measure satisfying all four formal
  constraints). Never B³ recall alone: **merging monotonically raises B³ recall and lowers B³
  precision**, so recall alone rewards coarsening.
- **CEAF** (Luo, HLT/EMNLP 2005) forces a one-to-one alignment, so 183 concepts against 46 gold
  entities is charged as precision error. **This is the metric under which the family layer should
  genuinely outperform the concept layer** — and therefore the honest justification for having built
  it, in place of v1's recall argument, which is arithmetically impossible.
- **AMI / ARI**, not bare NMI: Vinh, Epps & Bailey (*JMLR* 11:2837–2854, 2010) prove mutual
  information carries a strong monotone bias toward more clusters, exactly our regime (547
  instances, 183 clusters).
- **Never MUC** — Luo (2005) shows it favours systems producing fewer entities and can score a worse
  system higher.

### Step 6 — Set the budget guard the config already declares ($0)

`config/models.yaml` has `budget.max_usd_per_full_run: null`. Set it; add a pre-flight balance check
and a running tally that halts cleanly at 90%. **This is what would have prevented all three lost
runs** — not retry, and not LangGraph.

### Step 7 — The trivial baseline, without which the contribution is unfalsifiable (~$2)

What does **one gpt-5.5 call** — *"here are 28 papers, write a realist review"* — score on these same
metrics? And what does the pipeline score with a **generic entity schema** in place of the realist
ontology?

If a single call reaches 33/46, the entire multi-agent apparatus buys four entities, **and that is
the paper's actual result**. Without this ablation, "agentic realist synthesis framework" is not a
falsifiable claim, and a methods reviewer will say so.

### Step 8 — Two human coders, 8–10 papers, blind (human calendar time)

Unchanged from v1 and still the largest single blocker. Without a human–human ceiling every
agreement-style number is uninterpretable. Use **positive specific agreement / F**, not Cohen's κ,
for the span-extraction layer (Hripcsak & Rothschild, *JAMIA* 12:296–298, 2005 prove κ is
undefined where there is no fixed count of negatives); Krippendorff's α with a bootstrap CI plus
Gwet's AC1 for the fixed-category role assignment. Tooling exists and is unused: `res gold-template`.

### Step 9 — Pre-register, then run once ($0)

Fix, in advance: the primary metric, the concept layer it is computed at, the alignment rule (1:1,
1:n, n:m), the analysis plan, and the MDE. Disclose **how many times** the pipeline was evaluated
against the benchmark, and report all runs rather than the best. This is the single most effective
and lowest-cost safeguard against the §1 selection bias.

---

## 3. What we will NOT do, and why

### Embedding-based concept clustering — **dropped**

- It cannot raise coverage recall (§0, arithmetic).
- There is **no published head-to-head** showing embedding ER beats LLM-batch clustering for concept
  consolidation. KGGen (Mo et al., NeurIPS 2025, arXiv:2502.09956) uses LLM clustering deliberately
  and beats GraphRAG 66.07 vs 47.80 on MINE — but never ablates the clustering component, so it is
  not evidence about this choice either way.
- The documented failure mode of embedding clustering is **over-merging**: cosine similarity
  measures relatedness, not equivalence, and agglomerative linkage adds transitive chaining. Our
  E02/E03 collapse is this failure already occurring.
- The merge is also **role-conditional**, which a global pass cannot respect: Context 6 vs gold 5 and
  Mechanism_Resource 27 vs 13 are too fine, but **Mechanism_Response 6 vs 15 and Outcome 8 vs 13 are
  already too coarse**. A global merge damages two of four roles.

**What survives**: v1's diagnosis of `_batched_cluster` — alphabetical sort, batches of 40,
cross-batch merge only on byte-identical canonical labels — is correct and is the best paragraph in
v1. The fix is not embeddings; it is blocking by role *and* by polarity so antonyms land in the same
batch for **explicit adjudication** rather than silent merging. Cheap, and it addresses the E02/E03
failure directly.

### Hierarchical community summarisation as a retrieval mechanism — **dropped**

The independent evidence does not support it. Han et al. (arXiv:2502.11371) find plain RAG beats
Community-GraphRAG on detail-oriented and single-hop queries, and that **Global mode specifically
collapses on unanswerable queries (19.27% vs 80.07% for Local)** while costing 7,702 s to build
against 135 s. GraphRAG-Bench (arXiv:2506.02404) finds some GraphRAG methods score *below* a
no-retrieval baseline, and that tree-based RAPTOR beats Microsoft GraphRAG. Edge et al.
(arXiv:2404.16130) is a technical report whose evidence is LLM-judged win rates with no human
evaluation — the same judge protocol whose reliability is the subject of §1.

**But our use is different, and this must be said explicitly rather than glossed.** Our 8 Leiden
communities are an **analytic output** read by a human, not a retrieval index. The negative
retrieval evidence is therefore not evidence against our use. **Justify Leiden on its own terms** —
Traag, Waltman & van Eck (*Scientific Reports* 9:5233, 2019) guarantee well-connected communities,
which Louvain does not — and validate the communities against Richmond's own thematic groupings.
Do **not** cite Edge et al. as support.

One correction to v1 that survives: our Leiden layer is **8 communities against 28 gold mechanisms —
3.5× too coarse**, the opposite of v1's framing. Multi-resolution Leiden is worth exploring for that
reason, not because the system is "too fine".

### LangGraph / LangChain / the `graphrag` package — **deferred indefinitely**

- **No evidence orchestration frameworks improve output quality.** Dennis et al. (arXiv:2604.27891,
  2026) compare LangGraph, CrewAI, ADK and Semantic Kernel against simply putting the procedure in
  the context window and find in-context prompting performs comparably or better — and note that no
  controlled study had previously made that comparison. Cemri et al. (ICLR 2025, arXiv:2503.13657)
  open by observing that multi-agent gains on popular benchmarks "are often minimal", and their
  14-mode failure taxonomy catalogues failures **introduced by** the orchestration layer.
- The v1 case rested on retry (false — the SDK retries) and checkpointing (already built as
  `--resume` at the study grain, the only grain a stateless per-study loop has).
- **Parallelism is real and is 15 lines** of `ThreadPoolExecutor` — with a caveat v1 missed: parallel
  execution makes the *observed* failure worse, because five studies die mid-flight on
  `insufficient_quota` instead of one at a clean boundary. Do Step 6 first.
- **Do not adopt the `graphrag` package.** Its pipeline carries a generic entity/relation schema with
  no realist ontology, no mandatory verbatim quote and no character spans. We would lose the
  span-grounded evidence layer, which is the strongest thing this project has.

**The one legitimate argument for an orchestration framework** is reproducibility and auditability —
"every run checkpointed, every node's inputs and outputs logged, re-executable from any stage." That
is a transparency argument for a methods paper, not a quality argument, and it must be written that
way. Any sentence implying LangGraph made the extractions better is unsupported.

---

## 4. What is missing from both v1 and this document, and must be fixed

1. **No held-out set, and no second review.** Every number comes from the same 28 papers against one
   benchmark. A reviewer's first question is "where is your test set?" The strongest available
   answer is a **second published realist review with a figure-level programme theory**, coded the
   same way and run end-to-end with frozen settings. Without it the claim is "we fit Richmond", not
   "we do realist synthesis". **This is the largest methodological hole in the project.** Do not
   split n = 28 — annotate additional papers outside Richmond's 28 as the development target and
   keep the 28 frozen.
2. **The benchmark's own reliability is unmeasured.** Richmond's Figures 1–3 have no text layer and
   were transcribed by one person from rendered page images, with no second pass and no
   inter-transcriber agreement — and the gold was revised v1→v2→v3 *after* numbers were published. A
   second independent transcription of Figures 2–3 with agreement reported is a day's work and
   closes an obvious line of attack.
3. **No multiplicity control and no primary outcome.** Six outcome measures × five variants with no
   pre-specified primary and no correction: at α = .05 over 30 comparisons, ~1.5 false positives are
   expected, which given the MDEs in §1 fairly describes everything such a design would find.
4. **The response cache proposed in v1 is a trap.** Keying on `(model, prompts, schema, seed)` makes
   repeat runs *look* deterministic by replaying a frozen draw — hiding the exact variance Step 1
   exists to measure. And in an A/B the baseline arm may hit cache while the variant misses, making
   cache status a confound. If a cache is built: **all-or-nothing per comparison, and disabled for
   every run used to estimate variance.**
5. **Judge family is confounded with judge capability.** `self_preference_gap` is −0.309 to −0.444
   across all four runs — the independent judge (`gpt-4.1-mini`) is consistently the *more generous*
   one, against a composer that is `gpt-5.5`. That is not self-preference; it is a capability
   difference. A panel of "disjoint families" at mixed capability reproduces the confound. Judges
   must be **capability-matched**, or anchored to human ratings (Step 8). Also correct for judge
   sensitivity/specificity against a human-labelled calibration subsample (arXiv:2511.21140, ICML
   2026).
6. **Two documents in this repo now give two orders of work.** `VERIFICATION_PROTOCOL.md` §6 already
   contains a prioritised list — humans → prediction-powered inference → judge panel → B-cubed →
   RAMESES fidelity → conditional-bias check → pre-register. v1 reversed it without argument. **This
   plan is now consistent with it**; if they diverge again, the protocol wins.

---

## 5. The order

```
Step 1  measure judge variance            ~$5    ← nothing is interpretable before this
Step 2  graph fingerprint in the report   $0
Step 3  error taxonomy for the 51 flags   $0
Step 4  score both concept layers         ~$1    ← refutes or confirms v1's W1 for a dollar
Step 5  B-cubed / CEAF / AMI              ~$2
Step 6  budget guard                      $0
Step 7  trivial baseline + ablation       ~$2    ← without it the contribution is unfalsifiable
Step 8  two human coders                  human calendar time — START NOW, in parallel
Step 9  pre-register, then run once       $0
```

**Total API cost: about $10.** v1 proposed roughly $36 and 8–11 days of engineering for changes
whose premises were false and whose effects the design could not have detected.

**Not on the list, and deliberately:** embedding clustering, hierarchical summarisation for
retrieval, LangGraph, LangChain, the `graphrag` package. Each was examined against the literature
and against this repository's own artifacts, and none survived.
