#!/usr/bin/env python3
"""Write every prompt in the pipeline to ``config/prompts/``, and check they still agree.

Prof. Zheng's 2026-10-30 email asks by name for "the agents, prompts, instructions,
schemas, and configurations used in the pipeline". Before 2026-11-04 the prompts existed
only as string literals spread across ten modules, so there was nothing to hand over.

Each call site now reads ``system_prompt=P("<key>", "<literal>")``. This script walks the
AST, pulls the literal out of every such call, and writes it to a YAML file per module.
Those YAML files are the editable copy: ``core/prompts.py`` prefers them over the inline
literal, so the new topic's prompts can be written without touching code.

    python scripts/export_prompts.py            # write config/prompts/*.yaml
    python scripts/export_prompts.py --check    # fail if YAML and code have diverged

``--check`` is the part that matters over time. A YAML override that silently drifts from
the literal it shadows is worse than no override at all, because a run would then use a
prompt nobody has read. Run it before reporting results.
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "res_pipeline"


def _module_constants(tree: ast.Module) -> dict[str, str]:
    """Module-level ``NAME = "..."`` string constants, so a prompt held in one resolves.

    Nine of the twenty-three prompts are a bare name pointing at a constant defined at
    the top of the module, and three more concatenate a literal with one. Refusing to
    follow a name would leave twelve perfectly static prompts out of the export for no
    reason other than where the author chose to put them.
    """
    consts: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 \
                and isinstance(node.targets[0], ast.Name):
            try:
                value = ast.literal_eval(node.value)
            except ValueError:
                continue
            if isinstance(value, str):
                consts[node.targets[0].id] = value
    return consts


def _resolve(node: ast.expr, consts: dict[str, str]) -> str | None:
    """The prompt's text, following names and ``+`` concatenation; None if runtime-built."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name):
        return consts.get(node.id)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left, right = _resolve(node.left, consts), _resolve(node.right, consts)
        return None if left is None or right is None else left + right
    return None


def literals() -> dict[str, dict[str, str]]:
    """``{module_stem: {key: prompt_text}}`` for every ``P(key, ...)`` found."""
    found: dict[str, dict[str, str]] = {}
    for path in sorted(SRC.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        if "system_prompt" not in source:
            continue
        tree = ast.parse(source)
        consts = _module_constants(tree)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            for kw in node.keywords or []:
                if kw.arg != "system_prompt":
                    continue
                call = kw.value
                if not (isinstance(call, ast.Call) and getattr(call.func, "id", "") == "P"):
                    print(f"  ! {path.relative_to(ROOT)}:{node.lineno} not wrapped in P()",
                          file=sys.stderr)
                    continue
                key = ast.literal_eval(call.args[0])
                # An f-string, or text built by a call such as persona() reading
                # config/agents.yaml: composed per invocation and not liftable into a
                # static file. Recorded as None so the omission is visible, not silent.
                found.setdefault(path.stem, {})[key] = _resolve(call.args[1], consts)
    return found


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help="compare code against the YAML instead of rewriting it")
    args = ap.parse_args()

    out_dir = ROOT / "config" / "prompts"
    found = literals()
    static = {m: {k: v for k, v in d.items() if v is not None} for m, d in found.items()}
    dynamic = sum(1 for d in found.values() for v in d.values() if v is None)

    if args.check:
        drift = []
        for module, prompts in static.items():
            path = out_dir / f"{module}.yaml"
            on_disk = yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else {}
            for key, text in prompts.items():
                if (on_disk or {}).get(key, text) != text:
                    drift.append(f"{module}.yaml :: {key}")
        if drift:
            print("PROMPT DRIFT — the YAML override no longer matches the code literal:")
            for d in drift:
                print("   ", d)
            return 1
        print(f"OK — {sum(len(v) for v in static.values())} prompts agree with the code.")
        return 0

    out_dir.mkdir(parents=True, exist_ok=True)
    for module, prompts in sorted(static.items()):
        header = (f"# Prompts sent by res_pipeline/**/{module}.py\n"
                  f"# Generated by scripts/export_prompts.py. Editing a value here CHANGES\n"
                  f"# what the pipeline sends; core/prompts.py prefers this over the code\n"
                  f"# literal. Delete a key to fall back to the literal. Run --check after.\n\n")
        (out_dir / f"{module}.yaml").write_text(
            header + yaml.safe_dump(prompts, allow_unicode=True, sort_keys=True,
                                    default_flow_style=False, width=96),
            encoding="utf-8")
        print(f"  {module}.yaml  {len(prompts)} prompts")

    n = sum(len(v) for v in static.values())
    print(f"\n{n} prompts written to {out_dir.relative_to(ROOT)}")
    if dynamic:
        print(f"{dynamic} prompt(s) are composed at runtime (f-strings) and stay in code.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
