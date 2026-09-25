# ARCHITECTURE — Agentic Realist Evidence Synthesis (V2)

> ## How to read this file — design record, not description of record
>
> This is the **design proposal of 2026-07-14**, kept because the reasoning behind each decision
> is worth preserving. It is **not** a description of the system that was built. A line-by-line
> comparison against the source on 2026-09-24 found that several load-bearing technology choices
> here were never implemented.
>
> Section 2 now carries an **"as built"** column stating, for each decision, what the code
> actually does. Sections that describe unbuilt components are marked inline.
>
> **[`SYSTEM_AND_ALGORITHMS.md`](SYSTEM_AND_ALGORITHMS.md) is the description of record.** Read
> that one to learn what the system is; read this one to learn why it was designed that way.

---


_Status: **v1.0 — grounded proposal, approved-to-build** (RA granted full build authority
2026-07-14; every decision below is traceable to `docs/research/SOTA_REPORT.md`, the professor's
documents, or the Richmond primary source). Update this file when decisions change; log changes
in `DECISION_LOG.md`._

---

## 1. System overview

A **core-and-plugin, human-in-the-loop multi-agent pipeline** that reproduces the analytic
operations of a RAMESES realist review and is *separately* verified against Richmond et al.
(2020). PostgreSQL is the single source of truth; the Literature Knowledge Graph (LKG) is a
typed, span-grounded CMOC graph stored as parquet and loadable into Neo4j for queries and
visualization.

> **As built.** Orchestration is `cli.py` calling stage functions in sequence — a linear
> pipeline, not a state machine. **LangGraph is never imported.** The four HITL checkpoints are
> separate CLI subcommands plus FastAPI form posts in `res webui`, not framework interrupts.
> The parquet uses GraphRAG-compatible column names but is never loaded into a GraphRAG index,
> and **no embedding is ever computed.**

```
                          ┌────────────────────────────────────────────────┐
                          │   Orchestrator — AS BUILT: cli.py, sequential  │
                          │   (designed as LangGraph; never implemented)   │
                          └────────────────────────────────────────────────┘
 CORE (method-agnostic)                                     REALIST PLUGIN (method-specific)
 ┌──────────────────────────────┐                           ┌─────────────────────────────────┐
 │ A1 Protocol & Scope          │                           │ P1 IPT Manager (versioned)      │
 │ A2 Corpus Ingestion (PDF→txt)│                           │ P2 CMOC Extraction Agent        │
 │ A3 Registry & Deduplication  │                           │ P3 Entity Normalization Agent   │
 │ A4 T/A Screening Agent ──HITL-1─ Screening adjudication  │ P4 Synthesis & Demi-regularity  │
 │ A5 Full-Text Eligibility     │                           │ P5 Contradiction & Sensitivity  │
 │ A6 Reporting & Audit Export  │                           │      └──HITL-3─ Adjudication    │
 └──────────────────────────────┘                           │ P6 Programme Theory Composer    │
                                                            │      └──HITL-4─ Theory sign-off │
                                                            │ (P2 └──HITL-2─ CMOC validation) │
                                                            └─────────────────────────────────┘
 DATA LAYER:  PostgreSQL (state/registry/audit/HITL feedback)  ·  Parquet LKG (canonical artifact)
              Neo4j (derived query + viz layer)                ·  [embeddings: NEVER BUILT]
 EVALUATION (OUTSIDE the pipeline, per professor):  verification harness vs Richmond gold standard
```

## 2. The seven grounded decisions — as designed, and as built

The **Grounding** column records why the choice was made in July. The **As built** column records
what the code does as of 2026-09-24, verified against the source. Where the two differ, the
manuscript must describe the second.

| # | Decision | Designed | As built (verified 2026-09-24) |
|---|---|---|---|
| **D1** | Graph construction | Microsoft GraphRAG retained for communities/query; typed CMOC triples from our constrained extraction agent, loaded via BYOG; ontology in prompt + post-hoc domain/range validation. *(Grounding: SOTA Q1)* | **PARTIALLY BUILT.** Ontology-constrained extraction ✅, domain/range validation ✅ (456/459 valid), Leiden via the same `graspologic` GraphRAG uses ✅. But the `graphrag` package is **declared and never imported**, there is **no BYOG load**, **no vector store** and **no local/global search** — the programme-theory composer receives the whole evidence pack inline. Defensible phrasing is *"ontology-constrained KG construction with Leiden community detection"*, or *"GraphRAG-inspired"* with the differences stated. |
| **D2** | Novelty position | First framework to operationalise realist synthesis agentically. *(SOTA Q2)* | **HOLDS, and independently re-confirmed 2026-09-24.** No published or preprint work automates realist synthesis, CMOC extraction or programme-theory construction. The nearest prior art — Owen-Boukra et al. 2026, *BJGP Open*, with Geoff Wong (RAMESES) and James Thomas (RAISE) among the authors — poses the question and **defers the evaluation design entirely**. No published realist review reports an inter-rater statistic for CMOC coding, Richmond included. |
| **D3** | Ontology | Hybrid: 5 fixed entity types + 5 fixed predicates with domain/range constraints; emergent instances, normalised; E-codes only at verification; provenance on every triple. *(SOTA Q3)* | **BUILT AS DESIGNED.** `config/ontology.yaml`; 5 types, 5 predicates plus an `UNTYPED_CANDIDATE` overflow (3 of 459) surfaced at HITL-2 rather than dropped. Non-circularity holds: E-codes appear only in `verification/`, never in an extraction prompt. The strongest-held decision in this table. |
| **D4** | Models | Tiered single-vendor: `gpt-5.4-mini` screening (+`gpt-4.1-mini` 2nd vote), `gpt-5.4` extraction/synthesis, mini verifier, `text-embedding-3-small`. *(SOTA Q4)* | **CHANGED.** Extraction and synthesis are **gpt-5.5**, not gpt-5.4 (RA directive, 2026-07-14); gpt-5.4 became the critic/gold tier. The `embeddings` tier was **declared and never called**, and was removed from `models.yaml` rather than left standing as a false claim. A `gpt-4.1-mini` `independent_judge` tier was added 2026-09-23 for cross-family scoring. |
| **D5** | Storage | Postgres = state/audit SoT · Parquet = canonical LKG · Neo4j = derived query/viz. | **BUILT AS DESIGNED.** Postgres 18 is the single source of truth (14 tables, 1,084 audit events); parquet is the portable artifact; Neo4j loads via `res load-neo4j` (currently offline, not required by any metric). |
| **D6** | Verification | Independent **human** per-paper CMOC gold (2 coders, Cohen's κ); AI-adjudicated coding demoted to a suggestion aid; per-stage metrics including citation faithfulness. *(SOTA Q6)* | **NOT BUILT — and this is the project's largest open gap.** `gold/per_paper_gold/` is **LLM-produced**; `compute_kappa` exists in `gold_template.py` and is **called from nowhere**; `res gold-template` writes blank two-coder workbooks that remain unfilled. **No human has independently coded any paper.** Until that changes, every agreement-style number is uninterpretable, because there is no human–human ceiling to read it against. Note also that Cohen's κ is the wrong statistic for span extraction — positive specific agreement / F is correct (Hripcsak & Rothschild, *JAMIA* 2005). |
| **D7** | HITL | LangGraph `interrupt()`/`Command(resume)` at 4 checkpoints; approve/edit/reject payloads; feedback rows → few-shot injection on re-run. *(SOTA Q7)* | **BUILT DIFFERENTLY.** The four checkpoints exist and are exercised (`res adjudicate`, `res validate-cmocs`, the `res webui` review pages), but as CLI commands and web forms — **LangGraph is never imported**. The feedback→few-shot loop was **dead until 2026-09-24**: corrections were written into `hitl_feedback`, whose NOT NULL columns made every insert fail. Corrections now live in `agent_feedback` with a guard that raises on an agent key nothing reads. **Its effect is still unmeasured.** |

### Two decisions that should be added

| # | Decision | Why it belongs here |
|---|---|---|
| **D8** | **Report deterministic and model-judged metrics separately, with exact intervals** | Five of eight verification rows are arithmetic and reproducible forever; three need an LLM and move between runs *and between judges*. Two runs over a **byte-identical graph** returned anchored recall of 29/40 and 25/40 — **10 points of pure judge variance**. Clopper–Pearson intervals on every proportion are what made that visible. |
| **D9** | **The Richmond comparison is concurrent-validity evidence, reported once — not an objective function** | With a judge SE near 9.7 points, ten rounds of tuning against this benchmark would be expected to yield a ~20-point "improvement" from selection alone, even if every variant were identical (Dwork et al., *Science* 2015). See `IMPROVEMENT_PLAN.md` §1. |

## 3. Ontology (the scientific core)

Entity types: `Context` · `Intervention` · `Mechanism_Resource` · `Mechanism_Response` · `Outcome`
(+ structural nodes `Study`, `CMOC`).

Relation predicates with domain/range constraints (validated to cover all 40 gold relations):

| Predicate | Domain → Range | Meaning |
|---|---|---|
| PROVIDES | Intervention → Mechanism_Resource | intervention supplies a resource |
| TRIGGERS | Intervention \| Mechanism_Resource → Mechanism_Response | resource evokes cognitive/emotional response |
| ENABLES | Context → Mechanism_Response \| Outcome | context makes a response/outcome possible |
| LEADS_TO | Mechanism_Response → Mechanism_Response \| Outcome | response produces (further response or) outcome |
| CONSTRAINS | Context → Outcome | context limits/negatively conditions an outcome |

Every triple carries provenance `{study_id, text_unit_id, char_start, char_end, verbatim_quote,
extractor_model, prompt_version, confidence}`. A `CMOC` node bundles one C+I+M_res+M_resp+O
chain per study (the realist analytic unit per RAMESES II). Cross-study demi-regularities =
recurring CMOC motifs (subgraph patterns over typed edges); contradictions = same
resource/intervention with divergent outcomes under different contexts.

## 4. Pipeline phases & agents (inputs → outputs)

0. **Protocol & IPT** (A1, P1): review question + inclusion rules + IPT hypotheses → versioned
   YAML protocol in Postgres. Human-authored, agent-assisted.
1. **Ingestion & Registry** (A2, A3): 20 PDFs + 8 metadata records → clean text units with char
   offsets (provenance base) → study registry S001–S028, dedup by DOI/title.
2. **Screening** (A4, A5): recall-first rubric from protocol; include/exclude/uncertain +
   rationale + confidence; dual-model vote (union of includes); → **HITL-1** adjudication of
   uncertain/disagreement; corrections become few-shot examples; full-text eligibility pass.
   (Benchmark mode can bypass to all-28 for downstream verification runs, flagged in audit.)
3. **CMOC extraction** (P2, P3): per paper, narrow schema (one CMOC at a time, few fields —
   ExtractBench lesson), span-grounded quotes mandatory, self-check verifier pass
   (quote-supports-triple?); Pydantic validation of types + domain/range; normalization agent
   canonicalizes entity labels (e.g., "self-efficacy"≈"confidence"); → **HITL-2** sample
   validation; → typed triples to LKG (parquet + Neo4j), community detection.
   *As built: Leiden via `graspologic` ✅; **no BYOG index and no embeddings** — concept
   normalisation is LLM clustering over alphabetically-sorted batches of 40, not vector
   similarity.*
4. **Synthesis** (P4, P5): motif queries find recurring CMOC patterns (demi-regularities) and
   conflict motifs; → **HITL-3** contradiction adjudication (human interpretive resolution
   stored as theory rules). *As built: demi-regularity and contradiction detection are pure
   Python, no LLM. **There is no global/local search** — the composer receives the entire
   evidence pack inline, which is context stuffing, not retrieval.*
5. **Programme theory** (P6): compose per-context theory chains + narrative with n-study
   support; → **HITL-4** sign-off.
6. **Reporting** (A6): PRISMA flow, CMOC evidence tables (md+xlsx), theory diagrams
   (Mermaid/Graphviz + interactive HTML from Neo4j), narrative, full audit trail.

**Verification harness (separate package, not an agent)**: runs the gold-standard comparisons
and emits the side-by-side dashboard (see §6).

## 5. Repository layout (as scaffolded in July — see note below for what exists)

```
Realist Evidence Synthesis V2/
├── CLAUDE.md · WALKTHROUGH.md · README.md · pyproject.toml · .env(.example) · .gitignore
├── docs/            # PROJECT_CONTEXT, DECISION_LOG, ARCHITECTURE, research/
├── config/          # protocol.yaml, ontology.yaml, models.yaml, prompts/ (versioned)
├── src/res_pipeline/
│   ├── core/        # state.py (Pydantic state), orchestrator.py, registry.py, ingestion.py,
│   │                # screening.py, hitl.py, audit.py, reporting.py, llm.py (tiered clients)
│   ├── plugins/realist/   # ontology.py, cmoc_extraction.py, normalization.py,
│   │                      # synthesis.py, contradiction.py, programme_theory.py
│   ├── graph/       # graphrag_adapter.py (BYOG/parquet), neo4j_adapter.py, motifs.py
│   └── verification/ # gold_standard.py, metrics.py (per-stage), faithfulness.py, dashboard.py
├── data/            # (existing corpus — read-only)
├── gold/            # richmond_gold.json (E/R/PTS, verified), per_paper_gold/ (HUMAN-coded)
├── outputs/         # runs/<run_id>/ … parquet, reports, diagrams (regenerable)
└── tests/
```

> **As built.** Nine of the modules above were never written and do not exist:
> `core/state.py`, `core/orchestrator.py`, `core/hitl.py`, `core/audit.py`,
> `plugins/realist/contradiction.py`, `graph/graphrag_adapter.py`, `graph/motifs.py`,
> `verification/gold_standard.py`, `verification/faithfulness.py`. Their responsibilities live
> elsewhere: orchestration in `cli.py`, HITL in `cli.py` + `webui.py`, audit in `core/db.py`,
> contradiction detection inside `synthesis.py`, faithfulness inside `metrics.py`.
> `config/prompts/` is an **empty directory** — prompts are string literals in the modules with
> hand-maintained `PROMPT_VERSION` constants. And `gold/per_paper_gold/` is **LLM-produced**, not
> human-coded (D6). Modules added since and not in this tree: `core/results_export.py`,
> `verification/stats.py`, `plugins/realist/span_repair.py`, `plugins/realist/guidance.py`,
> `plugins/realist/ipt.py`, `plugins/realist/retroduction.py`, `graph/communities.py`.

## 6. Output artifacts (designed for 1:1 human comparison — answers the RA's open question)

The system emits the **same artifact genres Richmond published**, plus verification overlays:
PRISMA flow (vs their Fig 1) · per-paper CMOC evidence table with quotes (vs Appendix S1/S2) ·
five-context programme-theory overview diagram (vs Fig 2) · per-context CMOC chain diagrams
(vs Fig 3) · narrative theory with italicised CMOC statements · **verification dashboard**
(stage-by-stage metrics vs gold) · audit trail (RAMESES II transparency). Interface: static
interactive HTML (no server dependency) generated per run + Neo4j Bloom/Browser for exploration.

## 7. Cost & risk controls

3-paper pilot before any full run; per-run token budget logged to Postgres; prompts versioned in
`config/prompts/` (a feedback-updated prompt = new version, per RAMESES transparency); model IDs
pinned in `models.yaml`; benchmark-mode flags recorded in audit; **API key rotation recommended**
(key was pasted in chat). Known risks: extraction fidelity ceiling (mitigate: narrow schema +
verifier + HITL-2), fixed-typology miss rate (mitigate: `UNTYPED_CANDIDATE` overflow bucket
surfaced at HITL-2), gold-standard circularity (mitigated by D6), scope creep vs deadline
(mitigate: phases 0–6 strictly ordered, verification harness developed in parallel from phase 3).

> **As built, and a lesson paid for.** Token usage *is* logged per run (`token_usage`, now
> including `cached_tokens`), but `budget.max_usd_per_full_run` sat at `null` — **the budget guard
> this section describes was never switched on.** Credit exhaustion then killed three consecutive
> runs in September 2026, twice at the same study, each time re-paying for work already done until
> `res extract --resume` was built. The guard is now set (§ `config/models.yaml`), with a
> pre-flight balance check and a running tally that halts cleanly before the balance is gone.
> Prompt versioning also did not happen as designed: `config/prompts/` is empty.

## 8. Build order (long-term plan)

Phase 0 scaffold+config → Phase 1 ingestion/registry → Phase 2 screening+HITL-1 →
Phase 3 ontology+extraction+HITL-2+LKG → Phase 4 synthesis+HITL-3 → Phase 5 theory+HITL-4 +
reporting → Phase 6 verification harness + dashboard → Phase 7 pilot run (3 papers) → full run →
iterate → manuscript-support artifacts. Each phase ends with its WALKTHROUGH entry + tests.
