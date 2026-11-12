"""Command-line entry point: analysis modules always run in dependency order."""

from __future__ import annotations

import argparse
import sys
import types

from nhtsa_stats import cli


def test_named_modules_run_in_dependency_order(monkeypatch):
    ran = []
    fake = {}
    for name in ("first", "second", "third"):
        mod = types.ModuleType(f"fake_{name}")
        mod.run = lambda name=name: ran.append(name)
        monkeypatch.setitem(sys.modules, f"fake_{name}", mod)
        fake[name] = f"fake_{name}"
    monkeypatch.setattr(cli, "ANALYSES", fake)
    cli.cmd_analyze(argparse.Namespace(modules=["third", "first"]))
    assert ran == ["first", "third"]
    ran.clear()
    cli.cmd_analyze(argparse.Namespace(modules=[]))
    assert ran == ["first", "second", "third"]


def test_status_command_registered(capsys, monkeypatch):
    status = cli.TableStatus(["a/b.csv"], ["c/d.csv"], ["e/f.csv"], 3)
    monkeypatch.setattr(cli, "stale_tables", lambda: status)
    cli.main(["status"])
    out = capsys.readouterr().out
    assert "1 stale" in out and "1 without code_sha256" in out and "1 with changed input" in out
    for line in ("stale          a/b.csv", "no-hash        c/d.csv", "inputs-changed e/f.csv"):
        assert line in out
