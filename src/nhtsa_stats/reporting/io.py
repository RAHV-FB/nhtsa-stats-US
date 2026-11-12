"""Write analysis outputs with provenance.

Every table is written as CSV (``outputs/tables/<module>/<name>.csv``) with a JSON sidecar
recording the producing module, the git commit, the input datasets, and free-text notes
(population, unit, outcome, method).  Two digests make staleness checkable (``nhtsa status``):

* ``code_sha256``: one digest over the producing module's source and every ``nhtsa_stats``
  module it imports (transitively), so a change to a shared helper marks dependent tables
  stale.  It is taken when the module is loaded for a run (``snapshot_code_sha256``), not when
  the table is written, so editing a file during a long run cannot mark old results fresh.
* ``inputs_sha256``: SHA-256 of each local data file listed in ``inputs`` (``data/...`` paths).

``save_json`` dict outputs carry the same kind of record under a ``_provenance`` key.
Reports cite these files so every number can be traced back to code and raw archives.
"""

from __future__ import annotations

import ast
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


PACKAGE_NAME = "nhtsa_stats"
_PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def _module_file(name: str, root: Path, package: str) -> Path | None:
    """Source file of ``package.<sub>`` under ``root``, resolved by path (nothing is imported)."""
    if name != package and not name.startswith(package + "."):
        return None
    rel = name[len(package) :].strip(".")
    base = root.joinpath(*rel.split(".")) if rel else root
    for cand in (base.with_suffix(".py"), base / "__init__.py"):
        if cand.is_file():
            return cand
    return None


_IMPORT_CACHE: dict[tuple, set[str]] = {}


def _imported_modules(path: Path, name: str, is_pkg: bool, package: str) -> set[str]:
    """Candidate module names imported anywhere in ``path`` (including inside functions)."""
    try:
        st = path.stat()
        key = (str(path), st.st_mtime_ns, st.st_size, name, package)
    except OSError:
        return set()
    if key not in _IMPORT_CACHE:
        _IMPORT_CACHE[key] = _parse_imports(path, name, is_pkg, package)
    return _IMPORT_CACHE[key]


def _parse_imports(path: Path, name: str, is_pkg: bool, package: str) -> set[str]:
    try:
        tree = ast.parse(path.read_text())
    except (OSError, SyntaxError, UnicodeDecodeError):
        return set()
    here = name if is_pkg else name.rpartition(".")[0]
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                parts = here.split(".")
                keep = len(parts) - (node.level - 1)
                if keep < 1:
                    continue
                base = ".".join(parts[:keep] + ([node.module] if node.module else []))
            else:
                base = node.module or ""
            found.add(base)
            found.update(f"{base}.{a.name}" for a in node.names)  # ``from pkg import submodule``
    return {m for m in found if m == package or m.startswith(package + ".")}


def module_closure(module: str, root: Path | None = None, package: str | None = None) -> list[str]:
    """``module`` plus every package module it imports transitively (and their parent packages),
    sorted by name.  Resolved by parsing import statements, so no module is executed."""
    root = Path(root) if root is not None else _PACKAGE_ROOT
    package = package or root.name
    seen: set[str] = set()
    todo = [module]
    while todo:
        name = todo.pop()
        if name in seen:
            continue
        path = _module_file(name, root, package)
        if path is None:
            continue
        seen.add(name)
        is_pkg = path.name == "__init__.py"
        todo.extend(_imported_modules(path, name, is_pkg, package))
        parent = name.rpartition(".")[0]
        if parent:
            todo.append(parent)  # importing a.b.c runs a/__init__ and a/b/__init__
    return sorted(seen)


def code_sha256(module: str, root: Path | None = None, package: str | None = None) -> str | None:
    """One digest over the source of ``module`` and all package modules it imports transitively.

    ``None`` when ``module`` is not a package module with a source file."""
    root = Path(root) if root is not None else _PACKAGE_ROOT
    package = package or root.name
    names = module_closure(module, root, package)
    if module not in names:
        return None
    h = hashlib.sha256()
    for n in names:
        path = _module_file(n, root, package)
        if path is None:  # pragma: no cover - closure only holds resolvable modules
            continue
        h.update(n.encode())
        h.update(b"\0")
        h.update(path.read_bytes())
        h.update(b"\0")
    return h.hexdigest()


_CODE_SNAPSHOTS: dict[str, str | None] = {}


def snapshot_code_sha256(module: str) -> str | None:
    """Record (and return) the code digest of ``module`` as of now.  Call right after importing
    the module and before ``run()``; ``save_table`` then reports this digest for its caller
    whatever happens to the files afterwards."""
    _CODE_SNAPSHOTS[module] = code_sha256(module)
    # Tables written by a helper module on behalf of ``module`` report the helper's own digest.
    for dep in module_closure(module):
        if dep != module and dep not in _CODE_SNAPSHOTS:
            _CODE_SNAPSHOTS[dep] = code_sha256(dep)
    return _CODE_SNAPSHOTS[module]


def current_code_sha256(module: str) -> str | None:
    """The snapshot for ``module`` if one was taken in this process, else computed (and kept)
    on demand."""
    if module not in _CODE_SNAPSHOTS:
        _CODE_SNAPSHOTS[module] = code_sha256(module)
    # Tables written by a helper module on behalf of ``module`` report the helper's own digest.
    for dep in module_closure(module):
        if dep != module and dep not in _CODE_SNAPSHOTS:
            _CODE_SNAPSHOTS[dep] = code_sha256(dep)
    return _CODE_SNAPSHOTS[module]


_INPUT_HASHES: dict[str, str | None] = {}


def input_sha256(spec: str) -> str | None:
    """Digest of the local data behind an ``inputs`` entry, cached per process.

    Only ``data/...`` entries are hashed (a file, a directory, or a glob, relative to the project
    root); descriptive strings, ``outputs/...`` paths and missing data give ``None``."""
    if spec in _INPUT_HASHES:
        return _INPUT_HASHES[spec]
    digest: str | None = None
    if spec.startswith("data/"):
        root = config.PROJECT_ROOT
        if any(c in spec for c in "*?["):
            files = [p for p in root.glob(spec) if p.is_file()]
            files += [f for d in root.glob(spec) if d.is_dir() for f in d.rglob("*") if f.is_file()]
        elif (root / spec).is_dir():
            files = [f for f in (root / spec).rglob("*") if f.is_file()]
        elif (root / spec).is_file():
            files = [root / spec]
        else:
            files = []
        if files:
            h = hashlib.sha256()
            for f in sorted(set(files)):
                h.update(f.relative_to(root).as_posix().encode())
                h.update(b"\0")
                h.update(file_sha256(f).encode())
                h.update(b"\0")
            digest = h.hexdigest()
    _INPUT_HASHES[spec] = digest
    return digest


def inputs_sha256(inputs: list[str]) -> dict[str, str]:
    out = {}
    for spec in inputs:
        d = input_sha256(spec)
        if d is not None:
            out[spec] = d
    return out


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
        "code_sha256": current_code_sha256(producer),
        "inputs_sha256": inputs_sha256(inputs or []),
        "package_sha256": package_sha256(),
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
                "code_sha256": current_code_sha256(producer),
                "git_commit": git_commit(),
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
