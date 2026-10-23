"""Severity prediction for police-reported crashes with temporal validation (RQ8).

Research question (docs/research_plan.md, RQ8)
    How well can pre-crash and crash-circumstance information predict whether a
    police-reported crash is fatal (primary) or fatal-or-serious (KA, secondary), and do
    flexible models find structure that the main-effects logistic model misses?

Population
    CRSS police-reported crashes 2016-2024 (a national probability sample of crashes of
    every severity) with a determinable maximum severity (``MAXSEV_IM`` not 5/6/8).
    Temporal split: train 2016-2021, validation 2022 (tuning and threshold choice only),
    test 2023-2024 (never used for any choice).  ``YEAR`` is not a feature.
Unit
    Crash.
Outcomes
    ``fatal`` = MAXSEV_IM 4 (K) vs 0-3; ``ka`` = 3-4 vs 0-2: the processed CRSS outcomes
    (project definition v1.2: NHTSA-imputed maximum severity, whose weighted fatal totals
    reproduce FARS).  The strict complete-case versions (``fatal_cc``/``ka_cc``) are not
    modelled here; they are sensitivity outcomes of the inferential modules.
Features (leakage control)
    Only variables registered as ``pre_crash`` / ``crash_circumstance`` in
    ``processing.harmonize.REGISTRY`` (enforced with ``assert_no_leakage`` at run time and in
    tests).  Two stages: ``pre_crash`` (``specs.PRE_CRASH`` minus YEAR, plus the numeric
    speed limit and oldest-vehicle age with missing indicators) and
    ``pre_crash+circumstance`` (adds crash type and number of vehicles).  Explicitly
    excluded: ``hit_and_run`` (registered post-crash: leaving the scene), every outcome or
    outcome-derived count (fatal_cc, n_killed, n_ka, n_sev_unknown, NUM_INJ, MAX_SEV,
    MAXSEV_IM, kabco...), the sampling stratum ``STRATUM`` (assigned from injury severity),
    design variables and YEAR.  Tri-state flags enter as yes / no / unknown (unknown is never
    'no').  Encoders, imputers and scalers are fitted on the training years only.
    Proxy check: several 'unknown' levels (motorcycle / heavy-vehicle involvement, speeding,
    time of day) and a missing vehicle age occur mostly in hit-and-run crashes, so they can
    partly stand in for the excluded post-crash status.  The share is tabulated
    (``hit_and_run_proxy``), the evaluation is stratified by hit-and-run status (evaluation
    only, never a feature), and a "proxy-blind" refit, in which those unknowns are imputed
    from the weighted training marginal, bounds how much performance relies on the proxy.
    Imputation check: ``alcohol_im`` is NHTSA's imputation where police-reported alcohol is
    unknown; its fatal / non-fatal gradient among imputed records is tabulated
    (``alcohol_imputation_check``) because an imputation model that conditions on severity
    would carry outcome information into the input; the feature-set sensitivity refits with
    the police-reported field instead.
Models
    (1) logistic, main effects (tiny ridge, C=100, as in the survey models);
    (2) L2-regularised logistic, C tuned on 2022; (3) logistic + the pre-specified RQ2
    interaction products (``analysis.interactions.PAIRS``); (4) histogram gradient boosting
    (small grid tuned on 2022, early stopping on an internal split of the training years);
    (5) random forest (modest size).  All are fitted with survey weights as sample weights,
    so predicted probabilities refer to the population of police-reported crashes.
Evaluation
    On 2023-2024: AUROC, average precision vs prevalence, Brier and Brier skill score, log
    loss, calibration (reliability curve, calibration intercept/slope, calibration-in-the-
    large, observed/expected, expected calibration error, observed/expected within tiers of
    predicted risk), each weighted (population) and unweighted (sample); by year and
    subgroup; confusion matrices at thresholds fixed on 2022.
    Uncertainty: Rao-Wu rescaled bootstrap of variance PSUs (``PSU_VAR``) within strata
    (``PSUSTRAT``), >= 200 replicates, fixed seed; paired differences between models use the
    same replicates.  Temporal stability: models trained on 2016-2019, evaluated per year
    2020-2024.  Interpretation: weighted permutation importance on test, partial dependence /
    ICE, boosting-implied interactions for the pre-specified pairs, a Friedman-H screen for
    other interactions on 2022 data, and confirmatory survey-weighted (Taylor-linearised)
    tests of the screened patterns on the independent 2023-2024 data.
Model selection
    Pre-specified on 2022 (never on test): the simplest model, in the order
    logit_main < logit_l2 < logit_interact < hgb < rf, whose weighted 2022 log loss is within
    1% of the best and whose weighted AUROC is within 0.005 of the best.  Final models are
    those fitted on 2016-2021 (they are not refitted on 2022, so the test years evaluate
    exactly the saved models).
Interface
    ``predict_crash_fatal_risk(conditions)``: the selected model's predicted P(fatal) for a
    police-reported crash with the given recorded conditions, standardised over the weighted
    2023-2024 crash mix for every condition not given (structurally linked inputs -- crash
    type and vehicle count, speed-limit band and mph -- are drawn jointly so no impossible
    crash enters the average), with a 95% interval (design-based delta method for logistic
    models, PSU-bootstrap refits for boosting), the range across model classes, the
    population definition, flags (sparse levels, hit-and-run-proxy unknowns) and a caveat.
    Unseen category values, non-permitted inputs (e.g. YEAR, hit_and_run), numbers outside
    the training range and impossible configurations are refused.

Justified interpretation
    "Among police-reported crashes with these recorded circumstances, the model-predicted
    probability that the crash is fatal is p" (conditional risk stratification of reported
    crashes); "flexible models do / do not improve discrimination or calibration over a
    main-effects logistic model on later years"; screened patterns are hypotheses until the
    confirmatory survey analysis supports them.
Not justified
    Probability of crashing (exposure is not observed); causal effects of any feature;
    permutation importance or partial dependence as evidence of preventability; use of the
    model for individual enforcement or triage decisions.  Police-reported behaviours
    (speeding, alcohol) are ascertained more thoroughly in severe crashes, which can inflate
    their apparent predictive value.
"""

from __future__ import annotations

import copy
import logging
import os
import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

import joblib
import numpy as np
import pandas as pd
import polars as pl
from scipy import sparse, stats
from scipy.special import expit
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression

from nhtsa_stats import config
from nhtsa_stats.analysis import data, specs
from nhtsa_stats.analysis.interactions import PAIRS
from nhtsa_stats.analysis.survey import (
    ModelSpec,
    SurveyDesign,
    SurveyLogit,
    interaction_contrasts,
)
from nhtsa_stats.processing import harmonize as h
from nhtsa_stats.reporting.io import save_json, save_table

log = logging.getLogger(__name__)

MODULE = "ml"
MODULE_PATH = "nhtsa_stats.models.severity_ml"
MODEL_DIR = config.MODELS_DIR / MODULE
OUTCOMES: tuple[str, ...] = ("fatal", "ka")
OUTCOME_DEFINITIONS = {
    "fatal": "MAXSEV_IM 4 (K) vs 0-3 (O/C/B/A); 5/6/8 excluded",
    "ka": "MAXSEV_IM 3-4 (K or A) vs 0-2 (O/C/B); 5/6/8 excluded",
}
POPULATION = (
    "CRSS police-reported crashes (all severities, national probability sample) with a "
    "determinable maximum severity; train 2016-2021, validation 2022, test 2023-2024"
)
N_BOOT = 200
N_JOBS = 2
EPS = 1e-12
RIDGE_C = 100.0  # 1 / severity.RIDGE: tiny ridge for finite coefficients (weights mean 1)

# --------------------------------------------------------------------------------------
# Features and leakage control
# --------------------------------------------------------------------------------------
PRE_CRASH_CAT: list[str] = [v for v in specs.PRE_CRASH if v != "YEAR"]
CIRCUMSTANCE_CAT: list[str] = list(specs.CIRCUMSTANCE)
NUMERIC: list[str] = ["speed_limit_mph", "oldest_vehicle_age"]
STAGES: dict[str, list[str]] = {
    "pre_crash": PRE_CRASH_CAT,
    "pre_crash+circumstance": PRE_CRASH_CAT + CIRCUMSTANCE_CAT,
}
STAGE_TIMINGS: dict[str, set[str]] = {
    "pre_crash": {"pre_crash"},
    "pre_crash+circumstance": {"pre_crash", "crash_circumstance"},
}
TRI_COLS: list[str] = [c for c in specs.CRASH_TRI if c in PRE_CRASH_CAT]
# Derived columns that are not themselves in the registry, mapped to the registered variable
# they are computed from (same raw field, same timing).
FEATURE_SOURCE: dict[str, str] = {
    "speed_limit_mph": "speed_limit",  # VSPD_LIM in mph; the band is registered pre_crash
    "veh_age_band": "oldest_vehicle_age",
}
EXCLUDED: dict[str, str] = {
    "YEAR": "calendar year: not a feature under temporal validation",
    "hit_and_run": "registered post_crash: leaving the scene happens after the crash",
    "fatal": "outcome",
    "ka": "outcome",
    "injury": "outcome",
    "kabco": "outcome",
    "fatal_cc": "outcome (complete-case)",
    "ka_cc": "outcome (complete-case)",
    "fatal_im": "outcome",
    "ka_im": "outcome",
    "n_killed": "outcome count",
    "n_ka": "outcome count",
    "n_injured": "outcome count",
    "n_sev_unknown": "outcome-derived",
    "n_sev_injured_unknown": "outcome-derived",
    "NUM_INJ": "outcome count",
    "MAX_SEV": "outcome",
    "MAXSEV_IM": "outcome (imputed)",
    "STRATUM": "CRSS sampling stratum, assigned from injury severity",
    "WEIGHT": "design",
    "PSUSTRAT": "design",
    "PSU_VAR": "design",
    "PSU": "design",
    "PJ": "design",
    "case_id": "identifier",
    "rollover_any": "post-crash consequence",
    "fire_any": "post-crash consequence",
    "towed_any": "post-crash consequence",
}
MODEL_NAMES: tuple[str, ...] = ("logit_main", "logit_l2", "logit_interact", "hgb", "rf")
LOGISTIC_MODELS = ("logit_main", "logit_l2", "logit_interact")
MODEL_LABELS = {
    "logit_main": "Logistic, main effects",
    "logit_l2": "Logistic, L2 (C tuned)",
    "logit_interact": "Logistic + RQ2 interactions",
    "hgb": "Histogram gradient boosting",
    "rf": "Random forest",
}
L2_GRID = (1e-4, 1e-3, 1e-2, 1e-1, 1.0, 10.0)
HGB_GRID: tuple[dict[str, Any], ...] = tuple(
    {"learning_rate": lr, "max_leaf_nodes": mln, "min_samples_leaf": msl}
    for lr in (0.1,)
    for mln in (15, 31)
    for msl in (100, 400)
)
# Random forest: one modest configuration (CPU budget); it is a comparison model only.
RF_GRID: tuple[dict[str, Any], ...] = ({"min_samples_leaf": 50},)
SELECTION_LOGLOSS_TOL = 0.01  # relative
SELECTION_AUC_TOL = 0.005  # absolute
VEH_AGE_LEVELS = specs.PERSON_LEVELS["veh_age_band"]
ALL_LEVELS: dict[str, list] = {**specs.CRASH_LEVELS, "veh_age_band": VEH_AGE_LEVELS}


def stage_features(stage: str) -> list[str]:
    """All model inputs of a stage (categorical + numeric), as raw column names."""
    return [*STAGES[stage], *NUMERIC]


def check_features(features: Sequence[str], stage: str) -> None:
    """Raise unless every feature is permitted for ``stage`` (explicit exclusions + registry)."""
    bad = [f for f in features if f in EXCLUDED or f.endswith("_IM")]
    if bad:
        raise ValueError(f"explicitly excluded features in a severity model: {bad}")
    sources = [FEATURE_SOURCE.get(f, f) for f in features]
    h.assert_no_leakage(sources, allowed=STAGE_TIMINGS[stage])


def stage_products(stage: str) -> list[tuple[str, tuple[tuple[str, tuple], ...]]]:
    """Pre-specified RQ2 product terms whose variables are all available in ``stage``."""
    avail = set(STAGES[stage])
    out = []
    for comb in PAIRS:
        if comb.prespecified and all(e.var in avail for e in comb.exposures):
            out.append((comb.name, tuple((e.var, tuple(e.exposed)) for e in comb.exposures)))
    return out


# --------------------------------------------------------------------------------------
# Data
# --------------------------------------------------------------------------------------
def load_crashes() -> pd.DataFrame:
    """All CRSS crashes 2016-2024 with features, processed outcomes and design fields.

    Rows with an undeterminable severity keep NaN outcomes so that the survey design can be
    built from the full sample (correct domain variance) before subsetting.
    """
    path = config.PROCESSED_DIR / "crss_crash.parquet"
    if not path.exists():
        raise FileNotFoundError(f"{path} missing - run `nhtsa build` first")
    cols = [
        "YEAR",
        "case_id",
        "WEIGHT",
        "PSUSTRAT",
        "PSU_VAR",
        "MAXSEV_IM",  # kept only to verify the outcome definition (never a feature)
        *OUTCOMES,
        *PRE_CRASH_CAT,
        *CIRCUMSTANCE_CAT,
        *NUMERIC,
        "drugs",
        "distracted",
        "alcohol",
        "hit_and_run",  # post-crash: evaluation subgroups and proxy diagnostics only
    ]
    frame = (
        pl.read_parquet(path, columns=cols)
        .with_columns(h.vehicle_age_band("oldest_vehicle_age").alias("veh_age_band"))
        .to_pandas()
    )
    for c in [*TRI_COLS, "drugs", "distracted", "alcohol", "hit_and_run"]:
        frame[c] = data.tri_state(frame[c])
    for c in [*PRE_CRASH_CAT, *CIRCUMSTANCE_CAT, "veh_age_band"]:
        frame[c] = frame[c].astype(object)
    for c in [*NUMERIC, "fatal", "ka", "WEIGHT"]:
        frame[c] = frame[c].astype(float)
    frame["YEAR"] = frame["YEAR"].astype(int)
    frame["crash_family"] = (
        frame["crash_type"]
        .map(
            lambda t: (
                "pedestrian_cyclist"
                if t in ("pedestrian", "cyclist")
                else ("single_vehicle" if str(t).startswith("sv_") else "multi_vehicle")
            )
        )
        .astype(object)
    )
    return frame


def speed_band(mph: Sequence[float]) -> np.ndarray:
    """Speed-limit band of mph values with the shared harmonisation cut points."""
    vals = pl.DataFrame({"x": np.asarray(mph, dtype=float)}).with_columns(
        pl.col("x").fill_nan(None)
    )
    return vals.select(h.speed_limit_band("x")).to_series().to_numpy()


# --------------------------------------------------------------------------------------
# Preprocessing (fitted on training years only)
# --------------------------------------------------------------------------------------
@dataclass
class Preprocessor:
    """Training-fitted encoder: one-hot (reference = first declared level) for linear models,
    integer codes for boosting; numeric = training-median imputation + missing indicator
    (+ standardisation with training mean/SD in the one-hot design).  Values unseen in
    training become all-zero dummies / missing codes and are counted by :meth:`unseen`."""

    categorical: list[str]
    numeric: list[str] = field(default_factory=lambda: list(NUMERIC))
    products: list[tuple[str, tuple[tuple[str, tuple], ...]]] = field(default_factory=list)

    def fit(self, df: pd.DataFrame) -> Preprocessor:
        self.levels_: dict[str, list] = {}
        for c in self.categorical:
            present = set(pd.unique(df[c].astype(object)))
            declared = ALL_LEVELS[c]
            extra = present - set(declared)
            if extra:
                raise ValueError(f"{c}: undeclared levels in training data: {sorted(extra)}")
            if declared[0] not in present:
                raise ValueError(f"{c}: reference level {declared[0]!r} absent from training")
            self.levels_[c] = [lv for lv in declared if lv in present]
        self.impute_: dict[str, float] = {}
        self.center_: dict[str, float] = {}
        self.scale_: dict[str, float] = {}
        self.range_: dict[str, tuple[float, float]] = {}
        for c in self.numeric:
            v = df[c].to_numpy(dtype=float)
            med = float(np.nanmedian(v))
            filled = np.where(np.isnan(v), med, v)
            self.impute_[c] = med
            self.center_[c] = float(filled.mean())
            self.scale_[c] = float(filled.std()) or 1.0
            self.range_[c] = (float(np.nanmin(v)), float(np.nanmax(v)))
        names = [f"{c}[{lv}]" for c in self.categorical for lv in self.levels_[c][1:]]
        for c in self.numeric:
            names += [f"{c}(std)", f"{c}_missing"]
        names += [f"product:{name}" for name, _ in self.products]
        self.onehot_names_ = names
        self.ordinal_names_ = [*self.categorical] + [
            n for c in self.numeric for n in (c, f"{c}_missing")
        ]
        return self

    @property
    def categorical_mask(self) -> np.ndarray:
        return np.array([True] * len(self.categorical) + [False] * (2 * len(self.numeric)))

    def _codes(self, df: pd.DataFrame, c: str) -> np.ndarray:
        return pd.Index(self.levels_[c], dtype=object).get_indexer(df[c].astype(object))

    def _numeric(self, df: pd.DataFrame, c: str) -> tuple[np.ndarray, np.ndarray]:
        v = df[c].to_numpy(dtype=float)
        miss = np.isnan(v)
        return np.where(miss, self.impute_[c], v), miss

    def onehot(self, df: pd.DataFrame) -> np.ndarray:
        n = len(df)
        x = np.zeros((n, len(self.onehot_names_)))
        j = 0
        for c in self.categorical:
            codes = self._codes(df, c)
            rows = np.nonzero(codes > 0)[0]
            x[rows, j + codes[rows] - 1] = 1.0
            j += len(self.levels_[c]) - 1
        for c in self.numeric:
            v, miss = self._numeric(df, c)
            x[:, j] = (v - self.center_[c]) / self.scale_[c]
            x[:, j + 1] = miss
            j += 2
        for _, term in self.products:
            col = np.ones(n)
            for var, levels in term:
                col *= df[var].isin(list(levels)).to_numpy(dtype=float)
            x[:, j] = col
            j += 1
        return x

    def ordinal(self, df: pd.DataFrame) -> np.ndarray:
        cols = []
        for c in self.categorical:
            codes = self._codes(df, c).astype(float)
            codes[codes < 0] = np.nan
            cols.append(codes)
        for c in self.numeric:
            v, miss = self._numeric(df, c)
            cols += [v, miss.astype(float)]
        return np.column_stack(cols)

    def unseen(self, df: pd.DataFrame) -> dict[str, list]:
        out = {}
        for c in self.categorical:
            bad = sorted(set(pd.unique(df[c].astype(object))) - set(self.levels_[c]), key=str)
            if bad:
                out[c] = bad
        return out


@dataclass
class FittedModel:
    """A fitted estimator together with its (training-fitted) preprocessing."""

    name: str
    outcome: str
    stage: str
    pre: Preprocessor
    estimator: Any
    encoding: str  # "onehot" | "ordinal"
    params: dict = field(default_factory=dict)
    train_years: tuple[int, ...] = config.TRAIN_YEARS

    def matrix(self, df: pd.DataFrame) -> np.ndarray:
        return self.pre.onehot(df) if self.encoding == "onehot" else self.pre.ordinal(df)

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        return self.estimator.predict_proba(self.matrix(df))[:, 1]

    def predict_logit(self, df: pd.DataFrame) -> np.ndarray:
        p = np.clip(self.predict(df), 1e-9, 1 - 1e-9)
        return np.log(p / (1 - p))


# Newton-Cholesky (exact Newton steps; p << n here) converges in ~10 iterations to the same
# penalised pseudo-likelihood optimum as survey.SurveyLogit (tested), faster and more
# precisely than L-BFGS on levels with few events.
LOGIT_SOLVER: dict[str, Any] = {"solver": "newton-cholesky", "tol": 1e-8, "max_iter": 200}


def _weights(df: pd.DataFrame) -> np.ndarray:
    w = df["WEIGHT"].to_numpy(dtype=float)
    return w / w.mean()


def fit_logistic(
    pre: Preprocessor,
    df: pd.DataFrame,
    outcome: str,
    c: float,
    name: str,
    stage: str,
    x: np.ndarray | None = None,
) -> FittedModel:
    """Survey-weighted (pseudo-ML) logistic regression; ``x`` = precomputed ``pre.onehot(df)``."""
    est = LogisticRegression(C=c, **LOGIT_SOLVER)
    x = pre.onehot(df) if x is None else x
    est.fit(x, df[outcome].to_numpy(), sample_weight=_weights(df))
    return FittedModel(name, outcome, stage, pre, est, "onehot", {"C": c})


def fit_logistic_path(
    pre: Preprocessor,
    df: pd.DataFrame,
    outcome: str,
    cs: Sequence[float],
    name: str,
    stage: str,
    x: np.ndarray | None = None,
) -> list[FittedModel]:
    """L2 path over ``cs`` (fitted from weakest to strongest penalty, each warm-started at the
    previous solution; the optimum does not depend on the starting point)."""
    x = pre.onehot(df) if x is None else x
    y, w = df[outcome].to_numpy(), _weights(df)
    est = LogisticRegression(C=max(cs), warm_start=True, **LOGIT_SOLVER)
    fits = {}
    for c in sorted(cs, reverse=True):
        est.set_params(C=c)
        est.fit(x, y, sample_weight=w)
        e = copy.deepcopy(est)
        e.set_params(warm_start=False)
        fits[c] = FittedModel(name, outcome, stage, pre, e, "onehot", {"C": c})
    return [fits[c] for c in cs]


def fit_hgb(
    pre: Preprocessor, df: pd.DataFrame, outcome: str, params: dict, stage: str
) -> FittedModel:
    est = HistGradientBoostingClassifier(
        loss="log_loss",
        l2_regularization=1.0,
        max_iter=500,
        early_stopping=True,
        validation_fraction=0.15,
        n_iter_no_change=20,
        scoring="loss",
        categorical_features=pre.categorical_mask,
        random_state=config.RANDOM_SEED,
        **params,
    )
    est.fit(pre.ordinal(df), df[outcome].to_numpy(), sample_weight=_weights(df))
    return FittedModel(
        "hgb", outcome, stage, pre, est, "ordinal", {**params, "n_iter": est.n_iter_}
    )


def fit_rf(
    pre: Preprocessor, df: pd.DataFrame, outcome: str, params: dict, stage: str
) -> FittedModel:
    est = RandomForestClassifier(
        n_estimators=100,
        max_features="sqrt",
        max_samples=0.5,
        n_jobs=N_JOBS,
        random_state=config.RANDOM_SEED,
        **params,
    )
    est.fit(pre.onehot(df), df[outcome].to_numpy(), sample_weight=_weights(df))
    return FittedModel("rf", outcome, stage, pre, est, "onehot", dict(params))


# --------------------------------------------------------------------------------------
# Weighted metrics from score-group totals (vectorised over bootstrap replicates)
# --------------------------------------------------------------------------------------
@dataclass
class GroupedScores:
    """Predictions aggregated to (cluster x distinct score) totals.

    Every metric used here is a function of, per distinct predicted value g, the weighted
    number of events Y_g and the weighted number of crashes W_g.  A bootstrap replicate
    multiplies each cluster's weights by a constant, so replicate totals are
    ``multipliers @ cluster_totals`` -- this makes 200+ replicates of AUROC, AP, Brier, log
    loss, calibration and ECE cheap and exactly consistent with the point estimates.
    """

    p: np.ndarray
    y: np.ndarray
    w: np.ndarray
    cluster: np.ndarray  # integer cluster index (0..n_clusters-1)
    n_clusters: int
    n_bins: int = 20
    resolution: float | None = None  # None = exact; else group on a logit grid of this width

    def __post_init__(self) -> None:
        if self.resolution is None:
            self.pg, inv = np.unique(self.p, return_inverse=True)
        else:
            pc = np.clip(self.p, 1e-9, 1 - 1e-9)
            key = np.round(np.log(pc / (1 - pc)) / self.resolution).astype(np.int64)
            _, inv = np.unique(key, return_inverse=True)
            self.pg = np.bincount(inv, weights=self.p) / np.bincount(inv)
        shape = (self.n_clusters, len(self.pg))
        self.y_tot = sparse.csr_matrix((self.w * self.y, (self.cluster, inv)), shape=shape)
        self.w_tot = sparse.csr_matrix((self.w, (self.cluster, inv)), shape=shape)
        self.n = len(self.p)
        self.n_events = int(self.y.sum())
        # Equal-weight bins of predicted risk (fixed from the point sample).
        edges = weighted_quantile(self.p, self.w, np.linspace(0, 1, self.n_bins + 1)[1:-1])
        self.bin_of_group = np.searchsorted(edges, self.pg, side="right")
        self.g2b = sparse.csr_matrix(
            (np.ones(len(self.pg)), (np.arange(len(self.pg)), self.bin_of_group)),
            shape=(len(self.pg), self.n_bins),
        )

    def totals(self, mult: np.ndarray | None) -> tuple[np.ndarray, np.ndarray]:
        """(B x G) replicate totals of events and crashes; ``mult`` is (B x n_clusters)."""
        if mult is None:
            return (
                np.asarray(self.y_tot.sum(axis=0)),
                np.asarray(self.w_tot.sum(axis=0)),
            )
        return (self.y_tot.T @ mult.T).T, (self.w_tot.T @ mult.T).T

    def metrics(self, mult: np.ndarray | None = None, calibration: bool = True) -> dict:
        yb, wb = self.totals(mult)
        return metrics_from_totals(self.pg, yb, wb, self.g2b, calibration)

    def reliability(self, mult: np.ndarray | None = None) -> tuple[np.ndarray, ...]:
        """Per-bin (weighted crashes, events, expected events), each (B x n_bins)."""
        yb, wb = self.totals(mult)
        return wb @ self.g2b, yb @ self.g2b, (wb * self.pg) @ self.g2b


def weighted_quantile(x: np.ndarray, w: np.ndarray, q: np.ndarray | float) -> np.ndarray:
    """Smallest x whose weighted cumulative share reaches q."""
    o = np.argsort(x, kind="stable")
    cw = np.cumsum(w[o])
    cw = cw / cw[-1]
    idx = np.minimum(np.searchsorted(cw, np.atleast_1d(q), side="left"), len(x) - 1)
    return x[o][idx]


def _calibration_fit(pg: np.ndarray, yb: np.ndarray, wb: np.ndarray, iters: int = 30):
    """Logistic recalibration logit P(y) = a + b*logit(p) and calibration-in-the-large
    (intercept with slope fixed at 1), by vectorised Newton on grouped totals."""
    z = np.log(np.clip(pg, 1e-9, 1 - 1e-9) / (1 - np.clip(pg, 1e-9, 1 - 1e-9)))
    nb = yb.shape[0]
    a, b = np.zeros(nb), np.ones(nb)
    for _ in range(iters):
        mu = expit(a[:, None] + b[:, None] * z[None, :])
        r = yb - wb * mu
        v = wb * mu * (1 - mu)
        g0, g1 = r.sum(1), r @ z
        h00, h01, h11 = v.sum(1), v @ z, v @ (z * z)
        det = h00 * h11 - h01**2
        da = np.clip((h11 * g0 - h01 * g1) / det, -3, 3)
        db = np.clip((h00 * g1 - h01 * g0) / det, -3, 3)
        a, b = a + da, b + db
        if np.nanmax(np.abs(np.r_[da, db])) < 1e-10:
            break
    c = np.zeros(nb)
    for _ in range(iters):
        mu = expit(c[:, None] + z[None, :])
        dc = np.clip((yb - wb * mu).sum(1) / (wb * mu * (1 - mu)).sum(1), -3, 3)
        c = c + dc
        if np.nanmax(np.abs(dc)) < 1e-10:
            break
    return a, b, c


def metrics_from_totals(
    pg: np.ndarray,
    yb: np.ndarray,
    wb: np.ndarray,
    g2b: sparse.spmatrix | None = None,
    calibration: bool = True,
) -> dict[str, np.ndarray]:
    """Weighted performance metrics from per-score-group totals (rows = replicates)."""
    yb = np.atleast_2d(yb)
    wb = np.atleast_2d(wb)
    pos, neg = yb, wb - yb
    big_p, big_n = pos.sum(1), neg.sum(1)
    total = big_p + big_n
    with np.errstate(divide="ignore", invalid="ignore"):
        prev = big_p / total
        # AUROC: P(score of a random event > score of a random non-event), ties count 1/2.
        cneg = np.cumsum(neg, axis=1) - neg
        auc = (pos * (cneg + 0.5 * neg)).sum(1) / (big_p * big_n)
        # Average precision (step-wise, as sklearn): thresholds at distinct scores, descending.
        tp = np.cumsum(pos[:, ::-1], axis=1)
        fp = np.cumsum(neg[:, ::-1], axis=1)
        prec = np.where(tp + fp > 0, tp / np.where(tp + fp > 0, tp + fp, 1), 0.0)
        ap = (pos[:, ::-1] * prec).sum(1) / big_p
        pc = np.clip(pg, EPS, 1 - EPS)
        brier = (pos @ (1 - pg) ** 2 + neg @ pg**2) / total
        logloss = -(pos @ np.log(pc) + neg @ np.log1p(-pc)) / total
        expected = wb @ pg
        out = {
            "prevalence": prev,
            "mean_predicted": expected / total,
            "auroc": auc,
            "average_precision": ap,
            "ap_lift": ap / prev,
            "brier": brier,
            "brier_skill": 1 - brier / (prev * (1 - prev)),
            "log_loss": logloss,
            "oe_ratio": big_p / expected,
        }
        if g2b is not None:
            obs_bin = yb @ g2b
            exp_bin = (wb * pg) @ g2b
            out["ece"] = np.abs(obs_bin - exp_bin).sum(1) / total
    if calibration:
        a, b, c = _calibration_fit(pg, yb, wb)
        out["calibration_intercept"] = a
        out["calibration_slope"] = b
        out["calibration_in_the_large"] = c
    return out


# --------------------------------------------------------------------------------------
# Rao-Wu rescaled cluster bootstrap
# --------------------------------------------------------------------------------------
def cluster_index(stratum: np.ndarray, cluster: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Integer cluster index per row and the stratum code of each cluster."""
    codes, uniques = pd.factorize(pd.MultiIndex.from_arrays([stratum, cluster]), sort=True)
    return codes.astype(np.int64), np.asarray(uniques.get_level_values(0))


def rao_wu_multipliers(
    cluster_stratum: np.ndarray, n_boot: int, rng: np.random.Generator
) -> np.ndarray:
    """(n_boot x n_clusters) weight multipliers of the Rao-Wu (1988) rescaling bootstrap.

    In each stratum with n_h >= 2 clusters, n_h - 1 clusters are drawn with replacement and a
    cluster drawn r times gets multiplier r * n_h / (n_h - 1); this reproduces the
    with-replacement (ultimate cluster) variance used by the Taylor linearisation.  Strata
    with a single cluster contribute no variance (multiplier 1).
    """
    mult = np.ones((n_boot, len(cluster_stratum)))
    for s in np.unique(cluster_stratum):
        members = np.flatnonzero(cluster_stratum == s)
        nh = len(members)
        if nh < 2:
            continue
        counts = rng.multinomial(nh - 1, np.full(nh, 1.0 / nh), size=n_boot)
        mult[:, members] = counts * nh / (nh - 1)
    return mult


BOOT_RESOLUTION = 0.002  # logit-grid width used to group predictions in replicates


def point_and_boot(
    p: np.ndarray,
    y: np.ndarray,
    w: np.ndarray,
    cidx: np.ndarray,
    n_clusters: int,
    mult: np.ndarray,
    calibration: bool = True,
) -> tuple[GroupedScores, GroupedScores, dict[str, float], dict[str, np.ndarray]]:
    """Exact point metrics and bootstrap replicates (predictions grouped on a 0.002 logit
    grid for speed; the grouping changes metrics by far less than their sampling error)."""
    exact = GroupedScores(p, y, w, cidx, n_clusters)
    point = {k: float(v[0]) for k, v in exact.metrics(calibration=calibration).items()}
    grid = GroupedScores(p, y, w, cidx, n_clusters, resolution=BOOT_RESOLUTION)
    return exact, grid, point, boot_metrics(grid, mult, calibration)


def _summarise(point: float, reps: np.ndarray) -> dict[str, float]:
    reps = np.asarray(reps, dtype=float)
    ok = reps[np.isfinite(reps)]
    if len(ok) < 10:
        return {"estimate": point, "boot_se": np.nan, "ci_low": np.nan, "ci_high": np.nan}
    lo, hi = np.percentile(ok, [2.5, 97.5])
    return {
        "estimate": point,
        "boot_se": float(ok.std(ddof=1)),
        "ci_low": float(lo),
        "ci_high": float(hi),
        "n_boot_valid": len(ok),
    }


def boot_metrics(
    gs: GroupedScores, mult: np.ndarray, calibration: bool = True, chunk: int = 50
) -> dict[str, np.ndarray]:
    """Metrics for every bootstrap replicate (rows of ``mult``), in chunks."""
    parts: dict[str, list[np.ndarray]] = {}
    for start in range(0, mult.shape[0], chunk):
        m = gs.metrics(mult[start : start + chunk], calibration=calibration)
        for k, v in m.items():
            parts.setdefault(k, []).append(v)
    return {k: np.concatenate(v) for k, v in parts.items()}


# --------------------------------------------------------------------------------------
# Training and tuning
# --------------------------------------------------------------------------------------
def _point_metrics(p: np.ndarray, y: np.ndarray, w: np.ndarray) -> dict[str, float]:
    gs = GroupedScores(p, y, w, np.zeros(len(p), dtype=np.int64), 1)
    return {k: float(v[0]) for k, v in gs.metrics(calibration=True).items()}


def fit_stage(
    train: pd.DataFrame, valid: pd.DataFrame, outcome: str, stage: str
) -> tuple[dict[str, FittedModel], pd.DataFrame]:
    """Fit the five models for one outcome and feature stage; tune on the validation year."""
    check_features(stage_features(stage), stage)
    yv, wv = valid[outcome].to_numpy(), valid["WEIGHT"].to_numpy()
    rows: list[dict] = []
    models: dict[str, FittedModel] = {}

    def score(m: FittedModel) -> dict[str, float]:
        met = _point_metrics(m.predict(valid), yv, wv)
        rows.append(
            {
                "outcome": outcome,
                "stage": stage,
                "model": m.name,
                "params": repr(m.params),
                "valid_log_loss_w": met["log_loss"],
                "valid_auroc_w": met["auroc"],
                "valid_ap_w": met["average_precision"],
                "valid_brier_skill_w": met["brier_skill"],
                "valid_oe_w": met["oe_ratio"],
            }
        )
        return met

    def keep_best(name: str, candidates: list[FittedModel]) -> None:
        scores = [score(m)["log_loss"] for m in candidates]
        best = int(np.argmin(scores))
        for i, r in enumerate(rows[-len(candidates) :]):
            r["chosen"] = i == best
        models[name] = candidates[best]

    pre = Preprocessor(list(STAGES[stage])).fit(train)
    t0 = time.time()
    x_train = pre.onehot(train)
    keep_best(
        "logit_main",
        [fit_logistic(pre, train, outcome, RIDGE_C, "logit_main", stage, x=x_train)],
    )
    keep_best(
        "logit_l2", fit_logistic_path(pre, train, outcome, L2_GRID, "logit_l2", stage, x_train)
    )
    pre_int = Preprocessor(list(STAGES[stage]), products=stage_products(stage)).fit(train)
    keep_best(
        "logit_interact",
        [fit_logistic(pre_int, train, outcome, RIDGE_C, "logit_interact", stage)],
    )
    log.info("%s/%s logistic models: %.0fs", outcome, stage, time.time() - t0)
    t0 = time.time()
    keep_best("hgb", [fit_hgb(pre, train, outcome, p, stage) for p in HGB_GRID])
    log.info("%s/%s boosting grid: %.0fs", outcome, stage, time.time() - t0)
    t0 = time.time()
    keep_best("rf", [fit_rf(pre, train, outcome, p, stage) for p in RF_GRID])
    log.info("%s/%s random forest grid: %.0fs", outcome, stage, time.time() - t0)
    for m in models.values():
        unseen = m.pre.unseen(valid)
        if unseen:
            log.warning("%s: categories unseen in training appear in 2022: %s", m.name, unseen)
    return models, pd.DataFrame(rows)


def select_model(tuning: pd.DataFrame) -> tuple[str, dict]:
    """Pre-specified selection on the validation year (see module docstring)."""
    chosen = tuning[tuning["chosen"]].set_index("model")
    best_ll = chosen["valid_log_loss_w"].min()
    best_auc = chosen["valid_auroc_w"].max()
    for name in MODEL_NAMES:
        r = chosen.loc[name]
        if (
            r["valid_log_loss_w"] <= best_ll * (1 + SELECTION_LOGLOSS_TOL)
            and r["valid_auroc_w"] >= best_auc - SELECTION_AUC_TOL
        ):
            return name, {
                "rule": f"first of {list(MODEL_NAMES)} with 2022 weighted log loss <= best x "
                f"{1 + SELECTION_LOGLOSS_TOL} and weighted AUROC >= best - {SELECTION_AUC_TOL}",
                "best_valid_log_loss": float(best_ll),
                "best_valid_auroc": float(best_auc),
                "selected_valid_log_loss": float(r["valid_log_loss_w"]),
                "selected_valid_auroc": float(r["valid_auroc_w"]),
            }
    raise RuntimeError("selection rule failed")  # unreachable: the best model qualifies


# --------------------------------------------------------------------------------------
# Test-set evaluation
# --------------------------------------------------------------------------------------
DOMAINS: list[tuple[str, str, Any]] = [
    ("all", "all", None),
    ("year=2023", "YEAR", 2023),
    ("year=2024", "YEAR", 2024),
    ("urbanicity=urban", "urbanicity", "urban"),
    ("urbanicity=rural", "urbanicity", "rural"),
    ("crash_family=multi_vehicle", "crash_family", "multi_vehicle"),
    ("crash_family=single_vehicle", "crash_family", "single_vehicle"),
    ("crash_family=pedestrian_cyclist", "crash_family", "pedestrian_cyclist"),
    ("motorcycle=yes", "any_motorcycle", "yes"),
    ("motorcycle=no", "any_motorcycle", "no"),
    # Post-crash status used only to stratify the evaluation (never a feature): shows whether
    # performance holds where 'unknown' inputs cannot stand in for a fleeing driver.
    ("hit_and_run=no", "hit_and_run", "no"),
    ("hit_and_run=yes", "hit_and_run", "yes"),
]
UNWEIGHTED_DOMAINS = {"all", "year=2023", "year=2024"}
CALIBRATION_DOMAINS = {"all", "year=2023", "year=2024"}


def _domain_mask(df: pd.DataFrame, var: str, value: Any) -> np.ndarray:
    if var == "all":
        return np.ones(len(df), dtype=bool)
    return (df[var] == value).to_numpy()


def _flag(n_events: int, metric: str, est: float, se: float) -> str:
    if n_events < config.MIN_CELL_N:
        return "suppressed: fewer than 30 events"
    relative = metric in ("prevalence", "oe_ratio", "mean_predicted") and est and np.isfinite(se)
    if relative and se / abs(est) > config.MAX_RSE:
        return "unstable: RSE > 30%"
    return ""


def evaluate(
    test: pd.DataFrame,
    preds: dict[tuple[str, str, str], np.ndarray],
    n_boot: int,
    rng: np.random.Generator,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, np.ndarray]:
    """Point estimates and cluster-bootstrap CIs on the test years for every model/domain.

    Returns the long metric table, paired-difference table, reliability-curve table,
    calibration-by-risk-tier table and the bootstrap multipliers (reused for the threshold
    tables)."""
    cidx, cl_stratum = cluster_index(test["PSUSTRAT"].to_numpy(), test["PSU_VAR"].to_numpy())
    n_cl = len(cl_stratum)
    mult = rao_wu_multipliers(cl_stratum, n_boot, rng)
    rows, curves, tiers = [], [], []
    reps_all: dict[tuple[str, str, str], dict[str, np.ndarray]] = {}
    w_full = test["WEIGHT"].to_numpy()
    for (outcome, stage, model), p in preds.items():
        y = test[outcome].to_numpy()
        for dname, var, value in DOMAINS:
            d = _domain_mask(test, var, value)
            for weighting in ("weighted", "unweighted"):
                if weighting == "unweighted" and dname not in UNWEIGHTED_DOMAINS:
                    continue
                w = w_full[d] if weighting == "weighted" else np.ones(int(d.sum()))
                calib = dname in CALIBRATION_DOMAINS
                gs, grid, point, reps = point_and_boot(
                    p[d], y[d], w, cidx[d], n_cl, mult, calibration=calib
                )
                if dname == "all" and weighting == "weighted":
                    reps_all[(outcome, stage, model)] = reps
                for metric, est in point.items():
                    s = _summarise(est, reps[metric])
                    flag = _flag(gs.n_events, metric, est, s["boot_se"])
                    if flag.startswith("suppressed"):
                        s = {k: np.nan for k in s}
                    rows.append(
                        {
                            "outcome": outcome,
                            "stage": stage,
                            "model": model,
                            "domain": dname,
                            "weighting": weighting,
                            "metric": metric,
                            **s,
                            "n": gs.n,
                            "n_events": gs.n_events,
                            "flag": flag,
                            "quantity": "estimated (design-weighted)"
                            if weighting == "weighted"
                            else "sample (unweighted)",
                        }
                    )
                if dname == "all":
                    curves.append(
                        _reliability_rows(gs, grid, mult, outcome, stage, model, weighting)
                    )
                    tiers.append(_tier_rows(gs, grid, mult, outcome, stage, model, weighting))
    metrics = pd.DataFrame(rows)
    diffs = paired_differences(reps_all, metrics)
    return (
        metrics,
        diffs,
        pd.concat(curves, ignore_index=True),
        pd.concat(tiers, ignore_index=True),
        mult,
    )


# Risk tiers as ranges of the 20 equal-weight reliability bins (0-based, inclusive).
RISK_TIERS: dict[str, tuple[int, int]] = {
    "lowest 50% of predicted risk": (0, 9),
    "50th-80th percentile": (10, 15),
    "highest 20%": (16, 19),
}


def _tier_rows(
    gs: GroupedScores,
    grid: GroupedScores,
    mult: np.ndarray,
    outcome: str,
    stage: str,
    model: str,
    weighting: str,
) -> pd.DataFrame:
    """Observed / expected within broad tiers of predicted risk (calibration by risk level;
    overall O/E and the calibration slope can hide opposite errors at low and high risk)."""
    wb, yb, eb = gs.reliability(None)
    _, yr, er = grid.reliability(mult)
    rows = []
    for label, (lo, hi) in RISK_TIERS.items():
        sl = slice(lo, hi + 1)
        w_t, y_t, e_t = wb[0, sl].sum(), yb[0, sl].sum(), eb[0, sl].sum()
        with np.errstate(divide="ignore", invalid="ignore"):
            rep = yr[:, sl].sum(1) / er[:, sl].sum(1)
        s = _summarise(float(y_t / e_t) if e_t else np.nan, rep)
        rows.append(
            {
                "outcome": outcome,
                "stage": stage,
                "model": model,
                "weighting": weighting,
                "risk_tier": label,
                "share_of_crashes": w_t / wb[0].sum(),
                "share_of_expected_events": e_t / eb[0].sum(),
                "mean_predicted": e_t / w_t if w_t else np.nan,
                "observed_rate": y_t / w_t if w_t else np.nan,
                "oe_ratio": s["estimate"],
                "oe_low": s["ci_low"],
                "oe_high": s["ci_high"],
                "quantity": "estimated (design-weighted)"
                if weighting == "weighted"
                else "sample (unweighted)",
            }
        )
    return pd.DataFrame(rows)


def _reliability_rows(
    gs: GroupedScores,
    grid: GroupedScores,
    mult: np.ndarray,
    outcome: str,
    stage: str,
    model: str,
    weighting: str,
) -> pd.DataFrame:
    wb, yb, eb = gs.reliability(None)
    wr, yr, _ = grid.reliability(mult)
    with np.errstate(divide="ignore", invalid="ignore"):
        obs_r = yr / wr
    rows = []
    for b in range(gs.n_bins):
        rep = obs_r[:, b]
        rep = rep[np.isfinite(rep)]
        lo, hi = np.percentile(rep, [2.5, 97.5]) if len(rep) > 10 else (np.nan, np.nan)
        rows.append(
            {
                "outcome": outcome,
                "stage": stage,
                "model": model,
                "weighting": weighting,
                "bin": b + 1,
                "share_of_crashes": wb[0, b] / wb[0].sum(),
                "mean_predicted": eb[0, b] / wb[0, b] if wb[0, b] else np.nan,
                "observed_rate": yb[0, b] / wb[0, b] if wb[0, b] else np.nan,
                "observed_low": lo,
                "observed_high": hi,
            }
        )
    return pd.DataFrame(rows)


def paired_differences(
    reps: dict[tuple[str, str, str], dict[str, np.ndarray]], metrics: pd.DataFrame
) -> pd.DataFrame:
    """Model minus logit_main (same stage) and circumstance stage minus pre-crash stage (same
    model), weighted, overall test domain, from the same bootstrap replicates."""
    point = metrics[(metrics.domain == "all") & (metrics.weighting == "weighted")].set_index(
        ["outcome", "stage", "model", "metric"]
    )["estimate"]
    keys = ("auroc", "average_precision", "brier", "brier_skill", "log_loss", "ece")
    rows = []
    for (outcome, stage, model), r in reps.items():
        comparisons = []
        if model != "logit_main":
            comparisons.append(("vs logit_main", (outcome, stage, "logit_main")))
        if stage == "pre_crash+circumstance":
            comparisons.append(("circumstance stage vs pre_crash", (outcome, "pre_crash", model)))
        for label, other in comparisons:
            if other not in reps:
                continue
            for k in keys:
                d = r[k] - reps[other][k]
                est = point[(outcome, stage, model, k)] - point[(*other[:3], k)]
                rows.append(
                    {
                        "outcome": outcome,
                        "stage": stage,
                        "model": model,
                        "comparison": label,
                        "reference": f"{other[1]}/{other[2]}",
                        "metric": k,
                        **_summarise(est, d),
                        "quantity": "estimated difference (paired cluster bootstrap)",
                    }
                )
    return pd.DataFrame(rows)


def threshold_tables(
    valid: pd.DataFrame,
    test: pd.DataFrame,
    preds_valid: dict[tuple[str, str, str], np.ndarray],
    preds_test: dict[tuple[str, str, str], np.ndarray],
    mult: np.ndarray,
) -> pd.DataFrame:
    """Confusion matrices on test at thresholds fixed on the 2022 validation predictions."""
    cidx, cl_stratum = cluster_index(test["PSUSTRAT"].to_numpy(), test["PSU_VAR"].to_numpy())
    n_years = test["YEAR"].nunique()
    w = test["WEIGHT"].to_numpy()
    rows = []
    for key, pt in preds_test.items():
        outcome, stage, model = key
        pv = preds_valid[key]
        yv, wv = valid[outcome].to_numpy(), valid["WEIGHT"].to_numpy()
        o = np.argsort(-pv, kind="stable")
        cum_recall = np.cumsum((wv * yv)[o]) / (wv * yv).sum()
        thresholds = {
            "top 1% of 2022 crashes (weighted)": float(weighted_quantile(pv, wv, 0.99)[0]),
            "top 5% of 2022 crashes (weighted)": float(weighted_quantile(pv, wv, 0.95)[0]),
            "50% recall in 2022 (weighted)": float(pv[o][np.searchsorted(cum_recall, 0.5)]),
        }
        y = test[outcome].to_numpy()
        for label, t in thresholds.items():
            f = pt >= t
            cells = {
                "tp": f & (y == 1),
                "fp": f & (y == 0),
                "fn": ~f & (y == 1),
                "tn": ~f & (y == 0),
            }
            tot = {
                k: np.bincount(cidx, weights=w * v, minlength=len(cl_stratum))
                for k, v in cells.items()
            }
            rep = {k: mult @ v for k, v in tot.items()}
            pt_w = {k: v.sum() for k, v in tot.items()}

            def ratios(t: dict) -> dict[str, Any]:
                with np.errstate(divide="ignore", invalid="ignore"):
                    all_ = t["tp"] + t["fp"] + t["fn"] + t["tn"]
                    return {
                        "flagged_share": (t["tp"] + t["fp"]) / all_,
                        "sensitivity": t["tp"] / (t["tp"] + t["fn"]),
                        "specificity": t["tn"] / (t["tn"] + t["fp"]),
                        "ppv": t["tp"] / (t["tp"] + t["fp"]),
                        "npv": t["tn"] / (t["tn"] + t["fn"]),
                        "lift": (t["tp"] / (t["tp"] + t["fp"])) / ((t["tp"] + t["fn"]) / all_),
                    }

            r_pt, r_rep = ratios(pt_w), ratios(rep)
            rec = {
                "outcome": outcome,
                "stage": stage,
                "model": model,
                "threshold_rule": label,
                "threshold": t,
                **{f"n_{k}": int(v.sum()) for k, v in cells.items()},
                **{f"est_{k}_per_year": pt_w[k] / n_years for k in cells},
            }
            for k, v in r_pt.items():
                s = _summarise(float(v), r_rep[k])
                rec[k] = s["estimate"]
                rec[f"{k}_low"] = s["ci_low"]
                rec[f"{k}_high"] = s["ci_high"]
            rec["quantity"] = "estimated (design-weighted); n_* are unweighted sample counts"
            rows.append(rec)
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------------------
# Temporal stability
# --------------------------------------------------------------------------------------
def temporal_stability(
    df: pd.DataFrame,
    hgb_params: dict[tuple[str, str], dict],
    n_boot: int,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """Train on 2016-2019; evaluate each later year separately (weighted, PSU bootstrap)."""
    rows = []
    early = df["YEAR"].between(2016, 2019).to_numpy()
    for outcome in OUTCOMES:
        known = df[outcome].notna().to_numpy()
        train = df[early & known]
        for stage in STAGES:
            pre = Preprocessor(list(STAGES[stage])).fit(train)
            params = {
                k: v
                for k, v in hgb_params[(outcome, stage)].items()
                if k in ("learning_rate", "max_leaf_nodes", "min_samples_leaf")
            }
            models = {
                "logit_main": fit_logistic(pre, train, outcome, RIDGE_C, "logit_main", stage),
                "hgb": fit_hgb(pre, train, outcome, params, stage),
            }
            for year in range(2020, 2025):
                ev = df[(df["YEAR"] == year).to_numpy() & known]
                cidx, cl_stratum = cluster_index(
                    ev["PSUSTRAT"].to_numpy(), ev["PSU_VAR"].to_numpy()
                )
                mult = rao_wu_multipliers(cl_stratum, n_boot, rng)
                for name, m in models.items():
                    gs, _, point, reps = point_and_boot(
                        m.predict(ev),
                        ev[outcome].to_numpy(),
                        ev["WEIGHT"].to_numpy(),
                        cidx,
                        len(cl_stratum),
                        mult,
                    )
                    for metric in (
                        "prevalence",
                        "mean_predicted",
                        "auroc",
                        "average_precision",
                        "brier_skill",
                        "oe_ratio",
                        "calibration_in_the_large",
                        "calibration_slope",
                    ):
                        rows.append(
                            {
                                "outcome": outcome,
                                "stage": stage,
                                "model": name,
                                "train_years": "2016-2019",
                                "eval_year": year,
                                "metric": metric,
                                **_summarise(point[metric], reps[metric]),
                                "n": gs.n,
                                "n_events": gs.n_events,
                                "quantity": "estimated (design-weighted)",
                            }
                        )
            log.info("temporal stability %s/%s done", outcome, stage)
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------------------
# Interpretation
# --------------------------------------------------------------------------------------
# Interpretation features: every categorical feature, with the speed-limit band and the
# numeric limit moved jointly, and the oldest-vehicle age (numeric + missing indicator).
# Crash type is moved together with the vehicle count (both derive from VE_FORMS), so donor
# assignments never create a crash that cannot occur.
LINKED = {
    "speed_limit": ["speed_limit", "speed_limit_mph"],
    "crash_type": ["crash_type", "n_vehicles"],
}


def weighted_sample(df: pd.DataFrame, n: int, rng: np.random.Generator) -> pd.DataFrame:
    """Rows drawn with probability proportional to WEIGHT (so plain means are weighted)."""
    w = df["WEIGHT"].to_numpy()
    idx = rng.choice(len(df), size=n, replace=True, p=w / w.sum())
    return df.iloc[idx].reset_index(drop=True)


def interpretation_features(stage: str) -> dict[str, list[str]]:
    groups = {c: LINKED.get(c, [c]) for c in STAGES[stage]}
    groups["oldest_vehicle_age"] = ["oldest_vehicle_age"]
    return groups


# Features whose permutation is conditional on a structurally linked feature.
CONDITIONAL_PERMUTATION = {"n_vehicles": "crash_type"}


def _within_group_draw(groups: np.ndarray, w: np.ndarray, seed: int) -> np.ndarray:
    """Row indices drawn with probability proportional to ``w`` within each group."""
    rng = np.random.default_rng(seed)
    draw = np.empty(len(groups), dtype=np.int64)
    codes, _ = pd.factorize(groups)
    for g in np.unique(codes):
        idx = np.flatnonzero(codes == g)
        draw[idx] = rng.choice(idx, size=len(idx), replace=True, p=w[idx] / w[idx].sum())
    return draw


def permutation_importance(
    model: FittedModel,
    df: pd.DataFrame,
    outcome: str,
    n_repeats: int,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """Weighted permutation importance: increase in weighted log loss and drop in weighted
    AUROC when a feature (group) is replaced by draws from its weighted marginal.

    The replacement values are drawn with probability proportional to ``WEIGHT`` (independent
    of the outcome and of the other features), so the "permuted" feature follows its
    population distribution; a plain row permutation would impose the CRSS *sample*
    distribution, which over-represents injury crashes and their circumstances.

    The vehicle count is replaced by weighted draws *within the same crash type*
    (``CONDITIONAL_PERMUTATION``): a marginal draw would create crashes that cannot occur
    (e.g. a single-vehicle rollover with three vehicles), so its importance is conditional
    on crash type (crash type itself is permuted together with the vehicle count)."""
    y, w = df[outcome].to_numpy(), df["WEIGHT"].to_numpy()
    df = df[[*model.pre.categorical, *model.pre.numeric]]
    base = _point_metrics(model.predict(df), y, w)
    prob = w / w.sum()
    rows = []
    for feat, cols in interpretation_features(model.stage).items():
        given = CONDITIONAL_PERMUTATION.get(feat)
        given = given if given in df else None
        d_ll, d_auc = [], []
        for rep in range(n_repeats):
            draw = rng.choice(len(df), size=len(df), replace=True, p=prob)
            if given is not None:
                draw = _within_group_draw(df[given].to_numpy(), w, config.RANDOM_SEED + rep)
            shuffled = df.copy()
            for c in cols:
                shuffled[c] = df[c].to_numpy()[draw]
            m = _point_metrics(model.predict(shuffled), y, w)
            d_ll.append(m["log_loss"] - base["log_loss"])
            d_auc.append(base["auroc"] - m["auroc"])
        rows.append(
            {
                "outcome": outcome,
                "stage": model.stage,
                "model": model.name,
                "feature": feat,
                "log_loss_increase": float(np.mean(d_ll)),
                "log_loss_increase_sd": float(np.std(d_ll, ddof=1)),
                "log_loss_increase_pct": 100 * float(np.mean(d_ll)) / base["log_loss"],
                "auroc_drop": float(np.mean(d_auc)),
                "auroc_drop_sd": float(np.std(d_auc, ddof=1)),
                "n_repeats": n_repeats,
                "replacement": f"weighted draws within {given}" if given else "weighted marginal",
                "quantity": "model-predicted (predictive importance, not causal)",
            }
        )
    return pd.DataFrame(rows)


def set_feature(
    df: pd.DataFrame, feature: str, value: Any, reps: dict[str, dict] | None = None
) -> pd.DataFrame:
    """Copy of ``df`` with ``feature`` set to ``value`` for every row.

    ``speed_limit`` accepts an mph number (band derived) or a band label (mph set to the
    band's representative training value from ``reps``, NaN for unknown / none);
    ``oldest_vehicle_age`` accepts a number, NaN, or an age-band label (representative age);
    setting ``crash_type`` also moves vehicle counts that the type cannot have to the first
    compatible count (single-vehicle types -> 1, multi-vehicle types: 1 -> 2).
    """
    out = df.copy()
    if feature == "crash_type" and "n_vehicles" in out:
        allowed = compatible_n_vehicles(value)
        out.loc[~out["n_vehicles"].isin(allowed), "n_vehicles"] = allowed[0]
    if feature == "speed_limit":
        if isinstance(value, str):
            out["speed_limit"] = value
            out["speed_limit_mph"] = (reps or {}).get("speed_limit", {}).get(value, np.nan)
        else:
            out["speed_limit_mph"] = float(value)
            out["speed_limit"] = speed_band([value])[0]
    elif feature in ("oldest_vehicle_age", "veh_age_band"):
        if isinstance(value, str):
            out["oldest_vehicle_age"] = (reps or {}).get("veh_age_band", {}).get(value, np.nan)
        else:
            out["oldest_vehicle_age"] = float(value)
    else:
        out[feature] = value
    return out


def representative_values(train: pd.DataFrame) -> dict[str, dict]:
    """Weighted median mph within each speed-limit band and age within each age band."""
    out: dict[str, dict] = {"speed_limit": {}, "veh_age_band": {}}
    for col, num, key in (
        ("speed_limit", "speed_limit_mph", "speed_limit"),
        ("veh_age_band", "oldest_vehicle_age", "veh_age_band"),
    ):
        for lv, g in train.groupby(col):
            v = g[num].to_numpy(dtype=float)
            ok = np.isfinite(v)
            out[key][lv] = (
                float(weighted_quantile(v[ok], g["WEIGHT"].to_numpy()[ok], 0.5)[0])
                if ok.any()
                else np.nan
            )
    return out


def partial_dependence(
    models: dict[str, FittedModel],
    ref: pd.DataFrame,
    features: Sequence[str],
    reps: dict[str, dict],
    n_ice: int = 30,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Weighted partial dependence (ref rows drawn proportional to weight) and ICE curves."""
    pd_rows, ice_rows = [], []
    for feat in features:
        if feat == "speed_limit":
            values: list[Any] = [*range(15, 80, 5), "unknown"]
        elif feat == "oldest_vehicle_age":
            values = [*range(0, 31, 2), np.nan]
        else:
            first = next(iter(models.values()))
            values = list(first.pre.levels_[feat])
        for v in values:
            scen = set_feature(ref, feat, v, reps)
            for name, m in models.items():
                p = m.predict(scen)
                pd_rows.append(
                    {
                        "stage": m.stage,
                        "model": name,
                        "feature": feat,
                        "value": "unknown" if (isinstance(v, float) and np.isnan(v)) else v,
                        "pd_probability": float(p.mean()),
                        "pd_logit": float(
                            np.mean(np.log(np.clip(p, 1e-9, 1) / np.clip(1 - p, 1e-9, 1)))
                        ),
                        "quantity": "model-predicted (partial dependence)",
                    }
                )
                if name == "hgb" and feat in ("speed_limit", "oldest_vehicle_age"):
                    for i in range(min(n_ice, len(ref))):
                        ice_rows.append(
                            {
                                "stage": m.stage,
                                "model": name,
                                "feature": feat,
                                "value": "unknown" if (isinstance(v, float) and np.isnan(v)) else v,
                                "row": i,
                                "probability": float(p[i]),
                            }
                        )
    return pd.DataFrame(pd_rows), pd.DataFrame(ice_rows)


def _donor_assign(
    ref: pd.DataFrame, var: str, levels: Sequence, rng: np.random.Generator
) -> pd.DataFrame:
    """Values of ``var`` (and its linked columns) drawn from ref rows in ``levels``."""
    cols = LINKED.get(var, [var])
    donors = ref[ref[var].isin(list(levels))]
    if donors.empty:
        fill = {"n_vehicles": compatible_n_vehicles(levels[0])[0]}
        donors = pd.DataFrame({var: [levels[0]], **{c: [fill.get(c, np.nan)] for c in cols[1:]}})
    idx = rng.integers(0, len(donors), len(ref))
    return donors[cols].iloc[idx].reset_index(drop=True)


def implied_interactions(
    models: dict[str, FittedModel], ref: pd.DataFrame, stage: str, rng: np.random.Generator
) -> pd.DataFrame:
    """Interaction implied by each model for each pre-specified RQ2 pair.

    For the four exposure combinations (A, B) in {0,1}^2, every reference crash is assigned
    the exposure states (group levels drawn from the observed within-group distribution,
    identical draws across models) and predictions are averaged.  Reported: the mean
    double difference of log-odds (exactly the product-term coefficient in the logistic
    interaction model, exactly 0 in the main-effects model), the interaction contrast on
    the risk scale and the ratio of risk ratios."""
    rows = []
    avail = set(STAGES[stage])
    for comb in PAIRS:
        if not comb.prespecified or not all(e.var in avail for e in comb.exposures):
            continue
        a, b = comb.exposures
        assign = {
            (e.var, s): _donor_assign(ref, e.var, e.state(s), rng) for e in (a, b) for s in (0, 1)
        }
        scen = {}
        for sa in (0, 1):
            for sb in (0, 1):
                d = ref.copy()
                for e, s in ((a, sa), (b, sb)):
                    vals = assign[(e.var, s)]
                    for c in vals.columns:
                        d[c] = vals[c].to_numpy()
                scen[(sa, sb)] = d
        for name, m in models.items():
            lg = {k: m.predict_logit(v) for k, v in scen.items()}
            pr = {k: float(expit(v).mean()) for k, v in lg.items()}
            dd = float(np.mean(lg[(1, 1)] - lg[(1, 0)] - lg[(0, 1)] + lg[(0, 0)]))
            rec = {
                "stage": stage,
                "pair": comb.name,
                "model": name,
                "p00": pr[(0, 0)],
                "p10": pr[(1, 0)],
                "p01": pr[(0, 1)],
                "p11": pr[(1, 1)],
                "logit_double_difference": dd,
                "interaction_contrast": pr[(1, 1)] - pr[(1, 0)] - pr[(0, 1)] + pr[(0, 0)],
                "ratio_of_rr": pr[(1, 1)] * pr[(0, 0)] / (pr[(1, 0)] * pr[(0, 1)]),
                "quantity": "model-predicted (implied interaction)",
            }
            if name == "logit_interact":
                idx = m.pre.onehot_names_.index(f"product:{comb.name}")
                rec["product_coef"] = float(m.estimator.coef_[0, idx])
            rows.append(rec)
    return pd.DataFrame(rows)


def screening_levels(train: pd.DataFrame, stage: str) -> dict[str, list]:
    """Levels used to screen interactions (vehicle age enters through its bands)."""
    lv = {c: [x for x in ALL_LEVELS[c] if x in set(train[c])] for c in STAGES[stage]}
    lv["veh_age_band"] = [x for x in VEH_AGE_LEVELS if x in set(train["veh_age_band"])]
    return lv


def _set_level(df: pd.DataFrame, feat: str, level: Any, reps: dict[str, dict]) -> pd.DataFrame:
    if feat == "veh_age_band":
        out = set_feature(df, "veh_age_band", level, reps)
        out["veh_age_band"] = level
        return out
    if feat == "speed_limit":
        return set_feature(df, "speed_limit", level, reps)
    return set_feature(df, feat, level)


def cramers_v(a: np.ndarray, b: np.ndarray, w: np.ndarray) -> float:
    tab = pd.crosstab(a, b, values=w, aggfunc="sum").fillna(0).to_numpy()
    n = tab.sum()
    exp = np.outer(tab.sum(1), tab.sum(0)) / n
    with np.errstate(divide="ignore", invalid="ignore"):
        chi2 = np.nansum((tab - exp) ** 2 / exp)
    k = min(tab.shape) - 1
    return float(np.sqrt(chi2 / (n * k))) if k > 0 else 0.0


def interaction_screen(
    model: FittedModel,
    ref: pd.DataFrame,
    train: pd.DataFrame,
    reps: dict[str, dict],
    outcome: str,
) -> tuple[pd.DataFrame, dict]:
    """Friedman's H statistic (log-odds scale) for every feature pair of a boosted model,
    on reference crashes from the validation year (discovery data, disjoint from test)."""
    levels = screening_levels(train, model.stage)
    feats = list(levels)
    n = len(ref)
    obs = {f: ref[f].astype(object).to_numpy() for f in feats}

    def pd_values(assignments: list[dict[str, Any]]) -> np.ndarray:
        frames = []
        for a in assignments:
            d = ref
            for f, lv in a.items():
                d = _set_level(d, f, lv, reps)
            frames.append(d)
        big = pd.concat(frames, ignore_index=True)
        return model.predict_logit(big).reshape(len(assignments), n).mean(axis=1)

    pd1: dict[str, dict] = {}
    for f in feats:
        vals = pd_values([{f: lv} for lv in levels[f]])
        pd1[f] = dict(zip(levels[f], vals, strict=True))
    pd2_cache: dict[tuple[str, str], dict] = {}
    rows = []
    prespecified = {frozenset(e.var for e in c.exposures) for c in PAIRS if c.prespecified}
    w_train = train["WEIGHT"].to_numpy()
    for i, f in enumerate(feats):
        for g in feats[i + 1 :]:
            combos = sorted(set(zip(obs[f], obs[g], strict=True)), key=str)
            vals = pd_values([{f: a, g: b} for a, b in combos])
            pd2 = dict(zip(combos, vals, strict=True))
            pd2_cache[(f, g)] = pd2
            jf = np.array([pd1[f][x] for x in obs[f]])
            jg = np.array([pd1[g][x] for x in obs[g]])
            jfg = np.array([pd2[(x, z)] for x, z in zip(obs[f], obs[g], strict=True)])
            jf, jg, jfg = jf - jf.mean(), jg - jg.mean(), jfg - jfg.mean()
            resid = jfg - jf - jg
            rows.append(
                {
                    "outcome": outcome,
                    "stage": model.stage,
                    "model": model.name,
                    "feature_a": f,
                    "feature_b": g,
                    "h_squared": float((resid**2).sum() / max((jfg**2).sum(), EPS)),
                    "rms_interaction_logit": float(np.sqrt(np.mean(resid**2))),
                    "cramers_v_train": cramers_v(
                        train[f].astype(str).to_numpy(), train[g].astype(str).to_numpy(), w_train
                    ),
                    "prespecified_pair": frozenset({f, g}) in prespecified,
                    "quantity": "model-predicted (screening statistic)",
                }
            )
    out = pd.DataFrame(rows).sort_values("rms_interaction_logit", ascending=False)
    return out.reset_index(drop=True), {"pd1": pd1, "levels": levels}


def candidate_cells(
    model: FittedModel,
    ref: pd.DataFrame,
    train: pd.DataFrame,
    outcome: str,
    pair: tuple[str, str],
    reps: dict[str, dict],
    levels: dict[str, list],
) -> dict:
    """For a screened pair, the cell (a, b) whose log-odds double difference against the
    reference levels is largest in the boosted model, among cells with >= 30 training
    events in each of the four cells used by the contrast."""
    f, g = pair
    ref_f, ref_g = levels[f][0], levels[g][0]
    ev = train[train[outcome] == 1].groupby([f, g]).size()

    def events(a: Any, b: Any) -> int:
        return int(ev.get((a, b), 0))

    best = None
    for a in levels[f][1:]:
        for b in levels[g][1:]:
            if a == "unknown" or b == "unknown":
                continue
            if min(events(a, b), events(a, ref_g), events(ref_f, b)) < config.MIN_CELL_N:
                continue
            lg = {}
            for key, (x, z) in {
                "11": (a, b),
                "10": (a, ref_g),
                "01": (ref_f, b),
                "00": (ref_f, ref_g),
            }.items():
                d = _set_level(_set_level(ref, f, x, reps), g, z, reps)
                lg[key] = model.predict_logit(d)
            dd = float(np.mean(lg["11"] - lg["10"] - lg["01"] + lg["00"]))
            if best is None or abs(dd) > abs(best["hgb_logit_dd"]):
                best = {
                    "feature_a": f,
                    "level_a": a,
                    "ref_a": ref_f,
                    "feature_b": g,
                    "level_b": b,
                    "ref_b": ref_g,
                    "hgb_logit_dd": dd,
                    "train_events_11": events(a, b),
                }
    return best or {}


def _survey_frame(df: pd.DataFrame, train_median_age: float) -> pd.DataFrame:
    out = df.copy()
    out["veh_age_lin"] = out["oldest_vehicle_age"].fillna(train_median_age)
    mph = out["speed_limit_mph"].to_numpy()
    for name, cond in {
        "sl_25_in_band": mph == 25,
        "sl_35_in_band": mph == 35,
        "sl_45_in_band": mph == 45,
        "sl_55_in_band": mph == 55,
        "sl_65_in_band": mph == 65,
        "sl_75plus_in_band": mph >= 75,
    }.items():
        out[name] = cond.astype(float)
    return out


def _observed_levels(df: pd.DataFrame, var: str) -> list:
    present = set(pd.unique(df[var].astype(object)))
    return [lv for lv in ALL_LEVELS[var] if lv in present]


def confirm_patterns(
    df: pd.DataFrame,
    design_full: SurveyDesign,
    outcome: str,
    stage: str,
    candidates: list[dict],
    train_median_age: float,
) -> pd.DataFrame:
    """Confirmatory survey-weighted logistic analyses on the independent test years.

    Candidates come from the boosted model (screened on training/validation years).  Each is
    tested with a transparent model: all stage covariates (categorical, speed-limit bands,
    vehicle-age bands) plus the candidate term(s); design-based Wald F tests (Taylor
    linearisation, PSUSTRAT/PSU_VAR) and, for interactions, standardised margins with the
    additive interaction contrast and RERI.  Holm adjustment across all candidates."""
    mask = df["YEAR"].isin(config.TEST_YEARS).to_numpy() & df[outcome].notna().to_numpy()
    ev = _survey_frame(df[mask].reset_index(drop=True), train_median_age)
    design = design_full.subset(mask)
    y = ev[outcome].to_numpy()
    covs = [*STAGES[stage], "veh_age_band"]
    base_cat = {c: _observed_levels(ev, c) for c in covs}
    rows = []
    for cand in candidates:
        if cand["kind"] == "interaction":
            term = ((cand["feature_a"], [cand["level_a"]]), (cand["feature_b"], [cand["level_b"]]))
            cat = dict(base_cat)
            pair = {cand["feature_a"], cand["feature_b"]}
            if "crash_type" in pair:
                # Crash type fixes the vehicle count for most types; as in analysis/severity.py
                # the contrast comes from the model without the vehicle count, so the margins
                # never combine a crash type with an impossible number of vehicles.
                cat.pop("n_vehicles", None)
            elif "n_vehicles" in pair:
                cat.pop("crash_type", None)
            spec = ModelSpec(categorical=cat, products=[term])
            model = SurveyLogit(spec, ridge=0.01).fit(ev, y, design)
            name = model.names_[-1]
            test = model.wald_test([name])
            ct = model.coef_table().set_index("term").loc[name]
            fa, la, ra = cand["feature_a"], cand["level_a"], cand["ref_a"]
            fb, lb, rb = cand["feature_b"], cand["level_b"], cand["ref_b"]
            ms = model.margins(
                ev,
                {
                    "p11": lambda d, fa=fa, la=la, fb=fb, lb=lb: d.assign(**{fa: la, fb: lb}),
                    "p10": lambda d, fa=fa, la=la, fb=fb, rb=rb: d.assign(**{fa: la, fb: rb}),
                    "p01": lambda d, fa=fa, ra=ra, fb=fb, lb=lb: d.assign(**{fa: ra, fb: lb}),
                    "p00": lambda d, fa=fa, ra=ra, fb=fb, rb=rb: d.assign(**{fa: ra, fb: rb}),
                },
            )
            ic = interaction_contrasts(ms, "p11", "p10", "p01", "p00")
            ic_lo, ic_hi = ic["ic"].ci()
            reri_lo, reri_hi = ic["reri"].ci()
            agree = np.sign(ct["coef"]) == np.sign(cand["hgb_logit_dd"])
            within = bool(np.log(ct["or_low"]) <= cand["hgb_logit_dd"] <= np.log(ct["or_high"]))
            rows.append(
                {
                    "outcome": outcome,
                    "stage": stage,
                    "kind": "interaction",
                    "candidate": f"{fa}={la} x {fb}={lb} (refs {ra}, {rb})",
                    "boosting_estimate": cand["hgb_logit_dd"],
                    "boosting_estimate_scale": "mean log-odds double difference (screen data)",
                    "survey_estimate": float(ct["coef"]),
                    "survey_estimate_scale": "product-term log OR (2023-2024)",
                    "survey_ci_low": float(np.log(ct["or_low"])),
                    "survey_ci_high": float(np.log(ct["or_high"])),
                    "ratio_of_or": float(ct["odds_ratio"]),
                    "p11": ms.values["p11"],
                    "p10": ms.values["p10"],
                    "p01": ms.values["p01"],
                    "p00": ms.values["p00"],
                    "interaction_contrast": ic["ic"].estimate,
                    "ic_low": ic_lo,
                    "ic_high": ic_hi,
                    "reri": ic["reri"].estimate,
                    "reri_low": reri_lo,
                    "reri_high": reri_hi,
                    "wald_F": test["F"],
                    "df_num": test["q"],
                    "p_value": test["p"],
                    "direction_agrees": bool(agree),
                    # Is the boosting magnitude (screen data) compatible with the survey CI?
                    "boosting_within_survey_ci": within,
                    "n": design.n,
                    "n_events": int(y.sum()),
                }
            )
        else:
            numeric, terms = cand["numeric"], cand["terms"]
            cat = dict(base_cat)
            if cand.get("drop_band"):
                cat = {k: v for k, v in cat.items() if k != cand["drop_band"]}
            spec = ModelSpec(categorical=cat, numeric=numeric)
            model = SurveyLogit(spec, ridge=0.01).fit(ev, y, design)
            names = [n for n in model.names_ if n in terms]
            test = model.wald_test(names)
            ct = model.coef_table().set_index("term").loc[names]
            shape = ""
            compare = ct
            if cand.get("shape_terms"):
                # Shape without the linear term: band odds ratios vs the reference band.
                shape_model = SurveyLogit(ModelSpec(categorical=cat), ridge=0.01).fit(ev, y, design)
                sct = shape_model.coef_table().set_index("term").loc[cand["shape_terms"]]
                shape = "; ".join(
                    f"{t}: OR {r.odds_ratio:.3g} ({r.or_low:.3g}-{r.or_high:.3g})"
                    for t, r in sct.iterrows()
                )
                compare = sct
            agreement = term_agreement(cand.get("hgb_terms", {}), compare)
            rows.append(
                {
                    "outcome": outcome,
                    "stage": stage,
                    "kind": "non-linearity",
                    "shape_detail": shape,
                    "candidate": cand["label"],
                    "boosting_estimate": cand.get("hgb_summary", np.nan),
                    "boosting_estimate_scale": cand.get("hgb_scale", ""),
                    "survey_estimate": float(ct["coef"].abs().max()),
                    "survey_estimate_scale": "largest |log OR| among tested terms (2023-2024)",
                    "survey_ci_low": np.nan,
                    "survey_ci_high": np.nan,
                    "terms_detail": "; ".join(
                        f"{t}: OR {r.odds_ratio:.3g} ({r.or_low:.3g}-{r.or_high:.3g})"
                        for t, r in ct.iterrows()
                    ),
                    "wald_F": test["F"],
                    "df_num": test["q"],
                    "p_value": test["p"],
                    "direction_agrees": np.nan,
                    "term_agreement": agreement["detail"],
                    "terms_confirmed": agreement["confirmed"],
                    "terms_contradicted": agreement["contradicted"],
                    "terms_outside_ci": agreement["outside_ci"],
                    "terms_compared": agreement["compared"],
                    "n": design.n,
                    "n_events": int(y.sum()),
                }
            )
    out = pd.DataFrame(rows)
    if not out.empty:
        out["p_holm"] = holm(out["p_value"].to_numpy())
        out["verdict"] = [_verdict(r) for r in out.itertuples()]
        out["quantity"] = "adjusted association (design-based, test years)"
    return out


def term_agreement(hgb_terms: dict[str, float], survey: pd.DataFrame) -> dict[str, Any]:
    """Term-by-term comparison of a boosting shape (log-odds contrasts) with survey-model
    log odds ratios: 'confirmed' = same sign and the survey CI excludes 0; 'contradicted' =
    opposite sign and the CI excludes 0; otherwise 'not distinguishable from 0'.  Separately,
    'outside_ci' counts terms whose boosting value lies outside the survey 95% CI (the
    boosting magnitude is not reproduced, whatever the sign)."""
    parts, confirmed, contradicted, outside = [], 0, 0, 0
    for term, hb in hgb_terms.items():
        if term not in survey.index:
            continue
        r = survey.loc[term]
        excludes = r["or_low"] > 1 or r["or_high"] < 1
        if excludes and np.sign(r["coef"]) == np.sign(hb):
            status = "confirmed"
            confirmed += 1
        elif excludes:
            status = "contradicted"
            contradicted += 1
        else:
            status = "not distinguishable from 0"
        if not np.log(r["or_low"]) <= hb <= np.log(r["or_high"]):
            status += "; boosting value outside survey CI"
            outside += 1
        parts.append(
            f"{term}: boosting {hb:+.3f} vs survey {r['coef']:+.3f} "
            f"(OR {r['odds_ratio']:.3g}, {r['or_low']:.3g}-{r['or_high']:.3g}) -> {status}"
        )
    return {
        "detail": "; ".join(parts),
        "confirmed": confirmed,
        "contradicted": contradicted,
        "outside_ci": outside,
        "compared": len(parts),
    }


def _verdict(r: Any) -> str:
    if r.kind == "interaction":
        within = getattr(r, "boosting_within_survey_ci", True)
        magnitude = (
            "; boosting magnitude outside the survey 95% CI"
            if within is not None and not pd.isna(within) and not bool(within)
            else ""
        )
        if r.p_holm >= 0.05:
            return "not confirmed (Holm p>=0.05)" + magnitude
        if r.direction_agrees:
            return "supported (Holm p<0.05, same direction)" + magnitude
        return "not supported: significant but opposite direction"
    if r.p_holm >= 0.05:
        return "not confirmed (Holm p>=0.05)"
    outside = getattr(r, "terms_outside_ci", 0)
    return (
        "departure from the logistic form supported (Holm p<0.05); boosting shape: "
        f"{int(r.terms_confirmed)} of {int(r.terms_compared)} terms confirmed, "
        f"{int(r.terms_contradicted)} contradicted, "
        f"{int(outside) if pd.notna(outside) else 0} outside the survey 95% CI"
    )


def holm(p: np.ndarray) -> np.ndarray:
    p = np.asarray(p, dtype=float)
    o = np.argsort(p)
    m = len(p)
    adj = np.empty(m)
    running = 0.0
    for rank, i in enumerate(o):
        running = max(running, (m - rank) * p[i])
        adj[i] = min(1.0, running)
    return adj


# --------------------------------------------------------------------------------------
# Unknown values that mostly mark hit-and-run crashes (proxy for a post-crash variable)
# --------------------------------------------------------------------------------------
HR_PROXY_SHARE = 0.5  # weighted hit-and-run share above which an 'unknown' is treated as a proxy


def hit_and_run_unknown_shares(train: pd.DataFrame) -> pd.DataFrame:
    """Weighted share of hit-and-run crashes among crashes with each feature unknown/missing.

    A fleeing driver leaves the vehicle's body type, model year, speeding judgement and
    sometimes the crash time unrecorded, so 'unknown' can stand in for the post-crash
    hit-and-run status, which is excluded as a feature (training years, weighted)."""
    w = train["WEIGHT"].to_numpy()
    hr = (train["hit_and_run"] == "yes").to_numpy()
    rows = []
    for c in [*STAGES["pre_crash+circumstance"], *NUMERIC]:
        miss = (train[c].isna() if c in NUMERIC else train[c] == "unknown").to_numpy()
        if not miss.any():
            continue
        rows.append(
            {
                "feature": c,
                "unknown_kind": "missing value" if c in NUMERIC else "level 'unknown'",
                "n_unknown": int(miss.sum()),
                "weighted_share_of_crashes": float(w[miss].sum() / w.sum()),
                "hit_and_run_share_among_unknown": float((w * hr)[miss].sum() / w[miss].sum()),
                "hit_and_run_share_among_known": float((w * hr)[~miss].sum() / w[~miss].sum()),
                "share_of_all_hit_and_run_crashes": float((w * hr)[miss].sum() / (w * hr).sum()),
            }
        )
    out = pd.DataFrame(rows)
    out["treated_as_proxy"] = out["hit_and_run_share_among_unknown"] > HR_PROXY_SHARE
    out["quantity"] = "estimated (design-weighted, training years)"
    return out


def imputed_alcohol_check(train: pd.DataFrame, outcome: str = "fatal") -> pd.DataFrame:
    """Does NHTSA's imputed alcohol (``alcohol_im``) track severity where it was imputed?

    ``alcohol_im`` equals the police-reported value where that is known and is imputed by
    NHTSA where it is unknown; the imputation model is not documented.  If it ignored crash
    severity, the fatal / non-fatal ratio of P(alcohol_im = yes) among *imputed* records would
    be attenuated relative to the ratio among police-reported records; a ratio of similar size
    is what an imputation conditioning on severity (or on severity-related fields) produces,
    in which case the imputed values carry outcome information into a model input.
    Training years, weighted, by period (the police-reported field changed coding in 2019)."""
    rows = []
    for period, years in (("2016-2018", (2016, 2017, 2018)), ("2019-2021", (2019, 2020, 2021))):
        d = train[train["YEAR"].isin(years)]
        for status, mask in (
            ("police-reported (known)", d["alcohol"] != "unknown"),
            ("imputed (police-reported unknown)", d["alcohol"] == "unknown"),
        ):
            g = d[mask.to_numpy()]
            if g.empty:
                continue
            w, y = g["WEIGHT"].to_numpy(), g[outcome].to_numpy()
            yes = (g["alcohol_im"] == "yes").to_numpy()
            p_k = float((w * yes)[y == 1].sum() / w[y == 1].sum()) if (y == 1).any() else np.nan
            p_o = float((w * yes)[y == 0].sum() / w[y == 0].sum()) if (y == 0).any() else np.nan
            rows.append(
                {
                    "period": period,
                    "alcohol_im_source": status,
                    "n": len(g),
                    "n_events": int(y.sum()),
                    "weighted_share_of_crashes": float(w.sum() / d["WEIGHT"].sum()),
                    f"p_alcohol_im_yes_{outcome}": p_k,
                    f"p_alcohol_im_yes_not_{outcome}": p_o,
                    "ratio": p_k / p_o if p_o else np.nan,
                    "quantity": "estimated (design-weighted, training years); diagnostic only",
                }
            )
    return pd.DataFrame(rows)


def blind_unknowns(
    df: pd.DataFrame, train: pd.DataFrame, cols: Sequence[str], rng: np.random.Generator
) -> pd.DataFrame:
    """Replace unknown/missing values of ``cols`` by draws from the weighted training
    distribution of the known values (independent of the outcome and of other features), so
    a model cannot use 'unknown' as a stand-in for hit-and-run.  Unknown stays unknown in
    meaning (it is not recoded to 'no'); it simply carries no information."""
    out = df.copy()
    for c in cols:
        known = (train[c].notna() if c in NUMERIC else train[c] != "unknown").to_numpy()
        miss = (out[c].isna() if c in NUMERIC else out[c] == "unknown").to_numpy()
        if not miss.any():
            continue
        p = train["WEIGHT"].to_numpy()[known]
        vals = train[c].to_numpy()[known]
        out.loc[miss, c] = vals[rng.choice(len(vals), size=int(miss.sum()), p=p / p.sum())]
    return out


# --------------------------------------------------------------------------------------
# Feature-set sensitivity (fatal, circumstance stage)
# --------------------------------------------------------------------------------------
def feature_sensitivity(
    train: pd.DataFrame,
    test: pd.DataFrame,
    outcome: str,
    hgb_params: dict,
    mult: np.ndarray,
    proxy_cols: Sequence[str] = (),
) -> pd.DataFrame:
    """Test performance under alternative feature sets.

    * police-reported behaviours (severity-dependent ascertainment): drop speeding + alcohol;
      police-reported instead of imputed alcohol; add the drug and distraction fields;
    * 'proxy-blind': unknown values that mostly mark hit-and-run crashes (``proxy_cols``) are
      imputed from the weighted training marginal in training *and* test data, so the gap to
      the main feature set bounds how much performance comes from the hit-and-run proxy."""
    stage = "pre_crash+circumstance"
    base = list(STAGES[stage])
    variants: dict[str, tuple[list[str], bool]] = {
        "main feature set": (base, False),
        "without speeding and alcohol_im": (
            [c for c in base if c not in ("speeding", "alcohol_im")],
            False,
        ),
        "plus drugs and distracted (police-reported)": ([*base, "drugs", "distracted"], False),
        "police-reported alcohol instead of alcohol_im": (
            ["alcohol" if c == "alcohol_im" else c for c in base],
            False,
        ),
    }
    if proxy_cols:
        variants["proxy-blind: hit-and-run-dominated unknowns imputed"] = (base, True)
    cidx, cl_stratum = cluster_index(test["PSUSTRAT"].to_numpy(), test["PSU_VAR"].to_numpy())
    y, w = test[outcome].to_numpy(), test["WEIGHT"].to_numpy()
    rng = np.random.default_rng(config.RANDOM_SEED + 5)
    rows: list[dict] = []
    main: dict[str, tuple[dict, dict]] = {}
    for label, (feats, blind) in variants.items():
        check_features([*feats, *NUMERIC], stage)
        tr, te = train, test
        if blind:
            tr = blind_unknowns(train, train, proxy_cols, rng)
            te = blind_unknowns(test, train, proxy_cols, rng)
        pre = Preprocessor(feats).fit(tr)
        params = {k: hgb_params[k] for k in ("learning_rate", "max_leaf_nodes", "min_samples_leaf")}
        for m in (
            fit_logistic(pre, tr, outcome, RIDGE_C, "logit_main", stage),
            fit_hgb(pre, tr, outcome, params, stage),
        ):
            _, _, point, reps = point_and_boot(
                m.predict(te), y, w, cidx, len(cl_stratum), mult, calibration=False
            )
            if label == "main feature set":
                main[m.name] = (point, reps)
            for metric in ("auroc", "average_precision", "brier_skill", "oe_ratio"):
                # Paired difference from the main feature set (same model class, same
                # bootstrap replicates of the same test crashes).
                p0, r0 = main[m.name]
                diff = _summarise(point[metric] - p0[metric], reps[metric] - r0[metric])
                rows.append(
                    {
                        "outcome": outcome,
                        "stage": stage,
                        "variant": label,
                        "imputed_columns": "|".join(proxy_cols) if blind else "",
                        "model": m.name,
                        "metric": metric,
                        **_summarise(point[metric], reps[metric]),
                        "diff_vs_main": diff["estimate"],
                        "diff_ci_low": diff["ci_low"],
                        "diff_ci_high": diff["ci_high"],
                        "quantity": "estimated (design-weighted); difference paired over "
                        "bootstrap replicates",
                    }
                )
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------------------
# Interface: design-based CI for logistic predictions and the prediction function
# --------------------------------------------------------------------------------------
def logistic_vcov(model: FittedModel, train: pd.DataFrame, design: SurveyDesign) -> np.ndarray:
    """Design-based sandwich covariance of (intercept, coefficients) of a weighted,
    L2-penalised sklearn logistic regression (same estimator as survey.SurveyLogit)."""
    est = model.estimator
    x = np.column_stack([np.ones(len(train)), model.pre.onehot(train)])
    beta = np.r_[est.intercept_, est.coef_.ravel()]
    y = train[model.outcome].to_numpy(dtype=float)
    s = _weights(train)
    mu = expit(x @ beta)
    pen = np.full(x.shape[1], 1.0 / est.C)
    pen[0] = 0.0
    bread = (x * (s * mu * (1 - mu))[:, None]).T @ x + np.diag(pen)
    a_inv = np.linalg.inv(bread)
    meat = design.vcov_total(x * (s * (y - mu))[:, None])
    return a_inv @ meat @ a_inv


N_REFITS = 20
N_REFERENCE = 5000  # weight-proportional 2023-2024 crashes used to standardise predictions


def hgb_refits(
    model: FittedModel, train: pd.DataFrame, n_refits: int, rng: np.random.Generator
) -> list[HistGradientBoostingClassifier]:
    """Refits of a boosted model on Rao-Wu bootstrap replicates of the training PSUs (same
    preprocessing, hyper-parameters and number of iterations, no early stopping): the
    spread of their predictions gives a design-based interval for a boosted prediction."""
    cidx, cl_stratum = cluster_index(train["PSUSTRAT"].to_numpy(), train["PSU_VAR"].to_numpy())
    mult = rao_wu_multipliers(cl_stratum, n_refits, rng)
    x = model.pre.ordinal(train)
    y = train[model.outcome].to_numpy()
    w = train["WEIGHT"].to_numpy()
    params = {k: model.params[k] for k in ("learning_rate", "max_leaf_nodes", "min_samples_leaf")}
    out = []
    for r in range(n_refits):
        wr = w * mult[r, cidx]
        keep = wr > 0
        est = HistGradientBoostingClassifier(
            loss="log_loss",
            l2_regularization=1.0,
            max_iter=int(model.params["n_iter"]),
            early_stopping=False,
            categorical_features=model.pre.categorical_mask,
            random_state=config.RANDOM_SEED + r,
            **params,
        )
        est.fit(x[keep], y[keep], sample_weight=wr[keep] / wr[keep].mean())
        out.append(est)
    return out


_BUNDLES: dict[str, dict] = {}
CAVEAT = (
    "Model-predicted probability that a police-reported crash with these recorded "
    "circumstances is fatal (conditional on the crash having happened and been reported). "
    "It is not the probability of having a crash, not a causal effect of changing any "
    "condition, and not a prediction for an individual person. Police-reported behaviours "
    "(speeding, alcohol) are ascertained more thoroughly in severe crashes. The interval "
    "reflects survey sampling uncertainty of the fitted model only (not model "
    "misspecification, measurement error or year-to-year drift); 'model_range' shows how "
    "much the fitted model classes disagree. Absolute levels drift between years and are "
    "less accurate in some subgroups (in the 2023-2024 test years fatal shares were "
    "under-predicted for motorcycle, pedestrian/cyclist and non-hit-and-run crashes and "
    "over-predicted for hit-and-run crashes and for the lowest-risk half of crashes, where "
    "predictions were roughly twice the observed share; see the subgroup and risk-tier "
    "calibration in docs/model_validation.md)."
)


def _load_bundle(outcome: str = "fatal") -> dict:
    if outcome not in _BUNDLES:
        path = MODEL_DIR / f"interface_{outcome}.joblib"
        if not path.exists():
            raise FileNotFoundError(f"{path} missing - run nhtsa_stats.models.severity_ml.run()")
        _BUNDLES[outcome] = joblib.load(path)
    return _BUNDLES[outcome]


def _refuse(reason: str, **extra: Any) -> dict:
    return {"status": "refused", "reason": reason, **extra}


def _logit(p: float) -> float:
    return float(np.log(p / (1 - p)))


def _validate_conditions(conditions: Any, b: dict, stage: str | None) -> dict:
    """Checked, normalised conditions (``{'stage':..., 'cond':...}``) or a refusal dict."""
    if not isinstance(conditions, dict):
        return _refuse("conditions must be a dict")
    allowed = set(b["features"]["pre_crash+circumstance"])
    unknown_keys = sorted(set(conditions) - allowed)
    if unknown_keys:
        return _refuse(
            f"unknown or non-permitted feature(s): {unknown_keys}",
            allowed_features=sorted(allowed),
        )
    has_circ = any(k in CIRCUMSTANCE_CAT for k in conditions)
    stage = stage or ("pre_crash+circumstance" if has_circ else "pre_crash")
    if stage not in b["stages"]:
        return _refuse(f"unknown stage {stage!r}", allowed_stages=list(b["stages"]))
    if stage == "pre_crash" and has_circ:
        return _refuse("crash-configuration variables require stage 'pre_crash+circumstance'")
    pre: Preprocessor = b["stages"][stage]["model"].pre
    cond: dict[str, Any] = {}
    for k, v in conditions.items():
        if k in pre.levels_:
            if k in TRI_COLS and isinstance(v, bool | np.bool_):
                v = "yes" if v else "no"
            if v not in pre.levels_[k]:
                return _refuse(
                    f"value {v!r} for {k!r} was not seen in the training data",
                    allowed_values={k: list(pre.levels_[k])},
                )
        else:  # numeric
            if isinstance(v, bool | np.bool_):
                return _refuse(f"{k} must be a number")
            try:
                v = float(v)
            except (TypeError, ValueError):
                return _refuse(f"{k} must be a number")
            lo, hi = pre.range_[k]
            if not (np.isfinite(v) and lo <= v <= hi):
                return _refuse(f"{k}={v} outside the training range [{lo:g}, {hi:g}]")
        cond[k] = v
    if "crash_type" in cond and "n_vehicles" in cond:
        allowed_n = compatible_n_vehicles(cond["crash_type"])
        if cond["n_vehicles"] not in allowed_n:
            return _refuse(
                f"crash_type {cond['crash_type']!r} cannot occur with n_vehicles "
                f"{cond['n_vehicles']!r} (allowed: {allowed_n})"
            )
    if "speed_limit_mph" in cond:
        band = speed_band([cond["speed_limit_mph"]])[0]
        if "speed_limit" in cond and cond["speed_limit"] != band:
            return _refuse(
                f"speed_limit {cond['speed_limit']!r} is inconsistent with "
                f"speed_limit_mph={cond['speed_limit_mph']:g} (band {band!r})"
            )
        cond["speed_limit"] = band
    return {"stage": stage, "cond": cond}


def compatible_n_vehicles(crash_type: str) -> list[str]:
    """Vehicle counts a crash type can have (both are derived from VE_FORMS)."""
    if str(crash_type).startswith("sv_"):
        return ["1"]
    if str(crash_type).startswith("mv_"):
        return ["2", "3+"]
    return ["1", "2", "3+"]


# Structurally linked columns: when the key is given and the linked column is not, the linked
# value is drawn from reference crashes that share the given value (so no impossible crash,
# e.g. a single-vehicle rollover with three vehicles, enters the average).
_LINKED_FILL: dict[str, str] = {
    "speed_limit": "speed_limit_mph",
    "crash_type": "n_vehicles",
    "n_vehicles": "crash_type",
}


def _scenario(b: dict, cond: dict) -> pd.DataFrame:
    """Reference crashes (weighted 2023-2024 mix) with the given conditions imposed."""
    base: pd.DataFrame = b["reference"]
    ref = base.copy()
    for k, v in cond.items():
        ref[k] = v
    rng = np.random.default_rng(config.RANDOM_SEED)
    for key, linked in _LINKED_FILL.items():
        if key in cond and linked not in cond and linked in ref:
            donors = base.loc[base[key] == cond[key], linked]
            if len(donors):
                ref[linked] = donors.to_numpy()[rng.integers(0, len(donors), len(ref))]
            elif linked == "speed_limit_mph":
                ref[linked] = np.nan
            else:  # no reference crash of this kind: first structurally possible value
                ref[linked] = (
                    compatible_n_vehicles(cond[key])[0]
                    if key == "crash_type"
                    else ("sv_on_roadway" if cond[key] == "1" else "mv_other")
                )
    return ref


def _delta_ci(model: FittedModel, vcov: np.ndarray, ref: pd.DataFrame, df: int) -> dict:
    p = model.predict(ref)
    m = float(p.mean())
    x = np.column_stack([np.ones(len(ref)), model.pre.onehot(ref)])
    g = (x * (p * (1 - p))[:, None]).mean(axis=0)
    se_lg = float(np.sqrt(g @ vcov @ g)) / (m * (1 - m))
    t = float(stats.t.ppf(0.975, df))
    return {
        "probability": m,
        "ci_low": float(expit(_logit(m) - t * se_lg)),
        "ci_high": float(expit(_logit(m) + t * se_lg)),
        "ci_method": "delta method on the logit scale with the design-based (Taylor, "
        f"PSUSTRAT/PSU_VAR) sandwich covariance; t({df})",
    }


def support_flags(
    cond: dict,
    support: dict[str, dict[str, tuple[int, int]]],
    unknown_proxy: dict[str, float] | None = None,
) -> list[str]:
    """Warnings for requested levels that rest on few training (fatal) crashes, and for
    'unknown' inputs that mostly occur in hit-and-run crashes (a post-crash status)."""
    flags = []
    for k, v in cond.items():
        if v == "unknown" and k in (unknown_proxy or {}):
            flags.append(
                f"proxy: {100 * unknown_proxy[k]:.0f}% of training crashes with {k} unknown "
                "were hit-and-run crashes (a post-crash status, not a model input); the "
                "prediction for 'unknown' partly reflects that, not the unrecorded condition"
            )
        n, events = support.get(k, {}).get(v, (None, None))
        if n is None:
            continue
        if events < config.MIN_CELL_N:
            flags.append(
                f"sparse: {k}={v!r} occurs in {n:,} training crashes with only {events} fatal; "
                "the prediction for this level is driven mostly by the model's structure"
            )
    if "oldest_vehicle_age" in cond and cond["oldest_vehicle_age"] > 30:
        flags.append("sparse: oldest-vehicle ages above 30 years are rare in the training data")
    return flags


def predict_crash_fatal_risk(
    conditions: dict, *, stage: str | None = None, bundle: dict | None = None
) -> dict:
    """Model-predicted P(fatal | police-reported crash with ``conditions``) with a 95% interval.

    ``conditions`` maps feature names (``bundle['features']``) to values.  Categorical values
    must be levels seen in training, otherwise the request is refused (``status='refused'``,
    with the allowed values); tri-state variables also accept True/False.
    ``speed_limit_mph`` and ``oldest_vehicle_age`` must lie in the training range.  Features
    that are not given are averaged over the weighted 2023-2024 crash mix
    (standardisation) and listed in ``marginalized_over``.  The stage is
    'pre_crash+circumstance' when crash type / number of vehicles is given, else 'pre_crash'.
    The point estimate comes from the model selected on 2022 for that stage; its interval
    from PSU-bootstrap refits (boosting) or the design-based delta method (logistic).
    Crash type and vehicle count must be compatible (refused otherwise); when only one is
    given the other is drawn from reference crashes that share it.  ``flags`` lists
    requested levels with fewer than 30 training fatal crashes and 'unknown' inputs that
    mostly occur in hit-and-run crashes.
    """
    b = bundle if bundle is not None else _load_bundle("fatal")
    checked = _validate_conditions(conditions, b, stage)
    if checked.get("status") == "refused":
        return checked
    stage, cond = checked["stage"], checked["cond"]
    st = b["stages"][stage]
    primary: FittedModel = st["model"]
    ref = _scenario(b, cond)
    interval = st["interval"]
    if interval["kind"] == "delta":
        res = _delta_ci(primary, interval["vcov"], ref, b["design_df"])
    else:
        m = float(primary.predict(ref).mean())
        res = {"probability": m, "ci_low": np.nan, "ci_high": np.nan, "ci_method": "none"}
        if interval["kind"] == "refits":
            xo = primary.pre.ordinal(ref)
            reps = np.array(
                [_logit(float(e.predict_proba(xo)[:, 1].mean())) for e in interval["estimators"]]
            )
            se = float(reps.std(ddof=1))
            t = float(stats.t.ppf(0.975, len(reps) - 1))
            res.update(
                ci_low=float(expit(_logit(m) - t * se)),
                ci_high=float(expit(_logit(m) + t * se)),
                ci_method=f"{len(reps)} refits on Rao-Wu PSU-bootstrap replicates of the "
                f"training years; SE on the logit scale, t({len(reps) - 1})",
            )
    logistic = _delta_ci(st["logit_main"], st["logit_main_vcov"], ref, b["design_df"])
    by_model = {name: float(fm.predict(ref).mean()) for name, fm in st["others"].items()}
    by_model[primary.name] = res["probability"]
    return {
        "status": "ok",
        "outcome": "fatal",
        **res,
        "flags": support_flags(cond, b.get("support", {}), b.get("unknown_proxy")),
        "model": primary.name,
        "stage": stage,
        "conditions_used": cond,
        "marginalized_over": [f for f in b["features"][stage] if f not in cond],
        "baseline_probability": st["baseline"],
        "relative_to_baseline": res["probability"] / st["baseline"],
        "logistic_main_effects": logistic,
        "model_range": {
            "min": min(by_model.values()),
            "max": max(by_model.values()),
            "by_model": by_model,
        },
        "label": "model-predicted (conditional on a police-reported crash)",
        "population": b["population"],
        "caveat": CAVEAT,
        "test_performance": st["test_performance"],
    }


def build_interface_bundle(
    df: pd.DataFrame,
    design_full: SurveyDesign,
    fitted: dict[tuple[str, str, str], FittedModel],
    selection: dict[tuple[str, str], str],
    metrics: pd.DataFrame,
    outcome: str = "fatal",
    n_refits: int = N_REFITS,
) -> dict:
    """Everything ``predict_crash_fatal_risk`` needs, for the models selected on 2022."""
    train_mask = df["YEAR"].isin(config.TRAIN_YEARS).to_numpy() & df[outcome].notna().to_numpy()
    train = df[train_mask].reset_index(drop=True)
    tdesign = design_full.subset(train_mask)
    recent = df[df["YEAR"].isin(config.TEST_YEARS).to_numpy()]
    ref = weighted_sample(recent, N_REFERENCE, np.random.default_rng(config.RANDOM_SEED + 7))
    ref = ref[[*STAGES["pre_crash+circumstance"], *NUMERIC]].reset_index(drop=True)
    rng = np.random.default_rng(config.RANDOM_SEED + 11)
    stages = {}
    for stage in STAGES:
        sel = selection[(outcome, stage)]
        primary = fitted[(outcome, stage, sel)]
        if sel in LOGISTIC_MODELS:
            interval = {"kind": "delta", "vcov": logistic_vcov(primary, train, tdesign)}
        elif sel == "hgb":
            interval = {"kind": "refits", "estimators": hgb_refits(primary, train, n_refits, rng)}
        else:
            interval = {"kind": "none"}
        perf = metrics[
            (metrics.outcome == outcome)
            & (metrics.stage == stage)
            & (metrics.model == sel)
            & (metrics.domain == "all")
            & (metrics.weighting == "weighted")
            & metrics.metric.isin(
                ["auroc", "average_precision", "brier_skill", "oe_ratio", "calibration_slope"]
            )
        ]
        lm = fitted[(outcome, stage, "logit_main")]
        stages[stage] = {
            "model": primary,
            "interval": interval,
            "logit_main": lm,
            "logit_main_vcov": logistic_vcov(lm, train, tdesign),
            "others": {
                n: fitted[(outcome, stage, n)]
                for n in ("logit_main", "logit_l2", "logit_interact", "hgb")
                if n != sel
            },
            "baseline": float(primary.predict(ref).mean()),
            "test_performance": {
                r.metric: {"estimate": r.estimate, "ci_low": r.ci_low, "ci_high": r.ci_high}
                for r in perf.itertuples()
            },
        }
        log.info("interface bundle: %s/%s uses %s", outcome, stage, sel)
    support = {
        c: {
            lv: (len(g), int(g[outcome].sum())) for lv, g in train.groupby(c, sort=False)[[outcome]]
        }
        for c in STAGES["pre_crash+circumstance"]
    }
    proxy = hit_and_run_unknown_shares(train)
    proxy = proxy[proxy["treated_as_proxy"] & (proxy["unknown_kind"] == "level 'unknown'")]
    return {
        "outcome": outcome,
        "stages": stages,
        "support": support,
        "unknown_proxy": dict(
            zip(
                proxy["feature"],
                proxy["hit_and_run_share_among_unknown"].astype(float),
                strict=True,
            )
        ),
        "features": {s: stage_features(s) for s in STAGES},
        "reference": ref,
        "design_df": int(tdesign.df),
        "population": POPULATION
        + "; unspecified conditions averaged over the weighted 2023-2024 crash mix",
    }


# --------------------------------------------------------------------------------------
# Figures
# --------------------------------------------------------------------------------------
def _figures(
    curves: pd.DataFrame,
    metrics: pd.DataFrame,
    temporal: pd.DataFrame,
    importance: pd.DataFrame,
    pdp: pd.DataFrame,
    ice: pd.DataFrame,
    top_features: list[str],
) -> None:
    import matplotlib.pyplot as plt

    from nhtsa_stats.reporting import figures as fig_style
    from nhtsa_stats.reporting.io import save_figure

    colors = dict(
        zip(
            MODEL_NAMES,
            [fig_style.BLUE, fig_style.ORANGE, fig_style.AQUA, "#eda100", "#e87ba4"],
            strict=True,
        )
    )
    markers = dict(zip(MODEL_NAMES, ["o", "s", "^", "D", "v"], strict=True))

    # Reliability curves (test, weighted and unweighted) per outcome and stage.
    for outcome in OUTCOMES:
        fig, axes = plt.subplots(2, 2, figsize=(10, 9))
        for i, stage in enumerate(STAGES):
            for j, weighting in enumerate(("weighted", "unweighted")):
                ax = axes[i, j]
                sub = curves[
                    (curves.outcome == outcome)
                    & (curves.stage == stage)
                    & (curves.weighting == weighting)
                ]
                lo = max(sub["mean_predicted"].min(), 1e-5)
                hi = max(sub["mean_predicted"].max(), sub["observed_rate"].max())
                ax.plot([lo, hi], [lo, hi], color=fig_style.MUTED, lw=1, ls="--")
                for name in MODEL_NAMES:
                    s = sub[sub.model == name]
                    ax.plot(
                        s["mean_predicted"],
                        s["observed_rate"].clip(lower=lo / 2),
                        marker=markers[name],
                        ms=4,
                        lw=1.5,
                        color=colors[name],
                        label=MODEL_LABELS[name],
                    )
                ax.set_xscale("log")
                ax.set_yscale("log")
                ax.set_xlabel("Mean predicted probability (20 equal-size risk groups)")
                ax.set_ylabel("Observed proportion")
                ax.set_title(f"{stage} - {weighting}", fontsize=10)
        axes[0, 0].legend(loc="upper left")
        fig.suptitle(
            f"Calibration on 2023-2024 CRSS test crashes: outcome '{outcome}'", fontweight="bold"
        )
        fig_style._caption(
            fig,
            "Model-predicted vs observed, conditional on a police-reported crash. Weighted = "
            "population of police-reported crashes; unweighted = CRSS sample, which over-samples "
            "injury crashes (so observed rates exceed population-calibrated predictions).",
        )
        fig.tight_layout()
        save_figure(fig, MODULE, f"calibration_{outcome}")
        plt.close(fig)

    # Model comparison: weighted AUROC and Brier skill with bootstrap CIs.
    fig, axes = plt.subplots(1, 2, figsize=(11, 6))
    sub = metrics[(metrics.domain == "all") & (metrics.weighting == "weighted")]
    ylabels: list[str] = []
    ticks: list[float] = []
    ypos = 0.0
    for outcome in OUTCOMES:
        for stage in STAGES:
            for name in MODEL_NAMES:
                for ax, metric in zip(axes, ("auroc", "brier_skill"), strict=True):
                    r = sub[
                        (sub.outcome == outcome)
                        & (sub.stage == stage)
                        & (sub.model == name)
                        & (sub.metric == metric)
                    ].iloc[0]
                    ax.errorbar(
                        r.estimate,
                        ypos,
                        xerr=[[r.estimate - r.ci_low], [r.ci_high - r.estimate]],
                        fmt=markers[name],
                        color=colors[name],
                        ms=5,
                        capsize=2,
                    )
                ylabels.append(f"{outcome} | {stage} | {MODEL_LABELS[name]}")
                ticks.append(ypos)
                ypos -= 1
            ypos -= 0.6
    for ax, title in zip(axes, ("Weighted AUROC", "Weighted Brier skill score"), strict=True):
        ax.set_title(title, fontsize=10)
        ax.set_yticks(ticks)
    axes[0].set_yticklabels(ylabels, fontsize=7)
    axes[1].set_yticklabels([])
    fig.suptitle("Test performance (2023-2024) with PSU-bootstrap 95% CIs", fontweight="bold")
    fig_style._caption(
        fig,
        "Estimated (design-weighted) performance for police-reported crashes; conditional on a "
        "reported crash. Rao-Wu PSU bootstrap, 200 replicates.",
    )
    fig.tight_layout()
    save_figure(fig, MODULE, "model_comparison")
    plt.close(fig)

    # Temporal stability (trained 2016-2019): AUROC and O/E by year, separate panels.
    for outcome in OUTCOMES:
        fig, axes = plt.subplots(1, 2, figsize=(10, 4))
        for ax, metric, title in zip(
            axes, ("auroc", "oe_ratio"), ("Weighted AUROC", "Observed / expected"), strict=True
        ):
            for k, (stage, name) in enumerate(
                [(s, n) for s in STAGES for n in ("logit_main", "hgb")]
            ):
                s = temporal[
                    (temporal.outcome == outcome)
                    & (temporal.stage == stage)
                    & (temporal.model == name)
                    & (temporal.metric == metric)
                ]
                x = s["eval_year"] + (k - 1.5) * 0.08
                ax.errorbar(
                    x,
                    s["estimate"],
                    yerr=[s["estimate"] - s["ci_low"], s["ci_high"] - s["estimate"]],
                    marker=markers[name],
                    color=colors[name],
                    ls="-" if stage == "pre_crash+circumstance" else ":",
                    capsize=2,
                    ms=4,
                    label=f"{name} ({stage})",
                )
            if metric == "oe_ratio":
                ax.axhline(1, color=fig_style.MUTED, lw=1, ls="--")
            ax.set_title(title, fontsize=10)
            ax.set_xlabel("Evaluation year")
        axes[0].legend(fontsize=7)
        fig.suptitle(
            f"Temporal stability, trained on 2016-2019 CRSS: outcome '{outcome}'",
            fontweight="bold",
        )
        fig.tight_layout()
        save_figure(fig, MODULE, f"temporal_stability_{outcome}")
        plt.close(fig)

    # Permutation importance (fatal), both stages, logit_main vs hgb.
    fig, axes = plt.subplots(1, 2, figsize=(11, 6), sharex=False)
    for ax, stage in zip(axes, STAGES, strict=True):
        sub = importance[importance.stage == stage]
        order = sub[sub.model == "hgb"].sort_values("log_loss_increase_pct")["feature"].tolist()
        for k, name in enumerate(("logit_main", "hgb")):
            s = sub[sub.model == name].set_index("feature").loc[order]
            ax.barh(
                np.arange(len(order)) + (k - 0.5) * 0.38,
                s["log_loss_increase_pct"],
                height=0.36,
                color=colors[name],
                label=MODEL_LABELS[name],
            )
        ax.set_yticks(np.arange(len(order)))
        ax.set_yticklabels(order, fontsize=7)
        ax.set_xlabel("Increase in weighted test log loss when permuted (%)")
        ax.set_title(stage, fontsize=10)
    axes[0].legend()
    fig.suptitle(
        "Permutation importance, outcome 'fatal' (predictive, not causal)", fontweight="bold"
    )
    fig.tight_layout()
    save_figure(fig, MODULE, "permutation_importance_fatal")
    plt.close(fig)

    # Partial dependence for the top features (circumstance stage).
    feats = top_features[:6]
    fig, axes = plt.subplots(2, 3, figsize=(13, 8))
    for ax, feat in zip(axes.ravel(), feats, strict=False):
        sub = pdp[(pdp.feature == feat) & (pdp.stage == "pre_crash+circumstance")]
        numeric = feat in ("speed_limit", "oldest_vehicle_age")
        cats = [v for v in pd.unique(sub["value"]) if not (numeric and v == "unknown")]
        xs = np.arange(len(cats))
        if numeric:
            ice_sub = ice[(ice.feature == feat) & (ice.stage == "pre_crash+circumstance")]
            ice_sub = ice_sub[ice_sub["value"] != "unknown"]
            for _, g in ice_sub.groupby("row"):
                ax.plot(g["value"].astype(float), g["probability"], color=fig_style.GRID, lw=0.6)
        for name in ("logit_main", "logit_interact", "hgb"):
            s = sub[sub.model == name].set_index("value").loc[cats]
            xv = np.array(cats, dtype=float) if numeric else xs
            ax.plot(
                xv,
                s["pd_probability"],
                marker=markers[name],
                color=colors[name],
                lw=1.5 if numeric else 0,
                ms=5,
                label=MODEL_LABELS[name],
            )
        ax.set_yscale("log")
        if not numeric:
            ax.set_xticks(xs)
            ax.set_xticklabels([str(c) for c in cats], rotation=45, ha="right", fontsize=7)
        ax.set_title(feat, fontsize=10)
        ax.set_ylabel("Mean predicted P(fatal)")
    for ax in axes.ravel()[len(feats) :]:
        ax.set_visible(False)
    axes[0, 0].legend(fontsize=7)
    fig.suptitle(
        "Partial dependence on 2023-2024 crashes (model-predicted; grey = boosting ICE curves)",
        fontweight="bold",
    )
    fig.tight_layout()
    save_figure(fig, MODULE, "partial_dependence_fatal")
    plt.close(fig)


# --------------------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------------------
def _save(df: pd.DataFrame, name: str, description: str, **kw: Any) -> None:
    extra = {"module": MODULE_PATH, **kw.pop("extra", {})}
    save_table(
        df,
        MODULE,
        name,
        description=description,
        population=kw.pop("population", POPULATION),
        unit=kw.pop("unit", "crash"),
        inputs=["data/processed/crss_crash.parquet"],
        extra=extra,
        **kw,
    )


def feature_table() -> pd.DataFrame:
    rows = []
    for stage in STAGES:
        check_features(stage_features(stage), stage)
        for f in stage_features(stage):
            src = FEATURE_SOURCE.get(f, f)
            info = h.REGISTRY[src]
            rows.append(
                {
                    "stage": stage,
                    "feature": f,
                    "registry_variable": src,
                    "registry_timing": info.timing,
                    "registry_note": info.note,
                    "type": "numeric (+ missing indicator)"
                    if f in NUMERIC
                    else ("tri-state yes/no/unknown" if f in TRI_COLS else "categorical"),
                    "declared_levels": "" if f in NUMERIC else "|".join(map(str, ALL_LEVELS[f])),
                }
            )
    for f, why in EXCLUDED.items():
        rows.append({"stage": "excluded", "feature": f, "registry_note": why})
    return pd.DataFrame(rows)


def run(n_boot: int = N_BOOT, interpret: bool = True) -> dict[str, Any]:
    """Fit, tune, evaluate and interpret all models; write tables, figures and models."""
    t_start = time.time()
    rng = np.random.default_rng(config.RANDOM_SEED)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    df = load_crashes()
    design_full = SurveyDesign.from_frame(df)
    feats = feature_table()
    _save(feats, "feature_sets", "Model inputs per stage with registry timing; excluded variables")

    fitted: dict[tuple[str, str, str], FittedModel] = {}
    tuning_parts, selection, sel_info = [], {}, {}
    preds_valid, preds_test = {}, {}
    splits: dict[str, dict[str, pd.DataFrame]] = {}
    for outcome in OUTCOMES:
        known = df[outcome].notna().to_numpy()
        split = {
            "train": df[df["YEAR"].isin(config.TRAIN_YEARS).to_numpy() & known],
            "valid": df[df["YEAR"].isin(config.VALID_YEARS).to_numpy() & known],
            "test": df[df["YEAR"].isin(config.TEST_YEARS).to_numpy() & known],
        }
        split = {k: v.reset_index(drop=True) for k, v in split.items()}
        splits[outcome] = split
        for stage in STAGES:
            models, tuning = fit_stage(split["train"], split["valid"], outcome, stage)
            tuning_parts.append(tuning)
            name, info = select_model(tuning)
            selection[(outcome, stage)] = name
            sel_info[f"{outcome}|{stage}"] = {"selected": name, **info}
            for mname, m in models.items():
                fitted[(outcome, stage, mname)] = m
                preds_valid[(outcome, stage, mname)] = m.predict(split["valid"])
                preds_test[(outcome, stage, mname)] = m.predict(split["test"])
                unseen = m.pre.unseen(split["test"])
                if unseen:
                    log.warning(
                        "unseen test categories for %s/%s/%s: %s", outcome, stage, mname, unseen
                    )
                joblib.dump(
                    m,
                    MODEL_DIR / f"{outcome}__{stage.replace('+', '_plus_')}__{mname}.joblib",
                    compress=3,
                )
    tuning_df = pd.concat(tuning_parts, ignore_index=True)
    _save(
        tuning_df,
        "tuning",
        "Hyper-parameter tuning on the 2022 validation year (weighted metrics)",
        method="Models fitted on 2016-2021 with survey weights; chosen = lowest weighted 2022 log loss",
    )
    save_json(sel_info, MODULE, "selection")

    # Test evaluation (one test frame: both outcomes are known on the same crashes).
    test = splits["fatal"]["test"]
    assert splits["ka"]["test"]["case_id"].equals(test["case_id"])
    metrics, diffs, curves, tiers, mult = evaluate(test, preds_test, n_boot, rng)
    method = (
        f"Weighted (WEIGHT) and unweighted metrics; 95% percentile CIs from {n_boot} Rao-Wu "
        "rescaled bootstrap replicates of PSU_VAR within PSUSTRAT (seed config.RANDOM_SEED)"
    )
    _save(
        metrics,
        "metrics_test",
        "Test-set (2023-2024) performance by model, stage, domain",
        method=method,
    )
    _save(
        diffs,
        "paired_differences",
        "Paired bootstrap differences between models / stages on test",
        method=method,
    )
    _save(
        curves,
        "calibration_curves",
        "Reliability curves on test: 20 equal-size risk groups",
        method=method,
    )
    _save(
        tiers,
        "calibration_by_risk_tier",
        "Observed/expected on test within tiers of predicted risk (lowest 50%, 50-80%, top 20%)",
        method="Tiers from the 20 equal-weight reliability groups of each model's test "
        "predictions; " + method,
    )
    valid = splits["fatal"]["valid"]
    thr = threshold_tables(valid, test, preds_valid, preds_test, mult)
    _save(
        thr,
        "thresholds",
        "Confusion matrices on test at risk thresholds fixed on 2022",
        method="Thresholds from weighted 2022 predictions; test counts weighted (per year) and unweighted; "
        + method,
    )
    comparison = metrics[(metrics.domain == "all")].pivot_table(
        index=["outcome", "stage", "model"],
        columns=["weighting", "metric"],
        values="estimate",
    )
    comparison.columns = [f"{m}_{w[0]}" for w, m in comparison.columns]
    comparison = comparison.reset_index()
    comparison["selected_on_2022"] = [
        selection[(r.outcome, r.stage)] == r.model for r in comparison.itertuples()
    ]
    _save(
        comparison,
        "model_comparison",
        "Wide model-comparison table (test, all crashes; _w weighted, _u unweighted)",
    )
    log.info("evaluation done (%.0fs)", time.time() - t_start)

    hgb_params = {(o, s): fitted[(o, s, "hgb")].params for o in OUTCOMES for s in STAGES}
    temporal = temporal_stability(df, hgb_params, n_boot, rng)
    _save(
        temporal,
        "temporal_stability",
        "Models trained on 2016-2019, evaluated on each year 2020-2024",
        method="logit_main and hgb (hyper-parameters from the main tuning); " + method,
    )
    log.info("temporal stability done (%.0fs)", time.time() - t_start)

    proxy = hit_and_run_unknown_shares(splits["fatal"]["train"])
    _save(
        proxy,
        "hit_and_run_proxy",
        "Share of hit-and-run crashes among crashes with each feature unknown (training years)",
        method="Weighted shares; hit_and_run is post-crash and used here only as a diagnostic",
    )
    alc = imputed_alcohol_check(splits["fatal"]["train"])
    _save(
        alc,
        "alcohol_imputation_check",
        "Imputed alcohol (alcohol_im) by fatal status, police-reported vs imputed records",
        method="Weighted P(alcohol_im = yes) among fatal and non-fatal training crashes, "
        "separately where police-reported alcohol is known and where it was imputed",
    )
    proxy_cols = proxy.loc[proxy["treated_as_proxy"], "feature"].tolist()
    sens = feature_sensitivity(
        splits["fatal"]["train"],
        test,
        "fatal",
        hgb_params[("fatal", "pre_crash+circumstance")],
        mult,
        proxy_cols,
    )
    _save(
        sens,
        "feature_sensitivity",
        "Test performance under alternative feature sets (fatal)",
        method=method,
    )
    log.info("feature sensitivity done (%.0fs)", time.time() - t_start)

    out: dict[str, Any] = {
        "metrics": metrics,
        "paired_differences": diffs,
        "thresholds": thr,
        "calibration_by_risk_tier": tiers,
        "temporal": temporal,
        "selection": sel_info,
        "feature_sensitivity": sens,
        "hit_and_run_proxy": proxy,
        "alcohol_imputation_check": alc,
    }
    if interpret:
        out.update(_interpret(df, design_full, splits["fatal"], fitted, rng))
        log.info("interpretation done (%.0fs)", time.time() - t_start)
        bundle = build_interface_bundle(df, design_full, fitted, selection, metrics)
        joblib.dump(bundle, MODEL_DIR / "interface_fatal.joblib", compress=3)
        log.info("interface bundle done (%.0fs)", time.time() - t_start)
        _BUNDLES.pop("fatal", None)
        _figures(
            curves,
            metrics,
            temporal,
            out["importance"],
            out["partial_dependence"],
            out["ice"],
            out["top_features"],
        )
    run_info = {
        "runtime_seconds": round(time.time() - t_start, 1),
        "cpu_seconds": round(time.process_time(), 1),
        "thread_settings": {
            k: os.environ.get(k, "unset")
            for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "POLARS_MAX_THREADS")
        },
        "random_forest_n_jobs": N_JOBS,
        "n_boot": n_boot,
        "seed": config.RANDOM_SEED,
        "train_years": list(config.TRAIN_YEARS),
        "valid_years": list(config.VALID_YEARS),
        "test_years": list(config.TEST_YEARS),
        "outcome_definitions": OUTCOME_DEFINITIONS,
        "rows": {o: {k: len(v) for k, v in s.items()} for o, s in splits.items()},
        "events": {o: {k: int(v[o].sum()) for k, v in s.items()} for o, s in splits.items()},
        "weighted_prevalence": {
            o: {k: float(np.average(v[o], weights=v["WEIGHT"])) for k, v in s.items()}
            for o, s in splits.items()
        },
        "unweighted_prevalence": {
            o: {k: float(v[o].mean()) for k, v in s.items()} for o, s in splits.items()
        },
        "processed_file_mtime_utc": time.strftime(
            "%Y-%m-%dT%H:%M:%SZ",
            time.gmtime((config.PROCESSED_DIR / "crss_crash.parquet").stat().st_mtime),
        ),
        "feature_unknown_shares": {
            c: float((df[c] == "unknown").mean()) for c in [*PRE_CRASH_CAT, *CIRCUMSTANCE_CAT]
        },
    }
    save_json(run_info, MODULE, "run_info")
    out["run_info"] = run_info
    log.info("ml module finished in %.0fs", time.time() - t_start)
    return out


def _interpret(
    df: pd.DataFrame,
    design_full: SurveyDesign,
    split: dict[str, pd.DataFrame],
    fitted: dict[tuple[str, str, str], FittedModel],
    rng: np.random.Generator,
) -> dict[str, Any]:
    outcome = "fatal"
    train, valid, test = split["train"], split["valid"], split["test"]
    reps = representative_values(train)
    imp_parts, pd_parts, ice_parts, impl_parts = [], [], [], []
    ref_test = weighted_sample(test, 3000, np.random.default_rng(config.RANDOM_SEED + 1))
    for stage in STAGES:
        for name in ("logit_main", "hgb"):
            imp_parts.append(
                permutation_importance(fitted[(outcome, stage, name)], test, outcome, 3, rng)
            )
        models = {n: fitted[(outcome, stage, n)] for n in MODEL_NAMES}
        impl_parts.append(
            implied_interactions(
                models, ref_test, stage, np.random.default_rng(config.RANDOM_SEED + 2)
            )
        )
    importance = pd.concat(imp_parts, ignore_index=True)
    log.info("permutation importance and implied interactions done")
    _save(
        importance,
        "permutation_importance",
        "Weighted permutation importance on test (fatal); 3 repeats",
        method="Permute one feature (speed-limit band and mph jointly) across 2023-2024 crashes; "
        "change in weighted log loss and AUROC",
    )
    top = (
        importance[(importance.model == "hgb") & (importance.stage == "pre_crash+circumstance")]
        .sort_values("log_loss_increase", ascending=False)["feature"]
        .tolist()
    )
    for stage in STAGES:
        models = {n: fitted[(outcome, stage, n)] for n in ("logit_main", "logit_interact", "hgb")}
        feats_here = [f for f in top if f in interpretation_features(stage)][:6]
        for f in ("speed_limit", "oldest_vehicle_age"):
            if f not in feats_here:
                feats_here.append(f)
        p_, i_ = partial_dependence(models, ref_test, feats_here, reps)
        pd_parts.append(p_)
        ice_parts.append(i_)
    pdp = pd.concat(pd_parts, ignore_index=True)
    log.info("partial dependence done")
    ice = pd.concat(ice_parts, ignore_index=True)
    _save(pdp, "partial_dependence", "Weighted partial dependence (fatal) on 2023-2024 crashes")
    _save(ice, "ice_curves", "ICE curves of the boosted model for numeric features (30 crashes)")
    implied = pd.concat(impl_parts, ignore_index=True)
    _save(
        implied,
        "implied_interactions",
        "Interactions implied by each model for the pre-specified RQ2 pairs (fatal, test crashes)",
        method="Four-scenario standardisation over 3,000 weight-proportional test crashes",
    )

    # Screening (validation-year reference crashes) and confirmation (test years).
    hgb = fitted[(outcome, "pre_crash+circumstance", "hgb")]
    ref_valid = weighted_sample(valid, 1000, np.random.default_rng(config.RANDOM_SEED + 3))
    screen, _ = interaction_screen(hgb, ref_valid, train, reps, outcome)
    log.info("interaction screen done")
    screen["eligible_for_confirmation"] = (~screen["prespecified_pair"]) & (
        screen["cramers_v_train"] <= 0.5
    )
    _save(
        screen,
        "interaction_screen",
        "Friedman H screen of all feature pairs in the boosted model (fatal, circumstance stage)",
        method="Partial dependence on the log-odds scale over 1,000 weight-proportional 2022 crashes; "
        "pairs with Cramer's V > 0.5 (structurally dependent) or pre-specified are not carried forward",
    )
    candidates = []
    for r in screen[screen["eligible_for_confirmation"]].head(3).itertuples():
        cell = candidate_cells(
            hgb,
            ref_valid,
            train,
            outcome,
            (r.feature_a, r.feature_b),
            reps,
            screening_levels(train, hgb.stage),
        )
        if cell:
            candidates.append({"kind": "interaction", **cell})

    def pd_logit(model: str, feature: str, value: float) -> float:
        sel = pdp[
            (pdp.model == model)
            & (pdp.feature == feature)
            & (pdp.stage == "pre_crash+circumstance")
            & (pdp.value.astype(str) == str(value))
        ]
        return float(sel["pd_logit"].iloc[0]) if len(sel) else np.nan

    def band_logit(band: str) -> float:
        return float(np.mean(hgb.predict_logit(_set_level(ref_valid, "veh_age_band", band, reps))))

    age_shape_hgb = {
        f"veh_age_band[{b}]": band_logit(b) - band_logit(VEH_AGE_LEVELS[0])
        for b in VEH_AGE_LEVELS[1:5]
    }
    age_hgb = pd_logit("hgb", "oldest_vehicle_age", 30) - pd_logit("hgb", "oldest_vehicle_age", 18)
    age_lm = pd_logit("logit_main", "oldest_vehicle_age", 30) - pd_logit(
        "logit_main", "oldest_vehicle_age", 18
    )
    within = [(20, 25), (30, 35), (40, 45), (50, 55), (60, 65), (70, 75)]
    sl_hgb = {
        f"{b}-{a}": pd_logit("hgb", "speed_limit", b) - pd_logit("hgb", "speed_limit", a)
        for a, b in within
    }
    candidates += [
        {
            "kind": "non-linearity",
            "label": "oldest-vehicle age: departure from linearity (age bands beyond a linear term)",
            "numeric": ["veh_age_lin"],
            "terms": [f"veh_age_band[{b}]" for b in VEH_AGE_LEVELS[1:5]],
            "shape_terms": [f"veh_age_band[{b}]" for b in VEH_AGE_LEVELS[1:5]],
            "hgb_summary": age_hgb,
            "hgb_terms": age_shape_hgb,
            "hgb_scale": "boosting PD log-odds, age 30 minus age 18 (logit_main, linear: "
            f"{age_lm:.3f})",
        },
        {
            "kind": "non-linearity",
            "label": "speed limit: differences within the 10-mph bands (25/35/45/55/65/75+ vs lower value)",
            "numeric": [
                "sl_25_in_band",
                "sl_35_in_band",
                "sl_45_in_band",
                "sl_55_in_band",
                "sl_65_in_band",
                "sl_75plus_in_band",
            ],
            "terms": [
                "sl_25_in_band",
                "sl_35_in_band",
                "sl_45_in_band",
                "sl_55_in_band",
                "sl_65_in_band",
                "sl_75plus_in_band",
            ],
            "hgb_summary": sl_hgb["35-30"],
            "hgb_terms": {
                f"sl_{b if b < 75 else '75plus'}_in_band": sl_hgb[f"{b}-{a}"] for a, b in within
            },
            "hgb_scale": "boosting PD log-odds 35 minus 30 mph; all within-band contrasts: "
            + ", ".join(f"{k}: {v:.3f}" for k, v in sl_hgb.items()),
        },
    ]
    confirm = confirm_patterns(
        df,
        design_full,
        outcome,
        "pre_crash+circumstance",
        candidates,
        hgb.pre.impute_["oldest_vehicle_age"],
    )
    _save(
        confirm,
        "pattern_confirmation",
        "Confirmatory survey-weighted tests (2023-2024) of patterns suggested by boosting",
        method="SurveyLogit (Taylor linearisation, PSUSTRAT/PSU_VAR, design df) with all circumstance-stage "
        "covariates + vehicle-age bands; product term or non-linearity terms; Holm across candidates",
        outcome=outcome,
    )
    return {
        "importance": importance,
        "partial_dependence": pdp,
        "ice": ice,
        "implied_interactions": implied,
        "interaction_screen": screen,
        "pattern_confirmation": confirm,
        "top_features": top,
    }
