# Methodology

This document specifies every estimator used in the project, as implemented in
`src/nhtsa_stats`. It is the reference for *how* numbers are produced; `docs/research_plan.md`
says *why* each analysis exists, and `docs/limitations.md` what they cannot show.

## 1. Data sources and units of observation

| Source | Frame | Unit tables | Use in this project |
|---|---|---|---|
| FARS 2016–2024 | Census of motor-vehicle crashes on public trafficways with ≥1 death within 30 days | crash (`accident`), vehicle, person + 30 multi-row tables; auxiliary derived tables; multiply-imputed BAC (`miacc`, `midrvacc`, `miper`) | Observed counts of fatal crashes and deaths; composition of fatal crashes; within-vehicle (matched) person analyses |
| CRSS 2016–2024 | National probability sample of police-reported crashes of all severities | same structure; design variables `WEIGHT`, `PSUSTRAT`, `PSU_VAR`, `STRATUM`, `PJ`, `PSU`; single-imputed `*_IM` fields | Denominators; severity rates and models; co-occurrence and interaction; prediction |

Keys are verified, not assumed (`validation/integrity.py`): FARS crash = (YEAR, ST_CASE),
CRSS crash = CASENUM, vehicle + VEH_NO, person + PER_NO (VEH_NO = 0 for non-motorists).
Parked/working vehicles (`parkwork`) share the VEH_NO sequence with in-transport vehicles,
so vehicle-event tables are filtered to in-transport vehicles before vehicle-level joins.

**FARS and CRSS rows are never pooled.** Where the two are compared (over-representation
ratios, burden scaling), each quantity is estimated within its own source.

## 2. Design-based inference for CRSS

### 2.1 Design

Weights `WEIGHT`; variance strata `PSUSTRAT` (25); variance PSUs `PSU_VAR` (67), nested in
strata, with identical IDs and stratum membership in every year 2016–2024 and at least two
PSUs per stratum (no lonely PSUs). Pooled multi-year analyses use these 67 clusters, which also
captures the correlation of a PSU's crashes across years. Design degrees of freedom
d = 67 − 25 = 42; confidence intervals use the t distribution with d df.

The with-replacement (ultimate-cluster) approximation is used: for a vector of weighted
linearised contributions z_k,

    V̂(Σ z) = Σ_h  n_h/(n_h − 1) · Σ_i (z_hi − z̄_h)(z_hi − z̄_h)ᵀ ,

where z_hi is the total of z over PSU i of stratum h. This ignores finite-population
corrections (conservative). Implementation: `analysis/survey.py: SurveyDesign.vcov_total`.

### 2.2 Totals, means, proportions, domains

* Total: Ŷ = Σ w_k y_k, z_k = w_k y_k.
* Mean / proportion (ratio of totals): R̂ = Σ w y / Σ w, z_k = w_k (y_k − R̂)/Σ w.
* Domains (sub-populations) are estimated with the full design retained (z = 0 outside the
  domain), never by subsetting the sample, so every PSU contributes to the variance.
* Proportion CIs are computed on the logit scale and back-transformed.
* Reliability rules: estimates from fewer than 30 sample cases are *suppressed*; relative
  standard error above 30% is flagged *unstable* (`config.MIN_CELL_N`, `config.MAX_RSE`).

### 2.3 Survey-weighted logistic regression

Pseudo-maximum likelihood: β̂ solves Σ w_k x_k (y_k − μ_k) − λ β = 0 (weights normalised
to mean 1). Fitting uses damped Newton–Raphson with step-halving on the penalised
log-likelihood (plain Newton diverges on these rare-event data). A ridge λ = 0.01 is applied
to non-intercept coefficients: it keeps coefficients finite and stable for sparse levels and
cells (e.g. 38 crashes with unknown interstate status, 3 of them fatal; zero-event cells arise
in period-specific and interaction fits) and shrinks any level with ≥1,000 crashes by well
under 1%.

Variance: sandwich V(β̂) = A⁻¹ B A⁻¹ with A = Xᵀ diag(w μ(1−μ)) X + λI and
B = V̂(Σ_k w_k x_k (y_k − μ_k)) from §2.1. Tests of single or grouped coefficients use the
design-adjusted Wald F statistic F = (d − q + 1)/(d q) · W on (q, d − q + 1) df.

Validated in `tests/test_survey.py` against statsmodels GLM (identical point estimates;
variance equal to the cluster sandwich × G/(G−1) in the single-stratum case).

### 2.4 Standardised predictive margins (g-computation) and their linearisation

For a counterfactual assignment s (e.g. "every crash speeding-related"), the margin is

    M_s = Σ_k w_k p(x_k^s; β̂) / Σ_k w_k ,

the expected outcome rate if the whole (domain) population had x set by s, standardised to
the observed distribution of all other covariates. Its linearisation includes *both* the
sampling variability of the covariate distribution and of β̂:

    z_k = w_k (p_k^s − M_s)/W  +  gᵀ A⁻¹ w_k x_k (y_k − μ_k),   g = Σ_k w_k p_k^s(1 − p_k^s) x_k^s / W ,

so contrasts between margins (differences, ratios, any smooth function by the delta method)
get unconditional design-based standard errors from V̂(Σ z) of §2.1. In a saturated model this
reproduces the direct domain-mean SE exactly (verified in tests).

Reported contrasts: adjusted risk ratio M_a/M_ref (CI on the log scale) and adjusted risk
difference M_a − M_ref. These are *population-averaged* adjusted associations, not odds
ratios; odds ratios are reported separately in coefficient tables.

### 2.5 Interaction measures

For exposures A, B defined on *groups of levels* (e.g. speed limit 50+ vs <50 mph), the model
contains the full categorical main effects plus one product term 1[A]·1[B]. A group margin
is the mixture of level-specific margins weighted by the (weighted) distribution of levels
within the group. From the four margins p00, p10, p01, p11:

* risk ratio and risk difference of A within B = 0 and within B = 1;
* additive interaction contrast IC = p11 − p10 − p01 + p00, and RERI = IC / p00;
* multiplicative interaction on the risk-ratio scale RR11 / (RR10 · RR01);
* the product-term odds ratio with its Wald F test.

All have linearised CIs. Holm (family-wise) and Benjamini–Hochberg (false discovery rate)
adjustments are applied across the pre-specified pairs, separately for each scale.
Three-factor combinations report the eight adjusted risks, the three-way additive contrast
and the excess of the joint effect over the sum of single-factor excesses; they are estimated
only when the fully exposed cell has at least 20 fatal crashes.

**Co-occurrence** is reported separately and is *not* treated as interaction: weighted joint
prevalence relative to the product of marginal prevalences (observed/expected) among all
crashes and among fatal crashes, and a design-based odds ratio of association.

## 3. Adjustment strategy

Two covariate sets (`analysis/specs.py`):

* **Model A — PRE_CRASH**: year, census region, CRSS urbanicity, time of day, weekend,
  light, weather, surface, speed limit, interstate, junction, work zone, involvement of a
  driver aged 15–20 and of a driver 65+, motorcycle involvement, medium/heavy truck or bus
  involvement, speeding-related, alcohol (imputed).
* **Model B — A + configuration**: crash type (pedestrian, cyclist, single-vehicle
  rollover-first / off-roadway / on-roadway, multi-vehicle head-on / angle / rear-end /
  sideswipe / other) and number of vehicles in transport.

Crash configuration is plausibly a *mediator* of several pre-crash factors (darkness →
pedestrian crash; speeding → roadway departure), so model B estimates associations net of
configuration. Model A is *mutually adjusted*: each factor's model-A association also holds
fixed the pre-crash variables downstream of it in the dependency diagram (`specs.DESCENDANTS`:
time of day → light; weather → road surface; driver age mix and vehicle mix → speeding and
alcohol), so for those factors it is not a total association. For them a second association
that leaves the downstream variables out — "A excluding downstream variables", the `Ax_*`
columns of `severity/*_crude_vs_adjusted` — is reported as the closer analogue of a total
association; for the other factors the two coincide. Post-crash variables (ejection, rollover as an
outcome, fire, towing, airbag deployment, hospital transport, time of death) and outcome
counts are never covariates (`harmonize.REGISTRY` + `assert_no_leakage`). The conceptual
dependency diagram is in `docs/research_plan.md` §5.

The *share of the crude log risk ratio retained* after adjustment, log(RR_adj)/log(RR_crude),
summarises how much an association weakens (values near 0: largely accounted for by other
recorded circumstances; negative: reverses).

## 4. Missing, unknown and imputed values

* Unknown / not reported / not applicable codes are mapped explicitly (see
  `docs/variable_harmonization.md`); binary indicators are tri-state (1 / 0 / null) and enter
  models as yes / no / unknown — never as "no".
* CRSS severity outcomes use NHTSA's imputed severity (`MAXSEV_IM` for crashes, `INJSEV_IM`
  for persons). The unimputed `MAX_SEV` is the maximum over persons whose severity is known,
  so a crash containing a person of unknown severity would be classed by the others' injuries
  — "unknown" silently treated as "not fatal". Its weighted fatal total falls 0.6–12.8% short
  of the FARS count, by an amount that varies by year, whereas the imputed total reproduces
  FARS within 0.9% in every year (the weights are calibrated to FARS through it; tested in
  `tests/test_features.py`). The imputation fills only unknown codes. Crashes whose imputed
  maximum is still undeterminable (codes 5, 6, 8; 0.4%) are excluded. A strict complete-case
  outcome (`fatal_cc`, `ka_cc`: negative only when no person's severity is unknown; ~8% of
  crashes undetermined) is the sensitivity analysis; it changes levels and trends, so both
  are reported where trends are concerned.
* Alcohol: imputed `ALCHL_IM` is used for adjustment because the police-reported field has a
  2019 coding break and an outcome-dependent unknown category (see research plan §3).
* FARS BAC: the ten implicates of the multiply-imputed BAC files are combined as the mean
  over implicates of the indicator BAC ≥ 0.08 g/dL (an expected share). Implicates are in
  hundredths of g/dL; `ALC_RES` is in thousandths (verified: implicates equal ⌊ALC_RES/10⌋ for
  99.97% of tested persons).
* Severity-dependent ascertainment is analysed, not ignored (§8).

## 5. FARS analyses

FARS counts are a census and carry no sampling error; year-to-year changes are nonetheless
subject to random (Poisson-type) variation and to coding changes, and are interpreted with
that in mind. Person-level FARS models use crash-clustered sandwich variances
(`data.fars_design`). Within-vehicle designs (`analysis/matched.py`) use conditional logistic
regression with the vehicle as the matched set, which removes every factor shared by
occupants of the same vehicle (crash forces, travel speed, vehicle, road, weather), and the
classical double-pair comparison for belt use. They estimate relative risks *given a crash in
which at least one occupant died*; survivor misreporting of belt use is examined by
reclassification sensitivity analysis.

## 6. Relative involvement (quasi-induced exposure)

`analysis/exposure.py`, RQ7. Sample: CRSS crashes with exactly two in-transport vehicles,
no non-motorist, no hit-and-run vehicle and a driver present in both, in which exactly one
driver is culpable and the other non-culpable. Culpability (primary definition C1) uses
pre-crash actions only — speeding, the critical pre-crash event class and common
driver-error codes — never charges, which are laid after the crash and are rarely laid
against the dead. Because each qualifying crash contributes one culpable and one
non-culpable driver, the relative involvement ratio of group g (its share among culpable
drivers divided by its share among non-culpable drivers) equals the odds of culpability
within g. It is estimated from a saturated survey logistic model of culpability on the group,
with linearised CIs that account for both drivers of a crash sharing a PSU; adjusted ratios
come from a multivariable survey logit (age, sex, alcohol, vehicle type, night, year,
region, urbanicity). Hit-and-run crashes are excluded because fleeing drivers are almost
always coded culpable and have unknown age and sex. Alcohol is reported by CRSS coding
period, with the police-reported "yes vs not yes" contrast alongside the imputed one,
because the imputation fills the post-2019 unknowns almost independently of culpability. A
charge-based definition (excluding impairment and outcome-defined charges) is a sensitivity
analysis. Assumptions and their likely directions are listed in the module docstring and in
`docs/limitations.md`.

## 7. Burden

Severity-pathway attributable fractions (`analysis/burden.py`) are computed by g-computation:
the share of model-predicted fatal crashes that would not be fatal had exposed crashes the
reference level instead, holding other recorded circumstances fixed. They are scaled to FARS
deaths (mean 2022–2024) only as a labelled, model-predicted quantity. They exclude the
crash-occurrence pathway and assume no unmeasured confounding and correct measurement.

## 8. Measurement validity and quantitative bias analysis

`analysis/measurement.py` quantifies unknown rates by KABCO level and year (flagging
year-on-year changes ≥ 5 percentage points as coding breaks), compares the composition of
fatal crashes in CRSS (weighted) and FARS (census) — the same population measured by two
processes — and estimates police-report accuracy against measured BAC among tested FARS
drivers. The quantitative bias analysis corrects the crude 2×2 table for exposure
misclassification with outcome-specific sensitivities (Se among fatal, Se among non-fatal)
and specificity, using the standard matrix method, over a grid of assumptions. Results are a
range of risk ratios compatible with stated assumptions, not a corrected truth.

## 9. Prediction models

See `docs/model_validation.md`: temporal split (train 2016–2021, validate 2022, test
2023–2024), registry-enforced feature whitelist, preprocessing fitted on training years only,
weighted and unweighted metrics, calibration, PSU-cluster bootstrap CIs, and confirmatory
checks of any machine-learning pattern with the transparent survey models above.

## 10. Policy simulation and costs

See `docs/policy_assumptions.md`. The simulator separates (A) empirical baseline quantities
from this database, (B) intervention mechanisms, (C) user-supplied assumptions and (D)
outcomes, and labels every output *hypothetical*. No effect sizes or prices are supplied by
the project, except that belt effectiveness defaults to the project's own FARS within-vehicle
estimate (treated as causal by assumption, and labelled so) when the user gives none.

## 11. Reproducibility

`uv sync --extra app && uv run nhtsa all` rebuilds everything from `data/raw`: archive
validation → typed Parquet cache (incremental, SHA-256 manifest) → inventory → integrity
checks (build stops on structural failures) → analytic datasets → analysis modules. Each
output table has a JSON sidecar with the producing module, git commit, inputs and method.
Random seeds are fixed (`config.RANDOM_SEED`).

## 12. Phase 2: factor attribution, confounding and combinations

Plan and estimands: `docs/research_plan_phase2.md`. Modules (each `nhtsa analyze <name>`):
`speeding`, `drugs`, `multifactor`, `restraint_behaviour`, `contributions`, `stages`, `cases`.

### 12.1 Observation levels and linkage (`processing/drivers.py`)

Behaviour belongs to a driver, restraint to an occupant, death to a person. The driver files
carry one row per in-transport vehicle with *its own* driver's speeding type, alcohol and drug
fields; `crss_person_link` maps every occupant to their own vehicle and every non-motorist to
the striking vehicle (`STR_VEH`). Occupant analyses take driver behaviour from the linked
vehicle, never from crash-level "any driver" flags. "Other driver" flags are tri-state with a
separate `no_other_vehicle` level, so a single-vehicle crash is never coded as "the other driver
did not speed". FARS drug-test status and class positivity follow the audit recipe (deduplicated
2018+ `drugs` table; 3-digit codes 2016–2021, 4-digit codes 2022–2024; caffeine, nicotine,
cotinine, non-psychoactive and unspecified "other" results never count as psychoactive
positives; a person with only "other" results is indeterminate). Linkage and coding are tested
in `tests/test_driver_linkage.py` (synthetic frames) and `tests/test_drivers.py` (real data,
including reproduction of the audit test rates).

### 12.2 Lattices for speeding and alcohol (`analysis/speeding.py`)

The Phase-1 lattice estimator (§2.4, `confounding.fit_lattice`) is applied with seven blocks —
calendar/area, time, light, road environment, driver/vehicle mix, *the other behaviour*
(alcohol for speeding exposures, speeding type for alcohol) and crash configuration — to three
exposures (exceeded limit vs no speeding; any speeding vs none; alcohol). All 128 models share
one sample and one standardisation population, so differences between them are changes in a
collapsible quantity (standardised log-RR), not artefacts of non-collapsibility or changing
samples; conditional odds ratios from the same specifications are reported alongside. Shapley
shares are exact over all 7! orderings, with and without the configuration block. The
"behaviour change" table reports the reduction in log-RR when the other behaviour is added to
*every* subset of the remaining blocks, so the dependence of "how much alcohol explains" on
the rest of the model is visible. Stratum-specific RRs use model-A blocks minus the blocks that
define the stratum; heterogeneity between two strata is the ratio of their RRs with a CI from
the joint PSU-level linearisation.

### 12.3 Factorial margins (`analysis/factorial.py`, `analysis/multifactor.py`, `analysis/cases.py`)

For k binary factors, a survey logistic model with all main effects (factor levels other than
exposed/reference, e.g. unknown, keep their own coefficients), a product term for every
combination of non-reference levels of every subset of factors (so the factors are saturated
among all their observed levels, and "unknown" rows never share the interaction reference with
the reference level), and categorical covariates; 2^k standardised margins from one fit, jointly
linearised. Contrasts: single-factor RR/RD within every combination of the others; pairwise,
three- and four-way additive contrasts Σ(−1)^(k−|s|)p_s and their log-scale (multiplicative)
analogues; excess of the joint RD over the sum of single RDs. A combination whose *recorded*
cell has fewer than 30 sample units or 10 events is withheld together with every contrast using
it. Holm adjustment across the registered family, per scale. The case explorer's model is saturated
in the case factors (main effects and products for every subset of factors), so it is calibrated
within every factor cell by construction; it withholds model risks, contrasts and allocations
whenever any required combination is unsupported. (A first version with pairwise products only
was mis-calibrated in two large cells — observed/predicted 0.59 and 1.74 — which a calibration
test caught; higher-order interactions among the case factors are therefore material.)

Nested models (§12.4) add police-reported drugs as a separate step after the other behaviours
and the driver/vehicle mix, because the police co-record drugs with alcohol; burden and rank
models exclude them.

### 12.4 Contribution metrics (`analysis/contributions.py`)

* Nested models on a fixed sample: crude → environment → + the other behaviour (speeding type or
  alcohol) → + driver/vehicle mix → + police-reported drugs → + configuration; standardised
  RR/RD and conditional OR per factor.
* Prediction: models fitted on 2016–2021 and evaluated on 2023–2024 (2022 unused: no tuning);
  design-weighted McFadden R² (log-likelihood gain over the training base rate) and AUROC;
  all 2^6 block subsets, giving exact Shapley values of the test R², leave-one-block-out drops
  and single-block values; uncertainty by resampling PSUs within strata of the test set (model
  fixed); permutation importance permutes a block's columns jointly.
* Burden: AF(S) = 1 − M_S/M_obs from one model, where M_S sets the exposed crashes of every
  factor in S to the reference; singles, joints, overlap (Σ singles − joint) and exact Shapley
  allocation of the joint AF, all functions of jointly linearised margins.
* Rank probabilities: the vector of adjusted log-RRs (and RDs) of all crash-level factors from
  one model has a joint design-based covariance; 20,000 multivariate-normal draws give the
  probability of each rank.
* FARS overlap: deaths by combination of crash speeding, any-driver BAC ≥ .08 (expected counts
  over the 10 implicates), any-driver drug positivity (determinate crashes) and the victim's
  restraint.

### 12.5 Drug measurement (`analysis/drugs.py`)

Testing and positivity shares are census proportions (FARS). The minimal-selection comparison
fits a logistic model for "driver died" among drivers tested for both alcohol and drugs, with
crash-clustered sandwich SEs, in the states testing ≥ 50% of both killed and surviving drivers
for both substances. CRSS bounds allocate unknown drug status at k × the known prevalence,
separately among fatal and non-fatal crashes (k ∈ {0, 0.5, 1, 2, 3}) and at the two extremes.

### 12.6 Restraint by driver behaviour (`analysis/restraint_behaviour.py`)

The Phase-1 double-pair comparison (driver / right-front passenger, light vehicles) within
disjoint strata of the driver's behaviour, crash type and time; crash-cluster bootstrap
(1,000 replicates); heterogeneity z-test on the log RR. CRSS nested sequence for the unbelted
RR on a fixed occupant sample.
