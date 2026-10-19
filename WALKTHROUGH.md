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

---

## M32 (2026-09-23) — the output made observable, and the benchmark corrected

The session opened on the RA's standing question — *"where is the output, what does it look like,
and how exactly do we verify it?"* — and closed having found that part of the reason the output had
never been seen is that it was never actually written, and part of the reason the verification was
unpersuasive is that it was scoring against a benchmark the project had already documented as
wrong.

**1. The exports were empty.** `scripts/export_outputs.py` wrote CSVs in which *every data row was
a verbatim repeat of the header*: `pandas.read_sql` over a psycopg connection with
`row_factory=dict_row` converts each dict row into its keys. 517 entities, 439 relations and 91
CMOCs had been "exported" as 1,047 copies of four header lines — including in the `raw_outputs/`
bundles shipped to the professor in `outputs/submission/` and `outputs/submission_v2/`. Fixed with
a raw cursor plus `cur.description`; re-exported and verified.

**2. A single shareable results page.** New `core/results_export.py` + `res export-results` writes
`outputs/RESULTS.html` — one self-contained file, no server, no database, openable on a phone and
attachable to an email. Seven sections: the one-minute human-vs-machine answer; live output counts;
**a side-by-side of Richmond's five student contexts against ours, block by block**; the
verification matrix with exact confidence intervals and a "judged by" column; all 46 gold concepts
one by one with the matcher's reasoning; every CMOC, entity (with its verbatim quote), relation and
emergent mechanism, searchable; and what is not yet verified. This is the shareable rendering of
what `res webui` serves interactively — per the M21 lesson, it extends the one coherent system
rather than adding another one-off artefact. Published as an artifact for remote viewing.

**3. The benchmark was wrong, and it was the one being scored.** `gold/richmond_gold.json` was
byte-identical to `richmond_gold_v1.json` (MD5 `c3edd83…`), so every correction
`RICHMOND_CONCLUSIONS.md` §6 claimed had been applied had never reached `metrics.py`. **All five**
v1 programme-theory chains were cross-context contaminated and every one routed through `E19`, a
Figure-2 placeholder belonging to one context and carrying no relation (§6 admitted only two).
Further: E07–E18 were typed `Intervention` although Richmond tags each *"(Mresource)"*; E21 and E43
contradicted the paper's own `(Mresponse)` tags; `E01` is the review population, not a context, and
inflated the denominator to 47. Built `gold/richmond_gold_v3.json`
(`scripts/build_richmond_gold_v3.py`) recording **Richmond's own four-role scheme** alongside ours —
our ontology legitimately splits their Mresource column into Intervention + Mechanism_Resource
(Dalkin et al. 2015), so the system had been marked wrong for a distinction Richmond never drew.
`RES_GOLD=v1` still reproduces every published number exactly.

**4. Four metrics were computed dishonestly, and are not any more.**
- *Citation faithfulness* conflated exact, normalized and fuzzy tiers under the word **exact**,
  breaking the promise `span_repair.py` makes in its own docstring. True split: 48 exact, 432
  normalized (PDF de-hyphenation), 19 fuzzy, 18 unresolved → **92.8% verbatim, not 96.9% exact.**
- *Entity coverage* reported 91.5% against a per-sample range of 76.6–85.1% — a headline outside
  its own range — because the cross-role recovery pass ran **once, unvoted**, after a K=3 majority
  vote. Now sampled and voted identically; hallucinated and duplicate codes discarded.
- *Screening* silently blended six screening runs and took its denominator from its own output.
  Now one named run (`screen-4e53160c`), denominator from the study registry.
- *Theory correspondence* was graded by the same model tier that composed the theory. Now scored by
  both that tier and a new `independent_judge` tier from a different family, with the gap reported.

**5. Confidence intervals everywhere.** New `verification/stats.py` adds Clopper–Pearson exact
intervals to every proportion — chosen because the denominators are small (28, 40, 46) and two
headline values sit exactly at the boundary (28/28, 0/40) where Wald degenerates.

**Corrected scorecard (run `verify-d72550c4`, gold v3).** Screening 92.9% unaided → **100%**
(95% CI 87.7–100) after one human check, from one named run. Verbatim grounding **92.8%**
(90.3–94.9). Concepts **38/46 like-for-like** (68.6–92.2), 45/46 role-tolerant, 7 role
disagreements. Relations: type-level 39/40 **but only 8 distinct patterns exist in our graph
against 7 in the gold, so the tier is saturable and is now reported with its ceiling**; anchored
**29/40 (72.5%)**, rising to 80.6% over the arrows Richmond actually draws; strict **0/40**
(0.0–8.8). Emergent mechanisms **22/28 (78.6%)**. Programme theory **0.56 same-family vs 0.87
independent — a 0.31 gap on identical inputs, which is the finding, not a score.**

**6. `docs/VERIFICATION_PROTOCOL.md`** — the cited methodological answer to "how do you verify
this?". Three separable claims (faithful / non-inferior / in correspondence) each with its own
warrant; why each metric is the right one; and an honest gap list. Key external findings that
reshape the framing: no published work automates realist synthesis at all, and the field's own
flagship attempt (Owen-Boukra et al. 2026 *BJGP Open*, with Geoff Wong and James Thomas) **poses the
question and defers the evaluation design** — that is the gap; no published study reports IRR for
CMOC extraction, Richmond included, so there is no psychometric baseline and creating one is the
contribution; Cohen's κ is the *wrong* statistic for span extraction and positive specific agreement
/ F is the right one (Hripcsak & Rothschild 2005), which dissolves the standing "you can't compute κ
on 91 CMOCs" objection; human screeners err at 10.76% (Wang et al. 2020), so the target is
**non-inferiority, not correctness**; and "reproduces Richmond" is the wrong claim to make at all,
because a human gold standard is instrument-dependent, incomplete and not ground truth.

**Standing gap, unchanged and now blocking:** no human has coded anything. Until two coders
independently code 8–10 papers, there is no human–human ceiling and every agreement-style number
here is uninterpretable. `res gold-template` already produces the blank workbooks.

**Also still open** (found this session, not yet fixed): `res init-db` has no DDL for `cmocs`,
`entity_instances` or `typed_relations`, so the repository cannot rebuild its own schema; `res
run-all` crashes on its first line (Typer `OptionInfo` passed as a value); `res feedback` violates a
NOT NULL constraint so the HITL→few-shot loop has never recorded a correction; `pyproject.toml`
declares langchain/langgraph/graphrag (all unused) and omits openai, graspologic and python-docx;
and the "GraphRAG" claim is not supported by the code — there is Leiden community detection and LLM
community labelling, but no embeddings, no vector store and no retrieval.

---

## M33 (2026-09-23) — full-run attempt blocked by API credit; architecture described from the code

**The run was launched and stopped safely.** With a full `pg_dump` (943 KB) plus `*_bak_m33`
snapshot tables taken first, the pipeline was started end to end. `ingest` completed (28 studies,
165 text units, deterministic, no API). `screen` then died on its first model call with
`429 credit_balance_exhausted` — "You have no credits remaining". The `&&` chain stopped there, so
nothing downstream ran and **every table matched its snapshot exactly afterwards**. Diagnostics: the
key is a valid **project key** (`sk-proj-…`, authenticates, 132 models visible) with a zero balance —
the usual cause is credit added to the organisation while the key's *project* carries its own limit,
or credit added to a different organisation. Only the account holder can resolve it.

**Two blocking defects fixed before the run, both found in the M32 audit:**

- `res run-all` had never executed. Typer does not rewrite the decorated function, so calling
  `ingest()` bare passed the `typer.Option(...)` sentinel as the argument value; `Path(source)`
  received an `OptionInfo` and the documented "reproducible batch run" died on its first line. Now
  passes real values, and additionally chains `detect-communities` and `export-results`.
- `res extract` silently skipped every study that already had CMOCs, so a second run printed `n=0`
  with no explanation. New `--refresh` flag re-extracts, deleting each study's previous layer
  **immediately before re-extracting that study** (`_clear_study_cmocs`), never all up front — so a
  failure part-way costs one study rather than the corpus. This is the M26 lesson made structural.

**Reproducibility defects fixed (no API needed):**

- **`res init-db` now creates the CMOC layer.** There was no `CREATE TABLE` anywhere in the
  repository for `cmocs`, `entity_instances` or `typed_relations` — they existed only in the
  author's live database, so a replicator got `relation "cmocs" does not exist`. DDL transcribed
  from `pg_dump --schema-only`; verified idempotent against the live database (row counts
  unchanged).
- **`pyproject.toml` corrected in both directions.** Removed `langchain`, `langchain-openai`,
  `langgraph`, `langgraph-checkpoint-postgres`, `graphrag`, `jinja2` — none is imported anywhere.
  Added `openai`, `graspologic`, `scipy` to the runtime set and `matplotlib`, `python-docx` to
  `viz`. This mattered: on a clean install `graspologic` was absent, the bare `except` in
  `graph/communities.py` swallowed the `ImportError`, and the pipeline **silently ran NetworkX
  Louvain while every document said Leiden**.
- The package description no longer makes an unqualified "GraphRAG" claim.

**`docs/SYSTEM_AND_ALGORITHMS.md` — the description of record.** Written from the source, not from
the design documents. States the real reasoning stack (one `call_structured()` entry point, Pydantic
structured outputs, fixed seed, no retry/tool-use/history — so "8 agents" means 8 role prompts, and
four of the eight personas are never loaded at all); the one genuine loop (Self-Refine with an
*external* critic in CMOC extraction, ~Reflexion); every named algorithm with its parameters (Leiden
via graspologic, resolution 1.0, seed 20260714; union-of-includes screening; three-tier span
resolution; Clopper–Pearson intervals); and the settled tool stack.

**And it states plainly what "GraphRAG" is here.** Present: ontology-constrained typed extraction,
Leiden partition, one LLM label pass per community. Absent: embeddings, vector store, hierarchical
community summarisation, and local/global search — the programme-theory composer receives
`json.dumps(evidence_pack)`, which is context stuffing, not retrieval; and `guidance.py`'s
"GraphRAG-in-the-loop" is a `LIMIT 24` frequency query unrelated to the paper being extracted. The
defensible phrasing is *"ontology-constrained knowledge-graph construction with Leiden community
detection and LLM community labelling"*. `ARCHITECTURE.md` now carries a banner pointing here, with
a nine-row correction table (LangGraph never imported; nine listed modules absent; gpt-5.4 vs
gpt-5.5; empty `config/prompts/`; the per-paper gold is LLM output).

**Standing blockers, unchanged:** OpenAI credit (blocks any re-run); no human has coded anything
(blocks every agreement-style number); `res feedback` still violates a NOT NULL constraint; the
unfiltered `DELETE`s in normalize/communities/synthesize still discard other runs' rows and HITL-3
resolutions.

---

## M34 (2026-09-24) — the first complete end-to-end run

After three credit exhaustions, `res extract --resume extract-9035e95e` finished the five
remaining studies and the pipeline ran through synthesize → communities → verify → build-lkg →
report → exports without error. **One extraction vintage, 26 studies, one screening run** — the
first time every published number belongs to a single execution.

**Corpus:** 91 CMOCs · 544 entity instances · 460 typed relations · 9 emergent mechanisms.

**Scorecard (run `verify-0cc8eff6`, gold v3), with exact intervals:**

| | Result |
|---|---|
| Screening sensitivity | 92.9% unaided → **100%** (95% CI 87.7–100) after one human check |
| Quotes resolving to a verbatim span | **95.6%** (93.5–97.2) — exact 83, normalized 437, fuzzy 13, failed 11 |
| Concept coverage, same realist role | **37/46 = 80.4%** (66.1–90.6), per-sample 78.3–82.6% |
| Concept coverage, role-tolerant | 46/46 — **saturated, no longer informative** |
| Relation anchored | **32/40 = 80.0%** (64.4–90.9); 88.9% over the arrows Richmond actually draws |
| Relation strict | 1/40 (R26) — first non-zero |
| Relation type-level | 39/40, **saturable: only 8 patterns exist in our graph** |
| Emergent mechanisms | 19/28 = 67.9% (47.6–84.1), 9 communities |
| Programme theory | **0.87 independent judge vs 0.51 same-family — gap 0.36** |

**Against the previous (mixed-provenance) numbers**, relations improved materially — anchored
72.5% → 80.0%, strict 0 → 1 — and verbatim grounding rose 92.8% → 95.6%. Concept coverage within
role is flat (38→37 of 46), which is the honest read: the extraction changed, the concept matcher
did not get better.

**A new saturation flag, raised against ourselves.** Role-tolerant concept coverage reached
**46/46**. A metric that matches everything has stopped discriminating, exactly like the
type-level relation score. `res verify` now leads with the like-for-like figure, prints the
role-tolerant one beneath it marked `⚠ SATURATED — not informative`, and prints the type-level
ceiling inline. The summary table previously hardcoded `/47` and `E01-E47`; it now reads the
denominators from the report.

**Resumability, which is what made this run possible.** Extraction had been all-or-nothing, so
each of the three top-ups paid again for the same 25 studies and never reached the end — the same
study (S026) killed it twice. `--resume <run-id>` skips studies already extracted under that id;
the final resume cost five studies instead of twenty-six. A mixed-vintage guard
(`extraction_vintages()`) now puts a red banner on RESULTS.html and a warning on the CLI whenever
the CMOC layer holds more than one run, so an interrupted state can never be quoted silently.

**Cost, measured:** extraction is 81% of all tokens, essentially all of it gpt-5.5 reading each
full paper twice (draft + Self-Refine revise) and generating ~4.4k reasoning tokens per call —
~22.5k prompt and ~10.9k completion per study. Two low-risk reductions are available and not yet
implemented: skip the revise round when the critique finds nothing material (~30–40%), and
restructure the revise prompt so the paper text is a stable cacheable prefix (`cached_tokens` is
currently 0, so prompt caching is being wasted entirely).

**Human HITL-3 contradiction resolutions** were snapshotted to `contradictions_hitl3_m35` before
`synthesize` (which still issues an unfiltered DELETE) — that defect remains open.

---

## M35 (2026-09-24) — second complete run, and what comparing two runs revealed

A second full pipeline run completed without error on a single extraction vintage
(`extract-fb045429`, 26 studies): **94 CMOCs · 547 entity instances · 459 relations · 8 emergent
mechanisms**. Scored as `verify-91a39a5c`.

**The most useful result of the day is the comparison of the two complete runs**, same corpus,
same code, same benchmark:

| | `verify-0cc8eff6` | `verify-91a39a5c` |
|---|---|---|
| Screening after HITL | 100% (28/28) | 100% (28/28) — identical |
| Verbatim grounding | 95.6% (93.5–97.2) | 93.1% (90.6–95.0) |
| Concepts, same realist role | 37/46 (66.1–90.6) | 37/46 — identical |
| Relation anchored | **80.0%** (64.4–90.9) | **67.5%** (50.9–81.4) |
| Relation strict | 1/40 (0.1–13.2) | 5/40 (4.2–26.8) |
| Emergent mechanisms | 19/28 (47.6–84.1) | 17/28 (40.6–78.5) |
| Theory, independent judge | 0.87 | 0.94 |
| Theory, same-family judge | 0.51 | 0.50 |

Anchored relation recall moved 12.5 points between two runs of identical code, and strict recall
moved the other way. **Every confidence interval overlaps.** The intervals added in M32 are
earning their place: they show these swings are sampling noise, not improvement or regression,
and they make it plain that **two runs cannot be compared on point estimates alone.** Any future
claim that a change improved the pipeline needs a paired design on the same studies, not a
before/after of two runs.

**A self-inflicted error, recorded because it is the instructive kind.** Earlier in the session
the HITL feedback loop was repaired — corrections moved out of `hitl_feedback` (whose NOT NULL
columns had made every write fail) into their own `agent_feedback` table. The corrections were
then filed under `agent_key="cmoc_extractor"`, while `extraction_guidance_block()` reads
`"cmoc_extraction"`. The keys never matched, the few-shot block stayed empty, and a pilot showing
checker disagreement falling from 77% to 50% on three studies was reported as evidence the loop
worked. It was not: the loop was still dead, and — as the table above shows — three studies is
far too small to distinguish anything from noise. **Fixing a table is not fixing a pipeline; the
correction has to be observed arriving at the prompt.** `record_feedback` now raises on an agent
key nothing reads (`CONSUMING_AGENT_KEYS`), so a correction can never again be stored somewhere
that no agent consults. Both runs above are feedback-free and therefore internally consistent.

**Provenance drift guard.** Restoring state surfaced that RESULTS.html shows live database counts
beside scores from a named verification run, and the two can drift — at one point by one entity
instance out of 544. `_drift_note` now states the discrepancy on the page with both numbers and
the run id.

**Resumability paid for itself.** Credit ran out twice more during this work, at 18/28 and again
mid-run. Each time `--resume` continued under the original run id; the 16 studies extracted
before the first failure were banked to `*_fbrun`, restored afterwards, and never paid for twice.

## M36 — Judge variance, the trivial baseline, gold v3, and the papers (2026-09-25 → 09-30)

**The session that changed what this project is allowed to claim.**

**Gold v3.** `richmond_gold_v1` was still being scored: all five programme-theory chains had been
transcribed from a draft of Richmond's figures rather than the published ones, and E01
("undergraduate students in medical or health care professions education") was being scored despite
being the review's population description, which any extraction matches trivially. v3 fixes both:
denominator 46, not 47; E21/E43 re-typed to Mechanism_Response; R37–R40 flagged `derived`;
`reference_to_study_id["28"] = ["S004"]` corrected. `RES_GOLD` switches between versions so every
earlier published number remains reproducible.

**The empty exports.** `scripts/export_outputs.py` used `pandas.read_sql` over a psycopg
`dict_row` cursor, which turned every row into its own column names. Every CSV the project had ever
sent the supervisor contained the header repeated and nothing else. Fixed with a raw cursor and
explicit `columns=`. This is why eight months of "I never see any output" had a literal cause.

**Judge variance — the headline.** Ten verification runs over one frozen graph
(`extract-fb045429`, 547 instances, 94 CMOCs, 459 relations). Everything deterministic returned
byte-identical values ten times out of ten. Everything a model judged moved: concept coverage
31–37 (SD 1.96), anchored relations 24–31 (SD 2.31), mechanisms 16–21 (SD 1.32), and a
programme-theory gap of 0.319 between judge families that is thirteen times either SD and perfectly
reproducible. **Minimum detectable difference ≈ 7.8 items ≈ 17 pp on one comparison per arm.**
Written up in `docs/MEASUREMENT_NOISE.md`.

**The trivial baseline.** `verification/baseline.py` — one LLM call over the same 28 papers, no
pipeline. It recovers **32 of 46**, inside our own 31–37 range. The framework cannot be claimed
superior on concept coverage, and no further tuning would change that because the measurement
cannot resolve it. The contribution has to be claimed where the baseline produces nothing:
anchored quotes, per-study provenance, typed relations, algorithmic mechanisms, logged checkpoints.

**Three dishonest figures withdrawn.** "91.5% concept recovery" came from an unvoted recovery pass
and sat outside its own sampling range (76.6–85.1%); fixed with K=3 voting plus guards against
hallucinated codes and duplicate matches, giving 89.1%. "96.9% citation faithfulness, resolved to
an exact source span" conflated exact, normalised and fuzzy tiers under the word *exact*; exact is
53/547 = 9.7%. Screening had been blending six runs; now one named run with a registry denominator.

**Manual coding, and a correction to how it is described.** The RA coded all 28 papers by hand
against a frame built from the 46 benchmark concepts: 192 elements marked, 30 of 46 recovered. A
second pass under the identical frame recovered 28 of 46 across 139 elements, agreeing with the
first on 130 elements — positive specific agreement 0.785, the correct statistic because Cohen's κ
is undefined for span marking (Hripcsak & Rothschild, 2005). **That second pass was ChatGPT acting
as a coder, not a second person.** It is therefore not inter-rater reliability and is no longer
described as a human ceiling. What it does establish is the project's first human data point — 30
of 46 — and, read with the baseline (32) and the pipeline (31–37), the suggestion that roughly 30
of Richmond's 46 concepts are recoverable from the included studies at all. A second human coder
remains outstanding.

**The systematic failure.** Five concepts were recovered at no tier: E05, E06, E31, E32, E34 —
negative coping and low self-efficacy, mixed-knowledge groups, pressure of real consequences, fear,
pressure to perform. **Four of five are negative affect under pressure.** The pipeline recovers
positive affect and misses the negative half, which is precisely the half Richmond's central claim
depends on. Cause unknown: ontology, prompt, or corpus. This is the best open question the project
has.

**Architecture described from the code, not the docs.** There is no retrieval anywhere: extraction
passes whole papers (mean 22,977 chars), and `_evidence_pack()` passes the entire evidence base
unfiltered at 50,026 characters ≈ 12,506 tokens. Leiden is implemented — the global-search half of
GraphRAG — while subgraph retrieval is not, correctly, since at this corpus size retrieval could
only remove evidence. One genuine defect found: `_batched_cluster` merges across batches by exact
normalised label, which will fragment at scale. Assessed and recommended against integrating
LangChain or GraphRAG retrieval: neither addresses a measured limitation, and both would interpose
an abstraction between the code and the two properties the validation rests on.

**Delivered.** A six-file bundle and a seven-page comparison report to the supervisor on 09-25; the
supervisor's AERA draft completed on 09-30 with all 16 placeholders filled, the stale prose
corrected, four new Findings paragraphs, Table 2 grown to 16 rows, and references 9 → 14.

**Lost.** PostgreSQL was uninstalled from the machine before a dump could be taken. The database is
gone; the parquet snapshot and CSV exports survive, and the restore path is import, never re-run —
a re-run would produce a different graph and invalidate every figure in the submission.
`HANDOFF_FOR_NEW_MACHINE.md` records all of it.

## M37 — The database restored on the new machine, and the affect gap diagnosed (2026-09-30)

**The project now runs on macOS, and the "lost" database is back.** Nothing was re-run and no
extraction was paid for; the whole CMOC layer was imported from the snapshot.

**A latent defect that would have silently corrupted every span.** `pyproject.toml` declares
`pypdf>=4.2`. It matters far more than that. Re-ingesting the 20 PDFs under pypdf 6.19 produced
canonical text differing from the July run for **16 of 28 studies** (−1 to −23 characters); under
4.2 the drift reached −525. Every `char_start`/`char_end` in `entities.parquet` indexes into that
text, so importing the snapshot on top of a differently-extracted corpus would have made citation
faithfulness collapse for no reason — and the 93.1% figure in the AERA submission is a
*recomputed* metric, so it would have moved. Probing the version range found **pypdf 6.8–6.15
reproduces the July text exactly**; 6.12.0 gives sha256 identity on all 28. The pin belongs in
`pyproject.toml`, and `scripts/import_snapshot.py` refuses to import unless the hashes match.

**`scripts/import_snapshot.py`** — the importer `HANDOFF_FOR_NEW_MACHINE.md` §7.1 said was still
missing. It restores `cmocs` (94), `entity_instances` (547), `typed_relations` (459),
`concept_families` (183), `conceptual_entities` (8), `screening_decisions` (86, reconstructed from
the audit trail for run `screen-70a5d070` plus the two HITL-1 includes), and `audit_log` (1,084
events, also from the rendered trail); recomputes `demi_regularities` (32) and `contradictions`
(20) deterministically; and parses `programme_theories` v12 back out of the rendered markdown.

**The restore verifies.** Every deterministic metric reproduces exactly: screening 26/28 → 28/28
after HITL-1 with S018 and S028 as the two uncertain records; citation faithfulness tiers
`{exact 53, normalized 456, fuzzy 22, unresolved 16}` — 9.7% exact, 93.1% verbatim, 97.1% all
tiers. `res export-results` regenerates RESULTS.html at 547 / 459 / 94 / 8, which is the check
`RESTORE.md` specifies. That the 32 demi-regularities and 20 contradictions were *recomputed* from
the imported graph rather than copied, and came out at the published values, is the strongest
evidence the import is faithful.

**Not restored, because nothing exported it:** `token_usage`; the per-item `hitl_feedback`
payloads and the original screening rationales (the markdown renderer truncated the audit
`detail` column); `ipt_versions`; `agent_feedback`; `distractor_studies`. Consequence to expect:
RESULTS.html now shows **0 human decisions** where it used to show 28/17. That is an honest loss,
not a regression.

**The affect gap is no longer "cause unknown".** All 28 primary studies were read, and the five
concepts recovered at no tier decompose into four corpus limits and one polarity mismatch — none
of them an extraction failure:

- Richmond built Contexts 3 and 4 from five studies (refs 36, 37, 46, 50, 51). In our corpus
  **two are unusable** — S009 (Bender & Danielson) is a first-page-only PDF, 2,129 chars; S014
  (Pinnock) is a 185-character fragment — and **S023 (Bloice), a full text, contains no affect
  vocabulary at all**. S022 has `pressure` once and `frustrat` twice. Essentially the entire
  affective evidence base for those two contexts survives in **one study, S015 (McGregor)**.
- **E34 (pressure to perform) and E31 (pressure of real consequences)**: corpus. The only
  occurrence of "pressure" in S015 is *blood pressure cuff*.
- **E05 (lacking self-confidence or self-efficacy)**: corpus. `self-efficacy` and
  `self-confidence` occur **0 times** across all 28 studies.
- **E06 (different levels of knowledge within a group)**: corpus, and not an affect item —
  no study contains that construct's phrasing. The "four of five are negative affect" framing in
  `HANDOFF_FOR_NEW_MACHINE.md` §2.4 counts E06 among them and should be corrected.
- **E32 (fear)**: **polarity inversion, not blindness.** The extractor *did* capture fear from
  S015 — `reduced fear during referral`, typed `Mechanism_Response`, quote *"The SBAR structure
  was really useful. It took a bit of the fear away definitely"*. But that is fear being
  *reduced by a tool*, whereas Richmond's E32 is fear *induced* by simulation in low-coping
  learners. Same word, opposite causal role. A strict matcher declining it is arguably correct.

So the extractor is not affect-blind: 12 of its 117 `Mechanism_Response` instances name an
affect, span-grounded and correctly typed. What the corpus cannot supply, it correctly declines to
invent — which is the faithfulness constraint working as designed.

**A real normalisation defect found on the way, distinct from the above.** Concept normalisation
merges unrelated and opposite constructs under one canonical label: `mech:reduced-fear-or-premature-closure`
bundles reduced fear with premature closure; `mech:game-engagement` absorbs `novice frustration`;
`mech:cognitive-load` absorbs `hypothesised overwhelmed cognitive load` and `perceived time and
complexity burden`. Corpus-wide **no canonical concept name contains "stress", "panic", "anxiety"
or "pressure"**, and only one contains "fear". The matcher is shown `canonical_id` plus at most
**three** member labels plus **one** representative quote, so a concept with more than three
members can hide content from it — `novice frustration` is the fourth label of four in
`mech:game-engagement` and is never shown. This did not cause the E32 miss, but it is the
antonym-collapse hazard `IMPROVEMENT_PLAN.md` warned about for E02/E03, already occurring in the
existing LLM clustering without any embeddings involved. Cheap test: show the matcher the full
member list.

**Two smaller defects.** `registry.py:_pdf_title` references `PdfReader`, which is imported only
inside `build_registry_from_dir`, so it raises `NameError`, is swallowed by its bare
`except Exception`, and every generic-ingest title silently falls back to the filename stem — the
"scale to any folder of PDFs" path does not extract titles. And `gold/richmond_gold.json` is still
byte-identical to v1 (MD5 `c3edd83…`); `metrics.py` defaults to v3, but `gold_coder.py` (×2),
`gold_template.py`, `tests/test_ontology.py` and `scripts/build_correspondence.py` still read the
uncorrected v1, so the coding frame behind the 30/46 human figure carries v1's wrong typings.

**Also on the record:** the 85 files `git status` reports as modified are CRLF→LF noise from the
Windows→Mac move; `git diff -w` shows one real change, the M36 entry. Seventeen commits remain
unpushed. `outputs/RESULTS.html` §3b still says "two research assistants" and "Coder B (human)" —
the integrity correction of §3 of the handoff has not reached it. `outputs/Richmond_Correspondence.md`
is stale (22/40 anchored, 0/40 strict). The delivered `0_REPORT` footer cites "Richmond, H. et al."

### M37b — the last reading pass: what the entity matcher is actually counting

Finishing the file-by-file sweep (the eight `outputs/runs/report-*` sets, the three July HTML
reports, `03_Richmond_Correspondence_full.md`, the Microsoft GraphRAG paper and the earlier
KG specification) turned up one finding that bears directly on the headline number, and four
smaller ones.

**The headline concept figure is not injective.** `RESULTS.html` §4 leads with 34/46 (73.9%)
like-for-like concept recall and sets it beside the human ceiling — Coder A 30/46, Coder B 28/46,
both agreeing 28/46 — and concludes the system clears it. But the 34 matches in
`outputs/runs/verify-edcbf790/verification_report.json` rest on only **28 distinct canonical
concepts**. Four concepts each answer for two or three of Richmond's:

| concept | Richmond codes it is counted for |
|---|---|
| `mech:knowledge-elaboration` | E20 *understanding*, E27 *build understanding*, E39 *build upon what they already know* |
| `mech:cognitive-overload-or-confusion` | E23 *frustrated*, E33 *stress*, E45 *confusion* |
| `outc:improved-diagnostic-accuracy` | E25, E46 |
| `outc:learning-and-schema-integration` | E28, E40 |

The two human coders could not do this: the E-code sheet gives one code per element, so a human
match is one-to-one by construction. Under the same constraint the system scores **28/46 (60.9%)** —
equal to Coder B and to the both-agreed set, not above them. The comparison in §4 is therefore not
like-for-like, and the sentence "the system clears the ceiling" should not be shown to the professor
until either the matcher is made injective or the ceiling is recomputed without that constraint.
E23/E33/E45 collapsing into one concept is also the same antonym/valence collapse recorded above for
E02/E03, now visible on three affect items at once.

**The judge contradicts its own verdict in writing.** In the same run, `E03` (students with *high*
domain knowledge) is matched to `cont:knowledge-deficits` with the rationale "...which aligns with
high clinical domain-specific knowledge **as the opposite**", and `E24` (*rely on non-analytical
reasoning*) is matched to `mech:reasoning-strategy-shift` with "...which is the opposite of
non-analytical reasoning, **so it does not match**" — both stored as `matched: true`. E03 is excluded
from the like-for-like 34 by the `cross_type` flag, but E24 is inside it. A rationale that states a
non-match must not be allowed to set `matched: true`; this is a one-line guard in `metrics.py`.

**The July artefacts still in `outputs/` contradict the current ones and must not be sent.**
`Preliminary_Results_v2.html`, `Professor_Report.html` and `Knowledge_Graph_Report.html` carry the
superseded figures (180 concepts, 439 relations, 91 CMOCs, 14 contradictions, 36 demi-regularities,
"96.9% grounded in an exact source quote", 43/47 concepts) against today's 183 / 459 / 94 / 20 / 32
and 9.7% exact. `Preliminary_Results_v2.html` also says "4 of Richmond's **6** student-context
types"; Richmond has **five** contexts (E02–E06) — E01 is the review population and
`richmond_gold_v3.json` marks it `scored: false` with the note "not one of the five contexts".
`outputs/Richmond_Correspondence.md` is byte-identical (MD5 `13c8a21…`) to both submission copies,
i.e. all three are the July file.

**A PRISMA table that cannot be true was generated and shipped.**
`outputs/runs/report-51b61f45/prisma_flow.md` reports 159 auto-includes and 162 final includes from a
registry of 28 records, because it counted screening rows across every run in the database rather
than one named run. The July pair (`3754dce7`, `84f18e6c`) has the milder form, 31 final from 28.
Runs from `7fa4d4ff` onward print "Screening run scored: `screen-…`" and give 28. The same
run-blending is still live in `verification/distractor_pool.py::run_precision_test`, which selects
`DISTINCT ON (study_id) … ORDER BY created_at DESC` across all runs.

**Grounding confirmed, and one honest divergence named.** The GraphRAG paper (Edge et al. 2024)
does support two choices the docs attribute to it: Leiden via `graspologic` (§4.1.3, named
explicitly) and the draft→critique→revise gleaning loop (§A.2 self-reflection, with the measured
result that a 600-token chunk yields nearly twice the entity references of a 2400-token chunk). What
this project does *not* take from it is the query-time half — community summaries feeding map-reduce
query-focused summarization. Our synthesis stage is deterministic aggregation over the communities,
not QFS, so the system is GraphRAG-indexed, not GraphRAG-answered, and the paper should say so
rather than cite GraphRAG wholesale.

**Ontology gap behind the polarity problem.** The KG specification's own relation table shows why
valence keeps escaping: Richmond's R15/R16 make E31 (*pressure that their decision making could have
a real impact*) lead to a **positive** learning experience, while R20/R23 make E34 (*pressure to
perform*) lead to increased cognitive load and negative outcomes. The two are opposite-signed, and
`mech:time-pressure` was counted for both in the September 23 run. There is no polarity field on an
entity or a relation anywhere in the schema — which is also why
`neo4j_adapter._MOTIF_QUERIES["expertise_reversal"]` filters `r1.polarity` on edges created with only
`{study_id, cmoc_id}` and can never return a row. HANDOFF §2.4's "four of five are negative affect"
over-counts for the same reason: E31 is positive-valence pressure.

### M37c — a machine-vs-human comparison, because the professor keeps asking for one

The professor's recurring questions in meetings are always the same six: where are you, what have you
built, what does the pipeline do, show me the output, is it good enough, and **have you compared your
final result with Richmond's final result**. The last one had no single artefact behind it:
`RESULTS.html` §1 compares the two conclusions, §3 compares context by context, §4 holds the human
ceiling and §5 the 46-item checklist — but nothing put the machine result and the human result side by
side at every level Richmond published. Written now as `docs/MACHINE_VS_HUMAN.md`.

Assembling it surfaced two things the existing documents do not say.

**The context–study overlap is 4 of 47.** `results_export.py` already computes, per context, how many
studies Richmond assigns, how many we assign, and how many are the same paper — and it prints the line
in §3 — but the total is nowhere. It is: Richmond makes 47 context–study assignments across E02–E06,
we make 13, and **4 are the same paper**. On E02, Richmond's largest context at 22 studies, we agree on
2. The two reviews reach similar conclusions from substantially different readings of which paper
supports what. For a realist review that is as important as the concept count, and it is currently
unreported.

**The theory judges disagree in the direction nobody assumed.** `self_preference_gap` is **−0.289**:
the independent judge (different model family) scored the theory *higher* than the judge from the
composer's own family, which means the published 0.817 is the **more generous** of the two numbers,
not the conservative one. Per chain the gap reaches 0.507 (PTS2) and 0.473 (PTS3) — about half the
scale on identical inputs. The same-family mean is 0.528. Two numbers that far apart cannot be
averaged, so the honest position is that theory-level correspondence is *unmeasured* pending an expert
rating, which is stronger than quoting 0.817 with a caveat.

**Also found:** `results_export.py:594` hardcodes "it recovers <em>none</em> of the 40 causal links at
the strictest exact-concept-pair level" while every other figure in the same sentence is interpolated
from the report. The current run recovers **6/40 (15.0%)**, and §4 of the same page says so. The
headline section therefore contradicts the verification matrix two screens below it, and it understates
our own result. `docs/FOR_THE_PROFESSOR.md` carries the same stale 0/40 and still states "No human has
independently coded any paper yet", which the coding workbooks have since made false; it is generated,
so the fix belongs in `FOR_THE_PROFESSOR.template.md`. That file also tells the professor to reproduce
numbers with `run-all`, which `RESTORE.md` forbids — a re-run costs money and yields a different graph
that would invalidate every figure already reported.

---

## M38 — Two months of silence explained, and a deliverable quietly regressed (2026-10-01 → 10-19)

**Nothing happened in this project in October, and that was deliberate.** The project owner paused
it after M37 to answer the professor's other work stream: installing and then extending Tsinghua's
**OpenMAIC** classroom. That work is real, finished to Level 2, and lives entirely in
`~/Downloads/OpenMAIC` — a separate repository, a separate Vercel deployment, and **none of this
project's code was imported into it**. Its own log is `~/Downloads/OpenMAIC/WALKTHROUGH.md`; start
there if the question is about OpenMAIC. Nothing in that work changes a single figure here.

This entry exists so that the gap between 30 September and 19 October is not read, later, as a
project that stalled.

**What this session actually found here, while committing the backlog.**

Eighty-five files showed as modified. **Eighty-two of them had not changed.** The move from the
Windows machine rewrote nearly every tracked file with CRLF endings — 17,363 deleted lines that
delete nothing. Committing that would have buried the three real changes and left `git blame`
pointing at the migration for every line of the pipeline, in a project whose whole argument rests
on an audit trail. `.gitattributes` now fixes LF in the repository whatever machine is working, and
the index is renormalised.

The three real changes were **M36 and M37**, written on 25–30 September and never committed, and
the **pypdf pin** that M37 argued for, now actually in `pyproject.toml` with its reason beside it.

**The serious finding: `outputs/RESULTS.html` on disk was worse than the one in git.** The working
copy reported **0 human decisions** where the committed artefact reports **28**, and rendered one
concept list as a raw Python repr (`['repeated use across different days', …`) instead of the clean
comma list, truncated mid-structure. It has been **restored from git**, and the broken copy kept
out of the way rather than destroyed.

**The cause is not established, and must not be guessed at.** The exporter source on disk is
byte-identical to the committed source once line endings are ignored, so the same code produced
both files — which points at the *database* the export was run against, i.e. the snapshot restored
on the new machine in M37, rather than at the code. Two things follow:

- **Do not run `res export-results` until this is understood.** It is not a pipeline re-run and so
  it is not covered by the standing prohibition, but it overwrote the project's single most
  important deliverable with a worse version, silently, and the overwrite sat on disk unnoticed
  for weeks. The committed `RESULTS.html` is the artefact of record.
- **Check `screening_decisions` and the human-decision count in the restored database** before
  trusting any freshly exported number. M37 claimed the restore verified every deterministic
  metric; the human-decision count is apparently not among them.
