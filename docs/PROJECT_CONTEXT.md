# PROJECT CONTEXT — Realist Evidence Synthesis (living memory)

_Last updated: 2026-07-14. Maintained by Claude. This is the authoritative project memory.
Update it whenever understanding, decisions, or status change._

---

## 1. What this project actually is

- **Real deliverable:** a manuscript for **Review of Research in Education (RRE), Volume 50
  (2026)** — a AERA journal. It is a **methodological-innovation paper with a worked example**,
  explicitly *not* a tool/system paper and *not* a re-run of one review.
- The abstract/proposal was **already accepted** by the journal (see
  `documents/abstract-from-professor/abstract.md`).
- **Principal investigator / professor:** Wei Zheng. **RA (project owner / our collaborator):**
  Duy Nguyen. Meetings are weekly.
- **Framing that must survive peer review** (from the professor's editor-style critique):
  1. Method > platform (the AI system is *infrastructure enabling a method*, not the contribution).
  2. Review-methodology scholarship > AI novelty (introduction must read as if it could have been
     written before LLMs existed, then introduce AI as the enabler).
  3. Must address **change in complex educational systems** (RRE's mission).
  4. Human interpretive judgment preserved and foregrounded.

## 2. The proposed method (what we are building)

An **agentic, human-in-the-loop, GraphRAG-based multi-agent pipeline** for realist synthesis,
organized as a **core-and-plugin architecture**:

- **Core Review Infrastructure (method-agnostic "Review OS"):** protocol/scope, retrieval +
  provenance, study registry + deduplication, two-stage screening, reporting/audit export,
  and the HITL control layer.
- **Realist Synthesis Plugin (method-specific, the worked example):** IPT management, CMOC
  extraction, cross-study synthesis / demi-regularity detection, contradiction & sensitivity.
- The paper lays out *other* plugins conceptually (QCA, framework/thematic, meta-ethnography/CIS,
  meta-analysis/mixed-methods) but only **implements the Realist plugin**.

**Default agent set (~9–10 operational agents)** — professor's latest layout (NotebookLM doc):
Protocol & IPT · Search & Retrieval · Deduplication · Title/Abstract Screener ·
Full-Text Acquisition · Full-Text Eligibility · CMOC Extraction · (Normalization) ·
Theory Synthesis & Refinement · Contradiction & Sensitivity · Reporting & Audit.
> **Important correction from the professor:** the "Benchmark Agent" that compares model vs
> human is **NOT** part of the production pipeline. Model-vs-Richmond comparison is a
> *separate, independent evaluation activity* done for research verification only.

**Orchestration:** LangChain + **LangGraph** (stateful state-machine; "GraphChain" the professor
asked about is not a real product — LangGraph is the answer). Agents share a **single-source-of-truth
state** (study registry, LKG, CMOC store, theory store, audit log).

**Knowledge substrate:** a **Literature Knowledge Graph (LKG)** built with Microsoft **GraphRAG**
(entity/relation extraction + Leiden community detection + embeddings). **GraphRAG** retrieves
*subgraphs of connected claims* rather than isolated chunks, enabling configuration-level
("why/for whom/in what circumstances") reasoning. Professor's recurring concept: **"MOTIF
detection"** = treating CMOCs as recurring subgraph patterns; used for demi-regularity
consolidation and contradiction detection. He is aware subgraph isomorphism is NP-hard and
argues it is workable because relevant paper sets are small, retrieval is localized, and
embeddings/community structure prune the space.

**HITL "Master Control" — 4 checkpoints** (human decisions dominate; every correction is
recycled into prompts/rules = "lifelong/continual learning", with a "redo" trigger):
1. Screening adjudication (few-shot calibration on a stratified sample).
2. CMOC extraction validation (ground-truth spot-check).
3. Contradiction adjudication (human resolves conflict register).
4. Programme-theory sign-off.
Professor's forward-looking ideas: a "Living Project Handbook" (semantic policy anchoring),
active preference learning (RLHF-style), and an Adjudication UI sorted by uncertainty.

## 3. The Richmond benchmark (the worked example / gold standard)

Richmond A., Cooper N., Gay S., Atiomo W., Patel R. (2020). *The student is key: a realist review
of educational interventions to develop analytical and non-analytical clinical reasoning ability.*
Medical Education, 54(8), 709–719. https://doi.org/10.1111/medu.14137

- **RAMESES-standard realist review.** Workflow: Theory seeding (IPT, grounded in Dual-Process
  Theory) → structured search (MEDLINE, PsycINFO, ERIC, CINAHL; post-2000) → two-stage screening
  → CMOC extraction over **28 included papers** → synthesis of demi-regularities → final
  programme theory.
- **Headline finding:** *the student is key* — 5 student **contexts** defined mainly by
  pre-existing knowledge and self-confidence/self-efficacy determine which interventions work.
  Key phenomenon: **Expertise Reversal Effect** (directive/explicit teaching helps novices but
  hinders experts; unsupported observation harms low-knowledge students).
- **Corpus:** all 28 studies are clinical-reasoning-in-medical-education RCTs/studies
  (analytical vs non-analytical reasoning, self-explanation, worked/erroneous examples, schema
  instruction, simulation/virtual patients, feedback, serious games). See
  `data/studies_metadata.jsonl` (20 full-text PDFs + 8 abstract-only records).

**Operationalized gold standard already exists** (in the old project,
`../LLM-Knowledge-Graph/data/gold_standard.json`) — a defensible machine-checkable benchmark:
- **47 entities E01–E47** typed as Context / Intervention / Mechanism_Resource /
  Mechanism_Response / Outcome, each with a verbatim label + page location in Richmond.
- **40 relationships R01–R40** as (subject, predicate, object) triples with predicates
  PROVIDES / ENABLES / TRIGGERS / LEADS_TO / CONSTRAINS.
- **5 programme-theory statements PTS1–PTS5**, one per student context, each a canonical
  C→M→O chain.
This is genuinely reusable and probably the single most valuable asset from the old version.
**Verified 2026-07-14 against the primary source** (`data/paper-Richmond-original.pdf`): the 5
contexts, resource/response mechanism split, the five per-context CMOC statements, Expertise
Reversal + Matthew effects, and the search strategy (MEDLINE/PsycINFO/ERIC/CINAHL, from 2000,
searched May 2017; 149 full texts → 25 + 2 reference-list + 1 later = 28) all match. The
E-code/R-code/PTS operationalization is faithful and reusable. Only gap: a per-paper CMO mapping
coded by a *real independent human* (not AI) is still needed for verification step 2.

## 4. Verification protocol (how success is judged — separate from the pipeline)

From `documents/plan_verification_text.txt` (professor's 8-step plan). Compare model output to
Richmond's human output at each stage; report structural/conceptual correspondence, not verbatim:
1. **Search/screening alignment** — same search scope; overlap of model's included set vs the 28
   (recall/precision; explain divergences). Professor's variant: feed ~100 papers incl. the 28,
   see how close the model lands.
2. **CMOC extraction fidelity** — precision/recall of extracted C/M/O vs Richmond's CMOCs.
3. **Community ↔ mechanism alignment** — do emergent communities match Richmond's mechanisms.
4. **Cross-study synthesis** — do the same dominant + conditional patterns emerge.
5. **Programme-theory correspondence** — structural/conceptual match to PTS1–PTS5.
6. **Grounded Q&A** — "what works, for whom, why", forced CMOC framing + citations.
Boundary: the system does **not** claim to automate normative theory choice / final judgment.

## 5. Lessons from the OLD version (`../LLM-Knowledge-Graph/`)

What it did: a 10-agent LangGraph + Microsoft-GraphRAG pipeline (GPT-4o-mini) enforcing the
E01–E47 ontology via strict Pydantic Union types; produced PRISMA report, evidence table,
programme theory, dashboards; 1,318 entities / 1,672 relationships / 245 communities.

Why the RA was dissatisfied / open gaps (from its own `documents/Current_Project_Status_Gap_Report.md`):
- **Not yet a defensible research result.** Corpus coverage of all 28 studies unproven.
- **Relationship evaluation against R01–R40 never implemented.**
- **HITL checkpoints were auto-approve placeholders**, not real auditable human review.
- Output artifacts predate later fixes; need reconciling.
- Hardcoded paths (`d:\LLM-Knowledge-Graph\...`), `node_modules` committed — messy repo hygiene.
- **Tension to resolve:** the old pipeline *hardcoded* Richmond's E01–E47 ontology, but the
  professor's stated novelty is **community-defined / emergent conceptual entities** (not a
  predefined ontology). Reconcile: emergent extraction for the *method*; map to E-codes only for
  *verification* against Richmond. This is a central design question — do NOT silently re-hardcode.

### Assessment of `outputs/adjudication/Richmond_Per_Paper_Adjudication_Completed.xlsx`
- **What it is:** 57 model-extracted CMOC rows from the 28 papers, then adjudicated into
  `human_corrected_*` columns to build a *per-paper* CMOC benchmark (43 included / 14 excluded);
  fills the gap `gold_standard.json` flagged (no per-paper CMOC mapping). Good idea, well-structured
  (model baseline preserved, evidence quotes, support scores, decision-status taxonomy, data dictionary).
- **Serious caveat:** the "human_corrected" adjudication was itself **AI-assisted** (there is an
  `ai_adjudication_confidence` column; summary says "AI-assisted expert adjudication"). Using
  AI-adjudicated codes as the *gold standard* to then verify an AI pipeline is **circular** and
  will not survive reviewer scrutiny. For a defensible benchmark this per-paper coding needs a
  **genuine, independent human coder** (ideally 2 + inter-rater κ), or must be explicitly labelled
  as a *candidate* requiring human sign-off — never presented as ground truth.
- **Second caveat:** 16/57 rows are **abstract-only** — CMOCs extracted without full text; fidelity
  claims from those are weak and must be flagged or excluded.
- **Verdict:** valuable scaffolding and a good template to reuse, but not a usable gold standard
  as-is. Keep the structure; replace the AI adjudication with real human coding.
## 6. Current status & next steps

> **Last rewritten 2026-11-04.** The previous version of this section was written on 2026-07-14 and
> was never updated, so it still listed documents as unread and decisions as open that were settled
> in July and superseded in September. If you are orienting, read `CLAUDE.md` then `WALKTHROUGH.md`
> (newest entry first); this section is the summary, not the log.

### Built, and run

**Phases 0–7 of `ARCHITECTURE.md` §8 are built and the pipeline has run end to end twice** — M34
(2026-09-24) and M35 (2026-09-24), the second differing from the first in ways M35 records. The
current database holds **547 entity instances, 459 typed relations, 94 CMOCs and 8 conceptual
entities**, restored on the present machine from `scripts/import_snapshot.py` (M37) and re-verified
against those counts in M39.

The deliverable artefact is **`outputs/RESULTS.html`** — one self-contained searchable page, no
server. It is **import-only and must never be regenerated**; see `CLAUDE.md` reading-list item 1 for
why, and M38/M39 for how that was established.

### Verification

Two human coders coded **all 28 papers**, blind, on **2026-09-25**; positive specific agreement
between them is **0.785**, so the human–human ceiling exists (RA-confirmed 2026-11-02 — see
`MACHINE_VS_HUMAN.md` §5, which is the authoritative record). The defensible claim is
**non-inferiority, not superiority**: under the one-to-one constraint the humans worked under, the
system recovers **28/46** concepts, equal to Coder B. **Quote 28/46 and nothing looser** until the
`verification/metrics.py` matcher defect is fixed. `docs/VERIFICATION_PROTOCOL.md` carries the
metric choices with citations and the honest list of what is missing.

### Decisions that were later reversed — do not go looking for the reversed versions

The July decisions in `DECISION_LOG.md` are the record of what was *decided*, not of what is
*there*. Three were superseded, each with citations, in `docs/IMPROVEMENT_PLAN.md` §3:

- **LangChain / LangGraph / Microsoft `graphrag` are deferred indefinitely** and none are imported.
  Orchestration is plain Python; HITL is a Postgres-backed checkpoint queue, not `interrupt()`.
- **Embedding clustering and community-summarisation-as-retrieval were dropped.** There are **no
  embeddings**; normalisation is LLM clustering over alphabetical batches of 40.
- **There is no BYOG index and no global/local search.** `ARCHITECTURE.md` §4 states it plainly: the
  composer receives the whole evidence pack inline, which is context stuffing, not retrieval.

Of the three "still-pending decisions" in `DECISION_LOG.md`: the **second human coder happened**
(2026-09-25); **Neo4j was never set up** (the adapter exists, the database does not, and nothing
depends on it); a **budget ceiling was never set**.

### Open, and ordered

1. **`verification/metrics.py` lets a rationale that states a non-match set `matched: true`** (E03,
   E24; E24 is inside the headline 34). Found 2026-09-30, open since. Fixing it will *lower* the
   headline, which is the correct direction.
2. **No human has ever performed a HITL checkpoint.** Every one is signed
   `delegate:claude-code(RA-authorized-2026-07-14)` or `expert:claude(delegated-reviewer-per-RA-2026-07-14)`,
   and `initial_programme_theory.yaml` has `ratified_by: null`. The `/review` console is built and
   unused. This is the project's defining claim and the one operation never exercised.
3. **A negative-affect blind spot.** Five gold concepts are recovered at no tier, four of them about
   fear, pressure or low self-efficacy. Cause is open between ontology, prompt and corpus. This
   matters now rather than later because the new topic is emotion.
4. **No literature search and no full-text acquisition.** Richmond's 28 papers were handed to the
   pipeline. `docs/PROFESSOR_VISION_AND_GAPS.md` §2 has the full gap table.
5. **`config/prompts/` is empty** — prompts are embedded in code, and the professor asks for them by
   name.

### The new direction

Prof. Zheng's email of **2026-10-30** parks the learning platform and redirects this pipeline to
**students' emotional awareness and emotional regulation during learning** (higher education, STEM
focus), asking for six outputs and naming Pekrun 2006, Gross 1998, Brackett et al. 2012 and Durlak
et al. 2011 as seeds. **§5 of that email delegates the human-in-the-loop role to the RA in
writing** — authority the project did not previously have. The email is the specification; see M39
for what has been done against it, which so far is only the preparation.

A second review has somewhere to write: `RES_CONFIG_DIR`, `RES_DATA_DIR`, `RES_GOLD_DIR` and
`RES_OUTPUTS_DIR` override the project paths, and `res status` prints which are overridden. **The
Richmond corpus, `gold/` and `outputs/` must not be written to by a new topic.**
