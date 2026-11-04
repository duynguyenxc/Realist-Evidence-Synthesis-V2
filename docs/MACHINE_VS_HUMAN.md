# Machine vs human: our final result beside Richmond's final result

*Duy Nguyen — 2026-09-30. Every figure is from run `verify-edcbf790` and from
`gold/richmond_gold_v3.json`, and is reproducible from `outputs/RESULTS.html`. Where a number was
produced by a language model rather than by arithmetic, the table says so.*

The question this file answers: **taking the review Richmond's five reviewers published as the human
result, and the review our system produced as the machine result, how do the two compare — not on one
headline number, but at every level Richmond actually published?**

---

## 0. First, the honest asymmetry — the two sides were not asked to do the same job

This must be stated before any number, because every comparison below inherits it.

| | Richmond's team | Our system |
|---|---|---|
| Records screened | **7,097** titles/abstracts (MEDLINE 3,066 · PsycINFO 2,779 · ERIC 1,037 · CINAHL 745; 530 duplicates removed) | **28** — the included set, handed to it |
| Where the 28 came from | Their own search and two-stage screening | Given as a fixed corpus |
| People | 5 authors (AR did the protocol, searches, initial extraction, synthesis, figures, first draft; RP, SG, NC checked) | 1 RA supervising; agents did the analytic work |
| Standards | PROSPERO CRD42017072029, RAMESES | RAMESES-reportable artefacts produced |

**So we reproduce steps 3–7 of Richmond's seven-step algorithm, not steps 1–2.** The system's
screening sensitivity of 100% is measured on a corpus in which *every* record is a known include —
it can prove the system does not throw away a good paper, and it can prove nothing about whether the
system would have *found* those 28 among 7,097. Specificity is measured separately against a
distractor pool, which is a weaker substitute for the real search.

This is a scope decision, not an oversight, and it is the one limitation that changes what the paper
may claim.

---

## 1. Process: which of Richmond's operations does the machine actually perform?

| # | Richmond's step (human) | Our stage | Reproduced? |
|---|---|---|---|
| 1 | Background search + expert consensus → initial programme theory | Protocol & initial-theory seed | **Partly** — seeded from the published theory, not built from scratch |
| 2 | Theory-driven database search with supplementary term expansion | — | **No** — corpus fixed to Richmond's 28 |
| 3 | Two-stage screening: contribution to theory, then rigour | Two-model screening vote + human adjudication of the uncertain | **Yes** |
| 4 | Lead coder extracts CMOCs; a second reviewer checks **every** paper | Extractor drafts → a model in a different family critiques → one revision → span grounding | **Yes**, and mechanised as designed |
| 5 | Cross-study comparison; recurrent CMOC patterns identified | Normalisation + Leiden community detection + demi-regularity/contradiction detection | **Yes**, and this is where the system does something the humans did not (see §6) |
| 6 | Build the programme theory by context | Theory synthesis, 9 context chains, version 12 | **Yes** |
| 7 | Report with an audit trail | PRISMA flow, CMOC evidence table, programme theory, 1,085 audit events | **Yes** |

---

## 2. Volume: what each side produced

| | Richmond (published) | Our system | Note |
|---|---|---|---|
| Included studies | 28 | 28 | same set by construction |
| Student contexts | **5** (E02–E06) | **9** context chains | ours are finer-grained, not the same cut |
| Named concepts | **46** scored (in Figures 2–3 and §3.2) | **183** canonical concepts, from **547** quoted mentions | Richmond published a distilled figure; we publish the full graph |
| Causal links | **40** arrows | **459** typed relations | |
| Mechanisms | 28 mechanism entities, **authored by the reviewers** | **8** clusters, **discovered by Leiden from the data** | the methodological contribution |
| CMOCs | statements in §3.2.1–3.2.5 + Figures 2–3 | **94**, each carrying its verbatim sentence | |
| Recurrent patterns | described in prose | **32** demi-regularities, **20** contradictions, counted | |
| Provenance | data-extraction forms (Appendix S1) | every element resolved to a character offset in the source PDF | |

---

## 3. Result: the five levels of comparison, weakest evidence last

### Level 1 — the same papers? *(arithmetic)*
**100% sensitivity, 28/28** (95% CI 87.7%–100%). 26 auto-included; S018 and S028 were flagged
uncertain and routed to a human, who included them. The design working as intended.
*Caveat: no true negatives in this corpus — see §0.*

### Level 2 — the same concepts? *(language-model judged)*

| Tier | Result | What it means |
|---|---|---|
| Same realist role (**lead with this**) | **34/46 = 73.9%** (95% CI 58.9%–85.7%) | our concept means the same thing *and* sits in the same C/M/O role |
| Role-crossing allowed | 41/46 = 89.1% | 7 of these sit under a different realist role than Richmond assigned |
| **One concept may claim only one Richmond concept** | **28/46 = 60.9%** | see §5 — this is the figure comparable to a human coder |
| Per-sample spread over 3 samples | 67.4% – 78.3% | the judge is not stable to ±5 pp |

> **All three figures above are superseded by §5.1** (matcher fixed 2026-11-04): 39/46 role-crossing, **32/46** same-role, **26/46** one-to-one. Left in place because the published papers quote them.

Not recovered: **E05** (negative coping / low self-efficacy), **E06** (mixed-knowledge group), and in
the September 23 run also **E31/E32/E34** (the pressure/fear items). Traced to cause: the strings
"self-efficacy" and "self-confidence" occur **zero times** across all 28 source papers, and
"pressure" occurs once, as *blood pressure cuff*. **Richmond's reviewers brought those two contexts in
from outside the corpus** — from theory and expert consensus, which their method explicitly permits
("responses … can be theorised from existing theories of learning"). A system restricted to verbatim
grounding structurally cannot produce them. This is a finding about the method, not a bug.

**Measured properly on 2026-11-04**, over all 28 canonical texts and all 547 extracted entities.
The corpus barely contains affect at all:

| term | occurrences in all 28 papers | papers |
|---|---|---|
| `emotion` | **0** | 0 |
| `self-efficacy` | **0** | 0 |
| `anxious`, `worry` | **0** | 0 |
| `anxiety` | 1 | 1 |
| `fear` | 2 | 2 |
| `frustrat` | 4 | 2 |

And **the extractor captured affect wherever it did occur**: 9 of 117 `Mechanism_Response` instances
carry affective content — *novice frustration*, *reduced fear during referral*, *stress from pager
interruption*, *intended intrinsic motivation under time pressure*, *enjoyment and challenge*. So
the gap is not a blind spot in the ontology or the prompts, both of which already admit emotion
(`Mechanism_Response` is defined as "the cognitive **or emotional** reaction … panic, frustration").
It is the corpus, plus the verbatim constraint.

> **The consequence matters more than the finding, and it points at the new topic.** Richmond
> **cannot** tell us how well this pipeline handles emotion, because there is almost no emotion in
> Richmond to handle. Prof. Zheng's 2026-10-30 assignment is *emotional awareness and regulation*.
> So this is not a known weakness carried into the new topic — it is an **unmeasured capability**,
> and the new corpus will be full of exactly the vocabulary this one lacks. The real architectural
> gap it exposes is **retroduction without a quote**: Richmond's humans reached E05/E31/E32/E34 by
> theory-driven inference, which realist synthesis requires and verbatim grounding forbids.

### Level 3 — the same causal structure? *(arithmetic)*

| Tier | Result | Honest reading |
|---|---|---|
| Type-level (does the pattern occur anywhere?) | 39/40 = 97.5% | **near-unfailable** — only 8 distinct patterns exist in our graph and 7 in Richmond's. Never quote alone. |
| **Anchored** (same predicate, one endpoint the exact matched concept, other endpoint correct role) | **29/40 = 72.5%** (95% CI 56.1%–85.4%) | **the number to lead with.** 80.6% if you count only the arrows Richmond actually draws, excluding 4 transitive shortcuts. |
| Strict (both endpoints the exact matched concept) | **6/40 = 15.0%** | the honest floor. Bounded above by concept recall squared. |

### Level 4 — the same mechanisms? *(language-model judged)*
**19 of Richmond's 28 mechanism entities = 67.9%** (95% CI 47.6%–84.1%) align with one of the 8
clusters Leiden found. Richmond's mechanisms were written by people; ours were not written by anyone.

### Level 5 — the same programme theory? **This is "final result vs final result", and it is our weakest evidence.**

Richmond's final result is five context-specific chains. Ours is programme theory v12, 9 chains.
Correspondence, 0–1, scored per chain by a model:

| Richmond chain | Independent judge (different model family) | Judge from the composer's own family | Gap |
|---|---|---|---|
| PTS1 low domain knowledge | 0.933 | 0.863 | 0.07 |
| PTS2 high domain knowledge | 0.867 | 0.360 | **0.51** |
| PTS3 positive coping / self-efficacy | 0.800 | 0.327 | **0.47** |
| PTS4 negative coping / low self-efficacy | 0.700 | 0.580 | 0.12 |
| PTS5 mixed-knowledge group | 0.783 | 0.510 | 0.27 |
| **mean** | **0.817** | **0.528** | **0.29** |

Two judges given *identical inputs* differ by 0.29 on average and by roughly **half the scale** on
PTS2 and PTS3. Note the direction: the *independent* judge is the **more generous** one, so the
headline 0.817 is the higher of the two available numbers, not the conservative one.

**Therefore: no single programme-theory correspondence figure may be published.** The correct
statement is that theory-level correspondence is presently *unmeasured* — we have two model opinions
that disagree too much to average, and no human expert rating. This is the top of the "what I need
next" list.

### Level 6 — the same evidence behind each context? *(arithmetic — and this is the most uncomfortable table)*

Concept-level agreement says the two reviews *name* similar things. This asks whether they name them
**from the same papers**.

| Richmond context | Studies Richmond assigns | Studies we assign | Same paper |
|---|---|---|---|
| E02 low knowledge | 22 | 4 | **2** (S016, S020) |
| E03 high knowledge | 7 | 4 | **1** (S020) |
| E04 positive coping | 5 | 0 | 0 |
| E05 negative coping | 4 | 1 | **1** (S015) |
| E06 mixed-knowledge group | 9 | 4 | 0 |
| **total context–study assignments** | **47** | **13** | **4** |

On Richmond's largest context — 22 of 28 papers — the two reviews agree on **2 papers**. So the
system reaches recognisably similar *conclusions* from a substantially *different* reading of which
paper supports what. For a realist review, where the claim is "this mechanism, evidenced in these
studies", that matters as much as the concept count, and it is not yet reported in the paper.

---

## 4. Faithfulness — the one place the machine clearly exceeds the human record

| | Result |
|---|---|
| Elements resolving to a verbatim span in the source PDF | **93.0%** (95% CI 90.6%–95.0%), 509/547 |
| …at an exact, unmodified span | 9.7% |
| …after whitespace/hyphenation normalisation | 92.8% cumulative |
| …fuzzy (≥70% similarity) | 97.1% cumulative |
| Untyped relations quarantined for human review | 3 of 459 |

Every claim carries a character offset. A reader can check any sentence in the review against the
original PDF in seconds. Richmond kept data-extraction forms (Appendix S1) but the published review
cannot be audited at this granularity. **Quote the 9.7% exact figure alongside the 93.0%; describing
93.0% as "exact" is the error an earlier draft made.**

---

## 5. Machine vs the two human coders — what "beats a human" does and does not mean

Two research assistants coded all 28 papers independently against the same 46-item frame.

| Coder | Concepts found | Elements coded |
|---|---|---|
| Coder A (human) | 30/46 (65%) | 192 |
| Coder B (human) | 28/46 (61%) | 139 |
| Both humans agreed | 28/46 (61%) | 130 agreed |
| **The system** | **34/46 (74%)** → **32/46 (69.6%)** after §5.1 | 547 mentions |

Positive specific agreement between the two humans: **0.785**. Role agreement is deliberately not
reported — the reference sheet states each code's category, so two coders picking the same code are
*forced* to the same role; it would measure the lookup table, not judgement.

**The necessary correction.** The system's 34 matches rest on only **28 distinct canonical
concepts** — four concepts are each counted for two or three of Richmond's:

| One concept of ours | counted as recovering |
|---|---|
| `mech:knowledge-elaboration` | E20 *understanding*, E27 *build understanding*, E39 *build upon what they already know* |
| `mech:cognitive-overload-or-confusion` | E23 *frustrated*, E33 *stress*, E45 *confusion* |
| `outc:improved-diagnostic-accuracy` | E25, E46 |
| `outc:learning-and-schema-integration` | E28, E40 |

A human coder cannot do this: the frame gives one code per element, so human matching is one-to-one
by construction. Applying the same constraint, the system scores **28/46 (60.9%)** — **equal to
Coder B and to the both-agreed set, not above them.**

**The defensible claim is therefore non-inferiority, not superiority:** the system matches two human
coders working under time pressure, at 547 quoted mentions against their 192 and 139, with every
mention auditable. Given that human screeners themselves err about 10.8% of the time,
non-inferiority is the right target — but the word "exceeds" should not appear.

Two further matcher defects found on 2026-09-30, both correctable in `verification/metrics.py`:
`E03` (*high* domain knowledge) was matched to `cont:knowledge-deficits` with the stored rationale
"…aligns with high clinical domain-specific knowledge **as the opposite**", and `E24` was matched with
"…is the opposite of non-analytical reasoning, **so it does not match**" — both recorded as
`matched: true`, and E24 is inside the headline 34. A rationale that states a non-match must not be
allowed to set a match.

### 5.1 Fixed 2026-11-04 — and the one-to-one figure was already one too high

**The matcher is fixed.** `verification/metrics.py` now refuses a `matched: true` whose own rationale
states a non-match or asserts opposite polarity, in all three judging passes (within-role,
cross-role recovery — which previously had no guard of any kind — and community alignment).
Refusals are returned in `refuted_matches` rather than dropped. The root cause was a hole in the
prompt, not a dishonest judge: the instruction forbade "merely adjacent or broader" concepts and
said **nothing about polarity**, so an antonym on the same dimension read as construct identity. All
three prompts now forbid it, with these two cases as the worked examples. The guard was calibrated
against all 46 stored rationales and flags **E03 and E24 and nothing else** — zero false positives
(`tests/test_core_logic.py` holds both verbatim rationales as a regression test).

**The effect was recounted over the stored verdicts, not re-judged.** Re-running the judge would mix
the fix with judge variance, which this very section measures at 67.4%–78.3% across three samples;
a deterministic recount isolates it.

| | published | corrected | certainty |
|---|---|---|---|
| Role-crossing allowed | 41/46 | **39/46** | certain — both codes leave every tier |
| Same realist role | 34/46 | **32/46** | certain |
| **One concept may claim only one** | **28/46** | **26/46** | certain, and see below |
| Relation recovery | — | drops | **bounded, not computed**: exactly 3 of 40 scored relations have E03 or E24 as an endpoint (R02, R06, R07 — R06 has both), so at most 3/40 = 7.5 pp. The exact figure needs a verification re-run |

**Two separate errors each cost one concept, and only one of them was the matcher.**

- **E24** → `mech:reasoning-strategy-shift`, which **no other gold code claims**. The guard removes
  it, so the one-to-one figure loses one. This is the matcher defect.
- **E03** → `cont:knowledge-deficits`, which **E02 also claims** — and the over-merge table above
  **omits this pair**. So `34 − 10 + 4 = 28` should have been `27`: the published one-to-one figure
  was already one too high, independently of the matcher. The guard removing E03 and the one-to-one
  constraint collapsing the pair land on the same number, which is why the correction is −2 and not
  −3.

**What this does to the claim, stated plainly.** At **26/46** the system is no longer *equal* to
Coder B (28/46) — it is **two concepts below Coder B and four below Coder A (30/46)**. Non-inferiority
is still the right claim, but it now rests on **overlapping confidence intervals on a denominator of
46, not on parity**, and must be written that way. The rule stands and is now stronger: **the word
"exceeds" must not appear.** The qualitative asymmetry in §6 is untouched — 547 grounded mentions
against 192 and 139, every one traceable — and that, not the count, is what the architecture buys.

---

## 6. What each side did that the other did not

**Only the machine:**
- Discovered its mechanisms bottom-up (Leiden over the concept graph) instead of authoring them
- Counted 32 demi-regularities and 20 contradictions explicitly, rather than describing patterns in prose
- Grounded every element to a character offset, making the whole review auditable
- Wrote 1,085 audit events, so any figure can be traced to the call that produced it
- Produced 94 configurations from 26 papers in one run, and correctly declined to invent any for the 2 abstract-only records

**Only the humans:**
- Found the 28 papers among 7,097 records
- Brought in two contexts (self-efficacy/coping) that are **absent from the corpus text** — theory-driven retroduction, which realist method permits and verbatim grounding forbids
- Judged methodological rigour, removing 2 papers as lacking rigour and 2 as not contributing to theory
- Distilled 46 concepts into 5 teachable contexts; our 183 concepts and 9 chains are less parsimonious

---

## 7. One-paragraph answer, if only one paragraph is wanted

From the same 28 papers, with no access to Richmond's answer key, the system independently reached
Richmond's central claim — that the same teaching resource helps or hinders depending on the
learner's prior knowledge — and reproduced their analytic operations from screening through
programme theory. It recovers all 28 studies, resolves 93.0% of its claims to a verbatim span
(9.7% at an exact span), reconstructs 34 of Richmond's 46 concepts in the same realist role
(28 under a one-to-one constraint, matching two human coders rather than exceeding them), and
recovers 29 of their 40 causal links with at least one endpoint anchored (6 exactly). It does not
recover the two contexts Richmond imported from theory rather than from the papers, it agrees with
Richmond on only 4 of 47 context–study assignments, and the theory-level correspondence cannot yet be
stated as a number because two judges differ by 0.29. The claim the evidence supports is
**faithfulness and non-inferiority**, not reproduction.

---

## 8. What is needed before any of this is published

1. **Expert human rating of the programme-theory chains.** Two models disagree by 0.29; this is the one gap that blocks the headline result.
2. **An injective concept matcher**, and a guard so a rationale stating a non-match cannot set `matched: true`.
3. **A decision on the search.** Either reproduce Richmond's 7,097-record screen on a held-out corpus, or state the descope in the limitations with the specificity evidence that replaces it.
4. **Report the context–study overlap (§3 Level 6).** It is computed and currently unreported.
5. **Human ratification of the 7 role-crossing matches** now counted in the role-tolerant 41/46.
