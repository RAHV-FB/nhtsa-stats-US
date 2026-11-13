"""Crash-level severity: crude versus adjusted associations (CRSS, design-based).

Research question (RQ1, docs/research_plan.md): among police-reported crashes, which
circumstances are associated with the probability that the crash is fatal (K) or
fatal-or-serious (KA), and how do those associations change once other circumstances are
accounted for?

For every level of every factor the module reports

* the crude (weighted) outcome rate and the crude risk ratio versus the reference level;
* standardised adjusted risk ratios and risk differences from survey-weighted logistic
  models via predictive margins (g-computation over the observed covariate distribution):
  - model A adjusts for the whole PRE_CRASH set at once (mutually adjusted; for factors with
    registered downstream variables, ``specs.DESCENDANTS``, an association leaving those out
    is reported too, columns ``Ax_*``),
  - model B adds crash configuration (association net of crash type / vehicle count). For
    crash type itself the contrast comes from model A + crash type, and no vehicle-count
    contrast is reported: crash type fixes the vehicle count for most types, so setting
    either for every crash would standardise over combinations that cannot occur;
* the percentage change of the log risk ratio from crude to adjusted, which identifies
  associations that weaken or disappear after adjustment.

These are associations conditional on a police-reported crash having occurred.  They are not
causal effects and say nothing about crash occurrence (see docs/limitations.md).
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

import numpy as np
import pandas as pd
from scipy import stats

from nhtsa_stats import config
from nhtsa_stats.analysis import data, specs
from nhtsa_stats.analysis.measurement import corrected_rr
from nhtsa_stats.analysis.survey import (
    Estimate,
    MarginSet,
    ModelSpec,
    SurveyDesign,
    SurveyLogit,
    logit_ci,
    proportion_table,
    svy_mean,
)
from nhtsa_stats.processing import harmonize as h
from nhtsa_stats.reporting.io import save_json, save_table

log = logging.getLogger(__name__)
MODULE = "severity"
# Tiny L2 penalty (weights are normalised to mean 1, so the Fisher information of a level with
# k crashes and fatal rate p is ~k*p*(1-p)).  It keeps coefficients finite and stable for sparse
# levels and cells (e.g. 38 crashes with unknown interstate status, 3 fatal; zero-event cells in
# period-specific and interaction fits) while shrinking any level with >= 1,000 crashes by well
# under 1%.
RIDGE = 0.01


def observed_levels(df: pd.DataFrame, var: str, levels: Sequence | None = None) -> list:
    """Declared levels of ``var`` that occur in ``df`` (declared order kept)."""
    levels = specs.CRASH_LEVELS[var] if levels is None else levels
    present = set(pd.unique(df[var]))
    out = [lv for lv in levels if lv in present]
    if levels[0] not in present:
        if var == "YEAR" and out:
            # Year is a nuisance adjustment; in period-restricted fits use the first year present.
            return out
        raise ValueError(f"reference level {levels[0]!r} of {var} not observed")
    return out


def crash_spec(
    df: pd.DataFrame, covariates: Sequence[str], interactions: Sequence[tuple[str, str]] = ()
) -> ModelSpec:
    return ModelSpec(
        categorical={c: observed_levels(df, c) for c in covariates},
        interactions=list(interactions),
    )


POP_KNOWN = "CRSS police-reported crashes 2016-2024 with known maximum severity"
POP_CC = (
    "CRSS police-reported crashes 2016-2024 where the complete-case outcome is determined "
    "(crashes with a person of unknown severity are excluded unless the outcome is already met)"
)


def outcome_population(outcome: str) -> str:
    """Population string for a crash outcome: complete-case (``*_cc``) outcomes are fitted only
    where the strict outcome is determined, the imputed outcomes wherever MAXSEV_IM is known."""
    return POP_CC if outcome.endswith("_cc") else POP_KNOWN


def load(outcome: str, years: Sequence[int] | None = None) -> tuple[pd.DataFrame, SurveyDesign]:
    df, design = data.crss_crash(years=years, outcome=outcome, tri_state_cols=specs.CRASH_TRI)
    df[outcome] = df[outcome].astype(float)
    df["YEAR"] = df["YEAR"].astype(int)
    return df, design


def fit(
    df: pd.DataFrame,
    design: SurveyDesign,
    outcome: str,
    covariates: Sequence[str],
    interactions: Sequence[tuple[str, str]] = (),
    ridge: float = RIDGE,
) -> SurveyLogit:
    h.assert_no_leakage(list(covariates), allow_year=True)
    model = SurveyLogit(crash_spec(df, covariates, interactions), ridge=ridge)
    model.fit(df, df[outcome].to_numpy(), design)
    if not model.converged_:
        log.warning("model for %s did not converge", outcome)
    return model


def _fmt(est: Estimate, log_scale: bool = False) -> dict:
    lo, hi = est.ci()
    if log_scale:
        return {
            "est": float(np.exp(est.estimate)),
            "low": float(np.exp(lo)),
            "high": float(np.exp(hi)),
        }
    return {"est": est.estimate, "low": lo, "high": hi}


def factor_contrasts(
    model: SurveyLogit, df: pd.DataFrame, factor: str, levels: Sequence
) -> pd.DataFrame:
    """Standardised margins for each level of ``factor`` and contrasts vs the first level."""
    ref = levels[0]
    scenarios = {str(lv): (lambda d, lv=lv: d.assign(**{factor: lv})) for lv in levels}
    ms = model.margins(df, scenarios)
    rows = []
    for lv in levels:
        m = ms.estimate(str(lv))
        rr = _fmt(ms.log_ratio(str(lv), str(ref)), log_scale=True)
        rd = _fmt(ms.difference(str(lv), str(ref)))
        lo, hi = m.ci()
        rows.append(
            {
                "factor": factor,
                "level": lv,
                "adj_rate": m.estimate,
                "adj_rate_rse": m.se / m.estimate if m.estimate > 0 else np.inf,
                "adj_rate_low": lo,
                "adj_rate_high": hi,
                "adj_rr": rr["est"],
                "adj_rr_low": rr["low"],
                "adj_rr_high": rr["high"],
                "adj_rd": rd["est"],
                "adj_rd_low": rd["low"],
                "adj_rd_high": rd["high"],
            }
        )
    return pd.DataFrame(rows)


def crude_table(
    df: pd.DataFrame, design: SurveyDesign, outcome: str, factor: str, levels: Sequence, years: int
) -> pd.DataFrame:
    tab = proportion_table(df, design, outcome, factor, years=years)
    tab = tab.set_index(factor).reindex(levels).reset_index().rename(columns={factor: "level"})
    ref_rate = float(tab.loc[0, "rate"])
    # Crude RR CI via the delta method on the log scale, treating the two domain estimates'
    # covariance as zero is wrong for a shared design; compute it properly from a saturated
    # model instead (identical point estimates; exact linearised covariance).
    m = SurveyLogit(ModelSpec(categorical={factor: list(levels)})).fit(
        df, df[outcome].to_numpy(), design
    )
    cr = factor_contrasts(m, df, factor, levels)
    tab["crude_rr"] = tab["rate"] / ref_rate
    tab["crude_rr_low"] = cr["adj_rr_low"].to_numpy()
    tab["crude_rr_high"] = cr["adj_rr_high"].to_numpy()
    tab["factor"] = factor
    return tab


def crude_vs_adjusted(outcome: str = "fatal", years: Sequence[int] | None = None) -> pd.DataFrame:
    df, design = load(outcome, years)
    n_years = df["YEAR"].nunique()
    log.info("%s: %d crashes, %d events", outcome, len(df), int(df[outcome].sum()))
    model_a = fit(df, design, outcome, specs.PRE_CRASH)
    model_b = fit(df, design, outcome, specs.PRE_CRASH + specs.CIRCUMSTANCE)
    model_type = fit(df, design, outcome, [*specs.PRE_CRASH, "crash_type"])
    export_model(model_a, outcome, "A")
    export_model(model_b, outcome, "B")
    # Model A without each factor's downstream variables (one fit per distinct exclusion set).
    model_ax: dict[str, SurveyLogit] = {}
    by_excl: dict[tuple[str, ...], list[str]] = {}
    for f, desc in specs.DESCENDANTS.items():
        by_excl.setdefault(tuple(desc), []).append(f)
    for desc, fs in by_excl.items():
        m = fit(df, design, outcome, [c for c in specs.PRE_CRASH if c not in desc])
        model_ax.update(dict.fromkeys(fs, m))
    factors = [f for f in specs.PRE_CRASH + specs.CIRCUMSTANCE if f != "YEAR"] + ["YEAR"]
    out = []
    for f in factors:
        levels = observed_levels(df, f)
        crude = crude_table(df, design, outcome, f, levels, n_years)
        parts = [crude]
        if f in specs.PRE_CRASH:
            a = factor_contrasts(model_a, df, f, levels).add_prefix("A_")
            parts.append(a.drop(columns=["A_factor", "A_level"]))
        if f in model_ax:
            ax = factor_contrasts(model_ax[f], df, f, levels).add_prefix("Ax_")
            ax["Ax_excluded"] = ",".join(specs.DESCENDANTS[f])
            parts.append(ax.drop(columns=["Ax_factor", "Ax_level"]))
        if f == "n_vehicles":
            b = None  # not identifiable apart from crash type (see module docstring)
        else:
            b = factor_contrasts(model_type if f == "crash_type" else model_b, df, f, levels)
            b = b.add_prefix("B_").drop(columns=["B_factor", "B_level"])
            parts.append(b)
        merged = pd.concat(parts, axis=1)
        out.append(merged)
        log.info("contrasts done for %s", f)
    res = pd.concat(out, ignore_index=True)
    res.insert(0, "outcome", outcome)
    res["adj_flag"] = _adjusted_flags(res)
    # A level (or reference) with no events has no finite log-RR: the ridge keeps the fit
    # finite but its contrast and CI would be arbitrary and spuriously precise.
    no_events = res["n_events"].eq(0) | res.groupby("factor")["n_events"].transform("first").eq(0)
    adj_cols = [c for c in res.columns if c.startswith(("A_adj_r", "Ax_adj_r", "B_adj_r"))]
    adj_cols += ["crude_rr_low", "crude_rr_high"]  # the saturated crude fit degenerates too
    res.loc[no_events, adj_cols] = np.nan
    res.loc[no_events, "adj_flag"] = "no events in level or reference: not estimable"
    # Attenuation: share of the crude log-RR that remains after adjustment.
    with np.errstate(divide="ignore", invalid="ignore"):
        res["A_logrr_retained"] = np.log(res["A_adj_rr"]) / np.log(res["crude_rr"])
        res["B_logrr_retained"] = np.log(res["B_adj_rr"]) / np.log(res["crude_rr"])
    coef = pd.concat(
        [model_a.coef_table().assign(model="A"), model_b.coef_table().assign(model="B")],
        ignore_index=True,
    )
    save_table(
        coef,
        MODULE,
        f"{outcome}_model_coefficients",
        description=f"Survey-weighted logistic regression coefficients for crash outcome '{outcome}'",
        population=outcome_population(outcome),
        unit="crash",
        outcome=outcome,
        method="Pseudo-ML logistic regression; Taylor-linearised variance (25 strata, 67 PSUs); "
        "model A = PRE_CRASH covariates (mutually adjusted), model B = A + crash type + number of vehicles",
        inputs=["data/processed/crss_crash.parquet"],
        extra={
            "n": len(df),
            "events": int(df[outcome].sum()),
            "design_df": design.df,
            "converged": [model_a.converged_, model_b.converged_],
        },
    )
    return res


def _adjusted_flags(res: pd.DataFrame) -> list[str]:
    """Flag adjusted contrasts whose level or reference margin is unstable (n < 30 or RSE > 30%)."""
    flags = []
    ref_rse = res.groupby("factor")["A_adj_rate_rse"].transform("first")
    for i, r in res.iterrows():
        f = []
        if r["n"] < config.MIN_CELL_N:
            f.append("n<30")
        rse = r.get("A_adj_rate_rse")
        if pd.notna(rse) and rse > config.MAX_RSE:
            f.append("level RSE>30%")
        if pd.notna(ref_rse.iloc[i]) and ref_rse.iloc[i] > config.MAX_RSE:
            f.append("reference RSE>30%")
        flags.append("; ".join(f))
    return flags


def export_model(model: SurveyLogit, outcome: str, name: str) -> None:
    """Save a fitted model (levels, coefficients, design-based covariance) for prediction in
    the interface without refitting.  Predictions are conditional on a reported crash."""
    save_json(
        {
            "outcome": outcome,
            "model": name,
            "population": outcome_population(outcome),
            "levels": model.spec.categorical,
            "terms": model.names_,
            "coef": model.coef_.tolist(),
            "vcov": model.vcov_.tolist(),
            "design_df": model.design_.df,
            "n": model.n_,
            "events": model.n_events_,
            "ridge": model.ridge,
        },
        MODULE,
        f"model_{name}_{outcome}",
    )


def speeding_type_contrasts(outcome: str = "fatal") -> pd.DataFrame:
    """Adjusted risk ratios by speeding *type* (model A with the speeding indicator replaced).

    Police "speeding-related" mixes exceeding the posted limit (what automated enforcement
    targets) with "too fast for conditions" (often below the limit, e.g. on wet or icy roads).
    """
    df, design = load(outcome)
    df["speeding_type"] = df["speeding_type"].fillna("unknown")
    covs = [c if c != "speeding" else "speeding_type" for c in specs.PRE_CRASH]
    model = fit(df, design, outcome, covs)
    levels = observed_levels(df, "speeding_type")
    res = factor_contrasts(model, df, "speeding_type", levels)
    crude = crude_table(df, design, outcome, "speeding_type", levels, df["YEAR"].nunique())
    res = res.merge(
        crude[["level", "n", "n_events", "rate", "crude_rr", "crude_rr_low", "crude_rr_high"]],
        on="level",
        how="left",
    )
    # How each type is distributed over surfaces (weighted shares of crashes of that type).
    for surf in ("dry", "wet", "snow_ice"):
        res[f"share_on_{surf}"] = [
            float(
                np.average(
                    df.loc[df["speeding_type"] == lv, "surface"] == surf,
                    weights=design.weight[(df["speeding_type"] == lv).to_numpy()],
                )
            )
            for lv in res["level"]
        ]
    res.insert(0, "outcome", outcome)
    return res


def hit_and_run_sensitivity(outcome: str = "fatal") -> pd.DataFrame:
    """Model A refitted without crashes involving a hit-and-run vehicle.

    'Unknown' levels of police-reported driver attributes (speeding in particular) are mostly
    crashes whose driver fled -- a post-crash behaviour. Restricting the population removes
    that proxy without adjusting for a post-crash variable.
    """
    df, design = load(outcome)
    keep = (df["hit_and_run"] != 1).to_numpy()
    d = df.loc[keep].reset_index(drop=True)
    dsg = design.subset(keep)
    model = fit(d, dsg, outcome, specs.PRE_CRASH)
    parts = []
    for f in specs.PRE_CRASH:
        if f == "YEAR":
            continue
        parts.append(factor_contrasts(model, d, f, observed_levels(d, f)))
    res = pd.concat(parts, ignore_index=True)
    res.insert(0, "outcome", outcome)
    res["n_crashes"] = len(d)
    res["share_excluded_weighted"] = 1 - dsg.weight.sum() / design.weight.sum()
    return res


def outcome_definition_sensitivity(primary: pd.DataFrame, cc: pd.DataFrame) -> pd.DataFrame:
    """Model-A associations under the imputed (primary) and complete-case outcome definitions."""
    cols = ["crude_rr", "A_adj_rr", "A_adj_rr_low", "A_adj_rr_high"]
    keys = ["factor", "level"]
    a = primary[primary["A_adj_rr"].notna()][keys + cols]
    b = cc[cc["A_adj_rr"].notna()][keys + cols]
    m = a.merge(b, on=keys, suffixes=("", "_cc"))
    m["adj_rr_ratio_cc_vs_primary"] = m["A_adj_rr_cc"] / m["A_adj_rr"]
    return m


# --------------------------------------------------------------------------------------
# Additional tables (red-team follow-up, docs/red_team_2026-11.md)
# --------------------------------------------------------------------------------------
CI_LEVELS = (0.95, 0.90)


def _speeding_type_covariates(model: str) -> list[str]:
    covs = [c if c != "speeding" else "speeding_type" for c in specs.PRE_CRASH]
    return covs + (list(specs.CIRCUMSTANCE) if model == "B" else [])


def speeding_type_models(outcome: str = "fatal") -> pd.DataFrame:
    """Speeding-type risk ratios under model A and model B, with 95% and 90% intervals.

    Model A is the published specification (``speeding_type_contrasts``); model B adds crash
    configuration (crash type, vehicles), a plausible mediator, so the two bracket the
    association.  The 90% interval gives the two one-sided 5% tests of equivalence: ratios
    outside [low90, high90] are rejected, and ``equivalence_bound_pct`` is the symmetric
    percentage bound max(|log low90|, |log high90|) on the log scale.  An interval that excludes
    1 is not an equivalence result and a null interval does not show absence of an effect.
    """
    df, design = load(outcome)
    df["speeding_type"] = df["speeding_type"].fillna("unknown")
    rows = []
    for model_name in ("A", "B"):
        model = fit(df, design, outcome, _speeding_type_covariates(model_name))
        levels = observed_levels(df, "speeding_type")
        scen = {str(lv): (lambda d, lv=lv: d.assign(speeding_type=lv)) for lv in levels}
        ms = model.margins(df, scen)
        crude = crude_table(df, design, outcome, "speeding_type", levels, df["YEAR"].nunique())
        for lv in levels:
            if lv == levels[0]:
                continue
            rr = ms.log_ratio(str(lv), str(levels[0]))
            rd = ms.difference(str(lv), str(levels[0]))
            lo95, hi95 = rr.ci(0.95)
            lo90, hi90 = rr.ci(0.90)
            c = crude.set_index("level").loc[lv]
            rows.append(
                {
                    "outcome": outcome,
                    "model": model_name,
                    "level": lv,
                    "n": int(c["n"]),
                    "n_events": int(c["n_events"]),
                    "crude_rr": float(c["crude_rr"]),
                    "adj_rr": float(np.exp(rr.estimate)),
                    "adj_rr_low95": float(np.exp(lo95)),
                    "adj_rr_high95": float(np.exp(hi95)),
                    "adj_rr_low90": float(np.exp(lo90)),
                    "adj_rr_high90": float(np.exp(hi90)),
                    "adj_rd": rd.estimate,
                    "adj_rd_low95": rd.ci(0.95)[0],
                    "adj_rd_high95": rd.ci(0.95)[1],
                    "equivalence_bound_pct": 100 * (float(np.exp(max(abs(lo90), abs(hi90)))) - 1)
                    if np.isfinite(lo90)
                    else np.nan,
                }
            )
    return pd.DataFrame(rows)


# Non-differential recording sensitivities for the speeding-type bias analysis: same grid as
# ``measurement.qba_grid`` (fatal 0.7-1, non-fatal 0.3-1, specificity 1 and 0.99).
QBA_SE_FATAL = (0.7, 0.8, 0.9, 1.0)
QBA_SE_NONFATAL = (0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0)
QBA_SPECIFICITY = (1.0, 0.99)
QBA_TYPES = ("exceeded_limit_or_racing", "too_fast_for_conditions")


def qba_status(a: float, b: float, c: float, d: float, se_f: float, se_n: float, sp: float) -> str:
    """Why a matrix-method correction (``measurement.corrected_rr``) is or is not feasible.

    The corrected true counts are a_true = (a - (1-sp) F) / (se_f + sp - 1) for the exposed
    fatal crashes (F = all fatal crashes) and b_true = (b - (1-sp) N) / (se_n + sp - 1) for the
    exposed non-fatal crashes (N = all non-fatal crashes); the unexposed counts are the
    remainders.  The correction is infeasible when any corrected count is not positive.  With
    specificity below 1 this happens whenever the exposed crashes are fewer than (1 - sp) of the
    outcome group, i.e. the assumed false-positive rate already exceeds the recorded exposure
    share.
    """
    fat, non = a + c, b + d
    a_t = (a - (1 - sp) * fat) / (se_f + sp - 1)
    b_t = (b - (1 - sp) * non) / (se_n + sp - 1)
    c_t, d_t = fat - a_t, non - b_t
    bad = [
        name
        for name, v in (
            ("exposed fatal", a_t),
            ("exposed non-fatal", b_t),
            ("unexposed fatal", c_t),
            ("unexposed non-fatal", d_t),
        )
        if v <= 0
    ]
    if not bad:
        return "ok"
    detail = ""
    if sp < 1 and "exposed non-fatal" in bad:
        detail = (
            f"; recorded exposure share among non-fatal crashes {b / non:.4f} "
            f"< assumed false-positive rate {1 - sp:.2f}"
        )
    elif sp < 1 and "exposed fatal" in bad:
        detail = (
            f"; recorded exposure share among fatal crashes {a / fat:.4f} "
            f"< assumed false-positive rate {1 - sp:.2f}"
        )
    return "infeasible: corrected count not positive (" + ", ".join(bad) + ")" + detail


def speeding_type_qba(
    models: pd.DataFrame, outcomes: Sequence[str] = ("fatal", "ka")
) -> pd.DataFrame:
    """Bias analysis for outcome-dependent recording of each speeding type.

    Crude counts (type vs no speeding; other types and unknown left out, as in
    ``measurement.qba_grid``) are corrected for sensitivities ``se_fatal`` / ``se_nonfatal`` and
    specificity; the bias factor (corrected / observed crude RR) multiplies the model-A adjusted
    RR, as in ``burden.bias_sensitivity``.  ``status`` says why a row is blank.  Covers CRSS
    sampling only; the sensitivities are assumptions, not estimates.  ``models`` is the output of
    ``speeding_type_models`` (model-A rows supply the adjusted RR).
    """
    rows = []
    for outcome in outcomes:
        df, design = load(outcome)
        df["speeding_type"] = df["speeding_type"].fillna("unknown")
        st = df["speeding_type"].astype(str).to_numpy()
        y = df[outcome].to_numpy(float)
        w = design.weight
        adj = models[(models["outcome"] == outcome) & (models["model"] == "A")].set_index("level")
        for lv in QBA_TYPES:
            known = (st == lv) | (st == "no")
            x = (st == lv).astype(float)
            a = w[known & (x == 1) & (y == 1)].sum()
            b = w[known & (x == 1) & (y == 0)].sum()
            c = w[known & (x == 0) & (y == 1)].sum()
            d = w[known & (x == 0) & (y == 0)].sum()
            rr_obs = (a / (a + b)) / (c / (c + d))
            for se_f in QBA_SE_FATAL:
                for se_n in QBA_SE_NONFATAL:
                    for sp in QBA_SPECIFICITY:
                        rr = corrected_rr(a, b, c, d, se_f, se_n, sp)
                        status = qba_status(a, b, c, d, se_f, se_n, sp)
                        if status == "ok" and not np.isfinite(rr):
                            status = "infeasible: corrected risk ratio undefined"
                        ok = status == "ok"
                        rr_model = float(adj.loc[lv, "adj_rr"])
                        rows.append(
                            {
                                "outcome": outcome,
                                "speeding_type": lv,
                                "se_fatal": se_f,
                                "se_nonfatal": se_n,
                                "specificity": sp,
                                "crude_rr_observed": rr_obs,
                                "crude_rr_corrected": rr if ok else np.nan,
                                "bias_factor": rr / rr_obs if ok else np.nan,
                                "adj_rr_model_A": rr_model,
                                "adj_rr_bias_corrected": rr_model * rr / rr_obs if ok else np.nan,
                                "status": status,
                            }
                        )
    return pd.DataFrame(rows)


INTERSTATE_BANDS: dict[str, tuple[str, ...]] = {
    "<=25 mph": ("<=25",),
    "30-35 mph": ("30-35",),
    "40-45 mph": ("40-45",),
    "50-55 mph": ("50-55",),
    "60-65 mph": ("60-65",),
    "50-65 mph": ("50-55", "60-65"),
    "70+ mph": ("70+",),
}


def interstate_by_speed_band(outcome: str = "fatal") -> pd.DataFrame:
    """Interstate vs other roads within posted speed-limit bands (model A with interstate x
    speed-limit interaction; margins standardised over the crashes of each band).

    The published interstate RR is one number averaged over bands.  Rows give the RR within each
    band, and the ratio of the 70+ mph RR to the 50-65 mph RR (``ratio_of_rr``) with its CI.
    The model also contains the interaction of the speed-limit band with the (unknown) interstate
    level; the band is the posted limit of the crash's road.
    """
    df, design = load(outcome)
    model = fit(df, design, outcome, specs.PRE_CRASH, interactions=[("interstate", "speed_limit")])
    doms = {}
    scen = {
        "yes": lambda d: d.assign(interstate="yes"),
        "no": lambda d: d.assign(interstate="no"),
    }
    values, infl = {}, {}
    for band, lvls in INTERSTATE_BANDS.items():
        dom = df["speed_limit"].isin(lvls).to_numpy()
        doms[band] = dom
        for k, setter in scen.items():
            m, z = model.margin_influence(df, setter, dom)
            values[f"{band}|{k}"], infl[f"{band}|{k}"] = m, z
    ms_all = MarginSet(values, infl, design)
    rows = []
    for band in INTERSTATE_BANDS:
        rr = ms_all.log_ratio(f"{band}|yes", f"{band}|no")
        rd = ms_all.difference(f"{band}|yes", f"{band}|no")
        dom = doms[band]
        inter = (df["interstate"] == "yes").to_numpy()
        rows.append(
            {
                "outcome": outcome,
                "speed_limit_band": band,
                "quantity": "RR interstate vs not",
                "n_crashes": int(dom.sum()),
                "n_interstate_crashes": int((dom & inter).sum()),
                "n_events": int(df.loc[dom, outcome].sum()),
                "adj_rate_interstate": values[f"{band}|yes"],
                "adj_rate_other": values[f"{band}|no"],
                "estimate": float(np.exp(rr.estimate)),
                "low": float(np.exp(rr.ci()[0])),
                "high": float(np.exp(rr.ci()[1])),
                "rd": rd.estimate,
                "rd_low": rd.ci()[0],
                "rd_high": rd.ci()[1],
            }
        )
    hi, lo = "70+ mph", "50-65 mph"
    ror = ms_all.contrast(
        lambda m: float(np.log((m[f"{hi}|yes"] / m[f"{hi}|no"]) / (m[f"{lo}|yes"] / m[f"{lo}|no"])))
    )
    # Wald test of the interaction terms (heterogeneity across all bands).
    terms = [n for n in model.names_ if "interstate" in n and "speed_limit" in n]
    wt = model.wald_test(terms) if terms else {}
    rows.append(
        {
            "outcome": outcome,
            "speed_limit_band": f"{hi} vs {lo}",
            "quantity": "ratio of RRs",
            "estimate": float(np.exp(ror.estimate)),
            "low": float(np.exp(ror.ci()[0])),
            "high": float(np.exp(ror.ci()[1])),
            "interaction_wald_p": float(wt.get("p", np.nan)) if wt else np.nan,
        }
    )
    return pd.DataFrame(rows)


KEY_CONTRASTS = (
    ("young_driver", "yes", "Driver aged 15-20 involved vs not"),
    ("weather", "rain", "Rain vs clear weather"),
    ("surface", "wet", "Wet vs dry surface"),
    ("interstate", "yes", "Interstate vs other roads (averaged over speed limits)"),
)


def key_contrasts_side_by_side(results: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Selected contrasts with model A and B and the fatal and KA outcomes in one table
    (read from the crude-vs-adjusted results; nothing is re-estimated)."""
    rows = []
    for factor, level, label in KEY_CONTRASTS:
        for oc in ("fatal", "ka"):
            res = results[oc]
            r = res[(res["factor"] == factor) & (res["level"].astype(str) == level)].iloc[0]
            for m in ("A", "B"):
                rows.append(
                    {
                        "factor": factor,
                        "level": level,
                        "label": label,
                        "outcome": oc,
                        "model": m,
                        "adj_rr": r[f"{m}_adj_rr"],
                        "low": r[f"{m}_adj_rr_low"],
                        "high": r[f"{m}_adj_rr_high"],
                        "adj_rd": r[f"{m}_adj_rd"],
                        "rd_low": r[f"{m}_adj_rd_low"],
                        "rd_high": r[f"{m}_adj_rd_high"],
                        "crude_rr": r["crude_rr"],
                        "n_events": int(r["n_events"]),
                    }
                )
    return pd.DataFrame(rows)


def run_additional(results: dict[str, pd.DataFrame] | None = None) -> dict[str, pd.DataFrame]:
    """Tables added after the red-team review; they never alter the tables of ``run``."""
    out: dict[str, pd.DataFrame] = {}
    common = dict(
        population="CRSS police-reported crashes 2016-2024 with known maximum severity",
        unit="crash",
        inputs=["data/processed/crss_crash.parquet"],
    )
    out["speeding_type_models"] = pd.concat(
        [speeding_type_models(oc) for oc in ("fatal", "ka")], ignore_index=True
    )
    save_table(
        out["speeding_type_models"],
        MODULE,
        "speeding_type_models",
        description="Adjusted risk ratios by speeding type under model A and model B for fatal and "
        "fatal-or-serious (KA) crashes, with 95% and 90% intervals and the symmetric equivalence "
        "bound implied by the 90% interval",
        outcome="fatal; ka",
        method="Model A (published) and model B (A + crash type + vehicles) with the speeding "
        "indicator replaced by speeding type; standardised margins; linearised CIs (t, 42 df); "
        "the 90% interval gives two one-sided 5% tests",
        **common,
    )
    out["speeding_type_qba"] = speeding_type_qba(out["speeding_type_models"])
    save_table(
        out["speeding_type_qba"],
        MODULE,
        "speeding_type_qba",
        description="Bias analysis of outcome-dependent recording for each speeding type; "
        "'status' says why a row is blank",
        outcome="fatal; ka",
        method="Matrix-method correction (measurement.corrected_rr) of the crude RR of type vs no "
        "speeding for sensitivities and specificity on the measurement-module grid; the bias "
        "factor multiplies the model-A adjusted RR",
        **common,
    )
    out["interstate_by_speed_band"] = pd.concat(
        [interstate_by_speed_band(oc) for oc in ("fatal", "ka")], ignore_index=True
    )
    save_table(
        out["interstate_by_speed_band"],
        MODULE,
        "interstate_by_speed_band",
        description="Interstate vs other roads within posted speed-limit bands, and the ratio of "
        "the 70+ mph to the 50-65 mph risk ratio",
        outcome="fatal; ka",
        method="Model A plus interstate x speed-limit interaction; margins standardised within "
        "each band (domain of the full design); linearised CIs (t, 42 df)",
        **common,
    )
    if results is not None and all(k in results for k in ("fatal", "ka")):
        out["key_contrasts_ab"] = key_contrasts_side_by_side(results)
        save_table(
            out["key_contrasts_ab"],
            MODULE,
            "key_contrasts_ab",
            description="Teen-driver, rain, wet-surface and interstate contrasts under model A and "
            "model B for fatal and KA, side by side",
            outcome="fatal; ka",
            method="Copied from the fatal and ka crude-vs-adjusted tables (models A and B)",
            **common,
        )
    return out


# --------------------------------------------------------------------------------------
# Effect modification by crash configuration and calibration of model A
# --------------------------------------------------------------------------------------
EM_MIN_EVENTS = 20  # fatal crashes required in both the exposed and the reference cell of a stratum
# exposure -> (model variable, exposed level, reference level, label); the two speeding
# exposures come from the speeding-type version of model A (speeding replaced by speeding type).
EM_EXPOSURES: dict[str, tuple[str, str, str, str]] = {
    "exceeded_limit": (
        "speeding_type",
        "exceeded_limit_or_racing",
        "no",
        "Exceeded the posted limit or racing (police-reported)",
    ),
    "too_fast_for_conditions": (
        "speeding_type",
        "too_fast_for_conditions",
        "no",
        "Too fast for conditions (police-reported)",
    ),
    "alcohol": ("alcohol_im", "yes", "no", "Alcohol involved (NHTSA-imputed)"),
    "motorcycle": ("any_motorcycle", "yes", "no", "Motorcycle involved"),
    "large_truck": ("any_heavy_truck", "yes", "no", "Medium/heavy truck or bus involved"),
}
EM_SINGLE, EM_MULTI = "single-vehicle", "multi-vehicle"


def homogeneity_test(log_rr: np.ndarray, vcov: np.ndarray, design_df: int) -> dict:
    """Design-based Wald test that K stratum log risk ratios are equal.

    Tests the K-1 differences from the first stratum with the adjusted-F statistic of
    :meth:`SurveyLogit.wald_test`; ``vcov`` is the joint design covariance of the K log RRs."""
    k = len(log_rr)
    if k < 2:
        return {"q": 0, "wald_chi2": np.nan, "F": np.nan, "p": np.nan}
    c = np.hstack([-np.ones((k - 1, 1)), np.eye(k - 1)])
    d = c @ log_rr
    v = c @ vcov @ c.T
    q = k - 1
    w = float(d @ np.linalg.pinv(v) @ d)
    if design_df - q + 1 <= 0:
        return {"q": q, "wald_chi2": w, "F": np.nan, "p": np.nan}
    f = (design_df - q + 1) / (design_df * q) * w
    return {
        "q": q,
        "wald_chi2": w,
        "F": f,
        "p": float(stats.f.sf(f, q, design_df - q + 1)),
    }


def _em_covariates(variable: str) -> list[str]:
    return (
        [c if c != "speeding" else "speeding_type" for c in specs.PRE_CRASH]
        if (variable == "speeding_type")
        else list(specs.PRE_CRASH)
    )


def _em_modifier(df: pd.DataFrame, kind: str, exposure: str) -> tuple[pd.Series, list[str]]:
    """Stratum label of every crash and the ordered strata (reference first) for one modifier.

    ``vehicles``: single-vehicle (``n_vehicles`` 1; includes pedestrian and cyclist crashes) vs
    multi-vehicle.  ``crash_type``: the harmonised crash type; types with fewer than
    ``EM_MIN_EVENTS`` fatal crashes in the exposed or the reference cell are pooled into
    ``other crash types`` (itself reported only if it meets the same rule)."""
    if kind == "vehicles":
        lab = pd.Series(
            np.where(df["n_vehicles"].astype(str) == "1", EM_SINGLE, EM_MULTI), index=df.index
        )
        return lab, [EM_SINGLE, EM_MULTI]
    var, lvl, ref, _ = EM_EXPOSURES[exposure]
    ct = df["crash_type"].astype(str)
    keep = []
    for t in specs.CRASH_LEVELS["crash_type"]:
        m = (ct == t) & (df["fatal"] == 1)
        if (m & (df[var] == lvl)).sum() >= EM_MIN_EVENTS and (m & (df[var] == ref)).sum() >= (
            EM_MIN_EVENTS
        ):
            keep.append(t)
    lab = ct.where(ct.isin(keep), "other crash types")
    strata_order = keep + (["other crash types"] if (lab == "other crash types").any() else [])
    return lab, strata_order


def _em_fit(
    df: pd.DataFrame, design: SurveyDesign, outcome: str, variable: str, mod: pd.Series, order
) -> SurveyLogit:
    """Model A (variable set per exposure) plus the stratum main effect and variable x stratum."""
    d = df.assign(_stratum=mod.to_numpy())
    covs = _em_covariates(variable)
    h.assert_no_leakage(covs, allow_year=True)
    spec = ModelSpec(
        categorical={
            **{c: observed_levels(d, c) for c in covs},
            "_stratum": list(order),
        },
        interactions=[(variable, "_stratum")],
    )
    model = SurveyLogit(spec, ridge=RIDGE).fit(d, d[outcome].to_numpy(), design)
    if not model.converged_:
        log.warning("effect-modification model for %s did not converge", variable)
    return model


def effect_modification(outcome: str = "fatal") -> pd.DataFrame:
    """Adjusted fatal RR of five model-A exposures within strata of crash configuration.

    For each exposure and modifier, one survey logistic model holds model A (speeding replaced
    by speeding type for the two speeding exposures), the stratum main effect and the exposure x
    stratum interaction; nothing else interacts with the stratum.  The stratum RR is the ratio of
    predictive margins with the exposure set to its exposed vs reference level for every crash of
    the stratum (a domain of the full design, so the variance keeps the whole PSU structure).
    A stratum is reported only if it has at least ``EM_MIN_EVENTS`` fatal crashes in the exposed
    and in the reference cell (unweighted); smaller strata are listed with ``status`` and no
    estimate.  ``p_homogeneity_rr`` is a design-based Wald F test that the reported strata's
    log RRs are equal (joint linearisation of the margins); ``p_interaction_logit`` tests the
    interaction coefficients (conditional odds-ratio scale) of the same eligible strata.
    ``pooled_*`` is the unstratified model-A RR (as in ``fatal_crude_vs_adjusted`` and
    ``fatal_speeding_type``).  Associations conditional on a police-reported crash, not causal
    effects; crash configuration is a possible mediator, so within-stratum RRs are net of it."""
    df, design = load(outcome)
    df["speeding_type"] = df["speeding_type"].fillna("unknown")
    pooled_models = {
        "speeding_type": fit(df, design, outcome, _em_covariates("speeding_type")),
        "other": fit(df, design, outcome, specs.PRE_CRASH),
    }
    rows = []
    for exposure, (var, lvl, ref, label) in EM_EXPOSURES.items():
        pm = pooled_models["speeding_type" if var == "speeding_type" else "other"]
        pc = factor_contrasts(pm, df, var, observed_levels(df, var)).set_index("level").loc[lvl]
        pooled = {
            "pooled_model_a_rr": pc["adj_rr"],
            "pooled_model_a_rr_low": pc["adj_rr_low"],
            "pooled_model_a_rr_high": pc["adj_rr_high"],
        }
        for kind in ("vehicles", "crash_type"):
            mod, order = _em_modifier(df, kind, exposure)
            model = _em_fit(df, design, outcome, var, mod, order)
            exposed = (df[var] == lvl).to_numpy()
            reference = (df[var] == ref).to_numpy()
            fatal = (df[outcome] == 1).to_numpy()
            recs, logs, infl = [], [], []
            for stratum in order:
                dom = (mod == stratum).to_numpy()
                ev_e, ev_r = (
                    int((dom & exposed & fatal).sum()),
                    int((dom & reference & fatal).sum()),
                )
                rec = {
                    "outcome": outcome,
                    "exposure": exposure,
                    "label": label,
                    "modifier": "single vs multi-vehicle" if kind == "vehicles" else "crash type",
                    "stratum": stratum,
                    "n_crashes": int(dom.sum()),
                    "n_exposed": int((dom & exposed).sum()),
                    "events_exposed": ev_e,
                    "events_reference": ev_r,
                    "min_events_rule": EM_MIN_EVENTS,
                }
                ok = ev_e >= EM_MIN_EVENTS and ev_r >= EM_MIN_EVENTS
                rec["status"] = (
                    "ok"
                    if ok
                    else f"not estimated: fewer than {EM_MIN_EVENTS} fatal crashes in "
                    "the exposed or reference cell"
                )
                if ok:
                    scen = {
                        "e": lambda d, var=var, lvl=lvl: d.assign(**{var: lvl}),
                        "r": lambda d, var=var, ref=ref: d.assign(**{var: ref}),
                    }
                    dfm = df.assign(_stratum=mod.to_numpy())
                    m1, z1 = model.margin_influence(dfm, scen["e"], dom)
                    m0, z0 = model.margin_influence(dfm, scen["r"], dom)
                    ms = MarginSet({"e": m1, "r": m0}, {"e": z1, "r": z0}, design)
                    rr = ms.log_ratio("e", "r")
                    rd = ms.difference("e", "r")
                    rec.update(
                        adj_rate_exposed=m1,
                        adj_rate_reference=m0,
                        adj_rr=float(np.exp(rr.estimate)),
                        adj_rr_low=float(np.exp(rr.ci()[0])),
                        adj_rr_high=float(np.exp(rr.ci()[1])),
                        adj_rd=rd.estimate,
                        adj_rd_low=rd.ci()[0],
                        adj_rd_high=rd.ci()[1],
                    )
                    logs.append(rr.estimate)
                    infl.append(z1 / m1 - z0 / m0)
                    rec["_i"] = len(logs) - 1
                recs.append(rec)
            # Homogeneity across the estimated strata (RR scale) and the logit-scale interaction.
            est = [r for r in recs if r["status"] == "ok"]
            if len(est) >= 2:
                zmat = np.column_stack(infl)
                vcov = design.vcov_total(zmat)
                het = homogeneity_test(np.array(logs), vcov, design.df)
                kept = {r["stratum"] for r in est}
                terms = [
                    n
                    for n in model.names_
                    if n.startswith(f"{var}[{lvl}]:_stratum[")
                    and n.split("_stratum[")[1].rstrip("]") in kept
                    and n.split("_stratum[")[1].rstrip("]") != order[0]
                ]
                # the reference stratum of the model is order[0]; if it was not estimated the
                # interaction test is skipped (no like-for-like set of terms)
                lt = (
                    model.wald_test(terms)
                    if order[0] in kept and len(terms) == len(kept) - 1
                    else {"p": np.nan}
                )
                ref_est = est[0]
                v0 = vcov[0, 0]
                for r in est:
                    i = r.pop("_i")
                    dlog = logs[i] - logs[0]
                    se = float(np.sqrt(max(vcov[i, i] + v0 - 2 * vcov[i, 0], 0.0))) if i else 0.0
                    r["rr_ratio_to_first_stratum"] = float(np.exp(dlog))
                    t = design.tcrit()
                    r["rr_ratio_low"] = float(np.exp(dlog - t * se)) if i else 1.0
                    r["rr_ratio_high"] = float(np.exp(dlog + t * se)) if i else 1.0
                for r in recs:
                    r["first_stratum"] = ref_est["stratum"]
                    r["n_strata_tested"] = len(est)
                    r["homogeneity_F"] = het["F"]
                    r["p_homogeneity_rr"] = het["p"]
                    r["p_interaction_logit"] = lt["p"]
            for r in recs:
                r.pop("_i", None)
                r.update(pooled)
            rows += recs
            log.info("effect modification %s | %s done", exposure, kind)
    out = pd.DataFrame(rows)
    for col in (
        "adj_rate_exposed",
        "adj_rate_reference",
        "adj_rr",
        "adj_rr_low",
        "adj_rr_high",
        "adj_rd",
        "adj_rd_low",
        "adj_rd_high",
        "rr_ratio_to_first_stratum",
        "rr_ratio_low",
        "rr_ratio_high",
        "first_stratum",
        "n_strata_tested",
        "homogeneity_F",
        "p_homogeneity_rr",
        "p_interaction_logit",
    ):
        if col not in out:
            out[col] = np.nan
    out["note"] = (
        "association conditional on a police-reported crash, not causal; within-stratum RRs are "
        "net of crash configuration; strata with fewer than "
        f"{EM_MIN_EVENTS} fatal crashes in the exposed or reference cell are not estimated"
    )
    return out


def weighted_deciles(p: np.ndarray, weight: np.ndarray, k: int = 10) -> np.ndarray:
    """Group (1..k) of ``p`` holding about 1/k of the total weight each; tied values share a group.

    Rows are ordered by ``p`` and a run of identical predictions is placed, as a whole, in the
    group containing the midpoint of its cumulative weight, so no value straddles a boundary
    (group ranges of ``p`` never overlap).  A large tie can therefore make a group heavier
    than 1/k, and a group can be empty (it then does not appear in the result)."""
    p = np.asarray(p, dtype=float)
    weight = np.asarray(weight, dtype=float)
    order = np.argsort(p, kind="stable")
    ps, cum = p[order], np.cumsum(weight[order]) / weight.sum()
    start = np.r_[True, ps[1:] != ps[:-1]]
    run = np.cumsum(start) - 1
    run_end = cum[np.r_[np.flatnonzero(start)[1:] - 1, len(ps) - 1]]
    run_start = np.r_[0.0, run_end[:-1]]
    mid = ((run_start + run_end) / 2)[run]
    dec_sorted = np.clip(np.floor(mid * k).astype(int) + 1, 1, k)
    dec = np.empty(len(p), dtype=int)
    dec[order] = dec_sorted
    return dec


def calibration_by_decile(
    p: np.ndarray, y: np.ndarray, design: SurveyDesign, k: int = 10
) -> pd.DataFrame:
    """Weighted observed vs mean predicted outcome share by weighted decile of predicted risk.

    Observed share with a logit CI (design-based), predicted share (mean of ``p``) with its CI,
    and the observed minus predicted difference and the observed / predicted ratio with
    linearised CIs.  The predictions are held fixed (in-sample fitted values of model A), so the
    intervals do not include the variability of the fitted model."""
    dec = weighted_deciles(p, design.weight, k)
    t = design.tcrit()
    rows = []
    for g in [*range(1, k + 1), 0]:  # 0 = all crashes
        dom = np.ones(len(p), bool) if g == 0 else dec == g
        if not dom.any():  # a large tie of predictions can leave a decile empty
            continue
        obs = svy_mean(design, y, dom)
        pred = svy_mean(design, p, dom)
        dif = svy_mean(design, y - p, dom)
        w = design.weight * dom
        big = float((w * p).sum())
        ratio = float((w * y).sum()) / big
        z = w * (y - ratio * p) / big
        se_ratio = float(np.sqrt(design.vcov_total(z)[0, 0]))
        lo, hi = logit_ci(obs.estimate, obs.se, design.df)
        plo, phi = logit_ci(pred.estimate, pred.se, design.df)
        rows.append(
            {
                "decile": "all" if g == 0 else g,
                "n_crashes": int(dom.sum()),
                "n_events": int(y[dom].sum()),
                "predicted_min": float(p[dom].min()),
                "predicted_max": float(p[dom].max()),
                "observed": obs.estimate,
                "observed_low": lo,
                "observed_high": hi,
                "predicted": pred.estimate,
                "predicted_low": plo,
                "predicted_high": phi,
                "difference": dif.estimate,
                "difference_low": dif.estimate - t * dif.se,
                "difference_high": dif.estimate + t * dif.se,
                "ratio_observed_to_predicted": ratio,
                "ratio_low": ratio - t * se_ratio,
                "ratio_high": ratio + t * se_ratio,
            }
        )
    return pd.DataFrame(rows)


def model_a_calibration(outcome: str = "fatal") -> pd.DataFrame:
    """Calibration of model A (PRE_CRASH, unchanged specification) by weighted decile of risk."""
    df, design = load(outcome)
    model = fit(df, design, outcome, specs.PRE_CRASH)
    out = calibration_by_decile(model.predict(df), df[outcome].to_numpy(float), design)
    out.insert(0, "outcome", outcome)
    return out


def run_effect_modification(outcome: str = "fatal") -> dict[str, pd.DataFrame]:
    """Effect modification by crash configuration and model-A calibration (fatal outcome)."""
    common = dict(
        population="CRSS police-reported crashes 2016-2024 with known maximum severity",
        unit="crash",
        inputs=["data/processed/crss_crash.parquet"],
    )
    out = {"fatal_effect_modification": effect_modification(outcome)}
    save_table(
        out["fatal_effect_modification"],
        MODULE,
        "fatal_effect_modification",
        description="Adjusted fatal risk ratios of exceeding the limit, too fast for conditions, "
        "alcohol, motorcycle and large truck within single- and multi-vehicle crashes and within "
        "crash types, with design-based Wald tests of homogeneity and the pooled model-A RR",
        outcome=outcome,
        method="Model A (speeding replaced by speeding type for the speeding exposures) plus "
        "stratum main effect and exposure x stratum interaction; stratum RR = ratio of predictive "
        "margins over the crashes of the stratum (domain of the full design); linearised CIs "
        f"(t, 42 df); strata need >= {EM_MIN_EVENTS} fatal crashes in the exposed and reference "
        "cells; Wald F on the equality of the stratum log RRs (RR scale) and on the logit "
        "interaction terms",
        **common,
    )
    out["fatal_calibration"] = model_a_calibration(outcome)
    save_table(
        out["fatal_calibration"],
        MODULE,
        "fatal_calibration",
        description="Model A calibration: weighted observed vs mean predicted fatal share by "
        "weighted decile of predicted fatal risk, with design-based confidence intervals",
        outcome=outcome,
        method="Model A (published specification) fitted values; deciles hold 1/10 of the total "
        "weight; observed and predicted shares are weighted means (logit CIs); difference and "
        "ratio linearised; predictions treated as fixed (in-sample), so CIs omit model-fit "
        "variability",
        **common,
    )
    return out


def run(outcomes: Sequence[str] = ("fatal", "ka", "fatal_cc", "ka_cc")) -> dict[str, pd.DataFrame]:
    out = {}
    for oc in outcomes:
        res = crude_vs_adjusted(oc)
        save_table(
            res,
            MODULE,
            f"{oc}_crude_vs_adjusted",
            description=f"Crude and standardised adjusted risk ratios for crash outcome '{oc}' by factor level",
            population=outcome_population(oc),
            unit="crash",
            outcome=oc,
            method="Weighted rates; standardised predictive margins from survey logistic models A (pre-crash) "
            "and B (pre-crash + configuration); ratios of margins with linearised 95% CIs (t, 42 df)",
            inputs=["data/processed/crss_crash.parquet"],
        )
        out[oc] = res
        st = speeding_type_contrasts(oc)
        save_table(
            st,
            MODULE,
            f"{oc}_speeding_type",
            description=f"Adjusted risk ratios for crash outcome '{oc}' by police-reported speeding type",
            population=outcome_population(oc),
            unit="crash",
            outcome=oc,
            method="Model A with speeding replaced by speeding type; standardised margins; linearised CIs",
            inputs=["data/processed/crss_crash.parquet"],
        )
        out[f"{oc}_speeding_type"] = st
    for oc in ("fatal", "ka"):
        if oc not in out or f"{oc}_cc" not in out:
            continue
        sens = outcome_definition_sensitivity(out[oc], out[f"{oc}_cc"])
        save_table(
            sens,
            MODULE,
            f"{oc}_outcome_definition_sensitivity",
            description=f"Model-A adjusted risk ratios with the NHTSA-imputed '{oc}' outcome (primary) and "
            "the strict complete-case outcome (MAX_SEV; crashes with any person of unknown severity "
            "excluded unless the outcome is already met)",
            population="CRSS police-reported crashes 2016-2024",
            unit="crash",
            outcome=f"{oc} vs {oc}_cc",
            method="Same model A fitted to each outcome definition; ratio of adjusted RRs",
            inputs=["data/processed/crss_crash.parquet"],
        )
        out[f"{oc}_outcome_definition_sensitivity"] = sens
    if "fatal" in out:
        hr = hit_and_run_sensitivity("fatal")
        save_table(
            hr,
            MODULE,
            "fatal_excluding_hit_and_run",
            description="Model-A adjusted risk ratios for the fatal outcome, crashes involving a hit-and-run "
            "vehicle excluded (removes 'unknown' levels that mainly mark a driver who fled)",
            population="CRSS police-reported crashes 2016-2024 without a hit-and-run vehicle",
            unit="crash",
            outcome="fatal",
            method="Model A refitted on the restricted population (domain of the full design); "
            "standardised margins; linearised CIs",
            inputs=["data/processed/crss_crash.parquet"],
        )
        out["fatal_excluding_hit_and_run"] = hr
    out.update(run_additional(out))
    out.update(run_effect_modification())
    return out
