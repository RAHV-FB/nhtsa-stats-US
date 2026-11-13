"""Provenance mechanics: source hashing, import closures, the code snapshot, git, input hashes.

``reporting.io`` writes the tables and calls this module for what goes into the sidecars:

* ``code_sha256``: one digest over the producing module and every ``nhtsa_stats`` module it
  imports (transitively, including imports inside functions), so a change to a shared helper
  marks dependent tables stale.  A file is digested as its AST with docstrings removed, so
  comment, blank-line, formatting and docstring edits leave the digest alone while any code or
  string-literal change (sidecar ``method`` text included) changes it.
* One **snapshot** of every ``nhtsa_stats/**/*.py`` is taken per process (``take_snapshot``, called
  first thing by ``cli.main``; lazily on first use otherwise) and every closure is computed from
  it.  Files edited on disk afterwards cannot leak into the recorded hashes, whichever module
  has been imported by then.
* ``inputs_sha256``: SHA-256 of each local data file named in ``inputs`` (``data/...`` under
  ``config.DATA_DIR``, ``outputs/...`` under ``config.OUTPUT_DIR``).

This module is excluded from every closure: it records provenance and cannot change the content
of a table, so editing it must not mark every table stale.  A syntax or decode error in a file
that belongs to a closure raises ``ProvenanceError`` instead of silently shrinking the closure.
"""

from __future__ import annotations

import ast
import hashlib
import subprocess
from dataclasses import dataclass
from pathlib import Path

from nhtsa_stats import config

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
PROVENANCE_MODULE = "reporting.provenance"  # relative to the package, excluded from closures


class ProvenanceError(RuntimeError):
    """A source file needed for a code digest cannot be read or parsed."""


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ---- source digests ------------------------------------------------------------------------


def _strip_docstrings(tree: ast.AST) -> ast.AST:
    for node in ast.walk(tree):
        if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            body = node.body
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                node.body = body[1:] or [ast.Pass()]
    return tree


def ast_digest(source: bytes) -> str:
    """SHA-256 of the AST of ``source`` with module/class/function docstrings removed."""
    tree = _strip_docstrings(ast.parse(source))
    return hashlib.sha256(ast.dump(tree).encode()).hexdigest()


def _imports(tree: ast.AST, name: str, is_pkg: bool, package: str) -> frozenset[str]:
    """Candidate package modules imported anywhere in ``tree`` (including inside functions)."""
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
    return frozenset(m for m in found if m == package or m.startswith(package + "."))


@dataclass(frozen=True)
class SourceInfo:
    path: Path
    raw_sha256: str | None = None
    digest: str | None = None
    imports: frozenset[str] = frozenset()
    error: str | None = None


def _read_source(path: Path, name: str, is_pkg: bool, package: str) -> SourceInfo:
    try:
        data = path.read_bytes()
        tree = ast.parse(data)
        digest = ast_digest(data)
    except (OSError, SyntaxError, ValueError) as e:  # ValueError covers UnicodeDecodeError
        return SourceInfo(path, error=f"{type(e).__name__}: {e}")
    return SourceInfo(
        path,
        raw_sha256=hashlib.sha256(data).hexdigest(),
        digest=digest,
        imports=_imports(tree, name, is_pkg, package),
    )


class Snapshot:
    """The source of every ``*.py`` file of a package as it was when the snapshot was taken."""

    def __init__(self, root: Path | None = None, package: str | None = None):
        self.root = Path(root) if root is not None else PACKAGE_ROOT
        self.package = package or self.root.name
        self.sources: dict[str, SourceInfo] = {}
        for path in sorted(p for p in self.root.rglob("*.py") if "__pycache__" not in p.parts):
            rel = path.relative_to(self.root).with_suffix("")
            is_pkg = rel.name == "__init__"
            parts = rel.parent.parts if is_pkg else rel.parts
            name = ".".join((self.package, *parts))
            self.sources[name] = _read_source(path, name, is_pkg, self.package)
        self._closures: dict[str, list[str]] = {}
        self._codes: dict[str, str | None] = {}

    @property
    def excluded(self) -> str:
        return f"{self.package}.{PROVENANCE_MODULE}"

    def closure(self, module: str) -> list[str]:
        """``module`` plus every package module it imports transitively (and their parent
        packages), sorted by name; ``[]`` for a module that is not in the package.  Raises
        ``ProvenanceError`` when a member cannot be parsed."""
        if module in self._closures:
            return self._closures[module]
        seen: set[str] = set()
        todo = [module]
        while todo:
            name = todo.pop()
            if name in seen or name == self.excluded or name not in self.sources:
                continue
            src = self.sources[name]
            if src.error:
                raise ProvenanceError(f"cannot hash {name} ({src.path}): {src.error}")
            seen.add(name)
            todo.extend(src.imports)
            parent = name.rpartition(".")[0]
            if parent:
                todo.append(parent)  # importing a.b.c runs a/__init__ and a/b/__init__
        self._closures[module] = sorted(seen)
        return self._closures[module]

    def code_sha256(self, module: str) -> str | None:
        """Digest of ``module`` and its closure; ``None`` if ``module`` is not a package module."""
        if module not in self._codes:
            names = self.closure(module)
            if module not in names:
                self._codes[module] = None
            else:
                h = hashlib.sha256()
                for n in names:
                    h.update(n.encode())
                    h.update(b"\0")
                    h.update(str(self.sources[n].digest).encode())
                    h.update(b"\0")
                self._codes[module] = h.hexdigest()
        return self._codes[module]

    def source_sha256(self, module: str) -> str | None:
        """SHA-256 of the raw bytes of the module's own file (informational)."""
        src = self.sources.get(module)
        return src.raw_sha256 if src is not None else None

    def package_sha256(self) -> str:
        """One digest over every file of the package (module names and AST digests)."""
        h = hashlib.sha256()
        for name in sorted(self.sources):
            src = self.sources[name]
            h.update(name.encode())
            h.update(b"\0")
            h.update(str(src.digest or f"error:{src.error}").encode())
            h.update(b"\0")
        return h.hexdigest()


_SNAPSHOT: Snapshot | None = None
_GIT_COMMIT: str | None = None


def take_snapshot() -> Snapshot:
    """Take the process-wide source snapshot (once); later calls return the same snapshot.

    ``cli.main`` calls this before importing anything else, so later edits cannot leak in."""
    global _SNAPSHOT
    if _SNAPSHOT is None:
        _SNAPSHOT = Snapshot()
    return _SNAPSHOT


def current_code_sha256(module: str) -> str | None:
    return take_snapshot().code_sha256(module)


def module_closure(module: str) -> list[str]:
    return take_snapshot().closure(module)


def module_source_sha256(module: str) -> str | None:
    return take_snapshot().source_sha256(module)


def package_sha256() -> str:
    return take_snapshot().package_sha256()


# ---- git -----------------------------------------------------------------------------------


def _git_commit() -> str:
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


def git_commit() -> str:
    """Short HEAD commit (``-dirty`` when source files are modified), read once per process,
    at the same moment as the code snapshot."""
    global _GIT_COMMIT
    if _GIT_COMMIT is None:
        _GIT_COMMIT = _git_commit()
    return _GIT_COMMIT


# ---- inputs --------------------------------------------------------------------------------


def _input_bases() -> list[tuple[str, Path]]:
    """Spec prefix -> directory it stands for (most specific first), read from ``config``."""
    return [
        ("data/", config.DATA_DIR),
        ("outputs/tables/", config.TABLES_DIR),
        ("outputs/audit/", config.AUDIT_DIR),
        ("outputs/", config.OUTPUT_DIR),
    ]


_INPUT_HASHES: dict[tuple[str, str], str | None] = {}


def input_sha256(spec: str) -> str | None:
    """Digest of the local data behind an ``inputs`` entry.

    ``data/...`` and ``outputs/...`` entries (a file, a directory or a glob) are resolved under
    ``config.DATA_DIR`` / ``config.OUTPUT_DIR`` (so ``NHTSA_DATA_DIR`` is honoured); descriptive
    strings and missing data give ``None``.  Hashes of ``data/`` entries are cached per process;
    ``outputs/`` entries are re-read each time because earlier modules rewrite them."""
    resolved = next(
        ((base, spec[len(prefix) :]) for prefix, base in _input_bases() if spec.startswith(prefix)),
        None,
    )
    if resolved is None:
        return None
    base, rest = resolved
    key = (spec, str(base))
    if spec.startswith("data/") and key in _INPUT_HASHES:
        return _INPUT_HASHES[key]
    hits = list(base.glob(rest)) if any(c in rest for c in "*?[") else [base / rest]
    files: set[Path] = set()
    for p in hits:
        if p.is_file():
            files.add(p)
        elif p.is_dir():
            files.update(f for f in p.rglob("*") if f.is_file())
    digest: str | None = None
    if files:
        h = hashlib.sha256()
        for f in sorted(files):
            h.update(f.relative_to(base).as_posix().encode())
            h.update(b"\0")
            h.update(file_sha256(f).encode())
            h.update(b"\0")
        digest = h.hexdigest()
    if spec.startswith("data/"):
        _INPUT_HASHES[key] = digest
    return digest


def inputs_sha256(inputs: list[str]) -> dict[str, str]:
    out = {}
    for spec in inputs:
        d = input_sha256(spec)
        if d is not None:
            out[spec] = d
    return out
