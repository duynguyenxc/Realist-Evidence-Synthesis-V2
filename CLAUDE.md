# CLAUDE.md — Realist Evidence Synthesis (V2)

> This file is auto-loaded at the start of every session whose working directory is this
> folder. It is the project's persistent memory. Read `docs/PROJECT_CONTEXT.md` for the
> full context before making any non-trivial decision. Keep both files updated as the
> project evolves — this is how future sessions "remember" the project.

## One-paragraph summary
This is a **serious academic research project** for a real journal submission (Review of
Research in Education, RRE 2026). The deliverable is a **methodological-innovation paper**,
NOT a software demo. It proposes an **agentic, human-in-the-loop, GraphRAG-based multi-agent
framework** for automating **realist systematic reviews** in education. The paper's *worked
example / external benchmark* is **Richmond et al. (2020)** — a realist review of educational
interventions for clinical reasoning in medical students (28 included papers). The system
must reproduce Richmond's analytic operations (search → screen → CMOC extraction →
cross-study synthesis → programme theory) and be verified by comparing its outputs to
Richmond's human outputs. **Method > platform; human judgment stays sovereign.**

## Working rules (from the RA / project owner)
- **All project artifacts (code, files, docs, identifiers) must be written in English.**
  Vietnamese is only for chat between the RA and Claude.
- This is not a place for fabrication. **Every architectural / technology / ontology decision
  must be grounded** in the source documents here and in real external literature/repos —
  research before deciding, never invent.
- All new work happens in this folder (`Realist Evidence Synthesis V2/`). The sibling folder
  `../LLM-Knowledge-Graph/` is the **old version** (built with Cursor/Antigravity) — read it
  for reference and lessons, but do not build there.
- Aim for professional, tidy, optimized structure down to naming conventions. Quality over speed.

## Where things are
- `data/` — Richmond corpus: `20-paper-of-Richmond/` (20 PDFs) + 8 abstract/metadata records,
  `paper-Richmond-original.pdf`, `in4-about-28-studies-paper.pdf`, `studies_metadata.jsonl` (28 studies).
- `documents/` — professor's briefing material: `abstract-from-professor/abstract.md` (the
  accepted RRE proposal), `plan_verification_text.txt` (8-step verification protocol),
  `new-documents-from-professor/` (3 PDFs: agentic framework, KG+GraphRAG, plugin agent — the
  freshest guidance), `Human-Workflow-from-paper-Richmond.pdf`, `paper-Microsoft-GraphRAG.pdf`.
- `transcript-meetings/` — weekly RA↔professor meetings (Jan 23, Feb 4, Feb 19, **May 28**).
- `docs/` — project memory maintained by Claude (`PROJECT_CONTEXT.md`, `DECISION_LOG.md`).

## Read these first when asked "what is the output / how do we verify it?"
1. **`outputs/RESULTS.html`** (regenerate with `res export-results`) — the whole review as one
   self-contained page: Richmond's conclusions beside ours, context by context; the verification
   matrix with exact confidence intervals and a *judged by* column; all 46 gold concepts one by
   one; and every CMOC, entity, relation and emergent mechanism, searchable. This is the artefact
   to send to the professor or open in an interview. No server, no database.
2. **`docs/VERIFICATION_PROTOCOL.md`** — why those are the right metrics, with citations, and the
   honest list of what is still missing. The blocking gap is that **no human has coded anything**,
   so there is no human–human ceiling and the agreement-style numbers are uninterpretable.
3. **`gold/RICHMOND_CONCLUSIONS.md`** — what Richmond actually concluded, grounded line by line.

The benchmark is `gold/richmond_gold_v3.json` (corrected 2026-09-23; `RES_GOLD=v1` reproduces
every earlier published number). Never quote the relation type-level score without the anchored
and strict tiers, never quote entity coverage role-tolerant without like-for-like, and never quote
a single programme-theory correspondence number — two judges differ by 0.31 on identical inputs.

## Status pointer
**Architecture v1.0 adopted** (`docs/ARCHITECTURE.md`, grounded in `docs/research/SOTA_REPORT.md`).
Build authority granted; next step is Phase 0 (repository scaffold + config + ontology file),
then phases 1–7 per ARCHITECTURE §8. See `docs/PROJECT_CONTEXT.md` for full context and
`WALKTHROUGH.md` for the milestone log — **append a WALKTHROUGH entry every session** (standing
RA requirement). Credentials live in `.env` (OpenAI key, Postgres password; Neo4j not yet set up).
