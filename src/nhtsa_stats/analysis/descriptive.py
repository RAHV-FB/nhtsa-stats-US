"""Descriptive baseline: counts, shares, rates and over-representation.

Outputs (outputs/tables/descriptive):

* ``fars_annual`` -- observed fatal crashes and deaths per year (FARS census), deaths by
  person type.
* ``crss_annual`` -- estimated police-reported crashes per year by maximum severity (CRSS,
  design-based 95% CIs).
* ``frequency_vs_severity`` -- for each harmonised factor level, four distinct quantities:
    1. ``share_all_crashes``    weighted share of all police-reported crashes (CRSS);
    2. ``share_fatal_crss``     weighted share of fatal crashes in CRSS;
    3. ``share_fatal_fars``     share of all fatal crashes in FARS (census, no sampling error);
    4. ``fatal_rate``           crude probability that a crash with this level is fatal (CRSS),
  and the over-representation ratio ``share_fatal_fars / share_all_crashes``.  A ratio near 1
  means a factor is common in fatal crashes *because it is common in crashes*; a ratio well
  above 1 means fatal crashes are disproportionately concentrated in it.
* ``fars_composition_by_year`` -- yearly shares of key characteristics among FARS fatal crashes
  and deaths.

FARS and CRSS rows are never pooled: FARS supplies fatal-crash counts, CRSS the denominators.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from nhtsa_stats import config
from nhtsa_stats.analysis import data, specs
from nhtsa_stats.analysis.survey import logit_ci, svy_mean, svy_total
from nhtsa_stats.reporting.io import save_table

log = logging.getLogger(__name__)
MODULE = "descriptive"

# Factors harmonised identically in FARS and CRSS (same source fields and codes).
SHARED_FACTORS = [
    "light",
    "weather",
    "surface",
    "speed_limit",
    "tod",
    "weekend",
    "junction",
    "work_zone",
    "crash_type",
    "n_vehicles",
    "speeding",
    "any_motorcycle",
    "any_heavy_truck",
    "young_driver",
    "older_driver",
]
CRSS_ONLY = ["urbanicity", "region", "interstate", "alcohol", "alcohol_im", "drugs", "distracted"]


def fars_annual() -> pd.DataFrame:
    crash = data.fars_crash()
    per = data.fars_person()
    killed = per[per["killed"] == 1]
    a = crash.groupby("YEAR").agg(fatal_crashes=("case_id", "size"), deaths=("FATALS", "sum"))
    by_type = killed.pivot_table(
        index="YEAR", columns="ptype", values="case_id", aggfunc="size", fill_value=0
    )
    by_type.columns = [f"deaths_{c}" for c in by_type.columns]
    out = a.join(by_type).reset_index()
    return out


def crss_annual() -> pd.DataFrame:
    df, design = data.crss_crash(outcome=None)
    rows = []
    sev_labels = {0: "O_no_injury", 1: "C_possible", 2: "B_minor", 3: "A_serious", 4: "K_fatal"}
    for y in config.YEARS:
        dom_y = (df["YEAR"] == y).to_numpy()
        tot = svy_total(design, np.ones(design.n), dom_y)
        rec = {
            "YEAR": y,
            "n_sample": int(dom_y.sum()),
            "crashes": tot.estimate,
            "crashes_se": tot.se,
        }
        for k, lab in sev_labels.items():
            e = svy_total(design, (df["kabco"] == k).to_numpy(float), dom_y)
            rec[lab] = e.estimate
            rec[f"{lab}_se"] = e.se
        e = svy_total(design, df["kabco"].isna().to_numpy(float), dom_y)
        rec["severity_unknown"] = e.estimate
        p = svy_mean(design, df["fatal"].to_numpy(float), dom_y)
        lo, hi = logit_ci(p.estimate, p.se, p.df)
        rec.update(fatal_share=p.estimate, fatal_share_low=lo, fatal_share_high=hi)
        rows.append(rec)
    return pd.DataFrame(rows)


def _levels(var: str) -> list:
    return specs.CRASH_LEVELS.get(var, ["no", "yes", "unknown"])


def frequency_vs_severity() -> pd.DataFrame:
    tri = [v for v in SHARED_FACTORS + CRSS_ONLY if v in specs.CRASH_TRI]
    df, design = data.crss_crash(outcome=None, tri_state_cols=tri)
    fars = data.fars_crash()
    for v in tri:
        if v in fars.columns:
            fars[v] = data.tri_state(fars[v])
    fatal = df["fatal"].to_numpy(float)
    is_fatal = fatal == 1
    known_sev = np.isfinite(fatal)
    rows = []
    for var in SHARED_FACTORS + CRSS_ONLY:
        for lv in _levels(var):
            ind = (df[var] == lv).to_numpy(float)
            if ind.sum() == 0:
                continue
            share_all = svy_mean(design, ind)
            share_fat = svy_mean(design, ind, is_fatal)
            rate = svy_mean(design, fatal, (ind == 1) & known_sev)
            lo, hi = logit_ci(rate.estimate, rate.se, rate.df)
            rec = {
                "factor": var,
                "label": specs.LABELS.get(var, var),
                "level": lv,
                "n_crss": int(ind.sum()),
                "n_crss_fatal": int((ind * is_fatal).sum()),
                "share_all_crashes": share_all.estimate,
                "share_all_crashes_se": share_all.se,
                "share_fatal_crss": share_fat.estimate,
                "share_fatal_crss_se": share_fat.se,
                "fatal_rate": rate.estimate,
                "fatal_rate_low": lo,
                "fatal_rate_high": hi,
                "fatal_rate_flag": "suppressed"
                if rate.n < config.MIN_CELL_N or rec_events(ind, is_fatal) < 5
                else ("unstable" if rate.rse > config.MAX_RSE else ""),
            }
            if var in SHARED_FACTORS and var in fars.columns:
                share_fars = float((fars[var] == lv).mean())
                rec["n_fars"] = int((fars[var] == lv).sum())
                rec["share_fatal_fars"] = share_fars
                # CI of the ratio reflects CRSS sampling error only (FARS is a census).
                r = share_fars / share_all.estimate
                se_log = share_all.se / share_all.estimate
                t = design.tcrit()
                rec.update(
                    overrep_ratio=r,
                    overrep_low=r * np.exp(-t * se_log),
                    overrep_high=r * np.exp(t * se_log),
                )
            rows.append(rec)
    return pd.DataFrame(rows)


def rec_events(ind: np.ndarray, is_fatal: np.ndarray) -> int:
    return int((ind * is_fatal).sum())


def fars_composition_by_year() -> pd.DataFrame:
    crash = data.fars_crash()
    per = data.fars_person()
    killed = per[per["killed"] == 1].copy()
    occ_killed = killed[killed["ptype"].isin(["driver", "passenger"])]
    lpv = occ_killed[occ_killed["body"].isin(["car", "suv", "pickup", "van", "light_truck_other"])]
    rows = []
    for y, g in crash.groupby("YEAR"):
        k = killed[killed["YEAR"] == y]
        lv = lpv[lpv["YEAR"] == y]
        known_belt = lv["restraint"].isin(["belted", "none"])
        rows.append(
            {
                "YEAR": y,
                "fatal_crashes": len(g),
                "deaths": int(g["FATALS"].sum()),
                "pct_crashes_speeding": 100 * (g["speeding"] == 1).mean(),
                "pct_crashes_speeding_unknown": 100 * g["speeding"].isna().mean(),
                "pct_crashes_driver_bac08_mi": 100 * g["driver_bac08_prob"].mean(),
                "pct_crashes_dark": 100 * (g["dark"] == 1).mean(),
                "pct_crashes_pedestrian": 100 * (g["any_pedestrian"] == 1).mean(),
                "pct_crashes_motorcycle": 100 * (g["any_motorcycle"] == 1).mean(),
                "pct_crashes_rural_road": 100 * (g["rural"] == 1).mean(),
                "pct_deaths_pedestrian": 100 * (k["ptype"] == "pedestrian").mean(),
                "pct_deaths_cyclist": 100 * (k["ptype"] == "cyclist").mean(),
                "pct_deaths_motorcyclist": 100
                * ((k["body"] == "motorcycle") & k["ptype"].isin(["driver", "passenger"])).mean(),
                "lpv_occupant_deaths": len(lv),
                "pct_lpv_deaths_unrestrained_of_known": 100
                * (lv.loc[known_belt, "restraint"] == "none").mean(),
                "pct_lpv_deaths_restraint_unknown": 100
                * (~lv["restraint"].isin(["belted", "none", "child_restraint"])).mean(),
            }
        )
    return pd.DataFrame(rows)


def run() -> dict[str, pd.DataFrame]:
    out = {
        "fars_annual": fars_annual(),
        "crss_annual": crss_annual(),
        "frequency_vs_severity": frequency_vs_severity(),
        "fars_composition_by_year": fars_composition_by_year(),
    }
    meta = {
        "fars_annual": (
            "Observed fatal crashes and deaths per year, deaths by person type",
            "FARS census of fatal crashes",
            "crash / person",
            "count",
        ),
        "crss_annual": (
            "Estimated police-reported crashes per year by maximum KABCO severity with design-based SEs",
            "CRSS (national probability sample)",
            "crash",
            "MAX_SEV",
        ),
        "frequency_vs_severity": (
            "Factor prevalence among all crashes (CRSS) vs among fatal crashes (CRSS and FARS), crude fatal "
            "rate and over-representation ratio",
            "CRSS 2016-2024 (denominators); FARS 2016-2024 (fatal crashes)",
            "crash",
            "fatal (MAX_SEV=4)",
        ),
        "fars_composition_by_year": (
            "Yearly composition of FARS fatal crashes and deaths",
            "FARS census",
            "crash / person",
            "fatal",
        ),
    }
    for name, df in out.items():
        desc, pop, unit, oc = meta[name]
        save_table(
            df,
            MODULE,
            name,
            description=desc,
            population=pop,
            unit=unit,
            outcome=oc,
            method="Design-based (CRSS: Taylor linearisation, 25 strata/67 PSUs) or census counts (FARS)",
            inputs=[
                "data/processed/crss_crash.parquet",
                "data/processed/fars_crash.parquet",
                "data/processed/fars_person.parquet",
            ],
        )
    return out
