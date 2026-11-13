"""Code and input hashes in table sidecars: helpers, and staleness of the committed sidecars."""

from __future__ import annotations

import hashlib
import json

import pandas as pd
import pytest

from nhtsa_stats import cli, config
from nhtsa_stats.reporting import io, provenance


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


def _snap(root):
    return provenance.Snapshot(root, "tp")


def test_file_sha256(tmp_path):
    f = tmp_path / "a.py"
    f.write_bytes(b"x = 1\n")
    assert provenance.file_sha256(f) == hashlib.sha256(b"x = 1\n").hexdigest()


def test_real_snapshot_has_modules_and_raw_hash():
    snap = provenance.take_snapshot()
    name = "nhtsa_stats.reporting.io"
    assert snap.sources[name].path.name == "io.py"
    assert snap.source_sha256(name) == provenance.file_sha256(snap.sources[name].path)
    assert snap.source_sha256("nhtsa_stats.analysis.no_such_module") is None
    assert snap.code_sha256("nhtsa_stats.analysis.no_such_module") is None


def test_package_sha256_ignores_comments_but_not_code_or_paths(tmp_path):
    root = tmp_path / "tp"
    _make_pkg(root)
    base = _snap(root).package_sha256()
    assert base == _snap(root).package_sha256()
    (root / "util.py").write_text("# comment\nU = 1\n")
    assert _snap(root).package_sha256() == base
    (root / "util.py").write_text("U = 3\n")
    changed = _snap(root).package_sha256()
    assert changed != base
    (root / "util.py").rename(root / "util2.py")
    assert _snap(root).package_sha256() != changed


def test_module_closure_follows_relative_absolute_and_lazy_imports(tmp_path):
    root = tmp_path / "tp"
    _make_pkg(root)
    snap = _snap(root)
    assert snap.closure("tp.analysis.mod") == [
        "tp",
        "tp.analysis",
        "tp.analysis.helper",
        "tp.analysis.mod",
        "tp.other",
        "tp.util",
    ]
    assert snap.closure("tp.analysis.solo") == ["tp", "tp.analysis", "tp.analysis.solo"]
    assert snap.closure("tp.analysis.nope") == []


def test_code_sha256_changes_with_imported_helper_only_for_dependents(tmp_path):
    root = tmp_path / "tp"
    _make_pkg(root)
    s0 = _snap(root)
    mod, solo = s0.code_sha256("tp.analysis.mod"), s0.code_sha256("tp.analysis.solo")
    assert mod and solo and mod != solo
    assert s0.code_sha256("tp.analysis.nope") is None
    (root / "util.py").write_text("U = 2\n")  # transitive, lazy import
    s1 = _snap(root)
    assert s1.code_sha256("tp.analysis.mod") != mod
    assert s1.code_sha256("tp.analysis.solo") == solo
    (root / "analysis" / "mod.py").write_text(
        "from . import helper\nimport tp.other  # noqa\nZ = 1\n"
    )
    assert _snap(root).code_sha256("tp.analysis.mod") != s1.code_sha256("tp.analysis.mod")


def test_edit_after_snapshot_does_not_change_recorded_hash(tmp_path):
    root = tmp_path / "tp"
    _make_pkg(root)
    snap = _snap(root)
    before = snap.code_sha256("tp.analysis.mod")
    (root / "util.py").write_text("U = 99\n")  # edited while the run is in progress
    (root / "analysis" / "mod.py").write_text("raise SystemExit\n")
    assert snap.code_sha256("tp.analysis.mod") == before
    assert len(snap.closure("tp.analysis.mod")) == 6
    assert _snap(root).code_sha256("tp.analysis.mod") != before


def test_process_snapshot_is_taken_once(monkeypatch):
    monkeypatch.setattr(provenance, "_SNAPSHOT", None)
    first = provenance.take_snapshot()
    assert provenance.take_snapshot() is first
    assert provenance.current_code_sha256("nhtsa_stats.reporting.io") == first.code_sha256(
        "nhtsa_stats.reporting.io"
    )


def test_comment_and_docstring_edits_keep_digest_code_edits_change_it(tmp_path):
    root = tmp_path / "tp"
    _make_pkg(root)
    base = _snap(root).code_sha256("tp.analysis.helper")
    (root / "util.py").write_text('"""Doc."""\n# a comment\n\nU = 1  \n')
    assert _snap(root).code_sha256("tp.analysis.helper") == base
    (root / "analysis" / "helper.py").write_text(
        '"""Module doc."""\n\n\ndef f():\n    """Function doc."""\n    from tp import util  # c\n'
        "    return util.U\n"
    )
    assert _snap(root).code_sha256("tp.analysis.helper") == base
    (root / "util.py").write_text("U = 2\n")
    assert _snap(root).code_sha256("tp.analysis.helper") != base
    # a string literal that is not a docstring (e.g. sidecar method text) counts as code
    (root / "util.py").write_text("U = 1\nMETHOD = 'text'\n")
    with_text = _snap(root).code_sha256("tp.analysis.helper")
    (root / "util.py").write_text("U = 1\nMETHOD = 'other text'\n")
    assert _snap(root).code_sha256("tp.analysis.helper") != with_text


def _digest(src: str) -> str:
    return provenance.source_digest(src.encode())


_BASE = "def f(x):\n    if x:\n        y = 1\n    z = 'a'\n    return y + z\n"


def test_digest_ignores_comment_and_docstring_only_edits():
    base = _digest(_BASE)
    commented = (
        "# header\n"
        "def f(x):  # trailing\n"
        "    if x:\n"
        "        # inside\n"
        "        y = 1   \n"
        "\n"
        "    z = 'a'\n"
        "    return y + z\n"
    )
    assert _digest(commented) == base
    documented = (
        '"""Module doc."""\n'
        "def f(x):\n"
        '    """Function\n    doc with # hash."""\n'
        "    if x:\n"
        "        y = 1\n"
        "    z = 'a'\n"
        "    return y + z\n"
    )
    assert _digest(documented) == base
    cls = "class C:\n    '''Doc.'''\n    def m(self):\n        return 1\n"
    assert _digest(cls) == _digest("class C:\n    def m(self):\n        return 1\n")
    # non-ASCII text before a docstring on the same line (byte vs character offsets)
    assert provenance.canonical_source('x = "é"; """d"""\n'.encode()) == 'x = "é"; """d"""\n'
    assert provenance.canonical_source('def g():\n    """é"""\n    return "é"\n'.encode()) == (
        'def g():\n    return "é"\n'
    )


def test_digest_changes_with_code_string_and_indentation():
    base = _digest(_BASE)
    assert _digest(_BASE.replace("y + z", "y - z")) != base
    assert _digest(_BASE.replace("'a'", "'b'")) != base
    assert _digest(_BASE.replace("'a'", "'a '")) != base
    assert _digest(_BASE.replace("    z = 'a'\n", "        z = 'a'\n")) != base  # into
    nested = "def f(x):\n    if x:\n        y = 1\n        z = 2\n    return y\n"
    assert _digest(nested.replace("        z = 2", "    z = 2")) != _digest(nested)  # out of
    # a string that is not the first statement is code, not a docstring
    assert _digest("def f():\n    x = 1\n    'not a doc'\n") != _digest("def f():\n    x = 1\n")


def test_digest_of_fstrings_does_not_depend_on_tokenization():
    src = "name = 'a'\nmsg = f'{name!r:>{10}} # not a comment {name}'  # real comment\n"
    canon = provenance.canonical_source(src.encode())
    assert canon == "name = 'a'\nmsg = f'{name!r:>{10}} # not a comment {name}'\n"
    assert _digest(src) == hashlib.sha256(canon.encode()).hexdigest()
    assert _digest(src.replace("{name}", "{name.upper()}")) != _digest(src)


def test_canonical_source_exact_text_is_pinned():
    """Same text on every interpreter; a mismatch means digests would differ across Pythons."""
    src = (
        '"""Module doc."""\r\n'
        "# comment\n"
        "import os   \n"
        "\n"
        "\n"
        "class C:\n"
        '    """Doc\n'
        "    more.\n"
        '    """\n'
        "\n"
        "    X = f'{os.sep}\\u00e9 # in string'  # trailing\n"
        "\n"
        "    def m(self):\n"
        "        '''Method doc.'''\n"
        "        if self:\n"
        "            return 'caf\u00e9'\n"
        "        return (1,  # why\n"
        "                2)\n"
    )
    expected = (
        "import os\n"
        "class C:\n"
        "    X = f'{os.sep}\\u00e9 # in string'\n"
        "    def m(self):\n"
        "        if self:\n"
        "            return 'caf\u00e9'\n"
        "        return (1,\n"
        "                2)\n"
    )
    assert provenance.canonical_source(src.encode()) == expected
    assert _digest(src) == hashlib.sha256(expected.encode("utf-8")).hexdigest()


def test_syntax_and_decode_errors_raise(tmp_path):
    root = tmp_path / "tp"
    _make_pkg(root)
    (root / "util.py").write_text("def broken(:\n")
    snap = _snap(root)  # the snapshot itself succeeds; the closure that needs util raises
    assert snap.code_sha256("tp.analysis.solo")
    with pytest.raises(provenance.ProvenanceError, match=r"tp\.util"):
        snap.code_sha256("tp.analysis.mod")
    (root / "util.py").write_bytes(b"U = '\xff\xfe'\n# coding: utf-8\n")
    with pytest.raises(provenance.ProvenanceError):
        _snap(root).code_sha256("tp.analysis.mod")


def test_real_closure_has_lazy_imports_and_excludes_provenance():
    snap = provenance.take_snapshot()
    for mod in ("nhtsa_stats.analysis.severity", "nhtsa_stats.reporting.io"):
        closure = snap.closure(mod)
        assert mod in closure
        assert "nhtsa_stats.config" in closure
        assert "nhtsa_stats.reporting.provenance" not in closure
    assert "nhtsa_stats.reporting.io" in snap.closure("nhtsa_stats.analysis.severity")
    assert snap.closure("nhtsa_stats.reporting.provenance") == []


def test_toy_provenance_module_is_excluded(tmp_path):
    root = tmp_path / "tp"
    _make_pkg(root)
    (root / "reporting").mkdir()
    (root / "reporting" / "__init__.py").write_text("")
    (root / "reporting" / "provenance.py").write_text("P = 1\n")
    (root / "analysis" / "solo.py").write_text("from tp.reporting import provenance\n")
    snap = _snap(root)
    assert snap.closure("tp.analysis.solo") == [
        "tp",
        "tp.analysis",
        "tp.analysis.solo",
        "tp.reporting",
    ]
    before = snap.code_sha256("tp.analysis.solo")
    (root / "reporting" / "provenance.py").write_text("P = 2\n")
    assert _snap(root).code_sha256("tp.analysis.solo") == before


def test_input_sha256_files_dirs_and_globs(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path / "d")
    monkeypatch.setattr(config, "TABLES_DIR", tmp_path / "o" / "tables")
    monkeypatch.setattr(config, "OUTPUT_DIR", tmp_path / "o")
    monkeypatch.setattr(provenance, "_INPUT_HASHES", {})
    d = tmp_path / "d"
    (d / "sub").mkdir(parents=True)
    (d / "a.parquet").write_bytes(b"aaa")
    (d / "sub" / "b.bin").write_bytes(b"bbb")
    (tmp_path / "o" / "tables" / "m").mkdir(parents=True)
    (tmp_path / "o" / "tables" / "m" / "t.csv").write_bytes(b"x\n1\n")
    specs = [
        "data/a.parquet",
        "data/sub",
        "data/*.parquet",
        "outputs/tables/m/t.csv",
        "outputs/tables/m/*",
        "FARS person (text)",
        "data/missing",
        "outputs/tables/m/missing.csv",
    ]
    out = provenance.inputs_sha256(specs)
    assert set(out) == set(specs[:5])
    assert out["data/a.parquet"] != out["data/sub"]
    before = out["outputs/tables/m/t.csv"]
    (tmp_path / "o" / "tables" / "m" / "t.csv").write_bytes(b"x\n2\n")  # outputs are not cached
    assert provenance.input_sha256("outputs/tables/m/t.csv") != before


def test_cli_main_takes_the_snapshot_first(monkeypatch):
    monkeypatch.setattr(provenance, "_SNAPSHOT", None)
    cli.main(["list"])
    assert provenance._SNAPSHOT is not None


def test_declared_inputs_are_real_paths_and_cover_known_reads():
    """Descriptive strings in ``inputs`` are never hashed; a declared path must be a path."""
    import re
    from pathlib import Path

    src = Path(provenance.__file__).resolve().parents[1]
    bad = []
    for f in src.rglob("*.py"):
        for m in re.finditer(r'"((?:data|outputs)/[^"\n]*)"', f.read_text()):
            if "{" not in m.group(1) and re.match(
                r"(?:data|outputs)/[\w/.*]+ \(", m.group(1)
            ):  # "path (what we use)"
                bad.append(f"{f.name}: {m.group(1)}")
    assert not bad, bad
    from nhtsa_stats.analysis import burden, speeding
    from nhtsa_stats.simulation import baseline

    assert "data/processed/fars_driver.parquet" in speeding.INPUT
    assert "outputs/tables/severity/fatal_crude_vs_adjusted.csv" in baseline.ASSOCIATION_INPUTS
    assert (
        burden
    )  # imported for the bias_sensitivity inputs (outputs/tables/measurement/qba_grid.csv)


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
    monkeypatch.setattr(provenance, "_INPUT_HASHES", {})
    data = tmp_path / "proj" / "data"
    data.mkdir(parents=True)
    (data / "in.parquet").write_bytes(b"v1")
    monkeypatch.setattr(config, "DATA_DIR", data)
    side = _write("nhtsa_stats.reporting.io", tmp_path / "tables", monkeypatch, ["data/in.parquet"])
    meta = json.loads(side.read_text())
    snap = provenance.take_snapshot()
    code = snap.code_sha256("nhtsa_stats.reporting.io")
    assert meta["code_sha256"] == code
    assert meta["source_sha256"] == snap.source_sha256("nhtsa_stats.reporting.io")
    assert meta["package_sha256"] == snap.package_sha256()
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
    monkeypatch.setattr(provenance, "_INPUT_HASHES", {})
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
