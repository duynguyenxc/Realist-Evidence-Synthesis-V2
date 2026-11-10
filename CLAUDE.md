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
- **Append a `WALKTHROUGH.md` entry at the end of every session** — detailed enough that the next
  session can pick the work up *without re-reading the repository*, and without re-deciding
  something already decided. Say what was verified and **how**; say what was found and left
  unfixed; say what the next session must not assume. This is the cheapest thing in the project
  and the only thing that makes the rest cheap to come back to.
- **Orient from two files, not from the repo**: this one, then `WALKTHROUGH.md` (newest entry
  first, it is append-only). Open `docs/PROJECT_CONTEXT.md` and the rest only when the task needs
  them. Reading everything every time burns tokens and still gets the history wrong.

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
1. **`outputs/RESULTS.html`** — **import-only; never regenerate.** The whole review as one
   self-contained page: Richmond's conclusions beside ours, context by context; the verification
   matrix with exact confidence intervals and a *judged by* column; all 46 gold concepts one by
   one; and every CMOC, entity, relation and emergent mechanism, searchable. This is the artefact
   to send to the professor or open in an interview. No server, no database.
   **`res export-results` must never be run again.** The 28 human decisions this page reports live
   in `hitl_feedback`, which the markdown-based snapshot restore could not carry (M39 §4), so any
   re-export silently reports **0** and overwrites the only surviving record of them. Rebuild the
   *database* with `scripts/import_snapshot.py`; leave this file alone.
2. **`docs/VERIFICATION_PROTOCOL.md`** — why those are the right metrics, with citations, and the
   honest list of what is still missing. **Human coding is done and the ceiling exists**: two human
   coders, all 28 papers, blind, 2026-09-25; **positive specific agreement 0.785** (RA-confirmed
   2026-11-02 — `MACHINE_VS_HUMAN.md` §5 is right, and **the AERA draft is wrong** where it calls
   Coder B "a general-purpose model" and disclaims the reliability figure; fix the manuscript, not
   the record). The defensible claim is still **non-inferiority, not superiority** — under the
   one-to-one constraint the humans worked under, the system scores 28/46, equal to Coder B.
   `docs/MACHINE_VS_HUMAN.md` §5 is the authoritative record; the word *exceeds* must not appear.
   **The matcher defect is fixed (2026-11-04)** — `verification/metrics.py` now refuses a
   `matched: true` whose rationale states a non-match or asserts opposite polarity, in all three
   judging passes. The recount cost two concepts and found a *second* error: §5's over-merge table
   had omitted `cont:knowledge-deficits` ← E02, E03, so 28 was already one too high. **Quote
   32/46 same-role and 26/46 one-to-one (39/46 role-crossing)** — `MACHINE_VS_HUMAN.md` §5.1 has
   the arithmetic. The system is **two below Coder B, not equal**, so non-inferiority now rests on
   overlapping CIs, not parity. **Relation recovery was computed exactly on 2026-11-06** — no re-run
   was needed, because `relation_coverage()` is a pure function of the entity matches: **strict
   5/40, anchored 28/40** (from 6/40 and 29/40), type-level unchanged at 39/40.
3. **`gold/RICHMOND_CONCLUSIONS.md`** — what Richmond actually concluded, grounded line by line.

The benchmark is `gold/richmond_gold_v3.json` (corrected 2026-09-23; `RES_GOLD=v1` reproduces
every earlier published number). Never quote the relation type-level score without the anchored
and strict tiers, never quote entity coverage role-tolerant without like-for-like, and never quote
a single programme-theory correspondence number — two judges differ by 0.31 on identical inputs.

## There are two projects, and they are not related
This one, and **OpenMAIC** in `~/Downloads/OpenMAIC` — Tsinghua's multi-agent classroom, which the
professor asked to have installed and extended in levels (Level 2 done and deployed; Level 3 not
started). It has its own `CLAUDE.md` and `WALKTHROUGH.md`; read those, not this file, for anything
about it. **No code is shared between the two projects, in either direction.** October 2026 was
spent entirely on OpenMAIC, which is why this log jumps from 30 September to M38.

## Active work
**`PLAN.md`** tracks Prof. Zheng's 2026-10-30 assignment through to delivery — a live checklist,
not a record, so where it disagrees with the repository the repository wins. Read it before
starting work; retire it when deliverable #6 is sent.

## Status pointer (rewritten 2026-11-09 — the old one still said "next step is Phase 0")
**Phases 0–7 are built and the pipeline has run end to end twice** (M34, M35). The database holds
547 entity instances, 459 typed relations, 94 CMOCs, 8 conceptual entities. Verification is done
and the matcher defect is fixed. **P0, P1 and P2 of the 2026-11-04 plan are complete**
(`docs/IMPROVEMENT_PLAN.md` §6, WALKTHROUGH M40 §§7–8): the HITL checkpoints have been performed
and signed `ai-ra:claude(...awaiting countersignature)`, prompts are extracted to
`config/prompts/`, and the pipeline now has a literature search (`res search` — OpenAlex and
Crossref), full-text acquisition (`res acquire`), BM25 retrieval, and retroduction without a quote
(`res theorise`). `config-emotion/` is a complete draft configuration for the professor's new topic.

**Three things are waiting on a person, not on code:** the 21 HITL decisions are uncountersigned,
`config-emotion/protocol.yaml` is an unreviewed draft, and **nothing in P2 has been run against a
real corpus** (no `data-emotion/`, no emotion database). **The AERA 2027 paper was accepted on
2026-11-06** (Division D roundtable, Toronto, April 2027); reviewer comments sit unread on the All
Academic portal, and the accepted paper carries the superseded 34/46 and 28/46 figures.

See `docs/PROJECT_CONTEXT.md` §6 for full context and `WALKTHROUGH.md` for the milestone log —
**append a WALKTHROUGH entry every session** (standing RA requirement). Credentials live in `.env`
(OpenAI key, Postgres password; Neo4j adapter exists but no database was ever created).
