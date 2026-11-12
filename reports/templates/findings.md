# What makes US road crashes deadly? Findings from FARS and CRSS, 2016–2024

*All empirical numbers in this report (apart from fixed survey-design constants) are read from
`outputs/tables/` when it is rendered
(`nhtsa analyze report`). Each finding names its source table. Estimate types: **observed**
(FARS census counts), **estimated** (CRSS design-based), **adjusted association**
(model-based, conditional on a police-reported crash, not causal), and **model-predicted**.*

## Summary

**What these data answer.** Within the same vehicle in the same fatal crash, how much less often
belted occupants and helmeted riders died (finding 7); which circumstances remain associated with a
reported crash being fatal after design-based adjustment in CRSS (findings 2–4); how police-recorded
fields behave (finding 9); and how the fatal share of reported crashes changed after 2020
(finding 8). **What they cannot answer:** crash rates per mile, trip or driver (there is no exposure
measure); the effect of any enforcement, camera, testing or campaign (none is recorded); the effect
of drugs; and any causal effect. Every severity result is conditional on a police-reported crash.
Intervals cover sampling error only, not recording error or model choice, unless stated.

1. **Belts and helmets, within the same vehicle (FARS).** Given a crash that killed someone in the
   vehicle, belted drivers and right-front passengers died
   {{matched/belt_effect|estimand=fatality_risk_reduction_belt_given_fatal_crash|estimate|cipct:1}} less often than their unbelted companion. The pooled figure
   averages very different crash types: from {{matched/belt_by_crash_type|partition=crash type|min(dpc_reduction)|pct:0}} in multi-vehicle angle crashes to {{matched/belt_by_crash_type|partition=crash type|max(dpc_reduction)|pct:0}}
   in single-vehicle rollovers. It rests on survivors' reports of belt use: with 10% of belted
   survivors truly unbelted and 5% of unbelted-coded deaths truly belted the reduction would be
   {{matched/belt_misreporting_two_sided_dpc|analysis=belt_driver_rf;survivor_misreport_f=0.1;death_misreport_g=0.05|reduction_1_minus_rr|cipct:0@reduction}}, and it would vanish at about
   {{matched/belt_misreporting_two_sided_dpc|analysis=belt_driver_rf;survivor_misreport_f=0;death_misreport_g=0|tipping_f_given_g|pct:0}}
   of belted survivors misrecorded. In an exploratory follow-up, belts are somewhat *less* protective within crash
   configuration when the driver was speeding (ratio of belt risk ratios {{restraint_behaviour/dpc_contrast_within_configuration|contrast=driver speeding (any) vs not speeding;layer=pooled within layers|min(ratio_of_rrs)|.2f}} to {{restraint_behaviour/dpc_contrast_within_configuration|contrast=driver speeding (any) vs not speeding;layer=pooled within layers|max(ratio_of_rrs)|.2f}} across four layering
   schemes), and the alcohol contrast is null (`reports/alcohol_drugs_restraints.md`).
   For motorcycle helmets (operator and passenger of the same motorcycle) the reduction is
   {{matched/double_pair_comparison|analysis=motorcycle_helmet;misreport_fraction=0;component=combined (inverse-variance weighted)|reduction_1_minus_rr|cipct:0@reduction}}
   but it is imprecise and fragile: it vanishes at about
   {{matched/helmet_misreporting_dpc|analysis=motorcycle_helmet;survivor_misreport_f=0;death_misreport_g=0|tipping_f_given_g|pct:0}}
   misreporting.
2. **Conditional associations in CRSS that survive adjustment.** Crashes in which a driver
   exceeded the limit or was racing had an adjusted fatal risk ratio of {{severity/speeding_type_models|outcome=fatal;model=A;level=exceeded_limit_or_racing|adj_rr|.2f}} ({{severity/speeding_type_models|outcome=fatal;model=A;level=exceeded_limit_or_racing|adj_rr_low95|.2f}}–{{severity/speeding_type_models|outcome=fatal;model=A;level=exceeded_limit_or_racing|adj_rr_high95|.2f}})
   (model A) and {{severity/speeding_type_models|outcome=fatal;model=B;level=exceeded_limit_or_racing|adj_rr|.2f}} ({{severity/speeding_type_models|outcome=fatal;model=B;level=exceeded_limit_or_racing|adj_rr_low95|.2f}}–{{severity/speeding_type_models|outcome=fatal;model=B;level=exceeded_limit_or_racing|adj_rr_high95|.2f}}) with crash configuration also held
   fixed; motorcycle involvement, {{severity/fatal_crude_vs_adjusted|factor=any_motorcycle;level=yes|A_adj_rr|ci:1}};
   alcohol, {{measurement/alcohol_coding_sensitivity|period=2016-2024;coding=police, unknown as no|adj_rr|ci:1}}
   to {{measurement/alcohol_coding_sensitivity|period=2016-2024;coding=police, complete case|adj_rr|ci:1}}
   depending on the coding; pedestrians struck on 50–55 mph roads against ≤25 mph,
   {{vulnerable/pedestrian_killed_contrasts|victim=pedestrian;outcome=killed;factor=str_speed_limit;level=50-55|adj_rr|ci:1}};
   and crashes involving a driver aged 65+, {{severity/fatal_crude_vs_adjusted|factor=older_driver;level=yes|A_adj_rr|ci:2}}.
   No direction reversed in the red-team stress tests (`docs/red_team_2026-11.md`).
3. **Measurement.** Killed drivers are tested for alcohol far more often than surviving drivers
   ({{measurement/alcohol_testing_share|driver_status=killed|share_alcohol_tested|pct:0}} against
   {{measurement/alcohol_testing_share|driver_status=survived|share_alcohol_tested|pct:0}},
   FARS 2016–2024), yet police-recorded alcohol, drug and distraction fields are *more* often
   unknown in fatal crashes (alcohol unknown in {{measurement/unknown_by_severity|kabco=4;field=alcohol|pct_unknown|.0f}}% of fatal
   and {{measurement/unknown_by_severity|kabco=0;field=alcohol|pct_unknown|.0f}}% of no-injury crashes in CRSS). CRSS alcohol
   coding broke in 2019, so the alcohol association is reported under three codings. Drug and
   distraction fields cannot support severity or trend analysis.
4. **The post-2020 rise.** The fatal share of police-reported crashes rose by a factor of
   {{trends/numerator_denominator|outcome=fatal;comparison=2020-2024 vs 2016-2019;quantity=ratio_fatal_share|estimate|ci:2}}.
   The recorded crash mix accounts for {{trends/composition_robustness|covariate_set=A;quantity=composition_share_of_change_ref_P0~composition_share_of_change_ref_P1|min(estimate)|pct:0}} to {{trends/composition_robustness|covariate_set=A;quantity=composition_share_of_change_ref_P0~composition_share_of_change_ref_P1|max(estimate)|pct:0}} of the rise without crash
   configuration (model A) and {{trends/composition_robustness|covariate_set=B;quantity=composition_share_of_change_ref_P0~composition_share_of_change_ref_P1|min(estimate)|pct:0}} to {{trends/composition_robustness|covariate_set=B;quantity=composition_share_of_change_ref_P0~composition_share_of_change_ref_P1|max(estimate)|pct:0}} with it (model B; configuration may itself be a mediator), across four covariate specifications and both
   reference periods; several of the individual intervals include zero. The rest is a higher fatal share within the
   same recorded circumstances. Separately, the fall in the number of reported crashes accounts for
   {{trends/denominator_share|outcome=fatal;comparison=2020-2024 vs 2016-2019;quantity=denominator_share_of_log_rise|estimate|cipct:0}} of the rise in the share ({{trends/denominator_share|outcome=fatal_cc;comparison=2020-2024 vs 2016-2019;quantity=denominator_share_of_log_rise|estimate|cipct:0}} under the complete-case outcome).
5. **How often a factor appears in fatal crashes is a poor guide to danger.** Pedestrian
   crashes are {{descriptive/frequency_vs_severity|factor=crash_type;level=pedestrian|share_all_crashes|pct:1}}
   of police-reported crashes but {{descriptive/frequency_vs_severity|factor=crash_type;level=pedestrian|share_fatal_fars|pct:1}}
   of fatal crashes. Rain, wet roads, intersections and crashes involving teenage drivers are
   common in crashes but *under*-represented among fatal ones.
6. **Adjustment changes the picture.** Much of the excess severity of night-time crashes is
   accounted for by other circumstances. Rain-crashes show no clear difference in fatal severity
   from clear-weather crashes on the same road surface (model A {{severity/key_contrasts_ab|factor=weather;level=rain;outcome=fatal;model=A|adj_rr|ci:2}},
   model B {{severity/key_contrasts_ab|factor=weather;level=rain;outcome=fatal;model=B|adj_rr|ci:2}}) and are somewhat less severe for fatal-or-serious
   outcomes ({{severity/key_contrasts_ab|factor=weather;level=rain;outcome=ka;model=A|adj_rr|ci:2}} and {{severity/key_contrasts_ab|factor=weather;level=rain;outcome=ka;model=B|adj_rr|ci:2}}).
   Interstates reverse from riskier to safer than comparable roads, but only on 50–65 mph roads
   ({{severity/interstate_by_speed_band|outcome=fatal;speed_limit_band=50-65 mph;quantity=RR interstate vs not|estimate|ci:2}}); at 70+ mph the ratio is {{severity/interstate_by_speed_band|outcome=fatal;speed_limit_band=70+ mph;quantity=RR interstate vs not|estimate|ci:2}}. The excess
   severity of crashes involving older drivers is *unmasked*.
7. **"Speeding" is two different things (the type split is exploratory).** Exceeding the limit is
   strongly associated with a fatal outcome (item 2). "Too fast for conditions", three-quarters of
   police-reported speeding-related crashes, has an adjusted fatal risk ratio of
   {{severity/speeding_type_models|outcome=fatal;model=A;level=too_fast_for_conditions|adj_rr|.2f}} ({{severity/speeding_type_models|outcome=fatal;model=A;level=too_fast_for_conditions|adj_rr_low95|.2f}}–{{severity/speeding_type_models|outcome=fatal;model=A;level=too_fast_for_conditions|adj_rr_high95|.2f}}) under model A (its 90% interval excludes only effects beyond about
   ±{{severity/speeding_type_models|outcome=fatal;model=A;level=too_fast_for_conditions|equivalence_bound_pct|.0f}}%), and
   {{severity/speeding_type_models|outcome=fatal;model=B;level=too_fast_for_conditions|adj_rr|.2f}} ({{severity/speeding_type_models|outcome=fatal;model=B;level=too_fast_for_conditions|adj_rr_low95|.2f}}–{{severity/speeding_type_models|outcome=fatal;model=B;level=too_fast_for_conditions|adj_rr_high95|.2f}}) under model B; for fatal-or-serious outcomes
   {{severity/speeding_type_models|outcome=ka;model=A;level=too_fast_for_conditions|adj_rr|.2f}} ({{severity/speeding_type_models|outcome=ka;model=A;level=too_fast_for_conditions|adj_rr_low95|.2f}}–{{severity/speeding_type_models|outcome=ka;model=A;level=too_fast_for_conditions|adj_rr_high95|.2f}}) and {{severity/speeding_type_models|outcome=ka;model=B;level=too_fast_for_conditions|adj_rr|.2f}} ({{severity/speeding_type_models|outcome=ka;model=B;level=too_fast_for_conditions|adj_rr_low95|.2f}}–{{severity/speeding_type_models|outcome=ka;model=B;level=too_fast_for_conditions|adj_rr_high95|.2f}}). The data
   support a small association; they do not support "no excess".
8. **Some combinations amplify each other**, notably pedestrian crashes in unlit darkness. For
   others that are often assumed to (speeding in darkness, young drivers late at night), no
   interaction is detected for the fatal outcome, although speeding in unlit darkness shows an
   additive excess for fatal-or-serious crashes.
9. **Crash involvement and crash severity are different problems.** In two-vehicle crashes,
   teenage drivers are over-represented as the culpable party, but crashes involving them are
   less severe (model A {{severity/key_contrasts_ab|factor=young_driver;level=yes;outcome=fatal;model=A|adj_rr|ci:2}}; model B, which adds crash
   configuration, {{severity/key_contrasts_ab|factor=young_driver;level=yes;outcome=fatal;model=B|adj_rr|ci:2}}). Drivers aged 75+ are also
   over-represented as the culpable party, and crashes involving a driver aged 65+ are more severe.
10. **The database identifies no intervention effect.** It can show where deaths concentrate,
    how strongly circumstances are associated with severity, and what an intervention would
    have to achieve. It cannot show what cameras, checkpoints or tests would achieve.

---

## 1. Data and approach

FARS records every fatal crash on US public roads:
{{descriptive/fars_annual|YEAR=2016|deaths|,.0f}} deaths in 2016,
{{descriptive/fars_annual|YEAR=2019|deaths|,.0f}} in 2019, a peak of
{{descriptive/fars_annual|YEAR=2021|deaths|,.0f}} in 2021, and
{{descriptive/fars_annual|YEAR=2024|deaths|,.0f}} in 2024. CRSS is a national probability sample
of police-reported crashes of every severity
({{descriptive/crss_annual||min(n_sample)|,.0f}}–{{descriptive/crss_annual||max(n_sample)|,.0f}}
sampled crashes per year, representing
{{descriptive/crss_annual||min(crashes)|,.0f}}–{{descriptive/crss_annual||max(crashes)|,.0f}}
crashes). Severity rates and models use CRSS with design-based
inference: 25 strata, 67 PSUs, 42 degrees of freedom. Counts of deaths use FARS. Rows from the
two systems are never pooled. Methods: `docs/methodology.md`. Variable definitions and coding
breaks: `docs/variable_harmonization.md`.

The share of police-reported crashes that were fatal was
{{descriptive/crss_annual|YEAR=2019|fatal_share|cipct:2}} in 2019 and
{{descriptive/crss_annual|YEAR=2021|fatal_share|cipct:2}} in 2021 (estimated).

## 2. Finding 1 — Frequency is not danger

*Source: `descriptive/frequency_vs_severity`; figure `outputs/figures/figures/overrepresentation.png`.*

For each characteristic we compare its share of all police-reported crashes (CRSS, weighted)
with its share of fatal crashes (FARS, census). The ratio is the **over-representation ratio**.
A ratio near 1 means the characteristic is common in fatal crashes *because it is common in
crashes*.

| Characteristic | Share of all crashes | Share of fatal crashes | Over-representation (95% CI) | Crude fatal rate |
|---|---|---|---|---|
| Pedestrian crash | {{descriptive/frequency_vs_severity|factor=crash_type;level=pedestrian|share_all_crashes|pct:1}} | {{descriptive/frequency_vs_severity|factor=crash_type;level=pedestrian|share_fatal_fars|pct:1}} | ×{{descriptive/frequency_vs_severity|factor=crash_type;level=pedestrian|overrep_ratio|.1f}} ({{descriptive/frequency_vs_severity|factor=crash_type;level=pedestrian|overrep_low|.1f}}–{{descriptive/frequency_vs_severity|factor=crash_type;level=pedestrian|overrep_high|.1f}}) | {{descriptive/frequency_vs_severity|factor=crash_type;level=pedestrian|fatal_rate|pct:1}} |
| Driver exceeded the limit / racing | {{descriptive/frequency_vs_severity|factor=speeding_type;level=exceeded_limit_or_racing|share_all_crashes|pct:2}} | {{descriptive/frequency_vs_severity|factor=speeding_type;level=exceeded_limit_or_racing|share_fatal_fars|pct:1}} | ×{{descriptive/frequency_vs_severity|factor=speeding_type;level=exceeded_limit_or_racing|overrep_ratio|.1f}} | {{descriptive/frequency_vs_severity|factor=speeding_type;level=exceeded_limit_or_racing|fatal_rate|pct:1}} |
| Motorcycle involved | {{descriptive/frequency_vs_severity|factor=any_motorcycle;level=yes|share_all_crashes|pct:1}} | {{descriptive/frequency_vs_severity|factor=any_motorcycle;level=yes|share_fatal_fars|pct:1}} | ×{{descriptive/frequency_vs_severity|factor=any_motorcycle;level=yes|overrep_ratio|.1f}} | {{descriptive/frequency_vs_severity|factor=any_motorcycle;level=yes|fatal_rate|pct:1}} |
| Single vehicle, rollover first | {{descriptive/frequency_vs_severity|factor=crash_type;level=sv_rollover_first|share_all_crashes|pct:1}} | {{descriptive/frequency_vs_severity|factor=crash_type;level=sv_rollover_first|share_fatal_fars|pct:1}} | ×{{descriptive/frequency_vs_severity|factor=crash_type;level=sv_rollover_first|overrep_ratio|.1f}} | {{descriptive/frequency_vs_severity|factor=crash_type;level=sv_rollover_first|fatal_rate|pct:1}} |
| Head-on collision | {{descriptive/frequency_vs_severity|factor=crash_type;level=mv_head_on|share_all_crashes|pct:1}} | {{descriptive/frequency_vs_severity|factor=crash_type;level=mv_head_on|share_fatal_fars|pct:1}} | ×{{descriptive/frequency_vs_severity|factor=crash_type;level=mv_head_on|overrep_ratio|.1f}} | {{descriptive/frequency_vs_severity|factor=crash_type;level=mv_head_on|fatal_rate|pct:1}} |
| Dark, unlit | {{descriptive/frequency_vs_severity|factor=light;level=dark_not_lighted|share_all_crashes|pct:1}} | {{descriptive/frequency_vs_severity|factor=light;level=dark_not_lighted|share_fatal_fars|pct:1}} | ×{{descriptive/frequency_vs_severity|factor=light;level=dark_not_lighted|overrep_ratio|.1f}} | {{descriptive/frequency_vs_severity|factor=light;level=dark_not_lighted|fatal_rate|pct:2}} |
| 00:00–05:59 | {{descriptive/frequency_vs_severity|factor=tod;level=00-05|share_all_crashes|pct:1}} | {{descriptive/frequency_vs_severity|factor=tod;level=00-05|share_fatal_fars|pct:1}} | ×{{descriptive/frequency_vs_severity|factor=tod;level=00-05|overrep_ratio|.1f}} | {{descriptive/frequency_vs_severity|factor=tod;level=00-05|fatal_rate|pct:2}} |
| Speed limit 50–55 mph | {{descriptive/frequency_vs_severity|factor=speed_limit;level=50-55|share_all_crashes|pct:1}} | {{descriptive/frequency_vs_severity|factor=speed_limit;level=50-55|share_fatal_fars|pct:1}} | ×{{descriptive/frequency_vs_severity|factor=speed_limit;level=50-55|overrep_ratio|.1f}} | {{descriptive/frequency_vs_severity|factor=speed_limit;level=50-55|fatal_rate|pct:2}} |
| Speed limit 70+ mph | {{descriptive/frequency_vs_severity|factor=speed_limit;level=70+|share_all_crashes|pct:1}} | {{descriptive/frequency_vs_severity|factor=speed_limit;level=70+|share_fatal_fars|pct:1}} | ×{{descriptive/frequency_vs_severity|factor=speed_limit;level=70+|overrep_ratio|.1f}} | {{descriptive/frequency_vs_severity|factor=speed_limit;level=70+|fatal_rate|pct:2}} |
| "Too fast for conditions" | {{descriptive/frequency_vs_severity|factor=speeding_type;level=too_fast_for_conditions|share_all_crashes|pct:1}} | {{descriptive/frequency_vs_severity|factor=speeding_type;level=too_fast_for_conditions|share_fatal_fars|pct:1}} | ×{{descriptive/frequency_vs_severity|factor=speeding_type;level=too_fast_for_conditions|overrep_ratio|.1f}} | {{descriptive/frequency_vs_severity|factor=speeding_type;level=too_fast_for_conditions|fatal_rate|pct:2}} |
| Driver aged 65+ involved | {{descriptive/frequency_vs_severity|factor=older_driver;level=yes|share_all_crashes|pct:1}} | {{descriptive/frequency_vs_severity|factor=older_driver;level=yes|share_fatal_fars|pct:1}} | ×{{descriptive/frequency_vs_severity|factor=older_driver;level=yes|overrep_ratio|.1f}} | {{descriptive/frequency_vs_severity|factor=older_driver;level=yes|fatal_rate|pct:2}} |
| Wet surface | {{descriptive/frequency_vs_severity|factor=surface;level=wet|share_all_crashes|pct:1}} | {{descriptive/frequency_vs_severity|factor=surface;level=wet|share_fatal_fars|pct:1}} | ×{{descriptive/frequency_vs_severity|factor=surface;level=wet|overrep_ratio|.2f}} | {{descriptive/frequency_vs_severity|factor=surface;level=wet|fatal_rate|pct:2}} |
| Rain | {{descriptive/frequency_vs_severity|factor=weather;level=rain|share_all_crashes|pct:1}} | {{descriptive/frequency_vs_severity|factor=weather;level=rain|share_fatal_fars|pct:1}} | ×{{descriptive/frequency_vs_severity|factor=weather;level=rain|overrep_ratio|.2f}} | {{descriptive/frequency_vs_severity|factor=weather;level=rain|fatal_rate|pct:2}} |
| Intersection | {{descriptive/frequency_vs_severity|factor=junction;level=intersection|share_all_crashes|pct:1}} | {{descriptive/frequency_vs_severity|factor=junction;level=intersection|share_fatal_fars|pct:1}} | ×{{descriptive/frequency_vs_severity|factor=junction;level=intersection|overrep_ratio|.2f}} | {{descriptive/frequency_vs_severity|factor=junction;level=intersection|fatal_rate|pct:2}} |
| Driver aged 15–20 involved | {{descriptive/frequency_vs_severity|factor=young_driver;level=yes|share_all_crashes|pct:1}} | {{descriptive/frequency_vs_severity|factor=young_driver;level=yes|share_fatal_fars|pct:1}} | ×{{descriptive/frequency_vs_severity|factor=young_driver;level=yes|overrep_ratio|.2f}} | {{descriptive/frequency_vs_severity|factor=young_driver;level=yes|fatal_rate|pct:2}} |
| Rear-end collision | {{descriptive/frequency_vs_severity|factor=crash_type;level=mv_rear_end|share_all_crashes|pct:1}} | {{descriptive/frequency_vs_severity|factor=crash_type;level=mv_rear_end|share_fatal_fars|pct:1}} | ×{{descriptive/frequency_vs_severity|factor=crash_type;level=mv_rear_end|overrep_ratio|.2f}} | {{descriptive/frequency_vs_severity|factor=crash_type;level=mv_rear_end|fatal_rate|pct:2}} |

*Mixed systems.* Each ratio above divides a FARS share by a CRSS share, so it mixes two recording
systems, and its interval reflects CRSS sampling of the denominator only (FARS is a census; recording
differences between the systems are not in any interval). Police record speeding in fewer CRSS than FARS
fatal crashes, which inflates the mixed ratio for speeding. Within CRSS alone (`speeding/crss_overrepresentation`)
the over-representation of limit exceedance among fatal crashes is
{{speeding/crss_overrepresentation|speeding=exceeded_limit_or_racing|crss_only_ratio|ci:1}},
against {{speeding/crss_overrepresentation|speeding=exceeded_limit_or_racing|mixed_fars_crss_ratio|ci:1@mixed_ratio}}
for the mixed FARS/CRSS ratio; for any police-reported speeding the figures are
{{speeding/crss_overrepresentation|speeding=any_speeding|crss_only_ratio|ci:1}} and
{{speeding/crss_overrepresentation|speeding=any_speeding|mixed_fars_crss_ratio|ci:1@mixed_ratio}}.
The within-CRSS ratio is the lower figure because CRSS under-records speeding in fatal crashes; both
are reported and the truth lies between them only if CRSS under-recording is the whole difference.

*Robustness.* Pooled over 2016–2024, the CRSS-weighted composition of fatal crashes agrees
with the FARS census within the CRSS confidence interval for darkness
({{measurement/fars_crss_fatal_composition|YEAR=all;attribute=dark|crss_share|cipct:1@crss}} vs {{measurement/fars_crss_fatal_composition|YEAR=all;attribute=dark|fars_share|pct:1}}), pedestrian
involvement ({{measurement/fars_crss_fatal_composition|YEAR=all;attribute=any_pedestrian|crss_share|cipct:1@crss}} vs {{measurement/fars_crss_fatal_composition|YEAR=all;attribute=any_pedestrian|fars_share|pct:1}})
and single-vehicle crashes (`measurement/fars_crss_fatal_composition`), which supports
combining CRSS denominators with FARS numerators for these. It does not agree for motorcycle
involvement ({{measurement/fars_crss_fatal_composition|YEAR=all;attribute=any_motorcycle|crss_share|cipct:1@crss}} vs {{measurement/fars_crss_fatal_composition|YEAR=all;attribute=any_motorcycle|fars_share|pct:1}}),
so ratios that mix the two systems are less certain for motorcycle crashes, nor for young drivers
({{measurement/fars_crss_fatal_composition|YEAR=all;attribute=young_driver|crss_share|cipct:1@crss}} vs {{measurement/fars_crss_fatal_composition|YEAR=all;attribute=young_driver|fars_share|pct:1}}), largely
because CRSS uses NHTSA's imputed driver age and FARS the reported age, under which drivers of
unknown age are not counted as young. Police-recorded speeding is much rarer among CRSS fatal
crashes than in FARS ({{measurement/fars_crss_fatal_composition|YEAR=all;attribute=speeding|crss_share|pct:1}} vs {{measurement/fars_crss_fatal_composition|YEAR=all;attribute=speeding|fars_share|pct:1}}),
a measurement problem discussed under finding 3. *Limitation.* Ratios are descriptive; they do
not adjust for other circumstances (finding 2).

## 3. Finding 2 — Adjustment reshapes which circumstances look dangerous

*Source: `severity/fatal_crude_vs_adjusted`; figure `outputs/figures/figures/forest_fatal_crude_vs_adjusted.png`.
Method: survey-weighted logistic models; standardised risk ratios (g-computation). Model A
adjusts for all pre-crash circumstances at once (mutually adjusted), so for a factor with
downstream variables in the dependency diagram — time of day → light, weather → road surface,
driver and vehicle mix → police-reported behaviours — model A also holds those fixed; the
association without them is reported alongside. Model B adds crash configuration, a possible
mediator.*

| Circumstance (vs reference) | Crude RR | Adjusted RR, model A | Adjusted RR, model B |
|---|---|---|---|
| 00:00–05:59 (vs 10:00–15:59) | {{severity/fatal_crude_vs_adjusted|factor=tod;level=00-05|crude_rr|ci:2}} | {{severity/fatal_crude_vs_adjusted|factor=tod;level=00-05|A_adj_rr|ci:2}} | {{severity/fatal_crude_vs_adjusted|factor=tod;level=00-05|B_adj_rr|ci:2}} |
| Weekend | {{severity/fatal_crude_vs_adjusted|factor=weekend;level=yes|crude_rr|ci:2}} | {{severity/fatal_crude_vs_adjusted|factor=weekend;level=yes|A_adj_rr|ci:2}} | {{severity/fatal_crude_vs_adjusted|factor=weekend;level=yes|B_adj_rr|ci:2}} |
| Dark, unlit (vs daylight) | {{severity/fatal_crude_vs_adjusted|factor=light;level=dark_not_lighted|crude_rr|ci:2}} | {{severity/fatal_crude_vs_adjusted|factor=light;level=dark_not_lighted|A_adj_rr|ci:2}} | {{severity/fatal_crude_vs_adjusted|factor=light;level=dark_not_lighted|B_adj_rr|ci:2}} |
| Rain (vs clear) | {{severity/fatal_crude_vs_adjusted|factor=weather;level=rain|crude_rr|ci:2}} | {{severity/fatal_crude_vs_adjusted|factor=weather;level=rain|A_adj_rr|ci:2}} | {{severity/fatal_crude_vs_adjusted|factor=weather;level=rain|B_adj_rr|ci:2}} |
| Wet surface (vs dry) | {{severity/fatal_crude_vs_adjusted|factor=surface;level=wet|crude_rr|ci:2}} | {{severity/fatal_crude_vs_adjusted|factor=surface;level=wet|A_adj_rr|ci:2}} | {{severity/fatal_crude_vs_adjusted|factor=surface;level=wet|B_adj_rr|ci:2}} |
| Snow / ice surface | {{severity/fatal_crude_vs_adjusted|factor=surface;level=snow_ice|crude_rr|ci:2}} | {{severity/fatal_crude_vs_adjusted|factor=surface;level=snow_ice|A_adj_rr|ci:2}} | {{severity/fatal_crude_vs_adjusted|factor=surface;level=snow_ice|B_adj_rr|ci:2}} |
| Interstate | {{severity/fatal_crude_vs_adjusted|factor=interstate;level=yes|crude_rr|ci:2}} | {{severity/fatal_crude_vs_adjusted|factor=interstate;level=yes|A_adj_rr|ci:2}} | {{severity/fatal_crude_vs_adjusted|factor=interstate;level=yes|B_adj_rr|ci:2}} |
| Speed limit 50–55 (vs 30–35) | {{severity/fatal_crude_vs_adjusted|factor=speed_limit;level=50-55|crude_rr|ci:2}} | {{severity/fatal_crude_vs_adjusted|factor=speed_limit;level=50-55|A_adj_rr|ci:2}} | {{severity/fatal_crude_vs_adjusted|factor=speed_limit;level=50-55|B_adj_rr|ci:2}} |
| Speed limit 70+ | {{severity/fatal_crude_vs_adjusted|factor=speed_limit;level=70+|crude_rr|ci:2}} | {{severity/fatal_crude_vs_adjusted|factor=speed_limit;level=70+|A_adj_rr|ci:2}} | {{severity/fatal_crude_vs_adjusted|factor=speed_limit;level=70+|B_adj_rr|ci:2}} |
| Rural area (CRSS PSU) | {{severity/fatal_crude_vs_adjusted|factor=urbanicity;level=rural|crude_rr|ci:2}} | {{severity/fatal_crude_vs_adjusted|factor=urbanicity;level=rural|A_adj_rr|ci:2}} | {{severity/fatal_crude_vs_adjusted|factor=urbanicity;level=rural|B_adj_rr|ci:2}} |
| Intersection (vs non-junction) | {{severity/fatal_crude_vs_adjusted|factor=junction;level=intersection|crude_rr|ci:2}} | {{severity/fatal_crude_vs_adjusted|factor=junction;level=intersection|A_adj_rr|ci:2}} | {{severity/fatal_crude_vs_adjusted|factor=junction;level=intersection|B_adj_rr|ci:2}} |
| Driver 15–20 involved | {{severity/fatal_crude_vs_adjusted|factor=young_driver;level=yes|crude_rr|ci:2}} | {{severity/fatal_crude_vs_adjusted|factor=young_driver;level=yes|A_adj_rr|ci:2}} | {{severity/fatal_crude_vs_adjusted|factor=young_driver;level=yes|B_adj_rr|ci:2}} |
| Driver 65+ involved | {{severity/fatal_crude_vs_adjusted|factor=older_driver;level=yes|crude_rr|ci:2}} | {{severity/fatal_crude_vs_adjusted|factor=older_driver;level=yes|A_adj_rr|ci:2}} | {{severity/fatal_crude_vs_adjusted|factor=older_driver;level=yes|B_adj_rr|ci:2}} |
| Heavy truck / bus involved | {{severity/fatal_crude_vs_adjusted|factor=any_heavy_truck;level=yes|crude_rr|ci:2}} | {{severity/fatal_crude_vs_adjusted|factor=any_heavy_truck;level=yes|A_adj_rr|ci:2}} | {{severity/fatal_crude_vs_adjusted|factor=any_heavy_truck;level=yes|B_adj_rr|ci:2}} |
| Motorcycle involved | {{severity/fatal_crude_vs_adjusted|factor=any_motorcycle;level=yes|crude_rr|ci:2}} | {{severity/fatal_crude_vs_adjusted|factor=any_motorcycle;level=yes|A_adj_rr|ci:2}} | {{severity/fatal_crude_vs_adjusted|factor=any_motorcycle;level=yes|B_adj_rr|ci:2}} |
| Speeding-related (any type) | {{severity/fatal_crude_vs_adjusted|factor=speeding;level=yes|crude_rr|ci:2}} | {{severity/fatal_crude_vs_adjusted|factor=speeding;level=yes|A_adj_rr|ci:2}} | {{severity/fatal_crude_vs_adjusted|factor=speeding;level=yes|B_adj_rr|ci:2}} |
| Alcohol involved (imputed) | {{severity/fatal_crude_vs_adjusted|factor=alcohol_im;level=yes|crude_rr|ci:2}} | {{severity/fatal_crude_vs_adjusted|factor=alcohol_im;level=yes|A_adj_rr|ci:2}} | {{severity/fatal_crude_vs_adjusted|factor=alcohol_im;level=yes|B_adj_rr|ci:2}} |

What changes, and why it matters:

* **Night.** For 00:00–05:59 against 10:00–15:59 the crude risk ratio is
  {{severity/fatal_crude_vs_adjusted|factor=tod;level=00-05|crude_rr|ci:2}}. Adjusted for the
  other pre-crash circumstances but not for light, it is
  {{severity/fatal_crude_vs_adjusted|factor=tod;level=00-05|Ax_adj_rr|ci:2}}; holding light fixed
  as well, {{severity/fatal_crude_vs_adjusted|factor=tod;level=00-05|A_adj_rr|ci:2}}. Darkness is
  part of what night means, so the second figure removes part of the night effect itself. The
  night-time hazard is largely the hazard of *what happens at night*: darkness, alcohol,
  higher-speed roads and different crash types. A residual association remains.
  *How much each circumstance accounts for* (`confounding/sequential_fatal`,
  `confounding/shapley_fatal`; adjusted association). Defining night as 21:00–05:59 against
  06:00–20:59, the crude risk ratio is {{confounding/sequential_fatal|exposure=night;ordering=primary;step=0|rr|ci:2}}. Adjusting for eight blocks of
  circumstances at once leaves {{confounding/sequential_fatal|exposure=night;ordering=primary;step=8|rr|ci:2}}, which retains
  {{confounding/sequential_fatal|exposure=night;ordering=primary;step=8|share_logrr_retained|cipct:0@share_retained}} of the crude log risk ratio.
  Averaged over every order in which the blocks can be added (Shapley shares), light condition
  accounts for {{confounding/shapley_fatal|exposure=night;variant=all_blocks;block=light|shapley_share_of_crude|cipct:0@share}} of the crude log risk ratio, alcohol for {{confounding/shapley_fatal|exposure=night;variant=all_blocks;block=alcohol|shapley_share_of_crude|cipct:0@share}}, crash
  configuration for {{confounding/shapley_fatal|exposure=night;variant=all_blocks;block=configuration|shapley_share_of_crude|cipct:0@share}} and the road environment for {{confounding/shapley_fatal|exposure=night;variant=all_blocks;block=road_environment|shapley_share_of_crude|cipct:0@share}}.
  The share credited to light depends strongly on the order: from
  {{confounding/shapley_fatal|exposure=night;variant=all_blocks;block=light|min_share_any_order|pct:0}} to {{confounding/shapley_fatal|exposure=night;variant=all_blocks;block=light|max_share_any_order|pct:0}}
  across orders, because light and night are nearly the same thing: at night,
  {{confounding/night_light_overlap|period=night;light=dark_lighted|weighted_share_of_period|pct:0}}
  of crashes were in lit and
  {{confounding/night_light_overlap|period=night;light=dark_not_lighted|weighted_share_of_period|pct:0}}
  in unlit darkness (`confounding/night_light_overlap`). Comparing night with day among crashes
  in darkness only, the crude ratio of
  {{confounding/night_within_dark|outcome=fatal;model=crude|rr|ci:2}} falls to
  {{confounding/night_within_dark|outcome=fatal;model=all_blocks_without_light|rr|ci:2}} after
  adjustment (`confounding/night_within_dark`). The driver and vehicle mix works the other way:
  its share is negative,
  {{confounding/shapley_fatal|exposure=night;variant=all_blocks;block=driver_vehicle_mix|shapley_share_of_crude|cipct:0@share}},
  so holding it fixed widens the night–day gap.
  The same accounting for weekend crashes takes the crude ratio of {{confounding/sequential_fatal|exposure=weekend;ordering=primary;step=0|rr|ci:2}} to
  {{confounding/sequential_fatal|exposure=weekend;ordering=primary;step=8|rr|ci:2}}, mostly through time of day and alcohol; for crashes in rural sampling
  areas (an area-level measure, not the crash site), {{confounding/sequential_fatal|exposure=rural;ordering=primary;step=0|rr|ci:2}} becomes {{confounding/sequential_fatal|exposure=rural;ordering=primary;step=8|rr|ci:2}}.
  For crashes involving a driver aged 65+, adjustment *strengthens* the association, from
  {{confounding/sequential_fatal|exposure=older_driver;ordering=primary;step=0|rr|ci:2}} to {{confounding/sequential_fatal|exposure=older_driver;ordering=primary;step=8|rr|ci:2}}, so shares of it are not meaningful.
  Under the strict complete-case outcome the fully adjusted night ratio is
  {{confounding/outcome_definition_sensitivity|exposure=night;model=all_blocks|rr_cc|ci:2}}
  (`confounding/outcome_definition_sensitivity`), the same as under the imputed outcome; only
  the crude ratio moves
  ({{confounding/outcome_definition_sensitivity|exposure=night;model=crude|rr_cc|ci:2}}).
  These shares are statistical accounting, not causal mediation. The order of the blocks cannot
  be verified, several blocks are plausible mediators, the behaviours are police-recorded, and
  there are no exposure data, so they do not support statements such as "a third of the night
  effect is caused by darkness".
* **Rain** looks protective in the raw data (crude RR
  {{severity/fatal_crude_vs_adjusted|factor=weather;level=rain|crude_rr|ci:2}}). Adjusted for the
  other circumstances but not for road surface, rain-crashes remain less severe
  ({{severity/fatal_crude_vs_adjusted|factor=weather;level=rain|Ax_adj_rr|ci:2}}); holding the
  surface fixed as well, the difference disappears
  ({{severity/fatal_crude_vs_adjusted|factor=weather;level=rain|A_adj_rr|ci:2}}). Rain's lower
  crude severity is therefore accounted for by wet and icy surfaces (statistical accounting, not
  causal mediation), which remain associated with lower severity
  (wet {{severity/fatal_crude_vs_adjusted|factor=surface;level=wet|A_adj_rr|ci:2}}), plausibly
  because drivers slow down (speed is not observed). Model B, which also holds crash configuration
  fixed, gives {{severity/key_contrasts_ab|factor=weather;level=rain;outcome=fatal;model=B|adj_rr|ci:2}} for rain and the fatal-or-serious outcome gives
  {{severity/key_contrasts_ab|factor=weather;level=rain;outcome=ka;model=A|adj_rr|ci:2}} (model A) and {{severity/key_contrasts_ab|factor=weather;level=rain;outcome=ka;model=B|adj_rr|ci:2}} (model B)
  (`severity/key_contrasts_ab`): no clear difference in fatal severity, somewhat lower
  fatal-or-serious severity.
* **Interstates reverse, mostly on mid-speed roads.** Crude crashes on interstates are more often fatal, but compared with
  other roads *with the same speed limit* they are less severe. This is consistent with divided,
  access-controlled design. The contrast depends on the speed limit
  (`severity/interstate_by_speed_band`): on roads posted 50–65 mph the fatal risk ratio for
  interstates is {{severity/interstate_by_speed_band|outcome=fatal;speed_limit_band=50-65 mph;quantity=RR interstate vs not|estimate|ci:2}}, at 70+ mph it is {{severity/interstate_by_speed_band|outcome=fatal;speed_limit_band=70+ mph;quantity=RR interstate vs not|estimate|ci:2}}, and the
  ratio of the two is {{severity/interstate_by_speed_band|outcome=fatal;speed_limit_band=70+ mph vs 50-65 mph;quantity=ratio of RRs|estimate|ci:2}}. Averaged over speed
  limits it is {{severity/key_contrasts_ab|factor=interstate;level=yes;outcome=fatal;model=A|adj_rr|ci:2}}
  (model A) and {{severity/key_contrasts_ab|factor=interstate;level=yes;outcome=fatal;model=B|adj_rr|ci:2}}
  (model B). At the highest limits there is no detectable safety advantage.
* **Older drivers are unmasked.** Their crashes happen in low-severity settings (daytime, lower
  speeds), which hides a substantial excess severity once those settings are held constant. The
  likely mechanism is greater physical frailty of older occupants (see finding 7 for
  within-vehicle evidence).
* **Teenage drivers' crashes are *less* severe** after adjustment under model A
  ({{severity/key_contrasts_ab|factor=young_driver;level=yes;outcome=fatal;model=A|adj_rr|ci:2}}) and no longer clearly so once crash configuration is held
  fixed (model B, {{severity/key_contrasts_ab|factor=young_driver;level=yes;outcome=fatal;model=B|adj_rr|ci:2}}; fatal-or-serious
  {{severity/key_contrasts_ab|factor=young_driver;level=yes;outcome=ka;model=A|adj_rr|ci:2}} and {{severity/key_contrasts_ab|factor=young_driver;level=yes;outcome=ka;model=B|adj_rr|ci:2}}). Their problem is
  crash *involvement*, not severity (finding 6).

*Robustness.* Fatal-or-serious (KA) outcome: `severity/ka_crude_vs_adjusted`. Year effects are
included in every model. *Limitations.* Residual confounding is likely: travel speed, vehicle
mass and occupant health are not recorded.

## 4. Finding 3 — "Speeding" mixes a strong and a weaker association (exploratory split)

*Sources: `severity/fatal_speeding_type`, `descriptive/frequency_vs_severity`,
`burden/attributable_fractions_fatal`, `interactions/pairs_fatal` (follow-up pairs).*

*The split of speeding by type was motivated by earlier results and is exploratory (section 14).*

Police code a crash as speeding-related when a driver exceeded the limit, was racing, was "too
fast for conditions", or was speeding of unspecified type. Separating the types changes the
conclusion:

{{mdtable:severity/fatal_speeding_type|outcome=fatal|level:Speeding type:;n:Sample crashes:,.0f;n_events:Fatal:,.0f;rate:Crude fatal rate:pct:2;crude_rr:Crude RR:ci:2;adj_rr:Adjusted RR (model A):ci:2;share_on_wet:Share on wet roads:pct:0;share_on_snow_ice:Share on snow/ice:pct:0}}

* Crashes involving a driver who **exceeded the limit or was racing** are
  {{descriptive/frequency_vs_severity|factor=speeding_type;level=exceeded_limit_or_racing|share_all_crashes|pct:2}}
  of police-reported crashes but
  {{descriptive/frequency_vs_severity|factor=speeding_type;level=exceeded_limit_or_racing|share_fatal_fars|pct:1}}
  of fatal crashes. Their adjusted fatal risk ratio is
  {{severity/fatal_speeding_type|level=exceeded_limit_or_racing|adj_rr|ci:1}}.
* **"Too fast for conditions"** — most of the police-reported category — has a small adjusted
  association with a fatal outcome that is compatible with none under model A
  ({{severity/speeding_type_models|outcome=fatal;model=A;level=too_fast_for_conditions|adj_rr|.2f}} ({{severity/speeding_type_models|outcome=fatal;model=A;level=too_fast_for_conditions|adj_rr_low95|.2f}}–{{severity/speeding_type_models|outcome=fatal;model=A;level=too_fast_for_conditions|adj_rr_high95|.2f}})). That interval is not evidence of no effect: its 90%
  version excludes only effects beyond about ±{{severity/speeding_type_models|outcome=fatal;model=A;level=too_fast_for_conditions|equivalence_bound_pct|.0f}}%.
  With crash configuration, a possible mediator, held fixed (model B) the ratio is
  {{severity/speeding_type_models|outcome=fatal;model=B;level=too_fast_for_conditions|adj_rr|.2f}} ({{severity/speeding_type_models|outcome=fatal;model=B;level=too_fast_for_conditions|adj_rr_low95|.2f}}–{{severity/speeding_type_models|outcome=fatal;model=B;level=too_fast_for_conditions|adj_rr_high95|.2f}}); for fatal-or-serious (KA) outcomes it is
  {{severity/speeding_type_models|outcome=ka;model=A;level=too_fast_for_conditions|adj_rr|.2f}} ({{severity/speeding_type_models|outcome=ka;model=A;level=too_fast_for_conditions|adj_rr_low95|.2f}}–{{severity/speeding_type_models|outcome=ka;model=A;level=too_fast_for_conditions|adj_rr_high95|.2f}}) (model A) and {{severity/speeding_type_models|outcome=ka;model=B;level=too_fast_for_conditions|adj_rr|.2f}} ({{severity/speeding_type_models|outcome=ka;model=B;level=too_fast_for_conditions|adj_rr_low95|.2f}}–{{severity/speeding_type_models|outcome=ka;model=B;level=too_fast_for_conditions|adj_rr_high95|.2f}})
  (model B). The category is concentrated on wet and icy roads, where crashes are less severe.
  All four estimates (`severity/speeding_type_models`):

{{mdtable:severity/speeding_type_models||outcome:Outcome:;model:Model:;level:Speeding type:;adj_rr:Adjusted RR:.2f;adj_rr_low95:Low 95%:.2f;adj_rr_high95:High 95%:.2f}}

* The severity-pathway attributable fraction is
  {{burden/attributable_fractions_fatal|shift=exceeded_limit_removed|af|cipct:1}} of fatal
  crashes for limit exceedance and
  {{burden/attributable_fractions_fatal|shift=too_fast_for_conditions_removed|af|cipct:1}} for
  "too fast for conditions" (model-predicted, finding 10).
* This helps explain the apparently protective "speeding × wet" interaction: for limit
  exceedance, the risk ratio on wet roads
  ({{interactions/pairs_fatal|pair=exceeded_limit x wet|rr_A_given_B1|ci:1}}) is compared with
  that on dry roads ({{interactions/pairs_fatal|pair=exceeded_limit x wet|rr_A_given_B0|ci:1}})
  in an exploratory pair (`reports/interactions.md`).

*Measurement caveat.* Speeding is a police judgement made after the crash. FARS (fuller
investigation) records speeding in
{{measurement/fars_crss_fatal_composition|YEAR=all;attribute=speeding|fars_share|pct:0}} of fatal
crashes; CRSS records it in
{{measurement/fars_crss_fatal_composition|YEAR=all;attribute=speeding|crss_share|pct:0}} of the
same population. Recording is therefore more complete when crashes are investigated more
thoroughly. The crude risk ratio for speeding is
{{measurement/qba_grid|exposure=speeding;se_fatal=0.8;se_nonfatal=0.8;specificity=1|rr_observed|.2f}}
as recorded and
{{measurement/qba_grid|exposure=speeding;se_fatal=0.8;se_nonfatal=0.8;specificity=1|rr_corrected|.2f}}
after correcting for a recording sensitivity of 0.8 in all crashes; if sensitivity in non-fatal
crashes were 0.5 instead, the corrected ratio would be
{{measurement/qba_grid|exposure=speeding;se_fatal=0.8;se_nonfatal=0.5;specificity=1|rr_corrected|.2f}}
(`measurement/qba_grid`). The large association for limit exceedance (crude risk ratio
{{measurement/qba_grid|exposure=exceeded_limit;se_fatal=0.8;se_nonfatal=0.8;specificity=1|rr_observed|.1f}} against no speeding) is less exposed to this. With
recording sensitivity 0.8 in fatal crashes, the corrected ratio is still
{{measurement/qba_grid|exposure=exceeded_limit;se_fatal=0.8;se_nonfatal=0.2;specificity=1|rr_corrected|.1f}} if limit exceedance in non-fatal crashes were recorded
with sensitivity 0.2 and {{measurement/qba_grid|exposure=exceeded_limit;se_fatal=0.8;se_nonfatal=0.1;specificity=1|rr_corrected|.2f}} at 0.1; it falls below 1 only
between 0.1 and 0.05 ({{measurement/qba_grid|exposure=exceeded_limit;se_fatal=0.8;se_nonfatal=0.05;specificity=1|rr_corrected|.2f}}), that is, only if exceedance in
non-fatal crashes were recorded about a tenth as completely as in fatal crashes.

*Bias analysis by speeding type* (`severity/speeding_type_qba`; the same grid of sensitivities
applied to the type-specific crude ratio, with the bias factor multiplied into the model-A estimate).
For limit exceedance the bias-corrected adjusted fatal ratio stays above 1 in every feasible cell, from
{{severity/speeding_type_qba|outcome=fatal;speeding_type=exceeded_limit_or_racing|min(adj_rr_bias_corrected)|.2f}} to
{{severity/speeding_type_qba|outcome=fatal;speeding_type=exceeded_limit_or_racing|max(adj_rr_bias_corrected)|.2f}}.
For "too fast for conditions" it ranges from
{{severity/speeding_type_qba|outcome=fatal;speeding_type=too_fast_for_conditions|min(adj_rr_bias_corrected)|.2f}} to
{{severity/speeding_type_qba|outcome=fatal;speeding_type=too_fast_for_conditions|max(adj_rr_bias_corrected)|.2f}},
so its sign depends on the assumed differential recording and the bias analysis cannot settle it.
Some cells of that table are blank. The `status` column says why: with a false-positive rate of
1% (specificity 0.99) the matrix correction is infeasible when the recorded share of non-fatal crashes
with that speeding type is below the assumed false-positive rate, because the corrected count of
exposed non-fatal crashes would be negative. That is the case for every specificity-0.99 cell of
limit exceedance, whose recorded share among non-fatal crashes is under 1%. A blank cell means the
correction is impossible there, not that the corrected ratio is zero or unchanged.

*Policy relevance.* Automated speed enforcement acts on exceeding the posted limit — the
component with the strong association. The much larger "too fast for conditions" category is
not a camera target; its association with severity is small and imprecise, and the type split is exploratory.

## 5. Finding 4 — The most robust severity associations

*Sources: `severity/fatal_crude_vs_adjusted`, `measurement/alcohol_coding_sensitivity`, `vulnerable/*`.*

* **Motorcycle involvement**: adjusted RR
  {{severity/fatal_crude_vs_adjusted|factor=any_motorcycle;level=yes|A_adj_rr|ci:1}}.
* **Speed environment**: roads posted 50–55 mph,
  {{severity/fatal_crude_vs_adjusted|factor=speed_limit;level=50-55|A_adj_rr|ci:2}}, are as
  severe as 70+ mph roads, {{severity/fatal_crude_vs_adjusted|factor=speed_limit;level=70+|A_adj_rr|ci:2}}
  (vs 30–35 mph). 50–55 mph roads are typically undivided rural highways, where head-on crashes
  are possible.
* **Unlit darkness**: {{severity/fatal_crude_vs_adjusted|factor=light;level=dark_not_lighted|A_adj_rr|ci:2}}
  (lit darkness {{severity/fatal_crude_vs_adjusted|factor=light;level=dark_lighted|A_adj_rr|ci:2}}).
* **Heavy trucks and buses**: {{severity/fatal_crude_vs_adjusted|factor=any_heavy_truck;level=yes|A_adj_rr|ci:2}}.
* **Alcohol** is strongly associated with severity under every coding, but the size depends on
  the coding. The adjusted RR is
  {{measurement/alcohol_coding_sensitivity|period=2016-2024;coding=imputed (ALCHL_IM)|adj_rr|ci:1}}
  using NHTSA's imputation — {{measurement/alcohol_coding_sensitivity|period=2016-2018;coding=imputed (ALCHL_IM)|adj_rr|ci:1}}
  in 2016–2018 but {{measurement/alcohol_coding_sensitivity|period=2019-2024;coding=imputed (ALCHL_IM)|adj_rr|ci:1}}
  in 2019–2024, after the coding break, when the imputation fills far more unknowns —
  {{measurement/alcohol_coding_sensitivity|period=2016-2024;coding=police, complete case|adj_rr|ci:1}}
  among crashes with known police-reported alcohol, and
  {{measurement/alcohol_coding_sensitivity|period=2016-2024;coding=police, unknown as no|adj_rr|ci:1}}
  if unknown is treated as "no" (a coding known to attenuate). The complete-case estimate is
  stable across the 2019 coding break:
  {{measurement/alcohol_coding_sensitivity|period=2016-2018;coding=police, complete case|adj_rr|.1f}}
  in 2016–2018 and {{measurement/alcohol_coding_sensitivity|period=2019-2024;coding=police, complete case|adj_rr|.1f}}
  in 2019–2024.

**Pedestrians** (`vulnerable/pedestrian_killed_contrasts`; figure `pedestrians.png`). Given that a
pedestrian is struck, the adjusted risk of death rises steeply with the posted limit. Relative to
roads posted ≤25 mph, the RR is
{{vulnerable/pedestrian_killed_contrasts|victim=pedestrian;outcome=killed;factor=str_speed_limit;level=30-35|adj_rr|ci:1}}
at 30–35 mph,
{{vulnerable/pedestrian_killed_contrasts|victim=pedestrian;outcome=killed;factor=str_speed_limit;level=40-45|adj_rr|ci:1}}
at 40–45 mph and
{{vulnerable/pedestrian_killed_contrasts|victim=pedestrian;outcome=killed;factor=str_speed_limit;level=50-55|adj_rr|ci:1}}
at 50–55 mph. Compared with a passenger car, the adjusted RR is
{{vulnerable/pedestrian_killed_contrasts|victim=pedestrian;outcome=killed;factor=striking;level=suv|adj_rr|ci:2}}
when the striking vehicle is an SUV,
{{vulnerable/pedestrian_killed_contrasts|victim=pedestrian;outcome=killed;factor=striking;level=pickup|adj_rr|ci:2}}
for a pickup and
{{vulnerable/pedestrian_killed_contrasts|victim=pedestrian;outcome=killed;factor=striking;level=large|adj_rr|ci:2}}
for a large truck or bus. The SUV/pickup excess is relatively largest on roads posted ≤35 mph
(RR {{vulnerable/pedestrian_light_truck_by_speed|victim=pedestrian;outcome=killed;quantity=RR SUV/pickup vs car, <=35 mph|estimate|.2f}},
{{vulnerable/pedestrian_light_truck_by_speed|victim=pedestrian;outcome=killed;quantity=RR SUV/pickup vs car, <=35 mph|low|.2f}}–{{vulnerable/pedestrian_light_truck_by_speed|victim=pedestrian;outcome=killed;quantity=RR SUV/pickup vs car, <=35 mph|high|.2f}}).
SUVs' share of pedestrian deaths rose from
{{vulnerable/fars_pedestrian_deaths_by_striking_vehicle|YEAR=2016|share_suv|pct:1}} in 2016 to
{{vulnerable/fars_pedestrian_deaths_by_striking_vehicle|YEAR=2024|share_suv|pct:1}} in 2024
(FARS, observed). Unlit darkness
({{vulnerable/pedestrian_killed_contrasts|victim=pedestrian;outcome=killed;factor=light;level=dark_not_lighted|adj_rr|ci:1}}),
mid-block crossing
({{vulnerable/pedestrian_killed_contrasts|victim=pedestrian;outcome=killed;factor=location;level=midblock|adj_rr|ci:1}}
vs crossing in a crosswalk) and age 75+
({{vulnerable/pedestrian_killed_contrasts|victim=pedestrian;outcome=killed;factor=age_band;level=75+|adj_rr|ci:1}}
vs 25–34) are also strongly associated with pedestrian death. The posted limit of the striking vehicle is
unknown for {{vulnerable/speed_limit_missingness|victim=pedestrian;outcome=killed;group=all|estimate|pct:0}}
of struck pedestrians, and unknown far less often when the pedestrian died
({{vulnerable/speed_limit_missingness|victim=pedestrian;outcome=killed;group=fatal / outcome|estimate|cipct:0}}
of fatal cases against {{vulnerable/speed_limit_missingness|victim=pedestrian;outcome=killed;group=not|estimate|cipct:0}}
of non-fatal ones; `vulnerable/speed_limit_missingness`), so the crude shares who died by posted limit
depend on how unknown limits are handled; the adjusted ratios keep "unknown" as its own level. The
speed-limit gradient also reflects where high-limit roads are: without adjustment for location, light
and time of day the 50–55 mph ratio is
{{vulnerable/pedestrian_speed_limit_adjustment|victim=pedestrian;outcome=killed;specification=without location, light and time of day;level=50-55|adj_rr|ci:1}},
against {{vulnerable/pedestrian_speed_limit_adjustment|victim=pedestrian;outcome=killed;specification=full (published);level=50-55|adj_rr|ci:1}}
adjusted (`vulnerable/pedestrian_speed_limit_adjustment`); the adjusted figure is the one to read.
*Limitations*: impact speed, vehicle
mass and front-end geometry are not separately observed. Exposure to being struck is not
measured, so these ratios describe severity *given* a pedestrian crash.

## 6. Finding 5 — Which combinations amplify risk

See `reports/interactions.md`. In brief: among the 13 registered pairs, pedestrian crashes in
unlit darkness are the clearest case of amplification on both scales, and motorcycle crashes
involving alcohol carry a large *additive* excess (deaths) although on the ratio scale the
combination is sub-multiplicative (ratio of risk ratios
{{interactions/pairs_fatal|pair=motorcycle x alcohol|ratio_of_rr|ci:2}}). Pedestrian crashes on 50+ mph roads show
the largest additive excess of all, in an exploratory pair. The widely assumed amplifications of
speeding by darkness and of young drivers by night are not detected for the fatal outcome (ratio
of risk ratios {{interactions/pairs_fatal|pair=speeding x dark_unlit|ratio_of_rr|ci:2}} and
{{interactions/pairs_fatal|pair=young_driver x late_night|ratio_of_rr|ci:2}}); a non-significant result is not
evidence of no interaction. For fatal-or-serious crashes, speeding in unlit darkness does show
an additive excess of {{interactions/pairs_ka|pair=speeding x dark_unlit|ic|cix1000:1}} per 1,000 crashes (Holm
p {{interactions/pairs_ka|pair=speeding x dark_unlit|ic_p_holm|.1g}}). The protective-looking speeding × wet interaction
partly reflects the mix of speeding types ("too fast for conditions" concentrates on wet roads) and the
lower wet-road baseline.

## 7. Finding 6 — Crash involvement is not crash severity

*Sources: `exposure/relative_involvement` (quasi-induced exposure), `severity/fatal_crude_vs_adjusted`;
figure `relative_involvement_age.png`.*

The data contain no measure of how much people drive, so crash *rates* per mile cannot be
estimated. Quasi-induced exposure compares each driver group's share among culpable drivers in
two-vehicle crashes with its share among non-culpable drivers (a proxy for drivers on the road).
Culpability uses pre-crash actions (speeding, critical pre-crash event, driver-error codes), not
charges. Crashes with a hit-and-run vehicle
({{exposure/sample|definition=C1 action-based (primary)|weighted_share_excluded_hit_and_run|pct:0}}
of two-vehicle crashes) are excluded, because fleeing drivers are almost always coded culpable
and their age and sex are unknown. Relative involvement ratios (RIR), all qualifying crashes:

{{mdtable:exposure/relative_involvement|factor=age_band;stratum=all|level:Driver age:;n_drivers:Drivers:,.0f;rir:RIR (95% CI):ci:2;adj_rir_ratio_vs_ref:Adjusted ratio vs 35–44:.2f}}

* Drivers aged 15–20 are over-represented as the culpable party
  (RIR {{exposure/relative_involvement|factor=age_band;level=15-20;stratum=all|rir|ci:2}}), yet
  crashes involving them are *less* severe under model A
  ({{severity/fatal_crude_vs_adjusted|factor=young_driver;level=yes|A_adj_rr|ci:2}}); with crash
  configuration also held fixed (model B) the ratio is {{severity/key_contrasts_ab|factor=young_driver;level=yes;outcome=fatal;model=B|adj_rr|ci:2}}.
* Drivers aged 75+ are also over-represented as the culpable party
  (RIR {{exposure/relative_involvement|factor=age_band;level=75+;stratum=all|rir|ci:2}}), while
  drivers aged 65–74 are not
  ({{exposure/relative_involvement|factor=age_band;level=65-74;stratum=all|rir|ci:2}}). Crashes
  involving a driver aged 65+ are more severe
  ({{severity/fatal_crude_vs_adjusted|factor=older_driver;level=yes|A_adj_rr|ci:2}}).
* Alcohol-involved drivers are strongly over-represented, but the size depends on how alcohol
  is measured. With NHTSA's imputed alcohol field the RIR falls from
  {{exposure/relative_involvement|factor=alcohol_im;level=yes;stratum=2016-2018|rir|ci:1}} in
  2016–2018 to {{exposure/relative_involvement|factor=alcohol_im;level=yes;stratum=2020-2024|rir|ci:1}}
  in 2020–2024. The fall tracks the 2019–2020 coding break, when the imputation began filling
  a third of drivers' alcohol status almost independently of who was at fault; it is not
  evidence of a change in behaviour. Police-reported alcohol ("yes" vs anything else) gives a
  stable {{exposure/relative_involvement|factor=alcohol_police;level=yes;stratum=2016-2018|rir|ci:1}}
  and {{exposure/relative_involvement|factor=alcohol_police;level=yes;stratum=2020-2024|rir|ci:1}}
  in the same periods, an upper bound if police look for alcohol more in the driver at fault.
  With charge-based culpability (impairment charges excluded) the imputed estimate is
  {{exposure/relative_involvement_charge_based|factor=alcohol_im;level=yes|rir|ci:1}}.
* In two-vehicle crashes, teenage drivers' over-representation is lower at night
  (RIR {{exposure/relative_involvement|factor=age_band;level=15-20;stratum=night|rir|ci:2}}) than
  by day ({{exposure/relative_involvement|factor=age_band;level=15-20;stratum=day|rir|ci:2}}),
  relative to the other drivers on the road at each time. Single-vehicle crashes, where
  young and night-time drivers' crashes concentrate, are outside this design.

*Assumptions (untestable here):* non-culpable drivers represent drivers on the road — but the
non-culpable pool is dominated by drivers struck from behind, so it reflects congested traffic
more than all driving, and drivers less able to avoid other drivers' errors (possibly older
drivers) may be over-represented in it, which would push their RIR down; police code pre-crash
actions without bias by group. QIE says nothing about crash rates per mile, and crash-level
conditions (light, weather) cannot be assessed with it.

## 8. Finding 7 — Restraint use

*Sources: `matched/belt_effect`, `matched/double_pair_comparison`, `matched/clogit_coefficients`
(FARS, within the same vehicle); `person/lpv_killed_crude_vs_adjusted`,
`person/lpv_killed_interaction_restraint_x_age` (CRSS, design-based).*

Comparisons between people in different crashes cannot separate belt use from crash energy:
unbelted occupants are, on average, in more violent crashes. FARS allows a comparison **within
the same vehicle**, which holds fixed everything the occupants share — impact speed, vehicle,
road, weather.

* **Double-pair comparison** (drivers and right-front passengers; {{matched/belt_effect|estimand=fatality_risk_reduction_belt_given_fatal_crash|n_vehicles|,.0f}} pairs with at least one
  death). Given a crash severe enough to kill someone in the vehicle, a belted occupant's risk of
  dying was
  {{matched/belt_effect|estimand=fatality_risk_reduction_belt_given_fatal_crash|estimate|cipct:1}}
  lower than an unbelted occupant's (crash-cluster bootstrap CI). The four component comparisons
  agree closely.
* **Conditional logistic regression** with the vehicle as the matched set, adjusted for age, sex
  and seat: odds ratio of death, unbelted vs belted,
  {{matched/clogit_coefficients|model=main;term=unbelted|odds_ratio|ci:2@or}}. Deaths are common
  in these vehicles, so this odds ratio overstates the risk ratio.
* **The estimate depends on truthful reporting, and the error can run both ways.** Belt use of
  surviving occupants is largely what they tell police. If 10% of "belted" survivors were in fact
  unbelted, the reduction would be
  {{matched/belt_effect|estimand=fatality_risk_reduction_belt_given_fatal_crash_misreport_f10|estimate|cipct:1}};
  at 20%, {{matched/belt_effect|estimand=fatality_risk_reduction_belt_given_fatal_crash_misreport_f20|estimate|cipct:1}}.
  Those one-sided scenarios move only survivors. Adding the reverse error, a fraction g of deaths
  coded unbelted who were truly belted (`matched/belt_misreporting_two_sided_dpc`), lowers the
  reduction further: with 10% of belted survivors misrecorded and g at 5% it is {{matched/belt_misreporting_two_sided_dpc|analysis=belt_driver_rf;survivor_misreport_f=0.1;death_misreport_g=0.05|reduction_1_minus_rr|cipct:0@reduction}};
  with both at 10%, {{matched/belt_misreporting_two_sided_dpc|analysis=belt_driver_rf;survivor_misreport_f=0.1;death_misreport_g=0.1|reduction_1_minus_rr|cipct:0@reduction}}; with 20% and 5%, {{matched/belt_misreporting_two_sided_dpc|analysis=belt_driver_rf;survivor_misreport_f=0.2;death_misreport_g=0.05|reduction_1_minus_rr|pct:0}}
  (a negative reduction means the estimate has reversed). The association would vanish at about
  {{matched/belt_misreporting_two_sided_dpc|analysis=belt_driver_rf;survivor_misreport_f=0;death_misreport_g=0|tipping_f_given_g|pct:0}}
  of belted survivors misrecorded with no reverse error, at about
  {{matched/belt_misreporting_two_sided_dpc|analysis=belt_driver_rf;survivor_misreport_f=0;death_misreport_g=0.05|tipping_f_given_g|pct:0}}
  if 5% of unbelted-coded deaths were belted, or at about
  {{matched/belt_misreporting_two_sided_dpc|analysis=belt_driver_rf;survivor_misreport_f=0;death_misreport_g=0|tipping_g_given_f|pct:0}}
  reverse error alone. The true rates are unknowable from these data. The size is therefore
  uncertain; the direction is not, unless misreporting is very large.
* **The pooled figure averages very different crash types** (`matched/belt_by_crash_type`). The
  reduction in risk of death for a belted occupant, with its tipping point (the share of belted
  survivors who would have to be misrecorded to remove it):

{{mdtable:matched/belt_by_crash_type|partition=all~crash type~vehicle rollover|stratum:Stratum:;dpc_n_pairs:Pairs:,.0f;dpc_reduction:Reduction (95% CI):cipct:0;dpc_tipping_point_f:Tipping point:pct:0}}

  These strata are conditional on a fatal crash in the vehicle and the two partitions overlap.
* **Heterogeneity by driver behaviour (exploratory follow-up).** The earlier unstratified conclusion that
  the belt effect does not vary with driver speeding does not hold within crash configuration. Layering
  crashes four ways (single or multi-vehicle, rollover, both crossed, harmonised crash type), the ratio of
  belt risk ratios, speeding vs not, runs from {{restraint_behaviour/dpc_contrast_within_configuration|contrast=driver speeding (any) vs not speeding;layer=pooled within layers|min(ratio_of_rrs)|.2f}} to {{restraint_behaviour/dpc_contrast_within_configuration|contrast=driver speeding (any) vs not speeding;layer=pooled within layers|max(ratio_of_rrs)|.2f}} (smallest lower confidence limit {{restraint_behaviour/dpc_contrast_within_configuration|contrast=driver speeding (any) vs not speeding;layer=pooled within layers|min(ratio_low)|.2f}});
  above 1 means belts are somewhat less protective with a speeding driver. The crossed scheme gives the
  largest estimate, {{restraint_behaviour/dpc_contrast_within_configuration|contrast=driver speeding (any) vs not speeding;adjustment=single/multi-vehicle x rollover;layer=pooled within layers|ratio_of_rrs|ci:2@ratio}}, and the crash-type scheme pools only
  {{restraint_behaviour/dpc_contrast_within_configuration|contrast=driver speeding (any) vs not speeding;adjustment=crash type;layer=pooled within layers|n_layers_pooled|.0f}} of its 8 crash types, the rest having too few deaths in a cell. For exceeding the limit or racing, the crossed scheme gives
  {{restraint_behaviour/dpc_contrast_within_configuration|contrast=driver exceeded limit / racing vs not speeding;adjustment=single/multi-vehicle x rollover;layer=pooled within layers|ratio_of_rrs|ci:2@ratio}}.
  Pooling the crashes first gives {{restraint_behaviour/dpc_contrast_within_configuration|contrast=driver speeding (any) vs not speeding;adjustment=none (unstratified);layer=all vehicles|ratio_of_rrs|ci:2@ratio}}.
  The unstratified null reflects crash composition: speeding drivers are more often in single-vehicle
  crashes, where belts look more protective. For a driver at BAC .08 or more the within-configuration
  ratio is {{restraint_behaviour/dpc_contrast_within_configuration|contrast=driver BAC >= .08 (MI) vs BAC < .08;adjustment=single/multi-vehicle x rollover;layer=pooled within layers|ratio_of_rrs|ci:2@ratio}},
  no difference (`restraint_behaviour/dpc_contrast_within_configuration`). The layers are pooled as if
  independent and the follow-up is not multiplicity-adjusted.
* **Frailty.** Within the same vehicle, belted occupants aged 65+ died more often than belted
  occupants aged 25–44 of the same sex
  ({{matched/double_pair_comparison|analysis=age_65plus_vs_25_44_both_belted_same_sex;component=combined (inverse-variance weighted)|rr_x1_vs_x0|ci:2@rr}}
  times the risk). Women and men of similar age differed little
  ({{matched/double_pair_comparison|analysis=female_vs_male_both_belted_age_gap_le5;component=combined (inverse-variance weighted)|rr_x1_vs_x0|ci:2@rr}}).
* **Motorcycle helmets** (operator and passenger on the same motorcycle): risk ratio of death,
  helmeted vs unhelmeted,
  {{matched/double_pair_comparison|analysis=motorcycle_helmet;component=combined (inverse-variance weighted)|rr_x1_vs_x0|ci:2@rr}}.
  This is imprecise and fragile to misreporting (`matched/helmet_misreporting_dpc`): if 5% of
  helmeted-coded survivors were unhelmeted the reduction would be {{matched/helmet_misreporting_dpc|analysis=motorcycle_helmet;survivor_misreport_f=0.05;death_misreport_g=0|reduction_1_minus_rr|cipct:0@reduction}}, and it vanishes
  at about {{matched/helmet_misreporting_dpc|analysis=motorcycle_helmet;survivor_misreport_f=0;death_misreport_g=0|tipping_f_given_g|pct:0}}
  survivor misreporting, or {{matched/helmet_misreporting_dpc|analysis=motorcycle_helmet;survivor_misreport_f=0;death_misreport_g=0|tipping_g_given_f|pct:0}}
  reverse error. It rests on {{matched/helmet_pair_coverage|metric=pairs_discordant_helmet_use|count|,.0f}}
  operator-passenger pairs that differ in helmet use. Only
  {{matched/helmet_pair_coverage|metric=unhelmeted_deaths_in_pair_design|share|pct:0}}
  of the {{matched/helmet_pair_coverage|metric=unhelmeted_motorcyclist_deaths|count|,.0f}} unhelmeted motorcyclist deaths
  were in an operator-passenger pair of any kind (helmet use and outcome known for both riders, whether
  or not the pair differs in helmet use); most were on single-rider motorcycles,
  {{matched/helmet_pair_coverage|metric=unhelmeted_deaths_single_rider_motorcycle|share|pct:0}},
  so applying it to all unhelmeted deaths assumes two-up riders are representative of solo riders
  (`matched/helmet_pair_coverage`; its {{matched/helmet_pair_coverage|metric=unhelmeted_motorcyclist_deaths|count|,.0f}} unhelmeted deaths
  differ from the {{deaths/potential_lives_context|metric=unhelmeted_deaths|deaths|,.0f}} in `deaths/potential_lives_context`
  because the two modules define motorcycle and no helmet differently: the matched module uses the harmonised
  vehicle body type (BODY_TYP 80-89) and the harmonised REST_USE/HELM_USE helmet code, the deaths module the
  FARS auxiliary-file body type A_BODY = 7 and A_HELMUSE = 2).

Across crashes (CRSS), unbelted light-vehicle occupants were far more likely to die than belted
ones: crude RR {{person/lpv_killed_crude_vs_adjusted|factor=restraint;level=none|crude_rr|ci:1}},
{{person/lpv_killed_crude_vs_adjusted|factor=restraint;level=none|A_adj_rr|ci:1}} after
adjusting for person and pre-crash circumstances. These figures are several times the
within-vehicle estimate, as expected if unbelted occupants are in more severe crashes and
survivors over-report belt use. **They must not be read as belt effectiveness.** The *excess*
risk of being unbelted rises steeply with age on the additive scale: the risk difference is
{{person/lpv_killed_interaction_restraint_x_age|b_level=25-34|rd|pct:1}} at 25–34 but
{{person/lpv_killed_interaction_restraint_x_age|b_level=75+|rd|pct:1}} at 75+, although the
risk ratio is lower at 75+
({{person/lpv_killed_interaction_restraint_x_age|b_level=75+|ratio_of_rr|ci:2}} times the
25–34 ratio).

*Limitations.* All within-vehicle estimates are conditional on a fatal crash and assume that
occupants of the same vehicle differ only in belt use, age, sex and seat; belt use is recorded
by police, partly from survivors' statements.

## 9. Finding 8 — The post-2020 rise in severity

*Sources: `trends/numerator_denominator`, `trends/decomposition`, `trends/annual_shares`,
`trends/within_by_subgroup`, `trends/outcome_definitions_by_year`, `trends/fars_changes`.
Method: survey-weighted Oaxaca–Blinder-type decomposition with standardised margins: the
2016–19 model applied to 2020–24 crashes gives the fatal share expected from the change in
recorded circumstances alone. Labels: estimated (shares), adjusted association (composition and
within-circumstance parts), observed (FARS).*

**How large the rise is.** The fatal share of police-reported crashes rose from
{{trends/numerator_denominator|outcome=fatal;comparison=2020-2024 vs 2016-2019;quantity=fatal_share_base|estimate|cipct:2}} in 2016–19 to {{trends/numerator_denominator|outcome=fatal;comparison=2020-2024 vs 2016-2019;quantity=fatal_share_comparison|estimate|cipct:2}}
in 2020–24, a risk ratio of {{trends/numerator_denominator|outcome=fatal;comparison=2020-2024 vs 2016-2019;quantity=ratio_fatal_share|estimate|ci:2}}. Under the strict
complete-case outcome the rise is larger: {{trends/numerator_denominator|outcome=fatal_cc;comparison=2020-2024 vs 2016-2019;quantity=ratio_fatal_share|estimate|ci:2}}.
The fatal-or-serious (KA) share shows no clear rise
({{trends/decomposition|analysis=model_B;outcome=ka;quantity=total_change|estimate|ci:2}} percentage points).

**Numerator and denominator.** Fatal crashes rose
({{trends/numerator_denominator|outcome=fatal;comparison=2020-2024 vs 2016-2019;quantity=ratio_fatal_crashes_numerator|estimate|ci:3}}, matching the FARS census ratio of
{{trends/numerator_denominator|outcome=fatal;comparison=2020-2024 vs 2016-2019;quantity=FARS_ratio_fatal_crashes (census)|estimate|.3f}}), but the
number of police-reported crashes fell ({{trends/numerator_denominator|outcome=fatal;comparison=2020-2024 vs 2016-2019;quantity=ratio_reported_crashes_denominator|estimate|ci:3}}).
The fall in reported crashes accounts for {{trends/denominator_share|outcome=fatal;comparison=2020-2024 vs 2016-2019;quantity=denominator_share_of_log_rise|estimate|cipct:0}}
of the rise in the fatal share under NHTSA's imputed outcome and {{trends/denominator_share|outcome=fatal_cc;comparison=2020-2024 vs 2016-2019;quantity=denominator_share_of_log_rise|estimate|cipct:0}} under the
complete-case outcome (`trends/denominator_share`; intervals cover CRSS sampling only). It is not only a fall in property-damage-only reports: fatal
crashes also rose as a share of injury crashes ({{trends/numerator_denominator|outcome=fatal;comparison=2020-2024 vs 2016-2019;quantity=ratio_K_share_of_injury_KABC|estimate|ci:2}}).

**Composition accounts for a modest to substantial part of the rise, depending on the model.** This is a second, separate accounting of the
same rise, not an addition to the first. Changes in the recorded circumstances of crashes
(time, road, light, weather, alcohol, speeding, driver and vehicle mix, crash configuration)
account for {{trends/decomposition|analysis=model_B;outcome=fatal;quantity=composition_share_of_change_ref_P0|estimate|cipct:0}} of the rise
when the 2016–19 model is the reference and
{{trends/decomposition|analysis=model_B;outcome=fatal;quantity=composition_share_of_change_ref_P1|estimate|cipct:0}} with the 2020–24 model.
Without crash configuration the share is {{trends/decomposition|analysis=model_A;outcome=fatal;quantity=composition_share_of_change_ref_P0|estimate|cipct:0}}
({{trends/decomposition|analysis=model_A;outcome=fatal;quantity=composition_share_of_change_ref_P1|estimate|cipct:0}}
with the 2020–24 model);
without the three variables whose "unknown" coding drifted over the period (junction, weather,
road surface) it is {{trends/decomposition|analysis=sens_B_without_coding_drift_vars;outcome=fatal;quantity=composition_share_of_change_ref_P0|estimate|cipct:0}};
under the complete-case outcome it is {{trends/decomposition|analysis=model_B;outcome=fatal_cc;quantity=composition_share_of_change_ref_P0|estimate|cipct:0}}.
Across four covariate specifications (published, without imputed alcohol, without the coding-drift
variables, without both) and both reference periods, the composition share with crash configuration
(model B) runs from {{trends/composition_robustness|covariate_set=B;quantity=composition_share_of_change_ref_P0~composition_share_of_change_ref_P1|min(estimate)|pct:0}} to {{trends/composition_robustness|covariate_set=B;quantity=composition_share_of_change_ref_P0~composition_share_of_change_ref_P1|max(estimate)|pct:0}}, and without crash configuration (model A)
from {{trends/composition_robustness|covariate_set=A;quantity=composition_share_of_change_ref_P0~composition_share_of_change_ref_P1|min(estimate)|pct:0}} to {{trends/composition_robustness|covariate_set=A;quantity=composition_share_of_change_ref_P0~composition_share_of_change_ref_P1|max(estimate)|pct:0}} (`trends/composition_robustness`); "roughly a quarter to a
half" is the model-B range only (model B adds crash configuration, a possible mediator of the rise); the
intervals are wide and several of them include zero:

{{mdtable:trends/composition_robustness|covariate_set=B;quantity=composition_share_of_change_ref_P0~composition_share_of_change_ref_P1|specification:Specification (model B):;quantity:Reference period:;estimate:Composition share (95% CI):cipct:0}}

For the 2019→2021 jump alone the split is unstable: composition accounts for
{{trends/decomposition|analysis=sens_B_2019_vs_2021;outcome=fatal;quantity=composition_share_of_change_ref_P0|estimate|cipct:0}} of it with the 2019
model as reference but {{trends/decomposition|analysis=sens_B_2019_vs_2021;outcome=fatal;quantity=composition_share_of_change_ref_P1|estimate|cipct:0}}
with the 2021 model.
Within the same recorded circumstances the fatal share was higher by a factor of
{{trends/decomposition|analysis=model_B;outcome=fatal;quantity=risk_ratio_within_ref_P0|estimate|ci:2}}. The within-circumstance
increase is clearest in speeding-related crashes ({{trends/within_by_subgroup|analysis=model_B;outcome=fatal;subgroup=speeding-related|within_rr|ci:2}}),
although its interval overlaps those of motorcycle and interstate crashes; there is no
detectable increase in alcohol-involved crashes ({{trends/within_by_subgroup|analysis=model_B;outcome=fatal;subgroup=alcohol involved (imputed)|within_rr|ci:2}},
also compatible with the overall ratio).

**Year by year, the 2023–24 excess depends on the outcome definition.** Observed fatal share
against the share expected from the recorded crash mix under the 2016–19 model (model B):

| Year | Fatal share, imputed outcome | Observed ÷ expected, imputed | Fatal share, complete case | Observed ÷ expected, complete case |
|---|---|---|---|---|
| 2019 | {{trends/annual_shares|YEAR=2019;outcome=fatal|crude_share|cipct:2@crude}} | {{trends/annual_shares|YEAR=2019;outcome=fatal|obs_over_expectedB|ci:2}} | {{trends/annual_shares|YEAR=2019;outcome=fatal_cc|crude_share|cipct:2@crude}} | {{trends/annual_shares|YEAR=2019;outcome=fatal_cc|obs_over_expectedB|ci:2}} |
| 2020 | {{trends/annual_shares|YEAR=2020;outcome=fatal|crude_share|cipct:2@crude}} | {{trends/annual_shares|YEAR=2020;outcome=fatal|obs_over_expectedB|ci:2}} | {{trends/annual_shares|YEAR=2020;outcome=fatal_cc|crude_share|cipct:2@crude}} | {{trends/annual_shares|YEAR=2020;outcome=fatal_cc|obs_over_expectedB|ci:2}} |
| 2021 | {{trends/annual_shares|YEAR=2021;outcome=fatal|crude_share|cipct:2@crude}} | {{trends/annual_shares|YEAR=2021;outcome=fatal|obs_over_expectedB|ci:2}} | {{trends/annual_shares|YEAR=2021;outcome=fatal_cc|crude_share|cipct:2@crude}} | {{trends/annual_shares|YEAR=2021;outcome=fatal_cc|obs_over_expectedB|ci:2}} |
| 2022 | {{trends/annual_shares|YEAR=2022;outcome=fatal|crude_share|cipct:2@crude}} | {{trends/annual_shares|YEAR=2022;outcome=fatal|obs_over_expectedB|ci:2}} | {{trends/annual_shares|YEAR=2022;outcome=fatal_cc|crude_share|cipct:2@crude}} | {{trends/annual_shares|YEAR=2022;outcome=fatal_cc|obs_over_expectedB|ci:2}} |
| 2023 | {{trends/annual_shares|YEAR=2023;outcome=fatal|crude_share|cipct:2@crude}} | {{trends/annual_shares|YEAR=2023;outcome=fatal|obs_over_expectedB|ci:2}} | {{trends/annual_shares|YEAR=2023;outcome=fatal_cc|crude_share|cipct:2@crude}} | {{trends/annual_shares|YEAR=2023;outcome=fatal_cc|obs_over_expectedB|ci:2}} |
| 2024 | {{trends/annual_shares|YEAR=2024;outcome=fatal|crude_share|cipct:2@crude}} | {{trends/annual_shares|YEAR=2024;outcome=fatal|obs_over_expectedB|ci:2}} | {{trends/annual_shares|YEAR=2024;outcome=fatal_cc|crude_share|cipct:2@crude}} | {{trends/annual_shares|YEAR=2024;outcome=fatal_cc|obs_over_expectedB|ci:2}} |

The 2023–24 excess over the composition-only expectation is significant under the
complete-case outcome but smaller and not significant under NHTSA's imputed outcome; the
intervals overlap and the difference between the two was not tested. The imputed CRSS fatal total matches FARS every
year, but by construction (CRSS weights are calibrated to FARS through the imputed severity),
so this is not independent corroboration (`trends/outcome_definitions_by_year`).

**What FARS shows (observed counts; alcohol estimated by NHTSA's multiple imputation).**
Between 2019 and 2021 fatal crashes rose
{{trends/fars_changes|indicator=fatal_crashes|pct_change_2019_2021|.1f}}%. Crashes with police-recorded speeding rose
{{trends/fars_changes|indicator=speeding_crashes|pct_change_2019_2021|.1f}}% and crashes with a driver at BAC ≥ 0.08
(NHTSA's multiple imputation) {{trends/fars_changes|indicator=bac08_crashes_mi|pct_change_2019_2021|.1f}}%; these
overlapping groups account for {{trends/fars_changes|indicator=speeding_crashes|share_of_total_change_2019_2021|pct:0}}
and {{trends/fars_changes|indicator=bac08_crashes_mi|share_of_total_change_2019_2021|pct:0}} of the rise. Motorcyclist
deaths rose from {{trends/fars_composition_by_year|YEAR=2019|motorcyclist_deaths|,.0f}} (2019) to
{{trends/fars_composition_by_year|YEAR=2021|motorcyclist_deaths|,.0f}} (2021) and peaked at
{{trends/fars_composition_by_year|YEAR=2023|motorcyclist_deaths|,.0f}} in 2023; in 2024
({{trends/fars_composition_by_year|YEAR=2024|motorcyclist_deaths|,.0f}}) they were still above
their 2021 level, while total
deaths fell back from {{trends/fars_changes|indicator=deaths|2021|,.0f}} to {{trends/fars_changes|indicator=deaths|2024|,.0f}}.

*Limitations.* The within-circumstance part is a residual: it contains unmeasured circumstances
(travel speed above all), changes in recording, and changes in which crashes are reported to
the police. The split between composition and within-circumstance depends on the reference
model, and the variance of NHTSA's single imputation of severity is not in the intervals. There
are no exposure, speed or enforcement data, so the rise cannot be attributed to the pandemic or
any other cause.

## 10. Finding 9 — Measurement: what the data can and cannot measure

*Sources: `measurement/*`.*

* **Recorded differently by severity.** Killed drivers are tested for alcohol far more often than
  surviving drivers ({{measurement/alcohol_testing_share|driver_status=killed|share_alcohol_tested|pct:0}} against
  {{measurement/alcohol_testing_share|driver_status=survived|share_alcohol_tested|pct:0}} over 2016–2024,
  `measurement/alcohol_testing_share`), but the *police-recorded* alcohol, drug and distraction fields
  in CRSS are more often unknown in fatal crashes than in less severe ones: alcohol unknown in
  {{measurement/unknown_by_severity|kabco=4;field=alcohol|pct_unknown|.0f}}% of fatal crashes against
  {{measurement/unknown_by_severity|kabco=0;field=alcohol|pct_unknown|.0f}}% of no-injury crashes, drugs
  {{measurement/unknown_by_severity|kabco=4;field=drugs|pct_unknown|.0f}}% against
  {{measurement/unknown_by_severity|kabco=0;field=drugs|pct_unknown|.0f}}%, distraction
  {{measurement/unknown_by_severity|kabco=4;field=distracted|pct_unknown|.0f}}% against
  {{measurement/unknown_by_severity|kabco=0;field=distracted|pct_unknown|.0f}}%
  (`measurement/unknown_by_severity`). What is more complete in severe crashes is toxicology for
  killed drivers and, in FARS, speeding. The assumption in the bias analyses that recording
  sensitivity is higher in fatal crashes is not tested by these data.
* **Alcohol testing is selective.** In 2016, {{measurement/fars_testing|level=national;YEAR=2016;status=killed|pct_alcohol_tested|.0f}}% of
  killed drivers were tested, against {{measurement/fars_testing|level=national;YEAR=2016;status=survived|pct_alcohol_tested|.0f}}% of surviving
  drivers; in 2023 the figures were {{measurement/fars_testing|level=national;YEAR=2023;status=killed|pct_alcohol_tested|.0f}}% and
  {{measurement/fars_testing|level=national;YEAR=2023;status=survived|pct_alcohol_tested|.0f}}% (`measurement/fars_testing`). Part of the apparent
  decline is missing records: the share of killed drivers whose test status is not reported rose
  from {{measurement/fars_testing|level=national;YEAR=2016;status=killed|pct_alcohol_test_status_unknown|.0f}}% to
  {{measurement/fars_testing|level=national;YEAR=2023;status=killed|pct_alcohol_test_status_unknown|.0f}}%, and to
  {{measurement/fars_testing|level=national;YEAR=2024;status=killed|pct_alcohol_test_status_unknown|.0f}}% in 2024, whose toxicology records are
  incomplete in these archives.
  Survivors are tested mainly on suspicion.
* **Police reports miss alcohol in killed drivers.** Among tested FARS drivers with a known
  police report, the report identifies BAC ≥ 0.08 in
  {{measurement/police_vs_bac|driver_status=killed|police_sensitivity_vs_bac08|pct:0}} of killed
  and {{measurement/police_vs_bac|driver_status=survived|police_sensitivity_vs_bac08|pct:0}} of
  surviving drivers. The two groups are not selected alike: surviving drivers were tested mainly on
  suspicion, and only {{measurement/alcohol_testing_share|driver_status=survived|share_in_sensitivity_sample|pct:0}}
  of them (against {{measurement/alcohol_testing_share|driver_status=killed|share_in_sensitivity_sample|pct:0}}
  of killed drivers) are in this comparison. The survivors' sensitivity falls as testing broadens,
  from {{measurement/police_vs_bac_selection|scheme=state-year survivor test-rate tercile;group=low;driver_status=survived|police_sensitivity_vs_bac08|pct:1}}
  in state-years where few survivors were tested to
  {{measurement/police_vs_bac_selection|scheme=state-year survivor test-rate tercile;group=high;driver_status=survived|police_sensitivity_vs_bac08|pct:1}}
  where many were, so the high survivor figure partly reflects who was tested
  (`measurement/police_vs_bac_selection`); the killed drivers' figure ranges
  {{measurement/police_vs_bac_selection|scheme=state-year survivor test-rate tercile;group=high;driver_status=killed|police_sensitivity_vs_bac08|pct:0}}–{{measurement/police_vs_bac_selection|scheme=state-year survivor test-rate tercile;group=middle;driver_status=killed|police_sensitivity_vs_bac08|pct:0}}
  over the same terciles.
* **CRSS alcohol coding broke in 2019.** "Unknown" rose from
  {{measurement/unknown_by_year|field=alcohol;fatal=0;YEAR=2018|pct_unknown|.0f}}% to
  {{measurement/unknown_by_year|field=alcohol;fatal=0;YEAR=2019|pct_unknown|.0f}}% of non-fatal
  crashes in one year. Models use NHTSA's imputed field, and the alcohol association is reported
  under three codings (finding 4).
* **Restraint is self-reported by survivors.** Reported belt use among occupants with known
  status is {{measurement/restraint_reporting|kabco=0|pct_belted_among_known|.1f}}% among the
  uninjured but {{measurement/restraint_reporting|kabco=4|pct_belted_among_known|.1f}}% among the
  killed. Some of that gap is real protection, and some is likely over-reporting by survivors.
* **Drug involvement and distraction cannot be used.** Their "unknown" shares rose sharply in
  2018–2020 (drugs: {{measurement/unknown_by_year|field=drugs;fatal=0;YEAR=2018|pct_unknown|.0f}}% →
  {{measurement/unknown_by_year|field=drugs;fatal=0;YEAR=2020|pct_unknown|.0f}}% of non-fatal
  crashes). Drug testing is selective, and a positive test shows presence, not impairment. No
  severity association or prevalence is reported for drugs or distraction.

## 11. Finding 10 — Burden and what can be said about interventions

*Sources: `burden/attributable_fractions_fatal`, `policy/evidence_ledger`; details in
`reports/policy_analysis.md`.*

Severity-pathway attributable fractions are model-predicted shares of fatal crashes that would
not have been fatal had a circumstance been absent, holding everything else fixed and assuming
the crash still happened:

{{mdtable:burden/attributable_fractions_fatal|outcome=fatal|description:Hypothetical shift:;af:Share of fatal crashes (95% CI):cipct:1;fars_scaled_deaths_per_year:Deaths per year, FARS-scaled:,.0f}}

These are **not** lives saved by any programme. They omit any effect on crash occurrence. They
assume no unmeasured confounding and correct measurement, and they say nothing about whether an
intervention can actually change the circumstance. Under under-recording of speeding in
non-fatal crashes the speeding fraction shrinks, and in the severe cells of the bias grid it
falls to {{burden/bias_sensitivity|shift=speeding_removed|min(af_bias_corrected)|pct:0}} (a negative
fraction means no excess severity remains; `burden/bias_sensitivity`); the alcohol fraction also shrinks there, to
{{burden/bias_sensitivity|shift=alcohol_removed|min(af_bias_corrected)|pct:0}} at its lowest,
although it stays positive. (An earlier version of this report said the alcohol fraction does not
shrink; that was wrong.) Which cells are "plausible" is not defined by these data.

*Period and coding variants* (`burden/attributable_fraction_variants`). The published fractions come
from a 2016–2024 model with NHTSA-imputed alcohol, scaled to 2022–2024 deaths. Refitting on
2022–2024 only and coding alcohol from the police field moves them:

{{mdtable:burden/attributable_fraction_variants|outcome=fatal;shift=speeding_removed~alcohol_removed|alcohol_coding:Alcohol coding:;model_period:Model period:;shift:Hypothetical shift:;af:Share of fatal crashes (95% CI):cipct:1;fars_scaled_deaths_per_year:Deaths per year, FARS-scaled:,.0f}}

The speeding fraction is larger when refitted on the recent years, and the alcohol fraction depends
strongly on the alcohol coding: police-reported alcohol with unknowns dropped gives the largest
fraction and treating unknown as "no" the smallest. The complete-case fraction applies only to
crashes with a known police alcohol field and is not scaled to deaths (its deaths cells are blank),
because applying it to all FARS deaths would extrapolate to the crashes that were dropped. The
confidence intervals cover sampling error only;
they do not include the coding, period or recording-error differences shown here.

## 12. Prediction models

*Sources: `ml/metrics_test`, `ml/paired_differences`, `ml/calibration_by_risk_tier`,
`ml/temporal_stability`, `ml/pattern_confirmation`; full validation report and model cards in
`docs/model_validation.md`. Labels: model-predicted; the metrics are design-weighted estimates
on held-out years.*

Prediction models were trained on 2016–2021, tuned and selected on 2022, and evaluated once on
2023–2024, years used for no modelling choice. Inputs exclude every outcome and outcome-derived count, post-crash consequences (rollover, fire,
towing, hit-and-run) and the calendar year, enforced by the same leakage gate as the statistical models.
Two inputs are nevertheless recorded or judged after the crash: police-judged speeding, which the
registry flags `recorded_after_crash` (`processing/harmonize.py`, with a documented reason for its
use), and NHTSA-imputed alcohol, which may carry information about severity. Dropping both lowers the
boosted model's AUROC by
{{ml/feature_sensitivity|outcome=fatal;stage=pre_crash+circumstance;variant=without speeding and alcohol_im;model=hgb;metric=auroc|diff_vs_main|ci:3@diff_ci}},
so part of the reported discrimination rests on them (`ml/feature_sensitivity`). The models predict
severity given that the police recorded these fields. There are
two input stages: pre-crash circumstances only, and pre-crash circumstances plus crash
configuration. The outcome is a fatal crash among police-reported crashes; prevalence in the
test years was {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=hgb;domain=all;weighting=weighted;metric=prevalence|estimate|cipct:2@ci}}.

* **Discrimination.** With crash configuration, gradient-boosted trees reach an AUROC of
  {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=hgb;domain=all;weighting=weighted;metric=auroc|estimate|ci:3@ci}} against {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=logit_main;domain=all;weighting=weighted;metric=auroc|estimate|ci:3@ci}} for a
  main-effects survey logistic model. From pre-crash circumstances alone the figures are
  {{ml/metrics_test|outcome=fatal;stage=pre_crash;model=hgb;domain=all;weighting=weighted;metric=auroc|estimate|ci:3@ci}} and {{ml/metrics_test|outcome=fatal;stage=pre_crash;model=logit_main;domain=all;weighting=weighted;metric=auroc|estimate|ci:3@ci}}. Adding crash
  configuration raises the boosted model's AUROC by
  {{ml/paired_differences|outcome=fatal;stage=pre_crash+circumstance;model=hgb;comparison=circumstance stage vs pre_crash;metric=auroc|estimate|ci:3@ci}}.
* **Usefulness for picking out fatal crashes is limited.** Average precision is
  {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=hgb;domain=all;weighting=weighted;metric=average_precision|estimate|.3f}} against a base rate of
  {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=hgb;domain=all;weighting=weighted;metric=prevalence|estimate|.3f}}: even among the crashes ranked riskiest, most are not fatal.
* **Calibration.** Overall, observed ÷ predicted fatal crashes is
  {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=hgb;domain=all;weighting=weighted;metric=oe_ratio|estimate|ci:2@ci}}, but this hides miscalibration by risk level: among the half
  of crashes with the lowest predicted risk it is {{ml/calibration_by_risk_tier|outcome=fatal;stage=pre_crash+circumstance;model=hgb;weighting=weighted;risk_tier=lowest 50% of predicted risk|oe_ratio|ci:2@oe}}
  (predictions about twice the observed share), and among the riskiest fifth
  {{ml/calibration_by_risk_tier|outcome=fatal;stage=pre_crash+circumstance;model=hgb;weighting=weighted;risk_tier=highest 20%|oe_ratio|ci:2@oe}}. Logistic models show the same pattern.
* **Drift.** A model trained on 2016–2019 under-predicts fatal crashes in 2020–2022, and by
  2023–2024 observed and predicted no longer differ clearly
  (observed ÷ predicted {{ml/temporal_stability|outcome=fatal;stage=pre_crash+circumstance;model=hgb;eval_year=2020;metric=oe_ratio|estimate|ci:2@ci}} in 2020, {{ml/temporal_stability|outcome=fatal;stage=pre_crash+circumstance;model=hgb;eval_year=2022;metric=oe_ratio|estimate|ci:2@ci}} in 2022, {{ml/temporal_stability|outcome=fatal;stage=pre_crash+circumstance;model=hgb;eval_year=2024;metric=oe_ratio|estimate|ci:2@ci}} in 2024), in line
  with finding 8.
* **Interactions.** The 13 pre-specified interaction terms of finding 5 add almost nothing to
  prediction (AUROC {{ml/paired_differences|outcome=fatal;stage=pre_crash+circumstance;model=logit_interact;comparison=vs logit_main;metric=auroc|estimate|+.3f}}). Screening the boosted
  model on 2016–2022 suggested three further interactions. Tested on 2023–2024, two were confirmed
  (survey-weighted, Holm-adjusted): intersection × head-on collision (ratio of odds ratios
  {{ml/pattern_confirmation|candidate=junction=intersection x crash_type=mv_head_on (refs non_junction, mv_rear_end)|ratio_of_or|.2f}})
  and speeding × angle collision
  ({{ml/pattern_confirmation|candidate=speeding=yes x crash_type=mv_angle (refs no, mv_rear_end)|ratio_of_or|.2f}});
  a 40–45 mph × pedestrian term was not confirmed (Holm p
  {{ml/pattern_confirmation|candidate=speed_limit=40-45 x crash_type=pedestrian (refs 30-35, mv_rear_end)|p_holm|.2f}}).
  All three are exploratory and non-causal.

*Limitations.* Predictive accuracy is not evidence that any input causes fatal outcomes.
Several "unknown" inputs mostly mark hit-and-run crashes, and imputed alcohol may carry
information about severity (`docs/limitations.md` §2–3); excluding the hit-and-run proxies
changes test discrimination only slightly (`docs/model_validation.md`). Intervals reflect
test-set sampling only, not model selection or training-sample variability.

## 13. What is not supported by these data

* Crash rates per mile, trip or driver, and therefore any statement that a factor "causes crashes".
* The effect of speed cameras, sobriety checkpoints, roadside drug tests, belt enforcement or
  campaigns. No such programme is recorded in the archives.
* Drug-impairment prevalence or severity effects, and distraction trends.
* Causal effects of behaviours on severity. All severity associations are conditional on a
  reported crash and on recorded covariates.

## 14. Exploratory vs confirmatory

The pre-specified analyses are: crude versus adjusted severity (RQ1), the 13 registered interaction pairs,
the measurement analyses (RQ3), within-vehicle restraint (RQ6), QIE (RQ7) and burden (RQ9). These are
confirmatory within their stated assumptions, and only these registered families are adjusted for
multiple testing. The post-2020 decomposition (RQ5) and its subgroup table were added after the
descriptive results (research plan change log) and are exploratory, as are the speeding-type split, the
two interaction pairs added at implementation, the three limit-exceedance follow-ups, the
configuration-stratified belt contrasts and the helmet and two-sided misreporting scenarios, which were
motivated by the audit and the red-team review (`docs/red_team_2026-11.md`). Machine-learning importance
rankings are descriptive of the model, not findings about the world.
