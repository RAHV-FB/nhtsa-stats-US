# Limitations and unidentifiable quantities

This project is deliberately explicit about what the supplied FARS and CRSS archives cannot
show. The limitations below are research findings in their own right: they define which
policy questions require data that do not exist in this repository.

## 1. Quantities that are not identifiable from these data

| Quantity | Why not | What the project does instead |
|---|---|---|
| Probability of a crash per trip, mile, hour or driver | No exposure data (travel, licensing, vehicle-miles) in either system | Relative involvement by quasi-induced exposure (RQ7) under explicit assumptions; severity *given* a crash |
| P(fatal \| crash) from FARS | FARS contains only fatal crashes | Severity models use CRSS; FARS is used for counts and composition |
| Effect of speed cameras, sobriety checkpoints, roadside drug testing, belt enforcement, campaigns | No camera locations, enforcement intensity, checks performed, citations, campaign exposure or costs anywhere in the archives (checked: `outputs/audit/column_inventory.csv` contains no such fields) | Evidence ledger + simulator with user-supplied mechanism and effect parameters; break-even and threshold analysis |
| Lives saved by any intervention | Requires the above | Conditional, labelled-hypothetical projections only |
| Causal effect of speeding or alcohol on severity | Observational data; behaviours recorded by police after the crash; unmeasured confounding (travel speed, vehicle mass, occupant frailty beyond age) | Adjusted associations, sensitivity and bias analysis; the within-vehicle belt analysis is the closest design to a causal estimate and has its own caveats |
| Costs and monetary values | No cost data in the repository | Cost model requires user inputs; no defaults |

## 2. Measurement

* **Severity-dependent ascertainment.** Behavioural fields are recorded more completely, and
  often more thoroughly investigated, in severe crashes. Evidence from this project:
  CRSS records speeding in 20% of *fatal* crashes versus 27% in FARS for the same population
  (FARS analysts use more sources); alcohol tests are given to 59–74% of killed drivers but
  21–28% of surviving drivers; the drug-test rate is 55–63% vs 15–20% (2018–2024; the lowest
  values are 2024, whose toxicology records are incomplete in these archives). A quantitative bias
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
  treats crashes containing a person of unknown severity as non-fatal and falls up to 12.8%
  short in some years. The imputation rests on few crashes: 4–31 sampled crashes a year are
  imputed fatal, but they carry large weights and make up 0.6–12.2% of the weighted fatal
  total (most in 2017 and 2019–2020). Their imputation variance is not included in the
  design-based standard errors, so year-specific fatal and KA shares are somewhat more
  uncertain than their intervals suggest. Trend statements are therefore also checked
  against a strict complete-case outcome.
* **Unknown values as proxies for post-crash events.** Several "unknown" levels are
  concentrated in hit-and-run crashes, so they partly encode a driver leaving the scene, which
  happens after the crash. 92% of CRSS crashes with a driver of unreported age are hit-and-run
  (`docs/variable_harmonization.md`), so CRSS driver-age flags use NHTSA's imputed age. Among
  crashes with other unknown levels, the weighted hit-and-run shares in 2016–2021 are
  (`ml/hit_and_run_proxy`): missing vehicle age 97%, motorcycle involvement 95%, heavy-vehicle
  involvement 91%, time of day 71%, speeding 68%. The other unknown levels are kept as
  their own categories (never merged with "no") and are not interpreted; dropping them from the
  prediction models changes test discrimination by 0.002 AUROC (`docs/model_validation.md`).
* **Distraction and drug involvement** are unknown or not reported for 42–74% of drivers in
  recent years and their unknown share changed sharply; they are not used as exposures in the
  Phase-1 severity and prediction models. Phase-2 analyses that include police-reported drugs
  (`drugs/crss_bounds`, `drugs/crss_adjusted`, the four-factor model in `multifactor/`) report
  them only to show how far the estimate moves with the coding of unknowns, not as a drug effect. Drug *presence* in a toxicology result is not impairment.
* **Restraint use** among surviving occupants is largely self-reported to police; reported
  belt use among uninjured CRSS occupants (98.7%) is implausibly high, so person-level belt
  associations in CRSS are likely inflated. The FARS within-vehicle analysis is less affected
  but survivor misreporting is still possible (sensitivity analysis provided).
* **Police-reported speeding** combines exceeding the limit and "too fast for conditions";
  travel speed is unknown for most vehicles, so speed itself cannot be modelled.
* **CRSS urbanicity** describes the sampling area (PSU), not the road; FARS rural/urban
  describes the road. They are different concepts and are never compared directly.
* **FARS 2024** shows a jump in alcohol-test status "unknown" among killed drivers (26%
  vs 12–15% in 2020–2023), consistent with pending toxicology; 2024 alcohol figures are less
  complete.

## 3. Design and inference

* CRSS variance estimation uses the with-replacement approximation with 42 design degrees
  of freedom; small domains (< 30 sample crashes) are suppressed and high-RSE estimates
  flagged. CRSS 2016 was a transition sample (fewer PSUs).
* Pooling nine years uses the same PSUs; year effects are included in models, but changes in
  reporting practice across years are only partly captured.
* The primary CRSS outcome is NHTSA's imputed maximum severity (`MAXSEV_IM`); only crashes
  it codes as unknown or died-prior (~0.4%) are excluded. The sensitivity analysis is the
  strict complete case (`fatal_cc`, `ka_cc`), which drops about 8% of crashes, and which ones
  depends on the outcome: a crash drops out only when someone's severity is unknown and nobody
  died. It is a bound on the definition, not a better estimate. Where the two definitions
  disagree (the 2023–24 excess in RQ5, crude night and weekend RRs in RQ4), both are reported.
* NHTSA's single imputations (`*_IM`, CRSS) understate variance by roughly the imputed
  fraction; their imputation models are not documented in the archives. For alcohol there is
  indirect evidence that the imputation uses severity, directly or through correlated
  circumstances: among crashes whose police-reported alcohol is unknown, the imputed "yes"
  is 6.7 times (2016–18) and 4.2 times (2019–21) as common in fatal as in non-fatal crashes,
  about as steep as the gradient among police-reported records (6.4 and 5.5;
  `ml/alcohol_imputation_check`). Adjusted associations with imputed alcohol may therefore be
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
  share of a death "due to" each factor. Shapley allocations in `cases/` and `contributions/` are
  allocations of model quantities; they change with the scale (risk difference vs log risk
  ratio), the reference case and the factor set, and are reported precisely to show this.
* **Drugs.** CRSS has only police-reported drug involvement (50–70% unknown after 2019) and the
  police co-record drugs with alcohol several times more often than toxicology finds them
  together. No drug severity association, attributable fraction or ranking is reported as a
  finding (the drug risk ratios in `drugs/` and `multifactor/` are bounds and coding
  sensitivities, labelled as not identifying a drug effect); the
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
