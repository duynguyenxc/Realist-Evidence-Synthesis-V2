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
- [x] **C2** ✅ **2026-11-16.** `realist_emotion` created, `data-emotion/` and
      `outputs-emotion/` created. The env is passed per command rather than written into
      `.env`, because `.env` is shared with Richmond and `load_dotenv` does not override the
      shell — so an exported variable isolates this review without leaving a trap set for the
      next session that runs a Richmond command.
- [x] **C3** (#3, first half) ✅ **2026-11-16.** Search run: **1,863 candidate records**, 89%
      with an abstract, 68% with an open-access PDF link (572 full texts obtained).
      `outputs-emotion/SEARCH_REPORT.md` is
      generated from `search_log`, not written. The protocol's pre-registered validity check
      passed on all four of the professor's named references. **The second half of #3 — a
      "structured evidence database" — needs screening, which costs money.** Four defects were
      found and fixed in the search code on the way; see WALKTHROUGH M42.
- [x] **C3b** (#3, descriptive half) ✅ **2026-11-17.** `config-emotion/coding_frame.yaml` —
      a theory-grounded dictionary (Gross's five families via ERAS 2019; Pekrun's nine achievement
      emotions; the professor's intervention and context lists verbatim) applied to all 1,863
      records with **no model call**. `outputs-emotion/EVIDENCE_MAP.md` is generated from it.
      Three findings for the professor: anxiety is 578 of 678 emotion-tagged records; three of his
      five named interventions are nearly absent; STEM is 51 records. Frame revised 1.0 → 1.1 after
      its own promiscuity diagnostic exposed four over-matching terms.
- [x] **C3c** (search, second arm) ✅ **2026-11-17.** Three theory-only queries added and run into
      `theory_pool.jsonl` (445 records), after finding that ERAS — the paper joining the professor's
      two theoretical references — was unreachable by every corpus query by construction.
- [x] **C4a** ~~No cost history, so cost can be measured but not estimated~~ ✅ **2026-11-17.**
      `outputs-emotion/COST_MODEL.md`, computed from the rendered system prompt and
      `config/models.yaml`. **Screening the whole pool is $5.44**; the $45 figure was always
      extraction of 28 full papers.
- [ ] **C4** **Pilot of 3–10 papers, and report the measured cost.** Now costed rather than
      guessed: 3 papers ≈ $4–5, 10 ≈ $13–16, screening + 10-paper pilot ≈ $21. The pilot still
      exists to replace the projection with a measurement.
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

> ### ▶ RESUME HERE — paused 2026-11-17 midday, RA resting; picking up the same afternoon
>
> **Everything through 17 November is committed and pushed** (`1e40591`). Working tree clean,
> 26 tests passing. Nothing is half-finished in the code or the documents; what remains is
> three decisions and one optional download.
>
> **The three things only you can do, in this order:**
>
> 1. **Countersign the 21 HITL decisions** — `res webui`, then `/review`. ~15 minutes. The one
>    item no further work by Claude can close, and it is exactly what the professor's §5 asks
>    for. Until it is done, every checkpoint in the record reads `ai-ra:claude`.
> 2. **Read `handover/0_REQUIREMENTS_MATRIX.md`**, especially the four questions at the end.
>    Correct anything that is not in your voice — the handover is drafted in Claude's.
> 3. **Decide how the package goes to the professor** — attached files, GitHub link, or both.
>    Claude drafts the email; **you press send.** That was never delegated.
>
> **Deferred on purpose, not forgotten:** `res acquire --confirm` would download 1,266
> open-access full texts for nothing, but it is only useful once there is budget to extract
> from them, so it was judged not urgent. The report is complete without it.
>
> **What the afternoon session must read first:** this block, then `CLAUDE.md`'s status
> pointer, then `WALKTHROUGH.md` **M42** (the search and its four defects) and **M43** (the
> evidence map and the three literature findings). Those two entries contain everything from
> the 16–17 November sessions; the conversation added no decision that is not in them.
>
> **The one framing worth keeping from the conversation**, because it decides how the report
> reads: three weeks produced no finding *about emotion regulation* until 17 November, and the
> defensible case is not "look what we built" but **"four things this project was claiming were
> false, and they were caught before a journal submission"** — with the literature findings and
> the $25 ask as the forward half. The requirements matrix is written that way.

- [x] ~~Cost ceiling for Phase C~~ — Proposed default unless overridden: **pilot ≤ $10**, report
      the measured cost, then decide. Superseded 2026-11-17: the cost is now computed, not
      proposed — **$5.44 screens the whole pool**, a 3-paper pilot is $4–5, screening plus a
      10-paper pilot about $21 (`outputs-emotion/COST_MODEL.md`). Still unanswered, but it is
      now a question with a number attached.
- [ ] **The 21 HITL decisions are uncountersigned** (`0/20` contradictions, programme theory
      signed `ai-ra:claude(...awaiting countersignature)`). Only the RA can do this, and the
      professor's §4 asks us to *preserve* human verification — which cannot be preserved if it
      has never happened. ~15 minutes at `res webui` → `/review`.
- [ ] **Four research questions put to the professor 2026-11-17** and unanswered, each one
      capable of changing what the review is: (1) is STEM the focus or the gap, given 51 records;
      (2) follow his five named interventions or the literature's mindfulness-and-reappraisal
      centre; (3) one emotion or nine, given anxiety at 578 of 678; (4) may we spend ~$25.
      `handover/0_REQUIREMENTS_MATRIX.md` states all four. His §5 invites exactly these.
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
| 2026-11-16 | **Every remaining $0 stage identified** | `res search`, `res acquire` and `res ingest` call no model. Money starts at `res screen`. Deliverable #3 was wrongly filed as fully budget-blocked |
| 2026-11-16 | **Search run — 1,863 records** | OpenAlex 10 boolean queries + Crossref cross-check, isolated database, report generated from the log. Pre-registered validity check passed 4/4 |
| 2026-11-16 | **Four search defects found and fixed** | Full-text matching inflating the pool 44×; Crossref losing relevance ranking under cursor paging; `oa_pdf_url` dropped from the corpus format; one failed query discarding the whole run. Three now have regression tests |
| 2026-11-17 | **Theory arm added to the search** | ERAS (Harley/Pekrun/Taxer/Gross 2019) was unreachable by every corpus query by construction — no intervention or population term in its title/abstract. 3 theory queries, 445 records, pooled separately |
| 2026-11-17 | **Evidence map built, $0** | Theory-grounded dictionary over 1,863 records. Anxiety 578/678; 3 of the professor's 5 named interventions nearly absent; STEM 51 records. Frame self-diagnosed 4 bad terms and was revised |
| 2026-11-17 | **Cost model closes a standing limitation** | $5.44 screens the whole pool. "No cost history" was partly arithmetic nobody had done |
| 2026-11-17 | **Requirements matrix written** | `handover/0_REQUIREMENTS_MATRIX.md` — every clause of the email with a status and a file, plus 4 questions the professor must answer |
| 2026-11-16 | **"Free, keyless" retracted** | OpenAlex has required a key since 2026-02-13 and bills per request. The reproducibility claim in the manuscript needs the qualification |

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
