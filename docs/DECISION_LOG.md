# DECISION LOG

Append-only record of significant decisions (architecture, technology, ontology, methodology)
with date, the decision, the rationale, and who approved it. Keeps future sessions from silently
re-litigating settled choices or forgetting why something was chosen.

Format:
```
## YYYY-MM-DD — <short title>
- Decision:
- Rationale (grounded in which sources / research):
- Approved by:
- Supersedes / relates to:
```

---

## 2026-07-14 — Project restarted fresh in `Realist Evidence Synthesis V2`
- Decision: rebuild the project from scratch in V2 rather than continue the old
  `LLM-Knowledge-Graph`; use the old project as reference only.
- Rationale: RA found the old (Cursor/Antigravity-built) version confusing and not meeting the
  professor's requirements; wants a clean, professional, research-grounded rebuild.
- Approved by: Duy Nguyen (RA).

## 2026-07-14 — Working process: research-first, architecture approval before build
- Decision: Claude finishes reading (May 28 meeting, remaining professor PDFs, Richmond paper) +
  does SOTA web research, then presents a grounded ARCHITECTURE PROPOSAL for RA approval before
  writing pipeline code.
- Rationale: RA's choice; also matches the professor's repeated "architecture first" guidance.
- Approved by: Duy Nguyen (RA).

## 2026-07-14 — Orchestration + knowledge stack
- Decision: use **LangChain + LangGraph** for orchestration and **Microsoft GraphRAG** (open-source)
  for the Literature Knowledge Graph. "Microsoft Graph" (the M365 SharePoint/Teams API) is a
  DIFFERENT thing — it is optional; implement a local provenance layer described as
  "MS-Graph-compatible", upgradeable to real M365 later only if the professor insists.
- Rationale: RA confirmed LangChain+LangGraph; clarified the GraphRAG vs Graph confusion. M365 is
  overkill for a 28-PDF local verification prototype; the science lives in GraphRAG + the LKG.
- Approved by: Duy Nguyen (RA) — "use whatever is useful/optimal; use both if needed."

## 2026-07-14 — LLM provisioning
- Decision: RA provides an OpenAI API key; Claude selects models per task to balance cost/quality
  (e.g. cheaper models for screening/dedup, stronger models for CMOC extraction/synthesis).
  Concrete model choices to be proposed in the architecture doc BEFORE spending API credit.
- Approved by: Duy Nguyen (RA).

## 2026-07-14 — Architecture v1.0 adopted (seven grounded decisions)
- Decision: adopt `docs/ARCHITECTURE.md` v1.0 — D1 constrained typed extraction + GraphRAG BYOG;
  D2 novelty = first agentic realist-synthesis framework; D3 hybrid ontology (5 fixed entity
  types, 5 fixed predicates with domain/range constraints, emergent instances, E-code mapping
  only at verification, nanopub-style provenance); D4 tiered models (gpt-5.4-mini screening +
  gpt-4.1-mini second vote; gpt-5.4 extraction/synthesis; text-embedding-3-small; multi-vendor
  ensemble deferred to sensitivity analysis); D5 storage = Postgres (state/audit SoT) + parquet
  (canonical LKG artifact) + Neo4j (derived query/viz); D6 verification = fresh independent
  human per-paper CMOC gold (2 coders, Cohen's κ), AI-adjudicated xlsx demoted to suggestion
  aid; D7 HITL via LangGraph interrupt()/Command(resume) + AsyncPostgresSaver, feedback-to-
  few-shot loop.
- Rationale: each decision cites `docs/research/SOTA_REPORT.md` and/or professor documents.
- Approved by: Duy Nguyen (RA) — granted full build authority ("bạn cứ làm rồi chạy luôn",
  2026-07-14); architecture documented as the required record.

## 2026-07-14 — New standing requirements from the RA
- WALKTHROUGH.md: append a milestone entry (what/why/strengths/limitations) for every work
  session — layman-readable reporting is part of definition-of-done.
- Output design: system must emit the SAME artifact genres as Richmond's paper for 1:1
  human-vs-machine comparison (see ARCHITECTURE §6).
- Credentials: PostgreSQL password provided and stored in .env; Neo4j installed but not yet
  configured (set up during Phase 0/5). Both the OpenAI key and Postgres password were pasted
  in chat → rotate after the project stabilizes.

## 2026-07-14 — Model upgrade for quality-critical stages
- Decision: extraction and synthesis tiers → **gpt-5.5** (strongest reasoning tier available on
  the key); screening/verifier/normalization stay on mini tiers for cost. `llm.py` now sends
  `temperature` only when a tier declares one (gpt-5.5 accepts only the default) and always
  sends a fixed `seed` for best-effort reproducibility. Extraction prompt bumped to v2.0
  (mandatory affective Mechanism_Response capture, explicit negative pathways, 2-5 CMOCs).
- Rationale: RA directive to use the strongest-reasoning model while keeping cost optimal;
  first-pass verification showed the extractor under-captured affective responses and negative
  chains (PTS3/PTS4 weak) and relation coverage was low. Clarification: "best model" refers to
  the OpenAI API tier for the pipeline AND (separately) the Claude model the assistant runs on
  (Fable 5 vs Opus 4.8) — the latter is switched by the RA via /model, not by the assistant.
- Approved by: Duy Nguyen (RA).

## 2026-07-14 — Relation coverage measured at two levels
- Decision: report BOTH strict (exact concept match on both endpoints) AND type-level (predicate
  links an entity of the gold subject-type to one of the gold object-type) relation recovery,
  clearly labelled, never conflated. Rationale: strict recall is upper-bounded by entity-recall²
  and understates whether the causal *pattern* was recovered — the methodologically appropriate
  question for realist synthesis. Not metric-gaming: both numbers are always shown.

## (still-pending decisions)
- Neo4j initial password/setup (do during scaffold).
- Second human coder for per-paper gold standard (RA to arrange; professor?).
- Budget ceiling per full pipeline run (set after 3-paper pilot).

## 2026-11-18 — Three scope decisions for the emotion review, taken rather than referred
- **Decision 1: STEM is a context dimension, not an inclusion filter.** 51 of 1,088
  higher-education records are engineering, computing or natural sciences. Rationale: a
  realist review needs enough studies per configuration for a pattern to repeat, and 51
  before screening is ~10–20 after it — the scale at which this project already measured
  all 32 of Richmond's apparent recurring patterns failing a permutation test. Realist
  synthesis treats context as a variable, so the answerable question is which mechanisms
  fire differently inside STEM, not what works in STEM. **Reverses if** screening leaves
  40+ eligible STEM studies.
- **Decision 2: organise the synthesis by Gross's five regulation families, not by
  intervention name.** Three of the professor's five named interventions return 7, 6 and
  17 records while mindfulness, unnamed, returns 291. Rationale: regrouped by mechanism,
  "emotional awareness prompts" (6) and mindfulness (291) are the same family —
  attentional deployment — so the scarcity is largely a vocabulary gap, not an evidence
  gap, and that mismatch between practitioner and research vocabulary is itself
  reportable. **Reverses if** the families do not discriminate at extraction.
- **Decision 3: anxiety is the spine; boredom is a deliberate contrast case.** Anxiety is
  578 of 678 emotion-tagged records; the other eight sit at 11–79. Rationale: eight
  emotions at that scale cannot each support a programme theory, but boredom is an
  *activity* emotion in Pekrun's terms where anxiety is an *outcome* emotion, which makes
  "do anxiety's mechanisms work on boredom?" answerable and genuinely realist.
  **Reverses if** screening leaves fewer than ~20 eligible boredom studies.
- **Why taken rather than referred.** The professor's 2026-10-30 §5 asks for judgment on
  routine decisions with documentation, and for contact on important research directions.
  These were initially filed as four questions for him. The RA's position, accepted here:
  a supervisor who is not doing the work cannot adjudicate a scope question better than
  the people holding the data, and referring an answerable question is passing work back.
  All three are stated in the handover with their evidence and their reversal threshold,
  so he can overturn any of them in a sentence.
- **Still referred, because it is not ours:** the ~$25 budget. Recommendation is $5.44 for
  screening first, since every figure above rests on dictionary term counts and screening
  is what turns all three reversal thresholds into answerable questions.
