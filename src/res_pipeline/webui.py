"""The single coherent interface for the system (run: ``res webui``).

One local web application, designed as a research instrument rather than a generic
dashboard. It models the review as a STATEFUL pipeline: the home screen shows which
stages have run, which one is ready next, and guards the paid stages — so a reviewer
always knows what to do. It reads and writes the same PostgreSQL source of truth as
the pipeline; there are no scattered files.

Design language: an academic instrument. Warm-cool paper ground, a serif display for
headings, one meaningful colour axis — clay for the HUMAN review, teal for the
MACHINE — because the whole product is a human-vs-machine comparison. No emoji
section markers, no gradient hero.
"""

from __future__ import annotations

import glob
import json
import os
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from res_pipeline.core.config import (
    DATA_DIR,
    GOLD_DIR,
    OUTPUTS_DIR,
    PROJECT_ROOT,
    load_yaml_config,
)
from res_pipeline.core.db import get_connection, log_audit_event

app = FastAPI(title="Realist Synthesis")
INBOX = DATA_DIR / "inbox"

# ── pipeline runner ──────────────────────────────────────────────────────────
_JOB: dict = {"running": False, "stage": None, "log": [], "started": None, "rc": None}
_JOB_LOCK = threading.Lock()
_STAGES = {"ingest": ["ingest"], "ingest-uploaded": ["ingest", "--source", str(INBOX)],
           "screen": ["screen"], "extract-pilot": ["extract", "--limit", "3"],
           "extract": ["extract"], "synthesize": ["synthesize"], "verify": ["verify"],
           "build-lkg": ["build-lkg"], "report": ["report"]}


def _stream(proc: subprocess.Popen) -> None:
    for line in iter(proc.stdout.readline, ""):
        if line:
            _JOB["log"].append(line.rstrip())
            _JOB["log"] = _JOB["log"][-400:]
    proc.wait()
    _JOB["rc"] = proc.returncode
    _JOB["running"] = False


def _launch(label: str, args: list[str]) -> bool:
    """Start a `res <args>` subprocess, streaming stdout to the live console."""
    with _JOB_LOCK:
        if _JOB["running"]:
            return False
        _JOB.update(running=True, stage=label, log=[f"$ res {' '.join(args)}"],
                    started=time.strftime("%H:%M:%S"), rc=None)
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1"}
    proc = subprocess.Popen([sys.executable, "-m", "res_pipeline.cli", *args],
                            cwd=str(PROJECT_ROOT), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, encoding="utf-8", errors="replace", env=env)
    threading.Thread(target=_stream, args=(proc,), daemon=True).start()
    return True


def _start_stage(stage: str) -> bool:
    return _launch(stage, _STAGES[stage]) if stage in _STAGES else False


# Commands a user may type into the console (allowlist — no arbitrary shell).
_ALLOWED_CMDS = {"ingest", "screen", "extract", "synthesize", "verify", "status", "agents",
                 "detect-communities", "retroduce", "report", "build-lkg", "ratify-ipt",
                 "precision-test", "gold-code", "validate-cmocs", "adjudicate", "init-db"}


@app.post("/run/{stage}")
def run_stage(stage: str):
    started = _start_stage(stage)
    return JSONResponse({"started": started, "busy": _JOB["running"] and not started})


@app.post("/run-cmd")
def run_cmd(cmd: str = Form()):
    """Run a user-typed `res` subcommand (allowlisted) — the console is a real terminal."""
    parts = cmd.strip().split()
    if not parts or parts[0] not in _ALLOWED_CMDS:
        allowed = ", ".join(sorted(_ALLOWED_CMDS))
        return JSONResponse({"started": False, "error": f"'{cmd}' not allowed. Try: {allowed}"})
    started = _launch(parts[0], parts)
    return JSONResponse({"started": started, "busy": _JOB["running"] and not started})


@app.get("/run/status")
def run_status():
    return JSONResponse({"running": _JOB["running"], "stage": _JOB["stage"], "rc": _JOB["rc"],
                         "started": _JOB["started"], "log": _JOB["log"][-80:]})


_ALLOWED_UPLOAD = {".pdf", ".txt", ".json", ".jsonl", ".csv"}


@app.post("/upload")
async def upload(files: list[UploadFile] = File(...)):
    """Save uploaded documents to data/inbox/ so they can be ingested generically.

    Accepts any number of PDFs (full text), .txt (abstract sidecars), or .jsonl/.json/.csv
    metadata. The files land in a folder the pipeline can ingest with one click — this is
    what makes the system a general review tool, not a 28-paper fixture.
    """
    from pathlib import Path as _P

    INBOX.mkdir(parents=True, exist_ok=True)
    saved, skipped = [], []
    for f in files:
        name = _P(f.filename or "").name
        if not name or _P(name).suffix.lower() not in _ALLOWED_UPLOAD:
            skipped.append(name or "(unnamed)")
            continue
        (INBOX / name).write_bytes(await f.read())
        saved.append(name)
    return JSONResponse({"saved": saved, "skipped": skipped, "count": len(saved),
                         "folder": str(INBOX)})


@app.post("/upload/clear")
def upload_clear():
    """Empty the inbox (before uploading a fresh corpus)."""
    n = 0
    if INBOX.exists():
        for p in INBOX.iterdir():
            if p.is_file():
                p.unlink()
                n += 1
    return JSONResponse({"removed": n})


# ── design system ────────────────────────────────────────────────────────────
_NAV = [("/", "Control room"), ("/workflow", "Workflow & agents"), ("/inputs", "Inputs"),
        ("/ontology", "Ontology"), ("/graph", "Knowledge graph"), ("/review", "Human review"),
        ("/results", "Machine result"), ("/standard", "Human standard"),
        ("/verify", "Comparison"), ("/raw", "Raw data")]

_STYLE = """<style>
:root{
  --paper:#eceae4; --panel:#f7f5f0; --ink:#20262e; --muted:#5f6874; --line:#d8d4ca;
  --human:#a8482f; --machine:#0e6b74; --good:#2c6e49; --warn:#8a5a12; --bad:#9e3328;
  --good-bg:#e4efe6; --warn-bg:#f4ece0; --bad-bg:#f4e4e1; --rule:#c9c4b8;
}
:root[data-theme="dark"]{
  --paper:#14171b; --panel:#1c2027; --ink:#e7e9ec; --muted:#98a1ad; --line:#2b313a;
  --human:#e08a72; --machine:#63c3cc; --good:#5ec98a; --warn:#e0b34e; --bad:#e88b7f;
  --good-bg:#15301f; --warn-bg:#332a12; --bad-bg:#331b17; --rule:#333a44;
}
@media(prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --paper:#14171b; --panel:#1c2027; --ink:#e7e9ec; --muted:#98a1ad; --line:#2b313a;
  --human:#e08a72; --machine:#63c3cc; --good:#5ec98a; --warn:#e0b34e; --bad:#e88b7f;
  --good-bg:#15301f; --warn-bg:#332a12; --bad-bg:#331b17; --rule:#333a44;
}}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);
  font-family:'Segoe UI',system-ui,-apple-system,sans-serif;line-height:1.55;font-size:15px}
.serif{font-family:'Iowan Old Style','Palatino Linotype',Palatino,Charter,Georgia,serif}
header{border-bottom:1px solid var(--rule);padding:1.1rem 2.2rem;display:flex;align-items:baseline;gap:1rem;
  background:var(--panel)}
header .mark{font-family:'Iowan Old Style',Georgia,serif;font-weight:600;font-size:1.15rem;letter-spacing:.01em}
header .mark b{color:var(--machine)}
header .tl{color:var(--muted);font-size:.82rem;margin-left:auto}
nav{display:flex;gap:0;border-bottom:1px solid var(--rule);background:var(--panel);padding:0 2.2rem;flex-wrap:wrap}
nav a{font-size:.85rem;color:var(--muted);text-decoration:none;padding:.7rem .9rem;border-bottom:2px solid transparent;margin-bottom:-1px}
nav a:hover{color:var(--ink)}
nav a.on{color:var(--ink);border-bottom-color:var(--machine);font-weight:600}
.rawchips{display:flex;flex-wrap:wrap;gap:.35rem;margin:1rem 0 .2rem}
.rawchip{font-size:.78rem;padding:.3rem .55rem;border:1px solid var(--rule);border-radius:4px;
  text-decoration:none;color:var(--ink);background:var(--panel)}
.rawchip.on{border-color:var(--machine);font-weight:600}
.rawscroll{overflow:auto;max-height:70vh;border:1px solid var(--rule)}
.rawtable{border-collapse:collapse;font-size:.76rem;font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
.rawtable th{position:sticky;top:0;background:var(--panel);border-bottom:1px solid var(--rule);
  padding:.4rem .5rem;text-align:left;white-space:nowrap;z-index:1}
.rawtable td{border-bottom:1px solid var(--rule);padding:.35rem .5rem;vertical-align:top;
  max-width:30rem;word-break:break-word}
main{max-width:1000px;margin:0 auto;padding:1.8rem 2.2rem 4rem}
h2.title{font-family:'Iowan Old Style',Georgia,serif;font-weight:600;font-size:1.7rem;margin:0 0 .2rem;letter-spacing:-.01em}
.lead{color:var(--muted);margin:0 0 1.4rem;max-width:64ch;font-size:.96rem}
h3{font-family:'Iowan Old Style',Georgia,serif;font-weight:600;font-size:1.15rem;margin:1.6rem 0 .5rem}
.eyebrow{text-transform:uppercase;letter-spacing:.13em;font-size:.7rem;font-weight:700;color:var(--muted);margin-bottom:.5rem}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:4px;padding:1.2rem 1.3rem;margin:.9rem 0}
.rule{height:1px;background:var(--rule);border:none;margin:1.6rem 0}
/* stepper */
.stepper{display:flex;gap:0;margin:.4rem 0 1.2rem;border:1px solid var(--line);border-radius:4px;overflow:hidden;background:var(--panel)}
.stp{flex:1;padding:.9rem 1rem;border-right:1px solid var(--line);position:relative;min-width:0}
.stp:last-child{border-right:none}
.stp .st{display:flex;align-items:center;gap:.45rem;font-size:.72rem;text-transform:uppercase;letter-spacing:.06em;font-weight:700}
.stp .nm{font-family:'Iowan Old Style',Georgia,serif;font-size:1.02rem;margin:.25rem 0 .1rem}
.stp .ct{font-size:.78rem;color:var(--muted)}
.dot{width:.7rem;height:.7rem;border-radius:50%;flex:none}
.dot.done{background:var(--machine)}.dot.ready{background:transparent;border:2px solid var(--machine)}
.dot.locked{background:var(--line)}.dot.run{background:var(--warn);animation:pulse 1s infinite}
@keyframes pulse{50%{opacity:.4}}
.stp.done .st{color:var(--machine)}.stp.ready{background:color-mix(in srgb,var(--machine) 7%,var(--panel))}
.stp.locked{opacity:.55}.stp.ready .st{color:var(--ink)}
/* buttons */
.btn{font:inherit;font-size:.85rem;font-weight:600;padding:.5rem 1rem;border-radius:4px;cursor:pointer;
  border:1px solid var(--machine);background:var(--machine);color:var(--paper)}
.btn:hover{filter:brightness(1.06)}
.btn.ghost{background:transparent;color:var(--machine)}
.btn.human{background:var(--human);border-color:var(--human)}
.btn:disabled{opacity:.4;cursor:not-allowed;filter:none}
.btn.sm{padding:.35rem .7rem;font-size:.8rem}
.cost{font-size:.72rem;color:var(--warn);font-weight:700;margin-left:.4rem}
/* metrics */
.metrics{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:1px;background:var(--line);
  border:1px solid var(--line);border-radius:4px;overflow:hidden}
.metric{background:var(--panel);padding:.9rem 1rem}
.metric .n{font-size:1.7rem;font-weight:700;font-variant-numeric:tabular-nums;line-height:1}
.metric .l{color:var(--muted);font-size:.76rem;margin-top:.3rem;text-transform:uppercase;letter-spacing:.04em}
.good{color:var(--good)}.warn{color:var(--warn)}.bad{color:var(--bad)}.machine{color:var(--machine)}.human{color:var(--human)}
/* score bars */
.sb{display:grid;grid-template-columns:1fr 120px 46px;align-items:center;gap:.8rem;margin:.5rem 0;font-size:.9rem}
.sbbar{height:7px;background:var(--line);border-radius:4px;overflow:hidden}
.sbfill{display:block;height:100%}.sbfill.good{background:var(--good)}.sbfill.warn{background:var(--warn)}
.sbn{text-align:right;font-variant-numeric:tabular-nums;font-weight:700}
/* job log — a live terminal console, always visible */
.jobbox{margin-top:.9rem;border:1px solid #2a2f38;border-radius:6px;background:#12151a;display:none;overflow:hidden}
.jobbox.show{display:block}
.jobhead{padding:.5rem .8rem;border-bottom:1px solid #2a2f38;display:flex;align-items:center;gap:.6rem;background:#191d24}
.dots{display:inline-flex;gap:.28rem}.dots i{width:.6rem;height:.6rem;border-radius:50%;background:#3a4048;display:block}
.dots i:nth-child(1){background:#e06c5f}.dots i:nth-child(2){background:#e0b34e}.dots i:nth-child(3){background:#63c98a}
.jobstate{font-size:.82rem;font-weight:700;letter-spacing:.02em;display:inline-flex;align-items:center;gap:.5rem}
.jobstate.idle{color:#8b95a3}.jobstate.run{color:#ffcf5c}.jobstate.ok{color:#63c98a}.jobstate.err{color:#ef8c7f}
.jobtimer{margin-left:auto;color:#6b7480;font-size:.76rem;font-variant-numeric:tabular-nums;font-family:ui-monospace,Consolas,monospace}
.spin{width:.72rem;height:.72rem;border:2px solid #ffcf5c;border-top-color:transparent;border-radius:50%;
  display:inline-block;animation:spin .7s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
.joblog{margin:0;padding:.8rem 1rem;min-height:220px;max-height:440px;overflow:auto;
  font-family:ui-monospace,Consolas,monospace;font-size:.78rem;line-height:1.6;white-space:pre-wrap;color:#c7d0dc}
.joblog.live::after{content:"▋";color:#ffcf5c;animation:blink 1s steps(2) infinite}
@keyframes blink{50%{opacity:0}}
.jobcmd{display:flex;align-items:center;gap:.5rem;padding:.5rem .7rem;border-top:1px solid #2a2f38;background:#191d24}
.jobcmd .cprompt{color:#63c98a;font-family:ui-monospace,Consolas,monospace;font-weight:700;font-size:.82rem}
.jobcmd input{flex:1;background:#0e1116;border:1px solid #2a2f38;color:#c7d0dc;border-radius:4px;
  padding:.35rem .55rem;font-family:ui-monospace,Consolas,monospace;font-size:.78rem}
.jobcmd input:focus{outline:none;border-color:#0e6b74}
/* review cards — show the machine's work, then ask */
.revcard{border:1px solid var(--line);border-radius:4px;margin:.7rem 0;overflow:hidden;background:var(--panel)}
.revtop{display:flex;justify-content:space-between;align-items:center;gap:.6rem;padding:.6rem .9rem;
  border-bottom:1px solid var(--line);font-family:'Iowan Old Style',Georgia,serif}
.revwhat{padding:.7rem .9rem;background:color-mix(in srgb,var(--machine) 5%,var(--panel))}
.revask{padding:.7rem .9rem;border-top:1px solid var(--line);background:color-mix(in srgb,var(--human) 6%,var(--panel))}
/* data-processing flow */
.pipeflow{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:.6rem;margin-top:.5rem}
.pf{border:1px solid var(--line);border-radius:4px;padding:.6rem .7rem;background:var(--paper)}
.pf b{display:block;color:var(--machine);font-size:.82rem;margin-bottom:.25rem}
.pf span{font-size:.8rem;color:var(--muted);line-height:1.45}
#drop.drag{border-color:var(--machine);background:color-mix(in srgb,var(--machine) 8%,var(--paper))}
/* workflow steps + agent cards */
.wf{position:relative;padding-left:2.4rem;margin:.2rem 0}
.wf .step{border-left:2px solid var(--line);padding:0 0 1.1rem 1.2rem;position:relative}
.wf .step:last-child{border-left-color:transparent}
.wf .num{position:absolute;left:-1.15rem;top:-.15rem;width:1.85rem;height:1.85rem;border-radius:50%;
  background:var(--machine);color:var(--paper);display:flex;align-items:center;justify-content:center;
  font-weight:700;font-size:.82rem;font-family:Georgia,serif}
.wf.human .num{background:var(--human)}
.wf .st-t{font-family:'Iowan Old Style',Georgia,serif;font-size:1.05rem;font-weight:600;margin-bottom:.15rem}
.wf .st-d{color:var(--muted);font-size:.9rem;line-height:1.5}
.wf .st-d b{color:var(--ink)}
.agentcard{border:1px solid var(--line);border-radius:5px;padding:.8rem .95rem;background:var(--panel);margin:.5rem 0}
.agentcard .ac-h{display:flex;justify-content:space-between;align-items:baseline;gap:.6rem;margin-bottom:.3rem}
.agentcard .ac-t{font-family:'Iowan Old Style',Georgia,serif;font-weight:600;font-size:1rem}
.agentcard .ac-tier{font-family:ui-monospace,Consolas,monospace;font-size:.72rem;color:var(--machine);
  background:color-mix(in srgb,var(--machine) 10%,transparent);padding:.1rem .45rem;border-radius:3px}
.agentcard .ac-does{font-size:.88rem;margin:.15rem 0}
.agentcard .ac-mirror{font-size:.82rem;color:var(--muted);border-top:1px dashed var(--line);padding-top:.35rem;margin-top:.35rem}
.hitlrow{display:flex;gap:.6rem;align-items:baseline;padding:.4rem 0;border-bottom:1px solid var(--line);font-size:.9rem}
.hitlrow .hk{font-weight:700;color:var(--human);font-family:ui-monospace,Consolas,monospace;font-size:.8rem;min-width:4rem}
/* tables + compare */
table{width:100%;border-collapse:collapse;font-size:.88rem}
th,td{text-align:left;padding:.5rem .6rem;border-bottom:1px solid var(--line);vertical-align:top}
th{color:var(--muted);font-weight:600;font-size:.78rem;text-transform:uppercase;letter-spacing:.04em}
code{font-family:ui-monospace,Consolas,monospace;font-size:.85em;background:var(--paper);padding:.05rem .3rem;border-radius:3px}
.two{display:grid;grid-template-columns:1fr 1fr;gap:1rem}@media(max-width:720px){.two{grid-template-columns:1fr}}
.cmp{border:1px solid var(--line);border-radius:4px;overflow:hidden}
.cmp .ch{padding:.7rem 1rem;font-family:'Iowan Old Style',Georgia,serif;font-weight:600;border-bottom:1px solid var(--line);
  display:flex;justify-content:space-between;align-items:center;gap:.6rem}
.cmp .cc{display:grid;grid-template-columns:1fr 1fr}
.cmp .col{padding:.9rem 1rem}.cmp .col+.col{border-left:1px solid var(--line)}
.who{font-size:.7rem;font-weight:700;text-transform:uppercase;letter-spacing:.07em;margin-bottom:.4rem}
.who.h{color:var(--human)}.who.m{color:var(--machine)}
.li{font-size:.88rem;margin:.3rem 0;padding-left:1.3rem;position:relative}
.li.e::before{content:"›";position:absolute;left:.1rem;color:var(--good);font-weight:700}
.li.x::before{content:"×";position:absolute;left:.1rem;color:var(--bad);font-weight:700}
.tag{font-size:.7rem;font-weight:700;padding:.12rem .55rem;border-radius:3px}
.tag.match{background:var(--good-bg);color:var(--good)}.tag.part{background:var(--warn-bg);color:var(--warn)}.tag.gap{background:var(--bad-bg);color:var(--bad)}
.quote{border-left:2px solid var(--rule);padding:.3rem .8rem;color:var(--ink);font-style:italic;margin:.4rem 0;font-size:.9rem}
.muted{color:var(--muted);font-size:.85rem}.done{color:var(--good);font-weight:600}
.pill{font-size:.72rem;font-weight:700;padding:.12rem .5rem;border-radius:3px}
.pill.pos{background:var(--good-bg);color:var(--good)}.pill.neg{background:var(--bad-bg);color:var(--bad)}.pill.mix{background:var(--warn-bg);color:var(--warn)}
form.f{display:flex;gap:.5rem;flex-wrap:wrap;align-items:center;margin-top:.6rem}
input{font:inherit;font-size:.86rem;padding:.4rem;border:1px solid var(--line);border-radius:3px;background:var(--paper);color:var(--ink)}
a.tl{color:var(--machine)}
</style>"""


def _page(active: str, body: str) -> HTMLResponse:
    nav = "".join(f'<a href="{h}" class="{"on" if h == active else ""}">{l}</a>' for h, l in _NAV)
    return HTMLResponse(
        f"<!doctype html><html><head><meta charset='utf-8'>"
        f"<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>Realist Synthesis</title>{_STYLE}</head><body>"
        f"<header><span class='mark'>Realist Evidence Synthesis<b>.</b></span>"
        f"<span class='tl'>automating a realist review · benchmark: Richmond et&nbsp;al. 2020</span></header>"
        f"<nav>{nav}</nav><main>{body}</main></body></html>")


# ── pipeline state model ─────────────────────────────────────────────────────
def _pipeline_state() -> tuple[list[dict], dict]:
    with get_connection() as c:
        g = lambda q: c.execute(q).fetchone()["n"]  # noqa: E731
        studies = g("SELECT count(*) n FROM studies")
        screened = g("SELECT count(DISTINCT study_id) n FROM screening_decisions WHERE decider LIKE 'combined:%'")
        extracted = g("SELECT count(DISTINCT study_id) n FROM cmocs")
        try:
            synth = g("SELECT count(*) n FROM programme_theories")
        except Exception:
            synth = 0
        pend_screen = g("SELECT count(*) n FROM (SELECT DISTINCT ON (study_id) study_id,decision "
                        "FROM screening_decisions WHERE decider LIKE 'combined:%' ORDER BY study_id,created_at DESC) t "
                        "WHERE decision='uncertain' AND study_id NOT IN (SELECT study_id FROM screening_decisions WHERE decider LIKE 'human:%')")
        try:
            pend_conf = g("SELECT count(*) n FROM contradictions WHERE resolution IS NULL")
        except Exception:
            pend_conf = 0
    verify_done = bool(glob.glob(str(OUTPUTS_DIR / "runs" / "verify-*" / "verification_report.json")))
    raw = [
        {"id": "ingest", "name": "Ingest", "done": studies > 0, "count": f"{studies} papers", "cost": False,
         "runs": ["ingest"], "what": "load the corpus into the system"},
        {"id": "screen", "name": "Screen", "done": screened > 0, "count": f"{screened} screened", "cost": True,
         "runs": ["screen"], "what": "two models decide include / exclude"},
        {"id": "extract", "name": "Extract", "done": extracted > 0, "count": f"{extracted} papers coded", "cost": True,
         "runs": ["extract-pilot", "extract"], "what": "pull out the CMOCs with quotes"},
        {"id": "synthesize", "name": "Synthesise", "done": synth > 0, "count": "theory built" if synth else "—",
         "cost": True, "runs": ["synthesize"], "what": "graph, patterns, programme theory"},
        {"id": "verify", "name": "Verify", "done": verify_done, "count": "scored" if verify_done else "—",
         "cost": True, "runs": ["verify"], "what": "compare to Richmond"},
    ]
    ready_set = False
    for st in raw:
        if st["done"]:
            st["state"] = "done"
        elif not ready_set:
            st["state"] = "ready"
            ready_set = True
        else:
            st["state"] = "locked"
    return raw, {"pend_screen": pend_screen, "pend_conf": pend_conf}


def _latest_report() -> dict | None:
    reps = sorted(glob.glob(str(OUTPUTS_DIR / "runs" / "verify-*" / "verification_report.json")),
                  key=os.path.getmtime)  # by mtime — hex run-ids don't sort chronologically
    return json.load(open(reps[-1], encoding="utf-8")) if reps else None


def _pending_reviews() -> dict:
    """Items awaiting human judgement, WITH the context a reviewer needs to decide."""
    with get_connection() as c:
        screen = c.execute(
            "SELECT DISTINCT ON (sd.study_id) sd.study_id, s.title, s.year, s.abstract "
            "FROM screening_decisions sd JOIN studies s USING (study_id) "
            "WHERE sd.decider LIKE 'combined:%' AND sd.decision='uncertain' "
            "AND sd.study_id NOT IN (SELECT study_id FROM screening_decisions WHERE decider LIKE 'human:%') "
            "ORDER BY sd.study_id, sd.created_at DESC").fetchall()
        for r in screen:
            r_votes = c.execute(
                "SELECT decider, decision, rationale FROM screening_decisions "
                "WHERE study_id=%s AND decider LIKE 'model:%%' ORDER BY id DESC LIMIT 2",
                (r["study_id"],)).fetchall()
            r["votes"] = [dict(v) for v in r_votes]
        conf = c.execute(
            "SELECT id, driver_concept, positive_studies, negative_studies, positive_contexts, negative_contexts "
            "FROM contradictions WHERE resolution IS NULL ORDER BY id").fetchall()
        # summary of what's already been decided, so the section is never blank/confusing
        auto_inc = c.execute("SELECT count(*) n FROM (SELECT DISTINCT ON (study_id) decision FROM screening_decisions "
                             "WHERE decider LIKE 'combined:%' ORDER BY study_id, created_at DESC) t WHERE decision='include'").fetchone()["n"]
        human_dec = c.execute("SELECT count(DISTINCT study_id) n FROM screening_decisions WHERE decider LIKE 'human:%'").fetchone()["n"]
        conf_done = c.execute("SELECT count(*) n FROM contradictions WHERE resolution IS NOT NULL").fetchone()["n"]
        conf = [dict(x) for x in conf]
        for x in conf:
            x["evidence"] = _contradiction_evidence(c, x)
    return {"screen": [dict(r) for r in screen], "conf": [dict(r) for r in conf],
            "auto_inc": auto_inc, "human_dec": human_dec, "conf_done": conf_done}


def _contradiction_evidence(c, r: dict) -> dict:
    """The evidence a reviewer needs to answer "which context flips the outcome?".

    The question is unanswerable from study ids and context family codes alone, which is
    all this card used to show: measured 2026-11-04 over the 20 stored contradictions,
    2 of them print IDENTICAL context lists on both sides, and 14 have at least one study
    on BOTH sides with nothing to say why. The deciding variable is usually inside the
    CMOC narratives — in contradiction 12 it is whether novices were *instructed* in a
    strategy or told to use "whatever comes naturally", which no context family encodes.
    So the narratives and their verbatim quotes are what this returns.
    """
    def _norm(v):
        if v is None:
            return []
        if isinstance(v, str):
            return [x.strip() for x in v.replace(";", ",").split(",") if x.strip()]
        return list(v)

    pos_s, neg_s = _norm(r.get("positive_studies")), _norm(r.get("negative_studies"))
    pos_c, neg_c = set(_norm(r.get("positive_contexts"))), set(_norm(r.get("negative_contexts")))

    def side(study_ids: list[str], polarity: str) -> list[dict]:
        out = []
        for sid in study_ids[:4]:
            st = c.execute("SELECT title, year FROM studies WHERE study_id=%s", (sid,)).fetchone()
            cmocs = c.execute(
                "SELECT cmoc_id, narrative_statement FROM cmocs "
                "WHERE study_id=%s AND polarity=%s ORDER BY cmoc_id LIMIT 2",
                (sid, polarity)).fetchall()
            items = []
            for m in cmocs:
                quotes = c.execute(
                    "SELECT entity_type, label, verbatim_quote FROM entity_instances "
                    "WHERE cmoc_id=%s AND verbatim_quote IS NOT NULL "
                    "ORDER BY entity_id LIMIT 2", (m["cmoc_id"],)).fetchall()
                items.append({"narrative": m["narrative_statement"],
                              "quotes": [dict(q) for q in quotes]})
            out.append({"sid": sid, "title": (st or {}).get("title", ""),
                        "year": (st or {}).get("year", ""), "cmocs": items})
        return out

    return {
        "pos": side(pos_s, "positive"), "neg": side(neg_s, "negative"),
        "pos_more": max(0, len(pos_s) - 4), "neg_more": max(0, len(neg_s) - 4),
        "both_sides": sorted(set(pos_s) & set(neg_s)),
        "ctx_only_pos": sorted(pos_c - neg_c), "ctx_only_neg": sorted(neg_c - pos_c),
        "ctx_identical": bool(pos_c) and pos_c == neg_c,
    }


def _esc(s) -> str:
    return (str(s or "")).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _review_block(pend: dict, *, compact: bool = False) -> str:
    """Render the pending human-review items WITH the machine's work shown, so a
    reviewer can actually judge. Used both inline on the Control room and on /review."""
    out = []
    # ---- Screening decisions the two models disagreed / were unsure on ----
    for r in pend["screen"]:
        votes = ""
        for v in r.get("votes", []):
            model = v["decider"].split(":")[-1]
            dec = v["decision"]
            pill = {"include": "pos", "exclude": "neg"}.get(dec, "mix")
            votes += (f'<div style="margin:.3rem 0"><span class="pill {pill}">{model}: {dec}</span> '
                      f'<span class="muted">{_esc((v.get("rationale") or "")[:220])}</span></div>')
        out.append(
            f'<div class="revcard"><div class="revtop"><b>{_esc(r["study_id"])} · {_esc(r["title"][:90])}</b>'
            f'<span class="tag part">needs your call</span></div>'
            f'<div class="revwhat"><div class="who m">What the machine saw</div>'
            f'<div class="muted" style="margin:.2rem 0 .5rem">{_esc((r.get("abstract") or "(no abstract on file)")[:420])}…</div>'
            f'<div class="who m">How the two screening models voted</div>{votes or "<div class=muted>(no model rationale stored)</div>"}</div>'
            f'<div class="revask"><div class="who h">Your decision — is this study eligible?</div>'
            f'<form class="f" method="post" action="/review/screen">'
            f'<input type="hidden" name="sid" value="{_esc(r["study_id"])}">'
            f'<input name="reviewer" placeholder="Your name" required style="max-width:140px">'
            f'<input name="reason" placeholder="Reason for your call" required style="min-width:220px">'
            f'<button class="btn human sm" name="decision" value="include">Include</button>'
            f'<button class="btn ghost sm" name="decision" value="exclude">Exclude</button></form></div></div>')
    # ---- Contradictions: same driver, opposite outcomes ----
    for r in pend["conf"]:
        ev = r.get("evidence") or {}

        def _col(rows: list[dict], more: int) -> str:
            # One side of the comparison: real titles, the machine's own sentence, its quotes.
            if not rows:
                return '<div class="muted">(no studies on this side)</div>'
            html = ""
            for st in rows:
                html += (f'<div style="margin:.55rem 0 .8rem"><b>[{_esc(st["sid"])}]</b> '
                         f'{_esc((st["title"] or "")[:120])} <span class="muted">({_esc(st["year"])})</span>')
                for m in st["cmocs"]:
                    html += (f'<div class="muted" style="margin:.25rem 0 .2rem .6rem;font-size:.84rem">'
                             f'{_esc((m["narrative"] or "")[:260])}</div>')
                    for q in m["quotes"]:
                        html += (f'<div style="margin:.15rem 0 .3rem 1.1rem;font-size:.8rem">'
                                 f'<span class="muted">{_esc(q["entity_type"])}: {_esc(q["label"])}</span><br>'
                                 f'<span style="opacity:.85">&ldquo;{_esc((q["verbatim_quote"] or "")[:190])}&rdquo;</span></div>')
                html += "</div>"
            if more:
                html += f'<div class="muted" style="font-size:.8rem">+{more} more study(ies) on this side</div>'
            return html

        # The two things that previously made the question unanswerable, now stated outright.
        notes = ""
        if ev.get("ctx_identical"):
            notes += ('<div class="muted" style="margin:.3rem 0;font-size:.84rem">'
                      '<b>The machine labelled both sides with the same contexts.</b> It cannot tell '
                      'them apart from its context taxonomy &mdash; the deciding difference, if there is '
                      'one, is in the evidence below. This is precisely the judgement it needs from you.</div>')
        else:
            only_p = ", ".join(x.split(":")[-1].replace("-", " ") for x in ev.get("ctx_only_pos", []))
            only_n = ", ".join(x.split(":")[-1].replace("-", " ") for x in ev.get("ctx_only_neg", []))
            if only_p or only_n:
                notes += ('<div class="muted" style="margin:.3rem 0;font-size:.84rem">'
                          f'<b>Context labels that differ</b> &mdash; only when it worked: '
                          f'<i>{_esc(only_p or "none")}</i>; only when it did not: <i>{_esc(only_n or "none")}</i></div>')
        if ev.get("both_sides"):
            notes += ('<div class="muted" style="margin:.3rem 0;font-size:.84rem">'
                      f'<b>{len(ev["both_sides"])} study(ies) appear on BOTH sides</b> '
                      f'({_esc(", ".join(ev["both_sides"]))}) &mdash; the same paper reported the driver '
                      'helping in one configuration and not in another, so the difference is inside the '
                      'study, not between studies.</div>')

        out.append(
            f'<div class="revcard"><div class="revtop"><b>{_esc(r["driver_concept"].split(":")[-1].replace("-"," "))}</b>'
            f'<span class="tag gap">contradiction</span></div>'
            f'<div class="revwhat"><div class="who m">What the machine found &mdash; the same driver led to opposite outcomes</div>'
            f'{notes}'
            f'<div class="two" style="margin-top:.5rem">'
            f'<div><span class="pill pos">it worked here</span>{_col(ev.get("pos", []), ev.get("pos_more", 0))}</div>'
            f'<div><span class="pill neg">it did not work here</span>{_col(ev.get("neg", []), ev.get("neg_more", 0))}</div>'
            f'</div></div>'
            f'<div class="revask"><div class="who h">Your judgement &mdash; what is actually different between the two sides?</div>'
            f'<div class="muted" style="font-size:.82rem;margin:.15rem 0 .4rem">Read the two columns and name the '
            f'condition that separates them, in your own words. You do not need the machine&rsquo;s vocabulary.</div>'
            f'<form class="f" method="post" action="/review/conflict"><input type="hidden" name="cid" value="{r["id"]}">'
            f'<input name="reviewer" placeholder="Your name" required style="max-width:140px">'
            f'<input name="resolution" placeholder="e.g. students were explicitly taught the strategy, vs left to choose their own" required style="min-width:300px">'
            f'<button class="btn human sm" type="submit">Save resolution</button></form></div></div>')

    if not out:
        return ('<div class="panel" style="border-left:3px solid var(--good)">'
                f'<b class="done">Nothing is waiting for you right now.</b><br>'
                f'<span class="muted">The machine has already settled {pend["auto_inc"]} inclusions automatically, '
                f'you have adjudicated {pend["human_dec"]} borderline study(ies), and {pend["conf_done"]} contradiction(s) '
                f'are resolved. New items appear here whenever a stage finishes and the machine is unsure.</span></div>')
    head = ('' if compact else
            f'<p class="muted" style="margin:.2rem 0 .7rem">The machine only stops for you when it is <b>unsure</b>. '
            f'Below is exactly what it produced for each undecided item — read it, then make the call. '
            f'It has already auto-settled {pend["auto_inc"]} clear inclusions.</p>')
    return head + "".join(out)


def _corpus_panel() -> str:
    """Interactive DATA section: upload any N documents, see what's loaded, and read how
    the pipeline turns raw files into a provenance-bearing knowledge graph."""
    with get_connection() as c:
        rows = c.execute(
            "SELECT source_kind, count(*) n FROM studies GROUP BY source_kind"
        ).fetchall()
        total = c.execute("SELECT count(*) n FROM studies").fetchone()["n"]
        units = c.execute("SELECT count(*) n FROM text_units").fetchone()["n"]
    by = {r["source_kind"]: r["n"] for r in rows}
    ft, ab = by.get("fulltext_pdf", 0), by.get("abstract_only", 0)
    inbox_n = len([p for p in INBOX.iterdir() if p.is_file()]) if INBOX.exists() else 0
    inbox_note = (f'<span class="pill pos">{inbox_n} file(s) uploaded, ready to ingest</span>'
                  if inbox_n else '<span class="muted">no uploaded files waiting</span>')
    return f"""
    <div class="panel"><div class="eyebrow">0 · Data — upload your corpus &amp; see how it is processed</div>
      <div class="two" style="gap:1.2rem">
        <div>
          <div id="drop" style="border:2px dashed var(--rule);border-radius:6px;padding:1.2rem;
            text-align:center;cursor:pointer;background:var(--paper)">
            <div style="font-size:1.5rem">⤓</div>
            <div><b>Drop PDFs / JSON here</b> or click to choose</div>
            <div class="muted" style="font-size:.8rem">PDF · .txt (abstract) · .jsonl/.csv (metadata) · any number of files</div>
          </div>
          <input id="fileinput" type="file" multiple accept=".pdf,.txt,.json,.jsonl,.csv" style="display:none">
          <div id="uploadmsg" class="muted" style="margin:.5rem 0;font-size:.85rem">{inbox_note}</div>
          <button class="btn" id="uploadbtn" disabled>Upload selected</button>
          <button class="btn ghost sm" onclick="run('ingest-uploaded')" {'' if inbox_n else 'disabled'}
            id="ingestup">Ingest uploaded files →</button>
          <button class="btn ghost sm" onclick="clearInbox()">Clear</button>
        </div>
        <div>
          <div class="metrics"><div class="metric"><div class="n machine">{total}</div>
            <div class="l">documents in corpus</div></div>
            <div class="metric"><div class="n">{ft}</div><div class="l">full-text PDF</div></div>
            <div class="metric"><div class="n">{ab}</div><div class="l">abstract-only</div></div>
            <div class="metric"><div class="n">{units}</div><div class="l">text units</div></div></div>
          <a class="tl" href="/inputs">See the full document list →</a>
        </div>
      </div>
      <hr class="rule" style="margin:1rem 0">
      <div class="eyebrow">How your data is processed (the same for 28 or 1000 papers)</div>
      <div class="pipeflow">
        <div class="pf"><b>1 Ingest</b><span>PDF/abstract → clean text; each file gets a stable
          Study ID; text split into overlapping <b>units</b> with exact character offsets so every
          later claim can point back to a span.</span></div>
        <div class="pf"><b>2 Screen</b><span>two models vote include/exclude on theory-relevance;
          disagreements go to you (HITL-1).</span></div>
        <div class="pf"><b>3 Extract</b><span>per paper, an agent pulls C→M→O configurations, each
          element carrying a <b>verbatim quote</b>; a second agent checks every one.</span></div>
        <div class="pf"><b>4 Graph</b><span>quotes resolve to spans; synonymous concepts merge;
          Leiden finds emergent conceptual entities → the knowledge graph.</span></div>
        <div class="pf"><b>5 Synthesise</b><span>recurring patterns + contradictions → a programme
          theory you sign off (HITL-4).</span></div>
      </div>
    </div>"""


# ── Control room (home) ──────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
def home():
    stages, pend = _pipeline_state()
    stp = ""
    for st in stages:
        dot = {"done": "done", "ready": "ready", "locked": "locked"}[st["state"]]
        label = {"done": "done", "ready": "next up", "locked": "locked"}[st["state"]]
        stp += (f'<div class="stp {st["state"]}"><div class="st"><span class="dot {dot}"></span>{label}</div>'
                f'<div class="nm">{st["name"]}</div><div class="ct">{st["count"] if st["state"]=="done" else st["what"]}</div></div>')
    # controls: only the ready stage's buttons enabled
    ready = next((s for s in stages if s["state"] == "ready"), None)
    ctrl = ""
    if ready:
        for rk in ready["runs"]:
            lbl = {"ingest": "Run ingest", "screen": "Run screening", "extract-pilot": "Extract — pilot (3 papers)",
                   "extract": "Extract — all 28", "synthesize": "Run synthesis", "verify": "Run verification"}[rk]
            cost = '<span class="cost">uses paid API</span>' if rk in ("screen", "extract", "extract-pilot", "synthesize", "verify") else ""
            ctrl += f'<button class="btn" data-run onclick="run(\'{rk}\')">{lbl}</button>{cost} '
        ctrl = f'<p class="muted" style="margin:.2rem 0 .7rem">Next step: <b>{ready["name"]}</b> — {ready["what"]}.</p>{ctrl}'
    else:
        ctrl = '<p class="done">✓ All stages complete. Re-run any stage below, or review the results.</p>'
        ctrl += " ".join(f'<button class="btn ghost sm" data-run onclick="run(\'{s["runs"][-1]}\')">Re-run {s["name"].lower()}</button>' for s in stages)

    rev = _pending_reviews()
    npend = pend["pend_screen"] + pend["pend_conf"]
    body = f"""
    <div class="eyebrow">Control room · one continuous workspace</div>
    <h2 class="title serif">Run it, watch it run, review what it made — on one screen</h2>
    <p class="lead">The pipeline runs one stage at a time. You press <i>next up</i>, the live console
    below shows it working, and the moment it needs a human it surfaces the item right here — no tab-hunting.</p>
    <div class="stepper">{stp}</div>

    {_corpus_panel()}

    <div class="panel">
      <div class="eyebrow">1 · Operate</div>{ctrl}
      <div id="jobbox" class="jobbox show">
        <div class="jobhead"><span class="dots"><i></i><i></i><i></i></span>
          <span id="jobstate" class="jobstate idle">Idle — nothing running</span>
          <span id="jobtimer" class="jobtimer"></span></div>
        <pre class="joblog" id="joblog">Press a Run button above, or type a command below — everything the program prints stays here so you can read it after it finishes.</pre>
        <div class="jobcmd"><span class="cprompt">res</span>
          <input id="cmdinput" autocomplete="off" spellcheck="false"
            placeholder="type a command and press Enter — e.g. status · screen --limit 5 · detect-communities · agents">
          <button class="btn sm" id="cmdrun">Run</button></div>
      </div>
    </div>

    <div class="panel" id="reviewpanel" style="border-left:3px solid var(--human)">
      <div class="eyebrow">2 · Your review{f' · <span class="human">{npend} waiting</span>' if npend else ''}</div>
      {_review_block(rev, compact=True)}
      <div style="margin-top:.6rem"><a class="tl" href="/review">Open the full review page →</a></div>
    </div>

    <div class="panel">
      <div class="eyebrow">3 · Result vs Richmond</div>{_scorebars()}
      <a class="tl" href="/verify">Full side-by-side comparison →</a>
    </div>

    <script>
    let poller=null, wasRunning=false, runStart=0;
    function setBtns(dis){{document.querySelectorAll('.btn[data-run]').forEach(b=>{{b.disabled=dis;}});}}
    async function run(s){{
      setBtns(true); runStart=0;
      const r=await fetch('/run/'+s,{{method:'POST'}}); const j=await r.json();
      if(j.busy){{alert('A stage is already running — let it finish.');setBtns(false);return;}}
      if(!poller) poller=setInterval(poll,1000); poll();
    }}
    function paint(j){{
      const st=document.getElementById('jobstate'), tm=document.getElementById('jobtimer');
      const pre=document.getElementById('joblog');
      if(j.log&&j.log.length){{pre.textContent=j.log.join('\\n');pre.scrollTop=1e9;}}
      if(j.running){{wasRunning=true;setBtns(true); if(!runStart)runStart=Date.now();
        st.className='jobstate run'; st.innerHTML='<span class="spin"></span> RUNNING · '+j.stage;
        tm.textContent=Math.round((Date.now()-runStart)/1000)+'s'; pre.classList.add('live');
      }}else{{
        pre.classList.remove('live');
        const dur=runStart?(Math.round((Date.now()-runStart)/1000)+'s'):'';
        if(j.rc===0){{st.className='jobstate ok';
          st.innerHTML='✓ Finished '+(j.stage||'')+' &nbsp;<a href="/" style="color:#63c98a;text-decoration:underline">refresh to load new review items ↻</a>';tm.textContent=dur;}}
        else if(j.rc!==null){{st.className='jobstate err';st.textContent='✕ Failed: '+(j.stage||'')+' (exit '+j.rc+') — read the log above';tm.textContent=dur;}}
        else{{st.className='jobstate idle';st.textContent='Idle — nothing running';tm.textContent='';}}
      }}
    }}
    async function poll(){{
      const j=await (await fetch('/run/status')).json(); paint(j);
      if(!j.running && poller){{clearInterval(poller);poller=null;setBtns(false);}}
    }}
    // On load: restore the LAST run's output so it never vanishes; resume polling if running.
    fetch('/run/status').then(r=>r.json()).then(j=>{{paint(j); if(j.running){{poller=setInterval(poll,1000);poll();}}}});
    // Console command line — type a res subcommand and run it.
    (function(){{
      const box=document.getElementById('cmdinput'), btn=document.getElementById('cmdrun');
      async function go(){{
        const v=(box.value||'').trim(); if(!v)return;
        const fd=new FormData(); fd.append('cmd',v);
        const j=await (await fetch('/run-cmd',{{method:'POST',body:fd}})).json();
        if(j.error){{alert(j.error);return;}}
        if(j.busy){{alert('A stage is already running — let it finish.');return;}}
        runStart=0; box.value=''; if(!poller)poller=setInterval(poll,1000); poll();
      }}
      btn.onclick=go; box.addEventListener('keydown',e=>{{if(e.key==='Enter')go();}});
    }})();
    // ── file upload (generic corpus, any N documents) ──
    (function(){{
      const drop=document.getElementById('drop'), inp=document.getElementById('fileinput'),
            msg=document.getElementById('uploadmsg'), ub=document.getElementById('uploadbtn');
      if(!drop) return; let chosen=[];
      drop.onclick=()=>inp.click();
      ['dragover','dragenter'].forEach(e=>drop.addEventListener(e,ev=>{{ev.preventDefault();drop.classList.add('drag');}}));
      ['dragleave','drop'].forEach(e=>drop.addEventListener(e,ev=>{{ev.preventDefault();drop.classList.remove('drag');}}));
      drop.addEventListener('drop',ev=>{{chosen=[...ev.dataTransfer.files];show();}});
      inp.addEventListener('change',()=>{{chosen=[...inp.files];show();}});
      function show(){{if(chosen.length){{msg.textContent=chosen.length+' file(s) selected — press Upload';ub.disabled=false;}}}}
      ub.onclick=async()=>{{ if(!chosen.length)return; ub.disabled=true;
        msg.textContent='Uploading '+chosen.length+' file(s)…';
        const fd=new FormData(); chosen.forEach(f=>fd.append('files',f));
        const r=await fetch('/upload',{{method:'POST',body:fd}}); const j=await r.json();
        msg.textContent='Uploaded '+j.count+(j.skipped.length?(' ('+j.skipped.length+' skipped)'):'')+'. Reloading…';
        setTimeout(()=>location.reload(),900); }};
    }})();
    window.clearInbox=async()=>{{await fetch('/upload/clear',{{method:'POST'}});location.reload();}};
    </script>"""
    return _page("/", body)


def _scorebars() -> str:
    r = _latest_report()
    if not r:
        return '<p class="muted">Run <b>Verify</b> to populate this.</p>'
    s, e, rel = r["screening"], r["entity_coverage"], r["relation_coverage"]
    f = r["citation_faithfulness"]
    items = [("Recovered the 28 studies", s["final_sensitivity_after_hitl"], "good"),
             ("Causal-relation patterns", rel.get("type_recall", 0), "good"),
             ("Claims quote-anchored", f["faithfulness"], "good"),
             ("Richmond concepts recovered", e["recall"], "warn")]
    return "".join(f'<div class="sb"><span>{l}</span><span class="sbbar"><span class="sbfill {c}" '
                   f'style="width:{v*100:.0f}%"></span></span><span class="sbn {c}">{v*100:.0f}%</span></div>'
                   for l, v, c in items)


# ── Inputs ───────────────────────────────────────────────────────────────────
@app.get("/inputs", response_class=HTMLResponse)
def inputs():
    with get_connection() as c:
        rows = c.execute("SELECT study_id,title,year,source_kind FROM studies ORDER BY study_id").fetchall()
    proto = load_yaml_config("protocol")
    tr = "".join(f'<tr><td><code>{r["study_id"]}</code></td><td>{r["title"][:74]}</td><td>{r["year"] or "?"}</td>'
                 f'<td class="muted">{"full text" if r["source_kind"]=="fulltext_pdf" else "abstract"}</td></tr>' for r in rows)
    body = f"""
    <div class="eyebrow">Step 1 · what goes in</div>
    <h2 class="title serif">The inputs</h2>
    <p class="lead">The same two things a human review team starts with: the corpus, and the
    researcher-defined protocol. Nothing about Richmond's conclusions is fed in.</p>
    <div class="panel"><div class="eyebrow">Protocol · <code>config/protocol.yaml</code></div>
      <p style="margin:.2rem 0"><b>Question.</b> {proto['review_question']}</p>
      <p class="muted" style="margin:.4rem 0 0"><b>Population:</b> {proto['eligibility']['population']['include'][:170]}…</p>
      <p class="muted" style="margin:.3rem 0 0"><b>From:</b> {proto['eligibility']['timeframe']['published_from']} onward.</p></div>
    <h3>Corpus — {len(rows)} papers</h3>
    <div class="panel" style="padding:0"><table><thead><tr><th>ID</th><th>Title</th><th>Year</th><th>Source</th></tr></thead><tbody>{tr}</tbody></table></div>"""
    return _page("/inputs", body)


# ── Ontology ─────────────────────────────────────────────────────────────────
@app.get("/ontology", response_class=HTMLResponse)
def ontology():
    onto = load_yaml_config("ontology")
    with get_connection() as c:
        ec = {r["entity_type"]: r["n"] for r in c.execute("SELECT entity_type,count(*) n FROM entity_instances GROUP BY entity_type").fetchall()}
        pc = {r["predicate"]: r["n"] for r in c.execute("SELECT predicate,count(*) n FROM typed_relations WHERE constraint_valid GROUP BY predicate").fetchall()}
    er = "".join(f'<tr><td><code>{k}</code></td><td>{v["definition"][:105]}</td><td class="muted machine">{ec.get(k,0)}</td></tr>' for k, v in onto["entity_types"].items())
    pr = "".join(f'<tr><td><code>{k}</code></td><td>{"/".join(v["domain"])} → {"/".join(v["range"])}</td><td class="muted machine">{pc.get(k,0)}</td></tr>' for k, v in onto["relation_predicates"].items())
    body = f"""
    <div class="eyebrow">Step 2 · the vocabulary</div>
    <h2 class="title serif">How entities &amp; relations are defined</h2>
    <p class="lead">The realist Context–Mechanism–Outcome framework (the RAMESES standard) —
    <b>five entity types, five relation types</b>, machine-enforced. This is the method, not Richmond's answers.</p>
    <div class="two">
      <div class="panel" style="padding:0"><div class="eyebrow" style="padding:.9rem 1rem 0">5 entity types</div>
        <table><thead><tr><th>Type</th><th>Definition</th><th>#</th></tr></thead><tbody>{er}</tbody></table></div>
      <div class="panel" style="padding:0"><div class="eyebrow" style="padding:.9rem 1rem 0">5 relation types</div>
        <table><thead><tr><th>Predicate</th><th>Domain → Range</th><th>#</th></tr></thead><tbody>{pr}</tbody></table></div>
    </div>
    <p class="muted"><code>config/ontology.yaml</code> — validated to cover all 40 of Richmond's relations.</p>
    <h3>Are these faithful to Richmond, and useful? — self-assessment</h3>
    <div class="panel">
      <div class="li e"><b>Faithful.</b> Our five entity types are Richmond's exact CMO framework (§2):
        Context, Intervention, and Mechanism split into <b>resource</b> + <b>response</b> — the split most
        automated systems miss. Not an invented ontology.</div>
      <div class="li e"><b>The relations are ours, grounded in their prose.</b> Richmond names no relation
        types; our five operationalise their causal verbs ("offer resources", "leads to"), and the
        distribution matches their gold (TRIGGERS + LEADS_TO dominate).</div>
      <div class="li e"><b>Low fabrication.</b> 99.4% of extracted relations pass domain/range validation;
        96% of quotes resolve to a real span; unresolved ones are flagged, never invented.</div>
      <div class="li x"><b>Weakness 1 — over-granularity.</b> We hold 148 concepts where Richmond abstracted
        to 47; some are too study-specific. The concept-family layer coarsens 148→30, but the normaliser
        should abstract more.</div>
      <div class="li x"><b>Weakness 2 — Resource/Intervention/Response boundary is fuzzy.</b> e.g.
        "accuracy-speed pressure" is mis-typed as a Resource. Richmond's own gold shows the same tension.
        Fix: a sharper prompt rule + let the Checker re-type, not just flag.</div>
      <p class="muted" style="margin-top:.5rem">Full analysis: <code>docs/ENTITY_RELATIONSHIP_EVALUATION.md</code>.
      Bottom line: the entities/relations are the <i>right kinds</i>, faithfully grounded and usable — what
      remains is tidiness (abstraction + boundary precision), not correctness.</p>
    </div>"""
    return _page("/ontology", body)


# ── Workflow & agents ────────────────────────────────────────────────────────
_RICHMOND_STEPS = [
    ("Seed a theory first", "From a scoping search + expert opinion + learning theory, the team drafts "
     "an <b>initial programme theory</b> (IPT) — a first guess at the mechanisms — and agrees it by consensus."),
    ("Theory-driven search", "They search four databases using themes from the IPT, adding terms as new "
     "concepts emerge. The search grows with the theory."),
    ("Screen for relevance", "A study is kept if it plausibly <b>contributes to theory building</b> — realist "
     "relevance, not topical overlap."),
    ("Code CMOCs (lead + checker)", "AR codes every paper into Context–Mechanism–Outcome configurations; a "
     "second reviewer (RP/SG/NC) independently checks <b>every one of the 28</b> for consistency."),
    ("Compare across studies", "Recurrent CMOC patterns are identified; partial evidence from different "
     "studies is combined into fuller configurations."),
    ("Retroduction loop", "As later papers reshape the theory, <b>earlier studies are re-analysed</b> in its "
     "light — the defining iterative rhythm of realist synthesis."),
    ("Programme theory + consensus", "Five student-context CMOC statements (Figs 2–3); all authors agree the "
     "final output."),
]
_SYSTEM_STEPS = [
    ("Ingest", "Ingestion", "PDF/abstract → clean text; each file gets a Study ID and is split into "
     "provenance-bearing <b>text units</b> with exact character offsets."),
    ("Seed IPT", "IPT Manager", "Drafts the initial programme theory from public learning theory (never "
     "Richmond's answers); you ratify it at <b>HITL-0</b>."),
    ("Screen", "Screening Reviewers (×2)", "Two independent models vote include/exclude on theory-relevance; "
     "disagreements route to you at <b>HITL-1</b>."),
    ("Extract + check", "CMOC Extractor + Consistency Checker", "The extractor pulls typed C→M→O with a "
     "verbatim quote per element; an independent checker (different model family) re-checks every study → "
     "<b>HITL-2</b>."),
    ("Build the graph", "Normaliser + Community Analyst", "Quotes resolve to spans; synonymous concepts "
     "merge; Leiden community detection surfaces emergent <b>conceptual entities</b>."),
    ("Synthesise", "Synthesis Composer", "Recurrent patterns (demi-regularities) + contradictions → a "
     "five-context programme theory; contradictions resolved at <b>HITL-3</b>, theory signed at <b>HITL-4</b>."),
    ("Retroduction", "Retroduction loop", "The weakest studies are re-read under the refined theory until "
     "the configurations stabilise — mirroring Richmond's re-analysis of earlier studies."),
]


@app.get("/workflow", response_class=HTMLResponse)
def workflow():
    from res_pipeline.core.agents import human_checkpoints, roster_summary
    onto = load_yaml_config("agents")
    r_steps = "".join(
        f'<div class="step"><div class="num">{i}</div><div class="st-t">{t}</div>'
        f'<div class="st-d">{d}</div></div>' for i, (t, d) in enumerate(_RICHMOND_STEPS, 1))
    s_steps = "".join(
        f'<div class="step"><div class="num">{i}</div>'
        f'<div class="st-t">{t} &nbsp;<span class="ac-tier">{ag}</span></div>'
        f'<div class="st-d">{d}</div></div>' for i, (t, ag, d) in enumerate(_SYSTEM_STEPS, 1))
    agent_defs = onto["agents"]
    cards = "".join(
        f'<div class="agentcard"><div class="ac-h"><span class="ac-t">{a["title"]}</span>'
        f'<span class="ac-tier">{a["tier"]}</span></div>'
        f'<div class="ac-does">{" ".join(agent_defs[a["id"]]["persona"].split())}</div>'
        f'<div class="ac-mirror"><b>Mirrors in Richmond:</b> {a["richmond_analogue"]}</div></div>'
        for a in roster_summary())
    hitl = "".join(
        f'<div class="hitlrow"><span class="hk">{h["id"]}</span><span>{h["what"]} '
        f'<span class="muted">— {h["richmond_analogue"]}</span></span></div>'
        for h in human_checkpoints())
    body = f"""
    <div class="eyebrow">How it works — the human process and ours, side by side</div>
    <h2 class="title serif">Workflow &amp; the multi-agent system</h2>
    <p class="lead">Our system does not invent a process — it <b>reproduces Richmond's</b>. Left: how five
    human experts made their realist review. Right: how our eight agents perform the same operations, with
    you sovereign at five checkpoints. Full grounding in <code>docs/SYSTEM_WORKFLOW.md</code>.</p>
    <div class="two">
      <div class="panel"><div class="eyebrow human">Richmond's human workflow</div>
        <div class="wf human">{r_steps}</div></div>
      <div class="panel"><div class="eyebrow machine">Our system's workflow</div>
        <div class="wf">{s_steps}</div></div>
    </div>
    <h3>The agents — who does what</h3>
    <p class="muted" style="margin-top:-.3rem">Eight machine agents, each with an embedded expert persona,
    each mirroring a role a Richmond author played. (Also on the command line: <code>res agents</code>.)</p>
    {cards}
    <h3>Human-in-the-loop — where you decide</h3>
    <div class="panel">{hitl}</div>
    <h3>How we know it works</h3>
    <div class="panel">{_scorebars()}
      <p class="muted" style="margin-top:.6rem">Measured against Richmond's published outputs, OUTSIDE the
      pipeline (the answer key is never read by the agents). LLM-judged metrics are sampled 3× and
      reported with a range; deterministic ones (screening, faithfulness, type-validity) are stable.
      See the <a class="tl" href="/verify">Comparison</a> page for the full scorecard.</p></div>"""
    return _page("/workflow", body)


# ── Knowledge graph ──────────────────────────────────────────────────────────
_ETYPE_COLOR = {"Context": "#8a5a12", "Intervention": "#0e6b74",
                "Mechanism_Resource": "#3a6ea5", "Mechanism_Response": "#7b4397",
                "Outcome": "#2c6e49"}

# vis-network graph + node inspector (plain string so JS braces are literal).
_KG_JS = """
(function(){
  if(typeof vis==='undefined'){document.getElementById('kgnet').innerHTML=
    '<p style="padding:1rem" class="muted">Graph library needs internet to load. '+
    'The data is intact — see the relationships below or Neo4j Browser.</p>';return;}
  const nodes=new vis.DataSet(DATA.nodes.map(n=>({id:n.id,label:n.label,group:n.type,
    value:n.members,title:n.type.replace(/_/g,' ')+' · '+n.studies+' studies'})));
  const edges=new vis.DataSet(DATA.links.map((l,i)=>({id:i,from:l.s,to:l.o,label:l.p,
    arrows:'to',value:l.w})));
  const meta={}; DATA.nodes.forEach(n=>meta[n.id]=n);
  const groups={};
  for(const t in COLOR){groups[t]={color:{background:COLOR[t],border:COLOR[t]},
    font:{color:'#fff',size:11}};}
  const net=new vis.Network(document.getElementById('kgnet'),{nodes,edges},{
    groups,
    nodes:{shape:'dot',scaling:{min:6,max:34},font:{size:11,color:'#333'}},
    edges:{color:{color:'#c9c4b8',highlight:'#0e6b74'},width:0.5,
      font:{size:8,align:'middle',color:'#999'},arrows:{to:{scaleFactor:0.4}},
      smooth:{type:'continuous'}},
    physics:{barnesHut:{gravitationalConstant:-9000,springLength:110,springConstant:0.03},
      stabilization:{iterations:250}},
    interaction:{hover:true,tooltipDelay:120}});
  const ph=document.getElementById('kgph'), detail=document.getElementById('kgdetail');
  function esc(s){return (s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
  function show(id){
    const m=meta[id]; if(!m) return;
    const conns=DATA.links.filter(l=>l.s===id||l.o===id).map(l=>{
      if(l.s===id) return '<div>&rarr; <code>'+l.p+'</code> &rarr; '+esc((meta[l.o]||{}).label)+'</div>';
      return '<div>&larr; <code>'+l.p+'</code> &larr; '+esc((meta[l.s]||{}).label)+'</div>';});
    const col=COLOR[m.type]||'#666';
    detail.innerHTML='<span class="pill" style="background:'+col+'22;color:'+col+'">'+
      m.type.replace(/_/g,' ')+'</span>'+
      '<div style="font-family:Georgia,serif;font-size:1.15rem;margin:.4rem 0">'+esc(m.label)+'</div>'+
      '<div class="muted" style="font-size:.82rem">Appears in '+m.studies+' studies · '+
      m.members+' mentions</div>'+(m.quote?('<div class="quote">'+esc(m.quote)+'</div>'):'')+
      '<div class="who m" style="margin-top:.6rem">Connections ('+conns.length+')</div>'+
      '<div style="font-size:.85rem;max-height:230px;overflow:auto">'+
      (conns.join('')||'<span class="muted">none</span>')+'</div>';
    ph.style.display='none'; detail.style.display='block';
    net.selectNodes([id]); net.focus(id,{scale:1.1,animation:true});}
  net.on('click',p=>{if(p.nodes.length) show(p.nodes[0]);});
  const box=document.getElementById('kgsearch');
  box.addEventListener('keydown',e=>{if(e.key!=='Enter')return;
    const q=box.value.toLowerCase().trim(); if(!q)return;
    const hit=DATA.nodes.find(n=>(n.label||'').toLowerCase().includes(q));
    if(hit) show(hit.id);
    else{ph.textContent='No concept matches "'+box.value+'".';ph.style.display='block';
      detail.style.display='none';}});
})();
"""


def _graph_data(level: str = "canonical") -> dict:
    """The REAL knowledge graph (not a sample), at canonical-concept granularity by default.

    Nodes = deduplicated canonical concepts (the real entities the pipeline extracted);
    edges = typed relations aggregated between them, with the predicate and support count.
    Every node carries its type, study support, and a representative evidence quote for the
    Node Inspector. ``level='family'`` gives the coarser Richmond-granularity overview.
    """
    fam = level == "family"
    n_id = "f.family_id" if fam else "e.canonical_id"
    n_join = "JOIN concept_families f ON f.canonical_id = e.canonical_id" if fam else ""
    s_col = "fs.family_id" if fam else "se.canonical_id"
    o_col = "fo.family_id" if fam else "oe.canonical_id"
    e_join = ("JOIN concept_families fs ON fs.canonical_id = se.canonical_id "
              "JOIN concept_families fo ON fo.canonical_id = oe.canonical_id") if fam else ""
    with get_connection() as c:
        nodes_rows = c.execute(
            f"""
            SELECT {n_id} AS id, e.entity_type AS type,
                   mode() WITHIN GROUP (ORDER BY e.label) AS label,
                   count(DISTINCT e.study_id) AS studies, count(*) AS members,
                   (array_agg(e.verbatim_quote ORDER BY e.confidence DESC NULLS LAST))[1] AS quote
            FROM entity_instances e {n_join}
            WHERE {n_id} IS NOT NULL
            GROUP BY {n_id}, e.entity_type
            """
        ).fetchall()
        edges = c.execute(
            f"""
            SELECT {s_col} AS s, {o_col} AS o, tr.predicate AS p, count(*) AS w
            FROM typed_relations tr
            JOIN entity_instances se ON se.entity_id = tr.subject_entity_id
            JOIN entity_instances oe ON oe.entity_id = tr.object_entity_id
            {e_join}
            WHERE tr.constraint_valid AND {s_col} IS NOT NULL AND {o_col} IS NOT NULL
              AND {s_col} <> {o_col}
            GROUP BY {s_col}, {o_col}, tr.predicate
            """
        ).fetchall()
    nodes = [{"id": r["id"], "label": (r["label"] or r["id"])[:40], "type": r["type"],
              "studies": r["studies"], "members": r["members"],
              "quote": (r["quote"] or "")[:220]} for r in nodes_rows]
    keep = {n["id"] for n in nodes}
    links = [{"s": e["s"], "o": e["o"], "p": e["p"], "w": e["w"]}
             for e in edges if e["s"] in keep and e["o"] in keep]
    return {"nodes": nodes, "links": links}


@app.get("/graph", response_class=HTMLResponse)
def graph(level: str = "canonical"):
    data = _graph_data(level)
    onto = load_yaml_config("ontology")
    with get_connection() as c:
        comms = c.execute(
            "SELECT community_label, definition, entity_type, member_count, "
            "array_length(study_ids,1) studies, algorithm FROM conceptual_entities "
            "ORDER BY member_count DESC"
        ).fetchall()
        n_rel = c.execute("SELECT count(*) n FROM typed_relations WHERE constraint_valid").fetchone()["n"]
    legend = "".join(
        f'<span class="pill" style="background:{c}22;color:{c};border:1px solid {c}55">'
        f'{t.replace("_"," ")}</span> ' for t, c in _ETYPE_COLOR.items())
    algo = comms[0]["algorithm"] if comms else "—"
    comm_cards = "".join(
        f'<div class="revcard"><div class="revtop"><b>{_esc(r["community_label"])}</b>'
        f'<span class="pill" style="background:{_ETYPE_COLOR.get(r["entity_type"],"#666")}22;'
        f'color:{_ETYPE_COLOR.get(r["entity_type"],"#666")}">{r["entity_type"].replace("_"," ")}</span></div>'
        f'<div style="padding:.6rem .9rem"><div class="muted">{_esc(r["definition"])}</div>'
        f'<div class="muted" style="font-size:.8rem;margin-top:.3rem">{r["member_count"]} member '
        f'concepts · {r["studies"] or 0} studies</div></div></div>' for r in comms)
    other = "family" if level == "canonical" else "canonical"
    grain = "concept" if level == "canonical" else "Richmond-family"
    data_js = (f"const DATA={json.dumps(data)};const COLOR={json.dumps(_ETYPE_COLOR)};")
    body = f"""
    <div class="eyebrow">The Literature Knowledge Graph — real, quote-anchored</div>
    <h2 class="title serif">Knowledge graph — entities &amp; relationships</h2>
    <p class="lead">The <b>whole</b> extracted graph (not a sample): {len(data['nodes'])} {grain}-level
    entities and {len(data['links'])} typed relations, every one anchored to a verbatim quote.
    Click any node to inspect its type, evidence, and connections. Colours are the five realist
    entity types; arrows are the five directed relations.
    <a class="tl" href="/graph?level={other}">Switch to {other} granularity →</a></p>
    <div class="panel"><div class="eyebrow">Entity types (nodes)</div>{legend}</div>
    <div style="display:flex;gap:1rem;flex-wrap:wrap;margin:.9rem 0">
      <div id="kgnet" style="flex:3;min-width:420px;height:600px;border:1px solid var(--line);
        border-radius:4px;background:var(--paper)"></div>
      <div class="panel" id="inspector" style="flex:1;min-width:260px;height:600px;overflow:auto;margin:0">
        <div class="eyebrow">Node inspector</div>
        <input id="kgsearch" placeholder="Search a concept…" style="width:100%;margin-bottom:.6rem">
        <div id="kgph" class="muted">Click a node in the graph to inspect it — its type, the
        evidence quote behind it, and every relationship it participates in.</div>
        <div id="kgdetail" style="display:none"></div>
      </div>
    </div>
    <p class="muted">Full interactive graph also in Neo4j Browser; canonical parquet in
    <code>outputs/lkg/</code>. {n_rel} relations passed domain/range validation.</p>
    <h3>Emergent conceptual entities <span class="muted" style="font-size:.8rem">({algo})</span></h3>
    <div class="two">{comm_cards or '<p class="muted">Run synthesis to detect communities.</p>'}</div>
    <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <script>{data_js}</script>
    <script>{_KG_JS}</script>"""
    return _page("/graph", body)


# ── Human review ─────────────────────────────────────────────────────────────
@app.get("/review", response_class=HTMLResponse)
def review():
    pend = _pending_reviews()
    with get_connection() as c:
        th = c.execute("SELECT version,signed_off_by FROM programme_theories ORDER BY version DESC LIMIT 1").fetchone()
    tsign = (f'<div class="panel" style="border-left:3px solid var(--good)"><b class="done">Programme theory v{th["version"]} '
             f'signed off by {_esc(th["signed_off_by"])}.</b></div>'
             if th and th["signed_off_by"] else
             f'<div class="revcard"><div class="revtop"><b>Programme theory v{th["version"] if th else "—"}</b>'
             f'<span class="tag part">awaits sign-off</span></div>'
             f'<div class="revwhat"><div class="who m">What the machine built</div>'
             f'<div class="muted">The full theory is on the <a class="tl" href="/results">Machine result</a> page. '
             f'Read it there, then sign here to accept it as the review\'s programme theory.</div></div>'
             f'<div class="revask"><div class="who h">Your sign-off</div>'
             f'<form class="f" method="post" action="/review/sign"><input type="hidden" name="version" value="{th["version"] if th else 0}">'
             f'<input name="reviewer" placeholder="Your name" required style="max-width:140px">'
             f'<button class="btn human sm" type="submit">Sign off the theory</button></form></div></div>')
    body = f"""
    <div class="eyebrow">Step 3 · human master-control</div>
    <h2 class="title serif">Your review</h2>
    <p class="lead">The machine only stops for you when it is genuinely unsure. For each item below you
    see <span class="who m" style="display:inline">what the machine produced</span> first, then
    <span class="who h" style="display:inline">the decision it needs from you</span>. Everything is saved
    with your name in the audit trail.</p>
    <h3>Checkpoints 1 &amp; 3 — Screening and contradictions</h3>
    {_review_block(pend)}
    <h3>Checkpoint 4 — Programme theory sign-off</h3>{tsign}"""
    return _page("/review", body)


@app.post("/review/screen")
def r_screen(sid: str = Form(), reviewer: str = Form(), reason: str = Form(), decision: str = Form()):
    rid = f"webui-{uuid.uuid4().hex[:6]}"
    with get_connection() as c:
        c.execute("INSERT INTO screening_decisions (study_id,stage,decider,decision,rationale,confidence,run_id) "
                  "VALUES (%s,'title_abstract',%s,%s,%s,NULL,%s)", (sid, f"human:{reviewer}", decision, reason, rid))
        c.execute("INSERT INTO hitl_feedback (checkpoint,subject_ref,action,feedback,payload,run_id) "
                  "VALUES ('HITL-1',%s,'edit',%s,%s,%s)", (sid, reason, '{"decision":"%s"}' % decision, rid))
    log_audit_event(rid, f"human:{reviewer}", "webui_hitl1", subject_ref=sid, detail={"decision": decision})
    return RedirectResponse("/review", 303)


@app.post("/review/conflict")
def r_conflict(cid: int = Form(), reviewer: str = Form(), resolution: str = Form()):
    rid = f"webui-{uuid.uuid4().hex[:6]}"
    with get_connection() as c:
        c.execute("UPDATE contradictions SET resolution=%s,resolved_by=%s WHERE id=%s", (resolution, f"human:{reviewer}", cid))
        c.execute("INSERT INTO hitl_feedback (checkpoint,subject_ref,action,feedback,payload,run_id) "
                  "VALUES ('HITL-3',%s,'edit',%s,'{}',%s)", (f"contradiction-{cid}", resolution, rid))
    log_audit_event(rid, f"human:{reviewer}", "webui_hitl3", subject_ref=f"contradiction-{cid}")
    return RedirectResponse("/review", 303)


@app.post("/review/sign")
def r_sign(version: int = Form(), reviewer: str = Form()):
    rid = f"webui-{uuid.uuid4().hex[:6]}"
    with get_connection() as c:
        c.execute("UPDATE programme_theories SET signed_off_by=%s WHERE version=%s", (f"human:{reviewer}", version))
        c.execute("INSERT INTO hitl_feedback (checkpoint,subject_ref,action,feedback,payload,run_id) "
                  "VALUES ('HITL-4',%s,'approve',%s,'{}',%s)", (f"theory-v{version}", f"signed {reviewer}", rid))
    log_audit_event(rid, f"human:{reviewer}", "webui_hitl4", subject_ref=f"theory-v{version}")
    return RedirectResponse("/review", 303)


# ── Machine result ───────────────────────────────────────────────────────────
@app.get("/results", response_class=HTMLResponse)
def results():
    with get_connection() as c:
        th = c.execute("SELECT version,theory_json,signed_off_by FROM programme_theories ORDER BY version DESC LIMIT 1").fetchone()
        if not th:
            return _page("/results", '<h2 class="title serif">The machine\'s result</h2>'
                         '<p class="lead">Run <b>Synthesise</b> from the Control room first.</p>')
        tj = th["theory_json"] if isinstance(th["theory_json"], dict) else json.loads(th["theory_json"])
        # for each theory section, pull the machine's own Works / Backfires evidence by polarity
        blocks = ""
        for i, s in enumerate(tj["sections"], 1):
            sids = s.get("supporting_study_ids") or []
            works, backfires = [], []
            if sids:
                rows = c.execute(
                    "SELECT DISTINCT ON (study_id) study_id,polarity,narrative_statement FROM cmocs "
                    "WHERE study_id = ANY(%s) ORDER BY study_id, verifier_support DESC", (sids,)).fetchall()
                for r in rows:
                    (works if r["polarity"] == "positive" else backfires if r["polarity"] == "negative" else works).append(r)
            wl = "".join(f'<div class="li e">{_esc(r["narrative_statement"][:160])} '
                         f'<span class="muted">({_esc(r["study_id"])})</span></div>' for r in works[:4]) \
                 or '<div class="muted">—</div>'
            bl = "".join(f'<div class="li x">{_esc(r["narrative_statement"][:160])} '
                         f'<span class="muted">({_esc(r["study_id"])})</span></div>' for r in backfires[:4]) \
                 or '<div class="muted">— none found</div>'
            blocks += (
                f'<div class="cmp"><div class="ch"><span>Context {i} · {_esc(s["context_label"])}</span>'
                f'<span class="tag match">machine</span></div>'
                f'<div class="col" style="border-bottom:1px solid var(--line)">'
                f'<div class="quote" style="margin:0">{_esc(s["cmoc_statement"])}</div>'
                f'<div class="muted" style="margin-top:.4rem;font-size:.82rem">Built from {len(sids)} studies: {_esc(", ".join(sids))}</div></div>'
                f'<div class="cc"><div class="col"><div class="who m">✓ What works</div>{wl}</div>'
                f'<div class="col"><div class="who m">✕ What backfires</div>{bl}</div></div></div>')
    sign = (f'<span class="done">✓ signed off by {_esc(th["signed_off_by"])}</span>' if th["signed_off_by"]
            else '<span class="warn">awaiting your sign-off on the Review page</span>')
    body = f"""
    <div class="eyebrow">Step 4 · what the machine produced</div>
    <h2 class="title serif">The machine's result</h2>
    <p class="lead">The programme theory the system built from the 28 papers — its answer to "which
    teaching works, for whom, in what circumstances." It is laid out in the <b>same shape as the
    <a class="tl" href="/standard">Human standard</a></b>: one block per student context, each split into
    what <span class="who m" style="display:inline">works</span> and what backfires — so you can read the two pages
    side by side. Every claim is quote-anchored (see <code>cmoc_evidence_table.md</code>).</p>
    <p class="muted">Programme theory v{th["version"]} · {sign}</p>
    <div class="panel"><div class="eyebrow">The machine's headline</div><p style="margin:.2rem 0">{_esc(tj["overview"])}</p></div>
    {blocks}
    <p class="muted" style="margin-top:1rem"><b>Boundary of the theory:</b> {_esc(tj.get("boundary_statement",""))}</p>
    <p class="muted">Full graph explorable in Neo4j Browser; canonical parquet in <code>outputs/lkg/</code>.
    Compare block-for-block against the <a class="tl" href="/standard">Human standard</a> or see the scored
    <a class="tl" href="/verify">Comparison</a>.</p>"""
    return _page("/results", body)


# ── Human standard ───────────────────────────────────────────────────────────
def _bold(s: str) -> str:
    parts = s.split("**")
    return "".join(p if i % 2 == 0 else f"<b>{p}</b>" for i, p in enumerate(parts))


@app.get("/standard", response_class=HTMLResponse)
def standard():
    import re
    md = GOLD_DIR / "RICHMOND_CONCLUSIONS.md"
    text = md.read_text(encoding="utf-8") if md.exists() else "Not written yet."
    out = []
    for line in text.splitlines():
        s = line.rstrip()
        if s == "---":
            out.append('<hr class="rule">')
        elif s.startswith("### "):
            out.append(f"<h3>{_bold(s[4:])}</h3>")
        elif s.startswith("## "):
            out.append(f'<h3 class="serif" style="font-size:1.28rem;color:var(--human)">{_bold(s[3:])}</h3>')
        elif s.startswith("# ") or s.startswith("_"):
            continue
        elif re.match(r"^\d+\.\s", s):
            out.append(f'<div class="li" style="padding-left:1.5rem">'
                       f'<span style="position:absolute;left:0;color:var(--human);font-weight:700">'
                       f'{s.split(".")[0]}.</span>{_bold(s.split(". ", 1)[1])}</div>')
        elif s.startswith("- "):
            b = s[2:].lstrip()
            cls = "e" if b.startswith("✓") else ("x" if b.startswith("✕") else "")
            out.append(f'<div class="li {cls}">{_bold(b.lstrip("✓✕ "))}</div>')
        elif s:
            out.append(f"<p>{_bold(s)}</p>")
    body = f"""
    <div class="eyebrow">Step 5 · the human benchmark</div>
    <h2 class="title serif">What Richmond's team did, and concluded</h2>
    <p class="lead">The standard the machine is measured against — laid out carefully in two parts:
    <b>how</b> Richmond's team ran their realist review (their method, grounded in the paper), and
    <b>what</b> they concluded (the five student contexts). The machine result mirrors the same
    structure so the two can be read block-for-block. Source file: <code>gold/RICHMOND_CONCLUSIONS.md</code>.</p>
    <div class="panel" style="border-left:3px solid var(--human)">{''.join(out)}</div>
    <p class="muted">This is the RA's working interpretation to finalise against the original paper —
    the definitive human reading is yours to own. Next: see the <a class="tl" href="/results">machine's
    result</a> in the same shape, or the scored <a class="tl" href="/verify">comparison</a>.</p>"""
    return _page("/standard", body)


# ── Comparison ───────────────────────────────────────────────────────────────
@app.get("/verify", response_class=HTMLResponse)
def verify():
    r = _latest_report()
    if not r:
        return _page("/verify", '<h2 class="title serif">Comparison</h2><p class="lead">Run <b>Verify</b> from the Control room first.</p>')
    groups = [
        ("Low-knowledge novices", "match",
         [("e", "Explain the expert's reasoning; teach pattern + checking together"), ("x", "Observing without explanation → panic, poor learning")],
         [("e", "Explicit reasoning instruction &amp; schemas help novices"), ("x", "Unsupported / passive formats ineffective")]),
        ("High-knowledge learners", "match",
         [("e", "Real / simulated cases → fast intuitive reasoning"), ("x", "Novice-style directive teaching → little benefit (expertise reversal)")],
         [("e", "Structured comparison helps competent learners"), ("x", "Over-directive support adds little — <b>same expertise-reversal, found independently</b>")]),
        ("Mixed groups (feedback)", "part",
         [("e", "Timely accurate feedback → learning"), ("x", "Absent / wrong feedback → confusion")],
         [("e", "Feedback-and-correction is a positive pattern across studies")]),
        ("Coping / self-confidence", "gap",
         [("e", "Good copers gain from simulation"), ("x", "Poor copers → fear / stress → negative learning")],
         [("n", "Not reconstructed — \"self-efficacy\" appears 0× in the corpus. The system declined to invent it.")]),
    ]
    cmp_html = ""
    tagname = {"match": "match", "part": "partial", "gap": "corpus gap"}
    for name, verdict, hu, ma in groups:
        hl = "".join(f'<div class="li {c}">{t}</div>' for c, t in hu)
        ml = "".join((f'<div class="li {c}">{t}</div>' if c in ("e", "x") else f'<div class="muted">{t}</div>') for c, t in ma)
        cmp_html += (f'<div class="cmp"><div class="ch"><span>{name}</span><span class="tag {verdict}">{tagname[verdict]}</span></div>'
                     f'<div class="cc"><div class="col"><div class="who h">Richmond · human</div>{hl}</div>'
                     f'<div class="col"><div class="who m">System · machine</div>{ml}</div></div></div>')
    integrity = """
    <div class="panel"><div class="eyebrow">Did the machine copy Richmond's answers?</div>
      <div class="li e"><b>Code:</b> the pipeline reads only the 28 papers; Richmond's answer key is used only to score, afterwards. The extraction prompt contains 0 of Richmond's codes.</div>
      <div class="li e"><b>Evidence:</b> a copier would know all of Richmond's contexts, yet the system missed exactly the concepts absent from the corpus (self-efficacy 0×) and used its own emergent groups — it reasoned from the source.</div>
      <div class="li x"><b>Caveat:</b> the model may carry pre-training memory of the published paper; the 98% quote-grounding constrains it, and the definitive control (a review outside training data) is future work.</div></div>"""
    body = f"""
    <div class="eyebrow">Step 6 · human vs machine</div>
    <h2 class="title serif">The comparison</h2>
    <p class="lead">How closely the machine's output matches the human review — the scorecard, then
    conclusions side by side, then the integrity check. Full numbers in <code>outputs/MASTER_VERIFICATION_REPORT.md</code>.</p>
    <div class="panel"><div class="eyebrow">Scorecard</div>{_scorebars()}</div>
    <h3>Conclusions, side by side</h3>{cmp_html}
    <h3>Integrity</h3>{integrity}"""
    return _page("/verify", body)


# ── Raw data: the database with nothing written about it ─────────────────────
#
# Every other page on this site makes a choice about what to show. This one does not.
# It lists every table, and prints every row exactly as stored. It exists because the RA
# asked (2026-11-04) to see what the system actually holds rather than a summary of it,
# and because any claim made in the documents should be checkable against the rows that
# produced it. No ranking, no filtering beyond the search box, no commentary.
@app.get("/raw", response_class=HTMLResponse)
def raw(table: str = "", q: str = "", limit: int = 50, offset: int = 0):
    limit = max(1, min(limit, 500))
    with get_connection() as c:
        tables = [r["table_name"] for r in c.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema='public' AND table_type='BASE TABLE' "
            "ORDER BY table_name").fetchall()]
        counts = {}
        for t in tables:
            counts[t] = c.execute(f'SELECT count(*) n FROM "{t}"').fetchone()["n"]

        chips = "".join(
            f'<a href="/raw?table={t}" class="rawchip{" on" if t == table else ""}">'
            f'{_esc(t)} <span class="muted">{counts[t]}</span></a>' for t in tables)

        body = (
            '<div class="eyebrow">Raw data &middot; the database, unedited</div>'
            '<h1>Every row the system actually holds</h1>'
            '<p class="muted" style="max-width:62rem">Every other page here decides what is '
            'worth showing you. This one does not. These are the tables as the pipeline left '
            'them &mdash; the same rows every figure in the reports was computed from, including '
            'the empty ones. <b>Nothing on this page is summarised, ranked or written about.</b> '
            f'Download the whole thing with <code>python scripts/export_raw.py</code> '
            f'(JSON + CSV per table).</p>'
            f'<div class="rawchips">{chips}</div>')

        if not table:
            body += ('<div class="panel" style="margin-top:1rem"><span class="muted">'
                     'Pick a table above. <b>hitl_feedback</b> and <b>token_usage</b> are empty '
                     'and that is a real finding, not a loading error &mdash; the snapshot restore '
                     'could not carry them (see WALKTHROUGH M39 &sect;4).</span></div>')
            return _page("/raw", body)

        if table not in tables:
            return _page("/raw", body + '<div class="panel">No such table.</div>')

        cols = [r["column_name"] for r in c.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name=%s ORDER BY ordinal_position", (table,)).fetchall()]

        if q:
            where = " OR ".join(f'CAST("{col}" AS TEXT) ILIKE %s' for col in cols)
            params = tuple([f"%{q}%"] * len(cols))
            total = c.execute(f'SELECT count(*) n FROM "{table}" WHERE {where}',
                              params).fetchone()["n"]
            rows = c.execute(f'SELECT * FROM "{table}" WHERE {where} '
                             f'LIMIT {limit} OFFSET {offset}', params).fetchall()
        else:
            total = counts[table]
            rows = c.execute(f'SELECT * FROM "{table}" LIMIT {limit} OFFSET {offset}').fetchall()

    head = "".join(f"<th>{_esc(col)}</th>" for col in cols)
    trs = ""
    for r in rows:
        tds = ""
        for col in cols:
            v = dict(r).get(col)
            txt = "" if v is None else str(v)
            cell = _esc(txt if len(txt) <= 400 else txt[:400] + "…")
            tds += (f'<td title="{_esc(txt[:1500])}">'
                    f'{cell if txt else "<span class=muted>NULL</span>"}</td>')
        trs += f"<tr>{tds}</tr>"
    if not rows:
        trs = f'<tr><td colspan="{len(cols)}" class="muted">No rows.</td></tr>'

    shown_to = min(offset + limit, total)
    pager = ""
    if offset > 0:
        pager += (f'<a class="btn ghost sm" href="/raw?table={table}&q={q}'
                  f'&limit={limit}&offset={max(0, offset - limit)}">&larr; previous</a> ')
    if shown_to < total:
        pager += (f'<a class="btn ghost sm" href="/raw?table={table}&q={q}'
                  f'&limit={limit}&offset={offset + limit}">next &rarr;</a>')

    clear_link = (f' <a class="btn ghost sm" href="/raw?table={table}">clear</a>') if q else ""
    body += (
        f'<div class="panel" style="margin-top:1rem">'
        f'<form method="get" action="/raw" class="f" style="margin-bottom:.6rem">'
        f'<input type="hidden" name="table" value="{_esc(table)}">'
        f'<input name="q" value="{_esc(q)}" placeholder="search every column of {_esc(table)}" '
        f'style="min-width:280px"><button class="btn ghost sm" type="submit">Search</button>'
        f'{clear_link}'
        f'</form>'
        f'<div class="muted" style="font-size:.84rem;margin-bottom:.4rem">'
        f'<b>{_esc(table)}</b> &mdash; showing rows {offset + 1 if rows else 0}&ndash;{shown_to} '
        f'of {total}{" matching" if q else ""} &middot; {len(cols)} columns &middot; '
        f'hover a cell to see the full value</div>'
        f'<div class="rawscroll"><table class="rawtable"><thead><tr>{head}</tr></thead>'
        f'<tbody>{trs}</tbody></table></div>'
        f'<div style="margin-top:.6rem">{pager}</div></div>')
    return _page("/raw", body)
