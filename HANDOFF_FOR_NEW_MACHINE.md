# HANDOFF — read this first

**For: the Claude instance starting fresh on the new machine.**
**From: the session that ran 2026-09-23 → 2026-09-30.**
**Written: 2026-09-30.**

You are picking up an eight-month research project at a delicate moment. Read this whole file
before touching anything. Several numbers in this project have been retracted; several documents
still contain wrong claims; and one thing in the record is a research-integrity issue that you must
handle correctly rather than repeat.

---

## 1. What this project is

A **Review of Research in Education (RRE) 2026** methodological paper, plus an **AERA 2027
Division D** conference submission. The RA is **Duy Nguyen**; the supervisor is **Prof. Wei Zheng**.

The claim under test: an agentic, human-in-the-loop, multi-agent pipeline can perform a **realist
systematic review** — not summarise papers, but reproduce the analytic operations of one: search →
screen → extract context–mechanism–outcome configurations (CMOCs) → build a cross-study evidence
graph → derive mechanisms → compose a programme theory.

The benchmark is **Richmond, A., Cooper, N., Gay, S., Atiomo, W., & Patel, R. (2020). The student
is key: A realist review of educational interventions to develop analytical and non-analytical
clinical reasoning ability. *Medical Education, 54*(8), 709–719**, and its 28 included studies.

**Standing rules from the RA, which are not negotiable:**

- All project artefacts — code, files, docs, identifiers, commit messages — **in English**.
  Vietnamese is only for chat between the RA and Claude.
- **Nothing is fabricated.** Every architectural, technological and ontological decision must be
  grounded in the source documents in the repo or in real external literature. Research first,
  never invent. This has been violated before and it cost the project badly (§6).
- **Append a WALKTHROUGH.md entry every session.** This is a standing requirement.
- The RA wants short, plain, non-AI-sounding prose. They have said repeatedly that long ornate
  writing is unreadable to them, and that section headings must be blunt ("output" means write
  "OUTPUT", not "Evidentiary Artefacts"). Respect this.

---

## 2. Where things stand right now

### 2.1 The pipeline works end to end

One complete, single-vintage run exists and every reported figure comes from it:

| Run | ID |
|---|---|
| Screening | `screen-70a5d070` |
| Extraction | `extract-fb045429` |
| Synthesis | `synth-2dfada15` |
| Verification | `verify-edcbf790` |
| Report render | `report-b988e51b` |
| Benchmark file | `richmond_gold_v3` |

**Never mix runs.** An earlier version of this project blended six screening runs into one PRISMA
figure and produced "159 auto-included" on a 28-paper corpus. Quote one named run or nothing.

### 2.2 What the run produced

| Artefact | Count |
|---|---|
| Papers with extractable full text | 26 of 28 (`S002`, `S012` are abstract-only, no full text obtainable) |
| CMOC configurations | 94 |
| Concept instances | 547 |
| Typed causal relations | 459 (456 typed + 3 `UNTYPED_CANDIDATE`) |
| Mechanism communities (Leiden) | 8 |
| Contradictions | 20 |
| Demi-regularities | 32 |
| Programme theory | version 12, **nine** context-specific chains |

The programme theory is the deliverable that compares directly with Richmond pp. 714–716. It is at
`outputs/runs/report-b988e51b/programme_theory.md`. Its opening paragraph is the system's own
conclusion and it reaches Richmond's central finding independently: outcomes turn on the fit
between learner knowledge, task demand and instructional support, not on analytic reasoning being
superior.

### 2.3 Verified metrics — quote these exactly, with their tiers

| Measure | Value | 95% CI | Judged by |
|---|---|---|---|
| Screening, automatic | 26/28 = 92.9% | [76.5, 99.1] | counted |
| Screening, after human checkpoint | 28/28 = 100% | [87.7, 100.0] | counted |
| Concepts, same realist role | 34/46 = 73.9% | [58.9, 85.7] | model |
| Concepts, role-tolerant | 41/46 = 89.1% | [76.4, 96.4] | model |
| Relations, strict predicate | 6/40 = 15.0% | [5.7, 29.8] | model |
| Relations, anchored | 29/40 = 72.5% | [56.1, 85.4] | model |
| Relations, type level | 39/40 = 97.5% | [86.8, 99.9] | model — **weak discriminator, never quote alone** |
| Quotes, exact character match | 53/547 = 9.7% | [7.3, 12.5] | counted |
| Quotes, + normalised | 509/547 = 93.1% | [90.6, 95.0] | counted |
| Quotes, all tiers resolved | 531/547 = 97.1% | [95.3, 98.3] | counted |
| Mechanisms aligned | 19/28 = 67.9% | [47.6, 84.1] | model |
| Programme theory, independent judge | 0.82 | — | model |
| Programme theory, same-family judge | 0.53 | — | model |

Note: the exported CSV's `quote_resolved` column counts 532 True / 15 False, while the verifier's
stricter tier test counts 531. Both figures are correct for what they measure; say which you mean.

### 2.4 The three results that actually matter

These are the project's contribution. They are more defensible than any coverage score.

**(a) The evaluation instrument moves; the system does not.** The verification was run ten times
over a single **frozen, unchanged** graph. Everything counted came back byte-identical on all ten
runs. Everything a model judged moved:

| Metric | Range over 10 runs | SD |
|---|---|---|
| Concept coverage, same role (/46) | 31–37 | 1.96 |
| Concept coverage, role-tolerant (/46) | 37–45 | 2.26 |
| Relations, anchored (/40) | 24–31 | 2.31 |
| Relations, strict (/40) | 4–7 | 0.97 |
| Mechanisms (/28) | 16–21 | 1.32 |
| Programme theory, independent judge | 0.79–0.87 | 0.024 |
| Programme theory, same-family judge | 0.48–0.53 | 0.015 |
| Screening sensitivity | identical ×10 | 0 |
| Span grounding, all tiers | identical ×10 | 0 |

**Consequence you must enforce: minimum detectable difference ≈ 7.8 items ≈ 17 percentage points
on a single comparison per arm.** Nothing ships on one before/after run. Five replicates per arm
gets you to ~8 pp; ten gets you to ~5 pp. Full analysis in `docs/MEASUREMENT_NOISE.md`.

**(b) A trivial baseline matches the pipeline on concept coverage.** One plain LLM call over the
same 28 papers — no ontology, no per-study extraction, no span grounding, no graph, no checkpoints
— recovers **32 of 46**, inside the pipeline's own 31–37 range. The framework therefore **cannot**
be claimed superior on concept coverage. The defensible claim is what the baseline produces none
of: character-anchored quotations, per-study attribution, typed relations, algorithmically derived
mechanisms, four logged human checkpoints, a full audit trail. Code: `verification/baseline.py`.

**(c) The pipeline's misses are systematic, and they fall on the benchmark's core claim.** Five
concepts were recovered at no tier:

| Code | Role | Concept |
|---|---|---|
| E05 | Context | negative coping / lacking self-confidence or self-efficacy |
| E06 | Context | students with different levels of knowledge within a group |
| E31 | Mechanism response | pressure that decision making could have real impact |
| E32 | Mechanism response | fear |
| E34 | Mechanism response | pressure to perform |

**Four of five are negative affect under pressure.** The system recovers what teaching supplies,
what learners do, and *positive* affect (E04, confidence/engagement) — but not fear, pressure or
low self-efficacy. Richmond's central claim is that the same resource helps a confident learner and
harms an anxious one, so this gap sits on the argument's core, not its edge. **Whether the cause is
the ontology, the extraction prompt, or the corpus is unanswered and is the single most
publishable open question in the project.**

---

## 3. THE INTEGRITY ITEM — read carefully

The project reports a "human ceiling" from two coders, A and B, who each coded all 28 papers blind:
A found 30/46 (192 elements), B found 28/46 (139 elements), agreement 0.785 positive specific
agreement, 130 elements shared.

**Coder A is the RA, Duy. Coder B was not a person — it was ChatGPT, prompted to act as a second
RA.** The RA disclosed this on 2026-09-25, while preparing to present the figure to the supervisor.

This matters and you must not let it slip:

- It is **not** inter-rater reliability. Calling it that in a paper would be misrepresentation.
- The correct description is: **one manual coding pass by the first author, plus an independent
  LLM pass under the same coding frame.** 0.785 is human-against-model agreement.
- It does not establish a human ceiling. It establishes the project's **first human data point**:
  a careful reader working through all 28 papers recovers **30 of 46**.
- A genuine reliability figure still requires a **second person**. This is the top outstanding item.

There is a real and defensible finding here, and it should be used: four independent readings of
the same corpus — manual (30), LLM under the frame (28), plain baseline (32), full pipeline (31–37)
— all land between 28 and 37. The parsimonious reading is that **about 30 of Richmond's 46 concepts
are actually recoverable from the 28 included studies**, and the remainder were drawn from the
wider literature Richmond discuss. That reframes 34/46 from "mediocre" to "near the corpus ceiling."

**Already corrected** in `outputs/SEND_TO_PROFESSOR/0_REPORT.html` (and its PDF) and in the filled
AERA draft. **Not yet corrected** — see §7.

---

## 4. What the architecture actually is

Established by reading the code on 2026-09-30, not from documentation. Documentation in this repo
has been wrong before; trust the code.

**Eight stages, one Postgres database as the single source of truth, four mandatory human
checkpoints.**

1. **Ingest** — PDF → text, character offsets preserved (`core/ingestion.py`)
2. **Screen** — include / exclude / uncertain; uncertain routes to a human *(checkpoint 1 & 2)*
3. **Extract CMOCs** — per study, into the realist ontology (`plugins/realist/cmoc_extraction.py`)
4. **Critique and revise** — separate critic agent, one revise round below threshold 0.34
5. **Ground quotes** — exact → normalised (de-hyphenation with index map) → difflib fuzzy ≥ 70%
   (`plugins/realist/span_repair.py`); which tier each resolved at is recorded, never averaged
6. **Build graph** — canonicalise concepts across studies, type relations *(checkpoint 3)*
7. **Find mechanisms** — Leiden community detection, `graspologic`, resolution 1.0, seed 20260714
   (`graph/communities.py`)
8. **Synthesise and verify** — compose programme theory, score against benchmark *(checkpoint 4)*

**Ontology.** Five element types (Context, Intervention, Mechanism_Resource, Mechanism_Response,
Outcome) following Dalkin et al. (2015)'s split of mechanism into resource offered and learner
response. Five relation types: `PROVIDES`, `TRIGGERS`, `ENABLES`, `LEADS_TO`, `CONSTRAINS`. A real
causal link fitting none is stored as `UNTYPED_CANDIDATE`, flagged `constraint_valid = False`,
excluded from every metric, queued for a human. **3 of 459** — the small number is itself evidence
the ontology covers this literature.

### 4.1 Four architectural facts that surprise people

**There is no retrieval anywhere in this pipeline.** Not in extraction, not in synthesis.

- Extraction passes the **whole paper** as `FULL TEXT` (`cmoc_extraction.py:252`). Corpus: mean
  22,977 chars/paper, max 44,456, total 643,363 ≈ 161K tokens. No chunking. At this size, passing
  everything is strictly more informative than retrieving parts.
- Synthesis passes the **entire evidence base** with no selection. `programme_theory.py:49`
  `_evidence_pack()` issues four unfiltered SELECTs and serialises the lot: measured at
  **50,026 characters ≈ 12,506 tokens**. Retrieval could only *remove* evidence here.
- Exhaustive grep confirms: no embeddings, no vector store, no similarity search, no subgraph
  selection. The only hit for "embedding" is a comment in `metrics.py` saying the matcher is
  deliberately embedding-free.

**The graph is used for clustering and for vocabulary conditioning, not retrieval.** But there *is*
one genuine graph→extraction feedback path: `guidance.py:81` `_known_concepts_block()` injects the
top-N community labels and most frequent entity labels into each subsequent extraction prompt, so
study 20 names concepts consistently with study 3. Frequency-ranked, not semantic.

**Scaling wall.** At ~446 tokens/CMOC and ~3.35 CMOCs/study, the evidence pack reaches ~45K tokens
at 100 studies, ~134K at 300, and **exceeds context around 500**. Retrieval becomes necessary
somewhere between 200 and 400 studies — not now.

**One real engineering defect.** `normalization.py:53` `_batched_cluster()` clusters concepts in
batches and merges across batches **by exact normalised label**. "learner prior knowledge" and
"prior knowledge of the learner" will not merge. Fine at 547 instances; will fragment badly at
scale. Fixing it needs embedding-assisted blocking — and any such fix **must** be guarded so that
E02 (low knowledge) and E03 (high knowledge) never merge. They are near-antonyms with high lexical
overlap, and collapsing them would destroy Richmond's central finding while *improving* every
aggregate metric.

### 4.2 The gap between the abstract and what was built

Prof. Zheng's RRE abstract promised LangChain orchestration, a fine-tuned domain LLM, GraphRAG
subgraph retrieval, link prediction over graph embeddings, and RLHF. **None of the five are in the
system.** What *is* built: the Leiden global-search half of GraphRAG, and a hand-written stateful
coordinator.

A grounded assessment was produced on 2026-09-30 concluding that **integrating LangChain or
GraphRAG retrieval now would not improve any measured limitation, and would put an abstraction
between the code and the two properties the whole validation rests on — per-field schema
enforcement and character-offset provenance.** The justification to use in the paper is
quantitative, not hand-waving: *the complete evidence pack is 12,506 tokens and fits entirely in
context, so retrieval could only subtract; a selection stage is specified for corpora large enough
to need it.* Domain fine-tuning and RLHF were also correctly deferred, because training on the
benchmark's domain and then evaluating against that benchmark is circular.

Recommended instead, in order: (WP-A) a thin model-provider adapter in `core/llm.py`, ~80 lines,
**because without model swappability there is no ablation study and therefore no journal paper**;
(WP-B) embedding-assisted blocking in canonicalisation with the E02/E03 guard; (WP-C) specify
graph-based evidence selection now, build it when the pack exceeds ~60K tokens.

---

## 5. Where the outputs live

```
outputs/
  runs/report-b988e51b/     THE system output — send this when asked to "show the output"
    programme_theory.md     the system's own conclusion, 9 chains  (16 KB)
    cmoc_evidence_table.md  94 configurations with supporting quotes (159 KB)
    audit_trail.md          every prompt and response (195 KB)
    prisma_flow.md
    theory_diagram.html
  runs/verify-*/            30 verification runs; verify-edcbf790 is the current one
  exports/                  entities.csv 547 · relationships.csv 459 · cmocs.csv 94 · big_concepts.csv
  lkg/                      parquet snapshot + manifest.json — the last-known-good graph
  gold/                     human_ceiling.json · inter_coder_agreement.json · the two coder workbooks
  RESULTS.html              one page: Richmond beside us, verification table, all data, searchable
  SEND_TO_PROFESSOR/        the bundle sent 2026-09-25
gold/
  richmond_gold_v3.json     THE benchmark — 46 concepts, 40 relations, 5 PT chains
  RICHMOND_CONCLUSIONS.md   Richmond transcribed with page references
```

`RES_GOLD=v1` reproduces every earlier published number. v1 and v2 are kept for exactly that.

**The RA's most important instruction about output:** when they ask to see the output, they mean
**the files the pipeline writes** — `programme_theory.md` and the CSVs — **not** a report you
compose after reading the database, and **not** a table of counts. They said this repeatedly and
with increasing frustration before it was understood. Show files.

---

## 6. Retracted claims — do not resurrect these

Five claims were made in this project and later withdrawn. They appear in older documents and in
earlier drafts. If you see them, they are wrong.

| Claim | Why it was wrong |
|---|---|
| "Feedback loop cut checker disagreement 77% → 50%" | `agent_key` mismatch (`cmoc_extractor` written, `cmoc_extraction` read) meant the loop was never connected — **and** n=3 studies cannot beat noise of ±18 pp. `CONSUMING_AGENT_KEYS` now raises on an unread key |
| "91.5% concept recovery (43/47)" | Came from an **unvoted** recovery pass; fell **outside its own sampling range** (76.6–85.1%). Denominator was also wrong: E01 is Richmond's population description, not a scorable concept. Correct: 41/46 = 89.1% role-tolerant, 34/46 = 73.9% same-role |
| "96.9% citation faithfulness, resolved to an exact source span" | Conflated three matching tiers under the word "exact". Exact is **53/547 = 9.7%** |
| "532/547 exact span" | Same error, restated |
| IMPROVEMENT_PLAN v1 | Contained four false load-bearing claims. Withdrawn; v2 replaced it. The RA asked for it to be critiqued before implementation, which is what caught it — that instinct saved about five days and prevented an embedding change that would have collapsed E02/E03 |

**Lesson the project paid for twice: fixing a table is not fixing a pipeline. The correction has to
be observed arriving at the prompt.**

---

## 7. Known problems you are inheriting

### 7.1 The database is gone

PostgreSQL has been uninstalled from the old machine. `C:\Program Files\PostgreSQL\18` holds only
an empty installation log; there is no `data` directory and no `pg_dump.exe`; nothing listens on
5432. **No dump could be taken.**

The results survive: `outputs/lkg/*.parquet` is the designed last-known-good snapshot, and
`outputs/exports/*.csv` holds the same rows readably. **Rebuild by importing these. Do not re-run
the pipeline** — a re-run costs money and produces a *different* graph, which would invalidate every
figure already reported in the AERA submission. See `RESTORE.md` in this backup folder.

If no parquet import command exists yet, writing one is roughly half a day and costs no API calls.
Target tables: `entity_instances`, `typed_relations`, `cmocs`, `conceptual_entities`.

### 7.2 Seventeen commits were never pushed

All of the judge-variance study, the human coding, the baseline, gold v3, and `RESULTS.html` exist
only on the old disk and in `repo-full-history.bundle` in this backup. Remote is
`https://github.com/duynguyenxc/Realist-Evidence-Synthesis-V2.git`, whose `main` is 17 commits
behind. **Push before anything else.**

### 7.3 Documents that still contain wrong claims

These say "two coders" or "human ceiling" or "inter-coder agreement" and must be corrected to the
one-human-plus-one-LLM description of §3:

- `docs/MEASUREMENT_NOISE.md`
- `docs/HUMAN_CODING_GUIDE.md`
- `docs/VERIFICATION_PROTOCOL.md`
- `src/res_pipeline/verification/agreement.py` — module docstring, and the CLI table title
  "Inter-coder agreement — the human ceiling" in `cli.py`
- `outputs/gold/human_ceiling.json` — the filename itself is now misleading

Also: `CLAUDE.md` still says "**no human has coded anything**". That is now out of date — the RA
has coded all 28 papers manually. Update it.

### 7.4 Smaller items

- `cost_calibration_factor = 2.0` in the budget module has never been calibrated against the actual
  OpenAI dashboard. `max_usd_per_full_run = 45.0`.
- `WALKTHROUGH.md` stops at M35 (2026-09-24). M36 is being added alongside this handoff.
- `docs/WindowsMigrationAssistantSetup.exe` is a stray 158 MB installer, 77% of the repo's size.
  It is excluded from this backup. Delete it from the project.
- 54% checker disagreement on extraction remains undiagnosed.

---

## 8. What was delivered to the supervisor

### 2026-09-25 — progress report and output bundle

Six files, sent as email attachments (PDFs, not HTML — the supervisor asked for PDFs; HTML is only
for screen-sharing in meetings):

| File | Content |
|---|---|
| `0_REPORT.pdf` | "Reproducing Richmond (2020)", 7 pages — the whole comparison in one document |
| `1_programme_theory.pdf` | The system's own conclusion, nine chains |
| `3_entities.csv` | 547 concepts with quotes and character offsets |
| `4_relationships.csv` | 459 typed relations |
| `5_cmoc_evidence_table.pdf` | 94 configurations with supporting quotes |
| `6_richmond_conclusions.pdf` | Richmond transcribed with page references |

`0_REPORT.html` is also published as a private Artifact at
`https://claude.ai/artifact/8sV6iBY7KfrLVHPch8KYHu` (version 4).

Folder on the old machine: `C:\Users\Admin\OneDrive - HUCE\Desktop\GUI-THAY-ZHENG\`. Note this is a
**university OneDrive**; nothing containing credentials should ever go there.

### 2026-09-30 — the AERA 2027 paper

The supervisor's draft arrived with 16 yellow placeholders. It was completed in place, preserving
structure, styles, fonts and all four tables:
`AERA_2027_Division_D_AI_Agent_Evidence_Synthesis_Preliminary_Paper_FINAL.docx`.

What was done beyond filling placeholders — because leaving the surrounding prose would have
contradicted the inserted figures:

- "approximately 57 candidate CMOCs" → 94
- "Screening missed a substantial portion of the 28 papers" → 26 automatic, 28 after one checkpoint
- "contradiction and demi-regularity functions were incomplete" → operational, 20 and 32
- "Graph-based retrieval is added" → rewritten accurately, with the 12,500-token justification
- Four new Findings paragraphs added: instrument variance, the baseline, the human reference point,
  and the affect-blindness pattern
- Table 2 grown from 12 to 16 rows; "Value to Insert" renamed "Verified Value"
- References 9 → 14 (added Clopper & Pearson 1934, Dalkin et al. 2015, Hripcsak & Rothschild 2005,
  Traag et al. 2019, Zheng et al. 2023 — all real, all with DOIs where they exist)
- Table fonts repaired to the original 9 pt headers / 8.5 pt body after an earlier pass left them
  at 12 pt

Narrative is **2,138 words**; the supervisor's original was 1,959, which implies a 2,000-word
limit. If the portal enforces 2,000 strictly, delete the closing paragraph of Significance (55
words) and, if still needed, the unstructured-baseline paragraph (95 words, since Table 2 carries
the figure) — in that order.

A second, independently structured version also exists: `AERA_2027_Paper_REVISED.docx`, 2,716 words,
six tables, titled "Measuring the Instrument". It is the same evidence argued from scratch rather
than fitted to the supervisor's outline. Keep it; do not send both.

---

## 9. Publication readiness

### Conference (AERA 2027) — roughly one week of work

| # | Task | Blocking? |
|---|---|---|
| 1 | Re-number the draft against `verify-edcbf790` | **Done** 2026-09-30 |
| 2 | **Measure precision.** Stratified sample of ~100 of the 547 concepts, human adjudication of supported/unsupported against the cited span, exact binomial CI | **Yes** — every figure so far is recall; this is the first question a reviewer asks |
| 3 | Correct the coder-B description everywhere (§7.3) | **Yes** — integrity |
| 4 | Read and classify the 10 concepts found by the pipeline and by neither coding pass | **Yes** — connects directly to #2 |
| 5 | Instantiate the Table 3 error taxonomy with real counts | Advised |
| 6 | Record human effort per checkpoint | Advised |

### Journal (RRE 2026) — two to three months

| # | Missing | Why it blocks |
|---|---|---|
| 1 | **A second published realist review** | Without it, "the system was fitted to Richmond" is unanswerable. Ontology, prompts and the gold file were all revised while looking at Richmond results — adaptive overfitting risk is material |
| 2 | **Ablations**, ≥5 replicates per arm | Turns a system report into a methods paper. The replicate count is forced by the 17 pp resolution limit |
| 3 | **A second human coder** | For genuine inter-rater reliability |
| 4 | **Human expert rating of programme-theory correspondence** | Replaces the one figure the project openly does not defend |
| 5 | Full precision / false-discovery analysis | Extends conference item 2 |
| 6 | Efficiency accounting — wall clock, human minutes, API cost | The abstract's central promise is scalability; no figure exists |
| 7 | Pre-registration of metrics before the second benchmark | Forecloses the overfitting objection |
| 8 | Explicit reconciliation with the RRE abstract (§4.2) | Reviewers will hold the abstract |
| 9 | Diagnose the affect-blindness finding | Potentially the paper's best section |

---

## 10. How to behave on this project

Learned the hard way over eight months. These are not style preferences.

1. **Report tiers, never a single blended number.** Exact before normalised before fuzzy. Anchored
   before type-level. This is how three of the five retractions happened.
2. **Say which run.** Every figure carries a run id or it is not a figure.
3. **Label counted vs model-judged.** They behave completely differently and the whole
   contribution rests on the distinction.
4. **Never claim an improvement under 17 pp from one comparison.** Five replicates minimum.
5. **When the RA asks for output, open the files.** Not a summary, not counts.
6. **Say "I don't know" when you don't.** Precision, the 10 extra concepts, and 9-vs-5 contexts are
   all currently unanswered. The RA and the supervisor both notice invention immediately, and the
   project's credibility has already been spent twice on it.
7. **Critique plans before implementing them.** The RA asks for this. It has already caught four
   false claims and prevented a change that would have destroyed the benchmark's central finding.
8. **Write short.** The RA has said more than once that long ornate prose is unreadable to them.

---

## 11. First five things to do on the new machine

1. `git push origin main` — 17 commits (see `RESTORE.md` §1)
2. Install PostgreSQL 18, create `realist_synthesis`, password from `PROJECT/.env`
3. `pip install -e .`, then `res init-db`
4. **Import** `outputs/lkg/*.parquet` — do not re-run the pipeline
5. Verify: `res export-results` should regenerate `RESULTS.html` showing 547 / 459 / 94 / 8. If
   those four numbers match, the restore is correct.

Then start with conference item 2 — the precision sample. It is the largest single gap, it needs no
API spend, and it answers the reviewer's first question.

---

*Credentials are in `PROJECT/.env` (9 variables). Postgres is `localhost:5432`, user `postgres`,
database `realist_synthesis`. Rotate the OpenAI key if the old machine is being passed on.*
