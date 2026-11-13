# Applying the pipeline to emotional awareness and regulation

**Duy Nguyen — 13 November 2026.** Deliverable 2 of the 2026-10-30 assignment.

Your section 2 asked seven questions and a step-by-step plan. Each answer below is tied to code
that exists, not to what the system might do. Where the honest answer is "we cannot yet", it says so.

A draft configuration for this topic has already been written — `config-emotion/` in the
repository — so the answers point at real files you can read and correct.

---

## 1. What must be prepared before starting

**Four things. Three exist in draft; one needs your judgement.**

| | Status |
|---|---|
| Review question and eligibility criteria | Drafted — `config-emotion/protocol.yaml`. **Needs your review**: these criteria decide what the review is *about* |
| Initial programme theory | Drafted — `config-emotion/initial_programme_theory.yaml`, built from the four references you named |
| A corpus | The pipeline can now build it. A trial search on 6 November pooled 160 records and kept 158 after deduplication |
| Domain expertise in prompts | Drafted — `config-emotion/agents.yaml` |

**What needs to be arranged rather than written:** a separate database, so a new topic cannot
overwrite the Richmond evidence. The pipeline now refuses to run if this is not done.

**What cannot be prepared, and is the central methodological problem below: a benchmark.**

---

## 2. Research questions, inclusion criteria, definitions, frameworks

**Review question** as drafted: *What educational interventions improve students' emotional
awareness and emotional regulation during learning — and when, why, for whom, and in what
circumstances are they effective?*

**Framework.** Built from the four references you named, each contributing a distinct piece:

| Reference | What it contributes to the analysis |
|---|---|
| **Pekrun 2006** | Achievement emotions arise from appraisals of *control* and *value*. Consequence: an intervention changes emotion by changing an appraisal, so **the appraisal is where we look for the mechanism** — not the feeling |
| **Gross 1998** | Regulation acts at five points: situation selection, situation modification, attentional deployment, cognitive change, response modulation. Consequence: **where in that sequence an intervention acts** is a candidate explanation for why two similar interventions diverge |
| **Brackett et al. 2012** | Emotional skill can be taught explicitly and in sequence. Consequence: a shared **feeling vocabulary** is itself a mechanism resource, not packaging |
| **Durlak et al. 2011** | Across 213 programmes, effectiveness tracked four implementation features (Sequenced, Active, Focused, Explicit). Consequence: **implementation quality is a context dimension**, and a null result may be an implementation failure rather than a theory failure |

**Inclusion criteria**, drafted: students in higher education with a STEM focus; an educational
practice intended to change how students notice, understand, label or regulate learning-related
emotions; excluding purely correlational studies with no intervention, and clinical treatment of
diagnosed disorders.

**A check against your email, and four things it caught.** The draft was written from your
assignment, then checked back against it item by item on 13 November. Four things you name
explicitly were missing and have been added: **emotional awareness prompts** and **self-regulation
activities** as intervention types, and **prior experiences** and **emotional challenges** as
context dimensions. All eight topics you list in section 3 and all nine examples you give in
section 4 are now named in the configuration verbatim, so none is lost to paraphrase when the
extractor reads them.

**The definition that will cause the most argument, and should be settled by you:** whether a
study that measures emotion as an *outcome* of an ordinary teaching intervention is in scope, or
only studies that intervene on emotion *deliberately*. The draft takes the narrower reading. The
wider reading roughly triples the corpus and changes what the review is.

---

## 3. What inputs the pipeline requires, and how to organise them

A single file, `studies_metadata.jsonl` — one record per paper with title, authors, year, DOI,
abstract — plus PDFs where available. `res search` produces this file directly, so for this topic
no manual assembly is needed. Abstract-only records are acceptable: on Richmond, two of the 28 had
no full text, and the system correctly declined to extract configurations from them rather than
guessing.

---

## 4. What is reusable, and what must change

**Reusable without modification** — this is most of the system:

- All six pipeline stages, the eight agents, and all five human checkpoints
- **The ontology.** The five entity types are domain-neutral, intervention is already first-class,
  and mechanism-response is already defined as "the cognitive **or emotional** reaction … panic,
  frustration … gratitude". Your Context/Intervention/Mechanism/Outcome framing needs no change
- The verbatim-quote requirement, the character-level provenance, the audit trail
- The pattern and contradiction detection, which is database computation and domain-independent
- The verification harness, for any part where a reference standard exists

**Must be rewritten** — all configuration, no code:

- `protocol.yaml`, `initial_programme_theory.yaml`, and the agent personas, all of which currently
  describe clinical reasoning. Drafted in `config-emotion/`

**One change to the extractor's instructions, and it is important.** On Richmond the failure mode
was missing affect: the words *emotion* and *self-efficacy* occur **zero times** across all 28
papers, so the system could not recover four concepts Richmond's reviewers reached by inference
from theory. **On this topic the failure mode inverts.** Affective vocabulary will be everywhere
and the risk becomes over-extraction — every reported feeling promoted to a mechanism. The draft
prompts therefore state explicitly that a feeling is not a mechanism (the mechanism is the
appraisal that shifted) and that a measured emotion score is an outcome. **Expect the first run to
be calibration rather than result.**

---

## 5. How to find, retrieve and organise the publications

Built on 6 November and tested, though not yet run for real:

- **Search** — OpenAlex and Crossref. Both free, neither needs a key, and both are open catalogues,
  so a reader of the paper can repeat our search. Scopus and Web of Science cannot offer that
- **Deduplication** — by DOI, then by normalised title, reporting both counts, as PRISMA requires
- **Search logging** — every query recorded with its filters and result counts, so the search
  section of the paper is generated from the record rather than reconstructed
- **Full text** — only open-access copies the catalogue itself links. How many full texts were
  obtainable, and how many were not, is a finding about the evidence base and will be reported

Trial run, 6 November: two queries, 160 records pooled, **158 unique**, 47% with abstracts, and the
results were on topic.

---

## 6. How evidence is extracted, integrated and validated

**Extracted** one paper at a time, into typed configurations, each element carrying a verbatim
quote and its character position. Quotes are checked against the source afterwards by string
matching, not taken on trust — on Richmond, 99.8% resolved.

**Integrated** by collapsing repeated mentions into shared concepts, then computing: patterns
recurring across two or more independent studies, and **contradictions** where the same
intervention produced opposite outcomes. Contradictions are the valuable output of a realist
review and are never smoothed over — they go to a human, because the machine can detect that a
contradiction exists but not what explains it.

**Validated** at four levels: the quote exists in the source; the configuration obeys the ontology;
a second agent checks the extraction; and a human adjudicates what is flagged.

**The honest gap.** Validation currently measures *recall* against a benchmark. **Precision — how
much of what we extract is spurious — has never been measured, on any topic.** On a topic with no
benchmark this matters more, not less.

---

## 7. How to evaluate the results, and reach a publishable study

**This is the hardest question and deserves a direct answer rather than a plan.**

Richmond gave us an external answer key: 46 concepts, 40 relations, a published programme theory.
**This topic has no equivalent.** No figure produced here can be scored the way the Richmond
figures were, and any accuracy claim would be unfounded.

Two consequences, which should be designed in now rather than discovered at the end:

**First, the human checkpoints carry the whole validity argument.** On Richmond they were a
quality control on top of an external benchmark. Here they *are* the evidence. They must have a
real person behind them, documented, with disagreements recorded rather than resolved silently.

**Second, what gets reported is process evidence, not an accuracy number.** What this system can
show that an unstructured approach cannot: every claim anchored to a quotation; every configuration
attributed to a named study; typed causal relations; patterns and contradictions computed rather
than asserted; a complete adjudication record. That is the methodological contribution, and it does
not depend on having a benchmark.

**Richmond's role in the paper is therefore to show the method works where it *can* be checked**,
and this topic's role is to show it produces usable knowledge where no answer key exists. The two
studies do different jobs and should be written that way.

**What we measured that bears on this.** A single model call over the same 28 papers — the
counterfactual of pasting them into a chat window — recovered 32 of 46 concepts, inside our
pipeline's own range. **On concept coverage the pipeline is not better**, and we do not claim it
is. The difference is everything in the paragraph above, none of which the single call produces.

---

---

## 8. What the literature says about doing this with AI, and where it leaves us

Searched 13 November. Two findings matter more than the rest, and both are favourable.

**No peer-reviewed evaluation of LLM-based CMOC extraction against human realist reviewers
appears to exist.** The LLM-and-systematic-review literature has grown quickly, but it is almost
entirely PRISMA-shaped: screening and data extraction for effect-size reviews. A 2025 *JAMIA*
LLM-assisted review of the field found the most-covered stages were searching (34.9%) and data
extraction (31.4%); realist synthesis does not appear as a category. A methodological case study
has used AI tools to *search* for a realist review, but for extraction and synthesis the manual
baseline is still [Gilmore et al. (2019)](https://journals.sagepub.com/doi/10.1177/1609406919859754),
which describes how CMOCs are extracted by hand. **That makes the Richmond study's position
unusually clear: it is not a better version of something already benchmarked; it is the first
benchmark of its kind that we can find.**

**No dedicated systematic review of emotion-regulation interventions in STEM higher education,
framed by achievement emotions, appears to exist either.** The adjacent work is real but differently
scoped: a 2025 *Educational Psychology Review* meta-analysis of regulation *strategies* and
achievement in secondary and university students; Pekrun-linked work on regulating achievement
emotions, including the RAEQ instrument; a 2022 study of 174 STEM degree students finding
cognitive reappraisal associated with better exam performance; and a
[PNAS field experiment](https://www.pnas.org/doi/10.1073/pnas.1808589116) in which a reappraisal
intervention improved science exam scores and pass rates for lower-income students. **So the
review has a genuine gap to fill, and the evidence base to fill it exists.**

One validation worth noting: our trial search independently surfaced the 2022 STEM study the
literature search above also found. The tool is looking in the right place.

### Three things this changes in how we should work

**Report to an AI-assisted standard, not only to RAMESES.** Reporting guidance for AI-assisted
reviews now exists in draft: [PRISMA-LLM](https://arxiv.org/abs/2609.11559) (September 2026),
built from an analysis of 888 review-automation papers, plus ARISMA and L-PRISMA, and PRISMA 2026
is reported to add structured handling of AI-assisted screening. None is settled, so we should not
claim conformance — but PRISMA-LLM's central distinction is one we should adopt now, because it
is the distinction a reviewer will apply: **separate disclosing what the AI did from evaluating
what difference it made.** Its own finding is the warning: among papers reporting only positive
LLM evaluations, 52% nonetheless disclosed an unmet reliability requirement. A review that
reports only what worked is the common failure, not the exception.

**Do not build what exists.** For screening specifically, ASReview (open source, active learning,
Utrecht) and Rayyan (free tier) are mature. Our contribution is CMOC extraction, span grounding
and realist synthesis — stages those tools do not attempt. If screening ever becomes the
bottleneck, adopting one is cheaper than improving ours, and we should say so rather than
re-implement.

**Expect the extraction claim to be challenged on precision.** Where the field has evaluated LLM
extraction it has done so against human extraction on both precision and recall. We measure only
recall. This is the gap most likely to be raised, on either topic.

---

## A step-by-step plan

Ordered so the cheapest and most informative steps come first. Steps 1–4 cost nothing.

| | Step | Needs |
|---|---|---|
| 1 | **You review `config-emotion/protocol.yaml`** — particularly the scope question in §2 | Your judgement |
| 2 | Countersign the Richmond review checkpoints, closing the gap in §3 of deliverable 1 | ~15 min, Duy |
| 3 | Make the Richmond comparison computed rather than hand-written | — |
| 4 | Test whether the recurring patterns are more than chance (null-model significance) | — |
| 5 | Create the separate database and run the literature search | Small API cost |
| 6 | **Pilot of 10–15 papers**, reporting the measured cost before going further | API budget |
| 7 | Full extraction, synthesis, knowledge graph | API budget |
| 8 | Preliminary synthesis and progress report | — |

**On budget.** The Richmond run was configured with a $45 ceiling for 28 papers. We have no cost
history to extrapolate from — the usage records were lost when the database was restored — so step
6 exists to measure rather than estimate. Until a budget is available, steps 1–4 are what we can
do, and they are the steps that most improve the eventual result.
