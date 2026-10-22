# Research plan

Version 1.2 — written after the repository and data audit (see `docs/data_audit.md`) and
revised as findings emerged (change log at the end).

## 1. Central question

> What factors, individually and in combination, explain variation in the severity of
> police-reported road crashes in the United States (2016–2024), and what can those
> relationships responsibly tell us about road-safety policy?

The supplied data are two NHTSA systems:

* **FARS** — a census of crashes on public trafficways in which at least one person died
  within 30 days. It describes *fatal* crashes in detail but contains no non-fatal crashes,
  so it cannot estimate the probability that a crash becomes fatal.
* **CRSS** — a national probability sample (~46–55k crashes per year) of police-reported
  crashes of every severity, with survey weights and design variables. It is the only source
  of denominators for severity rates.

Neither system contains exposure (trips, vehicle-miles, driver-hours), enforcement, camera,
roadside-testing or cost information. Those absences define what can and cannot be
answered and are treated as findings, not as gaps to be filled with outside numbers.

## 2. What is identifiable — the outcome taxonomy

| Problem | Question | Source | Identifiable? |
|---|---|---|---|
| A. Fatal-crash characteristics | What distinguishes fatal crashes; how has their composition changed? | FARS | Yes (census, descriptive) |
| B. Crash severity | Among police-reported crashes, which circumstances are associated with a fatal / fatal-or-serious (KA) outcome? | CRSS | Yes, as adjusted associations conditional on a reported crash |
| C. Individual risk given involvement | Among people in reported crashes, who dies or is seriously injured? | CRSS (all severities); FARS within-vehicle designs | Yes; FARS matched designs come closest to causal for person-level factors |
| D. Crash occurrence | What raises the probability of crashing at all? | — | **Not identifiable** in absolute terms (no exposure). Relative involvement is partly addressable by quasi-induced exposure under strong assumptions (§4, RQ7) |
| E. National burden | How many deaths are associated with a factor; how many might be preventable? | FARS counts × CRSS-model fractions | Only as model-based, assumption-labelled quantities |

Every reported number is labelled as one of: **observed** (FARS count), **estimated**
(CRSS design-based estimate), **adjusted association** (model-based contrast),
**model-predicted** (conditional on a crash), **hypothetical** (simulation output under
user assumptions). Nothing in this project is labelled *causally identified* except where a
design argument is given (RQ6), and even there with explicit caveats.

## 3. Cross-cutting design decisions (from the audit)

1. **Never pool FARS and CRSS rows.** FARS supplies fatal-crash counts and fatal-crash
   composition; CRSS supplies denominators and severity models. Comparisons between them are
   ratios of separately estimated quantities (descriptive over-representation ratios).
2. **CRSS inference is design-based**: weights `WEIGHT`, variance strata `PSUSTRAT`
   (25), variance PSUs `PSU_VAR` (67), Taylor linearisation, t-reference with 42 df. PSU IDs
   are stable 2016–2024, so pooled multi-year analyses use the same clusters (this also
   captures within-PSU correlation across years).
3. **Unknowns are never "no".** Tri-state indicators (yes / no / unknown) are kept; models
   include an explicit unknown level; complete-case sensitivity analyses are reported.
4. **Alcohol**: CRSS police-reported `ALCOHOL` has a 2019 coding break (share "unknown"
   rose from ~12% to ~37% of non-fatal and ~30% to ~55% of fatal crashes) and its unknown
   category is strongly outcome-dependent. Models use NHTSA's imputed `ALCHL_IM`, which
   matches `ALCOHOL` in 99.998% of rows where `ALCOHOL` is known. FARS alcohol uses the
   multiply-imputed BAC files (10 implicates).
5. **Leakage control**: every analytic variable is registered as pre-crash, crash
   circumstance, post-crash or outcome (`processing/harmonize.py: REGISTRY`); models reject
   post-crash variables (ejection, rollover, fire, towing, airbag deployment, hospital,
   death timing).
6. **Two adjustment sets**: PRE_CRASH (time, light, weather, surface, speed limit, road
   class, junction, work zone, region, urbanicity, driver age mix, vehicle mix, speeding,
   alcohol, year) for *total* associations; + crash configuration (crash type, vehicles)
   for associations *net of* configuration. Configuration is treated as a potential
   mediator, not a confounder (§5).
7. **Temporal split for prediction**: train 2016–2021, validate 2022, test 2023–2024.

## 4. Research questions and analyses

Priority reflects scientific value × evidential strength × policy relevance × feasibility.

### RQ1 (priority 1) — Crude versus adjusted severity associations

| Element | Specification |
|---|---|
| Question | Which circumstances are associated with a crash being fatal (K) or KA, and how do associations change after adjustment? |
| Population | CRSS police-reported crashes 2016–2024 with a determinable maximum severity (imputed `MAXSEV_IM` not 5/6/8; 467,008 sampled crashes) |
| Unit | Crash |
| Outcome | `fatal` = `MAXSEV_IM` 4 vs 0–3; `ka` = 3–4 vs 0–2 (NHTSA-imputed maximum severity; codes 5/6/8 excluded, 0.4%). Complete-case sensitivity `fatal_cc` / `ka_cc` from `MAX_SEV`, negative only when no person's severity is unknown |
| Variables | PRE_CRASH set; crash configuration; all available and harmonised 2016–2024 |
| Method | Weighted crude rates; survey-weighted logistic models A (pre-crash) and B (+configuration); standardised predictive margins → adjusted risk ratios and differences with linearised CIs |
| Confounders / selection | Adjusted: listed covariates. Not available: travel speed (mostly unknown), vehicle mass, occupancy, EMS response. Selection: crash must be police-reported and sampled |
| Justified interpretation | "Conditional on a reported crash, crashes with X are fatal Y times as often as comparable crashes without X" |
| Not justified | Causal effect of X; effect of X on crash occurrence; effect of removing X via policy |
| Limitations | Police-reported behaviours are ascertained more thoroughly in fatal crashes (RQ3); residual confounding |
| Validation | Agreement of CRSS weighted fatal-crash composition with FARS census; KA as second outcome; complete-case (`MAX_SEV`) sensitivity; period-specific refits |

### RQ2 (priority 1) — Interactions and co-occurrence

| Element | Specification |
|---|---|
| Question | Which factor combinations are associated with disproportionately severe outcomes, beyond what each factor implies alone? |
| Population / unit / outcome | As RQ1 (fatal, KA) |
| Candidate pairs (pre-specified) | speeding×dark, speeding×wet, speeding×alcohol, alcohol×dark, dark×pedestrian crash, speed limit 50+×dark-unlit, motorcycle×speeding, motorcycle×alcohol, young driver×night, older driver×crash type (angle), heavy truck×speed limit 50+, rural×dark-unlit, weekend×night |
| Method | Weighted co-occurrence (observed/expected joint prevalence, all vs fatal crashes); model A + one product term per pair; four standardised margins → interaction contrast (additive), RERI, ratio of risk ratios (multiplicative); design-based Wald F for the product term; Holm adjustment across pairs; three-way combinations only for pairs that survive, with minimum-support thresholds |
| Justified | "The excess fatality risk of X is larger/smaller when Y is present" (statistical interaction, conditional on a crash) |
| Not justified | Synergy in a causal sense; co-occurrence in fatal crashes as evidence of interaction |
| Validation | Stability across 2016–2019 vs 2020–2024; KA outcome; complete-case for unknown levels |

### RQ3 (priority 1) — Measurement validity of behavioural factors

| Element | Specification |
|---|---|
| Question | Are speeding, alcohol, drug and restraint codes ascertained differently by severity, and how much could that bias severity associations? |
| Population | CRSS crashes; FARS drivers/occupants |
| Method | Unknown-rate and coding-break analysis by KABCO and year; FARS–CRSS composition comparison; FARS test rates by injury severity and state; quantitative bias analysis (differential misclassification of exposure by outcome) over a grid of sensitivities |
| Justified | Bounds on how far reported associations could move under stated misclassification assumptions |
| Not justified | A single "corrected" estimate presented as the truth |

### RQ4 (priority 2) — Confounding decomposition of night-time severity

| Element | Specification |
|---|---|
| Question | How much of the excess severity of night-time crashes is accounted for by light condition, speed environment, alcohol, speeding, driver age mix, vehicle mix and crash configuration? |
| Method | Sequential adjustment (crude → +calendar/area → +light → +road/speed limit → +alcohol → +speeding → +driver/vehicle mix → +configuration) of the standardised night-vs-day risk ratio; share of the crude log-RR retained at each step; order-sensitivity (alternative orderings) |
| Justified | Statistical accounting of an association; not a causal mediation analysis (no ordering assumptions are verifiable) |

### RQ5 (priority 2) — The post-2020 rise in crash severity

| Element | Specification |
|---|---|
| Question | The weighted fatal share of police-reported crashes rose from ~0.48% (2016–2019) to ~0.63% (2020–2024) while FARS deaths peaked at 43,230 in 2021. How much of the rise is explained by changes in the mix of crash circumstances (composition) versus changes in severity within circumstances? |
| Method | Survey-weighted Oaxaca–Blinder-type decomposition with standardised margins: predicted fatal share of 2020–24 crashes under the 2016–19 model vs observed; FARS composition trends for corroboration |
| Not justified | Attribution to a specific cause (pandemic, enforcement, etc.) — not measured |

### RQ6 (priority 1) — Person-level risk and within-vehicle designs

| Element | Specification |
|---|---|
| Question | Who dies given involvement: restraint, age, sex, seating position, vehicle type, partner-vehicle type |
| Population | (a) CRSS occupants of in-transport vehicles, all severities; (b) FARS occupants of light passenger vehicles with ≥2 occupants |
| Method | (a) survey logistic models of death / KA with crash covariates; interactions restraint×age, age×sex; (b) conditional logistic regression stratified by vehicle (each vehicle is its own matched set) — controls for everything shared within a vehicle (crash forces, speed, vehicle type, road, weather), estimating within-vehicle relative risks for belt use, age, sex and seat |
| Justified | (b) is close to a causal estimate of belt protection *given a fatal crash*, under the assumptions that belt use is reported without outcome-dependent error and that occupant-specific confounding is captured by age/sex/seat |
| Not justified | Generalising (b) to non-fatal crashes without qualification; ignoring survivor misreporting of belt use (quantified as a sensitivity analysis) |

### RQ7 (priority 3) — Relative crash involvement (quasi-induced exposure)

| Element | Specification |
|---|---|
| Question | Which driver groups are over-involved as the culpable party in two-vehicle crashes, relative to their presence as non-culpable drivers? |
| Method | CRSS two-vehicle crashes (no hit-and-run vehicle) with exactly one culpable driver; relative involvement ratio = share among culpable ÷ share among non-culpable, weighted, with design-based CIs. *Deviation (v1.2):* culpability is action-based (speeding, critical pre-crash event, driver-error codes), not violation-based as first planned, because charges are laid after the crash and almost never against the dead (`docs/audit/driver_behaviour_factors.md` §16); the charge-based version is a sensitivity analysis |
| Assumptions | Non-culpable drivers are a representative sample of drivers on the road at the same place/time; culpability is coded without bias by group |
| Justified | Relative (not absolute) crash-involvement propensities under QIE assumptions |
| Not justified | Crash rates per trip/mile; effects of enforcement |

### RQ8 (priority 2) — Severity-prediction models

| Element | Specification |
|---|---|
| Question | How well can pre-crash and crash-circumstance information predict a fatal outcome given a crash; do flexible models find structure missed by the logistic model? |
| Population | CRSS crashes; temporal split 2016–21 / 2022 / 2023–24 |
| Models | Logistic (main effects); logistic with pre-specified interactions; L2-regularised logistic; histogram gradient boosting; random forest |
| Evaluation | AUROC, average precision, Brier, log loss, calibration curves (weighted and unweighted), by year and subgroup; bootstrap CIs over PSUs |
| Leakage control | Registry-enforced feature whitelist; preprocessing fitted on training years only |
| Justified | Conditional risk stratification of reported crashes; identifying candidate non-linearities for confirmatory checking |
| Not justified | Trip-level crash risk; causal importance from SHAP/permutation importance |

### RQ9 (priority 2) — Burden and the evidence ledger for interventions

| Element | Specification |
|---|---|
| Question | How many fatal crashes are statistically associated with each modifiable factor, and what can the data say about candidate interventions? |
| Method | Model-based attributable fractions via g-computation in CRSS (fatal crashes predicted with the factor set to "absent" among crashes that had it), applied to FARS counts; evidence ledger per intervention (target factor, prevalence, severity association, interactions, affected population, evidence on the intervention itself — none in the data — and required assumptions) |
| Justified | Upper-bound style "severity-pathway" burden under no unmeasured confounding |
| Not justified | Lives saved by an intervention |

### RQ10 — Policy simulator and economics (tooling, not inference)

Layered engine (A empirical baseline → B mechanism → C user assumptions → D outcomes)
with break-even and threshold analysis. No costs or effect sizes are supplied by the
project; all are user inputs with sensitivity sweeps. See `docs/policy_assumptions.md`.

## 5. Conceptual dependency diagram

```
   calendar, region, area ─┐
   time of day ──► light ──┼──► speed environment (speed limit, road class)
   weather ──► surface ────┤
   driver age mix ─────────┼──► behaviours (speeding, alcohol) ──┐
   vehicle mix ────────────┘                                     ▼
                                     crash configuration (type, vehicles)   [mediator]
                                                   ▼
                                    crash forces / occupant protection  [unobserved]
                                                   ▼
                       post-crash: rollover, ejection, fire, EMS   [excluded: consequences]
                                                   ▼
                                       severity (KABCO)   ── selection: police report + CRSS sampling
```

Behaviours are recorded by police *after* the crash, and recording depends on severity
(RQ3) — this differential measurement is the main threat to RQ1/RQ2 for behavioural factors.

## 6. Staged implementation and acceptance criteria

| Stage | Deliverable | Acceptance criterion | Status |
|---|---|---|---|
| 1 | Archive inventory and validation | 36/36 archives checksum-verified; inventory CSVs | done |
| 2 | Relational integrity | 0 structural failures across 18 source-years | done (841/841 checks pass) |
| 3 | Variable audit and harmonisation | Every analytic variable mapped with evidence; breaks documented | done (docs/audit/*) |
| 4 | Analytic datasets | One row per unit; row counts reconcile with raw; leakage registry | done |
| 5 | Descriptive baseline | FARS/CRSS annual series; frequency-vs-severity table with CIs and suppression | done |
| 6 | RQ1, RQ3, RQ4, RQ5 | Converged models, CIs, sensitivity analyses written to outputs/tables | |
| 7 | RQ2 | Pre-specified pairs, additive+multiplicative measures, Holm-adjusted | |
| 8 | RQ6, RQ7 | Within-vehicle and QIE estimates with assumption statements | |
| 9 | RQ8 | Temporal validation report with calibration; leakage test passes | |
| 10 | RQ9, RQ10 | Evidence ledger; simulator and cost tools with tests | |
| 11 | Interface and reports | App runs headless; every reported number traces to an output table | |
| 12 | Independent audit and rebuild | Clean rebuild from raw; tests pass; audit issues fixed | |

## 7. Change log

* v1.0 — initial plan after audit.
* v1.1 — alcohol adjustment switched from police-reported `ALCOHOL` (3-level) to imputed
  `ALCHL_IM` after the 2019 coding break was found (RQ1 trial fit showed `alcohol=unknown`
  with an adjusted OR of 5.3, nearly equal to `alcohol=yes`, and year effects shifting at
  2019). RQ5 (post-2020 severity rise) added after the descriptive baseline showed the
  increase.
* v1.2 — CRSS outcomes switched from the unimputed `MAX_SEV` / `INJ_SEV` to NHTSA's imputed
  `MAXSEV_IM` / `INJSEV_IM` (sensitivity: strict complete case). The survey-design audit
  (`docs/audit/crss_survey_design.md`) showed that `MAX_SEV` is the maximum over persons with
  *known* severity, so crashes containing a person of unknown severity were coded from the
  others' injuries (an "unknown as no" error), and that the weighted `MAX_SEV` fatal total
  falls 0.6–12.8% short of the FARS count by a year-dependent amount. The imputed total
  reproduces FARS within 0.9% every year (exactly in 2016 and 2024). The year-dependent gap
  distorts severity trends: 2019→2024 fatal share +19% (imputed) vs +35% (complete case).
  Also in v1.2 (from the independent QIE audit): RQ7 culpability is action-based rather than
  violation-based; hit-and-run crashes are excluded from the QIE sample; alcohol relative
  involvement is reported by CRSS coding period instead of pooled.
