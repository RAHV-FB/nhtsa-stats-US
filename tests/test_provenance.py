"""Code and input hashes in table sidecars: helpers, and staleness of the committed sidecars."""

from __future__ import annotations

import hashlib
import json

import pandas as pd

from nhtsa_stats import cli, config
from nhtsa_stats.reporting import io


def _make_pkg(root):
    """tmp package ``tp``: tp.analysis.mod -> tp.analysis.helper -> tp.util (lazy import)."""
    (root / "analysis").mkdir(parents=True)
    (root / "__init__.py").write_text("")
    (root / "analysis" / "__init__.py").write_text("")
    (root / "util.py").write_text("U = 1\n")
    (root / "other.py").write_text("O = 1\n")
    (root / "analysis" / "helper.py").write_text(
        "def f():\n    from tp import util\n    return util.U\n"
    )
    (root / "analysis" / "mod.py").write_text("from . import helper\nimport tp.other  # noqa\n")
    (root / "analysis" / "solo.py").write_text("X = 1\n")


def test_file_sha256(tmp_path):
    f = tmp_path / "a.py"
    f.write_bytes(b"x = 1\n")
    assert io.file_sha256(f) == hashlib.sha256(b"x = 1\n").hexdigest()


def test_module_source_sha256_matches_file_and_handles_unknown():
    path = io.module_source_path("nhtsa_stats.reporting.io")
    assert path is not None and path.name == "io.py"
    assert io.module_source_sha256("nhtsa_stats.reporting.io") == io.file_sha256(path)
    assert io.module_source_sha256("nhtsa_stats.analysis.no_such_module") is None


def test_package_sha256_depends_on_paths_and_contents(tmp_path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "a.py").write_text("a = 1\n")
    (tmp_path / "b.py").write_text("b = 2\n")
    (tmp_path / "ignored.txt").write_text("not python")
    base = io.package_sha256(tmp_path)
    assert base == io.package_sha256(tmp_path)
    (tmp_path / "ignored.txt").write_text("changed")
    assert io.package_sha256(tmp_path) == base
    (tmp_path / "b.py").write_text("b = 3\n")
    changed = io.package_sha256(tmp_path)
    assert changed != base
    (tmp_path / "b.py").rename(tmp_path / "c.py")
    assert io.package_sha256(tmp_path) != changed


def test_module_closure_follows_relative_absolute_and_lazy_imports(tmp_path):
    root = tmp_path / "tp"
    _make_pkg(root)
    assert io.module_closure("tp.analysis.mod", root) == [
        "tp",
        "tp.analysis",
        "tp.analysis.helper",
        "tp.analysis.mod",
        "tp.other",
        "tp.util",
    ]
    assert io.module_closure("tp.analysis.solo", root) == ["tp", "tp.analysis", "tp.analysis.solo"]
    assert io.module_closure("tp.analysis.nope", root) == []


def test_code_sha256_changes_with_imported_helper_only_for_dependents(tmp_path):
    root = tmp_path / "tp"
    _make_pkg(root)
    mod, solo = io.code_sha256("tp.analysis.mod", root), io.code_sha256("tp.analysis.solo", root)
    assert mod and solo and mod != solo
    assert io.code_sha256("tp.analysis.nope", root) is None
    (root / "util.py").write_text("U = 2\n")  # transitive, lazy import
    assert io.code_sha256("tp.analysis.mod", root) != mod
    assert io.code_sha256("tp.analysis.solo", root) == solo
    mod2 = io.code_sha256("tp.analysis.mod", root)
    (root / "analysis" / "mod.py").write_text(
        "from . import helper\nimport tp.other  # noqa\n# x\n"
    )
    assert io.code_sha256("tp.analysis.mod", root) != mod2


def test_real_modules_depend_on_shared_helpers():
    closure = io.module_closure("nhtsa_stats.analysis.severity")
    assert "nhtsa_stats.analysis.severity" in closure
    assert "nhtsa_stats.reporting.io" in closure and "nhtsa_stats.config" in closure


def test_snapshot_is_used_instead_of_current_source(monkeypatch):
    monkeypatch.setattr(io, "_CODE_SNAPSHOTS", {})
    monkeypatch.setitem(io._CODE_SNAPSHOTS, "nhtsa_stats.x", "snap")
    assert io.current_code_sha256("nhtsa_stats.x") == "snap"
    snap = io.snapshot_code_sha256("nhtsa_stats.reporting.io")
    assert snap == io.code_sha256("nhtsa_stats.reporting.io")


def test_input_sha256_files_dirs_and_globs(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(io, "_INPUT_HASHES", {})
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "a.parquet").write_bytes(b"aaa")
    (tmp_path / "data" / "sub").mkdir()
    (tmp_path / "data" / "sub" / "b.bin").write_bytes(b"bbb")
    out = io.inputs_sha256(
        ["data/a.parquet", "data/sub", "data/*.parquet", "FARS person (text)", "data/missing"]
    )
    assert set(out) == {"data/a.parquet", "data/sub", "data/*.parquet"}
    assert out["data/a.parquet"] != out["data/sub"]


def _write(ns_name, tmp_path, monkeypatch, inputs=None):
    monkeypatch.setattr(config, "TABLES_DIR", tmp_path)
    ns = {"__name__": ns_name, "io": io, "df": pd.DataFrame({"a": [1]}), "inputs": inputs}
    exec(
        "def write():\n"
        "    io.save_table(df, 'm', 't', description='d', inputs=inputs)\n"
        "    io.save_json({'x': 1}, 'm', 'j')\n"
        "    io.save_json([1, 2], 'm', 'lst')\n",
        ns,
    )
    ns["write"]()
    return tmp_path / "m" / "t.json"


def test_save_table_and_json_record_hashes_and_status_flags_changes(tmp_path, monkeypatch):
    monkeypatch.setattr(io, "_CODE_SNAPSHOTS", {})
    monkeypatch.setattr(io, "_INPUT_HASHES", {})
    data = tmp_path / "proj" / "data"
    data.mkdir(parents=True)
    (data / "in.parquet").write_bytes(b"v1")
    monkeypatch.setattr(config, "PROJECT_ROOT", tmp_path / "proj")
    side = _write("nhtsa_stats.reporting.io", tmp_path / "tables", monkeypatch, ["data/in.parquet"])
    meta = json.loads(side.read_text())
    code = io.code_sha256("nhtsa_stats.reporting.io")
    assert meta["code_sha256"] == code
    assert meta["source_sha256"] == io.module_source_sha256("nhtsa_stats.reporting.io")
    assert meta["package_sha256"] == io.package_sha256()
    assert set(meta["inputs_sha256"]) == {"data/in.parquet"}
    j = json.loads((side.parent / "j.json").read_text())
    assert j["x"] == 1 and j["_provenance"]["code_sha256"] == code
    assert j["_provenance"]["module"] == "nhtsa_stats.reporting.io"
    assert json.loads((side.parent / "lst.json").read_text()) == [1, 2]

    ok = cli.stale_tables()
    assert (ok.stale, ok.unhashed, ok.inputs_changed, ok.n_checked) == ([], [], [], 2)

    meta["code_sha256"] = "0" * 64
    side.write_text(json.dumps(meta))
    assert cli.stale_tables().stale == ["m/t.csv"]

    meta["code_sha256"] = code
    side.write_text(json.dumps(meta))
    monkeypatch.setattr(io, "_INPUT_HASHES", {})
    (data / "in.parquet").write_bytes(b"v2")
    assert cli.stale_tables().inputs_changed == ["m/t.csv"]

    del meta["code_sha256"]
    side.write_text(json.dumps(meta))
    st = cli.stale_tables()
    assert st.unhashed == ["m/t.csv"] and st.stale == []


def test_committed_sidecars_carry_current_code_hash():
    """Strict: every committed table sidecar has a code_sha256 equal to the current code of its
    module (and the modules it imports).  Fails until every module is re-run from the commit
    being checked; the fix is `uv run nhtsa analyze` (see `uv run nhtsa status`)."""
    if not list(config.TABLES_DIR.rglob("*.json")):
        return
    st = cli.stale_tables()
    problems = [f"no code_sha256: {t}" for t in st.unhashed] + [
        f"stale (code changed): {t}" for t in st.stale
    ]
    assert not problems, f"{len(problems)} of {st.n_checked} outputs:\n" + "\n".join(problems)
