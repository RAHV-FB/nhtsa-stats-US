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
  CRSS records speeding in 21% of *fatal* crashes versus 27% in FARS for the same population
  (FARS analysts use more sources); alcohol tests are given to 59–74% of killed drivers but
  21–29% of surviving drivers; the drug-test rate is 53–63% vs 13–20%. A quantitative bias
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
* **Unknown values as proxies for post-crash events.** Unknown driver age and unknown
  speeding are concentrated in hit-and-run crashes (92% and 64% respectively in CRSS), so an
  "unknown" level partly encodes a driver leaving the scene. CRSS driver-age flags therefore
  use NHTSA's imputed age; the speeding "unknown" level remains and is not interpreted.
* **Distraction and drug involvement** are unknown or not reported for 42–74% of drivers in
  recent years and their unknown share changed sharply; they are not used as model
  exposures. Drug *presence* in a toxicology result is not impairment.
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
* Crashes with unknown maximum severity (~1.9% of CRSS) are excluded; they are also the least
  documented crashes, so excluding them removes poorly recorded crashes twice (once for the
  outcome, once for covariates). Sensitivity analysis uses NHTSA's imputed severity.
* NHTSA's single imputations (`*_IM`, CRSS) understate variance by roughly the imputed
  fraction; their imputation models are not documented in the archives (it is unverified
  whether they condition on severity).
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
  culpability is charged without bias by group; crash-level conditions cannot be assessed by
  QIE at all.

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
