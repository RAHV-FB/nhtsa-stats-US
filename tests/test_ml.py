"""Severity-prediction module (RQ8): software tests on synthetic data, plus a real-data smoke
test.  Synthetic data here test the code only and are never findings."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, roc_auc_score

from nhtsa_stats import config
from nhtsa_stats.analysis.survey import ModelSpec, SurveyDesign, SurveyLogit, svy_mean
from nhtsa_stats.models import severity_ml as ml


# --------------------------------------------------------------------------------------
# Leakage control
# --------------------------------------------------------------------------------------
@pytest.mark.parametrize("stage", list(ml.STAGES))
def test_stage_features_pass_registry(stage):
    feats = ml.stage_features(stage)
    ml.check_features(feats, stage)  # raises on leakage
    for forbidden in ("YEAR", "hit_and_run", "fatal", "ka", "n_killed", "STRATUM", "WEIGHT"):
        assert forbidden not in feats
    assert not [f for f in feats if f.endswith("_IM")]


@pytest.mark.parametrize(
    "bad",
    [
        "hit_and_run",
        "n_killed",
        "YEAR",
        "MAXSEV_IM",
        "NUM_INJ",
        "MAX_SEV",
        "STRATUM",
        "kabco",
        "ejected",
        "rollover_any",
        "towed_any",
        "not_a_registered_variable",
    ],
)
def test_check_features_rejects_leaky_inputs(bad):
    with pytest.raises(ValueError):
        ml.check_features(
            [*ml.stage_features("pre_crash+circumstance"), bad], "pre_crash+circumstance"
        )


def test_pre_crash_stage_rejects_crash_configuration():
    with pytest.raises(ValueError):
        ml.check_features([*ml.stage_features("pre_crash"), "crash_type"], "pre_crash")
    assert "crash_type" not in ml.stage_features("pre_crash")
    assert "crash_type" in ml.stage_features("pre_crash+circumstance")


def test_stage_products_respect_stage_features():
    pre = ml.stage_products("pre_crash")
    full = ml.stage_products("pre_crash+circumstance")
    assert all(var in ml.STAGES["pre_crash"] for _, term in pre for var, _ in term)
    assert len(full) > len(pre)
    assert any("pedestrian" in name for name, _ in full)
    assert not any("pedestrian" in name for name, _ in pre)


# --------------------------------------------------------------------------------------
# Metrics
# --------------------------------------------------------------------------------------
def _scores(n: int = 5000, seed: int = 0):
    rng = np.random.default_rng(seed)
    p = np.round(rng.beta(0.5, 8, n), 3)  # rounding creates ties
    y = (rng.random(n) < p).astype(float)
    w = rng.uniform(0.5, 30, n)
    return p, y, w


def test_weighted_metrics_match_sklearn():
    p, y, w = _scores()
    m = ml._point_metrics(p, y, w)
    assert m["auroc"] == pytest.approx(roc_auc_score(y, p, sample_weight=w), abs=1e-12)
    assert m["average_precision"] == pytest.approx(
        average_precision_score(y, p, sample_weight=w), abs=1e-12
    )
    assert m["brier"] == pytest.approx(brier_score_loss(y, p, sample_weight=w), rel=1e-10)
    assert m["log_loss"] == pytest.approx(
        log_loss(y, np.clip(p, ml.EPS, 1 - ml.EPS), sample_weight=w), rel=1e-9
    )
    prev = np.average(y, weights=w)
    assert m["prevalence"] == pytest.approx(prev)
    assert m["brier_skill"] == pytest.approx(1 - m["brier"] / (prev * (1 - prev)))
    assert m["oe_ratio"] == pytest.approx((w * y).sum() / (w * p).sum())


def test_grid_grouping_changes_metrics_negligibly():
    p, y, w = _scores(seed=1)
    p = np.clip(p + np.random.default_rng(2).normal(0, 1e-4, len(p)), 1e-4, 1)
    cl = np.zeros(len(p), dtype=np.int64)
    exact = ml.GroupedScores(p, y, w, cl, 1).metrics()
    grid = ml.GroupedScores(p, y, w, cl, 1, resolution=ml.BOOT_RESOLUTION).metrics()
    for k in ("auroc", "average_precision", "brier", "log_loss", "calibration_slope"):
        assert grid[k][0] == pytest.approx(exact[k][0], rel=2e-3, abs=2e-4)


def test_calibration_slope_and_intercept():
    rng = np.random.default_rng(3)
    eta = rng.normal(-3, 1.2, 200_000)
    p = 1 / (1 + np.exp(-eta))
    y = (rng.random(len(p)) < p).astype(float)
    w = np.ones(len(p))
    good = ml._point_metrics(p, y, w)
    assert good["calibration_slope"] == pytest.approx(1, abs=0.03)
    assert good["calibration_intercept"] == pytest.approx(0, abs=0.1)
    assert good["calibration_in_the_large"] == pytest.approx(0, abs=0.03)
    # Over-confident predictions (logit doubled) -> slope about 1/2.
    over = 1 / (1 + np.exp(-(2 * eta + 3)))
    assert ml._point_metrics(over, y, w)["calibration_slope"] == pytest.approx(0.5, abs=0.03)


def test_weighted_quantile():
    x = np.array([1.0, 2.0, 3.0, 4.0])
    w = np.array([1.0, 1.0, 1.0, 7.0])
    assert ml.weighted_quantile(x, w, 0.5)[0] == 4.0
    assert ml.weighted_quantile(x, w, 0.2)[0] == 2.0


# --------------------------------------------------------------------------------------
# Cluster bootstrap
# --------------------------------------------------------------------------------------
def test_rao_wu_multipliers_structure():
    cl_stratum = np.array([0, 0, 1, 1, 1, 2])
    mult = ml.rao_wu_multipliers(cl_stratum, 500, np.random.default_rng(0))
    assert mult.shape == (500, 6)
    # n_h = 2: one cluster drawn, multiplier 2 (= 1 * 2/1), the other 0.
    assert set(np.unique(mult[:, :2])) <= {0.0, 2.0}
    np.testing.assert_allclose(mult[:, :2].sum(1), 2.0)
    # n_h = 3: two draws, multipliers in {0, 1.5, 3}, summing to 3.
    np.testing.assert_allclose(mult[:, 2:5].sum(1), 3.0)
    # single-cluster stratum: no variance contribution.
    np.testing.assert_allclose(mult[:, 5], 1.0)
    assert mult.mean() == pytest.approx(1.0, abs=0.05)


def test_rao_wu_bootstrap_reproduces_taylor_variance():
    """Bootstrap SE of a weighted proportion ~ the design-based linearised SE."""
    rng = np.random.default_rng(4)
    n_strata, per = 12, 3
    rows = []
    for s in range(n_strata):
        for c in range(per):
            k = rng.integers(200, 400)
            base = rng.normal(-1.5, 0.6)  # cluster effect -> intra-cluster correlation
            y = (rng.random(k) < 1 / (1 + np.exp(-base))).astype(float)
            rows.append(pd.DataFrame({"s": s, "c": c, "y": y, "w": rng.uniform(1, 5, k)}))
    df = pd.concat(rows, ignore_index=True)
    design = SurveyDesign.from_frame(df, weight="w", strata="s", cluster="c")
    taylor = svy_mean(design, df["y"].to_numpy()).se
    cidx, cl_stratum = ml.cluster_index(df["s"].to_numpy(), df["c"].to_numpy())
    mult = ml.rao_wu_multipliers(cl_stratum, 3000, np.random.default_rng(5))
    wy = np.bincount(cidx, weights=df["w"] * df["y"])
    ww = np.bincount(cidx, weights=df["w"])
    boot = (mult @ wy) / (mult @ ww)
    assert boot.std(ddof=1) == pytest.approx(taylor, rel=0.1)


# --------------------------------------------------------------------------------------
# Preprocessing and estimators
# --------------------------------------------------------------------------------------
def _synthetic_crashes(n: int = 6000, seed: int = 0) -> pd.DataFrame:
    """Random crashes with every model feature (declared levels only)."""
    rng = np.random.default_rng(seed)
    df = pd.DataFrame(
        {c: rng.choice(ml.ALL_LEVELS[c], n) for c in ml.STAGES["pre_crash+circumstance"]}
    )
    for c in ml.STAGES["pre_crash+circumstance"]:  # make sure the reference level is present
        df.loc[: len(ml.ALL_LEVELS[c]) - 1, c] = ml.ALL_LEVELS[c]
    df["speed_limit_mph"] = np.where(rng.random(n) < 0.1, np.nan, rng.integers(2, 15, n) * 5.0)
    df["oldest_vehicle_age"] = np.where(rng.random(n) < 0.05, np.nan, rng.integers(0, 25, n) * 1.0)
    eta = (
        -3.5
        + 1.2 * (df["crash_type"] == "pedestrian")
        + 0.8 * (df["speeding"] == "yes")
        + 0.03 * df["oldest_vehicle_age"].fillna(10)
    )
    df["fatal"] = (rng.random(n) < 1 / (1 + np.exp(-eta))).astype(float)
    df["WEIGHT"] = rng.uniform(5, 200, n)
    df["PSUSTRAT"] = rng.integers(0, 8, n)
    df["PSU_VAR"] = df["PSUSTRAT"] * 10 + rng.integers(0, 3, n)
    return df


def test_preprocessor_is_fitted_on_training_rows_only():
    df = _synthetic_crashes()
    train = df.iloc[:3000].copy()
    train.loc[train["weather"] == "fog", "weather"] = "clear"  # 'fog' absent in training
    test = df.iloc[3000:]
    pre = ml.Preprocessor(list(ml.STAGES["pre_crash"])).fit(train)
    assert "fog" not in pre.levels_["weather"]
    assert pre.unseen(test) == {"weather": ["fog"]}
    assert pre.impute_["speed_limit_mph"] == np.nanmedian(train["speed_limit_mph"])
    x = pre.onehot(test)
    fog = (test["weather"] == "fog").to_numpy()
    cols = [i for i, n in enumerate(pre.onehot_names_) if n.startswith("weather[")]
    assert np.all(x[np.ix_(fog, cols)] == 0)  # unseen -> no dummy switched on
    codes = pre.ordinal(test)
    assert np.isnan(codes[fog, pre.categorical.index("weather")]).all()
    assert x.shape[1] == len(pre.onehot_names_)


def test_sklearn_logistic_equals_survey_logit():
    """The weighted sklearn fit (C=100) is the survey pseudo-ML estimator with ridge 0.01, and
    logistic_vcov reproduces SurveyLogit's design-based covariance."""
    df = _synthetic_crashes(8000, seed=1)
    cats = ["crash_type", "speeding", "light"]
    pre = ml.Preprocessor(cats, numeric=[]).fit(df)
    model = ml.fit_logistic(pre, df, "fatal", ml.RIDGE_C, "logit_main", "pre_crash+circumstance")
    design = SurveyDesign.from_frame(df, weight="WEIGHT", strata="PSUSTRAT", cluster="PSU_VAR")
    spec = ModelSpec(categorical={c: pre.levels_[c] for c in cats})
    sv = SurveyLogit(spec, ridge=1 / ml.RIDGE_C).fit(df, df["fatal"].to_numpy(), design)
    beta = np.r_[model.estimator.intercept_, model.estimator.coef_.ravel()]
    np.testing.assert_allclose(beta, sv.coef_, atol=2e-4)
    v = ml.logistic_vcov(model, df, design)
    np.testing.assert_allclose(np.sqrt(np.diag(v)), np.sqrt(np.diag(sv.vcov_)), rtol=2e-3)


def test_holm():
    adj = ml.holm(np.array([0.01, 0.04, 0.03]))
    np.testing.assert_allclose(adj, [0.03, 0.06, 0.06])


# --------------------------------------------------------------------------------------
# Interface prediction
# --------------------------------------------------------------------------------------
@pytest.fixture(scope="module")
def tiny_bundle():
    df = _synthetic_crashes(6000, seed=2)
    design = SurveyDesign.from_frame(df, weight="WEIGHT", strata="PSUSTRAT", cluster="PSU_VAR")
    stages = {}
    for stage in ml.STAGES:
        pre = ml.Preprocessor(list(ml.STAGES[stage])).fit(df)
        lm = ml.fit_logistic(pre, df, "fatal", ml.RIDGE_C, "logit_main", stage)
        vc = ml.logistic_vcov(lm, df, design)
        stages[stage] = {
            "model": lm,
            "interval": {"kind": "delta", "vcov": vc},
            "logit_main": lm,
            "logit_main_vcov": vc,
            "others": {},
            "baseline": float(lm.predict(df).mean()),
            "test_performance": {},
        }
    return {
        "outcome": "fatal",
        "stages": stages,
        "features": {s: ml.stage_features(s) for s in ml.STAGES},
        "reference": df[ml.stage_features("pre_crash+circumstance")].iloc[:500],
        "design_df": design.df,
        "population": "synthetic",
    }


def test_predict_refuses_unseen_and_invalid_inputs(tiny_bundle):
    f = ml.predict_crash_fatal_risk
    assert f({"crash_type": "spaceship"}, bundle=tiny_bundle)["status"] == "refused"
    r = f({"weather": "volcanic_ash"}, bundle=tiny_bundle)
    assert r["status"] == "refused"
    assert "clear" in r["allowed_values"]["weather"]
    assert f({"hit_and_run": "yes"}, bundle=tiny_bundle)["status"] == "refused"
    assert f({"YEAR": 2024}, bundle=tiny_bundle)["status"] == "refused"
    assert f({"oldest_vehicle_age": 500}, bundle=tiny_bundle)["status"] == "refused"
    assert f({"speed_limit_mph": "fast"}, bundle=tiny_bundle)["status"] == "refused"
    inconsistent = {"speed_limit": "30-35", "speed_limit_mph": 65}
    assert f(inconsistent, bundle=tiny_bundle)["status"] == "refused"
    assert f({"crash_type": "pedestrian"}, stage="pre_crash", bundle=tiny_bundle)["status"] == (
        "refused"
    )
    assert f("not a dict", bundle=tiny_bundle)["status"] == "refused"


def test_predict_returns_probability_interval_and_labels(tiny_bundle):
    f = ml.predict_crash_fatal_risk
    r = f({"crash_type": "pedestrian", "speeding": True, "speed_limit_mph": 45}, bundle=tiny_bundle)
    assert r["status"] == "ok"
    assert r["stage"] == "pre_crash+circumstance"
    assert 0 < r["ci_low"] < r["probability"] < r["ci_high"] < 1
    assert r["conditions_used"]["speed_limit"] == "40-45"
    assert r["conditions_used"]["speeding"] == "yes"
    assert "crash_type" not in r["marginalized_over"]
    assert "weather" in r["marginalized_over"]
    assert "model-predicted" in r["label"]
    assert "not the probability of having a crash" in r["caveat"]
    low = f({"crash_type": "mv_rear_end", "speeding": "no"}, bundle=tiny_bundle)
    assert low["probability"] < r["probability"]
    pre = f({"speeding": "yes"}, bundle=tiny_bundle)
    assert pre["stage"] == "pre_crash"


def test_figures_render_from_tables(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "FIGURES_DIR", tmp_path)
    rng = np.random.default_rng(0)
    curves, metrics, temporal, imp, pdp, ice = [], [], [], [], [], []
    for o in ml.OUTCOMES:
        for s in ml.STAGES:
            for m in ml.MODEL_NAMES:
                for wt in ("weighted", "unweighted"):
                    for b in range(1, 21):
                        curves.append(
                            dict(
                                outcome=o,
                                stage=s,
                                model=m,
                                weighting=wt,
                                bin=b,
                                mean_predicted=b / 1000,
                                observed_rate=b / 900,
                            )
                        )
                for met in ("auroc", "brier_skill"):
                    metrics.append(
                        dict(
                            outcome=o,
                            stage=s,
                            model=m,
                            domain="all",
                            weighting="weighted",
                            metric=met,
                            estimate=0.5,
                            ci_low=0.4,
                            ci_high=0.6,
                        )
                    )
            for m in ("logit_main", "hgb"):
                for yr in range(2020, 2025):
                    for met in ("auroc", "oe_ratio"):
                        temporal.append(
                            dict(
                                outcome=o,
                                stage=s,
                                model=m,
                                eval_year=yr,
                                metric=met,
                                estimate=1.0,
                                ci_low=0.9,
                                ci_high=1.1,
                            )
                        )
    for s in ml.STAGES:
        for m in ("logit_main", "hgb"):
            for feat in ml.interpretation_features(s):
                imp.append(dict(stage=s, model=m, feature=feat, log_loss_increase_pct=rng.random()))
    feats = ["crash_type", "speed_limit", "oldest_vehicle_age"]
    for m in ("logit_main", "logit_interact", "hgb"):
        for v in ml.ALL_LEVELS["crash_type"]:
            pdp.append(
                dict(
                    stage="pre_crash+circumstance",
                    model=m,
                    feature="crash_type",
                    value=v,
                    pd_probability=0.01,
                )
            )
        for v in [*range(15, 80, 5), "unknown"]:
            pdp.append(
                dict(
                    stage="pre_crash+circumstance",
                    model=m,
                    feature="speed_limit",
                    value=v,
                    pd_probability=0.01,
                )
            )
        for v in [*range(0, 31, 2), "unknown"]:
            pdp.append(
                dict(
                    stage="pre_crash+circumstance",
                    model=m,
                    feature="oldest_vehicle_age",
                    value=v,
                    pd_probability=0.01,
                )
            )
    for v in range(0, 31, 2):
        ice.append(
            dict(
                stage="pre_crash+circumstance",
                model="hgb",
                feature="oldest_vehicle_age",
                value=v,
                row=0,
                probability=0.01,
            )
        )
        ice.append(
            dict(
                stage="pre_crash+circumstance",
                model="hgb",
                feature="speed_limit",
                value=15 + v,
                row=0,
                probability=0.01,
            )
        )
    ml._figures(
        pd.DataFrame(curves),
        pd.DataFrame(metrics),
        pd.DataFrame(temporal),
        pd.DataFrame(imp),
        pd.DataFrame(pdp),
        pd.DataFrame(ice),
        feats,
    )
    names = {p.name for p in (tmp_path / ml.MODULE).iterdir()}
    assert {
        "calibration_fatal.png",
        "model_comparison.png",
        "partial_dependence_fatal.png",
        "permutation_importance_fatal.png",
        "temporal_stability_ka.png",
    } <= names


# --------------------------------------------------------------------------------------
# Real data (smoke)
# --------------------------------------------------------------------------------------
@pytest.mark.processed
def test_real_data_smoke():
    df = ml.load_crashes()
    # Outcomes follow the project definition: MAXSEV_IM 4 vs 0-3; 5/6/8 unknown.
    assert set(df["fatal"].dropna().unique()) <= {0.0, 1.0}
    assert df.loc[df["MAXSEV_IM"] == 4, "fatal"].eq(1).all()
    assert df.loc[df["MAXSEV_IM"].isin([0, 1, 2, 3]), "fatal"].eq(0).all()
    assert df.loc[df["MAXSEV_IM"].isin([5, 6, 8]), "fatal"].isna().all()
    for stage in ml.STAGES:
        ml.check_features(ml.stage_features(stage), stage)
    known = df["fatal"].notna()
    train = df[df["YEAR"].isin(config.TRAIN_YEARS) & known].sample(40_000, random_state=0)
    test = df[(df["YEAR"] == 2023) & known]
    pre = ml.Preprocessor(list(ml.STAGES["pre_crash+circumstance"])).fit(train)
    m = ml.fit_logistic(pre, train, "fatal", ml.RIDGE_C, "logit_main", "pre_crash+circumstance")
    met = ml._point_metrics(m.predict(test), test["fatal"].to_numpy(), test["WEIGHT"].to_numpy())
    assert met["auroc"] > 0.8
    assert 0.5 < met["oe_ratio"] < 2
    bundle_path = ml.MODEL_DIR / "interface_fatal.joblib"
    if bundle_path.exists():
        r = ml.predict_crash_fatal_risk({"crash_type": "pedestrian", "light": "dark_not_lighted"})
        assert r["status"] == "ok"
        assert 0 < r["ci_low"] <= r["probability"] <= r["ci_high"] < 1
        assert ml.predict_crash_fatal_risk({"light": "purple"})["status"] == "refused"
