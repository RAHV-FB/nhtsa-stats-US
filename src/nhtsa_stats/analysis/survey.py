"""Design-based inference for CRSS (and cluster-robust inference for FARS).

CRSS is a stratified multistage probability sample.  Variances are estimated by Taylor
linearisation under the usual with-replacement ("ultimate cluster") approximation:

    V(t) = sum_h  n_h / (n_h - 1) * sum_i (z_hi - zbar_h)(z_hi - zbar_h)^T

where ``z_hi`` is the weighted total of the linearised variable over variance PSU ``i`` in
variance stratum ``h``.  CRSS supplies ``PSUSTRAT`` (variance stratum) and ``PSU_VAR``
(variance PSU); their IDs are stable across 2016-2024 and every stratum has at least two
PSUs (verified in ``docs/data_audit.md``), so pooled multi-year analyses use the same
25 strata / 67 clusters, which also accounts for correlation of a PSU's crashes across years.
Design degrees of freedom = clusters - strata (42 for CRSS).

The same machinery provides cluster-robust (sandwich) inference for FARS person-level models,
using unit weights, a single stratum and the crash as the cluster.

Everything here is plain NumPy so that each estimator is transparent and unit-testable.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy import sparse, stats


# --------------------------------------------------------------------------------------
# Design
# --------------------------------------------------------------------------------------
@dataclass
class SurveyDesign:
    """Per-row weights plus integer stratum and (globally unique) cluster codes."""

    weight: np.ndarray
    stratum: np.ndarray
    cluster: np.ndarray
    cluster_stratum: np.ndarray = field(repr=False)  # stratum code of each cluster
    lonely_psu: str = "adjust"

    @classmethod
    def from_arrays(
        cls,
        weight: Sequence[float] | np.ndarray,
        stratum: Sequence | np.ndarray | None,
        cluster: Sequence | np.ndarray | None,
    ) -> SurveyDesign:
        w = np.asarray(weight, dtype=float)
        n = len(w)
        if np.any(~np.isfinite(w)) or np.any(w < 0):
            raise ValueError("weights must be finite and non-negative")
        s_raw = np.zeros(n, dtype=np.int64) if stratum is None else np.asarray(stratum)
        c_raw = np.arange(n) if cluster is None else np.asarray(cluster)
        # Clusters are identified within strata, so each cluster has exactly one stratum.
        c_codes, c_uniques = pd.factorize(pd.MultiIndex.from_arrays([s_raw, c_raw]), sort=True)
        s_codes, _ = pd.factorize(s_raw, sort=True)
        cluster_stratum = np.zeros(len(c_uniques), dtype=np.int64)
        cluster_stratum[c_codes] = s_codes
        return cls(w, s_codes.astype(np.int64), c_codes.astype(np.int64), cluster_stratum)

    @classmethod
    def from_frame(
        cls,
        df: pd.DataFrame,
        weight: str | None = "WEIGHT",
        strata: str | None = "PSUSTRAT",
        cluster: str | None = "PSU_VAR",
    ) -> SurveyDesign:
        w = np.ones(len(df)) if weight is None else df[weight].to_numpy(dtype=float)
        s = None if strata is None else df[strata].to_numpy()
        c = None if cluster is None else df[cluster].to_numpy()
        return cls.from_arrays(w, s, c)

    @property
    def n(self) -> int:
        return len(self.weight)

    @property
    def n_clusters(self) -> int:
        return len(self.cluster_stratum)

    @property
    def n_strata(self) -> int:
        return int(self.cluster_stratum.max()) + 1 if self.n_clusters else 0

    @property
    def df(self) -> int:
        """Design degrees of freedom (clusters - strata), at least 1."""
        return max(self.n_clusters - self.n_strata, 1)

    def subset(self, mask: np.ndarray) -> SurveyDesign:
        """Rows subset that keeps the full cluster universe (correct domain variance)."""
        mask = np.asarray(mask, dtype=bool)
        return SurveyDesign(
            self.weight[mask],
            self.stratum[mask],
            self.cluster[mask],
            self.cluster_stratum,
            self.lonely_psu,
        )

    # ----------------------------------------------------------------------------------
    def cluster_totals(self, z: np.ndarray) -> np.ndarray:
        """Sum rows of ``z`` (n x p, already weighted) within clusters -> (G x p)."""
        z = np.asarray(z, dtype=float)
        if z.ndim == 1:
            z = z[:, None]
        ind = sparse.csr_matrix(
            (np.ones(self.n), (self.cluster, np.arange(self.n))), shape=(self.n_clusters, self.n)
        )
        return np.asarray(ind @ z)

    def vcov_total(self, z: np.ndarray) -> np.ndarray:
        """Design-based covariance of the estimated total of weighted contributions ``z``."""
        zt = self.cluster_totals(z)
        p = zt.shape[1]
        v = np.zeros((p, p))
        grand = zt.mean(axis=0)
        for h in range(self.n_strata):
            zh = zt[self.cluster_stratum == h]
            nh = zh.shape[0]
            if nh == 0:
                continue
            if nh == 1:
                if self.lonely_psu == "adjust":
                    d = zh - grand
                    v += d.T @ d
                continue
            d = zh - zh.mean(axis=0)
            v += nh / (nh - 1) * (d.T @ d)
        return v

    def tcrit(self, level: float = 0.95) -> float:
        return float(stats.t.ppf(0.5 + level / 2, self.df))


# --------------------------------------------------------------------------------------
# Totals, means, proportions
# --------------------------------------------------------------------------------------
@dataclass
class Estimate:
    estimate: float
    se: float
    df: int
    n: int  # unweighted rows contributing (domain size)

    def ci(self, level: float = 0.95) -> tuple[float, float]:
        t = float(stats.t.ppf(0.5 + level / 2, self.df))
        return self.estimate - t * self.se, self.estimate + t * self.se

    @property
    def rse(self) -> float:
        return self.se / abs(self.estimate) if self.estimate else np.inf


def svy_total(design: SurveyDesign, y: np.ndarray, domain: np.ndarray | None = None) -> Estimate:
    y = np.asarray(y, dtype=float)
    d = np.ones(design.n, dtype=bool) if domain is None else np.asarray(domain, dtype=bool)
    z = design.weight * np.where(d, y, 0.0)
    v = design.vcov_total(z)[0, 0]
    return Estimate(float(z.sum()), float(np.sqrt(v)), design.df, int(d.sum()))


def svy_mean(design: SurveyDesign, y: np.ndarray, domain: np.ndarray | None = None) -> Estimate:
    """Weighted mean (a ratio of totals) with linearised variance; NaN y excluded from domain."""
    y = np.asarray(y, dtype=float)
    d = np.ones(design.n, dtype=bool) if domain is None else np.asarray(domain, dtype=bool)
    d = d & np.isfinite(y)
    w = design.weight * d
    big_n = w.sum()
    if big_n <= 0:
        return Estimate(np.nan, np.nan, design.df, 0)
    yy = np.where(d, y, 0.0)
    r = (w * yy).sum() / big_n
    z = w * (yy - r) / big_n
    v = design.vcov_total(z)[0, 0]
    return Estimate(float(r), float(np.sqrt(v)), design.df, int(d.sum()))


def logit_ci(p: float, se: float, df: int, level: float = 0.95) -> tuple[float, float]:
    """Logit-transformed CI for a proportion (stays inside [0, 1])."""
    if not (0 < p < 1) or not np.isfinite(se) or se == 0:
        return (p, p)
    t = float(stats.t.ppf(0.5 + level / 2, df))
    lg = np.log(p / (1 - p))
    se_lg = se / (p * (1 - p))
    lo, hi = lg - t * se_lg, lg + t * se_lg
    return float(1 / (1 + np.exp(-lo))), float(1 / (1 + np.exp(-hi)))


def proportion_table(
    df: pd.DataFrame,
    design: SurveyDesign,
    outcome: str,
    by: str | list[str],
    min_n: int = 30,
    max_rse: float = 0.30,
    years: int = 1,
) -> pd.DataFrame:
    """Weighted outcome rate within each level of ``by`` with design-based SEs.

    ``outcome`` must be 0/1 with NaN for unknown (excluded from the denominator).  Returns the
    unweighted n, the estimated number of crashes/persons per year (``weighted_n``/``years``),
    the rate, its SE and logit CI, and a ``flag`` column: ``suppressed`` when n < min_n,
    ``unstable`` when the RSE exceeds ``max_rse``.
    """
    by = [by] if isinstance(by, str) else list(by)
    y = df[outcome].to_numpy(dtype=float)
    keys = df[by].astype("object").fillna("<NA>")
    groups = keys.apply(tuple, axis=1) if len(by) > 1 else keys[by[0]]
    rows = []
    for g in pd.unique(groups):
        dom = (groups == g).to_numpy()
        est = svy_mean(design, y, dom)
        tot = svy_total(design, np.ones(design.n), dom & np.isfinite(y))
        events = svy_total(design, np.nan_to_num(y), dom & np.isfinite(y))
        lo, hi = logit_ci(est.estimate, est.se, est.df)
        rse = est.se / est.estimate if est.estimate > 0 else np.inf
        flag = "suppressed" if est.n < min_n else ("unstable" if rse > max_rse else "")
        rec = dict(zip(by, g if isinstance(g, tuple) else (g,), strict=True))
        rec.update(
            n=est.n,
            n_events=int(np.nansum(y[dom])),
            weighted_n_per_year=tot.estimate / years,
            weighted_events_per_year=events.estimate / years,
            rate=est.estimate,
            se=est.se,
            ci_low=lo,
            ci_high=hi,
            rse=rse,
            flag=flag,
        )
        rows.append(rec)
    return pd.DataFrame(rows).sort_values(by).reset_index(drop=True)


# --------------------------------------------------------------------------------------
# Design matrices
# --------------------------------------------------------------------------------------
@dataclass
class ModelSpec:
    """Explicit design-matrix specification (no formula parsing).

    ``categorical`` maps a column to its ordered levels; the first level is the reference.
    ``interactions`` are pairs of columns (categorical x categorical, or categorical x
    numeric) whose dummy/numeric blocks are multiplied.
    """

    categorical: dict[str, list] = field(default_factory=dict)
    numeric: list[str] = field(default_factory=list)
    interactions: list[tuple[str, str]] = field(default_factory=list)
    intercept: bool = True

    def _block(self, df: pd.DataFrame, var: str) -> tuple[np.ndarray, list[str]]:
        if var in self.categorical:
            levels = self.categorical[var]
            vals = df[var].to_numpy()
            unknown = ~pd.Series(vals).isin(levels).to_numpy()
            if unknown.any():
                bad = pd.unique(vals[unknown])[:5]
                raise ValueError(f"{var}: values outside declared levels: {bad}")
            cols = [(vals == lv).astype(float) for lv in levels[1:]]
            return np.column_stack(cols) if cols else np.zeros((len(df), 0)), [
                f"{var}[{lv}]" for lv in levels[1:]
            ]
        return df[var].to_numpy(dtype=float)[:, None], [var]

    def design_matrix(self, df: pd.DataFrame) -> tuple[np.ndarray, list[str]]:
        blocks, names = [], []
        if self.intercept:
            blocks.append(np.ones((len(df), 1)))
            names.append("Intercept")
        for v in [*self.categorical, *self.numeric]:
            b, nm = self._block(df, v)
            blocks.append(b)
            names += nm
        for a, b in self.interactions:
            xa, na = self._block(df, a)
            xb, nb = self._block(df, b)
            for i, ni in enumerate(na):
                for j, nj in enumerate(nb):
                    blocks.append((xa[:, i] * xb[:, j])[:, None])
                    names.append(f"{ni}:{nj}")
        return np.column_stack(blocks), names

    def columns(self) -> list[str]:
        return [*self.categorical, *self.numeric]


# --------------------------------------------------------------------------------------
# Survey-weighted logistic regression
# --------------------------------------------------------------------------------------
def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 0.5 * (1 + np.tanh(0.5 * x))


@dataclass
class SurveyLogit:
    """Pseudo-maximum-likelihood logistic regression with linearised (sandwich) variance.

    Weights are rescaled to mean 1 inside the fit (the sandwich variance is invariant to
    weight scaling).  ``ridge`` adds a small L2 penalty on non-intercept coefficients for
    numerical stability with sparse interaction cells (default 0: unpenalised).
    """

    spec: ModelSpec
    ridge: float = 0.0
    max_iter: int = 50
    tol: float = 1e-9

    def fit(self, df: pd.DataFrame, y: np.ndarray, design: SurveyDesign) -> SurveyLogit:
        x, names = self.spec.design_matrix(df)
        y = np.asarray(y, dtype=float)
        if len(y) != design.n or len(df) != design.n:
            raise ValueError("data, outcome and design must have the same rows")
        if not np.isin(y, (0.0, 1.0)).all():
            raise ValueError("outcome must be 0/1 without missing values")
        w = design.weight / design.weight.mean()
        p = x.shape[1]
        pen = np.full(p, self.ridge)
        if self.spec.intercept:
            pen[0] = 0.0
        beta = np.zeros(p)
        if self.spec.intercept:
            ybar = np.clip(np.average(y, weights=w), 1e-6, 1 - 1e-6)
            beta[0] = np.log(ybar / (1 - ybar))

        def objective(b: np.ndarray) -> float:
            eta = x @ b
            # log(1 + exp(eta)) computed stably
            return float(np.sum(w * (y * eta - np.logaddexp(0.0, eta))) - 0.5 * np.sum(pen * b * b))

        converged = False
        obj = objective(beta)
        it = 0
        for it in range(self.max_iter):  # noqa: B007 - reported as n_iter_
            mu = _sigmoid(x @ beta)
            grad = x.T @ (w * (y - mu)) - pen * beta
            hess = (x * (w * mu * (1 - mu))[:, None]).T @ x + np.diag(pen)
            step = np.linalg.lstsq(hess, grad, rcond=None)[0]
            # Damped Newton: halve the step until the penalised log-likelihood improves.
            t = 1.0
            while True:
                cand = beta + t * step
                cand_obj = objective(cand)
                if cand_obj >= obj - 1e-12 * abs(obj) or t < 1e-8:
                    break
                t *= 0.5
            beta, obj = cand, cand_obj
            if np.max(np.abs(t * step)) < self.tol:
                converged = True
                break
        eta = x @ beta
        mu = _sigmoid(eta)
        bread = (x * (w * mu * (1 - mu))[:, None]).T @ x + np.diag(pen)
        a_inv = np.linalg.inv(bread)
        scores = x * (w * (y - mu))[:, None]
        meat = design.vcov_total(scores)
        self.vcov_ = a_inv @ meat @ a_inv
        self.coef_ = beta
        self.names_ = names
        self.design_ = design
        self.converged_ = converged
        self.n_iter_ = it + 1
        self.n_ = design.n
        self.n_events_ = int(y.sum())
        # Keep what predictive margins need for linearisation.
        self._a_inv = a_inv
        self._x = x
        self._resid_w = w * (y - mu)
        self._w = w
        self._df_index = df.index
        return self

    # ----------------------------------------------------------------------------------
    def coef_table(self, level: float = 0.95) -> pd.DataFrame:
        se = np.sqrt(np.diag(self.vcov_))
        t = self.coef_ / se
        df = self.design_.df
        crit = stats.t.ppf(0.5 + level / 2, df)
        return pd.DataFrame(
            {
                "term": self.names_,
                "coef": self.coef_,
                "se": se,
                "t": t,
                "p": 2 * stats.t.sf(np.abs(t), df),
                "odds_ratio": np.exp(self.coef_),
                "or_low": np.exp(self.coef_ - crit * se),
                "or_high": np.exp(self.coef_ + crit * se),
            }
        )

    def wald_test(self, terms: Sequence[str]) -> dict:
        """Design-adjusted Wald F test that all listed coefficients are zero."""
        idx = [self.names_.index(t) for t in terms]
        b = self.coef_[idx]
        v = self.vcov_[np.ix_(idx, idx)]
        q = len(idx)
        w = float(b @ np.linalg.pinv(v) @ b)
        d = self.design_.df
        # Adjusted F (Korn & Graubard style): F = (d - q + 1)/(d q) * W ~ F(q, d - q + 1)
        if d - q + 1 > 0:
            f = (d - q + 1) / (d * q) * w
            p = float(stats.f.sf(f, q, d - q + 1))
        else:
            f, p = np.nan, np.nan
        return {"terms": list(terms), "wald_chi2": w, "q": q, "F": f, "p": p}

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        x, _ = self.spec.design_matrix(df)
        return _sigmoid(x @ self.coef_)

    # ----------------------------------------------------------------------------------
    def margin_influence(
        self,
        df: pd.DataFrame,
        setter: Callable[[pd.DataFrame], pd.DataFrame] | None,
        domain: np.ndarray | None = None,
    ) -> tuple[float, np.ndarray]:
        """Predictive margin and its per-row weighted linearised contribution.

        The margin is the weighted mean, over the (domain of the) fitted sample, of the
        predicted probability after applying ``setter`` (a counterfactual assignment such as
        "everyone speeding").  The linearisation includes both the sampling variability of
        the covariate distribution and of the coefficients, so contrasts between margins get
        unconditional design-based standard errors.
        """
        d = np.ones(len(df), dtype=bool) if domain is None else np.asarray(domain, dtype=bool)
        cf = df if setter is None else setter(df.copy())
        xa, _ = self.spec.design_matrix(cf)
        pa = _sigmoid(xa @ self.coef_)
        w = self._w * d
        big_w = w.sum()
        m = float((w * pa).sum() / big_w)
        g = (xa * (w * pa * (1 - pa))[:, None]).sum(axis=0) / big_w
        infl_beta = (self._x * self._resid_w[:, None]) @ (self._a_inv @ g)
        z = w * (pa - m) / big_w + infl_beta
        return m, z

    def margins(
        self,
        df: pd.DataFrame,
        scenarios: dict[str, Callable[[pd.DataFrame], pd.DataFrame] | None],
        domain: np.ndarray | None = None,
    ) -> MarginSet:
        ms, zs = {}, {}
        for name, setter in scenarios.items():
            ms[name], zs[name] = self.margin_influence(df, setter, domain)
        return MarginSet(ms, zs, self.design_)


@dataclass
class MarginSet:
    """A set of predictive margins with their joint linearisation, for any smooth contrast."""

    values: dict[str, float]
    influence: dict[str, np.ndarray]
    design: SurveyDesign

    def estimate(self, name: str) -> Estimate:
        v = self.design.vcov_total(self.influence[name])[0, 0]
        return Estimate(self.values[name], float(np.sqrt(v)), self.design.df, self.design.n)

    def contrast(self, f: Callable[[dict[str, float]], float], eps: float = 1e-7) -> Estimate:
        """Delta-method estimate of a smooth function of the margins."""
        base = f(self.values)
        grad = {}
        for k in self.values:
            bumped = dict(self.values)
            bumped[k] += eps
            grad[k] = (f(bumped) - base) / eps
        z = sum(grad[k] * self.influence[k] for k in self.values)
        v = self.design.vcov_total(z)[0, 0]
        return Estimate(float(base), float(np.sqrt(v)), self.design.df, self.design.n)

    def difference(self, a: str, b: str) -> Estimate:
        return self.contrast(lambda m: m[a] - m[b])

    def ratio(self, a: str, b: str) -> Estimate:
        return self.contrast(lambda m: m[a] / m[b])

    def log_ratio(self, a: str, b: str) -> Estimate:
        return self.contrast(lambda m: float(np.log(m[a] / m[b])))


def interaction_contrasts(
    ms: MarginSet, p11: str, p10: str, p01: str, p00: str
) -> dict[str, Estimate]:
    """Additive and multiplicative interaction measures from four predictive margins.

    * ``ic``   -- interaction contrast on the risk-difference scale, p11 - p10 - p01 + p00
    * ``reri`` -- relative excess risk due to interaction, RR11 - RR10 - RR01 + 1
    * ``log_ratio_of_rr`` -- log of RR11 / (RR10 * RR01) (multiplicative interaction on the
      risk-ratio scale)
    """
    return {
        "ic": ms.contrast(lambda m: m[p11] - m[p10] - m[p01] + m[p00]),
        "reri": ms.contrast(lambda m: (m[p11] - m[p10] - m[p01] + m[p00]) / m[p00]),
        "log_ratio_of_rr": ms.contrast(
            lambda m: float(np.log(m[p11] * m[p00] / (m[p10] * m[p01])))
        ),
    }
