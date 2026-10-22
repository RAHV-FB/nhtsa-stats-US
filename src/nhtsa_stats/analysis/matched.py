"""Within-vehicle (matched) designs for person-level risk in fatal crashes (FARS) -- RQ6(b).

Research question
    Within the same vehicle in the same fatal crash -- so with crash forces, impact speed and
    direction, vehicle type and mass, road, weather and time held fixed -- how much higher is
    the fatality risk of an unbelted than of a belted occupant, of an older than of a younger
    occupant, of a woman than of a man, and of an unhelmeted than of a helmeted motorcyclist?

Population
    FARS 2016-2024 occupants of in-transport light passenger vehicles (car, SUV, pickup, van,
    other light truck; PER_TYP 1/2/9 -- parked-vehicle occupants are excluded because their
    VEH_NO refers to the parkwork table), seated front-left, front-other or second row, aged
    13+ (adult belt codes meaningful), with restraint coded belted or none (unknown, child
    restraint and not-applicable excluded) and known 30-day survival.  Motorcycle analyses
    use operators and passengers with helmet coded helmet / none.
Unit / matched set
    Person within vehicle; the matched set is the vehicle (YEAR, case_id, VEH_NO).  Sets with
    >= 2 eligible occupants and discordant outcomes (some died, some survived) carry the
    conditional-likelihood information.
Outcome
    ``killed`` (died within 30 days, INJ_SEV 4) vs survived (INJ_SEV 0-3).
Methods
    1. Conditional logistic regression (statsmodels ConditionalLogit, groups = vehicle) of
       killed ~ unbelted + age band + sex + seat.  The vehicle-specific intercept absorbs
       everything shared by occupants of the vehicle.  Model-based and crash-cluster-robust
       (sandwich over crashes) CIs are reported; the robust CI is primary.
    2. Evans' double-pair comparison (DPC) for driver / right-front-passenger pairs.  With
       D_s[a, b] = deaths of the subject seat in vehicles where the driver has status a and
       the passenger status b (1 = belted, 0 = unbelted):
         driver as subject, other = passenger of status b:
             R = (D_drv[1, b] / D_pas[1, b]) / (D_drv[0, b] / D_pas[0, b])
         passenger as subject, other = driver of status a:
             R = (D_pas[a, 1] / D_drv[a, 1]) / (D_pas[a, 0] / D_drv[a, 0])
       i.e. the death ratio of a subject relative to an "other" occupant whose belt status is
       held fixed, compared between belted and unbelted subjects; the belted-belted and
       unbelted-unbelted pairs supply the seat-specific normalisation.  The four component
       estimates are combined as an inverse-variance weighted geometric mean (Poisson
       variances); the CI is a percentile bootstrap over vehicles (2,000 resamples, exact via
       multinomial resampling of the 16 vehicle cells), with a crash-cluster bootstrap as a
       robustness check.  The same estimator is applied to motorcycle helmet use (operator /
       passenger) and, among both-belted pairs, to age 65+ vs 25-44 and female vs male.
    3. Sensitivity to survivor misreporting of belt use: if a fraction f (0, 5, 10, 20%) of
       survivors coded "belted" were in truth unbelted (deaths correctly coded), the expected
       reclassified cell counts are computed in closed form and the DPC estimate and the
       matched-pair odds ratio (two-occupant vehicles, one death) are recomputed; the
       adjusted conditional logit is refitted after a seeded random reclassification.
Estimands and labels
    * within-vehicle odds ratio (conditional logit) -- *adjusted association* that controls
      for all vehicle-level confounding by design.  Because deaths are common in these sets
      the OR is much further from 1 than the risk ratio and must not be read as an RR.
    * DPC risk ratio R (belted vs unbelted) and "fatality risk reduction associated with belt
      use" 1 - R -- *estimated* under the DPC assumptions, *given a crash severe enough to
      kill an occupant of the pair's vehicle*.
Assumptions (stated, not verified by the data)
    * Belt use (and helmet use) is recorded without outcome-dependent error -- relaxed by the
      misreporting sensitivity analysis (only in the direction of survivors over-reported as
      belted, the documented concern).
    * Occupant-specific confounding is captured by age, sex and seat; occupants' risks within
      a vehicle are conditionally independent given the shared crash severity, and one
      occupant's belt use does not change the other's risk (an unbelted occupant striking a
      belted one would violate this).
    * DPC: the fatality risk factorises as crash severity x seat x belt (multiplicative).
Generalisation limits
    Applies to occupants of light passenger vehicles in fatal crashes carrying >= 2 eligible
    occupants (multi-occupant trips), and to crashes severe enough that someone in the
    vehicle died; it does not estimate belt effectiveness in non-fatal crashes or in the full
    crash population, nor lives saved by increasing belt use.
"""

from __future__ import annotations

import logging
import warnings
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd
import polars as pl
from scipy import optimize, stats
from statsmodels.discrete.conditional_models import ConditionalLogit
from statsmodels.tools.sm_exceptions import ConvergenceWarning

from nhtsa_stats import config
from nhtsa_stats.processing import harmonize as h
from nhtsa_stats.reporting.io import save_json, save_table

log = logging.getLogger(__name__)
MODULE = "matched"
INPUT = "data/processed/fars_person.parquet"

LPV_BODIES: tuple[str, ...] = h.LPV_BODY_GROUPS
ELIGIBLE_SEATS: tuple[str, ...] = ("front_left", "front_other", "second_row")
OCCUPANT_PTYPES: tuple[str, ...] = ("driver", "passenger")
MIN_AGE = 13
SEAT_POS_DRIVER = 11
SEAT_POS_RIGHT_FRONT = 13
MISREPORT_FRACTIONS: tuple[float, ...] = (0.0, 0.05, 0.10, 0.20)
N_BOOT = 2000
CL_MAXITER = 50

# (label, lowest age, highest age); the first entry after the reference is listed in order,
# the reference label is given separately.
AGE_FINE: tuple[tuple[str, int, int], ...] = (
    ("13-20", 13, 20),
    ("21-24", 21, 24),
    ("25-34", 25, 34),
    ("35-44", 35, 44),
    ("45-54", 45, 54),
    ("55-64", 55, 64),
    ("65-74", 65, 74),
    ("75+", 75, 200),
)
AGE_FINE_REF = "25-34"
AGE_COARSE: tuple[tuple[str, int, int], ...] = (
    ("13-24", 13, 24),
    ("25-44", 25, 44),
    ("45-64", 45, 64),
    ("65+", 65, 200),
)
AGE_COARSE_REF = "25-44"
FARS_COLUMNS: tuple[str, ...] = (
    "YEAR",
    "case_id",
    "VEH_NO",
    "PER_NO",
    "PER_TYP",
    "ptype",
    "age",
    "sex",
    "killed",
    "seat",
    "SEAT_POS",
    "restraint",
    "helmet",
    "body",
)


# --------------------------------------------------------------------------------------
# Data and populations
# --------------------------------------------------------------------------------------
def load_fars_occupants(years: Sequence[int] | None = None) -> pd.DataFrame:
    """FARS person rows of in-transport vehicle occupants, with vehicle and crash ids."""
    df = pl.read_parquet(config.PROCESSED_DIR / "fars_person.parquet", columns=list(FARS_COLUMNS))
    if years is not None:
        df = df.filter(pl.col("YEAR").is_in(list(years)))
    out = df.to_pandas()
    return add_ids(out)


def add_ids(df: pd.DataFrame) -> pd.DataFrame:
    """Integer vehicle (matched-set) and crash (cluster) identifiers."""
    year = df["YEAR"].astype(np.int64).to_numpy()
    case = df["case_id"].astype(np.int64).to_numpy()
    veh = df["VEH_NO"].astype(np.int64).to_numpy()
    if case.max(initial=0) >= 1_000_000 or veh.max(initial=0) >= 1_000:
        raise ValueError("identifier ranges exceed the packing scheme")
    df = df.copy()
    df["crash_id"] = year * 1_000_000 + case
    df["vehicle_id"] = (year * 1_000_000 + case) * 1_000 + veh
    return df


def lpv_flow_and_eligible(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Apply the LPV eligibility rules step by step; return (eligible rows, flow table)."""
    steps: list[tuple[str, pd.Series]] = [
        ("all FARS person records", pd.Series(True, index=df.index)),
        (
            "occupants of in-transport vehicles (driver/passenger)",
            df["ptype"].isin(OCCUPANT_PTYPES),
        ),
        ("light passenger vehicle", df["body"].isin(LPV_BODIES)),
        ("seat front-left / front-other / second row", df["seat"].isin(ELIGIBLE_SEATS)),
        (f"age {MIN_AGE}+ (known)", df["age"].ge(MIN_AGE).fillna(False).astype(bool)),
        ("restraint belted or none (known)", df["restraint"].isin(["belted", "none"])),
        ("known outcome (killed 0/1)", df["killed"].notna()),
    ]
    mask = pd.Series(True, index=df.index)
    rows = []
    for label, cond in steps:
        mask &= cond.astype(bool)
        sub = df.loc[mask]
        rows.append(
            {
                "step": label,
                "persons": int(mask.sum()),
                "deaths": int(sub["killed"].fillna(0).sum()),
                "vehicles": int(sub["vehicle_id"].nunique()),
                "crashes": int(sub["crash_id"].nunique()),
            }
        )
    elig = df.loc[mask].copy()
    elig["killed"] = elig["killed"].astype(int)
    elig["unbelted"] = (elig["restraint"] == "none").astype(int)
    sets = matched_sets(elig, "vehicle_id")
    for label, sub in (
        (">= 2 eligible occupants in the vehicle", sets["multi"]),
        ("matched sets with discordant outcomes (analysed)", sets["discordant"]),
        ("  of which discordant belt use (identify the belt OR)", sets["belt_discordant"]),
    ):
        rows.append(
            {
                "step": label,
                "persons": len(sub),
                "deaths": int(sub["killed"].sum()),
                "vehicles": int(sub["vehicle_id"].nunique()),
                "crashes": int(sub["crash_id"].nunique()),
            }
        )
    return elig.reset_index(drop=True), pd.DataFrame(rows)


def matched_sets(df: pd.DataFrame, group: str = "vehicle_id") -> dict[str, pd.DataFrame]:
    """Rows of vehicles with >= 2 eligible occupants, and of those with discordant outcomes."""
    g = df.groupby(group)["killed"]
    size = g.transform("size")
    deaths = g.transform("sum")
    multi = df.loc[size >= 2]
    disc_mask = (size >= 2) & (deaths > 0) & (deaths < size)
    disc = df.loc[disc_mask]
    out = {"multi": multi, "discordant": disc}
    if "unbelted" in df.columns:
        ub = disc.groupby(group)["unbelted"].transform("mean")
        out["belt_discordant"] = disc.loc[(ub > 0) & (ub < 1)]
    return out


# --------------------------------------------------------------------------------------
# Conditional logistic regression
# --------------------------------------------------------------------------------------
def age_dummies(age: pd.Series, bands: Sequence[tuple[str, int, int]], ref: str) -> pd.DataFrame:
    out = {}
    a = age.to_numpy(dtype=float)
    covered = np.zeros(len(a), dtype=bool)
    for label, lo, hi in bands:
        ind = (a >= lo) & (a <= hi)
        covered |= ind
        if label != ref:
            out[f"age[{label}]"] = ind.astype(float)
    if not covered.all():
        raise ValueError("ages outside the declared bands")
    return pd.DataFrame(out, index=age.index)


def occupant_covariates(
    df: pd.DataFrame,
    exposure: str = "unbelted",
    bands: Sequence[tuple[str, int, int]] = AGE_FINE,
    ref: str = AGE_FINE_REF,
    seat: bool = True,
) -> pd.DataFrame:
    """Design matrix (no intercept) for the conditional logit; all-zero columns dropped."""
    parts = [df[[exposure]].astype(float), age_dummies(df["age"], bands, ref)]
    sex = pd.DataFrame(
        {
            "sex[female]": (df["sex"] == "female").astype(float),
            "sex[unknown]": (df["sex"] == "unknown").astype(float),
        },
        index=df.index,
    )
    parts.append(sex)
    if seat:
        parts.append(
            pd.DataFrame(
                {
                    "seat[front_other]": (df["seat"] == "front_other").astype(float),
                    "seat[second_row]": (df["seat"] == "second_row").astype(float),
                },
                index=df.index,
            )
        )
    x = pd.concat(parts, axis=1)
    return x.loc[:, x.abs().sum(axis=0) > 0]


@dataclass
class CLResult:
    table: pd.DataFrame
    info: dict
    params: np.ndarray


def fit_clogit(
    y: np.ndarray,
    x: pd.DataFrame,
    groups: np.ndarray,
    clusters: np.ndarray,
    start: np.ndarray | None = None,
    level: float = 0.95,
) -> CLResult:
    """Conditional logit with model-based and cluster-robust (by crash) covariance.

    Every group passed must have discordant outcomes (statsmodels would silently drop the
    others, which would break the alignment of group scores with clusters).
    """
    y = np.asarray(y, dtype=float)
    groups = np.asarray(groups)
    clusters = np.asarray(clusters)
    order = pd.unique(groups)  # statsmodels keeps groups in order of first appearance
    k = pd.Series(y).groupby(groups).agg(["sum", "size"])
    if ((k["sum"] == 0) | (k["sum"] == k["size"])).any():
        raise ValueError("every matched set must have discordant outcomes")
    model = ConditionalLogit(y, x.to_numpy(dtype=float), groups=groups)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ConvergenceWarning)
        # Newton-Raphson (numerical Hessian from the analytic score) converges to a gradient
        # of ~1e-11; BFGS stopped at ~0.1 on these data.
        res = model.fit(method="newton", maxiter=CL_MAXITER, start_params=start, disp=False)
    params = np.asarray(res.params)
    if res.n_groups != len(order):
        raise AssertionError("statsmodels dropped matched sets unexpectedly")
    cov_model = np.asarray(res.cov_params())
    scores = np.vstack([model.score_grp(g, params) for g in range(res.n_groups)])
    # Map each group (in statsmodels order) to its crash and sum scores within crashes.
    first_cluster = pd.Series(clusters).groupby(groups).first().reindex(order).to_numpy()
    codes, uniq = pd.factorize(first_cluster)
    s_c = np.zeros((len(uniq), scores.shape[1]))
    np.add.at(s_c, codes, scores)
    n_c = len(uniq)
    meat = (n_c / (n_c - 1)) * (s_c.T @ s_c)
    cov_rob = cov_model @ meat @ cov_model
    se_m = np.sqrt(np.diag(cov_model))
    se_r = np.sqrt(np.diag(cov_rob))
    z = stats.norm.ppf(0.5 + level / 2)
    table = pd.DataFrame(
        {
            "term": list(x.columns),
            "coef": params,
            "se_model": se_m,
            "se_robust": se_r,
            "odds_ratio": np.exp(params),
            "or_low": np.exp(params - z * se_r),
            "or_high": np.exp(params + z * se_r),
            "or_low_model": np.exp(params - z * se_m),
            "or_high_model": np.exp(params + z * se_m),
            "p_robust": 2 * stats.norm.sf(np.abs(params / se_r)),
        }
    )
    grad = scores.sum(axis=0)
    # Convergence: the remaining Newton step must be negligible relative to the SEs.
    step = cov_model @ grad
    max_step_se = float(np.max(np.abs(step) / se_m))
    info = {
        "n_sets": int(res.n_groups),
        "n_persons": len(y),
        "n_deaths": int(y.sum()),
        "n_crash_clusters": int(n_c),
        "converged": bool(np.isfinite(max_step_se) and max_step_se < 1e-3),
        "max_abs_score": float(np.max(np.abs(grad))),
        "max_newton_step_over_se": max_step_se,
        "loglike": float(model.loglike(params)),
    }
    if not info["converged"]:
        log.warning("conditional logit not converged: %s", info)
    return CLResult(table, info, params)


def exposure_set_counts(df: pd.DataFrame, exposure: str) -> dict:
    """How many matched sets are discordant on the exposure (they identify its OR)."""
    m = df.groupby("vehicle_id")[exposure].mean()
    return {
        "sets_discordant_exposure": int(((m > 0) & (m < 1)).sum()),
        "persons_exposed": int(df[exposure].sum()),
        "deaths_exposed": int(df.loc[df[exposure] == 1, "killed"].sum()),
        "deaths_unexposed": int(df.loc[df[exposure] == 0, "killed"].sum()),
    }


# --------------------------------------------------------------------------------------
# Double-pair comparison (Evans)
# --------------------------------------------------------------------------------------
def pair_frame(
    df: pd.DataFrame,
    attribute: str,
    driver_mask: pd.Series,
    other_mask: pd.Series,
    carry: Sequence[str] = (),
) -> pd.DataFrame:
    """One row per vehicle with exactly one eligible driver and one eligible 'other' occupant.

    ``attribute`` is a 0/1 column (e.g. belted); output columns: x_d, k_d (driver attribute
    and death), x_p, k_p (other occupant), vehicle_id, crash_id, plus ``{c}_d`` / ``{c}_p``
    for every column in ``carry`` (used to restrict pairs, e.g. by age difference).
    """
    cols = ["vehicle_id", attribute, "killed", *carry]
    d = df.loc[driver_mask, ["crash_id", *cols]]
    p = df.loc[other_mask, cols]
    d = d[~d["vehicle_id"].duplicated(keep=False)]
    p = p[~p["vehicle_id"].duplicated(keep=False)]
    out = d.merge(p, on="vehicle_id", suffixes=("_d", "_p"), validate="one_to_one")
    res = pd.DataFrame(
        {
            "vehicle_id": out["vehicle_id"].to_numpy(),
            "crash_id": out["crash_id"].to_numpy(),
            "x_d": out[f"{attribute}_d"].astype(int).to_numpy(),
            "k_d": out["killed_d"].astype(int).to_numpy(),
            "x_p": out[f"{attribute}_p"].astype(int).to_numpy(),
            "k_p": out["killed_p"].astype(int).to_numpy(),
        }
    )
    for c in carry:
        res[f"{c}_d"] = out[f"{c}_d"].to_numpy()
        res[f"{c}_p"] = out[f"{c}_p"].to_numpy()
    return res


def cell_index(pairs: pd.DataFrame) -> np.ndarray:
    """Flat index of each vehicle's cell in the (x_d, k_d, x_p, k_p) 2x2x2x2 table."""
    return (
        pairs["x_d"].to_numpy() * 8
        + pairs["k_d"].to_numpy() * 4
        + pairs["x_p"].to_numpy() * 2
        + pairs["k_p"].to_numpy()
    )


def cell_counts(pairs: pd.DataFrame) -> np.ndarray:
    """Counts of vehicles in the 16 cells, shape (2, 2, 2, 2) = [x_d, k_d, x_p, k_p]."""
    return np.bincount(cell_index(pairs), minlength=16).reshape(2, 2, 2, 2).astype(float)


def death_counts(c: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Driver and other-occupant deaths by pair type; arrays (..., 2, 2) = [x_d, x_p]."""
    d_drv = c[..., :, 1, :, :].sum(axis=-1)  # sum over k_p -> (..., x_d, x_p)
    d_pas = c[..., :, :, :, 1].sum(axis=-2)  # sum over k_d -> (..., x_d, x_p)
    return d_drv, d_pas


COMPONENTS: tuple[str, ...] = (
    "driver_subject|other_x=1",
    "driver_subject|other_x=0",
    "other_subject|driver_x=1",
    "other_subject|driver_x=0",
)


def dpc_components(c: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Log risk ratios (x=1 vs x=0) of the four DPC comparisons and their Poisson variances.

    Returns arrays with a trailing axis of length 4 in the order of :data:`COMPONENTS`.
    Zero counts give inf/NaN, which the caller must handle.
    """
    dd, dp = death_counts(c)
    with np.errstate(divide="ignore", invalid="ignore"):
        logs, variances = [], []
        for b in (1, 0):  # driver as subject, other occupant's attribute fixed at b
            num = np.log(dd[..., 1, b]) - np.log(dp[..., 1, b])
            den = np.log(dd[..., 0, b]) - np.log(dp[..., 0, b])
            logs.append(num - den)
            variances.append(
                1 / dd[..., 1, b] + 1 / dp[..., 1, b] + 1 / dd[..., 0, b] + 1 / dp[..., 0, b]
            )
        for a in (1, 0):  # other occupant as subject, driver's attribute fixed at a
            num = np.log(dp[..., a, 1]) - np.log(dd[..., a, 1])
            den = np.log(dp[..., a, 0]) - np.log(dd[..., a, 0])
            logs.append(num - den)
            variances.append(
                1 / dp[..., a, 1] + 1 / dd[..., a, 1] + 1 / dp[..., a, 0] + 1 / dd[..., a, 0]
            )
    return np.stack(logs, axis=-1), np.stack(variances, axis=-1)


def dpc_combined(c: np.ndarray) -> np.ndarray:
    """Inverse-variance weighted mean of the four component log RRs (NaN if any is undefined)."""
    logs, var = dpc_components(c)
    with np.errstate(divide="ignore", invalid="ignore"):
        w = 1 / var
        est = (w * logs).sum(axis=-1) / w.sum(axis=-1)
    ok = np.isfinite(logs).all(axis=-1) & np.isfinite(var).all(axis=-1)
    return np.where(ok, est, np.nan)


def reclassify(c: np.ndarray, f: float) -> np.ndarray:
    """Expected cell counts if a fraction ``f`` of survivors coded x=1 truly had x=0.

    Applied independently to the driver and the other occupant (deaths keep their coded
    status).  Works on any array whose last four axes are [x_d, k_d, x_p, k_p].
    """
    if not 0 <= f < 1:
        raise ValueError("f must be in [0, 1)")
    out = np.array(c, dtype=float, copy=True)
    moved = f * out[..., 1, 0, :, :]
    out[..., 1, 0, :, :] -= moved
    out[..., 0, 0, :, :] += moved
    moved = f * out[..., :, :, 1, 0]
    out[..., :, :, 1, 0] -= moved
    out[..., :, :, 0, 0] += moved
    return out


def bootstrap_counts(
    pairs: pd.DataFrame, n_boot: int, rng: np.random.Generator, cluster: str | None = None
) -> np.ndarray:
    """Bootstrap replicates of the 16-cell table, shape (n_boot, 2, 2, 2, 2).

    ``cluster=None`` resamples vehicles: because the statistic depends on vehicles only
    through their cell, this is exactly a multinomial draw of the 16 cell counts.  With a
    cluster column (crash), whole crashes are resampled.
    """
    idx = cell_index(pairs)
    if cluster is None:
        n = len(idx)
        p = np.bincount(idx, minlength=16) / n
        return rng.multinomial(n, p, size=n_boot).reshape(n_boot, 2, 2, 2, 2).astype(float)
    codes, uniq = pd.factorize(pairs[cluster])
    per_cluster = np.zeros((len(uniq), 16))
    np.add.at(per_cluster, (codes, idx), 1.0)
    nc = len(uniq)
    out = np.empty((n_boot, 16))
    for b in range(n_boot):
        w = np.bincount(rng.integers(0, nc, nc), minlength=nc)
        out[b] = w @ per_cluster
    return out.reshape(n_boot, 2, 2, 2, 2)


def _pct_ci(x: np.ndarray, level: float = 0.95) -> tuple[float, float, float]:
    """Percentile CI of finite replicates and the share of degenerate replicates."""
    ok = np.isfinite(x)
    if ok.sum() < 0.9 * len(x):
        return np.nan, np.nan, float(1 - ok.mean())
    lo, hi = np.quantile(x[ok], [(1 - level) / 2, (1 + level) / 2])
    return float(lo), float(hi), float(1 - ok.mean())


def dpc_analysis(
    pairs: pd.DataFrame,
    label: str,
    attribute_label: str,
    rng: np.random.Generator,
    n_boot: int = N_BOOT,
    fractions: Sequence[float] = (0.0,),
) -> pd.DataFrame:
    """DPC estimates (four components + combined) with vehicle and crash bootstrap CIs.

    ``fractions`` > 0 apply the closed-form survivor reclassification of :func:`reclassify`
    to the observed table and to every bootstrap replicate.
    """
    c = cell_counts(pairs)
    boot_v = bootstrap_counts(pairs, n_boot, rng)
    boot_c = bootstrap_counts(pairs, n_boot, rng, cluster="crash_id")
    dd, dp = death_counts(c)
    n_contrib = int(((pairs["k_d"] + pairs["k_p"]) > 0).sum())
    rows = []
    for f in fractions:
        cf = reclassify(c, f)
        logs, var = dpc_components(cf)
        comb = dpc_combined(cf)
        bv = dpc_combined(reclassify(boot_v, f))
        bc = dpc_combined(reclassify(boot_c, f))
        bv_comp, _ = dpc_components(reclassify(boot_v, f))
        entries = [(name, logs[i], var[i], bv_comp[:, i]) for i, name in enumerate(COMPONENTS)]
        entries.append(("combined (inverse-variance weighted)", comb, np.nan, bv))
        for name, lg, v, boot in entries:
            lo, hi, degenerate = _pct_ci(boot)
            rec = {
                "analysis": label,
                "attribute_x1": attribute_label,
                "misreport_fraction": f,
                "component": name,
                "rr_x1_vs_x0": float(np.exp(lg)),
                "rr_low": float(np.exp(lo)),
                "rr_high": float(np.exp(hi)),
                "reduction_1_minus_rr": float(1 - np.exp(lg)),
                "reduction_low": float(1 - np.exp(hi)),
                "reduction_high": float(1 - np.exp(lo)),
                "se_log_poisson": float(np.sqrt(v)) if np.isfinite(v) else np.nan,
                "boot_degenerate_share": degenerate,
                "n_pairs": len(pairs),
                "n_pairs_with_death": n_contrib,
            }
            if name.startswith("combined"):
                clo, chi, _ = _pct_ci(bc)
                rec["rr_low_crash_boot"] = float(np.exp(clo))
                rec["rr_high_crash_boot"] = float(np.exp(chi))
            rows.append(rec)
    out = pd.DataFrame(rows)
    out["tipping_point_f"] = dpc_tipping_point(c) if len(fractions) > 1 else np.nan
    out.attrs["counts"] = {
        "cells": c.astype(int).tolist(),
        "driver_deaths[x_d][x_p]": dd.astype(int).tolist(),
        "other_deaths[x_d][x_p]": dp.astype(int).tolist(),
    }
    return out


def dpc_count_table(pairs: pd.DataFrame, label: str, attribute_label: str) -> pd.DataFrame:
    """Pair types with vehicles and deaths (the DPC input, for transparency)."""
    c = cell_counts(pairs)
    dd, dp = death_counts(c)
    rows = []
    for xd in (1, 0):
        for xp in (1, 0):
            rows.append(
                {
                    "analysis": label,
                    "attribute_x1": attribute_label,
                    "driver_x": xd,
                    "other_x": xp,
                    "vehicles": int(c[xd, :, xp, :].sum()),
                    "driver_deaths": int(dd[xd, xp]),
                    "other_deaths": int(dp[xd, xp]),
                    "both_died": int(c[xd, 1, xp, 1]),
                }
            )
    return pd.DataFrame(rows)


def dpc_tipping_point(c: np.ndarray, f_max: float = 0.95) -> float:
    """Smallest misreporting fraction f at which the combined DPC risk ratio reaches 1.

    NaN if the estimate does not cross 1 on [0, f_max]; 0 if it is already >= 1.
    """

    def g(f: float) -> float:
        return float(dpc_combined(reclassify(c, f)))

    if not np.isfinite(g(0.0)):
        return float("nan")
    if g(0.0) >= 0:
        return 0.0
    if g(f_max) < 0:
        return float("nan")
    return float(optimize.brentq(g, 0.0, f_max, xtol=1e-6))


# --------------------------------------------------------------------------------------
# Matched-pair odds ratio (closed form) and misreporting
# --------------------------------------------------------------------------------------
def matched_pair_or(sets: pd.DataFrame, f: float = 0.0, level: float = 0.95) -> dict:
    """OR (unbelted vs belted) from two-occupant vehicles with exactly one death.

    n10 = unbelted died & belted survived; n01 = belted died & unbelted survived;
    n00 = both belted, one died.  The conditional-likelihood estimate is n10 / n01 with
    SE(log OR) = sqrt(1/n10 + 1/n01).  Under misreporting (a fraction f of belted survivors
    truly unbelted): n10 -> (1 - f) n10, n01 -> n01 + f n00 (expected counts).
    """
    g = sets.groupby("vehicle_id")
    size = g["killed"].transform("size")
    deaths = g["killed"].transform("sum")
    two = sets.loc[(size == 2) & (deaths == 1)]
    dead = two.loc[two["killed"] == 1].set_index("vehicle_id")["unbelted"]
    alive = two.loc[two["killed"] == 0].set_index("vehicle_id")["unbelted"]
    j = pd.DataFrame({"dead_unb": dead, "alive_unb": alive.reindex(dead.index)})
    n10 = float(((j.dead_unb == 1) & (j.alive_unb == 0)).sum())
    n01 = float(((j.dead_unb == 0) & (j.alive_unb == 1)).sum())
    n00 = float(((j.dead_unb == 0) & (j.alive_unb == 0)).sum())
    n11 = float(((j.dead_unb == 1) & (j.alive_unb == 1)).sum())
    a, b = (1 - f) * n10, n01 + f * n00
    # Tipping point: (1 - f) n10 = n01 + f n00  <=>  f* = (n10 - n01) / (n10 + n00).
    f_star = (n10 - n01) / (n10 + n00) if n10 + n00 > 0 else np.nan
    z = stats.norm.ppf(0.5 + level / 2)
    lor = np.log(a / b)
    se = np.sqrt(1 / a + 1 / b)
    return {
        "misreport_fraction": f,
        "n10_unbelted_died_belted_survived": n10,
        "n01_belted_died_unbelted_survived": n01,
        "n00_both_belted": n00,
        "n11_both_unbelted": n11,
        "or_unbelted_vs_belted": float(np.exp(lor)),
        "or_low": float(np.exp(lor - z * se)),
        "or_high": float(np.exp(lor + z * se)),
        "n_vehicles": len(j),
        "tipping_point_f": float(f_star),
    }


def reclassify_rows(df: pd.DataFrame, f: float, u: np.ndarray) -> pd.DataFrame:
    """Reclassify belted survivors to unbelted where the uniform draw ``u`` < f.

    Using one vector ``u`` for every f nests the reclassified sets (those flipped at 5% are
    also flipped at 10%), so differences between fractions are not Monte Carlo noise.
    """
    out = df.copy()
    cand = ((out["unbelted"] == 0) & (out["killed"] == 0)).to_numpy()
    out.loc[cand & (u < f), "unbelted"] = 1
    return out


# --------------------------------------------------------------------------------------
# Driver
# --------------------------------------------------------------------------------------
def _save(
    df: pd.DataFrame,
    name: str,
    description: str,
    method: str,
    population: str,
    extra: dict | None = None,
) -> None:
    save_table(
        df,
        MODULE,
        name,
        description=description,
        population=population,
        unit="person within vehicle (matched set = vehicle)",
        outcome="killed (died within 30 days)",
        method=method,
        inputs=[INPUT],
        extra=extra,
    )


LPV_POP = (
    "FARS 2016-2024 occupants (driver/passenger) of in-transport light passenger vehicles, "
    "seat front-left/front-other/second row, age 13+, belted or unbelted, known outcome"
)


def clogit_models(
    elig: pd.DataFrame, rng: np.random.Generator, complete_vehicles: set | None = None
) -> dict[str, CLResult]:
    """Main, coarse-age (frailty), belt-by-seat-row and sensitivity conditional logits.

    Sensitivities: survivor misreporting (seeded, nested random reclassification) and, if
    ``complete_vehicles`` is given, restriction to vehicles none of whose occupants has
    unknown restraint (restraint unknown-ness is itself severity-dependent).
    """
    sets = matched_sets(elig)["discordant"].sort_values(["vehicle_id", "PER_NO"])
    y = sets["killed"].to_numpy()
    groups = sets["vehicle_id"].to_numpy()
    clusters = sets["crash_id"].to_numpy()
    out: dict[str, CLResult] = {}
    x_main = occupant_covariates(sets)
    out["main"] = fit_clogit(y, x_main, groups, clusters)
    log.info("clogit main done: %s", out["main"].info)
    x_coarse = occupant_covariates(sets, bands=AGE_COARSE, ref=AGE_COARSE_REF)
    out["coarse_age"] = fit_clogit(y, x_coarse, groups, clusters)
    log.info("clogit coarse done")
    x_seat = x_main.copy()
    x_seat["unbelted:seat[second_row]"] = x_seat["unbelted"] * x_seat["seat[second_row]"]
    start = np.append(out["main"].params, 0.0)
    out["belt_by_seat_row"] = fit_clogit(y, x_seat, groups, clusters, start=start)
    log.info("clogit seat interaction done")
    u = rng.random(len(sets))
    for f in MISREPORT_FRACTIONS:
        if f == 0:
            continue
        rs = reclassify_rows(sets, f, u)
        x_f = occupant_covariates(rs)
        if list(x_f.columns) != list(x_main.columns):
            raise AssertionError("covariate columns changed under reclassification")
        out[f"misreport_{f:.2f}"] = fit_clogit(y, x_f, groups, clusters, start=out["main"].params)
        log.info("clogit misreport f=%.2f done", f)
    if complete_vehicles is not None:
        cc = matched_sets(elig.loc[elig["vehicle_id"].isin(complete_vehicles)])["discordant"]
        cc = cc.sort_values(["vehicle_id", "PER_NO"])
        x_cc = occupant_covariates(cc)
        start = out["main"].params if list(x_cc.columns) == list(x_main.columns) else None
        out["complete_restraint_vehicles"] = fit_clogit(
            cc["killed"].to_numpy(),
            x_cc,
            cc["vehicle_id"].to_numpy(),
            cc["crash_id"].to_numpy(),
            start=start,
        )
        log.info("clogit complete-restraint vehicles done")
    return out


def motorcycle_analyses(df: pd.DataFrame, rng: np.random.Generator) -> dict:
    """Helmet: DPC for operator/passenger pairs and a conditional logit within motorcycles."""
    mc = df.loc[
        df["ptype"].isin(OCCUPANT_PTYPES)
        & (df["body"] == "motorcycle")
        & df["helmet"].isin(["helmet", "none"])
        & df["killed"].notna()
    ].copy()
    mc["killed"] = mc["killed"].astype(int)
    mc["helmeted"] = (mc["helmet"] == "helmet").astype(int)
    mc["unhelmeted"] = 1 - mc["helmeted"]
    pairs = pair_frame(mc, "helmeted", mc["ptype"] == "driver", mc["ptype"] == "passenger")
    res: dict = {"pairs": pairs, "n_riders": len(mc)}
    res["dpc"] = dpc_analysis(pairs, "motorcycle_helmet", "helmet worn", rng)
    res["dpc_counts"] = dpc_count_table(pairs, "motorcycle_helmet", "helmet worn")
    disc = matched_sets(mc)["discordant"].sort_values(["vehicle_id", "PER_NO"])
    known_age = disc["age"].notna()
    disc = disc.loc[known_age]
    disc = matched_sets(disc)["discordant"]
    x = occupant_covariates(
        disc.assign(passenger=(disc["ptype"] == "passenger").astype(float)),
        exposure="unhelmeted",
        bands=((("0-24", 0, 24), ("25-44", 25, 44), ("45-64", 45, 64), ("65+", 65, 200))),
        ref="25-44",
        seat=False,
    )
    x["passenger"] = (disc["ptype"] == "passenger").astype(float).to_numpy()
    res["clogit"] = fit_clogit(
        disc["killed"].to_numpy(), x, disc["vehicle_id"].to_numpy(), disc["crash_id"].to_numpy()
    )
    res["clogit_helmet_sets"] = exposure_set_counts(disc, "unhelmeted")
    return res


MAX_AGE_GAP_SEX_DPC = 5


def frailty_dpc(elig: pd.DataFrame, rng: np.random.Generator) -> list[pd.DataFrame]:
    """DPC among both-belted driver / right-front pairs (frailty comparisons).

    * age 65+ vs 25-44, both occupants of the same sex (sex differs systematically between
      driver and passenger seats and would otherwise confound the age comparison);
    * female vs male, occupants within 5 years of age of each other (otherwise the older
      partner -- more often the male driver in couples -- confounds the sex comparison).
    """
    belted = elig.loc[elig["unbelted"] == 0].copy()
    drv = (belted["ptype"] == "driver") & (belted["SEAT_POS"] == SEAT_POS_DRIVER)
    rf = (belted["ptype"] == "passenger") & (belted["SEAT_POS"] == SEAT_POS_RIGHT_FRONT)
    out = []
    known_sex = belted["sex"].isin(["male", "female"])
    age_ok = (belted["age"].between(25, 44) | (belted["age"] >= 65)) & known_sex
    belted["older65"] = (belted["age"] >= 65).astype(int)
    pairs_age = pair_frame(belted, "older65", drv & age_ok, rf & age_ok, carry=("sex",))
    pairs_age = pairs_age.loc[pairs_age["sex_d"] == pairs_age["sex_p"]]
    out.append(dpc_analysis(pairs_age, "age_65plus_vs_25_44_both_belted_same_sex", "age 65+", rng))
    belted["female"] = (belted["sex"] == "female").astype(int)
    pairs_sex = pair_frame(belted, "female", drv & known_sex, rf & known_sex, carry=("age",))
    gap = (pairs_sex["age_d"] - pairs_sex["age_p"]).abs()
    pairs_sex = pairs_sex.loc[gap <= MAX_AGE_GAP_SEX_DPC]
    out.append(dpc_analysis(pairs_sex, "female_vs_male_both_belted_age_gap_le5", "female", rng))
    return out


def belt_effect_table(
    dpc: pd.DataFrame, cl: dict[str, CLResult], mp: pd.DataFrame, dpc_cc: pd.DataFrame
) -> pd.DataFrame:
    """Machine-readable belt estimates for the policy simulator.

    The first two rows are the primary estimand (Evans DPC); every other row is either a
    different estimator (within-vehicle ORs, which are not risk ratios) or a sensitivity
    analysis, flagged by its estimand suffix.
    """
    rows = []
    for f in MISREPORT_FRACTIONS:
        r = dpc.loc[
            (dpc["misreport_fraction"] == f) & dpc["component"].str.startswith("combined")
        ].iloc[0]
        sfx = "" if f == 0 else f"_misreport_f{round(f * 100):02d}"
        method = "evans_double_pair_comparison_driver_rf_pairs_vehicle_bootstrap" + (
            "" if f == 0 else f"_closed_form_reclassification_f={f:.2f}"
        )
        rows.append(
            {
                "estimand": "fatality_rr_belted_vs_unbelted_given_fatal_crash" + sfx,
                "estimate": r["rr_x1_vs_x0"],
                "low": r["rr_low"],
                "high": r["rr_high"],
                "method": method,
                "n_vehicles": int(r["n_pairs_with_death"]),
            }
        )
        rows.append(
            {
                "estimand": "fatality_risk_reduction_belt_given_fatal_crash" + sfx,
                "estimate": r["reduction_1_minus_rr"],
                "low": r["reduction_low"],
                "high": r["reduction_high"],
                "method": method,
                "n_vehicles": int(r["n_pairs_with_death"]),
            }
        )
    for key, res in cl.items():
        if key == "main":
            sfx, method_sfx = "", ""
        elif key.startswith("misreport_"):
            pct = round(float(key.split("_")[1]) * 100)
            sfx, method_sfx = f"_misreport_f{pct:02d}", "_seeded_nested_random_reclassification"
        elif key == "complete_restraint_vehicles":
            sfx = method_sfx = "_complete_restraint_vehicles"
        else:
            continue
        t = res.table.set_index("term").loc["unbelted"]
        rows.append(
            {
                "estimand": "within_vehicle_or_killed_unbelted_vs_belted" + sfx,
                "estimate": t["odds_ratio"],
                "low": t["or_low"],
                "high": t["or_high"],
                "method": "conditional_logit_vehicle_strata_age_sex_seat_crash_robust_ci"
                + method_sfx,
                "n_vehicles": res.info["n_sets"],
            }
        )
    r = dpc_cc.loc[dpc_cc["component"].str.startswith("combined")].iloc[0]
    for est, val, lo, hi in (
        (
            "fatality_rr_belted_vs_unbelted_given_fatal_crash",
            r["rr_x1_vs_x0"],
            r["rr_low"],
            r["rr_high"],
        ),
        (
            "fatality_risk_reduction_belt_given_fatal_crash",
            r["reduction_1_minus_rr"],
            r["reduction_low"],
            r["reduction_high"],
        ),
    ):
        rows.append(
            {
                "estimand": est + "_complete_restraint_vehicles",
                "estimate": val,
                "low": lo,
                "high": hi,
                "method": "evans_double_pair_comparison_vehicles_without_unknown_restraint",
                "n_vehicles": int(r["n_pairs_with_death"]),
            }
        )
    for _, r in mp.iterrows():
        f = r["misreport_fraction"]
        sfx = "" if f == 0 else f"_misreport_f{round(f * 100):02d}"
        rows.append(
            {
                "estimand": "matched_pair_or_killed_unbelted_vs_belted" + sfx,
                "estimate": r["or_unbelted_vs_belted"],
                "low": r["or_low"],
                "high": r["or_high"],
                "method": "two_occupant_vehicles_one_death_conditional_ml_closed_form",
                "n_vehicles": int(r["n_vehicles"]),
            }
        )
    return pd.DataFrame(rows)


def run(years: Sequence[int] | None = None, n_boot: int = N_BOOT) -> dict:
    """Run every matched analysis and write tables to outputs/tables/matched/."""
    rng = np.random.default_rng(config.RANDOM_SEED)
    df = load_fars_occupants(years)
    elig, flow = lpv_flow_and_eligible(df)
    _save(
        flow,
        "population_flow",
        "Eligibility flow for the within-vehicle analyses",
        "Counts of persons, deaths, vehicles and crashes after each restriction",
        LPV_POP,
    )

    # Vehicles none of whose occupants has unknown restraint (sensitivity analyses).
    occ = df["ptype"].isin(OCCUPANT_PTYPES)
    unknown_veh = set(df.loc[occ & (df["restraint"] == "unknown"), "vehicle_id"])
    complete = set(elig["vehicle_id"]) - unknown_veh

    # 1. Conditional logistic regression ------------------------------------------------
    cl = clogit_models(elig, rng, complete_vehicles=complete)
    sets = matched_sets(elig)["discordant"]
    belt_sets = exposure_set_counts(sets, "unbelted")
    cl_tab = pd.concat(
        [
            r.table.assign(model=k, **{f"info_{i}": v for i, v in r.info.items()})
            for k, r in cl.items()
        ],
        ignore_index=True,
    )
    _save(
        cl_tab,
        "clogit_coefficients",
        "Within-vehicle conditional logistic regression of death: odds ratios (models: main = "
        "unbelted + 8 age bands + sex + seat; coarse_age = 4 age bands; belt_by_seat_row = main + "
        "unbelted x second row; misreport_f = main after seeded random reclassification of a "
        "fraction f of belted survivors to unbelted)",
        "statsmodels ConditionalLogit (groups = vehicle), BFGS; CIs from crash-cluster-robust "
        "sandwich (primary) and model-based information",
        LPV_POP + "; vehicles with >= 2 eligible occupants and discordant outcomes",
        extra={"belt_discordant_sets": belt_sets},
    )

    # 2. Double-pair comparison for belts -------------------------------------------------
    elig["belted"] = 1 - elig["unbelted"]
    drv = (elig["ptype"] == "driver") & (elig["SEAT_POS"] == SEAT_POS_DRIVER)
    rf = (elig["ptype"] == "passenger") & (elig["SEAT_POS"] == SEAT_POS_RIGHT_FRONT)
    pairs = pair_frame(elig, "belted", drv, rf)
    dpc = dpc_analysis(pairs, "belt_driver_rf", "belted", rng, n_boot, MISREPORT_FRACTIONS)
    dpc_counts = dpc_count_table(pairs, "belt_driver_rf", "belted")
    pairs_cc = pairs.loc[pairs["vehicle_id"].isin(complete)]
    dpc_cc = dpc_analysis(
        pairs_cc, "belt_driver_rf_complete_restraint_vehicles", "belted", rng, n_boot
    )
    dpc_counts_cc = dpc_count_table(
        pairs_cc, "belt_driver_rf_complete_restraint_vehicles", "belted"
    )

    # 3. Matched-pair OR (closed form) under misreporting --------------------------------
    mp = pd.DataFrame([matched_pair_or(sets, f) for f in MISREPORT_FRACTIONS])
    mp.insert(0, "population", "all eligible vehicles")
    mp_cc = matched_pair_or(sets.loc[sets["vehicle_id"].isin(complete)], 0.0)
    mp = pd.concat(
        [mp, pd.DataFrame([{"population": "complete-restraint vehicles", **mp_cc}])],
        ignore_index=True,
    )

    # 4. Frailty (age/sex) DPC and motorcycle helmets ------------------------------------
    frailty = frailty_dpc(elig, rng)
    moto = motorcycle_analyses(df, rng)

    dpc_all = pd.concat([dpc, dpc_cc, *frailty, moto["dpc"]], ignore_index=True)
    counts_all = pd.concat(
        [
            dpc_counts,
            dpc_counts_cc,
            *[dpc_count_table_from(f) for f in frailty],
            moto["dpc_counts"],
        ],
        ignore_index=True,
    )
    _save(
        dpc_all,
        "double_pair_comparison",
        "Evans double-pair comparison risk ratios (x=1 vs x=0) for driver / right-front "
        "passenger pairs (belts; age 65+ vs 25-44 and female vs male among both-belted pairs) "
        "and motorcycle operator / passenger pairs (helmet); misreport_fraction > 0 = closed-form "
        "reclassification of a fraction of 'belted' survivors to unbelted",
        "Four component ratios of death ratios and their inverse-variance weighted geometric "
        "mean; percentile bootstrap over vehicles (exact multinomial on 16 cells, "
        f"{n_boot} replicates) and over crashes",
        "FARS 2016-2024 vehicles with exactly one eligible driver (seat 11) and one eligible "
        "right-front passenger (seat 13) / motorcycles with one operator and one passenger",
    )
    _save(
        counts_all,
        "double_pair_counts",
        "Pair types, vehicles and deaths entering the DPC",
        "Counts",
        "As double_pair_comparison",
    )
    _save(
        mp,
        "matched_pair_or_misreporting",
        "Closed-form matched-pair OR (unbelted vs belted) in two-occupant vehicles with one "
        "death, under reclassification of a fraction f of belted survivors to unbelted",
        "Conditional ML for 1:1 matched pairs: OR = n10/n01; expected counts under "
        "misreporting n10*(1-f), n01 + f*n00",
        LPV_POP + "; vehicles with exactly 2 eligible occupants and exactly one death",
    )
    moto_tab = moto["clogit"].table.assign(
        **{f"info_{k}": v for k, v in moto["clogit"].info.items()}
    )
    _save(
        moto_tab,
        "clogit_motorcycle_helmet",
        "Within-motorcycle conditional logit of death: unhelmeted vs helmeted, age band, sex, "
        "passenger vs operator",
        "statsmodels ConditionalLogit (groups = motorcycle); crash-cluster-robust CIs",
        "FARS 2016-2024 motorcycle operators/passengers with helmet coded helmet/none, known "
        "age and outcome; motorcycles with >= 2 riders and discordant outcomes",
        extra={"helmet_discordant_sets": moto["clogit_helmet_sets"]},
    )
    belt = belt_effect_table(dpc, cl, mp.loc[mp["population"] == "all eligible vehicles"], dpc_cc)
    _save(
        belt,
        "belt_effect",
        "Machine-readable belt-use estimates (FARS within-vehicle designs) for the policy "
        "simulator.  All estimates are conditional on a crash severe enough to kill an "
        "occupant of the vehicle (fatal crash); rows with _misreport_fXX are sensitivity "
        "analyses, not alternative primary estimates",
        "See method column; primary = fatality_risk_reduction_belt_given_fatal_crash (Evans DPC)",
        LPV_POP,
    )
    digest = {
        "flow": flow.to_dict(orient="records"),
        "belt_sets": belt_sets,
        "dpc_belt_counts": dpc.attrs.get("counts"),
        "clogit_info": {k: v.info for k, v in cl.items()},
        "n_motorcycle_riders": moto["n_riders"],
        "n_motorcycle_pairs": len(moto["pairs"]),
        "helmet_sets": moto["clogit_helmet_sets"],
    }
    save_json(digest, MODULE, "key_numbers")
    return {
        "flow": flow,
        "clogit": cl_tab,
        "dpc": dpc_all,
        "dpc_counts": counts_all,
        "matched_pair_or": mp,
        "motorcycle_clogit": moto_tab,
        "belt_effect": belt,
    }


def dpc_count_table_from(dpc_result: pd.DataFrame) -> pd.DataFrame:
    """Rebuild the transparent count table from a DPC result's stored cell counts."""
    c = np.asarray(dpc_result.attrs["counts"]["cells"], dtype=float)
    dd, dp = death_counts(c)
    label = dpc_result["analysis"].iloc[0]
    attr = dpc_result["attribute_x1"].iloc[0]
    rows = []
    for xd in (1, 0):
        for xp in (1, 0):
            rows.append(
                {
                    "analysis": label,
                    "attribute_x1": attr,
                    "driver_x": xd,
                    "other_x": xp,
                    "vehicles": int(c[xd, :, xp, :].sum()),
                    "driver_deaths": int(dd[xd, xp]),
                    "other_deaths": int(dp[xd, xp]),
                    "both_died": int(c[xd, 1, xp, 1]),
                }
            )
    return pd.DataFrame(rows)
