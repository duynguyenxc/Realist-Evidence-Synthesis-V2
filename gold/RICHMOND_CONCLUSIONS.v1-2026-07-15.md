# The Human Standard — What Richmond et al. (2020) Did and Concluded

_This is the human benchmark our system is measured against, stated in plain language: both **how**
Richmond's team worked and **what** they concluded after manually reviewing 28 studies. Source:
Richmond A, Cooper N, Gay S, Atiomo W, Patel R. (2020), "The student is key: a realist review of
educational interventions to develop analytical and non-analytical clinical reasoning ability",
Medical Education 54(8):709–719 — Methods §2, Results §3, and Figures 1–3. Facts below are drawn
from the paper itself; where a statement is our interpretation it is marked as such._

---

## Part A — How Richmond's team did it (their method)

Richmond ran a **realist review**, not a conventional meta-analysis. A realist review does not ask
"does this intervention work on average?"; it asks **"what works, for whom, in what circumstances,
and why?"** The unit of analysis is the **Context–Mechanism–Outcome configuration (CMOC)**: a
statement that *in context C, an intervention triggers mechanism M, producing outcome O*.

Their process, step by step:

1. **Protocol & standards.** The review was pre-registered on PROSPERO (CRD42017072029) and followed
   the **RAMESES** publication standards for realist synthesis throughout — the recognised quality
   standard for this method.
2. **Initial programme theory (IPT).** Before searching exhaustively, they did background scoping and
   combined it with expert opinion and researcher experience to draft an *initial programme theory* —
   a first guess at the mechanisms, to be tested and refined against the literature. (This is why a
   realist review is iterative, not linear.)
3. **Search.** Four databases were searched — **MEDLINE, CINAHL, ERIC and PsycINFO** — and articles
   relevant to the developing theory were selected as appropriate. The PRISMA flow is their Figure 1.
4. **Screening & inclusion.** **149 full texts were retrieved.** Of these, **25 met the inclusion
   criteria**, **2 more were added from reference-list searching**, and **1 more from a subsequent
   search** on strategies to promote knowledge retention — **28 included studies** in total (3 UK,
   11 Canada, 3 USA, and others).
5. **CMOC extraction & iterative synthesis.** From each study they extracted context–mechanism–outcome
   configurations, and synthesised them across studies through an iterative process, continually
   refining the programme theory as evidence accumulated.
6. **Outputs.** The synthesis produced **CMO configurations for determining effectiveness**, an
   **initial programme theory (Figure 2)** and a **refined programme theory (Figure 3)** — the human
   process outputs our system is checked against.

The key student-level factors their synthesis surfaced as the contexts that change an intervention's
effect were **pre-existing knowledge, self-confidence, and self-efficacy / coping**.

---

## Part B — The single headline conclusion

**The student is the key variable.** The same teaching intervention does *not* have the same effect
for everyone — its effect depends on the student's pre-existing knowledge, self-confidence and
ability to cope. A "one-size-fits-all" approach fails. Teachers must identify a student's knowledge
level *before* choosing a method, and should promote fast, intuitive (non-analytical) reasoning only
once novices have acquired enough knowledge.

Two named effects underpin this:
- **Expertise-reversal effect** — techniques that help novices can *reduce* learning for more
  experienced students.
- **Matthew effect** — students who already know more gain more from the same teaching.

## The conclusion is context-dependent, not a single ranking

A realist review does not produce one global "best pedagogy" ranking. Its conclusion is a set of
**context → effective / ineffective** verdicts, one per student group:

### Group 1 — Students with low / undeveloped knowledge (22 of 28 studies)
- ✓ **Works:** explicitly revealing and explaining an expert's reasoning; teaching pattern-recognition
  and step-by-step feature checking *together*.
- ✕ **Backfires:** watching an expert *without* an explanation (causes panic/resentment); forcing
  purely analytical reasoning (causes frustration).

### Group 2 — Students with high domain-specific knowledge (7 studies)
- ✓ **Works:** discussing expert reasoning; real/simulated cases that let them practise fast,
  intuitive reasoning at high accuracy.
- ✕ **Backfires:** directive teaching designed for novices (little benefit, even frustration) —
  the expertise-reversal effect.

### Group 3 — Students with positive coping / appropriate self-confidence (5 studies)
- ✓ **Works:** resources that allow safe mistakes; simulation and real-life scenarios → they feel
  grateful, build understanding → positive learning and more complete illness scripts.

### Group 4 — Students with negative coping / low self-confidence (4 studies)
- ✕ **Backfires:** the same simulation/real-patient encounters → fear, stress, pressure →
  increased cognitive load → poor illness-script formation, faulty future reasoning, negative
  learning outcomes.

### Group 5 — Groups with mixed / varied knowledge levels (9 studies)
- ✓ **Works:** accurate, timely feedback; strategies that promote long-term knowledge retention
  (e.g. test-enhanced learning) → learning increases regardless of starting level.
- ✕ **Backfires:** absent, incomplete or erroneous feedback → confusion → impaired reasoning.

---

## Part C — Why this is the right standard to compare against

Richmond published these conclusions as narrative CMOC statements plus Figures 2 & 3. They are
observable, human-generated **process outputs** — not just a final yes/no answer — which is exactly
what makes them usable to check whether an automated pipeline reaches the same verdicts *by the same
kind of reasoning*. The machine-checkable version of this document lives in
`gold/richmond_gold.json` (entities E01–E47, relations R01–R40, programme-theory chains PTS1–5); the
scored, side-by-side comparison with our system's output is the **Comparison** page.
