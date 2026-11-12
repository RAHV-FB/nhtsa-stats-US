# Alcohol, drugs and restraint use: what can be separated, and what cannot

*Phase 2 report (research question C and D; `docs/research_plan_phase2.md`). Every number is read
from `outputs/tables/drugs/`, `outputs/tables/restraint_behaviour/` and
`outputs/tables/multifactor/` when this report is rendered. Estimate types: **observed** (FARS
census counts and shares), **estimated** (CRSS design-based), **adjusted association**
(model-based, not causal).*

## Summary

1. **Drug involvement is measured selectively, and the selection follows exactly the outcomes
   one would want to compare.** FARS tested
   {{drugs/testing_rates|dimension=all years;survival=killed|share_tested|pct:0}} of killed drivers
   for drugs but {{drugs/testing_rates|dimension=all years;survival=survived|share_tested|pct:0}}
   of surviving drivers; among survivors, testing follows police suspicion
   ({{drugs/testing_rates|dimension=police drug report;level=yes;survival=survived|share_tested|pct:0}}
   tested when police noted drugs vs
   {{drugs/testing_rates|dimension=police drug report;level=no;survival=survived|share_tested|pct:0}}
   when they did not) and injury severity. CRSS contains no drug test results at all.
2. **The police record alcohol and drugs together far more often than toxicology finds them
   together, among the very same drivers.** Take the
   {{drugs/same_driver_cooccurrence|measure=toxicology: BAC >= .08 and any psychoactive drug;survival=killed|n|,.0f}} killed drivers who were drug-tested with a determinate
   result, had a measured BAC and had both police fields known. For them the odds ratio between
   BAC ≥ .08 and a psychoactive drug is {{drugs/same_driver_cooccurrence|measure=toxicology: BAC >= .08 and any psychoactive drug;survival=killed|odds_ratio|ci:2}} by toxicology and
   {{drugs/same_driver_cooccurrence|measure=police report: alcohol and drugs both recorded;survival=killed|odds_ratio|ci:1}} by police report; among the
   {{drugs/same_driver_cooccurrence|measure=toxicology: BAC >= .08 and any psychoactive drug;survival=survived|n|,.0f}} surviving drivers in the same kind of set it is
   {{drugs/same_driver_cooccurrence|measure=toxicology: BAC >= .08 and any psychoactive drug;survival=survived|odds_ratio|ci:2}} by toxicology against
   {{drugs/same_driver_cooccurrence|measure=police report: alcohol and drugs both recorded;survival=survived|odds_ratio|ci:1}} by police report. Pairing one police field with one
   toxicology result gives values in between
   ({{drugs/same_driver_cooccurrence|measure=cross: police alcohol and toxicology drug;survival=killed|odds_ratio|.1f}} and {{drugs/same_driver_cooccurrence|measure=cross: toxicology BAC >= .08 and police drugs;survival=killed|odds_ratio|.1f}} for killed
   drivers), so the excess comes from both fields being police-recorded together. Because the
   comparison uses one driver set, it is not an artefact of comparing differently selected
   drivers. Police-recorded "drug involvement" is therefore partly a marker of an impaired-driving
   investigation, not an independent measurement.
3. **A CRSS severity association for drugs is not identified.** The crude fatal risk ratio of
   police-reported drug involvement in 2019–2024 ranges from
   {{drugs/crss_bounds|period=2019-2024|min(rr)|.1f}} to {{drugs/crss_bounds|period=2019-2024|max(rr)|.0f}}
   depending only on how the
   {{drugs/crss_bounds|period=2019-2024;scenario=all unknown negative|share_unknown|pct:0}} of
   crashes with unknown drug status are allocated. Restricting to non-differential allocations
   (the same rule in fatal and non-fatal crashes) narrows this only to
   {{drugs/crss_bounds_nondifferential|period=2019-2024;row_type=range;allocation=non-differential, equal absolute prevalence e|rr_min|.1f}}–{{drugs/crss_bounds_nondifferential|period=2019-2024;row_type=range;allocation=non-differential, proportional (k_fatal = k_nonfatal = k)|rr_max|.0f}}
   (§4). No defensible point estimate exists, so no drug contribution is reported anywhere in
   Phase 2.
4. **Where both are measured most completely, alcohol is the stronger correlate of dying.** In
   the {{drugs/killed_vs_survived|sample=high-testing states;specification=main effects;term=BAC >= .08 (measured)|n_states|.0f}}
   states that test at least half of both killed and surviving drivers for both alcohol and
   drugs, a driver in a fatal crash with BAC ≥ .08 had
   {{drugs/killed_vs_survived|sample=high-testing states;specification=main effects;term=BAC >= .08 (measured)|odds_ratio|ci:2}}
   times the odds of being the one who died, and a driver with any psychoactive drug
   {{drugs/killed_vs_survived|sample=high-testing states;specification=main effects;term=any psychoactive drug detected|odds_ratio|ci:2}}
   times, mutually adjusted. This is the comparison of the two in this project made where testing is least
   selective (drug-tested: {{drugs/state_testing|high_testing=True|min(drug_tested_killed)|pct:0}}–{{drugs/state_testing|high_testing=True|max(drug_tested_killed)|pct:0}} of killed and {{drugs/state_testing|high_testing=True|min(drug_tested_survived)|pct:0}}–{{drugs/state_testing|high_testing=True|max(drug_tested_survived)|pct:0}} of surviving drivers in these states) — and
   it is conditional on a fatal crash, on being tested, and on four small states.
5. **Restraint acts at a different stage from the behaviours, and its protection depends on
   how the crash happened.** Within the same vehicle, belted front-seat occupants' risk of
   death relative to unbelted ones is
   {{restraint_behaviour/dpc_by_driver_behaviour|split=driver speeding (any);stratum=driver not speeding|rr_belted_vs_unbelted|ci:2@rr}}
   when the driver was not speeding and
   {{restraint_behaviour/dpc_by_driver_behaviour|split=driver speeding (any);stratum=driver speeding|rr_belted_vs_unbelted|ci:2@rr}}
   when the driver was speeding: overall, no difference. But speeding drivers' crashes are
   concentrated in single-vehicle crashes, where belts protect more, and within crash
   configuration belts are *somewhat less* protective with a speeding driver (ratio of
   risk ratios, pooled within crash type,
   {{restraint_behaviour/dpc_contrast_within_configuration|contrast=driver speeding (any) vs not speeding;adjustment=crash type;layer=pooled within layers|ratio_of_rrs|ci:2@ratio}}).
   For a driver at BAC ≥ .08 the overall within-vehicle ratio is slightly lower
   ({{restraint_behaviour/dpc_by_driver_behaviour|split=driver BAC >= .08 (MI);stratum=driver BAC >= .08|rr_belted_vs_unbelted|ci:2@rr}}),
   but within crash configuration the contrast is null
   ({{restraint_behaviour/dpc_contrast_within_configuration|contrast=driver BAC >= .08 (MI) vs BAC < .08;adjustment=crash type;layer=pooled within layers|ratio_of_rrs|ci:2@ratio}}).
   Belt protection also differs by *kind of impact* (single- vs multi-vehicle crash, rollover
   or not). Across crashes, by contrast, the unbelted risk ratio in CRSS falls from
   {{restraint_behaviour/crss_unbelted_nested|step=crude|rr|.0f}} to
   {{restraint_behaviour/crss_unbelted_nested|step=+ crash configuration|rr|.0f}} as crash
   circumstances, the driver's own behaviour and configuration are added: unbelted occupants are
   concentrated in the most violent crashes.

---

## 1. Why these three factors need separate treatment

Alcohol, drugs and belt non-use appear together in official tallies of fatal crashes, but they
are measured differently and plausibly act at different stages (`docs/research_plan_phase2.md`
§2): impairment is a candidate cause of the crash and of its violence (Stages A–B), restraint
of whether an occupant survives the forces of a crash that has happened (Stage C). Two
questions follow. Can alcohol and drug involvement be compared at all, given how each is
measured? And does the restraint association look like an independent Stage-C mechanism, or
like a marker of the crashes in which impaired drivers are involved?

## 2. How drug involvement is measured (observed, FARS drivers 2016–2024)

*Source: `drugs/testing_rates`, `drugs/positivity`, `drugs/selection_gradient`.*

| | Killed drivers | Surviving drivers |
|---|---|---|
| Drivers | {{drugs/testing_rates|dimension=all years;survival=killed|n|,.0f}} | {{drugs/testing_rates|dimension=all years;survival=survived|n|,.0f}} |
| Drug-tested | {{drugs/testing_rates|dimension=all years;survival=killed|share_tested|pct:1}} | {{drugs/testing_rates|dimension=all years;survival=survived|share_tested|pct:1}} |
| BAC-tested | {{drugs/testing_rates|dimension=all years;survival=killed|share_bac_tested|pct:1}} | {{drugs/testing_rates|dimension=all years;survival=survived|share_bac_tested|pct:1}} |
| Drug-tested if police noted drugs | {{drugs/testing_rates|dimension=police drug report;level=yes;survival=killed|share_tested|pct:1}} | {{drugs/testing_rates|dimension=police drug report;level=yes;survival=survived|share_tested|pct:1}} |
| Drug-tested if police noted no drugs | {{drugs/testing_rates|dimension=police drug report;level=no;survival=killed|share_tested|pct:1}} | {{drugs/testing_rates|dimension=police drug report;level=no;survival=survived|share_tested|pct:1}} |
| Drug-tested if BAC ≥ .08 measured | {{drugs/testing_rates|dimension=measured BAC;level=BAC >= .08;survival=killed|share_tested|pct:1}} | {{drugs/testing_rates|dimension=measured BAC;level=BAC >= .08;survival=survived|share_tested|pct:1}} |
| Drug-tested in 2016 / 2024 | {{drugs/testing_rates|dimension=year;level=2016;survival=killed|share_tested|pct:1}} / {{drugs/testing_rates|dimension=year;level=2024;survival=killed|share_tested|pct:1}} | {{drugs/testing_rates|dimension=year;level=2016;survival=survived|share_tested|pct:1}} / {{drugs/testing_rates|dimension=year;level=2024;survival=survived|share_tested|pct:1}} |
| "Unknown if tested", 2024 | {{drugs/testing_rates|dimension=year;level=2024;survival=killed|share_unknown_if_tested|pct:1}} | {{drugs/testing_rates|dimension=year;level=2024;survival=survived|share_unknown_if_tested|pct:1}} |

**Testing follows severity even among survivors.** Surviving drivers with a serious (A)
injury were drug-tested in
{{drugs/testing_rates|dimension=survivor injury severity;level=A (serious)|share_tested|pct:0}}
of cases, uninjured ones in
{{drugs/testing_rates|dimension=survivor injury severity;level=O (none)|share_tested|pct:0}}.
Any comparison of drug prevalence between killed and surviving drivers, or between severity
levels, therefore compares differently selected samples.

**The selection signature.** If testing is targeted at suspected drivers, the share positive
among the tested should fall as testing widens. Grouping states by their survivor drug-test
rate (tertiles), drug positivity among tested survivors is
{{drugs/selection_gradient|survivor_test_tertile=low;survival=survived|drug_positivity|pct:0}}
where only {{drugs/selection_gradient|survivor_test_tertile=low;survival=survived|share_tested|pct:0}}
are tested and
{{drugs/selection_gradient|survivor_test_tertile=high;survival=survived|drug_positivity|pct:0}}
where {{drugs/selection_gradient|survivor_test_tertile=high;survival=survived|share_tested|pct:0}}
are tested. For alcohol the same signature is much stronger (BAC ≥ .08 among BAC-tested
survivors {{drugs/selection_gradient|survivor_test_tertile=low;survival=survived|bac08_among_bac_tested|pct:0}}
vs {{drugs/selection_gradient|survivor_test_tertile=high;survival=survived|bac08_among_bac_tested|pct:0}}),
which is consistent with suspicion-based BAC testing; the weaker drug gradient may also reflect
that drug panels are run when blood is already drawn for alcohol.

**What a positive test means.** Among drug-tested killed drivers with a determinate result,
{{drugs/positivity|period=2016-2021 (3-digit codes);survival=killed|any_psychoactive|pct:1}}
had at least one psychoactive drug detected in 2016–2021 and
{{drugs/positivity|period=2022-2024 (4-digit codes);survival=killed|any_psychoactive|pct:1}}
in 2022–2024 (cannabinoids {{drugs/positivity|period=2022-2024 (4-digit codes);survival=killed|cannabinoid|pct:1}},
stimulants {{drugs/positivity|period=2022-2024 (4-digit codes);survival=killed|stimulant|pct:1}},
narcotics {{drugs/positivity|period=2022-2024 (4-digit codes);survival=killed|narcotic|pct:1}}).
These are **detections, not impairment**: in 2022–2024,
{{drugs/positivity|period=2022-2024 (4-digit codes);survival=killed|carboxy_thc_only_share_of_cannabinoid|pct:0}}
of cannabinoid-positive killed drivers had only the inactive metabolite carboxy-THC, and
{{drugs/positivity|period=2022-2024 (4-digit codes);survival=killed|presumptive_only_share_of_positive|pct:0}}
of positives were positive only through presumptive screens. The coding scheme changed in 2022
(depressants roughly double), so classes are compared only within periods. Positivity among
tested survivors ({{drugs/positivity|period=2022-2024 (4-digit codes);survival=survived|any_psychoactive|pct:1}}
in 2022–2024) is not comparable with killed drivers' because survivors are tested on suspicion.

## 3. Are alcohol and drugs recorded together? (observed)

*Source: `drugs/same_driver_cooccurrence`, `drugs/police_validity`.*

All four rows use one set of drivers per survival status: drug-tested with a determinate
result, BAC measured, and both police fields (alcohol, drugs) known
(`drugs/same_driver_cooccurrence`). "Cross" rows pair one police field with one toxicology
result.

**Killed drivers**

{{mdtable:drugs/same_driver_cooccurrence|survival=killed|measure:Measure:;n:Drivers:,.0f;share_alcohol:Alcohol-positive:pct:0;share_drug:Drug-positive:pct:0;share_both:Both:pct:0;odds_ratio:Odds ratio:ci:2;prevalence_ratio_drug_by_alcohol:Drug prevalence ratio (alcohol-positive vs negative):ci:2@prevalence_ratio}}

**Surviving drivers**

{{mdtable:drugs/same_driver_cooccurrence|survival=survived|measure:Measure:;n:Drivers:,.0f;share_alcohol:Alcohol-positive:pct:0;share_drug:Drug-positive:pct:0;share_both:Both:pct:0;odds_ratio:Odds ratio:ci:2;prevalence_ratio_drug_by_alcohol:Drug prevalence ratio (alcohol-positive vs negative):ci:2@prevalence_ratio}}

*(Woolf intervals ignore the clustering of drivers within crashes; they are indicative.)*

By toxicology, drug detection is only modestly more common among alcohol-positive killed
drivers (prevalence ratio
{{drugs/same_driver_cooccurrence|measure=toxicology: BAC >= .08 and any psychoactive drug;survival=killed|prevalence_ratio_drug_by_alcohol|.2f}}).
By police report, among the same drivers, it is
{{drugs/same_driver_cooccurrence|measure=police report: alcohol and drugs both recorded;survival=killed|prevalence_ratio_drug_by_alcohol|.2f}}
times more common. The police report is also an insensitive
measure: among killed drivers whose toxicology found a psychoactive drug, the police recorded
drug involvement for only
{{drugs/police_validity|survival=killed|sensitivity_unknown_as_no|pct:0}}
({{drugs/police_validity|survival=killed|sensitivity_among_known|pct:0}} of those with a known
police code); {{drugs/police_validity|survival=killed|police_unknown_among_positive|pct:0}} were
coded unknown. *Competing explanations:* (i) police note drugs mainly when an impaired-driving
investigation is already under way; (ii) drivers who combine alcohol with drugs show more
visible impairment. The data cannot distinguish (i) from (ii), but either way the police field
over-states the overlap between alcohol and drugs and cannot serve as an independent drug
measure in models that also contain alcohol.

**Selection caveat for police-versus-BAC checks.** Comparing the police alcohol field with
measured BAC is possible only for drivers who were tested and whose police field is known:
{{measurement/alcohol_testing_share|driver_status=killed|share_in_sensitivity_sample|pct:0}} of
killed and {{measurement/alcohol_testing_share|driver_status=survived|share_in_sensitivity_sample|pct:0}}
of surviving drivers (alcohol-tested:
{{measurement/alcohol_testing_share|driver_status=killed|share_alcohol_tested|pct:0}} and
{{measurement/alcohol_testing_share|driver_status=survived|share_alcohol_tested|pct:0}}).
Police sensitivity against BAC ≥ .08 is
{{measurement/police_vs_bac_selection|scheme=all;driver_status=killed|police_sensitivity_vs_bac08|pct:0}}
for killed and {{measurement/police_vs_bac_selection|scheme=all;driver_status=survived|police_sensitivity_vs_bac08|pct:0}}
for surviving drivers in that sample, but the sample is selected on suspicion. Among surviving
drivers, BAC ≥ .08 prevalence in the tested sample falls from
{{measurement/police_vs_bac_selection|scheme=state-year survivor test-rate tercile;group=low;driver_status=survived|bac08_prevalence|pct:0}}
in the lowest survivor-test-rate tercile to
{{measurement/police_vs_bac_selection|scheme=state-year survivor test-rate tercile;group=high;driver_status=survived|bac08_prevalence|pct:0}}
in the highest, and the share of police-recorded alcohol that BAC confirms (positive predictive
value) from
{{measurement/police_vs_bac_selection|scheme=state-year survivor test-rate tercile;group=low;driver_status=survived|ppv|pct:0}}
to {{measurement/police_vs_bac_selection|scheme=state-year survivor test-rate tercile;group=high;driver_status=survived|ppv|pct:0}}.
The agreement figures therefore describe the tested, suspected-impaired subset and may not hold
for untested drivers.

## 4. Bounds on a drug severity association in CRSS (estimated)

*Source: `drugs/crss_bounds`, `drugs/crss_adjusted`. Population: CRSS police-reported crashes
with known severity; exposure: police-reported drug involvement of any driver.*

CRSS has only the police field. In 2019–2024,
{{drugs/crss_bounds|period=2019-2024;scenario=all unknown negative|unknown_share_fatal|pct:0}}
of fatal and {{drugs/crss_bounds|period=2019-2024;scenario=all unknown negative|unknown_share_nonfatal|pct:0}}
of non-fatal crashes have unknown drug status. The complete-case crude risk ratio is
{{drugs/crss_bounds|period=2019-2024;scenario=all unknown negative|rr_complete_case|.1f}}; if the
unknown crashes were drug-positive at k_f times the known prevalence among fatal crashes and
k_n times that among non-fatal crashes (k from 0 to 3), the risk ratio would lie anywhere
between {{drugs/crss_bounds|period=2019-2024|min(rr)|.1f}} and
{{drugs/crss_bounds|period=2019-2024|max(rr)|.0f}}. Even the two extreme codings — all unknown
negative ({{drugs/crss_bounds|period=2019-2024;scenario=all unknown negative|rr|.1f}}) and all
unknown positive ({{drugs/crss_bounds|period=2019-2024;scenario=all unknown positive|rr|.1f}}) —
differ widely. Model-A adjusted ratios are
{{drugs/crss_adjusted|period=2019-2024;coding=complete case|adj_rr|ci:2}} (complete case) and
{{drugs/crss_adjusted|period=2019-2024;coding=unknown as no|adj_rr|ci:2}} (unknown as no); their
narrow intervals reflect sampling error only and say nothing about which allocation of the
unknowns is right. Because testing and recording depend on severity (§2), the plausible
scenarios are those with k_f ≠ k_n, which is exactly where the bounds are widest.

**Non-differential allocations.** If unknown drug status is allocated by the same rule in fatal
and non-fatal crashes (`drugs/crss_bounds_nondifferential`), the range narrows but does not
close: proportional to the known prevalence (the same multiplier k in both), the crude ratio
lies between
{{drugs/crss_bounds_nondifferential|period=2019-2024;row_type=range;allocation=non-differential, proportional (k_fatal = k_nonfatal = k)|rr_min|.1f}} and
{{drugs/crss_bounds_nondifferential|period=2019-2024;row_type=range;allocation=non-differential, proportional (k_fatal = k_nonfatal = k)|rr_max|.1f}};
with the same absolute prevalence among unknown fatal and non-fatal crashes, between
{{drugs/crss_bounds_nondifferential|period=2019-2024;row_type=range;allocation=non-differential, equal absolute prevalence e|rr_min|.1f}} and
{{drugs/crss_bounds_nondifferential|period=2019-2024;row_type=range;allocation=non-differential, equal absolute prevalence e|rr_max|.1f}};
the extreme-corner grid above spans
{{drugs/crss_bounds_nondifferential|period=2019-2024;row_type=range;allocation=published grid (k_fatal, k_nonfatal in 0-3, any combination)|rr_min|.1f}}–{{drugs/crss_bounds_nondifferential|period=2019-2024;row_type=range;allocation=published grid (k_fatal, k_nonfatal in 0-3, any combination)|rr_max|.0f}}.
The non-differential values are **point estimates of assumed scenarios**: they carry no
sampling interval and no uncertainty about which scenario holds, and non-differential
allocation is itself implausible when testing and recording depend on severity. They show that
the conclusion does not rest on the extreme corners alone, not that a non-differential
association is the right one.

**Two drug definitions.** The reports use two different definitions of a drug-involved fatal
crash (`drugs/drug_definition_reconciliation`). Definition A, the police crash-level drug field
recorded as yes, covers
{{drugs/drug_definition_reconciliation|row_type=definition;definition=A: police crash-level drugs field = yes|deaths|,.0f}}
deaths in 2016–2024; definition B, any driver drug-positive on toxicology, covers
{{drugs/drug_definition_reconciliation|row_type=definition;definition=B: any driver drug-positive on toxicology|deaths|,.0f}}.
Both hold in {{drugs/drug_definition_reconciliation|row_type=overlap;definition=A and B|deaths|,.0f}}
deaths; A without B accounts for
{{drugs/drug_definition_reconciliation|row_type=overlap;definition=A not B|deaths|,.0f}} and B
without A for {{drugs/drug_definition_reconciliation|row_type=overlap;definition=B not A|deaths|,.0f}}.
A is a police judgement that exists in CRSS as well; B requires toxicology and exists only in
FARS, and many deaths fall in crashes where no driver is positive but some driver is untested or
indeterminate, so B is a floor. Neither is a measure of impairment and
the two cannot be substituted for one another.

**Verdict.** No drug severity association, drug attributable fraction or drug position in any
ranking is reported in Phase 2. This is a finding, not an omission.

## 5. A restricted comparison of alcohol and drugs (FARS, minimal selection)

*Source: `drugs/killed_vs_survived`, `drugs/state_testing`. Population: drivers in fatal
crashes tested for both alcohol and drugs; outcome: the driver died (vs survived).
Crash-clustered sandwich CIs. Adjusted for age, sex, vehicle type, crash configuration, night
and period.*

| Sample | BAC ≥ .08 | Any psychoactive drug | Alcohol × drug (product) | Drivers |
|---|---|---|---|---|
| States testing ≥ 50% of killed and surviving drivers for both | {{drugs/killed_vs_survived|sample=high-testing states;specification=main effects;term=BAC >= .08 (measured)|odds_ratio|ci:2}} | {{drugs/killed_vs_survived|sample=high-testing states;specification=main effects;term=any psychoactive drug detected|odds_ratio|ci:2}} | {{drugs/killed_vs_survived|sample=high-testing states;specification=with alcohol x drug;term=alcohol x drug (product term)|odds_ratio|ci:2}} | {{drugs/killed_vs_survived|sample=high-testing states;specification=main effects;term=BAC >= .08 (measured)|n_drivers|,.0f}} |
| All states (selectively tested survivors) | {{drugs/killed_vs_survived|sample=all states;specification=main effects;term=BAC >= .08 (measured)|odds_ratio|ci:2}} | {{drugs/killed_vs_survived|sample=all states;specification=main effects;term=any psychoactive drug detected|odds_ratio|ci:2}} | {{drugs/killed_vs_survived|sample=all states;specification=with alcohol x drug;term=alcohol x drug (product term)|odds_ratio|ci:2}} | {{drugs/killed_vs_survived|sample=all states;specification=main effects;term=BAC >= .08 (measured)|n_drivers|,.0f}} |

*What it estimates.* Among drivers involved in a crash in which somebody died, whether the
driver was the one who died. This mixes Stage B (impaired drivers' crashes are more often
single-vehicle and more violent for themselves) with Stage C (survivability), and conditions on
a fatal crash. It is not a severity effect and says nothing about crash occurrence.

*What it shows.* Where survivors are tested almost as routinely as the dead, the alcohol
association is larger than nationally (selective testing of survivors biases the national
comparison toward the null, because tested survivors are enriched for suspected impairment).
Drug detection is also associated with dying, less strongly than alcohol, and the
combination is sub-multiplicative. *Limitations:* four states with small samples; drug
detection is not impairment; the high-testing states are rural and not representative.

**Answer to C.** Alcohol and drugs can be separated only in a narrow, explicitly selected
population (tested drivers in fatal crashes in high-testing states), where alcohol is the
stronger correlate of dying. In the general population of crashes, selective testing and the
police tendency to record the two together prevent any defensible comparison; police-recorded
drug involvement should not be used as an adjustment variable for alcohol or speeding.

## 6. Restraint: Stage C, with protection that depends on the kind of impact and (somewhat) on speeding

*Sources: `restraint_behaviour/dpc_by_driver_behaviour` (FARS double-pair comparison,
crash-cluster bootstrap CIs), `restraint_behaviour/crss_unbelted_nested` (CRSS, design-based).*

**Within the same vehicle** (driver and right-front passenger; risk ratio of death, belted vs
unbelted):

{{mdtable:restraint_behaviour/dpc_by_driver_behaviour||split:Split:;stratum:Stratum:;n_pairs:Pairs:,.0f;rr_belted_vs_unbelted:RR belted vs unbelted:ci:2@rr;heterogeneity_ratio:Ratio of RRs (2nd vs 1st stratum):.2f;heterogeneity_p:p (heterogeneity):.2g}}

Overall, the within-vehicle belt risk ratio is the same whether or not the driver was
speeding (and similar with exceedance), and slightly lower with a driver at BAC ≥ .08
(p {{restraint_behaviour/dpc_by_driver_behaviour|split=driver BAC >= .08 (MI);stratum=driver BAC >= .08|heterogeneity_p|.2f}}).
That overall comparison does not hold crash configuration fixed, and the configuration differs
between the groups. Within crash configuration the picture changes
(`restraint_behaviour/dpc_contrast_within_configuration`; ratio of the belt risk ratio with the
behaviour to that without it, pooled across layers, >1 means belts protect less):

| Driver behaviour | Layers | Ratio of RRs (95% CI) |
|---|---|---|
| Speeding (any), by single/multi-vehicle | single vs multi-vehicle | {{restraint_behaviour/dpc_contrast_within_configuration|contrast=driver speeding (any) vs not speeding;adjustment=single vs multi-vehicle crash;layer=pooled within layers|ratio_of_rrs|ci:2@ratio}} |
| Speeding (any), by rollover | rollover vs not | {{restraint_behaviour/dpc_contrast_within_configuration|contrast=driver speeding (any) vs not speeding;adjustment=rollover vs no rollover;layer=pooled within layers|ratio_of_rrs|ci:2@ratio}} |
| Speeding (any), by crash type | crash type | {{restraint_behaviour/dpc_contrast_within_configuration|contrast=driver speeding (any) vs not speeding;adjustment=crash type;layer=pooled within layers|ratio_of_rrs|ci:2@ratio}} |
| Exceeded limit / racing, by crash type | crash type | {{restraint_behaviour/dpc_contrast_within_configuration|contrast=driver exceeded limit / racing vs not speeding;adjustment=crash type;layer=pooled within layers|ratio_of_rrs|ci:2@ratio}} |
| BAC ≥ .08, by single/multi-vehicle | single vs multi-vehicle | {{restraint_behaviour/dpc_contrast_within_configuration|contrast=driver BAC >= .08 (MI) vs BAC < .08;adjustment=single vs multi-vehicle crash;layer=pooled within layers|ratio_of_rrs|ci:2@ratio}} |
| BAC ≥ .08, by crash type | crash type | {{restraint_behaviour/dpc_contrast_within_configuration|contrast=driver BAC >= .08 (MI) vs BAC < .08;adjustment=crash type;layer=pooled within layers|ratio_of_rrs|ci:2@ratio}} |

So the earlier statement that the belt effect does not vary with the driver's speeding does not
survive: within crash configuration belts are somewhat less protective when the driver was
speeding, while the BAC contrast is null. Belt protection also differs by the *kind of impact*.
By crash type (FARS, within-vehicle double-pair comparison, `matched/belt_by_crash_type`):

{{mdtable:matched/belt_by_crash_type|partition=crash type~vehicle rollover|stratum:Stratum:;dpc_n_pairs:Pairs:,.0f;dpc_rr:RR belted vs unbelted:.2f;dpc_reduction:Risk reduction:cipct:0@dpc_reduction}}

Belts are associated with a larger reduction in single-vehicle crashes
({{restraint_behaviour/dpc_by_driver_behaviour|split=vehicles in crash;stratum=single vehicle|reduction|pct:0}})
than in multi-vehicle crashes ({{restraint_behaviour/dpc_by_driver_behaviour|split=vehicles in crash;stratum=multi-vehicle|reduction|pct:0}}),
and the reduction is largest when the vehicle rolled over
({{matched/belt_by_crash_type|stratum=vehicle rolled over (any crash type)|dpc_reduction|pct:0}}
vs {{matched/belt_by_crash_type|stratum=vehicle did not roll over|dpc_reduction|pct:0}}), and
smallest in multi-vehicle angle and head-on crashes, consistent with ejection in rollovers and
roadway departures being largely prevented by belts. A single pooled belt estimate therefore
averages over crash types in which the protection differs substantially.

**Across crashes** (CRSS light-vehicle occupants aged 15+; same sample at every step):

{{mdtable:restraint_behaviour/crss_unbelted_nested||step:Model:;rr:Unbelted vs belted RR:ci:1;rd:Risk difference:ci:4;share_logrr_retained:Share of crude log-RR retained:.2f}}

The across-crash risk ratio falls from
{{restraint_behaviour/crss_unbelted_nested|step=crude|rr|.0f}} to
{{restraint_behaviour/crss_unbelted_nested|step=+ driver's own speeding and alcohol|rr|.0f}}
once crash circumstances and the driver's own speeding and alcohol are held fixed (the
log-RR retains {{restraint_behaviour/crss_unbelted_nested|step=+ driver's own speeding and alcohol|share_logrr_retained|pct:0}}),
and to {{restraint_behaviour/crss_unbelted_nested|step=+ crash configuration|rr|.0f}} with crash
configuration. Unbelted occupants
are disproportionately in crashes with impaired or speeding drivers and in more violent crash
types. Even fully adjusted, the across-crash ratio is several times the within-vehicle ratio
(about {{restraint_behaviour/dpc_by_driver_behaviour|split=all|rr_belted_vs_unbelted|.2f}},
i.e. a large within-vehicle protective association), which is what one expects if unmeasured crash
energy and, possibly, survivor over-reporting of belt use inflate across-crash comparisons.

*Competing explanations.* (i) "Belt non-use only marks drunk or speeding drivers" — the
within-vehicle comparison holds the driver and crash fixed, and the overall belt risk ratio
is similar with and without a speeding or drinking driver; within crash configuration the
speeding contrast is modest and in the direction of *less* protection, which is not what a pure
marker would produce. (ii) "Survivors over-report belt use" — not testable from the data
directly, but quantifiable. Phase 1 showed that the within-vehicle reduction would fall from
{{matched/belt_effect|estimand=fatality_risk_reduction_belt_given_fatal_crash|estimate|pct:0}} to
{{matched/belt_effect|estimand=fatality_risk_reduction_belt_given_fatal_crash_misreport_f10|estimate|pct:0}}
if 10% of 'belted' survivors were unbelted (`matched/belt_effect`). The error can run in both
directions: a fraction g of deaths coded unbelted may truly have been belted. Crossing the two
(`matched/belt_misreporting_two_sided_dpc`):

{{mdtable:matched/belt_misreporting_two_sided_dpc||survivor_misreport_f:Belted survivors truly unbelted (f):.2f;death_misreport_g:Unbelted deaths truly belted (g):.2f;rr_x1_vs_x0:RR belted vs unbelted:ci:2@rr;reduction_1_minus_rr:Risk reduction:cipct:0@reduction}}

The belt effect is estimated to disappear if about
{{matched/belt_misreporting_two_sided_dpc|survivor_misreport_f=0;death_misreport_g=0|tipping_f_given_g|pct:0}}
of 'belted' survivors were truly unbelted with no reverse error, and reverse error (g) moves the
tipping fraction down
({{matched/belt_misreporting_two_sided_dpc|survivor_misreport_f=0;death_misreport_g=0.1|tipping_f_given_g|pct:0}}
at g = {{matched/belt_misreporting_two_sided_dpc|survivor_misreport_f=0;death_misreport_g=0.1|death_misreport_g|.2f}}).
The direction of the association is robust to modest misreporting; its size is not, and a
survivor misreporting fraction at the tipping value above would remove it entirely.

**Helmets.** The same design applied to motorcycle riders (operator and passenger on the same
motorcycle) rests on very few informative pairs. Of
{{matched/helmet_pair_coverage|metric=unhelmeted_motorcyclist_deaths|count|,.0f}} unhelmeted
motorcyclist deaths, only {{matched/helmet_pair_coverage|metric=unhelmeted_deaths_in_pair_design|share|pct:0}}
occurred on two-occupant motorcycles with complete information, and
{{matched/helmet_pair_coverage|metric=unhelmeted_deaths_in_informative_pairs|share|pct:1}}
in pairs that identify the matched-pair odds ratio; most are on single-rider motorcycles
({{matched/helmet_pair_coverage|metric=unhelmeted_deaths_single_rider_motorcycle|share|pct:0}}),
where no within-motorcycle comparison exists. The helmeted-versus-unhelmeted risk ratio is
{{matched/helmet_misreporting_dpc|survivor_misreport_f=0;death_misreport_g=0|rr_x1_vs_x0|ci:2@rr}}
as recorded, but it is far more fragile to misreporting than the belt estimate: with 5% of
'helmeted' survivors truly unhelmeted it is
{{matched/helmet_misreporting_dpc|survivor_misreport_f=0.05;death_misreport_g=0|rr_x1_vs_x0|ci:2@rr}}
and it reaches one at a misreporting fraction of
{{matched/helmet_misreporting_dpc|survivor_misreport_f=0;death_misreport_g=0|tipping_f_given_g|pct:0}}.
The helmet association should be read as suggestive only.

**Answer to D.** Among comparable occupants (same vehicle, same crash), belt use is associated
with roughly a two-thirds lower risk of death given a fatal crash. Overall the association is
the same with and without a speeding driver and slightly larger with a drinking driver; within
crash configuration it is somewhat smaller with a speeding driver and unchanged with a drinking
one. It is larger in single-vehicle crashes and in rollovers than in multi-vehicle crashes.
Across crashes the unbelted association is far larger and shrinks substantially under
adjustment, so across-crash ratios should not be read as belt effectiveness. The size of the
within-vehicle association is sensitive to misreporting of belt use in either direction.

## 7. Implications for official statistics

* "Drug-involved" fatal-crash counts depend on who is tested; they rise with testing and
  cannot be compared across states, years (2022 code change, 2024 pending toxicology) or with
  alcohol counts.
* "Alcohol and drugs" combined categories built from police reports overstate how often the
  two coincide relative to toxicology.
* "Unrestrained occupant deaths" are deaths of occupants who were unbelted — not deaths caused
  by being unbelted. Within-vehicle evidence supports a large protective association that
  varies with the kind of crash (and somewhat with the driver's speeding) and is sensitive to
  misreporting of belt use; across-crash counts mix it with crash violence.

## 8. What stronger evidence would require

Routine toxicology for every driver in a sample of crashes of all severities (not only fatal),
with impairment-relevant drug concentrations; measured belt use independent of survivors'
statements (e.g. event data recorders); and linked exposure data for crash occurrence.
