# RQ10 simulation engine and cost model -- summary

Module: `nhtsa_stats.simulation.engine` (`run()`), `nhtsa_stats.simulation.costs`.
Generated from the output tables in this directory; every number below is copied from them.

**What this is.** Tooling, not inference. The database contains no camera, enforcement,
checkpoint, roadside-testing, campaign or cost data (searched: 1712
source-table-column combinations in 67 source-tables of
`outputs/audit/column_inventory.csv`, label columns excluded; 53 enforcement/cost-like
column names matched, none of which measures an intervention or a cost --
`inventory_enforcement_cost_fields.csv`). So no intervention effect is estimated here. The
engine combines an **empirical baseline** (Layer A) with **user assumptions** (Layer C)
through explicit **mechanisms** (Layer B); every simulated output is labelled
`kind = "hypothetical"` and carries the assumptions used (Layer D). No default effect sizes
or prices exist anywhere in the code. Assumptions and worked hypothetical examples:
`docs/policy_assumptions.md`.

## 1. Layer A baseline (2022-2024, window means) -- `baseline.csv`, `baseline.json`

* FARS deaths: **41,000** per year (observed census); fatal crashes:
  **37,829** per year.
* CRSS police-reported crashes: 6,083,032 (95% CI 5,399,168-6,766,896) per year; KA crashes:
  193,817 (95% CI 176,628-211,006); CRSS-estimated fatal crashes 37,724 (95% CI 33,336-42,112)
  (compare FARS census 37,829).

| Year | FARS deaths | FARS fatal crashes |
|---|---|---|
| 2022 | 42,721 | 39,422 |
| 2023 | 41,025 | 37,769 |
| 2024 | 39,254 | 36,297 |

Target segments (deaths are observed FARS counts, mean per year; alcohol is the expected
value over the 10 BAC implicates; KA crashes are CRSS design-based estimates, 95% CI, 42 df):

| Segment | Reliability | Deaths/yr | Share of all deaths | Deaths/yr with unknown status (not counted) | CRSS KA crashes/yr | Share of segment deaths to prevent per 1% of all deaths |
|---|---|---|---|---|---|---|
| speeding | moderate | 11,786 | 28.7% | 3,310 | 34,277 (95% CI 29,285-39,269) | 3.5% |
| speeding_exceeded_limit | moderate | 4,702 | 11.5% | 5,574 | 8,460 (95% CI 6,666-10,253) | 8.7% |
| alcohol | moderate | 12,581 | 30.7% | none (BAC imputed) | 32,302 (95% CI 28,676-35,928) | 3.3% |
| drugs | low | 4,998 | 12.2% | 22,086 | 7,327 (95% CI 5,802-8,853) | 8.2% |
| unrestrained_lpv | moderate | 10,155 | 24.8% | 2,470 | n/a (persons) | 4.0% |

Segment definitions differ slightly between sources (FARS alcohol = driver MI-BAC >= .08;
CRSS alcohol = NHTSA-imputed police-reported involvement). Drug involvement is LOW
reliability (unknown for about half of fatal crashes, selective testing, presence is not
impairment). The unrestrained segment is restricted to the population of the within-vehicle
belt estimate (LPV occupants aged 13+, front or second row); deaths with unknown
restraint use are excluded, so the count is a lower bound.

Adjusted associations carried into Layer A (not causal; conditional on a crash):

| Quantity | Estimate (95% CI) | Source |
|---|---|---|
| severity.fatal_adj_rr.speeding | 1.821 (1.512-2.194) | outputs/tables/severity/fatal_crude_vs_adjusted.csv (A_adj_rr; {'factor': 'speeding', 'level': 'yes'}) |
| severity.fatal_adj_rr.alcohol | 4.244 (3.576-5.036) | outputs/tables/severity/fatal_crude_vs_adjusted.csv (A_adj_rr; {'factor': 'alcohol_im', 'level': 'yes'}) |
| severity.fatal_adj_rr.speeding_exceeded_limit | 5.216 (4.337-6.274) | outputs/tables/severity/fatal_speeding_type.csv (adj_rr; {'level': 'exceeded_limit_or_racing'}) |
| severity.ka_adj_rr.speeding | 1.562 (1.362-1.791) | outputs/tables/severity/ka_crude_vs_adjusted.csv (A_adj_rr; {'factor': 'speeding', 'level': 'yes'}) |
| severity.ka_adj_rr.alcohol | 2.740 (2.502-3.001) | outputs/tables/severity/ka_crude_vs_adjusted.csv (A_adj_rr; {'factor': 'alcohol_im', 'level': 'yes'}) |
| severity.ka_adj_rr.speeding_exceeded_limit | 3.390 (3.032-3.791) | outputs/tables/severity/ka_speeding_type.csv (adj_rr; {'level': 'exceeded_limit_or_racing'}) |
| belt.fatality_reduction | 0.658 (0.645-0.670) | outputs/tables/matched/belt_effect.csv (fatality_risk_reduction_belt_given_fatal_crash) |
| belt.fatality_reduction.misreport_f05 | 0.525 (0.510-0.538) | outputs/tables/matched/belt_effect.csv (fatality_risk_reduction_belt_given_fatal_crash_misreport_f05) |
| belt.fatality_reduction.misreport_f10 | 0.379 (0.362-0.394) | outputs/tables/matched/belt_effect.csv (fatality_risk_reduction_belt_given_fatal_crash_misreport_f10) |
| belt.fatality_reduction.misreport_f20 | 0.044 (0.020-0.064) | outputs/tables/matched/belt_effect.csv (fatality_risk_reduction_belt_given_fatal_crash_misreport_f20) |
| belt.fatality_reduction.complete_restraint_vehicles | 0.660 (0.647-0.673) | outputs/tables/matched/belt_effect.csv (fatality_risk_reduction_belt_given_fatal_crash_complete_restraint_vehicles) |

## 2. Overlap between segments (observed) -- `segment_overlap.csv`, `baseline_partitions.csv`

| Segments | Deaths/yr in both | Share of first also in second | Share of second also in first |
|---|---|---|---|
| speeding & alcohol | 4,912 | 41.7% | 39.0% |
| speeding & drugs | 1,865 | 15.8% | 37.3% |
| speeding & unrestrained_lpv | 3,862 | 32.8% | 38.0% |
| speeding_exceeded_limit & alcohol | 2,039 | 43.4% | 16.2% |
| speeding_exceeded_limit & drugs | 899 | 19.1% | 18.0% |
| speeding_exceeded_limit & unrestrained_lpv | 1,660 | 35.3% | 16.3% |
| alcohol & drugs | 2,118 | 16.8% | 42.4% |
| alcohol & unrestrained_lpv | 4,303 | 34.2% | 42.4% |
| drugs & unrestrained_lpv | 1,815 | 36.3% | 17.9% |

Combining interventions uses this cross-classification: within each cell, interventions
combine by multiplicative survival (default), so shared deaths are never counted twice;
the naive sum and the double counting it implies are reported by `engine.combine`.

## 3. Assumption-free threshold analysis (hypothetical arithmetic) -- `threshold_required_share.csv`

To reduce **all** road deaths by 1% (= 410 deaths/year) through a single segment,
the share of that segment's deaths that would have to be prevented is shown in the last column
of the table in section 1 (e.g. speeding-related 3.5%,
limit-exceeding speeding 8.7%,
alcohol BAC>=.08 3.3%).
Ten-percent reductions of all deaths would require preventing more than the whole segment
for: none.
`threshold_breakeven_grid.csv` gives the required share for any break-even requirement R
(= equivalent annual cost / cost-effectiveness threshold, both user-supplied).

### Conditional on the empirical estimates (still hypothetical) -- `threshold_conditional_on_empirical_estimates.csv`

If the Layer-A estimates were causal effects of the behaviour change (belt estimate given a
fatal crash; severity pathway only, `1 - 1/RR`, no crash-occurrence effect), the change needed
per 1% of all deaths would be:

| Segment | Empirical input | Input value | Required change |
|---|---|---|---|
| unrestrained_lpv | belt.fatality_reduction (estimate) | 0.658 | 6.1% |
| unrestrained_lpv | belt.fatality_reduction (ci_low) | 0.645 | 6.3% |
| unrestrained_lpv | belt.fatality_reduction (ci_high) | 0.670 | 6.0% |
| unrestrained_lpv | belt.fatality_reduction.misreport_f05 (estimate) | 0.525 | 7.7% |
| unrestrained_lpv | belt.fatality_reduction.misreport_f05 (ci_low) | 0.510 | 7.9% |
| unrestrained_lpv | belt.fatality_reduction.misreport_f05 (ci_high) | 0.538 | 7.5% |
| unrestrained_lpv | belt.fatality_reduction.misreport_f10 (estimate) | 0.379 | 10.7% |
| unrestrained_lpv | belt.fatality_reduction.misreport_f10 (ci_low) | 0.362 | 11.2% |
| unrestrained_lpv | belt.fatality_reduction.misreport_f10 (ci_high) | 0.394 | 10.3% |
| unrestrained_lpv | belt.fatality_reduction.misreport_f20 (estimate) | 0.044 | 92.6% |
| unrestrained_lpv | belt.fatality_reduction.misreport_f20 (ci_low) | 0.020 | 205.4% (not attainable: > 100%) |
| unrestrained_lpv | belt.fatality_reduction.misreport_f20 (ci_high) | 0.064 | 63.1% |
| unrestrained_lpv | belt.fatality_reduction.complete_restraint_vehicles (estimate) | 0.660 | 6.1% |
| unrestrained_lpv | belt.fatality_reduction.complete_restraint_vehicles (ci_low) | 0.647 | 6.2% |
| unrestrained_lpv | belt.fatality_reduction.complete_restraint_vehicles (ci_high) | 0.673 | 6.0% |
| speeding | severity.fatal_adj_rr.speeding (estimate) | 1.821 | 7.7% |
| speeding | severity.fatal_adj_rr.speeding (ci_low) | 1.512 | 10.3% |
| speeding | severity.fatal_adj_rr.speeding (ci_high) | 2.194 | 6.4% |
| speeding_exceeded_limit | severity.fatal_adj_rr.speeding_exceeded_limit (estimate) | 5.216 | 10.8% |
| speeding_exceeded_limit | severity.fatal_adj_rr.speeding_exceeded_limit (ci_low) | 4.337 | 11.3% |
| speeding_exceeded_limit | severity.fatal_adj_rr.speeding_exceeded_limit (ci_high) | 6.274 | 10.4% |
| alcohol | severity.fatal_adj_rr.alcohol (estimate) | 4.244 | 4.3% |
| alcohol | severity.fatal_adj_rr.alcohol (ci_low) | 3.576 | 4.5% |
| alcohol | severity.fatal_adj_rr.alcohol (ci_high) | 5.036 | 4.1% |

The belt rows show how strongly the answer depends on survivor misreporting of belt use
(matched module sensitivity rows): with 10-20% misreporting the required conversion rises
steeply. The speeding/alcohol rows ignore crash prevention (which would lower the requirement)
and treat a crash-conditional association as causal (which may overstate the severity effect).

## 4. Internal consistency checks (this run)

* FARS deaths partition (32 cells) sums to 41,000 deaths/yr = `fars.deaths_per_year` 41,000; fatal-crash partition sums to 37,829 = 37,829.
* CRSS KA partition sums to 193,817 = `crss.ka_crashes_per_year` 193,817.
* CRSS design-based estimate of fatal crashes 37,724 (95% CI 33,336-42,112) contains the FARS census count 37,829 (NHTSA-imputed severity is calibrated to FARS).
* FARS alcohol segment for 2022 (expected value over implicates): 13,458 deaths (`baseline_annual.csv`).

## 5. Engine capabilities (tested in `tests/test_simulation.py`, `tests/test_costs.py`)

* Mechanisms: `SpeedEnforcement` (units -> coverage -> response -> occurrence/severity),
  `ImpairedDrivingEnforcement` (checks -> coverage x detection -> deterrence elasticity),
  `RestraintEnforcement` (conversion x belt effectiveness, default from Layer A),
  `GenericIntervention`. Coverage: `LinearCappedCoverage`, `SaturatingCoverage`;
  `coverage_doubling_demo.csv` shows (dimensionless) that doubling units gives at most, and
  usually well under, double coverage.
* Outcomes: `evaluate`, `project` (ramp-up/decay), `combine` (overlap-aware), `tornado`,
  `corner_range`, `monte_carlo` (seed 20240601), `solve_scenario_parameter`.
* Costs: capital recovery factor, PV with renewals, equivalent annual cost, cost per death /
  KA prevented, incremental (marginal) cost-effectiveness with dominance, break-even deaths,
  break-even effectiveness parameter (solved through the engine), equal-budget indifference
  curves. All prices are required inputs; no value of a statistical life is assumed.

Worked examples with invented, clearly labelled inputs (cameras, alcohol checks, their
combination, costs in abstract currency units, break-even and equal-budget indifference, belt
enforcement) are in `docs/policy_assumptions.md` section 9; they are not results.

## 6. Limitations and alternative explanations

* Static baseline: projections hold the 2022-2024 mean fixed; secular trends (FARS deaths
  peaked in 2021, `descriptive/fars_annual.csv`) are not modelled.
* Segment counts rely on police coding; behaviours are ascertained more thoroughly in fatal
  crashes, and unknown-status deaths are excluded (lower bounds). Police may also attribute
  "speeding" after the fact in severe crashes, which would push the other way; the net bias of
  the segment counts is unknown.
* Segment shares are not "preventable fractions": a death in a speeding-related crash might
  have occurred without speeding, and deaths overlap across segments (section 2).
* The FARS alcohol segment is an expectation over NHTSA's imputation model.
* Adjusted RRs are associations conditional on a crash: their use as severity effects is an
  explicit, labelled assumption; they say nothing about crash occurrence.
* The belt estimate is conditional on a fatal crash and sensitive to misreporting.
* Monte Carlo reflects assumption uncertainty only (independent parameter draws).
* Nothing here identifies the effect of any intervention.
