"""PostgreSQL access layer: schema, persistence, and audit logging.

PostgreSQL is the pipeline's single source of truth (ARCHITECTURE D5): study
registry, canonical texts, text units, decisions, HITL feedback, and the audit
log all live here. The parquet LKG and Neo4j mirror are derived artifacts.

Every mutation of scientific state MUST go through :func:`log_audit_event` so the
RAMESES II transparency requirement ("what was done, why and how") is satisfied
by construction.
"""

from __future__ import annotations

import json
from contextlib import contextmanager
from typing import Any, Iterator

import psycopg
from psycopg.rows import dict_row

from res_pipeline.core.config import get_settings
from res_pipeline.core.ingestion import IngestedStudy
from res_pipeline.core.registry import StudyRecord

SCHEMA_DDL = """
CREATE TABLE IF NOT EXISTS studies (
    study_id            TEXT PRIMARY KEY CHECK (study_id ~ '^S[0-9]{3}$'),
    record_id           TEXT NOT NULL,
    doi                 TEXT,
    title               TEXT NOT NULL,
    authors             JSONB NOT NULL DEFAULT '[]',
    year                INT,
    journal             TEXT,
    abstract            TEXT,
    source_kind         TEXT NOT NULL CHECK (source_kind IN ('fulltext_pdf','abstract_only')),
    pdf_path            TEXT,
    metadata_confidence REAL NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS canonical_texts (
    study_id        TEXT PRIMARY KEY REFERENCES studies(study_id),
    canonical_text  TEXT NOT NULL,
    canonical_sha256 TEXT NOT NULL,
    n_pages         INT,
    ingested_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS text_units (
    text_unit_id TEXT PRIMARY KEY,
    study_id     TEXT NOT NULL REFERENCES studies(study_id),
    sequence     INT NOT NULL,
    char_start   INT NOT NULL,
    char_end     INT NOT NULL,
    text         TEXT NOT NULL,
    UNIQUE (study_id, sequence)
);

CREATE TABLE IF NOT EXISTS screening_decisions (
    id           BIGSERIAL PRIMARY KEY,
    study_id     TEXT NOT NULL REFERENCES studies(study_id),
    stage        TEXT NOT NULL CHECK (stage IN ('title_abstract','full_text')),
    decider      TEXT NOT NULL,              -- model id or 'human:<name>'
    decision     TEXT NOT NULL CHECK (decision IN ('include','exclude','uncertain')),
    rationale    TEXT NOT NULL,
    confidence   REAL,
    run_id       TEXT NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS hitl_feedback (
    id           BIGSERIAL PRIMARY KEY,
    checkpoint   TEXT NOT NULL CHECK (checkpoint IN ('HITL-1','HITL-2','HITL-3','HITL-4')),
    subject_ref  TEXT NOT NULL,              -- study_id / cmoc_id / conflict_id / theory version
    action       TEXT NOT NULL CHECK (action IN ('approve','edit','reject')),
    feedback     TEXT,
    payload      JSONB,
    run_id       TEXT NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS audit_log (
    id          BIGSERIAL PRIMARY KEY,
    run_id      TEXT NOT NULL,
    actor       TEXT NOT NULL,               -- agent name, model id, or 'human:<name>'
    action      TEXT NOT NULL,
    subject_ref TEXT,
    detail      JSONB,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS token_usage (
    id            BIGSERIAL PRIMARY KEY,
    run_id        TEXT NOT NULL,
    tier          TEXT NOT NULL,
    model         TEXT NOT NULL,
    prompt_tokens INT NOT NULL,
    completion_tokens INT NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- The CMOC layer. These three tables carry the review's actual findings and were, until
-- 2026-09-23, created only as a side effect of the author's live database: no CREATE TABLE
-- for them existed anywhere in the repository, so `res init-db` followed by `res extract`
-- died with `relation "cmocs" does not exist` on any fresh machine. The definitions below
-- are transcribed from the live schema (pg_dump --schema-only), so an existing database is
-- unaffected and a new one is now reproducible from the repository alone.

CREATE TABLE IF NOT EXISTS cmocs (
    cmoc_id             TEXT PRIMARY KEY,
    study_id            TEXT NOT NULL REFERENCES studies(study_id),
    polarity            TEXT NOT NULL CHECK (polarity IN ('positive','negative','mixed')),
    narrative_statement TEXT NOT NULL,
    verifier_support    REAL,
    verifier_notes      TEXT,
    checker_agrees      BOOLEAN,
    checker_notes       TEXT,
    run_id              TEXT NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS entity_instances (
    entity_id       TEXT PRIMARY KEY,
    study_id        TEXT NOT NULL REFERENCES studies(study_id),
    cmoc_id         TEXT NOT NULL,
    entity_type     TEXT NOT NULL CHECK (entity_type IN
                        ('Context','Intervention','Mechanism_Resource',
                         'Mechanism_Response','Outcome')),
    label           TEXT NOT NULL,
    canonical_id    TEXT,
    verbatim_quote  TEXT NOT NULL,
    char_start      INT,
    char_end        INT,
    quote_resolved  BOOLEAN NOT NULL DEFAULT FALSE,
    match_kind      TEXT,
    extractor_model TEXT NOT NULL,
    prompt_version  TEXT NOT NULL,
    confidence      REAL,
    run_id          TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS typed_relations (
    relation_id       TEXT PRIMARY KEY,
    study_id          TEXT NOT NULL REFERENCES studies(study_id),
    cmoc_id           TEXT NOT NULL,
    predicate         TEXT NOT NULL,
    subject_entity_id TEXT NOT NULL REFERENCES entity_instances(entity_id),
    object_entity_id  TEXT NOT NULL REFERENCES entity_instances(entity_id),
    constraint_valid  BOOLEAN NOT NULL,
    run_id            TEXT NOT NULL,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS agent_feedback (
    id          BIGSERIAL PRIMARY KEY,
    agent_key   TEXT NOT NULL,              -- which agent the correction teaches
    wrong       TEXT,                       -- what the agent did (optional)
    correct     TEXT NOT NULL,              -- what it should have done
    note        TEXT,                       -- why, in the reviewer's words
    study_id    TEXT,
    run_id      TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS agent_feedback_agent_idx ON agent_feedback (agent_key, created_at DESC);

CREATE INDEX IF NOT EXISTS entity_instances_cmoc_idx ON entity_instances (cmoc_id);
CREATE INDEX IF NOT EXISTS entity_instances_canonical_idx ON entity_instances (canonical_id);
CREATE INDEX IF NOT EXISTS typed_relations_cmoc_idx ON typed_relations (cmoc_id);
"""



@contextmanager
def get_connection() -> Iterator[psycopg.Connection]:
    conn = psycopg.connect(get_settings().postgres.dsn, row_factory=dict_row)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_schema() -> None:
    with get_connection() as conn:
        conn.execute(SCHEMA_DDL)


def upsert_registry(studies: list[StudyRecord]) -> None:
    with get_connection() as conn:
        for s in studies:
            conn.execute(
                """
                INSERT INTO studies (study_id, record_id, doi, title, authors, year, journal,
                                     abstract, source_kind, pdf_path, metadata_confidence)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (study_id) DO UPDATE SET
                    record_id = EXCLUDED.record_id, doi = EXCLUDED.doi,
                    title = EXCLUDED.title, authors = EXCLUDED.authors,
                    year = EXCLUDED.year, journal = EXCLUDED.journal,
                    abstract = EXCLUDED.abstract, source_kind = EXCLUDED.source_kind,
                    pdf_path = EXCLUDED.pdf_path,
                    metadata_confidence = EXCLUDED.metadata_confidence
                """,
                (
                    s.study_id, s.record_id, s.doi, s.title, json.dumps(s.authors),
                    s.year, s.journal, s.abstract, s.source_kind, s.pdf_path,
                    s.metadata_confidence,
                ),
            )


def store_ingested_study(ingested: IngestedStudy) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO canonical_texts (study_id, canonical_text, canonical_sha256, n_pages)
            VALUES (%s,%s,%s,%s)
            ON CONFLICT (study_id) DO UPDATE SET
                canonical_text = EXCLUDED.canonical_text,
                canonical_sha256 = EXCLUDED.canonical_sha256,
                n_pages = EXCLUDED.n_pages,
                ingested_at = now()
            """,
            (ingested.study_id, ingested.canonical_text, ingested.canonical_sha256,
             ingested.n_pages),
        )
        conn.execute("DELETE FROM text_units WHERE study_id = %s", (ingested.study_id,))
        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO text_units (text_unit_id, study_id, sequence, char_start,
                                        char_end, text)
                VALUES (%s,%s,%s,%s,%s,%s)
                """,
                [
                    (u.text_unit_id, u.study_id, u.sequence, u.char_start, u.char_end, u.text)
                    for u in ingested.text_units
                ],
            )


def log_audit_event(
    run_id: str, actor: str, action: str, subject_ref: str | None = None,
    detail: dict[str, Any] | None = None,
) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO audit_log (run_id, actor, action, subject_ref, detail) "
            "VALUES (%s,%s,%s,%s,%s)",
            (run_id, actor, action, subject_ref, json.dumps(detail or {})),
        )
