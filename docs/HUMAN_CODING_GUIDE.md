# Human Coding Guide — how two coders produce the missing baseline

> **Who this is for.** Two people (the RA and one other) who will each read the same papers and
> code them **independently, without seeing the machine's output or each other's**. No prior
> realist-review experience is assumed; everything needed is in this document.
>
> **Why it cannot be done by the machine.** The point of this exercise is to establish what *two
> humans* agree on when they read the same paper. If the system that produced the output also
> produced the reference, the comparison measures nothing. The repository already contains an
> AI-produced per-paper coding (`gold/per_paper_gold/`) and it is explicitly **not** treated as a
> gold standard for exactly this reason.
>
> **Why it is the single most important task left.** Every agreement-style number this project
> reports — concept coverage, mechanism alignment — is currently uninterpretable, because there is
> no human ceiling to read it against. In the published literature GPT-3 reached κ = 0.61 on a
> coding task, which reads as a success until you see that the two human experts reached κ = 0.88
> on the same items (Xiao et al., IUI 2023). Without your numbers, we cannot tell a good result
> from a bad one.

---

## Part 1 — What you need to read first (about 90 minutes)

Read in this order. Do **not** skip to the coding.

| # | Read | Where | Why |
|---|---|---|---|
| 1 | **This guide, Parts 1–3** | here | The rules you will apply |
| 2 | **Richmond et al. (2020), Methods §2 and Results §3.2** | `data/paper-Richmond-original.pdf`, pp. 710–716 | The method you are imitating, in its own words |
| 3 | **Richmond's Figures 2 and 3** | same PDF, pp. 713 and 715 | What a finished realist figure looks like |
| 4 | **The five element definitions** | Part 2 below | The only thing you must memorise |

**Do NOT read**, at any point before you finish coding:

- `outputs/exports/*.csv` — the machine's answers
- `outputs/RESULTS.html`
- `gold/per_paper_gold/` — the AI-produced coding
- Your co-coder's workbook

Seeing any of these makes your coding worthless as an independent reference. This is not a
formality: in the published literature, coding done *with* an LLM reached κ = 0.87 against the
person who did it, and only 0.54 against an independent third coder — the agreement was an
artefact of having seen the machine's answer (Dai, Xiong & Ku, Findings of EMNLP 2023).

---

## Part 2 — The five elements, and how to tell them apart

A realist review does not ask *"does this intervention work?"* It asks:

> **For which learners, does this teaching trigger what internal reaction, producing what result?**

That sentence has five slots. Everything you code goes in one of them.

### The definitions

| Element | Plain-language test | Richmond examples |
|---|---|---|
| **Context** | A condition that was **already true before the teaching started** — about the learner, the group, or the setting. If the intervention created it, it is not a Context. | "students with low clinical domain-specific knowledge"; "students with high domain-specific knowledge"; "mixed levels of knowledge within one group" |
| **Intervention** | The teaching activity itself — what was *done*. | a case-based seminar; simulation; test-enhanced learning |
| **Mechanism — Resource** | What the intervention **puts into** the situation. The thing that is now available that was not before. | "explicit explanation of an expert's reasoning"; "accurate and timely feedback"; "an opportunity to make mistakes safely" |
| **Mechanism — Response** | What happens **inside the learner's head**. Thinking, feeling, deciding. Not observable directly — inferred. | "understanding"; "panic"; "frustration"; "feeling at ease"; "increased cognitive load" |
| **Outcome** | The **result** — measured, reported, or claimed by the authors. | "improved diagnostic accuracy"; "no improvement in diagnostic accuracy"; "more complete illness scripts" |

### The three distinctions people get wrong

These are exactly the confusions the machine makes, so your judgements on them matter most.

**(a) Response vs Outcome — the hardest one.**

> **Test: is it inside one learner's head, or is it a result you could put in a results table?**

| Text says | Element | Why |
|---|---|---|
| "students felt frustrated" | **Response** | Inside the learner |
| "the two groups showed similar decision speed" | **Outcome** | A measured group result, not an internal state |
| "learners came to understand the reasoning process" | **Response** | Internal |
| "post-test scores rose by 12%" | **Outcome** | Measured |
| "risk of introduced bias" | **Outcome** | A consequence, not something a learner experiences |

**(b) Context vs Intervention.**

> **Test: was it true before the teaching began?**

"Students attended the seminar" is **not** a Context — it is exposure to the Intervention.
"Students were in their fourth year with no prior ECG training" **is** a Context.

**(c) Intervention vs Mechanism-Resource.**

The Intervention is the *activity*; the Resource is *what the activity supplies*.
The intervention is "an expert think-aloud session"; the resource is "an explicit account of how
an expert reaches a diagnosis".

If you cannot separate them for a particular case, **code the Resource and leave Intervention
blank** — Richmond themselves often name only the resource.

---

## Part 3 — The coding procedure, step by step

### Before you start

1. Generate the two blank workbooks (either coder runs this once):

   ```powershell
   cd "D:\Realist-Evidence-Synthesis\Realist-Evidence-Synthesis-V2"
   res gold-template
   ```

   This writes `outputs/gold/per_paper_coding_coder_A.xlsx` and `..._coder_B.xlsx`.

2. Decide who is **A** and who is **B**. Each person opens **only their own file**.

3. Agree the sample. **8–10 papers is the minimum**; more is better. Pick them at random, not by
   convenience — e.g. sort the 28 study IDs and take every third one. Write down which papers you
   chose **before** you start, so the sample cannot drift.

### For each paper

**Step 1 — Read the whole paper once, coding nothing.** You are looking for the authors' causal
story, not for keywords.

**Step 2 — Find the causal claims.** These usually live in the Discussion and in the sentences
around the results. Look for language like *because, this led to, students who … were able to,
this may explain, as a result*.

**Step 3 — For each causal claim, write one row.** A row is one configuration: one Context, one
Resource, one Response, one Outcome. One paper typically yields **2–5 rows**. If you have twenty,
you are coding sentences rather than claims.

**Step 4 — For every element, paste the sentence you took it from.** Verbatim, copied from the
PDF. If you cannot find a sentence, **do not code the element.** This is the single most important
rule: it is what makes your coding comparable to the machine's, which is required to quote a
source span for every element it produces.

**Step 5 — Mark your confidence**: `high` / `medium` / `low`. Low-confidence rows are still
useful — they tell us where the task itself is hard, which is a finding.

### What to do when you are unsure

| Situation | Do this |
|---|---|
| The claim is implied but never stated | Code it, mark confidence `low`, and note *"implied"* |
| Two elements seem to be the same thing | Code the one the text supports better; note the other in `notes` |
| The paper reports no outcome at all | Code Context/Resource/Response, leave Outcome blank. Richmond included one such study |
| You cannot tell Response from Outcome | Apply test (a). Still stuck → code as Outcome, mark `low`, and note the ambiguity |
| The paper is about something else entirely | Code nothing and note why. That is data too |

### Rules that must not be broken

1. **Never discuss a paper with your co-coder while coding it.** Not "how did you read this one?"
   Not anything. Independence is the entire value of the exercise.
2. **Never look at machine output** until both workbooks are finished and saved.
3. **Never go back and change an earlier paper** because of something you learned later. If your
   understanding shifts, finish the batch and note it — a change of rule mid-way makes the
   agreement statistic uninterpretable.
4. **Save a copy after each paper.** Workbooks get lost.

---

## Part 4 — After both of you finish

### Step 1 — Compute agreement *before* anyone looks at the machine

This is the number the project needs. Two coders, same papers, no machine involved.

```powershell
cd "D:\Realist-Evidence-Synthesis\Realist-Evidence-Synthesis-V2"
res gold-template --compare
```

Expect three figures:

- **Positive specific agreement (= F-measure)** on the elements. This — not Cohen's κ — is the
  correct statistic here, because there is no defined number of "negative" cases when you are
  marking spans of text. Hripcsak & Rothschild (*JAMIA* 12:296–298, 2005) prove the equivalence.
- **Krippendorff's α** on the *role* assigned (Context / Resource / Response / Outcome), where the
  category set *is* fixed. Interpret against α ≥ .800 firm, .667–.800 tentative only.
- **Gwet's AC1** alongside it, because the roles are unevenly distributed and κ-family statistics
  behave badly at skewed prevalence.

### Step 2 — Adjudicate, in writing

Sit down together **only now**. For every disagreement:

1. Both state your reading and the sentence it came from.
2. Agree a resolution, or record that you could not.
3. **Write down the rule** the resolution implies — e.g. *"a measured group-level result is an
   Outcome even when phrased as a learner experience"*.

That list of rules is a genuine research output. It is the coding frame that does not currently
exist for realist synthesis anywhere in the published literature, and it is what would let a third
person code the remaining papers consistently.

### Step 3 — Only then, compare against the machine

Now the machine's coverage number becomes interpretable: not *"the system found 37 of 46"*, but
*"the system found 37 of 46 where two trained humans agreed with each other on X%"*.

---

## Part 5 — How long it takes, and how to brief the second coder

**Time:** roughly **45–60 minutes per paper** for the first two, dropping to **25–30** once the
distinctions are familiar. For 10 papers, budget **6–8 hours per coder**, spread over several
sessions — coding fatigue degrades agreement.

**Briefing the second coder — send them exactly this:**

> We are checking whether an automated system reads research papers the way two trained people do.
> I need you to read 10 papers and code the causal claims in each, using a fixed five-element
> scheme. It takes about 6–8 hours in total and you can spread it over a week.
>
> The important constraint: you must work **independently**. Do not discuss the papers with me
> while coding, and do not look at any system output. The whole point is to find out what two
> people agree on without influencing each other, so anything that couples our judgements destroys
> the result.
>
> Everything you need is in `docs/HUMAN_CODING_GUIDE.md`. Read Parts 1–3 first — about 90 minutes,
> including two sections of the Richmond paper. Then open your workbook and start.
>
> When we are both done we will compute our agreement, then sit down and resolve every
> disagreement in writing. That written list of resolutions is itself a contribution — nothing
> like it exists in the published realist-review literature.

**What to tell the professor:** the honest framing is that this establishes the **human ceiling**
the evaluation has been missing, and that it also produces a **coding frame for CMOC extraction**,
which no published realist review provides — Richmond included, who report that a second reviewer
checked the coding but give no agreement statistic at all.

---

## Part 6 — Why the numbers you produce matter more than any code change

Two runs of this pipeline over a **byte-identical graph** returned concept coverage of 41/46 and
45/46 — a four-item swing with no change to the system at all, caused entirely by the LLM used to
score it. Against that noise, no engineering improvement we could make is measurable.

Your two workbooks fix that. They give:

1. **A ceiling** — how well two humans agree, which is the only fair target for a machine.
2. **A denominator that is not model-produced** — every current agreement figure is one model
   judging another.
3. **An adjudicated coding frame** — the written rules from Step 2, which is publishable in its own
   right.

Nothing in the codebase can substitute for this, and no amount of API credit buys it.
