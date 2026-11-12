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
    monkeypatch.setattr(cli, "stale_tables", lambda: (["a/b.csv"], ["c/d.csv"], 2))
    cli.main(["status"])
    out = capsys.readouterr().out
    assert "1 stale" in out and "stale     a/b.csv" in out and "no-hash   c/d.csv" in out
