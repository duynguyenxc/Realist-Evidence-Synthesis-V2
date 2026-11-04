"""Prompt text, overridable from ``config/prompts/`` without touching code.

Every prompt in this pipeline used to be a string literal inside the module that sent
it. That had two costs. Prof. Zheng's 2026-10-30 email asks by name for "the agents,
prompts, instructions, schemas, and configurations used in the pipeline", and there was
nothing to hand over but the source tree. And the same email redirects the pipeline at a
new topic, which needs the prompts rewritten — a job that should not require editing ten
modules and re-reading the diff for behaviour changes.

So each call site now reads::

    system_prompt=P("cmoc_extraction.extract", "...the literal, unchanged...")

``P`` returns the override from ``config/prompts/*.yaml`` when one exists and the inline
literal otherwise. **With no YAML files present the behaviour is byte-identical to
before**, which is what makes the extraction safe: the literals remain the specification,
the YAML is the override. ``scripts/export_prompts.py`` regenerates the YAML from the
literals and verifies the two agree.

Keys are ``<module>.<what>``. A key missing from the YAML is not an error — it falls
back — because a half-written override file should degrade to working code, not break a
run half way through a corpus.
"""

from __future__ import annotations

from functools import lru_cache

import yaml

from res_pipeline.core.config import CONFIG_DIR


@lru_cache(maxsize=1)
def _overrides() -> dict[str, str]:
    """Every ``key: text`` pair in ``config/prompts/*.yaml``, flattened.

    Cached, so a run uses one consistent set of prompts throughout rather than picking
    up a mid-run edit on some studies and not others.
    """
    out: dict[str, str] = {}
    d = CONFIG_DIR / "prompts"
    if not d.is_dir():
        return out
    for path in sorted(d.glob("*.yaml")):
        loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(loaded, dict):
            continue
        for key, value in loaded.items():
            if isinstance(value, str) and value.strip():
                out[str(key)] = value
    return out


def P(key: str, inline: str) -> str:
    """The prompt for ``key`` — the YAML override if there is one, else ``inline``."""
    return _overrides().get(key, inline)


def active_prompts() -> dict[str, str]:
    """Which keys are currently overridden; surfaced by ``res status``."""
    return dict(_overrides())
