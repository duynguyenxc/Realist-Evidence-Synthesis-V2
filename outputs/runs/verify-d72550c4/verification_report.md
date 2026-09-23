# Verification Report — System vs Richmond et al. (2020)

External benchmark evaluation (separate from the production pipeline).

## 1. Screening (title/abstract)
- Gold includes: 28
- Auto-include sensitivity: **92.9%** (26/28)
- False excludes: **0** 
- Uncertain → HITL-1: 2 ['S018', 'S028']
- Final sensitivity after HITL-1: **100.0%**
- Screening run scored: `screen-4e53160c`
- Sensitivity only — every corpus study is a gold include, so this metric has no true negatives and cannot detect over-inclusion. Specificity is measured separately against the distractor pool (`res precision-test`).

## 2. Entity coverage (46 scored gold entities, gold v3)
- Recall: **97.8%** (45/46) — LLM-judged semantic matching (human audit required before publication)
- Within Richmond's realist role: 38; role-crossing: 7
- Per-sample range over 3 judge samples: 80.4%–89.1%

## 3. Relation coverage (40 scored gold relations)
- Strict recall (exact concept match on both endpoints): **0.0%** (0/40)
- Anchored recall (one exact endpoint + correct role on the other): **72.5%** (29/40)
- Type-level recall (causal pattern recovered — predicate + endpoint roles): **97.5%** (39/40)
- Type-level recall only asks whether each gold pattern occurs anywhere in the graph. With so few distinct patterns on either side, any non-trivial extraction scores near 100%. Never quote type_recall without anchored_recall and recall beside it.
- Missed at the strict tier only (many are recovered at the anchored tier): R01, R02, R03, R04, R05, R06, R07, R08, R09, R10, R11, R12, R13, R14, R15, R16, R17, R18, R19, R20, R21, R22, R23, R24, R25, R26, R27, R28, R29, R30, R31, R32, R33, R34, R35, R36, R37, R38, R39, R40

## 4. Citation faithfulness (deterministic; three tiers, never conflated)
- Exact character span: **9.3%** (48/517)
- Exact **or** normalized (PDF de-hyphenation, whitespace, quote marks): **92.8%**
- All tiers including fuzzy (>=70% overlap): **96.5%** (499/517)
- Tier breakdown: {'exact': 48, 'normalized': 432, 'fuzzy': 19, 'unresolved': 18}
- Quote the `strict` (exact-span) figure as the headline; `faithfulness` counts normalized and fuzzy matches too and must never be described as exact.

## 5. Programme-theory correspondence (5 gold PTS chains)
- Independent-family judge: **0.87** (range 0.86–0.89)
- Composer's own model family: **0.56**
- Self-preference gap (same-family minus independent): **-0.309**
- Scored by a judge from a different model family than the composer; the same-family score is reported alongside so the self-preference gap is visible. Human expert rating still required before publication.

| PTS | Score | Rationale |
|---|---|---|
| PTS1 | 1.00 | PTS1 concerns students with low or poorly organised clinical knowledge, matching the SYSTEM context of novices with limited or poorly organi |
| PTS2 | 0.90 | PTS2 addresses students with high clinical domain-specific knowledge, corresponding to SYSTEM contexts of partially prepared learners with i |
| PTS3 | 0.82 | PTS3 focuses on positive coping strategies and self-confidence, with interventions involving teaching resources allowing mistakes and real c |
| PTS4 | 0.73 | PTS4 involves negative coping strategies or lacking self-confidence, with mechanisms of fear, stress, increased cognitive load, and negative |
| PTS5 | 0.90 | PTS5 concerns students with different knowledge levels within a group, with interventions promoting knowledge retention and feedback, mechan |