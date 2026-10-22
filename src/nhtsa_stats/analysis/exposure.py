"""Relative crash involvement by quasi-induced exposure (RQ7).

The database contains no exposure (trips, miles, hours), so absolute crash rates per unit of
driving cannot be estimated.  Quasi-induced exposure (QIE) offers a *relative* measure under
strong assumptions: in two-vehicle crashes where exactly one driver is culpable, the
non-culpable driver is treated as a quasi-random draw from drivers on the road at that place
and time.  The relative involvement ratio of driver group g is

    RIR_g = (share of culpable drivers in g) / (share of non-culpable drivers in g),

which, because each qualifying crash contributes one culpable and one non-culpable driver,
equals the odds of culpability within g.  RIR > 1 means g is over-represented among drivers
judged responsible relative to its presence as an innocent party.

Culpability, primary definition C1 (action-based, positive evidence both ways; recommended in
docs/audit/driver_behaviour_factors.md §16): a driver is *culpable* if the vehicle was
speeding-related (SPEEDREL 2-5), or its critical pre-crash event P_CRASH2 is in the culpable
class (own loss of control, lane departure, turning/crossing, backing, U-turn, striking a
slower/stopped vehicle in own lane), or a driver-error code common to FARS and CRSS is present
(DR_SF1-4 2016-2019 / driverrf 2020+: 6, 8, 102, 103, 36, 50, 51, 58; "looked but did not see"
10, or distract code 1 in 2016-2017); *non-culpable* if none of these AND SPEEDREL = 0 AND
P_CRASH2 is in the non-culpable (struck from behind / encroached upon) or neutral class AND no
driver-factor "unknown" code; otherwise undetermined.  Charges are deliberately *not* used:
violations are charged after the crash and dead drivers are almost never charged (outcome
dependent).  The charge-based definition is reported only as a sensitivity analysis.
Sample: crashes with exactly two in-transport vehicles, both with a driver present, no
non-motorist, exactly one culpable and one non-culpable driver.

Assumptions (all untestable here): (1) non-culpable drivers represent the driving population
at risk at the crash time and place; (2) police charge violations without bias by driver group
-- e.g. if police attribute errors more readily to young or drinking drivers, their RIR is
inflated; (3) culpability is approximately binary.  Speeding defines culpability, so speeding
itself cannot be studied with this sample.  Population: CRSS two-vehicle crashes
with both drivers present.  Unit: driver.  Not justified: crash rates per mile/trip; effects
of enforcement.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd
import polars as pl

from nhtsa_stats import config
from nhtsa_stats.analysis import severity
from nhtsa_stats.analysis.survey import MarginSet, ModelSpec, SurveyDesign, SurveyLogit
from nhtsa_stats.ingestion.cache import load_table
from nhtsa_stats.processing import harmonize as h
from nhtsa_stats.reporting.io import save_table

log = logging.getLogger(__name__)
MODULE = "exposure"
POST_CRASH_VIOLATIONS = [7, 8]
UNKNOWN_VIOLATIONS = [95, 97, 99]
# P_CRASH2 (critical pre-crash event) classes, verified by code-pair cross-tabs in the audit.
PC2_CULPABLE = [6, 8, 9, *range(10, 18), 19, 20, 21, 50, 51, 52]
PC2_NONCULPABLE = [53, 55, 56, *range(60, 79)]
PC2_NEUTRAL = [1, 2, 3, 4, 5, 18]
ERROR_CODES = [6, 8, 102, 103, 36, 50, 51, 58]
LBDNS = 10  # "looked but did not see" in driver factors from 2018
DRF_UNKNOWN = [99, 999]


def culpability(code: pl.Expr) -> pl.Expr:
    """Per-violation-row classification: 1 culpable, 0 none, null unknown/other."""
    moving = (code.is_between(1, 69) & ~code.is_in(POST_CRASH_VIOLATIONS)) | (code == 98)
    return (
        pl.when(moving)
        .then(pl.lit(1, dtype=pl.Int8))
        .when(code == 0)
        .then(pl.lit(0, dtype=pl.Int8))
        .when(code.is_in(UNKNOWN_VIOLATIONS))
        .then(pl.lit(None, dtype=pl.Int8))
        .otherwise(pl.lit(0, dtype=pl.Int8))  # non-moving / post-crash only -> not culpable
    )


def _driver_factor_flags(years) -> pl.DataFrame:
    """Per vehicle: any common driver-error code, any 'unknown' driver-factor code."""
    keys = ["YEAR", "CASENUM", "VEH_NO"]
    early = load_table(
        "CRSS",
        "vehicle",
        [y for y in years if y <= 2019],
        ["CASENUM", "VEH_NO", "DR_SF1", "DR_SF2", "DR_SF3", "DR_SF4"],
    )
    early = early.unpivot(
        index=keys, on=["DR_SF1", "DR_SF2", "DR_SF3", "DR_SF4"], value_name="code"
    ).drop("variable")
    late = load_table(
        "CRSS", "driverrf", [y for y in years if y >= 2020], ["CASENUM", "VEH_NO", "DRIVERRF"]
    )
    late = late.rename({"DRIVERRF": "code"})
    codes = pl.concat(
        [early.select([*keys, "code"]), late.select([*keys, "code"])], how="vertical_relaxed"
    )
    lb = load_table(
        "CRSS", "distract", [y for y in years if y <= 2017], ["CASENUM", "VEH_NO", "MDRDSTRD"]
    )
    lb = (
        lb.filter(pl.col("MDRDSTRD") == 1)
        .select(keys)
        .unique()
        .with_columns(pl.lit(True).alias("lbdns_dist"))
    )
    flags = codes.group_by(keys).agg(
        (pl.col("code").is_in(ERROR_CODES) | ((pl.col("YEAR") >= 2018) & (pl.col("code") == LBDNS)))
        .any()
        .alias("error"),
        pl.col("code").is_in(DRF_UNKNOWN).any().alias("drf_unknown"),
    )
    return (
        flags.join(lb, on=keys, how="full", coalesce=True)
        .with_columns(
            (pl.col("error").fill_null(False) | pl.col("lbdns_dist").fill_null(False)).alias(
                "error"
            ),
            pl.col("drf_unknown").fill_null(False),
        )
        .drop("lbdns_dist")
    )


def build_drivers() -> pl.DataFrame:
    years = config.YEARS
    keys = ["YEAR", "CASENUM", "VEH_NO"]
    viol = load_table("CRSS", "violatn", years, ["CASENUM", "VEH_NO", "MVIOLATN", "VIOLATION"])
    viol = viol.with_columns(pl.coalesce("VIOLATION", "MVIOLATN").alias("code")).with_columns(
        culpability(pl.col("code")).alias("c"),
        pl.col("code").is_in(UNKNOWN_VIOLATIONS).alias("unk"),
    )
    vc = viol.group_by(keys).agg(
        pl.when((pl.col("c") == 1).any())
        .then(pl.lit(1))
        .when(pl.col("unk").any())
        .then(None)
        .otherwise(pl.lit(0))
        .cast(pl.Int8)
        .alias("culp_viol")
    )
    veh = load_table(
        "CRSS",
        "vehicle",
        years,
        [
            "CASENUM",
            "VEH_NO",
            "BODY_TYP",
            "VEH_ALCH",
            "V_ALCH_IM",
            "DR_PRES",
            "SPEEDREL",
            "P_CRASH2",
        ],
    )
    per = load_table(
        "CRSS", "person", years, ["CASENUM", "VEH_NO", "PER_TYP", "AGE", "SEX"]
    ).filter(pl.col("PER_TYP") == 1)
    per = per.unique(subset=keys, keep="first")
    d = (
        veh.join(vc, on=keys, how="left")
        .join(per, on=keys, how="left")
        .join(_driver_factor_flags(years), on=keys, how="left")
        .with_columns(pl.col("error").fill_null(False), pl.col("drf_unknown").fill_null(False))
    )
    culp = (
        pl.col("SPEEDREL").is_between(2, 5)
        | pl.col("P_CRASH2").is_in(PC2_CULPABLE)
        | pl.col("error")
    )
    nonculp = (
        ~culp
        & (pl.col("SPEEDREL") == 0)
        & pl.col("P_CRASH2").is_in(PC2_NONCULPABLE + PC2_NEUTRAL)
        & ~pl.col("drf_unknown")
    )
    d = d.with_columns(
        pl.when(culp)
        .then(pl.lit(1, dtype=pl.Int8))
        .when(nonculp)
        .then(pl.lit(0, dtype=pl.Int8))
        .otherwise(pl.lit(None, dtype=pl.Int8))
        .alias("culp_c1"),
        h.body_group().alias("body"),
        h.crss_alcohol("V_ALCH_IM").alias("alcohol_im"),
        h.age_years().alias("age"),
        h.sex().alias("sex"),
    ).with_columns(h.age_band("age").alias("age_band"))
    return d.rename({"CASENUM": "case_id"})


def qualifying(drivers: pl.DataFrame, definition: str = "culp_c1") -> pd.DataFrame:
    crash = pl.read_parquet(
        config.PROCESSED_DIR / "crss_crash.parquet",
        columns=[
            "YEAR",
            "case_id",
            "WEIGHT",
            "PSUSTRAT",
            "PSU_VAR",
            "n_veh_in_transport",
            "tod",
            "light",
            "region",
            "urbanicity",
            "kabco",
            "any_nonmotorist",
        ],
    )
    two = crash.filter((pl.col("n_veh_in_transport") == 2) & (pl.col("any_nonmotorist") == 0))
    d = drivers.join(two, on=["YEAR", "case_id"], how="inner").with_columns(
        pl.col(definition).alias("culpable")
    )
    agg = d.group_by(["YEAR", "case_id"]).agg(
        pl.len().alias("n"),
        pl.col("culpable").sum().alias("n_culp"),
        pl.col("culpable").is_null().sum().alias("n_unk"),
        (pl.col("PER_TYP").is_null() | (pl.col("DR_PRES") != 1)).sum().alias("no_driver"),
    )
    ok = agg.filter(
        (pl.col("n") == 2)
        & (pl.col("n_culp") == 1)
        & (pl.col("n_unk") == 0)
        & (pl.col("no_driver") == 0)
    )
    d = d.join(ok.select(["YEAR", "case_id"]), on=["YEAR", "case_id"], how="semi").to_pandas()
    d["night"] = np.where(
        d["tod"].isin(["20-23", "00-05"]),
        "night",
        np.where(d["tod"] == "unknown", "unknown", "day"),
    )
    d["alcohol_im"] = d["alcohol_im"].map({1: "yes", 0: "no"}).fillna("unknown")
    d["body_grp"] = np.select(
        [
            d["body"] == "car",
            d["body"].isin(["suv", "van", "light_truck_other"]),
            d["body"] == "pickup",
            d["body"] == "motorcycle",
            d["body"].isin(["medium_heavy_truck", "bus"]),
        ],
        ["car", "suv_van", "pickup", "motorcycle", "large"],
        "other_unknown",
    )
    d["young_night"] = np.where((d["age_band"] == "15-20") & (d["night"] == "night"), "yes", "no")
    return d


LEVELS = {
    "age_band": [
        "35-44",
        "15-20",
        "21-24",
        "25-34",
        "45-54",
        "55-64",
        "65-74",
        "75+",
        "0-14",
        "unknown",
    ],
    "sex": ["male", "female", "unknown"],
    "alcohol_im": ["no", "yes", "unknown"],
    "body_grp": ["car", "suv_van", "pickup", "motorcycle", "large", "other_unknown"],
    "night": ["day", "night", "unknown"],
    "YEAR": list(config.YEARS),
    "region": ["south", "northeast", "midwest", "west"],
    "urbanicity": ["urban", "rural"],
}


def _design(df: pd.DataFrame) -> SurveyDesign:
    full = pl.read_parquet(
        config.PROCESSED_DIR / "crss_crash.parquet", columns=["WEIGHT", "PSUSTRAT", "PSU_VAR"]
    ).to_pandas()
    stacked = pd.concat([df[["WEIGHT", "PSUSTRAT", "PSU_VAR"]], full], ignore_index=True)
    mask = np.zeros(len(stacked), dtype=bool)
    mask[: len(df)] = True
    return SurveyDesign.from_frame(stacked).subset(mask)


def rir_table(df: pd.DataFrame, design: SurveyDesign, var: str, adjust: list[str]) -> pd.DataFrame:
    levels = severity.observed_levels(df, var, LEVELS[var])
    y = df["culpable"].to_numpy(float)
    crude = SurveyLogit(ModelSpec(categorical={var: levels}), ridge=severity.RIDGE).fit(
        df, y, design
    )
    ms = crude.margins(df, {str(lv): (lambda d, lv=lv: d.assign(**{var: lv})) for lv in levels})
    covs = [var, *[a for a in adjust if a != var]]
    adj = SurveyLogit(
        ModelSpec(categorical={c: severity.observed_levels(df, c, LEVELS[c]) for c in covs}),
        ridge=severity.RIDGE,
    ).fit(df, y, design)
    tab = adj.coef_table().set_index("term")
    rows = []
    for lv in levels:
        odds = MarginSet.contrast(ms, lambda m, lv=str(lv): float(np.log(m[lv] / (1 - m[lv]))))
        lo, hi = odds.ci()
        term = f"{var}[{lv}]"
        r = tab.loc[term] if term in tab.index else None
        n = int((df[var] == lv).sum())
        rows.append(
            {
                "factor": var,
                "level": lv,
                "n_drivers": n,
                "n_culpable": int(((df[var] == lv) & (df["culpable"] == 1)).sum()),
                "rir": float(np.exp(odds.estimate)),
                "rir_low": float(np.exp(lo)),
                "rir_high": float(np.exp(hi)),
                "adj_rir_ratio_vs_ref": 1.0 if r is None else float(r.odds_ratio),
                "adj_low": 1.0 if r is None else float(r.or_low),
                "adj_high": 1.0 if r is None else float(r.or_high),
                "flag": "few drivers" if n < config.MIN_CELL_N else "",
            }
        )
    return pd.DataFrame(rows)


def run() -> dict[str, pd.DataFrame]:
    drivers = build_drivers()
    df = qualifying(drivers, "culp_c1")
    design = _design(df)
    adjust = ["age_band", "sex", "alcohol_im", "body_grp", "night", "YEAR", "region", "urbanicity"]
    # Crash-level conditions (night, weather, road) are shared by both drivers of a crash, so
    # their RIR is 1 by construction; they are used only to stratify driver-level RIRs.
    parts = [
        rir_table(df, design, v, adjust) for v in ("age_band", "sex", "alcohol_im", "body_grp")
    ]
    res = pd.concat(parts, ignore_index=True).assign(stratum="all")
    for night in ("day", "night"):
        m = (df["night"] == night).to_numpy()
        sub = rir_table(
            df.loc[m].reset_index(drop=True),
            design.subset(m),
            "age_band",
            [a for a in adjust if a != "night"],
        ).assign(stratum=night)
        res = pd.concat([res, sub], ignore_index=True)
    # Same analysis restricted to KA crashes: does over-involvement differ for severe crashes?
    ka = df["kabco"].isin([3, 4]).to_numpy()
    df_ka = df.loc[ka].reset_index(drop=True)
    res_ka = pd.concat(
        [rir_table(df_ka, design.subset(ka), v, adjust) for v in ("age_band", "alcohol_im")],
        ignore_index=True,
    )
    # Sensitivity: culpability from violations charged (outcome-dependent; see module docstring).
    dv = qualifying(drivers, "culp_viol")
    dsv = _design(dv)
    res_v = pd.concat(
        [rir_table(dv, dsv, v, adjust) for v in ("age_band", "alcohol_im")], ignore_index=True
    )

    crash = pl.read_parquet(
        config.PROCESSED_DIR / "crss_crash.parquet",
        columns=["n_veh_in_transport", "any_nonmotorist", "WEIGHT"],
    )
    two = crash.filter((pl.col("n_veh_in_transport") == 2) & (pl.col("any_nonmotorist") == 0))
    summary = pd.DataFrame(
        [
            {
                "definition": name,
                "qualifying_crashes": int(len(d) / 2),
                "drivers": len(d),
                "two_vehicle_crashes_no_nonmotorist": two.height,
                "share_qualifying_unweighted": len(d) / 2 / two.height,
                "share_qualifying_weighted": float(d["WEIGHT"].sum() / 2 / two["WEIGHT"].sum()),
                "weighted_qualifying_crashes_per_year": float(
                    d["WEIGHT"].sum() / 2 / d["YEAR"].nunique()
                ),
            }
            for name, d in (
                ("C1 action-based (primary)", df),
                ("violations charged (sensitivity)", dv),
            )
        ]
    )
    common = dict(
        population="CRSS two-vehicle crashes 2016-2024 (no non-motorist, both drivers present) with exactly one "
        "culpable and one non-culpable driver",
        unit="driver",
        outcome="culpable (C1 action-based definition unless stated)",
        inputs=[
            "data/interim/CRSS/vehicle",
            "data/interim/CRSS/driverrf",
            "data/interim/CRSS/distract",
            "data/interim/CRSS/violatn",
            "data/interim/CRSS/person",
            "data/processed/crss_crash.parquet",
        ],
        method="Quasi-induced exposure: RIR = odds of culpability within group (saturated survey logit, "
        "linearised CI); adjusted ratios from a multivariable survey logit",
    )
    save_table(
        res,
        MODULE,
        "relative_involvement",
        description="Relative involvement ratios (QIE, C1), all qualifying crashes",
        **common,
    )
    save_table(
        res_ka,
        MODULE,
        "relative_involvement_ka",
        description="Relative involvement ratios (QIE, C1), KA crashes only",
        **common,
    )
    save_table(
        res_v,
        MODULE,
        "relative_involvement_charge_based",
        description="Sensitivity: RIR with culpability = moving violation charged (outcome-dependent definition)",
        **common,
    )
    save_table(
        summary,
        MODULE,
        "sample",
        description="QIE sample sizes under both culpability definitions",
        **common,
    )
    return {
        "relative_involvement": res,
        "relative_involvement_ka": res_ka,
        "charge_based": res_v,
        "sample": summary,
    }
