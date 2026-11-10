# Realist Evidence Synthesis (V2)

A multi-agent pipeline that performs the analytic work of a **realist systematic review** —
searching, screening, extracting causal configurations from each paper, consolidating them
across papers, and composing a programme theory — while leaving every interpretive judgement
to a human and keeping every claim traceable to the sentence it came from.

It is a **research artifact, not a product**, and it is the methodological contribution of a
manuscript for *Review of Research in Education* (Vol. 50, 2026). A companion paper,
*"AI Agent-Augmented Systematic Review for Synthesizing Evidence to Guide Pedagogical
Innovation,"* was accepted to **AERA 2027** (Division D, roundtable) on 6 November 2026.

## What problem this addresses

A realist review asks what works, **for whom, in what circumstances, and why** — not whether an
average effect is positive. Its unit of analysis is the Context–Mechanism–Outcome Configuration
(CMOC): *in this context, this resource triggers this response, producing this outcome.* Building
those by hand across dozens of papers takes a team months, and the reasoning is hard to audit
afterwards because it lives in reviewers' notes.

This pipeline does the mechanical part and records the reasoning. It does **not** replace the
reviewer: five checkpoints stop and ask a person, and the programme theory is not valid until a
human signs it.

## How it was tested

The pipeline was run over **Richmond et al. (2020)**, *"The student is key"* (*Medical Education*
54(8):709–719) — a published RAMESES realist review of 28 studies on clinical-reasoning education.
Richmond's own concepts and relations were turned into a benchmark, and the system's output was
scored against them by a **separate** verification harness that is not part of the pipeline.

Current figures (corrected 2026-11-04; see `docs/MACHINE_VS_HUMAN.md` §5.1 for the arithmetic):

| What is compared | Result |
|---|---|
| Concepts recovered, same realist role | 32/46 (69.6%) |
| Concepts recovered, role-crossing allowed | 39/46 (84.8%) |
| Concepts, one concept may claim only one — comparable to a human coder | 26/46 (56.5%) |
| Causal relations, anchored | 28/40 (70.0%) |
| Quotes matching the source after normalising hyphenation and whitespace | 509/547 (93.1%) |

Two people independently coded all 28 papers as a human reference standard; their positive
specific agreement is **0.785**. The system sits **below** both of them on the one-to-one
measure, so the defensible claim is **non-inferiority**, resting on overlapping confidence
intervals. `docs/VERIFICATION_PROTOCOL.md` explains why these are the right statistics, with
citations, and lists what is still missing.

## Where to start reading

| Document | Purpose |
|---|---|
| [`PLAN.md`](PLAN.md) | The work currently in progress |
| [`docs/MACHINE_VS_HUMAN.md`](docs/MACHINE_VS_HUMAN.md) | System against the two human coders — the central comparison |
| [`docs/VERIFICATION_PROTOCOL.md`](docs/VERIFICATION_PROTOCOL.md) | Why these metrics, with citations, and what is missing |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Design decisions, agents, ontology, phases |
| [`docs/PROJECT_CONTEXT.md`](docs/PROJECT_CONTEXT.md) | Goals, status, which earlier decisions were reversed |
| [`WALKTHROUGH.md`](WALKTHROUGH.md) | Milestone log, newest entry last — how each result was reached |
| [`outputs/raw_export/`](outputs/raw_export/) | Every row of every table, JSON and CSV, nothing summarised |
| [`config/ontology.yaml`](config/ontology.yaml) | The five entity types and five relation predicates |
| [`config/prompts/`](config/prompts/) | Prompt text, overridable without touching code |

## Stack

Python 3.11 · OpenAI API (tiered per stage — see `config/models.yaml`) · **PostgreSQL** for the
registry, evidence graph and audit trail · **Parquet** for the canonical knowledge-graph artifact
(`outputs/lkg/`) · **graspologic** for Leiden community detection · **FastAPI** for the review
console.

**Not used, despite earlier plans:** LangChain, LangGraph and the Microsoft `graphrag` package
were evaluated and **deferred indefinitely** with reasons and citations in
`docs/IMPROVEMENT_PLAN.md` §3; none is imported anywhere. There are **no embeddings**. A Neo4j
adapter exists but no Neo4j database was ever created. Earlier versions of this README claimed
all four as the stack; they were never built, and that claim is retracted here.

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,viz]"
cp .env.example .env            # then fill in OPENAI_API_KEY and POSTGRES_PASSWORD
res status
```

`res status` prints which config, data, gold and output directories are active and which database
is in use. Read it before running anything that writes.

## Commands

```
res search      find literature (OpenAlex + Crossref), deduplicate, write the corpus definition
res acquire     fetch open-access full texts the catalogue links (reports unless --confirm)
res ingest      build the study registry and extract canonical text
res screen      two-model screening vote; uncertain cases go to a human
res extract     CMOC extraction with a verbatim quote behind every element
res synthesize  normalise concepts, detect communities, compose the programme theory
res retroduce   re-analyse weak studies as the theory refines
res theorise    propose concepts the theory needs that the corpus never states
res verify      score the output against the benchmark
res webui       the human review console
```

## Running a second review

The Richmond corpus, benchmark and published outputs must not be overwritten. Point a new topic
at its own directories and its own database:

```bash
createdb realist_emotion
```

then in `.env`: `RES_CONFIG_DIR`, `RES_DATA_DIR`, `RES_OUTPUTS_DIR` and `POSTGRES_DB`. Setting the
directories while leaving `POSTGRES_DB` alone would write a new topic's extractions into
Richmond's tables, so every writing stage refuses that combination and says so.
`config-emotion/` is a worked example of such a configuration.

## Status

Phases 0–7 are built; the pipeline has run end to end twice. The database holds 547 entity
instances, 459 typed relations, 94 CMOCs and 8 emergent conceptual entities over 26 of the 28
studies — the two remaining records are abstract-only, and the system correctly declined to
extract configurations from them.

**What is not done:** no human has yet countersigned the review checkpoints (they are recorded
honestly as AI-performed under written delegation); precision has never been measured, only
recall; and the pipeline has never been run on a corpus it searched for itself. `PLAN.md` tracks
all three.
