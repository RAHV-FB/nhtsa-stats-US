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

3. Contrast within crash configuration.  Speeders and drunk drivers are concentrated in
   single-vehicle crashes, where the belt RR is lower, so the unstratified contrast of belt RRs
   mixes a configuration effect with the behaviour effect.  ``config_contrasts`` estimates the
   behaviour / reference ratio of belt RRs separately within each configuration layer (single vs
   multi-vehicle; rollover vs not; both crossed; harmonised crash type) and pools the log ratios
   across layers with inverse-variance weights (bootstrap SEs, as in the heterogeneity test
   above); ``belt_rr_by_configuration`` gives the belt RR itself in each layer.

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
    elig: pd.DataFrame,
    rng: np.random.Generator,
    n_boot: int = N_BOOT,
    joint_rng: np.random.Generator | None = None,
) -> pd.DataFrame:
    """Within-vehicle belt RR per stratum and, for two-stratum splits, a heterogeneity test.

    The per-stratum RRs and CIs use ``rng`` exactly as before.  The heterogeneity test (ratio of
    the second stratum's RR to the first's) takes its SE from a joint crash-cluster bootstrap of
    both strata (:func:`joint_log_ratio_se`, drawn from ``joint_rng``, default a fresh generator
    seeded ``RANDOM_SEED + 2`` as in :func:`config_contrasts`), because vehicles of one crash can
    fall in both strata (for example a speeding driver's car and the other driver's car), so the
    two RRs are not independent.  ``heterogeneity_low`` / ``heterogeneity_high`` are the 95% Wald
    limits of the ratio.
    """
    joint_rng = np.random.default_rng(config.RANDOM_SEED + 2) if joint_rng is None else joint_rng
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
                "heterogeneity_low": np.nan,
                "heterogeneity_high": np.nan,
                "heterogeneity_p": np.nan,
            }
            recs.append(rec)
        if len(recs) == 2:
            a, b = recs
            d = np.log(b["rr_belted_vs_unbelted"]) - np.log(a["rr_belted_vs_unbelted"])
            m_a, m_b = (m for m in levels.values())
            se = joint_log_ratio_se(elig, m_b, m_a, joint_rng, n_boot)
            b["heterogeneity_ratio"] = float(np.exp(d))
            b["heterogeneity_low"] = float(np.exp(d - 1.96 * se))
            b["heterogeneity_high"] = float(np.exp(d + 1.96 * se))
            b["heterogeneity_p"] = float(2 * stats.norm.sf(abs(d / se)))
        rows += recs
        log.info("dpc %s done", split)
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------------------
# Behaviour contrasts within crash configuration
# --------------------------------------------------------------------------------------
SPEEDING_TYPES = ["exceeded_limit_or_racing", "too_fast_for_conditions", "speeding_unspecified"]
MIN_LAYER_DEATHS = config.MIN_CELL_N


def add_configuration(elig: pd.DataFrame) -> pd.DataFrame:
    """Add vehicle ``veh_rollover`` (max over occupants; NaN if unknown) and ``crash_type``."""
    per = pl.read_parquet(
        config.PROCESSED_DIR / "fars_person.parquet",
        columns=["YEAR", "case_id", "VEH_NO", "veh_rollover", "crash_type"],
    ).to_pandas()
    veh = per.groupby(["YEAR", "case_id", "VEH_NO"], as_index=False).agg(
        veh_rollover=("veh_rollover", "max"), crash_type=("crash_type", "first")
    )
    base = elig.drop(columns=["veh_rollover", "crash_type"], errors="ignore")
    return base.merge(veh, on=["YEAR", "case_id", "VEH_NO"], how="left", validate="many_to_one")


def behaviour_masks(elig: pd.DataFrame) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """contrast -> (behaviour mask, reference mask); same definitions as :func:`strata`."""
    st = elig["own_speeding_type"].astype(str)
    p = elig["drv_p_p08"]
    return {
        "driver speeding (any) vs not speeding": (
            st.isin(SPEEDING_TYPES).to_numpy(),
            (st == "no").to_numpy(),
        ),
        "driver exceeded limit / racing vs not speeding": (
            (st == "exceeded_limit_or_racing").to_numpy(),
            (st == "no").to_numpy(),
        ),
        "driver BAC >= .08 (MI) vs BAC < .08": ((p > 0.5).to_numpy(), (p <= 0.5).to_numpy()),
    }


def configuration_layers(elig: pd.DataFrame) -> dict[str, dict[str, np.ndarray]]:
    """adjustment -> layer -> row mask (layers of one adjustment are disjoint)."""
    single = (elig["n_vehicles"].astype(str) == "1").to_numpy()
    roll = elig["veh_rollover"].to_numpy()
    r1, r0 = roll == 1, roll == 0
    ct = elig["crash_type"].astype(str)
    layers = {
        "single vs multi-vehicle crash": {"single vehicle": single, "multi-vehicle": ~single},
        "rollover vs no rollover": {"rollover": r1, "no rollover": r0},
        "single/multi-vehicle x rollover": {
            "single vehicle, rollover": single & r1,
            "single vehicle, no rollover": single & r0,
            "multi-vehicle, rollover": ~single & r1,
            "multi-vehicle, no rollover": ~single & r0,
        },
        "crash type": {
            t: (ct == t).to_numpy()
            for t in (
                "sv_rollover_first",
                "sv_off_roadway",
                "sv_on_roadway",
                "mv_angle",
                "mv_head_on",
                "mv_rear_end",
                "mv_sideswipe",
                "mv_other",
            )
        },
    }
    return layers


def _arm_pairs(elig: pd.DataFrame, mask: np.ndarray) -> pd.DataFrame:
    """Driver / right-front passenger pairs of the vehicles selected by ``mask``."""
    sub = elig.loc[mask]
    drv = (sub["ptype"] == "driver") & (sub["SEAT_POS"] == matched.SEAT_POS_DRIVER)
    rf = (sub["ptype"] == "passenger") & (sub["SEAT_POS"] == matched.SEAT_POS_RIGHT_FRONT)
    return matched.pair_frame(sub, "belted", drv, rf)


def belt_rr(elig: pd.DataFrame, mask: np.ndarray, label: str, rng, n_boot: int) -> dict:
    """Combined DPC belt RR (crash-bootstrap CI and SE) of the vehicles selected by ``mask``."""
    pairs = _arm_pairs(elig, mask)
    if len(pairs) == 0:
        return {"n_pairs": 0, "rr": np.nan, "se_log": np.nan, "min_death_count": 0.0}
    res = matched.dpc_analysis(pairs, label, "belted", rng, n_boot)
    comb = res[res["component"].str.startswith("combined")].iloc[0]
    return {
        "n_pairs": int(comb["n_pairs"]),
        "n_pairs_with_death": int(comb["n_pairs_with_death"]),
        "rr": float(comb["rr_x1_vs_x0"]),
        "rr_low": float(comb["rr_low_crash_boot"]),
        "rr_high": float(comb["rr_high_crash_boot"]),
        "se_log": float(comb["se_log_bootstrap"]),
        "min_death_count": float(comb["min_death_count"]),
    }


def joint_log_ratio_se(
    elig: pd.DataFrame,
    beh_mask: np.ndarray,
    ref_mask: np.ndarray,
    rng: np.random.Generator,
    n_boot: int,
) -> float:
    """Crash-bootstrap SE of log(belt RR, behaviour arm) - log(belt RR, reference arm).

    Vehicles of one crash can sit in both arms (for example a speeding driver's car and the
    other, non-speeding driver's car), so the two belt RRs are not independent.  Each replicate
    resamples whole crashes once and recomputes both arms from the same resampled crashes; the SE
    is the SD of the difference of the two combined DPC log RRs (NaN if more than 10% of the
    replicates are degenerate).
    """
    pb, pr = _arm_pairs(elig, beh_mask), _arm_pairs(elig, ref_mask)
    if len(pb) == 0 or len(pr) == 0:
        return float("nan")
    codes, uniq = pd.factorize(pd.concat([pb["crash_id"], pr["crash_id"]], ignore_index=True))
    nc = len(uniq)
    per = []
    for pairs, c in ((pb, codes[: len(pb)]), (pr, codes[len(pb) :])):
        m = np.zeros((nc, 16))
        np.add.at(m, (c, matched.cell_index(pairs)), 1.0)
        per.append(m)
    diff = np.empty(n_boot)
    for b in range(n_boot):
        w = np.bincount(rng.integers(0, nc, nc), minlength=nc)
        cb, cr = (w @ m for m in per)
        diff[b] = matched.dpc_combined(cb.reshape(2, 2, 2, 2)) - matched.dpc_combined(
            cr.reshape(2, 2, 2, 2)
        )
    return matched._boot_sd(diff)


def pool_log_ratios(d: np.ndarray, se: np.ndarray) -> dict:
    """Inverse-variance pooled log ratio -> ratio, 95% CI and two-sided p."""
    w = 1 / se**2
    m = float((w * d).sum() / w.sum())
    s = float(w.sum() ** -0.5)
    q = float((w * (d - m) ** 2).sum())
    z = stats.norm.ppf(0.975)
    return {
        "ratio": float(np.exp(m)),
        "low": float(np.exp(m - z * s)),
        "high": float(np.exp(m + z * s)),
        "p": float(2 * stats.norm.sf(abs(m / s))),
        "q_heterogeneity_p": float(stats.chi2.sf(q, len(d) - 1)) if len(d) > 1 else np.nan,
    }


def config_contrasts(
    elig: pd.DataFrame,
    rng: np.random.Generator,
    n_boot: int = N_BOOT,
    joint_rng: np.random.Generator | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Behaviour / reference ratio of belt RRs, unstratified and within crash configuration.

    Layers whose behaviour or reference arm has fewer than ``config.MIN_CELL_N`` deaths in the
    smallest DPC cell (or no finite bootstrap SE) are dropped from the pooled estimate and
    listed with ``used_in_pooled`` = False.  The SE of each ratio comes from a joint crash
    bootstrap of both arms (:func:`joint_log_ratio_se`, drawn from ``joint_rng``, default a
    fresh generator seeded ``RANDOM_SEED + 2``), not from combining independent arm SEs; the
    per-arm RRs and their CIs use ``rng`` exactly as before.  Layers are pooled as if
    independent, although a multi-vehicle crash can contribute vehicles to several layers.
    Returns (contrasts, belt RR per layer and arm).
    """
    joint_rng = np.random.default_rng(config.RANDOM_SEED + 2) if joint_rng is None else joint_rng
    contrasts, rr_rows = [], []
    all_rows = np.ones(len(elig), bool)
    cache: dict[tuple[str, str], dict] = {}

    def est(key: tuple[str, str], mask: np.ndarray, label: str) -> dict:
        if key not in cache:
            cache[key] = belt_rr(elig, mask, label, rng, n_boot)
        return cache[key]

    layers = configuration_layers(elig)
    for cname, (beh, ref) in behaviour_masks(elig).items():
        a = est((cname, "ref|all"), ref & all_rows, f"{cname}: reference")
        b = est((cname, "beh|all"), beh & all_rows, f"{cname}: behaviour")
        d = np.log(b["rr"]) - np.log(a["rr"])
        se = joint_log_ratio_se(elig, beh & all_rows, ref & all_rows, joint_rng, n_boot)
        contrasts.append(
            {
                "contrast": cname,
                "adjustment": "none (unstratified)",
                "layer": "all vehicles",
                "rr_reference": a["rr"],
                "rr_behaviour": b["rr"],
                "n_pairs_reference": a["n_pairs"],
                "n_pairs_behaviour": b["n_pairs"],
                "ratio_of_rrs": float(np.exp(d)),
                "ratio_low": float(np.exp(d - 1.96 * se)),
                "ratio_high": float(np.exp(d + 1.96 * se)),
                "p": float(2 * stats.norm.sf(abs(d / se))),
                "q_heterogeneity_p": np.nan,
                "used_in_pooled": True,
                "n_layers_pooled": 1,
            }
        )
        for adj, lay in layers.items():
            ds, ses, recs = [], [], []
            for lname, lmask in lay.items():
                a = est((cname, f"ref|{adj}|{lname}"), ref & lmask, f"{cname}: reference, {lname}")
                b = est((cname, f"beh|{adj}|{lname}"), beh & lmask, f"{cname}: behaviour, {lname}")
                ok = (
                    min(a["min_death_count"], b["min_death_count"]) >= MIN_LAYER_DEATHS
                    and np.isfinite(a["se_log"])
                    and np.isfinite(b["se_log"])
                    and a["rr"] > 0
                    and b["rr"] > 0
                )
                se = np.nan
                if ok:
                    se = joint_log_ratio_se(elig, beh & lmask, ref & lmask, joint_rng, n_boot)
                    ok = bool(np.isfinite(se))
                d = np.log(b["rr"]) - np.log(a["rr"]) if ok else np.nan
                if ok:
                    ds.append(d)
                    ses.append(se)
                recs.append(
                    {
                        "contrast": cname,
                        "adjustment": adj,
                        "layer": lname,
                        "rr_reference": a["rr"],
                        "rr_behaviour": b["rr"],
                        "n_pairs_reference": a["n_pairs"],
                        "n_pairs_behaviour": b["n_pairs"],
                        "ratio_of_rrs": float(np.exp(d)) if ok else np.nan,
                        "ratio_low": float(np.exp(d - 1.96 * se)) if ok else np.nan,
                        "ratio_high": float(np.exp(d + 1.96 * se)) if ok else np.nan,
                        "p": float(2 * stats.norm.sf(abs(d / se))) if ok else np.nan,
                        "q_heterogeneity_p": np.nan,
                        "used_in_pooled": bool(ok),
                        "n_layers_pooled": np.nan,
                    }
                )
            contrasts += recs
            if ds:
                pooled = pool_log_ratios(np.array(ds), np.array(ses))
                contrasts.append(
                    {
                        "contrast": cname,
                        "adjustment": adj,
                        "layer": "pooled within layers",
                        "rr_reference": np.nan,
                        "rr_behaviour": np.nan,
                        "n_pairs_reference": sum(
                            r["n_pairs_reference"] for r in recs if r["used_in_pooled"]
                        ),
                        "n_pairs_behaviour": sum(
                            r["n_pairs_behaviour"] for r in recs if r["used_in_pooled"]
                        ),
                        "ratio_of_rrs": pooled["ratio"],
                        "ratio_low": pooled["low"],
                        "ratio_high": pooled["high"],
                        "p": pooled["p"],
                        "q_heterogeneity_p": pooled["q_heterogeneity_p"],
                        "used_in_pooled": True,
                        "n_layers_pooled": len(ds),
                    }
                )
            log.info("config contrast %s | %s done", cname, adj)
    # Belt RR itself in each layer (all drivers, whatever their behaviour).
    for adj, lay in layers.items():
        for lname, lmask in lay.items():
            r = est(("all", f"{adj}|{lname}"), lmask, f"belt RR: {lname}")
            rr_rows.append(
                {
                    "adjustment": adj,
                    "layer": lname,
                    "n_pairs": r["n_pairs"],
                    "n_pairs_with_death": r.get("n_pairs_with_death", 0),
                    "rr_belted_vs_unbelted": r["rr"],
                    "rr_low": r.get("rr_low", np.nan),
                    "rr_high": r.get("rr_high", np.nan),
                    "se_log_bootstrap": r["se_log"],
                    "min_death_count": r["min_death_count"],
                }
            )
    return pd.DataFrame(contrasts), pd.DataFrame(rr_rows)


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
        method=f"Evans double-pair comparison, inverse-variance combination of four components; crash-cluster percentile bootstrap ({n_boot} replicates); heterogeneity z-test on the log ratio of the two strata's RRs with the SE from a joint crash-cluster bootstrap of both strata (they can share crashes; seed offset +2)",
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
    # Behaviour contrasts within crash configuration (added; uses the same estimators).  A fresh
    # generator keeps the pre-existing tables independent of this block.
    elig_cfg = add_configuration(elig)
    cfg_rng = np.random.default_rng(config.RANDOM_SEED + 1)
    contrasts, belt_by_layer = config_contrasts(elig_cfg, cfg_rng, n_boot)
    save_table(
        contrasts,
        MODULE,
        "dpc_contrast_within_configuration",
        description="Ratio of within-vehicle belt risk ratios, driver behaviour vs reference (speeding vs not, exceeded limit vs not, BAC >= .08 vs below), unstratified and within crash configuration (single/multi-vehicle, rollover, both crossed, harmonised crash type) with inverse-variance pooled estimates across layers",
        population="FARS 2016-2024 light passenger vehicles with one eligible driver and one right-front passenger (Phase-1 eligibility); vehicles with unknown rollover are excluded from rollover layers",
        unit="vehicle (pair)",
        outcome="death",
        method=f"Evans double-pair comparison per behaviour arm and layer (crash-cluster percentile bootstrap, {n_boot} replicates, fixed seed independent of the other tables); log ratio of arm RRs with SE from a joint crash-cluster bootstrap of both arms (the arms share crashes, so they are not treated as independent; separate seed offset +2), 95% Wald CI and z-test; pooled = inverse-variance weighted mean of layer log ratios, Cochran Q p for between-layer heterogeneity; layers with a DPC death count below {MIN_LAYER_DEATHS} in either arm are listed but not pooled",
        inputs=["data/processed/fars_person.parquet", "data/processed/fars_driver.parquet"],
    )
    save_table(
        belt_by_layer,
        MODULE,
        "belt_rr_by_configuration",
        description="Within-vehicle belt risk ratio of death (driver / right-front pairs) in each crash-configuration layer, all drivers",
        population="FARS 2016-2024 light passenger vehicles with one eligible driver and one right-front passenger (Phase-1 eligibility)",
        unit="vehicle (pair)",
        outcome="death",
        method=f"Evans double-pair comparison, crash-cluster percentile bootstrap ({n_boot} replicates)",
        inputs=["data/processed/fars_person.parquet", "data/processed/fars_driver.parquet"],
    )
    return {
        "dpc": dpc,
        "nested": nested,
        "config_contrasts": contrasts,
        "belt_rr_by_configuration": belt_by_layer,
    }
