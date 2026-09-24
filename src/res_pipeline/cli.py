"""Command-line entry points for the pipeline phases.

Usage (after ``pip install -e .``)::

    res init-db            # create PostgreSQL schema
    res ingest             # Phase 1: build registry + ingest corpus into Postgres
    res status             # corpus/pipeline status overview
"""

from __future__ import annotations

import uuid

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(name="res", help="Realist Evidence Synthesis pipeline", no_args_is_help=True)
console = Console()


@app.command("init-db")
def init_db() -> None:
    """Create (idempotently) the PostgreSQL schema."""
    from res_pipeline.core.db import init_schema

    init_schema()
    console.print("[green]Schema initialized.[/green]")


@app.command()
def ingest(
    source: str = typer.Option(
        None, help="A folder of PDFs (generic, any N) OR a metadata .jsonl. "
        "Default: the Richmond benchmark corpus."),
) -> None:
    """Phase 1: build the study registry and ingest all sources into Postgres.

    GENERIC ingest — point --source at a folder of PDFs to review ANY corpus (100+ papers),
    not just the 28-study benchmark. Supported inputs: PDF (full text), a .txt sidecar next
    to a PDF (abstract-only), or a .jsonl metadata file (structured records).
    """
    from pathlib import Path

    from res_pipeline.core.db import (
        init_schema,
        log_audit_event,
        store_ingested_study,
        upsert_registry,
    )
    from res_pipeline.core.ingestion import ingest_study
    from res_pipeline.core.registry import build_registry, build_registry_from_dir

    run_id = f"ingest-{uuid.uuid4().hex[:8]}"
    init_schema()
    if source:
        p = Path(source)
        if p.is_dir():
            studies = build_registry_from_dir(p)
            console.print(f"Generic ingest: {len(studies)} documents from {p}", markup=False)
        elif p.suffix == ".jsonl":
            studies = build_registry(p)
        else:
            console.print(f"[red]--source must be a folder or a .jsonl file[/red] (got {source})")
            raise typer.Exit(1)
    else:
        studies = build_registry()
    upsert_registry(studies)
    log_audit_event(run_id, "ingestion", "registry_built", detail={"n_studies": len(studies)})

    table = Table(title=f"Ingestion run {run_id}")
    table.add_column("StudyID")
    table.add_column("Year")
    table.add_column("Source")
    table.add_column("Units", justify="right")
    table.add_column("Chars", justify="right")

    for study in studies:
        ingested = ingest_study(study)
        store_ingested_study(ingested)
        log_audit_event(
            run_id, "ingestion", "study_ingested", subject_ref=study.study_id,
            detail={
                "source_kind": ingested.source_kind,
                "sha256": ingested.canonical_sha256[:12],
                "n_units": len(ingested.text_units),
                "n_chars": len(ingested.canonical_text),
            },
        )
        table.add_row(
            study.study_id, str(study.year or "?"), ingested.source_kind,
            str(len(ingested.text_units)), f"{len(ingested.canonical_text):,}",
        )

    console.print(table)
    console.print(f"[green]Ingested {len(studies)} studies.[/green]")


@app.command()
def screen(
    limit: int = typer.Option(None, help="Pilot mode: screen only the first N studies."),
) -> None:
    """Phase 2: title/abstract screening with dual-model vote (recall-first)."""
    import uuid as _uuid

    from res_pipeline.core.registry import build_registry
    from res_pipeline.core.screening import screen_study

    run_id = f"screen-{_uuid.uuid4().hex[:8]}"
    studies = build_registry()
    if limit:
        studies = studies[:limit]

    table = Table(title=f"Screening run {run_id} (n={len(studies)})")
    table.add_column("StudyID")
    table.add_column("Primary")
    table.add_column("2nd vote")
    table.add_column("Combined")

    tally: dict[str, int] = {"include": 0, "exclude": 0, "uncertain": 0}
    for study in studies:
        result = screen_study(study, run_id)
        tally[result["combined"]] += 1
        style = {"include": "green", "exclude": "red", "uncertain": "yellow"}[result["combined"]]
        table.add_row(
            study.study_id, result["primary"].decision, result["second"].decision,
            f"[{style}]{result['combined']}[/{style}]",
        )

    console.print(table)
    console.print(
        f"include={tally['include']} exclude={tally['exclude']} "
        f"uncertain={tally['uncertain']} (uncertain → HITL-1)"
    )
    _print_run_cost(run_id)


def _print_run_cost(run_id: str) -> None:
    from res_pipeline.core.db import get_connection

    with get_connection() as conn:
        rows = conn.execute(
            "SELECT model, sum(prompt_tokens) AS pt, sum(completion_tokens) AS ct "
            "FROM token_usage WHERE run_id = %s GROUP BY model",
            (run_id,),
        ).fetchall()
    for row in rows:
        console.print(
            f"  tokens {row['model']}: prompt={row['pt']:,} completion={row['ct']:,}",
            markup=False,
        )


@app.command()
def extract(
    limit: int = typer.Option(None, help="Pilot mode: extract only the first N included studies."),
    refresh: bool = typer.Option(
        False, "--refresh",
        help="Re-extract studies that already have CMOCs, replacing them one study at a time."),
    resume: str = typer.Option(
        None, "--resume",
        help="Continue an interrupted extraction: pass its run id. Studies already extracted "
             "under that run are skipped, so an API failure costs no repeated spend."),
) -> None:
    """Phase 3: CMOC extraction (typed, span-grounded, verified) for included studies.

    Three modes, because extraction is the expensive stage and an interruption used to mean
    paying for the same studies twice:

    * **default** — extract only studies that have no CMOCs at all. A second plain
      ``res extract`` is therefore a no-op (it used to print ``n=0`` with no explanation).
    * ``--refresh`` — re-extract everything. Each study's previous layer is deleted
      **immediately before that study is re-extracted**, never all up front, so a failure
      part-way through costs one study rather than the corpus.
    * ``--resume <run-id>`` — continue an interrupted run under its original id, skipping
      the studies it already finished. This is what to use after the API runs out of credit:
      top up, re-run with the same id, and only the remaining studies are paid for. The
      result is still a single-vintage extraction, which is what the metrics require.

    Take a database backup before ``--refresh`` regardless.
    """
    import uuid as _uuid

    from res_pipeline.core.db import get_connection
    from res_pipeline.plugins.realist.cmoc_extraction import extract_study_cmocs

    run_id = resume or f"extract-{_uuid.uuid4().hex[:8]}"
    if resume:
        # Skip what this run already produced; re-extract everything else, so studies left
        # holding an older run's rows (or cleared and never rewritten) are picked up.
        already_clause = (" AND study_id NOT IN (SELECT DISTINCT study_id FROM cmocs "
                          "WHERE run_id = %(run_id)s)")
        refresh = True
    elif refresh:
        already_clause = ""
    else:
        already_clause = " AND study_id NOT IN (SELECT DISTINCT study_id FROM cmocs)"
    with get_connection() as conn:
        rows = conn.execute(
            f"""
            SELECT DISTINCT study_id FROM screening_decisions
            WHERE ((decider LIKE 'combined:%%' AND decision='include')
               OR (decider LIKE 'human:%%' AND decision='include')){already_clause}
            ORDER BY study_id
            """,
            {"run_id": run_id},
        ).fetchall()
    study_ids = [r["study_id"] for r in rows]
    if resume:
        console.print(f"[green]Resuming {run_id}[/green] — "
                      f"{len(study_ids)} studies left to extract", markup=False)
    if limit:
        study_ids = study_ids[:limit]

    table = Table(title=f"CMOC extraction run {run_id} (n={len(study_ids)})")
    for col in ("StudyID", "CMOCs", "Entities", "Relations", "Unresolved", "Demoted",
                "LowSupp", "ChkFlag"):
        table.add_column(col, justify="right" if col != "StudyID" else "left")

    for study_id in study_ids:
        if refresh:
            _clear_study_cmocs(study_id)
        stats = extract_study_cmocs(study_id, run_id)
        table.add_row(study_id, *(str(stats.get(k, 0)) for k in
                      ("cmocs", "entities", "relations", "unresolved_quotes",
                       "demoted_relations", "low_support", "checker_flagged")))
        console.print(f"  {study_id} done", markup=False)

    console.print(table)

    # Span repair (PDF-artifact + near-verbatim recovery) — MUST run so faithfulness
    # reflects true grounding, not exact-match brittleness against PDF text.
    if study_ids:
        from res_pipeline.plugins.realist.span_repair import fuzzy_repair_spans, repair_spans
        r1 = repair_spans(run_id)
        r2 = fuzzy_repair_spans(run_id)
        console.print(f"  span repair: +{r1['repaired']} normalized, +{r2['repaired']} fuzzy, "
                      f"{r2['still_unresolved']} still unresolved → HITL-2", markup=False)
    _print_run_cost(run_id)


def _clear_study_cmocs(study_id: str) -> None:
    """Drop one study's CMOC layer, in dependency order, inside one transaction."""
    from res_pipeline.core.db import get_connection

    with get_connection() as conn:
        conn.execute("DELETE FROM typed_relations WHERE study_id = %s", (study_id,))
        conn.execute("DELETE FROM entity_instances WHERE study_id = %s", (study_id,))
        conn.execute("DELETE FROM cmocs WHERE study_id = %s", (study_id,))


@app.command()
def feedback(
    correct: str = typer.Option(..., help="The human's correction (what the agent SHOULD do)."),
    agent: str = typer.Option("cmoc_extraction", help="Agent the correction applies to."),
    wrong: str = typer.Option("", help="What the agent did wrong (optional, for contrast)."),
    note: str = typer.Option("", help="Short rationale (optional)."),
    study: str = typer.Option("", help="Study to re-extract now so the correction takes effect."),
    reextract: bool = typer.Option(
        False, help="Re-run extraction for --study using the new few-shot correction."),
) -> None:
    """HITL feedback -> few-shot -> re-run: record a human correction, then optionally
    re-extract a study so the agent immediately learns from it (professor's signature loop)."""
    import uuid as _uuid

    from res_pipeline.plugins.realist.guidance import record_feedback

    run_id = f"feedback-{_uuid.uuid4().hex[:8]}"
    record_feedback(agent, correct, wrong=wrong, note=note, study_id=study, run_id=run_id)
    console.print(f"Recorded correction for '{agent}': {correct}", markup=False)
    if reextract:
        if not study:
            console.print("--reextract needs --study.", markup=False)
            raise typer.Exit(1)
        from res_pipeline.plugins.realist.retroduction import _reextract_study
        console.print(f"Re-extracting {study} with the learned correction...", markup=False)
        _reextract_study(study, run_id)
        from res_pipeline.plugins.realist.span_repair import fuzzy_repair_spans, repair_spans
        repair_spans(run_id)
        fuzzy_repair_spans(run_id)
        console.print(f"  {study} re-extracted under HITL few-shot.", markup=False)
        _print_run_cost(run_id)


@app.command()
def adjudicate() -> None:
    """HITL-1: human adjudication of 'uncertain' screening decisions.

    Shows each pending study with both model rationales; the human decides
    include/exclude. Decisions are recorded as human decisions in
    screening_decisions and hitl_feedback (the audit trail of human sovereignty).
    """
    import uuid as _uuid

    from res_pipeline.core.db import get_connection, log_audit_event

    run_id = f"hitl1-{_uuid.uuid4().hex[:8]}"
    with get_connection() as conn:
        pending = conn.execute(
            """
            SELECT DISTINCT ON (sd.study_id) sd.study_id, s.title, s.year, s.abstract
            FROM screening_decisions sd JOIN studies s USING (study_id)
            WHERE sd.decider LIKE 'combined:%' AND sd.decision = 'uncertain'
              AND NOT EXISTS (
                  SELECT 1 FROM screening_decisions h
                  WHERE h.study_id = sd.study_id AND h.decider LIKE 'human:%'
              )
            ORDER BY sd.study_id, sd.created_at DESC
            """
        ).fetchall()

    if not pending:
        console.print("[green]No pending HITL-1 adjudications.[/green]")
        return

    reviewer = typer.prompt("Reviewer name (for the audit trail)")
    for row in pending:
        console.rule(f"{row['study_id']} ({row['year'] or '?'})")
        console.print(f"[bold]{row['title']}[/bold]", markup=False)
        console.print((row["abstract"] or "(no abstract)")[:800], markup=False)
        with get_connection() as conn:
            votes = conn.execute(
                "SELECT decider, decision, rationale FROM screening_decisions "
                "WHERE study_id = %s AND decider LIKE 'model:%%' ORDER BY id DESC LIMIT 2",
                (row["study_id"],),
            ).fetchall()
        for vote in votes:
            console.print(f"  {vote['decider']}: {vote['decision']} — {vote['rationale']}",
                          markup=False)
        decision = typer.prompt("Decision [include/exclude]", default="include").strip().lower()
        while decision not in ("include", "exclude"):
            decision = typer.prompt("Please type include or exclude").strip().lower()
        note = typer.prompt("Reason (recorded verbatim in the audit trail)")
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO screening_decisions (study_id, stage, decider, decision, "
                "rationale, confidence, run_id) "
                "VALUES (%s,'title_abstract',%s,%s,%s,NULL,%s)",
                (row["study_id"], f"human:{reviewer}", decision, note, run_id),
            )
            conn.execute(
                "INSERT INTO hitl_feedback (checkpoint, subject_ref, action, feedback, "
                "payload, run_id) VALUES ('HITL-1',%s,%s,%s,%s,%s)",
                (row["study_id"], "edit", note,
                 '{"decision": "%s"}' % decision, run_id),
            )
        log_audit_event(run_id, f"human:{reviewer}", "hitl1_adjudication",
                        subject_ref=row["study_id"], detail={"decision": decision})
        console.print(f"[green]Recorded: {row['study_id']} → {decision}[/green]")


@app.command("validate-cmocs")
def validate_cmocs(
    threshold: float = typer.Option(0.6, help="Show CMOCs with verifier support below this."),
) -> None:
    """HITL-2: human validation of low-support / unresolved-quote CMOCs.

    Surfaces the configurations the verifier flagged (low support) or whose quotes
    did not resolve, for a human to approve/reject. Records the decision in
    hitl_feedback (the CMOC-validation audit trail).
    """
    import uuid as _uuid

    from res_pipeline.core.db import get_connection, log_audit_event

    run_id = f"hitl2-{_uuid.uuid4().hex[:8]}"
    with get_connection() as conn:
        conn.execute("ALTER TABLE cmocs ADD COLUMN IF NOT EXISTS checker_agrees BOOLEAN")
        conn.execute("ALTER TABLE cmocs ADD COLUMN IF NOT EXISTS checker_notes TEXT")
        flagged = conn.execute(
            """
            SELECT c.cmoc_id, c.study_id, c.polarity, c.narrative_statement,
                   c.verifier_support, c.checker_agrees, c.checker_notes,
                   count(*) FILTER (WHERE NOT e.quote_resolved) AS unresolved
            FROM cmocs c JOIN entity_instances e USING (cmoc_id)
            WHERE c.cmoc_id NOT IN (SELECT subject_ref FROM hitl_feedback
                                    WHERE checkpoint='HITL-2')
            GROUP BY c.cmoc_id, c.study_id, c.polarity, c.narrative_statement,
                     c.verifier_support, c.checker_agrees, c.checker_notes
            HAVING c.verifier_support < %s OR count(*) FILTER (WHERE NOT e.quote_resolved) > 0
                   OR c.checker_agrees = false
            ORDER BY c.verifier_support
            """,
            (threshold,),
        ).fetchall()

    if not flagged:
        console.print("[green]No CMOCs require HITL-2 validation.[/green]")
        return

    reviewer = typer.prompt("Reviewer name (for the audit trail)")
    for row in flagged:
        console.rule(f"{row['cmoc_id']} ({row['study_id']})")
        chk = ("checker: DISAGREES" if row["checker_agrees"] is False
               else "checker: ok" if row["checker_agrees"] else "checker: —")
        console.print(f"support={row['verifier_support']:.2f} "
                      f"unresolved_quotes={row['unresolved']} | {chk}", markup=False)
        if row["checker_agrees"] is False and row["checker_notes"]:
            console.print(f"  checker note: {row['checker_notes']}", markup=False)
        console.print(f"> {row['narrative_statement']}", markup=False)
        with get_connection() as conn:
            for e in conn.execute(
                "SELECT entity_type, label, verbatim_quote, quote_resolved "
                "FROM entity_instances WHERE cmoc_id=%s", (row["cmoc_id"],)
            ).fetchall():
                flag = "" if e["quote_resolved"] else "  [UNRESOLVED]"
                console.print(f"  [{e['entity_type']}] {e['label']}{flag}: "
                              f"{e['verbatim_quote'][:90]}", markup=False)
        action = typer.prompt("Action [approve/reject]", default="approve").strip().lower()
        note = typer.prompt("Note (audit trail)", default="")
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO hitl_feedback (checkpoint, subject_ref, action, feedback, payload, "
                "run_id) VALUES ('HITL-2',%s,%s,%s,'{}',%s)",
                (row["cmoc_id"], "approve" if action == "approve" else "reject", note, run_id),
            )
            if action == "reject":
                conn.execute("UPDATE cmocs SET verifier_notes = coalesce(verifier_notes,'') || "
                             "' [HITL-2 REJECTED]' WHERE cmoc_id=%s", (row["cmoc_id"],))
        log_audit_event(run_id, f"human:{reviewer}", "hitl2_cmoc_validation",
                        subject_ref=row["cmoc_id"], detail={"action": action})


@app.command()
def agents() -> None:
    """Show the multi-agent roster and which Richmond human role each agent mirrors."""
    from res_pipeline.core.agents import human_checkpoints, roster_summary

    table = Table(title="Multi-agent roster (agent → Richmond human role)")
    table.add_column("Agent", style="cyan")
    table.add_column("Tier")
    table.add_column("Mirrors in Richmond et al. (2020)")
    for a in roster_summary():
        table.add_row(a["title"], a["tier"], a["richmond_analogue"][:88] + "…")
    console.print(table)
    console.print(f"[cyan]{len(roster_summary())} machine agents[/cyan] + the human, sovereign at "
                  f"{len(human_checkpoints())} checkpoints (HITL-0…HITL-4).")


@app.command("ratify-ipt")
def ratify_ipt() -> None:
    """HITL-0: register the Initial Programme Theory seed and record human ratification."""
    import uuid as _uuid

    from res_pipeline.plugins.realist.ipt import current_status, register_seed, ratify

    run_id = f"ipt-{_uuid.uuid4().hex[:8]}"
    version = register_seed(run_id)
    console.print(f"IPT seed registered: version [cyan]{version}[/cyan] "
                  "(theory-first; hypotheses only; contamination-safe).")
    console.print("This theory will STEER extraction and be refined by the corpus (retroduction).")
    ratifier = typer.prompt("Ratify as (your name; blank to leave as draft)", default="").strip()
    if ratifier:
        ratify(version, ratifier, run_id)
        console.print(f"[green]IPT {version} ratified by {ratifier}.[/green]")
    status = current_status()
    console.print(f"Status: {status['status']}", markup=False)


@app.command("detect-communities")
def detect_communities_cmd(min_size: int = typer.Option(2, help="Minimum community size.")) -> None:
    """Gap 4: Leiden community detection over the CMOC graph → conceptual entities."""
    import uuid as _uuid

    from res_pipeline.graph.communities import detect_communities

    run_id = f"community-{_uuid.uuid4().hex[:8]}"
    console.print("Building CMOC graph and running community detection...")
    summary = detect_communities(run_id, min_size=min_size)
    console.print(f"[green]{summary['conceptual_entities']} conceptual entities[/green] from "
                  f"{summary['communities_total']} communities via {summary['algorithm']} "
                  f"({summary['nodes']} nodes, {summary['edges']} edges).", markup=False)
    with __import__("res_pipeline.core.db", fromlist=["get_connection"]).get_connection() as conn:
        rows = conn.execute(
            "SELECT community_label, entity_type, member_count, array_length(study_ids,1) AS s "
            "FROM conceptual_entities ORDER BY member_count DESC LIMIT 15"
        ).fetchall()
    table = Table(title="Emergent conceptual entities (top 15)")
    table.add_column("Concept", style="cyan")
    table.add_column("Dominant type")
    table.add_column("Members", justify="right")
    table.add_column("Studies", justify="right")
    for r in rows:
        table.add_row(r["community_label"], r["entity_type"], str(r["member_count"]), str(r["s"]))
    console.print(table)
    _print_run_cost(run_id)


@app.command()
def retroduce(
    max_iter: int = typer.Option(2, help="Max retroduction iterations."),
    reextract: bool = typer.Option(
        True, help="Re-read flagged/low-support studies under the refined theory (uses paid API)."),
    max_studies: int = typer.Option(
        6, help="Cap re-reads to the N weakest studies per round (cost control; 0 = all)."),
) -> None:
    """Gap 2: the retroduction loop — re-analyse weak studies as the theory refines.

    Mirrors Richmond's "studies identified earlier were re-analysed in light of theories
    arising from papers included later" (L253-255) and the professor's iterative modifier.
    Each round: refine the theory, log which IPT hypotheses were confirmed/refined/rejected,
    re-read the studies the Checker flagged or the verifier scored low, then re-synthesise —
    until the flagged set is empty or max_iter is reached.
    """
    import uuid as _uuid

    from res_pipeline.plugins.realist.retroduction import run_retroduction

    run_id = f"retro-{_uuid.uuid4().hex[:8]}"
    result = run_retroduction(run_id, max_iter=max_iter, reextract=reextract,
                              max_studies=(max_studies or None), console=console)
    console.print(f"[green]Retroduction converged after {result['iterations']} iteration(s).[/green] "
                  f"Re-read {result['restudied']} studies; final IPT {result['ipt_version']}.",
                  markup=False)
    _print_run_cost(run_id)


@app.command()
def synthesize() -> None:
    """Phases 3b-5: normalization → demi-regularities/contradictions → programme theory."""
    import uuid as _uuid

    from res_pipeline.graph.communities import detect_communities
    from res_pipeline.plugins.realist.normalization import (
        build_concept_families,
        normalize_entities,
    )
    from res_pipeline.plugins.realist.programme_theory import compose_programme_theory
    from res_pipeline.plugins.realist.synthesis import persist_synthesis

    run_id = f"synth-{_uuid.uuid4().hex[:8]}"
    console.print("Normalizing entities (concept level)...")
    concept_counts = normalize_entities(run_id)
    for entity_type, n in concept_counts.items():
        console.print(f"  {entity_type}: {n} canonical concepts", markup=False)

    console.print("Clustering concepts into Richmond-granularity families...")
    family_counts = build_concept_families(run_id)
    for entity_type, n in family_counts.items():
        console.print(f"  {entity_type}: {n} families", markup=False)

    console.print("Detecting graph communities → conceptual entities (Leiden)...")
    comm = detect_communities(run_id)
    console.print(f"  {comm['conceptual_entities']} conceptual entities "
                  f"({comm['algorithm']}, {comm['nodes']} nodes/{comm['edges']} edges)",
                  markup=False)

    console.print("Computing demi-regularities and contradictions...")
    summary = persist_synthesis(run_id)
    console.print(f"  demi-regularities: {summary['demi_regularities']} | "
                  f"contradictions: {summary['contradictions']}")

    console.print("Composing programme theory (HITL-4 sign-off pending)...")
    theory = compose_programme_theory(run_id)
    console.print(f"[green]Theory drafted with {len(theory.sections)} context sections.[/green]")
    _print_run_cost(run_id)


@app.command()
def verify() -> None:
    """Verification harness: compare system outputs against the Richmond gold standard."""
    import uuid as _uuid

    from res_pipeline.core.config import OUTPUTS_DIR
    from res_pipeline.core.reporting import write_verification_markdown
    from res_pipeline.verification.metrics import run_full_verification

    run_id = f"verify-{_uuid.uuid4().hex[:8]}"
    out_dir = OUTPUTS_DIR / "runs" / run_id
    report = run_full_verification(run_id, out_dir)
    write_verification_markdown(report, out_dir / "verification_report.md")
    from res_pipeline.verification.dashboard import build_dashboard
    build_dashboard(report, out_dir / "dashboard.html")

    s, e, r = report["screening"], report["entity_coverage"], report["relation_coverage"]
    f, t = report["citation_faithfulness"], report["theory_correspondence"]
    table = Table(title="Verification vs Richmond et al. (2020)")
    table.add_column("Stage")
    table.add_column("Result")
    table.add_row("Screening sensitivity (auto)", f"{s['auto_sensitivity']:.1%}")
    table.add_row("Screening sensitivity (after HITL-1)",
                  f"{s['final_sensitivity_after_hitl']:.1%}")
    n_e, n_r = e["gold_entities"], r["gold_relations"]
    e_range = (f"  [per-sample {e['recall_min']:.0%}–{e['recall_max']:.0%} over {e['samples']}]"
               if "recall_min" in e else "")
    # Lead with the like-for-like figure. The role-tolerant one saturates — it has reached
    # 100% — and a score that matches everything has stopped discriminating.
    table.add_row("Concept coverage (same realist role)",
                  f"{e['matched_within_type'] / n_e:.1%} "
                  f"({e['matched_within_type']}/{n_e}){e_range}")
    table.add_row("  …role-tolerant",
                  f"{e['recall']:.1%} ({e['matched']}/{n_e}, "
                  f"{e['matched_cross_type']} cross-role)"
                  + ("  ⚠ SATURATED — not informative" if e["matched"] == n_e else ""))
    table.add_row("Relation strict (exact concept pair)",
                  f"{r['recall']:.1%} ({r['recovered']}/{n_r})")
    table.add_row("Relation anchored (lead with this)",
                  f"{r.get('anchored_recall', 0):.1%} "
                  f"({r.get('anchored_recovered', 0)}/{n_r})")
    ceiling = r.get("type_level_ceiling", {})
    table.add_row("Relation type-level (pattern)",
                  f"{r.get('type_recall', 0):.1%} ({r.get('type_recovered', 0)}/{n_r})"
                  f"  ⚠ saturable: only "
                  f"{ceiling.get('distinct_patterns_in_our_graph', '?')} patterns exist")
    tiers = f.get("tiers", {})
    table.add_row("Quotes resolving to a verbatim span",
                  f"{f.get('strict_plus_normalized', 0):.1%} "
                  f"(exact {tiers.get('exact', 0)}, normalized {tiers.get('normalized', 0)}, "
                  f"fuzzy {tiers.get('fuzzy', 0)}, failed {tiers.get('unresolved', 0)})")
    same = t.get("same_family_judge", {})
    table.add_row("Theory correspondence",
                  f"{t.get('mean_correspondence', 0):.2f} independent judge vs "
                  f"{same.get('mean_correspondence', 0):.2f} same-family "
                  f"(gap {abs(t.get('self_preference_gap', 0)):.2f} — judge-dependent, "
                  "do not quote one number)")
    ca = report.get("community_alignment", {})
    if "alignment_recall" in ca:
        table.add_row("Community↔Richmond mechanism alignment",
                      f"{ca['alignment_recall']:.1%} ({ca['aligned']}/{ca['gold_mechanisms']}, "
                      f"{ca['n_communities']} communities)")
    console.print(table)
    console.print(f"Report: {out_dir / 'verification_report.md'}", markup=False)
    _print_run_cost(run_id)


@app.command("precision-test")
def precision_test(per_category: int = typer.Option(18, help="Distractors per category.")) -> None:
    """Build a distractor pool (Europe PMC) and measure screening precision/specificity."""
    import uuid as _uuid

    from res_pipeline.verification.distractor_pool import build_distractor_pool, run_precision_test

    run_id = f"precision-{_uuid.uuid4().hex[:8]}"
    console.print("Building distractor pool from Europe PMC...")
    n = build_distractor_pool(per_category=per_category)
    console.print(f"  {n} distractors fetched (known-ineligible, 2000–2017, deduped vs the 28).")
    console.print("Screening the mixed pool...")
    result = run_precision_test(run_id)

    table = Table(title="Screening precision/specificity test")
    table.add_column("Metric")
    table.add_column("Result")
    table.add_row("Benchmark recall (the 28)", f"{result['benchmark_included']}/28")
    table.add_row("Distractors correctly excluded (specificity)",
                  f"{result['specificity']:.1%} ({result['distractor_excluded']}/{result['n_distractors']})")
    table.add_row("Distractors wrongly included", str(result["distractor_included"]))
    table.add_row("Distractors uncertain → HITL", str(result["distractor_uncertain"]))
    table.add_row("Precision proxy", f"{result['precision_proxy']:.1%}")
    console.print(table)
    for cat, c in result["per_category"].items():
        console.print(f"  [{cat}] excluded {c['excluded']}/{c['total']} "
                      f"(included {c['included']}, uncertain {c['uncertain']})", markup=False)
    _print_run_cost(run_id)


@app.command("gold-code")
def gold_code() -> None:
    """Produce the independent per-paper reference gold coding (blind, gpt-5.4)."""
    import uuid as _uuid

    from res_pipeline.verification.gold_coder import code_all_studies, compute_per_paper_fidelity

    run_id = f"goldcode-{_uuid.uuid4().hex[:8]}"
    console.print("Coding all studies against Richmond E-codes (blind to pipeline output)...")
    code_all_studies(run_id)
    console.print("Computing per-paper CMOC fidelity (pipeline vs reference)...")
    fidelity = compute_per_paper_fidelity(run_id)
    console.print(f"[green]Per-paper mean recall: {fidelity['mean_per_paper_recall']:.1%}[/green] "
                  f"over {fidelity['n_studies']} studies", markup=False)
    _print_run_cost(run_id)


@app.command("gold-template")
def gold_template() -> None:
    """Generate the human coding workbooks (coder_A, coder_B) for the per-paper gold standard."""
    from res_pipeline.verification.gold_template import build_coding_workbook

    for coder in ("coder_A", "coder_B"):
        path = build_coding_workbook(coder_label=coder)
        console.print(f"[green]Wrote[/green] {path}", markup=False)
    console.print("Two independent coders fill these in BLIND, then adjudicate + compute kappa.")


@app.command("build-lkg")
def build_lkg() -> None:
    """Export the typed knowledge layer to the canonical parquet LKG artifact."""
    import uuid as _uuid

    from res_pipeline.graph.lkg_export import export_lkg

    run_id = f"lkg-{_uuid.uuid4().hex[:8]}"
    counts = export_lkg(run_id)
    console.print(f"[green]LKG exported:[/green] {counts}", markup=False)


@app.command("load-neo4j")
def load_neo4j() -> None:
    """Load the parquet LKG into Neo4j (requires NEO4J_PASSWORD in .env)."""
    from res_pipeline.graph.neo4j_adapter import load_lkg_into_neo4j

    try:
        counts = load_lkg_into_neo4j()
        console.print(f"[green]Loaded into Neo4j:[/green] {counts}", markup=False)
    except Exception as exc:  # noqa: BLE001
        console.print(f"[yellow]Neo4j not loaded:[/yellow] {exc}", markup=False)


@app.command()
def report() -> None:
    """Generate the full artifact set (PRISMA, evidence table, theory, diagrams, audit)."""
    import uuid as _uuid

    from res_pipeline.core.config import OUTPUTS_DIR
    from res_pipeline.core.reporting import (
        write_audit_trail,
        write_evidence_table,
        write_prisma,
        write_theory_diagram,
        write_theory_markdown,
    )

    out_dir = OUTPUTS_DIR / "runs" / f"report-{_uuid.uuid4().hex[:8]}"
    out_dir.mkdir(parents=True, exist_ok=True)
    write_prisma(out_dir / "prisma_flow.md")
    write_evidence_table(out_dir / "cmoc_evidence_table.md")
    write_theory_markdown(out_dir / "programme_theory.md")
    write_theory_diagram(out_dir / "theory_diagram.html")
    write_audit_trail(out_dir / "audit_trail.md")
    console.print(f"[green]Artifacts written to {out_dir}[/green]", markup=False)


@app.command("export-results")
def export_results() -> None:
    """Write outputs/RESULTS.html — the whole review as one shareable, self-contained page.

    Same data as the review console, but as a single file that opens anywhere with no
    database and no server: the human standard, our output, and the verification matrix
    side by side. This is the artifact to send to a supervisor or a reviewer.
    """
    from res_pipeline.core.results_export import write

    from res_pipeline.core.results_export import extraction_vintages

    vintages = extraction_vintages()
    if len(vintages) > 1:
        console.print("[yellow]Warning: the CMOC layer mixes "
                      f"{len(vintages)} extraction runs[/yellow] — "
                      + ", ".join(f"{r} ({n} studies)" for r, n in vintages), markup=False)
        console.print("Every number on the page will be a cross-run composite. Finish the "
                      "extraction with `res extract --resume <run-id>` before quoting it.")
    target = write()
    size_kb = target.stat().st_size / 1024
    console.print(f"[green]Results page written:[/green] {target} ({size_kb:.0f} KB)",
                  markup=False)
    console.print("Open it in any browser — no server needed.")


@app.command("run-all")
def run_all(
    skip_extract: bool = typer.Option(False, help="Reuse existing CMOCs (skip re-extraction)."),
    refresh: bool = typer.Option(
        True, "--refresh/--no-refresh",
        help="Re-extract studies that already have CMOCs (default). --no-refresh only "
             "extracts studies with none, which makes a second run a no-op."),
) -> None:
    """Run the full pipeline end-to-end (ingest → screen → extract → synthesize → verify → report).

    HITL checkpoints are NOT auto-resolved here — run `res adjudicate` / `res validate-cmocs`
    between stages for genuine human review. This command is for reproducible batch runs.
    """
    # Call the underlying functions with REAL values. Typer does not rewrite the
    # decorated function, so calling `ingest()` bare passes the `typer.Option(...)`
    # sentinel as the argument value — which is truthy, so `Path(source)` received an
    # OptionInfo and `res run-all` died on its first line. Every documented
    # "reproducible batch run" had therefore never run.
    ingest(source=None)
    screen(limit=None)
    if not skip_extract:
        extract(limit=None, refresh=refresh)
    synthesize()
    detect_communities_cmd(min_size=2)
    verify()
    build_lkg()
    report()
    export_results()
    console.print("[bold green]Full pipeline complete.[/bold green] "
                  "See outputs/runs/ and outputs/lkg/.")


@app.command()
def webui(port: int = typer.Option(8000, help="Port for the review console.")) -> None:
    """Launch the browser-based human review console (the HITL 'windows')."""
    import uvicorn

    console.print(f"[green]Review console:[/green] http://127.0.0.1:{port}", markup=False)
    uvicorn.run("res_pipeline.webui:app", host="127.0.0.1", port=port, log_level="warning")


@app.command()
def progress(
    watch: bool = typer.Option(False, "--watch", "-w",
                               help="Refresh every 20s until the run finishes."),
) -> None:
    """Show how far the current (or last) run has got.

    Reads the newest log in outputs/logs/ and the live database, so it works whether the
    run was started from this terminal, another terminal, or a background process.
    """
    import time as _time
    from datetime import datetime, timezone

    from res_pipeline.core.config import OUTPUTS_DIR
    from res_pipeline.core.db import get_connection

    STAGES = [
        ("Ingest", "Ingested "),
        ("Screen", "include="),
        ("Extract", "CMOC extraction run"),
        ("Synthesize", "Demi-regularities"),
        ("Communities", "conceptual entities"),
        ("Verify", "Verification vs Richmond"),
        ("Build LKG", "LKG exported"),
        ("Report", "Artifacts written"),
        ("Results page", "Results page written"),
    ]

    def _render() -> bool:
        logs = sorted(OUTPUTS_DIR.glob("logs/*.log"), key=lambda p: p.stat().st_mtime)
        if not logs:
            console.print("[yellow]No run log found in outputs/logs/.[/yellow]")
            return True
        log = logs[-1]
        text = log.read_text(encoding="utf-8", errors="replace")
        age_s = datetime.now(timezone.utc).timestamp() - log.stat().st_mtime
        failed = "RateLimitError" in text or "Traceback" in text
        done = "Results page written" in text
        alive = age_s < 180 and not done and not failed

        table = Table(title=f"Run progress — {log.name}")
        table.add_column("Stage")
        table.add_column("Status")
        for name, marker in STAGES:
            hit = marker in text
            table.add_row(name, "[green]done[/green]" if hit else "[dim]waiting[/dim]")
        console.print(table)

        extracted = text.count(" done")
        if "CMOC extraction run" in text and not done:
            console.print(f"  extracting: [bold]{extracted}[/bold] studies finished")

        with get_connection() as conn:
            counts = {t: conn.execute(f"SELECT count(*) AS n FROM {t}").fetchone()["n"]
                      for t in ("cmocs", "entity_instances", "typed_relations")}
        console.print(f"  database now: {counts['cmocs']} CMOCs · "
                      f"{counts['entity_instances']} entities · "
                      f"{counts['typed_relations']} relations", markup=False)

        if failed:
            console.print("[red]The run stopped with an error.[/red] "
                          f"Last lines of {log}:")
            for line in text.rstrip().splitlines()[-3:]:
                console.print(f"  {line}", markup=False)
        elif done:
            console.print("[bold green]FINISHED[/bold green] — open outputs/RESULTS.html")
        elif alive:
            console.print(f"[green]RUNNING[/green] (log updated {age_s:.0f}s ago)")
        else:
            console.print(f"[yellow]STALLED?[/yellow] log has not changed for {age_s / 60:.0f} min")
        return done or failed

    if not watch:
        _render()
        return
    while True:
        console.clear()
        if _render():
            return
        _time.sleep(20)


@app.command()
def outputs() -> None:
    """Show what a run produced, grouped by what each file is FOR.

    A flat list of eighteen files answers "show me the output" with more confusion than it
    removes. The files fall into three jobs, and naming the job is most of the explanation:
    one file to show someone, a few to answer their follow-up questions, and the rest as
    evidence for when a specific number is challenged.
    """
    from res_pipeline.core.config import OUTPUTS_DIR
    from res_pipeline.core.db import get_connection

    TIERS: list[tuple[str, str, list[tuple[str, str]]]] = [
        ("1 — SHOW THIS", "The whole review on one page. If you open one file, open this one.", [
            ("RESULTS.html", "Richmond's conclusions beside ours, the verification table, and "
                             "every finding — searchable, opens in any browser"),
        ]),
        ("2 — OUR FINAL CONCLUSION", "What the system concluded, in its own words. This is the "
                                     "thing being compared with Richmond.", [
            ("runs/report-*/programme_theory.md", "The programme theory: for which student, "
                                                  "what teaching works, and why"),
            ("runs/report-*/theory_diagram.html", "The same theory as a diagram"),
        ]),
        ("3 — HOW WE CHECKED IT", "The comparison with Richmond, number by number.", [
            ("runs/verify-*/verification_report.md", "Scorecard: every metric, its interval, "
                                                     "and whether a machine or an AI judged it"),
            ("runs/report-*/prisma_flow.md", "Study flow, the way a systematic review reports it"),
        ]),
        ("4 — THE EVIDENCE", "Open these only when someone challenges a specific number.", [
            ("exports/cmocs.csv", "Every finding, one row each"),
            ("exports/entities.csv", "Every concept + the exact sentence it came from"),
            ("exports/relationships.csv", "Every causal link"),
            ("exports/big_concepts.csv", "Mechanisms the algorithm discovered by itself"),
            ("runs/report-*/cmoc_evidence_table.md", "Findings with their quotes, per paper"),
            ("runs/report-*/audit_trail.md", "Every action taken, by whom, when"),
            ("lkg/*.parquet", "The knowledge graph, for programmatic use"),
            ("logs/*.log", "Console log of the run"),
        ]),
    ]

    def _resolve(pattern: str):
        if "*" in pattern:
            matches = sorted(OUTPUTS_DIR.glob(pattern), key=lambda q: q.stat().st_mtime)
            return matches[-1] if matches else None
        path = OUTPUTS_DIR / pattern
        return path if path.exists() else None

    with get_connection() as conn:
        c = {r["k"]: r["n"] for r in conn.execute("""
            SELECT 'studies' AS k, count(*) AS n FROM studies
            UNION ALL SELECT 'cmocs', count(*) FROM cmocs
            UNION ALL SELECT 'entities', count(*) FROM entity_instances
            UNION ALL SELECT 'relations', count(*) FROM typed_relations
            UNION ALL SELECT 'mechanisms', count(*) FROM conceptual_entities
        """).fetchall()}

    console.print()
    console.print("[bold]What the pipeline did, in one line[/bold]")
    console.print(
        f"  {c['studies']} papers  →  {c['cmocs']} findings  →  {c['entities']} concepts "
        f"+ {c['relations']} causal links  →  {c['mechanisms']} mechanisms  →  "
        "[bold]1 programme theory[/bold]  →  compared with Richmond",
        markup=True)
    console.print("  [dim]The programme theory is our conclusion. Everything else is either the "
                  "evidence under it or the check on it.[/dim]")

    missing: list[str] = []
    for title, why, entries in TIERS:
        table = Table(title=f"{title}   —   {why}", title_justify="left")
        table.add_column("File")
        table.add_column("What it is")
        table.add_column("Size", justify="right")
        for pattern, what in entries:
            path = _resolve(pattern)
            if path is None:
                missing.append(pattern)
                continue
            size = path.stat().st_size
            human = (f"{size / 1_048_576:.1f} MB" if size >= 1_048_576
                     else f"{size / 1024:.1f} KB" if size >= 1024 else f"{size} B")
            table.add_row(str(path.relative_to(OUTPUTS_DIR)), what, human)
        console.print(table)

    console.print(f"[dim]Root: {OUTPUTS_DIR}[/dim]")
    if missing:
        console.print(f"[yellow]Not yet generated:[/yellow] {', '.join(missing)}", markup=False)


@app.command()
def status() -> None:
    """Show corpus and pipeline status."""
    from res_pipeline.core.db import get_connection

    optional = ("cmocs", "entity_instances", "typed_relations", "demi_regularities",
                "contradictions", "programme_theories")
    with get_connection() as conn:
        counts = {}
        for table_name in ("studies", "canonical_texts", "text_units",
                           "screening_decisions", "hitl_feedback", "audit_log", *optional):
            try:
                row = conn.execute(f"SELECT count(*) AS n FROM {table_name}").fetchone()
                counts[table_name] = row["n"]
            except Exception:  # noqa: BLE001 — table may not exist yet
                counts[table_name] = "-"
        studies_with_cmocs = conn.execute(
            "SELECT count(DISTINCT study_id) AS n FROM cmocs"
        ).fetchone()["n"] if counts.get("cmocs", "-") != "-" else 0
    table = Table(title="Pipeline status")
    table.add_column("Table")
    table.add_column("Rows", justify="right")
    for name, n in counts.items():
        table.add_row(name, str(n))
    console.print(table)
    console.print(f"[cyan]Studies with extracted CMOCs: {studies_with_cmocs}[/cyan]")


if __name__ == "__main__":
    app()
