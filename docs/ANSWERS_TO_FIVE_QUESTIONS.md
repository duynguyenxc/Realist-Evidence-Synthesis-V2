> ## ⚠ The verification figures in this document were superseded on 2026-11-04
>
> A matcher defect found on 2026-09-30 was fixed: `verification/metrics.py` was accepting a
> `matched: true` whose own rationale stated a non-match. Two concepts were affected — E03
> (*high* domain knowledge, matched to `knowledge-deficits`) and E24 (*non*-analytical reasoning,
> matched to analytic reasoning). The recount then found a **second, independent** error: the
> over-merge table in `MACHINE_VS_HUMAN.md` §5 had omitted the pair `cont:knowledge-deficits` ←
> E02, E03, so the one-to-one figure was already one too high before the matcher was touched.
>
> | | published here | corrected |
> |---|---|---|
> | Concepts, same realist role | 34/46 (73.9%) | **32/46 (69.6%)** |
> | Concepts, role-crossing allowed | 41/46 (89.1%) | **39/46 (84.8%)** |
> | Concepts, one-to-one (comparable to a human coder) | 28/46 | **26/46** |
> | Relations, strict | 6/40 (15.0%) | **5/40 (12.5%)** |
> | Relations, anchored | 29/40 (72.5%) | **28/40 (70.0%)** |
> | Relations, causal pattern | 39/40 | 39/40 (unchanged) |
>
> **At 26/46 the system is two concepts below Coder B and four below Coder A — not equal to them,
> as this document says.** Non-inferiority remains the defensible claim, but it now rests on
> overlapping confidence intervals rather than on parity, and must be written that way.
>
> The text below is left exactly as it was written, because correcting a published figure in place
> and saying nothing is how a record stops being trustworthy. **`docs/MACHINE_VS_HUMAN.md` §5.1 is
> the authoritative arithmetic.**

# Answers to the five questions of 2026-09-26/27

*Duy Nguyen — 2026-09-30. Each answer is taken from the code or the data as it stands today, with
the file and line so you can check it directly. Where an earlier document said something different,
the earlier document is wrong and is named.*

---

## 1. Why did the benchmark concept count change from 47 to 46?

**The concept is `E01`, and it was not deleted — it was de-scored.**

`E01` = *"undergraduate students in medical or health care professions education"*, located at
Richmond's **Conclusions, p. 717**.

It is still present in `gold/richmond_gold_v3.json`, now carrying:

```json
"scored": false,
"unscored_reason": "Review population/scope from the Conclusions (p.717); not one of the
                    five contexts, absent from Figures 2 and 3 and from every relation."
```

**Why.** E01 is the review's *population and scope statement*, not a CMOC element. It is not one of
Richmond's five student contexts (those are E02–E06); it does not appear in Figure 2 or Figure 3;
and it is the subject or object of **zero** of the 40 relations. Scoring it asked the system to
"recover" the sentence describing who the review is about, which is a category error: it inflates
the denominator with an item that carries no causal content.

No other concept changed. A set difference between v1 and v3 returns exactly `{E01}` removed and
nothing added. Setting `RES_GOLD=v1` reproduces every previously published 47-based figure.

---

## 2. What are the actual allowed outputs of the screening agent?

**Exactly three, enforced in code, and the combination rule is deterministic — not decided by a model.**

`src/res_pipeline/core/screening.py`:

- Line 30 — the schema constrains each vote with a regular expression:
  ```python
  decision: str = Field(pattern=r"^(include|exclude|uncertain)$")
  ```
  A model that returns anything else fails validation; it cannot invent a fourth state.

- Lines 79–84 — the two votes are combined by **union-of-includes (recall-first)**:
  ```python
  votes = {primary.decision, second.decision}
  if "include" in votes:      return "include"     # any include wins
  if votes == {"exclude"}:    return "exclude"     # both must exclude
  return "uncertain"                               # anything else -> HITL-1
  ```

- The module docstring states the design intent: *"missing a relevant study is far worse than a
  false include; borderline → 'uncertain'"*, and *"decision logic, never free-styled by the model
  (professor requirement)"* — your earlier instruction is implemented literally and recorded in the
  source.

Each study writes **three rows** to `screening_decisions`: `model:<ver>:primary`,
`model:<ver>:second_vote`, and `combined:<ver>`, each with its own rationale and confidence.

The two voters are deliberately from different model lineages (`config/models.yaml`):
`screening_primary` = gpt-5.4-mini, `screening_second_vote` = gpt-4.1-mini.

On the verified run: **26 include, 0 exclude, 2 uncertain** (S018, S028) → human adjudication →
**28/28**. Note that "uncertain" is not a negative class; nothing was automatically excluded.

---

## 3. Did the verified run perform literature retrieval, or start from Richmond's 28 studies?

**It started from Richmond's 28 studies. No database search and no deduplication were executed in
the run reported in the paper.**

The corpus is a fixed registry built from `data/20-paper-of-Richmond/` (20 full-text PDFs) plus 8
abstract/metadata records transcribed from `data/in4-about-28-studies-paper.pdf`. There is no
search agent, no database connector, and no deduplication stage in the executed pipeline.

This distinction must appear in the figure and the text, exactly as you say. Concretely:

- **Implemented and exercised:** screening, extraction, normalisation, community detection,
  synthesis, programme theory, reporting.
- **Described in the architecture but not exercised:** protocol-driven retrieval/search.

The consequence for the metric: the reported **100% screening sensitivity (28/28)** is measured on a
corpus in which *every record is a known include*. It demonstrates that the screener does not
discard a relevant paper. It demonstrates **nothing** about precision or about whether the system
could find those 28 among the 7,097 records Richmond screened. False-positive behaviour is assessed
separately against a distractor pool, which is a weaker substitute. I recommend the paper state this
in the limitations rather than let the 100% stand unqualified.

---

## 4. Is the pipeline still using the Microsoft GraphRAG package?

**No. Not at all, and it never was in the executed code.**

Three independent checks:

1. `graphrag` is **not** a dependency in `pyproject.toml`. The only occurrence of the string is a
   comment recording exactly this history: *"langchain, langgraph and graphrag were declared for a
   long time and never imported."*
2. `grep -rn "import graphrag|from graphrag" src/ scripts/` returns **nothing**.
3. It is not installed in the virtual environment. What is installed: `networkx 3.7`,
   `graspologic 3.4.4`, `graspologic-native 1.3.1`. LangChain and LangGraph are also absent.

**What is actually taken from GraphRAG (Edge et al., 2024), and it is genuine:**

- **Leiden community detection via `graspologic`** — the same library the GraphRAG paper names in
  §4.1.3. This is how the 8 mechanisms are discovered.
- **The gleaning / self-reflection idea** in §A.2 of that paper, realised here as the
  extract → critique → revise loop.

**What is deliberately not taken:** GraphRAG's query-time half — community summaries feeding
map-reduce query-focused summarization. Our synthesis is deterministic aggregation over the
communities, not QFS, and no subgraph retrieval is performed on this corpus.

So the honest description is **"a custom typed knowledge-graph pipeline that adopts GraphRAG's
community-detection step"** — GraphRAG-indexed, not GraphRAG-answered. The July text calling
Microsoft GraphRAG "the graph/indexing layer" overstated it and should be corrected.

---

## 5. Is the extraction-agent sequence still the July sequence?

**Yes, with one change you should know about: the revision round is now conditional.**

`src/res_pipeline/plugins/realist/cmoc_extraction.py`, prompt version
`cmoc-extraction-v5.0-guided+selfrefine`:

1. **Extract** — the extraction tier (gpt-5.5) drafts CMOCs against a deliberately *narrow* schema.
   Every entity mention must carry a verbatim quote of 10–40 words, copied exactly.
2. **Critique** — an independent reviewer critiques the draft (`_critique_draft`).
3. **Revise — conditional.** `_REVISE_THRESHOLD = 0.34`: a full revision round fires only when the
   reviewer disputes **≥34%** of the draft's configurations. Below that, the disputed configuration
   is routed to HITL-2 instead. Rationale in the source comment: revising is a second full-text call
   to the most expensive tier — measured at 2.19 such calls per study on run `extract-9035e95e`,
   i.e. it fired on essentially every paper — and when a single CMOC in a large set is questioned,
   HITL-2 is the cheaper and more honest place to settle it. Setting the threshold to 0.0 restores
   the original always-revise behaviour.
4. **Ground** — every quote is resolved to a character span against the canonical text: exact match
   first, then a whitespace-tolerant normalised fallback. Unresolvable quotes are **flagged, never
   fabricated**.
5. **Verify** — a second, cheaper model (`extraction_verifier` = gpt-5.4-mini) scores whether the
   quotes genuinely support each configuration. Low-support CMOCs are flagged for HITL-2.

Also unchanged: relations use the five fixed predicates, and a link violating the domain/range rules
is demoted to `UNTYPED_CANDIDATE` and preserved for human review rather than dropped or forced.
There are **3 such candidates out of 459** on the verified run.

So the July sequence is intact and extended by the support-scoring verifier. The one substantive
difference from the July description is the 0.34 threshold, which makes the revise step conditional
rather than unconditional.

---

## On your list of items to correct without asking

All five are right, and I confirm each from the run:

- **Six human checkpoints**, not four. Table 4 is correct; the "four checkpoints" sentence is stale.
- **Screening**: 26 auto-included, 2 deferred as uncertain, **0 auto-excluded**, 28/28 after
  adjudication. Agreed that "uncertain" must not be treated as a negative class.
- **47 / 43 / 91.5% and 96.9%** are superseded and must not be presented as current.
- **Current verified values** confirmed: 94 CMOCs, 547 concept instances, 459 typed relations,
  34/46 same-role concepts, 41/46 broader recovery, 29/40 anchored relations, 39/40 causal-pattern
  recovery.
- **The 17-percentage-point statement**: agreed, it is observed model-judge variability, not a
  formal minimum detectable difference.

One item to add to that list, found on 2026-09-30: the **34/46 same-role figure is not one-to-one**.
Those 34 matches rest on only **28 distinct extracted concepts**, because four of our concepts are
each counted against two or three of Richmond's (for example, one concept is counted for *frustrated*,
*stress* and *confusion*). A human coder cannot do this, since the coding frame allows one code per
element. Under the same constraint the system scores **28/46**, which equals our two human coders
(30/46 and 28/46) rather than exceeding them. The claim should therefore read **non-inferior to human
coders**, not better than them. Detail in `docs/MACHINE_VS_HUMAN.md` §5.
