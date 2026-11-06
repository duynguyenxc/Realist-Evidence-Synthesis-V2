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
    db = os.getenv("POSTGRES_DB", "realist_synthesis")
    # The directories can be isolated while the database is not, which is the one
    # combination that silently mixes two reviews' evidence. Say so here, loudly.
    unsafe = bool((os.getenv("RES_CONFIG_DIR") or "").strip()) and db == "realist_synthesis"
    out["database"] = db + ("   [!! NOT ISOLATED — writes are blocked, set POSTGRES_DB]"
                            if unsafe else "")
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


class IsolationError(RuntimeError):
    """A second review is configured to write into the first review's database."""


def assert_isolated() -> None:
    """Refuse to write a new review's data into Richmond's database.

    The directory overrides added on 2026-11-02 gave a second review somewhere to put
    its corpus, config and outputs. They do NOT isolate the database, and the database
    is where the entities, relations and CMOCs actually live — so a run with
    ``RES_CONFIG_DIR=config-emotion`` and no ``POSTGRES_DB`` would write a different
    topic's extractions into the tables every published Richmond figure was computed
    from, with no error and no obvious symptom until somebody recounted.

    Called by the stages that write. Reading is unaffected, so `res status` and the
    console still work and can explain the problem.
    """
    import os as _os

    config_overridden = bool((_os.getenv("RES_CONFIG_DIR") or "").strip())
    db = _os.getenv("POSTGRES_DB", "realist_synthesis")
    if config_overridden and db == "realist_synthesis":
        raise IsolationError(
            f"CONFIG_DIR is overridden ({CONFIG_DIR.name}) but POSTGRES_DB is still "
            f"'{db}' — Richmond's database. A second review must not write into it.\n"
            f"  Set POSTGRES_DB in .env (e.g. POSTGRES_DB=realist_emotion) and create it:\n"
            f"    createdb realist_emotion\n"
            f"Reading is unaffected; only stages that write are blocked.")
