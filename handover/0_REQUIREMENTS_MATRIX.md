# Your assignment, clause by clause

## In one glance

| The six outputs you asked for | |
|---|---|
| Documentation of the existing pipeline | **Done** |
| Assessment of what the new topic needs, with a plan | **Done** |
| Literature collection and evidence database | **Collected, not yet screened** |
| Extracted CMOCs and knowledge graph | **Not started — needs the AI model** |
| Preliminary synthesis | **Not started — needs the AI model** |
| Progress report | **Done** |

**Why the last three stop there.** Screening decides which of the 1,863 records are
eligible, and it is the first step that calls the AI model. JSU has not released the tool
allowance, so there has been no credit. Screening the whole pool costs **$5.44**; a
ten-paper trial extraction, **$16**.

**What we need from you.** One decision — may we spend about $25? Everything else below is
a report, not a question. Three scope decisions we took ourselves are at the end, each with
what would reverse it.

**What all of this cost so far.** Nothing.

---

Below is every clause of your email, in the order you wrote it, with a status and the file
that backs it up. Nothing is marked done without something you can open and check.
**Done** = finished. **Partly done** = what could be done without spending is done, and the
row says what is left. **Blocked** = the obstacle is named, with its price. **Yours** =
needs your judgement, not our work.

---

## Section 1 — "Review and provide our existing research pipeline"

| Your words | Status | Where |
|---|---|---|
| "The complete pipeline, source code, architecture, and relevant GitHub repository" | **Done** | [`1_WHAT_WE_BUILT.md`](1_WHAT_WE_BUILT.md) §2, repository root |
| "The agents, prompts, instructions, schemas, and configurations" | **Done — attached** | `pipeline-and-ai-record/prompts/` holds all ten agent prompts verbatim (21 of 24 prompts are editable without touching code); `config/ontology.yaml` and `config/agents.yaml` in the repository |
| "The input data, intermediate results, outputs, knowledge graphs, and verification reports" | **Done — attached** | `benchmark-outputs/raw_export/` (every row of every table, JSON and CSV, nothing summarised), `benchmark-outputs/Knowledge_Graph_Report.html`, `benchmark-outputs/MASTER_VERIFICATION_REPORT.md`, and `RICHMOND_RESULTS.html` for the whole review on one page |
| "The evaluation procedures and results from the Richmond benchmark" | **Done** | [`docs/VERIFICATION_PROTOCOL.md`](../docs/VERIFICATION_PROTOCOL.md), [`docs/MACHINE_VS_HUMAN.md`](../docs/MACHINE_VS_HUMAN.md) §5.1 |
| "The current conference paper draft and relevant research documentation" | **Done — attached** | `AERA_2027_paper_as_accepted.docx`, exactly as accepted on 6 November. **Its verification figures have since been superseded and must not be quoted from it** — the corrected ones are in [`6_PROGRESS_REPORT.md`](6_PROGRESS_REPORT.md). The accepted manuscript is deliberately left unedited |
| "The materials and instructions you previously provided to AI, together with important AI responses, recommendations, and decisions" | **Done — attached** | `pipeline-and-ai-record/`: `INSTRUCTIONS_TO_AI.md` (the standing instructions given at the start of every session), `DECISION_LOG.md`, and `SESSION_LOG.md` — the full development record, 48 milestone entries, append-only, including the findings that turned out to be wrong and how they were caught |
| "what modifications, if any, are necessary for the new research topic" | **Done** | [`2_WHAT_THE_NEW_TOPIC_NEEDS.md`](2_WHAT_THE_NEW_TOPIC_NEEDS.md) §4 — what is reusable and what had to change |

## Section 2 — "Consult AI about how to initiate the new research"

Your seven questions, each answered against code that exists rather than code we would
like to have. All in [`2_WHAT_THE_NEW_TOPIC_NEEDS.md`](2_WHAT_THE_NEW_TOPIC_NEEDS.md).

| Your question | Status | Where |
|---|---|---|
| "What materials, information, and datasets we need to prepare" | **Done** | §1 |
| "What research questions, inclusion criteria, definitions, and theoretical frameworks" | **Done** | §2, and `config-emotion/protocol.yaml` as the executable version |
| "What inputs the existing pipeline requires and how those inputs should be organized" | **Done** | §3 |
| "Which existing pipeline components can be reused directly and which require modification" | **Done** | §4 |
| "How to identify, retrieve, process, and organize the relevant research publications" | **Done**, and now **executed** | §5; [`outputs-emotion/SEARCH_REPORT.md`](../outputs-emotion/SEARCH_REPORT.md) |
| "How the pipeline should extract, integrate, and validate evidence" | **Done** | §6 |
| "How we can evaluate the results and develop a publishable research study" | **Done** | §7, §8 |
| "a concrete, step-by-step implementation plan" | **Done** | §"A step-by-step plan" — steps 1–5 complete or awaiting your judgement |

## Section 3 — "Begin the literature review"

| Your words | Status | Where / what we found |
|---|---|---|
| The four recommended references, "to establish the initial theoretical and methodological foundations" | **Done** | `config-emotion/initial_programme_theory.yaml` is built from Pekrun 2006 and Gross 1998; Brackett 2012 and Durlak 2011 are both **in the pool** |
| "ask our AI pipeline to conduct a broader literature search" | **Done, at no cost** | **1,863 candidate records**, 89% with an abstract, 68% with an open-access PDF *link*; **662 full texts actually obtained**. [`SEARCH_REPORT.md`](../outputs-emotion/SEARCH_REPORT.md), [`ACQUISITION_REPORT.md`](../outputs-emotion/ACQUISITION_REPORT.md) |
| "identifying additional relevant systematic reviews, realist reviews, experimental studies, and educational intervention studies" | **Done** | 274 review articles; 388 experimental or quasi-experimental; 317 qualitative. [`EVIDENCE_MAP.md`](../outputs-emotion/EVIDENCE_MAP.md) |
| "focus on higher education, particularly STEM education" | **Done, and decided** | 1,088 records are higher education, but engineering, computing and the natural sciences together account for **51**. Mathematics (mostly maths anxiety) accounts for 108. STEM is therefore carried as a context dimension rather than an inclusion filter — **Decision 1 below**, with what would reverse it |
| "emotional awareness, emotional regulation, achievement emotions, emotional intelligence, self-regulated learning, motivation, engagement, and academic outcomes" | **Done — after a correction** | All eight are named verbatim in `config-emotion/protocol.yaml`. **Seven of the eight were being counted; emotional intelligence was not.** This row previously claimed all eight, which was wrong: the coding frame measured its two sub-constructs, awareness and regulation, but had no category for the umbrella construct — so a study using an established EI instrument and naming neither sub-construct matched nothing. Added in frame v1.2 and it is substantial: **349 records, 19% of the pool**, the second-largest category after anxiety. Every figure in [`EVIDENCE_MAP.md`](../outputs-emotion/EVIDENCE_MAP.md) is recomputed |

**One addition we made on our own initiative, and why.** Every one of the ten search
queries requires an intervention term, which means they can only ever return intervention
studies — and we found that Harley, Pekrun, Taxer & Gross (2019), *"Emotion Regulation in
Achievement Situations: An Integrated Model"* (*Educational Psychologist* 54(2):106–126,
387 citations) was in neither pool. That paper is the one that joins your two theoretical
references: it integrates Pekrun's control-value theory with Gross's process model, for
achievement settings specifically. We checked why it was missed: its title and abstract
contain **no** intervention term and **no** population term, so no query could have
reached it. A realist review needs the theory literature as well as the intervention
literature, because the programme theory is what the evidence gets tested against. So we
added three theory-only queries, pooled **separately** — `theory_pool.jsonl`, 445 records,
which now contains Pekrun 2006 (7,582 citations) and ERAS. Theory papers are not candidate
studies and are not mixed into the corpus.

## Section 4 — "Apply the existing pipeline to the new research topic"

| Your words | Status | Note |
|---|---|---|
| "extract and organize evidence into Context–Mechanism–Outcome Configurations (CMOCs)" | **Blocked — about $5 of screening, then $4–$50 of extraction** | [`COST_MODEL.md`](../outputs-emotion/COST_MODEL.md). Nothing has been extracted; there are zero CMOCs on this topic |
| "Contexts: Student characteristics, learning situations, prior experiences, and emotional challenges" | **Prepared and measured** | All four are in the protocol verbatim and all four are counted in the evidence map |
| "Interventions: reflective writing, emotional awareness prompts, feedback, learning plans, and self-regulation activities" | **Prepared, and it changed how the review is organised** | All five are in the protocol. In the literature three are nearly absent — but grouped by mechanism rather than by name, the gap is mostly a vocabulary gap. **Decision 2 below** |
| "Mechanisms: how interventions influence … understanding, appraisals, … strategies, and learning behavior" | **Prepared** | Coded as Gross's five regulation families plus control-value theory's control and value appraisals, following ERAS |
| "Outcomes: … emotional awareness, regulation, motivation, engagement, self-regulated learning, and academic achievement" | **Prepared and measured** | All six counted, alongside Pekrun's nine achievement emotions. Anxiety is 85% of the tagged records, so the review is built on it with boredom as a contrast case — **Decision 3 below** |
| "construct an evidence-linked knowledge graph" | **Blocked** | The machinery exists and ran twice on Richmond; it needs extracted CMOCs to build from |
| "preserve the evidence traceability, human verification, and reproducibility features" | **Preserved by design, and extended** | Every CMOC element still requires a verbatim quote; every search query is logged with the field it matched; the search report, evidence map and cost model are all **generated from the data**, not written |

## Section 5 — "Interact with AI and handle human-in-the-loop requirements"

| Your words | Status | Note |
|---|---|---|
| "please interact with it directly and complete the necessary procedures rather than stopping the research process" | **Done on Richmond, and countersigned** | All 20 contradictions resolved and the programme theory signed under your delegation, recorded honestly as AI-performed, then each confirmed by Duy at the review console — none disputed. Nothing to do yet on the new topic, because screening has not run |
| "For routine decisions … please exercise your judgment and document your decisions" | **Done** | `WALKTHROUGH.md`, `docs/DECISION_LOG.md`, and the revision log inside `config-emotion/coding_frame.yaml`, which records every change to the coding dictionary and why |
| "If you encounter questions involving important research directions … please contact me" | **One question, not four** | Three of the four open questions turned out answerable from the pool itself, so they are **decided below with the reasoning and with what would reverse each one**, as your same paragraph asks for routine decisions. The one left is the budget, which is not ours to spend |

## Section 6 — "Initial research outputs"

| # | Your words | Status |
|---|---|---|
| 1 | "A complete package documenting our existing pipeline, its inputs, outputs, architecture, prompts, and evaluation results" | **Done** — [`1_WHAT_WE_BUILT.md`](1_WHAT_WE_BUILT.md) |
| 2 | "An AI-generated assessment of what is needed … including a step-by-step implementation plan" | **Done** — [`2_WHAT_THE_NEW_TOPIC_NEEDS.md`](2_WHAT_THE_NEW_TOPIC_NEEDS.md) |
| 3 | "A preliminary literature collection and structured evidence database" | **Collection done; database built but not yet screened.** 1,863 records, 662 full texts obtained and **all 662 ingested into the review database — 623 with a usable full text, 8,357 indexed text units, nothing lost**. What is missing is the eligibility decision on each record, which is the first stage that calls a model (~$5). Two reports describe what is there without one: [`EVIDENCE_MAP.md`](../outputs-emotion/EVIDENCE_MAP.md) and [`ACQUISITION_REPORT.md`](../outputs-emotion/ACQUISITION_REPORT.md) |
| 4 | "Initial extracted CMOCs and a knowledge graph" | **Not started.** Blocked on extraction |
| 5 | "A preliminary research synthesis identifying promising interventions, their underlying mechanisms, and the conditions under which they are effective" | **Not started, and we will not fake it.** The evidence map shows what the literature *studies*; it cannot show what *works*. Calling term frequencies "promising interventions" would be the one mistake this project cannot afford |
| 6 | "A progress report identifying what has been completed, what limitations remain, and what should be done next" | **Done** — [`6_PROGRESS_REPORT.md`](6_PROGRESS_REPORT.md) |

## Your closing instruction

> "Please begin by reviewing the existing pipeline with AI and determining what we need to
> prepare, then proceed with the literature search and a small pilot study using the
> current framework."

The review is done, the preparation is done, **the literature search is done**. The pilot
study is not, and that is the honest gap: it is the first step that spends money, and the
project has no budget at present. [`COST_MODEL.md`](../outputs-emotion/COST_MODEL.md)
prices it from the actual prompts rather than guessing — a three-paper pilot is about $5,
and it would replace every estimate in that file with a measurement.

---

# Three decisions taken, and one thing we cannot decide

Your section 5 asks us to exercise judgment on routine decisions and document them, and to
bring you the ones that touch important research directions. Three of the four open
questions turned out to be answerable from the pool itself, so they are **decided below
with the reasoning shown** rather than passed to you. Each says what would reverse it.
The fourth is money, which is not ours to spend.

### Decision 1 — STEM becomes a context, not a filter

**The finding.** Of 1,088 higher-education records, engineering, computing and the natural
sciences account for **51 between them**. Mathematics accounts for 108, and almost all of
it is maths or statistics *anxiety*. Health sciences account for 75.

**What we decided.** The review covers higher education, and STEM is carried as a
**context dimension inside the realist framework** rather than as an inclusion criterion.

**Why.** A realist review needs enough studies per configuration to see a pattern repeat.
Fifty-one records before screening is perhaps ten to twenty after it, and this project has
already measured what happens at that scale: on Richmond's 28 papers, all 32 apparent
recurring patterns failed a degree-preserving permutation test. A STEM-only review would
produce configurations we could not defend.

But realist synthesis does not filter by context — **it treats context as the variable**.
The answerable question is therefore not "what works in STEM" but **"which mechanisms fire
differently in STEM than outside it"**, and 51 against 1,037 is enough for that comparison
even though it is not enough for a review of its own. This keeps your "particularly STEM"
without promising something the evidence cannot carry.

**What would reverse it.** If screening leaves 40+ eligible STEM studies, a STEM-focused
review becomes defensible and we should revisit.

### Decision 2 — the review is organised by mechanism, not by intervention name

**The finding.** Three of the five intervention types you named by example are nearly
absent, while one you did not name dominates:

| Your examples | Records | | Not named by you | Records |
|---|---|---|---|---|
| Feedback | 149 | | **Mindfulness / attention training** | **291** |
| Reflective writing | 101 | | Social and emotional learning | 151 |
| Learning plans, goal setting | 17 | | Appraisal and reappraisal prompts | 103 |
| **Self-regulation activities** | **7** | | Expressive writing | 63 |
| **Emotional awareness prompts** | **6** | | ER training as a named programme | 58 |

**What we decided.** Neither "follow your examples" nor "follow the literature". The
synthesis groups studies by **Gross's five emotion-regulation families**, which is what
the programme theory is built on anyway.

**Why.** Reorganised that way the gap largely disappears, and the reason it looked like a
gap is itself the interesting part:

| Mechanism family | What falls inside it |
|---|---|
| Attentional deployment | mindfulness **291** + your emotional awareness prompts **6** |
| Cognitive change | reappraisal **103** + reflective writing **101** + expressive writing **63** |
| Situation modification | learning plans **17** + feedback |

**"Emotional awareness prompts" returns 6 records because it is a name for a practice, not
a name for a mechanism.** The same mechanism has 291 records filed under "mindfulness". So
the scarcity is mostly a vocabulary gap rather than an evidence gap — and *that* is worth
reporting on its own: a teacher searching for evidence about what they actually do will
not find it, because the literature files it under a word they would not think to use.

**What would reverse it.** If the mechanism families turn out not to discriminate between
studies at extraction — if nearly everything lands in cognitive change — the grouping is
not doing work and intervention type should come back.

### Decision 3 — anxiety is the spine, and boredom is the test case

**The finding.** Anxiety is **578 of 678** emotion-tagged records. Pekrun's other eight sit
between 11 and 79: enjoyment 79, boredom 68, anger 66, hope 59, pride 28, shame 27,
hopelessness 24, relief 11.

**What we decided.** The review is built on anxiety, with **boredom carried alongside it as
a deliberate contrast case**, and the absence of the other seven reported as a finding
rather than apologised for.

**Why.** Eight emotions at 11–79 records cannot each support a programme theory. But
boredom is not just the second-largest — it is **theoretically different in Pekrun's own
terms**: an *activity* emotion, arising during learning, where anxiety is an *outcome*
emotion, about the result. That gives a question this pool can actually answer: **do the
mechanisms that regulate anxiety still work on boredom?** If they do not, that is a
genuine realist finding — same mechanism, different context, different outcome.

It turns "we only have anxiety" from a limitation into a design.

**What would reverse it.** If screening leaves fewer than ~20 eligible boredom studies, the
contrast is too thin and the review becomes anxiety-only with absence reported.

---

## The one decision that is yours: may we spend about $25?

| | |
|---|---|
| Screen all 1,863 records against the protocol | **$5.44** |
| A 3-paper pilot extraction, which replaces every estimate with a measurement | **$4–5** |
| A 10-paper pilot — enough to see whether a programme theory forms | **$13–16** |
| Screen + 10-paper pilot | **≈ $21** |

Figures from [`COST_MODEL.md`](../outputs-emotion/COST_MODEL.md), computed from the system
prompt the pipeline actually sends and the prices in `config/models.yaml`, then doubled by
the project's own deliberately pessimistic calibration factor.

**Our recommendation is to approve the $5.44 first and hold the rest.** Not to economise —
because screening is what makes the three decisions above checkable. Every figure in them
comes from counting dictionary terms in titles and abstracts, which is stated plainly
wherever it appears. After screening we know how many records are genuinely *eligible*, and
all three thresholds above ("40+ STEM studies", "~20 boredom studies", "do the families
discriminate") become answerable with real numbers rather than term counts.

We had reported deliverables 3, 4 and 5 as needing budget. That was partly wrong: three of
the pipeline's stages call no model at all, which is why the search, the acquisition, the
ingest and every document in this package cost nothing. Screening is cheap. **Extraction is
the expensive stage, and it is the only one genuinely blocked.**
