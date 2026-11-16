"""Literature search and acquisition — the stage this pipeline never had.

Until 2026-11-06 the corpus arrived by hand: Richmond's 28 papers were placed in
``data/`` and the pipeline began at ingestion. Grepping ``pubmed|openalex|crossref|
scopus|eric`` across the whole source tree returned nothing. That was tolerable for
reproducing one published review and is not tolerable for Prof. Zheng's 2026-10-30
assignment, which asks in as many words for the pipeline to "conduct a broader
literature search" on a topic nobody has assembled a corpus for.

**Sources.** OpenAlex and Crossref, because both are free, neither needs a key, and
both are open-catalogue rather than licensed — so the search is reproducible by anyone
reading the paper, which Scopus and Web of Science are not. OpenAlex is primary: it
carries abstracts (as an inverted index), open-access status and concept tags. Crossref
is the cross-check, since it indexes some publishers OpenAlex is thin on.

**Reproducibility is the point, not a side effect.** RAMESES II requires a realist review
to report its search well enough to be repeated. Every query is written to ``search_log``
with its parameters, timestamp, result count and the exact URL issued, so the search
section of the paper can be generated from the record rather than remembered.

**Politeness.** Both APIs ask for a contact address to get the faster pool. Set
``OPENALEX_MAILTO`` in ``.env`` to opt in; without it the search still works, just in the
slower pool. It is never inferred from the environment, because an email address in a
third-party URL should be a decision, not a default.

**OpenAlex stopped being keyless on 2026-02-13** (verified against the live API on
2026-11-16, which answers every anonymous request with a notice saying so). Anonymous
requests now share **one $0.10/day budget per network IP address**; a free key raises it
to $1/day for its holder. A search request costs **$0.001**, so a run of this module's
size — a dozen or two queries — fits inside the anonymous budget, and that is how it is
run here. Set ``OPENALEX_API_KEY`` in ``.env`` if a key is ever obtained; nothing else
changes. Two consequences worth carrying into the manuscript: the claim that this search
is reproducible *without credentials* is no longer strictly true, and a run can fail
midway if somebody else on the same network has spent the shared budget.

**Where the query is matched matters more than the query.** OpenAlex ``search`` covers
title, abstract AND full text, which sounds generous and is not: the same boolean query
that matches 2,843 works in title-and-abstract matches **124,175** when full text is
included (measured 2026-11-16), and since only the top-N by relevance are retrieved, the
extra 121,332 are what the top-N is drawn from. ``title_abstract_only`` — the default for
the ``search`` command — restricts matching to ``title_and_abstract.search``. Boolean
``AND``/``OR``/``NOT`` (uppercase) and quoted phrases work in both modes.
"""

from __future__ import annotations

import json
import os
import re
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field

USER_AGENT = "res-pipeline/1.0 (realist evidence synthesis; academic research)"
_OPENALEX = "https://api.openalex.org/works"
_CROSSREF = "https://api.crossref.org/works"


@dataclass
class Candidate:
    """One search hit, before any screening decision has been made about it."""

    source: str
    source_id: str
    doi: str | None
    title: str
    authors: list[str] = field(default_factory=list)
    year: int | None = None
    journal: str | None = None
    publisher: str | None = None
    url: str | None = None
    type: str | None = None
    abstract: str | None = None
    cited_by: int | None = None
    open_access: bool | None = None
    oa_pdf_url: str | None = None

    def to_metadata(self) -> dict:
        """The shape ``core/registry.build_registry`` already reads.

        Emitting the existing format rather than a new one means screening, ingestion and
        everything downstream work on a searched corpus with no changes at all.
        """
        return {
            "record_id": f"{self.source}:{self.source_id}",
            "source": self.source,
            "source_id": self.source_id,
            "doi": self.doi,
            "title": self.title,
            "authors": self.authors,
            "year": self.year,
            "journal": self.journal,
            "publisher": self.publisher,
            "url": self.url,
            "type": self.type,
            "abstract": self.abstract,
            "doi_source": self.source if self.doi else None,
            "title_source": self.source,
            "abstract_source": self.source if self.abstract else None,
            # Open-access status and the PDF link the catalogue gives are the ONLY thing
            # `res acquire` can work from, and this method used to drop both: the search
            # retrieved them, the corpus file discarded them, and acquire fell back to the
            # DOI landing page, so it reported every record as having an open-access full
            # text. That ratio is something a realist review reports as a finding about
            # its evidence base, so getting it wrong is not a cosmetic loss.
            "open_access": self.open_access,
            "oa_pdf_url": self.oa_pdf_url,
            # Retrieved anyway, and a realist review with no budget needs some defensible
            # way to order a purposive sample. Kept rather than thrown away.
            "cited_by": self.cited_by,
            # A catalogue record with a DOI, a year and an abstract is about as good as
            # metadata gets before the PDF is read; one missing all three is a stub.
            "confidence": round(
                0.4 + 0.2 * bool(self.doi) + 0.2 * bool(self.abstract) + 0.2 * bool(self.year), 2),
            "notes": None,
        }


class SearchUnavailable(RuntimeError):
    """A catalogue declined to serve this request, after retrying.

    Separate from a programming error on purpose: a realist search runs a dozen
    queries and one catalogue hiccup must not be indistinguishable from a malformed
    query, because the first is retried and the second is fixed.
    """


def _get(url: str, *, retries: int = 5) -> dict:
    """One GET with backoff.

    Backoff is 3s, 6s, 12s, 24s rather than 1s, 2s, 4s. Measured on 2026-11-16:
    OpenAlex answers anonymous search with HTTP 503 and "Anonymous search is paused
    while the search cluster recovers from heavy load" during busy periods, and that
    outlasts a 7-second retry budget. A free API key is documented as the fix; waiting
    also works, and waiting needs no credentials.
    """
    last: Exception | None = None
    detail = ""
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            last = exc
            try:  # the body carries the catalogue's own explanation; keep it
                body = json.loads(exc.read().decode("utf-8"))
                detail = str(body.get("message") or body.get("error") or "")[:300]
            except Exception:  # noqa: BLE001 - diagnostics only
                detail = ""
            if exc.code not in (429, 500, 502, 503, 504):
                break  # a 400 is a bad query; retrying it just wastes the budget
            # OpenAlex says how long to wait ("Please retry in 34s"). Obeying the
            # catalogue beats guessing at it, and it is the difference between a
            # ten-query search completing and failing half way.
            told = re.search(r"retry in (\d+)\s*s", detail)
            time.sleep(min(90, int(told.group(1)) + 2) if told else 3 * 2 ** attempt)
        except Exception as exc:  # noqa: BLE001 - network, retried below
            last = exc
            time.sleep(3 * 2 ** attempt)
    raise SearchUnavailable(
        f"search request failed after {retries} tries: {url}\n  {last}"
        + (f"\n  catalogue said: {detail}" if detail else ""))


def _mailto() -> str:
    return (os.getenv("OPENALEX_MAILTO") or "").strip()


def _api_key() -> str:
    """An OpenAlex key, if one was obtained. Absent is a supported state, not an error."""
    return (os.getenv("OPENALEX_API_KEY") or "").strip()


def _inverted_to_text(index: dict | None) -> str | None:
    """OpenAlex stores abstracts as {word: [positions]}; rebuild the sentence."""
    if not index:
        return None
    positions: list[tuple[int, str]] = []
    for word, where in index.items():
        positions.extend((p, word) for p in where)
    if not positions:
        return None
    return " ".join(word for _, word in sorted(positions))


def search_openalex(query: str, *, from_year: int | None = None, to_year: int | None = None,
                    limit: int = 200, types: tuple[str, ...] = (),
                    title_abstract_only: bool = True) -> list[Candidate]:
    """Search OpenAlex, paging until ``limit`` or the results run out.

    ``title_abstract_only`` sends the query as the ``title_and_abstract.search`` filter
    instead of the ``search`` parameter. See the module docstring for why that is the
    default: full-text matching inflates the candidate set roughly 44-fold on a typical
    blocked boolean query, and only the top-N by relevance are ever retrieved.
    """
    out: list[Candidate] = []
    cursor = "*"
    per_page = min(200, max(1, limit))
    filters = []
    if from_year:
        filters.append(f"from_publication_date:{from_year}-01-01")
    if to_year:
        filters.append(f"to_publication_date:{to_year}-12-31")
    if types:
        filters.append("type:" + "|".join(types))
    while len(out) < limit:
        params = {"per-page": per_page, "cursor": cursor,
                  "select": "id,doi,display_name,publication_year,primary_location,type,"
                            "open_access,best_oa_location,authorships,cited_by_count,"
                            "abstract_inverted_index"}
        # A comma separates filters, so a query containing one would be split in half and
        # silently change meaning. Boolean queries use OR, not commas; refuse rather than
        # guess, because the damage is a corpus that looks fine and answers a different
        # question.
        if title_abstract_only:
            if "," in query:
                raise ValueError(
                    "title_and_abstract.search cannot carry a comma (OpenAlex splits "
                    f"filters on it). Rewrite the query with OR: {query!r}")
            filters.append(f"title_and_abstract.search:{query}")
        else:
            params["search"] = query
        if filters:
            params["filter"] = ",".join(filters)
        if _mailto():
            params["mailto"] = _mailto()
        if _api_key():
            params["api_key"] = _api_key()
        data = _get(f"{_OPENALEX}?{urllib.parse.urlencode(params)}")
        results = data.get("results") or []
        if not results:
            break
        for w in results:
            loc = (w.get("primary_location") or {}).get("source") or {}
            out.append(Candidate(
                source="openalex",
                source_id=(w.get("id") or "").rsplit("/", 1)[-1],
                doi=(w.get("doi") or "").replace("https://doi.org/", "") or None,
                title=w.get("display_name") or "",
                authors=[(a.get("author") or {}).get("display_name", "")
                         for a in (w.get("authorships") or [])][:25],
                year=w.get("publication_year"),
                journal=loc.get("display_name"),
                publisher=loc.get("host_organization_name"),
                url=w.get("doi") or w.get("id"),
                type=w.get("type"),
                abstract=_inverted_to_text(w.get("abstract_inverted_index")),
                cited_by=w.get("cited_by_count"),
                open_access=((w.get("open_access") or {}).get("is_oa")),
                oa_pdf_url=((w.get("best_oa_location") or {}).get("pdf_url")
                            or (w.get("open_access") or {}).get("oa_url")),
            ))
            if len(out) >= limit:
                break
        cursor = (data.get("meta") or {}).get("next_cursor")
        if not cursor:
            break
    return out


def search_crossref(query: str, *, from_year: int | None = None, to_year: int | None = None,
                    limit: int = 200) -> list[Candidate]:
    """Search Crossref. Used as a cross-check on OpenAlex, not as the primary source."""
    out: list[Candidate] = []
    cursor = "*"
    rows = min(100, max(1, limit))
    while len(out) < limit:
        # `sort`/`order` are NOT optional here. Measured 2026-11-16: with `cursor` and no
        # sort, Crossref returns an arbitrary index-ordered slice -- the first 100 hits for
        # "emotion regulation intervention university students" came back 1999-2002, and
        # the top result without a cursor (relevance-ordered) was a 2024 trial of exactly
        # that intervention. Taking the top N of an unsorted deep page is not a search,
        # and nothing in the response says the ranking was dropped.
        params = {"query": query, "rows": rows, "cursor": cursor,
                  "sort": "score", "order": "desc"}
        filters = []
        if from_year:
            filters.append(f"from-pub-date:{from_year}-01-01")
        if to_year:
            filters.append(f"until-pub-date:{to_year}-12-31")
        if filters:
            params["filter"] = ",".join(filters)
        if _mailto():
            params["mailto"] = _mailto()
        data = _get(f"{_CROSSREF}?{urllib.parse.urlencode(params)}").get("message", {})
        items = data.get("items") or []
        if not items:
            break
        for it in items:
            issued = ((it.get("issued") or {}).get("date-parts") or [[None]])[0]
            abstract = it.get("abstract")
            if abstract:
                abstract = re.sub(r"<[^>]+>", " ", abstract)
                abstract = re.sub(r"\s+", " ", abstract).strip()
            out.append(Candidate(
                source="crossref",
                source_id=it.get("DOI", ""),
                doi=it.get("DOI"),
                title=(it.get("title") or [""])[0],
                authors=[" ".join(filter(None, [a.get("given"), a.get("family")]))
                         for a in (it.get("author") or [])][:25],
                year=issued[0] if issued else None,
                journal=(it.get("container-title") or [None])[0],
                publisher=it.get("publisher"),
                url=it.get("URL"),
                type=it.get("type"),
                abstract=abstract,
                cited_by=it.get("is-referenced-by-count"),
            ))
            if len(out) >= limit:
                break
        cursor = data.get("next-cursor")
        if not cursor:
            break
    return out


def _title_key(title: str) -> str:
    """A title reduced to what survives reformatting between catalogues."""
    t = unicodedata.normalize("NFKD", title or "").lower()
    t = re.sub(r"[^a-z0-9 ]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def deduplicate(records: list[Candidate]) -> tuple[list[Candidate], dict]:
    """Collapse duplicates, DOI first and then normalised title.

    A named deduplication step is a PRISMA/RAMESES reporting requirement — the flow
    diagram has to state how many records were removed as duplicates — and
    ``PROFESSOR_VISION_AND_GAPS.md`` section 2 has listed it as missing since before the
    new assignment. Earlier records win, so the primary source is kept over the
    cross-check, and the fuller abstract is carried across rather than dropped.
    """
    by_doi: dict[str, Candidate] = {}
    by_title: dict[str, Candidate] = {}
    kept: list[Candidate] = []
    removed_doi = removed_title = 0
    for rec in records:
        doi = (rec.doi or "").strip().lower() or None
        tkey = _title_key(rec.title)
        existing = by_doi.get(doi) if doi else None
        if existing is None and tkey:
            existing = by_title.get(tkey)
        if existing is not None:
            if doi and doi in by_doi:
                removed_doi += 1
            else:
                removed_title += 1
            if not existing.abstract and rec.abstract:
                existing.abstract = rec.abstract
            if not existing.doi and rec.doi:
                existing.doi = rec.doi
            continue
        kept.append(rec)
        if doi:
            by_doi[doi] = rec
        if tkey:
            by_title[tkey] = rec
    return kept, {"input": len(records), "kept": len(kept),
                  "removed_by_doi": removed_doi, "removed_by_title": removed_title}


def write_metadata_jsonl(records: list[Candidate], path) -> int:
    """Write the searched corpus where ``build_registry`` will find it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec.to_metadata(), ensure_ascii=False) + "\n")
    return len(records)


def as_dicts(records: list[Candidate]) -> list[dict]:
    return [asdict(r) for r in records]


def acquire_fulltext(records: list[Candidate], dest_dir, *, limit: int = 0,
                     dry_run: bool = True, log=print) -> dict:
    """Download the open-access PDFs the catalogue points at.

    Only open-access copies the catalogue itself links, never a paywall bypass: the
    review can report exactly which full texts were obtainable and which were not, which
    is itself a finding a realist review should state rather than hide.

    ``dry_run`` is the DEFAULT, deliberately. This writes many files from the open web,
    so it should be an explicit decision each time rather than something a pipeline step
    does on the way past. A dry run reports what would be fetched and from where.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    have = [r for r in records if r.oa_pdf_url]
    if limit:
        have = have[:limit]
    result = {"candidates": len(records), "with_oa_pdf": len(have),
              "fetched": 0, "failed": 0, "files": [], "errors": []}
    if dry_run:
        result["dry_run"] = True
        return result
    for rec in have:
        name = (rec.doi or rec.source_id).replace("/", "_").replace(":", "_") + ".pdf"
        path = dest_dir / name
        if path.exists():
            result["files"].append(str(path))
            continue
        try:
            req = urllib.request.Request(rec.oa_pdf_url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=60) as resp:
                blob = resp.read()
            if not blob.startswith(b"%PDF"):
                raise ValueError("response is not a PDF")
            path.write_bytes(blob)
            result["fetched"] += 1
            result["files"].append(str(path))
            log(f"    {len(blob) // 1024:>6} KB  {name}")
        except Exception as exc:  # noqa: BLE001 - the open web; recorded, not raised
            result["failed"] += 1
            result["errors"].append({"doi": rec.doi, "url": rec.oa_pdf_url, "error": str(exc)[:160]})
        time.sleep(0.5)
    return result
