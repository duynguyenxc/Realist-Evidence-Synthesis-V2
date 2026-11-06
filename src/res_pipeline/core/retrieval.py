"""Lexical retrieval (BM25), so the synthesis stage stops depending on a small corpus.

``ARCHITECTURE.md`` section 4 is blunt about the current design: "the composer receives
the entire evidence pack inline, which is **context stuffing, not retrieval**". That is
sound at Richmond's 28 papers and 94 CMOC statements. Prof. Zheng's 2026-10-30 assignment
asks for a broader search; `res search` already returns hundreds of records for the new
topic, and a thousand statements will neither fit nor be attended to evenly.

**Why BM25 and not embeddings.** ``IMPROVEMENT_PLAN.md`` section 3 dropped embedding-based
concept clustering with citations, and its reasoning transfers: cosine similarity measures
relatedness rather than equivalence. That section also records Han et al.
(arXiv:2502.11371) finding plain RAG beats Community-GraphRAG on detail-oriented and
single-hop queries — which is what selecting supporting statements is. BM25 adds no model,
no embedding store, no new dependency, and is deterministic, so a retrieved evidence pack
is reproducible from the database alone. Robertson & Zaragoza (2009, *FnTIR* 3(4),
333-389) is the reference; k1=1.5 and b=0.75 are their standard defaults.

**It is off at Richmond's size, by design.** ``select()`` returns the input unchanged when
there are fewer candidates than the cap, so the published run's evidence pack is
byte-identical and no figure moves. Retrieval only engages on a corpus big enough to need
it, which is the only corpus where its own selection bias would matter.
"""

from __future__ import annotations

import math
import re
from collections import Counter

_WORD = re.compile(r"[a-z0-9]+")
_STOP = frozenset("""a an and are as at be been but by for from had has have in into is it its of
on or that the their then there these this to was were which who will with within without
study studies research paper review results finding findings""".split())


def tokenize(text: str) -> list[str]:
    return [w for w in _WORD.findall((text or "").lower()) if w not in _STOP and len(w) > 2]


class BM25:
    """Okapi BM25 over a fixed set of documents.

    Small and self-contained on purpose: a dependency for one scoring function would be a
    poor trade in a pipeline whose reproducibility argument is part of the paper.
    """

    def __init__(self, documents: list[str], *, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1, self.b = k1, b
        self.docs = [tokenize(d) for d in documents]
        self.n = len(self.docs)
        self.lengths = [len(d) for d in self.docs]
        self.avg_len = (sum(self.lengths) / self.n) if self.n else 0.0
        self.freqs = [Counter(d) for d in self.docs]
        df: Counter[str] = Counter()
        for doc in self.docs:
            df.update(set(doc))
        # Robertson-Sparck Jones idf with the +0.5 smoothing, floored at a small positive
        # value so a term in almost every document cannot contribute a negative score.
        self.idf = {
            term: max(1e-6, math.log(1 + (self.n - count + 0.5) / (count + 0.5)))
            for term, count in df.items()
        }

    def scores(self, query: str) -> list[float]:
        q = tokenize(query)
        out = [0.0] * self.n
        for i, freq in enumerate(self.freqs):
            length = self.lengths[i] or 1
            total = 0.0
            for term in q:
                f = freq.get(term, 0)
                if not f:
                    continue
                denom = f + self.k1 * (1 - self.b + self.b * length / (self.avg_len or 1))
                total += self.idf.get(term, 0.0) * f * (self.k1 + 1) / denom
            out[i] = total
        return out

    def top_k(self, query: str, k: int) -> list[tuple[int, float]]:
        ranked = sorted(enumerate(self.scores(query)), key=lambda x: x[1], reverse=True)
        return ranked[:k]


def select(items: list[dict], query: str, *, text_key: str, cap: int) -> tuple[list[dict], dict]:
    """The ``cap`` most relevant items, or every item when there are fewer than ``cap``.

    Returns the selection plus a report, because a synthesis built on a subset must be
    able to say so: a realist review that silently dropped two thirds of its evidence
    would be unreportable, and the omission belongs in the paper's limitations.
    """
    if len(items) <= cap:
        return items, {"retrieved": False, "candidates": len(items), "selected": len(items)}
    index = BM25([str(it.get(text_key) or "") for it in items])
    picked = index.top_k(query, cap)
    chosen = [items[i] for i, _ in picked]
    return chosen, {
        "retrieved": True,
        "candidates": len(items),
        "selected": len(chosen),
        "method": "BM25(k1=1.5,b=0.75)",
        "query": query,
        "score_range": [round(picked[-1][1], 3), round(picked[0][1], 3)],
        "dropped": len(items) - len(chosen),
    }
