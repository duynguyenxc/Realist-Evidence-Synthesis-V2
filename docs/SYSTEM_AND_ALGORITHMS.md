# System, Algorithms and Reasoning — what this pipeline actually is

> **The question this document answers.** *"What algorithm do you use? What is the architecture?
> How does the system reason? What is the GraphRAG? What tools, what database, what models, what
> libraries?"*
>
> It is written **from the source code**, verified by reading every module under `src/res_pipeline/`
> and every file in `config/`, not from earlier design documents. Where a previous document claimed
> something the code does not do, this one says so and corrects it. A methods paper cannot survive a
> reviewer opening the repository and finding a different system than the one described.
>
> Written 2026-09-23. Supersedes the technology claims in `ARCHITECTURE.md` (see §7).

---

## 1. One paragraph

The pipeline is a **staged, deterministic Python orchestration** in which each stage makes a small
number of **schema-constrained single-turn LLM calls** and writes typed rows to PostgreSQL. There is
no agent loop, no planner, no tool-calling, and no conversational state: every "agent" is one
request and one structured response. The only genuinely iterative component is a **one-round
Self-Refine** in CMOC extraction. The only non-trivial algorithm is **Leiden community detection**
over a co-occurrence graph of extracted concepts. Everything else — screening combination,
demi-regularity detection, contradiction detection, span resolution, and every deterministic
verification metric — is ordinary Python and SQL.

That is a smaller claim than "agentic GraphRAG multi-agent framework", and it is the one the code
supports. Section 6 states precisely what may and may not be claimed.

---

## 2. The architecture, stage by stage

Orchestration is `cli.py` calling functions in sequence. State lives entirely in PostgreSQL; nothing
is held in memory between stages.

```
data/ (28 PDFs + metadata)
   |
   |  [1] INGEST          pypdf -> whitespace-normalised canonical text + SHA-256
   |                      sliding window 4800 chars / 200 overlap, paragraph-preferring
   v
 canonical_texts, text_units                                       (no LLM)
   |
   |  [2] SCREEN          two models vote independently; union-of-includes
   v
 screening_decisions  ---- uncertain ---->  HITL-1  (res adjudicate)
   |
   |  [3] EXTRACT         draft -> critique -> revise (Self-Refine, 1 round)
   |                      -> per-CMOC support score -> consistency check
   |                      -> deterministic span resolution + span repair
   v
 cmocs, entity_instances, typed_relations  ---->  HITL-2  (res validate-cmocs)
   |
   |  [4] NORMALIZE       LLM clusters labels into canonical concepts, batches of 40
   v
 concept_families
   |
   |  [5] COMMUNITIES     Leiden over the concept co-occurrence graph, then one LLM
   |                      call per community to name and define it
   v
 conceptual_entities  (the "emergent mechanisms")
   |
   |  [6] SYNTHESIZE      pure Python: demi-regularities and contradictions
   v
 demi_regularities, contradictions  ---->  HITL-3  (resolve contradictions)
   |
   |  [7] PROGRAMME       one LLM call over the whole evidence pack
   v
 programme_theories  ---->  HITL-4  (sign-off)
   |
   |  [8] VERIFY          5 deterministic metrics + 3 LLM-judged, K=3 sampled
   v
 outputs/runs/verify-*/ , outputs/RESULTS.html
```

The human is not decoration: four checkpoints gate the scientific state, and every mutation is
written to `audit_log`, which is what RAMESES II's transparency requirement ("what was done, why and
how") asks for.

---

## 3. The reasoning, precisely

### 3.1 Every LLM call is the same shape

All model access goes through one function, `core/llm.py::call_structured()`:

- `client.beta.chat.completions.parse()` with a **Pydantic response_format** (OpenAI structured
  outputs), so the model cannot return anything outside the schema;
- `seed = 20260714` fixed; `temperature = 0` where the tier declares one (gpt-5.5 accepts only its
  default, so determinism there rests on the seed alone);
- **no retry, no self-consistency, no tool use, no message history.**

So "8 agents" means 8 **role prompts**, not 8 autonomous processes. `core/agents.py` concatenates a
shared-expertise string with a role string to form a system-prompt prefix. **Four of the eight
personas in `config/agents.yaml` are never loaded by any code path** — `screening_reviewer`,
`cmoc_extractor`, `concept_normaliser` and `audit_verifier` are superseded by hardcoded system
strings in their modules. That is a real inconsistency, and the honest description is *"a staged
pipeline with role-conditioned prompts at each stage"*.

### 3.2 The model tiers, and what each actually does

From `config/models.yaml`, cross-checked against every `tier=` call site in the source:

| Tier | Model | Used for |
|---|---|---|
| `screening_primary` | gpt-5.4-mini, T=0 | First screening vote |
| `screening_second_vote` | **gpt-4.1-mini**, T=0 | Second vote, deliberately a different family |
| `extraction` | gpt-5.5 | CMOC draft and revision |
| `gold_coder` | gpt-5.4, T=0 | Draft critique, consistency check, per-paper reference coding |
| `extraction_verifier` | gpt-5.4-mini, T=0 | Quote-supports-claim score; entity and community matching in verification |
| `normalization` | gpt-5.4-mini, T=0 | Concept clustering; community naming |
| `synthesis` | gpt-5.5 | Programme theory composition, and its same-family judge |
| `independent_judge` | **gpt-4.1-mini**, T=0 | Cross-family judge for programme-theory correspondence (added 2026-09-23) |

**A circularity that must be disclosed.** `models.yaml` describes `gold_coder` as deliberately
independent of the extraction tier so the reference coding is unbiased. But the `gold_coder` tier is
**called twice inside the extraction loop** — it critiques the draft and it runs the consistency
check. The model that authors the per-paper reference coding is therefore the same model that helped
rewrite the output being scored against it. That is a closed loop, and it is why
`gold/per_paper_gold/` cannot be called a gold standard (see `VERIFICATION_PROTOCOL.md` §3.2).

### 3.3 Where the only real reasoning loop is

CMOC extraction (`plugins/realist/cmoc_extraction.py`) is the one multi-step component:

1. **Draft** — zero-shot, against a hand-written system prompt that spends twelve lines on the
   Context / Mechanism-Resource / Mechanism-Response / Outcome boundary, plus a mandatory verbatim
   quote for every element.
2. **Critique** — a second model (`gold_coder`) names specific defects in the draft.
3. **Revise** — one round, in memory, before anything is persisted. This is **Self-Refine**
   (Madaan et al., 2023, NeurIPS, arXiv:2303.17651) with a single iteration and an *external*
   critic, which is closer to **Reflexion** (Shinn et al., 2023, NeurIPS, arXiv:2303.11366) than to
   self-critique, since the critic is a different model.
4. **Verify** — per CMOC, a support score in [0,1] for whether the quote sustains the claim.
5. **Consistency check** — a second independent pass, again `gold_coder`, playing the role of
   Richmond's second reviewer.

A revision is accepted only if it retains at least half the draft's configurations, which stops the
critic from silently deleting a paper's findings.

**Why the initial programme theory is not injected here.** An earlier iteration fed the IPT into
per-paper extraction and CMOC yield collapsed from about 3.5 to about 1 per study — the model
anchored on the theory instead of reading the paper. The IPT was reverted to driving **synthesis
only**, which is also what Richmond describe (§2.2): extraction is data-driven, theory comes after.

### 3.4 Span grounding is arithmetic, not judgement

Every extracted element carries `verbatim_quote`, `char_start`, `char_end`. Resolution is pure
Python in three escalating tiers — exact `str.find`; a normalised match over a lowercased,
de-hyphenated, whitespace-collapsed view of the text **with an index map back to original offsets**
(`plugins/realist/span_repair.py::_normalize_with_map`); and finally a `difflib.SequenceMatcher`
longest-common-block covering at least 70% of the quote, stamped `match_kind='fuzzy'`. Quotes that
still fail are flagged and surfaced at HITL-2, never fabricated.

This is what makes the faithfulness metric deterministic, and why it must be reported in tiers
rather than as one number (`VERIFICATION_PROTOCOL.md` §2.2).

---

## 4. The algorithms, named

| Component | Algorithm | Implementation | Parameters |
|---|---|---|---|
| Text segmentation | Sliding window with paragraph-boundary preference in the final 20% | `core/ingestion.py` | 4800 chars, 200 overlap |
| Screening combination | **Union of includes** across two models; either include wins; uncertain routes to a human | `core/screening.py::_combine` | recall-first by design |
| Span resolution | Exact match, then normalised match with index map, then `difflib` longest common block | `plugins/realist/span_repair.py` | fuzzy threshold 0.70 |
| Concept normalization | Regex key collapse, then **LLM clustering in batches of 40 alphabetically sorted labels**; two batches merge only if they independently emit the same canonical label | `plugins/realist/normalization.py` | batch 40 |
| Graph construction | Undirected weighted graph; nodes = canonical concepts; edges = same-CMOC co-occurrence (w=1.0) and typed relation (w=2.0) | `graph/communities.py::_load_graph` | `networkx.Graph` |
| Community detection | **Leiden** (Traag, Waltman & van Eck, 2019, *Scientific Reports* 9:5233) | `graspologic.partition.leiden` | resolution 1.0, seed 20260714, weighted, minimum community size 2 |
| Community naming | One LLM call per community over member labels | `graph/communities.py` | `normalization` tier |
| Demi-regularities | Cartesian product of (context x driver x outcome x polarity) per CMOC at concept-family granularity, bucketed, kept when at least 2 **distinct studies** support it | `plugins/realist/synthesis.py` | threshold 2 studies |
| Contradictions | Same driver concept carrying CMOCs of both polarities | `plugins/realist/synthesis.py` | — |
| Interval estimation | **Clopper–Pearson exact binomial** (1934, *Biometrika* 26(4), 404–413) | `verification/stats.py` | 95%, via `scipy.stats.beta` |
| Judge aggregation | K=3 sampling; majority vote for recall metrics, mean for scored metrics; per-sample range reported | `verification/metrics.py` | K=3 |

**There is no embedding anywhere.** Concept normalization is LLM clustering over sorted label
batches, not vector similarity. No cosine distance, no HDBSCAN, no agglomerative clustering, no
vector index. `config/models.yaml` previously declared a `text-embedding-3-small` tier that no code
ever called; it has been removed rather than left standing as a false claim.

---

## 5. What "GraphRAG" means here — and what it does not

Microsoft's GraphRAG (Edge, Trinh, Cheng, Bradley, Chao, Mody, Truitt, Metropolitansky, Ness &
Larson, 2024, arXiv:2404.16130) is, in outline: LLM entity/relation extraction into a graph, then a
Leiden partition, then **hierarchical community summarisation**, then **query-time retrieval** —
local search over entity neighbourhoods, global search by map-reduce over community reports —
supported by a **vector store**.

Measured against that, honestly:

| GraphRAG component | Here |
|---|---|
| LLM extraction into a typed graph | **Yes** — ontology-constrained and quote-grounded. Arguably stronger than GraphRAG's, because every node carries a source span. |
| Leiden community detection | **Yes** — `graspologic`, the same library, resolution 1.0, seed fixed. |
| Community reports | **Partial** — one flat LLM pass per community over member *labels only*. It never sees the underlying text, quotes, or relations, and there is **no hierarchical multi-level summarisation**, which is GraphRAG's actual contribution. |
| Vector store / embeddings | **No.** None exists. |
| Local / global search | **No.** The programme-theory composer receives `json.dumps(evidence_pack)` — every demi-regularity, every contradiction, every sufficiently-supported CMOC, every community. That is **context stuffing, not retrieval**: nothing is queried, ranked, scored or selected. |
| "GraphRAG-in-the-loop" extraction | **No.** `plugins/realist/guidance.py::_known_concepts_block` is `SELECT entity_type, label, count(*) FROM entity_instances GROUP BY 1,2 ORDER BY 3 DESC LIMIT 24` — the 24 globally most frequent labels, unrelated to the paper being extracted. It is a vocabulary hint, not retrieval. |
| `graphrag` package | Declared in `pyproject.toml`, **never imported**. |

**The defensible phrasing** is *"ontology-constrained knowledge-graph construction with Leiden
community detection and LLM community labelling"*, or *"GraphRAG-inspired"* with the differences
stated. Calling it GraphRAG without qualification will not survive a methods reviewer who opens the
repository — and `pyproject.toml`'s description line and `verification/dashboard.py`'s header both
currently make that unqualified claim.

The honest framing is also the more interesting one: the emergent conceptual entities are
**data-derived mechanisms** with no human counterpart in Richmond's review — which is the novelty
the professor named — and that claim does not require GraphRAG's retrieval layer at all.

---

## 6. The tool stack, settled

| Layer | Choice | Why |
|---|---|---|
| Language | Python 3.11 | — |
| LLM access | `openai` SDK, `beta.chat.completions.parse` with Pydantic schemas | Structured outputs make a malformed result impossible rather than merely unlikely |
| Models | gpt-5.5 (extraction, synthesis), gpt-5.4 / gpt-5.4-mini (critique, verification, normalization), gpt-4.1-mini (second screening vote, independent judge) | Two families are deliberately kept in play so screening and judging are not single-family |
| System of record | **PostgreSQL 18** (`realist_synthesis`, on `D:/Appdata/pg`) | Typed rows, transactions, and an `audit_log` that satisfies RAMESES II |
| Graph analytics | `networkx` for construction, **`graspologic`** for Leiden (`networkx` Louvain as fallback) | The same Leiden implementation Microsoft GraphRAG uses |
| Statistics | `scipy.stats` (Clopper–Pearson via the Beta quantile) | Exact intervals at small n and at the 0 and 1 boundaries |
| Graph export | Parquet via `pandas` + `pyarrow`; Neo4j 5 as an exploration mirror | Parquet is the canonical portable artefact; Neo4j is for looking, not for computing |
| Validation | `pydantic` v2 | Types the ontology at the boundary |
| CLI | `typer` + `rich` | 17 commands |
| Review console | `fastapi` + `uvicorn` | `res webui`, the four HITL checkpoints as browser pages |
| PDF ingest | `pypdf` | — |
| Reporting | `python-docx`, `matplotlib`, and a self-contained HTML writer (`core/results_export.py`) | — |

**Declared but never imported:** `langchain`, `langchain-openai`, `langgraph`,
`langgraph-checkpoint-postgres`, `graphrag`, `jinja2`. **Used but not declared:** `openai`,
`graspologic`, `scipy`, `matplotlib`, `python-docx`. `pyproject.toml` needs both corrections — the
second matters most, because on a clean install `graspologic` is absent, `_partition`'s bare
`except Exception` swallows the `ImportError`, and the pipeline **silently falls back to NetworkX
Louvain while every document still says Leiden**.

---

## 7. Corrections to `ARCHITECTURE.md`

`ARCHITECTURE.md` is the project's stated design of record and is contradicted at several
load-bearing points. Recorded here so the manuscript is written from reality.

| `ARCHITECTURE.md` says | The code |
|---|---|
| "One **LangGraph** state machine orchestrates all agents over a shared typed state"; "LangGraph `interrupt()`/`Command(resume)` at 4 checkpoints" | LangGraph is never imported. Orchestration is `cli.py`; HITL is separate CLI subcommands and FastAPI form posts. |
| "**text-embedding-3-small** vectors"; "GraphRAG index build (BYOG + Leiden + embeddings)" | No embedding is ever computed. |
| "GraphRAG **global/local search** grounds narrative" | The composer is given the entire evidence pack inline. |
| "Microsoft **GraphRAG** kept for communities/query, loaded via BYOG" | `graphrag` declared, never imported. |
| "`gpt-5.4` extraction/synthesis" | `models.yaml` says gpt-5.5; gpt-5.4 is the critic/gold tier. |
| "Independent **human** per-paper CMOC gold (2 coders, Cohen's κ)" | `gold/per_paper_gold/` is LLM output; `compute_kappa` exists and is called from nowhere. |
| "PROVIDES: Intervention → Mechanism_Resource" | `config/ontology.yaml` range is `[Mechanism_Resource, Mechanism_Response]`. |
| "prompts versioned in `config/prompts/`" | That directory is empty; prompts are string literals with hand-maintained version constants. |
| Repo layout lists `core/state.py`, `core/orchestrator.py`, `core/hitl.py`, `core/audit.py`, `plugins/realist/contradiction.py`, `graph/graphrag_adapter.py`, `graph/motifs.py`, `verification/gold_standard.py`, `verification/faithfulness.py` | None of these nine files exists. |

---

## 8. What to claim in the paper

**Defensible as written:**

- A staged, human-in-the-loop pipeline that performs the analytic operations of a realist review —
  screen, extract CMOCs, normalise concepts, detect recurrent patterns and contradictions, compose a
  programme theory — with **every element anchored to a verbatim source span**.
- **Ontology-constrained extraction** in which the realist Context / Mechanism-resource /
  Mechanism-response / Outcome distinction (Dalkin et al., 2015, *Implementation Science* 10:49) is
  enforced at the type level — which RAMESES II requires be made explicit and which most published
  realist reviews leave implicit.
- **Leiden community detection over the concept graph yielding data-derived mechanisms** with no
  human counterpart in the source review. This is the genuine novelty.
- **An evaluation that separates deterministic from model-judged metrics**, reports exact intervals,
  and reports judge spread for the latter. Given that 75% of published LLM-qualitative studies report
  no model parameters at all (Kempny et al., 2026, *BMC Med Res Methodol* 26:137), this alone is a
  contribution.
- **Full computational disclosure**: models, snapshots, temperature, seed, complete prompts, run ids.

**Not defensible without qualification:** "GraphRAG" (§5); "multi-agent" in the autonomous sense
(§3.1); "LangGraph orchestration" (§7); any claim of a vector store or retrieval; "human gold
standard" for the per-paper coding (§3.2).

**Open engineering defects**, listed so they are fixed rather than discovered:

1. `res init-db` has no DDL for `cmocs`, `entity_instances` or `typed_relations`, so the repository
   cannot rebuild its own schema on a fresh database.
2. `res feedback` violates a NOT NULL constraint, so the HITL-to-few-shot loop has never recorded a
   single correction despite being documented as an implemented feature.
3. `normalization.build_concept_families`, `graph/communities` and `synthesize` issue unfiltered
   `DELETE`s that discard other runs' rows — and, in the case of `contradictions`, every human HITL-3
   resolution.
4. Canonical ids are built from `entity_type[:4]`, and `"Mechanism_Resource"[:4]` equals
   `"Mechanism_Response"[:4]` equals `"Mech"`, so two concepts of different realist roles sharing a
   slug would silently merge. Not currently firing; one unlucky label away.
5. Relations whose subject or object label the extractor did not emit as an entity are silently
   skipped rather than stored as `UNTYPED_CANDIDATE`, contrary to both the module docstring and
   `config/ontology.yaml`.
