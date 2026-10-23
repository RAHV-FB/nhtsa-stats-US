"""Reproduce the worked HYPOTHETICAL examples in docs/policy_assumptions.md section 9.

Every input below is invented for illustration (abstract currency units, CU); none is an
estimate. The outputs depend on the saved Layer A baseline and on the severity tables, so they
change whenever ``nhtsa analyze severity matched policy`` is re-run.

    uv run python scripts/policy_worked_examples.py
"""

from __future__ import annotations

import pandas as pd

from nhtsa_stats.simulation import costs as c
from nhtsa_stats.simulation import engine as e
from nhtsa_stats.simulation.engine import Param

pd.set_option("display.width", 200)
SEG = "speeding_exceeded_limit"


def cameras(base: e.EmpiricalBaseline, units: int = 500, timing: bool = True) -> e.Scenario:
    return e.Scenario(
        "cameras",
        e.SpeedEnforcement(
            units_current=0,
            units_proposed=units,
            coverage=e.SaturatingCoverage(rate=Param(0.002, 0.001, 0.004)),
            behavioural_response=Param(0.3, 0.1, 0.5),
            occurrence_effect=Param(0.2, 0.0, 0.4),
            severity_effect=e.severity_effect_from_association(base, SEG),
            target_segment=SEG,
        ),
        e.Timing(ramp_years=Param(2, 1, 3), decay_per_year=Param(0.0, 0.0, 0.05))
        if timing
        else None,
    )


def checks(n: int = 20000) -> e.Scenario:
    return e.Scenario(
        "alcohol_checks",
        e.ImpairedDrivingEnforcement(
            checks_current=0,
            checks_proposed=n,
            coverage=e.SaturatingCoverage(rate=Param(5e-5, 2.5e-5, 1e-4)),
            detection_probability=Param(0.5, 0.3, 0.7),
            deterrence_elasticity=Param(1.0, 0.5, 2.0),
            occurrence_effect=Param(0.3, 0.1, 0.5),
            severity_effect=Param(0.3, 0.1, 0.5),
            target_segment="alcohol",
        ),
    )


def example_1(base: e.EmpiricalBaseline) -> e.Scenario:
    cams = cameras(base)
    r = e.evaluate(cams, base)
    sev = next(a for a in r["assumptions"] if a["parameter"] == "severity_effect")
    print("Example 1 - speed cameras")
    print(f"  target deaths/yr {r['baseline_target_deaths_per_year']:,.0f}")
    print(f"  chain {r['chain']}")
    print(f"  severity effect {sev['central']:.3f} ({sev['low']:.3f}-{sev['high']:.3f})")
    print(
        f"  central: {100 * r['relative_reduction_target_deaths']:.1f}% of target deaths, "
        f"{r['deaths_prevented']:,.0f} deaths/yr ({-r['pct_change_deaths']:.2f}% of all), "
        f"{r['fatal_crashes_prevented']:,.0f} fatal crashes/yr"
    )
    r2 = e.evaluate(cameras(base, 1000), base)
    print(
        f"  doubling to 1,000 units: coverage {r2['chain']['coverage_proposed']:.3f}, "
        f"{r2['deaths_prevented']:,.0f} deaths/yr (x{r2['deaths_prevented'] / r['deaths_prevented']:.2f})"
    )
    t = e.tornado(cams, base)
    cols = ["parameter", "deaths_prevented_at_low", "deaths_prevented_at_high", "swing"]
    print(t[cols].round(0).to_string(index=False))
    print(f"  corner range {e.corner_range(cams, base)['deaths_prevented']}")
    mc = e.monte_carlo(cams, base, n_draws=10000, horizon_years=5)
    print(mc.summary[["outcome", "mean", "p5", "p50", "p95"]].round(0).to_string(index=False))
    t5 = e.tornado(cams, base, horizon_years=5)
    print("  5-year cumulative, one-way:")
    cum = "cumulative_deaths_prevented_5y"
    print(t5[["parameter", f"{cum}_at_low", f"{cum}_at_high"]].round(0).to_string(index=False))
    return cams


def example_2(base: e.EmpiricalBaseline, cams: e.Scenario) -> e.Scenario:
    rbt = checks()
    ra = e.evaluate(rbt, base)
    print("Example 2 - alcohol checks and combination")
    print(f"  chain {ra['chain']}")
    print(
        f"  {ra['deaths_prevented']:,.0f} of {ra['baseline_target_deaths_per_year']:,.0f} "
        "alcohol deaths/yr"
    )
    comb = e.combine([cams, rbt], base)
    keys = (
        "deaths_prevented",
        "deaths_prevented_naive_sum",
        "double_counting_avoided",
        "deaths_in_all_target_segments_per_year",
    )
    print("  combine", {k: comb[k] for k in keys})
    print(f"  max rule {e.combine([cams, rbt], base, overlap='max')['deaths_prevented']:,.0f}")
    return rbt


def example_3(base: e.EmpiricalBaseline, cams: e.Scenario, rbt: e.Scenario) -> None:
    cc = c.SpeedCameraCosts(
        acquisition_per_unit=100,
        installation_per_unit=20,
        maintenance_per_unit_year=10,
        operations_per_unit_year=15,
        service_life_years=8,
        discount_rate=0.03,
    )
    prog = cc.programme(500)
    eac = prog.equivalent_annual_cost()
    print("Example 3 - costs and break-even (CU)")
    print(f"  {prog.summary(10)}")
    r = e.evaluate(cams, base)
    ce = c.cost_effectiveness(prog, r["deaths_prevented"])
    mc = e.monte_carlo(cams, base, n_draws=10000)
    ce_mc = c.cost_effectiveness(prog, mc.draws["deaths_prevented"].to_numpy())
    print(
        f"  cost per death prevented {ce['cost_per_death_prevented']} / MC {ce_mc['cost_per_death_prevented']}"
    )
    target = base.segment_deaths(SEG)
    rows = []
    for req in (100, 500, 1000, 2000, 3000):
        be = c.breakeven_parameter(cams, base, "behavioural_response", prog, eac / req)
        rows.append(
            {
                "R": req,
                "share_of_target": req / target,
                "status": be["status"],
                "min_behavioural_response": be["value"],
                "max_at_response_1": be["max_outcome_in_bounds"],
            }
        )
    print(pd.DataFrame(rows).round(4).to_string(index=False))
    be = c.breakeven_parameter(cams, base, "coverage.rate", prog, eac / 500, bounds=(0.0, 0.05))
    print(f"  minimum coverage rate for R=500: {be['value']}")

    rc = c.RoadsideCheckCosts(
        staff_hours_per_check=8,
        cost_per_staff_hour=1,
        tests_per_check=50,
        materials_per_test=0.1,
        confirmed_tests_per_check=1,
        lab_cost_per_confirmed_test=5,
        equipment_capital=1000,
        equipment_life_years=5,
        recurring_fixed_per_year=500,
        discount_rate=0.03,
    )

    def build_cams(u):
        m = cams.mechanism
        return e.Scenario(
            "cameras",
            e.SpeedEnforcement(
                0,
                u,
                m.coverage,
                behavioural_response=m.behavioural_response,
                occurrence_effect=m.occurrence_effect,
                severity_effect=m.severity_effect,
                target_segment=m.target_segment,
            ),
        )

    def build_rbt(n):
        m = rbt.mechanism
        return e.Scenario(
            "alcohol_checks",
            e.ImpairedDrivingEnforcement(
                0,
                n,
                m.coverage,
                detection_probability=m.detection_probability,
                deterrence_elasticity=m.deterrence_elasticity,
                occurrence_effect=m.occurrence_effect,
                severity_effect=m.severity_effect,
                target_segment="alcohol",
            ),
        )

    eb = c.equal_budget_indifference(
        eac,
        cc.programme,
        build_cams,
        "behavioural_response",
        10_000,
        rc.programme,
        build_rbt,
        "deterrence_elasticity",
        1e7,
        base,
        grid_x=[0.1, 0.2, 0.3, 0.4, 0.5],
        bounds_y=(0.0, 20.0),
    )
    print(f"  equal budget {eac:,.0f} CU/yr buys {eb['units_y']['units']:,.0f} checks/yr")
    print(
        eb["curve"][["x_value", "y_indifference_value", "status"]].round(2).to_string(index=False)
    )


def example_4(base: e.EmpiricalBaseline) -> None:
    belt = e.Scenario("belt", e.RestraintEnforcement(conversion_share=Param(0.1, 0.05, 0.2)))
    f10 = e.belt_effectiveness_param(base, "misreport_f10")
    belt_f10 = e.Scenario(
        "belt_f10", e.RestraintEnforcement(conversion_share=0.1, belt_effectiveness=f10)
    )
    print("Example 4 - belt enforcement")
    print(
        f"  {e.evaluate(belt, base)['deaths_prevented']:,.0f} deaths/yr; corner range "
        f"{e.corner_range(belt, base)['deaths_prevented']}"
    )
    print(
        f"  10% misreporting (belt effectiveness {f10.central:.3f}): "
        f"{e.evaluate(belt_f10, base)['deaths_prevented']:,.0f}"
    )


def main() -> None:
    base = e.EmpiricalBaseline.load()
    cams = example_1(base)
    rbt = example_2(base, cams)
    example_3(base, cams, rbt)
    example_4(base)


if __name__ == "__main__":
    main()
