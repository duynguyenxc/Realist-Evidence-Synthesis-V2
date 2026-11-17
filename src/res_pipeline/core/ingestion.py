"""Corpus ingestion: PDF/abstract -> provenance-bearing text units.

Every downstream claim must be traceable to a verbatim span. This module converts
each study's source (full-text PDF or abstract-only metadata) into an ordered list
of :class:`TextUnit` whose ``char_start``/``char_end`` index into the study's
canonical full text, which is persisted alongside the units so spans can always be
re-resolved and audited.

Chunking: paragraph-aware sliding window (~1200 tokens ≈ 4800 chars target,
200-char overlap) — mirrors GraphRAG defaults while keeping paragraph boundaries
where possible so quotes rarely straddle units.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from pydantic import BaseModel, Field
from pypdf import PdfReader

from res_pipeline.core.registry import StudyRecord

TARGET_UNIT_CHARS = 4800
UNIT_OVERLAP_CHARS = 200


class TextUnit(BaseModel):
    """A contiguous chunk of a study's canonical text, with absolute offsets."""

    text_unit_id: str  # e.g. "S007-tu-0003"
    study_id: str = Field(pattern=r"^S\d{3}$")
    sequence: int = Field(ge=0)
    char_start: int = Field(ge=0)
    char_end: int
    text: str


class IngestedStudy(BaseModel):
    study_id: str
    source_kind: str
    canonical_text: str
    canonical_sha256: str
    n_pages: int | None
    text_units: list[TextUnit]


def _extract_pdf_text(pdf_path: Path) -> tuple[str, int]:
    reader = PdfReader(str(pdf_path))
    pages = [(page.extract_text() or "") for page in reader.pages]
    # Normalize whitespace conservatively: join pages with form-feed markers kept
    # OUT of the canonical text (offsets must be stable and quote-friendly).
    text = "\n\n".join(pages)
    # Strip NUL and the other C0 control characters a PDF text layer can carry.
    #
    # PostgreSQL rejects 0x00 in a text field outright ("PostgreSQL text fields cannot
    # contain NUL (0x00) bytes"), which killed the first ingest of the emotion corpus
    # after several hundred papers. The Richmond benchmark never hit it: its 28 PDFs are
    # publisher-clean, while a corpus pulled off the open web is not. Removing these
    # cannot shift a quote offset, because every character removed is unprintable and
    # none is part of any span a reviewer would ever cite.
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip(), len(pages)


def _chunk(study_id: str, text: str) -> list[TextUnit]:
    units: list[TextUnit] = []
    n = len(text)
    start = 0
    sequence = 0
    while start < n:
        end = min(start + TARGET_UNIT_CHARS, n)
        if end < n:
            # Prefer to break at a paragraph boundary within the last 20% of the window.
            window_floor = start + int(TARGET_UNIT_CHARS * 0.8)
            break_at = text.rfind("\n\n", window_floor, end)
            if break_at == -1:
                break_at = text.rfind(". ", window_floor, end)
                break_at = break_at + 1 if break_at != -1 else end
            end = break_at if break_at > start else end
        units.append(
            TextUnit(
                text_unit_id=f"{study_id}-tu-{sequence:04d}",
                study_id=study_id,
                sequence=sequence,
                char_start=start,
                char_end=end,
                text=text[start:end],
            )
        )
        if end >= n:
            break
        start = max(end - UNIT_OVERLAP_CHARS, start + 1)
        sequence += 1
    return units


def ingest_study(study: StudyRecord) -> IngestedStudy:
    """Produce canonical text + provenance-bearing text units for one study."""
    if study.source_kind == "fulltext_pdf" and study.pdf_path:
        text, n_pages = _extract_pdf_text(Path(study.pdf_path))
    else:
        # Abstract-only record: canonical text is title + abstract, clearly labelled.
        parts = [f"TITLE: {study.title}"]
        if study.abstract:
            parts.append(f"ABSTRACT: {study.abstract}")
        text, n_pages = "\n\n".join(parts), None

    return IngestedStudy(
        study_id=study.study_id,
        source_kind=study.source_kind,
        canonical_text=text,
        canonical_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        n_pages=n_pages,
        text_units=_chunk(study.study_id, text),
    )
