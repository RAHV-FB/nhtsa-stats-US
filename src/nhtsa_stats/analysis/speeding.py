"""How much of the speeding-fatality association is accounted for by alcohol and by other
recorded circumstances?  (Phase 2, Q1, Q2, Q6; docs/research_plan_phase2.md §5.1.)

Exposures (crash level, CRSS police-reported crashes 2016-2024 with known imputed severity):

* ``exceeded``  -- a driver exceeded the posted limit or was racing (SPEEDREL 2/3) vs no
  speeding recorded for any driver; other speeding types and unknown keep their own level;
* ``speeding_any`` -- police-reported speeding of any type vs none (unknown separate);
* ``alcohol``  -- NHTSA-imputed alcohol involvement, with speeding *type* as a block, so the
  roles of the two behaviours can be compared symmetrically.

Method
    The Phase-1 lattice estimator (``confounding``): for every subset of seven covariate blocks
    {calendar/area, time, light, road environment, driver/vehicle mix, the other behaviour,
    crash configuration} a survey logistic model gives the exposure's standardised risk ratio
    and difference over all crashes.  Reported: sequential tables along several orderings
    (including "other behaviour first" and "other behaviour last"), exact Shapley shares of the
    crude log-RR with and without the configuration block (a plausible mediator), the range of
    each block's share over orderings, and odds ratios from the same specifications to show
    non-collapsibility.

Further analyses
    * stratum-specific adjusted RRs (alcohol absent / present under imputed and police coding,
      night / day, single / multi-vehicle, speed environment, period, hit-and-run excluded),
      with design-based tests of heterogeneity between strata;
    * speeding-type composition by alcohol, drugs, road, configuration, driver age and severity;
    * recording: FARS (fuller investigation) vs CRSS speeding share among fatal crashes within
      alcohol strata; a bias analysis of the alcohol-stratified exceedance RR under outcome-
      dependent recording; E-values;
    * selection by fatality: the speeding-alcohol association among all, non-fatal and fatal
      CRSS crashes and in FARS.

Not justified: "x% of speeding deaths are caused by alcohol".  A block's Shapley share is the
average change in a standardised log-RR when the block enters a model; it depends on the block
set, the ordering average, the standardisation population and on whether the block is a
confounder or a mediator, none of which the data can establish.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from pathlib import Path

import numpy as np
import pandas as pd
import polars as pl
from scipy import stats

from nhtsa_stats import config
from nhtsa_stats.analysis import confounding as cf
from nhtsa_stats.analysis import data, specs
from nhtsa_stats.analysis.measurement import corrected_rr
from nhtsa_stats.analysis.survey import (
    MarginSet,
    ModelSpec,
    SurveyDesign,
    SurveyLogit,
    logit_ci,
    svy_mean,
)
from nhtsa_stats.reporting.io import save_table

log = logging.getLogger(__name__)
MODULE = "speeding"
POP = cf.POPULATION
INPUT = ["data/processed/crss_crash.parquet", "data/processed/fars_crash.parquet"]
OUTCOMES = ("fatal", "ka")

ENV_BLOCKS = ("calendar_area", "time", "light", "road_environment", "driver_vehicle_mix")
EXPOSURES: dict[str, cf.Exposure] = {
    "exceeded": cf.Exposure(
        "exceeded",
        "speeding_type",
        "no",
        "exceeded_limit_or_racing",
        (*ENV_BLOCKS, "alcohol", "configuration"),
        "A driver exceeded the posted limit or was racing vs no speeding recorded",
    ),
    "speeding_any": cf.Exposure(
        "speeding_any",
        "speeding",
        "no",
        "yes",
        (*ENV_BLOCKS, "alcohol", "configuration"),
        "Police-reported speeding of any type vs none",
    ),
    "alcohol": cf.Exposure(
        "alcohol",
        "alcohol_im",
        "no",
        "yes",
        (*ENV_BLOCKS, "speeding_type", "configuration"),
        "Alcohol involved (NHTSA-imputed) vs not",
    ),
}
OTHER_BEHAVIOUR = {"exceeded": "alcohol", "speeding_any": "alcohol", "alcohol": "speeding_type"}

# Columns needed beyond the lattice blocks (strata and descriptions).
EXTRA_COLS = ("alcohol", "drugs", "hit_and_run", "n_vehicles", "kabco", "fatal_cc", "night")


def orders(exposure: cf.Exposure) -> dict[str, list[str]]:
    other = OTHER_BEHAVIOUR[exposure.name]
    env = list(ENV_BLOCKS)
    return {
        "other_behaviour_first": [other, *env, "configuration"],
        "environment_first": [*env, other, "configuration"],
        "configuration_first": ["configuration", *env, other],
        "reverse": list(exposure.blocks)[::-1],
    }


# --------------------------------------------------------------------------------------
# Data
# --------------------------------------------------------------------------------------
def load_frame() -> tuple[pd.DataFrame, SurveyDesign]:
    """Lattice frame of ``confounding.load_frame`` plus stratification columns."""
    df, design = data.crss_crash(outcome="fatal", tri_state_cols=specs.CRASH_TRI)
    df[cf.NIGHT_COLUMN] = df["night"].map({1: "night", 0: "day"}).fillna("unknown").astype(object)
    df["YEAR"] = df["YEAR"].astype(int)
    cols = cf.analysis_columns()
    keep = list(dict.fromkeys([*cols, cf.NIGHT_COLUMN, "fatal", "ka", *EXTRA_COLS]))
    df = df[keep].copy()
    for c in ("fatal", "ka", "fatal_cc"):
        df[c] = df[c].astype(float)
    for c in [*cols, cf.NIGHT_COLUMN]:
        df[c] = pd.Categorical(df[c], categories=cf.declared_levels(c))
        if df[c].isna().any():
            raise ValueError(f"{c}: values outside the declared levels")
    return df, design


# --------------------------------------------------------------------------------------
# Lattice summaries
# --------------------------------------------------------------------------------------
KEY_MODELS = {
    "crude": (),
    "other_behaviour_only": ("{other}",),
    "environment_only": ENV_BLOCKS,
    "environment_and_other_behaviour": (*ENV_BLOCKS, "{other}"),
    "all_blocks": (*ENV_BLOCKS, "{other}", "configuration"),
    "configuration_only": ("configuration",),
}


def key_models(exposure: cf.Exposure) -> dict[str, frozenset[str]]:
    other = OTHER_BEHAVIOUR[exposure.name]
    return {k: frozenset(b.replace("{other}", other) for b in v) for k, v in KEY_MODELS.items()}


def odds_ratio(
    df: pd.DataFrame, design: SurveyDesign, exposure: cf.Exposure, blocks, outcome: str
) -> tuple[float, float, float]:
    """Conditional odds ratio of the exposure from the same specification as a lattice fit."""
    blocks = frozenset(blocks)
    covs = [exposure.column, *exposure.variables(sorted(blocks, key=exposure.blocks.index))]
    cells, cdesign = cf.collapse_cells(df, design, covs, outcome)
    spec = ModelSpec(categorical={c: cf.category_levels(df, c) for c in covs})
    for c, levels in spec.categorical.items():
        cells[c] = cells[c].cat.set_categories(levels)
    m = SurveyLogit(spec, ridge=cf.RIDGE * len(cells) / len(df))
    m.fit(cells, cells[outcome].to_numpy(dtype=float), cdesign)
    tab = m.coef_table().set_index("term")
    r = tab.loc[f"{exposure.column}[{exposure.exposed}]"]
    return float(r["odds_ratio"]), float(r["or_low"]), float(r["or_high"])


def key_model_table(
    lattice: dict,
    ms: MarginSet,
    df: pd.DataFrame,
    design: SurveyDesign,
    exposure: cf.Exposure,
    outcome: str,
) -> pd.DataFrame:
    t = ms.design.tcrit()
    crude = "lr|crude"
    rows = []
    for name, blocks in key_models(exposure).items():
        k = cf.subset_key(blocks)
        f = lattice[blocks]
        lr, se = cf.linear_contrast(ms, {f"lr|{k}": 1.0})
        rd, rd_se = cf.linear_contrast(ms, {f"rd|{k}": 1.0})
        ret, ret_se = cf.ratio_contrast(ms, {f"lr|{k}": 1.0}, {crude: 1.0})
        orr, or_lo, or_hi = odds_ratio(df, design, exposure, blocks, outcome)
        rows.append(
            {
                "exposure": exposure.name,
                "outcome": outcome,
                "model": name,
                "blocks": k,
                "adj_rate_exposed": f.m_exposed,
                "adj_rate_reference": f.m_reference,
                "rr": np.exp(lr),
                "rr_low": np.exp(lr - t * se),
                "rr_high": np.exp(lr + t * se),
                "rd": rd,
                "rd_low": rd - t * rd_se,
                "rd_high": rd + t * rd_se,
                "share_logrr_retained": ret,
                "share_logrr_retained_low": ret - t * ret_se,
                "share_logrr_retained_high": ret + t * ret_se,
                "odds_ratio": orr,
                "odds_ratio_low": or_lo,
                "odds_ratio_high": or_hi,
                "log_or_minus_log_rr": np.log(orr) - lr,
            }
        )
    return pd.DataFrame(rows)


def behaviour_change_table(lattice: dict, ms: MarginSet, exposure: cf.Exposure, outcome: str):
    """Change in the exposure's log-RR when the other behaviour is added, for every subset of
    the remaining blocks: shows how the alcohol (or speeding) adjustment depends on what else
    is already in the model."""
    other = OTHER_BEHAVIOUR[exposure.name]
    t = ms.design.tcrit()
    rows = []
    for s in lattice:
        if other in s:
            continue
        a, b = cf.subset_key(s), cf.subset_key(s | {other})
        d, se = cf.linear_contrast(ms, {f"lr|{a}": 1.0, f"lr|{b}": -1.0})
        sh, sh_se = cf.ratio_contrast(ms, {f"lr|{a}": 1.0, f"lr|{b}": -1.0}, {"lr|crude": 1.0})
        rows.append(
            {
                "exposure": exposure.name,
                "outcome": outcome,
                "other_behaviour": other,
                "blocks_already_in": a,
                "n_blocks_already_in": len(s),
                "includes_configuration": "configuration" in s,
                "rr_before": np.exp(lattice[s].log_rr),
                "rr_after": np.exp(lattice[s | {other}].log_rr),
                "log_rr_reduction": d,
                "log_rr_reduction_low": d - t * se,
                "log_rr_reduction_high": d + t * se,
                "share_of_crude": sh,
                "share_of_crude_low": sh - t * sh_se,
                "share_of_crude_high": sh + t * sh_se,
            }
        )
    return pd.DataFrame(rows).sort_values(["n_blocks_already_in", "blocks_already_in"])


def run_lattices(
    df: pd.DataFrame, design: SurveyDesign, cache_dir: Path | None
) -> dict[str, pd.DataFrame]:
    out: dict[str, list[pd.DataFrame]] = {
        k: [] for k in ("sequential", "shapley", "lattice", "key_models", "behaviour_change")
    }
    fp = cf.data_fingerprint()
    for ex in EXPOSURES.values():
        for oc in OUTCOMES:
            lattice = cf.cached_lattice(df, design, ex, oc, cache_dir, fp)
            ms = cf.lattice_marginset(lattice, design)
            out["sequential"].append(cf.sequential_table(lattice, ms, ex, oc, orders(ex)))
            out["shapley"].append(cf.shapley_table(lattice, ms, ex, oc))
            out["shapley"].append(cf.shapley_table(lattice, ms, ex, oc, exclude=("configuration",)))
            out["lattice"].append(cf.lattice_table(lattice, ms, ex, oc))
            out["key_models"].append(key_model_table(lattice, ms, df, design, ex, oc))
            out["behaviour_change"].append(behaviour_change_table(lattice, ms, ex, oc))
            log.info("lattice %s/%s done", ex.name, oc)
    return {k: pd.concat(v, ignore_index=True) for k, v in out.items()}


# --------------------------------------------------------------------------------------
# Strata
# --------------------------------------------------------------------------------------
def strata_definitions(df: pd.DataFrame) -> dict[str, tuple[dict[str, np.ndarray], tuple]]:
    a_im = df["alcohol_im"].astype(str)
    a_pr = df["alcohol"].astype(str)
    sl = df["speed_limit"].astype(str)
    yr = df["YEAR"].to_numpy()
    nv = df["n_vehicles"].astype(str)
    return {
        "alcohol_imputed": (
            {"no alcohol": (a_im == "no").to_numpy(), "alcohol": (a_im == "yes").to_numpy()},
            ("alcohol",),
        ),
        "alcohol_police": (
            {
                "police: no alcohol": (a_pr == "no").to_numpy(),
                "police: alcohol": (a_pr == "yes").to_numpy(),
            },
            ("alcohol",),
        ),
        "night": (
            {
                "day (06-20)": (df[cf.NIGHT_COLUMN] == "day").to_numpy(),
                "night (21-05)": (df[cf.NIGHT_COLUMN] == "night").to_numpy(),
            },
            ("time", "light"),
        ),
        "vehicles": (
            {"single vehicle": (nv == "1").to_numpy(), "multi-vehicle": (nv != "1").to_numpy()},
            (),
        ),
        "speed_environment": (
            {
                "limit <= 45 mph": sl.isin(["<=25", "30-35", "40-45"]).to_numpy(),
                "limit >= 50 mph": sl.isin(["50-55", "60-65", "70+"]).to_numpy(),
            },
            (),
        ),
        "period": (
            {"2016-2019": yr <= 2019, "2020-2024": yr >= 2020},
            (),
        ),
        "hit_and_run": (
            {"hit-and-run excluded": (df["hit_and_run"] != 1).to_numpy()},
            (),
        ),
    }


def stratified_table(df: pd.DataFrame, design: SurveyDesign, outcome: str) -> pd.DataFrame:
    """Model-A-type adjusted RR of each speeding exposure within strata, and the ratio of RRs
    between the two strata of each split (design-based test of heterogeneity)."""
    cd = cf.cluster_design(design)
    t = cd.tcrit()
    rows = []
    for ex_name in ("exceeded", "speeding_any"):
        ex = EXPOSURES[ex_name]
        for split, (masks, drop) in strata_definitions(df).items():
            fits = {}
            for label, mask in masks.items():
                sub, sd = df.loc[mask].reset_index(drop=True), design.subset(mask)
                for c in sub.columns:
                    if isinstance(sub[c].dtype, pd.CategoricalDtype):
                        sub[c] = sub[c].cat.remove_unused_categories()
                blocks = [b for b in ex.blocks if b != "configuration" and b not in drop]
                exposed = sub[ex.column].astype(str) == ex.exposed
                if exposed.sum() < config.MIN_CELL_N or sub.loc[exposed, outcome].sum() < 10:
                    continue
                f = cf.fit_subset(sub, sd, ex, blocks, outcome)
                fits[label] = f
                ms = MarginSet({"lr": f.log_rr}, {"lr": f.t_log_rr}, cd)
                lr, se = cf.linear_contrast(ms, {"lr": 1.0})
                rows.append(
                    {
                        "exposure": ex_name,
                        "outcome": outcome,
                        "split": split,
                        "stratum": label,
                        "n_crashes": int(mask.sum()),
                        "n_exposed": int(exposed.sum()),
                        "n_exposed_events": int(sub.loc[exposed, outcome].sum()),
                        "adj_rate_exposed": f.m_exposed,
                        "adj_rate_reference": f.m_reference,
                        "rr": np.exp(lr),
                        "rr_low": np.exp(lr - t * se),
                        "rr_high": np.exp(lr + t * se),
                        "rd": f.m_exposed - f.m_reference,
                        "blocks": cf.subset_key(blocks),
                        "heterogeneity_ratio": np.nan,
                        "heterogeneity_ratio_low": np.nan,
                        "heterogeneity_ratio_high": np.nan,
                        "heterogeneity_p": np.nan,
                    }
                )
            if len(fits) == 2:
                fa_, fb = fits.values()
                ms = MarginSet(
                    {"a": fa_.log_rr, "b": fb.log_rr}, {"a": fa_.t_log_rr, "b": fb.t_log_rr}, cd
                )
                d, se = cf.linear_contrast(ms, {"b": 1.0, "a": -1.0})
                rows[-1].update(
                    heterogeneity_ratio=np.exp(d),
                    heterogeneity_ratio_low=np.exp(d - t * se),
                    heterogeneity_ratio_high=np.exp(d + t * se),
                    heterogeneity_p=float(2 * stats.t.sf(abs(d / se), cd.df)),
                )
        log.info("strata %s/%s done", ex_name, outcome)
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------------------
# Composition of speeding types
# --------------------------------------------------------------------------------------
TYPE_LEVELS = specs.CRASH_LEVELS["speeding_type"]


def type_composition(df: pd.DataFrame, design: SurveyDesign) -> pd.DataFrame:
    """Weighted distribution of the crash's speeding type within domains."""
    st = df["speeding_type"].astype(str)
    sl = df["speed_limit"].astype(str)
    ct = df["crash_type"].astype(str)
    sev = df["kabco"]
    domains: dict[str, dict[str, np.ndarray]] = {
        "all crashes": {"all": np.ones(len(df), bool)},
        "alcohol (imputed)": {
            v: (df["alcohol_im"].astype(str) == v).to_numpy() for v in ("no", "yes")
        },
        "alcohol (police)": {
            v: (df["alcohol"].astype(str) == v).to_numpy() for v in ("no", "yes", "unknown")
        },
        "drugs (police)": {
            v: (df["drugs"].astype(str) == v).to_numpy() for v in ("no", "yes", "unknown")
        },
        "speed limit": {
            "<=35": sl.isin(["<=25", "30-35"]).to_numpy(),
            "40-45": (sl == "40-45").to_numpy(),
            "50-55": (sl == "50-55").to_numpy(),
            "60+": sl.isin(["60-65", "70+"]).to_numpy(),
        },
        "crash type": {
            "single vehicle": ct.str.startswith("sv_").to_numpy(),
            "multi-vehicle": ct.str.startswith("mv_").to_numpy(),
            "pedestrian/cyclist": ct.isin(["pedestrian", "cyclist"]).to_numpy(),
        },
        "driver 15-20 involved": {
            v: (df["young_driver"].astype(str) == v).to_numpy() for v in ("no", "yes")
        },
        "time": {v: (df[cf.NIGHT_COLUMN].astype(str) == v).to_numpy() for v in ("day", "night")},
        "surface": {
            v: (df["surface"].astype(str) == v).to_numpy() for v in ("dry", "wet", "snow_ice")
        },
        "severity": {
            "O/C/B (no or minor injury)": sev.isin([0, 1, 2]).to_numpy(),
            "A (serious injury)": (sev == 3).to_numpy(),
            "K (fatal)": (sev == 4).to_numpy(),
        },
    }
    rows = []
    for dname, levels in domains.items():
        for lv, dom in levels.items():
            rec = {"domain": dname, "level": lv, "n": int(dom.sum())}
            for t_ in TYPE_LEVELS:
                e = svy_mean(design, (st == t_).to_numpy(float), dom)
                rec[f"share_{t_}"] = e.estimate
                lo, hi = logit_ci(e.estimate, e.se, e.df)
                rec[f"share_{t_}_low"], rec[f"share_{t_}_high"] = lo, hi
            sp = svy_mean(design, st.isin(TYPE_LEVELS[1:4]).to_numpy(float), dom)
            rec["share_any_speeding"] = sp.estimate
            ex_given = svy_mean(
                design,
                (st == "exceeded_limit_or_racing").to_numpy(float),
                dom & st.isin(TYPE_LEVELS[1:4]).to_numpy(),
            )
            rec["exceeded_share_of_speeding"] = ex_given.estimate
            rec["flag"] = "suppressed" if dom.sum() < config.MIN_CELL_N else ""
            rows.append(rec)
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------------------
# Recording and bias
# --------------------------------------------------------------------------------------
def fars_crss_recording(df: pd.DataFrame, design: SurveyDesign) -> pd.DataFrame:
    """Speeding share among fatal crashes in FARS (census) and CRSS (weighted), by alcohol.

    FARS alcohol: any driver with BAC >= .08 by NHTSA's multiple imputation (expected value
    over the 10 implicates); CRSS: imputed alcohol.  The two alcohol measures differ, so the
    comparison is of the *ratio* CRSS/FARS within each stratum: if recording were equally
    complete in both strata the ratios would agree.
    """
    fd = pl.read_parquet(
        config.PROCESSED_DIR / "fars_driver.parquet",
        columns=["YEAR", "case_id", *[f"drv_bac08_mi_{i}" for i in range(1, 11)]],
    )
    fc = pl.read_parquet(
        config.PROCESSED_DIR / "fars_crash.parquet", columns=["YEAR", "case_id", "speeding_type"]
    )
    # Crash-level any-driver BAC >= .08 per implicate, then averaged (expected indicator).
    imp = fd.group_by(["YEAR", "case_id"]).agg(
        [pl.col(f"drv_bac08_mi_{i}").max().alias(f"a{i}") for i in range(1, 11)]
    )
    f = fc.join(imp, on=["YEAR", "case_id"], how="left").to_pandas()
    p_alc = f[[f"a{i}" for i in range(1, 11)]].mean(axis=1).fillna(0.0).to_numpy()
    fst = f["speeding_type"].astype(str)
    st = df["speeding_type"].astype(str)
    fatal = (df["fatal"] == 1).to_numpy()
    rows = []
    for stratum, w_fars, dom in (
        ("no alcohol", 1 - p_alc, fatal & (df["alcohol_im"].astype(str) == "no").to_numpy()),
        ("alcohol", p_alc, fatal & (df["alcohol_im"].astype(str) == "yes").to_numpy()),
        ("all", np.ones(len(f)), fatal),
    ):
        for measure, levels in (
            ("any speeding", TYPE_LEVELS[1:4]),
            ("exceeded limit / racing", ["exceeded_limit_or_racing"]),
        ):
            fars_share = float(np.sum(w_fars * fst.isin(levels)) / np.sum(w_fars))
            e = svy_mean(design, st.isin(levels).to_numpy(float), dom)
            lo, hi = logit_ci(e.estimate, e.se, e.df)
            rows.append(
                {
                    "stratum": stratum,
                    "measure": measure,
                    "fars_share": fars_share,
                    "fars_expected_crashes": float(np.sum(w_fars)),
                    "crss_share": e.estimate,
                    "crss_share_low": lo,
                    "crss_share_high": hi,
                    "crss_n": int(dom.sum()),
                    "crss_over_fars": e.estimate / fars_share,
                    "crss_over_fars_low": lo / fars_share,
                    "crss_over_fars_high": hi / fars_share,
                }
            )
    return pd.DataFrame(rows)


SE_FATAL = (0.8, 0.9, 1.0)
SE_NONFATAL = (0.2, 0.3, 0.5, 0.7, 0.9, 1.0)


def stratified_qba(df: pd.DataFrame, design: SurveyDesign) -> pd.DataFrame:
    """Crude exceedance RR within alcohol strata corrected for outcome-dependent recording,
    allowing the non-fatal recording sensitivity to differ between alcohol strata (police may
    look for speed more when alcohol is involved)."""
    w = design.weight
    st = df["speeding_type"].astype(str)
    x = np.where(st == "exceeded_limit_or_racing", 1.0, np.where(st == "no", 0.0, np.nan))
    y = df["fatal"].to_numpy(float)
    rows = []
    for stratum in ("no", "yes"):
        s = (df["alcohol_im"].astype(str) == stratum).to_numpy() & ~np.isnan(x)
        a = w[s & (x == 1) & (y == 1)].sum()
        b = w[s & (x == 1) & (y == 0)].sum()
        c = w[s & (x == 0) & (y == 1)].sum()
        d = w[s & (x == 0) & (y == 0)].sum()
        obs = (a / (a + b)) / (c / (c + d))
        for se_f in SE_FATAL:
            for se_n in SE_NONFATAL:
                rr = corrected_rr(a, b, c, d, se_f, se_n)
                rows.append(
                    {
                        "alcohol_stratum": stratum,
                        "se_fatal": se_f,
                        "se_nonfatal": se_n,
                        "rr_observed": obs,
                        "rr_corrected": rr,
                    }
                )
    return pd.DataFrame(rows)


def e_value(rr: float) -> float:
    """VanderWeele-Ding E-value of a risk ratio (protective RRs are inverted)."""
    if not np.isfinite(rr) or rr <= 0:
        return np.nan
    r = rr if rr >= 1 else 1 / rr
    return float(r + np.sqrt(r * (r - 1)))


def e_values(key_models_: pd.DataFrame, strata: pd.DataFrame) -> pd.DataFrame:
    rows = []
    src = [
        (r.exposure, r.outcome, f"model: {r.model}", r.rr, r.rr_low, r.rr_high)
        for r in key_models_.itertuples()
    ] + [
        (r.exposure, r.outcome, f"stratum: {r.stratum}", r.rr, r.rr_low, r.rr_high)
        for r in strata.itertuples()
    ]
    for ex, oc, spec, rr, lo, hi in src:
        near = lo if rr >= 1 else hi
        crosses = lo <= 1 <= hi
        rows.append(
            {
                "exposure": ex,
                "outcome": oc,
                "specification": spec,
                "rr": rr,
                "e_value_point": e_value(rr),
                "e_value_ci": 1.0 if crosses else e_value(near),
            }
        )
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------------------
# Selection by fatality (collider demonstration)
# --------------------------------------------------------------------------------------
def _svy_or(design: SurveyDesign, x: np.ndarray, z: np.ndarray, dom: np.ndarray) -> dict:
    """Design-based crude odds ratio of x on z within a domain (saturated survey logit)."""
    keep = dom & ~np.isnan(x) & ~np.isnan(z)
    d = pd.DataFrame({"z": np.where(z == 1, "yes", "no")})
    spec = ModelSpec(categorical={"z": ["no", "yes"]})
    sub = d.loc[keep].reset_index(drop=True)
    m = SurveyLogit(spec).fit(sub, x[keep], design.subset(keep))
    r = m.coef_table().set_index("term").loc["z[yes]"]
    return {
        "or": r["odds_ratio"],
        "or_low": r["or_low"],
        "or_high": r["or_high"],
        "n": int(keep.sum()),
    }


def selection_by_fatality(df: pd.DataFrame, design: SurveyDesign) -> pd.DataFrame:
    """Speeding-alcohol odds ratio among all, non-fatal and fatal CRSS crashes, and in FARS.

    Conditioning on a fatal outcome (as FARS-only statistics do) selects on a consequence of
    both factors, which distorts their association (collider stratification)."""
    st = df["speeding_type"].astype(str)
    alc = df["alcohol_im"].astype(str).map({"yes": 1.0, "no": 0.0}).to_numpy(float)
    rows = []
    for measure, x in (
        (
            "any speeding",
            np.where(st.isin(TYPE_LEVELS[1:4]), 1.0, np.where(st == "no", 0.0, np.nan)),
        ),
        (
            "exceeded limit / racing",
            np.where(st == "exceeded_limit_or_racing", 1.0, np.where(st == "no", 0.0, np.nan)),
        ),
    ):
        for pop, dom in (
            ("CRSS all crashes", np.ones(len(df), bool)),
            ("CRSS non-fatal crashes", (df["fatal"] == 0).to_numpy()),
            ("CRSS fatal crashes", (df["fatal"] == 1).to_numpy()),
        ):
            rows.append({"measure": measure, "population": pop, **_svy_or(design, x, alc, dom)})
    # FARS: alcohol by implicate (any driver BAC >= .08), odds ratio per implicate.
    fd = pl.read_parquet(
        config.PROCESSED_DIR / "fars_driver.parquet",
        columns=["YEAR", "case_id", *[f"drv_bac08_mi_{i}" for i in range(1, 11)]],
    )
    imp = fd.group_by(["YEAR", "case_id"]).agg(
        [pl.col(f"drv_bac08_mi_{i}").max().fill_null(0).alias(f"a{i}") for i in range(1, 11)]
    )
    fc = (
        pl.read_parquet(
            config.PROCESSED_DIR / "fars_crash.parquet",
            columns=["YEAR", "case_id", "speeding_type"],
        )
        .join(imp, on=["YEAR", "case_id"], how="left")
        .to_pandas()
    )
    fst = fc["speeding_type"].astype(str)
    for measure, levels in (
        ("any speeding", TYPE_LEVELS[1:4]),
        ("exceeded limit / racing", ["exceeded_limit_or_racing"]),
    ):
        known = fst.isin([*levels, "no"])
        x = fst[known].isin(levels).to_numpy()
        lors = []
        for i in range(1, 11):
            z = fc.loc[known, f"a{i}"].fillna(0).to_numpy() == 1
            a, b = np.sum(x & z), np.sum(~x & z)
            c, d = np.sum(x & ~z), np.sum(~x & ~z)
            lors.append(np.log(a * d / (b * c)))
        rows.append(
            {
                "measure": measure,
                "population": "FARS fatal crashes (census; alcohol by multiple imputation)",
                "or": float(np.exp(np.mean(lors))),
                "or_low": float(np.exp(min(lors))),
                "or_high": float(np.exp(max(lors))),
                "n": int(known.sum()),
            }
        )
    out = pd.DataFrame(rows)
    out["interval"] = np.where(
        out["population"].str.startswith("FARS"),
        "range over 10 implicates",
        "95% CI (design-based)",
    )
    return out


# --------------------------------------------------------------------------------------
def _save(
    tab: pd.DataFrame,
    name: str,
    description: str,
    method: str,
    unit: str = "crash",
    outcome: str = "fatal; ka",
) -> None:
    save_table(
        tab,
        MODULE,
        name,
        description=description,
        population=POP,
        unit=unit,
        outcome=outcome,
        method=method,
        inputs=INPUT,
    )


def run(cache_dir: Path | None = config.OUTPUT_DIR / "cache") -> dict[str, pd.DataFrame]:
    cf.check_leakage()
    df, design = load_frame()
    out = run_lattices(df, design, cache_dir)
    lat_method = (
        "Survey logistic models for every subset of 7 covariate blocks (exact cell compression); "
        "standardised RR/RD over all crashes by g-computation; joint Taylor linearisation on the "
        "25-stratum/67-PSU design (t, 42 df); Shapley shares exact over all orderings"
    )
    _save(
        out["lattice"],
        "lattice",
        "Standardised RR of each exposure for every block subset",
        lat_method,
    )
    _save(
        out["sequential"],
        "sequential",
        "Sequential adjustment along four block orderings",
        lat_method,
    )
    _save(
        out["shapley"],
        "shapley",
        "Shapley shares of the crude log-RR, with and without the configuration block",
        lat_method,
    )
    _save(
        out["key_models"],
        "key_models",
        "Crude, other-behaviour-only, environment, and full models: RR, RD and OR (non-collapsibility)",
        lat_method,
    )
    _save(
        out["behaviour_change"],
        "behaviour_change",
        "Change in the exposure log-RR when the other behaviour is added, for every set of blocks already in the model",
        lat_method,
    )
    strata = pd.concat([stratified_table(df, design, oc) for oc in OUTCOMES], ignore_index=True)
    _save(
        strata,
        "strata",
        "Adjusted RR of speeding exposures within strata, with design-based heterogeneity tests (ratio of the two strata RRs)",
        "Model A blocks minus the blocks that define the stratum, fitted within stratum; standardised over stratum crashes",
    )
    out["strata"] = strata
    comp = type_composition(df, design)
    _save(
        comp,
        "type_composition",
        "Distribution of police-recorded speeding types within domains (weighted)",
        "Weighted domain proportions, logit CIs",
        outcome="",
    )
    out["type_composition"] = comp
    rec = fars_crss_recording(df, design)
    _save(
        rec,
        "fars_crss_recording",
        "Speeding recorded among fatal crashes: FARS census vs CRSS, by alcohol",
        "FARS: alcohol as expected share over 10 BAC implicates; CRSS: imputed alcohol, weighted domain proportions",
        outcome="fatal",
    )
    out["fars_crss_recording"] = rec
    qba = stratified_qba(df, design)
    _save(
        qba,
        "stratified_qba",
        "Crude exceedance RR within alcohol strata corrected for outcome-dependent recording sensitivity",
        "Matrix-method correction (measurement.corrected_rr), specificity 1",
        outcome="fatal",
    )
    out["stratified_qba"] = qba
    ev = e_values(out["key_models"], strata)
    _save(
        ev,
        "e_values",
        "E-values of adjusted speeding and alcohol RRs",
        "E = RR + sqrt(RR(RR-1)) (VanderWeele & Ding); CI limit nearest 1",
    )
    out["e_values"] = ev
    sel = selection_by_fatality(df, design)
    _save(
        sel,
        "selection_by_fatality",
        "Speeding-alcohol association among all, non-fatal and fatal crashes (CRSS) and FARS",
        "Crude survey-weighted odds ratios; FARS by implicate",
        outcome="",
    )
    out["selection_by_fatality"] = sel
    return out


def reproduce_phase1(df: pd.DataFrame, design: SurveyDesign) -> float:
    """Exceedance RR with the model-A block set (should equal severity/fatal_speeding_type)."""
    ex = EXPOSURES["exceeded"]
    return float(np.exp(cf.fit_subset(df, design, ex, [*ENV_BLOCKS, "alcohol"], "fatal").log_rr))


__all__: Sequence[str] = ("EXPOSURES", "load_frame", "run")
