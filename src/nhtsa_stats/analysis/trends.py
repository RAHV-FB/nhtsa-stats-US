"""The post-2020 rise in crash severity (RQ5, docs/research_plan.md).

Research question
    The weighted fatal share of police-reported crashes (CRSS) rose from about 0.48% in
    2016-2019 to about 0.63% in 2020-2024, and FARS deaths peaked in 2021.  How much of the
    rise is accounted for by a changed *mix* of crash circumstances (composition), and how much
    by higher severity *within* circumstances?  Could a fall in the reporting of minor crashes
    (a denominator change) have produced an apparent rise?

Population and unit
    CRSS police-reported crashes 2016-2024 (unit: crash), outcomes ``fatal`` (K vs O/C/B/A) and
    ``ka`` (K or A vs O/C/B) where maximum severity is known; FARS fatal crashes and deaths
    2016-2024 (census) for corroboration.

Methods
    (a) Year-specific crude weighted fatal shares, and shares *standardised* to the pooled
        2016-2024 covariate distribution (predictive margins of a survey logistic model with
        year + covariates; set A = pre-crash circumstances, set B = A + crash configuration).
    (b) Oaxaca-Blinder-type decomposition on the probability scale with standardised margins.
        Separate survey logistic models are fitted to 2016-2019 (P0) and 2020-2024 (P1).
        p0 and p1 are the fitted (= observed) fatal shares; the counterfactual p01 is the mean
        predicted fatal share of the *2020-24 crashes* under the *2016-19 model*.  Composition
        effect = p01 - p0; within-circumstance effect = p1 - p01.  The reverse reference
        (p10: 2016-19 crashes under the 2020-24 model) and the average of both are reported,
        because the split depends on the reference.  The yearly series of p0-model predictions
        gives a composition-only expected fatal share for every year.
    (c) Detailed composition contributions by factor (Yun 2004 weights): the share of the
        composition effect attributed to factor k is sum_j (xbar1_j - xbar0_j) b0_j over its
        columns divided by the same sum over all columns, where xbar are period means of the
        design-matrix columns and b0 the P0 coefficients.  Factor-level contributions are
        invariant to the reference category; single-level contributions are not.
        Police-reported speeding is binary in the main models (as in every other module); its
        split by type (exceeded limit / too fast for conditions / unspecified) is used for
        prevalence, within-subgroup estimates and one sensitivity decomposition.
    (d) Denominator check: KABCO distribution by year, fatal share among injury (K/KABC) and
        among K+A crashes (insensitive to the reporting of property-damage-only crashes), and an
        exact split of the change in the log fatal share into the change in the number of fatal
        crashes (numerator) and in the number of reported crashes (denominator), with FARS
        fatal-crash counts as an independent census of the numerator.
    (e) FARS composition of fatal crashes and deaths by year (speeding, multiply-imputed driver
        BAC >= .08 with Rubin's rules, pedestrians, motorcyclists, unrestrained light-vehicle
        occupants), with counts and changes 2019 -> 2021 -> 2024.

    Inference: every CRSS quantity is a smooth function of design-based totals, means or
    predictive margins.  Each is linearised (Taylor; for model-based margins including the
    coefficient influence), the influence is summed within the 67 variance PSUs, and contrasts
    between periods and models get variances from the 25-stratum / 67-PSU design (t, 42 df).
    The two periods share PSUs, so their covariance is included.  Linearisation is preferred to
    a PSU bootstrap: it is exact for these smooth statistics up to first order, deterministic
    and uses the same ultimate-cluster variance as every other module.  FARS is a census: its
    counts are reported as observed; CIs on FARS shares describe process (superpopulation)
    variability only (crash-clustered for person-level shares).

Justified interpretation
    "Conditional on a police-reported crash, the change in the mix of recorded circumstances
    between 2016-19 and 2020-24 would by itself have changed the fatal share by X pp under the
    2016-19 severity structure; the remaining Y pp is a rise in the fatal share within
    comparable recorded circumstances."

Not justified
    Attributing the rise to the pandemic, enforcement, traffic volumes, speeds or any other
    cause: none is measured (no exposure, travel-speed or enforcement data).  A within-
    circumstance effect is a residual: it contains changes in unmeasured circumstances, in
    police recording (speeding/alcohol ascertainment, junction/weather/surface coding drifts,
    the 2020 PJ sample change) and in which crashes are reported at all.  Composition effects
    are statistical accounting under the reference model, not causal contributions.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats
from scipy.special import expit

from nhtsa_stats import config
from nhtsa_stats.analysis import data, specs
from nhtsa_stats.analysis.confounding import cluster_design, data_fingerprint
from nhtsa_stats.analysis.survey import (
    MarginSet,
    ModelSpec,
    SurveyDesign,
    SurveyLogit,
    logit_ci,
    svy_mean,
)
from nhtsa_stats.ingestion.cache import load_table
from nhtsa_stats.processing.harmonize import MODEL_ALLOWED_TIMINGS, assert_no_leakage
from nhtsa_stats.reporting.io import save_json, save_table

log = logging.getLogger(__name__)
MODULE = "trends"
RIDGE = 0.01  # as in the severity module (mean-1 normalised weights)
P0_YEARS: tuple[int, ...] = (2016, 2017, 2018, 2019)
P1_YEARS: tuple[int, ...] = (2020, 2021, 2022, 2023, 2024)
OUTCOMES: tuple[str, ...] = ("fatal", "ka")
BASE_COVARIATES = [v for v in specs.PRE_CRASH if v != "YEAR"]
COVARIATE_SETS: dict[str, list[str]] = {
    "A": BASE_COVARIATES,
    "B": [*BASE_COVARIATES, *specs.CIRCUMSTANCE],
}
# Descriptive / sensitivity-only factor: police-reported speeding split by type (exceeded the
# limit or racing; too fast for conditions; unspecified).  The main models keep the binary
# ``speeding`` used by every other module.
EXTRA_FACTORS = ("speeding_type",)
SPEEDING_BY_TYPE = [
    "speeding_type" if c == "speeding" else c for c in [*BASE_COVARIATES, *specs.CIRCUMSTANCE]
]
SET_LABELS = {
    "A": "pre-crash circumstances (PRE_CRASH without year)",
    "B": "pre-crash circumstances + crash configuration (crash type, vehicles)",
}
# Variables with documented coding / reporting drifts across 2016-2024 (docs/audit): RELJCT2
# 'unknown' concentrated in 2019 and interchange codes jumping at 2019-20; weather unknown
# falling after 2020 (CO, PA); vehicle surface 'unknown' rising after 2020.
CODING_DRIFT = ("junction", "weather", "surface")
KABCO = {"O": 0, "C": 1, "B": 2, "A": 3, "K": 4}
CRSS_INPUT = "data/processed/crss_crash.parquet"
FARS_INPUTS = [
    "data/processed/fars_crash.parquet",
    "data/processed/fars_person.parquet",
    "data/interim/FARS/midrvacc (multiply-imputed driver BAC, 10 implicates)",
]
LPV_BODIES = ("car", "suv", "pickup", "van", "light_truck_other")


# --------------------------------------------------------------------------------------
# Data
# --------------------------------------------------------------------------------------
def load() -> tuple[pd.DataFrame, SurveyDesign]:
    """All CRSS crashes (including unknown severity) with the full design."""
    df, design = data.crss_crash(outcome=None, tri_state_cols=specs.CRASH_TRI)
    covs = COVARIATE_SETS["B"]
    keep = [*covs, *EXTRA_FACTORS, "YEAR", "kabco", "fatal", "ka", "fatal_im", "night"]
    df = df[keep].copy()
    df["YEAR"] = df["YEAR"].astype(int)
    for c in ("kabco", "fatal", "ka", "fatal_im", "night"):
        df[c] = df[c].astype(float)
    df["speeding_type"] = df["speeding_type"].fillna("unknown")
    for c in [*covs, *EXTRA_FACTORS]:
        df[c] = pd.Categorical(df[c], categories=specs.CRASH_LEVELS[c])
        if df[c].isna().any():
            raise ValueError(f"{c}: values outside specs.CRASH_LEVELS")
    df["period"] = np.where(df["YEAR"].isin(P0_YEARS), "2016-2019", "2020-2024")
    return df, design


def outcome_frame(
    df: pd.DataFrame, design: SurveyDesign, outcome: str
) -> tuple[pd.DataFrame, SurveyDesign]:
    """Rows with a known outcome; categories trimmed to the levels present (declared order)."""
    keep = df[outcome].notna().to_numpy()
    out = df.loc[keep].reset_index(drop=True)
    for c in [*COVARIATE_SETS["B"], *EXTRA_FACTORS]:
        out[c] = out[c].cat.remove_unused_categories()
    return out, design.subset(keep)


def levels_of(df: pd.DataFrame, var: str) -> list:
    return list(df[var].cat.categories)


# --------------------------------------------------------------------------------------
# Linearisation helpers (values + PSU totals of influence functions)
# --------------------------------------------------------------------------------------
def mean_lin(design: SurveyDesign, y: np.ndarray, domain: np.ndarray) -> tuple[float, np.ndarray]:
    """Weighted domain mean and the PSU totals of its linearised influence."""
    y = np.asarray(y, dtype=float)
    d = np.asarray(domain, dtype=bool) & np.isfinite(y)
    w = design.weight * d
    big_w = w.sum()
    yy = np.where(d, y, 0.0)
    r = float((w * yy).sum() / big_w)
    return r, design.cluster_totals(w * (yy - r) / big_w)[:, 0]


def total_lin(design: SurveyDesign, y: np.ndarray, domain: np.ndarray) -> tuple[float, np.ndarray]:
    z = design.weight * np.where(np.asarray(domain, dtype=bool), np.asarray(y, dtype=float), 0.0)
    return float(z.sum()), design.cluster_totals(z)[:, 0]


def delta_contrast(
    ms: MarginSet, f: Callable[[dict[str, float]], float], rel_step: float = 1e-6
) -> tuple[float, float]:
    """Delta-method estimate and SE of f(values) with central differences on a *relative*
    step.  (MarginSet.contrast uses a fixed absolute forward step, which loses precision for
    inputs on the scale of weighted crash totals, ~10^6-10^7.)"""
    vals = dict(ms.values)
    base = float(f(vals))
    z = np.zeros_like(next(iter(ms.influence.values())), dtype=float)
    for k, v in ms.values.items():
        h = rel_step * max(abs(v), 1e-4)
        vals[k] = v + h
        up = f(vals)
        vals[k] = v - h
        down = f(vals)
        vals[k] = v
        g = (up - down) / (2 * h)
        if g != 0.0:
            z = z + g * ms.influence[k]
    return base, float(np.sqrt(ms.design.vcov_total(z)[0, 0]))


def estimate(ms: MarginSet, f: Callable[[dict[str, float]], float], scale: str) -> dict:
    """Point estimate, SE and 95% CI of f(margins); ``scale`` picks the CI construction:
    'share' (logit), 'ratio' (log) or 'linear' (Wald)."""
    est, se = delta_contrast(ms, f)
    t = ms.design.tcrit()
    if scale == "share":
        lo, hi = logit_ci(est, se, ms.design.df)
    elif scale == "ratio":
        lg, lg_se = delta_contrast(ms, lambda m: float(np.log(f(m))))
        lo, hi = np.exp(lg - t * lg_se), np.exp(lg + t * lg_se)
    else:
        lo, hi = est - t * se, est + t * se
    return {"estimate": est, "se": se, "low": lo, "high": hi}


# --------------------------------------------------------------------------------------
# Period-specific models and cross-period predictive margins
# --------------------------------------------------------------------------------------
@dataclass
class PeriodFit:
    """Coefficients of a period model and the PSU totals of their influence (G x p)."""

    label: str
    spec: ModelSpec
    coef: np.ndarray
    names: list[str]
    coef_totals: np.ndarray
    n: int
    n_events: int
    converged: bool


def fit_period(
    df: pd.DataFrame,
    design: SurveyDesign,
    mask: np.ndarray,
    covariates: Sequence[str],
    outcome: str,
    label: str,
    ridge: float = RIDGE,
) -> PeriodFit:
    """Survey logistic model on ``mask`` rows with linearised coefficient influence.

    The coefficient influence of row i is A^-1 s_i (A = penalised information, s_i = weighted
    score), exactly the quantity SurveyLogit uses for its sandwich variance; it is recomputed
    here from the public fit and checked against ``model.vcov_``.
    """
    spec = ModelSpec(categorical={c: levels_of(df, c) for c in covariates})
    sub = df.loc[mask]
    sub_design = design.subset(mask)
    y = sub[outcome].to_numpy(dtype=float)
    model = SurveyLogit(spec, ridge=ridge).fit(sub, y, sub_design)
    if not model.converged_:
        log.warning("%s model for %s did not converge", label, outcome)
    x, _ = spec.design_matrix(sub)
    mu = expit(x @ model.coef_)
    w = sub_design.weight / sub_design.weight.mean()
    pen = np.full(x.shape[1], ridge)
    pen[0] = 0.0
    a_inv = np.linalg.inv((x * (w * mu * (1 - mu))[:, None]).T @ x + np.diag(pen))
    coef_totals = sub_design.cluster_totals(x * (w * (y - mu))[:, None]) @ a_inv
    check = cluster_design(design).vcov_total(coef_totals)
    if not np.allclose(check, model.vcov_, rtol=1e-5, atol=1e-12):
        raise RuntimeError("coefficient influence does not reproduce SurveyLogit.vcov_")
    return PeriodFit(
        label,
        spec,
        model.coef_.copy(),
        list(model.names_),
        coef_totals,
        len(sub),
        int(y.sum()),
        bool(model.converged_),
    )


def cross_margin(
    fit: PeriodFit,
    df: pd.DataFrame,
    design: SurveyDesign,
    target: np.ndarray,
    setter: Callable[[pd.DataFrame], pd.DataFrame] | None = None,
) -> tuple[float, np.ndarray]:
    """Weighted mean predicted risk of the ``target`` rows under ``fit``'s coefficients.

    The target rows need not be the rows the model was fitted to (e.g. 2020-24 crashes under
    the 2016-19 model).  Influence = covariate-distribution part (target rows) + coefficient
    part (fit rows), returned as PSU totals.
    """
    target = np.asarray(target, dtype=bool)
    tgt = df.loc[target]
    if setter is not None:
        tgt = setter(tgt.copy())
    x, _ = fit.spec.design_matrix(tgt)
    p = expit(x @ fit.coef)
    w = design.weight[target]
    big_w = w.sum()
    m = float(w @ p / big_w)
    t_cov = design.subset(target).cluster_totals(w * (p - m) / big_w)[:, 0]
    g = x.T @ (w * p * (1 - p)) / big_w
    return m, t_cov + fit.coef_totals @ g


# --------------------------------------------------------------------------------------
# (b) Aggregate decomposition
# --------------------------------------------------------------------------------------
@dataclass
class Decomposition:
    label: str
    outcome: str
    covariates: list[str]
    fit0: PeriodFit
    fit1: PeriodFit
    in0: np.ndarray
    in1: np.ndarray
    values: dict[str, float]
    totals: dict[str, np.ndarray]


def decompose(
    df: pd.DataFrame,
    design: SurveyDesign,
    covariates: Sequence[str],
    outcome: str,
    label: str,
    p0_years: Sequence[int] = P0_YEARS,
    p1_years: Sequence[int] = P1_YEARS,
) -> Decomposition:
    in0 = df["YEAR"].isin(p0_years).to_numpy()
    in1 = df["YEAR"].isin(p1_years).to_numpy()
    for c in covariates:
        for name, m in (("P0", in0), ("P1", in1)):
            missing = set(levels_of(df, c)) - set(pd.unique(df.loc[m, c]))
            if missing:
                log.warning("%s: levels %s absent in %s (ridge-determined)", c, missing, name)
    f0 = fit_period(df, design, in0, covariates, outcome, f"{label}:P0")
    f1 = fit_period(df, design, in1, covariates, outcome, f"{label}:P1")
    y = df[outcome].to_numpy(dtype=float)
    vals: dict[str, float] = {}
    tots: dict[str, np.ndarray] = {}
    for key, (fit, tgt) in {
        "p0": (f0, in0),
        "p1": (f1, in1),
        "p01": (f0, in1),
        "p10": (f1, in0),
    }.items():
        vals[key], tots[key] = cross_margin(fit, df, design, tgt)
    vals["obs0"], tots["obs0"] = mean_lin(design, y, in0)
    vals["obs1"], tots["obs1"] = mean_lin(design, y, in1)
    return Decomposition(label, outcome, list(covariates), f0, f1, in0, in1, vals, tots)


DECOMP_QUANTITIES: list[tuple[str, str, str, Callable[[dict[str, float]], float], str]] = [
    # (quantity, label, units, function, CI scale)
    ("observed_share_P0", "estimated", "proportion", lambda m: m["obs0"], "share"),
    ("observed_share_P1", "estimated", "proportion", lambda m: m["obs1"], "share"),
    ("fitted_share_P0", "model-predicted", "proportion", lambda m: m["p0"], "share"),
    ("fitted_share_P1", "model-predicted", "proportion", lambda m: m["p1"], "share"),
    (
        "counterfactual_P1_crashes_P0_model",
        "hypothetical (model-based)",
        "proportion",
        lambda m: m["p01"],
        "share",
    ),
    (
        "counterfactual_P0_crashes_P1_model",
        "hypothetical (model-based)",
        "proportion",
        lambda m: m["p10"],
        "share",
    ),
    ("total_change", "estimated", "percentage points", lambda m: 100 * (m["p1"] - m["p0"]), "lin"),
    (
        "composition_effect_ref_P0",
        "adjusted association (accounting)",
        "percentage points",
        lambda m: 100 * (m["p01"] - m["p0"]),
        "lin",
    ),
    (
        "within_effect_ref_P0",
        "adjusted association (accounting)",
        "percentage points",
        lambda m: 100 * (m["p1"] - m["p01"]),
        "lin",
    ),
    (
        "composition_effect_ref_P1",
        "adjusted association (accounting)",
        "percentage points",
        lambda m: 100 * (m["p1"] - m["p10"]),
        "lin",
    ),
    (
        "within_effect_ref_P1",
        "adjusted association (accounting)",
        "percentage points",
        lambda m: 100 * (m["p10"] - m["p0"]),
        "lin",
    ),
    (
        "composition_effect_average",
        "adjusted association (accounting)",
        "percentage points",
        lambda m: 50 * ((m["p01"] - m["p0"]) + (m["p1"] - m["p10"])),
        "lin",
    ),
    (
        "within_effect_average",
        "adjusted association (accounting)",
        "percentage points",
        lambda m: 50 * ((m["p1"] - m["p01"]) + (m["p10"] - m["p0"])),
        "lin",
    ),
    (
        "composition_share_of_change_ref_P0",
        "adjusted association (accounting)",
        "proportion of total change",
        lambda m: (m["p01"] - m["p0"]) / (m["p1"] - m["p0"]),
        "lin",
    ),
    (
        "composition_share_of_change_ref_P1",
        "adjusted association (accounting)",
        "proportion of total change",
        lambda m: (m["p1"] - m["p10"]) / (m["p1"] - m["p0"]),
        "lin",
    ),
    (
        "composition_share_of_change_average",
        "adjusted association (accounting)",
        "proportion of total change",
        lambda m: 0.5 * ((m["p01"] - m["p0"]) + (m["p1"] - m["p10"])) / (m["p1"] - m["p0"]),
        "lin",
    ),
    ("risk_ratio_total", "estimated", "ratio", lambda m: m["p1"] / m["p0"], "ratio"),
    (
        "risk_ratio_composition_ref_P0",
        "adjusted association (accounting)",
        "ratio",
        lambda m: m["p01"] / m["p0"],
        "ratio",
    ),
    (
        "risk_ratio_within_ref_P0",
        "adjusted association (accounting)",
        "ratio",
        lambda m: m["p1"] / m["p01"],
        "ratio",
    ),
    (
        "composition_share_of_log_rr_ref_P0",
        "adjusted association (accounting)",
        "proportion of log risk ratio",
        lambda m: np.log(m["p01"] / m["p0"]) / np.log(m["p1"] / m["p0"]),
        "lin",
    ),
]


def decomposition_table(dec: Decomposition, design: SurveyDesign) -> pd.DataFrame:
    ms = MarginSet(dec.values, dec.totals, cluster_design(design))
    rows = []
    for name, label, units, f, scale in DECOMP_QUANTITIES:
        rows.append(
            {
                "analysis": dec.label,
                "outcome": dec.outcome,
                "quantity": name,
                "label": label,
                "units": units,
                **estimate(ms, f, scale),
            }
        )
    out = pd.DataFrame(rows)
    out["covariates"] = ",".join(dec.covariates)
    out["n_P0"], out["events_P0"] = dec.fit0.n, dec.fit0.n_events
    out["n_P1"], out["events_P1"] = dec.fit1.n, dec.fit1.n_events
    out["converged"] = dec.fit0.converged and dec.fit1.converged
    return out


# --------------------------------------------------------------------------------------
# (c) Detailed composition contributions (Yun weights)
# --------------------------------------------------------------------------------------
def column_means(
    x: np.ndarray, design: SurveyDesign, mask: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Weighted means of design-matrix columns over ``mask`` and PSU totals (G x p)."""
    w = design.weight[mask]
    xm = x[mask]
    big_w = w.sum()
    mean = xm.T @ w / big_w
    tot = design.subset(mask).cluster_totals((xm - mean) * (w / big_w)[:, None])
    return mean, tot


def detailed_composition(
    dec: Decomposition, df: pd.DataFrame, design: SurveyDesign
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Factor-level (invariant) and column-level (reference-dependent) Yun contributions."""
    spec, names = dec.fit0.spec, dec.fit0.names
    x, _ = spec.design_matrix(df)
    x0, t0 = column_means(x, design, dec.in0)
    x1, t1 = column_means(x, design, dec.in1)
    del x
    p = len(names)
    vals = dict(dec.values)
    tots = dict(dec.totals)
    for j in range(p):
        vals[f"b{j}"], tots[f"b{j}"] = float(dec.fit0.coef[j]), dec.fit0.coef_totals[:, j]
        vals[f"x0_{j}"], tots[f"x0_{j}"] = float(x0[j]), t0[:, j]
        vals[f"x1_{j}"], tots[f"x1_{j}"] = float(x1[j]), t1[:, j]
    ms = MarginSet(vals, tots, cluster_design(design))
    bk = [f"b{j}" for j in range(p)]
    k0 = [f"x0_{j}" for j in range(p)]
    k1 = [f"x1_{j}" for j in range(p)]

    def index_terms(m: dict[str, float]) -> np.ndarray:
        b = np.array([m[k] for k in bk])
        d = np.array([m[k] for k in k1]) - np.array([m[k] for k in k0])
        return d * b

    def contribution(cols: list[int]) -> Callable[[dict[str, float]], float]:
        def f(m: dict[str, float]) -> float:
            terms = index_terms(m)
            return float(100 * terms[cols].sum() / terms.sum() * (m["p01"] - m["p0"]))

        return f

    def weight(cols: list[int]) -> Callable[[dict[str, float]], float]:
        def f(m: dict[str, float]) -> float:
            terms = index_terms(m)
            return float(terms[cols].sum() / terms.sum())

        return f

    def share_total(cols: list[int]) -> Callable[[dict[str, float]], float]:
        def f(m: dict[str, float]) -> float:
            terms = index_terms(m)
            return float(terms[cols].sum() / terms.sum() * (m["p01"] - m["p0"]))

        return lambda m: f(m) / (m["p1"] - m["p0"])

    groups = {v: [j for j, n in enumerate(names) if n.startswith(f"{v}[")] for v in dec.covariates}
    columns = {n: [j] for j, n in enumerate(names) if n != "Intercept"}

    def table(parts: dict[str, list[int]], kind: str) -> pd.DataFrame:
        rows = []
        for name, cols in parts.items():
            c = estimate(ms, contribution(cols), "lin")
            wgt = estimate(ms, weight(cols), "lin")
            sh = estimate(ms, share_total(cols), "lin")
            rows.append(
                {
                    "analysis": dec.label,
                    "outcome": dec.outcome,
                    kind: name,
                    "linear_index_change": float((x1[cols] - x0[cols]) @ dec.fit0.coef[cols]),
                    "contribution_pp": c["estimate"],
                    "contribution_low": c["low"],
                    "contribution_high": c["high"],
                    "share_of_composition_effect": wgt["estimate"],
                    "share_of_composition_low": wgt["low"],
                    "share_of_composition_high": wgt["high"],
                    "share_of_total_change": sh["estimate"],
                    "share_of_total_low": sh["low"],
                    "share_of_total_high": sh["high"],
                    "coding_drift_variable": name.split("[")[0] in CODING_DRIFT,
                }
            )
        return pd.DataFrame(rows)

    by_factor = table(groups, "factor")
    by_column = table(columns, "term")
    by_column["mean_P0"] = [float(x0[c[0]]) for c in columns.values()]
    by_column["mean_P1"] = [float(x1[c[0]]) for c in columns.values()]
    by_column["coef_P0"] = [float(dec.fit0.coef[c[0]]) for c in columns.values()]
    return by_factor.sort_values("contribution_pp", ascending=False), by_column


# --------------------------------------------------------------------------------------
# Within-circumstance change by subgroup
# --------------------------------------------------------------------------------------
SUBGROUPS: dict[str, Callable[[pd.DataFrame], np.ndarray]] = {
    "all crashes": lambda d: np.ones(len(d), dtype=bool),
    "speeding-related": lambda d: (d["speeding"] == "yes").to_numpy(),
    "speeding: exceeded limit or racing": lambda d: (
        d["speeding_type"] == "exceeded_limit_or_racing"
    ).to_numpy(),
    "speeding: too fast for conditions": lambda d: (
        d["speeding_type"] == "too_fast_for_conditions"
    ).to_numpy(),
    "speeding: type unspecified": lambda d: (
        d["speeding_type"] == "speeding_unspecified"
    ).to_numpy(),
    "alcohol involved (imputed)": lambda d: (d["alcohol_im"] == "yes").to_numpy(),
    "no speeding and no alcohol recorded": lambda d: (
        (d["speeding"] == "no") & (d["alcohol_im"] == "no")
    ).to_numpy(),
    "motorcycle involved": lambda d: (d["any_motorcycle"] == "yes").to_numpy(),
    "pedestrian crash": lambda d: (d["crash_type"] == "pedestrian").to_numpy(),
    "single-vehicle crash": lambda d: (d["n_vehicles"] == "1").to_numpy(),
    "night 21:00-05:59": lambda d: (d["night"] == 1).to_numpy(),
    "dark (any lighting)": lambda d: (
        d["light"].isin(["dark_lighted", "dark_not_lighted", "dark_unknown_lighting"]).to_numpy()
    ),
    "speed limit 50+ mph": lambda d: d["speed_limit"].isin(["50-55", "60-65", "70+"]).to_numpy(),
    "rural PSU": lambda d: (d["urbanicity"] == "rural").to_numpy(),
    "interstate": lambda d: (d["interstate"] == "yes").to_numpy(),
    "driver aged 15-20 involved": lambda d: (d["young_driver"] == "yes").to_numpy(),
    "driver aged 65+ involved": lambda d: (d["older_driver"] == "yes").to_numpy(),
}


def within_by_subgroup(dec: Decomposition, df: pd.DataFrame, design: SurveyDesign) -> pd.DataFrame:
    """Predicted outcome share of the pooled (2016-24) crashes of each subgroup under the P1
    model vs the P0 model: within-circumstance change standardised to a common mix."""
    y = df[dec.outcome].to_numpy(dtype=float)
    rows = []
    for name, sel in SUBGROUPS.items():
        g = sel(df)
        if g.sum() < config.MIN_CELL_N:
            continue
        vals, tots = {}, {}
        vals["q0"], tots["q0"] = cross_margin(dec.fit0, df, design, g)
        vals["q1"], tots["q1"] = cross_margin(dec.fit1, df, design, g)
        vals["o0"], tots["o0"] = mean_lin(design, y, g & dec.in0)
        vals["o1"], tots["o1"] = mean_lin(design, y, g & dec.in1)
        ms = MarginSet(vals, tots, cluster_design(design))
        rr = estimate(ms, lambda m: m["q1"] / m["q0"], "ratio")
        rd = estimate(ms, lambda m: 100 * (m["q1"] - m["q0"]), "lin")
        crr = estimate(ms, lambda m: m["o1"] / m["o0"], "ratio")
        n0, n1 = int((g & dec.in0).sum()), int((g & dec.in1).sum())
        e0, e1 = int(y[g & dec.in0].sum()), int(y[g & dec.in1].sum())
        rows.append(
            {
                "analysis": dec.label,
                "outcome": dec.outcome,
                "subgroup": name,
                "n_P0": n0,
                "events_P0": e0,
                "n_P1": n1,
                "events_P1": e1,
                "observed_share_P0": vals["o0"],
                "observed_share_P1": vals["o1"],
                "crude_rr": crr["estimate"],
                "crude_rr_low": crr["low"],
                "crude_rr_high": crr["high"],
                "std_share_P0_model": vals["q0"],
                "std_share_P1_model": vals["q1"],
                "within_rr": rr["estimate"],
                "within_rr_low": rr["low"],
                "within_rr_high": rr["high"],
                "within_rd_pp": rd["estimate"],
                "within_rd_low": rd["low"],
                "within_rd_high": rd["high"],
                "flag": "suppressed" if min(e0, e1) < 5 or min(n0, n1) < config.MIN_CELL_N else "",
            }
        )
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------------------
# (a) Annual crude, standardised and composition-only expected shares
# --------------------------------------------------------------------------------------
def annual_series(
    df: pd.DataFrame,
    design: SurveyDesign,
    outcome: str,
    decs: dict[str, Decomposition],
) -> pd.DataFrame:
    years = sorted(df["YEAR"].unique())
    y = df[outcome].to_numpy(dtype=float)
    yr = df["YEAR"].to_numpy()
    n_years_p0 = [yy for yy in years if yy in P0_YEARS]
    base = pd.DataFrame(
        {
            "YEAR": years,
            "n": [int((yr == yy).sum()) for yy in years],
            "events": [int(y[yr == yy].sum()) for yy in years],
        }
    )
    cols: dict[str, list] = {}
    vals: dict[str, float] = {}
    tots: dict[str, np.ndarray] = {}
    for yy in years:
        vals[f"crude{yy}"], tots[f"crude{yy}"] = mean_lin(design, y, yr == yy)
        vals[f"N{yy}"], tots[f"N{yy}"] = total_lin(design, np.ones(len(df)), yr == yy)
    for s, dec in decs.items():
        spec = ModelSpec(
            categorical={"YEAR": years, **{c: levels_of(df, c) for c in dec.covariates}}
        )
        model = SurveyLogit(spec, ridge=RIDGE).fit(df, y, design)
        scen = {str(yy): (lambda d, yy=yy: d.assign(YEAR=yy)) for yy in years}
        ms = model.margins(df, scen)
        for yy in years:
            vals[f"adj{s}_{yy}"] = ms.values[str(yy)]
            tots[f"adj{s}_{yy}"] = design.cluster_totals(ms.influence[str(yy)])[:, 0]
            vals[f"exp{s}_{yy}"], tots[f"exp{s}_{yy}"] = cross_margin(
                dec.fit0, df, design, yr == yy
            )
        del model, ms
    ms = MarginSet(vals, tots, cluster_design(design))

    def baseline(m: dict[str, float], prefix: str) -> float:
        """Unweighted mean of the 2016-2019 yearly values (each year counts equally)."""
        return float(np.mean([m[f"{prefix}{q}"] for q in n_years_p0]))

    for yy in years:
        n_est = estimate(ms, lambda m, yy=yy: m[f"N{yy}"], "lin")
        c = estimate(ms, lambda m, yy=yy: m[f"crude{yy}"], "share")
        rec = {
            "weighted_crashes_known_severity": n_est["estimate"],
            "weighted_crashes_known_severity_low": n_est["low"],
            "weighted_crashes_known_severity_high": n_est["high"],
            "crude_share": c["estimate"],
            "crude_low": c["low"],
            "crude_high": c["high"],
            "crude_rse": c["se"] / c["estimate"],
        }
        r = estimate(ms, lambda m, yy=yy: m[f"crude{yy}"] / baseline(m, "crude"), "ratio")
        rec.update(
            crude_rr_vs_2016_19=r["estimate"], crude_rr_low=r["low"], crude_rr_high=r["high"]
        )
        for s in decs:
            a = estimate(ms, lambda m, yy=yy, s=s: m[f"adj{s}_{yy}"], "share")
            ar = estimate(
                ms, lambda m, yy=yy, s=s: m[f"adj{s}_{yy}"] / baseline(m, f"adj{s}_"), "ratio"
            )
            ex = estimate(ms, lambda m, yy=yy, s=s: m[f"exp{s}_{yy}"], "share")
            oe = estimate(ms, lambda m, yy=yy, s=s: m[f"crude{yy}"] / m[f"exp{s}_{yy}"], "ratio")
            rec.update(
                {
                    f"adj{s}_share": a["estimate"],
                    f"adj{s}_low": a["low"],
                    f"adj{s}_high": a["high"],
                    f"adj{s}_rr_vs_2016_19": ar["estimate"],
                    f"adj{s}_rr_low": ar["low"],
                    f"adj{s}_rr_high": ar["high"],
                    f"expected{s}_P0_model": ex["estimate"],
                    f"expected{s}_low": ex["low"],
                    f"expected{s}_high": ex["high"],
                    f"obs_over_expected{s}": oe["estimate"],
                    f"obs_over_expected{s}_low": oe["low"],
                    f"obs_over_expected{s}_high": oe["high"],
                }
            )
        for k, v in rec.items():
            cols.setdefault(k, []).append(v)
    out = pd.concat([base, pd.DataFrame(cols)], axis=1)
    out.insert(1, "outcome", outcome)
    out["flag"] = np.where(
        out["n"] < config.MIN_CELL_N,
        "suppressed",
        np.where(out["crude_rse"] > config.MAX_RSE, "unstable", ""),
    )
    return out


# --------------------------------------------------------------------------------------
# Prevalence of circumstances by period (descriptive input to the composition effect)
# --------------------------------------------------------------------------------------
def prevalence_change(df: pd.DataFrame, design: SurveyDesign) -> pd.DataFrame:
    in0 = df["YEAR"].isin(P0_YEARS).to_numpy()
    in1 = df["YEAR"].isin(P1_YEARS).to_numpy()
    rows = []
    for var in [*COVARIATE_SETS["B"], *EXTRA_FACTORS]:
        for lv in levels_of(df, var):
            ind = (df[var] == lv).to_numpy(dtype=float)
            vals, tots = {}, {}
            vals["s0"], tots["s0"] = mean_lin(design, ind, in0)
            vals["s1"], tots["s1"] = mean_lin(design, ind, in1)
            ms = MarginSet(vals, tots, cluster_design(design))
            d = estimate(ms, lambda m: 100 * (m["s1"] - m["s0"]), "lin")
            n0, n1 = int(ind[in0].sum()), int(ind[in1].sum())
            rows.append(
                {
                    "factor": var,
                    "level": lv,
                    "n_P0": n0,
                    "n_P1": n1,
                    "share_P0": vals["s0"],
                    "share_P1": vals["s1"],
                    "change_pp": d["estimate"],
                    "change_low": d["low"],
                    "change_high": d["high"],
                    "coding_drift_variable": var in CODING_DRIFT,
                    "in_main_models": var in COVARIATE_SETS["B"],
                    "flag": "suppressed" if min(n0, n1) < config.MIN_CELL_N else "",
                }
            )
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------------------
# (d) KABCO distribution and the numerator / denominator split
# --------------------------------------------------------------------------------------
def kabco_marginset(df: pd.DataFrame, design: SurveyDesign) -> MarginSet:
    """Weighted totals of crashes by year and maximum severity class (U = unknown)."""
    yr = df["YEAR"].to_numpy()
    kab = df["kabco"].to_numpy()
    vals, tots = {}, {}
    for yy in sorted(set(yr)):
        dom = yr == yy
        for cls, code in KABCO.items():
            vals[f"{cls}|{yy}"], tots[f"{cls}|{yy}"] = total_lin(design, kab == code, dom)
        vals[f"U|{yy}"], tots[f"U|{yy}"] = total_lin(design, np.isnan(kab), dom)
    return MarginSet(vals, tots, cluster_design(design))


def _known(m: dict[str, float], yy: int) -> float:
    return sum(m[f"{c}|{yy}"] for c in KABCO)


def _period_mean(m: dict[str, float], cls: str, years: Sequence[int]) -> float:
    """Annual average of one class ('N' = all known severities; 'KA', 'KABC' = sums)."""
    if cls == "N":
        return float(np.mean([_known(m, yy) for yy in years]))
    return float(np.mean([sum(m[f"{c}|{yy}"] for c in cls) for yy in years]))


def kabco_by_year(ms: MarginSet, df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    yr = df["YEAR"].to_numpy()
    for yy in sorted(set(yr)):
        rec: dict = {"YEAR": yy, "n_sample": int((yr == yy).sum())}
        for cls in [*KABCO, "U"]:
            e = estimate(ms, lambda m, c=cls, yy=yy: m[f"{c}|{yy}"], "lin")
            rec[f"{cls}_crashes"] = e["estimate"]
            rec[f"{cls}_crashes_low"] = e["low"]
            rec[f"{cls}_crashes_high"] = e["high"]
        for cls in KABCO:
            s = estimate(ms, lambda m, c=cls, yy=yy: m[f"{c}|{yy}"] / _known(m, yy), "share")
            rec[f"{cls}_share_of_known"] = s["estimate"]
            rec[f"{cls}_share_low"] = s["low"]
            rec[f"{cls}_share_high"] = s["high"]
        specs_ = {
            "K_share_of_injury_KABC": lambda m, yy=yy: (
                m[f"K|{yy}"] / sum(m[f"{c}|{yy}"] for c in "KABC")
            ),
            "K_share_of_KA": lambda m, yy=yy: m[f"K|{yy}"] / (m[f"K|{yy}"] + m[f"A|{yy}"]),
            "KA_share_of_injury_KABC": lambda m, yy=yy: (
                (m[f"K|{yy}"] + m[f"A|{yy}"]) / sum(m[f"{c}|{yy}"] for c in "KABC")
            ),
            "injury_share_of_known": lambda m, yy=yy: (
                sum(m[f"{c}|{yy}"] for c in "KABC") / _known(m, yy)
            ),
            "unknown_share_of_all": lambda m, yy=yy: m[f"U|{yy}"] / (_known(m, yy) + m[f"U|{yy}"]),
        }
        for name, f in specs_.items():
            s = estimate(ms, f, "share")
            rec[name] = s["estimate"]
            rec[f"{name}_low"] = s["low"]
            rec[f"{name}_high"] = s["high"]
        rows.append(rec)
    return pd.DataFrame(rows)


def numerator_denominator(ms: MarginSet, fars_counts: pd.Series) -> pd.DataFrame:
    """Exact split: log(share1/share0) = log(K1/K0) - log(N1/N0), annual averages.

    K = crashes with a fatality, N = crashes with known maximum severity (the fatal-share
    denominator).  Comparisons: 2020-24 vs 2016-19 and each year 2020-2024 vs 2016-19.
    """
    rows = []
    comparisons = {"2020-2024 vs 2016-2019": P1_YEARS}
    comparisons.update({f"{yy} vs 2016-2019": (yy,) for yy in P1_YEARS})
    for comp, yrs in comparisons.items():

        def k(m, ys=yrs):
            return _period_mean(m, "K", ys)

        def n(m, ys=yrs):
            return _period_mean(m, "N", ys)

        def k0(m):
            return _period_mean(m, "K", P0_YEARS)

        def n0(m):
            return _period_mean(m, "N", P0_YEARS)

        items: list[tuple[str, str, str, Callable, str]] = [
            ("fatal_crashes_per_year_P0", "estimated", "crashes/year", k0, "lin"),
            ("fatal_crashes_per_year_comparison", "estimated", "crashes/year", k, "lin"),
            ("crashes_known_severity_per_year_P0", "estimated", "crashes/year", n0, "lin"),
            ("crashes_known_severity_per_year_comparison", "estimated", "crashes/year", n, "lin"),
            ("fatal_share_P0", "estimated", "proportion", lambda m: k0(m) / n0(m), "share"),
            ("fatal_share_comparison", "estimated", "proportion", lambda m: k(m) / n(m), "share"),
            (
                "ratio_fatal_share",
                "estimated",
                "ratio",
                lambda m: (k(m) / n(m)) / (k0(m) / n0(m)),
                "ratio",
            ),
            (
                "ratio_fatal_crashes_numerator",
                "estimated",
                "ratio",
                lambda m: k(m) / k0(m),
                "ratio",
            ),
            (
                "ratio_reported_crashes_denominator",
                "estimated",
                "ratio",
                lambda m: n(m) / n0(m),
                "ratio",
            ),
            (
                "numerator_share_of_log_rise",
                "estimated",
                "proportion of log ratio",
                lambda m: np.log(k(m) / k0(m)) / np.log((k(m) / n(m)) / (k0(m) / n0(m))),
                "lin",
            ),
            (
                "denominator_share_of_log_rise",
                "estimated",
                "proportion of log ratio",
                lambda m: -np.log(n(m) / n0(m)) / np.log((k(m) / n(m)) / (k0(m) / n0(m))),
                "lin",
            ),
            (
                "hypothetical_share_if_denominator_constant",
                "hypothetical",
                "proportion",
                lambda m: k(m) / n0(m),
                "share",
            ),
        ]
        for cls in KABCO:
            items.append(
                (
                    f"change_{cls}_crashes_per_year",
                    "estimated",
                    "crashes/year",
                    lambda m, c=cls, ys=yrs: _period_mean(m, c, ys) - _period_mean(m, c, P0_YEARS),
                    "lin",
                )
            )
            items.append(
                (
                    f"ratio_{cls}_crashes",
                    "estimated",
                    "ratio",
                    lambda m, c=cls, ys=yrs: _period_mean(m, c, ys) / _period_mean(m, c, P0_YEARS),
                    "ratio",
                )
            )
        for name, label, units, f, scale in items:
            rows.append(
                {
                    "comparison": comp,
                    "quantity": name,
                    "label": label,
                    "units": units,
                    **estimate(ms, f, scale),
                }
            )
        fars0 = float(fars_counts.loc[list(P0_YEARS)].mean())
        fars1 = float(fars_counts.loc[list(yrs)].mean())
        # Conditional shares that do not involve O (property-damage-only) or C crashes, and the
        # fatal share with the FARS census count as numerator (CI: CRSS denominator only).
        extra: list[tuple[str, str, str, Callable, str]] = [
            (
                "ratio_K_share_of_injury_KABC",
                "estimated",
                "ratio",
                lambda m, ys=yrs: (
                    (_period_mean(m, "K", ys) / _period_mean(m, "KABC", ys))
                    / (_period_mean(m, "K", P0_YEARS) / _period_mean(m, "KABC", P0_YEARS))
                ),
                "ratio",
            ),
            (
                "ratio_K_share_of_KA",
                "estimated",
                "ratio",
                lambda m, ys=yrs: (
                    (_period_mean(m, "K", ys) / _period_mean(m, "KA", ys))
                    / (_period_mean(m, "K", P0_YEARS) / _period_mean(m, "KA", P0_YEARS))
                ),
                "ratio",
            ),
            (
                "ratio_fatal_share_FARS_numerator_CRSS_denominator",
                "estimated (FARS census count / CRSS estimate)",
                "ratio",
                lambda m, ys=yrs, r=fars1 / fars0: (
                    r / (_period_mean(m, "N", ys) / _period_mean(m, "N", P0_YEARS))
                ),
                "ratio",
            ),
        ]
        for name, label, units, f, scale in extra:
            rows.append(
                {
                    "comparison": comp,
                    "quantity": name,
                    "label": label,
                    "units": units,
                    **estimate(ms, f, scale),
                }
            )
        rows.append(
            {
                "comparison": comp,
                "quantity": "FARS_ratio_fatal_crashes (census)",
                "label": "observed",
                "units": "ratio",
                "estimate": fars1 / fars0,
                "se": 0.0,
                "low": np.nan,
                "high": np.nan,
            }
        )
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------------------
# (e) FARS composition of fatal crashes and deaths
# --------------------------------------------------------------------------------------
def rubin_share(flags: np.ndarray) -> tuple[float, float, float]:
    """Rubin's rules for a proportion from an (n x M) matrix of 0/1 implicate values.

    Returns (estimate, total SE, degrees of freedom).  Within-imputation variance is the
    binomial (process) variance q(1-q)/n of each implicate.
    """
    flags = np.asarray(flags, dtype=float)
    n, m_imp = flags.shape
    q = flags.mean(axis=0)
    u_bar = float(np.mean(q * (1 - q) / n))
    b = float(q.var(ddof=1)) if m_imp > 1 else 0.0
    t = u_bar + (1 + 1 / m_imp) * b
    if b > 0 and u_bar > 0:
        r = (1 + 1 / m_imp) * b / u_bar
        dof = (m_imp - 1) * (1 + 1 / r) ** 2
    else:
        dof = np.inf
    return float(q.mean()), float(np.sqrt(t)), float(dof)


def _srs_share(ind: np.ndarray) -> tuple[float, float, float]:
    """Share with a binomial (process-variability) logit CI; FARS rows are a census."""
    ind = np.asarray(ind, dtype=float)
    d = SurveyDesign.from_arrays(np.ones(len(ind)), None, None)
    e = svy_mean(d, ind)
    lo, hi = logit_ci(e.estimate, e.se, e.df)
    return e.estimate, lo, hi


def fars_composition() -> tuple[pd.DataFrame, pd.DataFrame]:
    crash = data.fars_crash()
    per = data.fars_person()
    mi = load_table("FARS", "midrvacc", None, ["ST_CASE", *[f"A{i}" for i in range(1, 11)]])
    mi = mi.to_pandas().rename(columns={"ST_CASE": "case_id"})
    killed = per[per["killed"] == 1]
    occ = killed[killed["ptype"].isin(["driver", "passenger"])]
    lpv = occ[occ["body"].isin(LPV_BODIES)]
    rows = []
    for yy, g in crash.groupby("YEAR"):
        k = killed[killed["YEAR"] == yy]
        lv = lpv[lpv["YEAR"] == yy]
        m = mi[mi["YEAR"] == yy]
        flags = (m[[f"A{i}" for i in range(1, 11)]].to_numpy() >= 8).astype(float)
        bac, bac_se, bac_df = rubin_share(flags)
        tcrit = float(stats.t.ppf(0.975, bac_df)) if np.isfinite(bac_df) else 1.96
        spd = g["speeding"].to_numpy(dtype=float)
        spd_share, spd_lo, spd_hi = _srs_share(spd == 1)
        known = lv["restraint"].isin(["belted", "none"]).to_numpy()
        unr = (lv["restraint"] == "none").to_numpy()
        if known.any():
            lvk = lv[known].reset_index(drop=True)
            e = svy_mean(data.fars_design(lvk), (lvk["restraint"] == "none").to_numpy(float))
            unr_share = e.estimate
            unr_lo, unr_hi = logit_ci(e.estimate, e.se, e.df)
        else:
            unr_share = unr_lo = unr_hi = np.nan
        ped_share, ped_lo, ped_hi = _srs_share(g["any_pedestrian"].to_numpy() == 1)
        mc_d = ((k["body"] == "motorcycle") & k["ptype"].isin(["driver", "passenger"])).to_numpy()
        rows.append(
            {
                "YEAR": yy,
                "fatal_crashes": len(g),
                "deaths": int(g["FATALS"].sum()),
                "speeding_crashes": int((spd == 1).sum()),
                "speeding_unknown_crashes": int(np.isnan(spd).sum()),
                "speeding_share": spd_share,
                "speeding_share_low": spd_lo,
                "speeding_share_high": spd_hi,
                "speeding_share_of_known": float(np.nanmean(spd)),
                "crashes_with_mi_bac_record": len(m),
                "bac08_share_mi": bac,
                "bac08_share_low": bac - tcrit * bac_se,
                "bac08_share_high": bac + tcrit * bac_se,
                "bac08_crashes_mi": bac * len(m),
                "pedestrian_crashes": int((g["any_pedestrian"] == 1).sum()),
                "pedestrian_crash_share": ped_share,
                "pedestrian_crash_share_low": ped_lo,
                "pedestrian_crash_share_high": ped_hi,
                "pedestrian_deaths": int((k["ptype"] == "pedestrian").sum()),
                "motorcycle_crashes": int((g["any_motorcycle"] == 1).sum()),
                "motorcyclist_deaths": int(mc_d.sum()),
                "lpv_occupant_deaths": len(lv),
                "lpv_unrestrained_deaths": int(unr.sum()),
                "lpv_restraint_unknown_deaths": int(
                    (~lv["restraint"].isin(["belted", "none", "child_restraint"])).sum()
                ),
                "lpv_unrestrained_share_of_known": unr_share,
                "lpv_unrestrained_share_low": unr_lo,
                "lpv_unrestrained_share_high": unr_hi,
                "night_crashes": int((g["night"] == 1).sum()),
                "dark_crashes": int((g["dark"] == 1).sum()),
                "rural_road_crashes": int((g["rural"] == 1).sum()),
            }
        )
    comp = pd.DataFrame(rows)
    return comp, fars_changes(comp)


FARS_COUNTS = {
    "fatal_crashes": "fatal_crashes",
    "deaths": "deaths",
    "speeding_crashes": "fatal_crashes",
    "bac08_crashes_mi": "fatal_crashes",
    "pedestrian_crashes": "fatal_crashes",
    "motorcycle_crashes": "fatal_crashes",
    "night_crashes": "fatal_crashes",
    "pedestrian_deaths": "deaths",
    "motorcyclist_deaths": "deaths",
    "lpv_occupant_deaths": "deaths",
    "lpv_unrestrained_deaths": "deaths",
}


def fars_changes(comp: pd.DataFrame) -> pd.DataFrame:
    """Counts in 2019, 2021, 2024 and their changes; each count's change as a share of the
    change in all fatal crashes (or all deaths).  Categories overlap, so shares do not add."""
    c = comp.set_index("YEAR")
    rows = []
    for col, total in FARS_COUNTS.items():
        rec = {"indicator": col, "relative_to": total}
        for yy in (2019, 2021, 2024):
            rec[str(yy)] = float(c.loc[yy, col])
        for a, b in ((2019, 2021), (2021, 2024), (2019, 2024)):
            d = c.loc[b, col] - c.loc[a, col]
            dt = c.loc[b, total] - c.loc[a, total]
            rec[f"change_{a}_{b}"] = float(d)
            rec[f"pct_change_{a}_{b}"] = float(100 * d / c.loc[a, col])
            rec[f"share_of_total_change_{a}_{b}"] = float(d / dt) if dt else np.nan
            rec[f"share_of_total_{a}"] = float(c.loc[a, col] / c.loc[a, total])
        rows.append(rec)
    out = pd.DataFrame(rows)
    out["label"] = np.where(out["indicator"] == "bac08_crashes_mi", "estimated (MI)", "observed")
    return out


# --------------------------------------------------------------------------------------
# Driver
# --------------------------------------------------------------------------------------
def check_leakage() -> None:
    assert_no_leakage(
        [*COVARIATE_SETS["B"], *EXTRA_FACTORS, "YEAR"], allowed=MODEL_ALLOWED_TIMINGS | {"design"}
    )


def _save(df: pd.DataFrame, name: str, description: str, method: str, outcome: str, **kw) -> None:
    save_table(
        df,
        MODULE,
        name,
        description=description,
        population=kw.pop(
            "population",
            "CRSS police-reported crashes 2016-2024 with known maximum severity",
        ),
        unit=kw.pop("unit", "crash"),
        outcome=outcome,
        method=method,
        inputs=kw.pop("inputs", [CRSS_INPUT]),
        extra=kw.pop("extra", None),
    )


LIN_METHOD = (
    "Survey-weighted (pseudo-ML) logistic models, ridge 0.01; predictive margins; Taylor "
    "linearisation with coefficient influence, summed within 67 PSUs / 25 strata; t with 42 df"
)


def run(outcomes: Sequence[str] = OUTCOMES, sensitivity: bool = True) -> dict[str, pd.DataFrame]:
    check_leakage()
    fingerprint = data_fingerprint()
    df_all, design_all = load()
    out: dict[str, pd.DataFrame] = {}

    # (e) FARS first: its counts corroborate the CRSS numerator in (d).
    out["fars_composition_by_year"], out["fars_changes"] = fars_composition()
    fars_counts = out["fars_composition_by_year"].set_index("YEAR")["fatal_crashes"]

    # (d) KABCO distribution, numerator / denominator.
    ms_k = kabco_marginset(df_all, design_all)
    out["kabco_by_year"] = kabco_by_year(ms_k, df_all)
    nd = numerator_denominator(ms_k, fars_counts)
    out["numerator_denominator"] = nd

    decomp_tabs, detail_f, detail_c, within, annual = [], [], [], [], []
    for oc in outcomes:
        df, design = outcome_frame(df_all, design_all, oc)
        decs = {}
        for s, covs in COVARIATE_SETS.items():
            dec = decompose(df, design, covs, oc, f"model_{s}")
            decs[s] = dec
            decomp_tabs.append(decomposition_table(dec, design))
            by_factor, by_col = detailed_composition(dec, df, design)
            detail_f.append(by_factor)
            detail_c.append(by_col)
            within.append(within_by_subgroup(dec, df, design))
            log.info("%s: decomposition %s done", oc, s)
        annual.append(annual_series(df, design, oc, decs))
        if oc == "fatal":
            out["prevalence_change"] = prevalence_change(df, design)
        del decs

    if sensitivity:
        df, design = outcome_frame(df_all, design_all, "fatal")
        sens = [
            decompose(
                df,
                design,
                [c for c in COVARIATE_SETS["B"] if c not in CODING_DRIFT],
                "fatal",
                "sens_B_without_coding_drift_vars",
            ),
            decompose(
                df,
                design,
                COVARIATE_SETS["B"],
                "fatal",
                "sens_B_2021_24_vs_2016_19",
                p1_years=(2021, 2022, 2023, 2024),
            ),
            decompose(
                df,
                design,
                COVARIATE_SETS["B"],
                "fatal",
                "sens_B_2019_vs_2021",
                p0_years=(2019,),
                p1_years=(2021,),
            ),
            decompose(df, design, SPEEDING_BY_TYPE, "fatal", "sens_B_speeding_by_type"),
        ]
        dfi, dsi = outcome_frame(df_all, design_all, "fatal_im")
        sens_im = decompose(dfi, dsi, COVARIATE_SETS["B"], "fatal_im", "sens_B_outcome_MAXSEV_IM")
        decomp_tabs += [decomposition_table(d, design) for d in sens]
        decomp_tabs.append(decomposition_table(sens_im, dsi))
        for d in (sens[0], sens[-1]):
            by_factor, by_term = detailed_composition(d, df, design)
            detail_f.append(by_factor)
            if d is sens[-1]:
                detail_c.append(by_term)

    out["decomposition"] = pd.concat(decomp_tabs, ignore_index=True)
    out["decomposition_detailed_by_factor"] = pd.concat(detail_f, ignore_index=True)
    out["decomposition_detailed_by_term"] = pd.concat(detail_c, ignore_index=True)
    out["within_by_subgroup"] = pd.concat(within, ignore_index=True)
    out["annual_shares"] = pd.concat(annual, ignore_index=True)

    meta = {
        "fars_composition_by_year": (
            "FARS fatal crashes and deaths by year: speeding, MI driver BAC>=.08 (Rubin), "
            "pedestrians, motorcyclists, unrestrained light-passenger-vehicle occupant deaths",
            "Census counts (observed); shares with binomial/crash-clustered process CIs; MI BAC "
            "share among crashes with an MI record (Rubin's rules over 10 implicates)",
            "fatal",
            dict(
                population="FARS fatal crashes 2016-2024 (census)",
                unit="crash / person",
                inputs=FARS_INPUTS,
            ),
        ),
        "fars_changes": (
            "Changes in FARS counts 2019->2021->2024 and each indicator's change as a share of the "
            "change in all fatal crashes or deaths (overlapping categories; shares do not add)",
            "Census counts (observed); MI BAC count = Rubin point estimate x crashes with record",
            "fatal",
            dict(
                population="FARS fatal crashes 2016-2024 (census)",
                unit="crash / person",
                inputs=FARS_INPUTS,
            ),
        ),
        "kabco_by_year": (
            "Estimated police-reported crashes by maximum KABCO severity and year; shares of known "
            "severity, K/(KABC), K/(K+A)",
            "Weighted totals; ratios linearised jointly (25 strata / 67 PSUs, t 42 df); logit CIs",
            "MAX_SEV",
            dict(population="CRSS police-reported crashes 2016-2024 (all, incl. unknown severity)"),
        ),
        "numerator_denominator": (
            "Exact split of the change in the log fatal share into the change in fatal crashes "
            "(numerator) and in crashes with known severity (denominator), annual averages vs "
            "2016-2019; FARS census ratio for the numerator",
            "Weighted totals, joint linearisation; FARS observed counts",
            "fatal",
            dict(inputs=[CRSS_INPUT, "data/processed/fars_crash.parquet"]),
        ),
        "decomposition": (
            "Oaxaca-Blinder-type decomposition of the change in the fatal (KA) share between "
            "2016-19 and 2020-24 into composition and within-circumstance effects (both "
            "references and their average), plus sensitivity analyses",
            LIN_METHOD + "; separate period models; cross-period predictive margins",
            "fatal; ka; fatal_im (sensitivity)",
            dict(extra={"covariate_sets": SET_LABELS}),
        ),
        "decomposition_detailed_by_factor": (
            "Detailed composition effect by factor (Yun weights on 2016-19 coefficients)",
            LIN_METHOD + "; delta method over coefficients, period means and margins",
            "fatal; ka",
            {},
        ),
        "decomposition_detailed_by_term": (
            "Detailed composition effect by single design-matrix term (reference-dependent)",
            LIN_METHOD,
            "fatal; ka",
            {},
        ),
        "within_by_subgroup": (
            "Within-circumstance change by subgroup: pooled subgroup crashes predicted under the "
            "2020-24 vs the 2016-19 model (common mix), with crude period shares",
            LIN_METHOD,
            "fatal; ka",
            {},
        ),
        "annual_shares": (
            "Yearly crude fatal (KA) shares, shares standardised to the pooled 2016-24 covariate "
            "distribution (models A, B with year), and composition-only expected shares under "
            "the 2016-19 model",
            LIN_METHOD,
            "fatal; ka",
            {},
        ),
        "prevalence_change": (
            "Weighted prevalence of each circumstance level among crashes, 2016-19 vs 2020-24",
            "Weighted means; difference with joint linearisation (shared PSUs)",
            "",
            {},
        ),
    }
    for name, (desc, method, oc, kw) in meta.items():
        _save(out[name], name, desc, method, oc, **kw)
    save_json(
        {
            "periods": {"P0": list(P0_YEARS), "P1": list(P1_YEARS)},
            "covariate_sets": {k: v for k, v in COVARIATE_SETS.items()},
            "coding_drift_variables": list(CODING_DRIFT),
            "ridge": RIDGE,
            "design_df": design_all.df,
            "stochastic_components": "none (deterministic estimators)",
            "crss_crash_fingerprint": fingerprint,
            "data_unchanged_during_run": fingerprint == data_fingerprint(),
        },
        MODULE,
        "run_metadata",
    )
    return out
