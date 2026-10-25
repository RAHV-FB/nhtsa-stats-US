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
   for the driver's own death, 4.3 (3.3–5.7)
   for a passenger's death, 3.6 (2.8–4.6)
   for the death of an occupant of the *other* vehicle, and only
   1.22 (0.93–1.60)
   for the death of a struck pedestrian (environment held fixed).
2. **Speeding and alcohol combine super-additively but sub-multiplicatively at the crash level.**
   Crashes in which a driver exceeded the limit and alcohol was involved are fatal
   15.6 (11.8–20.7)
   times as often as crashes with neither, against
   6.8
   for exceedance alone and 4.7
   for alcohol alone: more excess deaths than the two excesses added up (additive contrast
   21.0 (8.6–33.4)
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
   7.3% (5.7–9.2%)
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
six registered analyses, separately per scale.

| Analysis | Population | Outcome | n | Deaths | Registered |
|---|---|---|---|---|---|
| crash_exceeded_x_alcohol | CRSS police-reported crashes | crash fatal | 467,008 | 9,958 | True |
| crash_speeding_x_alcohol_x_night | CRSS police-reported crashes (time known) | crash fatal | 464,470 | 9,839 | True |
| sv_driver_exceeded_x_alcohol | Drivers in single-vehicle crashes (the only driver behaviour in the crash) | crash fatal | 153,015 | 5,471 | True |
| lpv_driver_speeding_x_alcohol_x_unbelted | Drivers of light passenger vehicles (belt use belted, none or unknown) | driver killed | 734,362 | 5,515 | True |
| passenger_driver_speeding_x_driver_alcohol_x_unbelted | Passengers of light passenger vehicles aged 15+ (belt use belted, none or unknown) | passenger killed | 190,327 | 1,449 | True |
| lpv_driver_drugs_known_4way | Drivers of light passenger vehicles with known police drug status (a selected subset) | driver killed | 458,495 | 2,511 | True |
| crash_exceeded_x_alcohol_ka | CRSS police-reported crashes | crash fatal or serious (KA) | 467,008 | 60,345 | False |
| crash_exceeded_x_alcohol_police | CRSS police-reported crashes (police alcohol coding; unknown kept as a level) | crash fatal | 467,008 | 9,958 | False |
| lpv_driver_exceeded_x_alcohol_x_unbelted | Drivers of light passenger vehicles | driver killed | 734,362 | 5,515 | False |
| lpv_driver_speeding_x_alcohol_x_unbelted_config | Drivers of light passenger vehicles | driver killed | 734,362 | 5,515 | False |

## 2. Crash level: exceeding the limit × alcohol

| Combination | Crashes (sample) | Fatal | Crude fatal rate | Standardised fatal risk | RR vs neither |
|---|---|---|---|---|---|
| none | 376,544 | 5,444 | 0.39% (0.34–0.45%) | 0.40% (0.35–0.47%) | 1.0 (1.0–1.0) |
| alcohol | 23,233 | 1,845 | 2.59% (2.19–3.05%) | 1.90% (1.58–2.28%) | 4.7 (3.9–5.7) |
| exceeded | 4,593 | 555 | 3.84% (3.17–4.65%) | 2.73% (2.21–3.37%) | 6.8 (5.6–8.1) |
| exceeded + alcohol | 1,291 | 316 | 10.23% (8.35–12.49%) | 6.32% (4.97–8.00%) | 15.6 (11.8–20.7) |

* Additive contrast: 21.0 (8.6–33.4) per 1,000 crashes (Holm p 0.023).
* Ratio of risk ratios: 0.49 (0.40–0.61) (Holm p 3.1e-07).
* Exceedance within alcohol strata: 6.76 (5.60–8.15) without and 3.33 (2.66–4.18) with alcohol.

*Checks.* Police-reported alcohol instead of imputed: ratio of RRs
0.41 (0.32–0.52),
additive 13.5 (3.3–23.6).
Fatal-or-serious outcome: ratio 0.70 (0.61–0.82),
additive 47.2 (22.3–72.0) per 1,000.

*Competing explanation: is the sub-multiplicativity real?* A crash-level "exceeded × alcohol"
cell mixes crashes in which one driver both sped and drank with crashes in which two different
drivers each did one. §3 removes that ambiguity.

## 3. Driver level, single-vehicle crashes: one driver's own behaviour

| Combination | Drivers (sample) | Fatal crashes | Standardised fatal risk | RR vs neither |
|---|---|---|---|---|
| none | 115,513 | 3,210 | 0.88% (0.76–1.02%) | 1.00 (1.00–1.00) |
| alcohol | 10,578 | 776 | 1.82% (1.50–2.22%) | 2.08 (1.66–2.60) |
| exceeded | 2,483 | 274 | 3.09% (2.49–3.84%) | 3.52 (2.93–4.24) |
| exceeded + alcohol | 823 | 190 | 7.28% (5.67–9.30%) | 8.29 (6.22–11.05) |

Additive contrast 32.4 (15.5–49.3)
per 1,000 crashes (Holm p 0.0064);
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
| none | 593,372 | 1,814 | 0.07% (0.06–0.09%) | 1.0 (1.0–1.0) |
| unbelted | 13,134 | 1,173 | 2.51% (2.08–3.03%) | 35.4 (30.7–40.8) |
| alcohol | 14,418 | 342 | 0.44% (0.34–0.56%) | 6.2 (4.7–8.2) |
| alcohol + unbelted | 2,639 | 445 | 4.32% (3.31–5.62%) | 61.0 (46.4–80.2) |
| speeding | 32,467 | 270 | 0.15% (0.12–0.18%) | 2.1 (1.6–2.7) |
| speeding + unbelted | 2,443 | 357 | 4.27% (3.68–4.95%) | 60.2 (47.5–76.5) |
| speeding + alcohol | 2,876 | 92 | 0.62% (0.44–0.86%) | 8.7 (5.8–13.1) |
| speeding + alcohol + unbelted | 1,051 | 234 | 7.26% (5.70–9.19%) | 102.4 (75.0–139.9) |

| Contrast | Additive (per 1,000) | Holm p | Multiplicative ratio | Holm p |
|---|---|---|---|---|
| speeding x alcohol | 1.0 (-0.8 to 2.8) | 1 | 0.67 (0.49–0.93) | 0.24 |
| speeding x unbelted | 16.8 (9.1–24.6) | 0.0013 | 0.81 (0.68–0.98) | 0.35 |
| alcohol x unbelted | 14.5 (3.6–25.3) | 0.14 | 0.28 (0.21–0.36) | 3.7e-11 |
| speeding x alcohol x unbelted | 10.7 (-5.8 to 27.2) | 1 | 1.46 (0.94–2.28) | 0.92 |

**Passengers** (the driver's speeding and alcohol; their own belt; outcome: the passenger dies):

| Combination | Passengers | Deaths | Standardised risk of death | RR vs none |
|---|---|---|---|---|
| none | 149,360 | 436 | 0.07% (0.06–0.09%) | 1.0 (1.0–1.0) |
| unbelted | 5,206 | 309 | 2.11% (1.75–2.56%) | 29.8 (25.3–35.2) |
| driver_alcohol | 3,018 | 62 | 0.44% (0.33–0.57%) | 6.1 (4.4–8.6) |
| driver_alcohol + unbelted | 794 | 130 | 6.81% (5.36–8.62%) | 96.1 (71.9–128.5) |
| driver_speeding | 7,585 | 60 | 0.17% (0.12–0.25%) | 2.4 (1.7–3.6) |
| driver_speeding + unbelted | 1,101 | 110 | 4.82% (3.92–5.91%) | 68.0 (53.8–85.9) |
| driver_speeding + driver_alcohol | 771 | 40 | 1.35% (0.84–2.16%) | 19.0 (10.8–33.5) |
| driver_speeding + driver_alcohol + unbelted | 434 | 74 | 8.12% (5.85–11.16%) | 114.5 (78.6–166.8) |

| Contrast | Additive (per 1,000) | Holm p | Multiplicative ratio | Holm p |
|---|---|---|---|---|
| driver_speeding x driver_alcohol | 8.1 (1.4–14.8) | 0.24 | 1.27 (0.65–2.48) | 1 |
| driver_speeding x unbelted | 26.0 (17.6–34.5) | 4e-06 | 0.93 (0.63–1.37) | 1 |
| driver_alcohol x unbelted | 43.3 (27.5–59.2) | 3.9e-05 | 0.52 (0.37–0.74) | 0.0097 |
| driver_speeding x driver_alcohol x unbelted | -22.1 (-49.4 to 5.2) | 0.98 | 0.41 (0.20–0.85) | 0.24 |

*Reading.* Belt non-use carries by far the largest risk ratio for occupants
(35
for drivers, 30
for passengers), much larger than the within-vehicle ratio of about 3
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
35.4
to 24.0
and alcohol from 6.2
to 4.0;
part of each association runs through the type of crash. Exceedance instead of any speeding:
8.9 (6.4–12.5)
for the driver's death (any speeding 2.1).

## 5. Four factors: speeding × alcohol × drugs × belt (drivers with known police drug status)

| Combination | Drivers | Deaths | Standardised risk of death | Status |
|---|---|---|---|---|
| none | 394,842 | 933 | 0.05% (0.04–0.06%) | — |
| unbelted | 7,456 | 475 | 1.83% (1.38–2.43%) | — |
| drugs | 1,729 | 40 | 0.43% (0.25–0.76%) | — |
| drugs + unbelted | 395 | 55 | 4.76% (2.99–7.48%) | — |
| alcohol | 4,800 | 77 | 0.29% (0.22–0.39%) | — |
| alcohol + unbelted | 902 | 109 | 3.33% (2.26–4.86%) | — |
| alcohol + drugs | 1,475 | 62 | 0.96% (0.59–1.54%) | — |
| alcohol + drugs + unbelted | 490 | 102 | 7.69% (4.66–12.44%) | — |
| speeding | 16,813 | 93 | 0.09% (0.07–0.13%) | — |
| speeding + unbelted | 1,090 | 116 | 3.39% (2.55–4.50%) | — |
| speeding + drugs | 297 | 6 | — | suppressed: fewer than 30 sample units or 10 events |
| speeding + drugs + unbelted | 123 | 17 | 5.25% (2.84–9.52%) | — |
| speeding + alcohol | 1,010 | 23 | 0.50% (0.29–0.86%) | — |
| speeding + alcohol + unbelted | 358 | 65 | 6.60% (4.36–9.86%) | — |
| speeding + alcohol + drugs | 313 | 20 | 1.92% (0.85–4.26%) | — |
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
Holm p 0.034).
Because police drug status is neither complete nor independent of alcohol recording, these
numbers describe police-recorded drug involvement in a selected subset; they are not a drug
effect and are not used for ranking.

## 6. Driver, passenger, other road user: same behaviour, different victims

| Victim (behaviour of) | n | Deaths | Risk with neither | Speeding only, RR | Alcohol only, RR | Both, RR | Ratio of RRs |
|---|---|---|---|---|---|---|---|
| crash fatal (any driver's behaviour) | 467,008 | 9,958 | 0.40% (0.35–0.47%) | 1.99 (1.63–2.44) | 4.66 (3.87–5.61) | 7.00 (5.25–9.33) | 0.75 (0.62–0.91) |
| driver killed (own behaviour) | 734,451 | 5,515 | 0.14% (0.12–0.17%) | 2.05 (1.65–2.54) | 2.72 (2.07–3.58) | 4.24 (3.10–5.80) | 0.76 (0.59–0.98) |
| passenger killed (their driver's behaviour) | 192,534 | 1,468 | 0.14% (0.12–0.17%) | 2.74 (2.19–3.42) | 4.34 (3.30–5.72) | 6.27 (4.31–9.13) | 0.53 (0.36–0.77) |
| other-vehicle occupant killed (the other driver's behaviour) | 639,410 | 3,040 | 0.10% (0.09–0.12%) | 1.31 (0.95–1.83) | 3.60 (2.84–4.58) | 7.33 (4.78–11.25) | 1.55 (1.03–2.32) |
| pedestrian killed (striking driver's behaviour) | 24,651 | 1,777 | 8.05% (6.86–9.43%) | 1.03 (0.71–1.50) | 1.22 (0.93–1.60) | 1.58 (0.86–2.90) | 1.25 (0.58–2.66) |

* For **the impaired or speeding driver** and **their passengers**, both behaviours are
  associated with death, alcohol more than speeding (any type).
* *(This table is exploratory; it is not part of the Holm family.)* For **occupants of the other
  vehicle** in two-vehicle crashes, the other driver's alcohol is
  strongly associated with death (their own driver's behaviour and belt held fixed); the other
  driver's recorded speeding much less so, and the two combine super-multiplicatively
  (ratio 1.55 (1.03–2.32)).
* For **pedestrians**, once the speed limit, light and pedestrian age are held fixed, the
  associations with the striking driver's recorded speeding and alcohol are imprecise and much
  smaller than for occupants (intervals compatible with no association and with modest ones, but
  not with occupant-sized ratios). One hypothesis is that the posted limit already captures much
  of the impact-speed variation that matters for a pedestrian; the data cannot test it.
  Police-recorded speeding is rare in pedestrian crashes
  (798
  sample pedestrians), so this comparison is imprecise.

**Answer to F (units).** Estimated contributions depend strongly on the observation unit: a
crash-level association combines several drivers' behaviours and several people's deaths, and
should not be quoted as a driver-level or person-level risk.

## 7. Which combinations show interaction (answer to E)

Every registered contrast, with Holm-adjusted p-values (a contrast is called "detected" below
only if its Holm p < 0.05):

| Analysis | Contrast | Additive (per 1,000) | Holm p | Ratio of RRs | Holm p | Status |
|---|---|---|---|---|---|---|
| crash_exceeded_x_alcohol | exceeded x alcohol | 21.0 (8.6–33.4) | 0.023 | 0.49 (0.40–0.61) | 3.1e-07 | — |
| crash_speeding_x_alcohol_x_night | speeding x alcohol | 2.9 (-4.1 to 9.8) | 1 | 0.66 (0.51–0.84) | 0.023 | — |
| crash_speeding_x_alcohol_x_night | speeding x night | 4.8 (2.7–6.8) | 0.0006 | 1.04 (0.84–1.30) | 1 | — |
| crash_speeding_x_alcohol_x_night | alcohol x night | -0.9 (-4.2 to 2.5) | 1 | 0.49 (0.40–0.59) | 6.9e-08 | — |
| crash_speeding_x_alcohol_x_night | speeding x alcohol x night | 8.3 (-0.6 to 17.3) | 0.68 | 1.31 (0.95–1.82) | 0.92 | — |
| sv_driver_exceeded_x_alcohol | exceeded x alcohol | 32.4 (15.5–49.3) | 0.0064 | 1.13 (0.84–1.53) | 1 | — |
| lpv_driver_speeding_x_alcohol_x_unbelted | speeding x alcohol | 1.0 (-0.8 to 2.8) | 1 | 0.67 (0.49–0.93) | 0.24 | — |
| lpv_driver_speeding_x_alcohol_x_unbelted | speeding x unbelted | 16.8 (9.1–24.6) | 0.0013 | 0.81 (0.68–0.98) | 0.35 | — |
| lpv_driver_speeding_x_alcohol_x_unbelted | alcohol x unbelted | 14.5 (3.6–25.3) | 0.14 | 0.28 (0.21–0.36) | 3.7e-11 | — |
| lpv_driver_speeding_x_alcohol_x_unbelted | speeding x alcohol x unbelted | 10.7 (-5.8 to 27.2) | 1 | 1.46 (0.94–2.28) | 0.92 | — |
| passenger_driver_speeding_x_driver_alcohol_x_unbelted | driver_speeding x driver_alcohol | 8.1 (1.4–14.8) | 0.24 | 1.27 (0.65–2.48) | 1 | — |
| passenger_driver_speeding_x_driver_alcohol_x_unbelted | driver_speeding x unbelted | 26.0 (17.6–34.5) | 4e-06 | 0.93 (0.63–1.37) | 1 | — |
| passenger_driver_speeding_x_driver_alcohol_x_unbelted | driver_alcohol x unbelted | 43.3 (27.5–59.2) | 3.9e-05 | 0.52 (0.37–0.74) | 0.0097 | — |
| passenger_driver_speeding_x_driver_alcohol_x_unbelted | driver_speeding x driver_alcohol x unbelted | -22.1 (-49.4 to 5.2) | 0.98 | 0.41 (0.20–0.85) | 0.24 | — |
| lpv_driver_drugs_known_4way | speeding x alcohol | 1.7 (-1.1 to 4.5) | 1 | 0.96 (0.49–1.89) | 1 | — |
| lpv_driver_drugs_known_4way | speeding x drugs | — | — | — | — | withheld: a combination lacks support |
| lpv_driver_drugs_known_4way | speeding x unbelted | 15.2 (5.6–24.8) | 0.04 | 1.04 (0.67–1.62) | 1 | — |
| lpv_driver_drugs_known_4way | alcohol x drugs | 2.8 (-1.2 to 6.9) | 1 | 0.40 (0.23–0.71) | 0.034 | — |
| lpv_driver_drugs_known_4way | alcohol x unbelted | 12.6 (1.3–23.8) | 0.36 | 0.33 (0.21–0.53) | 0.00042 | — |
| lpv_driver_drugs_known_4way | drugs x unbelted | 25.4 (2.3–48.5) | 0.36 | 0.32 (0.15–0.66) | 0.044 | — |
| lpv_driver_drugs_known_4way | speeding x alcohol x drugs | — | — | — | — | withheld: a combination lacks support |
| lpv_driver_drugs_known_4way | speeding x alcohol x unbelted | 15.5 (-12.3 to 43.2) | 1 | 1.11 (0.44–2.80) | 1 | — |
| lpv_driver_drugs_known_4way | speeding x drugs x unbelted | — | — | — | — | withheld: a combination lacks support |
| lpv_driver_drugs_known_4way | alcohol x drugs x unbelted | 11.6 (-24.4 to 47.5) | 1 | 2.22 (0.87–5.65) | 0.92 | — |
| lpv_driver_drugs_known_4way | speeding x alcohol x drugs x unbelted | — | — | — | — | withheld: a combination lacks support |

Detected, by this criterion: exceedance × alcohol at crash level (super-additive and
sub-multiplicative) and for single-vehicle drivers (super-additive only); speeding × night
(super-additive); alcohol × night and speeding × alcohol at crash level (sub-multiplicative);
belt non-use × speeding (super-additive, drivers and passengers); belt non-use × alcohol
(sub-multiplicative for drivers; super-additive and sub-multiplicative for passengers); and,
in the selected drug-known subset, speeding × unbelted (super-additive) and alcohol × drugs,
alcohol × unbelted and drugs × unbelted (sub-multiplicative).
No three-way contrast is detected; the four-way contrast is withheld.

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
