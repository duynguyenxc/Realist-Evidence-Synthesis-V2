# Working plan — Prof. Zheng's assignment of 2026-10-30

**Opened 2026-11-10. Retire this file when deliverable #6 is sent**, then fold what is still
true into `WALKTHROUGH.md`. It exists so the work survives a session boundary without being
re-decided, and so the RA can check progress without reading the repository.

> **Precedence.** This is a to-do list, not a record. **Where it disagrees with the repository,
> the repository wins** — and the disagreement means this file is stale and must be fixed. The
> repository's own staleness is the problem this plan was written to clear (see §1), so a plan
> that rots the same way would be worse than none.

**Approved by the RA 2026-11-10:** do Phase A; deliver in **two batches** (B first, then C).

---

## 0. What the professor asked for

Six deliverables, in his numbering. Full breakdown of all six sections of the email is in the
2026-11-10 chat; the short form:

| # | Deliverable | Phase |
|---|---|---|
| 1 | Complete package: pipeline, inputs, outputs, architecture, prompts, evaluation | B |
| 2 | AI assessment of what is needed for the new topic + step-by-step implementation plan | B |
| 3 | Preliminary literature collection and structured evidence database | C |
| 4 | Initial CMOCs and a knowledge graph | C |
| 5 | Preliminary synthesis | C |
| 6 | Progress report: done / limitations / next | B |

His own sequencing instruction, easy to miss: *"begin by reviewing the existing pipeline with AI
and determining what we need to prepare, then proceed with the literature search and a small
pilot study."* Phases A→B→C follow it.

---

## 1. Phase A — make the record consistent  ✅ DONE 2026-11-10

Found by the 2026-11-10 audit. The figures changed on 2026-11-04 and 24 written artifacts
predate that. The professor is an outsider: if the report says 73.9% and the docs say 69.6%,
he loses confidence in every number, including the correct ones.

- [x] **A1** Rebuild `outputs/SEND_TO_PROFESSOR/0_REPORT.html`. It is dated 25 Sep and prints
      **73.9%** and **89.1%**; current figures are **69.6%** and **84.8%**. Print a
      *previously published* column beside the corrected one — we correct in the open, we do
      not quietly restate.
- [x] **A2** Mark the four professor-facing files that carry superseded figures with **no
      warning**: `docs/FOR_THE_PROFESSOR.md` (2), `outputs/SEND_TO_PROFESSOR/0_REPORT.html` (1),
      `HANDOFF_FOR_NEW_MACHINE.md` (8), `docs/ANSWERS_TO_FIVE_QUESTIONS.md` (4, partial).
- [x] **A3** Fix three statements in `docs/PROJECT_CONTEXT.md` §6 that P0 falsified hours after
      §6 was written: "prompts are embedded in code", "`config/prompts/` is empty",
      "`ratified_by: null`". Same for `docs/ARCHITECTURE.md` (prompts).
- [x] **A4** Rewrite `README.md`. It says **four** adjudication checkpoints (there are **five**)
      and mentions none of `res search`, `res acquire`, `res theorise`, `/raw`,
      `outputs/raw_export/`, `config-emotion/`, `scripts/export_prompts.py`.
- [x] **A5** Re-sweep the whole repository for figure mismatches; the exit condition is **zero
      unmarked occurrences** of 34/46, 38/46, 41/46, 28/46, 45/46, 73.9, 89.1, 6/40, 29/40.

**Not to be touched:** `outputs/RESULTS.html` and `SEND_TO_PROFESSOR/2_RESULTS.html` are
import-only and irreproducible (M39 §4). A1 states plainly that they carry the superseded
numbers and why they cannot be regenerated. That is a fact to disclose, not a defect to hide.

---

## 2. Phase B — deliverables #1, #2, #6  ✅ DRAFTED 2026-11-13

- [x] **B1** (#1) One navigation document over: the repository, `outputs/raw_export/`
      (16 tables, 2,736 rows, unmediated), `config/prompts/`, `config/agents.yaml`,
      `config/ontology.yaml`, the verification reports, the AERA paper.
- [x] **B2** (#2) Answer the **seven questions** he asks in §2 — materials needed; research
      questions / inclusion criteria / definitions / frameworks; required inputs and their
      organisation; what is reusable vs needs modification; how to find and process the
      literature; how evidence is extracted, integrated and validated; how results are
      evaluated into a publishable study. Each answer anchored to real code, not aspiration.
- [x] **B3** (#6) Progress report: completed / limitations / next steps.
- [ ] **B4** Draft the covering email for the RA to send, including the two items the professor
      does not yet know: the AERA acceptance of 2026-11-06 with **reviewer comments still
      unread**, and that the accepted paper carries the superseded 34/46 and 28/46.

---

## 3. Phase C — deliverables #3, #4, #5

- [ ] **C1** RA reviews `config-emotion/protocol.yaml`. Its eligibility criteria decide what the
      review is *about*; `ratified_by` is correctly `null`.
- [ ] **C2** `createdb realist_emotion`; set `RES_CONFIG_DIR`, `RES_DATA_DIR`,
      `RES_OUTPUTS_DIR`, `POSTGRES_DB` in `.env`. Until then `assert_isolated()` blocks every
      writing stage — by design, so a new topic cannot overwrite Richmond.
- [ ] **C3** (#3) `res search` → corpus + structured evidence database. Metadata only, cheap.
- [ ] **C4** **Pilot of 10–15 papers first, and report the measured cost**, because
      `token_usage` is empty (lost in the M39 restore) so there is no cost history to estimate
      from. `max_usd_per_full_run` is configured at $45 for 28 papers.
- [ ] **C5** (#4) Screen → extract → CMOCs + knowledge graph.
- [ ] **C6** (#5) Synthesis: promising interventions, mechanisms, conditions.

---

## 4. How the professor-facing documents get written

He has not seen this system and does not know what it does. Hold me to these:

1. **Write for someone who has never seen it.** Open with the problem it solves, not the
   architecture.
2. **Use the conventions he will recognise** — PRISMA/RAMESES reporting for #3–#5: flow counts,
   search strategy, inclusion criteria, stated limitations.
3. **Every number traceable** to a table and row in `outputs/raw_export/`.
4. **No promotional adjectives.** Limitations stated where the result is stated, not deferred
   to a final section.
5. **Disclose what was wrong.** The matcher defect, and that the figures were previously higher.
   An AERA reviewer who checks will find it; self-disclosure is always stronger.

---

## 5. Open — needs the RA

- [x] ~~Cost ceiling for Phase C~~ — Proposed default unless overridden: **pilot ≤ $10**, report
      the measured cost, then decide. Not yet answered.
- [ ] **The 21 HITL decisions are uncountersigned** (`0/20` contradictions, programme theory
      signed `ai-ra:claude(...awaiting countersignature)`). Only the RA can do this, and the
      professor's §4 asks us to *preserve* human verification — which cannot be preserved if it
      has never happened. ~15 minutes at `res webui` → `/review`.
- [ ] **AERA reviewer comments unread.** aera.net → login → 2027 Annual Meeting → Online Portal
      → Submitter Menu → Read your Reviews. May change what Phase B says.

---

## 6. Log

| Date | Item | Note |
|---|---|---|
| 2026-11-10 | Plan opened | Audit found the staleness in §1; RA approved A and two-batch delivery |
| 2026-11-13 | **Four $0 items done** | Computed comparison layer, motif null model, graph consistency checks, precision bound. Two changed what the project may claim |
| 2026-11-13 | **Email re-checked item by item** | Four things the professor names explicitly were missing from `config-emotion/` and were added; all 8 topics and 9 examples now named verbatim |
| 2026-11-13 | **Repository audited** | 39 modules, no dead code. Documents classified current / superseded-and-marked / historical / frozen. Two false stack claims retracted |
| 2026-11-13 | **Phase B drafted** | `handover/` — deliverables 1, 2, 6. Fact-checked against the database; the check caught a wrong prompt count (24, not 23) |
| 2026-11-13 | **Budget decision** | RA: **no budget available — $0 work only**. Phases C and M are suspended; the $0 items in deliverable 2's plan (steps 1–4) are what proceeds |
| 2026-11-10 | **Phase A complete** | Exit check passes: **0 unmarked superseded figures** outside the four excluded classes below |

**What Phase A actually found, beyond stale numbers.** Two substantive errors were in the
professor-facing report, not just outdated figures:

1. `0_REPORT.html` stated *"There is still only one human coder … the 0.785 above is human against
   an independent LLM pass."* **Both halves are false** — two people coded all 28 papers on
   2026-09-25, so 0.785 is a genuine inter-rater reliability figure. The report was *understating*
   the project's own evidence, the same error as the AERA manuscript. Corrected in place.
2. `README.md` advertised **LangChain, LangGraph, Microsoft GraphRAG and Neo4j** as the stack.
   None is imported anywhere; the first three are not even dependencies, and no Neo4j database was
   ever created. For a methods paper this is the worst class of error — a false claim about the
   architecture itself — and the repository is the first thing a reviewer would clone. Retracted
   explicitly in the new README rather than quietly deleted.

Also corrected: `README.md` said **four** adjudication checkpoints (there are five) and mentioned
none of the work of the past week.

**Excluded from the sweep by rule, each for a reason:**

| | Why |
|---|---|
| `WALKTHROUGH.md` | Append-only history; supersession is marked inline where it occurred |
| `outputs/RESULTS.html`, `SEND_TO_PROFESSOR/2_RESULTS.html` | Irreproducible (M39 §4). `0_REPORT.html` now discloses that they carry the old numbers and why they cannot be rebuilt |
| `outputs/runs/verify-*/` | Per-run records. Run `verify-edcbf790` **did** produce 41/46 on that date with that matcher; editing it would falsify a run |
| `PROJECT_BACKUP_2026-09-30/` | Gitignored, 0 tracked files, 49 MB on disk only — not part of the repository |
