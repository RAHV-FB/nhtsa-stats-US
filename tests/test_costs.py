"""Cost model, cost-effectiveness and break-even solving (synthetic inputs only).

All prices below are arbitrary software fixtures, not estimates of real costs.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from nhtsa_stats.simulation import costs as c
from nhtsa_stats.simulation import engine as e


def fs(*s: str) -> frozenset[str]:
    return frozenset(s)


def toy_baseline() -> e.EmpiricalBaseline:
    """1000 deaths/yr: speeding 200 (exceeded 50), alcohol 210 (50 shared with speeding)."""
    deaths = e.Partition(
        "deaths",
        e.PARTITION_SEGMENTS,
        {
            fs(): 640.0,
            fs("speeding"): 100.0,
            fs("speeding", "speeding_exceeded_limit"): 50.0,
            fs("alcohol"): 160.0,
            fs("speeding", "alcohol"): 50.0,
        },
        "observed",
        "toy",
    )
    fatal = e.Partition(
        "fatal_crashes",
        e.CRASH_SEGMENTS,
        {fs(): 700.0, fs("speeding"): 200.0, fs("alcohol"): 100.0},
        "observed",
        "toy",
    )
    return e.EmpiricalBaseline((2022, 2024), {}, deaths, fatal)


def camera_costs(**kw) -> c.SpeedCameraCosts:
    args = dict(
        acquisition_per_unit=80.0,
        installation_per_unit=20.0,
        maintenance_per_unit_year=5.0,
        operations_per_unit_year=10.0,
        service_life_years=10,
        discount_rate=0.05,
    )
    args.update(kw)
    return c.SpeedCameraCosts(**args)


def check_costs(**kw) -> c.RoadsideCheckCosts:
    args = dict(
        staff_hours_per_check=4.0,
        cost_per_staff_hour=50.0,
        tests_per_check=100.0,
        materials_per_test=1.0,
        confirmed_tests_per_check=2.0,
        lab_cost_per_confirmed_test=25.0,
        equipment_capital=1000.0,
        equipment_life_years=5,
        recurring_fixed_per_year=300.0,
        discount_rate=0.03,
    )
    args.update(kw)
    return c.RoadsideCheckCosts(**args)


# --------------------------------------------------------------------------------------
# Annuity arithmetic
# --------------------------------------------------------------------------------------
def test_capital_recovery_and_annuity_factors():
    assert c.capital_recovery_factor(0.05, 10) == pytest.approx(0.12950457496545661)
    assert c.capital_recovery_factor(0.0, 8) == pytest.approx(1 / 8)
    for r, n in ((0.0, 5), (0.03, 7), (0.1, 20), (0.05, 2.5)):
        assert c.annuity_factor(r, n) * c.capital_recovery_factor(r, n) == pytest.approx(1.0)
    assert c.annuity_factor(0.05, 10) == pytest.approx(7.721734929184818)
    assert c.discount_factor(0.1, 2) == pytest.approx(1 / 1.21)
    assert c.present_value([100, 100], 0.1) == pytest.approx(100 / 1.1 + 100 / 1.21)
    assert c.present_value([50], 0.1, start=0) == pytest.approx(50)
    with pytest.raises(ValueError):
        c.capital_recovery_factor(1.2, 10)
    with pytest.raises(ValueError):
        c.capital_recovery_factor(0.05, 0)
    with pytest.raises(c.MissingCostInputError):
        c.capital_recovery_factor(None, 10)


def test_programme_eac_pv_and_renewals():
    p = c.ProgrammeCosts(1000.0, 100.0, 5, 0.05)
    crf = c.capital_recovery_factor(0.05, 5)
    assert p.equivalent_annual_cost() == pytest.approx(1000 * crf + 100)
    # over exactly one service life, PV = EAC x annuity factor
    assert p.present_value(5) == pytest.approx(
        p.equivalent_annual_cost() * c.annuity_factor(0.05, 5)
    )
    # 12 years: investments at 0, 5, 10; residual of the last vintage 3/5 of its value
    assert p.capital_times(12) == [0.0, 5.0, 10.0]
    assert p.total_undiscounted(12) == pytest.approx(3 * 1000 + 12 * 100)
    assert p.residual_value(12) == pytest.approx(600.0)
    pv = 1000 * (1 + 1.05**-5 + 1.05**-10) + 100 * c.annuity_factor(0.05, 12)
    assert p.present_value(12) == pytest.approx(pv)
    assert p.present_value(12, residual_credit=True) == pytest.approx(pv - 600 * 1.05**-12)
    cf = p.cash_flows(12)
    assert cf["discounted"].sum() == pytest.approx(p.present_value(12))
    assert cf["total"].sum() == pytest.approx(p.total_undiscounted(12))
    s = p.summary(12)
    assert s["present_value"] == pytest.approx(pv)
    # non-integer service life: renewals at 2.5, 5.0, 7.5 are discounted at their exact times
    q = c.ProgrammeCosts(1000.0, 100.0, 2.5, 0.05)
    cfq = q.cash_flows(9)
    assert cfq["discounted"].sum() == pytest.approx(q.present_value(9))
    assert cfq.loc[cfq["year"] == 2, "capital"].item() == pytest.approx(1000.0)


def test_missing_and_invalid_cost_inputs():
    with pytest.raises(c.MissingCostInputError, match="acquisition_per_unit"):
        c.SpeedCameraCosts()
    with pytest.raises(c.MissingCostInputError, match="discount_rate"):
        camera_costs(discount_rate=None)
    with pytest.raises(ValueError):
        camera_costs(maintenance_per_unit_year=-1.0)
    with pytest.raises(ValueError):
        camera_costs(maintenance_per_unit_year=float("inf"))
    with pytest.raises(ValueError):
        camera_costs(discount_rate=1.5)
    with pytest.raises(ValueError):
        camera_costs(service_life_years=0)
    with pytest.raises(c.MissingCostInputError, match="together"):
        camera_costs(admin_per_citation=2.0)
    with pytest.raises(c.MissingCostInputError, match="lab_cost_per_confirmed_test"):
        check_costs(lab_cost_per_confirmed_test=None)
    with pytest.raises(c.MissingCostInputError):
        c.ProgrammeCosts(100.0, 10.0, 5)
    with pytest.raises(TypeError):
        check_costs().incremental(0, 10)  # new_programme must be stated explicitly


def test_speed_camera_programme():
    cc = camera_costs()
    p = cc.programme(10)
    assert p.initial_investment == pytest.approx(1000.0)
    assert p.annual_operating == pytest.approx(150.0)
    assert math.isnan(p.breakdown["admin_per_year"])  # excluded, not priced at zero
    ca = camera_costs(admin_per_citation=2.0, citations_per_unit_year=100.0)
    assert ca.programme(10).annual_operating == pytest.approx(150.0 + 10 * 200.0)
    inc = cc.incremental(10, 15)
    assert inc.initial_investment == pytest.approx(500.0)
    with pytest.raises(ValueError):
        cc.incremental(15, 10)
    with pytest.raises(ValueError):
        cc.programme(-1)


def test_roadside_check_programme():
    rc = check_costs()
    assert rc.cost_per_check() == pytest.approx(4 * 50 + 100 * 1 + 2 * 25)
    p = rc.programme(100)
    assert p.initial_investment == pytest.approx(1000.0)
    assert p.annual_operating == pytest.approx(100 * 350 + 300)
    inc = rc.incremental(100, 150, new_programme=False)
    assert inc.initial_investment == 0 and inc.annual_operating == pytest.approx(50 * 350)
    new = rc.incremental(0, 50, new_programme=True)
    assert new.annual_operating == pytest.approx(50 * 350 + 300)


# --------------------------------------------------------------------------------------
# Cost-effectiveness
# --------------------------------------------------------------------------------------
def test_cost_effectiveness_point_and_draws():
    p = c.ProgrammeCosts(0.0, 1000.0, 5, 0.0)
    r = c.cost_effectiveness(p, 20.0, ka_prevented=50.0)
    assert r["cost_per_death_prevented"] == pytest.approx(50.0)
    assert r["cost_per_ka_crash_prevented"] == pytest.approx(20.0)
    assert r["cost_per_fatal_crash_prevented"] is None
    assert r["kind"] == "hypothetical"
    assert math.isinf(c.cost_effectiveness(p, 0.0)["cost_per_death_prevented"])
    d = c.cost_effectiveness(p, np.array([10.0, 20.0, 40.0, -1.0]))["cost_per_death_prevented"]
    assert d["share_undefined_no_benefit"] == pytest.approx(0.25)
    assert d["p50"] == pytest.approx(50.0)
    h = c.cost_effectiveness_over_horizon(p, [10.0, 10.0], outcome_discount_rate=0.0)
    assert h["cost_per_outcome_prevented"] == pytest.approx(2000.0 / 20.0)


def test_marginal_cost_effectiveness_statuses():
    r = c.marginal_cost_effectiveness(100, 10, 300, 20)
    assert r["icer"] == pytest.approx(20.0)
    assert "dominates" in c.marginal_cost_effectiveness(100, 10, 90, 12)["status"]
    assert "dominated" in c.marginal_cost_effectiveness(100, 10, 120, 8)["status"]


def test_incremental_analysis_dominance():
    opts = [
        {"name": "A", "cost": 100.0, "effect": 10.0},
        {"name": "D", "cost": 150.0, "effect": 11.0},
        {"name": "B", "cost": 300.0, "effect": 12.0},
        {"name": "C", "cost": 250.0, "effect": 30.0},
    ]
    out = c.incremental_analysis(opts).set_index("name")
    assert out.loc["B", "status"] == "dominated"
    assert out.loc["D", "status"] == "extended_dominated"
    assert out.loc["A", "status"] == "extended_dominated"
    assert out.loc["C", "status"] == "frontier"
    assert out.loc["C", "comparator"] == "status_quo"
    assert out.loc["C", "icer"] == pytest.approx(250 / 30)
    simple = c.incremental_analysis(
        [{"name": "X", "cost": 100.0, "effect": 10.0}, {"name": "Y", "cost": 400.0, "effect": 20.0}]
    ).set_index("name")
    assert simple.loc["X", "icer"] == pytest.approx(10.0)
    assert simple.loc["Y", "icer"] == pytest.approx(30.0)
    with pytest.raises(ValueError):
        c.incremental_analysis(pd.DataFrame({"name": ["x"], "cost": [1.0]}))


# --------------------------------------------------------------------------------------
# Break-even
# --------------------------------------------------------------------------------------
def test_breakeven_deaths_and_net_benefit():
    assert c.breakeven_deaths(1000.0, 50.0) == pytest.approx(20.0)
    with pytest.raises(ValueError):
        c.breakeven_deaths(1000.0, 0.0)
    with pytest.raises(c.MissingCostInputError):
        c.breakeven_deaths(1000.0, None)
    with pytest.raises(c.MissingCostInputError):
        c.net_benefit(1000.0, 10.0, None)  # no value of life is assumed
    assert c.net_benefit(1000.0, 10.0, 150.0) == pytest.approx(500.0)


def test_breakeven_parameter_generic_closed_form():
    b = toy_baseline()
    s = e.Scenario("g", e.GenericIntervention("speeding", relative_reduction_deaths=0.05))
    p = c.ProgrammeCosts(0.0, 1000.0, 5, 0.0)
    r = c.breakeven_parameter(s, b, "relative_reduction_deaths", p, 50.0)
    # need 1000 / 50 = 20 deaths of 200 -> 10%
    assert r["status"] == "solved" and r["value"] == pytest.approx(0.1)
    assert r["required_outcome"] == pytest.approx(20.0)
    assert r["interpretation"] == "minimum value required"
    assert r["kind"] == "hypothetical"
    r2 = c.breakeven_parameter(s, b, "relative_reduction_deaths", p, 1.0)
    assert r2["status"] == "not_achievable"


def test_breakeven_parameter_through_mechanism():
    b = toy_baseline()
    speed = e.SpeedEnforcement(
        0.0,
        50.0,
        e.LinearCappedCoverage(per_unit=0.01),
        behavioural_response=0.2,
        occurrence_effect=0.5,
        severity_effect=0.2,
    )
    s = e.Scenario("cams", speed)
    p = camera_costs().programme(50)
    thr = p.equivalent_annual_cost() / 3.0  # break-even needs 3 deaths/yr
    r = c.breakeven_parameter(s, b, "behavioural_response", p, thr)
    # deaths = 50 * (0.5 * resp) * (1 - 0.5*0.8) = 15 * resp -> resp = 0.2
    assert r["value"] == pytest.approx(0.2)
    check = e.evaluate(s, b, {"behavioural_response": r["value"]})["deaths_prevented"]
    assert check == pytest.approx(3.0)


def test_breakeven_parameter_over_horizon():
    b = toy_baseline()
    s = e.Scenario(
        "g",
        e.GenericIntervention("speeding", relative_reduction_deaths=0.05),
        e.Timing(2.0, 0.0),
    )
    p = c.ProgrammeCosts(0.0, 1000.0, 5, 0.0)
    with pytest.raises(c.MissingCostInputError):
        c.breakeven_parameter(s, b, "relative_reduction_deaths", p, 50.0, horizon_years=4)
    r = c.breakeven_parameter(
        s, b, "relative_reduction_deaths", p, 50.0, horizon_years=4, outcome_discount_rate=0.0
    )
    # PV costs 4000 -> need 80 deaths; deaths = 200 x (0.5 + 1 + 1 + 1) x rr = 700 rr
    assert r["value"] == pytest.approx(80 / 700)


def test_units_for_budget_and_equal_budget_indifference():
    cc = camera_costs()
    per_unit_eac = cc.programme(1).equivalent_annual_cost()
    u = c.units_for_budget(cc.programme, 10 * per_unit_eac, 1000)
    assert u["status"] == "solved" and u["units"] == pytest.approx(10.0)
    assert c.units_for_budget(cc.programme, 1e9, 5)["status"] == "budget not exhausted at max_units"
    rc = check_costs()
    low = c.units_for_budget(rc.programme, 1.0, 100)
    assert low["status"] == "budget below fixed costs"

    b = toy_baseline()

    def build_x(units: float) -> e.Scenario:
        return e.Scenario(
            "cams",
            e.SpeedEnforcement(
                0.0,
                units,
                e.SaturatingCoverage(rate=0.05),
                behavioural_response=0.3,
                occurrence_effect=0.2,
                severity_effect=0.2,
                target_segment="speeding",
            ),
        )

    def build_y(checks: float) -> e.Scenario:
        return e.Scenario(
            "rbt",
            e.ImpairedDrivingEnforcement(
                0.0,
                checks,
                e.SaturatingCoverage(rate=0.01),
                detection_probability=0.5,
                deterrence_elasticity=1.0,
                occurrence_effect=0.2,
                severity_effect=0.2,
            ),
        )

    res = c.equal_budget_indifference(
        200 * per_unit_eac,
        cc.programme,
        build_x,
        "behavioural_response",
        1000,
        rc.programme,
        build_y,
        "deterrence_elasticity",
        10_000,
        b,
        grid_x=[0.1, 0.2, 0.3],
        bounds_y=(0.0, 50.0),
    )
    assert res["units_x"]["units"] == pytest.approx(200.0)
    eac_y = rc.programme(res["units_y"]["units"]).equivalent_annual_cost()
    assert eac_y == pytest.approx(200 * per_unit_eac)
    curve = res["curve"]
    assert curve["status"].eq("solved").all()
    assert curve["y_indifference_value"].is_monotonic_increasing
    # at the indifference point both prevent the same number of deaths
    sx = build_x(res["units_x"]["units"])
    sy = build_y(res["units_y"]["units"])
    for _, row in curve.iterrows():
        dx = e.evaluate(sx, b, {"behavioural_response": row["x_value"]})["deaths_prevented"]
        dy = e.evaluate(sy, b, {"deterrence_elasticity": row["y_indifference_value"]})[
            "deaths_prevented"
        ]
        assert dx == pytest.approx(dy, rel=1e-6)


def test_indifference_curve_generic_closed_form():
    b = toy_baseline()
    x = e.Scenario("x", e.GenericIntervention("alcohol", relative_reduction_deaths=0.1))
    y = e.Scenario("y", e.GenericIntervention("speeding", relative_reduction_deaths=0.1))
    curve = c.indifference_curve(
        x, "relative_reduction_deaths", y, "relative_reduction_deaths", b, grid_x=[0.1, 0.5, 1.0]
    )
    assert curve["y_indifference_value"].iloc[0] == pytest.approx(0.1 * 210 / 200)
    assert curve["y_indifference_value"].iloc[1] == pytest.approx(0.5 * 210 / 200)
    # Y would need to prevent more than all its target deaths to match X at x = 1
    assert curve["status"].iloc[2] == "not_achievable"
    assert (curve["kind"] == "hypothetical").all()
