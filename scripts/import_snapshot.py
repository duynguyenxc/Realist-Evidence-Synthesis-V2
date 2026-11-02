"""Rebuild the database from the last-known-good snapshot. Import, never re-run.

Why this exists
---------------
PostgreSQL was uninstalled from the original machine before a dump could be taken, so the
live `realist_synthesis` database is gone (see PROJECT_BACKUP_2026-09-30/RESTORE.md). Every
figure in the AERA 2027 submission comes from run `extract-fb045429` / `verify-edcbf790`.
Re-running the pipeline would cost money AND produce a *different* graph, invalidating those
figures. So the restore path is an import.

This script restores what the exports actually contain, and says plainly what they do not.

What is restored, and from where
--------------------------------
    cmocs                outputs/lkg/cmocs.parquet  + checker columns from exports/cmocs.csv
    entity_instances     outputs/lkg/entities.parquet
    typed_relations      outputs/lkg/relationships.parquet
    concept_families     outputs/lkg/communities.parquet (members exploded)
    conceptual_entities  outputs/exports/big_concepts.csv (the 8 Leiden mechanisms)
    screening_decisions  audit_trail.md, run screen-70a5d070 + the 2 HITL-1 includes
    audit_log            audit_trail.md (1,084 events)
    demi_regularities    RECOMPUTED deterministically (pure Python, no API)
    contradictions       RECOMPUTED deterministically (pure Python, no API)
    programme_theories   parsed from runs/report-b988e51b/programme_theory.md

What is NOT restored, because nothing exported it
-------------------------------------------------
    token_usage          per-call token/cost accounting — gone. Cost figures in the paper
                         come from the WALKTHROUGH, not from a queryable table.
    hitl_feedback        the per-item human decisions. The audit trail records that the
                         batches happened (HITL-1 n=2, HITL-3 n=9 then n=13, HITL-4 sign-offs)
                         but its `detail` column was TRUNCATED by the markdown renderer, so
                         the per-item payloads are unrecoverable.
    screening rationales same truncation: the decisions survive, the reasoning text does not.
    ipt_versions         gone; config/initial_programme_theory.yaml still holds the seed.
    agent_feedback       gone (2 corrections; both were filed under an unread key anyway).
    distractor_studies   gone; precision_test_report.md holds the results.

A hard prerequisite
-------------------
`res ingest` must have run under **pypdf 6.8-6.15**. Newer and older pypdf extract these
PDFs differently: 6.19 shifts 16 of 28 canonical texts by 1-23 characters and 4.2 by up to
525, which silently invalidates every stored char_start/char_end and would make citation
faithfulness collapse for no reason. This script verifies the canonical texts against the
sha256 values recorded in the July audit trail and refuses to import if they disagree.

Usage
-----
    res init-db && res ingest          # schema + corpus (deterministic, free)
    python scripts/import_snapshot.py  # this script
    res export-results                 # expect 547 / 459 / 94 / 8
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from res_pipeline.core.db import get_connection, init_schema  # noqa: E402

LKG = ROOT / "outputs" / "lkg"
EXPORTS = ROOT / "outputs" / "exports"
REPORT = ROOT / "outputs" / "runs" / "report-b988e51b"
AUDIT_MD = REPORT / "audit_trail.md"

# The run this snapshot belongs to. Every restored row is stamped with it so a future
# `extraction_vintages()` check sees one vintage, not a mixture.
EXTRACT_RUN = "extract-fb045429"
SCREEN_RUN = "screen-70a5d070"
SYNTH_RUN = "synth-2dfada15"
IMPORT_RUN = "import-snapshot-01"


def _say(msg: str) -> None:
    print(msg, flush=True)


# ─────────────────────────────── guard ────────────────────────────────────────


def verify_canonical_texts() -> None:
    """Refuse to import if the ingested text is not the text the offsets were cut from."""
    recorded: dict[str, tuple[str, int]] = {}
    for line in AUDIT_MD.read_text(encoding="utf-8").splitlines():
        m = re.search(
            r'study_ingested \| (S\d{3}) \| \{"sha256": "([0-9a-f]+)", "n_chars": (\d+)', line
        )
        if m and m.group(1) not in recorded:
            recorded[m.group(1)] = (m.group(2), int(m.group(3)))
    if not recorded:
        raise SystemExit("Could not read ingest hashes from the audit trail — aborting.")

    with get_connection() as conn:
        live = {
            r["study_id"]: (r["canonical_sha256"], len(r["canonical_text"]))
            for r in conn.execute(
                "SELECT study_id, canonical_sha256, canonical_text FROM canonical_texts"
            ).fetchall()
        }
    if not live:
        raise SystemExit("No canonical_texts — run `res ingest` first.")

    bad = [
        (s, recorded[s][1], live[s][1])
        for s in sorted(recorded)
        if s not in live or not live[s][0].startswith(recorded[s][0])
    ]
    if bad:
        _say("REFUSING TO IMPORT — canonical text does not match the run these offsets "
             "were measured against:")
        for s, old, new in bad:
            _say(f"  {s}: July {old} chars, now {new}")
        raise SystemExit(
            "Install pypdf 6.12.0 (`pip install 'pypdf==6.12.0'`), re-run `res ingest`, "
            "and try again. Importing now would corrupt every span."
        )
    _say(f"  canonical text verified byte-identical for all {len(recorded)} studies")


# ──────────────────────────── the CMOC layer ──────────────────────────────────


def import_cmoc_layer() -> dict[str, int]:
    cmocs = pd.read_parquet(LKG / "cmocs.parquet")
    ents = pd.read_parquet(LKG / "entities.parquet")
    rels = pd.read_parquet(LKG / "relationships.parquet")

    # checker_agrees / checker_notes exist only in the CSV export, not in the parquet.
    checker: dict[str, tuple[bool | None, str | None]] = {}
    csv = pd.read_csv(EXPORTS / "cmocs.csv", encoding="utf-8-sig")
    for row in csv.itertuples():
        agrees = getattr(row, "checker_agrees", None)
        checker[row.cmoc_id] = (
            None if pd.isna(agrees) else bool(agrees),
            None if pd.isna(getattr(row, "checker_agrees", None)) else None,
        )
    notes = dict(zip(csv["cmoc_id"], csv.get("checker_notes", pd.Series([None] * len(csv)))))

    with get_connection() as conn:
        conn.execute("DELETE FROM typed_relations")
        conn.execute("DELETE FROM entity_instances")
        conn.execute("DELETE FROM cmocs")

        for r in cmocs.itertuples():
            agrees = checker.get(r.id, (None, None))[0]
            note = notes.get(r.id)
            conn.execute(
                "INSERT INTO cmocs (cmoc_id, study_id, polarity, narrative_statement, "
                "verifier_support, verifier_notes, checker_agrees, checker_notes, run_id) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (r.id, r.study_id, r.polarity, r.narrative_statement,
                 None if pd.isna(r.verifier_support) else float(r.verifier_support),
                 r.verifier_notes, agrees,
                 None if (note is None or pd.isna(note)) else str(note), EXTRACT_RUN),
            )

        for r in ents.itertuples():
            conn.execute(
                "INSERT INTO entity_instances (entity_id, study_id, cmoc_id, entity_type, "
                "label, canonical_id, verbatim_quote, char_start, char_end, quote_resolved, "
                "match_kind, extractor_model, prompt_version, confidence, run_id) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (r.id, r.study_id, r.cmoc_id, r.type, r.title, r.canonical_id, r.description,
                 None if pd.isna(r.char_start) else int(r.char_start),
                 None if pd.isna(r.char_end) else int(r.char_end),
                 bool(r.quote_resolved),
                 None if (r.match_kind is None or pd.isna(r.match_kind)) else r.match_kind,
                 r.extractor_model, r.prompt_version,
                 None if pd.isna(r.confidence) else float(r.confidence), EXTRACT_RUN),
            )

        # relationships.parquet stores canonical ids in source/target; the *instance* ids the
        # FK needs survive in text_unit_ids = [subject_entity_id, object_entity_id].
        skipped = 0
        for r in rels.itertuples():
            pair = list(r.text_unit_ids) if r.text_unit_ids is not None else []
            if len(pair) != 2:
                skipped += 1
                continue
            conn.execute(
                "INSERT INTO typed_relations (relation_id, study_id, cmoc_id, predicate, "
                "subject_entity_id, object_entity_id, constraint_valid, run_id) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                (r.id, r.study_id, r.cmoc_id, r.description, str(pair[0]), str(pair[1]),
                 bool(r.constraint_valid), EXTRACT_RUN),
            )
    if skipped:
        _say(f"  WARNING: {skipped} relations had no endpoint ids and were not imported")
    return {"cmocs": len(cmocs), "entity_instances": len(ents),
            "typed_relations": len(rels) - skipped}


def import_concept_families() -> int:
    comms = pd.read_parquet(LKG / "communities.parquet")
    n = 0
    with get_connection() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS concept_families ("
            " canonical_id TEXT PRIMARY KEY, entity_type TEXT NOT NULL,"
            " family_id TEXT NOT NULL, family_label TEXT NOT NULL,"
            " run_id TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now())"
        )
        conn.execute("DELETE FROM concept_families")
        for r in comms.itertuples():
            for member in (list(r.members) if r.members is not None else []):
                conn.execute(
                    "INSERT INTO concept_families (canonical_id, entity_type, family_id, "
                    "family_label, run_id) VALUES (%s,%s,%s,%s,%s) "
                    "ON CONFLICT (canonical_id) DO NOTHING",
                    (str(member), r.entity_type, r.id, r.title, EXTRACT_RUN),
                )
                n += 1
    return n


def import_conceptual_entities() -> int:
    """The 8 Leiden mechanisms. Only the CSV export survives, so member_canonical_ids are
    recovered by mapping member labels back through entity_instances."""
    df = pd.read_csv(EXPORTS / "big_concepts.csv", encoding="utf-8-sig")
    with get_connection() as conn:
        label_to_canon = {
            r["label"]: r["canonical_id"]
            for r in conn.execute(
                "SELECT DISTINCT label, canonical_id FROM entity_instances "
                "WHERE canonical_id IS NOT NULL"
            ).fetchall()
        }
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS conceptual_entities (
                id BIGSERIAL PRIMARY KEY, community_key INT NOT NULL,
                community_label TEXT NOT NULL, definition TEXT NOT NULL,
                entity_type TEXT NOT NULL, member_canonical_ids TEXT[] NOT NULL,
                member_labels TEXT[] NOT NULL, study_ids TEXT[] NOT NULL,
                member_count INT NOT NULL, algorithm TEXT NOT NULL, run_id TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                description TEXT, rationale TEXT, realist_role TEXT)
            """
        )
        conn.execute("DELETE FROM conceptual_entities")
        for key, r in enumerate(df.itertuples()):
            labels = [s.strip() for s in str(r.member_labels).split(",") if s.strip()]
            studies = [s.strip() for s in str(r.study_ids).split(",") if s.strip()]
            canon = sorted({label_to_canon[lab] for lab in labels if lab in label_to_canon})
            conn.execute(
                "INSERT INTO conceptual_entities (community_key, community_label, definition, "
                "entity_type, member_canonical_ids, member_labels, study_ids, member_count, "
                "algorithm, run_id, description, rationale, realist_role) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (key, r.community_label, r.definition, r.entity_type, canon, labels, studies,
                 int(r.member_count), "leiden(graspologic)", EXTRACT_RUN,
                 getattr(r, "description", None), None, r.realist_role),
            )
    return len(df)


# ────────────────── screening + audit, from the audit trail ───────────────────

_LOST_RATIONALE = (
    "RESTORED FROM AUDIT TRAIL. The decision is the one recorded for run "
    f"{SCREEN_RUN}; the original rationale text was truncated by the markdown "
    "renderer and is not recoverable."
)


def import_screening() -> int:
    rows: list[tuple[str, str]] = []
    for line in AUDIT_MD.read_text(encoding="utf-8").splitlines():
        if SCREEN_RUN not in line or "study_screened" not in line:
            continue
        m = re.search(r"\| (S\d{3}) \| (\{.*?\})\s*\|", line)
        if m:
            rows.append((m.group(1), m.group(2)))
    n = 0
    with get_connection() as conn:
        conn.execute("DELETE FROM screening_decisions")
        for study_id, detail_json in rows:
            d = json.loads(detail_json)
            pv = d.get("prompt_version", "screening-v1.0")
            for decider, decision in (
                (f"model:{pv}:primary", d["primary"]),
                (f"model:{pv}:second_vote", d["second"]),
                (f"combined:{pv}", d["combined"]),
            ):
                conn.execute(
                    "INSERT INTO screening_decisions (study_id, stage, decider, decision, "
                    "rationale, confidence, run_id) VALUES (%s,'title_abstract',%s,%s,%s,NULL,%s)",
                    (study_id, decider, decision, _LOST_RATIONALE, SCREEN_RUN),
                )
                n += 1
        # The two 'uncertain' records were adjudicated to include at HITL-1; the audit trail
        # records the batch (n=2) and prisma_flow.md records the outcome, but not per-item
        # payloads. Restored as such, and labelled so nobody reads it as a fresh decision.
        uncertain = sorted(s for s, dj in rows if json.loads(dj)["combined"] == "uncertain")
        for study_id in uncertain:
            conn.execute(
                "INSERT INTO screening_decisions (study_id, stage, decider, decision, "
                "rationale, confidence, run_id) VALUES (%s,'title_abstract',%s,'include',%s,"
                "NULL,%s)",
                (study_id, "human:restored-from-audit(hitl1-delegate-01)",
                 "RESTORED: HITL-1 adjudicated this uncertain record to include "
                 "(audit run hitl1-delegate-01, n=2; prisma_flow.md 'Human-adjudicated "
                 "includes = 2'). Delegate decision, ratification still pending.",
                 SCREEN_RUN),
            )
            n += 1
    _say(f"  screening: {len(rows)} studies, HITL-1 includes restored for {uncertain}")
    return n


def import_audit_log() -> int:
    n = 0
    with get_connection() as conn:
        conn.execute("DELETE FROM audit_log")
        for line in AUDIT_MD.read_text(encoding="utf-8").splitlines():
            if not line.startswith("| 20"):
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) < 6:
                continue
            ts, run_id, actor, action, subject, detail = cells[:6]
            try:
                parsed = json.loads(detail)
            except (ValueError, TypeError):
                # Truncated by the renderer — keep the fragment rather than drop the event.
                parsed = {"_truncated_in_export": detail}
            conn.execute(
                "INSERT INTO audit_log (run_id, actor, action, subject_ref, detail, created_at) "
                "VALUES (%s,%s,%s,%s,%s,%s)",
                (run_id, actor, action, subject or None, json.dumps(parsed), ts),
            )
            n += 1
    return n


# ───────────────── deterministic recomputation + theory ──────────────────────


def recompute_synthesis() -> dict:
    from res_pipeline.plugins.realist.synthesis import persist_synthesis

    return persist_synthesis(SYNTH_RUN)


def import_programme_theory() -> int:
    """Rebuild theory_json from the rendered markdown (the only surviving form)."""
    md = (REPORT / "programme_theory.md").read_text(encoding="utf-8")
    version = int(re.search(r"# Programme Theory \(v(\d+)\)", md).group(1))
    body = md.split("\n## ", 1)
    overview = re.sub(r"^#.*$|^_.*_$", "", body[0], flags=re.M).strip()

    sections, boundary = [], ""
    for chunk in body[1].split("\n## ") if len(body) > 1 else []:
        head, _, rest = chunk.partition("\n")
        if head.strip().lower().startswith("boundary"):
            boundary = rest.strip()
            continue
        stmt = re.search(r"^> \*(.+?)\*\s*$", rest, flags=re.M | re.S)
        studies = re.search(r"\*\*Supporting studies:\*\*\s*(.+)$", rest, flags=re.M)
        contra = re.search(r"\*\*Conflicting evidence:\*\*\s*(.+)$", rest, flags=re.M)
        explanation = "\n".join(
            ln for ln in rest.splitlines()
            if ln.strip() and not ln.startswith((">", "**"))
        ).strip()
        sections.append({
            "context_label": re.sub(r"^Context \d+:\s*", "", head.strip()),
            "cmoc_statement": (stmt.group(1).strip() if stmt else ""),
            "explanation": explanation,
            "supporting_study_ids": (
                [s.strip() for s in studies.group(1).split(",")] if studies else []
            ),
            "contradiction_note": (contra.group(1).strip() if contra else ""),
        })

    theory = {"overview": overview, "sections": sections, "boundary_statement": boundary}
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS programme_theories (
                id BIGSERIAL PRIMARY KEY, version INT NOT NULL, theory_json JSONB NOT NULL,
                signed_off_by TEXT, run_id TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now())
            """
        )
        conn.execute("DELETE FROM programme_theories")
        conn.execute(
            "INSERT INTO programme_theories (version, theory_json, signed_off_by, run_id) "
            "VALUES (%s,%s,NULL,%s)",
            (version, json.dumps(theory), SYNTH_RUN),
        )
    _say(f"  programme theory v{version}: {len(sections)} context chains")
    return len(sections)


# ──────────────────────────────── main ────────────────────────────────────────


def main() -> None:
    _say("Restoring the database from the last-known-good snapshot (import, not re-run).\n")
    init_schema()

    _say("1. verifying the ingest matches the snapshot's provenance")
    verify_canonical_texts()

    _say("2. importing the CMOC layer")
    counts = import_cmoc_layer()
    for k, v in counts.items():
        _say(f"  {k}: {v}")

    _say("3. importing normalisation + mechanism layers")
    _say(f"  concept_families: {import_concept_families()}")
    _say(f"  conceptual_entities: {import_conceptual_entities()}")

    _say("4. restoring screening decisions and the audit trail")
    _say(f"  screening_decisions rows: {import_screening()}")
    _say(f"  audit_log events: {import_audit_log()}")

    _say("5. recomputing synthesis deterministically (no API)")
    for k, v in recompute_synthesis().items():
        _say(f"  {k}: {v}")

    _say("6. restoring the programme theory")
    import_programme_theory()

    _say("\nNOT restored (nothing exported them): token_usage, hitl_feedback payloads, "
         "screening rationales, ipt_versions, agent_feedback, distractor_studies.")
    _say("Verify with: res status && res outputs && res export-results")


if __name__ == "__main__":
    main()
