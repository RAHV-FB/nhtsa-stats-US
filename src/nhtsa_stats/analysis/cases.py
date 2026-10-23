"""Evidence-based case comparisons (Phase 2, Q7; docs/research_plan_phase2.md §5.5).

A user describes a case -- e.g. "a light-vehicle driver who exceeded the limit, with alcohol,
unbelted, at night, in a single-vehicle crash" -- and wants to know what the records can say
about it.  This module pre-computes, for every combination on a grid of driver-level factors:

1. the observational support in CRSS (sample drivers with exactly that recorded combination,
   deaths among them) and in FARS (drivers killed with that combination: a census count of
   *deaths*, not a risk);
2. the observed weighted death rate, shown only where the cell has >= 30 drivers and >= 10
   deaths;
3. the model-standardised probability that the driver dies, with a design-based CI, withheld
   where the cell is unsupported (extrapolation);
4. one-factor-removed contrasts: the modelled risk with each present factor set to its
   reference, holding the others;
5. Shapley allocations of the modelled risk difference between the case and the
   all-reference case, on the risk-difference scale and on the log-risk-ratio scale.  The two
   allocations differ, which demonstrates that "how much of the death is due to each factor"
   has no unique answer even within one model.

Population and model
    CRSS drivers of light passenger vehicles 2016-2024 with known injury outcome and belt use
    belted / none / unknown.  Outcome: the driver dies (imputed severity).  Survey logistic
    model with the case factors (speeding: none / exceeded limit / other speeding / unknown;
    alcohol imputed; unbelted; night; single-vehicle) as main effects plus all pairwise
    products of their indicators, adjusted for crash environment, driver age and sex, vehicle
    body type and the other drivers' recorded behaviour; standardised over all such drivers.
    A second model adds police-reported drugs (yes / no) on the subset with known drug status.

Not inferable: the cause of any individual death; the share of a death "due to" each factor.
"""

from __future__ import annotations

import itertools
import logging
import math

import numpy as np
import pandas as pd
import polars as pl

from nhtsa_stats import config
from nhtsa_stats.analysis import multifactor
from nhtsa_stats.analysis.confounding import collapse_cells
from nhtsa_stats.analysis.survey import ModelSpec, SurveyLogit, logit_ci
from nhtsa_stats.reporting.io import save_table

log = logging.getLogger(__name__)
MODULE = "cases"
RIDGE = 0.01
MIN_N, MIN_EVENTS = config.MIN_CELL_N, 10

# Factor -> (column, levels in grid order; first = reference)
GRID: dict[str, tuple[str, list[str]]] = {
    "speeding": ("case_speeding", ["none", "exceeded_limit", "other_speeding"]),
    "alcohol": ("own_alcohol_im", ["no", "yes"]),
    "unbelted": ("unbelted", ["no", "yes"]),
    "night": ("night_period", ["day", "night"]),
    "single_vehicle": ("single_vehicle", ["no", "yes"]),
}
DRUG_GRID = ("own_drugs_police", ["no", "yes"])
COVARIATES = [c for c in multifactor.ENV if c not in ("tod", "light")] + [
    "age",
    "sex",
    "body",
    "other_speeding",
    "other_alcohol_im",
]


def case_frame():
    df, design = multifactor.driver_frame()
    mask = (
        df["body"].isin(list(multifactor.LPV_BODY_GROUPS)).to_numpy()
        & df["drv_restraint"].isin(["belted", "none", multifactor.UNK]).to_numpy()
        & df["drv_killed"].notna().to_numpy()
    )
    df, design = df.loc[mask].reset_index(drop=True), design.subset(mask)
    st = df["own_speeding_type"].astype(str)
    df["case_speeding"] = np.select(
        [
            st == "no",
            st == "exceeded_limit_or_racing",
            st.isin(["too_fast_for_conditions", "speeding_unspecified"]),
        ],
        ["none", "exceeded_limit", "other_speeding"],
        multifactor.UNK,
    )
    df["single_vehicle"] = np.where(df["n_vehicles"] == "1", "yes", "no")
    df["drv_killed"] = df["drv_killed"].astype(float)
    return df, design


def _products(factors: dict[str, tuple[str, list[str]]]) -> list:
    """Pairwise products of non-reference indicators of the grid factors."""
    ind = [(col, [lv]) for col, levels in factors.values() for lv in levels[1:]]
    out = []
    for (ca, la), (cb, lb) in itertools.combinations(ind, 2):
        if ca != cb:
            out.append(((ca, la), (cb, lb)))
    return out


def fit(df: pd.DataFrame, design, factors: dict[str, tuple[str, list[str]]]):
    cols = list(dict.fromkeys([*(c for c, _ in factors.values()), *COVARIATES]))
    work = df[[*cols, "drv_killed"]].copy()
    for c in cols:
        work[c] = np.asarray(work[c], dtype=object)
    cells, cd = collapse_cells(work, design, cols, "drv_killed")
    cats = {}
    for c in cols:
        fl = next((levels for col, levels in factors.values() if col == c), None)
        ref = fl[0] if fl else pd.Series(work[c]).value_counts().index[0]
        cats[c] = [ref, *sorted((v for v in pd.unique(work[c]) if v != ref), key=str)]
    m = SurveyLogit(
        ModelSpec(categorical=cats, products=_products(factors)),
        ridge=RIDGE * len(cells) / len(work),
    )
    m.fit(cells, cells["drv_killed"].to_numpy(float), cd)
    return m, cells, cd


def scenario_key(s: dict[str, str]) -> str:
    return "|".join(f"{k}={v}" for k, v in s.items())


def case_label(key: str) -> str:
    """Scenario key without '|' (report placeholders use '|' as a separator)."""
    return key.replace("|", ", ")


def grid(factors) -> list[dict[str, str]]:
    names = list(factors)
    return [
        dict(zip(names, combo, strict=True))
        for combo in itertools.product(*(factors[n][1] for n in names))
    ]


def support(
    df: pd.DataFrame, design, factors, scenarios, pred: np.ndarray | None = None
) -> dict[str, dict]:
    """Observed support per combination; with ``pred`` (model prediction for every row, at its
    own covariates) also the mean prediction in the cell: observed vs predicted-in-cell is a
    calibration check, predicted-in-cell vs standardised risk shows the covariate-mix effect."""
    w = design.weight
    y = df["drv_killed"].to_numpy(float)
    out = {}
    cols = {n: df[c].astype(str).to_numpy() for n, (c, _) in factors.items()}
    for s in scenarios:
        mask = np.ones(len(df), bool)
        for n, v in s.items():
            mask &= cols[n] == v
        n = int(mask.sum())
        ev = int(y[mask].sum())
        rate = float(np.sum(w[mask] * y[mask]) / np.sum(w[mask])) if n else np.nan
        out[scenario_key(s)] = {
            "crss_n": n,
            "crss_deaths": ev,
            "observed_rate": rate if (n >= MIN_N and ev >= MIN_EVENTS) else np.nan,
            "supported": n >= MIN_N and ev >= MIN_EVENTS,
            "predicted_in_cell": (
                float(np.sum(w[mask] * pred[mask]) / np.sum(w[mask]))
                if pred is not None and n >= MIN_N and ev >= MIN_EVENTS
                else np.nan
            ),
        }
    return out


def fars_counts(factors) -> dict[str, float]:
    """FARS light-vehicle drivers killed with each combination (alcohol: expected count over
    the 10 BAC implicates; drugs: police-reported, matching the CRSS definition)."""
    cols = [
        "own_speeding_type",
        "drv_killed",
        "drv_restraint",
        "night",
        "n_vehicles",
        "body",
        "own_drugs_police",
        *[f"drv_bac08_mi_{i}" for i in range(1, 11)],
    ]
    f = (
        pl.read_parquet(config.PROCESSED_DIR / "fars_driver.parquet", columns=cols)
        .filter(
            (pl.col("drv_killed") == 1) & pl.col("body").is_in(list(multifactor.LPV_BODY_GROUPS))
        )
        .to_pandas()
    )
    st = f["own_speeding_type"].astype(str)
    f["speeding"] = np.select(
        [
            st == "no",
            st == "exceeded_limit_or_racing",
            st.isin(["too_fast_for_conditions", "speeding_unspecified"]),
        ],
        ["none", "exceeded_limit", "other_speeding"],
        "unknown",
    )
    f["unbelted"] = f["drv_restraint"].map({"belted": "no", "none": "yes"}).fillna("unknown")
    f["night"] = f["night"].map({1: "night", 0: "day"}).fillna("unknown")
    f["single_vehicle"] = np.where(f["n_vehicles"].astype(str) == "1", "yes", "no")
    f["drugs"] = f["own_drugs_police"].astype(str)
    p_alc = f[[f"drv_bac08_mi_{i}" for i in range(1, 11)]].fillna(0).mean(axis=1).to_numpy()
    names = list(factors)
    out = {}
    for s in grid(factors):
        mask = np.ones(len(f), bool)
        for n, v in s.items():
            if n == "alcohol":
                continue
            mask &= f[n].astype(str).to_numpy() == v
        wa = p_alc if s.get("alcohol") == "yes" else 1 - p_alc
        out[scenario_key({k: s[k] for k in names})] = float(np.sum(wa[mask])) / len(config.YEARS)
    return out


def _shapley(present: list[str], value) -> dict[str, float]:
    n = len(present)
    phi = {}
    for j in present:
        others = [x for x in present if x != j]
        tot = 0.0
        for r in range(n):
            wgt = math.factorial(r) * math.factorial(n - r - 1) / math.factorial(n)
            for s in itertools.combinations(others, r):
                tot += wgt * (value((*s, j)) - value(s))
        phi[j] = tot
    return phi


def _risk_function(vals: dict, case: dict[str, str], ref: dict[str, str]):
    """Risk with the factors in ``subset`` at their case level and the others at reference."""

    def risk_of(subset) -> float:
        sc = {n: (case[n] if n in subset else ref[n]) for n in case}
        return vals[scenario_key(sc)]

    return risk_of


def analyse(df, design, factors, label: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    m, cells, cd = fit(df, design, factors)
    scenarios = grid(factors)
    sup = support(df, design, factors, scenarios, m.predict(df))
    scen = {}
    for s in scenarios:
        assign = {factors[n][0]: v for n, v in s.items()}
        scen[scenario_key(s)] = lambda d, a=assign: d.assign(**a)
    ms = m.margins(cells, scen)
    t = cd.tcrit()
    ref = {n: lv[0] for n, (_, lv) in factors.items()}
    ref_key = scenario_key(ref)
    fars = fars_counts(factors) if "drugs" not in factors else {}
    rows, contrast_rows = [], []
    for s in scenarios:
        k = scenario_key(s)
        e = ms.estimate(k)
        lo, hi = logit_ci(e.estimate, e.se, e.df)
        ok = sup[k]["supported"] and sup[ref_key]["supported"]
        present = [n for n in s if s[n] != ref[n]]
        rr = ms.log_ratio(k, ref_key)
        rd = ms.difference(k, ref_key)
        rec = {
            "model": label,
            "scenario": k,
            "case": case_label(k),
            **{n: s[n] for n in s},
            "n_factors_present": len(present),
            **sup[k],
            "fars_drivers_killed_per_year": fars.get(k, np.nan),
            "model_risk": e.estimate if ok else np.nan,
            "model_risk_low": lo if ok else np.nan,
            "model_risk_high": hi if ok else np.nan,
            "rr_vs_reference": float(np.exp(rr.estimate)) if ok else np.nan,
            "rr_vs_reference_low": float(np.exp(rr.estimate - t * rr.se)) if ok else np.nan,
            "rr_vs_reference_high": float(np.exp(rr.estimate + t * rr.se)) if ok else np.nan,
            "rd_vs_reference": rd.estimate if ok else np.nan,
            "status": "supported" if ok else "insufficient support: no model estimate shown",
        }
        rows.append(rec)
        if not ok or not present:
            continue
        vals = ms.values
        risk_of = _risk_function(vals, s, ref)
        # Allocations use every intermediate combination; withhold them if any is unsupported.
        alloc_ok = all(
            sup[scenario_key({n: (s[n] if n in sub else ref[n]) for n in s})]["supported"]
            for r_ in range(len(present) + 1)
            for sub in itertools.combinations(present, r_)
        )
        na = np.nan

        sh_rd = _shapley(present, lambda sub, r=risk_of: r(sub) - r(()))
        sh_lr = _shapley(present, lambda sub, r=risk_of: float(np.log(r(sub) / r(()))))
        total_rd, total_lr = (
            risk_of(tuple(present)) - risk_of(()),
            float(np.log(risk_of(tuple(present)) / risk_of(()))),
        )
        for n in present:
            without = dict(s, **{n: ref[n]})
            kw = scenario_key(without)
            sup_w = sup[kw]["supported"]
            c_rr = ms.log_ratio(k, kw)
            # Order-specific attributions (first and last position) bracket the Shapley value.
            first = risk_of((n,)) - risk_of(())
            last = risk_of(tuple(present)) - risk_of(tuple(x for x in present if x != n))
            contrast_rows.append(
                {
                    "model": label,
                    "scenario": k,
                    "case": case_label(k),
                    "factor": n,
                    "case_level": s[n],
                    "risk_without_factor": vals[kw] if sup_w else np.nan,
                    "rr_case_vs_without": float(np.exp(c_rr.estimate)) if sup_w else np.nan,
                    "rr_case_vs_without_low": float(np.exp(c_rr.estimate - t * c_rr.se))
                    if sup_w
                    else np.nan,
                    "rr_case_vs_without_high": float(np.exp(c_rr.estimate + t * c_rr.se))
                    if sup_w
                    else np.nan,
                    "without_factor_supported": sup_w,
                    "allocation_supported": alloc_ok,
                    "shapley_share_risk_difference": sh_rd[n] / total_rd if alloc_ok else na,
                    "shapley_share_log_rr": sh_lr[n] / total_lr if alloc_ok else na,
                    "share_if_added_first": first / total_rd if alloc_ok else na,
                    "share_if_added_last": last / total_rd if alloc_ok else na,
                }
            )
    return pd.DataFrame(rows), pd.DataFrame(contrast_rows)


def run() -> dict[str, pd.DataFrame]:
    df, design = case_frame()
    scen, contr = analyse(df, design, GRID, "main (no drugs)")
    known = df["own_drugs_police"].isin(["yes", "no"]).to_numpy()
    dfk, dk = df.loc[known].reset_index(drop=True), design.subset(known)
    g2 = {**{k: v for k, v in GRID.items() if k != "night"}, "drugs": DRUG_GRID}
    scen2, contr2 = analyse(dfk, dk, g2, "drug-known subset (police-reported drugs)")
    scen_all = pd.concat([scen, scen2], ignore_index=True)
    contr_all = pd.concat([contr, contr2], ignore_index=True)
    pop = "CRSS 2016-2024 drivers of light passenger vehicles (belt use belted/none/unknown); second model: drivers with known police drug status"
    method = "Survey logistic model with grid factors, all pairwise products of their indicators, and environment/person covariates; g-computation standardised over the population; Taylor linearisation (42 df); cells with < 30 drivers or < 10 deaths withheld; Shapley allocations exact over the factors present"
    save_table(
        scen_all,
        MODULE,
        "scenarios",
        description="Every grid case: CRSS and FARS support, observed rate, model-standardised risk of the driver dying, RR and RD vs the all-reference case",
        population=pop,
        unit="scenario",
        outcome="driver killed",
        method=method,
        inputs=[*multifactor.INPUT, "data/processed/fars_driver.parquet"],
    )
    save_table(
        contr_all,
        MODULE,
        "scenario_contrasts",
        description="For each case and each factor present: risk with that factor at reference, RR, and Shapley / first / last-position shares of the modelled risk difference on two scales",
        population=pop,
        unit="scenario x factor",
        outcome="driver killed",
        method=method,
        inputs=multifactor.INPUT,
    )
    return {"scenarios": scen_all, "contrasts": contr_all}
