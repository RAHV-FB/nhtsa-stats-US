"""Crash-level severity: crude versus adjusted associations (CRSS, design-based).

Research question (RQ1, docs/research_plan.md): among police-reported crashes, which
circumstances are associated with the probability that the crash is fatal (K) or
fatal-or-serious (KA), and how do those associations change once other circumstances are
accounted for?

For every level of every factor the module reports

* the crude (weighted) outcome rate and the crude risk ratio versus the reference level;
* standardised adjusted risk ratios and risk differences from survey-weighted logistic
  models via predictive margins (g-computation over the observed covariate distribution):
  - model A adjusts for the PRE_CRASH set (total association),
  - model B adds crash configuration (association net of crash type / vehicle count);
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

from nhtsa_stats.analysis import data, specs
from nhtsa_stats.analysis.survey import (
    Estimate,
    ModelSpec,
    SurveyDesign,
    SurveyLogit,
    proportion_table,
)
from nhtsa_stats.reporting.io import save_json, save_table

log = logging.getLogger(__name__)
MODULE = "severity"
# Tiny L2 penalty (weights are normalised to mean 1, so the Fisher information of a level with
# k crashes and fatal rate p is ~k*p*(1-p)).  It keeps coefficients finite for levels with zero
# events (e.g. 36 crashes with unknown interstate status, none fatal) while shrinking any level
# with >= 1,000 crashes by well under 1%.
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
    export_model(model_a, outcome, "A")
    export_model(model_b, outcome, "B")
    factors = [f for f in specs.PRE_CRASH + specs.CIRCUMSTANCE if f != "YEAR"] + ["YEAR"]
    out = []
    for f in factors:
        levels = observed_levels(df, f)
        crude = crude_table(df, design, outcome, f, levels, n_years)
        b = factor_contrasts(model_b, df, f, levels).add_prefix("B_")
        parts = [crude]
        if f in specs.PRE_CRASH:
            a = factor_contrasts(model_a, df, f, levels).add_prefix("A_")
            parts.append(a.drop(columns=["A_factor", "A_level"]))
        parts.append(b.drop(columns=["B_factor", "B_level"]))
        merged = pd.concat(parts, axis=1)
        out.append(merged)
        log.info("contrasts done for %s", f)
    res = pd.concat(out, ignore_index=True)
    res.insert(0, "outcome", outcome)
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
        population="CRSS police-reported crashes 2016-2024 with known maximum severity",
        unit="crash",
        outcome=outcome,
        method="Pseudo-ML logistic regression; Taylor-linearised variance (25 strata, 67 PSUs); "
        "model A = PRE_CRASH covariates, model B = A + crash type + number of vehicles",
        inputs=["data/processed/crss_crash.parquet"],
        extra={
            "n": len(df),
            "events": int(df[outcome].sum()),
            "design_df": design.df,
            "converged": [model_a.converged_, model_b.converged_],
        },
    )
    return res


def export_model(model: SurveyLogit, outcome: str, name: str) -> None:
    """Save a fitted model (levels, coefficients, design-based covariance) for prediction in
    the interface without refitting.  Predictions are conditional on a reported crash."""
    save_json(
        {
            "outcome": outcome,
            "model": name,
            "population": "CRSS police-reported crashes 2016-2024 with known maximum severity",
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


def run(outcomes: Sequence[str] = ("fatal", "ka")) -> dict[str, pd.DataFrame]:
    out = {}
    for oc in outcomes:
        res = crude_vs_adjusted(oc)
        save_table(
            res,
            MODULE,
            f"{oc}_crude_vs_adjusted",
            description=f"Crude and standardised adjusted risk ratios for crash outcome '{oc}' by factor level",
            population="CRSS police-reported crashes 2016-2024 with known maximum severity",
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
            population="CRSS police-reported crashes 2016-2024 with known maximum severity",
            unit="crash",
            outcome=oc,
            method="Model A with speeding replaced by speeding type; standardised margins; linearised CIs",
            inputs=["data/processed/crss_crash.parquet"],
        )
        out[f"{oc}_speeding_type"] = st
    return out
