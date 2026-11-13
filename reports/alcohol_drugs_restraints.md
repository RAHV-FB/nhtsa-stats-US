<!-- Generated from reports/templates/alcohol_drugs_restraints.md by `nhtsa analyze report`; every number is looked up in outputs/tables. Edit the template, not this file. -->

# Alcohol, drugs and restraint use: what can be separated, and what cannot

*Phase 2 report (research question C and D; `docs/research_plan_phase2.md`). Every number is read
from `outputs/tables/drugs/`, `outputs/tables/restraint_behaviour/` and
`outputs/tables/multifactor/` when this report is rendered. Estimate types: **observed** (FARS
census counts and shares), **estimated** (CRSS design-based), **adjusted association**
(model-based, not causal).*

## Summary

1. **Drug involvement is measured selectively, and the selection follows exactly the outcomes
   one would want to compare.** FARS tested
   62% of killed drivers
   for drugs but 19%
   of surviving drivers; among survivors, testing follows police suspicion
   (83%
   tested when police noted drugs vs
   18%
   when they did not) and injury severity. CRSS contains no drug test results at all.
2. **The police record alcohol and drugs together far more often than toxicology finds them
   together, among the very same drivers.** Take the
   68,755 killed drivers who were drug-tested with a determinate
   result, had a measured BAC and had both police fields known. For them the odds ratio between
   BAC ≥ .08 and a psychoactive drug is 1.44 (1.40–1.49) by toxicology and
   3.5 (3.4–3.6) by police report; among the
   31,870 surviving drivers in the same kind of set it is
   2.06 (1.93–2.19) by toxicology against
   4.1 (3.9–4.4) by police report. Pairing one police field with one
   toxicology result gives values in between
   (1.7 and 1.9 for killed
   drivers), so the excess comes from both fields being police-recorded together. Because the
   comparison uses one driver set, it is not an artefact of comparing differently selected
   drivers. Police-recorded "drug involvement" is therefore partly a marker of an impaired-driving
   investigation, not an independent measurement.
3. **A CRSS severity association for drugs is not identified.** The crude fatal risk ratio of
   police-reported drug involvement in 2019–2024 ranges from
   1.7 to 73
   depending only on how the
   54% of
   crashes with unknown drug status are allocated. Restricting to non-differential allocations
   (the same rule in fatal and non-fatal crashes) narrows this only to
   1.7–19
   (§4). No defensible point estimate exists, so no drug contribution is reported anywhere in
   Phase 2.
4. **Where both are measured most completely, alcohol is the stronger correlate of dying.** In
   the 4
   states that test at least half of both killed and surviving drivers for both alcohol and
   drugs, a driver in a fatal crash with BAC ≥ .08 had
   2.16 (1.82–2.57)
   times the odds of being the one who died, and a driver with any psychoactive drug
   1.28 (1.14–1.45)
   times, mutually adjusted. This is the comparison of the two in this project made where testing is least
   selective (drug-tested: 69%–88% of killed and 51%–80% of surviving drivers in these states) — and
   it is conditional on a fatal crash, on being tested, and on four small states.
5. **Restraint acts at a different stage from the behaviours, and its protection depends on
   how the crash happened.** Within the same vehicle, belted front-seat occupants' risk of
   death relative to unbelted ones is
   0.34 (0.32–0.35)
   when the driver was not speeding and
   0.34 (0.32–0.36)
   when the driver was speeding: overall, no detectable difference (p = 0.96). But speeding drivers' crashes are
   concentrated in single-vehicle crashes, where belts protect more, and within crash
   configuration belts are *somewhat less* protective with a speeding driver (exploratory
   follow-up; ratio of risk ratios 1.10 to 1.23 across four layering schemes, 1.23 (1.13–1.34) with single/multi-vehicle
   and rollover crossed).
   For a driver at BAC ≥ .08 the overall within-vehicle ratio is slightly lower
   (0.32 (0.30–0.34)),
   but within crash configuration there is no detectable contrast (p = 0.95;
   1.00 (0.91–1.09)).
   Belt protection also differs by *kind of impact* (single- vs multi-vehicle crash, rollover
   or not). Across crashes, by contrast, the unbelted risk ratio in CRSS falls from
   46 to
   19 as crash
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
| Drivers | 222,856 | 264,519 |
| Drug-tested | 61.6% | 18.5% |
| BAC-tested | 65.2% | 23.0% |
| Drug-tested if police noted drugs | 94.0% | 82.6% |
| Drug-tested if police noted no drugs | 58.2% | 17.7% |
| Drug-tested if BAC ≥ .08 measured | 85.4% | 57.3% |
| Drug-tested in 2016 / 2024 | 63.7% / 55.1% | 20.8% / 14.7% |
| "Unknown if tested", 2024 | 21.7% | 4.9% |

**Testing follows severity even among survivors.** Surviving drivers with a serious (A)
injury were drug-tested in
26%
of cases, uninjured ones in
16%.
Any comparison of drug prevalence between killed and surviving drivers, or between severity
levels, therefore compares differently selected samples.

**The selection signature.** If testing is targeted at suspected drivers, the share positive
among the tested should fall as testing widens. Grouping states by their survivor drug-test
rate (tertiles), drug positivity among tested survivors is
42%
where only 9%
are tested and
37%
where 39%
are tested. For alcohol the same signature is much stronger (BAC ≥ .08 among BAC-tested
survivors 27%
vs 12%),
which is consistent with suspicion-based BAC testing; the weaker drug gradient may also reflect
that drug panels are run when blood is already drawn for alcohol.

**What a positive test means.** Among drug-tested killed drivers with a determinate result,
46.3%
had at least one psychoactive drug detected in 2016–2021 and
52.0%
in 2022–2024 (cannabinoids 26.9%,
stimulants 18.0%,
narcotics 10.0%).
These are **detections, not impairment**: in 2022–2024,
8%
of cannabinoid-positive killed drivers had only the inactive metabolite carboxy-THC, and
6%
of positives were positive only through presumptive screens. The coding scheme changed in 2022
(depressants roughly double), so classes are compared only within periods. Positivity among
tested survivors (41.1%
in 2022–2024) is not comparable with killed drivers' because survivors are tested on suspicion.

## 3. Are alcohol and drugs recorded together? (observed)

*Source: `drugs/same_driver_cooccurrence`, `drugs/police_validity`.*

All four rows use one set of drivers per survival status: drug-tested with a determinate
result, BAC measured, and both police fields (alcohol, drugs) known
(`drugs/same_driver_cooccurrence`). "Cross" rows pair one police field with one toxicology
result.

**Killed drivers**

| Measure | Drivers | Alcohol-positive | Drug-positive | Both | Odds ratio | Drug prevalence ratio (alcohol-positive vs negative) |
|---|---|---|---|---|---|---|
| toxicology: BAC >= .08 and any psychoactive drug | 68,755 | 31% | 46% | 16% | 1.44 (1.40–1.49) | 1.21 (1.19–1.23) |
| police report: alcohol and drugs both recorded | 68,755 | 32% | 30% | 15% | 3.51 (3.39–3.63) | 2.30 (2.25–2.35) |
| cross: police alcohol and toxicology drug | 68,755 | 32% | 46% | 18% | 1.71 (1.65–1.76) | 1.31 (1.29–1.34) |
| cross: toxicology BAC >= .08 and police drugs | 68,755 | 31% | 30% | 12% | 1.91 (1.84–1.97) | 1.55 (1.51–1.58) |

**Surviving drivers**

| Measure | Drivers | Alcohol-positive | Drug-positive | Both | Odds ratio | Drug prevalence ratio (alcohol-positive vs negative) |
|---|---|---|---|---|---|---|
| toxicology: BAC >= .08 and any psychoactive drug | 31,870 | 15% | 35% | 7% | 2.06 (1.93–2.19) | 1.53 (1.48–1.58) |
| police report: alcohol and drugs both recorded | 31,870 | 22% | 26% | 11% | 4.12 (3.90–4.36) | 2.59 (2.50–2.68) |
| cross: police alcohol and toxicology drug | 31,870 | 22% | 35% | 12% | 2.66 (2.52–2.81) | 1.77 (1.72–1.83) |
| cross: toxicology BAC >= .08 and police drugs | 31,870 | 15% | 26% | 6% | 2.60 (2.44–2.77) | 1.91 (1.83–1.99) |

*(Woolf intervals ignore the clustering of drivers within crashes; they are indicative.)*

By toxicology, drug detection is only modestly more common among alcohol-positive killed
drivers (prevalence ratio
1.21).
By police report, among the same drivers, it is
2.30
times more common. The police report is also an insensitive
measure: among killed drivers whose toxicology found a psychoactive drug, the police recorded
drug involvement for only
36%
(62% of those with a known
police code); 42% were
coded unknown. *Competing explanations:* (i) police note drugs mainly when an impaired-driving
investigation is already under way; (ii) drivers who combine alcohol with drugs show more
visible impairment. The data cannot distinguish (i) from (ii), but either way the police field
over-states the overlap between alcohol and drugs and cannot serve as an independent drug
measure in models that also contain alcohol.

**Selection caveat for police-versus-BAC checks.** Comparing the police alcohol field with
measured BAC is possible only for drivers who were tested and whose police field is known:
43% of
killed and 21%
of surviving drivers (alcohol-tested:
67% and
25%).
Police sensitivity against BAC ≥ .08 is
87%
for killed and 98%
for surviving drivers in that sample, but the sample is selected on suspicion. Among surviving
drivers, BAC ≥ .08 prevalence in the tested sample falls from
39%
in the lowest survivor-test-rate tercile to
14%
in the highest, and the share of police-recorded alcohol that BAC confirms (positive predictive
value) from
75%
to 67%.
The agreement figures therefore describe the tested, suspected-impaired subset and may not hold
for untested drivers.

## 4. Bounds on a drug severity association in CRSS (estimated)

*Source: `drugs/crss_bounds`, `drugs/crss_adjusted`. Population: CRSS police-reported crashes
with known severity; exposure: police-reported drug involvement of any driver.*

CRSS has only the police field. In 2019–2024,
66%
of fatal and 54%
of non-fatal crashes have unknown drug status. The complete-case crude risk ratio is
11.9; if the
unknown crashes were drug-positive at k_f times the known prevalence among fatal crashes and
k_n times that among non-fatal crashes (k from 0 to 3), the risk ratio would lie anywhere
between 1.7 and
73. Even the two extreme codings — all unknown
negative (7.8) and all
unknown positive (2.1) —
differ widely. Model-A adjusted ratios are
4.30 (3.07–6.02) (complete case) and
2.97 (2.23–3.96) (unknown as no); their
narrow intervals reflect sampling error only and say nothing about which allocation of the
unknowns is right. Because testing and recording depend on severity (§2), the plausible
scenarios are those with k_f ≠ k_n, which is exactly where the bounds are widest.

**Non-differential allocations.** If unknown drug status is allocated by the same rule in fatal
and non-fatal crashes (`drugs/crss_bounds_nondifferential`), the range narrows but does not
close: proportional to the known prevalence (the same multiplier k in both), the crude ratio
lies between
7.8 and
19.0;
with the same absolute prevalence among unknown fatal and non-fatal crashes, between
1.7 and
7.8;
the extreme-corner grid above spans
1.7–73.
The non-differential values are **point estimates of assumed scenarios**: they carry no
sampling interval and no uncertainty about which scenario holds, and non-differential
allocation is itself implausible when testing and recording depend on severity. They show that
the conclusion does not rest on the extreme corners alone, not that a non-differential
association is the right one.

**Two drug definitions.** The reports use two different definitions of a drug-involved fatal
crash (`drugs/drug_definition_reconciliation`). Definition A, the police crash-level drug field
recorded as yes, covers
43,552
deaths in 2016–2024; definition B, any driver drug-positive on toxicology, covers
84,207.
Both hold in 34,915
deaths; A without B accounts for
8,637 and B
without A for 49,292.
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
| States testing ≥ 50% of killed and surviving drivers for both | 2.16 (1.82–2.57) | 1.28 (1.14–1.45) | 0.64 (0.47–0.89) | 7,860 |
| All states (selectively tested survivors) | 1.40 (1.35–1.46) | 1.17 (1.14–1.20) | 0.87 (0.81–0.93) | 164,499 |

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

| Split | Stratum | Pairs | RR belted vs unbelted | Ratio of RRs (2nd vs 1st stratum), 95% CI | p (heterogeneity) |
|---|---|---|---|---|---|
| all | all vehicles | 90,667 | 0.34 (0.33–0.35) | — | — |
| driver speeding (any) | driver not speeding | 71,670 | 0.34 (0.32–0.35) | — | — |
| driver speeding (any) | driver speeding | 16,582 | 0.34 (0.32–0.36) | 1.00 (0.93–1.08) | 0.96 |
| driver exceeded limit | driver not speeding | 71,670 | 0.34 (0.32–0.35) | — | — |
| driver exceeded limit | driver exceeded limit / racing | 7,007 | 0.36 (0.33–0.39) | 1.06 (0.96–1.17) | 0.26 |
| driver BAC >= .08 (MI) | driver BAC < .08 | 78,274 | 0.35 (0.34–0.37) | — | — |
| driver BAC >= .08 (MI) | driver BAC >= .08 | 12,393 | 0.32 (0.30–0.34) | 0.90 (0.83–0.98) | 0.012 |
| driver speeding and alcohol | neither | 65,375 | 0.35 (0.33–0.37) | — | — |
| driver speeding and alcohol | both | 5,638 | 0.33 (0.30–0.37) | 0.96 (0.86–1.07) | 0.44 |
| vehicles in crash | multi-vehicle | 60,556 | 0.44 (0.42–0.46) | — | — |
| vehicles in crash | single vehicle | 30,111 | 0.27 (0.25–0.28) | 0.61 (0.57–0.66) | 1.1e-39 |
| time | day | 61,659 | 0.35 (0.33–0.36) | — | — |
| time | night | 28,815 | 0.33 (0.31–0.35) | 0.93 (0.87–1.00) | 0.067 |

Overall, there is no detectable difference in the within-vehicle belt risk ratio whether or not the
driver was speeding (p = 0.96; exceeding the limit, p = 0.26), and it is slightly lower with a driver at BAC ≥ .08
(p 0.01).
The BAC ≥ .08 splits use NHTSA-imputed BAC (MI) for untested drivers. Among untested
drivers an imputed BAC of .08 or more is associated with being killed with an adjusted odds ratio of
3.82 (3.59–4.07), against 1.14 (1.10–1.18) for a measured BAC among tested drivers
(`measurement/imputed_bac_injury`), which is consistent with the imputation model using injury
severity but does not show it: the tested drivers are themselves selected on the outcome
(145,403 of 206,123 were killed, against 77,453 of 281,252 of the imputed group), and with police-reported alcohol, light, area
and weekend added the tested odds ratio is 2.53 (2.42–2.65). BAC-based splits therefore may depend on a model
that uses the outcome, and measured-BAC results avoid that dependence but describe tested drivers
only. This is a diagnostic, not a causal estimate.

That overall comparison does not hold crash configuration fixed, and the configuration differs
between the groups. Within crash configuration the picture changes
(`restraint_behaviour/dpc_contrast_within_configuration`; ratio of the belt risk ratio with the
behaviour to that without it, pooled across layers, >1 means belts protect less):

| Driver behaviour | Layers | Ratio of RRs (95% CI) |
|---|---|---|
| Speeding (any), by single/multi-vehicle | single vs multi-vehicle | 1.17 (1.08–1.27) |
| Speeding (any), by rollover | rollover vs not | 1.10 (1.01–1.19) |
| Speeding (any), by crash type | crash type | 1.22 (1.10–1.35) |
| Exceeded limit / racing, by crash type | crash type | 1.35 (1.16–1.57) |
| BAC ≥ .08, by single/multi-vehicle | single vs multi-vehicle | 1.04 (0.95–1.13) |
| BAC ≥ .08, by crash type | crash type | 1.00 (0.91–1.09) |

So the earlier unstratified conclusion that the belt effect does not vary with the driver's speeding
does not hold within crash configuration: across the four layering schemes belts are somewhat less
protective when the driver was speeding (ratio of RRs 1.10 to 1.23; the crash-type scheme pools only 3 of
its 8 crash types), while the BAC contrast shows no detectable difference (p = 0.66). This is an exploratory follow-up, not
multiplicity-adjusted, and the layers are pooled as if independent. Belt protection also differs by the *kind of impact*.
By crash type (FARS, within-vehicle double-pair comparison, `matched/belt_by_crash_type`):

| Stratum | Pairs | RR belted vs unbelted | Risk reduction |
|---|---|---|---|
| single vehicle, rollover first | 4,578 | 0.16 | 84% (82–87%) |
| single vehicle, no rollover first | 18,225 | 0.30 | 70% (68–71%) |
| multi-vehicle, angle | 26,084 | 0.49 | 51% (47–54%) |
| multi-vehicle, head-on | 14,211 | 0.46 | 54% (50–58%) |
| multi-vehicle, rear-end | 9,804 | 0.35 | 65% (60–70%) |
| multi-vehicle, sideswipe | 4,354 | 0.34 | 66% (59–72%) |
| other (multi-vehicle other, non-motorist) | 13,411 | 0.32 | 68% (61–75%) |
| vehicle rolled over (any crash type) | 18,101 | 0.23 | 77% (76–79%) |
| vehicle did not roll over | 72,566 | 0.43 | 57% (55–59%) |

Belts are associated with a larger reduction in single-vehicle crashes
(73%)
than in multi-vehicle crashes (56%),
and the reduction is largest when the vehicle rolled over
(77%
vs 57%), and
smallest in multi-vehicle angle and head-on crashes, consistent with ejection in rollovers and
roadway departures being largely prevented by belts. A single pooled belt estimate therefore
averages over crash types in which the protection differs substantially.

**Across crashes** (CRSS light-vehicle occupants aged 15+; same sample at every step):

| Model | Unbelted vs belted RR | Risk difference | Share of crude log-RR retained |
|---|---|---|---|
| crude | 46.1 (40.8–52.1) | 0.0423 (0.0378–0.0468) | 1.00 |
| + crash environment | 33.5 (29.8–37.6) | 0.0305 (0.0265–0.0344) | 0.92 |
| + person and vehicle | 35.8 (31.8–40.3) | 0.0325 (0.0281–0.0370) | 0.93 |
| + driver's own speeding and alcohol | 27.9 (24.6–31.8) | 0.0256 (0.0215–0.0298) | 0.87 |
| + crash configuration | 18.8 (17.0–20.8) | 0.0173 (0.0148–0.0198) | 0.77 |

The across-crash risk ratio falls from
46 to
28
once crash circumstances and the driver's own speeding and alcohol are held fixed (the
log-RR retains 87%),
and to 19 with crash
configuration. Unbelted occupants
are disproportionately in crashes with impaired or speeding drivers and in more violent crash
types. Even fully adjusted, the across-crash ratio is several times the within-vehicle ratio
(about 0.34,
i.e. a large within-vehicle protective association), which is what one expects if unmeasured crash
energy and, possibly, survivor over-reporting of belt use inflate across-crash comparisons.

*Competing explanations.* (i) "Belt non-use only marks drunk or speeding drivers" — the
within-vehicle comparison holds the driver and crash fixed, and the overall belt risk ratio
shows no detectable difference with and without a speeding or drinking driver (§6); within crash configuration the
speeding contrast (exploratory) is modest and in the direction of *less* protection, which is not what a pure
marker would produce. (ii) "Survivors over-report belt use" — not testable from the data
directly, but quantifiable. Phase 1 showed that the within-vehicle reduction would fall from
66% to
38%
if 10% of 'belted' survivors were unbelted (`matched/belt_effect`). The error can run in both
directions: a fraction g of deaths coded unbelted may truly have been belted. Crossing the two
(`matched/belt_misreporting_two_sided_dpc`):

| Belted survivors truly unbelted (f) | Unbelted deaths truly belted (g) | RR belted vs unbelted | Risk reduction |
|---|---|---|---|
| 0.00 | 0.00 | 0.34 (0.33–0.35) | 66% (65–67%) |
| 0.05 | 0.00 | 0.47 (0.46–0.49) | 53% (51–54%) |
| 0.10 | 0.00 | 0.62 (0.60–0.63) | 38% (37–40%) |
| 0.20 | 0.00 | 0.95 (0.93–0.98) | 5% (2–7%) |
| 0.00 | 0.05 | 0.42 (0.41–0.43) | 58% (57–59%) |
| 0.05 | 0.05 | 0.56 (0.55–0.58) | 44% (42–45%) |
| 0.10 | 0.05 | 0.72 (0.70–0.73) | 28% (27–30%) |
| 0.20 | 0.05 | 1.07 (1.05–1.09) | -7% (-9 to -5%) |
| 0.00 | 0.10 | 0.50 (0.49–0.52) | 50% (48–51%) |
| 0.05 | 0.10 | 0.65 (0.64–0.67) | 35% (33–36%) |
| 0.10 | 0.10 | 0.82 (0.80–0.83) | 18% (17–20%) |
| 0.20 | 0.10 | 1.19 (1.16–1.21) | -19% (-21 to -16%) |

The belt effect is estimated to disappear if about
21%
of 'belted' survivors were truly unbelted with no reverse error, and reverse error (g) moves the
tipping fraction down
(15%
at g = 0.10).
The direction of the association is robust to modest misreporting; its size is not, and a
survivor misreporting fraction at the tipping value above would remove it entirely.

**Helmets.** The same design applied to motorcycle riders (operator and passenger on the same
motorcycle) rests on very few informative pairs. Of
18,336 unhelmeted
motorcyclist deaths, only 16%
occurred in an operator-passenger pair with complete information (whether or not the pair differs in helmet use), and
1.2%
in pairs that identify the matched-pair odds ratio; most are on single-rider motorcycles
(84%),
where no within-motorcycle comparison exists. The helmeted-versus-unhelmeted risk ratio is
0.70 (0.61–0.81)
as recorded, but it is far more fragile to misreporting than the belt estimate: with 5% of
'helmeted' survivors truly unhelmeted it is
0.97 (0.86–1.10)
and it reaches one at a misreporting fraction of
5%.
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
