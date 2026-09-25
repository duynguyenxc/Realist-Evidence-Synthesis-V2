<!-- GENERATED from FOR_THE_PROFESSOR.template.md by scripts/fill_professor_answers.py.
     Edit the template, never this file. -->

# Answers to your five questions

*Duy Nguyen — 2026-09-23. Five questions from our last meeting, one short answer each.
Numbers below are from run `verify-edcbf790`; all of them are reproducible with two commands
(§6).*

---

## 1. "Show me the output."

The system's real output is **a PostgreSQL database**. Everything else is an export of it. After a
run, here is what exists and where:

| What you can open | File | What it contains |
|---|---|---|
| **The whole review, one page** | `outputs/RESULTS.html` | Richmond's conclusions beside ours, the verification table, and every finding — searchable. Opens in any browser, no software needed. **Start here.** |
| The findings as a spreadsheet | `outputs/exports/cmocs.csv` | One row per finding: study, direction, the sentence |
| Every concept, with its evidence | `outputs/exports/entities.csv` | Concept, realist role, **the exact sentence from the paper it came from**, character position |
| Every causal link | `outputs/exports/relationships.csv` | From-concept → relation → to-concept |
| The mechanisms the machine discovered | `outputs/exports/big_concepts.csv` | Clusters the algorithm found on its own |
| The scorecard | `outputs/runs/verify-*/verification_report.md` | Every verification number |
| The graph, for programmatic use | `outputs/lkg/*.parquet` | Nodes and edges |
| PRISMA flow, evidence table, theory | `outputs/runs/report-*/` | The same artefact types Richmond published |
| Full audit trail | `audit_log` table | Every action, who did it, when |

**Scale:** 28 papers in; **94 findings**, **547 concepts with quotes**, **459
causal links**, **8 discovered mechanisms** out.

---

## 2. "Is the output good enough?"

**Honest answer: parts of it are solid and publishable now; parts are not yet validated, and I can
tell you exactly which is which.**

**Solid — deterministic, reproducible forever, no AI judgement involved:**

- We recover **all 28** of Richmond's included studies (26 automatically; 2 flagged as uncertain and
  sent to a human, which is the design working).
- **93.0% (95% CI 90.6%–95.0%) of every claim the system makes resolves to a verbatim sentence in the source
  paper**, with its character position. The system cannot assert something that is not in a paper.
- **29 of Richmond's 40 causal links** are recovered with at least one endpoint pinned to
  the matching concept.

**Not yet validated — and I am not presenting these as results:**

- Concept matching and mechanism matching are judged by an AI, not a person.
- The programme-theory score changes by **0.29 on a 0–1 scale** depending only on which AI does the
  judging. That spread means the number is not yet trustworthy.
- **No human has independently coded any paper yet.** Until two coders do, there is no human
  benchmark to compare against.

**What makes this acceptable rather than a failure:** the weak parts have a named, costed fix —
two coders on 8–10 papers, and a statistical correction (prediction-powered inference) that makes
the AI-judged numbers valid even if the judge is biased. The blank coding workbooks already exist
(`res gold-template`). This is a first iteration with its limits measured, not hidden.

---

## 3. "How do you verify it against Richmond?"

We split the review into the things Richmond actually published, and compare each one separately.
The column that matters most is the last one.

| What we compare | Richmond's artefact | How | Result | Judged by |
|---|---|---|---|---|
| Did we find the same papers? | The 28 included studies | Do we include each one? | **100%** after one human check | machine |
| Is every claim really in the paper? | They quote sources | Does each quote match text in the PDF? | **93.0% (95% CI 90.6%–95.0%)** | machine |
| Same concepts? | 46 concepts in their Figures 2–3 | Does one of ours mean the same thing? | **34/46** | **AI** |
| Same causal shape? | 40 arrows | Is the pattern present? | **39/40** — *but this cannot fail, see below* | machine |
| …anchored to a real concept? | Same 40 | One endpoint exact, other correct role | **29/40** | machine |
| …exact concept pair? | Same 40 | Both endpoints exact | **6/40** | machine |
| Same mechanisms? | Their mechanism list | Does a discovered cluster match? | **19/28** | **AI** |
| Same theory? | Their 5 theory chains | Structural correspondence | **judge-dependent** | **AI** |

**Three things I want to state plainly, because they protect the work:**

1. **One of our numbers cannot fail, and we say so.** "39 of 40 causal patterns" only asks whether a
   shape like *Context constrains Outcome* appears anywhere in the graph. There are only 8 such
   shapes in our graph and 7 in Richmond's, so almost any output scores ~100%. We report the ceiling
   next to the score and lead with the anchored number instead.
2. **The strict number is zero, and we publish it.** Exact concept-pair recovery is 0/40. Our
   concepts are named differently from Richmond's, so this is expected — and it is the honest floor
   under the claim.
3. **We do not claim to reproduce Richmond.** Their figures are one team's rendering, drawn with one
   method; comparison research shows such maps are instrument-dependent and incomplete. Our claim
   is narrower and defensible: the system is **faithful** to its sources, **non-inferior** to a
   human coder where agreement is a meaningful idea, and in **measurable correspondence** with a
   published human review where it is not. Human screeners themselves err about 10.8% of the time,
   so non-inferiority — not perfection — is the right target.

Full methodology with citations: `docs/VERIFICATION_PROTOCOL.md`.

---

## 4. "Do you understand the project? What is the algorithm and the architecture?"

**The project in one sentence.** Richmond's five reviewers spent months reading 28 papers to work
out *which teaching helps which student, and why*. We built a system that does the same analytic
work automatically, with a human approving at four checkpoints, and we measure how close it gets.

**The architecture — eight stages, one database.**

```
28 PDFs
  1 INGEST      -> clean text + character positions        (no AI)
  2 SCREEN      -> two AI models vote; disagreement -> HUMAN CHECKPOINT 1
  3 EXTRACT     -> pull out C-M-O findings, each with a quote -> HUMAN CHECKPOINT 2
  4 NORMALIZE   -> merge synonyms into shared concepts
  5 COMMUNITIES -> Leiden clustering finds mechanisms       (the novel part)
  6 SYNTHESIZE  -> recurring patterns + contradictions      -> HUMAN CHECKPOINT 3
  7 THEORY      -> write the programme theory               -> HUMAN CHECKPOINT 4
  8 VERIFY      -> compare with Richmond
```

Everything lives in PostgreSQL; every action is written to an audit log.

**The main algorithm — Leiden community detection.** We build a graph where each node is a concept
and an edge means two concepts appeared in the same finding. The **Leiden algorithm** (Traag et al.,
2019) partitions that graph into clusters. Each cluster is a *mechanism the machine discovered from
the evidence*, not one a reviewer wrote down. **This is the novel contribution: Richmond's
mechanisms were authored by people; ours emerge from the data, and we can measure how well the two
agree.**

**How the reasoning works.** Each stage makes structured AI calls with a fixed schema and a fixed
seed. The one genuine loop is in extraction: **draft → a different AI model critiques it → revise
once**, then a support score, then a second independent consistency check — deliberately mirroring
Richmond's "coded by one reviewer, checked by another".

**What I want to be precise about.** We describe this as GraphRAG-inspired, not GraphRAG. We build a
typed graph and run the same Leiden partition Microsoft's GraphRAG uses, but we do **not** have
embeddings, a vector store, or retrieval-based search. Saying so keeps the claim defensible.

**Tools:** Python 3.11 · OpenAI structured outputs (gpt-5.5 extraction and synthesis; gpt-5.4 family
for critique and checking; gpt-4.1-mini as an independent judge) · PostgreSQL 18 · networkx +
graspologic (Leiden) · scipy (exact confidence intervals) · Neo4j and Parquet for exploration ·
FastAPI for the human review console.

Detail: `docs/SYSTEM_AND_ALGORITHMS.md`.

---

## 5. "What is a 'candidate'?"

You saw **`UNTYPED_CANDIDATE`** in the relationships file. Here is exactly what it means.

Our ontology defines five permitted causal relations:

| Relation | Meaning |
|---|---|
| `PROVIDES` | A teaching intervention supplies a resource to the learner |
| `TRIGGERS` | A resource sets off a reaction in the learner |
| `ENABLES` | One thing makes another possible |
| `LEADS_TO` | A reaction produces an outcome |
| `CONSTRAINS` | A context limits or worsens an outcome |

When the extractor finds a genuine causal link between two concepts but it **does not fit any of
those five**, we face a choice: throw it away, or force it into the nearest box. Both are bad —
discarding loses evidence, forcing it corrupts the ontology.

So we do a third thing: store it as **`UNTYPED_CANDIDATE`** — *"a real link we could not type"* —
mark it as not satisfying the ontology constraint, and put it in the human review queue at
Checkpoint 2. It is excluded from every metric until a person types it.

**In this run there are 3 of 459.** That the number is tiny is itself the finding:
the five-relation ontology covers essentially all the causal language in this literature.

The word *candidate* appears in one other place — the verification step, where the AI matcher is
shown our concepts as "candidates" and asked which, if any, means the same as each Richmond concept.
There it simply means "the options offered to the matcher".

---

## 6. Reproducing any number here

```bash
PYTHONPATH=src python -m res_pipeline.cli run-all        # the whole pipeline
PYTHONPATH=src python -m res_pipeline.cli export-results # rebuild outputs/RESULTS.html
```

Deterministic numbers come out identical every time. AI-judged numbers are sampled three times and
reported with their range. `RES_GOLD=v1` reproduces the figures in the earlier preliminary report,
before the benchmark corrections of 2026-09-23.

## 7. What I need next

1. **Two human coders** on 8–10 papers, blind. This unblocks every agreement number; nothing else
   substitutes for it.
2. **An expert rating** of the programme theory, since two AI judges disagree by 0.29.
3. Confirmation of the delegated human-checkpoint decisions logged during development.
