"""Confounding decomposition of crash-severity associations (RQ4, docs/research_plan.md).

Research question
    How much of the excess severity of night-time crashes (21:00-05:59 vs 06:00-20:59) is
    statistically accounted for by calendar/area, weekend, light condition, the road
    environment, alcohol, speeding, the driver-age / vehicle mix and crash configuration?
    The same accounting is done for crashes in rural (vs urban) CRSS PSUs, weekend (vs
    weekday) crashes and crashes involving a driver aged 65+ (vs none).

Population
    CRSS police-reported crashes 2016-2024 with known maximum severity (MAX_SEV 0-4;
    n = 458,907).  Unit: crash.  Outcomes: ``fatal`` (K vs O/C/B/A) and ``ka`` (K or A vs
    O/C/B).

Method
    For every subset S of the covariate blocks of an exposure, a survey-weighted logistic
    model (exposure + blocks in S) is fitted and the exposure's *standardised* risk ratio is
    computed from predictive margins: the weighted mean predicted risk with every crash set
    to "exposed" divided by the same with every crash set to "reference" (g-computation over
    the observed covariate distribution of all crashes).  Unlike odds ratios, standardised
    risk ratios are collapsible, so a change between nested models reflects the covariates,
    not non-collapsibility.  With all 2^k subsets available:

    * sequential tables follow any ordering of blocks (the pre-specified order, light
      excluded, behaviours first, light last, reverse), reporting the RR, the risk
      difference, and the share of the crude log-RR retained, log RR(S) / log RR(crude);
    * a Shapley decomposition averages each block's reduction of the log-RR over all k!
      orderings (exact, from the 2^k subsets); the block contributions plus the retained
      share sum to 1;
    * every quantity has a design-based 95% CI.  Each margin is linearised (Taylor; coefficient
      and covariate-distribution variability), its influence is summed within the 67 variance
      PSUs, and any smooth function of margins from *different* models then has a variance
      from the same 25-stratum / 67-PSU design (t reference, 42 df).

    Computation uses an exact sufficient-statistic compression: the design matrix depends on
    categorical covariates only, so the weighted pseudo-likelihood, the PSU totals of the
    scores and of every margin influence are unchanged when rows that share covariate pattern,
    PSU and outcome are merged into one cell carrying the summed weight (the ridge is rescaled
    so the penalised fit is identical; verified in tests/test_confounding.py).

Light condition and night
    Darkness is part of what "night" is: about 94% of night crashes (weighted) are in darkness
    and only ~2.5% are coded daylight (``night_light_overlap``), whereas 81% of daytime crashes
    are in daylight.  Adjusting for light therefore (i) removes the part of the night
    association that runs through darkness itself, and (ii) relies on the logistic model to
    extrapolate the night effect into night x daylight cells that barely exist.  The
    module reports results with and without the light block, the night-by-light overlap table,
    and a within-darkness comparison (night vs evening/early-morning crashes in the dark),
    which needs no such extrapolation.

Justified interpretation
    "Conditional on a police-reported crash, crashes at night are fatal X times as often as
    daytime crashes; after standardising for blocks S the ratio is Y, i.e. the blocks
    statistically account for Z% of the crude log risk ratio."

Not justified
    Causal mediation ("Z% of the night effect is caused by alcohol"): the ordering of blocks
    cannot be verified, several blocks are plausibly mediators (light, behaviours,
    configuration) rather than confounders, behaviours are police-recorded with severity-
    dependent ascertainment (RQ3), and there is no exposure (traffic volume) information.
    Nothing here concerns the probability of a crash occurring.  CRSS ``urbanicity`` is a
    PSU-level (area) classification from 21 rural PSUs, not the rurality of the crash site.
"""

from __future__ import annotations

import itertools
import logging
import math
import pickle
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from nhtsa_stats import config
from nhtsa_stats.analysis import data, specs
from nhtsa_stats.analysis.survey import (
    MarginSet,
    ModelSpec,
    SurveyDesign,
    SurveyLogit,
    proportion_table,
)
from nhtsa_stats.processing.harmonize import MODEL_ALLOWED_TIMINGS, assert_no_leakage
from nhtsa_stats.reporting.io import save_json, save_table

log = logging.getLogger(__name__)
MODULE = "confounding"
OUTCOMES: tuple[str, ...] = ("fatal", "ka")
# Same tiny L2 penalty as the severity module (mean-1 normalised weights): it keeps
# coefficients of zero-event levels finite and shrinks any level with >= 1,000 crashes by <1%.
RIDGE = 0.01
CRSS_INPUT = "data/processed/crss_crash.parquet"
POPULATION = "CRSS police-reported crashes 2016-2024 with known maximum severity (MAX_SEV 0-4)"

# --------------------------------------------------------------------------------------
# Covariate blocks and exposures
# --------------------------------------------------------------------------------------
BLOCKS: dict[str, tuple[str, ...]] = {
    "calendar_area": ("YEAR", "region", "urbanicity"),
    "calendar_region": ("YEAR", "region"),
    "weekend": ("weekend",),
    "time_of_day": ("tod",),
    "time": ("tod", "weekend"),
    "light": ("light",),
    "road_environment": (
        "speed_limit",
        "interstate",
        "junction",
        "work_zone",
        "weather",
        "surface",
    ),
    "alcohol": ("alcohol_im",),
    "speeding": ("speeding",),
    "driver_vehicle_mix": ("young_driver", "older_driver", "any_motorcycle", "any_heavy_truck"),
    "driver_vehicle_mix_other": ("young_driver", "any_motorcycle", "any_heavy_truck"),
    "configuration": ("crash_type", "n_vehicles"),
}
BEHAVIOURS = ("alcohol", "speeding")
NIGHT_COLUMN = "night_period"
NIGHT_LEVELS = ["day", "night", "unknown"]
DARK_LEVELS = ("dark_lighted", "dark_not_lighted", "dark_unknown_lighting")


@dataclass(frozen=True)
class Exposure:
    """A binary contrast (``exposed`` vs ``reference``) and its ordered covariate blocks.

    Further levels of ``column`` (e.g. 'unknown') stay in the model as their own category and
    in the standardisation population; they are never merged into the reference.
    """

    name: str
    column: str
    reference: str
    exposed: str
    blocks: tuple[str, ...]  # canonical (pre-specified) order
    label: str

    def variables(self, blocks: Iterable[str]) -> list[str]:
        out: list[str] = []
        for b in blocks:
            out += [v for v in BLOCKS[b] if v not in out]
        return out


EXPOSURES: dict[str, Exposure] = {
    "night": Exposure(
        "night",
        NIGHT_COLUMN,
        "day",
        "night",
        (
            "calendar_area",
            "weekend",
            "light",
            "road_environment",
            "alcohol",
            "speeding",
            "driver_vehicle_mix",
            "configuration",
        ),
        "Night (21:00-05:59) vs day (06:00-20:59); time-of-day bands are not adjusted for "
        "because they define the exposure",
    ),
    "rural": Exposure(
        "rural",
        "urbanicity",
        "urban",
        "rural",
        (
            "calendar_region",
            "time",
            "light",
            "road_environment",
            "alcohol",
            "speeding",
            "driver_vehicle_mix",
            "configuration",
        ),
        "Crash in a rural vs urban CRSS PSU (area-level URBANICITY, not crash-site rurality)",
    ),
    "weekend": Exposure(
        "weekend",
        "weekend",
        "no",
        "yes",
        (
            "calendar_area",
            "time_of_day",
            "light",
            "road_environment",
            "alcohol",
            "speeding",
            "driver_vehicle_mix",
            "configuration",
        ),
        "Weekend (Saturday/Sunday) vs weekday",
    ),
    "older_driver": Exposure(
        "older_driver",
        "older_driver",
        "no",
        "yes",
        (
            "calendar_area",
            "time",
            "light",
            "road_environment",
            "alcohol",
            "speeding",
            "driver_vehicle_mix_other",
            "configuration",
        ),
        "At least one driver aged 65+ vs no such driver (crashes with an unknown-age driver "
        "and no known 65+ driver form a separate 'unknown' level)",
    ),
}


def orderings(exposure: Exposure) -> dict[str, list[str]]:
    """Pre-specified block orderings used for the sequential tables."""
    canon = list(exposure.blocks)
    behaviours = [b for b in BEHAVIOURS if b in canon]
    out = {"primary": canon}
    if "light" in canon:
        no_light = [b for b in canon if b != "light"]
        out["primary_without_light"] = no_light
        out["light_last"] = [*no_light, "light"]
    out["behaviours_first"] = [*behaviours, *(b for b in canon if b not in behaviours)]
    out["reverse"] = canon[::-1]
    return out


# --------------------------------------------------------------------------------------
# Data
# --------------------------------------------------------------------------------------
def analysis_columns() -> list[str]:
    cols = {v for vs in BLOCKS.values() for v in vs}
    return sorted(cols | {"urbanicity", "weekend", "older_driver"})


def load_frame() -> tuple[pd.DataFrame, SurveyDesign]:
    """CRSS crashes with known severity, tri-state labels, and the night exposure column."""
    df, design = data.crss_crash(outcome="fatal", tri_state_cols=specs.CRASH_TRI)
    if df["ka"].isna().any():
        raise ValueError("fatal and ka must be known on the same crashes")
    df[NIGHT_COLUMN] = df["night"].map({1: "night", 0: "day"}).fillna("unknown").astype(object)
    df["YEAR"] = df["YEAR"].astype(int)
    keep = [*analysis_columns(), NIGHT_COLUMN, "night", "fatal", "ka"]
    df = df[keep].copy()
    df["fatal"] = df["fatal"].astype(float)
    df["ka"] = df["ka"].astype(float)
    # Categorical dtype (declared levels) makes cell compression and design matrices fast.
    for c in [*analysis_columns(), NIGHT_COLUMN]:
        df[c] = pd.Categorical(df[c], categories=declared_levels(c))
        if df[c].isna().any():
            raise ValueError(f"{c}: values outside the declared levels")
    return df, design


def declared_levels(var: str) -> list:
    return NIGHT_LEVELS if var == NIGHT_COLUMN else list(specs.CRASH_LEVELS[var])


def category_levels(df: pd.DataFrame, var: str) -> list:
    """Declared levels present in ``df`` (declared order; the first present is the reference)."""
    declared = declared_levels(var)
    present = set(pd.unique(np.asarray(df[var], dtype=object)))
    out = [lv for lv in declared if lv in present]
    extra = present - set(declared)
    if extra:
        raise ValueError(f"{var}: undeclared levels {sorted(map(str, extra))}")
    return out


def collapse_cells(
    df: pd.DataFrame, design: SurveyDesign, columns: Sequence[str], outcome: str
) -> tuple[pd.DataFrame, SurveyDesign]:
    """Merge rows sharing covariate values, variance PSU and outcome into weighted cells.

    For a model whose design matrix depends only on ``columns``, the weighted
    pseudo-likelihood and the PSU totals of scores and of predictive-margin influence
    functions are sums over rows, so they are identical on the cells (cell weight = sum of
    the rows' weights).  SurveyLogit normalises weights to mean 1, so the ridge must be
    multiplied by n_cells / n_rows to reproduce the row-level penalised fit exactly.
    The returned design keeps the full stratum/PSU universe.
    """
    keys = [*(_codes(df[c]) for c in columns), design.cluster, _codes(df[outcome])]
    combined = np.zeros(len(df), dtype=np.int64)
    for codes in keys:
        if (codes < 0).any():
            raise ValueError("missing values are not allowed in collapse keys")
        combined = combined * (int(codes.max()) + 1) + codes
        if combined.max() > 2**40:  # re-index to keep the mixed-radix key small
            combined = pd.factorize(combined)[0].astype(np.int64)
    _, first, inverse = np.unique(combined, return_index=True, return_inverse=True)
    weight = np.bincount(inverse, weights=design.weight)
    cells = df.iloc[first][[*columns, outcome]].reset_index(drop=True)
    cdesign = SurveyDesign(
        weight,
        design.stratum[first],
        design.cluster[first],
        design.cluster_stratum,
        design.lonely_psu,
    )
    return cells, cdesign


def _codes(s: pd.Series | np.ndarray) -> np.ndarray:
    if isinstance(s, pd.Series) and isinstance(s.dtype, pd.CategoricalDtype):
        return s.cat.codes.to_numpy(dtype=np.int64)
    return pd.factorize(np.asarray(s), sort=False)[0].astype(np.int64)


def cluster_design(design: SurveyDesign) -> SurveyDesign:
    """One row per variance PSU: ``vcov_total`` of PSU totals equals that of the rows."""
    g = design.n_clusters
    return SurveyDesign(
        np.ones(g),
        design.cluster_stratum.copy(),
        np.arange(g, dtype=np.int64),
        design.cluster_stratum,
        design.lonely_psu,
    )


# --------------------------------------------------------------------------------------
# Lattice of nested models
# --------------------------------------------------------------------------------------
@dataclass
class SubsetFit:
    """Standardised margins of one model; ``t_*`` are PSU totals of their influence."""

    blocks: frozenset[str]
    m_exposed: float
    m_reference: float
    t_exposed: np.ndarray
    t_reference: np.ndarray
    n_params: int
    n_cells: int
    converged: bool

    @property
    def log_rr(self) -> float:
        return float(np.log(self.m_exposed / self.m_reference))

    @property
    def t_log_rr(self) -> np.ndarray:
        return self.t_exposed / self.m_exposed - self.t_reference / self.m_reference


def subset_key(blocks: Iterable[str]) -> str:
    b = sorted(blocks)
    return "+".join(b) if b else "crude"


def fit_subset(
    df: pd.DataFrame,
    design: SurveyDesign,
    exposure: Exposure,
    blocks: Iterable[str],
    outcome: str,
    ridge: float = RIDGE,
) -> SubsetFit:
    """Exposure + covariate blocks -> standardised exposed / reference margins."""
    blocks = frozenset(blocks)
    covs = [exposure.column, *exposure.variables(sorted(blocks, key=exposure.blocks.index))]
    cells, cdesign = collapse_cells(df, design, covs, outcome)
    spec = ModelSpec(categorical={c: category_levels(df, c) for c in covs})
    for c, levels in spec.categorical.items():
        if isinstance(cells[c].dtype, pd.CategoricalDtype):
            cells[c] = cells[c].cat.set_categories(levels)
    model = SurveyLogit(spec, ridge=ridge * len(cells) / len(df))
    model.fit(cells, cells[outcome].to_numpy(dtype=float), cdesign)
    if not model.converged_:
        log.warning("%s/%s %s: model did not converge", exposure.name, outcome, sorted(blocks))
    col = exposure.column
    ms = model.margins(
        cells,
        {
            "exposed": lambda d: d.assign(**{col: exposure.exposed}),
            "reference": lambda d: d.assign(**{col: exposure.reference}),
        },
    )
    return SubsetFit(
        blocks=blocks,
        m_exposed=ms.values["exposed"],
        m_reference=ms.values["reference"],
        t_exposed=cdesign.cluster_totals(ms.influence["exposed"])[:, 0],
        t_reference=cdesign.cluster_totals(ms.influence["reference"])[:, 0],
        n_params=len(model.coef_),
        n_cells=len(cells),
        converged=bool(model.converged_),
    )


def fit_lattice(
    df: pd.DataFrame,
    design: SurveyDesign,
    exposure: Exposure,
    outcome: str,
    blocks: Sequence[str] | None = None,
) -> dict[frozenset[str], SubsetFit]:
    """Fit the model for every subset of ``blocks`` (default: all blocks of the exposure)."""
    blocks = list(exposure.blocks if blocks is None else blocks)
    out = {}
    for r in range(len(blocks) + 1):
        for subset in itertools.combinations(blocks, r):
            out[frozenset(subset)] = fit_subset(df, design, exposure, subset, outcome)
        log.info("%s/%s: %d-block subsets done", exposure.name, outcome, r)
    return out


def lattice_marginset(lattice: dict[frozenset[str], SubsetFit], design: SurveyDesign) -> MarginSet:
    """Log-RRs (``lr|key``) and risk differences (``rd|key``) of all subsets, jointly
    linearised on the PSU-level design (correct covariances across models)."""
    cd = cluster_design(design)
    values, infl = {}, {}
    for s, f in lattice.items():
        k = subset_key(s)
        values[f"lr|{k}"], infl[f"lr|{k}"] = f.log_rr, f.t_log_rr
        values[f"rd|{k}"] = f.m_exposed - f.m_reference
        infl[f"rd|{k}"] = f.t_exposed - f.t_reference
    return MarginSet(values, infl, cd)


def linear_contrast(ms: MarginSet, coefs: dict[str, float]) -> tuple[float, float]:
    """Estimate and SE of sum(c_k * value_k) (exact linearisation, no numeric gradient)."""
    est = sum(c * ms.values[k] for k, c in coefs.items())
    z = sum(c * ms.influence[k] for k, c in coefs.items())
    return float(est), float(np.sqrt(ms.design.vcov_total(z)[0, 0]))


def ratio_contrast(
    ms: MarginSet, num: dict[str, float], den: dict[str, float]
) -> tuple[float, float]:
    """Estimate and SE of (sum c_k v_k) / (sum d_k v_k) by the delta method."""
    a = sum(c * ms.values[k] for k, c in num.items())
    b = sum(c * ms.values[k] for k, c in den.items())
    za = sum(c * ms.influence[k] for k, c in num.items())
    zb = sum(c * ms.influence[k] for k, c in den.items())
    z = za / b - a / b**2 * zb
    return float(a / b), float(np.sqrt(ms.design.vcov_total(z)[0, 0]))


# --------------------------------------------------------------------------------------
# Shapley decomposition
# --------------------------------------------------------------------------------------
def shapley_coefficients(players: Sequence[str]) -> dict[str, dict[frozenset[str], float]]:
    """phi_j = sum_S w(|S|) [v(S) - v(S + j)] over S not containing j, as coefficients on v.

    ``phi_j`` is the average, over all orderings of ``players``, of the *reduction* in v when
    j is added; the phi_j sum to v(empty) - v(all).
    """
    n = len(players)
    out: dict[str, dict[frozenset[str], float]] = {}
    for j in players:
        others = [p for p in players if p != j]
        coefs: dict[frozenset[str], float] = {}
        for r in range(n):
            w = math.factorial(r) * math.factorial(n - r - 1) / math.factorial(n)
            for s in itertools.combinations(others, r):
                s0 = frozenset(s)
                coefs[s0] = coefs.get(s0, 0.0) + w
                coefs[s0 | {j}] = coefs.get(s0 | {j}, 0.0) - w
        out[j] = coefs
    return out


def shapley_values(
    v: Callable[[frozenset[str]], float], players: Sequence[str]
) -> dict[str, float]:
    """Plain-number Shapley values of the reduction in ``v`` (used for tests and checks)."""
    return {
        j: sum(c * v(s) for s, c in coefs.items())
        for j, coefs in shapley_coefficients(players).items()
    }


# --------------------------------------------------------------------------------------
# Tables
# --------------------------------------------------------------------------------------
def _ci(est: float, se: float, t: float) -> tuple[float, float]:
    return est - t * se, est + t * se


def sequential_table(
    lattice: dict[frozenset[str], SubsetFit],
    ms: MarginSet,
    exposure: Exposure,
    outcome: str,
) -> pd.DataFrame:
    t = ms.design.tcrit()
    crude = "lr|crude"
    crude_lo, crude_hi = _ci(*linear_contrast(ms, {crude: 1.0}), t)
    crude_unstable = crude_lo <= 0 <= crude_hi
    rows = []
    for name, order in orderings(exposure).items():
        prev: frozenset[str] = frozenset()
        for step in range(len(order) + 1):
            cur = frozenset(order[:step])
            f = lattice[cur]
            k = f"lr|{subset_key(cur)}"
            lr, lr_se = linear_contrast(ms, {k: 1.0})
            rd, rd_se = linear_contrast(ms, {f"rd|{subset_key(cur)}": 1.0})
            ret, ret_se = ratio_contrast(ms, {k: 1.0}, {crude: 1.0})
            if step:
                pk = f"lr|{subset_key(prev)}"
                d, d_se = ratio_contrast(ms, {pk: 1.0, k: -1.0}, {crude: 1.0})
            else:
                d, d_se = np.nan, np.nan
            added = order[step - 1] if step else "crude"
            rows.append(
                {
                    "exposure": exposure.name,
                    "outcome": outcome,
                    "ordering": name,
                    "step": step,
                    "block_added": added,
                    "variables_added": ",".join(BLOCKS[added]) if step else "",
                    "adj_rate_exposed": f.m_exposed,
                    "adj_rate_reference": f.m_reference,
                    "rr": np.exp(lr),
                    "rr_low": np.exp(lr - t * lr_se),
                    "rr_high": np.exp(lr + t * lr_se),
                    "log_rr": lr,
                    "log_rr_se": lr_se,
                    "rd": rd,
                    "rd_low": rd - t * rd_se,
                    "rd_high": rd + t * rd_se,
                    "share_logrr_retained": ret,
                    "share_retained_low": ret - t * ret_se,
                    "share_retained_high": ret + t * ret_se,
                    "share_removed_this_step": d,
                    "share_removed_low": d - t * d_se,
                    "share_removed_high": d + t * d_se,
                    "n_params": f.n_params,
                    "converged": f.converged,
                    "flag": "crude log-RR CI includes 0: shares unstable" if crude_unstable else "",
                }
            )
            prev = cur
    return pd.DataFrame(rows)


def shapley_table(
    lattice: dict[frozenset[str], SubsetFit],
    ms: MarginSet,
    exposure: Exposure,
    outcome: str,
    exclude: Sequence[str] = (),
) -> pd.DataFrame:
    """Shapley shares of the crude log-RR over the exposure's blocks minus ``exclude``."""
    t = ms.design.tcrit()
    players = [b for b in exposure.blocks if b not in exclude]
    crude = {"lr|crude": 1.0}
    crude_lo, crude_hi = _ci(*linear_contrast(ms, crude), t)
    variant = "all_blocks" if not exclude else "excluding_" + "_".join(exclude)
    rows = []
    for j, coefs in shapley_coefficients(players).items():
        num = {f"lr|{subset_key(s)}": c for s, c in coefs.items()}
        phi, phi_se = linear_contrast(ms, num)
        share, share_se = ratio_contrast(ms, num, crude)
        # Order dependence: the block's share when added to each subset of the other blocks.
        marg = [
            (lattice[s].log_rr - lattice[s | {j}].log_rr) / lattice[frozenset()].log_rr
            for s in coefs
            if j not in s
        ]
        rows.append(
            {
                "block": j,
                "variables": ",".join(BLOCKS[j]),
                "shapley_logrr_reduction": phi,
                "shapley_logrr_low": phi - t * phi_se,
                "shapley_logrr_high": phi + t * phi_se,
                "shapley_share_of_crude": share,
                "share_low": share - t * share_se,
                "share_high": share + t * share_se,
                "min_share_any_order": min(marg),
                "max_share_any_order": max(marg),
            }
        )
    full = frozenset(players)
    ret, ret_se = ratio_contrast(ms, {f"lr|{subset_key(full)}": 1.0}, crude)
    lr_full, lr_full_se = linear_contrast(ms, {f"lr|{subset_key(full)}": 1.0})
    rows.append(
        {
            "block": "retained_after_all_blocks",
            "variables": "",
            "shapley_logrr_reduction": lr_full,
            "shapley_logrr_low": lr_full - t * lr_full_se,
            "shapley_logrr_high": lr_full + t * lr_full_se,
            "shapley_share_of_crude": ret,
            "share_low": ret - t * ret_se,
            "share_high": ret + t * ret_se,
            "min_share_any_order": np.nan,
            "max_share_any_order": np.nan,
        }
    )
    out = pd.DataFrame(rows)
    out.insert(0, "variant", variant)
    out.insert(0, "outcome", outcome)
    out.insert(0, "exposure", exposure.name)
    out["crude_rr"] = np.exp(lattice[frozenset()].log_rr)
    out["full_rr"] = np.exp(lattice[full].log_rr)
    out["flag"] = "crude log-RR CI includes 0: shares unstable" if crude_lo <= 0 <= crude_hi else ""
    return out


def lattice_table(
    lattice: dict[frozenset[str], SubsetFit], ms: MarginSet, exposure: Exposure, outcome: str
) -> pd.DataFrame:
    t = ms.design.tcrit()
    rows = []
    for s, f in lattice.items():
        k = subset_key(s)
        lr, se = linear_contrast(ms, {f"lr|{k}": 1.0})
        rows.append(
            {
                "exposure": exposure.name,
                "outcome": outcome,
                "blocks": k,
                "n_blocks": len(s),
                "includes_light": "light" in s,
                "rr": np.exp(lr),
                "rr_low": np.exp(lr - t * se),
                "rr_high": np.exp(lr + t * se),
                "log_rr": lr,
                "log_rr_se": se,
                "adj_rate_exposed": f.m_exposed,
                "adj_rate_reference": f.m_reference,
                "n_params": f.n_params,
                "n_cells": f.n_cells,
                "converged": f.converged,
            }
        )
    return pd.DataFrame(rows).sort_values(["n_blocks", "blocks"]).reset_index(drop=True)


def crude_rates(df: pd.DataFrame, design: SurveyDesign) -> pd.DataFrame:
    """Observed weighted outcome rates by exposure level (the crude numerators/denominators)."""
    n_years = df["YEAR"].nunique()
    out = []
    for ex in EXPOSURES.values():
        for oc in OUTCOMES:
            tab = proportion_table(
                df,
                design,
                oc,
                ex.column,
                min_n=config.MIN_CELL_N,
                max_rse=config.MAX_RSE,
                years=n_years,
            )
            tab = tab.rename(columns={ex.column: "level"})
            tab.insert(0, "outcome", oc)
            tab.insert(0, "exposure", ex.name)
            out.append(tab)
    return pd.concat(out, ignore_index=True)


def night_light_overlap(df: pd.DataFrame, design: SurveyDesign) -> pd.DataFrame:
    """Weighted distribution of light condition within night and day crashes (positivity)."""
    rows = []
    w = design.weight
    for period in NIGHT_LEVELS:
        dom = (df[NIGHT_COLUMN] == period).to_numpy()
        tot = w[dom].sum()
        for lv in specs.CRASH_LEVELS["light"]:
            cell = dom & (df["light"] == lv).to_numpy()
            rows.append(
                {
                    "period": period,
                    "light": lv,
                    "n": int(cell.sum()),
                    "n_fatal": int(df.loc[cell, "fatal"].sum()),
                    "weighted_share_of_period": w[cell].sum() / tot if tot else np.nan,
                }
            )
    return pd.DataFrame(rows)


def within_dark(df: pd.DataFrame, design: SurveyDesign) -> pd.DataFrame:
    """Night vs day among crashes in darkness only (no night-in-daylight extrapolation)."""
    ex = EXPOSURES["night"]
    mask = df["light"].isin(DARK_LEVELS).to_numpy()
    sub, sub_design = df.loc[mask].reset_index(drop=True), design.subset(mask)
    full = list(ex.blocks)
    rows = []
    for oc in OUTCOMES:
        for label, blocks in (
            ("crude", []),
            ("all_blocks_without_light", [b for b in full if b != "light"]),
            ("all_blocks_with_dark_type", full),
        ):
            f = fit_subset(sub, sub_design, ex, blocks, oc)
            ms = MarginSet({"lr": f.log_rr}, {"lr": f.t_log_rr}, cluster_design(sub_design))
            lr, se = linear_contrast(ms, {"lr": 1.0})
            t = sub_design.tcrit()
            rows.append(
                {
                    "outcome": oc,
                    "model": label,
                    "domain": "light in " + ",".join(DARK_LEVELS),
                    "n_crashes": int(mask.sum()),
                    "n_night": int((sub[NIGHT_COLUMN] == "night").sum()),
                    "n_day": int((sub[NIGHT_COLUMN] == "day").sum()),
                    "adj_rate_night": f.m_exposed,
                    "adj_rate_day": f.m_reference,
                    "rr": np.exp(lr),
                    "rr_low": np.exp(lr - t * se),
                    "rr_high": np.exp(lr + t * se),
                }
            )
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------------------
# Driver
# --------------------------------------------------------------------------------------
def data_fingerprint() -> str:
    """Size and modification time of the processed CRSS crash file (identifies the build)."""
    st = (config.PROCESSED_DIR / "crss_crash.parquet").stat()
    return f"{st.st_size}-{int(st.st_mtime)}"


def cached_lattice(
    df: pd.DataFrame,
    design: SurveyDesign,
    exposure: Exposure,
    outcome: str,
    cache_dir: Path | None = None,
) -> dict[frozenset[str], SubsetFit]:
    """``fit_lattice`` with an optional pickle cache (a convenience for re-tabulating only;
    delete the cache whenever data or model code change)."""
    if cache_dir is None:
        return fit_lattice(df, design, exposure, outcome)
    path = Path(cache_dir) / f"lattice_{exposure.name}_{outcome}_{data_fingerprint()}.pkl"
    if path.exists():
        log.info("using cached lattice %s", path)
        with path.open("rb") as fh:
            return pickle.load(fh)
    lattice = fit_lattice(df, design, exposure, outcome)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as fh:
        pickle.dump(lattice, fh)
    return lattice


def analyse_exposure(
    df: pd.DataFrame,
    design: SurveyDesign,
    exposure: Exposure,
    outcome: str,
    cache_dir: Path | None = None,
) -> dict[str, pd.DataFrame]:
    lattice = cached_lattice(df, design, exposure, outcome, cache_dir)
    ms = lattice_marginset(lattice, design)
    shap = [shapley_table(lattice, ms, exposure, outcome)]
    if "light" in exposure.blocks:
        shap.append(shapley_table(lattice, ms, exposure, outcome, exclude=("light",)))
    return {
        "sequential": sequential_table(lattice, ms, exposure, outcome),
        "shapley": pd.concat(shap, ignore_index=True),
        "lattice": lattice_table(lattice, ms, exposure, outcome),
    }


def check_leakage() -> None:
    feats = [*analysis_columns(), "night"]
    assert_no_leakage(feats, allowed=MODEL_ALLOWED_TIMINGS | {"design"})


def _meta(description: str, method: str, outcome: str = "fatal; ka") -> dict:
    return {
        "description": description,
        "population": POPULATION,
        "unit": "crash",
        "outcome": outcome,
        "method": method,
        "inputs": [CRSS_INPUT],
    }


LATTICE_METHOD = (
    "Survey-weighted logistic models (exposure + every subset of covariate blocks; ridge 0.01 on "
    "mean-1 weights; exact cell compression); standardised predictive margins over all crashes; "
    "risk ratio = margin(all exposed) / margin(all reference); Taylor-linearised influence summed "
    "within 67 PSUs / 25 strata, t with 42 df; shares and Shapley values by the delta method "
    "across models"
)


def run(
    outcomes: Sequence[str] = OUTCOMES,
    exposures: Sequence[str] | None = None,
    cache_dir: Path | None = None,
) -> dict[str, pd.DataFrame]:
    """Fit all lattices and write the tables (about 2,000 model fits; ~1 h on 2 cores)."""
    check_leakage()
    fingerprint = data_fingerprint()
    df, design = load_frame()
    log.info("confounding: %d crashes, %d fatal", len(df), int(df["fatal"].sum()))
    names = list(EXPOSURES) if exposures is None else list(exposures)
    out: dict[str, pd.DataFrame] = {}

    out["crude_rates"] = crude_rates(df, design)
    save_table(
        out["crude_rates"],
        MODULE,
        "crude_rates",
        **_meta(
            "Observed weighted fatal / KA shares by exposure level (crude numerators and "
            "denominators; flag: suppressed n<30, unstable RSE>30%)",
            "Weighted proportions, Taylor-linearised SEs, logit CIs",
        ),
    )
    out["night_light_overlap"] = night_light_overlap(df, design)
    save_table(
        out["night_light_overlap"],
        MODULE,
        "night_light_overlap",
        **_meta(
            "Weighted light-condition distribution within night, day and unknown-hour crashes "
            "(positivity check for adjusting night for light)",
            "Weighted shares",
            outcome="",
        ),
    )
    out["night_within_dark"] = within_dark(df, design)
    save_table(
        out["night_within_dark"],
        MODULE,
        "night_within_dark",
        **_meta(
            "Night vs day standardised risk ratio among crashes in darkness only",
            LATTICE_METHOD,
        ),
    )
    for oc in outcomes:
        parts: dict[str, list[pd.DataFrame]] = {"sequential": [], "shapley": [], "lattice": []}
        for name in names:
            res = analyse_exposure(df, design, EXPOSURES[name], oc, cache_dir)
            for k, v in res.items():
                parts[k].append(v)
        for k, frames in parts.items():
            tab = pd.concat(frames, ignore_index=True)
            out[f"{k}_{oc}"] = tab
            save_table(
                tab,
                MODULE,
                f"{k}_{oc}",
                **_meta(
                    {
                        "sequential": "Sequential adjustment of standardised risk ratios "
                        "(night, rural PSU, weekend, driver 65+) under pre-specified block "
                        "orderings: RR, RD and share of the crude log-RR retained",
                        "shapley": "Shapley (all-orderings average) shares of the crude log-RR "
                        "accounted for by each covariate block, with and without light",
                        "lattice": "Standardised risk ratio for every subset of covariate blocks",
                    }[k],
                    LATTICE_METHOD,
                    outcome=oc,
                ),
                extra={"exposures": {n: EXPOSURES[n].label for n in names}},
            )
    save_json(
        {
            "exposures": {n: EXPOSURES[n].label for n in names},
            "blocks": {b: list(v) for b, v in BLOCKS.items()},
            "orderings": {n: orderings(EXPOSURES[n]) for n in names},
            "n_crashes": len(df),
            "n_fatal": int(df["fatal"].sum()),
            "n_ka": int(df["ka"].sum()),
            "design_df": design.df,
            "ridge": RIDGE,
            "stochastic_components": "none (deterministic estimators)",
            "crss_crash_fingerprint": fingerprint,
            "data_unchanged_during_run": fingerprint == data_fingerprint(),
        },
        MODULE,
        "run_metadata",
    )
    return out
