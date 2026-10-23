"""Leakage gate of the pedestrian / cyclist models (synthetic frames, no data needed)."""

from __future__ import annotations

import pandas as pd
import pytest

from nhtsa_stats.analysis import vulnerable as v


def test_covariates_pass_leakage_gate():
    df = pd.DataFrame({c: [v.LEVELS[c][0]] for c in v.COVARIATES})
    spec = v._spec(df, v.COVARIATES)
    assert set(spec.categorical) == set(v.COVARIATES)


def test_derived_regroupings_are_gated_through_their_source(monkeypatch):
    monkeypatch.setitem(v.LEVELS, "speed_grp", ["<=35", "40+", "unknown"])
    monkeypatch.setitem(v.LEVELS, "light_truck", ["no", "yes", "other"])
    df = pd.DataFrame({"speed_grp": ["<=35", "40+"], "light_truck": ["no", "yes"]})
    spec = v._spec(df, ["speed_grp", "light_truck"], interactions=[("light_truck", "speed_grp")])
    assert spec.interactions == [("light_truck", "speed_grp")]


def test_post_crash_feature_rejected(monkeypatch):
    monkeypatch.setitem(v.LEVELS, "hit_and_run", ["no", "yes"])
    df = pd.DataFrame({"hit_and_run": ["no", "yes"]})
    with pytest.raises(ValueError, match="not permitted"):
        v._spec(df, ["hit_and_run"])
