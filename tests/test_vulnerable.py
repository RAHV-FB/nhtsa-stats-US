"""Leakage gate of the pedestrian / cyclist models (synthetic frames, no data needed)."""

from __future__ import annotations

import numpy as np
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


def _toy_nonmotorists(monkeypatch, n=6000, seed=11):
    """Synthetic struck pedestrians: the speed limit is far more often unknown when not killed."""
    from nhtsa_stats.analysis.survey import SurveyDesign

    rng = np.random.default_rng(seed)
    killed = (rng.random(n) < 0.1).astype(float)
    unknown = rng.random(n) < np.where(killed == 1, 0.1, 0.3)
    limit = np.where(unknown, "unknown", rng.choice(["<=25", "30-35", "50-55"], n))
    df = pd.DataFrame({"killed": killed, "str_speed_limit": limit})
    stratum = rng.integers(0, 4, n)
    design = SurveyDesign.from_arrays(
        rng.uniform(1, 3, n), stratum, stratum * 10 + rng.integers(0, 3, n)
    )
    monkeypatch.setattr(v, "load", lambda victim, outcome: (df.copy(), design))
    return df, design


def test_speed_limit_missingness_shares_difference_and_ratio(monkeypatch):
    df, design = _toy_nonmotorists(monkeypatch)
    out = v.speed_limit_missingness("pedestrian", "killed").set_index("group")
    w = design.weight
    unk = (df["str_speed_limit"] == "unknown").to_numpy()
    for grp, mask in (("fatal / outcome", df["killed"] == 1), ("not", df["killed"] == 0)):
        m = mask.to_numpy()
        assert out.loc[grp, "estimate"] == pytest.approx(np.average(unk[m], weights=w[m]))
        assert out.loc[grp, "low"] < out.loc[grp, "estimate"] < out.loc[grp, "high"]
        assert out.loc[grp, "n_unknown"] == unk[m].sum()
    diff, ratio = out.loc["outcome minus not"], out.loc["outcome over not"]
    assert diff["estimate"] == pytest.approx(
        out.loc["fatal / outcome", "estimate"] - out.loc["not", "estimate"]
    )
    assert ratio["estimate"] == pytest.approx(
        out.loc["fatal / outcome", "estimate"] / out.loc["not", "estimate"]
    )
    # Fatal cases have the limit unknown less often: both intervals exclude "no difference".
    assert diff["high"] < 0 and ratio["high"] < 1


def test_speed_limit_adjustment_specs_drop_only_named_covariates():
    assert v.SPEED_SPECS["full (published)"] == ()
    assert set(v.SPEED_SPECS["without location, light and time of day"]) == {
        "location",
        "light",
        "tod",
    }
    for drop in v.SPEED_SPECS.values():
        assert set(drop) <= set(v.COVARIATES)
        assert "str_speed_limit" not in drop
