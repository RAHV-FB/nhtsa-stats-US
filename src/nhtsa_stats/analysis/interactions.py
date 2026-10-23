"""Factor co-occurrence and statistical interaction in crash severity (RQ2).

Question: does the excess fatality risk associated with one circumstance depend on the
presence of another?  Co-occurrence (two factors appearing together) is *not* evidence of
interaction; interaction is assessed with adjusted risks for the four (or eight) exposure
combinations.

Population / unit / outcome: CRSS police-reported crashes 2016-2024 with known maximum
severity; crash; ``fatal`` (K) and ``ka`` (K or A).

Method, for each pre-specified pair (A, B) -- defined on *groups of levels* (e.g. speed limit
50+ mph vs below 50):

1. Co-occurrence: weighted prevalence of A, B and A∧B among all crashes and among fatal
   crashes; observed/expected ratio P(A∧B)/(P(A)P(B)); design-based odds ratio of association.
2. Interaction: survey-weighted logistic model with the full adjustment set (model A or B of
   the severity module) plus one product term 1[A]·1[B].  Standardised margins for the four
   cells (each group margin is the mixture of level-specific margins weighted by the level
   distribution within the group) give adjusted risks p00, p10, p01, p11, from which
   - the risk ratio and risk difference of A within B=0 and B=1,
   - the additive interaction contrast IC = p11 - p10 - p01 + p00 and RERI,
   - the multiplicative interaction on the risk-ratio scale, RR11/(RR10*RR01),
   - the product-term odds-ratio interaction with a design-adjusted Wald F test,
   all with linearised 95% CIs.  Holm and Benjamini-Hochberg adjustments are applied across
   the pre-specified pairs, separately for the additive and multiplicative scales.
3. Stability: the same estimates for 2016-2019 and 2020-2024 separately, and for KA.
4. Three-factor combinations for a few scientifically motivated triples, with a minimum
   support of 20 fatal crashes in the fully exposed cell.

Interpretation: interaction here is statistical (non-additivity / non-multiplicativity of
adjusted risks *given a reported crash*).  It does not establish causal synergy, and
behavioural factors are subject to severity-dependent ascertainment (see the measurement
module).
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy import stats

from nhtsa_stats import config
from nhtsa_stats.analysis import severity, specs
from nhtsa_stats.analysis.survey import (
    MarginSet,
    ModelSpec,
    SurveyDesign,
    SurveyLogit,
    interaction_contrasts,
    svy_mean,
    svy_total,
)
from nhtsa_stats.processing import harmonize as h
from nhtsa_stats.reporting.io import save_table

log = logging.getLogger(__name__)
MODULE = "interactions"
MIN_TRIPLE_EVENTS = 20


@dataclass(frozen=True)
class Exposure:
    var: str
    exposed: tuple
    reference: tuple
    label: str

    def state(self, s: int) -> tuple:
        return self.exposed if s == 1 else self.reference


@dataclass(frozen=True)
class Combination:
    name: str
    exposures: tuple[Exposure, ...]
    covariates: str = "A"  # A = PRE_CRASH, B = PRE_CRASH + configuration
    rationale: str = ""
    extra_covariates: tuple[str, ...] = field(default=())
    prespecified: bool = True
    # Standardisation population for the margins (None = all crashes). Pairs whose exposure
    # is a multi-vehicle crash type are standardised over multi-vehicle crashes only, because
    # setting a single-vehicle crash to 'angle collision' is not a possible crash.
    domain: str | None = None


DOMAINS = {"multi_vehicle": lambda d: (d["n_vehicles"] != "1").to_numpy()}


SPEEDING = Exposure("speeding", ("yes",), ("no",), "speeding-related")
ALCOHOL = Exposure("alcohol_im", ("yes",), ("no",), "alcohol-involved (imputed)")
DARK_UNLIT = Exposure("light", ("dark_not_lighted",), ("daylight",), "dark, unlit (vs daylight)")
WET = Exposure("surface", ("wet",), ("dry",), "wet surface (vs dry)")
MOTORCYCLE = Exposure("any_motorcycle", ("yes",), ("no",), "motorcycle involved")
HEAVY = Exposure("any_heavy_truck", ("yes",), ("no",), "medium/heavy truck or bus involved")
YOUNG = Exposure("young_driver", ("yes",), ("no",), "driver 15-20 involved")
OLDER = Exposure("older_driver", ("yes",), ("no",), "driver 65+ involved")
HIGH_SPEED = Exposure(
    "speed_limit", ("50-55", "60-65", "70+"), ("<=25", "30-35", "40-45"), "speed limit 50+ mph"
)
LATE_NIGHT = Exposure("tod", ("00-05",), ("10-15",), "00:00-05:59 (vs 10:00-15:59)")
WEEKEND = Exposure("weekend", ("yes",), ("no",), "weekend")
RURAL = Exposure("urbanicity", ("rural",), ("urban",), "rural area (CRSS PSU urbanicity)")
PEDESTRIAN = Exposure(
    "crash_type",
    ("pedestrian",),
    (
        "mv_angle",
        "mv_rear_end",
        "mv_sideswipe",
        "mv_head_on",
        "mv_other",
        "sv_on_roadway",
        "sv_off_roadway",
        "sv_rollover_first",
        "cyclist",
    ),
    "pedestrian crash (vs all other types)",
)
ANGLE = Exposure("crash_type", ("mv_angle",), ("mv_rear_end",), "angle (vs rear-end) collision")

PAIRS: list[Combination] = [
    Combination(
        "speeding x dark_unlit",
        (SPEEDING, DARK_UNLIT),
        "A",
        "Speed reduces available reaction distance; darkness reduces detection distance.",
    ),
    Combination(
        "speeding x wet",
        (SPEEDING, WET),
        "A",
        "'Too fast for conditions' on wet roads may occur at lower absolute speeds.",
    ),
    Combination(
        "speeding x alcohol", (SPEEDING, ALCOHOL), "A", "Common co-occurring risk behaviours."
    ),
    Combination(
        "alcohol x dark_unlit",
        (ALCOHOL, DARK_UNLIT),
        "A",
        "Impaired perception compounded by darkness.",
    ),
    Combination(
        "speeding x high_speed_road",
        (SPEEDING, HIGH_SPEED),
        "A",
        "Kinetic energy rises with the square of speed; speeding on fast roads adds more energy. "
        "Added at implementation, not in the registered plan: exploratory.",
        prespecified=False,
    ),
    Combination(
        "high_speed_road x dark_unlit", (HIGH_SPEED, DARK_UNLIT), "A", "Unlit high-speed roads."
    ),
    Combination(
        "motorcycle x speeding", (MOTORCYCLE, SPEEDING), "A", "Unprotected riders at higher speeds."
    ),
    Combination(
        "motorcycle x alcohol", (MOTORCYCLE, ALCOHOL), "A", "Balance/control demands of riding."
    ),
    Combination("young_driver x late_night", (YOUNG, LATE_NIGHT), "A", "Inexperience at night."),
    Combination(
        "older_driver x angle",
        (OLDER, ANGLE),
        "B",
        "Frailty in side impacts; older drivers over-involved in angle crashes.",
        domain="multi_vehicle",
    ),
    Combination(
        "heavy_truck x high_speed_road", (HEAVY, HIGH_SPEED), "A", "Mass incompatibility at speed."
    ),
    Combination("rural x dark_unlit", (RURAL, DARK_UNLIT), "A", "Rural lighting and EMS distance."),
    Combination(
        "weekend x late_night", (WEEKEND, LATE_NIGHT), "A", "Weekend night-time travel patterns."
    ),
    Combination(
        "pedestrian x dark_unlit", (PEDESTRIAN, DARK_UNLIT), "B", "Pedestrian conspicuity at night."
    ),
    Combination(
        "pedestrian x high_speed_road",
        (PEDESTRIAN, HIGH_SPEED),
        "B",
        "Impact speed and pedestrian survival. Added at implementation, not in the registered "
        "plan: exploratory.",
        prespecified=False,
    ),
]

EXCEEDED = Exposure(
    "speeding_type",
    ("exceeded_limit_or_racing",),
    ("no",),
    "exceeded limit / racing (vs not speeding)",
)
# Follow-up pairs added AFTER the speeding-type analysis showed that "speeding-related" mixes a
# strong association (exceeding the limit) with none ("too fast for conditions").  Exploratory:
# excluded from the multiplicity family of the pre-specified pairs.
FOLLOW_UP: list[Combination] = [
    Combination(
        "exceeded_limit x wet",
        (EXCEEDED, WET),
        "A",
        "Does the wet-road deficit persist for limit exceedance?",
        prespecified=False,
    ),
    Combination(
        "exceeded_limit x dark_unlit",
        (EXCEEDED, DARK_UNLIT),
        "A",
        "Limit exceedance in darkness.",
        prespecified=False,
    ),
    Combination(
        "exceeded_limit x high_speed_road",
        (EXCEEDED, HIGH_SPEED),
        "A",
        "Limit exceedance on 50+ mph roads.",
        prespecified=False,
    ),
]

TRIPLES: list[Combination] = [
    Combination("speeding x alcohol x dark_unlit", (SPEEDING, ALCOHOL, DARK_UNLIT), "A"),
    Combination("motorcycle x speeding x alcohol", (MOTORCYCLE, SPEEDING, ALCOHOL), "A"),
    Combination("speeding x high_speed_road x dark_unlit", (SPEEDING, HIGH_SPEED, DARK_UNLIT), "A"),
]


# --------------------------------------------------------------------------------------
def _covariates(comb: Combination) -> list[str]:
    base = list(specs.PRE_CRASH) + (list(specs.CIRCUMSTANCE) if comb.covariates == "B" else [])
    if any(e.var == "speeding_type" for e in comb.exposures):
        base = ["speeding_type" if c == "speeding" else c for c in base]
    for e in comb.exposures:
        if e.var not in base:
            base.append(e.var)
    return base


def _indicator(df: pd.DataFrame, e: Exposure) -> np.ndarray:
    """1 exposed / 0 reference / NaN neither (e.g. unknown or other levels)."""
    out = np.full(len(df), np.nan)
    out[df[e.var].isin(e.exposed).to_numpy()] = 1.0
    out[df[e.var].isin(e.reference).to_numpy()] = 0.0
    return out


def _level_weights(df: pd.DataFrame, w: np.ndarray, e: Exposure, s: int) -> dict:
    levels = e.state(s)
    tot = {lv: float(w[(df[e.var] == lv).to_numpy()].sum()) for lv in levels}
    z = sum(tot.values())
    return {lv: t / z for lv, t in tot.items() if t > 0}


def combo_margins(
    model: SurveyLogit, df: pd.DataFrame, design: SurveyDesign, comb: Combination
) -> MarginSet:
    """Margins for every exposed/reference state combination as level mixtures."""
    k = len(comb.exposures)
    states = [tuple((i >> j) & 1 for j in range(k)) for i in range(2**k)]
    dom = None if comb.domain is None else DOMAINS[comb.domain](df)
    wdom = design.weight if dom is None else np.where(dom, design.weight, 0.0)
    weights = [{s: _level_weights(df, wdom, e, s) for s in (0, 1)} for e in comb.exposures]
    values, influence = {}, {}
    cache: dict[tuple, tuple[float, np.ndarray]] = {}
    for st in states:
        name = "p" + "".join(str(s) for s in st)
        # all level combinations within this state
        combos: list[tuple[dict, float]] = [({}, 1.0)]
        for e, s, wmap in zip(comb.exposures, st, weights, strict=True):
            combos = [({**a, e.var: lv}, pw * wl) for a, pw in combos for lv, wl in wmap[s].items()]
        m_tot, z_tot = 0.0, np.zeros(design.n)
        for assign, pw in combos:
            key = tuple(sorted(assign.items()))
            if key not in cache:
                cache[key] = model.margin_influence(df, lambda d, a=assign: d.assign(**a), dom)
            m, z = cache[key]
            m_tot += pw * m
            z_tot += pw * z
        values[name], influence[name] = m_tot, z_tot
    return MarginSet(values, influence, design)


def _fit(
    df: pd.DataFrame,
    design: SurveyDesign,
    outcome: str,
    comb: Combination,
    full_product: bool = True,
) -> tuple[SurveyLogit, str]:
    covs = _covariates(comb)
    h.assert_no_leakage(covs, allow_year=True)
    exps = comb.exposures
    products = []
    if len(exps) == 2:
        products = [((exps[0].var, list(exps[0].exposed)), (exps[1].var, list(exps[1].exposed)))]
    else:
        for i in range(len(exps)):
            for j in range(i + 1, len(exps)):
                products.append(
                    ((exps[i].var, list(exps[i].exposed)), (exps[j].var, list(exps[j].exposed)))
                )
        if full_product:
            products.append(tuple((e.var, list(e.exposed)) for e in exps))
    spec = ModelSpec(
        categorical={c: severity.observed_levels(df, c) for c in covs}, products=products
    )
    model = SurveyLogit(spec, ridge=severity.RIDGE).fit(df, df[outcome].to_numpy(), design)
    term = spec.design_matrix(df.iloc[:1])[1][-1]
    return model, term


def cooccurrence(
    df: pd.DataFrame, design: SurveyDesign, outcome: str, a: Exposure, b: Exposure
) -> dict:
    ia, ib = _indicator(df, a), _indicator(df, b)
    known = np.isfinite(ia) & np.isfinite(ib)
    fat = df[outcome].to_numpy(float) == 1
    out = {}
    for tag, dom in (("all", known), ("fatal", known & fat)):
        pa = svy_mean(design, np.nan_to_num(ia), dom).estimate
        pb = svy_mean(design, np.nan_to_num(ib), dom).estimate
        pab = svy_mean(design, np.nan_to_num(ia * ib), dom).estimate
        out[f"prev_A_{tag}"] = pa
        out[f"prev_B_{tag}"] = pb
        out[f"prev_AB_{tag}"] = pab
        out[f"obs_exp_{tag}"] = pab / (pa * pb) if pa * pb > 0 else np.nan
    # Odds ratio of association between A and B among all crashes (design-based).
    sub = known
    tmp = pd.DataFrame({"a": np.where(ia == 1, "yes", "no")})
    m = SurveyLogit(ModelSpec(categorical={"a": ["no", "yes"]})).fit(
        tmp[sub].reset_index(drop=True), np.nan_to_num(ib)[sub], design.subset(sub)
    )
    row = m.coef_table().iloc[1]
    out.update(assoc_or=row.odds_ratio, assoc_or_low=row.or_low, assoc_or_high=row.or_high)
    return out


def cells(
    df: pd.DataFrame, design: SurveyDesign, outcome: str, comb: Combination, n_years: int
) -> list[dict]:
    inds = [_indicator(df, e) for e in comb.exposures]
    y = df[outcome].to_numpy(float)
    rows = []
    k = len(inds)
    for i in range(2**k):
        st = tuple((i >> j) & 1 for j in range(k))
        dom = np.ones(len(df), dtype=bool)
        for ind, s in zip(inds, st, strict=True):
            dom &= ind == s
        rate = svy_mean(design, y, dom)
        rows.append(
            {
                "cell": "p" + "".join(map(str, st)),
                "n": int(dom.sum()),
                "n_events": int(y[dom].sum()),
                "crashes_per_year": svy_total(design, np.ones(design.n), dom).estimate / n_years,
                "crude_rate": rate.estimate,
            }
        )
    return rows


def _est_row(prefix: str, est, log_scale: bool = False) -> dict:
    lo, hi = est.ci()
    if log_scale:
        return {
            prefix: float(np.exp(est.estimate)),
            f"{prefix}_low": float(np.exp(lo)),
            f"{prefix}_high": float(np.exp(hi)),
        }
    t = est.estimate / est.se if est.se > 0 else np.nan
    p = float(2 * stats.t.sf(abs(t), est.df)) if np.isfinite(t) else np.nan
    return {prefix: est.estimate, f"{prefix}_low": lo, f"{prefix}_high": hi, f"{prefix}_p": p}


def analyse_pair(
    df: pd.DataFrame, design: SurveyDesign, outcome: str, comb: Combination, n_years: int
) -> dict:
    a, b = comb.exposures
    model, term = _fit(df, design, outcome, comb)
    ms = combo_margins(model, df, design, comb)
    ic = interaction_contrasts(ms, "p11", "p10", "p01", "p00")
    wald = model.wald_test([term])
    coef = model.coef_table().set_index("term").loc[term]
    rec = {
        "pair": comb.name,
        "prespecified": comb.prespecified,
        "A": a.label,
        "B": b.label,
        "covariate_set": comb.covariates,
        "outcome": outcome,
        "rationale": comb.rationale,
    }
    for c in ("p00", "p10", "p01", "p11"):
        rec.update(_est_row(f"adj_{c}", ms.estimate(c)))
    rec.update(_est_row("rr_A_given_B0", ms.log_ratio("p10", "p00"), log_scale=True))
    rec.update(_est_row("rr_A_given_B1", ms.log_ratio("p11", "p01"), log_scale=True))
    rec.update(_est_row("rd_A_given_B0", ms.difference("p10", "p00")))
    rec.update(_est_row("rd_A_given_B1", ms.difference("p11", "p01")))
    rec.update(_est_row("rr_11_vs_00", ms.log_ratio("p11", "p00"), log_scale=True))
    rec.update(_est_row("ic", ic["ic"]))
    rec.update(_est_row("reri", ic["reri"]))
    rec.update(_est_row("ratio_of_rr", ic["log_ratio_of_rr"], log_scale=True))
    # p-value of the multiplicative (risk-ratio scale) interaction
    lr = ic["log_ratio_of_rr"]
    rec["ratio_of_rr_p"] = (
        float(2 * stats.t.sf(abs(lr.estimate / lr.se), lr.df)) if lr.se > 0 else np.nan
    )
    rec.update(
        product_or=coef.odds_ratio,
        product_or_low=coef.or_low,
        product_or_high=coef.or_high,
        product_wald_F=wald["F"],
        product_p=wald["p"],
    )
    for crec in cells(df, design, outcome, comb, n_years):
        c = crec.pop("cell")
        rec.update({f"{c}_{k}": v for k, v in crec.items()})
    rec.update(cooccurrence(df, design, outcome, a, b))
    rec["min_cell_events"] = min(rec[f"{c}_n_events"] for c in ("p00", "p10", "p01", "p11"))
    rec["flag"] = "low_support" if rec["min_cell_events"] < MIN_TRIPLE_EVENTS else ""
    return rec


def analyse_triple(
    df: pd.DataFrame, design: SurveyDesign, outcome: str, comb: Combination, n_years: int
) -> dict:
    cell_rows = cells(df, design, outcome, comb, n_years)
    full = next(c for c in cell_rows if c["cell"] == "p111")
    rec = {
        "combination": comb.name,
        "outcome": outcome,
        "covariate_set": comb.covariates,
        "labels": " | ".join(e.label for e in comb.exposures),
        "p111_n_events": full["n_events"],
    }
    if full["n_events"] < MIN_TRIPLE_EVENTS:
        rec["flag"] = f"insufficient support (<{MIN_TRIPLE_EVENTS} events in fully exposed cell)"
        return rec
    model, term = _fit(df, design, outcome, comb)
    ms = combo_margins(model, df, design, comb)
    for c in sorted(ms.values):
        rec.update(_est_row(f"adj_{c}", ms.estimate(c)))
        if c != "p000":
            rec.update(_est_row(f"rr_{c}", ms.log_ratio(c, "p000"), log_scale=True))
    # Three-way additive interaction contrast.
    ic3 = ms.contrast(
        lambda m: (
            m["p111"]
            - m["p110"]
            - m["p101"]
            - m["p011"]
            + m["p100"]
            + m["p010"]
            + m["p001"]
            - m["p000"]
        )
    )
    rec.update(_est_row("ic3", ic3))
    # Excess of the triple over the sum of single-factor excesses (additive joint-effect check).
    exc = ms.contrast(
        lambda m: (
            (m["p111"] - m["p000"])
            - ((m["p100"] - m["p000"]) + (m["p010"] - m["p000"]) + (m["p001"] - m["p000"]))
        )
    )
    rec.update(_est_row("excess_over_additive_singles", exc))
    wald = model.wald_test([term])
    rec.update(three_way_product_p=wald["p"])
    for crec in cell_rows:
        c = crec.pop("cell")
        rec.update({f"{c}_{k}": v for k, v in crec.items()})
    rec["flag"] = ""
    return rec


def _adjust_p(p: pd.Series, method: str) -> pd.Series:
    vals = p.to_numpy(float)
    ok = np.isfinite(vals)
    out = np.full(len(vals), np.nan)
    v = vals[ok]
    m = len(v)
    order = np.argsort(v)
    adj = np.empty(m)
    if method == "holm":
        running = 0.0
        for rank, idx in enumerate(order):
            running = max(running, min(1.0, (m - rank) * v[idx]))
            adj[idx] = running
    else:  # Benjamini-Hochberg
        running = 1.0
        for rank in range(m - 1, -1, -1):
            idx = order[rank]
            running = min(running, v[idx] * m / (rank + 1))
            adj[idx] = min(running, 1.0)
    out[ok] = adj
    return pd.Series(out, index=p.index)


def run_pairs(
    outcome: str,
    years: Sequence[int] | None = None,
    tag: str = "all",
    include_follow_up: bool = True,
) -> pd.DataFrame:
    df, design = severity.load(outcome, years)
    n_years = df["YEAR"].nunique()
    rows = []
    for comb in PAIRS:
        try:
            rows.append({**analyse_pair(df, design, outcome, comb, n_years), "period": tag})
            log.info("%s %s %s done", outcome, tag, comb.name)
        except Exception as exc:  # keep going; record the failure explicitly
            log.exception("pair %s failed", comb.name)
            rows.append(
                {"pair": comb.name, "outcome": outcome, "period": tag, "flag": f"failed: {exc}"}
            )
    for comb in FOLLOW_UP if include_follow_up else []:
        try:
            rows.append({**analyse_pair(df, design, outcome, comb, n_years), "period": tag})
            log.info("%s %s %s done", outcome, tag, comb.name)
        except Exception as exc:  # keep going; record the failure explicitly
            log.exception("pair %s failed", comb.name)
            rows.append(
                {"pair": comb.name, "outcome": outcome, "period": tag, "flag": f"failed: {exc}"}
            )
    res = pd.DataFrame(rows)
    pre = res["prespecified"].fillna(True).astype(bool)
    for col in ("ic_p", "ratio_of_rr_p", "product_p"):
        if col in res:
            # Multiplicity adjustment within the pre-specified family only.
            res[f"{col}_holm"] = np.nan
            res[f"{col}_bh"] = np.nan
            res.loc[pre, f"{col}_holm"] = _adjust_p(res.loc[pre, col], "holm")
            res.loc[pre, f"{col}_bh"] = _adjust_p(res.loc[pre, col], "bh")
    return res


def run(outcomes: Sequence[str] = ("fatal", "ka")) -> dict[str, pd.DataFrame]:
    out: dict[str, pd.DataFrame] = {}
    common = dict(
        population="CRSS police-reported crashes with known maximum severity",
        unit="crash",
        inputs=["data/processed/crss_crash.parquet"],
        method="Survey logistic model (severity module covariate set A or B) + one product term per pair; "
        "standardised margins as level mixtures; IC, RERI, ratio of RRs with Taylor-linearised CIs (t, 42 df); "
        "Holm/BH across pre-specified pairs",
    )
    for oc in outcomes:
        res = run_pairs(oc)
        save_table(
            res,
            MODULE,
            f"pairs_{oc}",
            description=f"Pre-specified two-factor interactions, outcome {oc}, 2016-2024",
            outcome=oc,
            **common,
        )
        out[f"pairs_{oc}"] = res
    # Period stability for the primary outcome.
    early = run_pairs("fatal", years=[y for y in config.YEARS if y <= 2019], tag="2016-2019")
    late = run_pairs("fatal", years=[y for y in config.YEARS if y >= 2020], tag="2020-2024")
    stab = pd.concat([early, late], ignore_index=True)
    save_table(
        stab,
        MODULE,
        "pairs_fatal_by_period",
        description="Interaction estimates by period (stability check)",
        outcome="fatal",
        **common,
    )
    out["pairs_fatal_by_period"] = stab
    # Three-factor combinations.
    df, design = severity.load("fatal")
    n_years = df["YEAR"].nunique()
    triples = pd.DataFrame([analyse_triple(df, design, "fatal", c, n_years) for c in TRIPLES])
    save_table(
        triples,
        MODULE,
        "triples_fatal",
        description="Pre-specified three-factor combinations (fatal)",
        outcome="fatal",
        **common,
    )
    out["triples_fatal"] = triples
    return out
