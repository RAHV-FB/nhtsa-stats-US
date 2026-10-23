<!-- Generated from reports/templates/policy_analysis.md by `nhtsa analyze report`; every number is looked up in outputs/tables. Edit the template, not this file. -->

# What the crash data can and cannot say about interventions

*Speed cameras, roadside alcohol and drug testing, belt enforcement and other measures.
Every number is read from `outputs/tables/` when this report is rendered. Estimate types:
**observed** (FARS census), **estimated** (CRSS design-based), **adjusted association**
(model-based, conditional on a reported crash, not causal) and **hypothetical** (follows from
stated assumptions, not from data about the intervention).*

## 1. The identification problem

The 36 archives describe crashes. They contain no record of where cameras stood, how many
roadside checks were held, how many drivers were tested or warned, what campaigns ran, or what
any of it cost. A search of all
1,712 source
columns for enforcement- or cost-like fields found nothing that measures an intervention
(`simulation/inventory_enforcement_cost_fields`).

So the data **cannot** estimate the effect of any intervention. What they can do is:

1. show where deaths concentrate and how the target groups overlap (observed);
2. show how strongly each targeted circumstance is associated with a crash being fatal, and how
   much of that association survives measurement error (adjusted association);
3. say what an intervention **would have to achieve** to reach a given reduction
   (hypothetical, but needing no assumption about the intervention itself);
4. project outcomes **if** the user's assumptions about coverage, behaviour and effects hold
   (hypothetical; the policy simulator in the research interface).

## 2. The evidence ledger

*Source: `policy/evidence_ledger`.*

| Intervention | FARS deaths per year in target segment (2022–2024) | Adjusted fatal RR of the targeted circumstance | Strength of the target association | Can the data give a numeric effect? |
|---|---|---|---|---|
| Automated speed enforcement (speed cameras) | 4,702 | all speeding-related: 1.82 (1.51-2.19); exceeded limit / racing: 5.22 (4.34-6.27); too fast for conditions: 1.06 (0.89-1.26) | strong for exceeding the limit (large association); none detected for 'too fast for conditions'; aggregate magnitude sensitive to ascertainment | Only conditional/hypothetical (simulator + break-even). |
| Roadside alcohol testing / sobriety checkpoints | 12,581 | 4.24 (3.58-5.04) | strong in direction (large under every coding and robust to plausible differential ascertainment); magnitude coding-dependent | Only conditional/hypothetical. The direction of the target association is among the most robust in the data; its size depends on alcohol coding. |
| Roadside drug testing | 4,998 | NOT ESTIMATED: exposure measurement depends on severity and changed in 2019-2020; presence != impairment | insufficient | No defensible estimate from these data; simulator can only show what effect sizes would be required |
| Seat-belt (restraint) enforcement | 10,155 | within-vehicle (FARS matched): fatality_rr_belted_vs_unbelted_given_fatal_crash: 0.34 (0.33-0.35) [evans_double_pair_comparison_driver_rf_pairs_crash_cluster_bootstrap]; fatality_risk_reduction_belt_given_fatal_crash: 0.66 (0.65-0.67) [evans_double_pair_comparison_driver_rf_pairs_crash_cluster_bootstrap]; fatality_rr_belted_vs_unbelted_given_fatal_crash_misreport_f05: 0.48 (0.46-0.49) [evans_double_pair_comparison_driver_rf_pairs_crash_cluster_bootstrap_closed_form_reclassification_f=0.05]; fatality_risk_reduction_belt_given_fatal_crash_misreport_f05: 0.52 (0.51-0.54) [evans_double_pair_comparison_driver_rf_pairs_crash_cluster_bootstrap_closed_form_reclassification_f=0.05]; fatality_rr_belted_vs_unbelted_given_fatal_crash_misreport_f10: 0.62 (0.61-0.64) [evans_double_pair_comparison_driver_rf_pairs_crash_cluster_bootstrap_closed_form_reclassification_f=0.10]; fatality_risk_reduction_belt_given_fatal_crash_misreport_f10: 0.38 (0.36-0.39) [evans_double_pair_comparison_driver_rf_pairs_crash_cluster_bootstrap_closed_form_reclassification_f=0.10]; fatality_rr_belted_vs_unbelted_given_fatal_crash_misreport_f20: 0.96 (0.94-0.98) [evans_double_pair_comparison_driver_rf_pairs_crash_cluster_bootstrap_closed_form_reclassification_f=0.20]; fatality_risk_reduction_belt_given_fatal_crash_misreport_f20: 0.04 (0.02-0.06) [evans_double_pair_comparison_driver_rf_pairs_crash_cluster_bootstrap_closed_form_reclassification_f=0.20]; within_vehicle_or_killed_unbelted_vs_belted: 5.07 (4.84-5.31) [conditional_logit_vehicle_strata_age_sex_seat_crash_robust_ci]; within_vehicle_or_killed_unbelted_vs_belted_misreport_f05: 3.14 (3.02-3.27) [conditional_logit_vehicle_strata_age_sex_seat_crash_robust_ci_seeded_nested_random_reclassification]; within_vehicle_or_killed_unbelted_vs_belted_misreport_f10: 2.25 (2.17-2.33) [conditional_logit_vehicle_strata_age_sex_seat_crash_robust_ci_seeded_nested_random_reclassification]; within_vehicle_or_killed_unbelted_vs_belted_misreport_f20: 1.31 (1.26-1.35) [conditional_logit_vehicle_strata_age_sex_seat_crash_robust_ci_seeded_nested_random_reclassification]; within_vehicle_or_killed_unbelted_vs_belted_complete_restraint_vehicles: 5.08 (4.84-5.32) [conditional_logit_vehicle_strata_age_sex_seat_crash_robust_ci_complete_restraint_vehicles]; fatality_rr_belted_vs_unbelted_given_fatal_crash_complete_restraint_vehicles: 0.34 (0.33-0.35) [evans_double_pair_comparison_vehicles_without_unknown_restraint_crash_cluster_bootstrap]; fatality_risk_reduction_belt_given_fatal_crash_complete_restraint_vehicles: 0.66 (0.65-0.67) [evans_double_pair_comparison_vehicles_without_unknown_restraint_crash_cluster_bootstrap]; matched_pair_or_killed_unbelted_vs_belted: 4.92 (4.63-5.22) [two_occupant_vehicles_one_death_conditional_ml_closed_form_poisson_ci]; matched_pair_or_killed_unbelted_vs_belted_misreport_f05: 2.81 (2.67-2.95) [two_occupant_vehicles_one_death_conditional_ml_closed_form_poisson_ci]; matched_pair_or_killed_unbelted_vs_belted_misreport_f10: 1.90 (1.82-1.99) [two_occupant_vehicles_one_death_conditional_ml_closed_form_poisson_ci]; matched_pair_or_killed_unbelted_vs_belted_misreport_f20: 1.08 (1.04-1.12) [two_occupant_vehicles_one_death_conditional_ml_closed_form_poisson_ci] | strong for protection given a fatal crash (matched design), with misreporting caveat | Closest to defensible: protection given a crash is estimated within vehicles; behaviour change remains an assumption |
| Combined speed and alcohol enforcement | — | see multifactor/margins (crash_exceeded_x_alcohol): the combination is super-additive and sub-multiplicative at crash level; multiplicative for single-vehicle drivers | overlap and super-additivity are estimated; programme effects are not | Only conditional: segment deaths overlap, so effects of separate programmes cannot be added; the joint AF is smaller than the sum of single AFs |
| Targeted enforcement in high-risk periods (weekend nights) | 6,179 | time of day, all days (not weekend nights only), 00-05 vs 10-15: crude 3.97 (3.50-4.50); adjusted, light not held fixed 2.46 (2.15-2.82); adjusted, light held fixed 1.62 (1.46-1.79) | time is a marker of risk composition rather than an independent target | Only via the behaviour targeted (alcohol/speeding), conditional on assumptions |
| Education / awareness campaigns | — | — | — | No; data cannot distinguish campaign effects from any other change |
| Pedestrian safety: lighting, speed management, vehicle front-end design | 7,347 | see vulnerable module: speed-limit gradient, dark-unlit, SUV/pickup vs car | strong (large, objective measures, consistent across adjustment) | Conditional/hypothetical via the simulator's generic segment intervention |

The full ledger, with prevalence, robustness to measurement error, relevant interactions, who is
most affected, and the assumptions each projection needs, is in
`outputs/tables/policy/evidence_ledger.csv` and the interface.

## 3. Where deaths concentrate (observed)

Mean deaths per year, 2022–2024, in each target segment (FARS). Deaths whose status is unknown
are not counted, so segment counts are lower bounds. The alcohol segment (a driver at BAC ≥ 0.08)
is an expected value over NHTSA's 10 multiply-imputed BAC values, not a census count.

| Segment | Reliability | Deaths per year | Share of all road deaths |
|---|---|---|---|
| speeding | moderate | 11,786 | 28.7% |
| speeding_exceeded_limit | moderate | 4,702 | 11.5% |
| alcohol | moderate | 12,581 | 30.7% |
| drugs | low | 4,998 | 12.2% |
| unrestrained_lpv | moderate | 10,155 | 24.8% |

All road deaths: 41,000
per year. The segments overlap heavily, so their deaths cannot be added:

| Segment A | Segment B | Deaths per year in both | Share of A also in B | Share of B also in A |
|---|---|---|---|---|
| speeding | alcohol | 4,912 | 42% | 39% |
| speeding | drugs | 1,865 | 16% | 37% |
| speeding | unrestrained_lpv | 3,862 | 33% | 38% |
| speeding_exceeded_limit | alcohol | 2,039 | 43% | 16% |
| speeding_exceeded_limit | drugs | 899 | 19% | 18% |
| speeding_exceeded_limit | unrestrained_lpv | 1,660 | 35% | 16% |
| alcohol | drugs | 2,118 | 17% | 42% |
| alcohol | unrestrained_lpv | 4,303 | 34% | 42% |
| drugs | unrestrained_lpv | 1,815 | 36% | 18% |

A combined programme against speeding and alcohol therefore acts on
19,455 deaths a
year, not on the sum of the two segments. The simulator combines interventions within each cell
of this overlap, so shared deaths are counted once.

## 4. What an intervention would have to achieve (no effect assumptions)

To cut **all** road deaths by 1%, 5% or 10% through one segment alone, this share of the
segment's deaths would have to be prevented (hypothetical arithmetic on observed counts):

**1% of all deaths**

| Segment | Deaths to prevent per year | Share of segment deaths to prevent |
|---|---|---|
| speeding | 410 | 3.5% |
| speeding_exceeded_limit | 410 | 8.7% |
| alcohol | 410 | 3.3% |
| drugs | 410 | 8.2% |
| unrestrained_lpv | 410 | 4.0% |

**5% of all deaths**

| Segment | Deaths to prevent per year | Share of segment deaths to prevent |
|---|---|---|
| speeding | 2,050 | 17.4% |
| speeding_exceeded_limit | 2,050 | 43.6% |
| alcohol | 2,050 | 16.3% |
| drugs | 2,050 | 41.0% |
| unrestrained_lpv | 2,050 | 20.2% |

**10% of all deaths**

| Segment | Deaths to prevent per year | Share of segment deaths to prevent |
|---|---|---|
| speeding | 4,100 | 34.8% |
| speeding_exceeded_limit | 4,100 | 87.2% |
| alcohol | 4,100 | 32.6% |
| drugs | 4,100 | 82.0% |
| unrestrained_lpv | 4,100 | 40.4% |

Limit-exceeding speeding — the part of speeding that cameras act on — is a much smaller segment
than speeding as a whole, so a camera programme would have to prevent a far larger share of its
target deaths to reach the same national reduction.

## 5. If the measured associations were causal (still hypothetical)

Treating the adjusted associations as causal effects of removing the factor (severity pathway
only, no effect on whether crashes happen), the change required for a 1% reduction in all road
deaths would be:

| Segment | Empirical input | Value | Required change | Required value |
|---|---|---|---|---|
| unrestrained_lpv | belt.fatality_reduction | 0.658 | share of unbelted occupants (in fatal crashes) who must buckle up | 6.1% |
| unrestrained_lpv | belt.fatality_reduction.misreport_f05 | 0.525 | share of unbelted occupants (in fatal crashes) who must buckle up | 7.7% |
| unrestrained_lpv | belt.fatality_reduction.misreport_f10 | 0.379 | share of unbelted occupants (in fatal crashes) who must buckle up | 10.7% |
| unrestrained_lpv | belt.fatality_reduction.misreport_f20 | 0.044 | share of unbelted occupants (in fatal crashes) who must buckle up | 92.6% |
| unrestrained_lpv | belt.fatality_reduction.complete_restraint_vehicles | 0.660 | share of unbelted occupants (in fatal crashes) who must buckle up | 6.1% |
| speeding | severity.fatal_adj_rr.speeding | 1.821 | share of target-segment crashes whose factor must be removed (severity pathway only) | 7.7% |
| speeding_exceeded_limit | severity.fatal_adj_rr.speeding_exceeded_limit | 5.216 | share of target-segment crashes whose factor must be removed (severity pathway only) | 10.8% |
| alcohol | severity.fatal_adj_rr.alcohol | 4.244 | share of target-segment crashes whose factor must be removed (severity pathway only) | 4.3% |

Two cautions apply. First, these associations are conditional on a crash and are not causal;
residual confounding and the recording of behaviours after the crash can inflate them (finding
9 in `reports/findings.md`). Second, the belt rows depend strongly on how truthfully surviving
occupants report belt use. If 10% of "belted" survivors were in fact unbelted, the required
conversion rises to
10.7%
of unbelted occupants, against
6.1%
with no misreporting.

## 6. Interventions one by one

**Speed cameras.** The data separate two kinds of police-recorded speeding. Exceeding the limit
— what automated enforcement detects — has a large adjusted association with a fatal outcome
(5.2 (4.3–6.3)). "Too fast for
conditions", the larger category, shows no detectable excess for a fatal outcome
(1.06 (0.89–1.26)) and a small one for
fatal-or-serious outcomes (1.18 (1.03–1.36)). Any projection
of a camera programme should therefore target limit-exceeding crashes. How many cameras give
what coverage of speeding exposure, how much speeding falls where they operate, and how far the
effect spills over are not in the data; the simulator requires them as inputs. Doubling the
number of cameras does not double coverage: under a saturating coverage curve, doubling from
the point where one unit covers about 63% of the exposure adds only
1.37 times the
coverage (`simulation/coverage_doubling_demo`, a mathematical property of the curve, not data).

**Roadside alcohol testing.** Alcohol involvement is strongly associated with a fatal outcome
under every coding (`reports/findings.md`, finding 4), and FARS attributes
12,581
deaths a year to crashes with a driver at BAC ≥ 0.08 (expected value over NHTSA's imputations).
How many checks, how often impaired drivers are detected, and how strongly the perceived risk of
detection deters drinking and driving are not in the data.

**Roadside drug testing.** The data cannot support even the target association: drug status is
unknown for about half of fatal crashes, testing is selective by injury severity and state,
coding changed in 2019–2020, and a positive test shows presence, not impairment. The segment is
flagged LOW reliability, and the simulator can only show what effect sizes would be needed.

**Belt enforcement.** This is the closest the data come to an effect estimate. Within the same
vehicle in fatal crashes, belted occupants were less likely to die than unbelted ones
(`reports/findings.md`, finding 7). How many unbelted occupants enforcement would convert, and
whether converters resemble other unbelted occupants, are assumptions.

**Pedestrian lighting, speed management and vehicle design.** The contrasts between existing
conditions (lit vs unlit roads, speed limits, striking-vehicle type) are large and objectively
measured, but they compare places and vehicles as they are, not the effect of changing them.

## 7. Costs and break-even

No prices exist in the data, and none are assumed. Given user-supplied costs (investment,
operating cost, service life, discount rate), the cost tools compute the equivalent annual cost,
the cost per death or KA crash prevented under the user's effect assumptions, and three
break-even quantities:

* the minimum number of deaths a programme must prevent each year to meet a cost-effectiveness
  threshold the user sets;
* the minimum value of an effectiveness parameter (for example, the behavioural response to
  cameras) at which the programme meets that threshold, solved through the simulation engine;
* the effectiveness at which one intervention outperforms another for the same budget.

Worked examples with invented, clearly labelled inputs are in `docs/policy_assumptions.md`;
they are illustrations of the arithmetic, not results.

## 8. What would be needed to estimate effects

Effect estimates would require data that are not in this repository: camera locations and
operating periods, check schedules and test counts, citation records, measured travel speeds
or traffic volumes, and programme costs, linked to crashes in time and place. With such data,
designs such as before–after comparisons with comparison sites or staggered roll-outs could
estimate effects; the severity associations here would then serve as plausibility checks.
