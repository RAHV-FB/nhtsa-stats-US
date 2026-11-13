<!-- Generated from reports/templates/multifactor_interactions.md by `nhtsa analyze report`; every number is looked up in outputs/tables. Edit the template, not this file. -->

# How factors combine: two-, three- and four-factor analyses at the right observation level

*Phase 2 report (research questions E and F; `docs/research_plan_phase2.md` §5.3). CRSS
police-reported crashes 2016–2024, survey-weighted; every number is read from
`outputs/tables/multifactor/` when this report is rendered. All risks are **adjusted
associations**: standardised predictive margins from survey logistic models, conditional on a
police-reported crash, not causal effects.*

## Summary

1. **The unit matters.** The same recorded behaviour has different associations depending on
   whose death is the outcome. Recorded alcohol involvement — of any driver for the crash
   outcome, of the responsible driver for each person's death — carries a risk ratio of 4.7 (3.9–5.6)
   for the crash being fatal, 2.7 (2.1–3.6)
   for the driver's own death, 4.4 (3.3–5.7)
   for a passenger's death, 3.6 (2.8–4.6)
   for the death of an occupant of the *other* vehicle, and only
   1.23 (0.94–1.61)
   for the death of a struck pedestrian (environment held fixed) — small *in relative terms*
   only: the pedestrian's baseline risk is high, so the absolute risk difference has a larger
   point estimate than for any occupant but is imprecise
   (19.9 (-6.6 to 46.4)
   per 1,000 struck pedestrians; §6). These unit-specific
   ratios come from models with different adjustment sets and are not comparable across units
   (§6).
2. **Speeding and alcohol combine super-additively but sub-multiplicatively at the crash level.**
   Crashes in which a driver exceeded the limit and alcohol was involved are fatal
   15.6 (11.8–20.6)
   times as often as crashes with neither, against
   6.7
   for exceedance alone and 4.7
   for alcohol alone: more excess deaths than the two excesses added up (additive contrast
   20.7 (8.4–33.0)
   per 1,000 crashes), but a smaller ratio than their product (ratio of risk ratios
   0.49 (0.40–0.61)).
3. **When one driver is the only driver, no departure from multiplicativity is detected.** In
   single-vehicle crashes the ratio of risk ratios is
   1.13 (0.84–1.53):
   no departure from multiplicativity is detected. The crash-level sub-multiplicativity may
   partly reflect pooling two different drivers' behaviours and different crash types in one
   crash-level contrast; the two explanations cannot be separated here.
4. **Belt non-use dominates every occupant combination.** Its additive interaction with the
   driver's speeding is positive for drivers and passengers, and with the driver's alcohol for
   passengers (Holm-adjusted; for drivers the alcohol × unbelted additive contrast does not
   survive the adjustment). For light-vehicle drivers, the standardised risk of dying is
   0.07% (0.06–0.09%)
   with none of the three factors and
   7.2% (5.7–9.2%)
   with all three. The three-way additive contrast is not distinguishable from zero.
5. **Four-factor combinations involving drugs cannot be estimated.** Among drivers with known
   police drug status, the speeding + drugs cell (belted, no alcohol) has
   6
   deaths; it and every contrast that uses it — including the four-way contrast — are withheld.

---

## 1. Question and design

*Question.* When several dangerous factors coexist, is the risk of death larger than the single
factors imply (interaction), and does the answer depend on whose death is counted?

*Why it matters.* Official statistics count a death once for each factor present. If
factors combine super-additively, a death "involving" two factors is not two separately
attributable deaths; if they combine sub-multiplicatively, adding up relative risks overstates
the combination.

*Design.* For each analysis a survey logistic model contains every factor's categorical main
effect, a product term for every combination of non-reference levels (unknown included) of every
subset of factors (so the factors are
saturated among themselves), and the adjustment covariates. The 2^k standardised risks are the
mean predicted risk over the analysis population with every unit set to each combination.
Additive interaction is the k-way contrast Σ(−1)^(k−|s|) p_s (for two factors
p11 − p10 − p01 + p00); multiplicative interaction is the same contrast on the log scale
(for two factors RR11 / (RR10 · RR01)). Combinations with fewer than 30 sample units or 10
deaths are withheld with every contrast using them. Holm adjustment across all contrasts of the
six registered analyses, separately per scale. The family is fixed in advance: a registered
contrast that cannot be estimated (withheld cells) still counts toward the family size, is treated
as not rejectable, and shows no p-value.

*How to read the two scales.* A positive additive interaction (contrast > 0) is expected
whenever two factors each raise risk and combine multiplicatively, so it shows where excess
deaths concentrate (burden), not a special mechanism. A combination is called *amplifying*
here only when the ratio of risk ratios is above 1 with a confidence interval that excludes 1;
"super-additive" below describes the additive scale only and is not evidence of amplification.
The interaction margins treat the mixture weights of the factor levels as fixed.

| Analysis | Population | Outcome | n | Deaths | Registered |
|---|---|---|---|---|---|
| crash_exceeded_x_alcohol | CRSS police-reported crashes | crash fatal | 468,993 | 9,958 | True |
| crash_speeding_x_alcohol_x_night | CRSS police-reported crashes (time known) | crash fatal | 466,448 | 9,839 | True |
| sv_driver_exceeded_x_alcohol | Drivers in single-vehicle crashes (the only driver behaviour in the crash) | crash fatal | 153,940 | 5,471 | True |
| lpv_driver_speeding_x_alcohol_x_unbelted | Drivers of light passenger vehicles (belt use belted, none or unknown) | driver killed | 735,787 | 5,515 | True |
| passenger_driver_speeding_x_driver_alcohol_x_unbelted | Passengers of light passenger vehicles aged 15+ (belt use belted, none or unknown) | passenger killed | 190,757 | 1,449 | True |
| lpv_driver_drugs_known_4way | Drivers of light passenger vehicles with known police drug status (a selected subset) | driver killed | 459,638 | 2,511 | True |
| crash_exceeded_x_alcohol_ka | CRSS police-reported crashes | crash fatal or serious (KA) | 467,185 | 60,345 | False |
| crash_exceeded_x_alcohol_police | CRSS police-reported crashes (police alcohol coding; unknown kept as a level) | crash fatal | 468,993 | 9,958 | False |
| lpv_driver_exceeded_x_alcohol_x_unbelted | Drivers of light passenger vehicles | driver killed | 735,787 | 5,515 | False |
| lpv_driver_speeding_x_alcohol_x_unbelted_config | Drivers of light passenger vehicles | driver killed | 735,787 | 5,515 | False |

## 2. Crash level: exceeding the limit × alcohol

| Combination | Crashes (sample) | Fatal | Crude fatal rate | Standardised fatal risk | RR vs neither |
|---|---|---|---|---|---|
| none | 377,893 | 5,444 | 0.39% (0.34–0.45%) | 0.40% (0.35–0.47%) | 1.0 (1.0–1.0) |
| alcohol | 23,376 | 1,845 | 2.57% (2.18–3.02%) | 1.89% (1.57–2.26%) | 4.7 (3.9–5.6) |
| exceeded | 4,611 | 555 | 3.83% (3.16–4.63%) | 2.72% (2.20–3.35%) | 6.7 (5.6–8.1) |
| exceeded + alcohol | 1,299 | 316 | 10.17% (8.31–12.39%) | 6.28% (4.95–7.93%) | 15.6 (11.8–20.6) |

* Additive contrast: 20.7 (8.4–33.0) per 1,000 crashes (Holm p 0.03).
* Ratio of risk ratios: 0.49 (0.40–0.61) (Holm p 4.3e-07).
* Exceedance within alcohol strata: 6.75 (5.60–8.13) without and 3.33 (2.65–4.17) with alcohol.

*Does the speeding-by-alcohol pattern survive crash configuration?* The strata specification
above does not adjust for crash configuration (single- vs multi-vehicle, impact type). Adding it
(`multifactor/speeding_alcohol_strata_configuration`, fatal outcome) changes the comparison of
the two behaviours:

| Behaviour | Specification | RR, no alcohol | RR, alcohol | Ratio (alcohol / no alcohol) |
|---|---|---|---|---|
| Exceeded the limit | without configuration | 6.5 (5.5–7.8) | 3.3 (2.7–4.0) | 0.50 (0.42–0.61) |
| Exceeded the limit | with configuration | 5.3 (4.5–6.3) | 3.7 (3.0–4.4) | 0.68 (0.57–0.82) |
| Any speeding | without configuration | 1.9 (1.5–2.3) | 1.6 (1.2–1.9) | 0.82 (0.66–1.01) |
| Any speeding | with configuration | 2.0 (1.8–2.3) | 2.0 (1.7–2.4) | 1.00 (0.84–1.19) |

For exceedance the speeding risk ratio is smaller where alcohol is present with or without
configuration (the ratio stays below one), though less so with configuration. For any speeding
the apparent attenuation by alcohol without configuration (ratio
0.82 (0.66–1.01))
disappears once configuration is held fixed
(1.00 (0.84–1.19)).
The sub-multiplicative pattern for speeding × alcohol therefore depends on the specification
for any speeding and should be read as specification-dependent, not as a stable property.

*Checks.* Police-reported alcohol instead of imputed: ratio of RRs
0.41 (0.32–0.52),
additive 13.4 (3.3–23.5).
Fatal-or-serious outcome: ratio 0.70 (0.60–0.82),
additive 47.0 (22.1–71.8) per 1,000.

*Competing explanation: is the sub-multiplicativity real?* A crash-level "exceeded × alcohol"
cell mixes crashes in which one driver both sped and drank with crashes in which two different
drivers each did one. §3 removes that ambiguity.

## 3. Driver level, single-vehicle crashes: one driver's own behaviour

| Combination | Drivers (sample) | Fatal crashes | Standardised fatal risk | RR vs neither |
|---|---|---|---|---|
| none | 116,179 | 3,210 | 0.87% (0.75–1.01%) | 1.00 (1.00–1.00) |
| alcohol | 10,658 | 776 | 1.81% (1.49–2.20%) | 2.07 (1.66–2.60) |
| exceeded | 2,490 | 274 | 3.09% (2.49–3.83%) | 3.53 (2.94–4.25) |
| exceeded + alcohol | 827 | 190 | 7.24% (5.65–9.24%) | 8.28 (6.22–11.02) |

Additive contrast 32.2 (15.3–49.0)
per 1,000 crashes (Holm p 0.0083);
ratio of RRs 1.13 (0.84–1.53).
Within single-vehicle crashes both risk ratios are smaller than at the crash level, because
the crash-level comparison also contrasts *crash types* (alcohol and exceedance are
concentrated in single-vehicle crashes, which are more severe), and no departure from
multiplicativity is detected. One interpretation consistent with both analyses: the same
driver's alcohol and speed do not "use up" each other's risk, and the crash-level
sub-multiplicativity reflects pooling different drivers and crash types. Because the
single-vehicle restriction changes both the driver attribution and the crash type, the data
cannot say which of the two matters.

## 4. Occupant level: whose behaviour, whose belt

**Light-vehicle drivers** (their own speeding, alcohol and belt use; outcome: the driver dies):

| Combination | Drivers | Deaths | Standardised risk of death | RR vs none |
|---|---|---|---|---|
| none | 594,248 | 1,814 | 0.07% (0.06–0.09%) | 1.0 (1.0–1.0) |
| unbelted | 13,183 | 1,173 | 2.50% (2.07–3.01%) | 35.3 (30.6–40.7) |
| alcohol | 14,467 | 342 | 0.44% (0.34–0.56%) | 6.2 (4.7–8.2) |
| alcohol + unbelted | 2,664 | 445 | 4.28% (3.28–5.57%) | 60.5 (46.0–79.7) |
| speeding | 32,556 | 270 | 0.15% (0.12–0.18%) | 2.1 (1.6–2.7) |
| speeding + unbelted | 2,463 | 357 | 4.23% (3.64–4.91%) | 59.8 (47.0–76.0) |
| speeding + alcohol | 2,889 | 92 | 0.62% (0.44–0.86%) | 8.7 (5.8–13.1) |
| speeding + alcohol + unbelted | 1,058 | 234 | 7.22% (5.67–9.15%) | 102.1 (74.7–139.5) |

| Contrast | Additive (per 1,000) | Holm p | Multiplicative ratio | Holm p |
|---|---|---|---|---|
| speeding x alcohol | 1.0 (-0.8 to 2.8) | 1 | 0.68 (0.49–0.93) | 0.31 |
| speeding x unbelted | 16.6 (8.9–24.2) | 0.0019 | 0.81 (0.67–0.98) | 0.43 |
| alcohol x unbelted | 14.2 (3.4–25.0) | 0.2 | 0.28 (0.21–0.36) | 4.2e-11 |
| speeding x alcohol x unbelted | 11.0 (-5.4 to 27.5) | 1 | 1.47 (0.94–2.30) | 1 |

**Passengers** (the driver's speeding and alcohol; their own belt; outcome: the passenger dies):

| Combination | Passengers | Deaths | Standardised risk of death | RR vs none |
|---|---|---|---|---|
| none | 149,593 | 436 | 0.07% (0.06–0.09%) | 1.0 (1.0–1.0) |
| unbelted | 5,231 | 309 | 2.11% (1.74–2.54%) | 29.7 (25.2–35.0) |
| driver_alcohol | 3,025 | 62 | 0.43% (0.33–0.57%) | 6.1 (4.4–8.6) |
| driver_alcohol + unbelted | 794 | 130 | 6.80% (5.35–8.61%) | 96.1 (71.9–128.5) |
| driver_speeding | 7,607 | 60 | 0.17% (0.12–0.25%) | 2.4 (1.7–3.6) |
| driver_speeding + unbelted | 1,108 | 110 | 4.76% (3.86–5.86%) | 67.2 (53.0–85.3) |
| driver_speeding + driver_alcohol | 776 | 40 | 1.34% (0.84–2.14%) | 19.0 (10.8–33.3) |
| driver_speeding + driver_alcohol + unbelted | 437 | 74 | 8.07% (5.83–11.08%) | 114.1 (78.3–166.1) |

| Contrast | Additive (per 1,000) | Holm p | Multiplicative ratio | Holm p |
|---|---|---|---|---|
| driver_speeding x driver_alcohol | 8.0 (1.4–14.7) | 0.32 | 1.27 (0.65–2.48) | 1 |
| driver_speeding x unbelted | 25.5 (17.0–34.1) | 8.9e-06 | 0.93 (0.63–1.37) | 1 |
| driver_alcohol x unbelted | 43.3 (27.5–59.2) | 4.6e-05 | 0.53 (0.37–0.75) | 0.013 |
| driver_speeding x driver_alcohol x unbelted | -21.9 (-48.9 to 5.1) | 1 | 0.41 (0.20–0.85) | 0.31 |

*Reading.* Belt non-use carries by far the largest risk ratio for occupants
(35
for drivers, 30
for passengers), much larger than the within-vehicle ratio
(`reports/alcohol_drugs_restraints.md` §6): across crashes, unbelted occupants are in more
violent crashes, and survivors may over-report belt use (not testable here). On the additive
scale the pairs involving belt non-use are positive; an unbelted passenger of a drinking or
speeding driver has a much larger *excess* risk than either factor alone implies. On the ratio
scale, alcohol × unbelted is clearly sub-multiplicative for drivers and passengers, whereas no
multiplicative departure is detected for speeding × unbelted (§7 gives every contrast with its
Holm-adjusted p-value). Super-additive and sub-multiplicative at once is not a contradiction: the
two scales answer different questions (how many extra deaths vs how many times the risk).

*Sensitivity.* Adding crash configuration (a mediator of speeding and alcohol) reduces every
risk ratio — the driver's unbelted RR from
35.3
to 23.9
and alcohol from 6.2
to 4.0;
part of each association runs through the type of crash. Exceedance instead of any speeding:
8.9 (6.4–12.5)
for the driver's death (any speeding 2.1).

## 5. Four factors: speeding × alcohol × drugs × belt (drivers with known police drug status)

| Combination | Drivers | Deaths | Standardised risk of death | Status |
|---|---|---|---|---|
| none | 395,642 | 933 | 0.05% (0.04–0.06%) | — |
| unbelted | 7,498 | 475 | 1.82% (1.37–2.42%) | — |
| drugs | 1,737 | 40 | 0.43% (0.25–0.76%) | — |
| drugs + unbelted | 396 | 55 | 4.71% (2.96–7.41%) | — |
| alcohol | 4,822 | 77 | 0.29% (0.21–0.39%) | — |
| alcohol + unbelted | 915 | 109 | 3.29% (2.24–4.80%) | — |
| alcohol + drugs | 1,486 | 62 | 0.95% (0.59–1.53%) | — |
| alcohol + drugs + unbelted | 492 | 102 | 7.62% (4.63–12.32%) | — |
| speeding | 16,892 | 93 | 0.09% (0.07–0.13%) | — |
| speeding + unbelted | 1,107 | 116 | 3.33% (2.49–4.44%) | — |
| speeding + drugs | 299 | 6 | — | suppressed: fewer than 30 sample units or 10 events |
| speeding + drugs + unbelted | 125 | 17 | 5.20% (2.81–9.40%) | — |
| speeding + alcohol | 1,016 | 23 | 0.50% (0.29–0.86%) | — |
| speeding + alcohol + unbelted | 361 | 65 | 6.56% (4.32–9.83%) | — |
| speeding + alcohol + drugs | 315 | 20 | 1.91% (0.85–4.24%) | — |
| speeding + alcohol + drugs + unbelted | 182 | 38 | 7.73% (4.78–12.27%) | — |

This analysis is restricted to the
56% of driver
records with a known police drug code — a subset selected by recording practice (drug status
is recorded more often when impairment is suspected and in severe crashes; see
`reports/alcohol_drugs_restraints.md`). One of 16 combinations lacks support, which removes the
four-way contrast and the speeding × drugs contrasts. The supported pairs show the same pattern
as alcohol: police-recorded drug involvement is associated with the driver's death
(8.2 (4.8–14.0)
when it is the only factor), and alcohol × drugs is sub-multiplicative
(0.40 (0.23–0.71),
Holm p 0.045).
Because police drug status is neither complete nor independent of alcohol recording, these
numbers describe police-recorded drug involvement in a selected subset; they are not a drug
effect and are not used for ranking.

## 6. Driver, passenger, other road user: same behaviour, different victims

| Victim (behaviour of) | n | Deaths | Risk with neither | Speeding only, RR | Alcohol only, RR | Both, RR | Ratio of RRs |
|---|---|---|---|---|---|---|---|
| crash fatal (any driver's behaviour) | 468,993 | 9,958 | 0.40% (0.35–0.47%) | 1.99 (1.63–2.43) | 4.65 (3.86–5.60) | 6.97 (5.24–9.28) | 0.75 (0.62–0.91) |
| driver killed (own behaviour) | 735,877 | 5,515 | 0.14% (0.12–0.17%) | 2.05 (1.65–2.54) | 2.71 (2.06–3.57) | 4.24 (3.10–5.80) | 0.76 (0.59–0.98) |
| passenger killed (their driver's behaviour) | 192,968 | 1,468 | 0.14% (0.12–0.17%) | 2.72 (2.17–3.41) | 4.35 (3.30–5.73) | 6.26 (4.30–9.11) | 0.53 (0.36–0.78) |
| other-vehicle occupant killed (the other driver's behaviour) | 640,520 | 3,040 | 0.10% (0.09–0.12%) | 1.31 (0.94–1.82) | 3.61 (2.84–4.58) | 7.33 (4.77–11.25) | 1.55 (1.03–2.32) |
| pedestrian killed (striking driver's behaviour) | 24,966 | 1,777 | 7.93% (6.75–9.30%) | 1.03 (0.72–1.49) | 1.23 (0.94–1.61) | 1.59 (0.87–2.93) | 1.25 (0.59–2.65) |

**Unit-specific ratios are not comparable across units.** Each row above comes from a model
with its own adjustment set (the unit-specific specification), so a risk ratio cannot be
compared between rows: part of any difference is the adjustment, not the unit. The table below
re-estimates the alcohol-only association for the same four victims with one **common**
specification (environment, victim age band and sex) and with crash configuration added
(`multifactor/victims_common_spec`), next to the published unit-specific estimates, with the
risk difference per 1,000.

| Victim | Specification | Alcohol only, RR | Risk difference per 1,000 |
|---|---|---|---|
| driver killed (own behaviour) | unit-specific (published) | 2.71 (2.06–3.57) | 2.4 (1.4–3.4) |
| driver killed (own behaviour) | common: environment + victim age band + sex | 6.20 (4.67–8.22) | 6.7 (4.6–8.8) |
| driver killed (own behaviour) | common + crash configuration | 3.32 (2.52–4.37) | 3.2 (2.0–4.4) |
| passenger killed (their driver's behaviour) | unit-specific (published) | 4.35 (3.30–5.73) | 4.8 (3.3–6.3) |
| passenger killed (their driver's behaviour) | common: environment + victim age band + sex | 8.83 (6.46–12.07) | 10.4 (7.3–13.6) |
| passenger killed (their driver's behaviour) | common + crash configuration | 6.16 (4.38–8.64) | 7.1 (4.6–9.5) |
| other-vehicle occupant killed (the other driver's behaviour) | unit-specific (published) | 3.61 (2.84–4.58) | 2.7 (1.8–3.6) |
| other-vehicle occupant killed (the other driver's behaviour) | common: environment + victim age band + sex | 3.96 (3.03–5.18) | 3.1 (2.0–4.1) |
| other-vehicle occupant killed (the other driver's behaviour) | common + crash configuration | 2.26 (1.70–3.00) | 1.3 (0.7–2.0) |
| pedestrian killed (striking driver's behaviour) | unit-specific (published) | 1.23 (0.94–1.61) | 18.5 (-7.3 to 44.2) |
| pedestrian killed (striking driver's behaviour) | common: environment + victim age band + sex | 1.25 (0.95–1.64) | 19.9 (-6.6 to 46.4) |
| pedestrian killed (striking driver's behaviour) | common + crash configuration | 1.25 (0.95–1.64) | 19.9 (-6.6 to 46.5) |

The ranking of units changes with the specification, so the contrast between units (for
instance occupant vs pedestrian) is stable only in the broad sense that the pedestrian ratio is
small in relative terms under every specification. The pedestrian risk difference has the
largest point estimate of the four because the baseline risk is high, but its interval includes
zero.

* For **the impaired or speeding driver** and **their passengers**, both behaviours are
  associated with death, alcohol more than speeding (any type).
* *(This table is exploratory; it is not part of the Holm family.)* For **occupants of the other
  vehicle** in two-vehicle crashes, the other driver's alcohol is
  strongly associated with death (their own driver's behaviour and belt held fixed); the other
  driver's recorded speeding much less so, and the two combine super-multiplicatively
  (ratio 1.55 (1.03–2.32)).
* For **pedestrians**, once the speed limit, light and pedestrian age are held fixed, the
  associations with the striking driver's recorded speeding and alcohol are imprecise and much
  smaller *in relative terms* than for occupants (intervals compatible with no association and with modest ones, but
  not with occupant-sized ratios). One hypothesis is that the posted limit already captures much
  of the impact-speed variation that matters for a pedestrian; the data cannot test it.
  Police-recorded speeding is rare in pedestrian crashes
  (807
  sample pedestrians), so this comparison is imprecise.

**Answer to F (units).** Estimated contributions depend strongly on the observation unit: a
crash-level association combines several drivers' behaviours and several people's deaths, and
should not be quoted as a driver-level or person-level risk.

## 7. Which combinations show interaction (answer to E)

Every registered contrast, with Holm-adjusted p-values (a contrast is called "detected" below
only if its Holm p < 0.05):

| Analysis | Contrast | Additive (per 1,000) | Holm p | Ratio of RRs | Holm p | Status |
|---|---|---|---|---|---|---|
| crash_exceeded_x_alcohol | exceeded x alcohol | 20.7 (8.4–33.0) | 0.03 | 0.49 (0.40–0.61) | 4.3e-07 | — |
| crash_speeding_x_alcohol_x_night | speeding x alcohol | 2.8 (-4.1 to 9.7) | 1 | 0.66 (0.51–0.84) | 0.03 | — |
| crash_speeding_x_alcohol_x_night | speeding x night | 4.8 (2.7–6.8) | 0.00066 | 1.05 (0.84–1.30) | 1 | — |
| crash_speeding_x_alcohol_x_night | alcohol x night | -0.9 (-4.2 to 2.5) | 1 | 0.49 (0.40–0.59) | 8.2e-08 | — |
| crash_speeding_x_alcohol_x_night | speeding x alcohol x night | 8.3 (-0.6 to 17.1) | 0.93 | 1.31 (0.95–1.82) | 1 | — |
| sv_driver_exceeded_x_alcohol | exceeded x alcohol | 32.2 (15.3–49.0) | 0.0083 | 1.13 (0.84–1.53) | 1 | — |
| lpv_driver_speeding_x_alcohol_x_unbelted | speeding x alcohol | 1.0 (-0.8 to 2.8) | 1 | 0.68 (0.49–0.93) | 0.31 | — |
| lpv_driver_speeding_x_alcohol_x_unbelted | speeding x unbelted | 16.6 (8.9–24.2) | 0.0019 | 0.81 (0.67–0.98) | 0.43 | — |
| lpv_driver_speeding_x_alcohol_x_unbelted | alcohol x unbelted | 14.2 (3.4–25.0) | 0.2 | 0.28 (0.21–0.36) | 4.2e-11 | — |
| lpv_driver_speeding_x_alcohol_x_unbelted | speeding x alcohol x unbelted | 11.0 (-5.4 to 27.5) | 1 | 1.47 (0.94–2.30) | 1 | — |
| passenger_driver_speeding_x_driver_alcohol_x_unbelted | driver_speeding x driver_alcohol | 8.0 (1.4–14.7) | 0.32 | 1.27 (0.65–2.48) | 1 | — |
| passenger_driver_speeding_x_driver_alcohol_x_unbelted | driver_speeding x unbelted | 25.5 (17.0–34.1) | 8.9e-06 | 0.93 (0.63–1.37) | 1 | — |
| passenger_driver_speeding_x_driver_alcohol_x_unbelted | driver_alcohol x unbelted | 43.3 (27.5–59.2) | 4.6e-05 | 0.53 (0.37–0.75) | 0.013 | — |
| passenger_driver_speeding_x_driver_alcohol_x_unbelted | driver_speeding x driver_alcohol x unbelted | -21.9 (-48.9 to 5.1) | 1 | 0.41 (0.20–0.85) | 0.31 | — |
| lpv_driver_drugs_known_4way | speeding x alcohol | 1.7 (-1.1 to 4.5) | 1 | 0.97 (0.49–1.89) | 1 | — |
| lpv_driver_drugs_known_4way | speeding x drugs | — | — | — | — | withheld: a combination lacks support |
| lpv_driver_drugs_known_4way | speeding x unbelted | 14.7 (5.2–24.2) | 0.063 | 1.03 (0.66–1.60) | 1 | — |
| lpv_driver_drugs_known_4way | alcohol x drugs | 2.8 (-1.2 to 6.9) | 1 | 0.40 (0.23–0.71) | 0.045 | — |
| lpv_driver_drugs_known_4way | alcohol x unbelted | 12.3 (1.2–23.5) | 0.49 | 0.33 (0.21–0.53) | 0.0005 | — |
| lpv_driver_drugs_known_4way | drugs x unbelted | 25.1 (2.3–47.9) | 0.49 | 0.32 (0.15–0.66) | 0.054 | — |
| lpv_driver_drugs_known_4way | speeding x alcohol x drugs | — | — | — | — | withheld: a combination lacks support |
| lpv_driver_drugs_known_4way | speeding x alcohol x unbelted | 15.9 (-11.7 to 43.6) | 1 | 1.13 (0.45–2.84) | 1 | — |
| lpv_driver_drugs_known_4way | speeding x drugs x unbelted | — | — | — | — | withheld: a combination lacks support |
| lpv_driver_drugs_known_4way | alcohol x drugs x unbelted | 11.6 (-24.0 to 47.3) | 1 | 2.23 (0.88–5.65) | 1 | — |
| lpv_driver_drugs_known_4way | speeding x alcohol x drugs x unbelted | — | — | — | — | withheld: a combination lacks support |

A contrast is detected on a scale when its Holm-adjusted p < 0.05 within the fixed family of
registered contrasts; the table lists every registered contrast that is detected on at least one
scale, with its direction, and every contrast the data withhold.

| Analysis | Contrast | Detected | Additive Holm p | Multiplicative Holm p |
|---|---|---|---|---|
| crash_exceeded_x_alcohol | exceeded x alcohol | super-additive and sub-multiplicative | 0.03 | 4.3e-07 |
| crash_speeding_x_alcohol_x_night | speeding x alcohol | sub-multiplicative | 1 | 0.03 |
| crash_speeding_x_alcohol_x_night | speeding x night | super-additive | 0.00066 | 1 |
| crash_speeding_x_alcohol_x_night | alcohol x night | sub-multiplicative | 1 | 8.2e-08 |
| sv_driver_exceeded_x_alcohol | exceeded x alcohol | super-additive | 0.0083 | 1 |
| lpv_driver_speeding_x_alcohol_x_unbelted | speeding x unbelted | super-additive | 0.0019 | 0.43 |
| lpv_driver_speeding_x_alcohol_x_unbelted | alcohol x unbelted | sub-multiplicative | 0.2 | 4.2e-11 |
| passenger_driver_speeding_x_driver_alcohol_x_unbelted | driver_speeding x unbelted | super-additive | 8.9e-06 | 1 |
| passenger_driver_speeding_x_driver_alcohol_x_unbelted | driver_alcohol x unbelted | super-additive and sub-multiplicative | 4.6e-05 | 0.013 |
| lpv_driver_drugs_known_4way | speeding x drugs | withheld | — | — |
| lpv_driver_drugs_known_4way | alcohol x drugs | sub-multiplicative | 1 | 0.045 |
| lpv_driver_drugs_known_4way | alcohol x unbelted | sub-multiplicative | 0.49 | 0.0005 |
| lpv_driver_drugs_known_4way | speeding x alcohol x drugs | withheld | — | — |
| lpv_driver_drugs_known_4way | speeding x drugs x unbelted | withheld | — | — |
| lpv_driver_drugs_known_4way | speeding x alcohol x drugs x unbelted | withheld | — | — |

*Distinguishing genuine interaction from high baselines.* Several combinations look
"unusually deadly" in raw counts simply because each factor has a high risk on its own; the
multiplicative contrasts above show that, on the ratio scale, almost no combination exceeds the
product of its parts. The additive excesses matter for burden: a given difference in one factor is
associated with more excess deaths where the other factor is present. That is a statement about
associations conditional on a crash, not about what an intervention would achieve, and it does
not show biological synergy.

## 8. Limitations

Behaviours are police-recorded after the crash; belt use is partly self-reported by survivors;
CRSS alcohol is imputed. The models condition on a police-reported crash and cannot show how
combinations affect crash occurrence. Covariate adjustment differs by unit (crash-level
analyses adjust for the vehicle mix, person-level ones for age, sex and vehicle type) because
the relevant confounders differ.
