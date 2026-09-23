# ARCHITECTURE — Agentic Realist Evidence Synthesis (V2)

> ## ⚠ TECHNOLOGY CLAIMS SUPERSEDED (2026-09-23)
>
> A line-by-line comparison of this document against the source code found that several
> load-bearing technology claims here are not implemented: LangGraph is never imported, no
> embedding is ever computed, there is no vector store and no GraphRAG local/global search, the
> `graphrag` package is declared but never used, the extraction/synthesis tier is gpt-5.5 rather
> than gpt-5.4, `config/prompts/` is empty, the per-paper gold is LLM-produced rather than
> human-coded, and nine of the modules listed in the repo layout below do not exist.
>
> **[`SYSTEM_AND_ALGORITHMS.md`](SYSTEM_AND_ALGORITHMS.md) is now the description of record** for
> architecture, reasoning, algorithms and tooling; it carries the full correction table in §7.
> This file is retained for its decision history (D1–D7) and for the ontology and phase plan, which
> remain accurate.

---


_Status: **v1.0 — grounded proposal, approved-to-build** (RA granted full build authority
2026-07-14; every decision below is traceable to `docs/research/SOTA_REPORT.md`, the professor's
documents, or the Richmond primary source). Update this file when decisions change; log changes
in `DECISION_LOG.md`._

---

## 1. System overview

A **core-and-plugin, human-in-the-loop multi-agent pipeline** that reproduces the analytic
operations of a RAMESES realist review and is *separately* verified against Richmond et al.
(2020). One LangGraph state machine orchestrates all agents over a shared typed state;
PostgreSQL is the single source of truth; the Literature Knowledge Graph (LKG) is a typed,
span-grounded CMOC graph stored as GraphRAG-native parquet and mirrored to Neo4j for queries
and visualization.

```
                          ┌────────────────────────────────────────────────┐
                          │            LangGraph Orchestrator              │
                          │   (typed Pydantic state · AsyncPostgresSaver)  │
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
              Neo4j (derived motif-query + viz layer)          ·  text-embedding-3-small vectors
 EVALUATION (OUTSIDE the pipeline, per professor):  verification harness vs Richmond gold standard
```

## 2. The seven grounded decisions

| # | Decision | Choice | Grounding (see SOTA_REPORT) |
|---|---|---|---|
| D1 | Graph construction | Microsoft GraphRAG kept for communities/query, but typed CMOC triples come from **our constrained extraction agent** loaded via **BYOG**; ontology injected in prompt + **post-hoc domain/range validation** | Q1 (BYOG docs; OMD-GraphRAG +3.17% F1; OG-RAG −40% hallucination) |
| D2 | Novelty position | First framework to operationalize **realist synthesis** agentically — genuine gap in the literature | Q2 (no prior realist/RAMESES automation found) |
| D3 | Ontology | **Hybrid**: 5 fixed entity types + 5 fixed predicates with domain/range constraints; emergent entity *instances*, normalized; E-code mapping only at verification; nanopub-style provenance on every triple | Q3 (RAMESES II mandates explicit C/M/O labels) |
| D4 | Models | Tiered single-vendor: `gpt-5.4-mini` screening (+`gpt-4.1-mini` 2nd vote), `gpt-5.4` extraction/synthesis, mini-tier verifier pass, `text-embedding-3-small`; multi-vendor ensemble deferred to sensitivity analysis | Q4 (screening meta-analysis; dual-model ensemble; ExtractBench; JAMIA cross-critique) |
| D5 | Storage | Postgres = state/audit SoT · Parquet = canonical reproducible LKG artifact · Neo4j = derived query/viz | Q5 |
| D6 | Verification | Independent **human** per-paper CMOC gold (2 coders, Cohen's κ); AI-adjudicated xlsx demoted to post-hoc suggestion aid; per-stage metrics incl. citation-faithfulness | Q6 (non-circularity; RAMESES II transparency) |
| D7 | HITL | LangGraph `interrupt()`/`Command(resume)` at 4 checkpoints; approve/edit/reject payloads; feedback rows → few-shot injection on re-run | Q7 (official LangGraph patterns) |

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
   validation; → typed triples to LKG (parquet + Neo4j), GraphRAG index build (BYOG + Leiden
   communities + embeddings).
4. **Synthesis** (P4, P5): motif queries find recurring CMOC patterns (demi-regularities) and
   conflict motifs; GraphRAG global/local search grounds narrative; → **HITL-3** contradiction
   adjudication (human interpretive resolution stored as theory rules).
5. **Programme theory** (P6): compose per-context theory chains + narrative with n-study
   support; → **HITL-4** sign-off.
6. **Reporting** (A6): PRISMA flow, CMOC evidence tables (md+xlsx), theory diagrams
   (Mermaid/Graphviz + interactive HTML from Neo4j), narrative, full audit trail.

**Verification harness (separate package, not an agent)**: runs the gold-standard comparisons
and emits the side-by-side dashboard (see §6).

## 5. Repository layout (to scaffold)

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

## 8. Build order (long-term plan)

Phase 0 scaffold+config → Phase 1 ingestion/registry → Phase 2 screening+HITL-1 →
Phase 3 ontology+extraction+HITL-2+LKG → Phase 4 synthesis+HITL-3 → Phase 5 theory+HITL-4 +
reporting → Phase 6 verification harness + dashboard → Phase 7 pilot run (3 papers) → full run →
iterate → manuscript-support artifacts. Each phase ends with its WALKTHROUGH entry + tests.
