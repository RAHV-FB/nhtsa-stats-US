# Limitations and unidentifiable quantities

This project is deliberately explicit about what the supplied FARS and CRSS archives cannot
show. The limitations below are research findings in their own right: they define which
policy questions require data that do not exist in this repository.

## 1. Quantities that are not identifiable from these data

| Quantity | Why not | What the project does instead |
|---|---|---|
| Probability of a crash per trip, mile, hour or driver | No exposure data (travel, licensing, vehicle-miles) in either system | Relative involvement by quasi-induced exposure (RQ7) under explicit assumptions; severity *given* a crash |
| P(fatal \| crash) from FARS | FARS contains only fatal crashes | Severity models use CRSS; FARS is used for counts and composition |
| Effect of speed cameras, sobriety checkpoints, roadside drug testing, belt enforcement, campaigns | No camera locations, enforcement intensity, checks performed, citations, campaign exposure or costs anywhere in the archives (checked: `outputs/audit/column_inventory.csv` contains no such fields) | Evidence ledger restating measured associations; observed deaths by overlapping segment; no effect is estimated |
| Lives saved by any intervention | Requires the above | None reported; deaths in each segment are counts, not preventable fractions |
| Causal effect of speeding or alcohol on severity | Observational data; behaviours recorded by police after the crash; unmeasured confounding (travel speed, vehicle mass, occupant frailty beyond age) | Adjusted associations, sensitivity and bias analysis; the within-vehicle belt analysis is the closest design to a causal estimate and has its own caveats |
| Costs and monetary values | No cost data in the repository | None |

## 2. Measurement

* **Severity-dependent ascertainment.** Recording differs by severity, and not in one direction.
  Toxicology testing of killed drivers and speeding as recorded by FARS are more complete in severe
  crashes, but the police-recorded alcohol, drug and distraction fields in CRSS are *more* often
  unknown in fatal crashes than in less severe ones (`measurement/unknown_by_severity`: alcohol
  unknown in about half of fatal crashes against about a quarter at lower severities; drugs,
  distraction and speeding show the same direction). Whether
  sensitivity is higher in fatal crashes, as the bias analyses assume, is not tested by these data.
  Evidence from this project:
  CRSS records speeding in fewer *fatal* crashes than FARS does for the same population (FARS
  analysts use more sources; `measurement/`); alcohol tests are given to most killed drivers but
  to about a quarter of surviving drivers, and drug tests show a similar gap
  (`measurement/fars_testing`; the lowest values are 2024, whose toxicology records are
  incomplete in these archives). A quantitative bias
  analysis shows the speeding–severity association is fragile to plausible differential
  recording, while the alcohol association is robust (see `reports/findings.md`).
* **Coding breaks.** CRSS police-reported alcohol (2019), drug involvement (2019–2020),
  distraction (2017–2020), junction coding (2017–2021, worst in 2019), traffic-control
  coding, CRSS surface "not reported" (rising every year from 2020), FARS rollover (2022), restraint/helmet (2019
  move of helmet codes), body type (2017 pickup merge), and several label rewordings. Each is
  documented in `docs/variable_harmonization.md` and handled by harmonisation, imputed
  versions, explicit unknown levels or exclusion from trend claims.
* **Imputed severity.** CRSS severity outcomes use NHTSA's single imputation (`MAXSEV_IM`,
  `INJSEV_IM`), whose weighted fatal total reproduces the FARS count; the unimputed field
  treats crashes containing a person of unknown severity as non-fatal and falls
  short by up to about 13% in some years. The imputation rests on few crashes: only a few dozen sampled crashes a year are
  imputed fatal, but they carry large weights and make up from under 1% to about 12% of the
  weighted fatal total depending on the year (largest in 2017 and 2019–2020). Their imputation variance is not included in the
  design-based standard errors, so year-specific fatal and KA shares are somewhat more
  uncertain than their intervals suggest. Trend statements are therefore also checked
  against a strict complete-case outcome.
* **Unknown values as proxies for post-crash events.** Several "unknown" levels are
  concentrated in hit-and-run crashes, so they partly encode a driver leaving the scene, which
  happens after the crash. Nearly all CRSS crashes with a driver of unreported age are hit-and-run
  (`docs/variable_harmonization.md`), so CRSS driver-age flags use NHTSA's imputed age. Among
  crashes with other unknown levels, the weighted hit-and-run shares in 2016–2021 are
  high (`ml/hit_and_run_proxy`: about 70% to over 90% for missing vehicle age, motorcycle and
  heavy-vehicle involvement, time of day and speeding). The other unknown levels are kept as
  their own categories (never merged with "no") and are not interpreted; dropping them from the
  prediction models changes test discrimination only negligibly (`docs/model_validation.md`).
* **Distraction and drug involvement** are unknown or not reported for a large share of drivers
  (roughly half, `measurement/unknown_by_severity`) in recent years and their unknown share changed sharply; they are not used as exposures in the
  Phase-1 severity and prediction models. Phase-2 analyses that include police-reported drugs
  report them only as coding sensitivities (`drugs/crss_bounds`, `drugs/crss_adjusted`: how far
  the estimate moves with the allocation of unknowns) or within the selected complete-case subset
  of drivers with known drug status (the four-factor model in `multifactor/`); the reports state
  that neither is a drug effect. Drug *presence* in a toxicology result is not impairment.
* **Restraint use** among surviving occupants is largely self-reported to police; reported
  belt use among uninjured CRSS occupants (about 99%) is implausibly high, so person-level belt
  associations in CRSS are likely inflated. The FARS within-vehicle analysis is less affected
  but survivor misreporting is still possible (sensitivity analysis provided).
* **Police-reported speeding** combines exceeding the limit and "too fast for conditions";
  travel speed is unknown for most vehicles, so speed itself cannot be modelled.
* **CRSS urbanicity** describes the sampling area (PSU), not the road; FARS rural/urban
  describes the road. They are different concepts and are never compared directly.
* **FARS 2024** shows a jump in alcohol-test status "unknown" among killed drivers (about
  double the 2020–2023 level; `measurement/fars_testing`), consistent with pending toxicology; 2024 alcohol figures are less
  complete.

## 3. Design and inference

* CRSS variance estimation uses the with-replacement approximation with 42 design degrees
  of freedom; small domains (< 30 sample crashes) are suppressed and high-RSE estimates
  flagged. CRSS 2016 was a transition sample (fewer PSUs).
* Pooling nine years uses the same PSUs; year effects are included in models, but changes in
  reporting practice across years are only partly captured.
* The primary CRSS outcome is NHTSA's imputed maximum severity (`MAXSEV_IM`); only crashes
  it codes as unknown or died-prior (a fraction of 1%) are excluded. The sensitivity analysis is the
  strict complete case (`fatal_cc`, `ka_cc`), which drops under 10% of crashes, and which ones
  depends on the outcome: a crash drops out only when someone's severity is unknown and nobody
  died. It is a bound on the definition, not a better estimate. Where the two definitions
  disagree (the 2023–24 excess in RQ5, crude night and weekend RRs in RQ4), both are reported.
* NHTSA's single imputations (`*_IM`, CRSS) understate variance by roughly the imputed
  fraction; their imputation models are not documented in the archives. For alcohol there is
  indirect evidence that the imputation uses severity, directly or through correlated
  circumstances: among crashes whose police-reported alcohol is unknown, the imputed "yes"
  is several times as common in fatal as in non-fatal crashes, about as steep as the gradient
  among police-reported records (`ml/alcohol_imputation_check`). Adjusted associations with imputed alcohol may therefore be
  overstated; the police-reported coding, analysed by coding period, is the check. Imputed
  driver age may behave the same way; this was not tested.
* Multiple testing: interaction analyses are pre-specified and adjusted (Holm, BH);
  exploratory results are labelled as such.

## 4. Confounding and interpretation

* Adjusted associations condition on the recorded covariates only. Unmeasured: travel speed,
  impact speed and direction, vehicle mass and crashworthiness (beyond body type and age),
  occupant health, EMS response time, road geometry detail in CRSS.
* Crash configuration (e.g. pedestrian, head-on) is treated as a potential mediator;
  associations "net of configuration" are not direct causal effects.
* Attributable fractions are severity-pathway, model-based quantities that assume no
  unmeasured confounding and correct measurement; they omit any effect on crash occurrence.
  Scaling to FARS deaths assumes the CRSS model fraction applies to the FARS census.
* Quasi-induced exposure assumes non-culpable drivers represent drivers on the road and that
  police code pre-crash actions (speeding, critical event, driver errors) without bias by
  group. The non-culpable pool is dominated by drivers struck from behind, so it reflects
  congested traffic more than all driving; drivers less able to avoid others' errors may be
  over-represented in it (pushing their ratio down); single-vehicle crashes, where young,
  alcohol-involved and night-time crashes concentrate, are outside the design; and
  hit-and-run crashes are excluded. The imputed alcohol field cannot support within-crash
  contrasts after the 2019–2020 coding break, so alcohol is reported by coding period.
  Crash-level conditions cannot be assessed by QIE at all.

## 5. Generalisation

* All CRSS results concern **police-reported** crashes; unreported minor crashes are outside
  the frame, and changes in reporting (e.g. in 2020) change the denominator.
* Within-vehicle (FARS) estimates apply to crashes severe enough to kill at least one
  occupant.
* Prediction models estimate risk *given* a reported crash; they cannot predict whether a
  particular trip will end in a crash.

## 6. What additional information would most improve the evidence

1. Exposure data (vehicle-miles by road class, time and driver group) — would convert
   severity and involvement measures into risk per unit of travel.
2. Enforcement and intervention records linked by place and time (camera sites, checkpoint
   schedules, citations) — the minimum needed to estimate any programme effect.
3. Measured travel/impact speed (event data recorders) — would replace the police
   "speeding-related" judgement.
4. Consistent toxicology for surviving drivers — would make alcohol/drug severity
   comparisons unbiased.
5. Programme cost data — would allow cost-effectiveness without user assumptions.

## 7. Phase 2 additions

* **No individual attribution.** No analysis identifies the cause of a particular death or the
  share of a death "due to" each factor. Shapley allocations in `contributions/` and
  `speeding/shapley` are allocations of model quantities; they change with the scale (risk
  difference vs log risk ratio), the reference case and the factor set, and are reported precisely
  to show this. A Shapley value averages over all orders of adding factors, so it does not depend
  on one order; `speeding/shapley` additionally reports the range of each block's share over
  single orderings.
* **Drugs.** CRSS has only police-reported drug involvement (more than half unknown after 2019) and the
  police co-record drugs with alcohol several times more often than toxicology finds them
  together. No drug severity association, attributable fraction or ranking is reported as a
  finding (the drug risk ratios in `drugs/` are bounds and coding sensitivities, and those in
  `multifactor/` describe a selected subset; the reports state that they do not identify a drug
  effect); the
  only drug–alcohol comparison is conditional on a fatal crash and on testing, in four
  high-testing states.
* **Mediator adjustment.** Crash configuration lies on plausible pathways from speeding and
  alcohol to death; estimates with and without it bracket "net of configuration" and "closer to
  total" associations; neither is a causal direct or total effect.
* **Selection on fatality.** FARS-only comparisons (factor co-occurrence among fatal crashes,
  killed-vs-surviving drivers) condition on a common consequence of the factors; Phase 2 shows
  the speeding–alcohol association changes when fatal crashes alone are examined
  (`speeding/selection_by_fatality`).
* **Predictive contribution.** Measured on a temporal split with the model fixed; Shapley values
  split information shared by correlated blocks evenly and are not causal importance.
* **Sparse combinations.** Four-factor combinations with drugs and several case-explorer cells
  are withheld for lack of support; they are reported as unsupported, not as zero.
* **Stage D.** Post-crash survival effects are not identifiable: EMS times are recorded only for
  fatal crashes (FARS) and not at all in CRSS.

## 8. Deaths analysis (November 2026)

* **Composition, not risk.** `deaths/` tables describe how the people killed are distributed
  across behaviours, road users, vehicles, places and states. Without exposure they cannot show
  that one state, road, vehicle or group is more dangerous per mile, trip or person.
* **Lives belts and helmets would have saved** are model-based expectations for the people who
  died, from within-vehicle effectiveness estimates. They are not the effect of any law,
  enforcement, campaign or other intervention (section 1 still applies). The belt estimate depends
  strongly on how accurately surviving occupants' belt use is recorded (scenarios in
  `deaths/potential_lives`), and the front-seat effectiveness is applied to every seat.
* **Driver records** come from each driver's state file and count convictions, suspensions and
  crashes in the five years before the crash. They miss arrests without conviction, offences
  reduced by plea and offences recorded in other states, so prior drink-driving and speeding are
  undercounted. The three suspension fields used here (`PREV_SUS1–3`) start in 2018.
* **Victim roles** depend on which vehicle is coded speeding or has a driver at .08 or more; for
  alcohol the assignment changes across imputations and is averaged.
* **Recording differs by state.** Speeding coding varies between police agencies, and the share
  of occupants killed whose belt use was not recorded ranges from almost none to about one in five
  by state (`deaths/states`, column `restraint_unknown_share`: a maximum of about 21% among the states and about
  27% including DC), so state shares are not strictly comparable.
* **Vehicle age.** The rising share of deaths in vehicles 18 or more years old partly reflects the
  ageing of the fleet, which the data do not measure; the adjusted CRSS risk ratio is the evidence
  on risk, and it is an association conditional on a police-reported crash.

## 9. Additions from the November 2026 red-team review

These limitations were identified by `docs/red_team_2026-11.md` and added without removing any
earlier item. Where a number is given it is approximate; the named table has the value.

* **The four-factor union depends on undetermined drug status.** Drug status is undetermined for
  a large share of deaths (`contributions/fars_overlap_treatments`). Scoring undetermined as
  drug-negative gives a lower union of deaths with at least one factor (a floor); scoring it
  positive gives a much higher one (a ceiling); restricting to deaths whose drug factor is
  determinate and the three measured factors without drugs give the other values in that table.
  The published union and the share of deaths that also involve another factor are floors.
* **Belt and helmet misreporting scenarios were one-sided and pooled.** The original scenarios
  moved only belted-coded survivors, and the pooled belt estimate averages different crash types.
  `matched/belt_misreporting_two_sided_dpc` and `matched/helmet_misreporting_dpc` add the reverse
  error (unbelted or unhelmeted-coded deaths who were protected) with tipping points, and
  `matched/belt_by_crash_type` gives the belt estimate by crash type (from about half in multi-vehicle angle
  crashes to more than 80% in single-vehicle rollovers). The true misreporting rates are not identifiable.
  The helmet estimate rests on pairs that differ in helmet use and covers a minority of unhelmeted
  motorcyclist deaths (`matched/helmet_pair_coverage`); applying it to all unhelmeted deaths assumes
  riders with a passenger represent solo riders.
* **FARS imputed BAC may use injury.** NHTSA's imputation model is undocumented. A reviewer found
  that among untested FARS drivers the imputed BAC is higher for killed drivers; the committed
  table `measurement/imputed_bac_injury` shows the same under the project's specification:
  among untested drivers an imputed BAC of .08 or more has a much larger adjusted odds ratio for
  the driver being killed than a measured BAC of .08 or more has among tested drivers (adjusted for
  age band, sex, vehicle type, crash type, time of day and year; values in the table). This is a
  diagnostic, not a causal estimate. It is consistent with the imputation using injury severity but
  does not show it: the tested comparison group is itself selected on the outcome (most tested
  drivers were killed; most imputed-group drivers were not; counts in the table), and adding
  police-reported alcohol, light, area and weekend moves the tested odds ratio substantially, so the
  gap depends on the covariates chosen. FARS figures built on imputed BAC may therefore depend on a
  model that uses the outcome; the measured-BAC figures avoid that but describe tested drivers only. Figures that use imputed BAC (drunk-driving deaths, victim roles, prior-DWI
  shares) are therefore shown with measured-BAC-only counterparts where available
  (`deaths/victim_roles_bac_basis`, `deaths/driver_records_measured_bac`; a large share of drivers at .08 or
  more have an imputed BAC, `deaths/driver_bac_imputed_share`).
* **CRSS weights are benchmarked to FARS.** The weighted CRSS fatal total reproduces the FARS count
  each year, so agreement between the two systems on fatal totals is partly by construction and not
  independent corroboration.
* **The CRSS pedestrian speed limit is missing in an outcome-dependent way.** It is unknown for
  a much larger share of non-fatal than of fatal struck pedestrians
  (`vulnerable/speed_limit_missingness`). Crude shares who died by posted limit depend on how
  unknown limits are handled; the adjusted ratios keep unknown as its own level.
* **Driver-record completeness varies by state.** Prior-conviction fields come from state driver
  files, so state-level and pooled shares of prior DWI or speeding reflect state reporting as well
  as behaviour.
* **Only the registered families are multiplicity-adjusted.** Holm or BH adjustment covers the 13
  registered interaction pairs and the other registered families; the speeding-type split, the
  post-2020 decomposition (RQ5, added after the descriptive results), configuration-stratified
  contrasts and the other follow-ups are exploratory and unadjusted.
* **Intervals cover sampling error only.** Confidence intervals for the mixed FARS/CRSS ratios,
  attributable fractions and composition shares reflect CRSS sampling (the denominator or model), not
  recording error, coding choices or the variance of NHTSA's imputations.

## 10. Additions after the red-team review (follow-up, November 2026)

These items were added after the review and the follow-up analyses it prompted; none replaces an
earlier limitation. Where a number is given it is approximate; the named table has the value.

* **Degrees of freedom for small domains.** CRSS intervals use the design degrees of freedom (42),
  which is standard practice. Rural-only contrasts rest on far fewer primary sampling units: the rural
  domain has 21 PSUs in 9 strata (from the processed CRSS file: `urbanicity == "rural"`, distinct `PSU_VAR` and
  `PSUSTRAT`), so the degrees of freedom are 21 − 9 = 12, and their intervals may be several percent too
  narrow. The same applies, less severely, to other small domains.
* **Interaction margins treat level-mixture weights as fixed.** The standardised margins for
  interactions average predictions over the observed mix of factor levels and do not carry the
  sampling variability of that mix into the intervals. The effect is small.
* **The pooled model-A risk ratios average over very different crash configurations.**
  `severity/fatal_effect_modification` (exploratory, added after the review) shows that the
  adjusted fatal risk ratios for exceeding the limit, alcohol, motorcycles and large trucks differ
  sharply between single-vehicle and multi-vehicle crashes (homogeneity p very small for each), with
  the larger ratios in multi-vehicle crashes, where the baseline fatal risk is low; for "too fast for
  conditions" there is no detectable difference between single- and multi-vehicle crashes (p in the
  same table), although finer crash types do differ. A pooled ratio therefore describes neither configuration well, and
  the table is an association conditional on a police-reported crash, not an effect.
* **Model A is calibrated overall but not within the risk distribution.**
  `severity/fatal_calibration` shows observed/predicted fatal shares clearly below 1 (about three-quarters) in the
  middle deciles of predicted risk (over-prediction) with overall calibration. The check is
  in-sample and its intervals omit model-fit variability. Absolute risks, risk differences and the
  attributable fractions built on them are therefore less reliable than the relative contrasts.
* **Imputed BAC and injury.** See the revised "FARS imputed BAC may use injury" item above and
  `measurement/imputed_bac_injury`: BAC-based figures in FARS may depend on a model that uses the
  outcome (the diagnostic is consistent with that, not proof, and its comparison group is selected).
* **EMS intervals are known for only part of crashes.** The share of fatal crashes with a recorded
  EMS arrival time is about half or less in every year (`stages/ems_availability`), and intervals that are
  negative or longer than 12 hours are set to missing, so timing summaries describe the crashes with
  a plausible interval and may not represent all fatal crashes.
* **Prior-DWI shares vary widely by state.** Among drivers at .08 or more the state shares range
  from a few percent to about a fifth (`deaths/prior_dwi_state_range`, `deaths/prior_dwi_by_state`); this reflects
  state record completeness as well as behaviour and is not a ranking of states.
* **Large-truck victim roles describe who was in the crash, not fault.** The share not the truck
  driver is about half in single-truck crashes and nearly all in crashes between a truck and a
  passenger vehicle (`deaths/large_truck_crash_types`).
* **The rise in invalid-licence crashes is robust to the definition.** It appears with and without
  counting expired or cancelled licences as invalid (`deaths/licence_trend`), but licence status is
  a state-file field with uneven completeness.
