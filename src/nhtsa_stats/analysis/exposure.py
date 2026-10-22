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

Culpability (consistent 2016-2024, CRSS ``violatn``: ``MVIOLATN`` 2016-2019 / ``VIOLATION``
2020-2024, identical code lists apart from 4 rare codes): culpable = at least one moving
violation charged (codes 1-6, 9-69, 98; codes 7/8 hit-and-run / failure to aid are post-crash
and excluded); non-culpable = violation code 0 only; otherwise unknown (excluded).

Assumptions (all untestable here): (1) non-culpable drivers represent the driving population
at risk at the crash time and place; (2) police charge violations without bias by driver group
-- e.g. if young or drinking drivers are charged more readily for the same behaviour, their RIR
is inflated; (3) culpability is approximately binary.  Population: CRSS two-vehicle crashes
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


def build_drivers() -> pl.DataFrame:
    years = config.YEARS
    viol = load_table("CRSS", "violatn", years, ["CASENUM", "VEH_NO", "MVIOLATN", "VIOLATION"])
    viol = viol.with_columns(pl.coalesce("VIOLATION", "MVIOLATN").alias("code")).with_columns(
        culpability(pl.col("code")).alias("c"),
        pl.col("code").is_in(UNKNOWN_VIOLATIONS).alias("unk"),
    )
    vc = viol.group_by(["YEAR", "CASENUM", "VEH_NO"]).agg(
        pl.when((pl.col("c") == 1).any())
        .then(pl.lit(1))
        .when(pl.col("unk").any())
        .then(None)
        .otherwise(pl.lit(0))
        .cast(pl.Int8)
        .alias("culpable")
    )
    veh = load_table(
        "CRSS",
        "vehicle",
        years,
        ["CASENUM", "VEH_NO", "BODY_TYP", "VEH_ALCH", "V_ALCH_IM", "DR_PRES"],
    )
    per = load_table(
        "CRSS", "person", years, ["CASENUM", "VEH_NO", "PER_TYP", "AGE", "SEX"]
    ).filter(pl.col("PER_TYP") == 1)
    per = per.unique(subset=["YEAR", "CASENUM", "VEH_NO"], keep="first")
    d = veh.join(vc, on=["YEAR", "CASENUM", "VEH_NO"], how="left").join(
        per, on=["YEAR", "CASENUM", "VEH_NO"], how="left"
    )
    d = d.with_columns(
        h.body_group().alias("body"),
        h.crss_alcohol("V_ALCH_IM").alias("alcohol_im"),
        h.age_years().alias("age"),
        h.sex().alias("sex"),
    ).with_columns(h.age_band("age").alias("age_band"))
    return d.rename({"CASENUM": "case_id"})


def qualifying(drivers: pl.DataFrame) -> pd.DataFrame:
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
        ],
    )
    two = crash.filter(pl.col("n_veh_in_transport") == 2)
    d = drivers.join(two, on=["YEAR", "case_id"], how="inner")
    agg = d.group_by(["YEAR", "case_id"]).agg(
        pl.len().alias("n"),
        pl.col("culpable").sum().alias("n_culp"),
        pl.col("culpable").is_null().sum().alias("n_unk"),
        pl.col("PER_TYP").is_null().sum().alias("no_driver"),
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
    df = qualifying(drivers)
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
    crash = pl.read_parquet(
        config.PROCESSED_DIR / "crss_crash.parquet", columns=["n_veh_in_transport", "WEIGHT"]
    )
    two = crash.filter(pl.col("n_veh_in_transport") == 2)
    summary = pd.DataFrame(
        [
            {
                "qualifying_crashes": int(len(df) / 2),
                "drivers": len(df),
                "two_vehicle_crashes": two.height,
                "share_qualifying_unweighted": len(df) / 2 / two.height,
                "share_qualifying_weighted": float(df["WEIGHT"].sum() / 2 / two["WEIGHT"].sum()),
                "weighted_qualifying_crashes_per_year": float(
                    df["WEIGHT"].sum() / 2 / df["YEAR"].nunique()
                ),
            }
        ]
    )
    common = dict(
        population="CRSS two-vehicle crashes 2016-2024 with exactly one driver charged with a moving violation",
        unit="driver",
        outcome="culpable (moving violation charged)",
        inputs=[
            "data/interim/CRSS/violatn",
            "data/interim/CRSS/vehicle",
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
        description="Relative involvement ratios (QIE), all two-vehicle crashes",
        **common,
    )
    save_table(
        res_ka,
        MODULE,
        "relative_involvement_ka",
        description="Relative involvement ratios (QIE), KA crashes only",
        **common,
    )
    save_table(summary, MODULE, "sample", description="QIE sample size", **common)
    return {"relative_involvement": res, "relative_involvement_ka": res_ka, "sample": summary}
