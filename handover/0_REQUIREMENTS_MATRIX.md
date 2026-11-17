# Your assignment, clause by clause

**Duy Nguyen.** A traceability matrix for your email of 30 October 2026.

Read this first if you want to know what is done. Every row is a clause of your email, in
your order, with a status and the file that substantiates it. Nothing is marked done
without something to open.

**Status vocabulary.** *Done* — finished, with the artifact named. *Partly done* — the part
that could be done without spending has been, and the row says what is left and why.
*Blocked* — the obstacle is named, with its price where it has one. *Yours* — it needs your
judgement, not our work.

---

## Section 1 — "Review and provide our existing research pipeline"

| Your words | Status | Where |
|---|---|---|
| "The complete pipeline, source code, architecture, and relevant GitHub repository" | **Done** | [`1_WHAT_WE_BUILT.md`](1_WHAT_WE_BUILT.md) §2, repository root |
| "The agents, prompts, instructions, schemas, and configurations" | **Done** | `config/prompts/` (21 of 24 prompts editable without touching code), `config/ontology.yaml`, `config/agents.yaml` |
| "The input data, intermediate results, outputs, knowledge graphs, and verification reports" | **Done** | `outputs/raw_export/` — every row of every table, JSON and CSV, nothing summarised |
| "The evaluation procedures and results from the Richmond benchmark" | **Done** | [`docs/VERIFICATION_PROTOCOL.md`](../docs/VERIFICATION_PROTOCOL.md), [`docs/MACHINE_VS_HUMAN.md`](../docs/MACHINE_VS_HUMAN.md) §5.1 |
| "The current conference paper draft and relevant research documentation" | **Done** | AERA 2027 draft; accepted 6 November. **It carries superseded figures** — see [`6_PROGRESS_REPORT.md`](6_PROGRESS_REPORT.md) |
| "The materials and instructions you previously provided to AI, together with important AI responses, recommendations, and decisions" | **Done** | `docs/DECISION_LOG.md`, `WALKTHROUGH.md` (42 milestone entries, append-only) |
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
| "ask our AI pipeline to conduct a broader literature search" | **Done, 16 November, at no cost** | **1,863 candidate records**, 89% with an abstract, 68% with a free full text. [`SEARCH_REPORT.md`](../outputs-emotion/SEARCH_REPORT.md) |
| "identifying additional relevant systematic reviews, realist reviews, experimental studies, and educational intervention studies" | **Done** | 274 review articles; 388 experimental or quasi-experimental; 317 qualitative. [`EVIDENCE_MAP.md`](../outputs-emotion/EVIDENCE_MAP.md) |
| "focus on higher education, particularly STEM education" | **Done — and it raises a question for you** | 1,088 records are higher education. But engineering, computing and the natural sciences together account for **51**. Mathematics (mostly maths anxiety) accounts for 108. **See Question 1 below.** |
| "emotional awareness, emotional regulation, achievement emotions, emotional intelligence, self-regulated learning, motivation, engagement, and academic outcomes" | **Done** | All eight are named verbatim in `config-emotion/protocol.yaml` and all eight are counted in the evidence map |

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
| "Interventions: reflective writing, emotional awareness prompts, feedback, learning plans, and self-regulation activities" | **Prepared — and this is our most unexpected finding** | All five are in the protocol. In the literature, three of them are nearly absent. **See Question 2.** |
| "Mechanisms: how interventions influence … understanding, appraisals, … strategies, and learning behavior" | **Prepared** | Coded as Gross's five regulation families plus control-value theory's control and value appraisals, following ERAS |
| "Outcomes: … emotional awareness, regulation, motivation, engagement, self-regulated learning, and academic achievement" | **Prepared and measured** | All six counted, alongside Pekrun's nine achievement emotions. **See Question 3.** |
| "construct an evidence-linked knowledge graph" | **Blocked** | The machinery exists and ran twice on Richmond; it needs extracted CMOCs to build from |
| "preserve the evidence traceability, human verification, and reproducibility features" | **Preserved by design, and extended** | Every CMOC element still requires a verbatim quote; every search query is logged with the field it matched; the search report, evidence map and cost model are all **generated from the data**, not written |

## Section 5 — "Interact with AI and handle human-in-the-loop requirements"

| Your words | Status | Note |
|---|---|---|
| "please interact with it directly and complete the necessary procedures rather than stopping the research process" | **Done on Richmond** | All 20 contradictions resolved and the programme theory signed, recorded honestly as AI-performed under your delegation. Nothing to do yet on the new topic, because screening has not run |
| "For routine decisions … please exercise your judgment and document your decisions" | **Done** | `WALKTHROUGH.md`, `docs/DECISION_LOG.md`, and the revision log inside `config-emotion/coding_frame.yaml`, which records every change to the coding dictionary and why |
| "If you encounter questions involving important research directions … please contact me" | **Doing it now** | Four questions below. Three of them are findings from this week that change what the review should be |

## Section 6 — "Initial research outputs"

| # | Your words | Status |
|---|---|---|
| 1 | "A complete package documenting our existing pipeline, its inputs, outputs, architecture, prompts, and evaluation results" | **Done** — [`1_WHAT_WE_BUILT.md`](1_WHAT_WE_BUILT.md) |
| 2 | "An AI-generated assessment of what is needed … including a step-by-step implementation plan" | **Done** — [`2_WHAT_THE_NEW_TOPIC_NEEDS.md`](2_WHAT_THE_NEW_TOPIC_NEEDS.md) |
| 3 | "A preliminary literature collection and structured evidence database" | **Half done.** The collection exists: 1,863 records, 1,266 with a free full text. The *structured evidence database* in the sense you mean — screened, with eligibility applied — needs screening (~$5). What exists instead is a **descriptive evidence map** of the whole pool, built without a model: [`EVIDENCE_MAP.md`](../outputs-emotion/EVIDENCE_MAP.md) |
| 4 | "Initial extracted CMOCs and a knowledge graph" | **Not started.** Blocked on extraction |
| 5 | "A preliminary research synthesis identifying promising interventions, their underlying mechanisms, and the conditions under which they are effective" | **Not started, and we will not fake it.** The evidence map shows what the literature *studies*; it cannot show what *works*. Calling term frequencies "promising interventions" would be the one mistake this project cannot afford |
| 6 | "A progress report identifying what has been completed, what limitations remain, and what should be done next" | **Done** — [`6_PROGRESS_REPORT.md`](6_PROGRESS_REPORT.md) |

## Your closing instruction

> "Please begin by reviewing the existing pipeline with AI and determining what we need to
> prepare, then proceed with the literature search and a small pilot study using the
> current framework."

The review is done, the preparation is done, **the literature search is done**. The pilot
study is not, and that is the honest gap: it is the first step that spends money, and the
project has had no budget since 13 November. [`COST_MODEL.md`](../outputs-emotion/COST_MODEL.md)
prices it from the actual prompts rather than guessing — a three-paper pilot is about $5,
and it would replace every estimate in that file with a measurement.

---

# Four questions for you

Your section 5 asks us to bring you questions about "important research directions" rather
than deciding them ourselves. These are those.

### Question 1 — Is STEM the focus, or the gap?

You asked for higher education, particularly STEM. Of 1,088 higher-education records,
engineering, computing and the natural sciences account for **51 between them**. Maths and
statistics account for 108, and almost all of that is maths or statistics *anxiety*. Health
sciences account for 75.

Two defensible reviews follow from this, and they are different papers:

- **Narrow to STEM and report the gap as the finding.** "There is almost no realist
  evidence on emotion-regulation interventions in engineering, computing or the laboratory
  sciences" is a publishable claim and an argument for new primary research.
- **Review higher education broadly and treat STEM as one context among several.** More
  evidence to synthesise, a weaker contribution, and it is no longer the review you
  described.

We do not think this is ours to choose.

### Question 2 — Follow your five examples, or follow the literature?

You named five intervention types by example. Here is how often each appears in 1,863
records:

| Your example | Records |
|---|---|
| Feedback | 149 |
| Reflective writing | 101 |
| Learning plans and goal setting | 17 |
| **Self-regulation activities** | **7** |
| **Emotional awareness prompts** | **6** |

And here is what the literature actually studies:

| Not named by you | Records |
|---|---|
| **Mindfulness and attention training** | **291** |
| Social and emotional learning programmes | 151 |
| Appraisal and reappraisal prompts | 103 |
| Expressive writing | 63 |
| Emotion-regulation training as a named programme | 58 |

We widened the dictionary deliberately to check whether the near-zeros were our fault:
self-regulation activities went from 0 to 7, emotional awareness prompts from 3 to 6. The
scarcity is real, not an artifact. Note also that "feedback" is counted generously — all
149 come from the bare word, which appears in many abstracts for reasons unrelated to
emotion, so that figure is an upper bound.

So: does the review follow your examples, and report that practitioners' vocabulary and the
research literature barely overlap? Or does it follow the literature, and centre on
mindfulness and reappraisal? The first is more original. The second has more evidence.

### Question 3 — One emotion, or nine?

Pekrun's taxonomy has nine achievement emotions. In our pool:

| | Records |
|---|---|
| **Anxiety** | **578** |
| Enjoyment | 79 |
| Boredom | 68 |
| Anger | 66 |
| Hope | 59 |
| Pride | 28 |
| Shame | 27 |
| Hopelessness | 24 |
| Relief | 11 |

**Anxiety is 85% of the 678 emotion-tagged records.** The field has studied one negative,
activating, outcome-focused emotion and left the other eight at the margins. Boredom —
which Pekrun treats as an *activity* emotion, the one that arises during learning rather
than about its result — appears 68 times.

This is a finding in its own right, and it decides the review's shape. A review of
"emotional awareness and regulation" that follows the evidence will be mostly a review of
anxiety management. A review that holds to the full taxonomy will be reporting absence
across two thirds of it.

### Question 4 — May we spend about $25?

| | |
|---|---|
| Screen all 1,863 records against the protocol | **$5.44** |
| A 3-paper pilot extraction, which replaces every estimate with a measurement | **$4–5** |
| A 10-paper pilot — enough to see whether a programme theory forms | **$13–16** |
| Screen + 10-paper pilot | **≈ $21** |

Figures from [`COST_MODEL.md`](../outputs-emotion/COST_MODEL.md), computed from the system
prompt the pipeline actually sends and the prices in `config/models.yaml`, then doubled by
the project's own deliberately pessimistic calibration factor.

We had reported deliverables 3, 4 and 5 as needing budget. That was partly wrong: three of
the pipeline's stages call no model at all, which is why the search and everything in this
week's documents cost nothing. Screening is cheap. **Extraction is the expensive stage, and
it is the only one that is genuinely blocked.**
