"""Can drug involvement be measured well enough to compare with alcohol?  (Phase 2, Q3;
docs/research_plan_phase2.md §5.2.)

Phase 1 declared drug fields unusable on the strength of audit scripts
(``docs/audit/alcohol_drugs.md``).  This module turns that verdict into reproducible tables and
tests whether any restricted analysis is defensible.

Data
    FARS drivers 2016-2024 (``fars_driver``): drug-test status and psychoactive-class
    positivity from toxicology (see ``processing/drivers.py``), measured BAC and alcohol-test
    status, police-reported drugs and alcohol, survival.  CRSS crashes and drivers: police-
    reported drug involvement only (CRSS contains no drug test results).

Analyses
    1. Test selection: drug-test rate by survival x year, by driver injury severity, by police
       drug / alcohol report, by state testing level.
    2. Positivity among tested drivers by survival and period (classes comparable only within
       2016-2021 and within 2022-2024), with indeterminate, presumptive-only and
       carboxy-THC-only shares.
    3. Alcohol-drug co-occurrence among drivers tested for both, and police co-recording.
    4. Police report against toxicology (sensitivity, specificity) by survival.
    5. Minimal-selection comparison: drivers in states that drug-test >= 50% of killed *and* of
       surviving drivers (and BAC-test >= 50% of both).  Within fatal crashes, the odds that a
       driver died rather than survived by measured BAC >= .08 and by drug positivity, mutually
       adjusted (crash-clustered sandwich), compared with the same model in all states.
       Estimand: association with *dying given involvement in a fatal crash and being tested*
       -- not a severity effect, not an effect on crash occurrence.
    6. CRSS bounds: the crude fatal RR of police-reported drug involvement under codings of
       "unknown" from "all negative" to "all positive" and under differential missingness
       scenarios, and model-A adjusted RRs for the two codings that can be fitted.

Justified: statements about test selection and about positivity among tested drivers.
Not justified: drug-impairment prevalence; a drug severity effect from CRSS; a ranking of
drugs against alcohol in the general crash population.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd
import polars as pl

from nhtsa_stats import config
from nhtsa_stats.analysis import data, severity, specs
from nhtsa_stats.analysis.survey import ModelSpec, SurveyLogit
from nhtsa_stats.processing.drivers import DRUG_CLASSES
from nhtsa_stats.reporting.io import save_table

log = logging.getLogger(__name__)
MODULE = "drugs"
FARS_POP = "FARS drivers (PER_TYP 1) of in-transport vehicles in fatal crashes, 2016-2024"
INPUT = ["data/processed/fars_driver.parquet", "data/processed/crss_crash.parquet"]
PERIODS = {
    "2016-2021 (3-digit codes)": range(2016, 2022),
    "2022-2024 (4-digit codes)": range(2022, 2025),
}
HIGH_TEST_THRESHOLD = 0.5


def load_fars_drivers() -> pd.DataFrame:
    cols = [
        "YEAR",
        "case_id",
        "VEH_NO",
        "STATE",
        "has_driver_record",
        "drv_killed",
        "drv_kabco",
        "drv_age_band",
        "drv_sex",
        "drv_pr_drugs",
        "drv_pr_alcohol",
        "drv_alc_test_status",
        "drv_bac08_measured",
        "drv_p_p08",
        "drv_drug_test_status",
        "drv_drug_any",
        *[f"drv_drug_{c}" for c in DRUG_CLASSES],
        "drv_drug_presumptive_only",
        "drv_drug_carboxy_thc_only",
        "body",
        "crash_type",
        "n_vehicles",
        "night",
        "own_speeding_type",
    ]
    df = pl.read_parquet(config.PROCESSED_DIR / "fars_driver.parquet", columns=cols).to_pandas()
    df = df[df["has_driver_record"] == 1].reset_index(drop=True)
    df["survival"] = df["drv_killed"].map({1: "killed", 0: "survived"}).fillna("unknown")
    df["drug_tested"] = (df["drv_drug_test_status"] == "tested").astype(float)
    df["bac_tested"] = (df["drv_alc_test_status"] == "tested_result").astype(float)
    return df


def _share(x: pd.Series) -> float:
    return float(np.mean(x)) if len(x) else np.nan


# --------------------------------------------------------------------------------------
# 1. Test selection
# --------------------------------------------------------------------------------------
def testing_rates(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    d = df[df["survival"] != "unknown"]
    status_levels = ["tested", "not_tested", "not_reported", "unknown_if_tested"]

    def add(dim: str, level: str, sub: pd.DataFrame, surv: str) -> None:
        rec = {"dimension": dim, "level": level, "survival": surv, "n": len(sub)}
        for s in status_levels:
            rec[f"share_{s}"] = _share(sub["drv_drug_test_status"] == s)
        rec["share_bac_tested"] = _share(sub["bac_tested"] == 1)
        rows.append(rec)

    for surv in ("killed", "survived"):
        s = d[d["survival"] == surv]
        add("all years", "2016-2024", s, surv)
        for y, g in s.groupby("YEAR"):
            add("year", str(y), g, surv)
        for v, lab in ((1, "yes"), (0, "no")):
            add("police drug report", lab, s[s["drv_pr_drugs"] == v], surv)
            add("police alcohol report", lab, s[s["drv_pr_alcohol"] == v], surv)
        add("police drug report", "not reported / unknown", s[s["drv_pr_drugs"].isna()], surv)
        for v, lab in ((1, "BAC >= .08"), (0, "BAC < .08")):
            add("measured BAC", lab, s[s["drv_bac08_measured"] == v], surv)
        add("measured BAC", "no BAC result", s[s["drv_bac08_measured"].isna()], surv)
    # Survivors by their own injury severity (testing rises with injury).
    s = d[d["survival"] == "survived"]
    for k, lab in ((3, "A (serious)"), (2, "B (minor)"), (1, "C (possible)"), (0, "O (none)")):
        add("survivor injury severity", lab, s[s["drv_kabco"] == k], "survived")
    return pd.DataFrame(rows)


def state_testing(df: pd.DataFrame) -> pd.DataFrame:
    """Per-state test rates (pooled years) and positivity among tested killed drivers."""
    d = df[df["survival"] != "unknown"]
    g = d.groupby(["STATE", "survival"]).agg(
        n=("drug_tested", "size"),
        drug_tested=("drug_tested", "mean"),
        bac_tested=("bac_tested", "mean"),
    )
    wide = g.unstack("survival")
    wide.columns = [f"{a}_{b}" for a, b in wide.columns]
    wide = wide.reset_index()
    pos = (
        d[(d["survival"] == "killed") & (d["drug_tested"] == 1)]
        .groupby("STATE")["drv_drug_any"]
        .mean()
        .rename("drug_positivity_killed_tested")
    )
    wide = wide.merge(pos, on="STATE", how="left")
    wide["high_testing"] = (
        (wide["drug_tested_killed"] >= HIGH_TEST_THRESHOLD)
        & (wide["drug_tested_survived"] >= HIGH_TEST_THRESHOLD)
        & (wide["bac_tested_killed"] >= HIGH_TEST_THRESHOLD)
        & (wide["bac_tested_survived"] >= HIGH_TEST_THRESHOLD)
    )
    wide["tertile_survivor_drug_testing"] = pd.qcut(
        wide["drug_tested_survived"], 3, labels=["low", "middle", "high"]
    ).astype(str)
    return wide


def selection_gradient(df: pd.DataFrame, states: pd.DataFrame) -> pd.DataFrame:
    """Positivity among tested drivers vs the state's survivor test rate (tertiles): if testing
    is targeted, positivity falls as testing widens."""
    tert = states.set_index("STATE")["tertile_survivor_drug_testing"]
    d = df[
        (df["drug_tested"] == 1) & df["drv_drug_any"].notna() & (df["survival"] != "unknown")
    ].copy()
    d["tertile"] = d["STATE"].map(tert)
    rows = []
    for (t, surv), g in d.groupby(["tertile", "survival"]):
        all_s = df[(df["STATE"].map(tert) == t) & (df["survival"] == surv)]
        rows.append(
            {
                "survivor_test_tertile": t,
                "survival": surv,
                "n_tested": len(g),
                "share_tested": _share(all_s["drug_tested"] == 1),
                "drug_positivity": g["drv_drug_any"].mean(),
                "bac08_among_bac_tested": all_s.loc[
                    all_s["bac_tested"] == 1, "drv_bac08_measured"
                ].mean(),
            }
        )
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------------------
# 2-4. Positivity, co-occurrence, police validity
# --------------------------------------------------------------------------------------
def positivity(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    t = df[(df["drug_tested"] == 1) & (df["survival"] != "unknown")]
    for period, years in PERIODS.items():
        for surv in ("killed", "survived"):
            g = t[t["YEAR"].isin(list(years)) & (t["survival"] == surv)]
            det = g[g["drv_drug_any"].notna()]
            rec = {
                "period": period,
                "survival": surv,
                "n_tested": len(g),
                "share_indeterminate": _share(g["drv_drug_any"].isna()),
                "any_psychoactive": det["drv_drug_any"].mean(),
                "presumptive_only_share_of_positive": det.loc[
                    det["drv_drug_any"] == 1, "drv_drug_presumptive_only"
                ].mean(),
                "carboxy_thc_only_share_of_cannabinoid": det.loc[
                    det["drv_drug_cannabinoid"] == 1, "drv_drug_carboxy_thc_only"
                ].mean(),
            }
            for c in DRUG_CLASSES:
                rec[c] = det[f"drv_drug_{c}"].mean()
            rows.append(rec)
    return pd.DataFrame(rows)


def _or2x2(a: float, b: float, c: float, d: float) -> tuple[float, float, float]:
    """Odds ratio with a Woolf CI (independent drivers; cluster correlation ignored)."""
    if min(a, b, c, d) <= 0:
        return np.nan, np.nan, np.nan
    lor = np.log(a * d / (b * c))
    se = np.sqrt(1 / a + 1 / b + 1 / c + 1 / d)
    return float(np.exp(lor)), float(np.exp(lor - 1.96 * se)), float(np.exp(lor + 1.96 * se))


def co_occurrence(df: pd.DataFrame) -> pd.DataFrame:
    """Alcohol (measured BAC >= .08) and drug positivity among drivers tested for both, and
    police co-recording (DRINKING and DRUGS both known)."""
    rows = []
    for surv in ("killed", "survived"):
        g = df[
            (df["survival"] == surv)
            & (df["drug_tested"] == 1)
            & df["drv_drug_any"].notna()
            & df["drv_bac08_measured"].notna()
        ]
        x, z = g["drv_bac08_measured"] == 1, g["drv_drug_any"] == 1
        a, b, c, d = (x & z).sum(), (x & ~z).sum(), (~x & z).sum(), (~x & ~z).sum()
        o, lo, hi = _or2x2(a, b, c, d)
        rows.append(
            {
                "measure": "toxicology: BAC >= .08 and any psychoactive drug",
                "survival": surv,
                "n": len(g),
                "share_alcohol": x.mean(),
                "share_drug": z.mean(),
                "share_both": (x & z).mean(),
                "share_drug_among_alcohol": z[x].mean(),
                "share_drug_among_no_alcohol": z[~x].mean(),
                "share_alcohol_among_drug": x[z].mean(),
                "odds_ratio": o,
                "odds_ratio_low": lo,
                "odds_ratio_high": hi,
            }
        )
        p = df[(df["survival"] == surv) & df["drv_pr_drugs"].notna() & df["drv_pr_alcohol"].notna()]
        x, z = p["drv_pr_alcohol"] == 1, p["drv_pr_drugs"] == 1
        a, b, c, d = (x & z).sum(), (x & ~z).sum(), (~x & z).sum(), (~x & ~z).sum()
        o, lo, hi = _or2x2(a, b, c, d)
        rows.append(
            {
                "measure": "police report: alcohol and drugs both recorded",
                "survival": surv,
                "n": len(p),
                "share_alcohol": x.mean(),
                "share_drug": z.mean(),
                "share_both": (x & z).mean(),
                "share_drug_among_alcohol": z[x].mean(),
                "share_drug_among_no_alcohol": z[~x].mean(),
                "share_alcohol_among_drug": x[z].mean(),
                "odds_ratio": o,
                "odds_ratio_low": lo,
                "odds_ratio_high": hi,
            }
        )
    return pd.DataFrame(rows)


def police_validity(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for surv in ("killed", "survived"):
        g = df[(df["survival"] == surv) & (df["drug_tested"] == 1) & df["drv_drug_any"].notna()]
        pos, neg = g[g["drv_drug_any"] == 1], g[g["drv_drug_any"] == 0]
        rows.append(
            {
                "survival": surv,
                "n_positive": len(pos),
                "n_negative": len(neg),
                "sensitivity_unknown_as_no": _share(pos["drv_pr_drugs"] == 1),
                "sensitivity_among_known": _share(
                    pos.loc[pos["drv_pr_drugs"].notna(), "drv_pr_drugs"] == 1
                ),
                "police_unknown_among_positive": _share(pos["drv_pr_drugs"].isna()),
                "specificity_among_known": _share(
                    neg.loc[neg["drv_pr_drugs"].notna(), "drv_pr_drugs"] == 0
                ),
                "tested_if_police_yes": _share(
                    df.loc[(df["survival"] == surv) & (df["drv_pr_drugs"] == 1), "drug_tested"] == 1
                ),
                "tested_if_police_no": _share(
                    df.loc[(df["survival"] == surv) & (df["drv_pr_drugs"] == 0), "drug_tested"] == 1
                ),
            }
        )
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------------------
# 5. Minimal-selection comparison
# --------------------------------------------------------------------------------------
DRIVER_COVS = {
    "age": [
        "25-34",
        "0-14",
        "15-20",
        "21-24",
        "35-44",
        "45-54",
        "55-64",
        "65-74",
        "75+",
        "unknown",
    ],
    "sex": ["male", "female", "unknown"],
    "vehicle": ["light", "motorcycle", "heavy", "other"],
    "config": ["multi_vehicle", "single_vehicle", "nonmotorist"],
    "night_": ["day", "night", "unknown"],
    "period": ["2016-2019", "2020-2024"],
}


def _driver_frame(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    d["age"] = d["drv_age_band"].fillna("unknown").astype(str)
    d["sex"] = d["drv_sex"].fillna("unknown").astype(str)
    body = d["body"].astype(str)
    d["vehicle"] = np.select(
        [
            body == "motorcycle",
            body.isin(["medium_heavy_truck", "bus", "truck_unknown_type"]),
            body.isin(["car", "suv", "pickup", "van", "light_truck_other", "light_unknown_type"]),
        ],
        ["motorcycle", "heavy", "light"],
        "other",
    )
    ct = d["crash_type"].astype(str)
    d["config"] = np.where(
        ct.isin(["pedestrian", "cyclist"]),
        "nonmotorist",
        np.where(ct.str.startswith("sv_"), "single_vehicle", "multi_vehicle"),
    )
    d["night_"] = d["night"].map({1: "night", 0: "day"}).fillna("unknown")
    d["period"] = np.where(d["YEAR"] <= 2019, "2016-2019", "2020-2024")
    d["alcohol"] = d["drv_bac08_measured"].map({1: "yes", 0: "no"})
    d["drug"] = d["drv_drug_any"].map({1.0: "yes", 0.0: "no"})
    return d


def killed_vs_survived(df: pd.DataFrame, states: pd.DataFrame) -> pd.DataFrame:
    """Odds that a tested driver in a fatal crash died, by BAC >= .08 and drug positivity
    (mutually adjusted, + driver/crash covariates), in high-testing states and in all states."""
    high = set(states.loc[states["high_testing"], "STATE"])
    d = _driver_frame(df)
    d = d[(d["survival"] != "unknown") & d["alcohol"].notna() & d["drug"].notna()].reset_index(
        drop=True
    )
    d["y"] = (d["survival"] == "killed").astype(float)
    rows = []
    for sample, mask in (
        ("high-testing states", d["STATE"].isin(high).to_numpy()),
        ("all states", np.ones(len(d), bool)),
    ):
        for spec_name, extra_products in (
            ("main effects", []),
            ("with alcohol x drug", [(("alcohol", ["yes"]), ("drug", ["yes"]))]),
        ):
            sub = d.loc[mask].reset_index(drop=True)
            cats = {"alcohol": ["no", "yes"], "drug": ["no", "yes"]}
            cats.update({k: [lv for lv in v if lv in set(sub[k])] for k, v in DRIVER_COVS.items()})
            spec = ModelSpec(categorical=cats, products=extra_products)
            design = data.fars_design(sub)
            m = SurveyLogit(spec, ridge=0.0).fit(sub, sub["y"].to_numpy(), design)
            tab = m.coef_table().set_index("term")
            for term, label in (
                ("alcohol[yes]", "BAC >= .08 (measured)"),
                ("drug[yes]", "any psychoactive drug detected"),
                ("alcohol{yes}:drug{yes}", "alcohol x drug (product term)"),
            ):
                if term not in tab.index:
                    continue
                r = tab.loc[term]
                rows.append(
                    {
                        "sample": sample,
                        "specification": spec_name,
                        "term": label,
                        "odds_ratio": r["odds_ratio"],
                        "odds_ratio_low": r["or_low"],
                        "odds_ratio_high": r["or_high"],
                        "p": r["p"],
                        "n_drivers": len(sub),
                        "n_killed": int(sub["y"].sum()),
                        "n_states": len(set(sub["STATE"])),
                        "share_alcohol": float((sub["alcohol"] == "yes").mean()),
                        "share_drug": float((sub["drug"] == "yes").mean()),
                    }
                )
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------------------
# 6. CRSS bounds
# --------------------------------------------------------------------------------------
K_GRID = (0.0, 0.5, 1.0, 2.0, 3.0)


def crss_bounds() -> pd.DataFrame:
    """Crude fatal RR of police-reported drug involvement (any driver) when "unknown" crashes
    are allocated under scenarios: unknown-positive prevalence = k_f x the known-positive
    prevalence among fatal crashes and k_n x that among non-fatal crashes."""
    df, design = data.crss_crash(outcome="fatal")
    w = design.weight
    y = df["fatal"].to_numpy(float)
    x = df["drugs"].to_numpy(float)  # 1 / 0 / NaN
    rows = []
    for period, years in (
        ("2016-2018", range(2016, 2019)),
        ("2019-2024", range(2019, 2025)),
        ("2016-2024", range(2016, 2025)),
    ):
        s = df["YEAR"].isin(list(years)).to_numpy()
        known = s & ~np.isnan(x)
        unk = s & np.isnan(x)
        a = w[known & (x == 1) & (y == 1)].sum()
        b = w[known & (x == 1) & (y == 0)].sum()
        c = w[known & (x == 0) & (y == 1)].sum()
        d = w[known & (x == 0) & (y == 0)].sum()
        uf, un = w[unk & (y == 1)].sum(), w[unk & (y == 0)].sum()
        pf, pn = a / (a + c), b / (b + d)
        share_unknown = (uf + un) / (a + b + c + d + uf + un)
        for kf in K_GRID:
            for kn in K_GRID:
                ef, en = min(1.0, kf * pf), min(1.0, kn * pn)
                A, B = a + ef * uf, b + en * un
                C, D = c + (1 - ef) * uf, d + (1 - en) * un
                rows.append(
                    {
                        "period": period,
                        "scenario": "k scenario",
                        "k_fatal": kf,
                        "k_nonfatal": kn,
                        "share_unknown": share_unknown,
                        "unknown_share_fatal": uf / (a + c + uf),
                        "unknown_share_nonfatal": un / (b + d + un),
                        "rr": (A / (A + B)) / (C / (C + D)),
                        "rr_complete_case": (a / (a + b)) / (c / (c + d)),
                    }
                )
        for label, ef, en in (
            ("all unknown negative", 0.0, 0.0),
            ("all unknown positive", 1.0, 1.0),
        ):
            A, B, C, D = a + ef * uf, b + en * un, c + (1 - ef) * uf, d + (1 - en) * un
            rows.append(
                {
                    "period": period,
                    "k_fatal": np.nan,
                    "k_nonfatal": np.nan,
                    "scenario": label,
                    "share_unknown": share_unknown,
                    "unknown_share_fatal": uf / (a + c + uf),
                    "unknown_share_nonfatal": un / (b + d + un),
                    "rr": (A / (A + B)) / (C / (C + D)),
                    "rr_complete_case": (a / (a + b)) / (c / (c + d)),
                }
            )
    return pd.DataFrame(rows)


def crss_adjusted() -> pd.DataFrame:
    """Model-A adjusted RR of police-reported drugs under complete case and unknown-as-no."""
    rows = []
    for period, years in (
        ("2016-2018", [2016, 2017, 2018]),
        ("2019-2024", list(range(2019, 2025))),
    ):
        df, design = severity.load("fatal", years)
        for coding in ("complete case", "unknown as no"):
            d = df.copy()
            keep = np.ones(len(d), bool)
            if coding == "complete case":
                keep = (d["drugs"] != "unknown").to_numpy()
            else:
                d["drugs"] = d["drugs"].replace({"unknown": "no"})
            d = d.loc[keep].reset_index(drop=True)
            m = severity.fit(d, design.subset(keep), "fatal", [*specs.PRE_CRASH, "drugs"])
            fc = (
                severity.factor_contrasts(
                    m, d, "drugs", severity.observed_levels(d, "drugs", ["no", "yes"])
                )
                .set_index("level")
                .loc["yes"]
            )
            rows.append(
                {
                    "period": period,
                    "coding": coding,
                    "n": len(d),
                    "events": int(d["fatal"].sum()),
                    "adj_rr": fc["adj_rr"],
                    "adj_rr_low": fc["adj_rr_low"],
                    "adj_rr_high": fc["adj_rr_high"],
                }
            )
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------------------
def _save(tab, name, description, method, population=FARS_POP, unit="driver", outcome=""):
    save_table(
        tab,
        MODULE,
        name,
        description=description,
        population=population,
        unit=unit,
        outcome=outcome,
        method=method,
        inputs=INPUT,
    )


def run() -> dict[str, pd.DataFrame]:
    df = load_fars_drivers()
    out = {}
    out["testing_rates"] = testing_rates(df)
    _save(
        out["testing_rates"],
        "testing_rates",
        "Drug- and BAC-test status of FARS drivers by survival, year, police report, measured BAC and survivor injury severity",
        "Unweighted shares (census)",
    )
    states = state_testing(df)
    out["state_testing"] = states
    _save(
        states,
        "state_testing",
        "State drug/BAC test rates (pooled 2016-2024) and the high-testing set (>= 50% of killed and surviving drivers tested for both)",
        "Unweighted shares",
        unit="state",
    )
    out["selection_gradient"] = selection_gradient(df, states)
    _save(
        out["selection_gradient"],
        "selection_gradient",
        "Drug positivity among tested drivers by the state's survivor drug-testing tertile",
        "Unweighted shares",
    )
    out["positivity"] = positivity(df)
    _save(
        out["positivity"],
        "positivity",
        "Psychoactive drug positivity among drug-tested drivers, by survival and coding period",
        "Share of tested drivers with a determinate result; detection, not impairment",
    )
    out["co_occurrence"] = co_occurrence(df)
    _save(
        out["co_occurrence"],
        "co_occurrence",
        "Alcohol and drug co-occurrence among tested drivers and in police reports",
        "2x2 tables; Woolf CIs ignore clustering",
    )
    out["police_validity"] = police_validity(df)
    _save(
        out["police_validity"],
        "police_validity",
        "Police-reported drug involvement against toxicology",
        "Shares among tested drivers",
    )
    out["killed_vs_survived"] = killed_vs_survived(df, states)
    _save(
        out["killed_vs_survived"],
        "killed_vs_survived",
        "Odds that a tested driver in a fatal crash died: measured BAC >= .08 and drug positivity, mutually adjusted",
        "Logistic regression, crash-clustered sandwich SEs; covariates: age, sex, vehicle type, crash configuration, night, period",
        outcome="driver killed (vs survived) given a fatal crash",
    )
    out["crss_bounds"] = crss_bounds()
    _save(
        out["crss_bounds"],
        "crss_bounds",
        "Crude fatal RR of police-reported drug involvement under allocations of unknown status",
        "Weighted 2x2 with unknown crashes allocated by scenario",
        population="CRSS police-reported crashes with known severity",
        unit="crash",
        outcome="fatal",
    )
    out["crss_adjusted"] = crss_adjusted()
    _save(
        out["crss_adjusted"],
        "crss_adjusted",
        "Model-A adjusted fatal RR of police-reported drug involvement under two codings",
        "Survey logistic model A + drugs; standardised RR",
        population="CRSS police-reported crashes with known severity",
        unit="crash",
        outcome="fatal",
    )
    return out
