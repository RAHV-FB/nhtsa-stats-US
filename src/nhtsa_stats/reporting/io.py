"""Write analysis outputs with provenance.

Every table is written as CSV (``outputs/tables/<module>/<name>.csv``) with a JSON sidecar
recording the producing module, the git commit, the input datasets with their row counts,
and free-text notes (population, unit, outcome, method).  Reports cite these files so every
number can be traced back to code and raw archives.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import polars as pl

from nhtsa_stats import config


def git_commit() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=config.PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        # Only source changes make a run "dirty"; the outputs being written do not.
        dirty = subprocess.run(
            [
                "git",
                "status",
                "--porcelain",
                "--untracked-files=no",
                "--",
                ".",
                ":(exclude)outputs",
                ":(exclude)reports",
                ":(exclude)docs/generated",
            ],
            cwd=config.PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout.strip()
        return out.stdout.strip() + ("-dirty" if dirty else "")
    except (subprocess.SubprocessError, OSError):
        return "unknown"


def file_sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def module_source_path(module: str) -> Path | None:
    """Source file of an importable module, found without importing (running) it."""
    try:
        spec = importlib.util.find_spec(module)
    except (ImportError, ValueError):
        return None
    if spec is None or not spec.origin or not spec.origin.endswith(".py"):
        return None
    return Path(spec.origin)


def module_source_sha256(module: str) -> str | None:
    path = module_source_path(module)
    return file_sha256(path) if path is not None and path.exists() else None


def package_sha256(root: Path | None = None) -> str:
    """One digest over every ``*.py`` file of the package (sorted relative paths + bytes)."""
    root = Path(root) if root is not None else Path(__file__).resolve().parents[1]
    h = hashlib.sha256()
    for f in sorted(p for p in root.rglob("*.py") if "__pycache__" not in p.parts):
        h.update(f.relative_to(root).as_posix().encode())
        h.update(b"\0")
        h.update(f.read_bytes())
        h.update(b"\0")
    return h.hexdigest()


def table_path(module: str, name: str) -> Path:
    return config.TABLES_DIR / module / f"{name}.csv"


def _caller_module(default: str) -> str:
    """Name of the package module that called ``save_table`` (provenance for the sidecar)."""
    name = sys._getframe(2).f_globals.get("__name__", "")
    return name if name.startswith("nhtsa_stats.") else default


def save_table(
    df: pd.DataFrame | pl.DataFrame,
    module: str,
    name: str,
    *,
    description: str,
    population: str = "",
    unit: str = "",
    outcome: str = "",
    method: str = "",
    inputs: list[str] | None = None,
    extra: dict[str, Any] | None = None,
    float_format: str = "%.6g",
) -> Path:
    path = table_path(module, name)
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(df, pl.DataFrame):
        df = df.to_pandas()
    df.to_csv(path, index=False, float_format=float_format)
    producer = _caller_module(f"nhtsa_stats.analysis.{module}")
    meta = {
        "table": f"{module}/{name}.csv",
        "description": description,
        "population": population,
        "unit": unit,
        "outcome": outcome,
        "method": method,
        "inputs": inputs or [],
        "rows": len(df),
        "columns": list(df.columns),
        "module": producer,
        "git_commit": git_commit(),
        "source_sha256": module_source_sha256(producer),
        "package_sha256": package_sha256(),
        "generated_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        **(extra or {}),
    }
    path.with_suffix(".json").write_text(json.dumps(meta, indent=1, default=str))
    return path


def save_json(obj: Any, module: str, name: str) -> Path:
    path = config.TABLES_DIR / module / f"{name}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, default=float))
    return path


def save_figure(fig, module: str, name: str) -> Path:
    path = config.FIGURES_DIR / module / f"{name}.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    return path


def load_table(module: str, name: str) -> pd.DataFrame:
    return pd.read_csv(table_path(module, name))
