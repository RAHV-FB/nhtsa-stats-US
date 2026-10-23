"""Stage D -- post-crash survival: what the data record and why its effect is not identified.
(Phase 2, docs/research_plan_phase2.md §2 and §5.6.)

FARS records, for fatal crashes only, the time EMS was notified and arrived and when the
injured reached hospital (crash level), and for every death whether it occurred at the scene
or en route and the lag between the crash and the death (person level).  CRSS records none of
these.  An effect of response time on survival needs survivors with the same injuries and
different response times; FARS has no survivors of crashes in which nobody died, and CRSS has
no EMS times, so the survival effect of Stage D is *not identifiable* here.

What can be described: availability of the timing fields, the distribution of time to death
(an indication of how much of the burden occurs before any post-crash care could act), and
how these differ by the recorded factors.  These are descriptive census counts.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd
import polars as pl

from nhtsa_stats import config
from nhtsa_stats.ingestion.cache import load_table
from nhtsa_stats.reporting.io import save_table

log = logging.getLogger(__name__)
MODULE = "stages"


def _minutes(h: pl.Expr, m: pl.Expr) -> pl.Expr:
    return pl.when(h.is_between(0, 23) & m.is_between(0, 59)).then(h * 60 + m)


def ems_frame() -> pd.DataFrame:
    acc = load_table(
        "FARS",
        "accident",
        None,
        [
            "ST_CASE",
            "HOUR",
            "MINUTE",
            "NOT_HOUR",
            "NOT_MIN",
            "ARR_HOUR",
            "ARR_MIN",
            "HOSP_HR",
            "HOSP_MN",
            "RUR_URB",
        ],
    )
    acc = acc.with_columns(
        _minutes(pl.col("HOUR"), pl.col("MINUTE")).alias("t_crash"),
        _minutes(pl.col("NOT_HOUR"), pl.col("NOT_MIN")).alias("t_notified"),
        _minutes(pl.col("ARR_HOUR"), pl.col("ARR_MIN")).alias("t_arrived"),
    ).with_columns(
        # Times are clock times; a negative difference crosses midnight (+24 h).
        ((pl.col("t_arrived") - pl.col("t_crash")) % 1440).alias("min_crash_to_arrival"),
        ((pl.col("t_notified") - pl.col("t_crash")) % 1440).alias("min_crash_to_notification"),
    )
    return acc.rename({"ST_CASE": "case_id"}).to_pandas()


def death_timing() -> pd.DataFrame:
    per = load_table(
        "FARS",
        "person",
        None,
        ["ST_CASE", "VEH_NO", "PER_NO", "INJ_SEV", "DOA", "LAG_HRS", "LAG_MINS"],
    )
    per = per.filter(pl.col("INJ_SEV") == 4).rename({"ST_CASE": "case_id"})
    proc = pl.read_parquet(
        config.PROCESSED_DIR / "fars_person.parquet",
        columns=["YEAR", "case_id", "VEH_NO", "PER_NO", "restraint", "speeding", "rural", "ptype"],
    )
    drv = pl.read_parquet(
        config.PROCESSED_DIR / "fars_driver.parquet",
        columns=["YEAR", "case_id", *[f"drv_bac08_mi_{i}" for i in range(1, 11)]],
    )
    alc = drv.group_by(["YEAR", "case_id"]).agg(
        pl.mean_horizontal(
            [pl.col(f"drv_bac08_mi_{i}").max().fill_null(0) for i in range(1, 11)]
        ).alias("p_alcohol")
    )
    out = per.join(proc, on=["YEAR", "case_id", "VEH_NO", "PER_NO"], how="left").join(
        alc, on=["YEAR", "case_id"], how="left"
    )
    out = out.with_columns(
        pl.when(pl.col("LAG_HRS").is_between(0, 720) & pl.col("LAG_MINS").is_between(0, 59))
        .then(pl.col("LAG_HRS") * 60 + pl.col("LAG_MINS"))
        .alias("lag_min")
    )
    return out.to_pandas()


TIMING_BANDS = [
    ("at the scene (DOA)", None),
    ("within 1 hour", (0, 60)),
    ("1-24 hours", (60, 1440)),
    ("1-30 days", (1440, 720 * 60 + 60)),
]


def timing_table(d: pd.DataFrame) -> pd.DataFrame:
    groups = {
        "all deaths": np.ones(len(d), bool),
        "vehicle occupant, unbelted": (d["restraint"] == "none").to_numpy(),
        "vehicle occupant, belted": (d["restraint"] == "belted").to_numpy(),
        "pedestrian": (d["ptype"] == "pedestrian").to_numpy(),
        "speeding-related crash": (d["speeding"] == 1).to_numpy(),
        "crash not speeding-related": (d["speeding"] == 0).to_numpy(),
        "rural road": (d["rural"] == 1).to_numpy(),
        "urban road": (d["rural"] == 0).to_numpy(),
    }
    rows = []
    for g, mask in groups.items():
        sub = d.loc[mask]
        n = len(sub)
        scene = sub["DOA"] == 7
        lag = sub["lag_min"]
        rec = {
            "group": g,
            "deaths": n,
            "share_died_at_scene": scene.mean(),
            "share_died_en_route": (sub["DOA"] == 8).mean(),
        }
        rec["share_lag_unknown"] = lag.isna().mean()
        for label, rng in TIMING_BANDS[1:]:
            rec[f"share_{label.replace(' ', '_').replace('-', '_')}"] = (
                (lag >= rng[0]) & (lag < rng[1])
            ).mean()
        rec["median_lag_hours_if_not_at_scene"] = (
            float(lag[~scene].median() / 60) if (~scene).any() else np.nan
        )
        rows.append(rec)
    # Alcohol as expected counts over implicates.
    for label, w in (
        ("driver BAC >= .08 in crash (MI)", d["p_alcohol"].fillna(0)),
        ("no driver BAC >= .08 (MI)", 1 - d["p_alcohol"].fillna(0)),
    ):
        scene = (d["DOA"] == 7).astype(float)
        rows.append(
            {
                "group": label,
                "deaths": float(w.sum()),
                "share_died_at_scene": float((w * scene).sum() / w.sum()),
                "share_died_en_route": float((w * (d["DOA"] == 8)).sum() / w.sum()),
                "share_lag_unknown": float((w * d["lag_min"].isna()).sum() / w.sum()),
                "share_within_1_hour": float(
                    (w * ((d["lag_min"] >= 0) & (d["lag_min"] < 60))).sum() / w.sum()
                ),
            }
        )
    return pd.DataFrame(rows)


def ems_availability(acc: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (y, ru), g in acc.groupby(
        ["YEAR", acc["RUR_URB"].map({1: "rural", 2: "urban"}).fillna("unknown")]
    ):
        arr = g["min_crash_to_arrival"]
        rows.append(
            {
                "YEAR": y,
                "road": ru,
                "fatal_crashes": len(g),
                "share_arrival_time_known": arr.notna().mean(),
                "median_minutes_crash_to_arrival": float(arr.median()),
                "p90_minutes_crash_to_arrival": float(arr.quantile(0.9)),
            }
        )
    return pd.DataFrame(rows)


def identifiability() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "stage": "A. crash occurrence",
                "identified": "no",
                "reason": "No exposure (trips, miles, driver-hours); both systems sample crashes, not travel",
                "what_is_reported": "Relative involvement (Phase-1 QIE) only",
            },
            {
                "stage": "B. configuration and impact",
                "identified": "partly (associations)",
                "reason": "Travel and impact speed unobserved for most vehicles; posted limit and police speeding judgement are proxies",
                "what_is_reported": "Associations of recorded speeding and speed environment with severity given a crash",
            },
            {
                "stage": "C. injury given the crash",
                "identified": "closest to identified",
                "reason": "Within-vehicle designs hold crash forces fixed; survivor belt misreporting remains",
                "what_is_reported": "Within-vehicle belt, age and sex risk ratios; occupant-level adjusted risks",
            },
            {
                "stage": "D. post-crash survival",
                "identified": "no",
                "reason": "EMS times exist only for fatal crashes (FARS); no survivors with comparable injuries and different response times; CRSS has no EMS times",
                "what_is_reported": "Descriptive timing of deaths and EMS arrival among fatal crashes",
            },
        ]
    )


def run() -> dict[str, pd.DataFrame]:
    acc = ems_frame()
    d = death_timing()
    out = {
        "death_timing": timing_table(d),
        "ems_availability": ems_availability(acc),
        "identifiability": identifiability(),
    }
    save_table(
        out["death_timing"],
        MODULE,
        "death_timing",
        description="Timing of death after the crash (at scene, within 1 h, 1-24 h, 1-30 days) by group",
        population="FARS deaths 2016-2024",
        unit="person killed",
        method="Census shares; alcohol groups as expected counts over 10 BAC implicates",
        inputs=["FARS person (raw DOA, LAG_HRS, LAG_MINS)", "data/processed/fars_person.parquet"],
    )
    save_table(
        out["ems_availability"],
        MODULE,
        "ems_availability",
        description="Availability of EMS arrival time and minutes from crash to EMS arrival, fatal crashes",
        population="FARS fatal crashes 2016-2024",
        unit="crash",
        method="Clock-time differences modulo 24 h; unknown codes excluded",
        inputs=["FARS accident (raw NOT_*, ARR_*, HOSP_*)"],
    )
    save_table(
        out["identifiability"],
        MODULE,
        "identifiability",
        description="Which of the four crash stages the data can identify",
        population="",
        unit="stage",
        method="Design argument",
    )
    return out
