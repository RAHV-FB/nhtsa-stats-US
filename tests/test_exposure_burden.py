"""Culpability coding, QIE identity, burden and app prediction helpers (synthetic data)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import polars as pl
import pytest

from nhtsa_stats.analysis import exposure
from nhtsa_stats.analysis.survey import ModelSpec, SurveyDesign, SurveyLogit


def test_culpability_codes():
    codes = pl.DataFrame({"c": [0, 4, 7, 8, 46, 58, 71, 98, 99, 95]})
    out = codes.select(exposure.culpability(pl.col("c")).alias("x"))["x"].to_list()
    # 0 none -> 0; 4/46/58/98 moving -> 1; 7/8 post-crash -> 0; 71 licence (non-moving) -> 0; 99/95 unknown -> null
    assert out == [0, 1, 0, 0, 1, 1, 0, 1, None, None]


def test_rir_equals_within_group_odds_in_one_to_one_pairs():
    # Two drivers per crash, exactly one culpable: RIR_g = culpable share / non-culpable share = odds within g.
    rng = np.random.default_rng(0)
    n_crash = 4000
    young_culp = rng.random(n_crash) < 0.3
    young_non = rng.random(n_crash) < 0.15
    df = pd.DataFrame(
        {
            "group": np.r_[
                np.where(young_culp, "young", "other"), np.where(young_non, "young", "other")
            ],
            "culpable": np.r_[np.ones(n_crash), np.zeros(n_crash)],
        }
    )
    crash = np.r_[np.arange(n_crash), np.arange(n_crash)]
    design = SurveyDesign.from_arrays(np.ones(2 * n_crash), None, crash)
    m = SurveyLogit(ModelSpec(categorical={"group": ["other", "young"]})).fit(
        df, df["culpable"].to_numpy(), design
    )
    ms = m.margins(df, {"young": lambda d: d.assign(group="young")})
    p = ms.values["young"]
    rir = young_culp.mean() / young_non.mean()
    assert p / (1 - p) == pytest.approx(rir, rel=1e-6)


def test_app_prediction_matches_model():
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
    pytest.importorskip("streamlit")
    from views.severity_model import predict

    rng = np.random.default_rng(1)
    n = 3000
    df = pd.DataFrame({"a": rng.choice(["no", "yes"], n)})
    y = (rng.random(n) < np.where(df["a"] == "yes", 0.2, 0.05)).astype(float)
    spec = ModelSpec(categorical={"a": ["no", "yes"]})
    m = SurveyLogit(spec).fit(df, y, SurveyDesign.from_arrays(np.ones(n), None, None))
    model = {
        "levels": spec.categorical,
        "terms": m.names_,
        "coef": m.coef_.tolist(),
        "vcov": m.vcov_.tolist(),
        "design_df": 100,
    }
    p, lo, hi = predict(model, {"a": "yes"})
    assert p == pytest.approx(y[df["a"] == "yes"].mean(), rel=1e-6)
    assert lo < p < hi
