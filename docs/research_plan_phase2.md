# Research plan — Phase 2: factor attribution, confounding, competing explanations

Version 2.1. Written after auditing the Phase-1 system (merged in commit 1236262) and before any
Phase-2 code. Phase 1's plan (`docs/research_plan.md`) and its validated results are unchanged;
this document records what Phase 2 adds, why, and how it will be judged. Change log at the end.

## 1. Starting state (audit, 2026-10-23)

* Branch `cl/affectionate-heisenberg-foukkl`, created from `main` after PR #2 was squash-merged
  (`main` = 1236262). Working tree clean.
* Raw archives (Git LFS) verified; typed cache and the four processed datasets rebuilt with
  `nhtsa ingest` + `nhtsa features` (about 1.5 minutes). The committed Phase-1 output tables are
  reused as they are; the 84-minute `nhtsa all` (Phase-1 timing) was not re-run.
* Existing test suite run on the rebuilt data before any change (`outputs/logs/`, not committed).

### 1.1 What Phase 1 already established (numbers from `outputs/tables`)

| Topic | Phase-1 result | Where |
|---|---|---|
| Speeding (crash level, any type) | crude RR 2.36; model A (mutually adjusted for alcohol and all pre-crash circumstances) 1.82; model B (+configuration) 2.07 | `severity/fatal_crude_vs_adjusted` |
| Speeding types | exceeded limit / racing adjusted RR 5.2; "too fast for conditions" 1.06 | `severity/fatal_speeding_type` |
| Alcohol (imputed) | crude 6.41; model A 4.24; complete-case police coding 5.9 | `severity/*`, `measurement/alcohol_coding_sensitivity` |
| Speeding × alcohol | sub-multiplicative (ratio of RRs 0.78), positive additive IC 5.9/1,000 | `interactions/pairs_fatal` |
| Speeding × alcohol × darkness | one fixed triple | `interactions/triples_fatal` |
| Attributable fractions | speeding 9.1%, alcohol 19.7%, joint 26.5% (< 28.8% sum) | `burden/attributable_fractions_fatal` |
| Shapley/sequential confounding | for night, rural, weekend, older driver only | `confounding/*` |
| Person-level restraint | CRSS unbelted RR 24 (adjusted); FARS within-vehicle belt reduction 66%, sensitive to survivor misreporting | `person/*`, `matched/*` |
| Measurement | speeding recorded in 27% of FARS vs 20% of CRSS fatal crashes; QBA grid for speeding; drugs declared unusable | `measurement/*`, `docs/audit/alcohol_drugs.md` |

### 1.2 What Phase 1 did not do (the scientific gap)

1. **The speeding–alcohol confounding question was never isolated.** Every adjusted speeding
   estimate holds alcohol *and* ten other blocks fixed at once; no table shows how much of the
   speeding association changes because of alcohol specifically, in which order, or how the
   attribution depends on the block set. The Shapley machinery exists but was applied only to
   night, rural, weekend and older drivers.
2. **Observation levels were not separated.** All behavioural factors are crash-level
   "any driver" flags. A crash where driver 1 was speeding and driver 2 was drinking counts as
   "speeding and alcohol". Person models adjust for these crash-level flags, never for the
   behaviour of the person's *own* driver, so driver, passenger and other-road-user deaths
   were never distinguished by whose behaviour was recorded.
3. **No factorial analysis of speeding × alcohol × drugs × restraint**, and no occupant-level
   combination of driver behaviour with the occupant's own restraint use.
4. **Drugs were excluded by verdict, not by a pipeline analysis.** The audit appendix
   documents the selection problems in scripts; no reproducible table quantifies them, and no
   bound shows how wide a drug association could be.
5. **No comparison of "contribution" under different meanings** (association, adjusted risk
   difference, predictive information, statistical decomposition, burden) and therefore no
   test of whether any ranking is stable.
6. **Official-statistics overlap was not quantified**: how many deaths are counted under more
   than one factor, and how a conditioning-on-fatality design distorts the apparent
   co-occurrence of factors.
7. **No case-level explorer** that states, for a combination of factors, what is supported by
   data and what is not.

## 2. Conceptual framework: four stages, not one "cause of death"

```
 Stage A  crash occurrence      impairment (alcohol, drugs), speeding, night, road, driver age
          (NOT identifiable: no exposure denominators; CRSS/FARS sample crashes, not trips)
                │  selection: only crashes that happen and are police-reported enter CRSS;
                │  only crashes with a death enter FARS
                ▼
 Stage B  configuration / energy  speed environment (posted limit), recorded speeding,
          crash type (single-vehicle departure, head-on, pedestrian), vehicle mix
          (travel and impact speed are NOT observed for most vehicles)
                ▼
 Stage C  injury given the crash  restraint use, occupant age and sex, seat, vehicle type,
          motorcycle / pedestrian vulnerability, partner-vehicle mass
                ▼
 Stage D  post-crash survival    EMS notification / arrival, transport, time of death
          (recorded in FARS for fatal crashes only: NOT identifiable as an effect on survival)
```

Hypothesised pathways (not data-identified): alcohol and drugs → Stage A (errors) and Stage B
(speed choice, belt non-use: a *behavioural* correlation, not a physical one); speeding →
Stages A and B; restraint → Stage C only; darkness → A (visibility) and B (behaviour mix).
Each Phase-2 analysis states which stage(s) its estimand conditions on. Severity estimands
(P(fatal | reported crash)) mix stages B and C and condition on stage A having happened, so
they say nothing about crash occurrence.

## 3. Questions, hypotheses, estimands

Throughout: CRSS estimates are design-based (25 strata, 67 PSUs, t with 42 df) and
standardised over a stated population; FARS counts are a census. Factor definitions belong
to their unit: driver behaviour to a driver/vehicle, restraint to an occupant, death to a
person. Crash-level "any driver" flags are used only for crash-level outcomes.

| ID | Question | Hypothesis tested (H0 / competing) | Estimand | Population / unit |
|---|---|---|---|---|
| Q1 | How much of the speeding–fatality association is accounted for by alcohol and by other recorded circumstances? | Hypothesis: alcohol accounts for a substantial share. Competing: other circumstances (road, configuration) account for more; or little changes | Standardised RR and RD of fatal (exceeded limit vs no speeding; any speeding vs none) for every subset of 7 covariate blocks; Shapley share of the crude log-RR per block; with/without the configuration block (mediator) | CRSS crashes, crash level |
| Q2 | Does exceeding the limit remain independently associated with fatal severity, in strata where alcohol is not a candidate explanation? | H: the RR is ≥ 2 among crashes with no alcohol (imputed and police complete-case) | Stratum-specific standardised RR: alcohol no / yes; night / day; single / multi-vehicle; speed environment; single-vehicle driver-level with the driver's own alcohol | CRSS crashes; CRSS single-vehicle drivers |
| Q3 | Can alcohol and drug involvement be separated? | H: drug measurement is too selective to estimate a severity association | Test rates and positivity by survival, year, state, alcohol; drug-alcohol co-occurrence; bounds on the drug severity RR under missingness scenarios; minimal-selection FARS comparison (high-testing states) of alcohol and drug associations with driver death | FARS drivers 2016–2024; CRSS drivers |
| Q4 | How much does restraint use change fatality associations within comparable occupants, and is belt protection modified by the driver's behaviour? | H: belt association is large and similar whether or not the driver sped or drank (Stage C independent of Stage A/B) | (a) CRSS occupant standardised risks over own-driver speeding × alcohol × own belt; (b) FARS within-vehicle belt RR stratified by driver speeding / alcohol | CRSS light-vehicle occupants aged ≥ 8; FARS front-seat pairs |
| Q5 | Which combinations show additive or multiplicative interaction? | H0: no interaction on either scale | 2^k standardised cells; IC, RERI, ratio of RRs, 3-way IC; Holm across a registered family (below) | Crash level; driver level (single-vehicle); occupant level |
| Q6 | How much do contributions depend on unit, definition, specification and missingness? | — | The same contrast across units, definitions (any speeding / exceeded; imputed / police alcohol), outcomes (K / KA), complete-case vs imputed outcome, configuration in/out | as above |
| Q7 | Can a principal cause of an individual death be identified? | H: no — individual attribution is not identified | Demonstration: Shapley allocations of a modelled prediction difference change with the reference scenario, ordering scale (risk vs log-odds) and factor set | Case explorer |
| Q8 | How should official counts be read? | H: deaths "involving" factors overlap so that factor counts sum to well over the death total | FARS deaths by combination of speeding, driver BAC ≥ .08 (multiple imputation, expected count), drug-positive (tested), unbelted; sum of single-factor counts / union; conditioning-on-fatality distortion of factor co-occurrence (CRSS all vs fatal vs FARS) | FARS deaths and fatal crashes; CRSS crashes |

Mapping to the A–H labels used in `reports/factor_contributions.md` (its "Answers to the
Phase-2 questions at a glance" table):

| Question | Report label | Topic |
|---|---|---|
| Q1 | A | Speeding–fatality association explained by alcohol and other recorded factors |
| Q2 | B | Exceeding the limit remains associated with fatal severity |
| Q3 | C | Alcohol and drugs separated reliably? |
| Q4 | D | Restraint use within comparable occupants |
| Q5 | E | Interaction between combinations of factors |
| Q6 | F | Dependence of contributions on units, definitions, specification and missingness |
| Q7 | G | Identification of a principal cause of an individual death |
| Q8 | H | Reading official statistics |

## 4. Factor definitions (Stage 2)

New driver-level datasets (`data/processed/crss_driver.parquet`, `fars_driver.parquet`; one
row per in-transport vehicle with its driver) built by `processing/drivers.py`:

* own speeding type (SPEEDREL 2/3 exceeded-or-racing, 4 too fast, 5 unspecified, 0 no,
  8/9 unknown);
* own alcohol: CRSS `V_ALCH_IM` (imputed) and `VEH_ALCH` (police, tri-state); FARS
  multiply-imputed driver BAC (mean of 10 implicates of BAC ≥ .08), measured BAC, test status;
* own drugs: police `DRUGS` (tri-state; both systems); FARS toxicology status (tested /
  not tested / not reported / unknown) and class positivity from the deduplicated `drugs`
  table (2018–2024) or DRUGRES1-3 (2016–2017), excluding caffeine, nicotine, cotinine and
  non-psychoactive codes; carboxy-THC-only and 2023+ presumptive-only positives flagged;
* driver restraint, age (CRSS imputed), sex, body type, hit-and-run, driver killed / KA;
* own-vehicle occupant counts and deaths; deaths outside the vehicle;
* "other driver" behaviour flags in multi-vehicle crashes (any *other* driver speeding /
  alcohol), so own and other behaviour are separable;
* FARS prior speeding convictions and DWI convictions (pre-crash driver history).

Occupant analyses link each occupant to the driver of the *same vehicle* by
(YEAR, case, VEH_NO), never to crash-level flags; links are tested.

## 5. Analytical design (Stage 3)

### 5.1 Speeding confounding (Q1, Q2, Q6) — `analysis/speeding.py`

* Lattice of all 2^7 models over blocks {calendar_area, time (tod, weekend), light,
  road_environment, driver_vehicle_mix, alcohol, configuration} for exposures: exceeded limit
  (speeding type, reference "no"), any speeding (tri-state), and alcohol (with a speeding-type
  block in place of alcohol) — the same estimator, standardisation population and PSU
  linearisation as Phase-1 RQ4. Outcomes fatal and KA.
* Reported: crude → +alcohol only → all but alcohol → all; Shapley shares (with and without
  the configuration block); min/max share over orderings; odds ratios from the same fits to
  show non-collapsibility.
* Stratified RRs (model A within stratum): imputed alcohol no / yes; police alcohol known
  no (complete case); night / day; single / multi-vehicle; speed limit ≤ 45 / 50+; KA.
* Driver-level single-vehicle crashes: own speeding type with own alcohol, outcome crash
  fatal (in a single-vehicle crash, crash-level and driver-level attribution coincide).
* Distribution of speeding types by alcohol, drugs (known), road, collision, driver age,
  severity (crash and driver level).
* Recording: FARS vs CRSS speeding share among fatal crashes *within alcohol strata*; a
  QBA where speeding sensitivity differs by alcohol status; E-values for adjusted RRs.

### 5.2 Alcohol, drugs, restraint (Q3, Q4) — `analysis/drugs.py`, `analysis/restraint_behaviour.py`

* Drug testing: rates by killed/survived × year × alcohol × state-testing tertile; positivity
  by class among tested; alcohol–drug co-occurrence among tested killed drivers;
  police-drug sensitivity against tests.
* Minimal-selection comparison: FARS drivers in states where ≥ 50% of killed *and* surviving
  drivers are drug-tested; conditional on a fatal crash, odds of the driver dying by
  measured BAC ≥ .08 and by drug positivity, mutually adjusted, with the selection
  explicitly stated (conditioning on a fatal crash and on being tested).
* CRSS severity bounds for police-reported drug involvement: RR under complete case, unknown
  as no, unknown as yes, and unknown at k × the known prevalence (k ∈ {0.5, 1, 2}), by period.
* Restraint: CRSS occupant models adding own-driver speeding and alcohol; FARS double-pair
  belt comparison within strata of driver speeding and alcohol.

### 5.3 Multi-factor interactions (Q5) — `analysis/multifactor.py`

Registered family (Holm within each scale; everything else exploratory):

| Level | Factors (exposed vs reference) | Outcome |
|---|---|---|
| crash | exceeded limit × alcohol (imputed) | fatal |
| crash | any speeding × alcohol × night | fatal |
| driver (single-vehicle) | own exceeded limit × own alcohol | crash fatal |
| driver (light vehicle) | own speeding × own alcohol × own belt | driver killed |
| occupant (passengers) | driver speeding × driver alcohol × own belt | passenger killed |
| driver (light vehicle, drugs known) | own speeding × own alcohol × own drugs (police) × own belt | driver killed |

Each is fitted as a survey logistic model with all main effects, all product terms among the
k factors, and the model-A covariates; the 2^k standardised margins give IC, RERI and ratio
of RRs for every pair (within the other factors' reference), the three-way IC, and, for
k = 4, the four-way contrast. Cells with < 30 sample units or < 10 events are suppressed
(estimate withheld, support reported). Crash-level, driver-level and occupant-level results
are reported in separate tables and never pooled.

### 5.4 Contributions and rankings (Q6, Q8) — `analysis/contributions.py`

* Nested models with fixed sample: demographics/environment → + speed factors → + alcohol →
  + drugs (police, with unknown level) → + vehicle and configuration; standardised RRs and
  odds ratios at every step.
* Predictive contribution: temporal split (train 2016–2021, test 2023–2024) logistic model;
  block ablation (Δ test log-loss, Δ AUROC with PSU bootstrap), Shapley over five factor
  blocks of the test-set log-likelihood gain, and permutation importance.
* Attributable burden: single, joint and pairwise AFs; overlap = Σ single − joint; Shapley
  allocation of the joint AF; uncertainty by linearisation.
* Ranking table across seven quantities (adjusted RR, adjusted RD, Δ predictive fit, Shapley
  AF share, FARS deaths involved, exposure prevalence among crashes, AF) with rank
  probabilities from the joint normal approximation of the linearised estimates.
* FARS overlap: deaths by factor combination; sum of single-factor counts vs union.
* Selection by fatality: speeding–alcohol odds ratio among all CRSS crashes, non-fatal,
  fatal, and in FARS.

### 5.5 Case explorer (Q7) — `analysis/cases.py`

Pre-computed scenario grid (speeding type × alcohol × drugs × restraint × night ×
single/multi-vehicle) at driver level: support counts (CRSS sample, FARS deaths), observed
weighted outcome with CI where n ≥ 30 and events ≥ 10, standardised model risk with CI where
the cell is supported, one-factor-removed contrasts, Shapley allocation of the modelled risk
difference from the reference scenario on two scales (risk and log-odds) to show
non-uniqueness, and an explicit statement of what cannot be inferred.

### 5.6 Stage D — `analysis/stages.py`

FARS EMS timing and death timing: availability, missingness, distribution; statement of
non-identifiability (no non-fatal comparison group; EMS times recorded for fatal crashes only).

## 6. Main identification problems and how each is handled

| Problem | Consequence | Handling |
|---|---|---|
| Conditioning on a crash (all CRSS) | No crash-occurrence effects; collider bias among factors | Estimands stated as P(outcome \| reported crash); collider demonstration (5.4) |
| Conditioning on a fatal crash (FARS) | Factor co-occurrence and killed-vs-survived contrasts distorted | FARS used for counts and within-fatal-crash designs only, labelled |
| Post-crash, severity-dependent recording | Associations inflated (speeding, drugs) or attenuated (alcohol "unknown as no") | Multiple codings, QBA, minimal-selection subsets, bounds |
| Mediator adjustment (configuration) | Removes part of the association that runs through crash type | Report with and without; Shapley with and without |
| Non-collapsibility of odds ratios | ORs change between nested models even without confounding | Standardised RRs/RDs as primary; ORs shown alongside |
| Changing samples between models | Spurious change in estimates | Fixed analysis sample for every nested comparison |
| Sparse combinations | Unstable or extrapolated estimates | Suppression rules; support shown; no extrapolated cells |
| Drug testing selection | Positivity not representative | No drug severity point estimate unless bounds are narrow |
| Survivor belt misreporting | Belt association inflated | Within-vehicle designs; FARS reclassification sensitivity (Phase 1) |

## 7. Validation procedures

* Unit tests (synthetic): driver/occupant linkage, tri-state and unknown/untested coding,
  drug-code classification, factorial margin arithmetic, interaction contrast arithmetic,
  Shapley efficiency and order invariance, suppression rules, survey-weight handling,
  calibration helper, counterfactual comparison arithmetic.
* Data tests (real cache, skipped when absent): driver-file row counts reconcile with raw
  vehicle tables; every occupant links to at most one driver; FARS drug status reproduces the
  audit appendix test rates; single-vehicle crash-level and driver-level speeding agree.
* Consistency: every number in the new reports is a placeholder resolved from
  `outputs/tables` by the existing renderer, and `tests/test_reports_in_sync.py` covers them.
* Cross-checks against Phase 1: the full-block exceeded-limit RR must reproduce the Phase-1
  model-A estimate when the block set matches.

## 8. Implementation stages and acceptance criteria

| Stage | Deliverable | Acceptance criterion | Status |
|---|---|---|---|
| 1 | This plan | Gap list, estimands, criteria written before code | Delivered |
| 2 | `processing/drivers.py`, driver datasets, data dictionary entries | Row counts reconcile with raw; linkage tests pass | Delivered |
| 3–4 | Modules `speeding`, `drugs`, `restraint_behaviour`, `multifactor`, `contributions`, `cases`, `stages` | ruff clean; unit tests; deterministic | Delivered |
| 5 | Outputs in `outputs/tables/<module>/` with provenance sidecars | All registered estimands produced with CIs and support | Delivered |
| 6 | Challenge analyses (recording, selection, mediator, outcome definition, definitions) | Each headline result has at least one alternative-explanation test | Delivered |
| 7 | Reports (`reports/factor_contributions.md`, `speeding_confounding.md`, `alcohol_drugs_restraints.md`, `multifactor_interactions.md`, `case_comparisons.md`) rendered from templates | Render succeeds; sync test passes; questions A–H answered | Delivered |
| 8 | Streamlit pages | App smoke tests pass headless | Delivered |
| 9 | Full test suite; module runs | All tests pass | Delivered |
| 10 | Independent audit of claims vs tables | Confirmed errors fixed | Delivered |
| 11 | Commit, push, PR | PR open against `main` | Delivered |

## 9. Change log

* v2.0 (2026-10-23) — Phase-2 plan written after the audit in §1.
* v2.1 (2026-10-29) — Delivery record.
  * Delivered: all stages; reports and pages listed in §8.
  * Deviations from the plan:
    * RD with CI is reported for the six key models (`speeding/key_models.csv`), not for all
      lattice subsets (`speeding/lattice.csv` has RR only).
    * Speeding-type composition is crash-level only (`speeding/type_composition.csv`).
    * Predictive block ablation reports R² CIs, but the AUROC drop has no CI
      (`contributions/predictive.csv`).
    * The prior speeding and DWI conviction variables are built in `fars_driver` but not used
      in any analysis.
    * Selection by fatality is in the speeding module (`speeding/selection_by_fatality.csv`),
      not `contributions`.
    * The four-way contrast and the sparse three-way and drug-pair terms are withheld for
      insufficient support (`multifactor/interactions.csv`; `docs/limitations.md` §7).
  * Stage-10 audit (2026-10-29): the claims in the reports and on the public website were
    checked against `outputs/tables`, with no numeric mismatches. The website's wording was
    clarified: the adjusted speeding RR includes crash configuration, alcohol's Shapley share
    depends on order, and segment counts are lower bounds. Synthetic linkage and Phase-2 module
    unit tests were added.
