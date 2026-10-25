"""Restraint use and driver behaviour: does belt protection depend on how the crash came about?
(Phase 2, Q4; docs/research_plan_phase2.md §5.2.)

Hypothesis from the stage framework: belts act at Stage C (injury given the crash), whereas
speeding and alcohol act at Stages A-B (whether and how violently the crash happens).  If so,
the *within-vehicle* belt association should be similar whatever the driver's behaviour, while
the *across-crash* belt association should shrink when crash-level behaviour is adjusted for
(unbelted occupants are over-represented in crashes with impaired or speeding drivers).

1. FARS double-pair comparison (Phase-1 estimator, ``matched.dpc_analysis``): driver /
   right-front-passenger pairs in light vehicles, belted vs unbelted, within strata of the
   driver's recorded speeding (any; exceeded limit), the driver's BAC >= .08 (multiple
   imputation, implicate mean > 0.5), single- vs multi-vehicle crash and night.  Each stratum
   gives a within-vehicle risk ratio of death; strata are disjoint, so differences are tested
   with the crash-bootstrap SEs.
2. CRSS nested sequence for the unbelted risk ratio among light-vehicle occupants aged 15+:
   crude -> + crash environment -> + person (age, sex, seat, vehicle type) -> + the driver's
   own speeding and alcohol -> + crash configuration.  Same population in every step;
   standardised RR and RD (``factorial`` with one factor).

Limitations: belt use of survivors is largely self-reported (Phase 1: the within-vehicle
reduction falls from 66% to 38% if 10% of 'belted' survivors were unbelted); the pairs are
conditional on a fatal crash; the strata use police-recorded behaviour.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd
import polars as pl
from scipy import stats

from nhtsa_stats import config
from nhtsa_stats.analysis import factorial, matched, multifactor
from nhtsa_stats.analysis.factorial import Factor
from nhtsa_stats.reporting.io import save_table

log = logging.getLogger(__name__)
MODULE = "restraint_behaviour"
N_BOOT = 1000


def fars_pairs_frame() -> pd.DataFrame:
    df = matched.load_fars_occupants()
    elig, _ = matched.lpv_flow_and_eligible(df)
    drv = pl.read_parquet(
        config.PROCESSED_DIR / "fars_driver.parquet",
        columns=[
            "YEAR",
            "case_id",
            "VEH_NO",
            "own_speeding_type",
            "drv_p_p08",
            "n_vehicles",
            "night",
        ],
    ).to_pandas()
    elig = elig.merge(drv, on=["YEAR", "case_id", "VEH_NO"], how="left", validate="many_to_one")
    elig["belted"] = 1 - elig["unbelted"]
    return elig


def strata(elig: pd.DataFrame) -> dict[str, dict[str, np.ndarray]]:
    st = elig["own_speeding_type"].astype(str)
    p = elig["drv_p_p08"]
    nv = elig["n_vehicles"].astype(str)
    return {
        "all": {"all vehicles": np.ones(len(elig), bool)},
        "driver speeding (any)": {
            "driver not speeding": (st == "no").to_numpy(),
            "driver speeding": st.isin(
                ["exceeded_limit_or_racing", "too_fast_for_conditions", "speeding_unspecified"]
            ).to_numpy(),
        },
        "driver exceeded limit": {
            "driver not speeding": (st == "no").to_numpy(),
            "driver exceeded limit / racing": (st == "exceeded_limit_or_racing").to_numpy(),
        },
        "driver BAC >= .08 (MI)": {
            "driver BAC < .08": (p <= 0.5).to_numpy(),
            "driver BAC >= .08": (p > 0.5).to_numpy(),
        },
        "driver speeding and alcohol": {
            "neither": ((st == "no") & (p <= 0.5)).to_numpy(),
            "both": (
                st.isin(
                    ["exceeded_limit_or_racing", "too_fast_for_conditions", "speeding_unspecified"]
                )
                & (p > 0.5)
            ).to_numpy(),
        },
        "vehicles in crash": {
            "multi-vehicle": (nv != "1").to_numpy(),
            "single vehicle": (nv == "1").to_numpy(),
        },
        "time": {
            "day": (elig["night"] == 0).to_numpy(),
            "night": (elig["night"] == 1).to_numpy(),
        },
    }


def dpc_by_stratum(
    elig: pd.DataFrame, rng: np.random.Generator, n_boot: int = N_BOOT
) -> pd.DataFrame:
    rows = []
    for split, levels in strata(elig).items():
        recs = []
        for label, mask in levels.items():
            sub = elig.loc[mask]
            drv = (sub["ptype"] == "driver") & (sub["SEAT_POS"] == matched.SEAT_POS_DRIVER)
            rf = (sub["ptype"] == "passenger") & (sub["SEAT_POS"] == matched.SEAT_POS_RIGHT_FRONT)
            pairs = matched.pair_frame(sub, "belted", drv, rf)
            res = matched.dpc_analysis(pairs, f"{split}: {label}", "belted", rng, n_boot)
            comb = res[res["component"].str.startswith("combined")].iloc[0]
            rec = {
                "split": split,
                "stratum": label,
                "n_pairs": int(comb["n_pairs"]),
                "n_pairs_with_death": int(comb["n_pairs_with_death"]),
                "min_death_count": comb["min_death_count"],
                "rr_belted_vs_unbelted": comb["rr_x1_vs_x0"],
                "rr_low": comb["rr_low_crash_boot"],
                "rr_high": comb["rr_high_crash_boot"],
                "reduction": comb["reduction_1_minus_rr"],
                "reduction_low": 1 - comb["rr_high_crash_boot"],
                "reduction_high": 1 - comb["rr_low_crash_boot"],
                "se_log_bootstrap": comb["se_log_bootstrap"],
                "flag": comb["flag"],
                "heterogeneity_ratio": np.nan,
                "heterogeneity_p": np.nan,
            }
            recs.append(rec)
        if len(recs) == 2:
            a, b = recs
            d = np.log(b["rr_belted_vs_unbelted"]) - np.log(a["rr_belted_vs_unbelted"])
            se = np.hypot(a["se_log_bootstrap"], b["se_log_bootstrap"])
            b["heterogeneity_ratio"] = float(np.exp(d))
            b["heterogeneity_p"] = float(2 * stats.norm.sf(abs(d / se)))
        rows += recs
        log.info("dpc %s done", split)
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------------------
NESTED = {
    "crude": [],
    "+ crash environment": multifactor.ENV,
    "+ person and vehicle": [*multifactor.ENV, "age_band", "sex", "role", "body"],
    "+ driver's own speeding and alcohol": [
        *multifactor.ENV,
        "age_band",
        "sex",
        "role",
        "body",
        "lnk_speeding",
        "lnk_alcohol_im",
    ],
    "+ crash configuration": [
        *multifactor.ENV,
        "age_band",
        "sex",
        "role",
        "body",
        "lnk_speeding",
        "lnk_alcohol_im",
        "crash_type",
        "n_vehicles",
    ],
}
UNBELTED = Factor("unbelted", "unbelted", ("yes",), ("no",), "unbelted vs belted")


def crss_nested() -> pd.DataFrame:
    df, design = multifactor.person_frame()
    mask = (
        df["relation"].isin(["driver", "passenger"]).to_numpy()
        & df["body"].isin(list(multifactor.LPV_BODY_GROUPS)).to_numpy()
        & df["restraint"].isin(["belted", "none", multifactor.UNK]).to_numpy()
        & ~df["age_band"].isin(["0-14", multifactor.UNK]).to_numpy()
        & df["killed"].notna().to_numpy()
    )
    sub, sd = df.loc[mask].reset_index(drop=True), design.subset(mask)
    rows = []
    for step, covs in NESTED.items():
        res = factorial.fit_factorial(sub, sd, [UNBELTED], covs, "killed")
        mt = factorial.margins_table(res).set_index("key")
        rows.append(
            {
                "step": step,
                "covariates": ",".join(covs),
                "n": len(sub),
                "n_events": res.n_events,
                "risk_belted": mt.loc["0", "adj_risk"],
                "risk_unbelted": mt.loc["1", "adj_risk"],
                "rr": mt.loc["1", "rr_vs_none"],
                "rr_low": mt.loc["1", "rr_vs_none_low"],
                "rr_high": mt.loc["1", "rr_vs_none_high"],
                "rd": mt.loc["1", "rd_vs_none"],
                "rd_low": mt.loc["1", "rd_vs_none_low"],
                "rd_high": mt.loc["1", "rd_vs_none_high"],
            }
        )
        log.info("crss nested %s done", step)
    out = pd.DataFrame(rows)
    out["share_logrr_retained"] = np.log(out["rr"]) / np.log(out["rr"].iloc[0])
    return out


def run(n_boot: int = N_BOOT) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(config.RANDOM_SEED)
    elig = fars_pairs_frame()
    dpc = dpc_by_stratum(elig, rng, n_boot)
    save_table(
        dpc,
        MODULE,
        "dpc_by_driver_behaviour",
        description="Within-vehicle belt risk ratio of death (driver / right-front pairs) within strata of the driver's speeding, BAC, crash type and time",
        population="FARS 2016-2024 light passenger vehicles with one eligible driver and one right-front passenger (Phase-1 eligibility)",
        unit="vehicle (pair)",
        outcome="death",
        method=f"Evans double-pair comparison, inverse-variance combination of four components; crash-cluster percentile bootstrap ({n_boot} replicates); heterogeneity z-test on log RR with bootstrap SEs",
        inputs=["data/processed/fars_person.parquet", "data/processed/fars_driver.parquet"],
    )
    nested = crss_nested()
    save_table(
        nested,
        MODULE,
        "crss_unbelted_nested",
        description="Unbelted vs belted standardised RR of death for light-vehicle occupants as covariate blocks are added (fixed sample)",
        population="CRSS 2016-2024 drivers and passengers of light passenger vehicles aged 15+, belt use belted/none/unknown",
        unit="occupant",
        outcome="killed (imputed severity)",
        method="Survey logistic model, unbelted + covariates; standardised margins; Taylor linearisation (42 df)",
        inputs=[
            "data/processed/crss_person.parquet",
            "data/processed/crss_driver.parquet",
            "data/processed/crss_person_link.parquet",
        ],
    )
    return {"dpc": dpc, "nested": nested}
