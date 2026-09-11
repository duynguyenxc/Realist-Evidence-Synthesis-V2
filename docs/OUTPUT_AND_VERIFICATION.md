# Output and Verification — the definitive answer

> **The question this document exists to answer** (asked by Prof. Wei Zheng and the VinUni
> reviewers, unresolved for eight months): *What exactly does our system produce, what does that
> output look like, and HOW do we verify it — how do we lay it beside what Richmond's human team
> produced and show, with numbers, how close we came?*
>
> This is the single reference for that answer. Every number below is either (a) recomputed live
> from the database on the day of writing, or (b) taken from a named verification run whose
> deterministic anchors match the live database exactly. Where a number is soft, model-judged, or
> not yet defensible, this document says so plainly. Nothing here is estimated or aspirational.
>
> Generated 2026-09-10. Canonical extraction run `extract-531966df`; synthesis run
> `synth-e1c81001`; verification run `verify-15b50105`. Human standard: `gold/RICHMOND_CONCLUSIONS.md`
> and `gold/richmond_gold_v2.json`.

---

## 0. How to read this in one minute

Richmond et al. (2020) is a *realist review*: five human reviewers read 28 studies and produced,
by hand, a chain of reasoning — **for which students (Context), what teaching (Intervention)
triggers what change in the learner (Mechanism), producing what result (Outcome)** — organised
around **five student contexts**, with two figures (Fig 2, Fig 3) and a written programme theory
whose headline is *"the student is key."*

Our system takes the **same 28 papers** and runs the same realist operations automatically
(search → screen → extract Context–Mechanism–Outcome configurations → cluster across studies →
write a programme theory), with a human able to intervene at four checkpoints. It produces the
**same *kinds* of artefacts** Richmond produced. Verification = putting each of our artefacts
beside the matching Richmond artefact and measuring the overlap with a stated statistic.

The honest headline, in one line each:

- **Screening** — we recover **all 28** of Richmond's included studies (26/28 automatically,
  the last 2 after one human check). Deterministic.
- **Extraction** — every extracted claim is anchored to a **verbatim quote in the source**
  (96.9% resolve to an exact character span). Deterministic.
- **Concept coverage** — we recover **37 of Richmond's 47 figure entities** where the realist
  role also matches (43/47 if we allow role-crossing). Model-judged, with a stated range.
- **Causal structure** — we recover **the causal *pattern* of 39 of 40** Richmond relations
  (e.g. "Context constrains Outcome"); we recover **almost none at the exact-concept level**
  (0/40 strict). This gap is real and is the honest headroom item — Section 4 explains why.
- **Programme theory** — the system independently rewrites Richmond's core finding ("the same
  resource helps or hinders depending on the student") at **0.54 correspondence** on a 0–1 scale.
  Model-judged; a human rating is still required.

If you read nothing else, read **Section 3 (the matrix)** and **Section 4 (what each number
honestly means)**.

---

## 1. What Richmond produced (the human standard we verify against)

Full sentence-by-sentence grounding is in [`gold/RICHMOND_CONCLUSIONS.md`](../gold/RICHMOND_CONCLUSIONS.md).
The machine-readable operationalisation is [`gold/richmond_gold_v2.json`](../gold/richmond_gold_v2.json).
In brief, Richmond's published outputs are:

| Richmond artefact | What it is | Size |
|---|---|---|
| Inclusion list | The studies that survived screening | **28 studies** |
| Five student contexts | The organising spine of the review (§3.2.1–3.2.5) | 5 contexts |
| Figure 2 | Programme-theory diagram: intervention → mechanism → outcome, per context | transcribed as entities/relations |
| Figure 3 | The dual-process (analytical / non-analytical) mechanism diagram | transcribed as entities/relations |
| Entities in Fig 2 & 3 | Contexts, interventions, mechanism-resources, mechanism-responses, outcomes | **59** (47 in the core set E01–E47; 12 Fig-3 supplements E48–E59) |
| Relations in Fig 2 & 3 | The typed causal arrows between them | **61** (40 in the core set R01–R40; 21 Fig-3 supplements) |
| Programme-theory statements | The written C→M→O logic for each of the 5 contexts (PTS1–PTS5) | 5 chains, mapped to the 28 studies by Richmond's own reference numbers |
| Written conclusions | "The student is key"; dual-process reasoning; the expertise-reversal effect | narrative |

> **Why two sizes (47/40 vs 59/61).** The scored benchmark uses Richmond's **core** figure set
> (47 entities, 40 relations = `gold/richmond_gold.json`), which every historical number is
> reproducible against. `richmond_gold_v2.json` adds the 12 Fig-3 supplement entities and the
> per-context study membership (Richmond's reference numbers 8–58 mapped to our study IDs S001–S028)
> for the richer side-by-side reader view. The two are kept separate on purpose so no score silently
> shifts. One provenance note: Richmond ref 28 (Eva 2007) maps to two of our metadata records
> (S004, S005) — flagged for a manual check, does not affect any context count.

---

## 2. What our system produces (the actual output, with live counts)

Everything the pipeline computes lives in **one PostgreSQL database (`realist_synthesis`) — the
single source of truth.** Files under `outputs/` are *exports* of that database for reading and
sharing. Counts below are the live row counts of the canonical run on 2026-09-10.

### 2.1 The primary output — the knowledge graph and CMOCs (in the database)

| Output artefact | Table | Live count | Plain-language description |
|---|---|---|---|
| **CMOCs** | `cmocs` | **91** | Context–Mechanism–Outcome configurations: one realist "if [context] then [outcome] because [mechanism]" statement per row, each tied to the study it came from and a plain-English `narrative_statement`. Polarity: 56 positive, 31 negative, 4 mixed. |
| **Entity instances** | `entity_instances` | **517** | Every Context / Intervention / Mechanism-Resource / Mechanism-Response / Outcome the extractor found, each with a **verbatim quote and character offsets** into the source text. |
| **Typed relations** | `typed_relations` | **439** | The causal arrows between entities (PROVIDES, TRIGGERS, ENABLES, LEADS_TO, CONSTRAINS). |
| **Canonical concepts** | `concept_families` | **180** | The 517 raw entities de-duplicated into 180 shared concepts (e.g. many "self-explanation" phrasings → one concept), so the same idea across papers is counted once. |
| **Emergent communities** | `conceptual_entities` | **8** | Clusters found by the Leiden algorithm over the concept graph — the system's *data-derived* mechanisms (see 2.2). |
| **Demi-regularities** | `demi_regularities` | **36** | Recurring C→M→O patterns that appear across ≥2 studies — the realist "semi-predictable patterns." |
| **Programme theories** | `programme_theories` | **10 versions** | The written synthesis; the final signed version is `theory-v2-final`. |
| **Contradictions** | `contradictions` | **14** | Where studies disagree — the raw material for the expertise-reversal finding. |
| **Human decisions** | `hitl_feedback`, `hitl_ratifications` | **28 / 17** | Every human-in-the-loop action, logged with a timestamp. |
| **Screening decisions** | `screening_decisions` | **432** | Every include/exclude/uncertain vote (multiple voters × studies + distractors). |
| **Provenance** | `audit_log`, `token_usage` | **781 / 2040** | Full audit trail and per-call token/cost accounting. |

### 2.2 The system's eight emergent mechanisms (what the graph clustering produced)

These are the `conceptual_entities` — the closest thing to Richmond's Fig-3 mechanisms, but
discovered bottom-up by the Leiden community algorithm rather than authored by hand:

1. **Structured reasoning uptake** (Mechanism-Response, 39 members)
2. **Contrastive diagnostic scaffolding** (Mechanism-Resource, 29)
3. **Reasoning-practice scaffolding** (Intervention, 25)
4. **Structured diagnostic knowledge building** (Mechanism-Response, 23)
5. **Pressure-driven case patterning** (Mechanism-Response, 18)
6. **Unguided diagnostic reasoning** (Mechanism-Response, 17)
7. **Guided self-explanation** (Mechanism-Response, 17)
8. **Error-resistant diagnostic learning** (Outcome, 12)

### 2.3 The reader-facing exports (what a human opens)

| File | Format | What it is |
|---|---|---|
| `outputs/exports/{entities,relationships,cmocs,big_concepts}.csv` | CSV | The graph as spreadsheets — open in Excel, sort, filter. |
| `outputs/lkg/*.parquet` + `manifest.json` | Parquet | The "labelled knowledge graph" for programmatic use / Neo4j load. |
| `outputs/Knowledge_Graph_Report.{html,pdf}` | HTML/PDF | The graph rendered for reading. |
| `outputs/runs/verify-15b50105/dashboard.html` | HTML | The verification scorecard as a dashboard. |
| `outputs/Richmond_Correspondence.md` | Markdown | The narrative side-by-side with Richmond. |
| `gold/richmond_gold_v2.json` | JSON | Richmond's outputs, machine-readable, for the matrix. |

### 2.4 The final programme theory, in the system's own words

The signed `theory-v2-final` opens:

> *"Across the evidence, educational interventions appear to develop undergraduate health
> professions students' clinical reasoning when they calibrate reasoning resources to the student
> context… The central programme theory is not that any single intervention is inherently
> effective; rather, **the same resource can help or hinder depending on whether it reduces
> uncertainty and supports productive elaboration, or instead overloads learners, encourages
> passive processing, or asks them to combine strategies before they have sufficient knowledge.**"*

This is, in the system's own generated prose, Richmond's *"the student is key"* plus the
**expertise-reversal effect** — reconstructed from the data, not copied from Richmond.

---

## 3. The verification matrix

This is the artefact the eight-month question was really asking for. **One row per realist review
product. Each row names Richmond's human artefact, our system artefact, how the two are compared,
the statistic, who does the judging, the current value, and the honest caveat.**

| # | Review product | Richmond's human artefact | Our system artefact | Comparison method | Statistic | Judge | Current value | Honest caveat |
|---|---|---|---|---|---|---|---|---|
| 1 | **Screening (recall)** | The 28 included studies | `screening_decisions` (combined vote) | Do we include each of Richmond's 28? | Sensitivity | Deterministic | **92.9% auto (26/28); 100% after 1 human check (28/28)** | The 2 "uncertain" were correctly routed to a human — that is the design, not a miss. |
| 2 | **Screening (precision)** | (none — Richmond didn't publish a distractor set) | screening on a 72-paper distractor pool | Do we *reject* irrelevant papers? | Specificity | Deterministic | recall-first tuning ≈76%, precision-first ≈99% (`precision-test`) | Distractor pool is *our* construction, not Richmond's; report as a tunable, not a match to Richmond. |
| 3 | **Concept coverage** | 47 entities in Fig 2 & 3 (E01–E47) | 180 canonical concepts (`concept_families`) | Does an extracted concept express the same construct as each gold entity? | Recall of 47 | **LLM semantic matcher**, K=3 majority vote | **37/47 within realist role** (per-sample range 76.6–85.1%); **43/47 (91.5%) if role-crossing allowed** | The 91.5% headline counts 6 concepts the system filed under a *different* realist role than Richmond. Report 37/47 as the like-for-like number and 43/47 as the role-tolerant number — **never the 91.5% alone.** (See §4.) |
| 4 | **Extraction faithfulness** | (implicit — Richmond quotes sources) | `entity_instances.verbatim_quote` + offsets | Does each quote resolve to an exact span in the source text? | % resolved | Deterministic | **96.9% (501/517)** | The strongest, most defensible number. The 16 unresolved are logged, not hidden. |
| 5 | **Causal structure (pattern)** | 40 relations in Fig 2 & 3 (R01–R40) | 439 typed relations | Is the gold relation's *pattern* (predicate + subject-type + object-type, e.g. Context CONSTRAINS Outcome) present in our graph? | Type-level recall | Deterministic | **97.5% (39/40)** | **Saturable**: our graph contains 9 distinct type-patterns and the gold uses only 7, so a high score is nearly guaranteed. Informative but weak on its own. |
| 6 | **Causal structure (anchored)** | R01–R40 | 439 typed relations | Same predicate, one endpoint the exact matched concept, other endpoint correct type | Anchored recall | Deterministic (given #3's matches) | **55% (22/40)** | The fairest middle tier — depends on the concept matches from row 3. |
| 7 | **Causal structure (exact)** | R01–R40 | 439 typed relations | Same predicate links the *exact two concepts* matched to the gold subject/object | Strict recall | Deterministic | **0% (0/40)** | Honest floor. Bounded by concept-recall² and by canonical-ID naming differences; near-zero is expected and is the headroom item, not a failure of the causal graph (which row 5 shows is largely present). |
| 8 | **Emergent mechanisms** | Fig-3 mechanisms (14 mechanism entities) | 8 Leiden communities (`conceptual_entities`) | Does a community express the same mechanism as a gold mechanism? | Alignment recall | **LLM matcher**, K=3 | **50% (7/14)** | Model-judged; a human mechanism-mapping is required before publication. This is the professor's named novelty (data-derived vs human-authored mechanisms). |
| 9 | **Programme theory** | PTS1–PTS5 + written conclusions | `theory-v2-final` | Structural+conceptual correspondence of each C→M→O chain | Mean correspondence 0–1 | **LLM judge (same model tier that composed the theory)** | **0.54 (range 0.50–0.56)** | **Self-judging** (see §4). Treat as indicative only; a human expert rating is mandatory before any claim. |
| 10 | **Demi-regularities** | Richmond's recurrent per-context patterns | 36 `demi_regularities` (≥2 studies each) | Qualitative — do the top patterns match Richmond's five-context story? | (narrative) | Human reading | e.g. *learner-expertise + case-based-learning → diagnostic-accuracy-gains* (6 studies) | Not yet a scored metric; currently read side-by-side. A scoreable mapping is future work. |

**Deterministic vs model-judged, at a glance.** Rows 1, 2, 4, 5, 6, 7 are **deterministic** — same
inputs, same numbers, no LLM, reproducible forever. Rows 3, 8, 9 are **model-judged** — they need
an LLM and vary run-to-run, so they are reported with K=3 sampling and a range, and each carries a
"human rating required" flag. This split is itself part of the honesty of the method.

---

## 4. What each number honestly means (and what we must NOT overclaim)

The three audits of the codebase surfaced places where a number could mislead a reviewer. They are
recorded here so the paper never overclaims.

1. **The 91.5% entity coverage must not be the headline.** The verification code runs a K=3
   majority vote *within realist role* (which gives the 76.6–85.1% per-sample range, ≈37/47), then
   adds a **single-pass** cross-role recovery step that picks up 6 more concepts the system had
   filed under a different role than Richmond. Adding a single-sample pass on top of a majority-vote
   and reporting the sum as one "majority-vote" figure inflates the headline above its own range.
   **Correct reporting:** *37/47 like-for-like (majority vote, range 76.6–85.1%); 43/47 (91.5%) when
   role-crossing matches are allowed, of which 6 are role-disagreements.* The role disagreements are
   themselves a finding (Richmond files self-efficacy/coping as *context*; our extractor files the
   same construct as a *mechanism-response*), not noise.

2. **Strict relation recall is 0/40 and that is fine — if reported with row 5.** Exact-concept-pair
   matching is bounded by concept-recall squared and by the fact that our canonical concept IDs are
   named differently from Richmond's. The defensible claim is: *the causal **structure** of
   Richmond's theory is largely recovered (97.5% of patterns, 55% anchored), while exact concept-pair
   reconstruction is the open problem.* Never quote 97.5% without also stating it is type-level and
   saturable, and never quote 0% without row 5.

3. **The programme-theory judge currently grades its own work.** `theory_correspondence` calls the
   *same* model tier (`synthesis`) that composed the theory. Self-preference bias is well documented
   (LLM-as-judge literature). The 0.54 is therefore indicative only. **Fix before publication:**
   judge with a *different* model family, and add a human expert rating — the number is not
   defensible as a validation statistic until then.

4. **Per-paper "gold" is AI-coded, not human.** The per-paper reference coding was produced by a
   different model family (gpt-5.4) than the extractor (gpt-5.5), blind to the output, and
   constrained to Richmond's E-codes. It is honestly labelled an *"expert reference coding
   (AI-assisted)"*. A two-human-coder pass with Cohen's κ (`res gold-template`) is the required next
   step and is not yet done.

5. **Stale numbers exist in older files.** `outputs/MASTER_VERIFICATION_REPORT.md` (dated
   2026-07-14) still shows screening 89.3% (25/28) and citation 98.3% (464/472). The **current**
   database gives 92.9% (26/28) and 96.9% (501/517). The `verify-15b50105` run *is* current (its
   deterministic anchors match the live DB exactly); the July master report is the stale one and is
   superseded by this document.

6. **A small data-quality gap:** 2 of the 439 relations carry the placeholder predicate
   `UNTYPED_CANDIDATE`, and Richmond ref 28 maps to two study records. Both are logged for cleanup;
   neither changes any headline.

---

## 5. What is verified, what is not, and the road to close the gap

**Solid and defensible today (deterministic):** screening recall (100% after HITL), extraction
faithfulness (96.9%), the presence of the causal structure (type-level 97.5%, anchored 55%). These
can go into the paper as they stand, with their caveats.

**Indicative but not yet defensible (model-judged, needs human ratification):** concept coverage
(37–43/47), community↔mechanism alignment (7/14), programme-theory correspondence (0.54). These need:

1. **Human coding pass** — two human coders on a sample of papers, Cohen's κ / Gwet's AC1 against
   the machine extraction. Tooling exists (`res gold-template` → `outputs/gold/per_paper_coding_coder_{A,B}.xlsx`).
2. **Cross-family judging** — re-run the LLM-judged metrics with a judge model from a *different*
   family than the extractor/composer, to remove self-preference bias.
3. **A scoreable demi-regularity mapping** — turn row 10 from a narrative comparison into a metric.

**Blocked right now:** the OpenAI API returned `429 insufficient_quota` (credit balance exhausted)
on 2026-09-10, so the three model-judged rows could **not** be re-run today; they are quoted from
`verify-15b50105`, which is consistent with the live database on both deterministic anchors. Re-run
`res verify` once credits are restored to refresh rows 3, 8, 9.

---

## 6. How to reproduce every number in this document

```bash
# Deterministic numbers (free, exact, no API):
PYTHONPATH=src python -m res_pipeline.cli status          # row counts
#   screening (rows 1)         -> screening_decisions, decider LIKE 'combined:%'
#   citation faithfulness (4)  -> entity_instances.quote_resolved
#   relation patterns (5,6,7)  -> typed_relations JOIN entity_instances

# Model-judged numbers (needs OpenAI credits; rows 3, 8, 9):
PYTHONPATH=src python -m res_pipeline.cli verify          # writes outputs/runs/verify-<id>/

# The human standard:
python scripts/build_richmond_gold_v2.py                  # rebuilds gold/richmond_gold_v2.json
```

Provenance for every stored row is in the `audit_log` and `token_usage` tables. The canonical run
IDs are `extract-531966df` (extraction), `synth-e1c81001` (synthesis), `verify-15b50105`
(verification).
