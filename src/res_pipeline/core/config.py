"""Central configuration: environment, paths, and YAML config loading.

Single place where paths and settings are resolved; no other module should read
``.env`` or construct project paths ad hoc.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel

PROJECT_ROOT = Path(__file__).resolve().parents[3]

# .env is read BEFORE the directories are resolved, because the directories are
# now overridable from it. Moving this line below them would silently restore the
# hardcoded paths for anyone configuring a second review through .env.
load_dotenv(PROJECT_ROOT / ".env")


def _dir(env_var: str, default: str) -> Path:
    """A project directory, overridable from the environment.

    Richmond's corpus, gold standard and published outputs all live at the paths
    below. A SECOND review on a new topic — the professor's 2026-10-30 assignment
    is the first — needs its own config, corpus and outputs, and until these were
    overridable it had nowhere to go: `res export-results` writes
    ``outputs/RESULTS.html``, which is the project's artefact of record and was
    once already overwritten with a worse version (M38). Pointing a new review at
    the same directory would destroy published figures, not just inconvenience
    someone. ``POSTGRES_DB`` was already overridable; these are what was missing.

    Relative values resolve against the project root, so ``RES_OUTPUTS_DIR=outputs-emotion``
    means what it looks like.
    """
    raw = os.getenv(env_var)
    if not raw or not raw.strip():
        return PROJECT_ROOT / default
    candidate = Path(raw.strip()).expanduser()
    return candidate if candidate.is_absolute() else PROJECT_ROOT / candidate


CONFIG_DIR = _dir("RES_CONFIG_DIR", "config")
DATA_DIR = _dir("RES_DATA_DIR", "data")
GOLD_DIR = _dir("RES_GOLD_DIR", "gold")
OUTPUTS_DIR = _dir("RES_OUTPUTS_DIR", "outputs")


def active_paths() -> dict[str, str]:
    """The directories and database this process will actually use.

    Isolation you cannot see is isolation you will forget you configured, and the
    failure mode is writing a new topic's results over Richmond's. Surfaced by
    ``res status``.
    """
    default = {
        "config": PROJECT_ROOT / "config",
        "data": PROJECT_ROOT / "data",
        "gold": PROJECT_ROOT / "gold",
        "outputs": PROJECT_ROOT / "outputs",
    }
    live = {"config": CONFIG_DIR, "data": DATA_DIR, "gold": GOLD_DIR, "outputs": OUTPUTS_DIR}
    out = {}
    for name, path in live.items():
        try:
            shown = str(path.relative_to(PROJECT_ROOT))
        except ValueError:
            shown = str(path)
        out[name] = shown + ("" if path == default[name] else "   [overridden]")
    out["database"] = os.getenv("POSTGRES_DB", "realist_synthesis")
    return out


class PostgresSettings(BaseModel):
    host: str = os.getenv("POSTGRES_HOST", "localhost")
    port: int = int(os.getenv("POSTGRES_PORT", "5432"))
    user: str = os.getenv("POSTGRES_USER", "postgres")
    password: str = os.getenv("POSTGRES_PASSWORD", "")
    database: str = os.getenv("POSTGRES_DB", "realist_synthesis")

    @property
    def dsn(self) -> str:
        return (
            f"host={self.host} port={self.port} user={self.user} "
            f"password={self.password} dbname={self.database}"
        )


class Settings(BaseModel):
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    postgres: PostgresSettings = PostgresSettings()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


@lru_cache(maxsize=None)
def load_yaml_config(name: str) -> dict:
    """Load a YAML file from ``config/`` by bare name, e.g. ``models`` or ``ontology``."""
    path = CONFIG_DIR / f"{name}.yaml"
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)
