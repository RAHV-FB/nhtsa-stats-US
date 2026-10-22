"""Person-level risk given crash involvement (CRSS, design-based) -- RQ6(a).

Research question
    Among people in police-reported crashes, who is killed (K) or killed-or-seriously
    injured (KA)?  How strongly are restraint use, age, sex, seating role, vehicle type,
    vehicle age and the type of the other vehicle (two-vehicle crashes) associated with the
    outcome, before and after adjustment for crash circumstances, and do the associations
    of restraint and sex vary with age and crash type?

Populations (CRSS 2016-2024, occupants of in-transport vehicles, PER_TYP 1/2/9, known outcome)
    * ``lpv`` -- occupants of light passenger vehicles (car, SUV, pickup, van, other light
      truck) with a recorded age of 8 years or more, where belt codes are meaningful.  Seat
      belt (restraint) analyses use only this population.  Restraint "not_applicable"
      (harmonised: seat outside belted rows 1-4 or unknown seat, e.g. cargo areas) is kept
      as its own level, distinct from "unknown".
    * ``motorcycle`` -- motorcycle operators and passengers (helmet instead of restraint;
      the CRSS ``restraint`` field is not comparable for riders across years: helmet codes
      moved from REST_USE to HELM_USE in 2019).
Unit
    Person (each person carries the crash's sampling weight; variance by Taylor
    linearisation over the CRSS design -- 25 strata, 67 PSUs, 42 df).  Persons are clustered
    within crashes within PSUs; the PSU-level ultimate-cluster variance already accounts for
    that dependence.
Outcomes
    ``killed`` (INJ_SEV 4 vs 0-3) and ``killed_or_serious`` (3-4 vs 0-2); severity unknown
    (5, 6, 9) excluded, as in ``data.crss_person``.
Method
    * Crude weighted rates and crude risk ratios (saturated survey logistic model).
    * Survey-weighted logistic models; standardised predictive margins (g-computation over
      the population's own covariate distribution) give adjusted risk ratios / differences
      with linearised CIs:
        - model A: person covariates + the shared PRE_CRASH crash set (specs.PRE_CRASH);
        - model B: model A + crash configuration (crash type, number of vehicles).
      Configuration can be a mediator of driver/occupant characteristics (e.g. young
      drivers -> single-vehicle crashes) but is a plausible *confounder* of restraint use
      (belt non-users are over-represented in high-energy crash types), so both are shown.
    * Interactions (pre-specified): restraint x age band and restraint x crash type
      (complete-case: belted vs none only), age band x sex (sex known).  Product terms in
      model A (B for crash type); four standardised margins per cell give the stratum
      specific RR, the additive interaction contrast (IC), RERI and the ratio of risk ratios,
      plus a design-adjusted Wald F test of all product terms.
    * Leakage control: every feature is checked against ``harmonize.REGISTRY``; post-crash
      variables (ejection, airbag deployment, rollover) are never used.
Justified interpretation
    "Among occupants of light passenger vehicles in police-reported crashes, unbelted
    occupants were killed X times as often as belted occupants with the same distribution
    of age, sex, seat, vehicle and crash circumstances" -- an adjusted association conditional
    on involvement in a reported crash (label: *adjusted association*; rates: *estimated*).
Not justified
    A causal effect of belts (belt non-use is correlated with unmeasured crash energy and
    risk-taking; police-reported belt use of survivors may be over-reported); effects on
    crash occurrence; lives saved by raising belt use.  The FARS within-vehicle design
    (``matched``) comes closer to a causal estimate for restraint, age and sex.
"""

from __future__ import annotations

import gc
import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import polars as pl
from scipy import stats

from nhtsa_stats import config
from nhtsa_stats.analysis import data, specs
from nhtsa_stats.analysis.severity import crude_table, factor_contrasts, observed_levels
from nhtsa_stats.analysis.survey import (
    Estimate,
    MarginSet,
    ModelSpec,
    SurveyDesign,
    SurveyLogit,
    interaction_contrasts,
    proportion_table,
    svy_total,
)
from nhtsa_stats.processing.harmonize import REGISTRY, assert_no_leakage
from nhtsa_stats.reporting.io import save_json, save_table

log = logging.getLogger(__name__)
MODULE = "person"
OUTCOMES: tuple[str, ...] = ("killed", "killed_or_serious")
OCCUPANT_PER_TYP: tuple[int, ...] = (1, 2, 9)
LPV_BODIES: tuple[str, ...] = ("car", "suv", "pickup", "van", "light_truck_other")
MIN_RESTRAINT_AGE = 8
# Same tiny L2 penalty as the crash-level models (severity.RIDGE): keeps coefficients finite
# for levels with zero events (e.g. occupants in pedestrian crashes) while shrinking any level
# with >= 1,000 persons by well under 1%.
RIDGE = 0.01
INPUT = "data/processed/crss_person.parquet (+ young/older_driver from crss_crash.parquet)"

# Crash-level columns of the PRE_CRASH set that the person file does not carry.
CRASH_ONLY_COLS: tuple[str, ...] = ("young_driver", "older_driver")
PERSON_COLS: tuple[str, ...] = (
    "YEAR",
    "case_id",
    "PER_TYP",
    "WEIGHT",
    "PSUSTRAT",
    "PSU_VAR",
    "age",
    "age_band",
    "sex",
    "role",
    "restraint",
    "helmet",
    "body",
    "veh_age_band",
    "other_vehicle_body",
    "crash_type",
    "n_vehicles",
)

# Features derived in this module from registered variables (for the leakage check).
DERIVED_FROM: dict[str, str] = {"rider": "role", "n_vehicles_mv": "n_vehicles"}
# Features that are not (yet) in harmonize.REGISTRY, with the reason they are admissible.
UNREGISTERED_ADMISSIBLE: dict[str, str] = {
    "other_vehicle_body": "body group of the other in-transport vehicle in two-vehicle crashes "
    "(a pre-crash vehicle attribute describing crash configuration; not a consequence)",
}

_PL = specs.PERSON_LEVELS
LPV_LEVELS: dict[str, list] = {
    "age_band": ["25-34", "8-14", *_PL["age_band"][2:9]],
    "sex": _PL["sex"],
    "role": _PL["role"],
    "restraint": ["belted", "none", "child_restraint", "not_applicable", "unknown"],
    "body": list(LPV_BODIES),
    "veh_age_band": _PL["veh_age_band"],
    "other_vehicle_body": _PL["other_vehicle_body"],
}
MC_LEVELS: dict[str, list] = {
    "helmet": ["helmet", "none", "unknown"],
    "age_band": _PL["age_band"],
    "sex": _PL["sex"],
    "rider": ["operator", "passenger"],
    "veh_age_band": _PL["veh_age_band"],
    "other_vehicle_body": _PL["other_vehicle_body"],
}
LPV_PERSON = list(LPV_LEVELS)
MC_PERSON = list(MC_LEVELS)


# --------------------------------------------------------------------------------------
# Data
# --------------------------------------------------------------------------------------
@dataclass
class Population:
    """A modelling domain: rows, their design (full cluster universe kept), levels."""

    name: str
    label: str
    df: pd.DataFrame
    design: SurveyDesign
    person_covariates: list[str]
    levels: dict[str, list]
    crash_covariates: list[str] = field(default_factory=list)

    def subset(self, mask: np.ndarray, name: str, label: str) -> Population:
        mask = np.asarray(mask, dtype=bool)
        return Population(
            name,
            label,
            self.df.loc[mask].reset_index(drop=True),
            self.design.subset(mask),
            list(self.person_covariates),
            dict(self.levels),
            list(self.crash_covariates),
        )


def load_occupants(outcome: str) -> tuple[pd.DataFrame, SurveyDesign]:
    """Column-selective equivalent of ``data.crss_person(outcome, occupants_only=True)``.

    Same population rule (PER_TYP 1/2/9 with known ``outcome``) and the same design
    construction (design built from *every* row of the person file, then subset, so domain
    variances use all PSUs) -- but only the columns the models need are read, which keeps the
    process well under 3 GB.  The crash-level PRE_CRASH columns absent from the person file
    (young/older driver involved) are attached from the crash file, and tri-state indicators
    are converted to 'no'/'yes'/'unknown' labels.
    """
    cols = list(
        dict.fromkeys(
            [
                *PERSON_COLS,
                outcome,
                "killed",
                *(c for c in specs.PRE_CRASH if c not in CRASH_ONLY_COLS),
            ]
        )
    )
    pers = pl.read_parquet(config.PROCESSED_DIR / "crss_person.parquet", columns=cols)
    # String columns become pandas categoricals (integer codes): ~10x less memory than
    # per-row Python strings, which matters for ~1M-row design matrices and margins.
    pers = pers.with_columns(pl.col(pl.String).cast(pl.Categorical))
    df = pers.to_pandas()
    del pers
    design = SurveyDesign.from_frame(df)
    keep = df["PER_TYP"].isin(list(OCCUPANT_PER_TYP)).to_numpy() & df[outcome].notna().to_numpy()
    df = df.loc[keep].reset_index(drop=True)
    design = design.subset(keep)
    crash = pl.read_parquet(
        config.PROCESSED_DIR / "crss_crash.parquet", columns=["YEAR", "case_id", *CRASH_ONLY_COLS]
    ).to_pandas()
    if crash.duplicated(["YEAR", "case_id"]).any():
        raise ValueError("crss_crash has duplicate (YEAR, case_id) keys")
    merged = df.merge(crash, on=["YEAR", "case_id"], how="left", validate="many_to_one")
    if len(merged) != len(df) or not merged["case_id"].equals(df["case_id"]):
        raise AssertionError("crash merge changed the person rows")
    df = merged
    for c in specs.CRASH_TRI:
        if c in df.columns:
            df[c] = data.tri_state(df[c]).astype("category")
    df[outcome] = df[outcome].astype(float)
    df["killed"] = df["killed"].astype(float)
    df["YEAR"] = df["YEAR"].astype(int)
    return df, design


def _categorise(df: pd.DataFrame, columns: Sequence[str]) -> pd.DataFrame:
    for c in columns:
        if c in df.columns and not isinstance(df[c].dtype, pd.CategoricalDtype):
            df[c] = df[c].astype("category")
    return df


def _relabel(s: pd.Series, mapping: dict[str, str]) -> pd.Series:
    return s.astype(object).replace(mapping).astype("category")


def build_populations(df: pd.DataFrame, design: SurveyDesign) -> dict[str, Population]:
    """LPV occupants aged 8+ (restraint analyses) and motorcycle riders."""
    body = df["body"].to_numpy(dtype=object)
    age = df["age"].to_numpy(dtype=float)
    lpv_mask = np.isin(body, LPV_BODIES) & (np.nan_to_num(age, nan=-1) >= MIN_RESTRAINT_AGE)
    mc_mask = body == "motorcycle"

    lpv_df = df.loc[lpv_mask].reset_index(drop=True)
    lpv_df["age_band"] = _relabel(lpv_df["age_band"], {"0-14": "8-14"})
    lpv_crash = list(specs.PRE_CRASH)

    mc_df = df.loc[mc_mask].reset_index(drop=True)
    mc_df["rider"] = np.where(mc_df["role"].to_numpy() == "driver", "operator", "passenger")
    mc_df["helmet"] = _relabel(mc_df["helmet"], {"not_applicable": "unknown"})
    # Every motorcycle rider is by definition in a crash involving a motorcycle.
    mc_crash = [c for c in specs.PRE_CRASH if c != "any_motorcycle"]

    cat_cols = [*specs.CRASH_LEVELS, *LPV_LEVELS, *MC_LEVELS]
    return {
        "lpv": Population(
            "lpv",
            f"CRSS occupants of light passenger vehicles aged {MIN_RESTRAINT_AGE}+ (known age)",
            _categorise(lpv_df, cat_cols),
            design.subset(lpv_mask),
            LPV_PERSON,
            LPV_LEVELS,
            lpv_crash,
        ),
        "motorcycle": Population(
            "motorcycle",
            "CRSS motorcycle operators and passengers",
            _categorise(mc_df, cat_cols),
            design.subset(mc_mask),
            MC_PERSON,
            MC_LEVELS,
            mc_crash,
        ),
    }


def population_flow(df: pd.DataFrame, design: SurveyDesign, outcome: str) -> pd.DataFrame:
    """Unweighted and weighted (per year) counts at each restriction step."""
    n_years = df["YEAR"].nunique()
    body = df["body"].to_numpy(dtype=object)
    age = df["age"].to_numpy(dtype=float)
    lpv = np.isin(body, LPV_BODIES)
    steps = {
        "occupants (PER_TYP 1/2/9) with known outcome": np.ones(len(df), dtype=bool),
        "  light passenger vehicle occupants": lpv,
        "    age unknown (excluded)": lpv & np.isnan(age),
        f"    age < {MIN_RESTRAINT_AGE} (excluded)": lpv & (np.nan_to_num(age, nan=99) < 8),
        f"    LPV analysis population (age {MIN_RESTRAINT_AGE}+)": lpv
        & (np.nan_to_num(age, nan=-1) >= MIN_RESTRAINT_AGE),
        "  motorcycle riders (analysis population)": body == "motorcycle",
        "  other vehicle types (bus, truck, other, unknown; not modelled)": ~lpv
        & (body != "motorcycle"),
    }
    y = df[outcome].to_numpy(dtype=float)
    rows = []
    for label, m in steps.items():
        tot = svy_total(design, np.ones(design.n), m)
        ev = svy_total(design, y, m)
        rows.append(
            {
                "outcome": outcome,
                "step": label,
                "n_persons": int(m.sum()),
                "n_events": int(y[m].sum()),
                "weighted_persons_per_year": tot.estimate / n_years,
                "weighted_events_per_year": ev.estimate / n_years,
                "crude_rate": ev.estimate / tot.estimate if tot.estimate > 0 else np.nan,
            }
        )
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------------------
# Models
# --------------------------------------------------------------------------------------
@dataclass
class LeanSurveyLogit(SurveyLogit):
    """``SurveyLogit`` whose predictive margins are computed in row chunks.

    Numerically identical to :meth:`SurveyLogit.margin_influence` (verified in
    tests/test_person.py) but never materialises more than ``chunk_rows`` rows of the
    counterfactual design matrix, and forms the coefficient part of the influence function
    as ``(X @ v) * r`` instead of ``(X * r) @ v``.  With ~0.9M persons and ~110 parameters
    this keeps the transient memory of each margin below ~200 MB instead of ~1.5 GB.
    """

    chunk_rows: int = 100_000

    def margin_influence(
        self,
        df: pd.DataFrame,
        setter: Callable[[pd.DataFrame], pd.DataFrame] | None,
        domain: np.ndarray | None = None,
    ) -> tuple[float, np.ndarray]:
        n = len(df)
        d = np.ones(n, dtype=bool) if domain is None else np.asarray(domain, dtype=bool)
        cf = df if setter is None else setter(df.copy())
        w = self._w * d
        big_w = w.sum()
        pa = np.empty(n)
        g = np.zeros(len(self.coef_))
        for start in range(0, n, self.chunk_rows):
            sl = slice(start, min(start + self.chunk_rows, n))
            xa, _ = self.spec.design_matrix(cf.iloc[sl])
            pa[sl] = 0.5 * (1 + np.tanh(0.5 * (xa @ self.coef_)))
            g += xa.T @ (w[sl] * pa[sl] * (1 - pa[sl]))
        m = float((w * pa).sum() / big_w)
        g /= big_w
        infl_beta = (self._x @ (self._a_inv @ g)) * self._resid_w
        z = w * (pa - m) / big_w + infl_beta
        return m, z


def check_features(features: Sequence[str]) -> None:
    """Leakage check against harmonize.REGISTRY (derived names map to their source).

    ``YEAR`` is registered with timing 'design' (calendar year) and is admitted as an
    adjustment variable, as in every crash-level model; other design variables (weights,
    strata, PSUs) and every post-crash / outcome variable are rejected.
    """
    registered = []
    for f in features:
        if f in UNREGISTERED_ADMISSIBLE and f not in REGISTRY:
            continue
        if f == "YEAR":
            continue
        registered.append(DERIVED_FROM.get(f, f))
    assert_no_leakage(registered)


def levels_for(pop: Population, var: str) -> list:
    declared = pop.levels.get(var, specs.CRASH_LEVELS.get(var))
    if declared is None:
        raise KeyError(f"no declared levels for {var}")
    return observed_levels(pop.df, var, declared)


def make_spec(
    pop: Population, covariates: Sequence[str], interactions: Sequence[tuple[str, str]] = ()
) -> ModelSpec:
    check_features(covariates)
    return ModelSpec(
        categorical={c: levels_for(pop, c) for c in covariates}, interactions=list(interactions)
    )


def fit_model(
    pop: Population,
    outcome: str,
    covariates: Sequence[str],
    interactions: Sequence[tuple[str, str]] = (),
    ridge: float = RIDGE,
) -> SurveyLogit:
    spec = make_spec(pop, covariates, interactions)
    lean = pop.df[[*spec.columns(), outcome]]
    model = LeanSurveyLogit(spec, ridge=ridge).fit(lean, lean[outcome].to_numpy(), pop.design)
    if not model.converged_:
        log.warning("%s/%s model did not converge", pop.name, outcome)
    log.info(
        "%s/%s: n=%d events=%d params=%d converged=%s",
        pop.name,
        outcome,
        model.n_,
        model.n_events_,
        len(model.coef_),
        model.converged_,
    )
    return model


def _flag(n: int, rse: float) -> str:
    if n < config.MIN_CELL_N:
        return "suppressed"
    if not np.isfinite(rse) or rse > config.MAX_RSE:
        return "unstable"
    return ""


def _adjusted_flags(res: pd.DataFrame, prefix: str, tcrit: float) -> list[str]:
    """Suppression / instability flag of each adjusted margin (crude n, margin RSE)."""
    se = (res[f"{prefix}_adj_rate_high"] - res[f"{prefix}_adj_rate_low"]) / (2 * tcrit)
    rse = (se / res[f"{prefix}_adj_rate"]).to_numpy(dtype=float)
    return [_flag(int(n), float(r)) for n, r in zip(res["n"], rse, strict=True)]


def reported_factors(pop: Population) -> list[str]:
    """Person factors whose contrasts are reported from the main models.

    ``other_vehicle_body`` is an adjuster only: its contrast against 'none_or_multi' would
    set single-vehicle-crash occupants to having a partner vehicle and collide with the
    crash-level any_heavy_truck / any_motorcycle flags.  Partner-vehicle contrasts are
    estimated in the two-vehicle-crash domain instead (:func:`partner_vehicle`).
    """
    return [c for c in pop.person_covariates if c != "other_vehicle_body"]


def crude_vs_adjusted(
    pop: Population, outcome: str, factors: Sequence[str] | None = None
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Crude and standardised adjusted RRs for each person-level factor (models A and B).

    Models are fitted one at a time and released before the next (each holds an n x p
    design matrix) to keep memory bounded.
    """
    factors = reported_factors(pop) if factors is None else list(factors)
    cov_a = [*pop.person_covariates, *pop.crash_covariates]
    models = {"A": cov_a, "B": [*cov_a, *specs.CIRCUMSTANCE]}
    n_years = pop.df["YEAR"].nunique()
    lean = pop.df[[*dict.fromkeys(models["B"]), outcome]]
    parts: dict[str, list[pd.DataFrame]] = {f: [] for f in factors}
    for f in factors:
        parts[f].append(crude_table(lean, pop.design, outcome, f, levels_for(pop, f), n_years))
    coefs, meta = [], {"n": len(lean), "events": int(lean[outcome].sum())}
    for name, covs in models.items():
        model = fit_model(pop, outcome, covs)
        coefs.append(model.coef_table().assign(model=name))
        meta[f"params_{name}"] = len(model.coef_)
        meta[f"converged_{name}"] = bool(model.converged_)
        for f in factors:
            con = factor_contrasts(model, lean, f, levels_for(pop, f))
            parts[f].append(con.drop(columns=["factor", "level"]).add_prefix(f"{name}_"))
            log.info("%s/%s model %s contrasts done for %s", pop.name, outcome, name, f)
        del model
        gc.collect()
    res = pd.concat([pd.concat(p, axis=1) for p in parts.values()], ignore_index=True)
    res.insert(0, "population", pop.name)
    res.insert(1, "outcome", outcome)
    lead = ["population", "outcome", "factor", "level"]
    res = res[lead + [c for c in res.columns if c not in lead]]
    with np.errstate(divide="ignore", invalid="ignore"):
        for name in models:
            res[f"{name}_logrr_retained"] = np.log(res[f"{name}_adj_rr"]) / np.log(res["crude_rr"])
    for name in models:
        res[f"{name}_flag"] = _adjusted_flags(res, name, pop.design.tcrit())
    coef = pd.concat(coefs, ignore_index=True)
    coef.insert(0, "population", pop.name)
    coef.insert(1, "outcome", outcome)
    meta["design_df"] = pop.design.df
    coef.attrs["meta"] = meta
    return res, coef


# Crash-level flags that are fully determined by the partner vehicle in a two-vehicle crash
# of an LPV occupant or motorcycle rider; they are dropped when partner type is the exposure.
PARTNER_DETERMINED: tuple[str, ...] = ("any_heavy_truck", "any_motorcycle")


def partner_vehicle(pop: Population, outcome: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Partner-vehicle type contrasts among occupants of two-vehicle crashes (ref: car).

    Domain: persons whose crash had exactly two in-transport vehicles.  Adjusted for the
    person covariates and PRE_CRASH minus the flags the partner type determines; model B adds
    crash type (number of vehicles is constant in this domain).
    """
    ov = pop.df["other_vehicle_body"].to_numpy(dtype=object)
    sub = pop.subset(
        ov != "none_or_multi", f"{pop.name}_two_vehicle", f"{pop.label}, two-vehicle crashes"
    )
    sub.levels["other_vehicle_body"] = [
        lv for lv in _PL["other_vehicle_body"] if lv != "none_or_multi"
    ]
    sub.crash_covariates = [c for c in pop.crash_covariates if c not in PARTNER_DETERMINED]
    sub.df["other_vehicle_body"] = sub.df["other_vehicle_body"].cat.remove_unused_categories()
    res, coef = crude_vs_adjusted(sub, outcome, factors=["other_vehicle_body"])
    res["population"] = sub.name
    coef["population"] = sub.name
    return res, coef


# --------------------------------------------------------------------------------------
# Interactions
# --------------------------------------------------------------------------------------
def _setter(assign: dict[str, object]) -> Callable[[pd.DataFrame], pd.DataFrame]:
    return lambda d: d.assign(**assign)


def _ci_row(prefix: str, est: Estimate, exp: bool = False) -> dict[str, float]:
    lo, hi = est.ci()
    if exp:
        return {
            prefix: float(np.exp(est.estimate)),
            f"{prefix}_low": float(np.exp(lo)),
            f"{prefix}_high": float(np.exp(hi)),
        }
    return {prefix: est.estimate, f"{prefix}_low": lo, f"{prefix}_high": hi}


def interaction_table(
    model: SurveyLogit,
    df: pd.DataFrame,
    outcome: str,
    a: str,
    a_ref: str,
    a_exp: str,
    b: str,
    b_levels: Sequence[str],
) -> pd.DataFrame:
    """Stratum-specific adjusted RRs of ``a_exp`` vs ``a_ref`` within each level of ``b``,
    and additive / multiplicative interaction measures versus the reference level of ``b``.

    Four standardised margins per level (everyone set to the (a, b) combination) share one
    joint linearisation, so every contrast has a design-based CI.
    """
    b_ref = b_levels[0]

    def key(av: str, bv: str) -> str:
        return f"{a}={av}|{b}={bv}"

    scenarios = {key(av, bv): _setter({a: av, b: bv}) for bv in b_levels for av in (a_ref, a_exp)}
    ms: MarginSet = model.margins(df, scenarios)
    y = df[outcome].to_numpy(dtype=float)
    av_obs = df[a].to_numpy()
    bv_obs = df[b].to_numpy()
    rows = []
    for bv in b_levels:
        p1 = ms.estimate(key(a_exp, bv))
        p0 = ms.estimate(key(a_ref, bv))
        in_b = bv_obs == bv
        n1 = int((in_b & (av_obs == a_exp)).sum())
        n0 = int((in_b & (av_obs == a_ref)).sum())
        rec = {
            "outcome": outcome,
            "factor_a": a,
            "a_exposed": a_exp,
            "a_reference": a_ref,
            "factor_b": b,
            "b_level": bv,
            "n_a_exposed": n1,
            "events_a_exposed": int(y[in_b & (av_obs == a_exp)].sum()),
            "n_a_reference": n0,
            "events_a_reference": int(y[in_b & (av_obs == a_ref)].sum()),
            **_ci_row("risk_a_exposed", p1),
            **_ci_row("risk_a_reference", p0),
            **_ci_row("rr", ms.log_ratio(key(a_exp, bv), key(a_ref, bv)), exp=True),
            **_ci_row("rd", ms.difference(key(a_exp, bv), key(a_ref, bv))),
        }
        rse = max(p1.rse, p0.rse)
        rec["flag"] = _flag(min(n1, n0), rse)
        if bv == b_ref:
            rec.update({k: np.nan for k in ("ic", "reri", "ratio_of_rr")})
        else:
            ic = interaction_contrasts(
                ms, key(a_exp, bv), key(a_exp, b_ref), key(a_ref, bv), key(a_ref, b_ref)
            )
            rec.update(_ci_row("ic", ic["ic"]))
            rec.update(_ci_row("reri", ic["reri"]))
            rec.update(_ci_row("ratio_of_rr", ic["log_ratio_of_rr"], exp=True))
            rec["p_ratio_of_rr"] = _two_sided_p(ic["log_ratio_of_rr"])
            rec["p_ic"] = _two_sided_p(ic["ic"])
        rows.append(rec)
    return pd.DataFrame(rows)


def _two_sided_p(est: Estimate) -> float:
    if not np.isfinite(est.se) or est.se == 0:
        return float("nan")
    return float(2 * stats.t.sf(abs(est.estimate / est.se), est.df))


@dataclass(frozen=True)
class InteractionSpec:
    name: str
    a: str
    a_ref: str
    a_exp: str
    b: str
    with_configuration: bool
    description: str


INTERACTIONS: tuple[InteractionSpec, ...] = (
    InteractionSpec(
        "restraint_x_age",
        "restraint",
        "belted",
        "none",
        "age_band",
        False,
        "Unbelted vs belted adjusted RR within age bands (complete case: belted/none)",
    ),
    InteractionSpec(
        "age_x_sex",
        "sex",
        "male",
        "female",
        "age_band",
        False,
        "Female vs male adjusted RR within age bands (sex known)",
    ),
    InteractionSpec(
        "restraint_x_crash_type",
        "restraint",
        "belted",
        "none",
        "crash_type",
        True,
        "Unbelted vs belted adjusted RR within crash types (complete case; motor-vehicle "
        "crash types only -- occupant deaths in pedestrian/cyclist crashes are too rare)",
    ),
)
NON_OCCUPANT_CRASH_TYPES = ("pedestrian", "cyclist")


def interaction_population(pop: Population, ispec: InteractionSpec) -> Population:
    df = pop.df
    if ispec.a == "restraint":
        mask = df["restraint"].isin([ispec.a_ref, ispec.a_exp]).to_numpy()
        sub = pop.subset(mask, f"{pop.name}_restraint_known", f"{pop.label}, belted or none")
        sub.levels["restraint"] = [ispec.a_ref, ispec.a_exp]
    elif ispec.a == "sex":
        mask = df["sex"].isin([ispec.a_ref, ispec.a_exp]).to_numpy()
        sub = pop.subset(mask, f"{pop.name}_sex_known", f"{pop.label}, sex known")
        sub.levels["sex"] = [ispec.a_ref, ispec.a_exp]
    else:  # pragma: no cover - guarded by INTERACTIONS
        raise ValueError(ispec.a)
    if ispec.b == "crash_type":
        keep = ~sub.df["crash_type"].isin(list(NON_OCCUPANT_CRASH_TYPES)).to_numpy()
        sub = sub.subset(keep, sub.name, sub.label + ", motor-vehicle crash types")
        # Within motor-vehicle crash types, '1 vehicle' is exactly the single-vehicle crash
        # types, so number of vehicles is collapsed to 3+ vs 1-2 to avoid perfect collinearity.
        sub.df["n_vehicles_mv"] = np.where(sub.df["n_vehicles"].to_numpy() == "3+", "3+", "1-2")
        sub.levels["n_vehicles_mv"] = ["1-2", "3+"]
    for c in (ispec.a, ispec.b):
        if isinstance(sub.df[c].dtype, pd.CategoricalDtype):
            sub.df[c] = sub.df[c].astype(object)
    return sub


def run_interaction(pop: Population, outcome: str, ispec: InteractionSpec) -> dict:
    sub = interaction_population(pop, ispec)
    covs = [*sub.person_covariates, *sub.crash_covariates]
    if ispec.with_configuration:
        covs += ["crash_type", "n_vehicles_mv"]
    covs = list(dict.fromkeys(covs))
    model = fit_model(sub, outcome, covs, interactions=[(ispec.a, ispec.b)])
    b_levels = levels_for(sub, ispec.b)
    lean = sub.df[[*covs, outcome]]
    tab = interaction_table(
        model, lean, outcome, ispec.a, ispec.a_ref, ispec.a_exp, ispec.b, b_levels
    )
    tab.insert(0, "interaction", ispec.name)
    terms = [t for t in model.names_ if ":" in t]
    test = model.wald_test(terms)
    test_row = {
        "interaction": ispec.name,
        "outcome": outcome,
        "population": sub.label,
        "n": int(model.n_),
        "events": int(model.n_events_),
        "n_product_terms": test["q"],
        "wald_F": test["F"],
        "df_num": test["q"],
        "df_den": sub.design.df - test["q"] + 1,
        "p": test["p"],
        "converged": bool(model.converged_),
    }
    del model
    gc.collect()
    return {"table": tab, "test": test_row}


# --------------------------------------------------------------------------------------
# Driver
# --------------------------------------------------------------------------------------
def _save(
    df: pd.DataFrame,
    name: str,
    description: str,
    pop_label: str,
    outcome: str,
    method: str,
    extra: dict | None = None,
) -> None:
    save_table(
        df,
        MODULE,
        name,
        description=description,
        population=pop_label,
        unit="person",
        outcome=outcome,
        method=method,
        inputs=[INPUT],
        extra=extra,
    )


ADJ_METHOD = (
    "Survey-weighted logistic regression (pseudo-ML, ridge 0.01), Taylor-linearised variance "
    "(25 strata, 67 PSUs, t with 42 df); standardised predictive margins -> adjusted RR/RD. "
    "Model A = person covariates + PRE_CRASH; model B = A + crash type + number of vehicles."
)


def analyse_outcome(outcome: str, interactions: bool = True) -> dict[str, pd.DataFrame]:
    df, design = load_occupants(outcome)
    flow = population_flow(df, design, outcome)
    body_tab = proportion_table(df, design, outcome, "body", years=df["YEAR"].nunique())
    body_tab.insert(0, "outcome", outcome)
    pops = build_populations(df, design)
    del df, design
    gc.collect()
    out: dict[str, pd.DataFrame] = {"flow": flow, "body_crude": body_tab}
    _save(
        body_tab,
        f"all_occupants_{outcome}_crude_by_body",
        "Crude weighted outcome rate by vehicle body group, all occupants (descriptive only; "
        "no adjustment -- restraint/helmet are not comparable across body groups)",
        "CRSS 2016-2024 occupants of in-transport vehicles with known outcome",
        outcome,
        "Weighted proportions, Taylor-linearised SEs, logit CIs; flags n<30 / RSE>30%",
    )
    _save(
        flow,
        f"population_flow_{outcome}",
        "Population flow for the CRSS person-level analyses (unweighted and weighted counts)",
        "CRSS 2016-2024 occupants of in-transport vehicles (PER_TYP 1/2/9) with known outcome",
        outcome,
        "Counts; weighted totals by Taylor-linearised design (per year = total / 9)",
    )
    for key, pop in pops.items():
        res, coef = crude_vs_adjusted(pop, outcome)
        out[f"{key}_crude_vs_adjusted"] = res
        _save(
            res,
            f"{key}_{outcome}_crude_vs_adjusted",
            f"Crude and standardised adjusted risk ratios of '{outcome}' by person-level factor "
            f"({pop.label})",
            pop.label,
            outcome,
            "Crude: weighted rate and saturated survey logit; " + ADJ_METHOD,
            extra=coef.attrs.get("meta"),
        )
        _save(
            coef,
            f"{key}_{outcome}_model_coefficients",
            f"Survey logistic regression coefficients for '{outcome}' ({pop.label})",
            pop.label,
            outcome,
            ADJ_METHOD,
            extra=coef.attrs.get("meta"),
        )
        pres, pcoef = partner_vehicle(pop, outcome)
        out[f"{key}_partner_vehicle"] = pres
        _save(
            pres,
            f"{key}_{outcome}_partner_vehicle",
            f"Partner-vehicle type in two-vehicle crashes (ref: car): crude and adjusted RRs "
            f"of '{outcome}' ({pop.label})",
            f"{pop.label}, two-vehicle crashes",
            outcome,
            "Crude: weighted rate and saturated survey logit; "
            + ADJ_METHOD
            + " Partner-determined flags (any heavy truck / motorcycle) dropped.",
            extra=pcoef.attrs.get("meta"),
        )
    if interactions:
        tabs, tests = [], []
        for ispec in INTERACTIONS:
            r = run_interaction(pops["lpv"], outcome, ispec)
            tabs.append(r["table"])
            tests.append(r["test"])
            _save(
                r["table"],
                f"lpv_{outcome}_interaction_{ispec.name}",
                ispec.description,
                r["test"]["population"],
                outcome,
                "Model A (B for crash type) with product terms; four standardised margins per "
                "cell; IC = p11-p10-p01+p00, RERI = IC/p00, ratio of RR = RR11/(RR10*RR01); "
                "linearised CIs (t, 42 df)",
            )
        tests_df = pd.DataFrame(tests)
        out["interaction_tests"] = tests_df
        out["interactions"] = pd.concat(tabs, ignore_index=True)
    if outcome == "killed_or_serious":
        res, coef = killed_given_ka(pops["lpv"])
        out["lpv_killed_given_ka"] = res
        _save(
            res,
            "lpv_killed_given_ka_crude_vs_adjusted",
            "Measurement sensitivity: P(killed | killed or seriously injured) by person factor. "
            "K and A casualties are both usually examined (not self-reported) by police, so "
            "survivor over-reporting of belt use matters less; but conditioning on KA (itself "
            "affected by belts) means the RR is NOT the effect of belts on death",
            f"{pops['lpv'].label}, injury K or A",
            "killed (among K/A)",
            "Crude: weighted rate and saturated survey logit; " + ADJ_METHOD,
            extra=coef.attrs.get("meta"),
        )
    return out


KA_FACTORS: tuple[str, ...] = ("restraint", "age_band", "sex", "role", "body")


def killed_given_ka(lpv: Population) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Crude/adjusted RRs of death among LPV occupants who were killed or seriously injured."""
    ka = lpv.df["killed_or_serious"].to_numpy(dtype=float) == 1
    known = np.isfinite(lpv.df["killed"].to_numpy(dtype=float))
    sub = lpv.subset(ka & known, "lpv_ka", f"{lpv.label}, injury K or A")
    for c in KA_FACTORS:
        sub.df[c] = sub.df[c].cat.remove_unused_categories()
    return crude_vs_adjusted(sub, "killed", factors=list(KA_FACTORS))


def run(outcomes: Sequence[str] = OUTCOMES, interactions: bool = True) -> dict:
    """Run every analysis for each outcome; write tables to outputs/tables/person/."""
    results: dict[str, dict[str, pd.DataFrame]] = {}
    tests = []
    for oc in outcomes:
        results[oc] = analyse_outcome(oc, interactions=interactions)
        if "interaction_tests" in results[oc]:
            tests.append(results[oc]["interaction_tests"])
        gc.collect()
    if tests:
        all_tests = pd.concat(tests, ignore_index=True)
        # Holm adjustment across the pre-specified interaction tests (3 per outcome).
        all_tests["p_holm"] = holm(all_tests["p"].to_numpy())
        _save(
            all_tests,
            "interaction_tests",
            "Design-adjusted Wald F tests of the pre-specified interaction product terms",
            "CRSS LPV occupants aged 8+ (see table rows)",
            ",".join(outcomes),
            "Korn-Graubard adjusted Wald F on all product terms; Holm adjustment across tests",
        )
        results["interaction_tests"] = {"all": all_tests}
    save_json(key_numbers(results), MODULE, "key_numbers")
    return results


def holm(p: np.ndarray) -> np.ndarray:
    """Holm step-down adjusted p-values (NaN-safe)."""
    p = np.asarray(p, dtype=float)
    out = np.full_like(p, np.nan)
    ok = np.isfinite(p)
    pv = p[ok]
    m = len(pv)
    order = np.argsort(pv)
    adj = np.empty(m)
    running = 0.0
    for rank, idx in enumerate(order):
        running = max(running, min(1.0, (m - rank) * pv[idx]))
        adj[idx] = running
    out[ok] = adj
    return out


def key_numbers(results: dict) -> dict:
    """Small machine-readable digest of headline estimates (for SUMMARY.md / reports)."""
    digest: dict = {}
    for oc, res in results.items():
        if oc == "interaction_tests":
            continue
        for pop in ("lpv", "motorcycle"):
            tab = res.get(f"{pop}_crude_vs_adjusted")
            if tab is None:
                continue
            for _, r in tab.iterrows():
                if r["level"] == levels_first(tab, r["factor"]):
                    continue
                digest[f"{oc}|{pop}|{r['factor']}={r['level']}"] = {
                    "crude_rr": r["crude_rr"],
                    "A_adj_rr": [r["A_adj_rr"], r["A_adj_rr_low"], r["A_adj_rr_high"]],
                    "B_adj_rr": [r["B_adj_rr"], r["B_adj_rr_low"], r["B_adj_rr_high"]],
                    "n": int(r["n"]),
                    "events": int(r["n_events"]),
                }
    return digest


def levels_first(tab: pd.DataFrame, factor: str) -> object:
    return tab.loc[tab["factor"] == factor, "level"].iloc[0]
