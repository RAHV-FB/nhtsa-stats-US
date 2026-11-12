"""Source hashes in table sidecars: helpers, and staleness of the committed sidecars."""

from __future__ import annotations

import hashlib
import json

import pandas as pd

from nhtsa_stats import cli, config
from nhtsa_stats.reporting import io


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


def test_save_table_records_hashes_and_status_flags_stale(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "TABLES_DIR", tmp_path)
    ns = {"__name__": "nhtsa_stats.reporting.io", "io": io, "df": pd.DataFrame({"a": [1]})}
    exec("def write():\n    io.save_table(df, 'm', 't', description='d')\n", ns)
    ns["write"]()
    side = tmp_path / "m" / "t.json"
    meta = json.loads(side.read_text())
    assert meta["source_sha256"] == io.module_source_sha256("nhtsa_stats.reporting.io")
    assert meta["package_sha256"] == io.package_sha256()
    assert cli.stale_tables() == ([], [], 1)
    meta["source_sha256"] = "0" * 64
    side.write_text(json.dumps(meta))
    assert cli.stale_tables() == (["m/t.csv"], [], 1)
    del meta["source_sha256"]
    side.write_text(json.dumps(meta))
    assert cli.stale_tables() == ([], ["m/t.csv"], 1)


def test_committed_sidecars_match_current_module_source():
    sidecars = sorted(config.TABLES_DIR.rglob("*.json"))
    if not sidecars:
        return
    stale, unhashed, n = cli.stale_tables()
    if unhashed:
        print(f"{len(unhashed)} of {n} sidecars have no source_sha256 (set at the next full run)")
    assert not stale, "tables older than their producing module:\n" + "\n".join(stale)
