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
   together.** Among tested killed drivers, the odds ratio between BAC ≥ .08 and a psychoactive
   drug is {{drugs/co_occurrence|measure=toxicology: BAC >= .08 and any psychoactive drug;survival=killed|odds_ratio|ci:2}};
   in police reports for the same population it is
   {{drugs/co_occurrence|measure=police report: alcohol and drugs both recorded;survival=killed|odds_ratio|ci:1}},
   and among survivors {{drugs/co_occurrence|measure=police report: alcohol and drugs both recorded;survival=survived|odds_ratio|ci:1}}
   against {{drugs/co_occurrence|measure=toxicology: BAC >= .08 and any psychoactive drug;survival=survived|odds_ratio|ci:2}}.
   Police-recorded "drug involvement" is therefore partly a marker of an impaired-driving
   investigation, not an independent measurement.
3. **A CRSS severity association for drugs is not identified.** The crude fatal risk ratio of
   police-reported drug involvement in 2019–2024 ranges from
   {{drugs/crss_bounds|period=2019-2024|min(rr)|.1f}} to {{drugs/crss_bounds|period=2019-2024|max(rr)|.0f}}
   depending only on how the
   {{drugs/crss_bounds|period=2019-2024;scenario=all unknown negative|share_unknown|pct:0}} of
   crashes with unknown drug status are allocated. No defensible point estimate exists, so no
   drug contribution is reported anywhere in Phase 2.
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
5. **Restraint acts at a different stage from the behaviours.** Within the same vehicle, belted
   front-seat occupants' risk of death relative to unbelted ones is
   {{restraint_behaviour/dpc_by_driver_behaviour|split=driver speeding (any);stratum=driver not speeding|rr_belted_vs_unbelted|ci:2@rr}}
   when the driver was not speeding and
   {{restraint_behaviour/dpc_by_driver_behaviour|split=driver speeding (any);stratum=driver speeding|rr_belted_vs_unbelted|ci:2@rr}}
   when the driver was speeding — the driver's speeding does not change it — and only slightly
   more protective with a driver at BAC ≥ .08
   ({{restraint_behaviour/dpc_by_driver_behaviour|split=driver BAC >= .08 (MI);stratum=driver BAC >= .08|rr_belted_vs_unbelted|ci:2@rr}}).
   It does differ by *kind of impact* (single- vs multi-vehicle crash).
   Across crashes, by contrast, the unbelted risk ratio in CRSS falls from
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

*Source: `drugs/co_occurrence`, `drugs/police_validity`.*

| Population | Measure | n | Drug among alcohol-positive | Drug among alcohol-negative | Odds ratio |
|---|---|---|---|---|---|
| Killed drivers tested for both | toxicology | {{drugs/co_occurrence|measure=toxicology: BAC >= .08 and any psychoactive drug;survival=killed|n|,.0f}} | {{drugs/co_occurrence|measure=toxicology: BAC >= .08 and any psychoactive drug;survival=killed|share_drug_among_alcohol|pct:0}} | {{drugs/co_occurrence|measure=toxicology: BAC >= .08 and any psychoactive drug;survival=killed|share_drug_among_no_alcohol|pct:0}} | {{drugs/co_occurrence|measure=toxicology: BAC >= .08 and any psychoactive drug;survival=killed|odds_ratio|ci:2}} |
| Killed drivers, both police fields known | police report | {{drugs/co_occurrence|measure=police report: alcohol and drugs both recorded;survival=killed|n|,.0f}} | {{drugs/co_occurrence|measure=police report: alcohol and drugs both recorded;survival=killed|share_drug_among_alcohol|pct:0}} | {{drugs/co_occurrence|measure=police report: alcohol and drugs both recorded;survival=killed|share_drug_among_no_alcohol|pct:0}} | {{drugs/co_occurrence|measure=police report: alcohol and drugs both recorded;survival=killed|odds_ratio|ci:2}} |
| Surviving drivers tested for both | toxicology | {{drugs/co_occurrence|measure=toxicology: BAC >= .08 and any psychoactive drug;survival=survived|n|,.0f}} | {{drugs/co_occurrence|measure=toxicology: BAC >= .08 and any psychoactive drug;survival=survived|share_drug_among_alcohol|pct:0}} | {{drugs/co_occurrence|measure=toxicology: BAC >= .08 and any psychoactive drug;survival=survived|share_drug_among_no_alcohol|pct:0}} | {{drugs/co_occurrence|measure=toxicology: BAC >= .08 and any psychoactive drug;survival=survived|odds_ratio|ci:2}} |
| Surviving drivers, both police fields known | police report | {{drugs/co_occurrence|measure=police report: alcohol and drugs both recorded;survival=survived|n|,.0f}} | {{drugs/co_occurrence|measure=police report: alcohol and drugs both recorded;survival=survived|share_drug_among_alcohol|pct:0}} | {{drugs/co_occurrence|measure=police report: alcohol and drugs both recorded;survival=survived|share_drug_among_no_alcohol|pct:0}} | {{drugs/co_occurrence|measure=police report: alcohol and drugs both recorded;survival=survived|odds_ratio|ci:2}} |

*(Woolf intervals ignore the clustering of drivers within crashes; they are indicative.)*

By toxicology, drug detection is only modestly more common among alcohol-positive drivers. By
police report, it is several times more common. The police report is also an insensitive
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
differ by a factor of three. Model-A adjusted ratios are
{{drugs/crss_adjusted|period=2019-2024;coding=complete case|adj_rr|ci:2}} (complete case) and
{{drugs/crss_adjusted|period=2019-2024;coding=unknown as no|adj_rr|ci:2}} (unknown as no); their
narrow intervals reflect sampling error only and say nothing about which allocation of the
unknowns is right. Because testing and recording depend on severity (§2), the plausible
scenarios are those with k_f ≠ k_n, which is exactly where the bounds are widest.

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

## 6. Restraint: Stage C, independent of how the crash happened

*Sources: `restraint_behaviour/dpc_by_driver_behaviour` (FARS double-pair comparison,
crash-cluster bootstrap CIs), `restraint_behaviour/crss_unbelted_nested` (CRSS, design-based).*

**Within the same vehicle** (driver and right-front passenger; risk ratio of death, belted vs
unbelted):

{{mdtable:restraint_behaviour/dpc_by_driver_behaviour||split:Split:;stratum:Stratum:;n_pairs:Pairs:,.0f;rr_belted_vs_unbelted:RR belted vs unbelted:ci:2@rr;heterogeneity_ratio:Ratio of RRs (2nd vs 1st stratum):.2f;heterogeneity_p:p (heterogeneity):.2g}}

The within-vehicle belt risk ratio is the same whether or not the driver was speeding or had
exceeded the limit, and only slightly more protective when the driver had a BAC ≥ .08
(p {{restraint_behaviour/dpc_by_driver_behaviour|split=driver BAC >= .08 (MI);stratum=driver BAC >= .08|heterogeneity_p|.2f}}).
It *does* differ by crash type: belts are associated with a larger reduction in single-vehicle
crashes ({{restraint_behaviour/dpc_by_driver_behaviour|split=vehicles in crash;stratum=single vehicle|reduction|pct:0}})
than in multi-vehicle crashes ({{restraint_behaviour/dpc_by_driver_behaviour|split=vehicles in crash;stratum=multi-vehicle|reduction|pct:0}}),
consistent with ejection in rollovers and roadway departures being largely prevented by belts.
The mechanism the data support is therefore: belt protection depends on the *kind of impact*,
not on the behaviour that led to it.

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
i.e. unbelted about three times the risk), which is what one expects if unmeasured crash
energy and, possibly, survivor over-reporting of belt use inflate across-crash comparisons.

*Competing explanations tested.* (i) "Belt non-use only marks drunk or speeding drivers" —
rejected for the within-vehicle comparison, which holds the driver and crash fixed and does not
vary with the driver's behaviour. (ii) "Survivors over-report belt use" — not testable here;
Phase 1 showed the within-vehicle reduction would fall from
{{matched/belt_effect|estimand=fatality_risk_reduction_belt_given_fatal_crash|estimate|pct:0}} to
{{matched/belt_effect|estimand=fatality_risk_reduction_belt_given_fatal_crash_misreport_f10|estimate|pct:0}}
if 10% of 'belted' survivors were unbelted (`matched/belt_effect`). The direction is robust; the size is not.

**Answer to D.** Among comparable occupants (same vehicle, same crash), belt use is associated
with roughly a two-thirds lower risk of death given a fatal crash, and this association is
unchanged by the driver's speeding and only slightly larger with a drinking driver; it is
larger in single-vehicle than in multi-vehicle crashes. Across crashes the unbelted
association is far larger and shrinks substantially under adjustment, so across-crash ratios
should not be read as belt effectiveness.

## 7. Implications for official statistics

* "Drug-involved" fatal-crash counts depend on who is tested; they rise with testing and
  cannot be compared across states, years (2022 code change, 2024 pending toxicology) or with
  alcohol counts.
* "Alcohol and drugs" combined categories built from police reports overstate how often the
  two coincide relative to toxicology.
* "Unrestrained occupant deaths" are deaths of occupants who were unbelted — not deaths caused
  by being unbelted. Within-vehicle evidence supports a large protective association that is
  independent of driver behaviour; across-crash counts mix it with crash violence.

## 8. What stronger evidence would require

Routine toxicology for every driver in a sample of crashes of all severities (not only fatal),
with impairment-relevant drug concentrations; measured belt use independent of survivors'
statements (e.g. event data recorders); and linked exposure data for crash occurrence.
