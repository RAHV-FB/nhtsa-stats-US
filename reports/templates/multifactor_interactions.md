# How factors combine: two-, three- and four-factor analyses at the right observation level

*Phase 2 report (research questions E and F; `docs/research_plan_phase2.md` §5.3). CRSS
police-reported crashes 2016–2024, survey-weighted; every number is read from
`outputs/tables/multifactor/` when this report is rendered. All risks are **adjusted
associations**: standardised predictive margins from survey logistic models, conditional on a
police-reported crash, not causal effects.*

## Summary

1. **The unit matters.** The same recorded behaviour has different associations depending on
   whose death is the outcome. Alcohol involvement of the responsible driver carries a risk ratio
   of {{multifactor/victims|victim=crash fatal (any driver's behaviour)|rr_alcohol_only|ci:1@rr_alcohol_only}}
   for the crash being fatal, {{multifactor/victims|victim=driver killed (own behaviour)|rr_alcohol_only|ci:1@rr_alcohol_only}}
   for the driver's own death, {{multifactor/victims|victim=passenger killed (their driver's behaviour)|rr_alcohol_only|ci:1@rr_alcohol_only}}
   for a passenger's death, {{multifactor/victims|victim=other-vehicle occupant killed (the other driver's behaviour)|rr_alcohol_only|ci:1@rr_alcohol_only}}
   for the death of an occupant of the *other* vehicle, and only
   {{multifactor/victims|victim=pedestrian killed (striking driver's behaviour)|rr_alcohol_only|ci:2@rr_alcohol_only}}
   for the death of a struck pedestrian (environment held fixed).
2. **Speeding and alcohol combine super-additively but sub-multiplicatively at the crash level.**
   Crashes in which a driver exceeded the limit and alcohol was involved are fatal
   {{multifactor/margins|analysis=crash_exceeded_x_alcohol;combination=exceeded + alcohol|rr_vs_none|ci:1}}
   times as often as crashes with neither, against
   {{multifactor/margins|analysis=crash_exceeded_x_alcohol;combination=exceeded|rr_vs_none|.1f}}
   for exceedance alone and {{multifactor/margins|analysis=crash_exceeded_x_alcohol;combination=alcohol|rr_vs_none|.1f}}
   for alcohol alone: more excess deaths than the two excesses added up (additive contrast
   {{multifactor/interactions|analysis=crash_exceeded_x_alcohol;contrast=exceeded x alcohol|additive_contrast|cix1000:1}}
   per 1,000 crashes), but a smaller ratio than their product (ratio of risk ratios
   {{multifactor/interactions|analysis=crash_exceeded_x_alcohol;contrast=exceeded x alcohol|multiplicative_ratio|ci:2}}).
3. **When one driver is the only driver, the two behaviours combine multiplicatively.** In
   single-vehicle crashes the ratio of risk ratios is
   {{multifactor/interactions|analysis=sv_driver_exceeded_x_alcohol;contrast=exceeded x alcohol|multiplicative_ratio|ci:2}}:
   no departure from multiplicativity. The crash-level sub-multiplicativity is partly an artefact
   of attributing two different drivers' behaviours to one crash.
4. **Belt non-use dominates every occupant combination, and combines super-additively with
   behaviour.** For light-vehicle drivers, the standardised risk of dying is
   {{multifactor/margins|analysis=lpv_driver_speeding_x_alcohol_x_unbelted;combination=none|adj_risk|cipct:2}}
   with none of the three factors and
   {{multifactor/margins|analysis=lpv_driver_speeding_x_alcohol_x_unbelted;combination=speeding + alcohol + unbelted|adj_risk|cipct:1}}
   with all three. The three-way additive contrast is not distinguishable from zero.
5. **Four-factor combinations involving drugs cannot be estimated.** Among drivers with known
   police drug status, the speeding + drugs cell (belted, no alcohol) has
   {{multifactor/margins|analysis=lpv_driver_drugs_known_4way;combination=speeding + drugs|n_events|.0f}}
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
effect, the product of the exposed indicators for every subset of factors (so the factors are
saturated among themselves), and the adjustment covariates. The 2^k standardised risks are the
mean predicted risk over the analysis population with every unit set to each combination.
Additive interaction is the k-way contrast Σ(−1)^(k−|s|) p_s (for two factors
p11 − p10 − p01 + p00); multiplicative interaction is the same contrast on the log scale
(for two factors RR11 / (RR10 · RR01)). Combinations with fewer than 30 sample units or 10
deaths are withheld with every contrast using them. Holm adjustment across all contrasts of the
six registered analyses, separately per scale.

{{mdtable:multifactor/analyses||analysis:Analysis:;population:Population:;outcome:Outcome:;n:n:,.0f;n_events:Deaths:,.0f;registered:Registered:}}

## 2. Crash level: exceeding the limit × alcohol

{{mdtable:multifactor/margins|analysis=crash_exceeded_x_alcohol|combination:Combination:;n:Crashes (sample):,.0f;n_events:Fatal:,.0f;crude_rate:Crude fatal rate:cipct:2@crude_rate;adj_risk:Standardised fatal risk:cipct:2;rr_vs_none:RR vs neither:ci:1}}

* Additive contrast: {{multifactor/interactions|analysis=crash_exceeded_x_alcohol;contrast=exceeded x alcohol|additive_contrast|cix1000:1}} per 1,000 crashes (Holm p {{multifactor/interactions|analysis=crash_exceeded_x_alcohol;contrast=exceeded x alcohol|additive_contrast_p_holm|.2g}}).
* Ratio of risk ratios: {{multifactor/interactions|analysis=crash_exceeded_x_alcohol;contrast=exceeded x alcohol|multiplicative_ratio|ci:2}} (Holm p {{multifactor/interactions|analysis=crash_exceeded_x_alcohol;contrast=exceeded x alcohol|multiplicative_ratio_p_holm|.2g}}).
* Exceedance within alcohol strata: {{multifactor/single_factor|analysis=crash_exceeded_x_alcohol;factor=exceeded;other_factors=alcohol=no|rr|ci:2}} without and {{multifactor/single_factor|analysis=crash_exceeded_x_alcohol;factor=exceeded;other_factors=alcohol=yes|rr|ci:2}} with alcohol.

*Checks.* Police-reported alcohol instead of imputed: ratio of RRs
{{multifactor/interactions|analysis=crash_exceeded_x_alcohol_police;contrast=exceeded x alcohol|multiplicative_ratio|ci:2}},
additive {{multifactor/interactions|analysis=crash_exceeded_x_alcohol_police;contrast=exceeded x alcohol|additive_contrast|cix1000:1}}.
Fatal-or-serious outcome: ratio {{multifactor/interactions|analysis=crash_exceeded_x_alcohol_ka;contrast=exceeded x alcohol|multiplicative_ratio|ci:2}},
additive {{multifactor/interactions|analysis=crash_exceeded_x_alcohol_ka;contrast=exceeded x alcohol|additive_contrast|cix1000:1}} per 1,000.

*Competing explanation: is the sub-multiplicativity real?* A crash-level "exceeded × alcohol"
cell mixes crashes in which one driver both sped and drank with crashes in which two different
drivers each did one. §3 removes that ambiguity.

## 3. Driver level, single-vehicle crashes: one driver's own behaviour

{{mdtable:multifactor/margins|analysis=sv_driver_exceeded_x_alcohol|combination:Combination:;n:Drivers (sample):,.0f;n_events:Fatal crashes:,.0f;adj_risk:Standardised fatal risk:cipct:2;rr_vs_none:RR vs neither:ci:2}}

Additive contrast {{multifactor/interactions|analysis=sv_driver_exceeded_x_alcohol;contrast=exceeded x alcohol|additive_contrast|cix1000:1}}
per 1,000 crashes (Holm p {{multifactor/interactions|analysis=sv_driver_exceeded_x_alcohol;contrast=exceeded x alcohol|additive_contrast_p_holm|.2g}});
ratio of RRs {{multifactor/interactions|analysis=sv_driver_exceeded_x_alcohol;contrast=exceeded x alcohol|multiplicative_ratio|ci:2}}.
Within single-vehicle crashes both risk ratios are smaller than at the crash level, because
the crash-level comparison also contrasts *crash types* (alcohol and exceedance are
concentrated in single-vehicle crashes, which are more severe), and the two behaviours combine
multiplicatively. The interpretation that best fits both analyses: the same driver's alcohol and
speed do not "use up" each other's risk; the apparent sub-multiplicativity at the crash level
is mostly a consequence of pooling different drivers and crash types.

## 4. Occupant level: whose behaviour, whose belt

**Light-vehicle drivers** (their own speeding, alcohol and belt use; outcome: the driver dies):

{{mdtable:multifactor/margins|analysis=lpv_driver_speeding_x_alcohol_x_unbelted|combination:Combination:;n:Drivers:,.0f;n_events:Deaths:,.0f;adj_risk:Standardised risk of death:cipct:2;rr_vs_none:RR vs none:ci:1}}

{{mdtable:multifactor/interactions|analysis=lpv_driver_speeding_x_alcohol_x_unbelted|contrast:Contrast:;additive_contrast:Additive (per 1,000):cix1000:1;additive_contrast_p_holm:Holm p:.2g;multiplicative_ratio:Multiplicative ratio:ci:2;multiplicative_ratio_p_holm:Holm p:.2g}}

**Passengers** (the driver's speeding and alcohol; their own belt; outcome: the passenger dies):

{{mdtable:multifactor/margins|analysis=passenger_driver_speeding_x_driver_alcohol_x_unbelted|combination:Combination:;n:Passengers:,.0f;n_events:Deaths:,.0f;adj_risk:Standardised risk of death:cipct:2;rr_vs_none:RR vs none:ci:1}}

{{mdtable:multifactor/interactions|analysis=passenger_driver_speeding_x_driver_alcohol_x_unbelted|contrast:Contrast:;additive_contrast:Additive (per 1,000):cix1000:1;additive_contrast_p_holm:Holm p:.2g;multiplicative_ratio:Multiplicative ratio:ci:2;multiplicative_ratio_p_holm:Holm p:.2g}}

*Reading.* Belt non-use carries by far the largest risk ratio for occupants (about 30 for
drivers, 28 for passengers), much larger than the within-vehicle ratio of about 3
(`reports/alcohol_drugs_restraints.md` §6): across crashes, unbelted occupants are in more
violent crashes and survivors over-report belt use. On the additive scale the pairs involving
belt non-use are positive and, for passengers, Holm-significant: an unbelted passenger of a
drinking or speeding driver has a much larger *excess* risk than either factor alone implies.
On the ratio scale the same pairs are sub-multiplicative. Both statements are correct; they
answer different questions (how many extra deaths vs how many times the risk). The three-way
contrasts are not distinguishable from zero on either scale.

*Sensitivity.* Adding crash configuration (a mediator of speeding and alcohol) reduces every
risk ratio — the driver's unbelted RR from
{{multifactor/margins|analysis=lpv_driver_speeding_x_alcohol_x_unbelted;combination=unbelted|rr_vs_none|.1f}}
to {{multifactor/margins|analysis=lpv_driver_speeding_x_alcohol_x_unbelted_config;combination=unbelted|rr_vs_none|.1f}}
and alcohol from {{multifactor/margins|analysis=lpv_driver_speeding_x_alcohol_x_unbelted;combination=alcohol|rr_vs_none|.1f}}
to {{multifactor/margins|analysis=lpv_driver_speeding_x_alcohol_x_unbelted_config;combination=alcohol|rr_vs_none|.1f}};
part of each association runs through the type of crash. Exceedance instead of any speeding:
{{multifactor/margins|analysis=lpv_driver_exceeded_x_alcohol_x_unbelted;combination=exceeded|rr_vs_none|ci:1}}
for the driver's death (any speeding {{multifactor/margins|analysis=lpv_driver_speeding_x_alcohol_x_unbelted;combination=speeding|rr_vs_none|.1f}}).

## 5. Four factors: speeding × alcohol × drugs × belt (drivers with known police drug status)

{{mdtable:multifactor/margins|analysis=lpv_driver_drugs_known_4way|combination:Combination:;n:Drivers:,.0f;n_events:Deaths:,.0f;adj_risk:Standardised risk of death:cipct:2;flag:Status:}}

This analysis is restricted to the
{{multifactor/analyses|analysis=lpv_driver_drugs_known_4way|share_of_frame|pct:0}} of driver
records with a known police drug code — a subset selected by recording practice (drug status
is recorded more often when impairment is suspected and in severe crashes; see
`reports/alcohol_drugs_restraints.md`). One of 16 combinations lacks support, which removes the
four-way contrast and the speeding × drugs contrasts. The supported pairs show the same pattern
as alcohol: police-recorded drug involvement is associated with the driver's death
({{multifactor/margins|analysis=lpv_driver_drugs_known_4way;combination=drugs|rr_vs_none|ci:1}}
when it is the only factor), and alcohol × drugs is sub-multiplicative
({{multifactor/interactions|analysis=lpv_driver_drugs_known_4way;contrast=alcohol x drugs|multiplicative_ratio|ci:2}}).
Because police drug status is neither complete nor independent of alcohol recording, these
numbers describe police-recorded drug involvement in a selected subset; they are not a drug
effect and are not used for ranking.

## 6. Driver, passenger, other road user: same behaviour, different victims

{{mdtable:multifactor/victims||victim:Victim (behaviour of):;n:n:,.0f;n_events:Deaths:,.0f;risk_neither:Risk with neither:cipct:2@risk_neither;rr_speeding_only:Speeding only, RR:ci:2@rr_speeding_only;rr_alcohol_only:Alcohol only, RR:ci:2@rr_alcohol_only;rr_both:Both, RR:ci:2@rr_both;multiplicative_ratio:Ratio of RRs:ci:2}}

* For **the impaired or speeding driver** and **their passengers**, both behaviours are
  associated with death, alcohol more than speeding (any type).
* For **occupants of the other vehicle** in two-vehicle crashes, the other driver's alcohol is
  strongly associated with death (their own driver's behaviour and belt held fixed); the other
  driver's recorded speeding much less so, and the two combine super-multiplicatively
  (ratio {{multifactor/victims|victim=other-vehicle occupant killed (the other driver's behaviour)|multiplicative_ratio|ci:2}}).
* For **pedestrians**, once the speed limit, light and pedestrian age are held fixed, the
  striking driver's recorded speeding and alcohol add little: the pedestrian's death is
  dominated by impact speed proxies already in the model (the posted limit) and by
  vulnerability. Police-recorded speeding is rare in pedestrian crashes
  ({{multifactor/victims|victim=pedestrian killed (striking driver's behaviour)|n_speeding_only|,.0f}}
  sample pedestrians), so this comparison is imprecise.

**Answer to F (units).** Estimated contributions depend strongly on the observation unit: a
crash-level association combines several drivers' behaviours and several people's deaths, and
should not be quoted as a driver-level or person-level risk.

## 7. Which combinations show interaction (answer to E)

| Combination (unit) | Additive | Multiplicative |
|---|---|---|
| Exceeded × alcohol (crash) | super-additive, Holm p {{multifactor/interactions|analysis=crash_exceeded_x_alcohol;contrast=exceeded x alcohol|additive_contrast_p_holm|.2g}} | sub-multiplicative, Holm p {{multifactor/interactions|analysis=crash_exceeded_x_alcohol;contrast=exceeded x alcohol|multiplicative_ratio_p_holm|.2g}} |
| Exceeded × alcohol (single-vehicle driver) | super-additive, Holm p {{multifactor/interactions|analysis=sv_driver_exceeded_x_alcohol;contrast=exceeded x alcohol|additive_contrast_p_holm|.2g}} | none detected ({{multifactor/interactions|analysis=sv_driver_exceeded_x_alcohol;contrast=exceeded x alcohol|multiplicative_ratio|ci:2}}) |
| Speeding × night (crash) | super-additive, Holm p {{multifactor/interactions|analysis=crash_speeding_x_alcohol_x_night;contrast=speeding x night|additive_contrast_p_holm|.2g}} | none detected |
| Alcohol × night (crash) | none detected | sub-multiplicative, Holm p {{multifactor/interactions|analysis=crash_speeding_x_alcohol_x_night;contrast=alcohol x night|multiplicative_ratio_p_holm|.2g}} |
| Speeding × alcohol × night (crash) | {{multifactor/interactions|analysis=crash_speeding_x_alcohol_x_night;contrast=speeding x alcohol x night|additive_contrast|cix1000:1}} per 1,000 (Holm p {{multifactor/interactions|analysis=crash_speeding_x_alcohol_x_night;contrast=speeding x alcohol x night|additive_contrast_p_holm|.2g}}) | {{multifactor/interactions|analysis=crash_speeding_x_alcohol_x_night;contrast=speeding x alcohol x night|multiplicative_ratio|ci:2}} |
| Speeding × unbelted (driver) | super-additive, Holm p {{multifactor/interactions|analysis=lpv_driver_speeding_x_alcohol_x_unbelted;contrast=speeding x unbelted|additive_contrast_p_holm|.2g}} | sub-multiplicative ({{multifactor/interactions|analysis=lpv_driver_speeding_x_alcohol_x_unbelted;contrast=speeding x unbelted|multiplicative_ratio|ci:2}}) |
| Alcohol × unbelted (driver) | positive ({{multifactor/interactions|analysis=lpv_driver_speeding_x_alcohol_x_unbelted;contrast=alcohol x unbelted|additive_contrast|cix1000:1}} per 1,000; Holm p {{multifactor/interactions|analysis=lpv_driver_speeding_x_alcohol_x_unbelted;contrast=alcohol x unbelted|additive_contrast_p_holm|.2g}}) | sub-multiplicative, Holm p {{multifactor/interactions|analysis=lpv_driver_speeding_x_alcohol_x_unbelted;contrast=alcohol x unbelted|multiplicative_ratio_p_holm|.2g}} |
| Driver alcohol × unbelted (passenger) | super-additive, Holm p {{multifactor/interactions|analysis=passenger_driver_speeding_x_driver_alcohol_x_unbelted;contrast=driver_alcohol x unbelted|additive_contrast_p_holm|.2g}} | {{multifactor/interactions|analysis=passenger_driver_speeding_x_driver_alcohol_x_unbelted;contrast=driver_alcohol x unbelted|multiplicative_ratio|ci:2}} |
| Speeding × alcohol × unbelted (driver; passenger) | not detected | not detected |
| Four-way with drugs | withheld (insufficient support) | withheld |

*Distinguishing genuine interaction from high baselines.* Several combinations look
"unusually deadly" in raw counts simply because each factor has a high risk on its own; the
multiplicative contrasts above show that, on the ratio scale, almost no combination exceeds the
product of its parts. The additive excesses are real in the sense that matters for burden: the
same intervention on one factor removes more deaths where the other factor is present. They do
not show biological synergy.

## 8. Limitations

Behaviours are police-recorded after the crash; belt use is partly self-reported by survivors;
CRSS alcohol is imputed. The models condition on a police-reported crash and cannot show how
combinations affect crash occurrence. Covariate adjustment differs by unit (crash-level
analyses adjust for the vehicle mix, person-level ones for age, sex and vehicle type) because
the relevant confounders differ.
