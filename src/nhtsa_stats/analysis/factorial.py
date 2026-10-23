"""Standardised risks for every combination of k binary factors, and their interaction contrasts.

Phase-1 interaction analyses handled one pair (or a fixed triple) at a time.  Phase 2 needs the
full 2^k factorial for up to four factors at a stated observation level (crash, driver or
occupant), with the support behind every cell made explicit.  This module is the shared core.

Model
    A survey-weighted logistic regression containing (i) every factor's full categorical main
    effect (so levels outside exposed/reference, e.g. 'unknown' or other speeding types, keep
    their own coefficient and are never merged into the reference), (ii) a product term for
    every combination of non-reference levels of every subset of >= 2 factors, so the k factors
    are saturated among all their observed levels, and (iii) the adjustment covariates as
    categorical main effects.

Margins
    For each of the 2^k combinations s, M_s = weighted mean over the standardisation
    population of p(x with each factor set to its exposed or reference level).  All margins
    come from one model, are linearised jointly (coefficient and covariate-distribution
    variability; PSU totals), so any contrast has a design-based CI (``MarginSet``).

Contrasts (all from the same margins; ``key`` strings are factor states, e.g. "101")
    * single-factor RR and RD with every other factor at reference;
    * pairwise IC = p11 - p10 - p01 + p00, RERI = IC / p00 and ratio of RRs RR11/(RR10 RR01),
      other factors at reference;
    * k-way additive contrast  sum_s (-1)^(k-|s|) p_s  over the 2^k subsets of a set of k
      factors (three- and four-way interaction contrasts), and its multiplicative analogue
      on the log scale;
    * excess of the joint risk difference over the sum of single-factor risk differences.

Support and suppression
    The observed cell of combination s is the set of rows whose factors are *recorded* at
    exactly those levels.  Its unweighted size and event count are reported.  A margin whose
    observed cell has fewer than ``min_n`` rows or ``min_events`` events is withheld (NaN with a
    flag), because the model would then be extrapolating the combination from other cells;
    every contrast that uses a withheld margin is withheld too.

Computation uses the exact categorical cell compression of ``confounding.collapse_cells``.
"""

from __future__ import annotations

import itertools
import logging
from collections.abc import Sequence
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy import stats

from nhtsa_stats import config
from nhtsa_stats.analysis.confounding import collapse_cells
from nhtsa_stats.analysis.survey import (
    Estimate,
    MarginSet,
    ModelSpec,
    SurveyDesign,
    SurveyLogit,
    logit_ci,
    svy_mean,
    svy_total,
)

log = logging.getLogger(__name__)
RIDGE = 0.01
MIN_EVENTS = 10


@dataclass(frozen=True)
class Factor:
    """A binary contrast on one column: ``exposed`` vs ``reference`` level groups."""

    name: str
    column: str
    exposed: tuple[str, ...]
    reference: tuple[str, ...]
    label: str = ""

    def level(self, state: int) -> str:
        return (self.exposed if state else self.reference)[0]


@dataclass
class FactorialResult:
    factors: list[Factor]
    margins: MarginSet
    support: pd.DataFrame  # one row per combination key
    suppressed: set[str]
    model: SurveyLogit
    n_rows: int
    n_events: int
    standardisation: str
    meta: dict = field(default_factory=dict)

    @property
    def k(self) -> int:
        return len(self.factors)


def keys(k: int) -> list[str]:
    return ["".join(map(str, s)) for s in itertools.product((0, 1), repeat=k)]


def subset_keys(on: Sequence[int], k: int) -> list[tuple[str, int]]:
    """Keys of all 2^|on| combinations of the factors at positions ``on`` (others 0), with
    the sign (-1)^(|on| - |s|) of the |on|-way additive contrast."""
    out = []
    for bits in itertools.product((0, 1), repeat=len(on)):
        key = ["0"] * k
        for pos, b in zip(on, bits, strict=True):
            key[pos] = str(b)
        out.append(("".join(key), (-1) ** (len(on) - sum(bits))))
    return out


def product_terms(
    factors: Sequence[Factor], levels: dict[str, list] | None = None
) -> list[tuple[tuple[str, list], ...]]:
    """Products of level indicators for every subset of >= 2 factors.

    Without ``levels``: one product of the exposed-group indicators per subset.  With
    ``levels`` (column -> all observed levels, reference first): one product per combination of
    non-reference levels, so the factors are saturated among *all* their observed levels
    (e.g. 'unknown' or other speeding types get their own interaction terms instead of being
    pooled with the reference in the interaction part of the model).
    """
    out = []
    for r in range(2, len(factors) + 1):
        for comb in itertools.combinations(factors, r):
            if levels is None:
                out.append(tuple((f.column, list(f.exposed)) for f in comb))
                continue
            for lv in itertools.product(*(levels[f.column][1:] for f in comb)):
                out.append(tuple((f.column, [v]) for f, v in zip(comb, lv, strict=True)))
    return out


def _levels(df: pd.DataFrame, col: str, first: str) -> list:
    vals = pd.unique(np.asarray(df[col], dtype=object))
    rest = sorted((v for v in vals if v != first), key=str)
    return [first, *rest]


def cell_support(
    df: pd.DataFrame,
    design: SurveyDesign,
    factors: Sequence[Factor],
    outcome: str,
    n_years: int,
    min_n: int = config.MIN_CELL_N,
    min_events: int = MIN_EVENTS,
) -> pd.DataFrame:
    """Observed support and crude outcome rate for every combination (recorded levels)."""
    rows = []
    y = df[outcome].to_numpy(dtype=float)
    for key in keys(len(factors)):
        dom = np.ones(len(df), dtype=bool)
        for f, b in zip(factors, key, strict=True):
            levels = f.exposed if b == "1" else f.reference
            dom &= df[f.column].isin(list(levels)).to_numpy()
        n = int(dom.sum())
        ev = int(np.nansum(y[dom]))
        rec: dict = {"key": key, "n": n, "n_events": ev}
        for f, b in zip(factors, key, strict=True):
            rec[f.name] = int(b)
        if n:
            est = svy_mean(design, y, dom)
            lo, hi = logit_ci(est.estimate, est.se, est.df)
            tot = svy_total(design, np.ones(design.n), dom)
            rec.update(
                crude_rate=est.estimate,
                crude_rate_low=lo,
                crude_rate_high=hi,
                weighted_per_year=tot.estimate / n_years,
            )
        else:
            rec.update(
                crude_rate=np.nan,
                crude_rate_low=np.nan,
                crude_rate_high=np.nan,
                weighted_per_year=0.0,
            )
        rec["supported"] = n >= min_n and ev >= min_events
        if not rec["supported"]:
            rec.update(crude_rate=np.nan, crude_rate_low=np.nan, crude_rate_high=np.nan)
        rows.append(rec)
    return pd.DataFrame(rows)


def fit_factorial(
    df: pd.DataFrame,
    design: SurveyDesign,
    factors: Sequence[Factor],
    covariates: Sequence[str],
    outcome: str,
    standardise: np.ndarray | None = None,
    standardisation: str = "all rows of the analysis population",
    min_n: int = config.MIN_CELL_N,
    min_events: int = MIN_EVENTS,
    ridge: float = RIDGE,
) -> FactorialResult:
    """Fit the saturated-in-factors model and compute all 2^k standardised margins.

    ``standardise`` (boolean mask over ``df``) restricts the standardisation population; by
    default it is every row of ``df``.
    """
    factors = list(factors)
    k = len(factors)
    cols = list(dict.fromkeys([*(f.column for f in factors), *covariates]))
    work = df[[*cols, outcome]].copy()
    for c in cols:
        if work[c].isna().any():
            raise ValueError(f"{c}: missing values; code them as an explicit level first")
        work[c] = np.asarray(work[c], dtype=object)
    flag_col = "__std__"
    work[flag_col] = (
        np.ones(len(work), dtype=bool) if standardise is None else np.asarray(standardise, bool)
    ).astype(np.int8)
    cells, cdesign = collapse_cells(work, design, [*cols, flag_col], outcome)
    categorical = {}
    for c in cols:
        f = next((f for f in factors if f.column == c), None)
        # Reference level: the factor's reference group; for an adjustment covariate, its
        # most frequent value (the choice does not affect standardised margins).
        first = f.reference[0] if f else pd.Series(work[c]).value_counts().index[0]
        categorical[c] = _levels(work, c, first)
    spec = ModelSpec(
        categorical=categorical,
        products=product_terms(factors, {f.column: categorical[f.column] for f in factors}),
    )
    model = SurveyLogit(spec, ridge=ridge * len(cells) / len(work))
    model.fit(cells, cells[outcome].to_numpy(dtype=float), cdesign)
    if not model.converged_:
        log.warning("factorial model %s did not converge", [f.name for f in factors])
    dom = cells[flag_col].to_numpy() == 1
    scenarios = {}
    for key in keys(k):
        assign = {f.column: f.level(int(b)) for f, b in zip(factors, key, strict=True)}
        scenarios[key] = lambda d, a=assign: d.assign(**a)
    ms = model.margins(cells, scenarios, domain=dom)
    n_years = int(df["YEAR"].nunique()) if "YEAR" in df else 1
    support = cell_support(df, design, factors, outcome, n_years, min_n, min_events)
    suppressed = set(support.loc[~support["supported"], "key"])
    return FactorialResult(
        factors=factors,
        margins=ms,
        support=support,
        suppressed=suppressed,
        model=model,
        n_rows=len(df),
        n_events=int(np.nansum(df[outcome].to_numpy(dtype=float))),
        standardisation=standardisation,
        meta={"n_cells": len(cells), "n_params": len(model.coef_), "converged": model.converged_},
    )


# --------------------------------------------------------------------------------------
# Contrasts
# --------------------------------------------------------------------------------------
def _est_dict(prefix: str, est: Estimate | None, exp: bool = False, scale: float = 1.0) -> dict:
    if est is None:
        return {
            prefix: np.nan,
            f"{prefix}_low": np.nan,
            f"{prefix}_high": np.nan,
            f"{prefix}_p": np.nan,
        }
    t = stats.t.ppf(0.975, est.df)
    lo, hi = est.estimate - t * est.se, est.estimate + t * est.se
    p = float(2 * stats.t.sf(abs(est.estimate / est.se), est.df)) if est.se > 0 else np.nan
    if exp:
        return {
            prefix: np.exp(est.estimate),
            f"{prefix}_low": np.exp(lo),
            f"{prefix}_high": np.exp(hi),
            f"{prefix}_p": p,
        }
    return {
        prefix: scale * est.estimate,
        f"{prefix}_low": scale * lo,
        f"{prefix}_high": scale * hi,
        f"{prefix}_p": p,
    }


def _uses_suppressed(res: FactorialResult, ks: Sequence[str]) -> bool:
    return any(k in res.suppressed for k in ks)


def margins_table(res: FactorialResult) -> pd.DataFrame:
    """One row per combination: factor states, support, crude rate, standardised risk, RR
    and RD against the all-reference combination."""
    k = res.k
    ref = "0" * k
    rows = []
    for _, s in res.support.iterrows():
        key = s["key"]
        rec = {f.name: int(key[i]) for i, f in enumerate(res.factors)}
        rec["combination"] = (
            " + ".join(f.name for i, f in enumerate(res.factors) if key[i] == "1") or "none"
        )
        rec["key"] = key
        rec.update(
            {
                c: s[c]
                for c in (
                    "n",
                    "n_events",
                    "weighted_per_year",
                    "crude_rate",
                    "crude_rate_low",
                    "crude_rate_high",
                )
            }
        )
        sup = key in res.suppressed or ref in res.suppressed
        if key in res.suppressed:
            rec.update(adj_risk=np.nan, adj_risk_low=np.nan, adj_risk_high=np.nan)
        else:
            e = res.margins.estimate(key)
            lo, hi = logit_ci(e.estimate, e.se, e.df)
            rec.update(adj_risk=e.estimate, adj_risk_low=lo, adj_risk_high=hi)
        rec.update(
            _est_dict("rr_vs_none", None if sup else res.margins.log_ratio(key, ref), exp=True)
        )
        rec.update(_est_dict("rd_vs_none", None if sup else res.margins.difference(key, ref)))
        rec["flag"] = (
            "suppressed: fewer than 30 sample units or 10 events" if key in res.suppressed else ""
        )
        rows.append(rec)
    return pd.DataFrame(rows)


def interaction_table(res: FactorialResult) -> pd.DataFrame:
    """Every pairwise, three-way and (k = 4) four-way contrast, other factors at reference."""
    k = res.k
    ms = res.margins
    ref = "0" * k
    rows = []
    for r in range(2, k + 1):
        for on in itertools.combinations(range(k), r):
            terms = subset_keys(on, k)
            ks = [t for t, _ in terms]
            name = " x ".join(res.factors[i].name for i in on)
            rec: dict = {
                "contrast": name,
                "order": r,
                "factors": ",".join(res.factors[i].name for i in on),
            }
            bad = _uses_suppressed(res, ks)
            ic = None if bad else ms.contrast(lambda m, t=terms: sum(sg * m[kk] for kk, sg in t))
            lic = (
                None
                if bad
                else ms.contrast(lambda m, t=terms: float(sum(sg * np.log(m[kk]) for kk, sg in t)))
            )
            full = "".join("1" if i in on else "0" for i in range(k))
            singles = ["".join("1" if i == j else "0" for i in range(k)) for j in on]
            excess = (
                None
                if bad
                else ms.contrast(
                    lambda m, f=full, s=singles: (m[f] - m[ref]) - sum(m[x] - m[ref] for x in s)
                )
            )
            reri = (
                None
                if bad
                else ms.contrast(
                    lambda m, f=full, s=singles: (
                        ((m[f] - m[ref]) - sum(m[x] - m[ref] for x in s)) / m[ref]
                    )
                )
            )
            rec.update(_est_dict("additive_contrast", ic))
            rec.update(_est_dict("multiplicative_ratio", lic, exp=True))
            rec.update(_est_dict("excess_over_additive_singles", excess))
            rec.update(_est_dict("reri_singles", reri))
            rec.update(_est_dict("rr_joint", None if bad else ms.log_ratio(full, ref), exp=True))
            for j, sk in zip(on, singles, strict=True):
                rec.update(
                    _est_dict(
                        f"rr_{res.factors[j].name}_alone",
                        None if bad else ms.log_ratio(sk, ref),
                        exp=True,
                    )
                )
            rec["min_cell_n"] = int(res.support.set_index("key").loc[ks, "n"].min())
            rec["min_cell_events"] = int(res.support.set_index("key").loc[ks, "n_events"].min())
            rec["flag"] = "withheld: a combination lacks support" if bad else ""
            rows.append(rec)
    return pd.DataFrame(rows)


def single_factor_table(res: FactorialResult) -> pd.DataFrame:
    """RR and RD of each factor within every combination of the other factors (effect
    heterogeneity across strata of the others)."""
    k = res.k
    rows = []
    for j, f in enumerate(res.factors):
        for key in keys(k):
            if key[j] == "1":
                continue
            exp_key = key[:j] + "1" + key[j + 1 :]
            others = ", ".join(
                f"{g.name}={'yes' if key[i] == '1' else 'no'}"
                for i, g in enumerate(res.factors)
                if i != j
            )
            bad = _uses_suppressed(res, [key, exp_key])
            rec = {
                "factor": f.name,
                "other_factors": others or "(none)",
                "key_reference": key,
                "key_exposed": exp_key,
            }
            rec.update(
                _est_dict("rr", None if bad else res.margins.log_ratio(exp_key, key), exp=True)
            )
            rec.update(_est_dict("rd", None if bad else res.margins.difference(exp_key, key)))
            rec["flag"] = "withheld: a combination lacks support" if bad else ""
            rows.append(rec)
    return pd.DataFrame(rows)


def holm(p: pd.Series) -> pd.Series:
    """Holm step-down adjusted p-values (NaN kept as NaN)."""
    p = pd.Series(p, dtype=float)
    ok = p.notna()
    vals = p[ok].to_numpy()
    order = np.argsort(vals)
    m = len(vals)
    adj = np.empty(m)
    running = 0.0
    for rank, idx in enumerate(order):
        running = max(running, min(1.0, (m - rank) * vals[idx]))
        adj[idx] = running
    out = pd.Series(np.nan, index=p.index)
    out[ok] = adj
    return out
