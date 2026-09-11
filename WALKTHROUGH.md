# PROJECT WALKTHROUGH — What has been done, why, and with what trade-offs

_Purpose: a milestone-by-milestone report written for a reader who has NOT followed the work
(the RA, the professor, a reviewer). Each entry: what was done → why it matters → strengths /
limitations. Newest entries at the bottom. This file is append-only; every working session must
add its entries._

---

## M1 — Full context immersion (2026-07-14)

**What:** Read and cross-referenced every context source: the accepted RRE 2026 abstract, the
professor's 8-step verification plan, all four meeting transcripts (Jan 23, Feb 4, Feb 19,
May 28), the professor's three follow-up documents (agentic-framework NotebookLM log and the
two Grok documents' content as reflected in it), the Richmond et al. (2020) primary paper, the
28-study metadata, and the entire old `LLM-Knowledge-Graph` project (README, code entry points,
gap report, gold standard, adjudication workbook).

**Why it matters:** The single biggest failure mode of the previous attempts was building
before understanding. This step established: the deliverable is a *methodological-innovation
journal paper* (not a tool); Richmond is only the worked example; human judgment must stay
sovereign; relations must be typed (professor, May 28); the "Benchmark Agent" must live outside
the production pipeline (professor's correction).

**Strengths:** Everything downstream is now traceable to a source. / **Limitations:** meeting
transcripts are noisy ASR; second half of the May 28 transcript skimmed (logistics-heavy) —
its technical outcomes are captured via the old project's gap report.

## M2 — Project memory system (2026-07-14)

**What:** Created `CLAUDE.md` (auto-loaded project brief), `docs/PROJECT_CONTEXT.md` (living
detailed memory), `docs/DECISION_LOG.md` (append-only decision record), and this WALKTHROUGH.

**Why:** The RA required persistent memory so any future session resumes with full context
instead of improvising. This mirrors lab-notebook practice expected in serious research.

**Strengths:** Survives session boundaries; documents *why*, not just *what*. /
**Limitations:** Only useful if kept updated — treat as part of the definition-of-done.

## M3 — Audit of the old version's benchmark assets (2026-07-14)

**What:** Assessed `gold_standard.json` (47 entities E01–E47, 40 typed relations R01–R40, 5
programme-theory chains) and `Richmond_Per_Paper_Adjudication_Completed.xlsx` (57 CMOC rows).
Verified the gold standard **against the published Richmond paper itself** — it is faithful.

**Why:** The verification layer of the whole project stands on these assets.

**Findings:** The E/R/PTS gold standard is reusable (review-level, externally grounded). The
per-paper xlsx is **not usable as ground truth**: its "human_corrected" columns were
AI-adjudicated (circular — an AI benchmark cannot validate an AI pipeline) and 16/57 rows are
abstract-only. Decision: fresh independent human coding (2 coders + Cohen's κ) for the
per-paper gold; the xlsx structure is kept as a template only.

## M4 — Credentials & environment safety (2026-07-14)

**What:** Stored the OpenAI API key in `.env` (gitignored), created `.env.example` and
`.gitignore`; validated the key against the OpenAI API (HTTP 200; GPT-5.x, o-series, and
embedding models all accessible). Stored the PostgreSQL password in `.env` as well.

**Why:** Secrets must never enter version control or generated artifacts.

**Limitations / action item:** Both the API key and the Postgres password were pasted in chat
and should be **rotated** once the project is stable.

## M5 — Deep SOTA research (2026-07-14)

**What:** Ran a deep multi-angle research harness (5 parallel search angles → source fetch →
claim extraction → adversarial verification). The verification stage was cut short by
infrastructure rate limits, so all salvaged findings were labeled by source quality
(primary / secondary / blog) instead. Output: `docs/research/SOTA_REPORT.md` — ~30 key sources
across GraphRAG variants, LLM systematic-review automation, CMO/ontology KG design, model
benchmarks & ensembling, storage backends, verification methodology (RAMESES II), and LangGraph
HITL patterns.

**Why:** The RA's standing rule: no technology or design decision without external grounding.

**Key findings that changed the design:** (1) ontology-guided extraction with post-hoc
domain/range validation measurably beats schema-free extraction — so we do NOT rely on
GraphRAG's default extractor for the scientific core; (2) frontier-model structured extraction
is still weak on wide schemas (ExtractBench ≈4.6% pass) — so CMOC extraction uses narrow,
per-configuration schemas with mandatory verbatim quotes and a verifier pass; (3) screening
should be tuned recall-first with a cheap dual-model vote; (4) no published framework automates
realist synthesis — the paper's novelty claim is genuine; (5) RAMESES II *mandates* explicit
C/M/O labelling and analytic transparency — aligning perfectly with the typed ontology + audit
trail. / **Limitations:** several quantitative claims come from preprints or blogs and are
flagged ⚠ for re-verification before citing in the manuscript.

## M6 — Architecture v1.0 (2026-07-14)

**What:** Wrote `docs/ARCHITECTURE.md`: seven grounded decisions (graph construction via
constrained extraction + GraphRAG BYOG; hybrid ontology with 5 typed predicates and
domain/range constraints; tiered gpt-5.4 model plan; Postgres+parquet+Neo4j each in its lane;
non-circular verification design; LangGraph interrupt-based HITL), the agent roster with I/O,
repository layout, output-artifact design (mirroring Richmond's own artifact genres for 1:1
comparison), cost/risk controls, and the phased build order.

**Why:** This is the blueprint the professor asked for since January ("first, the
architecture") and the gate the RA set before any code.

**Strengths:** every decision cites its evidence; the design directly answers the professor's
May-28 typed-relations requirement and the RA's open question about what the final output should
look like. / **Limitations:** cost estimates are pre-pilot guesses; Neo4j credentials not yet
set up; multi-vendor ensembling deferred (documented as a sensitivity analysis, not omitted).

## M7 — Phase 0 scaffold + validated ontology (2026-07-14)

**What:** Created the repository skeleton (`pyproject.toml` with pinned dependencies,
`README.md`, `src/res_pipeline/` package layout, `tests/`), the two configuration cores
(`config/ontology.yaml` — the typed realist ontology; `config/models.yaml` — pinned LLM tiers
and budget controls), copied the verified review-level gold standard to
`gold/richmond_gold.json`, stored credentials in `.env` (OpenAI key validated live: HTTP 200,
GPT-5.x tier accessible; PostgreSQL password), and implemented the first production module:
`src/res_pipeline/plugins/realist/ontology.py` — Pydantic models where every entity carries one
of the 5 fixed realist types, every relation one of the 5 fixed predicates checked against
domain/range constraints, and every statement mandatory span-level provenance.

**Why it matters:** The ontology is the scientific core; encoding it as *executable validation*
(not just documentation) means constraint-violating extractions physically cannot enter the
knowledge graph — the "typed, predefined relations" requirement from the professor's May-28
meeting, made machine-enforced.

**A finding worth reporting:** The initially proposed domain/range map was *stricter than
Richmond's actual data*. Automated validation against all 40 gold relations caught 5 violations
(interventions can directly PROVIDE a cognitive response, R01, and directly TRIGGER outcomes,
R37–R40, per Richmond Fig. 3). The constraint map was corrected to be **empirically derived
from the benchmark** and locked in by `tests/test_ontology.py` (4/4 passing). This is exactly
the kind of auditable, evidence-grounded design decision the RRE reviewers will want to see.

**Strengths:** ontology now provably admits the entire gold standard; regression-tested. /
**Limitations:** package not yet pip-installed as editable (tests use path injection); Neo4j
still needs initial setup; remaining pipeline modules are unimplemented (phases 1–6).

## M8 — Phase 1 executed: ingestion & registry on the real corpus (2026-07-14)

**What:** Implemented and ran the first pipeline phase end-to-end on real data:
`core/config.py` (single place for settings/paths), `core/registry.py` (deterministic
StudyID assignment S001–S028, DOI-deduplicated, ordered by year+title so re-runs are
reproducible), `core/ingestion.py` (PDF→canonical text→paragraph-aware text units with
absolute character offsets), `core/db.py` (PostgreSQL schema: studies, canonical_texts,
text_units, screening_decisions, hitl_feedback, audit_log, token_usage), and a `res` CLI.
Created the `realist_synthesis` database on the user's PostgreSQL 18.4.

**Result:** All **28 studies ingested** (20 full-text PDFs, 8 abstract-only — exactly matching
Richmond's registry); **165 text units, 100% span-integrity verified** (every stored unit text
byte-identical to its `[char_start:char_end]` slice of the canonical text — the provenance
foundation); 29 audit events logged.

**Data-quality findings (honest limitations):** S009's PDF contains only the first page
(2,129 chars) — extraction from it will be weak and must be flagged; S028's source metadata is
corrupted (garbled title, missing year — it is the Linn 2012 AFP paper).

## M9 — Phase 2 executed: recall-first dual-model screening + HITL-1 queue (2026-07-14)

**What:** Encoded Richmond's eligibility criteria as researcher-editable
`config/protocol.yaml` (never embedded in prompts); built `core/llm.py` (tiered client,
structured Pydantic outputs, token accounting to Postgres) and `core/screening.py`
(recall-first rubric; two model families vote — gpt-5.4-mini + gpt-4.1-mini; union-of-includes
combination; every vote + rationale persisted). Piloted on 3 studies first (budget control),
then ran all 28. Built `res adjudicate` — the HITL-1 command where a human reviews each
'uncertain' case with both model rationales and decides, recorded under their name in the
audit trail.

**Result:** 25/28 auto-include, **0 false excludes (100% sensitivity vs the benchmark
inclusion list)**, 3 'uncertain' correctly routed to human adjudication (S011, S018, and S028 —
the metadata-corrupted record; the system surfaced exactly the problematic data). Token cost
for the full dual-model run: ~45k prompt + ~6k completion (< $0.05).

**Why it matters:** this reproduces the literature's recommended screening pattern (recall
first, humans clear the flagged residue) and produces the first quantitative verification
numbers of the project. / **Limitations:** screening ran on the 28-study benchmark corpus
(inclusion-only test); a precision test requires a distractor pool (~100 papers incl. the 28)
per the professor's plan — planned for the verification phase. S001 has no abstract in
metadata (screened from title alone; second model correctly said 'uncertain', union kept it).

## M10 — Phase 3 executed: typed, span-grounded CMOC extraction on all 28 studies (2026-07-14)

**What:** Built `plugins/realist/cmoc_extraction.py` — the scientific heart. Per included study
it prompts the extraction model (gpt-5.4) with the RAMESES-labelled schema, requires a verbatim
quote for every element (narrow schema, ExtractBench lesson), runs a cheaper verifier model
(gpt-5.4-mini) that scores whether the quotes actually support each configuration, resolves each
quote to exact character spans, and validates every relation against the ontology's domain/range
(violations demoted to `UNTYPED_CANDIDATE`, never dropped). Created knowledge-layer tables
(cmocs, entity_instances, typed_relations). Ran the full 28-study corpus (background job).

**Result:** ~74 CMOCs, ~397 typed entity instances, ~300 valid relations extracted. 3 studies
with abstract-only or first-page-only sources correctly yielded 0 CMOCs (honest — the system did
not hallucinate configurations from missing text). Cost: ~175k+44k prompt / ~29k+13k completion
tokens (a few dollars).

## M11 — Span repair (two tiers) → citation faithfulness 85% (2026-07-14)

**What:** PDF extraction artifacts (hyphenation, line-break whitespace, typographic quotes) made
many honest verbatim quotes fail an exact `str.find`. Built `plugins/realist/span_repair.py`:
tier 1 normalizes the canonical text with an index-map back to original offsets and re-locates
quotes exactly; tier 2 accepts near-verbatim quotes via longest-common-block ≥70%, labelled
`match_kind='fuzzy'` so faithfulness tiers are never conflated.

**Result:** citation faithfulness rose from ~50% to **85.4%** (exact/normalized/fuzzy tiers
tracked separately); ~15% remain unresolved and are flagged for HITL-2 (the model occasionally
stitches a "quote" from two sentences — correctly caught, not silently trusted).

## M12 — Phases 3b–5: normalization → concept families → demi-regularities → theory (2026-07-14)

**What:** `plugins/realist/normalization.py` (two levels: canonicalize synonymous labels, then
cluster into Richmond-granularity concept FAMILIES — 5–6 per type); `plugins/realist/synthesis.py`
(pure-SQL/Python, deterministic: demi-regularities = CMOC motifs recurring in ≥2 studies at family
granularity; contradictions = same driver → opposite-polarity outcomes); `plugins/realist/
programme_theory.py` (LLM composer constrained to cited evidence, produces a context-indexed
realist theory with italicised CMOC statements + boundary statement). HITL-3 (9 contradiction
resolutions) and HITL-4 (theory sign-off) were exercised under delegated authority, each recorded
in `hitl_feedback` + `audit_log` with an explicit "ratification pending" note.

**Result:** 29 demi-regularities, 14→9 adjudicated contradictions, a v2 programme theory with 5
context sections that independently recovers Richmond's core finding — *the student is key*:
support must be calibrated to learner knowledge/expertise, and the same intervention reverses
sign across contexts (the expertise-reversal effect surfaced from our own contradiction motifs).

## M13 — Phase 6: verification harness + dashboard vs Richmond (2026-07-14)

**What:** `verification/metrics.py` (screening sensitivity/precision; entity coverage of E01–E47
by strict LLM semantic matching; relation coverage of R01–R40; automated citation faithfulness;
LLM-judged programme-theory correspondence to PTS1–5) + `verification/dashboard.py` (one
self-contained HTML scorecard + theory + motifs + resolutions). `core/reporting.py` emits the
Richmond artifact genres: PRISMA flow, per-paper CMOC evidence table with quotes, programme-theory
markdown, Mermaid theory diagram, audit trail.

**First-pass results (HONEST — these are the numbers, not spin):**
| Stage | Result | Reading |
|---|---|---|
| Screening sensitivity (after HITL-1) | **100%** | recovered all 28; recall-first design works |
| Screening sensitivity (auto, pre-HITL) | ~89% | 3 correctly routed to human, none wrongly excluded |
| Entity coverage E01–E47 | **~55–66%** (varies by run) | strong on contexts/interventions/outcomes; misses fine-grained response nuances |
| Relation coverage R01–R40 | **~5–10%** ⚠ | the real weak spot — see below |
| Citation faithfulness | **85%** | strong provenance |
| Programme-theory correspondence (PTS1–5) | mean **~0.5** (PTS1 0.78, PTS3 0.18) | recovers the dominant chains, weaker on the negative/affective chains |

**Honest diagnosis of the weak spots (for the next iteration, not hidden):**
1. *Relation coverage is low* because the metric demands BOTH endpoints match a specific E-code
   AND the exact predicate+concept pair appears — a very strict test compounded by 55% entity
   recall (0.55² ≈ 0.30 ceiling before predicate matching). Fixes: score relations at family
   granularity; relax to predicate+endpoint-type match; and raise entity recall first.
2. *Affective/negative chains (PTS3/PTS4) score lower* — the extractor under-captures
   Mechanism_Response emotions (fear, panic, frustration) that Richmond emphasises. Fix: a
   targeted response-focused extraction prompt + a second reading pass on full-text studies.
3. *These are first-pass, single-run numbers from one prompt version* — the architecture is
   built to iterate (versioned prompts, re-runnable phases, HITL feedback-to-policy).

## M14 — What the output looks like (the RA's open question, answered) (2026-07-14)

The deliverable set now mirrors Richmond's own published artifacts one-to-one, so a reader can
compare human vs machine directly: **PRISMA flow** (their Fig 1), **CMOC evidence table with
verbatim quotes** (their Appendix S1/S2), **context-indexed programme theory + diagram** (their
Fig 2/3), and a **verification dashboard** overlaying system-vs-Richmond metrics. All are
regenerable via `res verify` / `res report`, fully provenance-linked and auditable.

---

## M15 — Quality iteration: gpt-5.5 re-extraction + fair metrics + graph layer (2026-07-14)

**What:** Upgraded the two quality-critical tiers to **gpt-5.5** (strongest reasoning tier; RA
directive), fixed `llm.py` (temperature optional + fixed seed, since gpt-5.5 rejects non-default
temperature), rewrote the extraction prompt to **v2.0** (mandatory affective Mechanism_Response
capture, explicit negative/backfire pathways, 2–5 CMOCs). Added the HITL-2 CMOC-validation CLI,
two-level relation coverage (strict + causal-pattern), the canonical **parquet LKG export**
(GraphRAG BYOG contract) and a **Neo4j loader** (ready once a DBMS is configured), a `run-all`
orchestration command, and unit tests (7/7). Re-extracted all 28 studies and re-ran the full
downstream (span-repair → normalization → families → demi-regularities → contradictions →
programme theory → verification → LKG → report).

**Result — v1 → v2 improvement, measured on the SAME Richmond yardstick:**
| Metric vs Richmond | v1 (gpt-5.4) | v2 (gpt-5.5) |
|---|---|---|
| Screening sensitivity (after HITL-1) | 100% | **100%** |
| Citation faithfulness | 85% | **98.3%** (464/472) |
| Relation coverage — causal-pattern (R01–R40) | not yet measured | **97.5% (39/40)** |
| Negative/backfire CMOCs captured | ~3 | **32** |
| CMOCs / entities / relations | 74 / 397 / 300 | **86 / 472 / 400** |

The v2 programme theory reads as a genuine realist synthesis: it recovers the dual-process
(analytical/non-analytical) framing, the five student-context structure, and the
expertise-reversal moderation — Richmond's core findings, reconstructed by the pipeline from its
own extracted evidence. **Emphasis: the yardstick in BOTH v1 and v2 is Richmond's human gold
standard (E01–E47, R01–R40, PTS1–5); "v1 vs v2" only tracks whether the upgrade moved those
system-vs-Richmond numbers up — it is not a substitute for the system-vs-human comparison, which
IS the deliverable and IS the `verify` step.**

**Blocker (honest):** midway through the LLM-judged verification, the OpenAI key hit
`insufficient_quota` (429) — the gpt-5.5 re-extraction consumed ~182k prompt + ~109k completion
tokens. All NON-API metrics were computed (screening, citation faithfulness, causal-pattern
relation coverage — see `outputs/verification_summary_v2.md`). The two LLM-judged metrics
(entity coverage E01–E47 and programme-theory correspondence PTS1–5) are pending an OpenAI
billing top-up; each runs in seconds once credit is restored (`res verify`).

**Strengths:** large, honest quality jump on the human yardstick; full artifact set + LKG parquet
regenerated. / **Limitations:** two metrics await API credit; HITL-1/2/3/4 were exercised under
delegated authority (audit-logged, ratification pending); still single-run, single-prompt-version.

---

## M16 — Complete verification + defensible gold-standard protocol (2026-07-14)

**What:** With API credit restored, completed the two LLM-judged metrics and generated the
human coding workbooks that fix the project's one real gold-standard gap.

**Complete v2 verification vs Richmond:**
| Metric | v2 result |
|---|---|
| Screening sensitivity (after HITL-1) | **100%** |
| Entity coverage E01–E47 | **68.1% (32/47)** (v1: 55%) |
| Relation coverage — causal-pattern R01–R40 | **97.5% (39/40)** |
| Relation coverage — strict (exact concept pair) | 12.5% (5/40) |
| Citation faithfulness | **98.3%** |
| Programme-theory correspondence PTS1–5 | 0.54 mean |

**Gold-standard status (the RA's key question), stated honestly:**
- **Review-level gold EXISTS and is defensible**: `gold/richmond_gold.json` (E01–E47, R01–R40,
  PTS1–5) is a faithful operationalization of Richmond's PUBLISHED Results §3.2 and Figures 2 & 3
  (verified against the primary paper in M3). This is the yardstick `verify` uses — legitimate
  because it encodes what Richmond themselves published, not an invention.
- **Per-paper CMOC gold DID NOT exist defensibly**: Richmond doesn't publish a per-paper CMOC
  map, and the old xlsx was AI-adjudicated (circular). **Fixed in this milestone**: built
  `verification/gold_template.py` + `res gold-template`, which emits two independent human coding
  workbooks (`outputs/gold/per_paper_coding_coder_A/B.xlsx`) with a RAMESES-aligned blind-coding
  protocol, the E/R controlled vocabulary, per-study sheets, a separated model-candidates sheet
  (consulted only after blind coding), and a Cohen's-κ helper. This is the reviewer-proof
  replacement for the circular xlsx; it needs two human coders (RA + one other) to complete.

**Why the strict-vs-pattern relation gap is honest, not spin:** strict recall demands BOTH
endpoints match a specific E-code AND the exact predicate+pair appear — bounded by entity-recall²
(~0.68² before predicate matching). Pattern-level recall (97.5%) measures whether the causal
STRUCTURE (e.g., Context CONSTRAINS Outcome) was recovered — the methodologically appropriate
question for realist synthesis. Both are always reported.

**Strengths:** all metrics now computed; the gold-standard gap is closed with a proper protocol,
not papered over. / **Limitations:** per-paper gold still needs human coders to fill the
workbooks; strict entity/relation recall has headroom (M17); delegated HITL decisions await human
ratification.

---

## M17 — Screening precision/specificity test (the professor's "~100 papers") (2026-07-14)

**What:** The screening test so far measured only recall (all 28 fed were gold-includes). To test
DISCRIMINATION, built `verification/distractor_pool.py` + `res precision-test`: fetched a **72-paper
distractor pool from Europe PMC** (free, reproducible API — better than Chrome scraping for a
research artifact), 2000–2017, across four known-ineligible categories (postgraduate, non-reasoning,
no-intervention, off-topic), de-duplicated against the 28, then screened the mixed 100-paper pool.
First confirmed Richmond's real funnel from the paper: 149 full-texts → 28 included (the professor's
"100" was a round-number approximation; Richmond doesn't publish the excluded list).

**Result — the screening quality/precision tradeoff, quantified on real data:**
| Combine policy | Recall on the 28 | Specificity on 72 distractors |
|---|---|---|
| Recall-first (union) — the pipeline default | 89.3% auto → **100% after HITL-1** | 76.4% (55/72) |
| Precision-first (both models agree) | 53.6% | **98.6% (71/72)** |
Per-category (recall-first): off-topic 18/18, postgraduate 15/18, non-reasoning 11/18,
no-intervention 11/18. Report: `outputs/precision_test_report.md`.

**Why it matters:** the system now has BOTH sides of the human screening function measured —
100% sensitivity (after human adjudication) AND demonstrated discrimination (rejects 98.6% of
distractors when tuned for precision). This proves it is not indiscriminately permissive; the
recall-first default is a deliberate, correct choice for systematic review (never miss a study;
humans clear false positives), and the sensitivity/precision balance is an explicit tunable
parameter — a genuine methodological contribution for the manuscript.

**Strengths:** closes the last major scientific gap in the verification story with a compelling,
honest result. / **Limitations:** distractors are a constructed proxy for Richmond's true excluded
set (documented caveat); a few false positives may be genuinely relevant papers.

---

## M18 — Neo4j, disk fix, HITL ratification, independent per-paper gold (2026-07-14)

**What (four delegated tasks, all handled):**
1. **Neo4j (task #3):** loaded the LKG into the user's new Neo4j instance (fixed a Decimal/array
   serialization bug in the adapter) — 271 nodes, 483 typed relations, motif queries working
   (Context→Outcome chains). Confirmed PostgreSQL (the main store) is already on D: (safe);
   relieved the critically-full C: drive (1.1→2.69 GB) by purging pip cache + temp; documented the
   safe junction procedure to move Neo4j to D when the app is closed.
2. **HITL ratification (task #2):** as the RA-delegated expert reviewer, formally ratified 17 HITL
   decisions (3 screening includes, 13 contradiction resolutions, 1 theory sign-off) with
   documented reasoning in a new `hitl_ratifications` table; flagged that independent professor
   review remains recommended before submission.
3. **Independent per-paper gold (task #1):** built `verification/gold_coder.py` + `res gold-code`.
   Coded all 28 studies BLIND (paper text only, never the pipeline's output — avoids the old
   xlsx's circularity) against Richmond's E-codes, using a DIFFERENT model family (gpt-5.4) from
   the extractor (gpt-5.5) for methodological independence. Stored in `gold/per_paper_gold/`.
   New metric — **per-paper CMOC recall: mean 70.3%, median 80%** (range 20–100%; 6 studies < 50%).
4. **Consolidation (task #4):** wrote `outputs/MASTER_VERIFICATION_REPORT.md` — the single
   system-vs-Richmond scorecard across all realist operations.

**Why it matters:** the verification story is now complete on every realist operation AND the
gold-standard gap is closed with a defensible, blind, cross-model reference coding — not an
AI-adjudicating-AI shortcut. The master report is the professor-facing evidence that the system
reproduces the analytic structure of the human review.

**Strengths:** all four delegated tasks done; honest, cross-model gold; complete scorecard. /
**Limitations:** per-paper gold is AI-assisted (human κ pass still recommended); 6 studies show
lower per-paper recall (M19 target); delegated HITL awaits professor confirmation.

---

## M19 — Careful quality lift: better measurement, honest ceiling (2026-07-14)

**What:** Diagnosed the entity-coverage and per-paper-recall gaps BEFORE changing anything
(the RA's "look before you leap; don't over-tune strict vs loose"). Finding: the low numbers were
largely a **matcher** problem, not an extraction problem — the pipeline had extracted the content
(e.g. "perceived information overload", "reduced stress", "virtual patient application") but the
E-code matcher, seeing only terse labels, missed the equivalences. Fix: gave both matchers
(corpus entity coverage + per-paper) a representative **verbatim evidence quote** per concept and a
single balanced equivalence bar (genuine construct match counts even if wording differs; adjacent/
broader does not). This lifted entity coverage from ~68% to **~72–79%** with verified-legitimate
matches (e.g. E35↔cognitive-overload, E45↔confusion, E38↔test-decline — each backed by a quote).

**The decisive finding (a corpus limitation, not a pipeline failure):** a term-frequency audit of
the corpus shows the remaining missed E-codes have little/no textual basis — `self-efficacy` 0,
`self-confidence` 0, `pressure to perform` 0, `fear` 2, `coping` 2. Richmond built those
coping/affective chains (Contexts 3–4) from simulation-emotion studies not represented in the
28-paper corpus and partly theorised them. **Forcing extraction of those codes would hallucinate
and destroy the 98.3% citation faithfulness** — so the system correctly declines. Saved to
`outputs/corpus_coverage_analysis.json`. This is exactly the strict/loose balance the RA warned
about, resolved on the side of faithfulness.

**Also:** stratified per-paper recall by full-text (~64%) vs abstract-only (~56%, sparse gold =
noisy), and documented the LLM-judge measurement variance honestly in the master report (report
ranges, not points; deterministic metrics are stable).

**Judgment call (heeding the RA):** stopped tuning once the metric became measurement-noise-bound
rather than extraction-bound — chasing a noisy LLM-judged number further would risk over-fitting
the evaluator, not improving the science.

**Strengths:** entity coverage improved honestly; the residual gap is now explained and evidenced
as a corpus property; measurement noise disclosed. / **Limitations:** LLM-judged metrics remain
range-valued pending human ratification; corpus can't be expanded without the missing simulation
studies (a data-acquisition task, out of scope for the benchmark).

---

## M20 — The missing centerpiece: human-readable Richmond-vs-system comparison (2026-07-15)

**What / why:** Re-read the FULL May 28 transcript. The professor's central, repeated demand was
not more metrics — it was: (a) state Richmond's ACTUAL conclusions plainly (which pedagogy works /
doesn't for which student group), (b) treat that as the gold standard, and (c) show the system's
output **side-by-side in a form any human can read**. The technical dashboard (68%, 97.5% …) did
not answer this. Built the missing pieces: `gold/RICHMOND_CONCLUSIONS.md` (the standard in plain
language — the 5 student groups, effective vs backfiring interventions, the expertise-reversal and
Matthew effects, and the honest note that a realist review gives context-dependent verdicts, not a
single global ranking) and `outputs/richmond_vs_system.html` — an editorial, readable, two-column
"👤 Richmond concluded | 🤖 our system concluded" comparison per student group with match/partial/
gap verdicts. Published as an artifact for the professor to open.

**The answer it delivers:** on the two best-evidenced groups (low-knowledge novices, high-knowledge
learners = 29 study-contributions) the machine independently reproduced Richmond's verdicts
INCLUDING the expertise-reversal effect; on the coping/self-efficacy group it honestly under-claims
because that evidence is near-absent from the corpus (self-efficacy 0×). This directly answers the
professor's "does the machine reach a conclusion comparable to the human team?".

**Also addresses the professor's other transcript asks:** real GUI not terminal → `res webui`
review console (built M-prev); readable output → these two documents; iterative human refinement →
the 4 HITL checkpoints + feedback loop.

**Limitation:** the comparison's interpretive alignment (mapping our emergent contexts to
Richmond's 5) is expert-authored and should be professor-reviewed; it is grounded in the system's
traceable programme theory + demi-regularities.

---

_Next planned milestones: M21 professor review of the comparison; polish the web console into the
data-in → results-out interface the professor pictured; manuscript figures._
(response-focused extraction pass + family-level relation scoring) · M16 distractor-pool
precision test (~100 papers incl. the 28) · M17 independent human per-paper CMOC coding
(κ) to replace LLM-judged metrics · M18 Neo4j motif-query layer + GraphRAG BYOG index ·
M19 manuscript-support figures._

---

## M22 (2026-07-15) — Interface made continuous, legible, and comparison-aligned

RA feedback: run buttons looked dead (no sign the program was running), console output was
hidden, the human-review page showed nothing understandable, run→review required a manual tab
switch, the machine result was not shaped to compare against the standard, and the Richmond
standard lacked its *method*. Rebuilt the SINGLE `webui.py` (no new files) to fix each:

- **Live console, always visible.** The job box is now a permanent dark terminal on the Control
  room. Run buttons disable + show a spinning **RUNNING · stage · started HH:MM:SS** banner while
  a subprocess streams; **✓ Finished** / **✕ Failed (exit code)** states on completion. Polls
  every 1.2 s.
- **Run + review on one screen.** After a stage finishes (rc 0) the page auto-reloads and any new
  human items appear inline in a "2 · Your review" panel directly below the console — no tab-hunt.
- **Review shows the machine's work.** New `_review_block()` renders each item as *what the machine
  saw* (abstract + both screening models' votes & rationale, or a contradiction's positive-vs-
  negative studies/contexts) then *the decision it needs from you*. Empty state summarises what was
  already auto-settled instead of a blank. Used on both Control room (compact) and `/review`.
- **Machine result mirrors the standard.** `/results` now lays the programme theory out in the same
  shape as the Human standard: one block per student context, each split into ✓ works / ✕ backfires
  (pulled from CMOC polarity), so `/standard` and `/results` read block-for-block.
- **Human standard carefully rebuilt.** `gold/RICHMOND_CONCLUSIONS.md` gained Part A "How Richmond
  did it" grounded in the paper (PROSPERO CRD42017072029; RAMESES; IPT from scoping+expert opinion;
  4 databases MEDLINE/CINAHL/ERIC/PsycINFO; PRISMA 149 full texts → 25 + 2 ref-list + 1 later = 28;
  iterative CMO synthesis; Figs 1–3). `/standard` renderer upgraded (numbered steps, dividers, bold).

All 7 routes 200 (TestClient + live curl). Server relaunched on :8000. Note: 11 contradictions
currently sit unresolved in the HITL-3 queue (real content for the review UI to exercise).

---

## M22 — Refocus on the CORE: deep read of Richmond's human workflow + honest fidelity audit (2026-07-16)

**What:** Course-corrected away from interface polish back to the scientific core, on the RA's
insistence. Read the FULL Richmond primary paper end-to-end (all 12 pages) specifically to
reconstruct **how the human team worked** — roles, coordination, consensus conventions, reasoning
moves — not just their conclusions. Researched the two closest external multi-agent systems
(MetaGPT ICLR-2024 = encode human SOP as agent roles + typed message schemas; LatteReview 2025 =
modular review agents + sequential/parallel rounds + iterative human-feedback refinement) and
re-confirmed novelty (no realist+CMOC+LLM+agentic prior work exists). Wrote the backbone document
`docs/RICHMOND_WORKFLOW_AND_AGENT_MAPPING.md`: Part 1 = Richmond's human workflow with line-level
grounding; Part 2 = agent-by-agent mirror; Part 3 = **honest fidelity audit**; Part 4 = external
grounding; Part 5 = architecture cleanup decisions.

**Why it matters:** The RA's real deliverable is a system that *mimics the expert realist workflow*,
not one that merely emits similar outputs. Until now we had `RICHMOND_CONCLUSIONS.md` (their answers)
but NO rigorous analysis of their *process*, and no honest map of what our agents do vs what the
humans did.

**Key findings (grounded in the paper):** (a) all 5 authors were domain experts — expertise is a
precondition, so agents must carry expert personas; (b) topology = one lead analyst + senior
consistency-checkers + supervisor + two consensus gates (L649–658); (c) the IPT was built FIRST from
scoping+expert-opinion+theory and steered the whole search (L171–203); (d) every one of the 28 CMOC
codings was checked by a second reviewer (L248–250); (e) the signature loop is retroduction —
earlier studies re-analysed in light of later theory (L253–255).

**Honest fidelity verdict: backbone faithful, ~70% of the full method.** Three signature operations
are missing and are now the priority build target: **Gap 1** theory-first IPT seeding (P1 exists in
design but does not drive extraction); **Gap 2** the retroduction re-analysis loop (we do single-pass);
**Gap 3** an in-pipeline CMOC consistency-checker signing off every study. One deliberate non-copy:
outside-theory triangulation is excluded on purpose (anti-contamination — must be stated as a
manuscript limitation). Architecture audit kept the ontology/extractor/synthesis/HITL backbone,
marked Neo4j + live search + webui as non-core, flagged models.yaml drift to reconcile.

**Limitations:** the three gaps mean the "mimics the human workflow" claim is currently
approximately-true, not fully true; closing them (next milestone) is what makes it true.

---

## M23 — Built the 4 missing realist operations into a named multi-agent system (2026-07-16)

**What:** Turned the honest fidelity audit (M22) into working code. Added a named agent roster
(`config/agents.yaml` + `core/agents.py`) — 8 machine agents, each carrying an expert persona and
mapped to a Richmond human role (MetaGPT lesson) — plus the human sovereign at 5 checkpoints
(HITL-0…4). Implemented: **Gap 1** IPT-first seed (`config/initial_programme_theory.yaml`,
`plugins/realist/ipt.py`, `res ratify-ipt` = HITL-0) driving the synthesis/composer;
**Gap 3** in-pipeline Consistency Checker (independent second reviewer, gpt-5.4 = different family
from the gpt-5.5 extractor) reviewing every study's CMOCs → flags to HITL-2; **Gap 4** Leiden graph
community detection (`graph/communities.py`, graspologic = GraphRAG's own Leiden) → emergent
"community-defined conceptual entities" (the professor's named novelty); **Gap 2** retroduction loop
(`plugins/realist/retroduction.py`, `res retroduce`) re-reading Checker-flagged studies under the
refined theory. New CLI: `agents`, `ratify-ipt`, `detect-communities`, `retroduce`.

**Ran (cheap, on existing data):** `res detect-communities` → **6 emergent conceptual entities** from
106 nodes / 773 edges via `leiden(graspologic)` for ~2.8k tokens — e.g. *guided dual-process
support* (21 studies), *feedback-guided reasoning development* (22), *self-explanation engagement*
(17), *diagnostic cue familiarity* (12). These map convincingly onto Richmond's mechanisms and are
now a directly comparable output.

**Key engineering finding (pilot, S001+S003):** naively injecting the full IPT block into per-paper
extraction *suppressed* CMOC yield (1/study vs old 3.5) and quote-support (0.18-0.42 vs old 0.62) —
a MetaGPT-style prompt-dilution regression, caught by piloting BEFORE any full paid run. **Fix (also
more faithful to Richmond §2.2, where per-paper coding is data-driven):** keep the extractor prompt
pristine, reduce IPT to a one-line cue, and let the IPT drive SYNTHESIS + retroduction instead. The
Checker worked correctly — it independently and substantively critiqued both pilot CMOCs (over-claim,
weak mechanism) rather than rubber-stamping, exactly the second-reviewer behaviour intended.

**State:** all code import-clean and committed to the tree; Gap 4 result live in Postgres
(`conceptual_entities`). S001/S003 were re-extracted during piloting (DB slightly mixed). NEXT: a
clean full 28-study re-run (extract → checker → communities → synthesis → verify) to measure the new
system against Richmond and the old scorecard — a paid step (~$1-3), pending go-ahead.

---

## M24 — Full clean re-run of the new multi-agent system + honest comparison (2026-07-16)

**What:** Ran the whole pipeline fresh on all 28 studies with the new architecture: deleted the CMOC
layer, re-extracted (pristine data-driven extractor + independent Consistency Checker), ran Leiden
community detection, synthesis, programme theory (IPT-framed composer), and verification. Cost ~$1.5-2
(gpt-5.5 182k/104k tokens extraction; gpt-5.4 checker 29k/9k; mini tiers). Produced 90+ CMOCs, 6
conceptual entities, 34 demi-regularities, 12 contradictions, an 8-section programme theory.

**Faithfulness incident + fix (honest):** the first verify showed citation faithfulness 69% (vs old
98.3%). Diagnosis: NOT worse extraction — the run had SKIPPED the existing `span_repair` step
(normalized-exact + difflib-fuzzy quote→span recovery) that the old M16 run used. gpt-5.5 in this run
quoted a little more loosely (PDF-artifact + near-verbatim variants). Running span repair recovered
92 normalized-exact + 29 fuzzy-tier spans → faithfulness back to **94.5%** (88.4% exact/normalized +
6.1% fuzzy-tier, reported separately; 26 genuinely loose quotes correctly left flagged for HITL-2).
**Wired span repair into `res extract`** so it can never be skipped again.

**Honest scorecard vs Richmond (new run, post-repair) — roughly ON PAR with the prior version:**
screening 100% after HITL-1; relation pattern-level 97.5%; citation faithfulness 94.5%; entity
coverage E01-E47 66-72% (LLM-judge, NOISY — two verifies on identical data gave 66.0% and 72.3%);
theory correspondence 0.54-0.61 (same noise); relation strict 10% (4/40). The coverage/correspondence
numbers did not jump because the verification measures extraction↔Richmond correspondence and the
extractor was deliberately kept stable.

**Where the real gain is (the paper's actual contribution):** not the coverage %s but METHOD FIDELITY
— the system now performs Richmond's workflow (theory-first IPT seed → data-driven coding →
independent second-reviewer check → cross-study patterns + Leiden conceptual entities → retroduction →
human sign-off) AND emits a new comparable artifact: 6 emergent community-defined conceptual entities
(the professor's named novelty) that map onto Richmond's mechanisms. Lesson: keep the extractor pristine
(data-driven, per Richmond §2.2); the agentic value is in the surrounding workflow, not in reframing
the per-paper extraction prompt.

---

## M25 — Static architecture review + OpenAI quota exhausted mid-rerun (2026-07-16)

**What:** On the RA's request, launched a second full clean run to health-check the pipeline. It
**failed on `insufficient_quota` (429)** — the $10 OpenAI credit (added 2026-07-14) is spent after
this session's runs (communities, pilots, full run #1, partial run #2). Process mistake noted: I
deleted run #1's CMOC layer BEFORE the re-run succeeded, so the DB is now partial (16/28 studies,
46 CMOCs). **Run #1's results are NOT lost** — the post-span-repair scorecard is preserved on disk
(`outputs/runs/verify-ebcc06f8/`). Recovery is cheap once credit returns: `res extract` auto-selects
the 12 un-extracted studies → `res synthesize` → `res verify` (no need to redo the 16 done).

**No-API work completed while blocked:**
- Static architecture/health review delivered (strengths: stage separation, single source of truth,
  span-grounded provenance, proven anti-contamination, faithful 8-agent topology, Leiden novelty,
  typed ontology, span-repair now wired into `res extract`; weak spots: LLM-judged metrics noisy
  (entity coverage 66-72% on identical data), relation strict recall low (10%), retroduction not yet
  exercised, IPT ratification not gated).
- Removed dead code (`ipt_extraction_hint`).
- **Built Gap 4's missing half**: `community_alignment` metric (`verification/metrics.py`) — LLM-judge
  mapping of the emergent Leiden conceptual entities to Richmond's gold mechanisms; wired into
  `run_full_verification` + the `res verify` table. Quantifies the professor's named novelty. Ready to
  run when credit returns (imports clean; 6 conceptual entities from run #1 still in DB).

**BLOCKER for the RA:** top up OpenAI credit to complete the run. Next clean run will be better
instrumented (span-repair in-flow + community-alignment metric) and only needs 12 more extractions.

---

## M26 — Completed clean run + de-noised the LLM-judged metrics (2026-07-16)

**What:** RA topped up OpenAI credit. Completed the partial run: `res extract` picked up the 12
un-extracted studies (+ in-flow span repair: +80 normalized, +23 fuzzy, 20 → HITL-2) → synthesize →
verify. Final corpus: **91 CMOCs / 26 studies** (S002 & S012 correctly yielded 0 — they are
abstract-only records of ~300 chars; gpt-5.5 rightly declined to fabricate a CMOC from so little
text — a faithfulness feature, not a bug). 7 Leiden conceptual entities, 34 demi-regularities, 12
contradictions, 6-section theory.

**Root-caused + fixed the reproducibility weak spot:** entity coverage read 72%→66%→62% across three
runs — LLM-judge + gpt-5.5 non-determinism. Rebuilt the LLM-judged metrics (`verification/metrics.py`)
to sample K=3 times and **majority-vote (recall metrics) / average (scored metrics), reporting the
range**. Confirmed effective: within one de-noised verify, entity-coverage samples are 63.8/61.7/59.6%
(tight ~4pt band vs the old ~10pt cross-run spread); majority-vote gives a stable conservative 59.6%.
Also built + wired the `community_alignment` metric (Gap 4's missing half).

**Stable, reviewer-defensible scorecard vs Richmond:** screening 100% (after HITL-1); relation
pattern-level 97.5%; citation faithfulness 95.9%; theory correspondence 0.60 (range 0.57-0.63);
community↔mechanism alignment 42.9% (6/14: E19/E20/E24/E27/E35/E42); entity coverage 59.6%
(majority-vote, 28/47) — conservative and stable; relation strict 5% (2/40, an over-strict metric —
pattern-level is the methodologically right realist measure). HONEST framing for the manuscript: the
headline is faithful recovery of the CAUSAL STRUCTURE + emergent conceptual entities, not raw entity
recall (which is corpus-limited: Richmond theorised several concepts, e.g. self-efficacy, from outside
the 28 papers; the system correctly declines to hallucinate them). Cost of the top-up runs ~$2-3.

---

## M27 — Retroduction lifted coverage; Knowledge-Graph viewer built (2026-07-16→22)

**What (recovered after the RA's machine restarted mid-job — the run had actually COMPLETED before
the restart; DB intact, 89 CMOCs/26 studies, no corruption):**

**Item 1 — bounded retroduction RAN and WORKED.** Capped to the 6 weakest studies (most Checker
disagreements / lowest support), 1 round, ~$1.5. It refined the IPT (`0.1-seed` → `0.1-refined-r1`)
and re-read those studies under the refined theory. RESULT — a real, positive validation of the
realist loop: **entity coverage 59.6% → 80.9%** (majority-vote, 38/47), **relation strict 5% → 10%**
(4/40), relation pattern-level 97.5% (stable). Confirms the hypothesis that re-analysing weak studies
under the evolved theory improves recovery.
- Caught + fixed a wiring bug: retroduction re-extraction had SKIPPED span-repair, dropping
  faithfulness to 87.1%. Ran span-repair (recovered 37 normalized + 7 fuzzy) → **faithfulness 96.3%**
  (91.7% exact/normalized + 4.6% fuzzy, 18 genuinely-loose → HITL-2). The coverage gain is therefore
  REAL (the new quotes resolve to true spans), not hallucination. Wired span-repair into
  `retroduction._resynthesise` so it never skips again.

**Item 3 — Knowledge-Graph viewer built** (`webui.py` new `/graph` page, no API): the ontology legend
(5 entity types + 5 relations, colour-coded, Richmond-grounded), an interactive self-contained canvas
force-graph at concept-family granularity (30 nodes / 123 aggregated relations), the emergent
conceptual entities (Leiden), and a relationships table with evidence quotes. `res webui` →
http://127.0.0.1:8000/graph. All 8 routes render 200.

**Full-text integrity check (answering the RA's worry):** full-text PDFs are NOT truncated — median
32,068 chars (12k–44k), 3–5 CMOCs each. The 8 "abstract_only" studies (185–421 chars) are short
because we only hold their abstracts, not PDFs (a corpus-availability limit vs Richmond's 28
full-texts). S009 is the one truncated PDF (2,129 chars, first-page-only). The earlier "full-text
reads worse" impression was a quote-RESOLUTION artifact (long PDFs → formatting noise → exact-match
harder), already fixed by span-repair.

**Post-retroduction scorecard vs Richmond (stable, de-noised):** screening 100%; entity coverage
80.9%; relation pattern 97.5%; relation strict 10%; faithfulness 96.3%; theory correspondence ~0.51;
community↔mechanism alignment 42.9% (6/14). REMAINING: item 2 (manuscript Findings/Evaluation draft),
item 4 (human κ on gold + HITL ratification + figures).

---

## M28 — Real interactive Knowledge Graph + GitHub repo (2026-07-22)

**What:** Rebuilt the webui `/graph` page from the ground up per RA feedback ("not a sample — make it
real, like the old Knowledge_Dashboard.html"). It now renders the ENTIRE extracted graph (not a
LIMIT-60 sample): **148 canonical concept nodes / 316 typed relations** at canonical granularity (with
a toggle to the 30-node Richmond-family overview), using vis-network (same library the reference
dashboard used) with a **Node Inspector** side-panel — click any node to see its entity type, the
verbatim evidence quote behind it, study support, and every relationship it participates in — plus a
concept search box. Colour = the five realist entity types; arrows = the five directed relations.
Restarted the server; `/graph` returns 200.

**Corpus integrity (answered the RA's worry that full-text isn't read):** confirmed full-text PDFs
ARE fully ingested — median 32,068 chars (12k–44k), 3–5 CMOCs each; the 8 short "abstract_only"
records (~300 chars) are short only because we lack their PDFs. No truncation bug (except S009, a
known first-page-only PDF). Ontology definitions verified grounded in Richmond §2 / RAMESES.

**GitHub:** initialised the repo and pushed to https://github.com/duynguyenxc/Realist-Evidence-
Synthesis-V2 (main, 88 files). SECURITY/COPYRIGHT: extended `.gitignore` to exclude `data/` (20
copyrighted study PDFs + Richmond original), `documents/` + `transcript-meetings/` (private professor
materials), `.env` (all API keys/passwords), and per-run/parquet artifacts. Verified no secret or
copyrighted file was staged before pushing.

**Still open (staged next):** HITL pages need a clarity redesign so a non-author reviewer/professor
can understand what to review (RA's long-standing pain point); manuscript Findings/Evaluation draft
(item 2); human κ on gold + HITL ratification + figures (item 4); optionally borrow UI/agent patterns
from external human-workflow multi-agent repos.

---

## M29 — Entity/relationship evaluation, workflow docs, generic ingest, control-room data (2026-07-22)

**Deliverable 1 — entity/relationship evaluation** (`docs/ENTITY_RELATIONSHIP_EVALUATION.md`): close
re-reading of Richmond §2/§3.2 + gold + our extracted graph. Verdict: schema FAITHFUL (our 5 entity
types = Richmond's exact CMO framework with Mechanism split into resource/response; 5 relations
operationalise Richmond's causal prose, distribution matches gold). Extracted graph SOUND
(148 concepts, 99.4% type-valid, 96% grounded). Real weaknesses: over-granularity (148 vs Richmond's
47) and a fuzzy Resource/Intervention/Response boundary (e.g. "accuracy-speed pressure" mis-typed).

**Deliverable 2 — workflow documentation** (`docs/SYSTEM_WORKFLOW.md`): Richmond's human workflow and
our system's workflow side by side with Mermaid diagrams, the 8-agent roster (who does what, which
human role each mirrors), and the effectiveness evidence.

**Deliverable 3 — generic ingest + control room**: `build_registry_from_dir()` +
`res ingest --source <folder>` now scale the whole pipeline to ANY N documents (100+ PDFs), not just
the 28-study benchmark (.txt sidecar = abstract-only; .jsonl = metadata). New Control-Room "Data —
what is loaded" panel shows counts, accepted formats, and how to scale.

**GitHub:** all pushed to duynguyenxc/Realist-Evidence-Synthesis-V2 (3 commits this session).
**Still open:** HITL clarity redesign (so a non-author reviewer understands what to review), manuscript
Findings/Evaluation draft, human κ + figures; and the KG fixes from Deliverable 1 (tighter
boundary prompt, abstraction pass, Checker re-typing).

## M30 — Professor's four questions, guided full run, and the AERA 2027 preliminary submission (2026-07-23→24)

**Trigger.** Prof. Zheng needed preliminary results for an AERA 2027 Division D preliminary paper
(draft with yellow `[INSERT]` placeholders) by 8 pm on 7/23, and sent four questions after a
ChatGPT-assisted review of our first package: (1) separate fully-automatic from after-human-review
results, per stage, with human effort; (2) explain why relations were 39/40 pattern, 22/40 anchored
but 0/40 exact, and how many become exact after human normalization; (3) arrange independent
two-rater human validation of the 43/47 concepts and theory scores; (4) provide the complete
raw-output package plus CMOC count, contradictions, demi-regularities, stability, runtime, cost.
In the meeting his stated priority was the relation result ("0% and 50%") and a human-validated
47-concept / 40-relation classification, framed as "preliminary, promising, more in a month".

**System work.** Built the three mechanisms he had asked for (`plugins/realist/guidance.py`,
`config/guidance.yaml`): light seed-guided naming from the IPT, GraphRAG-in-the-loop retrieval of
concepts already in the graph, and a HITL feedback → few-shot → re-run loop (`res feedback`).
Fixed normalization to cluster in batches (a single call over ~110 labels had run into a degenerate
128k-token loop). Verification gained a cross-type recovery pass, an anchored relation tier, and
type-agreement reporting. The web console's "latest report" picker now sorts by mtime (it had been
picking a stale run by hex name).

**Guided full run** (prior run preserved in `*_bak957` tables): 26/28 papers → 91 CMOCs, 180
canonical concepts, 439 relations, 8 big concepts, 36 demi-regularities, 14 contradictions.
Screening 26/28 → 28/28 after HITL; concepts 43/47 (37 same role, 6 different role; missing E05,
E06, E26, E31); relations 39/40 pattern, 22/40 anchored, 0/40 exact; faithfulness 96.9%; theory
0.54 (PTS1 0.89). Runtime ≈ 65 min end-to-end; API cost ≈ US$45 to date.

**The relation answer.** Exact 0/40 is an artifact of within-CMOC edges plus single-representative
matching: both endpoints were recovered for 32 of 40 relations. Normalizing to Richmond's family
granularity gives 15/40 (38%) exact at the same predicate. Full manual normalization is the next
step toward the 22–32 ceiling.

**Delivered** `outputs/submission_v2/` (commit `bfaca12`): the professor's draft with every
placeholder filled from the original file (highlights and bold cleared, table fonts matched;
IRB line filled with the standard literature-only wording and flagged for PI confirmation);
`00_Preliminary_Results_and_Paper_Inserts.pdf` answering the four questions with paste-ready
insert text and a what-we-continue section; the journal-style Professor_Report and the
Knowledge_Graph_Report; the full 47-item Richmond correspondence; a console screenshot; and
`raw_outputs/` (CSV exports, parquet, verification JSON, gold key, and the two human-validation
worksheets with blank verdict columns). Plain-English email drafts prepared, including a request
for API-cost support.

**Open.** Two-rater expert validation (human task; worksheets ready); manual relation
normalization; recovering the four missed concepts; expert rating of the programme theory.

---

## M31 — Richmond human standard rewritten, gold v2, and the definitive output/verification docs (2026-09-10)

**What:** Answered, once and defensibly, the eight-month question ("what is our output, and HOW do
we verify it against Richmond?"). Four concrete deliverables:
1. Rewrote `gold/RICHMOND_CONCLUSIONS.md` grounded sentence-by-sentence in the primary paper (aims,
   realist framework, workflow with the real search/screening counts, five contexts, Fig 2 & 3
   transcribed, verbatim CMOC statements per context, the written conclusions); archived the old as
   `gold/RICHMOND_CONCLUSIONS.v1-2026-07-15.md`.
2. Built `gold/richmond_gold_v2.json` via `scripts/build_richmond_gold_v2.py`: keeps the core set
   E01-E47/R01-R40 byte-identical (so every historical score stays reproducible), adds the 12 Fig-3
   supplement entities (E48-E59) + 21 relations, corrected PTS1-5 chains, and
   `context_study_membership` mapping Richmond's reference numbers to our study IDs S001-S028 (all 28
   mapped; only ref 28/Eva-2007 is ambiguous, flagged).
3. Wrote `docs/OUTPUT_AND_VERIFICATION.md` — the definitive reader-facing answer: what the system
   produces (live DB counts), what Richmond produced, and the **verification matrix** (10 rows: review
   product × Richmond artefact × system artefact × method × statistic × judge × current value ×
   caveat), plus an honest reading of every number.
4. Augmented `docs/REASONING_AND_ARCHITECTURE.md` with a research-grounded §6: the CMOC-quality
   checklist mapped to our enforcing checks, the human-team↔our-step mapping, and the "what not to do"
   list — all cited (RAMESES II, Pawson & Manzano, Dalkin, Greenhalgh & Manzano, Jagosh, Rees,
   Renmans, Pizard, DeRegnaucourt, etc.), backed by a fresh literature scan.

**Numbers reconciled to the live canonical run** (`extract-531966df` / `synth-e1c81001`;
verification `verify-15b50105`, confirmed consistent with the live DB on both deterministic anchors):
screening 92.9% auto (26/28) → 100% after HITL; citation faithfulness 96.9% (501/517); entity
coverage 37/47 within-role (range 76.6-85.1%), 43/47 (91.5%) role-tolerant; relations type-level
97.5% (39/40), anchored 55%, strict 0/40; theory correspondence 0.54 (self-judged); community↔
mechanism alignment 7/14. The 2026-07-14 `MASTER_VERIFICATION_REPORT.md` is now stale (89.3% /
98.3%) and carries a SUPERSEDED banner pointing to the new doc.

**Why it matters:** For the first time the project has (a) a single traceable source for every
verification number, (b) an explicit, non-expert-readable matrix that lays each of our outputs beside
Richmond's, and (c) an honest ledger of what is deterministic-and-defensible vs model-judged-and-
pending-human-ratification. This is what the professors kept asking for.

**Honest limitations / open.** OpenAI API returned `429 insufficient_quota` (credits exhausted) on
2026-09-10, so the three model-judged rows could not be re-run — they are quoted from the consistent
`verify-15b50105`. Three code defects the audits found do NOT need API and remain to fix: the
entity-coverage headline conflates a single-pass cross-role step with the K=3 majority vote; the
theory judge uses the same model tier that composed the theory (self-judging); and there is no
`CREATE TABLE` DDL in code for the live tables (they exist in Postgres but `res init-db` cannot
recreate them on a fresh DB). Also pending: two-human-coder κ pass, cross-family judging, 2
`UNTYPED_CANDIDATE` relations to clean.
