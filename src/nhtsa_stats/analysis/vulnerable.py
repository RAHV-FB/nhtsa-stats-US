"""Pedestrians and cyclists: who dies when struck, and by what (extension of RQ6).

Question: given that a pedestrian (or cyclist) is struck in a police-reported crash, how does
the probability of death depend on the striking vehicle's type, the speed environment, light,
location and the victim's age -- after mutual adjustment?

Population: CRSS pedestrians (PER_TYP 5) and pedalcyclists (6, 7) 2016-2024 with known
injury severity; the striking vehicle is identified by the person-level ``STR_VEH`` field
(linked for 100% of non-motorists).  Unit: person.  Outcomes: killed (K), killed or seriously
injured (KA).

Method: survey-weighted logistic regression (Taylor linearisation, 25 strata / 67 PSUs) with
standardised margins -> adjusted risk ratios versus a passenger car (and versus <= 25 mph for
speed limit), interaction of striking-vehicle type with the speed environment, and FARS
corroboration (striking-vehicle mix of pedestrian deaths by year, census counts).

Justified: "struck pedestrians are X times as likely to die when the striking vehicle is an
SUV rather than a car, among comparable crashes".  Not justified: that changing vehicle fleets
would reduce deaths by that ratio (impact speed, vehicle mass and front-end geometry are not
separately observed; exposure to being struck is not measured).
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

import numpy as np
import pandas as pd
import polars as pl

from nhtsa_stats import config
from nhtsa_stats.analysis import severity, specs
from nhtsa_stats.analysis.survey import ModelSpec, SurveyDesign, SurveyLogit, interaction_contrasts
from nhtsa_stats.ingestion.cache import load_table
from nhtsa_stats.processing import harmonize as h
from nhtsa_stats.reporting.io import save_table

log = logging.getLogger(__name__)
MODULE = "vulnerable"

STRIKING_LEVELS = ["car", "suv", "pickup", "van", "large", "motorcycle", "other_unknown"]
LOCATION_LEVELS = ["crosswalk", "intersection_other", "midblock", "other", "unknown"]
AGE_LEVELS = [
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
]


def _striking(body: pl.Expr) -> pl.Expr:
    return (
        pl.when(body.is_in(["car", "suv", "pickup", "van", "motorcycle"]))
        .then(body)
        .when(body.is_in(["medium_heavy_truck", "bus"]))
        .then(pl.lit("large"))
        .otherwise(pl.lit("other_unknown"))
    )


def _location(col: str = "LOCATION") -> pl.Expr:
    """Non-motorist location (codes stable 2016-2024 in both sources, embedded labels)."""
    c = pl.col(col)
    # 'crosswalk': at an intersection in a marked or unmarked/unknown crosswalk (1, 2), or in a
    # marked crosswalk away from an intersection (10).
    return (
        pl.when(c.is_in([1, 2, 10]))
        .then(pl.lit("crosswalk"))
        .when(c.is_in([3, 9]))
        .then(pl.lit("intersection_other"))
        .when(c.is_in([11, 12, 13]))
        .then(pl.lit("midblock"))
        .when(c.is_in([98, 99]))
        .then(pl.lit("unknown"))
        .otherwise(pl.lit("other"))
    )


def build(source: str = "CRSS", years: Sequence[int] = config.YEARS) -> pl.DataFrame:
    case = "CASENUM" if source == "CRSS" else "ST_CASE"
    # CRSS severity: NHTSA-imputed INJSEV_IM (primary, as in processing/features.py); INJ_SEV
    # is kept for the complete-case sensitivity outcome.
    sev = "INJSEV_IM" if source == "CRSS" else "INJ_SEV"
    p = load_table(
        source,
        "person",
        years,
        [case, "VEH_NO", "PER_NO", "PER_TYP", "STR_VEH", "AGE", "SEX", "INJ_SEV", "LOCATION"]
        + (["INJSEV_IM"] if source == "CRSS" else []),
    )
    p = p.filter(pl.col("PER_TYP").is_in([5, 6, 7]))
    v = load_table(
        source, "vehicle", years, [case, "VEH_NO", "BODY_TYP", "VSPD_LIM", "SPEEDREL"]
    ).with_columns(
        h.body_group().alias("body"),
        h.speeding_related().alias("str_speeding"),
        h.speed_limit_band().alias("str_speed_limit"),
    )
    df = p.join(
        v.select(["YEAR", case, "VEH_NO", "body", "str_speeding", "str_speed_limit"]),
        left_on=["YEAR", case, "STR_VEH"],
        right_on=["YEAR", case, "VEH_NO"],
        how="left",
    )
    df = df.with_columns(
        pl.when(pl.col("PER_TYP") == 5)
        .then(pl.lit("pedestrian"))
        .otherwise(pl.lit("cyclist"))
        .alias("victim"),
        _striking(pl.col("body").fill_null("unknown")).alias("striking"),
        _location().alias("location"),
        h.fatal(sev).alias("killed"),
        h.killed_or_serious(sev).alias("killed_or_serious"),
        h.fatal("INJ_SEV").alias("killed_cc"),
        h.killed_or_serious("INJ_SEV").alias("killed_or_serious_cc"),
        h.age_years().alias("age"),
        h.sex().alias("sex"),
        pl.col("str_speed_limit").fill_null(h.UNKNOWN),
    ).with_columns(h.age_band("age").alias("age_band"))
    return df.rename({case: "case_id"})


def load(victim: str, outcome: str) -> tuple[pd.DataFrame, SurveyDesign]:
    """Non-motorists joined to crash covariates, with the design built on all crashes."""
    nm = build("CRSS").filter(pl.col("victim") == victim)
    crash = pl.read_parquet(
        config.PROCESSED_DIR / "crss_crash.parquet",
        columns=[
            "YEAR",
            "case_id",
            "WEIGHT",
            "PSUSTRAT",
            "PSU_VAR",
            "region",
            "urbanicity",
            "tod",
            "weekend",
            "light",
            "alcohol_im",
        ],
    )
    df = nm.join(crash, on=["YEAR", "case_id"], how="left").to_pandas()
    for c in ("alcohol_im", "weekend", "str_speeding"):
        df[c] = df[c].map({1: "yes", 0: "no"}).fillna("unknown")
    # Design on the full CRSS crash file's clusters: building from these rows keeps the PSU
    # universe only if every PSU appears; use the crash file to define all clusters.
    full = pl.read_parquet(
        config.PROCESSED_DIR / "crss_crash.parquet", columns=["WEIGHT", "PSUSTRAT", "PSU_VAR"]
    ).to_pandas()
    keep = df[outcome].notna().to_numpy()
    df = df.loc[keep].reset_index(drop=True)
    stacked = pd.concat([df[["WEIGHT", "PSUSTRAT", "PSU_VAR"]], full], ignore_index=True)
    design_all = SurveyDesign.from_frame(stacked)
    mask = np.zeros(len(stacked), dtype=bool)
    mask[: len(df)] = True
    design = design_all.subset(mask)
    df[outcome] = df[outcome].astype(float)
    return df, design


LEVELS = {
    "striking": STRIKING_LEVELS,
    "str_speed_limit": [
        "<=25",
        "30-35",
        "40-45",
        "50-55",
        "60-65",
        "70+",
        "none_nontrafficway",
        "unknown",
    ],
    "location": LOCATION_LEVELS,
    "age_band": AGE_LEVELS,
    "sex": ["male", "female", "unknown"],
    "light": specs.CRASH_LEVELS["light"],
    "tod": specs.CRASH_LEVELS["tod"],
    "weekend": ["no", "yes", "unknown"],
    "urbanicity": ["urban", "rural"],
    "region": specs.CRASH_LEVELS["region"],
    "alcohol_im": ["no", "yes"],
    "str_speeding": ["no", "yes", "unknown"],
    "YEAR": list(config.YEARS),
}
COVARIATES = [
    "YEAR",
    "region",
    "urbanicity",
    "tod",
    "weekend",
    "light",
    "str_speed_limit",
    "str_speeding",
    "alcohol_im",
    "location",
    "age_band",
    "sex",
    "striking",
]


def _spec(df: pd.DataFrame, covs: list[str], interactions=()) -> ModelSpec:
    h.assert_no_leakage(covs, allow_year=True)
    return ModelSpec(
        categorical={c: severity.observed_levels(df, c, LEVELS[c]) for c in covs},
        interactions=list(interactions),
    )


def adjusted_contrasts(victim: str, outcome: str) -> pd.DataFrame:
    df, design = load(victim, outcome)
    model = SurveyLogit(_spec(df, COVARIATES), ridge=severity.RIDGE).fit(
        df, df[outcome].to_numpy(), design
    )
    crude_rows = []
    for f in ("striking", "str_speed_limit", "light", "location", "age_band"):
        levels = severity.observed_levels(df, f, LEVELS[f])
        adj = severity.factor_contrasts(model, df, f, levels)
        crude_m = SurveyLogit(ModelSpec(categorical={f: levels}), ridge=severity.RIDGE).fit(
            df, df[outcome].to_numpy(), design
        )
        crude = severity.factor_contrasts(crude_m, df, f, levels)
        n = df.groupby(f).agg(n=(outcome, "size"), events=(outcome, "sum"))
        adj = adj.assign(
            crude_rate=crude["adj_rate"].to_numpy(),
            crude_rr=crude["adj_rr"].to_numpy(),
            crude_rr_low=crude["adj_rr_low"].to_numpy(),
            crude_rr_high=crude["adj_rr_high"].to_numpy(),
        )
        adj["n"] = adj["level"].map(n["n"]).fillna(0).astype(int)
        adj["n_events"] = adj["level"].map(n["events"]).fillna(0).astype(int)
        ref_rse = adj["adj_rate_rse"].iloc[0]
        adj["flag"] = [
            "; ".join(
                x
                for x, cond in (
                    ("few events", ev < 20),
                    ("n<30", n_ < config.MIN_CELL_N),
                    ("level RSE>30%", rse > config.MAX_RSE),
                    ("reference RSE>30%", ref_rse > config.MAX_RSE),
                )
                if cond
            )
            for ev, n_, rse in zip(adj["n_events"], adj["n"], adj["adj_rate_rse"], strict=True)
        ]
        crude_rows.append(adj)
    out = pd.concat(crude_rows, ignore_index=True)
    out.insert(0, "outcome", outcome)
    out.insert(0, "victim", victim)
    return out


def body_by_speed(victim: str = "pedestrian", outcome: str = "killed") -> pd.DataFrame:
    """Does the light-truck (SUV/pickup) excess differ between low- and high-speed roads?"""
    df, design = load(victim, outcome)
    df["speed_grp"] = np.select(
        [
            df["str_speed_limit"].isin(["<=25", "30-35"]),
            df["str_speed_limit"].isin(["40-45", "50-55", "60-65", "70+"]),
        ],
        ["<=35", "40+"],
        "unknown",
    )
    df["light_truck"] = np.where(
        df["striking"].isin(["suv", "pickup"]),
        "yes",
        np.where(df["striking"] == "car", "no", "other"),
    )
    covs = [c for c in COVARIATES if c not in ("str_speed_limit", "striking")]
    LEVELS["speed_grp"] = ["<=35", "40+", "unknown"]
    LEVELS["light_truck"] = ["no", "yes", "other"]
    spec = _spec(
        df, [*covs, "speed_grp", "light_truck"], interactions=[("light_truck", "speed_grp")]
    )
    model = SurveyLogit(spec, ridge=severity.RIDGE).fit(df, df[outcome].to_numpy(), design)
    sc = {
        f"p{i}{j}": (lambda d, lt=lt, sg=sg: d.assign(light_truck=lt, speed_grp=sg))
        for i, lt in ((0, "no"), (1, "yes"))
        for j, sg in ((0, "<=35"), (1, "40+"))
    }
    ms = model.margins(df, sc)
    ic = interaction_contrasts(ms, "p11", "p10", "p01", "p00")
    rows = []
    for name, est in (
        ("risk car <=35", ms.estimate("p00")),
        ("risk SUV/pickup <=35", ms.estimate("p10")),
        ("risk car 40+", ms.estimate("p01")),
        ("risk SUV/pickup 40+", ms.estimate("p11")),
        ("RR SUV/pickup vs car, <=35 mph", ms.log_ratio("p10", "p00")),
        ("RR SUV/pickup vs car, 40+ mph", ms.log_ratio("p11", "p01")),
        ("RD SUV/pickup vs car, <=35 mph", ms.difference("p10", "p00")),
        ("RD SUV/pickup vs car, 40+ mph", ms.difference("p11", "p01")),
        ("interaction contrast (additive)", ic["ic"]),
        ("ratio of RRs", ic["log_ratio_of_rr"]),
    ):
        lo, hi = est.ci()
        is_log = name.startswith("RR") or name == "ratio of RRs"
        rows.append(
            {
                "victim": victim,
                "outcome": outcome,
                "quantity": name,
                "estimate": np.exp(est.estimate) if is_log else est.estimate,
                "low": np.exp(lo) if is_log else lo,
                "high": np.exp(hi) if is_log else hi,
            }
        )
    return pd.DataFrame(rows)


def fars_striking_mix() -> pd.DataFrame:
    df = (
        build("FARS")
        .filter((pl.col("victim") == "pedestrian") & (pl.col("killed") == 1))
        .to_pandas()
    )
    tab = df.groupby(["YEAR", "striking"]).size().unstack(fill_value=0)
    share = tab.div(tab.sum(axis=1), axis=0).add_prefix("share_")
    return tab.add_prefix("deaths_").join(share).reset_index()


def run() -> dict[str, pd.DataFrame]:
    out = {}
    common = dict(
        population="CRSS pedestrians / pedalcyclists 2016-2024 with known injury severity",
        unit="person",
        inputs=[
            "data/interim/CRSS/person",
            "data/interim/CRSS/vehicle",
            "data/processed/crss_crash.parquet",
        ],
        method="Survey logistic regression; standardised margins; Taylor-linearised CIs (t, 42 df)",
    )
    for victim in ("pedestrian", "cyclist"):
        for oc in ("killed", "killed_or_serious"):
            res = adjusted_contrasts(victim, oc)
            save_table(
                res,
                MODULE,
                f"{victim}_{oc}_contrasts",
                description=f"Crude and adjusted risk ratios of {oc} for struck {victim}s",
                outcome=oc,
                **common,
            )
            out[f"{victim}_{oc}"] = res
    out["body_by_speed"] = body_by_speed()
    save_table(
        out["body_by_speed"],
        MODULE,
        "pedestrian_light_truck_by_speed",
        description="SUV/pickup vs car pedestrian fatality risk by speed environment (interaction)",
        outcome="killed",
        **common,
    )
    out["fars_mix"] = fars_striking_mix()
    save_table(
        out["fars_mix"],
        MODULE,
        "fars_pedestrian_deaths_by_striking_vehicle",
        description="FARS pedestrian deaths by striking vehicle type and year (observed counts and shares)",
        population="FARS pedestrians killed 2016-2024",
        unit="person",
        outcome="killed",
        inputs=["data/interim/FARS/person", "data/interim/FARS/vehicle"],
        method="Census counts",
    )
    return out
