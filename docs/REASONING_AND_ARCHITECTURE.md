# The System's Reasoning, Algorithm, and Architecture — with an honest audit

_What our core algorithm actually is, how the reasoning is organised, how it compares to the current
state of the art in agentic literature review, what we borrowed, and where it is still shallow. Written
so a reviewer can judge whether the machine "thinks" like an expert reviewer or merely runs steps._

---

## 1. The core algorithm, in one page

The pipeline is a **typed, provenance-first, human-supervised realist-synthesis algorithm**. Its unit
of reasoning is the **CMOC** (Context → Mechanism[resource → response] → Outcome), and its invariant is
that *no claim exists without a verbatim quote resolved to a source span*.

```
INPUT: a corpus of documents D, a review protocol P, a typed ontology O (5 entity + 5 relation types)

1  INGEST      for each d in D: text → provenance-bearing units u(char offsets)
2  SEED THEORY IPT ← hypotheses from public learning theory (never the benchmark's answers)   [HITL-0]
3  SCREEN      for each d: two independent models vote include/exclude on THEORY-RELEVANCE
               keep = union of includes; disagreements → human                                [HITL-1]
4  EXTRACT     for each included d:
   4a draft    CMOCs(d) ← LLM(d, O)                          # typed, quote-per-element
   4b reflect  issues ← Checker(draft)                       # independent 2nd model family
   4c revise   if issues: CMOCs(d) ← LLM(d, draft, issues)   # SELF-REFINE (new)
   4d verify   for each cmoc: support ← Verifier(cmoc)       # cross-critique score
   4e ground   resolve each quote → exact/near span; else FLAG (never fabricate)
   4f validate keep relation iff type(subject)×type(object) ∈ domain/range(predicate)
   4g check    Checker signs off / flags residuals → human                                    [HITL-2]
5  NORMALISE   cluster synonymous labels → canonical concepts → Richmond-granularity families
6  COMMUNITIES Leiden partition of the CMOC graph → emergent conceptual entities
7  SYNTHESISE  demi-regularities = CMOC motifs in ≥2 studies (pure graph query)
               contradictions   = same driver, opposite outcome → human                       [HITL-3]
8  THEORISE    programme theory ← LLM(demi-regularities, contradictions, communities, IPT)     [HITL-4]
9  RETRODUCE   re-read the weakest studies under the refined theory; repeat 4–8 until stable
OUTPUT: a typed knowledge graph + a five-context programme theory, every edge quote-grounded
EVALUATE (outside the loop): compare to the human benchmark; the answer key is never read by 1–9
```

**Why this shape.** Steps 5–7 are deliberately *deterministic graph/SQL operations, not LLM calls* —
so demi-regularities and contradictions are reproducible and auditable, and the LLM's judgement is
confined to where interpretation genuinely belongs (extraction, community labelling, theory prose).
This is the opposite of an "ask-the-LLM-everything" design and is what makes the output traceable.

## 2. Architecture

- **Orchestration:** a staged pipeline over a shared typed state; one stage's output is the next's input.
- **Agents (8):** IPT Manager · Screening Reviewers (×2, different families) · CMOC Extractor ·
  Faithfulness Verifier · Consistency Checker (different family) · Normaliser · Community Analyst ·
  Synthesis Composer. Each carries an embedded expert persona (`config/agents.yaml`). See
  `docs/SYSTEM_WORKFLOW.md`.
- **Data layer:** PostgreSQL = single source of truth; parquet LKG = canonical reproducible artifact;
  Neo4j = derived exploration. Every triple: `{study, unit, char span, quote, model, prompt version,
  confidence}`.
- **Human:** sovereign at five checkpoints (HITL-0…4).

## 3. Reasoning audit — vs the state of the art

We compared our reasoning to current agentic-review systems and adopted what fits.

| SOTA technique (source) | What it gives | In our system? |
|---|---|---|
| **Self-Refine / Reflexion** (Madaan 2023; Shinn 2023) — draft → self-critique → revise | fewer errors without retraining | **Adopted** (step 4a–4c): the Checker critiques the draft and the extractor revises *before* persisting — previously it only flagged for the human. |
| **Independent 2nd reviewer / different model family** (JAMIA cross-critique) | reduces shared blind spots | **Yes** — Checker is gpt-5.4 vs extractor gpt-5.5. |
| **Multi-agent debate** (Du 2023; many 2025) — agents argue to a better answer | higher factual accuracy | **Partial** — our critique→revise is one round of structured disagreement, not full multi-round debate. Multi-round is a candidate upgrade. |
| **Evidence-gather-then-answer** (PaperQA2, FutureHouse) — retrieve + relevance-score evidence before answering | superhuman citation precision | **Not yet** — the extractor reads the whole paper at once. A gather-score-then-extract front-end is a candidate upgrade. |
| **GraphRAG retrieval for synthesis** (Microsoft) | reasoning over connected evidence | **Partial** — synthesis reasons over the typed graph via SQL motifs + communities, but the theory composer is fed a JSON evidence pack, not retrieved subgraphs. |
| **Role-play + reasoning transparency** (LatteReview) | auditable per-agent rationale | **Yes** — personas + per-agent audit-log rationale. |

**Honest verdict on optimality.** The *structure* is sound and, for a realist review specifically,
arguably better-suited than a generic RAG-QA system: it keeps C/M/O typed and quote-grounded, it
surfaces contradictions instead of averaging them, and it now self-corrects. It is **not yet optimal**
in reasoning depth: the debate is single-round, there is no evidence-relevance front-end, and synthesis
does not do true GraphRAG subgraph retrieval. These are the next reasoning upgrades, in priority order.

## 4. What changed this iteration (grounded, not guessed)

1. **Self-Refine reflection loop** (step 4a–4c) — the biggest reasoning change: the independent
   reviewer's critique now *improves* each paper's coding before it is stored, mirroring how Richmond's
   second reviewer's feedback led the lead coder to revise (§2.2, L248-250) — and matching the
   Reflexion/Self-Refine result that self-correction beats one-shot.
2. **Sharper Resource/Response/Context boundary rule** — fixes the most-mistyped realist distinction
   (a supplied *thing* vs an internal *reaction* vs a pre-existing *condition*).

## 5. The next reasoning upgrades (ranked)

1. **Evidence-gather front-end** (PaperQA2-style): for each candidate configuration, retrieve and
   relevance-score the supporting passages before committing — should raise strict recovery and cut
   over-claims.
2. **Multi-round debate** on the hardest CMOCs (extractor vs checker, 2–3 turns) instead of one revise.
3. **GraphRAG retrieval in the theory composer**: feed retrieved subgraphs + community reports, not a
   flat JSON pack, so the theory is reasoned from connected evidence paths.

Sources consulted: Madaan et al., *Self-Refine* (2023); Shinn et al., *Reflexion* (2023); Du et al.,
*multi-agent debate* (2023); Rostam & Kojima, *LatteReview* (2025, arXiv:2501.05468); FutureHouse,
*PaperQA2* (2024); Hong et al., *MetaGPT* (ICLR 2024); Edge et al., *GraphRAG* (2024).

---

## 6. Research grounding — does the system reason like a human realist team?

This section answers the professor's second question: *does the machine perform the same analytic
operations, to the same quality bar, as Richmond's human reviewers?* It is grounded in the realist
methodology literature (not invented), and it states honestly where the design already conforms and
where it does not. A key finding from the literature scan: **no published study applies LLMs to CMOC
extraction or realist synthesis proper** — the nearest work is AI-assisted *searching* for a realist
review (BMC Med Res Methodol 2026) and LLM deductive *coding* of qualitative data. So the framework
is a genuine gap our RRE 2026 paper can claim, and its validation must borrow from the adjacent
LLM-qualitative-coding and realist-methodology literatures.

### 6.1 What counts as a *good* CMOC — the quality bar the system is held to

The realist literature converges on concrete criteria. The table maps each to the check in our
pipeline that enforces it (or flags where nothing does yet). "(auto)" = deterministic check;
"(LLM)" = model-judged; "(—)" = not enforced yet.

| Criterion for a faithful CMOC | Source | Enforced by |
|---|---|---|
| A CMOC is a causal *if-then proposition*, not a row of labels ("configurations not catalogues") | Pawson & Manzano-Santaella 2012 | `cmocs.narrative_statement` + typed relations (auto); orphan entities flaggable (—) |
| Mechanism = **resource + response** (M(Resource)+C→M(Reasoning)=O) | Dalkin et al. 2015 | ontology splits `Mechanism_Resource` / `Mechanism_Response`; PROVIDES→TRIGGERS chain (auto) |
| Mechanism ≠ intervention activity ("don't mislabel strategies as mechanisms") | RAMESES II 2017; Pawson & Manzano 2012 | domain/range validation (auto); low Intervention↔Mechanism-Response overlap check (partial) |
| Context *modifies whether/how the mechanism fires* — not a direct cause of the outcome | RAMESES II 2017; Greenhalgh & Manzano 2022 | CONSTRAINS/ENABLES relations from Context (auto) |
| A concept's realist role is an *explanatory decision* — the same thing can be C here, M there | Greenhalgh & Manzano 2022 | role recorded per instance; **row-3 cross-role matches in verification make this visible** (auto) |
| Every element carries a **verbatim quote** that exists in the source; outcomes from results, not intros | Wong 2013; Sci Rep 2025; Pizard 2025 | quote resolution to exact span — **96.9%** (auto) |
| Relations extracted *at the same time* as elements (linked coding), not assembled later | Jackson & Kolla 2012; Rees 2026 | extractor emits typed relations inline (auto) |
| Demi-regularity requires **recurrence** (≥2 independent sources), else it is a candidate theory | Jagosh 2012; Rees 2025/2026 | `demi_regularities` built on ≥2 studies (auto) |
| Contradictions handled by a named operation (juxtapose / reconcile / adjudicate / consolidate) | Pawson & Manzano 2012 (via RAMESES) | `contradictions` table surfaces them; operation-label is (—) |
| Refined theory judged by coherence — consilience, simplicity, analogy | Dada 2023; Dalal 2024 (IBE-Eval) | theory correspondence (LLM, self-judged — see §4/OUTPUT_AND_VERIFICATION.md) |
| Untested/refuted hunches are *kept and marked*, never deleted | Dalkin 2021; RAMESES II 2017 | `ipt_versions` retained; downstream persistence of HITL-3 needs fixing (—) |
| Appraisal at the **fragment** level (relevance/richness/rigour), never a global study-quality gate | Wong 2013; Dada 2023 | screening is theory-relevance based (partial); richness/rigour scores (—) |
| Independent double-coding + chance-corrected agreement + adjudication | Jagosh 2012; Khraisha 2024 | two screening models + Checker; **Cohen's κ / human pass still required** (—) |

The "(—)" rows are the honest to-do list: **operation-labelled contradictions, fragment-level
richness/rigour scores, guaranteed retention of refuted hunches, and a human double-coding κ pass.**

### 6.2 How the pipeline mirrors how human realist teams actually work

Published "how we did it" accounts (Jagosh 2012; Dalkin 2021; Rees 2026; Ajjawi & Kent 2022;
Richmond 2020 itself) share a recognisable pattern. Our steps map onto it:

| Human realist practice | Source | Our step |
|---|---|---|
| Build an initial programme theory from scoping + expert opinion + substantive theory | Shearn 2017; Richmond 2020 | Step 2 IPT seeding (HITL-0), from public learning theory — **never the benchmark's answers** |
| Theory-driven (not exhaustive) screening for *relevance to the developing theory* | Wong 2013; Jagosh 2026 | Step 3, two independent reviewers vote on theory-relevance |
| Extract linked configurations, conditioned on the current theory (deductive coding works; open coding is where LLMs fail) | DeRegnaucourt 2026; Xiao 2023 | Step 4, ontology-conditioned extraction with quote grounding |
| Two independent coders + whole-team refinement triggered by *coding misfit* | Jagosh 2012; Dalkin 2021 | Step 4b–4c Checker critique→revise (Self-Refine); HITL-2 |
| Re-read earlier papers in light of the revised theory | Dalkin 2021; RAMESES materials | Step 9 retroduction loop (**no prior LLM system does this** — a contribution) |
| Consolidate hundreds of CMOCs into demi-regularities; two leads compare independently | Rees 2025/2026 | Steps 6–7, Leiden communities + ≥2-study demi-regularities (deterministic) |
| Organise by explanatory contexts and compare across them | Rees 2026 (settings); Richmond (5 student contexts) | programme theory sections per context |

### 6.3 What the literature says NOT to do — checked against our design

- *Don't output catalogues* (separate C/M/O lists, or clusters that group like-with-like without
  triads). — We emit typed triads and causal edges; the Leiden communities are labelled by realist
  role but sit **inside** the CMOC graph, not as free-floating lists. **Watch item:** ensure
  community output is always read as part of a configuration, never as a standalone taxonomy.
- *Don't label intervention components as mechanisms.* — Enforced by domain/range validation; the
  Resource/Response split is the sharpest guard (Dalkin 2015).
- *Don't gate inclusion on study design / global quality scores.* — Our screening is theory-relevance
  based, correct per Wong 2013.
- *Don't report raw accuracy or single-run LLM-judged numbers.* — We report chance-correctable
  designs and K=3 ranges; **but** the entity-coverage headline and the self-judging theory score are
  the two places we currently fall short (documented in OUTPUT_AND_VERIFICATION.md §4).
- *Don't expect prompt tricks (CoT, self-reflection) to fix interpretive weakness* — gains are modest
  (Oami 2026). We rely on theory-conditioning + verification + human adjudication instead, which is
  the literature's recommended posture.
- *Don't assume a public CMOC gold standard exists or that exact-match scoring is meaningful* — experts
  themselves disagree on CMOC granularity (Renmans 2024). This is exactly why our strict relation
  recall is near-zero and why semantic/type-level matching with tolerance is the right lens.

### 6.4 The honest verdict

The system performs the **same operations** as a human realist team, in the same order, with the
human sovereign at five checkpoints, and it enforces most of the literature's CMOC-quality criteria
deterministically. Where it is weaker is exactly where the LLM-qualitative-coding literature predicts:
the *interpretive* judgements (mechanism identification, context-vs-mechanism role, programme-theory
coherence) are model-judged and need human ratification and cross-family judging. Those are named,
scoped, and blocked only by (a) API credits and (b) a human coding pass — not by any design flaw.

**Sources for §6:** RAMESES II *Quality Standards* (Wong et al. 2017); Wong et al., *RAMESES training
materials* (2013) & *publication standards* (BMC Med 2013); Dalkin et al., *What's in a mechanism?*
(Implement Sci 2015); Pawson & Manzano-Santaella, *A realist diagnostic workshop* (Evaluation 2012);
Greenhalgh & Manzano, *Understanding 'context'* (IJSRM 2022); Dada et al., *relevance, richness, rigour*
(Res Synth Methods 2023); Rees et al. (Med Educ 2025, 2026); Jagosh et al. (Milbank Q 2012); Jackson &
Kolla, *linked coding* (AJE 2012); Dalkin et al., *NVivo for realist theory* (IJSRM 2021); Renmans et al.,
*CMOC database* (Evaluation 2024); Pizard et al., *LLMs for qualitative synthesis* (arXiv 2510.16502,
2025); DeRegnaucourt et al. (JMIR Form Res 2026); Xiao et al. (IUI 2023); Qiu et al., *hypothesis
refinement* (ICLR 2024); Dalal et al., *IBE in LLMs* (ACL 2024); Lin et al., *Agent-as-Peer-Debriefer*
(2026); Khraisha et al. (Res Synth Methods 2024); Oami et al. (Front Digit Health 2026); Ajjawi & Kent
(J Grad Med Educ 2022); Shearn et al. (IJQM 2017). DOIs in the project research log.
