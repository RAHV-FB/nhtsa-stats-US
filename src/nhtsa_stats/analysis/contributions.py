"""What does "contribution" mean, and is any ranking of factors stable?  (Phase 2, Q6, Q8;
docs/research_plan_phase2.md §5.4.)

The same factor can be "important" in different, non-equivalent senses.  This module computes
them side by side, for the same factors, and never combines them into one score:

1. **Association** -- crude and adjusted standardised risk ratios / differences along a fixed
   sequence of nested models (same sample at every step), with conditional odds ratios from
   the same fits to expose non-collapsibility.
2. **Predictive information** -- temporal split (train 2016-2021, test 2023-2024): design-
   weighted test log-likelihood gain over an intercept-only model (McFadden R^2) and AUROC;
   leave-one-block-out ablation, exact Shapley allocation of the test R^2 over factor blocks,
   and permutation importance.  PSU bootstrap of the test set for uncertainty.
3. **Statistical attribution of burden** -- severity-pathway attributable fractions for single
   factors and their combination, the overlap (sum of single AFs minus the joint AF) and an exact
   Shapley allocation of the joint AF, all jointly linearised.
4. **Counts** -- FARS deaths in crashes involving each factor, their overlaps, and the
   over-count produced by adding factor-specific totals.
5. **Rank stability** -- for each metric, the rank of each factor and, where a joint sampling
   distribution is available, the probability of each rank.

Units are kept apart: crash-level factors (speeding, alcohol, police-reported drugs) are not
ranked against occupant-level restraint on the same scale; restraint is reported from its own
occupant-level model.
"""

from __future__ import annotations

import itertools
import logging
import math
from collections.abc import Sequence

import numpy as np
import pandas as pd
import polars as pl
from sklearn.metrics import roc_auc_score

from nhtsa_stats import config
from nhtsa_stats.analysis import multifactor
from nhtsa_stats.analysis.confounding import collapse_cells
from nhtsa_stats.analysis.survey import MarginSet, ModelSpec, SurveyDesign, SurveyLogit
from nhtsa_stats.reporting.io import save_table

log = logging.getLogger(__name__)
MODULE = "contributions"
INPUT = [
    "data/processed/crss_crash.parquet",
    "data/processed/fars_driver.parquet",
    "data/processed/fars_person.parquet",
]
CRASH_POP = "CRSS police-reported crashes 2016-2024 with known imputed severity"
RIDGE = 0.01
SEED = config.RANDOM_SEED

ENVIRONMENT = [
    "YEAR",
    "region",
    "urbanicity",
    "tod",
    "weekend",
    "light",
    "weather",
    "surface",
    "speed_limit",
    "interstate",
    "junction",
    "work_zone",
]
MIX = ["young_driver", "older_driver", "any_motorcycle", "any_heavy_truck"]
CONFIG = ["crash_type", "n_vehicles"]

# Crash-level factors: column, exposed level, reference level, label.
FACTORS = {
    "exceeded": ("exceeded", "yes", "no", "Driver exceeded the limit / racing"),
    "speeding_other": (
        "exceeded",
        "other_speeding",
        "no",
        "Other speeding types (too fast for conditions, unspecified)",
    ),
    "alcohol": ("alcohol_im", "yes", "no", "Alcohol involved (imputed)"),
    "drugs_police": (
        "drugs",
        "yes",
        "no",
        "Drugs (police-reported; incomplete, selectively recorded)",
    ),
}
# Police-reported drugs enter as their own step: they are co-recorded with alcohol by the police
# (drugs/co_occurrence), so adjusting alcohol or speeding for them mixes a measurement artefact
# into the adjustment.  The ranking uses the step before it.
NESTED_STEPS = {
    "crude": [],
    "environment": ENVIRONMENT,
    "+ other speeding/alcohol": [*ENVIRONMENT, "<behaviours>"],
    "+ driver/vehicle mix": [*ENVIRONMENT, "<behaviours>", *MIX],
    "+ police-reported drugs": [*ENVIRONMENT, "<behaviours>", *MIX, "drugs"],
    "+ crash configuration": [*ENVIRONMENT, "<behaviours>", *MIX, "drugs", *CONFIG],
}
BEHAVIOUR_COLS = ["exceeded", "alcohol_im"]


# --------------------------------------------------------------------------------------
# Model fitting on compressed cells, margins for several factors from one fit
# --------------------------------------------------------------------------------------
def fit_cells(
    df: pd.DataFrame, design: SurveyDesign, covs: Sequence[str], outcome: str
) -> tuple[SurveyLogit, pd.DataFrame, SurveyDesign]:
    covs = list(dict.fromkeys(covs))
    work = df[[*covs, outcome]].copy()
    for c in covs:
        work[c] = np.asarray(work[c], dtype=object)
    cells, cd = collapse_cells(work, design, covs, outcome)
    cats = {}
    for c in covs:
        ref = (
            next((v[2] for v in FACTORS.values() if v[0] == c), None)
            or pd.Series(work[c]).value_counts().index[0]
        )
        vals = sorted((v for v in pd.unique(work[c]) if v != ref), key=str)
        cats[c] = [ref, *vals]
    m = SurveyLogit(ModelSpec(categorical=cats), ridge=RIDGE * len(cells) / len(work))
    m.fit(cells, cells[outcome].to_numpy(float), cd)
    return m, cells, cd


def factor_margins(m: SurveyLogit, cells: pd.DataFrame, names: Sequence[str]) -> MarginSet:
    scen = {}
    for n in names:
        col, exp, ref, _ = FACTORS[n]
        scen[f"{n}|1"] = lambda d, c=col, v=exp: d.assign(**{c: v})
        scen[f"{n}|0"] = lambda d, c=col, v=ref: d.assign(**{c: v})
    return m.margins(cells, scen)


def _ci(est: float, se: float, t: float, exp: bool = False) -> tuple[float, float, float]:
    if exp:
        return float(np.exp(est)), float(np.exp(est - t * se)), float(np.exp(est + t * se))
    return est, est - t * se, est + t * se


def nested_models(df: pd.DataFrame, design: SurveyDesign) -> pd.DataFrame:
    rows = []
    t = design.tcrit()
    for name, (col, exp, _ref, label) in FACTORS.items():
        for step, covs in NESTED_STEPS.items():
            cc = []
            for c in covs:
                if c == "<behaviours>":
                    cc += [b for b in BEHAVIOUR_COLS if b != col]
                elif c != col:
                    cc.append(c)
            m, cells, _ = fit_cells(df, design, [col, *cc], "fatal")
            ms = factor_margins(m, cells, [name])
            lr = ms.log_ratio(f"{name}|1", f"{name}|0")
            rd = ms.difference(f"{name}|1", f"{name}|0")
            tab = m.coef_table().set_index("term").loc[f"{col}[{exp}]"]
            rr = _ci(lr.estimate, lr.se, t, exp=True)
            d = _ci(rd.estimate, rd.se, t)
            rows.append(
                {
                    "factor": name,
                    "label": label,
                    "step": step,
                    "covariates": ",".join(cc),
                    "rr": rr[0],
                    "rr_low": rr[1],
                    "rr_high": rr[2],
                    "rd": d[0],
                    "rd_low": d[1],
                    "rd_high": d[2],
                    "odds_ratio": tab["odds_ratio"],
                    "odds_ratio_low": tab["or_low"],
                    "odds_ratio_high": tab["or_high"],
                    "n": len(df),
                }
            )
        log.info("nested %s done", name)
    out = pd.DataFrame(rows)
    crude = out[out.step == "crude"].set_index("factor")["rr"]
    out["share_logrr_retained"] = np.log(out["rr"]) / np.log(out["factor"].map(crude))
    out["log_or_minus_log_rr"] = np.log(out["odds_ratio"]) - np.log(out["rr"])
    return out


# --------------------------------------------------------------------------------------
# Predictive contribution
# --------------------------------------------------------------------------------------
PRED_BLOCKS: dict[str, list[str]] = {
    "speeding_type": ["exceeded"],
    "alcohol": ["alcohol_im"],
    "drugs_police": ["drugs"],
    "environment": ENVIRONMENT[1:],  # calendar year excluded from prediction (temporal split)
    "driver_vehicle_mix": MIX,
    "configuration": CONFIG,
}


def _wll(y: np.ndarray, p: np.ndarray, w: np.ndarray) -> float:
    p = np.clip(p, 1e-12, 1 - 1e-12)
    return float(np.sum(w * (y * np.log(p) + (1 - y) * np.log(1 - p))) / np.sum(w))


def _r2(y, p, w, p0) -> float:
    return 1 - _wll(y, p, w) / _wll(y, np.full_like(p, p0), w)


def predictive(
    df: pd.DataFrame, design: SurveyDesign, n_boot: int = 200
) -> dict[str, pd.DataFrame]:
    years = df["YEAR"].astype(int).to_numpy()
    tr = np.isin(years, config.TRAIN_YEARS)
    te = np.isin(years, config.TEST_YEARS)
    dtr, dte = df.loc[tr].reset_index(drop=True), df.loc[te].reset_index(drop=True)
    sdtr = design.subset(tr)
    y, w = dte["fatal"].to_numpy(float), design.weight[te]
    p0 = float(np.average(dtr["fatal"], weights=sdtr.weight))
    blocks = list(PRED_BLOCKS)
    preds: dict[frozenset, np.ndarray] = {}
    for r in range(len(blocks) + 1):
        for s in itertools.combinations(blocks, r):
            covs = [c for b in s for c in PRED_BLOCKS[b]]
            if not covs:
                preds[frozenset()] = np.full(len(dte), p0)
                continue
            m, _, _ = fit_cells(dtr, sdtr, covs, "fatal")
            # Levels unseen in training would raise; none expected (same harmonised codes).
            preds[frozenset(s)] = m.predict(dte)
        log.info("predictive: %d-block subsets done", r)
    full = frozenset(blocks)

    def metrics(idx: np.ndarray) -> dict[frozenset, tuple[float, float]]:
        out = {}
        for s, p in preds.items():
            r2 = _r2(y[idx], p[idx], w[idx], p0)
            auc = roc_auc_score(y[idx], p[idx], sample_weight=w[idx]) if s else 0.5
            out[s] = (r2, auc)
        return out

    def shapley(vals: dict[frozenset, float]) -> dict[str, float]:
        n = len(blocks)
        phi = {}
        for j in blocks:
            tot = 0.0
            others = [b for b in blocks if b != j]
            for r in range(n):
                wgt = math.factorial(r) * math.factorial(n - r - 1) / math.factorial(n)
                for s in itertools.combinations(others, r):
                    s0 = frozenset(s)
                    tot += wgt * (vals[s0 | {j}] - vals[s0])
            phi[j] = tot
        return phi

    base_idx = np.arange(len(dte))
    base = metrics(base_idx)
    r2 = {s: v[0] for s, v in base.items()}
    auc = {s: v[1] for s, v in base.items()}
    sh_r2 = shapley(r2)
    # PSU bootstrap (within strata) of the test set: predictions fixed, metrics recomputed.
    rng = np.random.default_rng(SEED)
    sdte = design.subset(te)
    psu = sdte.cluster
    strata = sdte.cluster_stratum
    clusters_by_stratum = {h: np.unique(psu[strata[psu] == h]) for h in np.unique(strata[psu])}
    rows_by_cluster = pd.Series(np.arange(len(psu))).groupby(psu).apply(np.asarray).to_dict()
    boot = {k: [] for k in ("sh_" + b for b in blocks)}
    boot.update({f"abl_{b}": [] for b in blocks})
    boot.update({f"single_{b}": [] for b in blocks})
    boot["full_r2"] = []
    for _ in range(n_boot):
        idx = []
        for _h, cl in clusters_by_stratum.items():
            for c in rng.choice(cl, size=len(cl), replace=True):
                idx.append(rows_by_cluster[c])
        idx = np.concatenate(idx)
        r2b = {s: _r2(y[idx], p[idx], w[idx], p0) for s, p in preds.items()}
        shb = shapley(r2b)
        for b in blocks:
            boot["sh_" + b].append(shb[b])
            boot["abl_" + b].append(r2b[full] - r2b[full - {b}])
            boot["single_" + b].append(r2b[frozenset({b})])
        boot["full_r2"].append(r2b[full])
    rows = []
    for b in blocks:

        def ci(key: str) -> tuple[float, float]:
            v = np.asarray(boot[key])
            return float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))

        rows.append(
            {
                "block": b,
                "variables": ",".join(PRED_BLOCKS[b]),
                "r2_alone": r2[frozenset({b})],
                "r2_alone_low": ci("single_" + b)[0],
                "r2_alone_high": ci("single_" + b)[1],
                "auc_alone": auc[frozenset({b})],
                "r2_drop_when_removed": r2[full] - r2[full - {b}],
                "r2_drop_when_removed_low": ci("abl_" + b)[0],
                "r2_drop_when_removed_high": ci("abl_" + b)[1],
                "auc_drop_when_removed": auc[full] - auc[full - {b}],
                "shapley_r2": sh_r2[b],
                "shapley_r2_low": ci("sh_" + b)[0],
                "shapley_r2_high": ci("sh_" + b)[1],
                "shapley_share": sh_r2[b] / r2[full],
                "full_r2": r2[full],
                "full_auc": auc[full],
            }
        )
    tab = pd.DataFrame(rows)
    # Permutation importance (test set; block columns permuted jointly).
    m_full, _, _ = fit_cells(dtr, sdtr, [c for b in blocks for c in PRED_BLOCKS[b]], "fatal")
    base_ll = _wll(y, preds[full], w)
    perm = []
    for b in blocks:
        incs = []
        for rep in range(5):
            r = np.random.default_rng(SEED + rep).permutation(len(dte))
            d2 = dte.copy()
            for c in PRED_BLOCKS[b]:
                d2[c] = dte[c].to_numpy()[r]
            incs.append(base_ll - _wll(y, m_full.predict(d2), w))
        perm.append(
            {
                "block": b,
                "logloss_increase": float(np.mean(incs)),
                "logloss_increase_sd": float(np.std(incs)),
            }
        )
    tab = tab.merge(pd.DataFrame(perm), on="block")
    lattice = pd.DataFrame(
        [
            {
                "blocks": "+".join(sorted(s)) or "intercept",
                "n_blocks": len(s),
                "test_r2": r2[s],
                "test_auc": auc[s],
            }
            for s in preds
        ]
    ).sort_values(["n_blocks", "blocks"])
    return {"predictive": tab, "predictive_lattice": lattice}


# --------------------------------------------------------------------------------------
# Attributable burden with overlap and Shapley allocation
# --------------------------------------------------------------------------------------
PLAYER_SETS = {
    "speeding_alcohol": {
        "speeding": [("exceeded", ("yes", "other_speeding"), "no")],
        "alcohol": [("alcohol_im", ("yes",), "no")],
    },
    "exceeded_other_alcohol": {
        "exceeded": [("exceeded", ("yes",), "no")],
        "speeding_other": [("exceeded", ("other_speeding",), "no")],
        "alcohol": [("alcohol_im", ("yes",), "no")],
    },
}


def _af(key: str, m: dict) -> float:
    return 1 - m[key] / m["obs"] if key else 0.0


def _key(names: Sequence[str], members: Sequence[str]) -> str:
    """Canonical scenario key of a set of players (in ``names`` order)."""
    return "+".join(x for x in names if x in members)


def _setter(players: dict, members: Sequence[str]):
    def setter(d: pd.DataFrame) -> pd.DataFrame:
        d = d.copy()
        for p_ in members:
            for col, exp, ref in players[p_]:
                vals = np.asarray(d[col], dtype=object)
                d[col] = np.where(np.isin(vals, exp), ref, vals)
        return d

    return setter


def _shapley_af(names: Sequence[str], j: str):
    """Exact Shapley value of player j for the joint AF, as a function of the margins."""
    n = len(names)
    others = [x for x in names if x != j]
    terms = []
    for r in range(n):
        wgt = math.factorial(r) * math.factorial(n - r - 1) / math.factorial(n)
        for s in itertools.combinations(others, r):
            terms.append((wgt, _key(names, (*s, j)), _key(names, s)))

    def phi(m: dict) -> float:
        return sum(w * (_af(a, m) - _af(b, m)) for w, a, b in terms)

    return phi


def _burden_set(m, cells, cd, set_name: str, players: dict, deaths: float) -> list[dict]:
    names = list(players)
    scen = {"obs": None}
    for r in range(1, len(names) + 1):
        for s in itertools.combinations(names, r):
            scen[_key(names, s)] = _setter(players, s)
    ms = m.margins(cells, scen)
    t = cd.tcrit()
    allk = _key(names, names)
    quantities: list[tuple[str, object, str]] = []
    for r in range(1, len(names) + 1):
        for s in itertools.combinations(names, r):
            k = _key(names, s)
            quantities.append((f"AF[{k}]", lambda m_, k=k: _af(k, m_), "attributable fraction"))
    quantities.append(
        (
            "sum of single-factor AFs",
            lambda m_: sum(_af(x, m_) for x in names),
            "attributable fraction (sum; double counts)",
        )
    )
    quantities.append(
        (
            "overlap = sum of singles - joint",
            lambda m_: sum(_af(x, m_) for x in names) - _af(allk, m_),
            "attributable fraction (overlap)",
        )
    )
    for j in names:
        phi = _shapley_af(names, j)
        quantities.append((f"Shapley[{j}]", phi, "Shapley allocation of the joint AF"))
        quantities.append(
            (f"Shapley share[{j}]", lambda m_, phi=phi: phi(m_) / _af(allk, m_), "share")
        )
    rows = []
    for label, f, kind in quantities:
        e = ms.contrast(f)
        v, lo, hi = _ci(e.estimate, e.se, t)
        rows.append(
            {
                "player_set": set_name,
                "quantity": label,
                "kind": kind,
                "estimate": v,
                "estimate_low": lo,
                "estimate_high": hi,
                "fars_deaths_per_year": v * deaths if kind != "share" else np.nan,
            }
        )
    return rows


def burden(df: pd.DataFrame, design: SurveyDesign, fars_deaths_per_year: float) -> pd.DataFrame:
    """AF(S) = 1 - M_S / M_obs, where M_S sets the exposed crashes of every player in S to the
    reference; Shapley allocation of AF(all players).  Model: environment + behaviours + mix
    (model-A equivalent with speeding type; police-reported drugs are not adjusted for)."""
    covs = [*ENVIRONMENT, "exceeded", "alcohol_im", *MIX]
    m, cells, cd = fit_cells(df, design, covs, "fatal")
    rows = []
    for set_name, players in PLAYER_SETS.items():
        rows += _burden_set(m, cells, cd, set_name, players, fars_deaths_per_year)
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------------------
# FARS overlap of official-style counts
# --------------------------------------------------------------------------------------
def fars_overlap() -> pd.DataFrame:
    """Deaths by combination of crash speeding, any-driver BAC >= .08 (per MI implicate,
    averaged), any-driver drug positivity (among determinate crashes) and the dead person's
    own restraint (unbelted light-vehicle occupant)."""
    drv = pl.read_parquet(
        config.PROCESSED_DIR / "fars_driver.parquet",
        columns=["YEAR", "case_id", "drv_drug_any", *[f"drv_bac08_mi_{i}" for i in range(1, 11)]],
    )
    crash = drv.group_by(["YEAR", "case_id"]).agg(
        *[pl.col(f"drv_bac08_mi_{i}").max().fill_null(0).alias(f"a{i}") for i in range(1, 11)],
        pl.when((pl.col("drv_drug_any") == 1).any())
        .then(pl.lit("yes"))
        .when(pl.col("drv_drug_any").null_count() == 0)
        .then(pl.lit("no"))
        .otherwise(pl.lit("undetermined"))
        .alias("drug"),
    )
    per = pl.read_parquet(
        config.PROCESSED_DIR / "fars_person.parquet",
        columns=["YEAR", "case_id", "killed", "restraint", "body", "PER_TYP", "speeding"],
    ).filter(pl.col("killed") == 1)
    per = per.join(crash, on=["YEAR", "case_id"], how="left").to_pandas()
    per["S"] = (per["speeding"] == 1).astype(int)
    per["U"] = ((per["restraint"] == "none") & per["PER_TYP"].isin([1, 2, 9])).astype(int)
    per["drug"] = per["drug"].fillna("undetermined")
    total = len(per)
    rows = []
    for (s, u, d), g in per.groupby(["S", "U", "drug"]):
        a_exp = g[[f"a{i}" for i in range(1, 11)]].fillna(0).mean(axis=1)
        for a_state in (1, 0):
            cnt = float((a_exp if a_state else 1 - a_exp).sum())
            rows.append(
                {
                    "speeding": s,
                    "alcohol_bac08": a_state,
                    "drugs": d,
                    "unbelted_victim": u,
                    "deaths": cnt,
                }
            )
    combos = pd.DataFrame(rows)
    combos["share_of_deaths"] = combos["deaths"] / total
    combos["n_factors"] = (
        combos["speeding"]
        + combos["alcohol_bac08"]
        + (combos["drugs"] == "yes")
        + combos["unbelted_victim"]
    )
    combos["years"] = "2016-2024"
    return combos, total


def overlap_summary(combos: pd.DataFrame, total: int) -> pd.DataFrame:
    def cnt(mask) -> float:
        return float(combos.loc[mask, "deaths"].sum())

    f = {
        "speeding-related crash": combos["speeding"] == 1,
        "driver BAC >= .08 (MI)": combos["alcohol_bac08"] == 1,
        "driver drug-positive (determinate crashes only)": combos["drugs"] == "yes",
        "victim an unbelted vehicle occupant": combos["unbelted_victim"] == 1,
    }
    rows = []
    any_mask = np.zeros(len(combos), bool)
    for k, m in f.items():
        c = cnt(m)
        alone = cnt(m & (combos["n_factors"] == 1))
        rows.append(
            {
                "factor": k,
                "deaths": c,
                "share_of_all_deaths": c / total,
                "deaths_with_no_other_listed_factor": alone,
                "share_also_involving_another_factor": 1 - alone / c,
            }
        )
        any_mask |= m.to_numpy()
    s = sum(r["deaths"] for r in rows)
    union = cnt(any_mask)
    rows.append(
        {"factor": "sum of the four factor counts", "deaths": s, "share_of_all_deaths": s / total}
    )
    rows.append(
        {
            "factor": "deaths involving at least one factor (union)",
            "deaths": union,
            "share_of_all_deaths": union / total,
        }
    )
    rows.append(
        {
            "factor": "deaths involving none of the four",
            "deaths": total - union,
            "share_of_all_deaths": 1 - union / total,
        }
    )
    rows.append({"factor": "all deaths", "deaths": float(total), "share_of_all_deaths": 1.0})
    out = pd.DataFrame(rows)
    out["overcount_ratio_sum_over_union"] = s / union
    out["deaths_undetermined_drug_status"] = cnt(combos["drugs"] == "undetermined")
    return out


def pairwise_overlap(combos: pd.DataFrame, total: int) -> pd.DataFrame:
    defs = {
        "speeding": combos["speeding"] == 1,
        "alcohol": combos["alcohol_bac08"] == 1,
        "drugs": combos["drugs"] == "yes",
        "unbelted victim": combos["unbelted_victim"] == 1,
    }
    rows = []
    for a, b in itertools.combinations(defs, 2):
        ma, mb = defs[a], defs[b]
        both = float(combos.loc[ma & mb, "deaths"].sum())
        na, nb = float(combos.loc[ma, "deaths"].sum()), float(combos.loc[mb, "deaths"].sum())
        rows.append(
            {
                "pair": f"{a} & {b}",
                "deaths_both": both,
                "share_of_a_also_b": both / na,
                "share_of_b_also_a": both / nb,
                "observed_over_expected": (both / total) / ((na / total) * (nb / total)),
            }
        )
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------------------
# Ranking
# --------------------------------------------------------------------------------------
# Police-reported drugs are not ranked: their severity association is not identified
# (drugs/crss_bounds).
RANK_FACTORS = ["exceeded", "speeding_other", "alcohol"]


def _contrast_influence(ms: MarginSet, f) -> np.ndarray:
    """Per-row linearised influence of a smooth function of margins (as MarginSet.contrast)."""
    g = {}
    for k, val in ms.values.items():
        h = 6e-6 * max(abs(val), 1e-12)
        up, dn = dict(ms.values), dict(ms.values)
        up[k], dn[k] = val + h, val - h
        g[k] = (f(up) - f(dn)) / (2 * h)
    return sum(g[k] * ms.influence[k] for k in ms.values)


def _log_rr(name: str):
    return lambda m: float(np.log(m[f"{name}|1"] / m[f"{name}|0"]))


def _rd(name: str):
    return lambda m: m[f"{name}|1"] - m[f"{name}|0"]


def rank_probabilities(
    df: pd.DataFrame, design: SurveyDesign, n_draws: int = 20000
) -> pd.DataFrame:
    """Adjusted log-RRs and RDs of all crash-level factors from one model (the '+ driver/vehicle
    mix' step), jointly linearised; Monte-Carlo rank probabilities from their joint normal
    approximation."""
    covs = [*ENVIRONMENT, "exceeded", "alcohol_im", *MIX]
    m, cells, cd = fit_cells(df, design, covs, "fatal")
    ms = factor_margins(m, cells, RANK_FACTORS)
    rows = []
    rng = np.random.default_rng(SEED)
    for metric, make in (("adjusted RR", _log_rr), ("adjusted RD", _rd)):
        fns = [make(n) for n in RANK_FACTORS]
        ests = np.array([f(ms.values) for f in fns])
        z = np.column_stack([_contrast_influence(ms, f) for f in fns])
        vc = cd.vcov_total(z)
        draws = rng.multivariate_normal(ests, vc, size=n_draws)
        ranks = (-draws).argsort(axis=1).argsort(axis=1) + 1
        for i, n in enumerate(RANK_FACTORS):
            est = float(np.exp(ests[i])) if metric == "adjusted RR" else float(ests[i])
            rec = {
                "metric": metric,
                "factor": n,
                "estimate": est,
                "se_link": float(np.sqrt(vc[i, i])),
            }
            for r in range(1, len(RANK_FACTORS) + 1):
                rec[f"p_rank_{r}"] = float(np.mean(ranks[:, i] == r))
            rows.append(rec)
    out = pd.DataFrame(rows)
    out["rank_point"] = out.groupby("metric")["estimate"].rank(ascending=False).astype(int)
    return out


def ranking_table(
    nested: pd.DataFrame,
    pred: pd.DataFrame,
    burden_tab: pd.DataFrame,
    overlap: pd.DataFrame,
    prev: pd.DataFrame,
    restraint: pd.DataFrame | None,
) -> pd.DataFrame:
    """Each factor's value and rank on each quantity; no combined score."""
    adj = nested[nested.step == "+ driver/vehicle mix"].set_index("factor")
    crude = nested[nested.step == "crude"].set_index("factor")
    b = burden_tab[burden_tab.player_set == "exceeded_other_alcohol"].set_index("quantity")
    pmap = {
        "exceeded": "speeding_type",
        "speeding_other": "speeding_type",
        "alcohol": "alcohol",
        "drugs_police": "drugs_police",
    }
    pr = pred.set_index("block")
    ov = overlap.set_index("factor")
    fc = pl.read_parquet(
        config.PROCESSED_DIR / "fars_crash.parquet", columns=["speeding_type", "FATALS"]
    )
    fars_speed = (
        fc.group_by("speeding_type")
        .agg(pl.col("FATALS").sum())
        .to_pandas()
        .set_index("speeding_type")["FATALS"]
        .to_dict()
    )
    undetermined = ov["deaths_undetermined_drug_status"].iloc[0] / ov.loc["all deaths", "deaths"]
    rows = []
    notes = {
        "exceeded": "predictive value is that of the whole speeding-type block",
        "speeding_other": "shares the speeding-type predictive block with 'exceeded'",
        "alcohol": "",
        "drugs_police": "NOT RANKED: severity association not identified (drugs/crss_bounds); "
        f"FARS count is a lower bound ({undetermined:.0%} of deaths in crashes with undetermined drug "
        "status)",
    }
    for f in [*RANK_FACTORS, "drugs_police"]:
        rows.append(
            {
                "factor": f,
                "unit": "crash",
                "rankable": f in RANK_FACTORS,
                "note": notes[f],
                "prevalence_all_crashes": prev.loc[f, "prev_all"],
                "prevalence_fatal_crashes": prev.loc[f, "prev_fatal"],
                "crude_rr": crude.loc[f, "rr"],
                "adjusted_rr": adj.loc[f, "rr"],
                "adjusted_rd": adj.loc[f, "rd"],
                "shapley_test_r2_of_block": pr.loc[pmap[f], "shapley_r2"]
                if f != "speeding_other"
                else np.nan,
                "shapley_share_joint_af": b.loc[f"Shapley[{f}]", "estimate"]
                if f"Shapley[{f}]" in b.index
                else np.nan,
                "fars_deaths_in_crashes_with_factor": {
                    "exceeded": fars_speed.get("exceeded_limit_or_racing", np.nan),
                    "speeding_other": fars_speed.get("too_fast_for_conditions", 0.0)
                    + fars_speed.get("speeding_unspecified", 0.0),
                    "alcohol": ov.loc["driver BAC >= .08 (MI)", "deaths"],
                    "drugs_police": ov.loc[
                        "driver drug-positive (determinate crashes only)", "deaths"
                    ],
                }[f],
            }
        )
    if restraint is not None:
        r = restraint
        rows.append(
            {
                "factor": "unbelted (occupant)",
                "unit": "occupant",
                "rankable": False,
                "note": "occupant-level quantity; not comparable with crash-level factors",
                "crude_rr": r.loc[r.step == "crude", "rr"].iloc[0],
                "adjusted_rr": r.loc[r.step == "+ driver's own speeding and alcohol", "rr"].iloc[0],
                "adjusted_rd": r.loc[r.step == "+ driver's own speeding and alcohol", "rd"].iloc[0],
                "fars_deaths_in_crashes_with_factor": ov.loc[
                    "victim an unbelted vehicle occupant", "deaths"
                ],
            }
        )
    out = pd.DataFrame(rows)
    crash = out["rankable"].astype(bool)
    for c in (
        "prevalence_fatal_crashes",
        "crude_rr",
        "adjusted_rr",
        "adjusted_rd",
        "shapley_test_r2_of_block",
        "shapley_share_joint_af",
        "fars_deaths_in_crashes_with_factor",
    ):
        out[f"rank_{c}"] = out.loc[crash, c].rank(ascending=False)
    return out


def prevalence(df: pd.DataFrame, design: SurveyDesign) -> pd.DataFrame:
    rows = []
    w = design.weight
    fat = (df["fatal"] == 1).to_numpy()
    for n, (col, exp, _, _) in FACTORS.items():
        x = (df[col].astype(str) == exp).to_numpy()
        rows.append(
            {
                "factor": n,
                "prev_all": float(np.sum(w * x) / np.sum(w)),
                "prev_fatal": float(np.sum(w * x * fat) / np.sum(w * fat)),
            }
        )
    return pd.DataFrame(rows).set_index("factor")


# --------------------------------------------------------------------------------------
def run(n_boot: int = 200) -> dict[str, pd.DataFrame]:
    df, design = multifactor.crash_frame()
    out = {}
    out["nested"] = nested_models(df, design)
    save_table(
        out["nested"],
        MODULE,
        "nested_models",
        description="Crude and adjusted standardised RR, RD and conditional OR of each crash-level factor along a fixed sequence of nested models",
        population=CRASH_POP,
        unit="crash",
        outcome="fatal",
        method="Survey logistic models on a fixed sample; standardised margins; Taylor linearisation (42 df)",
        inputs=INPUT,
    )
    pred = predictive(df, design, n_boot)
    out.update(pred)
    save_table(
        pred["predictive"],
        MODULE,
        "predictive",
        description="Predictive information of factor blocks: test R2 alone, drop when removed, exact Shapley allocation of the full-model test R2, permutation importance",
        population="CRSS crashes; train 2016-2021, test 2023-2024",
        unit="crash",
        outcome="fatal",
        method=f"Survey logistic models fitted on training years; design-weighted McFadden R2 and AUROC on test years; PSU-within-stratum bootstrap of the test set ({n_boot} replicates)",
        inputs=INPUT,
    )
    save_table(
        pred["predictive_lattice"],
        MODULE,
        "predictive_lattice",
        description="Test R2 and AUROC of every block subset",
        population="CRSS crashes; train 2016-2021, test 2023-2024",
        unit="crash",
        outcome="fatal",
        method="as predictive",
        inputs=INPUT,
    )
    fars_deaths = (
        float(
            pl.read_parquet(config.PROCESSED_DIR / "fars_crash.parquet", columns=["YEAR", "FATALS"])
            .filter(pl.col("YEAR") >= 2022)["FATALS"]
            .sum()
        )
        / 3
    )
    out["burden"] = burden(df, design, fars_deaths)
    save_table(
        out["burden"],
        MODULE,
        "burden_shapley",
        description="Severity-pathway attributable fractions: single, joint, overlap and exact Shapley allocation of the joint AF",
        population=CRASH_POP,
        unit="crash",
        outcome="fatal",
        method="g-computation from one survey logistic model (environment + speeding type + alcohol + police drugs + mix); joint Taylor linearisation; FARS-scaled deaths = AF x mean FARS deaths 2022-2024",
        inputs=INPUT,
        extra={"fars_deaths_per_year_2022_2024": fars_deaths},
    )
    combos, total = fars_overlap()
    out["fars_overlap_combinations"] = combos
    save_table(
        combos,
        MODULE,
        "fars_overlap_combinations",
        description="FARS deaths by combination of crash speeding, any-driver BAC >= .08 (expected over 10 implicates), any-driver drug positivity and the victim's restraint",
        population="FARS deaths 2016-2024",
        unit="person killed",
        outcome="",
        method="Census counts; alcohol as expected counts over multiple-imputation implicates",
        inputs=INPUT,
    )
    out["fars_overlap_summary"] = overlap_summary(combos, total)
    save_table(
        out["fars_overlap_summary"],
        MODULE,
        "fars_overlap_summary",
        description="Deaths counted under each factor, the sum of factor counts and the union",
        population="FARS deaths 2016-2024",
        unit="person killed",
        method="Census counts",
        inputs=INPUT,
    )
    out["fars_pairwise_overlap"] = pairwise_overlap(combos, total)
    save_table(
        out["fars_pairwise_overlap"],
        MODULE,
        "fars_pairwise_overlap",
        description="Pairwise overlap of factor-specific death counts",
        population="FARS deaths 2016-2024",
        unit="person killed",
        method="Census counts",
        inputs=INPUT,
    )
    out["rank_probabilities"] = rank_probabilities(df, design)
    save_table(
        out["rank_probabilities"],
        MODULE,
        "rank_probabilities",
        description="Probability of each rank of crash-level factors on adjusted RR and adjusted RD",
        population=CRASH_POP,
        unit="crash",
        outcome="fatal",
        method="Joint Taylor linearisation of all factor contrasts from one model; 20,000 multivariate-normal draws",
        inputs=INPUT,
    )
    try:
        from nhtsa_stats.reporting.io import load_table

        restraint = load_table("restraint_behaviour", "crss_unbelted_nested")
    except FileNotFoundError:
        restraint = None
    out["ranking"] = ranking_table(
        out["nested"],
        pred["predictive"],
        out["burden"],
        out["fars_overlap_summary"],
        prevalence(df, design),
        restraint,
    )
    save_table(
        out["ranking"],
        MODULE,
        "ranking",
        description="Each factor's value and rank on separate quantities (no combined score); restraint is occupant-level and not ranked against crash-level factors",
        population=CRASH_POP,
        unit="factor",
        outcome="fatal",
        method="Assembled from nested_models, predictive, burden_shapley, fars_overlap_summary and restraint_behaviour/crss_unbelted_nested",
        inputs=INPUT,
    )
    return out
