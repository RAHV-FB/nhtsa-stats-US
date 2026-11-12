"""Measurement validity of behavioural and protective factors (RQ3).

Question: are speeding, alcohol, drug, distraction and restraint codes ascertained
differently by crash severity or year, and how far could that move the severity
associations reported elsewhere?

Analyses (outputs/tables/measurement):

``unknown_by_severity``   weighted share coded unknown / yes by KABCO level (CRSS).
``unknown_by_year``       the same by year, separately for fatal and non-fatal crashes, with
                          year-on-year changes flagged as potential coding breaks (>= 5 pp).
``fars_crss_fatal_composition``  share of *fatal* crashes with each attribute in CRSS (weighted)
                          and FARS (census), by year: both describe the same population, so
                          systematic differences indicate source-specific ascertainment.
``fars_testing``          alcohol and drug test rates among FARS drivers by survival status,
                          year and state (selection into measurement).
``police_vs_bac``         accuracy of police-reported alcohol involvement against measured BAC
                          >= 0.08 among tested FARS drivers, killed vs surviving.
``restraint_reporting``   reported belt use and unknown restraint among CRSS occupants by KABCO.
``imputed_bac_injury``    diagnostic of NHTSA's multiple imputation of BAC: among FARS drivers whose BAC
                          is imputed (not tested, no result), is the imputed BAC >= .08 associated
                          with the driver being killed, adjusted for the covariates available to
                          tested and untested drivers alike?  Compared with the same association
                          among tested drivers.  Not a causal estimate (see the function).
``qba_grid``              quantitative bias analysis: the crude fatal risk ratio for speeding,
                          limit exceedance (vs no speeding) and alcohol after correcting for
                          differential sensitivity of recording in fatal vs non-fatal crashes,
                          over a grid of assumptions.

Interpretation: these quantify *how* measurement depends on severity; the bias analysis gives
the range of risk ratios compatible with stated misclassification assumptions, not a single
corrected truth.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

import numpy as np
import pandas as pd

from nhtsa_stats import config
from nhtsa_stats.analysis import data
from nhtsa_stats.analysis.survey import ModelSpec, SurveyLogit, svy_mean
from nhtsa_stats.ingestion.cache import load_table
from nhtsa_stats.processing import harmonize as h
from nhtsa_stats.reporting.io import save_table

log = logging.getLogger(__name__)
MODULE = "measurement"
BREAK_PP = 5.0

CRASH_FIELDS = {
    "speeding": "Speeding-related (any vehicle)",
    "alcohol": "Alcohol involved (police-reported ALCOHOL)",
    "drugs": "Drug involvement (any driver, police-reported)",
    "distracted": "Distracted driver (any driver)",
    "young_driver": "Driver 15-20 involved (CRSS: NHTSA-imputed age)",
}


def observed_severity(max_sev: pd.Series) -> np.ndarray:
    """Recorded (unimputed) maximum severity: 0-4, or 9 for unknown severity, else -1.

    Recording completeness is stratified by the severity police actually recorded, with
    unknown severity as its own stratum. Stratifying by imputed severity would move crashes of
    unknown severity -- which also have the most unknown fields -- into the KABCO cells.
    """
    v = max_sev.to_numpy(float)
    return np.where(np.isin(v, [0, 1, 2, 3, 4, 9]), v, -1).astype(int)


def unknown_by_severity() -> pd.DataFrame:
    df, design = data.crss_crash(outcome=None)
    sev = observed_severity(df["MAX_SEV"])
    rows = []
    for k in (0, 1, 2, 3, 4, 9):
        dom = sev == k
        for var, label in CRASH_FIELDS.items():
            x = df[var].to_numpy(float)
            unk = svy_mean(design, np.isnan(x).astype(float), dom)
            yes = svy_mean(design, (x == 1).astype(float), dom)
            yes_known = svy_mean(design, (x == 1).astype(float), dom & ~np.isnan(x))
            rows.append(
                {
                    "kabco": k,
                    "field": var,
                    "label": label,
                    "n": int(dom.sum()),
                    "pct_unknown": 100 * unk.estimate,
                    "pct_unknown_se": 100 * unk.se,
                    "pct_yes": 100 * yes.estimate,
                    "pct_yes_among_known": 100 * yes_known.estimate,
                }
            )
        x = df["speed_limit"].to_numpy()
        unk = svy_mean(design, (x == "unknown").astype(float), dom)
        rows.append(
            {
                "kabco": k,
                "field": "speed_limit",
                "label": "Posted speed limit",
                "n": int(dom.sum()),
                "pct_unknown": 100 * unk.estimate,
                "pct_unknown_se": 100 * unk.se,
            }
        )
    return pd.DataFrame(rows)


def unknown_by_year() -> pd.DataFrame:
    # 'fatal' here is the recorded severity (MAX_SEV 4 vs 0-3), see observed_severity().
    df, design = data.crss_crash(outcome=None)
    sev = observed_severity(df["MAX_SEV"])
    rows = []
    for y in config.YEARS:
        for fat in (0, 1):
            in_sev = (sev == 4) if fat else np.isin(sev, [0, 1, 2, 3])
            dom = (df["YEAR"] == y).to_numpy() & in_sev
            for var in [*CRASH_FIELDS, "alcohol_im"]:
                x = df[var].to_numpy(float)
                rows.append(
                    {
                        "YEAR": y,
                        "fatal": fat,
                        "field": var,
                        "n": int(dom.sum()),
                        "pct_unknown": 100
                        * svy_mean(design, np.isnan(x).astype(float), dom).estimate,
                        "pct_yes": 100 * svy_mean(design, (x == 1).astype(float), dom).estimate,
                    }
                )
    out = pd.DataFrame(rows).sort_values(["field", "fatal", "YEAR"])
    out["change_pp_unknown"] = out.groupby(["field", "fatal"])["pct_unknown"].diff()
    out["change_pp_yes"] = out.groupby(["field", "fatal"])["pct_yes"].diff()
    out["coding_break_flag"] = (out["change_pp_unknown"].abs() >= BREAK_PP) | (
        out["change_pp_yes"].abs() >= BREAK_PP
    )
    return out.reset_index(drop=True)


def fars_crss_fatal_composition() -> pd.DataFrame:
    df, design = data.crss_crash(outcome="fatal")
    fars = data.fars_crash()
    attrs = {
        "speeding": lambda d: d["speeding"] == 1,
        "speeding_unknown": lambda d: d["speeding"].isna(),
        "dark": lambda d: d["dark"] == 1,
        "any_pedestrian": lambda d: d["any_pedestrian"] == 1,
        "any_motorcycle": lambda d: d["any_motorcycle"] == 1,
        "single_vehicle": lambda d: d["VE_FORMS"] == 1,
        "young_driver": lambda d: d["young_driver"] == 1,
        "speed_limit_unknown": lambda d: d["speed_limit"] == "unknown",
        "junction_unknown": lambda d: d["junction"] == "unknown",
    }
    rows = []
    for y in [*config.YEARS, "all"]:
        sel = (df["fatal"] == 1) & ((df["YEAR"] == y) if y != "all" else True)
        dom = sel.to_numpy()
        fy = fars if y == "all" else fars[fars["YEAR"] == y]
        for name, f in attrs.items():
            ind = f(df).to_numpy(float)
            est = svy_mean(design, ind, dom)
            lo, hi = est.ci()
            share_f = float(f(fy).mean())
            rows.append(
                {
                    "YEAR": y,
                    "attribute": name,
                    "crss_n_fatal": int(dom.sum()),
                    "crss_share": est.estimate,
                    "crss_low": lo,
                    "crss_high": hi,
                    "fars_share": share_f,
                    "fars_within_crss_ci": lo <= share_f <= hi,
                    "ratio_crss_to_fars": est.estimate / share_f if share_f else np.nan,
                }
            )
    return pd.DataFrame(rows)


def fars_testing() -> pd.DataFrame:
    per = data.fars_person()
    drv = per[per["ptype"] == "driver"].copy()
    drv["status"] = np.where(
        drv["killed"] == 1, "killed", np.where(drv["killed"] == 0, "survived", "unknown")
    )
    # Drug testing: any specimen result other than 'test not given' in the drugs table (2018+), or
    # the person-level DRUGS-test fields in earlier years are not comparable -> 2018+ only.
    drugs = load_table(
        "FARS",
        "drugs",
        years=[y for y in config.YEARS if y >= 2018],
        columns=["ST_CASE", "VEH_NO", "PER_NO", "DRUGSPEC", "DRUGRES"],
    ).unique()
    # DRUGSPEC (embedded labels): 0 test not given; 96 not reported; 99 reported as unknown if
    # tested. 97 'unknown specimen' and 98 'other specimen' mean a test was given.
    tested = (
        drugs.to_pandas()
        .assign(tested=lambda d: ~d["DRUGSPEC"].isin([0, 96, 99]))
        .groupby(["YEAR", "ST_CASE", "VEH_NO", "PER_NO"])["tested"]
        .max()
        .reset_index()
        .rename(columns={"ST_CASE": "case_id"})
    )
    drv = drv.merge(tested, on=["YEAR", "case_id", "VEH_NO", "PER_NO"], how="left")
    rows = []
    for (y, st), g in drv.groupby(["YEAR", "status"]):
        rows.append(
            {
                "level": "national",
                "YEAR": y,
                "status": st,
                "drivers": len(g),
                "pct_alcohol_tested": 100 * (g["alc_tested"] == 1).mean(),
                "pct_alcohol_test_status_unknown": 100 * g["alc_tested"].isna().mean(),
                "pct_drug_tested": 100 * g["tested"].mean() if y >= 2018 else np.nan,
            }
        )
    nat = pd.DataFrame(rows)
    st_rows = []
    late = drv[drv["YEAR"] >= 2022]
    for (state, st), g in late.groupby(["STATE", "status"]):
        st_rows.append(
            {
                "level": "state_2022_2024",
                "STATE": state,
                "status": st,
                "drivers": len(g),
                "pct_alcohol_tested": 100 * (g["alc_tested"] == 1).mean(),
                "pct_drug_tested": 100 * g["tested"].mean(),
            }
        )
    return pd.concat([nat, pd.DataFrame(st_rows)], ignore_index=True)


def police_vs_bac() -> pd.DataFrame:
    per = data.fars_person()
    drv = per[
        (per["ptype"] == "driver") & per["bac_measured"].notna() & per["pr_alcohol"].notna()
    ].copy()
    drv["bac08"] = (drv["bac_measured"] >= 0.08).astype(int)
    rows = []
    for status, g in [
        ("killed", drv[drv["killed"] == 1]),
        ("survived", drv[drv["killed"] == 0]),
        ("all", drv),
    ]:
        tp = int(((g["pr_alcohol"] == 1) & (g["bac08"] == 1)).sum())
        fn = int(((g["pr_alcohol"] == 0) & (g["bac08"] == 1)).sum())
        fp = int(((g["pr_alcohol"] == 1) & (g["bac08"] == 0)).sum())
        tn = int(((g["pr_alcohol"] == 0) & (g["bac08"] == 0)).sum())
        rows.append(
            {
                "driver_status": status,
                "n_tested_with_police_report": len(g),
                "bac08_prevalence": (tp + fn) / max(len(g), 1),
                "police_sensitivity_vs_bac08": tp / max(tp + fn, 1),
                "police_specificity_vs_bac08": tn / max(tn + fp, 1),
                "ppv": tp / max(tp + fp, 1),
                "tp": tp,
                "fn": fn,
                "fp": fp,
                "tn": tn,
            }
        )
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------------------
# Selection into measurement: who is tested, and does police sensitivity depend on it?
# --------------------------------------------------------------------------------------
def _wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    if n <= 0:
        return np.nan, np.nan
    p = k / n
    den = 1 + z**2 / n
    mid = (p + z**2 / (2 * n)) / den
    half = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / den
    return float(mid - half), float(mid + half)


def _driver_status(per: pd.DataFrame) -> pd.DataFrame:
    drv = per[per["ptype"] == "driver"].copy()
    drv["driver_status"] = np.where(
        drv["killed"] == 1, "killed", np.where(drv["killed"] == 0, "survived", "unknown")
    )
    return drv


def alcohol_testing_share(drv: pd.DataFrame) -> pd.DataFrame:
    """Share of each driver group that was alcohol-tested and the share that enters the
    police-versus-BAC contrast (measured BAC *and* a known police alcohol field)."""
    rows = []
    groups = [(s, drv[drv["driver_status"] == s]) for s in ("killed", "survived")]
    groups.append(("all (killed + survived)", drv[drv["driver_status"] != "unknown"]))
    for status, g in groups:
        in_sample = g["bac_measured"].notna() & g["pr_alcohol"].notna()
        bac08 = (g.loc[in_sample, "bac_measured"] >= 0.08).astype(int)
        rows.append(
            {
                "driver_status": status,
                "n_drivers": len(g),
                "n_alcohol_tested": int((g["alc_tested"] == 1).sum()),
                "share_alcohol_tested": float((g["alc_tested"] == 1).mean()),
                "n_with_bac_result": int(g["bac_measured"].notna().sum()),
                "share_with_bac_result": float(g["bac_measured"].notna().mean()),
                "share_police_alcohol_known": float(g["pr_alcohol"].notna().mean()),
                "n_in_sensitivity_sample": int(in_sample.sum()),
                "share_in_sensitivity_sample": float(in_sample.mean()),
                "bac08_prevalence_in_sample": float(bac08.mean()),
                "note": "tested = FARS alcohol test given (ALC_STATUS); sample = BAC result and "
                "police alcohol field both known (the police_vs_bac rows)",
            }
        )
    return pd.DataFrame(rows)


def _sens_row(g: pd.DataFrame, scheme: str, group: str, status: str, rate_lo, rate_hi) -> dict:
    """Police-versus-BAC>=.08 accuracy among the tested drivers of ``g`` with both fields known."""
    s = g[g["bac_measured"].notna() & g["pr_alcohol"].notna()]
    bac = (s["bac_measured"] >= 0.08).to_numpy()
    pol = (s["pr_alcohol"] == 1).to_numpy()
    tp, fn = int((pol & bac).sum()), int((~pol & bac).sum())
    fp, tn = int((pol & ~bac).sum()), int((~pol & ~bac).sum())
    lo, hi = _wilson(tp, tp + fn)
    return {
        "scheme": scheme,
        "group": group,
        "driver_status": status,
        "group_survivor_test_rate_min": rate_lo,
        "group_survivor_test_rate_max": rate_hi,
        "n_drivers": len(g),
        "share_alcohol_tested": float((g["alc_tested"] == 1).mean()) if len(g) else np.nan,
        "n_in_sample": len(s),
        "bac08_prevalence": (tp + fn) / max(len(s), 1),
        "police_sensitivity_vs_bac08": tp / max(tp + fn, 1),
        "sensitivity_low": lo,
        "sensitivity_high": hi,
        "police_specificity_vs_bac08": tn / max(tn + fp, 1),
        "ppv": tp / max(tp + fp, 1),
        "tp": tp,
        "fn": fn,
        "fp": fp,
        "tn": tn,
    }


CUMULATIVE_RATES = (0.0, 0.2, 0.3, 0.4, 0.5)


def police_vs_bac_selection(drv: pd.DataFrame) -> pd.DataFrame:
    """Does police sensitivity against measured BAC depend on how widely drivers are tested?

    Surviving drivers are tested mostly on suspicion, so the 98% sensitivity among tested
    survivors may reflect that selection.  The place-and-year survivor alcohol-test rate
    (state x year, survivors) is used as the measure of how widely survivors are tested.  The
    contrast is shown (i) by terciles of that rate, (ii) cumulatively as the places included
    broaden (survivor test rate >= x) and (iii) by state terciles of the pooled-years rate.
    Killed drivers are shown in the same places for comparison.  Wilson CIs treat drivers as
    independent (crash clustering ignored).  Descriptive; not a corrected sensitivity."""
    d = drv[drv["driver_status"].isin(["killed", "survived"])].copy()
    surv = d[d["driver_status"] == "survived"]
    sy = surv.groupby(["STATE", "YEAR"])["alc_tested"].apply(lambda s: (s == 1).mean())
    d["sy_rate"] = pd.MultiIndex.from_frame(d[["STATE", "YEAR"]]).map(sy)
    st = surv.groupby("STATE")["alc_tested"].apply(lambda s: (s == 1).mean())
    d["st_rate"] = d["STATE"].map(st)
    d = d[d["sy_rate"].notna()]
    rows = []
    allrows = d
    for status in ("survived", "killed"):
        rows.append(
            _sens_row(
                allrows[allrows["driver_status"] == status], "all", "all", status, np.nan, np.nan
            )
        )
    for scheme, col in (
        ("state-year survivor test-rate tercile", "sy_rate"),
        ("state survivor test-rate tercile (pooled years)", "st_rate"),
    ):
        # terciles over survivor *drivers* so that each group holds a third of surviving drivers
        ranks = d.loc[d["driver_status"] == "survived", col]
        cuts = np.quantile(ranks, [1 / 3, 2 / 3])
        lab = np.select([d[col] <= cuts[0], d[col] <= cuts[1]], ["low", "middle"], "high")
        for g_name in ("low", "middle", "high"):
            m = lab == g_name
            lo, hi = float(d.loc[m, col].min()), float(d.loc[m, col].max())
            for status in ("survived", "killed"):
                rows.append(
                    _sens_row(
                        d[m & (d["driver_status"] == status).to_numpy()],
                        scheme,
                        g_name,
                        status,
                        lo,
                        hi,
                    )
                )
    for thr in CUMULATIVE_RATES:
        m = d["sy_rate"] >= thr
        for status in ("survived", "killed"):
            rows.append(
                _sens_row(
                    d[m & (d["driver_status"] == status)],
                    "cumulative: state-year survivor test rate >=",
                    f"{thr:.0%}",
                    status,
                    float(d.loc[m, "sy_rate"].min()),
                    float(d.loc[m, "sy_rate"].max()),
                )
            )
    return pd.DataFrame(rows)


def restraint_reporting() -> pd.DataFrame:
    # Stratified by recorded person severity (INJ_SEV; 9 = unknown), see observed_severity().
    df, design = data.crss_person(outcome=None)
    sev = observed_severity(df["INJ_SEV"])
    lpv = df["body"].isin(h.LPV_BODY_GROUPS).to_numpy() & (df["age"] >= 13).to_numpy()
    rows = []
    for k in (0, 1, 2, 3, 4, 9):
        dom = lpv & (sev == k)
        r = df["restraint"].to_numpy()
        known = dom & np.isin(r, ["belted", "none"])
        rows.append(
            {
                "kabco": k,
                "n_occupants": int(dom.sum()),
                "pct_unknown": 100 * svy_mean(design, (r == "unknown").astype(float), dom).estimate,
                "pct_belted_among_known": 100
                * svy_mean(design, (r == "belted").astype(float), known).estimate,
                "pct_none_among_known": 100
                * svy_mean(design, (r == "none").astype(float), known).estimate,
            }
        )
    return pd.DataFrame(rows)


def corrected_rr(
    a: float, b: float, c: float, d: float, se_f: float, se_n: float, sp: float = 1.0
) -> float:
    """Crude RR of fatality for exposure after correcting non-differential specificity ``sp``
    and outcome-specific sensitivities (``se_f`` among fatal, ``se_n`` among non-fatal).

    a = exposed fatal, b = exposed non-fatal, c = unexposed fatal, d = unexposed non-fatal
    (weighted counts as recorded).  Standard matrix-method correction (Lash, Fox & Fink).
    """
    fat, non = a + c, b + d
    a_true = (a - (1 - sp) * fat) / (se_f + sp - 1)
    b_true = (b - (1 - sp) * non) / (se_n + sp - 1)
    c_true, d_true = fat - a_true, non - b_true
    if min(a_true, b_true, c_true, d_true) <= 0:
        return np.nan
    return (a_true / (a_true + b_true)) / (c_true / (c_true + d_true))


# Non-fatal recording sensitivities on the grid.  Limit exceedance has a far larger crude RR,
# so its grid extends to very low sensitivities to show where the association would vanish.
SE_NONFATAL = (0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0)
SE_NONFATAL_WIDE = (0.05, 0.1, 0.15, 0.2, *SE_NONFATAL)


def qba_grid() -> pd.DataFrame:
    df, design = data.crss_crash(outcome="fatal")
    w = design.weight
    # Exceeded limit / racing vs no speeding; other speeding types and unknown are left out.
    st = df["speeding_type"].astype(str)
    exceeded = np.where(st == "exceeded_limit_or_racing", 1.0, np.where(st == "no", 0.0, np.nan))
    rows = []
    for var, x, grid in (
        ("speeding", df["speeding"].to_numpy(float), SE_NONFATAL),
        ("alcohol_im", df["alcohol_im"].to_numpy(float), SE_NONFATAL),
        ("exceeded_limit", exceeded, SE_NONFATAL_WIDE),
    ):
        y = df["fatal"].to_numpy(float)
        known = ~np.isnan(x)
        a = w[known & (x == 1) & (y == 1)].sum()
        b = w[known & (x == 1) & (y == 0)].sum()
        c = w[known & (x == 0) & (y == 1)].sum()
        d = w[known & (x == 0) & (y == 0)].sum()
        rr_obs = (a / (a + b)) / (c / (c + d))
        for se_f in (0.7, 0.8, 0.9, 1.0):
            for se_n in grid:
                for sp in (1.0, 0.99):
                    rr = corrected_rr(a, b, c, d, se_f, se_n, sp)
                    rows.append(
                        {
                            "exposure": var,
                            "se_fatal": se_f,
                            "se_nonfatal": se_n,
                            "specificity": sp,
                            "rr_observed": rr_obs,
                            "rr_corrected": rr,
                            "bias_factor": rr / rr_obs if np.isfinite(rr) else np.nan,
                        }
                    )
    return pd.DataFrame(rows)


def alcohol_coding_sensitivity() -> pd.DataFrame:
    """Adjusted fatal RR for alcohol under three codings and two periods.

    Codings: NHTSA-imputed ALCHL_IM (primary); police-reported ALCOHOL complete-case (unknown
    crashes dropped); police-reported with unknown counted as "no".  Periods: 2016-2018 (non-
    reports mostly coded "No") and 2019-2024 (non-reports coded unknown, then imputed).  The
    adjustment set is model A with the alcohol variable swapped.
    """
    from nhtsa_stats.analysis import severity, specs

    rows = []
    for period, years in (
        ("2016-2018", [2016, 2017, 2018]),
        ("2019-2024", list(range(2019, 2025))),
        ("2016-2024", list(config.YEARS)),
    ):
        df, design = severity.load("fatal", years)
        variants = {
            "imputed (ALCHL_IM)": ("alcohol_im", np.ones(len(df), dtype=bool), None),
            "police, complete case": ("alcohol", (df["alcohol"] != "unknown").to_numpy(), None),
            "police, unknown as no": (
                "alcohol",
                np.ones(len(df), dtype=bool),
                df["alcohol"].replace({"unknown": "no"}),
            ),
        }
        for name, (var, keep, newcol) in variants.items():
            d = df.copy()
            if newcol is not None:
                d[var] = newcol
            d = d.loc[keep].reset_index(drop=True)
            covs = [c for c in specs.PRE_CRASH if c != "alcohol_im"] + [var]
            m = severity.fit(d, design.subset(keep), "fatal", covs)
            levels = severity.observed_levels(d, var, ["no", "yes"])
            fc = severity.factor_contrasts(m, d, var, levels).set_index("level").loc["yes"]
            rows.append(
                {
                    "period": period,
                    "coding": name,
                    "n": len(d),
                    "events": int(d["fatal"].sum()),
                    "share_yes": float(
                        np.average(d[var] == "yes", weights=design.subset(keep).weight)
                    ),
                    "adj_rr": fc["adj_rr"],
                    "adj_rr_low": fc["adj_rr_low"],
                    "adj_rr_high": fc["adj_rr_high"],
                }
            )
            log.info("alcohol sensitivity %s %s done", period, name)
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------------------
# Does NHTSA's BAC imputation use injury?  (red-team item X1)
# --------------------------------------------------------------------------------------
IMPUTATION_COVARIATES = ("age_band", "sex", "body", "crash_type", "tod", "YEAR")
# Sensitivity set: adds police-reported alcohol (an input of NHTSA's imputation model, known for
# tested and untested drivers alike), light, area and weekend.
IMPUTATION_COVARIATES_EXTENDED = (
    *IMPUTATION_COVARIATES,
    "pr_alcohol",
    "light",
    "rural",
    "weekend",
)


def _levels_by_frequency(x: pd.Series) -> list:
    """Observed levels, most frequent first (the reference level of a dummy coding)."""
    return list(x.value_counts().index)


def imputed_bac_injury(per: pd.DataFrame | None = None) -> pd.DataFrame:
    """Is the imputed BAC >= .08 associated with being killed, among drivers who were not tested?

    DIAGNOSTIC of whether NHTSA's imputation model uses injury, NOT a causal estimate of the
    effect of alcohol.  For an untested driver the imputed BAC is a draw from a model; if the
    model does not use the injury outcome, the imputed ``p08`` (share of the 10 implicates with
    BAC >= .08) carries only what the covariates already predict about death, and its association
    with being killed, given those covariates, is expected to be weaker than among tested drivers
    (whose BAC is measured).  A larger or equal association among the untested suggests that
    the imputation model does use injury.  Both groups are fitted with the same covariates
    (age band, sex, vehicle body type, crash type, time of day, year; levels the NHTSA model may
    have used beyond these are unavailable to us).

    Rows: ``imputed`` (BAC not measured: ``ALC_RES`` outside 0-940, i.e. not tested or no result),
    ``tested`` (measured BAC; ``p08`` is then 0 or 1) and ``imputed vs tested`` (ratio of the two
    ORs from one model with a group x p08 interaction, Wald test of the interaction).  The OR is
    for ``p08`` = 1 versus 0 (BAC >= .08 in every implicate versus none), from a logistic
    regression of killed (drivers with known survival status) on ``p08`` and the covariates;
    the CI is cluster-robust (crash = cluster, FARS census; no sampling weights).
    """
    per = data.fars_person() if per is None else per
    d = per[(per["ptype"] == "driver") & per["killed"].notna() & per["p_p08"].notna()].copy()
    d["killed"] = d["killed"].astype(float)
    d["measured"] = d["ALC_RES"].between(0, 940)
    d["group"] = np.where(d["measured"], "tested", "imputed")
    d["p08"] = d["p_p08"].astype(float)
    for c in IMPUTATION_COVARIATES_EXTENDED:
        d[c] = d[c].astype(object).where(d[c].notna(), "unknown")
    d = d.reset_index(drop=True)
    design_all = data.fars_design(d)
    rows = []

    def levels(covariates: Sequence[str]) -> dict[str, list]:
        return {c: _levels_by_frequency(d[c]) for c in covariates}

    def fit(mask: np.ndarray, covariates: Sequence[str]) -> SurveyLogit:
        sub = d.loc[mask].reset_index(drop=True)
        spec = ModelSpec(
            categorical={c: _levels_by_frequency(sub[c]) for c in covariates}, numeric=["p08"]
        )
        return SurveyLogit(spec, ridge=0.01).fit(
            sub, sub["killed"].to_numpy(), design_all.subset(mask)
        )

    for set_name, covs in (
        ("primary", IMPUTATION_COVARIATES),
        ("plus police alcohol, light, area, weekend", IMPUTATION_COVARIATES_EXTENDED),
    ):
        for grp in ("imputed", "tested"):
            mask = (d["group"] == grp).to_numpy()
            crude = fit(mask, ()).coef_table().set_index("term").loc["p08"]
            adj_model = fit(mask, covs)
            adj = adj_model.coef_table().set_index("term").loc["p08"]
            rows.append(
                {
                    "covariate_set": set_name,
                    "group": grp,
                    "n_drivers": int(mask.sum()),
                    "n_killed": int(d.loc[mask, "killed"].sum()),
                    "mean_p08": float(d.loc[mask, "p08"].mean()),
                    "share_p08_above_half": float((d.loc[mask, "p08"] > 0.5).mean()),
                    "crude_or": crude["odds_ratio"],
                    "crude_or_low": crude["or_low"],
                    "crude_or_high": crude["or_high"],
                    "adj_or": adj["odds_ratio"],
                    "adj_or_low": adj["or_low"],
                    "adj_or_high": adj["or_high"],
                    "p": adj["p"],
                    "converged": bool(adj_model.converged_),
                    "adjusted_for": ", ".join(covs),
                }
            )
        # One model for both groups with a group x p08 interaction (a single set of covariate
        # effects, so a summary contrast rather than the ratio of the two separate fits above).
        pooled_spec = ModelSpec(
            categorical={"group": ["tested", "imputed"], **levels(covs)},
            numeric=["p08"],
            interactions=[("group", "p08")],
        )
        pooled = SurveyLogit(pooled_spec, ridge=0.01).fit(d, d["killed"].to_numpy(), design_all)
        ct = pooled.coef_table().set_index("term")
        term = "group[imputed]:p08"
        rows.append(
            {
                "covariate_set": set_name,
                "group": "imputed vs tested",
                "n_drivers": len(d),
                "n_killed": int(d["killed"].sum()),
                "adj_or": ct.loc[term, "odds_ratio"],
                "adj_or_low": ct.loc[term, "or_low"],
                "adj_or_high": ct.loc[term, "or_high"],
                "p": pooled.wald_test([term])["p"],
                "converged": bool(pooled.converged_),
                "adjusted_for": ", ".join(covs),
            }
        )
        log.info("imputed-BAC injury diagnostic: %s done", set_name)
    out = pd.DataFrame(rows)
    out["note"] = (
        "diagnostic of whether NHTSA's BAC imputation uses injury; not a causal estimate; "
        "OR for imputed/measured BAC >= .08 (p08 = 1) vs 0; last row = ratio of the two ORs"
    )
    return out


_CRSS_CRASH = "CRSS police-reported crashes 2016-2024"
_FARS_DRV = "FARS drivers (PER_TYP 1) 2016-2024"
_TESTED = "FARS drivers with a measured BAC result and a known police alcohol field"
# (population, unit, outcome, method) of each table, matching the code that builds it.
META: dict[str, tuple[str, str, str, str]] = {
    "unknown_by_severity": (
        f"{_CRSS_CRASH}, stratified by recorded (unimputed) maximum severity "
        "(KABCO 0-4 and 9 = unknown severity)",
        "crash (survey-weighted)",
        "share of crashes with each behavioural field coded unknown / yes",
        "Design-based weighted means (WEIGHT, PSUSTRAT, PSU_VAR) within severity domains",
    ),
    "unknown_by_year": (
        f"{_CRSS_CRASH}, by year; fatal = recorded MAX_SEV 4, non-fatal = 0-3 "
        "(unknown-severity crashes excluded)",
        "crash (survey-weighted)",
        "share unknown / yes per field; year-on-year change in percentage points",
        "Design-based weighted means by year and fatal status; changes >= 5 pp flagged as "
        "potential coding breaks",
    ),
    "fars_crss_fatal_composition": (
        "Fatal crashes 2016-2024: CRSS (fatal outcome known; MAXSEV_IM 4) and FARS (census)",
        "crash (CRSS survey-weighted, FARS unweighted)",
        "share of fatal crashes with each attribute",
        "Design-based CRSS shares with 95% CI compared with FARS census shares; "
        "ratio CRSS/FARS and whether FARS lies inside the CRSS CI",
    ),
    "fars_testing": (
        f"{_FARS_DRV} by survival status; drug testing 2018+ only; state rows 2022-2024",
        "driver",
        "percent alcohol-tested, alcohol test status unknown, and drug-tested",
        "Unweighted proportions by year x status and by state x status "
        "(selection into measurement)",
    ),
    "police_vs_bac": (
        f"{_TESTED}, by killed / survived / all",
        "driver",
        "police-reported alcohol versus measured BAC >= 0.08 (sensitivity, specificity, PPV)",
        "2x2 cross-classification of police alcohol report against measured BAC >= 0.08; "
        "unweighted counts, no sampling error",
    ),
    "alcohol_testing_share": (
        f"{_FARS_DRV} by killed / survived / all with known survival status",
        "driver",
        "share alcohol-tested, with a BAC result, and in the police-vs-BAC sample",
        "Unweighted shares; describes selection into the police-vs-BAC contrast",
    ),
    "police_vs_bac_selection": (
        f"{_TESTED}, in state-years with a survivor test rate; survivors and killed shown "
        "separately",
        "driver",
        "police sensitivity / specificity / PPV against measured BAC >= 0.08 by how widely "
        "surviving drivers are tested",
        "Unweighted 2x2 accuracy within state-year and state survivor test-rate terciles and "
        "cumulative thresholds; Wilson 95% CI for sensitivity (crash clustering ignored); "
        "descriptive, not a corrected sensitivity",
    ),
    "restraint_reporting": (
        "CRSS occupants of light passenger vehicles aged 13+ 2016-2024, stratified by recorded "
        "person severity (KABCO 0-4 and 9 = unknown)",
        "person (survey-weighted)",
        "percent restraint unknown; percent belted / unbelted among known restraint",
        "Design-based weighted means within severity domains",
    ),
    "qba_grid": (
        f"{_CRSS_CRASH} with known fatal outcome and known exposure "
        "(speeding, imputed alcohol, exceeded limit vs no speeding)",
        "crash (survey-weighted)",
        "crude fatal risk ratio for the exposure, corrected for recording sensitivity",
        "Quantitative bias analysis: matrix-method correction over a grid of fatal and "
        "non-fatal recording sensitivities and specificity; assumptions, not estimates",
    ),
    "alcohol_coding_sensitivity": (
        f"{_CRSS_CRASH} with known fatal outcome, periods 2016-2018, 2019-2024 and 2016-2024 "
        "(complete-case coding drops unknown-alcohol crashes)",
        "crash (survey-weighted)",
        "fatal crash (MAXSEV_IM 4) versus non-fatal; adjusted risk ratio for alcohol",
        "Design-based logistic model A with the alcohol variable swapped between imputed, "
        "complete-case and unknown-as-no codings; adjusted RR by marginal standardisation",
    ),
    "imputed_bac_injury": (
        f"{_FARS_DRV} with known survival status and an NHTSA-imputed BAC probability, "
        "split into untested (imputed) and tested (measured BAC)",
        "driver (FARS census, crash-clustered)",
        "driver killed; OR for imputed/measured BAC >= .08 (p08 = 1 vs 0)",
        "Logistic regression of killed on p08 plus covariates, cluster-robust CI, no sampling "
        "weights; group x p08 interaction gives the ratio of ORs; diagnostic, not causal",
    ),
}


def run() -> dict[str, pd.DataFrame]:
    drivers = _driver_status(data.fars_person())
    out = {
        "unknown_by_severity": unknown_by_severity(),
        "unknown_by_year": unknown_by_year(),
        "fars_crss_fatal_composition": fars_crss_fatal_composition(),
        "fars_testing": fars_testing(),
        "police_vs_bac": police_vs_bac(),
        "alcohol_testing_share": alcohol_testing_share(drivers),
        "police_vs_bac_selection": police_vs_bac_selection(drivers),
        "restraint_reporting": restraint_reporting(),
        "qba_grid": qba_grid(),
        "alcohol_coding_sensitivity": alcohol_coding_sensitivity(),
        "imputed_bac_injury": imputed_bac_injury(),
    }
    desc = {
        "unknown_by_severity": "Weighted % unknown / yes by KABCO for police-reported behavioural fields (CRSS crashes)",
        "unknown_by_year": "Weighted % unknown / yes by year and fatal status with coding-break flags (CRSS crashes)",
        "fars_crss_fatal_composition": "Attribute shares among fatal crashes: CRSS (weighted, 95% CI) vs FARS (census)",
        "fars_testing": "Alcohol and drug test rates among FARS drivers by survival status, year and state",
        "police_vs_bac": "Police-reported alcohol vs measured BAC>=0.08 among tested FARS drivers",
        "alcohol_testing_share": "Share of killed and surviving FARS drivers alcohol-tested and in the police-vs-BAC sample (selection into measurement)",
        "police_vs_bac_selection": "Police-reported alcohol vs measured BAC>=0.08 by how widely surviving drivers are tested (state-year survivor test-rate terciles, cumulative thresholds, state terciles), killed drivers alongside",
        "restraint_reporting": "Restraint reporting among CRSS light-vehicle occupants aged 13+ by KABCO",
        "qba_grid": "Quantitative bias analysis: crude fatal RR corrected for outcome-dependent exposure sensitivity",
        "alcohol_coding_sensitivity": "Adjusted fatal RR for alcohol under imputed / complete-case / unknown-as-no codings, by period",
        "imputed_bac_injury": "Diagnostic (not causal): association of NHTSA's imputed BAC >= .08 with the driver being killed among untested FARS drivers, compared with tested drivers, adjusted for age band, sex, vehicle type, crash type, time of day and year",
    }
    for name, df in out.items():
        pop, unit, outcome, method = META[name]
        save_table(
            df,
            MODULE,
            name,
            description=desc[name],
            population=pop,
            unit=unit,
            outcome=outcome,
            method=method,
            inputs=["data/processed/*.parquet", "data/interim/FARS/drugs"],
        )
    return out
