# Verification Protocol

> **The question this document answers.** *"How do you verify this? Against what? With what
> statistic? How do you know the result is trustworthy?"* — asked by Prof. Wei Zheng, by the
> VinUni panel, and by every reviewer this work will meet.
>
> `OUTPUT_AND_VERIFICATION.md` reports **what our numbers currently are**. This document states
> **why those are the right numbers to compute**, grounded in the published methodology of
> systematic-review automation, qualitative-coding reliability, knowledge-graph evaluation and
> LLM-as-judge validity — and it states, item by item, what is still missing before any of it can
> be called validated.
>
> Written 2026-09-23 against gold `v3` and verification run `verify-d72550c4`.

---

## 1. The claim we are actually making

The single most damaging thing this project could say is *"the machine reproduces Richmond."*
Three separate findings in the literature make that claim indefensible:

- A human gold standard is **instrument-dependent**. Hodgkinson, Maule & Bown (2004,
  *Organizational Research Methods* 7(1), 3–26) show that how a causal map is elicited materially
  changes the map. Richmond's Figures 2 and 3 are one team's rendering, not the truth.
- A human gold standard is **incomplete**. Tan et al. (2022, EMNLP, *Revisiting DocRED*) re-annotated
  a curated relation-extraction benchmark and gained **≈13 F1 with no model change** — the missing
  points were the benchmark's, not the model's.
- Human consensus is **not ground truth**. Liu et al. (2026, arXiv:2607.28890) had an independent
  expert blindly adjudicate 855 human-vs-LLM coding pairs: preference was 51.5% human / 48.5% LLM,
  *p* = 0.537 — statistically indistinguishable — and for several codes the human consensus encoded
  a shared bias the expert rejected.

So we make three separable claims, each with its own warrant, and we never let one carry another:

| | Claim | Warrant | Status |
|---|---|---|---|
| **C1** | The pipeline is **faithful**: nothing enters the knowledge graph that is not in a source paper | Deterministic measurement, plus a human audit sample | **Measured.** 92.8% resolve to a verbatim span (95% CI 90.3–94.9) |
| **C2** | The pipeline is **non-inferior to a human coder** on the operations where agreement is a coherent idea (screening, CMOC slot coding) | Agreement statistics with intervals + a pre-specified non-inferiority margin | **Screening measured; CMOC coding NOT YET — no human coder has coded anything** |
| **C3** | The pipeline's output is **in measurable correspondence** with a published human synthesis at the interpretive level | Structured correspondence + blind expert adjudication; explicitly *not* an accuracy claim | **Partially measured, model-judged only** |

The sentence to say out loud when asked:

> *We do not claim the machine is correct. We claim it is faithful to its sources — which is
> deterministically verifiable — non-inferior to a human coder on the operations where agreement
> is a coherent concept, and in measurable correspondence with a published human synthesis where
> it is not. And we report the human ceiling for every one of those.*

---

## 2. Why each metric is the metric

### 2.1 Screening — sensitivity, and why it cannot stand alone

Sensitivity against the 28 included studies is the field's accepted primary metric (Cohen et al.,
2006, *JAMIA* 13(2), 206–219, which introduced WSS@95%). Our harness reports it from **one named
screening run** with the denominator taken from the study registry, not from our own output — both
were wrong before 2026-09-23 (see §5).

Two honest limits, stated because a reviewer will find them otherwise:

1. **There are no true negatives.** Every corpus study is a gold include, so a screener that
   returned `include` unconditionally would score 100%. Specificity is measured separately against
   a 72-paper distractor pool we constructed, because Richmond did not publish their excluded
   studies. That test shows the system discriminates; it is not a match to Richmond.
2. **The human comparator is not perfect.** Wang et al. (2020, *PLOS ONE* 15(1), e0227742) analysed
   329,332 human screening decisions and found a combined false-inclusion + false-exclusion rate of
   **10.76% (95% CI 7.43–14.09)** — about one error per nine abstracts. Their own conclusion is that
   automation reaching similar error rates would be adequate for implementation. This converts the
   question from *"is it perfect?"* to *"is it non-inferior?"*, which is the answerable one.

Madeyski, Kitchenham & Shepperd (arXiv:2511.12635) audit the LLM-screening literature: only 24% of
studies publish a full confusion matrix and none of five claiming workload savings quantified
false-negative cost. Publishing ours costs nothing and puts the work in the top quartile of current
reporting practice.

### 2.2 Extraction faithfulness — three tiers, never one number

Every extracted element carries a verbatim quote and a character offset. What counts as "resolved"
is not one thing, so it is reported as three:

| Tier | What it means | Count |
|---|---|---|
| **exact** | The stored quote is character-for-character the text at `[start, end)` | 48 |
| **normalized** | Identical after undoing PDF line-break hyphenation, whitespace collapse and typographic quote folding | 432 |
| **fuzzy** | A `difflib` longest-common-block covering ≥70% of the quote | 19 |
| **unresolved** | Logged, surfaced at HITL-2, never hidden | 18 |

The headline is **exact + normalized = 92.8% (95% CI 90.3–94.9)**. Normalization here undoes a
typesetting artefact, not a difference in wording, so it is legitimately part of "verbatim"; the
fuzzy tier is not, and is excluded. Reporting `exact` alone (9.3%) would be misleading in the other
direction, because PDF extraction inserts hyphens the author never wrote.

This metric is the operationalisation of **AIS — Attributable to Identified Sources** (Rashkin et
al., 2023, *Computational Linguistics* 49(4), 777–840), which is the accepted definition of "this
statement is supported by the cited source" and which supplies the human annotation protocol for
validating it. The natural refinement is FActScore-style atomic decomposition (Min et al., 2023,
EMNLP): break the programme theory into atomic C→M→O claims and score each for support.

> **Correction of record.** Until 2026-09-23 this project reported *"citation faithfulness
> (automated, exact): 96.9%"*. That figure conflated all three tiers under the word *exact*, in
> direct violation of the tiering `span_repair.py` promises. The corrected, tiered figures are
> above.

### 2.3 Concept coverage — a model judgement, reported as one

An LLM judges whether one of our canonical concepts expresses the same construct as each of
Richmond's. It is sampled K=3 and majority-voted, within-role first and then a role-crossing
recovery pass that is voted the same way.

Two things make this honest rather than decorative:

- **Roles are compared under Richmond's scheme, not ours.** Richmond's CMOC vocabulary has four
  roles; our ontology splits their single *mechanism resource* column into `Intervention` and
  `Mechanism_Resource` (following Dalkin et al., 2015, *Implementation Science* 10:49, which
  Richmond themselves adopt). Scoring role agreement against *our* finer scheme marked the system
  wrong for a distinction Richmond never drew.
- **Role disagreements are reported, not smoothed.** 7 of the matches sit under a different realist
  role than Richmond used. This is **rating indeterminacy**, not error: Guerdan et al. (2025,
  NeurIPS, arXiv:2503.05965) show that forced-choice validation of judge systems selects systems
  performing **up to 31% worse** than multi-label validation when the construct legitimately admits
  more than one answer. Armstrong et al. (1997, *Sociology* 31(3), 597–606) found six human
  researchers coding one transcript agreed on theme *content* and diverged on how themes were
  *packaged* — exactly this pattern, thirty years before LLMs.

**Report as:** 38/46 like-for-like (95% CI 68.6–92.2), 45/46 with role-crossing allowed, of which 7
are role disagreements. Never the role-tolerant figure alone.

### 2.4 Relation recovery — three tiers, and one of them cannot fail

| Tier | Question | Result |
|---|---|---|
| **type-level** | Does the *pattern* (e.g. Context CONSTRAINS Outcome) occur anywhere in the graph? | 39/40 — **saturable, see below** |
| **anchored** | Same predicate, one endpoint the exact matched concept, the other of the right role | **29/40 (95% CI 56.1–85.4)** — the number to lead with |
| **strict** | Same predicate between the exact two matched concepts | 0/40 (95% CI 0.0–8.8) |

The type-level tier is near-vacuous by construction: our graph contains **8 distinct
(predicate, subject-role, object-role) patterns** and the benchmark uses **7**, so any non-trivial
extraction scores ~100%. The harness now reports that ceiling next to the score. The project
previously led with "98% of Richmond's causal patterns recovered", which is the single claim most
likely to end badly in review.

Strict recall of 0/40 is the honest floor and is **expected**, for reasons that are citable rather
than excuses: it is bounded by concept-recall squared; our canonical ids are named differently from
Richmond's; and Markóczy & Goldberg (1995, *Journal of Management* 21(2), 305–333) established that
two causal maps cannot be meaningfully compared unless the construct pool is controlled first — ours
is not, by design, because the system derives its own concepts.

For calibration: Saklad et al. (arXiv:2505.18931) built the first real-world dataset for
constructing causal graphs from academic literature and report a **best-model average F1 of 0.535**.
Text2KGBench (Mihindukulasooriya et al., ISWC 2023) is the right scoring vocabulary to adopt —
fact-extraction P/R/F1, **ontology conformance**, and **hallucination rate** — which maps almost
one-to-one onto what this harness already computes.

### 2.5 Community ↔ mechanism alignment

Our mechanisms are discovered bottom-up by Leiden community detection (Traag, Waltman & van Eck,
2019, *Scientific Reports* 9:5233) over the concept graph, then named by an LLM. Comparing them to
Richmond's hand-authored mechanisms is a **partition comparison**, and the current recall-style
metric is the weakest thing in the harness.

The correct replacement is **B-cubed precision/recall/F** (Bagga & Baldwin, 1998; Amigó et al.,
2009, *Information Retrieval* 12(4), 461–486, which proves B-cubed is the only extrinsic clustering
measure satisfying all four formal constraints and extends it to overlapping clusterings — necessary
here, since a concept can belong to more than one realist mechanism). **Do not report bare NMI:**
Jerdee, Kirkley & Newman (2025, *Nature Communications* 16) show conclusions about which algorithm
is best can flip under a chance-corrected measure.

### 2.6 Programme-theory correspondence — currently not a defensible number

The same programme theory, the same five gold chains, two judges from different model families:

| Chain | Independent judge (gpt-4.1 family) | Same-family judge (gpt-5.5, the composer) |
|---|---|---|
| PTS1 | 1.00 | 0.86 |
| PTS2 | 0.90 | 0.28 |
| PTS3 | 0.82 | 0.42 |
| PTS4 | 0.73 | 0.64 |
| PTS5 | 0.90 | 0.60 |
| **mean** | **0.87** | **0.56** |

**A gap of 0.31 on a 0–1 scale, from identical inputs.** That spread *is* the result. Reporting
either number alone would be indefensible, and the direction is itself informative: the gap runs
**opposite** to the self-preference hypothesis (Panickssery et al., 2024, NeurIPS,
arXiv:2404.13076, who show GPT-4 self-recognises at 73.5% and that self-recognition *causes*
self-preference). Here the independent judge is the more generous one, which points at judge
capability rather than vanity — consistent with Bavaresco et al. (2025, ACL), whose JUDGE-BENCH
across 20 tasks found the best judge reached only **mean κ = 0.28 ± 0.32** against human labels, and
with Szymanski et al. (arXiv:2410.20266), where subject-matter experts agreed with LLM judges only
**64–68%** of the time on expert-knowledge tasks. A realist review is squarely in that regime.

Three fixes, all pending:

1. **A panel, not a judge.** Verga et al. (2024, PoLL, arXiv:2404.18796) show a panel of
   deliberately disjoint model families beats a single GPT-4 judge on every dataset (κ vs human
   0.763 vs 0.627 on NQ) at 7–8× lower cost, and note that *"the highest positive delta for each
   individual model being scored occurs when it is judged by itself."*
2. **Decompose the scalar.** One 0–1 number invites style-over-substance scoring (Wu & Aji, 2023,
   arXiv:2307.03025; Feuer et al., 2025, ICLR, where style correlates with the judge's own score at
   R = 0.999 while factual errors are penalised only 13% of the time). Replace it with atomic-claim
   support plus a multi-dimension rubric.
3. **Anchor to humans and correct statistically.** See §3.

### 2.7 A note on what "3 samples" does and does not buy

The harness samples each LLM judge three times and majority-votes. That is a *repetition-stability*
measure (Shi et al., 2025, AACL, arXiv:2406.07791), and it is worth keeping. It is **not** three
raters. Prescott et al. (2024, *JMIR AI* 3:e54482) found ChatGPT–Bard agreement of 100% (inductive)
and 83% (deductive) while each agreed with humans at only 36–47%; Dai, Xiong & Ku (2023, Findings of
EMNLP) found human-with-LLM κ of 0.87 that collapsed to 0.54 against an independent third coder.
Correlated model errors inflate agreement without improving correspondence to anything external.

---

## 3. What is still missing — the honest gap list

Nothing below is a nice-to-have. Each is a specific reason a reviewer could reject a claim.

### 3.1 No human has coded anything (blocking C2)

There is no human–human ceiling, so every agreement-style number here is uninterpretable. Xiao et
al. (2023, IUI) report GPT-3 at κ = 0.61 — which reads as a success until you see the expert–expert
ceiling of κ = 0.88 on the same items.

**What to run.** Two coders, blind to machine output, code a **design-based random sample of 8–10 of
the 28 papers (~25–35%)** into the typed CMOC schema. Compute **human–human agreement first**, then
machine-vs-each-human.

**Which statistic.** Not Cohen's κ. For span/CMOC extraction there is **no well-defined number of
negative cases**, and Hripcsak & Rothschild (2005, *JAMIA* 12(3), 296–298) prove that in exactly this
situation the mean F-measure between coder pairs is numerically identical to **positive specific
agreement**, which is the appropriate reliability statistic. This resolves the standing objection
*"you cannot compute κ on 91 CMOCs."* For the fixed-category judgements (realist role assignment),
report **Krippendorff's α** with a bootstrap CI (Hayes & Krippendorff, 2007; thresholds α ≥ .800
firm, .667–.800 tentative) **alongside Gwet's AC1** (Gwet, 2008, *BJMSP* 61(1), 29–48), because
prevalence is skewed and κ is paradoxical there (Feinstein & Cicchetti, 1990) — at 10.5% prevalence
Wongpakaran et al. (2013) measured κ = .604 where AC1 = .857 on the same data.

**How many papers.** Plan for a target CI width on α, not for significance (Rotondi & Donner, 2012,
*J Clin Epidemiol* 65(7), 778–784; R package `kappaSize`). Note the inversion worth writing up: the
qualitative convention of double-coding 10–25% exists because *human* coding is the expensive half;
here the machine codes 100% and the **human subsample is the limiting resource**, so the design
question becomes *what fraction must a human code to bound the error at stated precision* — which,
as far as this review of the literature found, nobody has posed.

### 3.2 The per-paper "gold" is AI-coded (blocking C2 and C3)

`gold/per_paper_gold/` was produced by a model, blind and cross-family, and is honestly labelled —
but the literature is unambiguous that this cannot be a gold standard. Pangakis et al. (2023,
arXiv:2306.00176): any automated annotation process using an LLM must be validated against
human-generated labels. Egami et al. (2023, NeurIPS, arXiv:2306.04746): direct use of surrogate
labels produces substantial bias and **invalid confidence intervals even at 80–90% surrogate
accuracy**. Ashwin, Chhabra & Rao (2025, *Sociological Methods & Research*): LLM annotation errors
are **not random with respect to subject characteristics**, so downstream comparisons are biased,
not merely noisy — and this survives high average accuracy.

**Keep it, relabel it as pre-annotation** shown to humans *after* their first independent pass, and
run the two-coder study. The `res gold-template` tooling already exists and is unused.

### 3.3 The model-judged headlines carry no valid interval (blocking C3)

Every proportion here now carries a **Clopper–Pearson exact interval** (1934, *Biometrika* 26(4),
404–413), chosen because our denominators are small (28, 40, 46) and two headline values sit exactly
at the boundary (28/28 and 0/40) where the Wald interval degenerates. But those intervals cover
**sampling variation in the counting only**. They say nothing about judge bias.

The fix is **prediction-powered inference** (Angelopoulos et al., 2023, *Science* 382(6671),
669–674): human-label a probability sample of the machine-judged items, estimate a rectifier on it,
and obtain confidence intervals that are **provably valid regardless of judge bias**. It is what
lets the paper write *"the LLM judged all 46 gold concepts; two humans independently judged a random
20; the reported recall and its CI are valid whatever the judge's bias."* Confidence-driven
inference (Gligorić et al., 2025, NAACL) cuts the human labels needed by >25% by escalating only
low-confidence items — which is architecturally identical to our existing HITL checkpoints.

Cite the ceiling pre-emptively: Dorner, Nastl & Hardt (2025, ICLR, arXiv:2410.13341) prove that when
the judge is no more accurate than the system being evaluated, **no debiasing method can reduce the
required ground-truth labels by more than half**. An LLM judge is a variance-reduction device, not a
substitute for human labels.

Use **clustered standard errors** — 91 CMOCs drawn from 28 papers are not 91 independent
observations (Miller, 2024, arXiv:2411.00640).

### 3.4 Nobody has tested whether disagreement is *systematic*

Beyond average agreement, the question Ashwin et al. (2025) force is whether machine–human
disagreement is **independent of the covariates the synthesis conditions on** — study design,
discipline, country, year, realist role, polarity. If agreement is lower on the psychology studies
than the medical ones, the programme theory is skewed even at high average agreement. No current
qualitative reporting guideline requires this test. Running it is a contribution in itself.

### 3.5 No fidelity-to-method score

The RAMESES **quality standards** (Wong et al., 2014) score realist syntheses across 8 domains on
Inadequate / Adequate / Good / Excellent. Their *Inadequate* descriptors name the failure modes in
operational language — *"programme activities or strategies are confused with mechanisms"*;
*"outcomes are assumed to be caused by the intervention"*; *"data extraction is undertaken
mechanically and with no attention to how the data informs the review."* That last one is precisely
what a hostile reviewer will say about an LLM pipeline. Pre-empt it by scoring against it, rated by
≥2 realist-trained humans blind to which outputs are machine-produced.

Mukumbang et al. (2025, *PLOS ONE* 20(9), e0332250) are developing **QUATRES** precisely because
*"little comprehensive guidance exists on effectively assessing the quality of realist syntheses."*
The tool does not exist yet. That is the gap this project can fill.

### 3.6 Reporting compliance

Comply, and say so, with: **PRISMA 2020**; **RAMESES publication standards for realist syntheses**
(Wong et al., 2013, *BMC Medicine* 11:21 — all 19 items, mapped in an appendix; note that item 11's
*demi-regularities* requirement means our `demi_regularities` table is literally a reporting-standard
item); **RAMESES II** (2016, *BMC Medicine* 14:96), which mandates explicitly labelling what is C, M
and O — so our typed ontology is method-mandated, not a design preference; **ENTREQ** (Tong et al.,
2012), which names realist synthesis in scope; **RAISE 1–3** (OSF 10.17605/OSF.IO/FWAUD,
version-pinned) and the four-organisation position statement (Flemyng et al., 2025, published
simultaneously in *Cochrane DB Syst Rev*, *Campbell Systematic Reviews*, *JBI Evidence Synthesis*
and *Environmental Evidence*), whose binding requirement is that any AI use making or suggesting
judgements be fully and transparently reported; and **TRIPOD-LLM** (Gallifant et al., 2025, *Nature
Medicine* 31(1), 60–69).

Disclose model name *and* snapshot, temperature, seed, context length, deployment mode, complete
prompts, and number of runs. Kempny et al. (2026, *BMC Med Res Methodol* 26:137) found **75% of
published LLM-qualitative studies report no model parameters at all**; full disclosure is the
cheapest credibility gain available.

---

## 4. Positioning: there is no prior art, and that is the opening

No published or preprint work automates or semi-automates realist synthesis, CMOC extraction, or
programme-theory construction. The two nearest pieces both come from the RAMESES inner circle and
neither reports an evaluation design:

- **Hunter, Booth & Wood (2026)**, *BMC Med Res Methodol* 26(1), DOI 10.1186/s12874-026-02814-3 —
  AI for *searching only* inside a realist review; concludes AI is "a valuable adjunct rather than
  a substitute."
- **Owen-Boukra et al. (2026)**, *BJGP Open* 10(1), DOI 10.3399/BJGPO.2025.0073 — a realist review
  protocol embedding two Studies-Within-A-Review asking how AI might *"support data extraction and
  analysis in future realist reviews."* Co-authors include **Geoff Wong** (RAMESES lead) and
  **James Thomas** (RAISE lead). **The protocol poses the question and defers the evaluation design
  entirely.** That is the shape of the gap, in the field's own words.

A second, independent gap: **no published study reports inter-rater reliability for CMOC
extraction.** Richmond is the pattern — `RICHMOND_CONCLUSIONS.md` §3.4 records that "initial CMOC
coding was undertaken by AR and all 28 articles were checked for consistency by another reviewer",
with **no agreement statistic reported**. (The paper says something slightly different at p. 717:
"RP, SG and NC reviewed *a sample* of full texts." Both statements are in the source; the honest
answer to "how many reviewers checked each paper?" is "the paper says both things.") So there is no
psychometric baseline for an automated extractor to be measured against. **Creating one is the
contribution.**

Frame the study as a retrospective **Study Within A Review**, the vehicle the field has settled on —
Arno et al. (2022, *Annals of Internal Medicine* 175(7), 1001–1009), the only RCT of review
automation, which established non-inferiority of ML-assisted risk-of-bias assessment (risk
difference −0.014, 95% CI −0.093 to 0.065); Gartlehner et al. (2025, *Annals* 178(12), 1763–1771),
a prospective SWAR over 9,341 data elements finding AI-assisted extraction **more** accurate than
human-only (91.0% vs 89.0%); and CESAR (Gartlehner et al., 2026, *J Clin Epidemiol* 198:112390), the
adaptive-platform SWAR that is the current state of the art in evaluation design.

Pre-empt the n=1 objection rather than waiting for it: SESR-Eval (arXiv:2507.19027) found that
**between-review variance exceeds between-model variance**, so no single-review benchmark can
establish general performance — for anyone. Saying so is honest rather than damaging. And
**pre-register the evaluation protocol with the non-inferiority margins fixed in advance**, as Rose
et al. (2025, *Cochrane Evidence Synthesis and Methods* 3(5), e70048) did; it is the cheapest
available defence against *"you tuned until it looked good."*

---

## 5. Corrections of record (2026-09-23)

Four defects were found in what the harness was actually scoring, and four in how it scored. All are
fixed; `RES_GOLD=v1` reproduces every earlier number exactly.

**The benchmark** (`scripts/build_richmond_gold_v3.py`):

1. `gold/richmond_gold.json` — the file every metric loaded — was **byte-identical to v1**
   (MD5 `c3edd836964f107ad34de2a80ebc7b35`), so the corrections `RICHMOND_CONCLUSIONS.md` §6
   claimed had been applied never reached the scorer. **All five** v1 programme-theory chains were
   cross-context contaminated and every one routed through `E19`, a Figure-2 placeholder belonging
   to one context and carrying no relation. §6 admitted only two.
2. E07–E18 were typed `Intervention` although Richmond tags each *"(Mresource)"*. Role agreement is
   now judged under Richmond's four-role scheme.
3. E21 and E43 were typed `Outcome` against the paper's own explicit *"(Mresponse)"* tags.
4. E01 is the review population from the Conclusions, not one of the five contexts; it appears in
   neither figure and in no relation. Scored denominator is **46, not 47**. Also:
   `reference_to_study_id["28"]` mapped Eva 2007 to two studies; R37–R40 are transitive shortcuts
   Figure 3 never draws, now flagged `derived`.

**The harness** (`verification/metrics.py`):

5. **Citation faithfulness conflated three tiers under the word "exact."** Now tiered (§2.2).
6. **Entity coverage reported a headline above its own range** (91.5% against a per-sample range of
   76.6–85.1%) because the cross-role recovery pass ran **once, unvoted**, after a 3-sample majority
   vote. It is now sampled and voted identically. Hallucinated and duplicate codes are discarded.
7. **Screening blended six runs** and took its denominator from its own output. Now one named run,
   denominator from the registry.
8. **The theory judge graded its own model family's work.** Now scored by both, with the gap
   reported.

**And one in the exports:** `scripts/export_outputs.py` wrote CSVs in which **every data row was a
repeat of the header** (`pandas.read_sql` over a psycopg `dict_row` connection turns each row into
its keys). The raw-output bundles shipped in `outputs/submission/` and `outputs/submission_v2/`
contain those empty files.

---

## 6. The order to do the remaining work in

1. **Two human coders, 8–10 papers, blind.** Unblocks C2, the human ceiling, κ/α/AC1, and the
   per-paper gold. Nothing else can substitute for it.
2. **Prediction-powered inference over a human-labelled probability sample** of the concept matches.
   Converts the weakest numbers into statistically valid ones.
3. **Judge panel + decomposed theory score**, replacing the single scalar.
4. **B-cubed for community alignment**, replacing recall.
5. **RAMESES 8-domain fidelity rating** by two realist-trained humans.
6. **The conditional-bias check** (§3.4).
7. **Pre-register**, then write, against the reporting block in §3.6.

---

*Every figure in this document is reproducible: deterministic metrics from
`PYTHONPATH=src python -m res_pipeline.cli status`, scored metrics from `res verify`
(`RES_GOLD=v1` for the historical numbers), and the reader-facing rendering from
`res export-results`.*
