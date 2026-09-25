"""Generate a human coding workbook for the per-paper CMOC gold standard.

The per-paper gold standard MUST be produced by independent human coders — not by
the model, and not by AI-adjudicating the model's own output (the circularity that
made the old ``Richmond_Per_Paper_Adjudication_Completed.xlsx`` unusable as ground
truth). This module builds a clean, self-documenting workbook designed for a
defensible, reviewer-proof coding protocol:

  * Sheet ``Instructions`` — the coding protocol and the two-coder + kappa workflow.
  * Sheet ``E-code reference`` — Richmond's 47 entities (the controlled vocabulary).
  * Sheet ``R-code reference`` — Richmond's 40 relation predicates.
  * One sheet per study ``S0xx`` — the coder reads the paper and records CMOCs
    BLIND (model output is deliberately NOT shown, to avoid anchoring bias).
  * Sheet ``Model candidates`` — the model's extractions, provided ONLY for the
    post-blind ADJUDICATION pass, clearly separated.

Cohen's kappa between two coders' completed workbooks is computed by
:func:`compute_kappa`.
"""

from __future__ import annotations

import json
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

from res_pipeline.core.config import GOLD_DIR, OUTPUTS_DIR
from res_pipeline.core.db import get_connection

_HEADER_FILL = PatternFill("solid", fgColor="2F5BD0")
_HEADER_FONT = Font(color="FFFFFF", bold=True)
_WRAP = Alignment(wrap_text=True, vertical="top")


def _style_header(ws, row: int = 1) -> None:
    for cell in ws[row]:
        cell.fill = _HEADER_FILL
        cell.font = _HEADER_FONT
        cell.alignment = Alignment(vertical="center")


def build_coding_workbook(out_path: Path | None = None, coder_label: str = "coder_A") -> Path:
    gold = json.loads((GOLD_DIR / "richmond_gold.json").read_text(encoding="utf-8"))
    out_path = out_path or (OUTPUTS_DIR / "gold" / f"per_paper_coding_{coder_label}.xlsx")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    wb = Workbook()

    # --- Instructions ---
    ws = wb.active
    ws.title = "Instructions"
    ws.column_dimensions["A"].width = 110
    instructions = [
        ("Per-paper CMOC gold-standard coding protocol", True),
        ("", False),
        ("Purpose: build an INDEPENDENT human gold standard of the Context-Mechanism-Outcome "
         "configurations (CMOCs) each of the 28 Richmond studies supports, so the automated "
         "pipeline's per-paper extraction can be validated without circularity.", False),
        ("", False),
        ("Protocol (RAMESES-aligned):", True),
        ("1. Two coders complete a copy of this workbook INDEPENDENTLY (coder_A, coder_B).", False),
        ("2. For each study sheet, READ THE PAPER and record every CMOC you judge it to support. "
         "Do this BLIND — do not look at the 'Model candidates' sheet until step 4.", False),
        ("3. For each CMOC element, pick the closest Richmond E-code from the dropdown (or write "
         "'NEW' + a short label if genuinely outside the E01-E47 vocabulary), and paste the "
         "verbatim supporting quote with its page.", False),
        ("4. ADJUDICATION: after both coders finish blind, run `res gold-template --compare`. "
         "It reports positive specific agreement on the elements (the correct statistic for "
         "span marking — Cohen's kappa is undefined here, per Hripcsak & Rothschild 2005) plus "
         "Krippendorff's alpha and Gwet's AC1 on the role assignment. ONLY THEN open "
         "ADJUDICATION_ONLY_model_candidates.xlsx, which is a separate file for this reason.",
         False),
        ("5. The reconciled workbook becomes gold/per_paper_gold/ — the ground truth for the "
         "CMOC-extraction verification metric.", False),
        ("", False),
        ("Element types: Context, Intervention, Mechanism_Resource, Mechanism_Response, Outcome "
         "(see 'E-code reference'). Every CMOC needs at least one Context and one Outcome.", False),
    ]
    for i, (text, bold) in enumerate(instructions, 1):
        cell = ws.cell(row=i, column=1, value=text)
        cell.alignment = _WRAP
        if bold:
            cell.font = Font(bold=True, size=12 if i == 1 else 11)

    # --- E-code reference ---
    ws = wb.create_sheet("E-code reference")
    ws.append(["E-code", "Category", "Label (Richmond)", "Location"])
    _style_header(ws)
    for code, spec in gold["entities"].items():
        ws.append([code, spec["category"], spec["label"], spec.get("location", "")])
    for col, width in zip("ABCD", (10, 22, 80, 28)):
        ws.column_dimensions[col].width = width

    ecode_list = ",".join(list(gold["entities"].keys()) + ["NEW"])

    # --- R-code reference ---
    ws = wb.create_sheet("R-code reference")
    ws.append(["R-code", "Subject", "Predicate", "Object"])
    _style_header(ws)
    cats = {c: s["category"] for c, s in gold["entities"].items()}
    for rel in gold["relationships"]:
        ws.append([rel["id"], f"{rel['subject_code']} ({cats[rel['subject_code']]})",
                   rel["predicate"], f"{rel['object_code']} ({cats[rel['object_code']]})"])
    for col, width in zip("ABCD", (10, 40, 16, 40)):
        ws.column_dimensions[col].width = width

    # --- Worked example -------------------------------------------------------------
    # A coder who has never done this needs to see one paper already coded far more than
    # they need another paragraph of instructions. The example is Richmond's own Context-2
    # statement (p.714), where the authors themselves tagged each element in the sentence —
    # so it shows the target without anyone having to invent one.
    ws = wb.create_sheet("EXAMPLE — read this first")
    ws.cell(row=1, column=1, value=(
        "WORKED EXAMPLE. This is what ONE coded paper looks like. Do not edit this sheet — "
        "it is here to show you the target. Each study sheet has these same seven columns."
    )).font = Font(bold=True, size=12)
    ws.cell(row=2, column=1, value=(
        "The source sentence is Richmond et al. (2020) p.714, where the authors marked the "
        "elements themselves:  \"When an expert's reasoning processes or thoughts are "
        "explicitly revealed and discussed (Mresource) with students with sufficient "
        "domain-specific knowledge (C), this promotes understanding (Mresponse) leading to "
        "insight (Mresponse) into the reasoning process (O) and a positive learning "
        "experience (O).\"   That one sentence becomes the four rows below: one CMOC."
    )).alignment = _WRAP
    ws.row_dimensions[2].height = 60
    ws.append([])
    ws.append(["CMOC #", "Element type", "E-code", "Your label", "Verbatim quote",
               "Page", "Polarity"])
    _style_header(ws, row=4)
    for row in [
        [1, "Context", "E03", "students with high domain-specific knowledge",
         "students with sufficient domain-specific knowledge", "714", "positive"],
        [1, "Mechanism_Resource", "E07", "expert's reasoning made explicit and discussed",
         "an expert's reasoning processes or thoughts are explicitly revealed and discussed",
         "714", "positive"],
        [1, "Mechanism_Response", "E20", "understanding of the reasoning process",
         "this promotes understanding", "714", "positive"],
        [1, "Outcome", "E22", "positive learning experience",
         "a positive learning experience", "714", "positive"],
    ]:
        ws.append(row)
    ws.append([])
    for note in [
        "HOW TO READ IT:",
        "  * All four rows share CMOC # = 1, because they are one causal story. The next "
        "story in the same paper would be CMOC # 2.",
        "  * 'Your label' is your own short wording. 'Verbatim quote' must be copied from the "
        "paper exactly — if you cannot find a sentence, do not code that element.",
        "  * E-code is the closest match from the 'E-code reference' sheet, or type NEW if the "
        "paper says something genuinely outside that list.",
        "  * Most papers give 2-5 CMOCs. Twenty means you are coding sentences, not claims.",
        "",
        "THE DISTINCTION PEOPLE GET WRONG MOST OFTEN:",
        "  Mechanism_Response = inside one learner's head (understood, panicked, felt at ease).",
        "  Outcome            = a result you could put in a results table (accuracy rose, "
        "scores unchanged, similar decision speed across groups).",
        "  'The two groups showed similar decision speed' is an OUTCOME, not a response — "
        "even though it is about learners.",
    ]:
        r = ws.max_row + 1
        c = ws.cell(row=r, column=1, value=note)
        c.alignment = _WRAP
        if note.endswith(":"):
            c.font = Font(bold=True)
    for col, width in zip("ABCDEFG", (8, 22, 10, 40, 70, 8, 10)):
        ws.column_dimensions[col].width = width

    with get_connection() as conn:
        studies = conn.execute(
            "SELECT study_id, title, year FROM studies ORDER BY study_id"
        ).fetchall()

    for study in studies:
        ws = wb.create_sheet(study["study_id"])
        ws.cell(row=1, column=1,
                value=f"{study['study_id']} ({study['year']}): {study['title']}").font = Font(bold=True)
        ws.append([])
        header = ["CMOC #", "Element type", "E-code", "Your label", "Verbatim quote", "Page", "Polarity"]
        ws.append(header)
        _style_header(ws, row=3)
        dv_ecode = DataValidation(type="list", formula1=f'"{ecode_list[:250]}"', allow_blank=True)
        dv_type = DataValidation(
            type="list",
            formula1='"Context,Intervention,Mechanism_Resource,Mechanism_Response,Outcome"',
            allow_blank=True)
        dv_pol = DataValidation(type="list", formula1='"positive,negative,mixed"', allow_blank=True)
        ws.add_data_validation(dv_ecode)
        ws.add_data_validation(dv_type)
        ws.add_data_validation(dv_pol)
        for r in range(4, 40):
            dv_type.add(ws.cell(row=r, column=2))
            dv_ecode.add(ws.cell(row=r, column=3))
            dv_pol.add(ws.cell(row=r, column=7))
        for col, width in zip("ABCDEFG", (8, 20, 10, 32, 60, 8, 10)):
            ws.column_dimensions[col].width = width

    # The machine's own answers are deliberately NOT in this file. They used to be, on a
    # sheet headed "DO NOT CONSULT" — but a warning label in the same workbook a coder has
    # open all day is not a control. Coding done after seeing model output agrees with the
    # model, not independently: Dai, Xiong & Ku (Findings of EMNLP 2023) measured
    # human-with-LLM agreement at kappa 0.87 against the person who did it and 0.54 against
    # an independent third coder. They are written to a separate file, opened only at
    # adjudication, after `res gold-template --compare` has produced the human ceiling.

    wb.save(out_path)
    _write_model_candidates(out_path.parent / "ADJUDICATION_ONLY_model_candidates.xlsx")
    return out_path


def _write_model_candidates(out_path: Path) -> Path:
    """The pipeline's own extraction, in a separate file for the adjudication step only."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Model candidates"
    ws.cell(row=1, column=1, value=(
        "DO NOT OPEN until BOTH coders have finished and `res gold-template --compare` has "
        "been run. Seeing these before coding makes your coding agree with the machine rather "
        "than independently, which destroys the only thing this exercise produces."
    )).font = Font(bold=True, color="B23B3B")
    ws.append(["Study", "CMOC", "Element type", "Model label", "Verbatim quote", "Support"])
    _style_header(ws, row=2)
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT e.study_id, e.cmoc_id, e.entity_type, e.label, e.verbatim_quote, "
            "c.verifier_support FROM entity_instances e JOIN cmocs c USING (cmoc_id) "
            "ORDER BY e.study_id, e.cmoc_id"
        ).fetchall()
    for row in rows:
        ws.append([row["study_id"], row["cmoc_id"], row["entity_type"], row["label"],
                   (row["verbatim_quote"] or "")[:200], round(row["verifier_support"] or 0, 2)])
    for col, width in zip("ABCDEF", (8, 20, 20, 32, 60, 10)):
        ws.column_dimensions[col].width = width
    wb.save(out_path)
    return out_path


def compute_kappa(coder_a_codes: list[str], coder_b_codes: list[str]) -> float:
    """Cohen's kappa for two aligned lists of categorical codes."""
    if len(coder_a_codes) != len(coder_b_codes) or not coder_a_codes:
        raise ValueError("Coder code lists must be non-empty and equal length.")
    n = len(coder_a_codes)
    observed = sum(a == b for a, b in zip(coder_a_codes, coder_b_codes)) / n
    labels = set(coder_a_codes) | set(coder_b_codes)
    expected = sum(
        (coder_a_codes.count(k) / n) * (coder_b_codes.count(k) / n) for k in labels
    )
    return (observed - expected) / (1 - expected) if expected != 1 else 1.0
