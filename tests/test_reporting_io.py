"""Provenance sidecars written by save_table."""

from __future__ import annotations

import json

import pandas as pd

from nhtsa_stats import config
from nhtsa_stats.reporting import io


def test_sidecar_names_the_calling_module(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "TABLES_DIR", tmp_path)
    df = pd.DataFrame({"a": [1]})
    # Called from outside the package: the module defaults to the analysis namespace.
    io.save_table(df, "m", "outside", description="d")
    meta = json.loads((tmp_path / "m" / "outside.json").read_text())
    assert meta["module"] == "nhtsa_stats.analysis.m"
    # Called from a package module (simulated): that module is recorded.
    ns = {"__name__": "nhtsa_stats.models.example", "io": io, "df": df}
    exec("def write():\n    io.save_table(df, 'm', 'inside', description='d')\n", ns)
    ns["write"]()
    meta = json.loads((tmp_path / "m" / "inside.json").read_text())
    assert meta["module"] == "nhtsa_stats.models.example"
