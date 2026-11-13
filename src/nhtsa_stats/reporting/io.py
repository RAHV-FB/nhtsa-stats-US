"""Write analysis outputs with provenance.

Every table is written as CSV (``outputs/tables/<module>/<name>.csv``) with a JSON sidecar
recording the producing module, the git commit, the input datasets, and free-text notes
(population, unit, outcome, method).  Two digests make staleness checkable (``nhtsa status``);
how they are computed lives in ``nhtsa_stats.reporting.provenance``:

* ``code_sha256``: digest over the producing module and every ``nhtsa_stats`` module it imports
  (transitively), taken from the source snapshot made when the process started, so editing a
  file during a long run cannot mark old results fresh and comment or docstring edits do not
  mark tables stale.
* ``inputs_sha256``: SHA-256 of each local data file listed in ``inputs``.

``save_json`` dict outputs carry the same kind of record under a ``_provenance`` key.
Reports cite these files so every number can be traced back to code and raw archives.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import polars as pl

from nhtsa_stats import config
from nhtsa_stats.reporting import provenance


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
        "git_commit": provenance.git_commit(),
        "source_sha256": provenance.module_source_sha256(producer),
        "code_sha256": provenance.current_code_sha256(producer),
        "inputs_sha256": provenance.inputs_sha256(inputs or []),
        "package_sha256": provenance.package_sha256(),
        "generated_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        **(extra or {}),
    }
    path.with_suffix(".json").write_text(json.dumps(meta, indent=1, default=str))
    return path


def save_json(obj: Any, module: str, name: str) -> Path:
    """Write ``obj`` as JSON.  Dict outputs get a ``_provenance`` entry (module, code digest,
    git commit, time); lists are written as they are."""
    path = config.TABLES_DIR / module / f"{name}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(obj, dict):
        producer = _caller_module(f"nhtsa_stats.analysis.{module}")
        obj = {
            **obj,
            "_provenance": {
                "module": producer,
                "code_sha256": provenance.current_code_sha256(producer),
                "git_commit": provenance.git_commit(),
                "generated_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            },
        }
    path.write_text(json.dumps(obj, indent=1, default=float))
    return path


def save_figure(fig, module: str, name: str) -> Path:
    path = config.FIGURES_DIR / module / f"{name}.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    return path


def load_table(module: str, name: str) -> pd.DataFrame:
    return pd.read_csv(table_path(module, name))
