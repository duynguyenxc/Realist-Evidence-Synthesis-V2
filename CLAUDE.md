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

## Status pointer (updated 2026-11-17 — the pool is described, and the questions are the professor's)
**Phases 0–7 are built and the pipeline has run end to end twice** (M34, M35). The database holds
547 entity instances, 459 typed relations, 94 CMOCs, 8 conceptual entities. Verification is done
and the matcher defect is fixed. **P0, P1 and P2 of the 2026-11-04 plan are complete**
(`docs/IMPROVEMENT_PLAN.md` §6, WALKTHROUGH M40 §§7–8): the HITL checkpoints have been performed
and signed `ai-ra:claude(...awaiting countersignature)`, prompts are extracted to
`config/prompts/`, and the pipeline now has a literature search (`res search` — OpenAlex and
Crossref), full-text acquisition (`res acquire`), BM25 retrieval, and retroduction without a quote
(`res theorise`). `config-emotion/` is a complete draft configuration for the professor's new topic.

**Two claims were withdrawn on 2026-11-13** (M41 §3; the three modules are `res motif-test`,
`res check-graph`, `res compare-theory`, all $0, outputs committed under `outputs/analysis/`).
**Never report "32 demi-regularities" as a result** — a degree-preserving permutation null expects
**32.3** by chance against 32 observed (27.6 under the stricter within-study shuffle) and **no motif
survives FDR q<0.05**; they are candidates for adjudication. And the Richmond comparison is now
**computed, not hand-written**: three of the five programme-theory statements **recover the full
causal chain and fail to name the population** (PTS2, PTS4, PTS5 — PTS5 returns 3/3 interventions,
4/4 mechanism-responses, 5/5 outcomes, and the old page had called it a corpus gap). That weakness
is the same defect as M40's 22 orphan Contexts and needs normalisation re-run, which is forbidden on
Richmond — carry it into the new topic, do not repair it here. Graph consistency: **1 defect** (a
3-concept cycle) over 547/459/94; the 29 "both polarities in one study" hits are **two-arm designs,
not errors**. Precision is **bounded, not measured**: 31 of our 183 concepts have a Richmond
counterpart, 152 do not, 72 of those are a single mention in a single study — never write
"precision = 31/183".

**The new topic has a candidate pool as of 2026-11-16** (M42). `realist_emotion` database,
`data-emotion/` (gitignored) and `outputs-emotion/` exist; the emotion review runs under **exported**
env vars — `RES_CONFIG_DIR=config-emotion RES_DATA_DIR=data-emotion RES_OUTPUTS_DIR=outputs-emotion
POSTGRES_DB=realist_emotion` — never written into `.env`, which is shared with Richmond.
**1,863 candidate records** (89% abstract, 68% an OA PDF *link* — only **434 full texts actually
download**, see `outputs-emotion/ACQUISITION_REPORT.md`; 274 reviews), from ten blocked
boolean queries recorded in `config-emotion/protocol.yaml` §`search_strategy` and executed only by
`scripts/run_protocol_search.py`. `outputs-emotion/SEARCH_REPORT.md` is **generated** by
`scripts/search_report.py`, never written by hand. **It is a pool, not a corpus** — nothing has
been screened, and `res screen` is the first stage that spends credit. **Search, acquire and ingest
call no model**; deliverable #3 had been wrongly filed as entirely budget-blocked. Three traps:
`RES_GOLD_DIR` still points at Richmond's `gold/`, so **never run `res verify` on the emotion
review**; **any Crossref result from before 2026-11-16 is void** (cursor paging silently dropped
relevance ranking); and **"OpenAlex is free and keyless" expired 2026-02-13** — it bills $0.001 a
search against a $0.10/day budget shared per network IP, so the manuscript's credential-free
reproducibility claim needs qualifying.

**The pool is now described, 2026-11-17** (M43), still at $0. `config-emotion/coding_frame.yaml`
(a theory-grounded dictionary: Gross's five regulation families via **ERAS** — Harley, Pekrun,
Taxer & Gross 2019, the paper that joins the professor's two theoretical references — plus
Pekrun's nine achievement emotions and his own intervention and context lists verbatim) is applied
by `scripts/evidence_map.py` to all 1,863 records. **It counts term presence in titles and
abstracts: nothing in it is a CMOC and no number in it is evidence of effectiveness.** Three
findings, dictionary-based and provisional, strong enough to ask the professor about and not to
publish: **anxiety is 578 of 678** emotion-tagged records; **three of his five named interventions
are nearly absent** (self-regulation activities 7, awareness prompts 6, learning plans 17) while
mindfulness, unnamed by him, has 291; and **STEM is 51 records** (engineering 20 + computing 18 +
natural sciences 13) of 1,088 higher-education ones. The frame carries a `revisions:` block —
**add to it, never edit a term silently**. A second search arm was added because every corpus query
requires an intervention term and therefore could never reach the theory literature:
`theory_pool.jsonl`, 445 records, **not the corpus**. And `outputs-emotion/COST_MODEL.md` closed
the standing "no cost history" limitation: **screening the whole pool is $5.44** — the $45 ceiling
was always extraction of 28 full papers. `handover/0_REQUIREMENTS_MATRIX.md` is the clause-by-clause
answer to the email and ends with four questions only the professor can settle.

**The RA suspended all paid work on 2026-11-13 — there is no budget.** Ask before planning anything
that spends credit. `handover/` holds deliverables 1, 2 and 6 as drafts in Claude's voice: **unread,
uncorrected and unsent**, and the RA sends them, not Claude.

**Three things are waiting on a person, not on code:** the 21 HITL decisions are uncountersigned,
`config-emotion/protocol.yaml` is an unreviewed draft, and **nothing in P2 has been run against a
real corpus** (no `data-emotion/`, no emotion database). **The AERA 2027 paper was accepted on
2026-11-06** (Division D roundtable, Toronto, April 2027); reviewer comments sit unread on the All
Academic portal, and the accepted paper carries the superseded 34/46 and 28/46 figures.

See `docs/PROJECT_CONTEXT.md` §6 for full context and `WALKTHROUGH.md` for the milestone log —
**append a WALKTHROUGH entry every session** (standing RA requirement). Credentials live in `.env`
(OpenAI key, Postgres password; Neo4j adapter exists but no database was ever created).
