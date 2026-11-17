#!/usr/bin/env python3
"""Describe what the candidate pool is about, using no model and spending nothing.

WHY THIS EXISTS
---------------
After the search of 2026-11-16 the project had 1,863 records and nothing to say about
the professor's actual question. Screening and extraction are what turn records into
evidence, and both call a model, and the project has no API budget. So the honest options
were to report "we have 1,863 records" and stop, or to find out what can be established
from the records themselves at zero cost. This is the second option.

It applies `<CONFIG_DIR>/coding_frame.yaml` — a theory-grounded dictionary whose
categories come from Gross's process model as integrated by ERAS (Harley, Pekrun, Taxer &
Gross 2019), Pekrun's control-value taxonomy of achievement emotions (2006), and the
intervention and context lists the assignment names — to the title and abstract of every
record, and reports what the literature concentrates on and what it leaves alone.

WHAT THIS IS NOT, AND THE REPORT SAYS SO IN ITS FIRST PARAGRAPH
---------------------------------------------------------------
A term match means a record MENTIONS something. It does not mean the study tested it,
found it effective, or explained why. **Nothing here is a CMOC, and no number here is
evidence of effectiveness.** A descriptive evidence map answers "what is this literature
made of and where are its holes", which is a legitimate and standard scoping output, and
it is the question that can be answered for free. The causal questions — for whom, why,
in what circumstances — need screening and extraction.

TWO SELF-CRITICISMS IT PRINTS ABOUT ITSELF
------------------------------------------
1. **Frame coverage.** The share of records matching no term in a category is reported per
   category. A frame that tags everything is measuring nothing; a frame that tags almost
   nothing is the wrong frame. The reader needs both numbers to judge the rest.
2. **Term promiscuity.** For every category the three highest-hitting individual terms are
   printed with their share. A category carried by one loose word — `feedback`, say, which
   appears in methods sections for reasons unrelated to emotion — is an artifact of the
   dictionary, not a feature of the literature, and the reader is shown which categories
   are in that position instead of having to guess.

USAGE
-----
    export RES_CONFIG_DIR=config-emotion RES_DATA_DIR=data-emotion \\
           RES_OUTPUTS_DIR=outputs-emotion POSTGRES_DB=realist_emotion
    python scripts/evidence_map.py
"""

from __future__ import annotations

import collections
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

# Category blocks in the coding frame, in the order a realist review reads them.
BLOCKS = [
    ("interventions", "Interventions", "What the literature intervenes with"),
    ("mechanism_families", "Mechanism families", "The candidate answers to *why*"),
    ("achievement_emotions", "Achievement emotions", "Pekrun's taxonomy, as outcomes and as targets"),
    ("other_outcomes", "Other outcomes", "The non-emotional outcomes the assignment lists"),
    ("context_dimensions", "Context dimensions", "The four the assignment names, verbatim"),
    ("disciplines", "Disciplines", "Whether the STEM focus is actually served"),
    ("settings", "Settings", "Higher education against school-age"),
    ("study_designs", "Study designs", "How much of the pool could carry mechanism evidence"),
]


def _compile(terms: list[str]) -> list[tuple[str, re.Pattern]]:
    """Word-boundary, case-insensitive matchers.

    A trailing fragment like ``metacognit`` is deliberate — it catches *metacognition*,
    *metacognitive* and *metacognitively* — so the right boundary is only applied when the
    term ends in a word character AND looks like a whole word. Prefixes stay open-ended.
    """
    out = []
    for t in terms:
        esc = re.escape(t.strip().lower()).replace(r"\ ", r"[\s\-]+")
        out.append((t, re.compile(rf"\b{esc}", re.IGNORECASE)))
    return out


def _load_pool(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def _pct(n: int, d: int) -> str:
    return f"{100 * n / d:.0f}%" if d else "–"


def main() -> int:
    import yaml

    from res_pipeline.core.config import CONFIG_DIR, DATA_DIR, OUTPUTS_DIR

    frame_path = CONFIG_DIR / "coding_frame.yaml"
    if not frame_path.exists():
        print(f"No coding frame at {frame_path}. It is a research decision and belongs in "
              f"the protocol directory, so this script will not invent one.", file=sys.stderr)
        return 1
    frame = yaml.safe_load(frame_path.read_text(encoding="utf-8"))

    pool = _load_pool(DATA_DIR / "studies_metadata.jsonl")
    if not pool:
        print(f"No pool at {DATA_DIR / 'studies_metadata.jsonl'}.", file=sys.stderr)
        return 1
    theory = _load_pool(DATA_DIR / "theory_pool.jsonl")

    # --- tag every record -------------------------------------------------------
    matchers = {
        block: {key: (spec.get("label", key), _compile(spec.get("terms") or []), spec)
                for key, spec in (frame.get(block) or {}).items()}
        for block, _, _ in BLOCKS
    }

    tags: list[dict[str, set[str]]] = []
    term_hits: dict[str, collections.Counter] = {b: collections.Counter() for b, _, _ in BLOCKS}
    for rec in pool:
        text = f"{rec.get('title') or ''} \n {rec.get('abstract') or ''}"
        row: dict[str, set[str]] = {}
        for block, cats in matchers.items():
            hit = set()
            for key, (_label, pats, _spec) in cats.items():
                for term, pat in pats:
                    if pat.search(text):
                        hit.add(key)
                        term_hits[block][f"{key}|{term}"] += 1
            row[block] = hit
        tags.append(row)

    n = len(pool)
    with_abstract = sum(1 for r in pool if r.get("abstract"))

    L: list[str] = []
    w = L.append
    w("# Descriptive evidence map — emotional awareness and regulation in learning")
    w("")
    w(f"Generated {datetime.now(timezone.utc):%Y-%m-%d %H:%M UTC} by `scripts/evidence_map.py` "
      f"from `{(DATA_DIR / 'studies_metadata.jsonl').name}` and "
      f"`{frame_path.parent.name}/{frame_path.name}` (frame version "
      f"{frame.get('version')}). No model was called; this cost nothing.")
    w("")
    w("## Read this first")
    w("")
    w(f"**This map says what {n} records TALK ABOUT. It does not say what works.** Every figure "
      "below is a count of records whose title or abstract contains a term from a "
      "theory-grounded dictionary. A record counted under *reappraisal prompts* mentions "
      "reappraisal; it may have found the intervention useless, may be a protocol, may be a "
      "critique. **Nothing here is a Context–Mechanism–Outcome Configuration**, and no number "
      "here is evidence of effectiveness. Those require screening and extraction, which call a "
      "model and are the stages this project currently has no budget for.")
    w("")
    w("What a map like this is for: seeing what a literature is made of, and where its holes "
      "are, before paying to read it. The holes are the more useful half — they are where a "
      "realist review has something to contribute rather than something to summarise.")
    w("")
    w(f"Coverage caveat: **{with_abstract} of {n} records ({_pct(with_abstract, n)}) have an "
      "abstract.** The rest are matched on title alone and are therefore under-tagged "
      "throughout. Every percentage below is of all "
      f"{n} records, not of the {with_abstract} with abstracts, so each is a floor.")
    w("")

    # --- the blocks -------------------------------------------------------------
    for block, heading, blurb in BLOCKS:
        cats = matchers[block]
        w(f"## {heading}")
        w("")
        w(f"*{blurb}.*")
        w("")
        counts = {key: sum(1 for t in tags if key in t[block]) for key in cats}
        tagged_any = sum(1 for t in tags if t[block])
        w(f"**{tagged_any} of {n} records ({_pct(tagged_any, n)}) carry at least one "
          f"{heading.lower().rstrip('s')} tag**; "
          f"{n - tagged_any} carry none.")
        w("")
        w("| Category | Records | Share | Carried mostly by |")
        w("|---|---|---|---|")
        for key, c in sorted(counts.items(), key=lambda kv: -kv[1]):
            label, _pats, spec = cats[key]
            star = " ★" if spec.get("named_by_professor") else ""
            top = [(t.split("|", 1)[1], h) for t, h in term_hits[block].most_common()
                   if t.split("|", 1)[0] == key][:3]
            carried = ", ".join(f"`{t}` {h}" for t, h in top) or "—"
            w(f"| {label}{star} | {c} | {_pct(c, n)} | {carried} |")
        w("")
        if any(spec.get("named_by_professor") for _l, _p, spec in cats.values()):
            w("★ = named by example in the assignment of 2026-10-30.")
            w("")

    # --- the cross-tabulations that matter --------------------------------------
    def crosstab(block_a: str, block_b: str, title: str, note: str) -> None:
        w(f"## {title}")
        w("")
        w(note)
        w("")
        cats_a, cats_b = matchers[block_a], matchers[block_b]
        order_a = sorted(cats_a, key=lambda k: -sum(1 for t in tags if k in t[block_a]))
        order_b = sorted(cats_b, key=lambda k: -sum(1 for t in tags if k in t[block_b]))
        w("| | " + " | ".join(cats_b[k][0].split("(")[0].strip() for k in order_b) + " |")
        w("|---" * (len(order_b) + 1) + "|")
        empty: list[str] = []
        for ka in order_a:
            cells = []
            for kb in order_b:
                c = sum(1 for t in tags if ka in t[block_a] and kb in t[block_b])
                cells.append(str(c) if c else "**·**")
                if c == 0:
                    empty.append(f"{cats_a[ka][0]} × {cats_b[kb][0]}")
            w(f"| **{cats_a[ka][0]}** | " + " | ".join(cells) + " |")
        w("")
        w(f"**·** marks a pair no record in the pool mentions together: **{len(empty)} of "
          f"{len(order_a) * len(order_b)} cells are empty.** An empty cell is a gap in what "
          "this literature *discusses*, which is where a review can say something new — but "
          "it may equally be a gap in the dictionary, and only reading the papers separates "
          "the two.")
        w("")
        if empty:
            w("<details><summary>The empty pairs</summary>")
            w("")
            for e in empty[:60]:
                w(f"- {e}")
            if len(empty) > 60:
                w(f"- …and {len(empty) - 60} more")
            w("")
            w("</details>")
            w("")

    crosstab("interventions", "achievement_emotions",
             "Which interventions are studied against which emotions",
             "The review question joins an educational practice to a specific emotion. This is "
             "the table that shows whether the literature has done that, or whether it has "
             "studied practices and emotions separately.")

    crosstab("interventions", "mechanism_families",
             "Which interventions are discussed alongside which mechanism family",
             "A realist review's unit is the mechanism, not the intervention. Gross's five "
             "families plus control-value theory's two appraisal pathways are the candidate "
             "mechanisms; this is where each intervention's proposed *why* would live.")

    # --- settings × disciplines, as a readable list ----------------------------
    w("## Is the STEM focus actually served?")
    w("")
    w("The assignment asks for higher education, *particularly STEM*. That is a claim this "
      "pool can be checked against rather than assumed.")
    w("")
    he = {i for i, t in enumerate(tags) if "higher_education" in t["settings"]}
    sa = {i for i, t in enumerate(tags) if "school_age" in t["settings"]}
    w(f"- Higher education: **{len(he)}** records ({_pct(len(he), n)})")
    w(f"- School-age: **{len(sa)}** records ({_pct(len(sa), n)})")
    w(f"- Both mentioned: **{len(he & sa)}**; neither: **{n - len(he | sa)}**")
    w("")
    w("| Discipline | In higher-education records | Share of higher-education records |")
    w("|---|---|---|")
    for key in sorted(matchers["disciplines"],
                      key=lambda k: -len({i for i, t in enumerate(tags) if k in t["disciplines"]} & he)):
        label = matchers["disciplines"][key][0]
        c = len({i for i, t in enumerate(tags) if key in t["disciplines"]} & he)
        w(f"| {label} | {c} | {_pct(c, len(he))} |")
    w("")

    # --- the pool's capacity to answer the question at all ---------------------
    w("## How much of the pool could carry mechanism evidence")
    w("")
    w("A realist review needs studies that explain, not studies that correlate. This is the "
      "pool's ceiling, before a single eligibility decision.")
    w("")
    designs = matchers["study_designs"]
    exp = {i for i, t in enumerate(tags)
           if t["study_designs"] & {"rct", "quasi_experiment"}}
    qual = {i for i, t in enumerate(tags) if "qualitative" in t["study_designs"]}
    corr = {i for i, t in enumerate(tags) if "correlational" in t["study_designs"]}
    rev = {i for i, t in enumerate(tags) if "review" in t["study_designs"]}
    w(f"- Experimental or quasi-experimental: **{len(exp)}** ({_pct(len(exp), n)})")
    w(f"- Qualitative — often the richest mechanism evidence in a realist review: "
      f"**{len(qual)}** ({_pct(len(qual), n)})")
    w(f"- Experimental **and** qualitative (mixed methods): **{len(exp & qual)}**")
    w(f"- Correlational or cross-sectional only — the protocol excludes these unless they "
      f"carry mechanism evidence: **{len(corr - exp - qual)}** ({_pct(len(corr - exp - qual), n)})")
    w(f"- Reviews and syntheses: **{len(rev)}** ({_pct(len(rev), n)})")
    w("")

    # --- the records that answer the question most directly --------------------
    w("## The records closest to the review question")
    w("")
    w("Ranked by how many of the four roles a record touches — an intervention, a mechanism "
      "family, an achievement emotion and a named context — then by citations. **This is a "
      "dictionary score, not a quality judgement**, and it is the order a screening pilot "
      "should work down if budget arrives for only part of the pool.")
    w("")
    scored = []
    for rec, t in zip(pool, tags):
        roles = sum(bool(t[b]) for b in
                    ("interventions", "mechanism_families", "achievement_emotions",
                     "context_dimensions"))
        scored.append((roles, rec.get("cited_by") or 0, rec, t))
    scored.sort(key=lambda s: (-s[0], -s[1]))
    w("| Roles | Cites | Year | Title | Interventions × mechanisms |")
    w("|---|---|---|---|---|")
    for roles, cites, rec, t in scored[:25]:
        iv = ", ".join(sorted(matchers["interventions"][k][0] for k in t["interventions"]))[:46]
        mech = ", ".join(sorted(matchers["mechanism_families"][k][0] for k in t["mechanism_families"]))[:46]
        title = (rec.get("title") or "").replace("|", "\\|")[:72]
        w(f"| {roles}/4 | {cites} | {rec.get('year')} | {title} | {iv} × {mech} |")
    w("")
    full = sum(1 for roles, _c, _r, _t in scored if roles == 4)
    w(f"**{full} records ({_pct(full, n)}) touch all four roles.** That is the realistic "
      "size of a first screening round aimed at mechanism evidence rather than at coverage.")
    w("")

    # --- the theory pool -------------------------------------------------------
    if theory:
        w("## The theory pool, separately")
        w("")
        w(f"{len(theory)} records, searched without an intervention term, because the "
          "ten corpus queries all require one and therefore cannot reach the literature this "
          "review's programme theory is built from. They are **not** candidate studies.")
        w("")
        w("| Cites | Year | Title |")
        w("|---|---|---|")
        for rec in sorted(theory, key=lambda r: -(r.get("cited_by") or 0))[:15]:
            w(f"| {rec.get('cited_by')} | {rec.get('year')} | "
              f"{(rec.get('title') or '').replace('|', '\\|')[:86]} |")
        w("")

    w("## What this map cannot tell you")
    w("")
    w("- **Whether anything works.** No effect, no direction, no magnitude. Term presence only.")
    w("- **Whether a record is eligible.** The protocol's criteria have been applied to nothing.")
    w("- **Whether a mechanism is real.** A record mentioning reappraisal may be measuring it, "
      "teaching it, or arguing against it.")
    w("- **What the gaps mean.** An empty cell is either a gap in the literature or a gap in "
      "the dictionary, and this file cannot distinguish them.")
    w("")
    w("All four need screening and extraction. The evidence map's job is to make that spend "
      "small and well-aimed, and the table of records closest to the review question is where "
      "it should be aimed.")
    w("")

    out = OUTPUTS_DIR / "EVIDENCE_MAP.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"{len(L)} lines -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
