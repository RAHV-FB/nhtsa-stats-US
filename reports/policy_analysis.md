<!-- Generated from reports/templates/policy_analysis.md by `nhtsa analyze report`; every number is looked up in outputs/tables. Edit the template, not this file. -->

# What the crash data can and cannot say about interventions

*Speed cameras, roadside alcohol and drug testing, belt enforcement and other measures.
Every number is read from `outputs/tables/` when this report is rendered. Estimate types:
**observed** (FARS census), **estimated** (CRSS design-based) and **adjusted association**
(model-based, conditional on a reported crash, not causal).*

## 1. The identification problem

The 36 archives describe crashes. They contain no record of where cameras stood, how many
roadside checks were held, how many drivers were tested or warned, what campaigns ran, or what
any of it cost. A search of all
1,712 source
columns for enforcement- or cost-like fields found nothing that measures an intervention
(`simulation/inventory_enforcement_cost_fields`).

So the data **cannot** estimate the effect of any intervention. What they can do is show where
deaths concentrate and how the target groups overlap (observed), and how strongly each targeted
circumstance is associated with a crash being fatal (adjusted association, not a causal effect).

## 2. Where deaths concentrate (observed)

Mean deaths per year, 2022–2024, in each target segment (FARS; all road deaths:
41,000 per year). Deaths whose status is
unknown are not counted, so segment counts are lower bounds. The alcohol segment (a driver at
BAC ≥ 0.08) is an expected value over NHTSA's 10 multiply-imputed BAC values, not a census count.

| Segment | Reliability | Deaths per year | Share of all road deaths | Deaths per year with unknown status (not counted) |
|---|---|---|---|---|
| Speeding-related | moderate | 11,786 | 28.7% | 3,310 |
| Exceeded the limit or racing | moderate | 4,702 | 11.5% | 5,574 |
| Alcohol (driver BAC ≥ 0.08) | moderate | 12,581 | 30.7% | none (BAC imputed) |
| Drugs (police-reported) | low | 4,998 | 12.2% | 22,086 |
| Unrestrained occupants of light vehicles | moderate | 10,155 | 24.8% | 2,470 |

**The drug segment is driven by missing data, not by drug involvement.** The counted segment
is a lower bound on drug-positive crashes and mostly reflects who was tested and recorded: the
22,086 deaths per year
in crashes of unknown drug status (not counted) far outnumber the
4,998 counted. Testing is
selective by injury severity and state (`reports/alcohol_drugs_restraints.md`), and the police
field used here and the toxicology-based count used elsewhere in the reports are different
definitions of drug involvement, so this row neither shows how many deaths drugs contribute nor
allows a comparison with the other segments.

The segments overlap heavily, so their deaths cannot be added:

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

For example, speeding-related and alcohol-involved crashes together account for
19,455 deaths a
year, not the sum of the two segments. Segment counts are not "preventable fractions": a death
in a speeding-related crash might have occurred without the speeding.

## 3. Associations with a fatal outcome (adjusted, not causal)

The two kinds of police-recorded speeding differ. Exceeding the limit has a large adjusted
association with a fatal outcome
(5.2 (4.3–6.3)). "Too fast for
conditions", the larger category, shows no detectable excess for a fatal outcome
(1.06 (0.89–1.26)) and a small one for
fatal-or-serious outcomes (1.18 (1.03–1.36)).
These are associations conditional on a police-reported crash; residual confounding and the
recording of behaviours after the crash can inflate them (finding 9 in `reports/findings.md`).
Alcohol involvement is strongly associated with a fatal outcome under every coding
(`reports/findings.md`, finding 4). Drug involvement cannot support even the association: drug
status is unknown for 53% of fatal crashes in CRSS, testing is selective by injury severity and
state, coding changed in 2019–2020, and a positive test shows presence, not impairment. Within
the same vehicle in fatal crashes, belted occupants were less likely to die than unbelted ones
(`reports/findings.md`, finding 7); that estimate is conditional on a fatal crash and sensitive to
survivor misreporting of belt use, and it says nothing about how many occupants enforcement
would convert. The contrasts for pedestrian lighting, speed limits and striking-vehicle type
compare places and vehicles as they are, not the effect of changing them.

## 4. The evidence ledger

*Source: `policy/evidence_ledger`.*

| Intervention | FARS deaths per year in target segment (2022–2024) | Adjusted fatal RR of the targeted circumstance | Strength of the target association |
|---|---|---|---|
| Automated speed enforcement (speed cameras) | 4,702 | all speeding-related: 1.82 (1.51-2.19); exceeded limit / racing: 5.22 (4.34-6.27); too fast for conditions: 1.06 (0.89-1.26) | strong for exceeding the limit (large association); none detected for 'too fast for conditions'; aggregate magnitude sensitive to ascertainment |
| Roadside alcohol testing / sobriety checkpoints | 12,581 | 4.24 (3.58-5.04) | strong in direction (large under every coding and robust to plausible differential ascertainment); magnitude coding-dependent |
| Roadside drug testing | 4,998 | NOT ESTIMATED: exposure measurement depends on severity and changed in 2019-2020; presence != impairment | insufficient |
| Seat-belt (restraint) enforcement | 10,155 | within-vehicle (FARS matched): fatality_rr_belted_vs_unbelted_given_fatal_crash: 0.34 (0.33-0.35) [evans_double_pair_comparison_driver_rf_pairs_crash_cluster_bootstrap]; fatality_risk_reduction_belt_given_fatal_crash: 0.66 (0.65-0.67) [evans_double_pair_comparison_driver_rf_pairs_crash_cluster_bootstrap]; fatality_rr_belted_vs_unbelted_given_fatal_crash_misreport_f05: 0.48 (0.46-0.49) [evans_double_pair_comparison_driver_rf_pairs_crash_cluster_bootstrap_closed_form_reclassification_f=0.05]; fatality_risk_reduction_belt_given_fatal_crash_misreport_f05: 0.52 (0.51-0.54) [evans_double_pair_comparison_driver_rf_pairs_crash_cluster_bootstrap_closed_form_reclassification_f=0.05]; fatality_rr_belted_vs_unbelted_given_fatal_crash_misreport_f10: 0.62 (0.61-0.64) [evans_double_pair_comparison_driver_rf_pairs_crash_cluster_bootstrap_closed_form_reclassification_f=0.10]; fatality_risk_reduction_belt_given_fatal_crash_misreport_f10: 0.38 (0.36-0.39) [evans_double_pair_comparison_driver_rf_pairs_crash_cluster_bootstrap_closed_form_reclassification_f=0.10]; fatality_rr_belted_vs_unbelted_given_fatal_crash_misreport_f20: 0.96 (0.94-0.98) [evans_double_pair_comparison_driver_rf_pairs_crash_cluster_bootstrap_closed_form_reclassification_f=0.20]; fatality_risk_reduction_belt_given_fatal_crash_misreport_f20: 0.04 (0.02-0.06) [evans_double_pair_comparison_driver_rf_pairs_crash_cluster_bootstrap_closed_form_reclassification_f=0.20]; within_vehicle_or_killed_unbelted_vs_belted: 5.07 (4.84-5.31) [conditional_logit_vehicle_strata_age_sex_seat_crash_robust_ci]; within_vehicle_or_killed_unbelted_vs_belted_misreport_f05: 3.14 (3.02-3.27) [conditional_logit_vehicle_strata_age_sex_seat_crash_robust_ci_seeded_nested_random_reclassification]; within_vehicle_or_killed_unbelted_vs_belted_misreport_f10: 2.25 (2.17-2.33) [conditional_logit_vehicle_strata_age_sex_seat_crash_robust_ci_seeded_nested_random_reclassification]; within_vehicle_or_killed_unbelted_vs_belted_misreport_f20: 1.31 (1.26-1.35) [conditional_logit_vehicle_strata_age_sex_seat_crash_robust_ci_seeded_nested_random_reclassification]; within_vehicle_or_killed_unbelted_vs_belted_complete_restraint_vehicles: 5.08 (4.84-5.32) [conditional_logit_vehicle_strata_age_sex_seat_crash_robust_ci_complete_restraint_vehicles]; fatality_rr_belted_vs_unbelted_given_fatal_crash_complete_restraint_vehicles: 0.34 (0.33-0.35) [evans_double_pair_comparison_vehicles_without_unknown_restraint_crash_cluster_bootstrap]; fatality_risk_reduction_belt_given_fatal_crash_complete_restraint_vehicles: 0.66 (0.65-0.67) [evans_double_pair_comparison_vehicles_without_unknown_restraint_crash_cluster_bootstrap]; matched_pair_or_killed_unbelted_vs_belted: 4.92 (4.63-5.22) [two_occupant_vehicles_one_death_conditional_ml_closed_form_poisson_ci]; matched_pair_or_killed_unbelted_vs_belted_misreport_f05: 2.81 (2.67-2.95) [two_occupant_vehicles_one_death_conditional_ml_closed_form_poisson_ci]; matched_pair_or_killed_unbelted_vs_belted_misreport_f10: 1.90 (1.82-1.99) [two_occupant_vehicles_one_death_conditional_ml_closed_form_poisson_ci]; matched_pair_or_killed_unbelted_vs_belted_misreport_f20: 1.08 (1.04-1.12) [two_occupant_vehicles_one_death_conditional_ml_closed_form_poisson_ci] | strong for protection given a fatal crash (matched design), with misreporting caveat |
| Combined speed and alcohol enforcement | — | see multifactor/margins (crash_exceeded_x_alcohol): the combination is super-additive and sub-multiplicative at crash level; multiplicative for single-vehicle drivers | overlap and super-additivity are estimated; programme effects are not |
| Targeted enforcement in high-risk periods (weekend nights) | 6,179 | time of day, all days (not weekend nights only), 00-05 vs 10-15: crude 3.97 (3.50-4.50); adjusted, light not held fixed 2.46 (2.15-2.82); adjusted, light held fixed 1.62 (1.46-1.79) | time is a marker of risk composition rather than an independent target |
| Education / awareness campaigns | — | — | — |
| Pedestrian safety: lighting, speed management, vehicle front-end design | 7,347 | see vulnerable module: speed-limit gradient, dark-unlit, SUV/pickup vs car | strong (large, objective measures, consistent across adjustment) |

The full ledger, with prevalence, robustness to measurement error, relevant interactions, who is
most affected, and what each intervention's effect would require, is in
`outputs/tables/policy/evidence_ledger.csv` and the interface.

## 5. What would be needed to estimate effects

Effect estimates would require data that are not in this repository: camera locations and
operating periods, check schedules and test counts, citation records, measured travel speeds
or traffic volumes, and programme costs, linked to crashes in time and place. With such data,
designs such as before–after comparisons with comparison sites or staggered roll-outs could
estimate effects; the severity associations here would then serve as plausibility checks.
