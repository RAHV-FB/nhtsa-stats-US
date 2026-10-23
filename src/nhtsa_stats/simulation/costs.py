"""Programme cost model, cost-effectiveness and break-even analysis (RQ10 tooling).

Research question
    What would an intervention programme cost, what would it cost per death (or KA crash)
    prevented under stated effectiveness assumptions, and -- more robustly -- how effective
    would it have to be to meet a user-supplied cost-effectiveness threshold?

Population / unit
    None from the data: this module contains no empirical quantity.  Its unit is a programme
    (cameras, roadside checks, or a generic programme) described entirely by user inputs.

Outcome
    Initial investment, annual operating cost, multi-year totals, equivalent annual cost (EAC,
    via the capital recovery factor), present value (PV), cost per death / KA crash prevented,
    incremental (marginal) cost-effectiveness between options, and break-even thresholds:
    (i) minimum deaths prevented per year to meet a threshold, (ii) the minimum value of an
    effectiveness parameter for a scenario to meet it (solved numerically through the engine),
    (iii) the indifference curve over two uncertain effectiveness parameters at which
    intervention X and intervention Y prevent the same number of deaths for an equal budget.

Method
    Standard annuity arithmetic: CRF(r, n) = r(1+r)^n / ((1+r)^n - 1) (1/n when r = 0);
    capital at t = 0 and renewed every service life within the horizon; operating costs at the
    end of each year; discounting at the user's rate.  Incremental analysis removes strongly
    and extendedly dominated options before computing ICERs.

Justified interpretation
    "At an equivalent annual cost of C and a threshold of T per death prevented, the programme
    would need to prevent at least C/T deaths per year; under the stated mechanism that requires
    a behavioural response of at least x."

Not justified
    Any statement that a programme *is* cost-effective: effectiveness is never estimated from
    the data (no enforcement or cost data exist in the database).  No default prices, no
    default discount rate and no monetary value of a statistical life are provided; every
    monetary input is a required argument and a missing one raises ``MissingCostInputError``.
    Fines are transfers, not resource costs or savings, and are not modelled.
"""

from __future__ import annotations

import itertools
import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, fields
from typing import Any

import numpy as np
import pandas as pd
from scipy import optimize

from nhtsa_stats.simulation import engine

HYPOTHETICAL = engine.HYPOTHETICAL
ArrayLike = float | np.ndarray


class MissingCostInputError(ValueError):
    """A required monetary or programme input was not supplied (no default prices exist)."""


# ======================================================================================
# Annuity arithmetic
# ======================================================================================
def _check_rate(rate: float | None, owner: str = "discount_rate") -> float:
    if rate is None:
        raise MissingCostInputError(f"{owner}: a discount rate is required (no default)")
    r = float(rate)
    if not math.isfinite(r) or r < 0 or r >= 1:
        raise ValueError(f"{owner}: discount rate must be in [0, 1), got {rate!r}")
    return r


def _check_years(years: float, name: str = "years") -> float:
    n = float(years)
    if not math.isfinite(n) or n <= 0:
        raise ValueError(f"{name} must be a positive number, got {years!r}")
    return n


def capital_recovery_factor(rate: float, years: float) -> float:
    """CRF(r, n) = r(1+r)^n / ((1+r)^n - 1); 1/n when r = 0.  EAC of capital K = K * CRF."""
    r, n = _check_rate(rate), _check_years(years)
    if r == 0:
        return 1.0 / n
    g = (1.0 + r) ** n
    return r * g / (g - 1.0)


def annuity_factor(rate: float, years: float) -> float:
    """PV of 1 per year at the end of years 1..n: (1 - (1+r)^-n) / r; n when r = 0."""
    r, n = _check_rate(rate), _check_years(years)
    if r == 0:
        return n
    return (1.0 - (1.0 + r) ** (-n)) / r


def discount_factor(rate: float, t: float) -> float:
    return (1.0 + _check_rate(rate)) ** (-float(t))


def present_value(flows: Sequence[float] | np.ndarray, rate: float, start: int = 1) -> float:
    """PV of ``flows`` occurring at t = start, start + 1, ... (end-of-year convention)."""
    r = _check_rate(rate)
    f = np.asarray(flows, dtype=float)
    t = np.arange(start, start + len(f))
    return float(np.sum(f * (1.0 + r) ** (-t)))


def _require(owner: str, obj: Any, names: Sequence[str]) -> None:
    missing = [n for n in names if getattr(obj, n) is None]
    if missing:
        raise MissingCostInputError(
            f"{owner}: missing required inputs: {', '.join(missing)}. This project supplies no "
            "default prices, rates or service lives -- every monetary input must come from the "
            "user (see docs/policy_assumptions.md)."
        )
    for n in names:
        v = float(getattr(obj, n))
        if not math.isfinite(v) or v < 0:
            raise ValueError(f"{owner}: {n} must be a finite non-negative number, got {v!r}")


# ======================================================================================
# Programme costs
# ======================================================================================
@dataclass(frozen=True)
class ProgrammeCosts:
    """Generic programme: one-off investment (renewed every service life), annual operating
    cost, service life and discount rate.  All inputs required."""

    initial_investment: float | None = None
    annual_operating: float | None = None
    service_life_years: float | None = None
    discount_rate: float | None = None
    label: str = "programme"
    breakdown: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require(
            "ProgrammeCosts",
            self,
            ["initial_investment", "annual_operating", "service_life_years", "discount_rate"],
        )
        _check_years(self.service_life_years, "service_life_years")  # type: ignore[arg-type]
        _check_rate(self.discount_rate)

    @property
    def crf(self) -> float:
        return capital_recovery_factor(self.discount_rate, self.service_life_years)  # type: ignore[arg-type]

    def annualised_capital(self) -> float:
        return float(self.initial_investment) * self.crf  # type: ignore[arg-type]

    def equivalent_annual_cost(self) -> float:
        """EAC = investment x CRF(r, service life) + annual operating cost."""
        return self.annualised_capital() + float(self.annual_operating)  # type: ignore[arg-type]

    def capital_times(self, horizon_years: int) -> list[float]:
        """Investment at t = 0 and renewals every service life strictly before the horizon."""
        h = int(horizon_years)
        if h < 1:
            raise ValueError("horizon_years must be >= 1")
        life = float(self.service_life_years)  # type: ignore[arg-type]
        times, t = [], 0.0
        while t < h:
            times.append(t)
            t += life
        return times

    def residual_value(self, horizon_years: int) -> float:
        """Straight-line unexpired value of the last capital vintage at the horizon."""
        life = float(self.service_life_years)  # type: ignore[arg-type]
        last = self.capital_times(horizon_years)[-1]
        frac = max(0.0, (last + life - horizon_years) / life)
        return float(self.initial_investment) * frac  # type: ignore[arg-type]

    def total_undiscounted(self, horizon_years: int) -> float:
        """Multi-year total: investments (incl. renewals) + operating costs over the horizon."""
        n_cap = len(self.capital_times(horizon_years))
        return n_cap * float(self.initial_investment) + horizon_years * float(self.annual_operating)  # type: ignore[arg-type]

    def present_value(self, horizon_years: int, residual_credit: bool = False) -> float:
        """PV over ``horizon_years``: capital at t=0 and renewals, operating at t=1..H, minus
        the discounted straight-line residual value if ``residual_credit``."""
        r = float(self.discount_rate)  # type: ignore[arg-type]
        pv_cap = sum(
            float(self.initial_investment) * (1 + r) ** (-t)
            for t in self.capital_times(horizon_years)
        )  # type: ignore[arg-type]
        pv_op = float(self.annual_operating) * annuity_factor(r, horizon_years)  # type: ignore[arg-type]
        pv = pv_cap + pv_op
        if residual_credit:
            pv -= self.residual_value(horizon_years) * (1 + r) ** (-horizon_years)
        return float(pv)

    def cash_flows(self, horizon_years: int) -> pd.DataFrame:
        """Year-by-year undiscounted and discounted cash flows (year 0 = investment).

        A renewal at a fractional time t (non-integer service life) is listed in year
        floor(t) but discounted at t, so ``discounted`` sums to ``present_value``.
        """
        r = float(self.discount_rate)  # type: ignore[arg-type]
        h = int(horizon_years)
        k = float(self.initial_investment)  # type: ignore[arg-type]
        cap, cap_pv = np.zeros(h + 1), np.zeros(h + 1)
        for t in self.capital_times(h):
            cap[math.floor(t)] += k
            cap_pv[math.floor(t)] += k * (1 + r) ** (-t)
        op = np.r_[0.0, np.full(h, float(self.annual_operating))]  # type: ignore[arg-type]
        df = pd.DataFrame({"year": np.arange(h + 1), "capital": cap, "operating": op})
        df["total"] = df["capital"] + df["operating"]
        df["discount_factor"] = (1 + r) ** (-df["year"].astype(float))
        df["discounted"] = cap_pv + df["operating"] * df["discount_factor"]
        df["label"] = self.label
        return df

    def summary(self, horizon_years: int | None = None) -> dict[str, Any]:
        out = {
            "label": self.label,
            "initial_investment": float(self.initial_investment),  # type: ignore[arg-type]
            "annual_operating": float(self.annual_operating),  # type: ignore[arg-type]
            "service_life_years": float(self.service_life_years),  # type: ignore[arg-type]
            "discount_rate": float(self.discount_rate),  # type: ignore[arg-type]
            "capital_recovery_factor": self.crf,
            "equivalent_annual_cost": self.equivalent_annual_cost(),
            "breakdown": dict(self.breakdown),
            "kind": "user cost inputs",
        }
        if horizon_years is not None:
            out["horizon_years"] = int(horizon_years)
            out["total_undiscounted"] = self.total_undiscounted(horizon_years)
            out["present_value"] = self.present_value(horizon_years)
        return out


@dataclass(frozen=True)
class SpeedCameraCosts:
    """Unit costs of automated speed enforcement (all monetary inputs required).

    Admin/processing cost per citation and citations per camera-year are optional *together*:
    when omitted the admin component is excluded (shown as such in the breakdown), not priced
    at zero by assumption.
    """

    acquisition_per_unit: float | None = None
    installation_per_unit: float | None = None
    maintenance_per_unit_year: float | None = None
    operations_per_unit_year: float | None = None
    service_life_years: float | None = None
    discount_rate: float | None = None
    admin_per_citation: float | None = None
    citations_per_unit_year: float | None = None

    REQUIRED = (
        "acquisition_per_unit",
        "installation_per_unit",
        "maintenance_per_unit_year",
        "operations_per_unit_year",
        "service_life_years",
        "discount_rate",
    )

    def __post_init__(self) -> None:
        _require("SpeedCameraCosts", self, self.REQUIRED)
        _check_years(self.service_life_years, "service_life_years")  # type: ignore[arg-type]
        _check_rate(self.discount_rate)
        pair = (self.admin_per_citation, self.citations_per_unit_year)
        if (pair[0] is None) != (pair[1] is None):
            raise MissingCostInputError(
                "SpeedCameraCosts: admin_per_citation and citations_per_unit_year must be given "
                "together (or both omitted to exclude the admin component)"
            )
        if pair[0] is not None:
            _require("SpeedCameraCosts", self, ["admin_per_citation", "citations_per_unit_year"])

    def annual_per_unit(self) -> float:
        admin = (
            0.0
            if self.admin_per_citation is None
            else float(self.admin_per_citation) * float(self.citations_per_unit_year)  # type: ignore[arg-type]
        )
        return float(self.maintenance_per_unit_year) + float(self.operations_per_unit_year) + admin  # type: ignore[arg-type]

    def programme(self, units: float, label: str = "speed cameras") -> ProgrammeCosts:
        u = float(units)
        if not math.isfinite(u) or u < 0:
            raise ValueError(f"units must be finite and >= 0, got {units!r}")
        capital = u * (float(self.acquisition_per_unit) + float(self.installation_per_unit))  # type: ignore[arg-type]
        breakdown = {
            "acquisition": u * float(self.acquisition_per_unit),  # type: ignore[arg-type]
            "installation": u * float(self.installation_per_unit),  # type: ignore[arg-type]
            "maintenance_per_year": u * float(self.maintenance_per_unit_year),  # type: ignore[arg-type]
            "operations_per_year": u * float(self.operations_per_unit_year),  # type: ignore[arg-type]
            "admin_per_year": (
                u * float(self.admin_per_citation) * float(self.citations_per_unit_year)  # type: ignore[arg-type]
                if self.admin_per_citation is not None
                else float("nan")
            ),
        }
        return ProgrammeCosts(
            capital,
            u * self.annual_per_unit(),
            self.service_life_years,
            self.discount_rate,
            label=f"{label} ({u:g} units)",
            breakdown=breakdown,
        )

    def incremental(self, units_current: float, units_proposed: float) -> ProgrammeCosts:
        """Costs of the *additional* units (the engine's effects are incremental too)."""
        if units_proposed < units_current:
            raise ValueError("incremental costs of removing units are not modelled")
        return self.programme(units_proposed - units_current, label="additional speed cameras")


@dataclass(frozen=True)
class RoadsideCheckCosts:
    """Unit costs of roadside alcohol/drug checks (all inputs required).

    Per check: staff-hours x cost per staff-hour + screening tests x materials per test +
    confirmed (evidential/laboratory) tests x lab cost.  Programme-level: equipment capital
    (with its service life) and fixed recurring costs (training, administration, calibration).
    """

    staff_hours_per_check: float | None = None
    cost_per_staff_hour: float | None = None
    tests_per_check: float | None = None
    materials_per_test: float | None = None
    confirmed_tests_per_check: float | None = None
    lab_cost_per_confirmed_test: float | None = None
    equipment_capital: float | None = None
    equipment_life_years: float | None = None
    recurring_fixed_per_year: float | None = None
    discount_rate: float | None = None

    def __post_init__(self) -> None:
        _require("RoadsideCheckCosts", self, [f.name for f in fields(self)])
        _check_years(self.equipment_life_years, "equipment_life_years")  # type: ignore[arg-type]
        _check_rate(self.discount_rate)

    def cost_per_check(self) -> float:
        return (
            float(self.staff_hours_per_check) * float(self.cost_per_staff_hour)  # type: ignore[arg-type]
            + float(self.tests_per_check) * float(self.materials_per_test)  # type: ignore[arg-type]
            + float(self.confirmed_tests_per_check) * float(self.lab_cost_per_confirmed_test)  # type: ignore[arg-type]
        )

    def programme(
        self, checks_per_year: float, include_fixed: bool = True, label: str = "roadside checks"
    ) -> ProgrammeCosts:
        c = float(checks_per_year)
        if not math.isfinite(c) or c < 0:
            raise ValueError(f"checks_per_year must be finite and >= 0, got {checks_per_year!r}")
        variable = c * self.cost_per_check()
        fixed = float(self.recurring_fixed_per_year) if include_fixed else 0.0  # type: ignore[arg-type]
        return ProgrammeCosts(
            float(self.equipment_capital) if include_fixed else 0.0,  # type: ignore[arg-type]
            variable + fixed,
            self.equipment_life_years,
            self.discount_rate,
            label=f"{label} ({c:g} checks/yr)",
            breakdown={
                "staff_per_year": c
                * float(self.staff_hours_per_check)
                * float(self.cost_per_staff_hour),  # type: ignore[arg-type]
                "materials_per_year": c
                * float(self.tests_per_check)
                * float(self.materials_per_test),  # type: ignore[arg-type]
                "lab_per_year": c
                * float(self.confirmed_tests_per_check)
                * float(self.lab_cost_per_confirmed_test),  # type: ignore[arg-type]
                "recurring_fixed_per_year": fixed,
                "equipment_capital": float(self.equipment_capital) if include_fixed else 0.0,  # type: ignore[arg-type]
            },
        )

    def incremental(
        self, checks_current: float, checks_proposed: float, *, new_programme: bool
    ) -> ProgrammeCosts:
        """Costs of the additional checks.  ``new_programme`` (required, no default) decides
        whether equipment and fixed recurring costs are incurred (True) or already exist."""
        if checks_proposed < checks_current:
            raise ValueError("incremental costs of fewer checks are not modelled")
        return self.programme(
            checks_proposed - checks_current, include_fixed=new_programme, label="additional checks"
        )


# ======================================================================================
# Cost-effectiveness
# ======================================================================================
def _ratio(cost: float, effect: ArrayLike) -> ArrayLike:
    e = np.asarray(effect, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        r = np.where(e > 0, cost / np.where(e > 0, e, 1.0), np.inf)
    return r if r.ndim else float(r)


def _dist_summary(x: np.ndarray) -> dict[str, float]:
    finite = x[np.isfinite(x)]
    out = {"share_undefined_no_benefit": float(1 - len(finite) / len(x)) if len(x) else math.nan}
    if len(finite):
        q = np.percentile(finite, [5, 50, 95])
        out.update(p5=float(q[0]), p50=float(q[1]), p95=float(q[2]))
    return out


def cost_effectiveness(
    programme: ProgrammeCosts,
    deaths_prevented: ArrayLike,
    ka_prevented: ArrayLike | None = None,
    fatal_crashes_prevented: ArrayLike | None = None,
) -> dict[str, Any]:
    """Steady-state cost per outcome prevented = EAC / annual outcomes prevented.

    Accepts point values or Monte Carlo arrays (then returns percentiles over draws with a
    positive benefit and the share of draws with no benefit, where the ratio is undefined).
    """
    eac = programme.equivalent_annual_cost()
    out: dict[str, Any] = {
        "kind": HYPOTHETICAL,
        "label": programme.label,
        "equivalent_annual_cost": eac,
    }
    for name, eff in (
        ("death", deaths_prevented),
        ("ka_crash", ka_prevented),
        ("fatal_crash", fatal_crashes_prevented),
    ):
        if eff is None:
            out[f"cost_per_{name}_prevented"] = None
            continue
        r = _ratio(eac, eff)
        if np.ndim(r):
            out[f"cost_per_{name}_prevented"] = _dist_summary(np.asarray(r))
        else:
            out[f"cost_per_{name}_prevented"] = r
    out["cost_inputs"] = programme.summary()
    return out


def cost_effectiveness_over_horizon(
    programme: ProgrammeCosts,
    prevented_by_year: Sequence[float],
    outcome_discount_rate: float,
    residual_credit: bool = False,
) -> dict[str, Any]:
    """PV(costs over the horizon) / PV(outcomes prevented), outcomes at the end of years 1..H.

    ``outcome_discount_rate`` is required: whether and how much to discount health outcomes is
    a value judgement the user must make explicitly (0 is allowed).
    """
    h = len(prevented_by_year)
    pv_cost = programme.present_value(h, residual_credit)
    pv_out = present_value(prevented_by_year, outcome_discount_rate)
    return {
        "kind": HYPOTHETICAL,
        "horizon_years": h,
        "pv_costs": pv_cost,
        "pv_outcomes_prevented": pv_out,
        "undiscounted_outcomes_prevented": float(np.sum(prevented_by_year)),
        "cost_per_outcome_prevented": _ratio(pv_cost, pv_out),
        "cost_discount_rate": programme.discount_rate,
        "outcome_discount_rate": float(outcome_discount_rate),
    }


def marginal_cost_effectiveness(
    cost_a: float, effect_a: float, cost_b: float, effect_b: float
) -> dict[str, Any]:
    """Incremental cost-effectiveness of B relative to A, with dominance."""
    dc, de = float(cost_b) - float(cost_a), float(effect_b) - float(effect_a)
    if de >= 0 and dc <= 0 and (de > 0 or dc < 0):
        status, icer = "B dominates A (no more costly, at least as effective)", None
    elif de <= 0 and dc >= 0 and (de < 0 or dc > 0):
        status, icer = "B dominated by A", None
    elif de == 0:
        status, icer = "equal effect and cost", None
    else:
        status, icer = (
            ("B more effective at extra cost" if de > 0 else "B cheaper, less effective"),
            dc / de,
        )
    return {
        "kind": HYPOTHETICAL,
        "delta_cost": dc,
        "delta_effect": de,
        "icer": icer,
        "status": status,
    }


def incremental_analysis(
    options: pd.DataFrame | Sequence[Mapping[str, Any]],
    include_status_quo: bool = True,
) -> pd.DataFrame:
    """Cost-effectiveness frontier over options with columns ``name``, ``cost`` (annual,
    e.g. EAC) and ``effect`` (e.g. deaths prevented per year).

    Strongly dominated options (another option is no costlier and at least as effective) and
    extendedly dominated options (a mix of neighbours would dominate) are flagged; ICERs are
    computed between consecutive frontier options.
    """
    df = pd.DataFrame(options).copy()
    for c in ("name", "cost", "effect"):
        if c not in df:
            raise ValueError(f"options need column {c!r}")
    if include_status_quo:
        df = pd.concat(
            [pd.DataFrame([{"name": "status_quo", "cost": 0.0, "effect": 0.0}]), df],
            ignore_index=True,
        )
    df["cost"] = df["cost"].astype(float)
    df["effect"] = df["effect"].astype(float)
    df = df.sort_values(["effect", "cost"], kind="stable").reset_index(drop=True)
    status = pd.Series("frontier", index=df.index)
    for i in df.index:
        others = df.drop(index=i)
        dom = (
            (others["cost"] <= df.at[i, "cost"])
            & (others["effect"] >= df.at[i, "effect"])
            & ((others["cost"] < df.at[i, "cost"]) | (others["effect"] > df.at[i, "effect"]))
        )
        if dom.any():
            status[i] = "dominated"
    frontier = [i for i in df.index if status[i] == "frontier"]
    changed = True
    while changed and len(frontier) > 2:
        changed = False
        icers = [
            (df.at[b, "cost"] - df.at[a, "cost"]) / (df.at[b, "effect"] - df.at[a, "effect"])
            for a, b in itertools.pairwise(frontier)
        ]
        for j in range(1, len(icers)):
            if icers[j] < icers[j - 1]:
                status[frontier[j]] = "extended_dominated"
                frontier.pop(j)
                changed = True
                break
    df["status"] = status
    df["comparator"] = None
    df["icer"] = np.nan
    for a, b in itertools.pairwise(frontier):
        df.at[b, "comparator"] = df.at[a, "name"]
        de = df.at[b, "effect"] - df.at[a, "effect"]
        df.at[b, "icer"] = (df.at[b, "cost"] - df.at[a, "cost"]) / de if de else np.nan
    df["kind"] = HYPOTHETICAL
    return df


# ======================================================================================
# Break-even
# ======================================================================================
def _positive(x: float | None, name: str) -> float:
    if x is None:
        raise MissingCostInputError(f"{name} is required (no default)")
    v = float(x)
    if not math.isfinite(v) or v <= 0:
        raise ValueError(f"{name} must be a positive number, got {x!r}")
    return v


def breakeven_deaths(annual_cost: float, threshold_cost_per_death: float) -> float:
    """(i) Minimum deaths prevented per year for cost per death <= threshold: C / T."""
    c = float(annual_cost)
    if not math.isfinite(c) or c < 0:
        raise ValueError("annual_cost must be finite and non-negative")
    return c / _positive(threshold_cost_per_death, "threshold_cost_per_death")


def net_benefit(
    annual_cost: float, outcomes_prevented: ArrayLike, value_per_outcome: float | None
) -> ArrayLike:
    """Monetised net benefit = value x outcomes - cost.  ``value_per_outcome`` (e.g. a value
    per statistical life) must be supplied by the user; none is assumed."""
    v = _positive(value_per_outcome, "value_per_outcome")
    nb = v * np.asarray(outcomes_prevented, dtype=float) - float(annual_cost)
    return nb if nb.ndim else float(nb)


def breakeven_parameter(
    scenario: engine.Scenario,
    baseline: engine.EmpiricalBaseline,
    parameter: str,
    programme: ProgrammeCosts,
    threshold_cost_per_outcome: float,
    outcome: str = "deaths_prevented",
    bounds: tuple[float, float] | None = None,
    horizon_years: int | None = None,
    outcome_discount_rate: float | None = None,
    values: Mapping[str, float] | None = None,
) -> dict[str, Any]:
    """(ii) Minimum value of an effectiveness parameter for the scenario to meet the threshold.

    Steady state (default): annual outcome(parameter) >= EAC / threshold.  With
    ``horizon_years``: PV of outcomes (with the scenario's ramp-up/decay; outcome discount rate
    required) >= PV of costs / threshold.  Other parameters stay at their central values (or
    ``values``).  Solved numerically through the engine.
    """
    thr = _positive(threshold_cost_per_outcome, "threshold_cost_per_outcome")
    if horizon_years is None:
        required = programme.equivalent_annual_cost() / thr
        res = engine.solve_scenario_parameter(
            scenario, baseline, parameter, required, outcome, bounds, values=values
        )
        basis = "steady state: EAC / threshold"
    else:
        if outcome_discount_rate is None:
            raise MissingCostInputError("outcome_discount_rate is required with horizon_years")
        required = programme.present_value(horizon_years) / thr
        params = engine.flat_parameters(scenario, baseline)
        if parameter not in params:
            raise KeyError(f"unknown parameter {parameter!r}; parameters are {sorted(params)}")

        def pv_outcome(x: float) -> float:
            proj = engine.project(
                scenario, baseline, horizon_years, values={**(values or {}), parameter: x}
            )
            col = proj[outcome]
            if col.isna().any():
                raise ValueError(f"{outcome} not defined for this scenario")
            return present_value(col.to_numpy(), outcome_discount_rate)

        res = {
            "kind": HYPOTHETICAL,
            "parameter": parameter,
            "outcome": outcome,
            **engine.solve_monotone(
                pv_outcome, required, engine.search_bounds(params[parameter], bounds)
            ),
        }
        basis = f"PV over {horizon_years} years: PV(costs) / threshold vs PV(outcomes)"
    meaning = {
        "solved": (
            "minimum value required"
            if res.get("direction") == "increasing"
            else "maximum value allowed"
        ),
        "met_throughout_bounds": "threshold met for every value in the search bounds",
        "not_achievable": "threshold not met for any value in the search bounds",
    }[res["status"]]
    return {
        **res,
        "required_outcome": required,
        "basis": basis,
        "threshold_cost_per_outcome": thr,
        "interpretation": meaning,
        "programme": programme.summary(),
    }


def units_for_budget(
    cost_of_units: Callable[[float], ProgrammeCosts],
    annual_budget: float,
    max_units: float,
) -> dict[str, Any]:
    """Units whose equivalent annual cost equals ``annual_budget`` (EAC increasing in units)."""
    b = _positive(annual_budget, "annual_budget")
    hi = _positive(max_units, "max_units")

    def gap(u: float) -> float:
        return cost_of_units(u).equivalent_annual_cost() - b

    if gap(0.0) > 0:
        return {"units": 0.0, "status": "budget below fixed costs"}
    if gap(hi) < 0:
        return {"units": hi, "status": "budget not exhausted at max_units"}
    u = optimize.brentq(gap, 0.0, hi, xtol=1e-9)
    return {"units": float(u), "status": "solved"}


def indifference_curve(
    scenario_x: engine.Scenario,
    param_x: str,
    scenario_y: engine.Scenario,
    param_y: str,
    baseline: engine.EmpiricalBaseline,
    grid_x: Sequence[float] | None = None,
    n_grid: int = 21,
    bounds_y: tuple[float, float] | None = None,
    outcome: str = "deaths_prevented",
) -> pd.DataFrame:
    """(iii) For each value of X's uncertain parameter, the value of Y's parameter at which Y
    prevents exactly as many outcomes as X.  With both scenarios set to the deployment an
    equal budget buys (see ``equal_budget_indifference``), Y outperforms X above the curve
    (when Y's outcome increases in its parameter) and X outperforms Y below it."""
    px = engine.flat_parameters(scenario_x, baseline)[param_x]
    if grid_x is None:
        lo, hi = engine.search_bounds(px, None)
        grid_x = np.linspace(lo, hi, n_grid)
    rows = []
    for x in grid_x:
        out_x = engine.evaluate(scenario_x, baseline, {param_x: float(x)})[outcome]
        if out_x is None:
            raise ValueError(f"{outcome} not defined for scenario {scenario_x.name!r}")
        sol = engine.solve_scenario_parameter(
            scenario_y, baseline, param_y, out_x, outcome, bounds_y
        )
        rows.append(
            {
                "x_parameter": f"{scenario_x.name}.{param_x}",
                "x_value": float(x),
                f"{outcome}_x": float(out_x),
                "y_parameter": f"{scenario_y.name}.{param_y}",
                "y_indifference_value": sol["value"] if sol["status"] == "solved" else np.nan,
                "status": sol["status"],
                "y_direction": sol.get("direction"),
                "kind": HYPOTHETICAL,
            }
        )
    return pd.DataFrame(rows)


def equal_budget_indifference(
    annual_budget: float,
    cost_x: Callable[[float], ProgrammeCosts],
    build_x: Callable[[float], engine.Scenario],
    param_x: str,
    max_units_x: float,
    cost_y: Callable[[float], ProgrammeCosts],
    build_y: Callable[[float], engine.Scenario],
    param_y: str,
    max_units_y: float,
    baseline: engine.EmpiricalBaseline,
    grid_x: Sequence[float] | None = None,
    n_grid: int = 21,
    bounds_y: tuple[float, float] | None = None,
) -> dict[str, Any]:
    """Deploy each intervention at the scale the same annual budget buys (EAC = budget), then
    trace the indifference curve over the two uncertain effectiveness parameters."""
    ux = units_for_budget(cost_x, annual_budget, max_units_x)
    uy = units_for_budget(cost_y, annual_budget, max_units_y)
    sx, sy = build_x(ux["units"]), build_y(uy["units"])
    curve = indifference_curve(sx, param_x, sy, param_y, baseline, grid_x, n_grid, bounds_y)
    return {
        "kind": HYPOTHETICAL,
        "annual_budget": float(annual_budget),
        "units_x": ux,
        "units_y": uy,
        "curve": curve,
        "reading": f"Y ({sy.name}) prevents more outcomes than X ({sx.name}) for the same budget "
        f"when {param_y} exceeds y_indifference_value at the assumed {param_x}",
    }
