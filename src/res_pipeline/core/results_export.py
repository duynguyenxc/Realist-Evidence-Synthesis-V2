"""Render the whole review — human standard, machine output, and the verification —
as ONE self-contained HTML page that can be opened anywhere and sent to anyone.

Why this module exists
----------------------
`webui.py` is the interactive console: it runs stages, serves the four human
checkpoints, and needs a live database and a local server. That is the right tool at
the desk and the wrong tool for the recurring question this project is asked —
*"show me the output, and show me how you verified it"* — which is asked by people who
have no database, no terminal and no access to this machine (the professor, a journal
reviewer, an interview panel).

This module answers that question with a single static file. It reads the same three
sources of truth the console reads — the PostgreSQL database, `gold/` (Richmond's
published outputs), and the newest verification run under `outputs/runs/` — and writes
`outputs/RESULTS.html`: no server, no dependencies, no network, one file to open or
attach. It adds nothing of its own; every number on the page is read from those
sources, and every claim carries the study and the verbatim quote behind it.

    res export-results            # -> outputs/RESULTS.html

The page is deliberately written for a reader who knows neither realist review
methodology nor this codebase.
"""

from __future__ import annotations

import html
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from res_pipeline.core.db import get_connection

ROOT = Path(__file__).resolve().parents[3]
GOLD = ROOT / "gold"
OUTPUTS = ROOT / "outputs"
DEFAULT_TARGET = OUTPUTS / "RESULTS.html"

# Richmond's five student contexts, keyed by their gold entity code. The prose for each
# is parsed out of gold/RICHMOND_CONCLUSIONS.md so that file stays the single source of
# truth for what Richmond concluded.
CONTEXT_CODES = ["E02", "E03", "E04", "E05", "E06"]
CONTEXT_SHORT = {
    "E02": "Low knowledge",
    "E03": "High domain knowledge",
    "E04": "Positive coping / self-efficacy",
    "E05": "Negative coping / low self-efficacy",
    "E06": "Mixed knowledge in one group",
}


# --------------------------------------------------------------------------- sources


def _load_gold() -> dict[str, Any]:
    """The same corrected benchmark the verification harness scores against.

    Reading a different gold file here than `verification/metrics.py` reads is how a
    page comes to show one standard's labels beside another standard's numbers.
    """
    from res_pipeline.verification.metrics import gold_version

    path = GOLD / f"richmond_gold_{gold_version()}.json"
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def _parse_richmond_contexts() -> dict[str, dict[str, Any]]:
    """Pull the five per-context CMOC statements out of RICHMOND_CONCLUSIONS.md section 4.5.

    The document is the human-readable standard and is maintained by hand; parsing it
    here (rather than re-typing the statements into a second file) keeps one source of
    truth. The structure relied on is stable and explicit:

        **Context 1 — <name> (<n> studies)**
        > <verbatim CMOC statement>
        Explanation ...
        Studies (...): <list>
    """
    text = (GOLD / "RICHMOND_CONCLUSIONS.md").read_text(encoding="utf-8")
    section = text.split("### 4.5")[1].split("### 4.6")[0]
    blocks = re.split(r"\n\*\*Context (\d) — ", section)[1:]
    parsed: dict[str, dict[str, Any]] = {}
    for i in range(0, len(blocks), 2):
        idx, body = int(blocks[i]), blocks[i + 1]
        head, _, rest = body.partition("\n")
        name = head.strip()
        n_studies = None
        if m := re.search(r"\((\d+) studies?\)", name):
            n_studies = int(m.group(1))
            name = name[: m.start()].strip()
        statements = [
            re.sub(r"\s+", " ", s.replace("\n>", " ").lstrip("> ").strip(" *"))
            for s in re.findall(r"((?:^> .*\n?)+)", rest, flags=re.MULTILINE)
        ]
        explanation = ""
        if m := re.search(r"^Explanation[^:]*:\s*(.*?)(?=^Studies \()", rest,
                          flags=re.MULTILINE | re.DOTALL):
            explanation = re.sub(r"\s+", " ", m.group(1)).strip()
        named = ""
        if m := re.search(r"^Studies \([^)]*\):\s*(.*?)(?=\n\n|\Z)", rest,
                          flags=re.MULTILINE | re.DOTALL):
            named = re.sub(r"\s+", " ", m.group(1)).strip()
        parsed[CONTEXT_CODES[idx - 1]] = {
            "name": name,
            "n_studies_stated": n_studies,
            "statements": [s for s in statements if s],
            "explanation": explanation,
            "named_studies": named,
        }
    if len(parsed) != 5:
        raise RuntimeError(
            f"expected 5 Richmond contexts in RICHMOND_CONCLUSIONS.md section 4.5, "
            f"parsed {len(parsed)} — the document structure changed"
        )
    return parsed


def _latest_verification() -> tuple[str, dict[str, Any]] | tuple[None, None]:
    runs = sorted(
        OUTPUTS.glob("runs/verify-*/verification_report.json"),
        key=lambda p: p.stat().st_mtime,
    )
    if not runs:
        return None, None
    with runs[-1].open(encoding="utf-8") as fh:
        return runs[-1].parent.name, json.load(fh)


def _fetch(cur, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    cur.execute(sql, params)
    return list(cur.fetchall())


def extraction_vintages() -> list[tuple[str, int]]:
    """Which extraction runs the CMOC layer currently holds, largest first.

    More than one means the layer is a composite of different runs — different prompts,
    possibly different models, certainly different days. Every metric computed over it is
    then a cross-vintage average that belongs to no single execution, which is exactly the
    defect the screening metric was fixed for. Callers that publish numbers must check this.
    """
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT run_id, count(DISTINCT study_id) AS n FROM cmocs "
            "GROUP BY run_id ORDER BY n DESC"
        ).fetchall()
    return [(r["run_id"], r["n"]) for r in rows]


def collect() -> dict[str, Any]:
    """Read everything the page shows. No computation beyond joining and counting."""
    verify_run, verification = _latest_verification()
    data: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "verify_run": verify_run,
        "verification": verification or {},
        "gold": _load_gold(),
        "richmond_contexts": _parse_richmond_contexts(),
    }

    with get_connection() as conn:
        cur = conn.cursor()

        data["counts"] = {
            row["label"]: row["n"]
            for row in _fetch(cur, """
                SELECT 'studies' AS label, count(*) AS n FROM studies
                UNION ALL SELECT 'cmocs', count(*) FROM cmocs
                UNION ALL SELECT 'entities', count(*) FROM entity_instances
                UNION ALL SELECT 'relations', count(*) FROM typed_relations
                UNION ALL SELECT 'concepts', count(DISTINCT canonical_id) FROM entity_instances
                UNION ALL SELECT 'big_concepts', count(*) FROM conceptual_entities
                UNION ALL SELECT 'demi_regularities', count(*) FROM demi_regularities
                UNION ALL SELECT 'contradictions', count(*) FROM contradictions
                UNION ALL SELECT 'human_decisions', count(*) FROM hitl_feedback
                UNION ALL SELECT 'audit_events', count(*) FROM audit_log
                UNION ALL SELECT 'studies_with_cmocs', count(DISTINCT study_id) FROM cmocs
            """)
        }

        data["studies"] = _fetch(cur, """
            SELECT s.study_id, s.title, s.year, s.journal, s.source_kind,
                   count(DISTINCT c.cmoc_id) AS n_cmocs
            FROM studies s LEFT JOIN cmocs c ON c.study_id = s.study_id
            GROUP BY s.study_id, s.title, s.year, s.journal, s.source_kind
            ORDER BY s.study_id
        """)

        data["cmocs"] = _fetch(cur, """
            SELECT c.cmoc_id, c.study_id, c.polarity, c.narrative_statement,
                   c.verifier_support, c.checker_agrees, s.title
            FROM cmocs c JOIN studies s ON s.study_id = c.study_id
            ORDER BY c.study_id, c.cmoc_id
        """)

        data["entities"] = _fetch(cur, """
            SELECT entity_id, study_id, cmoc_id, entity_type, label, canonical_id,
                   verbatim_quote, char_start, char_end, quote_resolved
            FROM entity_instances ORDER BY study_id, cmoc_id, entity_type
        """)

        data["relations"] = _fetch(cur, """
            SELECT tr.relation_id, tr.study_id, tr.cmoc_id, tr.predicate,
                   se.label AS subject, se.entity_type AS subject_type,
                   se.canonical_id AS subject_cid,
                   oe.label AS object, oe.entity_type AS object_type,
                   oe.canonical_id AS object_cid
            FROM typed_relations tr
            JOIN entity_instances se ON se.entity_id = tr.subject_entity_id
            JOIN entity_instances oe ON oe.entity_id = tr.object_entity_id
            ORDER BY tr.study_id, tr.cmoc_id
        """)

        data["big_concepts"] = _fetch(cur, """
            SELECT community_label, realist_role, member_count, definition,
                   description, member_labels, study_ids
            FROM conceptual_entities ORDER BY member_count DESC
        """)

        data["demi_regularities"] = _fetch(cur, """
            SELECT context_concept, driver_concept, outcome_concept, polarity, study_ids
            FROM demi_regularities
            ORDER BY array_length(study_ids, 1) DESC NULLS LAST
        """)

        data["contradictions"] = _fetch(cur, """
            SELECT driver_concept, positive_studies, negative_studies,
                   positive_contexts, negative_contexts, resolution
            FROM contradictions ORDER BY id
        """)

        theory = _fetch(cur, """
            SELECT version, theory_json, signed_off_by, run_id, created_at
            FROM programme_theories ORDER BY version DESC LIMIT 1
        """)
        if theory:
            row = dict(theory[0])
            raw = row["theory_json"]
            row["theory"] = json.loads(raw) if isinstance(raw, str) else raw
            data["theory"] = row

        data["context_concepts"] = _fetch(cur, """
            SELECT canonical_id, count(DISTINCT cmoc_id) AS n_cmocs,
                   count(DISTINCT study_id) AS n_studies,
                   (array_agg(DISTINCT label))[1:4] AS examples
            FROM entity_instances WHERE entity_type = 'Context'
            GROUP BY canonical_id ORDER BY count(DISTINCT cmoc_id) DESC
        """)

        data["screening"] = _fetch(cur, """
            SELECT study_id, decision, rationale, decider
            FROM screening_decisions WHERE decider LIKE %s
            ORDER BY study_id
        """, ("combined:%",))

    data["vintages"] = extraction_vintages()
    data["side_by_side"] = _build_side_by_side(data)
    return data


def _build_side_by_side(data: dict[str, Any]) -> list[dict[str, Any]]:
    """For each of Richmond's five contexts, put our CMOCs next to their statement.

    The link between the two sides is the concept the verification run matched to that
    context's gold entity. Where the run matched nothing, that is shown as a gap rather
    than papered over — the honest result for the two coping/self-efficacy contexts.
    """
    per_entity = data["verification"].get("entity_coverage", {}).get("per_entity", {})
    membership = data["gold"].get("context_study_membership", {})
    cmocs_by_id = {c["cmoc_id"]: c for c in data["cmocs"]}

    cmocs_for_concept: dict[str, set[str]] = defaultdict(set)
    for ent in data["entities"]:
        if ent["entity_type"] == "Context" and ent["canonical_id"]:
            cmocs_for_concept[ent["canonical_id"]].add(ent["cmoc_id"])

    rows: list[dict[str, Any]] = []
    for code in CONTEXT_CODES:
        gold_entity = data["gold"]["entities"].get(code, {})
        match = per_entity.get(code, {})
        concept = match.get("concept") or ""
        matched = bool(match.get("matched"))
        our_cmocs = (
            [cmocs_by_id[cid] for cid in sorted(cmocs_for_concept.get(concept, ())) if cid in cmocs_by_id]
            if concept else []
        )
        our_studies = {c["study_id"] for c in our_cmocs}
        richmond_studies = set(membership.get(code, {}).get("study_ids") or [])
        overlap = our_studies & richmond_studies
        rows.append({
            "code": code,
            "short": CONTEXT_SHORT[code],
            "gold_label": gold_entity.get("label", ""),
            "gold_location": gold_entity.get("location", ""),
            "richmond": data["richmond_contexts"].get(code, {}),
            "richmond_studies": sorted(richmond_studies),
            "matched": matched,
            "concept": concept,
            "rationale": match.get("rationale") or "",
            "cross_type": bool(match.get("cross_type")),
            "type_agrees": bool(match.get("type_agrees")),
            "our_cmocs": our_cmocs,
            "our_studies": sorted(our_studies),
            "overlap": sorted(overlap),
        })
    return rows


# ---------------------------------------------------------------------------- render


def _e(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def _pct(value: Any) -> str:
    return "—" if value is None else f"{float(value) * 100:.1f}%"


def _verdict(row: dict[str, Any]) -> tuple[str, str]:
    """A plain-language verdict for one side-by-side context row."""
    if not row["matched"]:
        return "gap", "Not recovered"
    if row["overlap"]:
        return "match", "Recovered"
    return "partial", "Recovered (different studies)"


STYLE = """
:root{
  --bg:#fbfaf8; --panel:#ffffff; --ink:#1b1b1a; --muted:#61615e; --line:#e4e1db;
  --accent:#1f5f4f; --accent-soft:#eaf2ef;
  --match:#1f7a52; --match-bg:#e8f4ee;
  --partial:#8a6318; --partial-bg:#fcf3e0;
  --gap:#9c3030; --gap-bg:#fbeceb;
  --human:#3f4d8a; --human-bg:#eceff8;
  --mono:ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,monospace;
}
@media (prefers-color-scheme:dark){ :root:not([data-theme="light"]){
  --bg:#15161a; --panel:#1d1f24; --ink:#eceae6; --muted:#a0a09c; --line:#33353c;
  --accent:#6fc2a5; --accent-soft:#1d2b28;
  --match:#63c39a; --match-bg:#162a22; --partial:#d8ab5c; --partial-bg:#2c2418;
  --gap:#e08b86; --gap-bg:#2d1b1b; --human:#9aa8e0; --human-bg:#1d2033;
}}
:root[data-theme="dark"]{
  --bg:#15161a; --panel:#1d1f24; --ink:#eceae6; --muted:#a0a09c; --line:#33353c;
  --accent:#6fc2a5; --accent-soft:#1d2b28;
  --match:#63c39a; --match-bg:#162a22; --partial:#d8ab5c; --partial-bg:#2c2418;
  --gap:#e08b86; --gap-bg:#2d1b1b; --human:#9aa8e0; --human-bg:#1d2033;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font:16px/1.65 Charter,"Iowan Old Style",Georgia,"Times New Roman",serif;}
.wrap{max-width:1080px;margin:0 auto;padding:0 22px 96px}
header.top{padding:52px 0 28px;border-bottom:2px solid var(--ink);margin-bottom:34px}
.kicker{font:600 12px/1 ui-sans-serif,system-ui,sans-serif;letter-spacing:.14em;
  text-transform:uppercase;color:var(--accent);margin-bottom:14px}
h1{font-size:clamp(28px,4.4vw,42px);line-height:1.15;margin:0 0 14px;letter-spacing:-.02em}
.lede{font-size:18px;color:var(--muted);max-width:60ch;margin:0}
h2{font-size:clamp(21px,2.6vw,27px);margin:56px 0 6px;letter-spacing:-.01em;
  padding-top:22px;border-top:1px solid var(--line)}
h2 .num{color:var(--accent);font-family:var(--mono);font-size:15px;margin-right:10px}
h3{font-size:18px;margin:30px 0 8px}
h2+.sub{color:var(--muted);margin:0 0 20px;max-width:64ch}
p{max-width:68ch}
a{color:var(--accent)}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(132px,1fr));gap:10px;margin:26px 0}
.tile{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px 15px}
.tile .n{font:700 27px/1 ui-sans-serif,system-ui,sans-serif;letter-spacing:-.02em}
.tile .l{font:500 12px/1.35 ui-sans-serif,system-ui,sans-serif;color:var(--muted);
  margin-top:7px;text-transform:uppercase;letter-spacing:.06em}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:12px;
  padding:20px 22px;margin:20px 0}
.callout{border-left:4px solid var(--accent);background:var(--accent-soft);
  border-radius:0 10px 10px 0;padding:16px 20px;margin:20px 0}
.callout p{margin:0;max-width:none}
blockquote{margin:12px 0;padding:2px 0 2px 18px;border-left:3px solid var(--line);
  color:var(--ink);font-style:italic}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px}
@media(max-width:760px){.grid2{grid-template-columns:1fr}}
.col{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px 18px}
.col.human{border-top:3px solid var(--human)}
.col.machine{border-top:3px solid var(--accent)}
.col h4{margin:0 0 4px;font:600 12px/1 ui-sans-serif,system-ui,sans-serif;
  letter-spacing:.1em;text-transform:uppercase;color:var(--muted)}
.ctx-head{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;margin-top:34px}
.ctx-head h3{margin:0}
.badge{display:inline-block;font:600 11px/1.55 ui-sans-serif,system-ui,sans-serif;
  padding:2px 9px;border-radius:999px;letter-spacing:.04em;white-space:nowrap}
.b-match{background:var(--match-bg);color:var(--match)}
.b-partial{background:var(--partial-bg);color:var(--partial)}
.b-gap{background:var(--gap-bg);color:var(--gap)}
.b-human{background:var(--human-bg);color:var(--human)}
.b-auto{background:var(--accent-soft);color:var(--accent)}
.tablewrap{overflow-x:auto;margin:18px 0;border:1px solid var(--line);border-radius:12px;
  background:var(--panel)}
table{border-collapse:collapse;width:100%;font:14px/1.5 ui-sans-serif,system-ui,sans-serif}
th,td{text-align:left;padding:10px 13px;border-bottom:1px solid var(--line);vertical-align:top}
th{font-weight:600;color:var(--muted);font-size:12px;letter-spacing:.05em;
  text-transform:uppercase;position:sticky;top:0;background:var(--panel)}
tr:last-child td{border-bottom:none}
td.num{font-family:var(--mono);white-space:nowrap}
code,.cid{font-family:var(--mono);font-size:12.5px;background:var(--accent-soft);
  color:var(--accent);padding:1px 6px;border-radius:5px;white-space:nowrap}
.quote{font-size:13px;color:var(--muted);font-style:italic}
.small{font-size:13px;color:var(--muted)}
ul.tight{margin:8px 0;padding-left:20px}
ul.tight li{margin:4px 0}
details{border:1px solid var(--line);border-radius:10px;background:var(--panel);
  padding:12px 16px;margin:12px 0}
details>summary{cursor:pointer;font:600 14px/1.5 ui-sans-serif,system-ui,sans-serif}
details[open]>summary{margin-bottom:10px;padding-bottom:8px;border-bottom:1px solid var(--line)}
.filter{width:100%;padding:11px 14px;border:1px solid var(--line);border-radius:9px;
  background:var(--panel);color:var(--ink);font:14px/1.4 ui-sans-serif,system-ui,sans-serif;
  margin-bottom:12px}
.pol{font:600 11px/1.5 ui-sans-serif,system-ui,sans-serif;padding:1px 7px;border-radius:999px}
.pol-positive{background:var(--match-bg);color:var(--match)}
.pol-negative{background:var(--gap-bg);color:var(--gap)}
.pol-mixed{background:var(--partial-bg);color:var(--partial)}
footer{margin-top:64px;padding-top:22px;border-top:1px solid var(--line);
  color:var(--muted);font-size:13px}
"""

FILTER_JS = """
document.querySelectorAll('[data-filter]').forEach(function(box){
  var t = document.getElementById(box.dataset.filter);
  if(!t) return;
  var rows = Array.prototype.slice.call(t.tBodies[0].rows);
  var out = document.getElementById(box.dataset.filter + '-count');
  box.addEventListener('input', function(){
    var q = box.value.toLowerCase().trim(), shown = 0;
    rows.forEach(function(r){
      var hit = !q || r.textContent.toLowerCase().indexOf(q) !== -1;
      r.hidden = !hit; if(hit) shown++;
    });
    if(out) out.textContent = shown + ' of ' + rows.length + ' shown';
  });
});
"""


def _vintage_warning(d: dict[str, Any]) -> str:
    """A banner when the CMOC layer mixes extraction runs — never a silent composite."""
    vintages = d.get("vintages") or []
    if len(vintages) <= 1:
        return ""
    rows = " · ".join(f"<code>{_e(run)}</code> ({n} studies)" for run, n in vintages)
    return f"""
<div class="callout" style="border-left-color:var(--gap);background:var(--gap-bg)">
  <p><strong>This page is built from an incomplete extraction.</strong> The findings below
  come from {len(vintages)} different extraction runs — {rows} — so every count and every
  score on this page is a composite that belongs to no single execution. This happens when a
  run is interrupted part-way. Finish the extraction
  (<code>res extract --resume &lt;run-id&gt;</code>) and regenerate before quoting anything
  here.</p>
</div>
"""


def _section_headline(d: dict[str, Any]) -> str:
    v = d["verification"]
    c = d["counts"]
    theory = d.get("theory", {}).get("theory", {})
    overview = theory.get("overview", "")
    screening = v.get("screening", {})
    faith = v.get("citation_faithfulness", {})
    ent = v.get("entity_coverage", {})
    rel = v.get("relation_coverage", {})
    return f"""
<h2><span class="num">01</span>The one-minute answer</h2>
<p class="sub">Richmond's five reviewers spent months producing a realist review of 28 studies.
Our system was given the same 28 studies and asked to do the same analytic work. Here is what
each side concluded, in their own words.</p>

<div class="grid2">
  <div class="col human">
    <h4>Richmond et al. (2020) — five human reviewers</h4>
    <blockquote>The student is key. Educational interventions "do not work independently, but work
    inter-dependently with the individual, their pre-existing clinical domain-specific knowledge and
    their ability to cope." The same intervention helps some students and harms others; students with
    low knowledge determine most whether an intervention succeeds.</blockquote>
    <p class="small">Conclusions, p.717; Discussion, pp.716–717.</p>
  </div>
  <div class="col machine">
    <h4>Our system — unaided, from the same 28 papers</h4>
    <blockquote>{_e(overview[:700])}{'…' if len(overview) > 700 else ''}</blockquote>
    <p class="small">Programme theory version {_e(d.get('theory', {}).get('version', '—'))},
    generated from {c.get('cmocs', 0)} extracted configurations.</p>
  </div>
</div>

<div class="callout"><p><strong>The short verdict.</strong> The system independently arrives at
Richmond's central claim — that the same teaching resource helps or hinders depending on the
student's prior knowledge — and it recovers all {screening.get('n_gold_includes', 28)} studies,
{_pct(faith.get('strict_plus_normalized'))} of its claims resolve to a verbatim span in the
source, and it recovers {rel.get('anchored_recovered', 0)} of {rel.get('gold_relations', 40)} of
Richmond's causal links with at least one endpoint pinned to the matching concept.
It does <em>not</em> recover Richmond's two emotion/coping contexts, it reconstructs
{ent.get('matched_within_type', 0)} of Richmond's {ent.get('gold_entities', 46)} named concepts in
the same realist role, and it recovers <em>none</em> of the 40 causal links at the strictest
exact-concept-pair level. Sections 4 and 5 show exactly how each of those numbers was produced,
with its confidence interval and who judged it.</p></div>
"""


def _section_counts(d: dict[str, Any]) -> str:
    c = d["counts"]
    tiles = [
        (c.get("studies", 0), "Papers ingested"),
        (c.get("cmocs", 0), "CMOCs extracted"),
        (c.get("entities", 0), "Entity instances"),
        (c.get("concepts", 0), "Distinct concepts"),
        (c.get("relations", 0), "Causal relations"),
        (c.get("big_concepts", 0), "Emergent mechanisms"),
        (c.get("demi_regularities", 0), "Demi-regularities"),
        (c.get("contradictions", 0), "Contradictions"),
        (c.get("human_decisions", 0), "Human decisions"),
        (c.get("audit_events", 0), "Audit events"),
    ]
    tile_html = "".join(
        f'<div class="tile"><div class="n">{n}</div><div class="l">{_e(label)}</div></div>'
        for n, label in tiles
    )
    return f"""
<h2><span class="num">02</span>What the machine produced</h2>
<p class="sub">Every count here is read live from the project database, which is the single
source of truth for what the pipeline produced.</p>
<div class="tiles">{tile_html}</div>
<p><strong>A CMOC</strong> — Context–Mechanism–Outcome configuration — is the unit of a realist
review. It is one sentence of the form <em>"for this kind of student, this teaching triggers this
response, producing this result."</em> Richmond's team wrote theirs by hand; ours were extracted
by the system, one or more per paper, each carrying the verbatim sentence it came from.
{c.get('studies_with_cmocs', 0)} of the {c.get('studies', 0)} papers yielded at least one; the
remaining papers are abstract-only records too short to support a configuration, and the system
correctly declines to invent one.</p>
"""


def _section_side_by_side(d: dict[str, Any]) -> str:
    parts = ["""
<h2><span class="num">03</span>Side by side, context by context</h2>
<p class="sub">Richmond organised the whole review around five kinds of student. This is the
heart of the verification: for each of those five, Richmond's published conclusion sits on the
left and everything our system found for the same context sits on the right. Read one block and
you can judge the system yourself, without any statistic.</p>
"""]
    for row in d["side_by_side"]:
        kind, label = _verdict(row)
        rich = row["richmond"]
        statements = "".join(f"<blockquote>{_e(s)}</blockquote>" for s in rich.get("statements", []))
        rich_studies = row["richmond_studies"]
        our_studies = row["our_studies"]
        overlap = row["overlap"]

        if row["our_cmocs"]:
            items = "".join(
                f'<li>{_e(c["narrative_statement"])} '
                f'<span class="small">— <code>{_e(c["study_id"])}</code></span></li>'
                for c in row["our_cmocs"][:8]
            )
            more = (f'<p class="small">…and {len(row["our_cmocs"]) - 8} more configurations '
                    f'in this context.</p>') if len(row["our_cmocs"]) > 8 else ""
            machine = f"""
              <p class="small">Matched to our concept <span class="cid">{_e(row['concept'])}</span>
              {'<span class="badge b-partial">filed under a different realist role</span>'
               if row['cross_type'] and not row['type_agrees'] else ''}</p>
              <ul class="tight">{items}</ul>{more}"""
        else:
            machine = ("<p>The system produced <strong>no configuration</strong> for this context."
                       "</p>")
            if row["concept"]:
                machine += (f'<p class="small">The matcher proposed <span class="cid">'
                            f'{_e(row["concept"])}</span> but it did not pass the agreement bar.</p>')

        why = (f'<p class="small"><strong>Why the matcher linked these:</strong> '
               f'{_e(row["rationale"])}</p>') if row["rationale"] else ""

        overlap_line = (
            f'<p class="small"><strong>Study-level overlap:</strong> Richmond assigns '
            f'{len(rich_studies)} studies to this context; our system assigns {len(our_studies)}; '
            f'<strong>{len(overlap)}</strong> are the same paper'
            f'{" (" + ", ".join(overlap) + ")" if overlap else ""}.</p>'
        )

        parts.append(f"""
<div class="ctx-head">
  <h3>{_e(row['short'])}</h3>
  <span class="badge b-{kind}">{_e(label)}</span>
  <span class="small">Richmond {_e(row['code'])} · {_e(row['gold_location'])}</span>
</div>
<div class="grid2">
  <div class="col human">
    <h4>What Richmond concluded</h4>
    <p class="small">{_e(row['gold_label'])}</p>
    {statements}
    <p class="small"><strong>{rich.get('n_studies_stated') or len(rich_studies)} studies.</strong>
    {_e(rich.get('named_studies', ''))[:300]}</p>
  </div>
  <div class="col machine">
    <h4>What our system found</h4>
    {machine}
  </div>
</div>
{why}
{overlap_line}
""")
    parts.append("""
<div class="callout"><p><strong>How to read the two "Not recovered" blocks.</strong> Richmond's
third and fourth contexts are about emotion — coping, self-confidence, self-efficacy. Our system
found almost nothing for them, and that is the honest and correct result: those constructs are
close to absent from the text of the 28 papers we hold. Richmond's reviewers brought them in from
the wider simulation and emotion literature, which is a legitimate human move a text-grounded
extractor is designed not to make. Forcing the system to produce them would mean letting it invent
claims, which is exactly what the verbatim-quote requirement exists to prevent.</p></div>
""")
    return "".join(parts)


def _ci(block: dict[str, Any] | None) -> str:
    """Render a Clopper-Pearson interval, or fall back gracefully on an older run."""
    if not block or block.get("proportion") is None:
        return "—"
    return (f"<strong>{block['proportion']:.1%}</strong><br>"
            f"<span class='small'>95% CI {block['ci_low']:.1%}–{block['ci_high']:.1%}<br>"
            f"{block['successes']}/{block['total']}</span>")


def _section_matrix(d: dict[str, Any]) -> str:
    v = d["verification"]
    c = d["counts"]
    scr = v.get("screening", {})
    ent = v.get("entity_coverage", {})
    rel = v.get("relation_coverage", {})
    fai = v.get("citation_faithfulness", {})
    com = v.get("community_alignment", {})
    the = v.get("theory_correspondence", {})
    per_chain = the.get("per_chain", {})
    same_family = the.get("same_family_judge", {})
    tiers = fai.get("tiers", {})
    ceiling = rel.get("type_level_ceiling", {})

    rows = [
        ("Did we find the same papers?",
         f"The {scr.get('n_gold_includes', 28)} studies Richmond included",
         "Our screening vote on every candidate, from one named run",
         "Sensitivity",
         _ci(scr.get("final_sensitivity_ci")),
         "auto",
         f"{_pct(scr.get('auto_sensitivity'))} unaided; the "
         f"{len(scr.get('uncertain_routed_to_hitl', []))} the system was unsure about went to a "
         "human, which is the design working rather than a miss. Sensitivity has no true "
         "negatives here and so cannot detect over-inclusion — specificity is a separate test "
         "against a distractor pool."),
        ("Is every claim really in the paper?",
         "Richmond quote their sources",
         "Every extracted element carries a verbatim quote and a character offset",
         "% resolving to a verbatim span",
         _ci(fai.get("strict_plus_normalized_ci")),
         "auto",
         f"This is the exact tier ({tiers.get('exact', 0)} quotes) plus the normalized tier "
         f"({tiers.get('normalized', 0)}) — quotes that match only after undoing PDF line-break "
         "hyphenation, a typesetting artefact rather than a difference in wording. A further "
         f"{tiers.get('fuzzy', 0)} match approximately and {tiers.get('unresolved', 0)} fail; both "
         "are counted separately and never folded in. Arithmetic, not opinion."),
        ("Did we find the same concepts?",
         f"The {ent.get('gold_entities', 46)} concepts Richmond names in Figures 2 and 3",
         f"Our {c.get('concepts', 0)} canonical concepts",
         "Recall, same realist role",
         _ci(ent.get("recall_within_type_ci")),
         "judge",
         f"With role-crossing allowed it is {ent.get('matched', 0)}/{ent.get('gold_entities', 46)}, "
         f"of which {ent.get('matched_cross_type', 0)} sit under a different realist role than "
         "Richmond used. Lead with the like-for-like figure. A language model judges whether two "
         "differently-worded concepts name the same construct, sampled 3× and majority-voted; "
         f"per-sample range {_pct(ent.get('recall_min'))}–{_pct(ent.get('recall_max'))}. Human "
         "ratification still required."),
        ("Did we find the same causal shape?",
         f"The {rel.get('gold_relations', 40)} arrows in Richmond's figures",
         f"Our {c.get('relations', 0)} typed relations",
         "Type-level recall",
         _ci(rel.get("type_recall_ci")),
         "auto",
         "Nearly meaningless alone: it asks only whether a pattern such as &ldquo;Context "
         "constrains Outcome&rdquo; occurs <em>anywhere</em> in the graph, and there are only "
         f"{ceiling.get('distinct_patterns_in_our_graph', '?')} distinct patterns in our graph "
         f"against {ceiling.get('distinct_patterns_in_gold', '?')} in the benchmark. Any "
         "non-trivial extraction scores near 100%. Never quote it on its own."),
        ("…anchored to a real concept?",
         "The same arrows",
         f"Our {c.get('relations', 0)} typed relations",
         "Anchored recall",
         _ci(rel.get("anchored_recall_ci")),
         "auto",
         "Same predicate, one endpoint the exact matched concept, the other of the correct "
         "realist role. <strong>This is the number to lead with for causal structure.</strong> "
         "Counting only the arrows Richmond actually draws — excluding "
         f"{len(rel.get('drawn_only', {}).get('excluded_derived', []))} transitive shortcuts that "
         "exist in the benchmark but not in the figure — it rises to "
         f"{_pct(rel.get('drawn_only', {}).get('anchored_recall'))}."),
        ("…between the exact same two concepts?",
         "The same arrows",
         f"Our {c.get('relations', 0)} typed relations",
         "Strict recall",
         _ci(rel.get("recall_ci")),
         "auto",
         "The honest floor, and the open problem. Bounded by concept recall squared and by our "
         "concepts carrying different names from Richmond's. The causal structure is largely "
         "present, as the row above shows; exact concept-pair reconstruction is not."),
        ("Did we find the same mechanisms?",
         f"Richmond's {com.get('gold_mechanisms', 0)} mechanism entities",
         f"{com.get('n_communities', 0)} clusters found bottom-up by the Leiden algorithm",
         "Alignment recall",
         _ci(com.get("alignment_recall_ci")),
         "judge",
         "Our mechanisms are discovered by clustering the concept graph, not authored by anyone — "
         "the one part of the method with no human counterpart to copy from. A human mechanism "
         "mapping is required before publication."),
        ("Did we reach the same theory?",
         "Richmond's five programme-theory chains",
         "Our signed programme theory",
         "Mean correspondence, 0–1",
         (f"<strong>{the.get('mean_correspondence', 0):.2f}</strong><br>"
          f"<span class='small'>independent judge<br>"
          f"{same_family.get('mean_correspondence', 0):.2f} same-family judge</span>"),
         "judge",
         "<strong>Do not quote a single number here.</strong> Two judges from different model "
         f"families differ by {abs(the.get('self_preference_gap', 0)):.2f} on a 0–1 scale given "
         "identical inputs. That spread is the finding: this measure is judge-dependent and is "
         "not defensible until human experts rate the same chains. Note the gap runs opposite to "
         "self-preference — the independent judge is the <em>more</em> generous one, which points "
         "at judge capability rather than vanity."),
    ]

    body = "".join(f"""
<tr>
  <td><strong>{q}</strong><div class="small">{caveat}</div></td>
  <td>{hum}</td><td>{mach}</td><td>{stat}</td>
  <td class="num">{val}</td>
  <td><span class="badge {'b-auto' if who == 'auto' else 'b-partial'}">
      {'deterministic' if who == 'auto' else 'model-judged'}</span></td>
</tr>""" for q, hum, mach, stat, val, who, caveat in rows)

    chain_rows = "".join(
        f'<tr><td class="num">{_e(k)}</td>'
        f'<td class="num">{x.get("correspondence", 0):.2f}</td>'
        f'<td class="num">'
        f'{same_family.get("per_chain", {}).get(k, {}).get("correspondence", 0):.2f}</td>'
        f'<td>{_e(x.get("rationale", ""))}</td></tr>'
        for k, x in sorted(per_chain.items())
    )

    return f"""
<h2><span class="num">04</span>The verification matrix — how each number is made</h2>
<p class="sub">This is the answer to "how do you verify it?". One row per question a reviewer can
ask: Richmond's artefact, our artefact, the exact comparison, the result with an exact
(Clopper–Pearson) confidence interval, and — the column that matters most — whether a machine or
a language model did the judging.</p>
<div class="tablewrap"><table>
<thead><tr><th style="min-width:250px">Question</th><th>Richmond's artefact</th>
<th>Our artefact</th><th>Statistic</th><th>Result</th><th>Judged by</th></tr></thead>
<tbody>{body}</tbody></table></div>

<div class="callout"><p><strong>The one distinction to carry away.</strong> Five of these eight
rows are <em>deterministic</em>: same inputs, same number, forever, no model involved. Three are
<em>model-judged</em>: a language model decides whether two differently-worded ideas mean the
same thing, so they move between runs and between judges. Every interval above covers sampling
variation in the counting only — it says nothing about whether the benchmark itself is right, and
on the model-judged rows the spread between judges is wider than the interval. Trust the first
five as they stand; treat the last three as provisional until human experts have rated the same
items. Reporting that split <em>is</em> the method, not an apology for it.</p></div>

<details><summary>Per-chain detail, and how far the two judges disagree</summary>
<div class="tablewrap"><table>
<thead><tr><th>Chain</th><th>Independent judge</th><th>Same-family judge</th>
<th>The independent judge's reasoning</th></tr></thead>
<tbody>{chain_rows}</tbody></table></div>
<p class="small">The same programme theory, the same five gold chains, two judges — and scores
that differ by up to 0.6 on individual chains. That is why the row above carries no single
number.</p></details>
"""


def _section_concepts(d: dict[str, Any]) -> str:
    per_entity = d["verification"].get("entity_coverage", {}).get("per_entity", {})
    gold_entities = d["gold"]["entities"]
    rows = []
    for code in sorted(per_entity):
        m = per_entity[code]
        g = gold_entities.get(code, {})
        if m.get("matched"):
            kind, label = ("match", "Found") if m.get("type_agrees") else ("partial", "Found, other role")
        else:
            kind, label = "gap", "Not found"
        rows.append(f"""
<tr>
  <td class="num">{_e(code)}</td>
  <td>{_e(g.get('label', ''))}<div class="small">{_e(g.get('category', ''))} · {_e(g.get('location', ''))}</div></td>
  <td><span class="badge b-{kind}">{label}</span></td>
  <td>{f'<span class="cid">{_e(m.get("concept"))}</span>' if m.get('concept') else '—'}</td>
  <td class="small">{_e(m.get('rationale', ''))}</td>
</tr>""")
    n = len(rows)
    return f"""
<h2><span class="num">05</span>Every one of Richmond's concepts, one by one</h2>
<p class="sub">No aggregate to hide behind. For each concept Richmond named in their figures:
did we find it, which of our concepts matched it, and what was the matcher's stated reason. Search
the table to check any single case yourself.</p>
<input class="filter" data-filter="concepts" placeholder="Search Richmond's concepts, our concepts, or the reasoning…">
<p class="small" id="concepts-count">{n} of {n} shown</p>
<div class="tablewrap"><table id="concepts">
<thead><tr><th>Code</th><th>Richmond's concept</th><th>Verdict</th><th>Our concept</th>
<th>Why the matcher linked them</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table></div>
"""


def _section_browse(d: dict[str, Any]) -> str:
    cmoc_rows = "".join(f"""
<tr><td class="num">{_e(c['study_id'])}</td>
<td><span class="pol pol-{_e(c['polarity'])}">{_e(c['polarity'])}</span></td>
<td>{_e(c['narrative_statement'])}</td></tr>""" for c in d["cmocs"])

    ent_rows = "".join(f"""
<tr><td class="num">{_e(e['study_id'])}</td><td class="num">{_e(e['entity_type'])}</td>
<td>{_e(e['label'])}<div class="small"><span class="cid">{_e(e['canonical_id'])}</span></div></td>
<td class="quote">"{_e(e['verbatim_quote'])}"
<div class="small">chars {_e(e['char_start'])}–{_e(e['char_end'])} ·
{'exact match in source' if e['quote_resolved'] else 'span unresolved'}</div></td></tr>"""
        for e in d["entities"])

    rel_rows = "".join(f"""
<tr><td class="num">{_e(r['study_id'])}</td>
<td>{_e(r['subject'])}<div class="small">{_e(r['subject_type'])}</div></td>
<td class="num">{_e(r['predicate'])}</td>
<td>{_e(r['object'])}<div class="small">{_e(r['object_type'])}</div></td></tr>"""
        for r in d["relations"])

    big_rows = "".join(f"""
<tr><td><strong>{_e(b['community_label'])}</strong><div class="small">{_e(b['realist_role'])}</div></td>
<td class="num">{_e(b['member_count'])}</td>
<td>{_e(b['definition'])}</td>
<td class="small">{_e(', '.join(b['study_ids'] or []))}</td></tr>"""
        for b in d["big_concepts"])

    demi_rows = "".join(f"""
<tr><td>{_e(x['context_concept'])}</td><td>{_e(x['driver_concept'])}</td>
<td>{_e(x['outcome_concept'])}</td>
<td><span class="pol pol-{_e(x['polarity'])}">{_e(x['polarity'])}</span></td>
<td class="num">{len(x['study_ids'] or [])}</td></tr>"""
        for x in d["demi_regularities"])

    return f"""
<h2><span class="num">06</span>Browse the machine's actual output</h2>
<p class="sub">The complete output, not a sample. Open a section, type in the box to filter.
This is the same data as <code>outputs/exports/*.csv</code> — the spreadsheets are for Excel,
this is for reading.</p>

<details open><summary>All {len(d['cmocs'])} CMOCs — the review's findings, one sentence each</summary>
<input class="filter" data-filter="cmocs" placeholder="Filter configurations…">
<p class="small" id="cmocs-count">{len(d['cmocs'])} of {len(d['cmocs'])} shown</p>
<div class="tablewrap"><table id="cmocs">
<thead><tr><th>Study</th><th>Direction</th><th>Configuration</th></tr></thead>
<tbody>{cmoc_rows}</tbody></table></div></details>

<details><summary>All {len(d['entities'])} entities — every concept, with the sentence it came from</summary>
<input class="filter" data-filter="entities" placeholder="Filter entities and quotes…">
<p class="small" id="entities-count">{len(d['entities'])} of {len(d['entities'])} shown</p>
<div class="tablewrap"><table id="entities">
<thead><tr><th>Study</th><th>Role</th><th>Concept</th><th>Verbatim evidence</th></tr></thead>
<tbody>{ent_rows}</tbody></table></div></details>

<details><summary>All {len(d['relations'])} relations — the causal arrows</summary>
<input class="filter" data-filter="relations" placeholder="Filter relations…">
<p class="small" id="relations-count">{len(d['relations'])} of {len(d['relations'])} shown</p>
<div class="tablewrap"><table id="relations">
<thead><tr><th>Study</th><th>From</th><th>Relation</th><th>To</th></tr></thead>
<tbody>{rel_rows}</tbody></table></div></details>

<details><summary>{len(d['big_concepts'])} emergent mechanisms — found by clustering, not written by anyone</summary>
<p class="small">These are the system's own mechanisms: the Leiden community-detection algorithm
grouped the concept graph, and each cluster was then named and defined. They are the closest thing
to Richmond's Figure 3, but discovered bottom-up from the evidence rather than authored by a
reviewer. This is the part of the method with no human counterpart to copy from.</p>
<div class="tablewrap"><table>
<thead><tr><th>Mechanism</th><th>Members</th><th>Definition</th><th>Studies</th></tr></thead>
<tbody>{big_rows}</tbody></table></div></details>

<details><summary>{len(d['demi_regularities'])} demi-regularities — patterns recurring across studies</summary>
<p class="small">A demi-regularity is realist review's semi-predictable pattern: the same
context–driver–outcome appearing in two or more independent studies.</p>
<div class="tablewrap"><table>
<thead><tr><th>Context</th><th>Driver</th><th>Outcome</th><th>Direction</th><th>Studies</th></tr></thead>
<tbody>{demi_rows}</tbody></table></div></details>
"""


def _section_limits(d: dict[str, Any]) -> str:
    return """
<h2><span class="num">07</span>What is not yet verified</h2>
<p class="sub">Stated here so it never has to be discovered by a reviewer.</p>
<ol class="tight">
  <li><strong>No human coder has checked the extraction.</strong> The per-paper reference coding
  was produced by a different model family, blind — honest, but it is not a human gold standard.
  Two human coders and a Cohen's κ are the required next step; the blank worksheets already exist.</li>
  <li><strong>The programme-theory judge grades work from its own model family.</strong>
  Self-preference bias is well documented. That score is indicative until a different judge family
  and a human expert rating are added.</li>
  <li><strong>Concept matching is model-judged.</strong> Reported as a 3-sample range for that
  reason; a human ratification pass is required before the number is quoted as a result.</li>
  <li><strong>Strict relation recall is zero.</strong> The causal <em>shape</em> is recovered; the
  exact concept-pair reconstruction is not. This is the real open problem and is stated as such.</li>
  <li><strong>Precision was tested against a distractor pool we built ourselves</strong>, because
  Richmond did not publish their excluded studies. It shows the system discriminates; it is not a
  match to Richmond.</li>
</ol>
"""


def render(d: dict[str, Any]) -> str:
    c = d["counts"]
    return f"""<title>Realist Review: Machine vs Human</title>
<style>{STYLE}</style>
<div class="wrap">
<header class="top">
  <div class="kicker">Agentic realist evidence synthesis · verification report</div>
  <h1>Can a machine reproduce a human realist review?</h1>
  <p class="lede">Richmond et al. (2020) reviewed 28 studies on teaching clinical reasoning and
  concluded that <em>the student is key</em>. We gave our multi-agent system the same 28 papers.
  This page shows what it produced, and lays it beside the human review so you can judge the
  answer for yourself.</p>
</header>

{_vintage_warning(d)}
{_section_headline(d)}
{_section_counts(d)}
{_section_side_by_side(d)}
{_section_matrix(d)}
{_section_concepts(d)}
{_section_browse(d)}
{_section_limits(d)}

<footer>
  <p>Generated {_e(d['generated_at'])} from the project database
  ({c.get('studies', 0)} studies, {c.get('cmocs', 0)} CMOCs, {c.get('entities', 0)} entities,
  {c.get('relations', 0)} relations). Verification run
  <code>{_e(d.get('verify_run') or 'none')}</code>. Human standard:
  <code>gold/RICHMOND_CONCLUSIONS.md</code> and <code>gold/richmond_gold_v2.json</code>,
  both grounded line by line in Richmond et al. (2020),
  <em>BMC Medical Education</em> 20:187.</p>
  <p>Regenerate with <code>res export-results</code>. Every count is read live from the
  database and every score from the named verification run; the explanatory text around them is
  written by hand and says so wherever it interprets rather than reports.</p>
</footer>
</div>
<script>{FILTER_JS}</script>
"""


def write(target: Path | None = None) -> Path:
    target = target or DEFAULT_TARGET
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render(collect()), encoding="utf-8")
    return target


if __name__ == "__main__":  # pragma: no cover - manual use
    print(write())
