<!-- Generated from reports/templates/docs/model_validation.md by `nhtsa analyze report`; every number is looked up in outputs/tables. Edit the template, not this file. -->

# Prediction-model validation (RQ8)

This document is the validation report and the set of model cards for the severity-prediction
models in `src/nhtsa_stats/models/severity_ml.py` (module `ml`). It is rendered from the
template `reports/templates/docs/model_validation.md` by `nhtsa analyze report`: every result
number below is looked up in an output table in `outputs/tables/ml/` (named in brackets) that was
produced by `nhtsa_stats.models.severity_ml.run()`, so the document cannot drift from the tables.
Numbers that are not results (method constants, seeds, grid definitions, counts of pre-specified
items) are typed in the template. Edit the template, not this file. Figures are in
`outputs/figures/ml/` and fitted models in `outputs/models/ml/` (git-ignored). The interface of §10 is
described, not tabulated: its predictions come from the saved interface bundle and are not copied here.

**What these models are for.** Conditional risk stratification of *police-reported crashes*:
given the circumstances recorded for a crash, how likely is it that the crash is fatal (K;
primary) or fatal-or-serious (KA; secondary)? They also serve as a check on the transparent
survey models of RQ1/RQ2: do flexible learners find structure that a main-effects logistic
model misses, and does that structure hold up in a confirmatory, design-based analysis?

**What they are not.** They do not estimate the probability of *having* a crash (the data
contain no exposure), the causal effect of any input, or what an intervention would achieve.
Permutation importance and partial dependence describe the fitted models, not the world.
Labels used throughout: *observed* (counted in the sample), *estimated* (design-weighted
population quantity), *adjusted association* (survey regression), *model-predicted*.

## 1. Design at a glance

| Element | Specification |
|---|---|
| Population | CRSS police-reported crashes (all severities; national probability sample), 2016–2024, with a determinable outcome (definitions below; [`run_info.json`]) |
| Unit | Crash |
| Outcomes | `fatal` = imputed maximum severity K vs the rest (primary): MAXSEV_IM 4 (K) vs 0-3 (O/C/B/A) and 5/6/8 (coded 0: no crash death is possible); only 9 (unknown) is excluded. `ka` = K or A vs the rest (secondary): MAXSEV_IM 3-4 (K or A) vs 0-2 (O/C/B) and 6/8 (coded 0); 5 (injured, severity unknown: a serious injury is possible) and 9 are unknown and excluded. Processed outcomes (project outcome definitions); never inputs |
| Split | Train 2016–2021 (313,277 crashes with a determinable fatal outcome, of which 6,422 fatal; 311,821 with a determinable KA outcome, of which 39,789 KA) · validation 2022 (53,955; 1,301 fatal; 7,180 KA) — tuning, selection and thresholds only · test 2023–2024 (101,761; 2,235 fatal; 13,376 KA) — never used for a choice |
| Inputs | Registry-checked pre-crash variables (stage `pre_crash`), plus crash type and vehicle count (stage `pre_crash+circumstance`); `YEAR` is not an input |
| Preprocessing | One-hot / ordinal encoders, median imputation, missing indicators and scaling fitted on the training years only |
| Models | (1) logistic, main effects; (2) L2 logistic, C tuned on 2022; (3) logistic + the 13 pre-specified RQ2 interaction products; (4) histogram gradient boosting, small grid tuned on 2022, early stopping on an internal split of the training years; (5) random forest, one modest configuration |
| Weights | Survey weights (`WEIGHT`, normalised to mean 1) as sample weights in every fit; metrics both weighted and unweighted |
| Uncertainty | Rao–Wu rescaled bootstrap of variance PSUs (`PSU_VAR`) within strata (`PSUSTRAT`), 200 replicates, seed `config.RANDOM_SEED` (20240601); paired model differences on the same replicates |
| Selection | Pre-specified in the module docstring (`src/nhtsa_stats/models/severity_ml.py`), not in the research plan, and applied on 2022: first of logit_main < logit_l2 < logit_interact < hgb < rf whose weighted log loss is within 1% of the best and weighted AUROC within 0.005 of the best |

Weighted fatal prevalence (estimated share of police-reported crashes that are fatal):
0.554% (train), 0.661% (2022),
0.600% (test); unweighted sample shares
2.05%, 2.41%,
2.20%. KA: 3.20%,
3.31%, 3.13% weighted;
12.8%, 13.3%,
13.2% unweighted [`run_info.json`].

## 2. Inputs and leakage control

**Stage `pre_crash`** (17 categorical + 2 numeric): region, CRSS urbanicity, time of day,
weekend, light, weather, surface, speed-limit band, interstate, junction, work zone, driver
15–20 involved, driver 65+ involved, motorcycle involved, medium/heavy truck or bus involved,
speeding-related (police), alcohol-involved (NHTSA-imputed); posted speed limit in mph and age
of the oldest vehicle, each with a missing indicator. **Stage `pre_crash+circumstance`** adds
crash type (10 levels) and number of vehicles in transport. Tri-state indicators enter as
yes / no / unknown; unknown is never "no". The full list with registry timing and declared
levels is in [`feature_sets`].

**Recorded after the crash.** The registry flags police-judged speeding (`speeding`, `speeding_type`,
`str_speeding`, `veh_speeding`) as `recorded_after_crash`; `assert_no_leakage` rejects a flagged field
without a documented reason (`RECORDED_AFTER_CRASH_ALLOWED`). The flag records that these are police
judgements made after the crash, not measurements; a model using them predicts severity given that the
police recorded them. NHTSA-imputed alcohol is registered as pre-crash with a note that its imputation
may use severity.

**Enforcement.** `check_features` runs `harmonize.assert_no_leakage` on the stage's inputs
with the stage's permitted timings (`pre_crash`; plus `crash_circumstance` for the second
stage) every time a model is fitted, and `tests/test_ml.py` calls the registry check directly.
The two numeric inputs are not themselves registry entries; they are mapped to the registered
variable they are computed from (`speed_limit_mph` → `speed_limit`, both from `VSPD_LIM`) or
are registered (`oldest_vehicle_age`). Explicitly excluded: `hit_and_run` (registered
post-crash: leaving the scene), every outcome and outcome-derived count (`fatal_cc`, `ka_cc`,
`n_killed`, `n_ka`, `n_sev_unknown`, `n_sev_injured_unknown`, `NUM_INJ`, `MAX_SEV`,
`MAXSEV_IM`, `kabco`), the CRSS sampling stratum `STRATUM` (assigned from injury severity),
post-crash consequences (rollover, fire, towing), design variables and `YEAR`.

**Unknown values as a hit-and-run proxy.** A fleeing driver leaves the vehicle's body type,
model year, speeding judgement and sometimes the crash time unrecorded, so some "unknown"
inputs stand in for the excluded post-crash status [`hit_and_run_proxy`; training years,
weighted]:

| Input (unknown / missing) | Share of crashes | Hit-and-run among these | Hit-and-run among known | Share of all hit-and-run crashes |
|---|---|---|---|---|
| tod | 0.6% | 71.0% | 12.6% | 3.4% |
| any_motorcycle | 3.6% | 95.2% | 9.8% | 26.8% |
| any_heavy_truck | 3.8% | 91.3% | 9.8% | 27.2% |
| speeding | 4.2% | 67.7% | 10.5% | 21.8% |
| oldest_vehicle_age | 2.4% | 96.5% | 10.9% | 17.7% |
| All other unknowns (light, weather, surface, speed limit, junction, interstate, driver age) | — | 14.0%–31.4% | 12.6%–12.9% | — |

These inputs are kept as specified (unknown is information about the record, and recoding it to
"no" would be worse), but three checks bound their influence: (i) a **proxy-blind refit**
(§6) in which the five proxy inputs' unknowns are replaced, in training and test data, by
draws from the weighted training distribution of known values, so they carry no information;
(ii) evaluation **stratified by hit-and-run status** (used only to split the test set, never
as an input); (iii) the interface flags any request that sets one of these inputs to
"unknown".

**Imputed alcohol.** `alcohol_im` equals the police-reported alcohol field where that is known
and is NHTSA's imputation where it is unknown (15% of weighted training crashes in 2016–2018,
36% in 2019–2021); the imputation model is not documented. Among *imputed* records the
weighted share imputed "yes" is 6.5 (2016–2018) and 4.2 (2019–2021) times higher in fatal than
in non-fatal crashes, against 6.3 and 5.5 among police-reported records
[`alcohol_imputation_check`; training years]. An imputation that ignored severity would show a
much flatter gradient, so the imputed values very likely depend on severity or on
severity-related fields, and may carry outcome information into this input. The input is kept
because it is registered pre-crash and is the project's adjustment variable, but its effect is
bounded by the refit that uses the police-reported field (with its "unknown" level) instead:
test AUROC changes by -0.0015 (boosting) and -0.0001 (logistic) (§6). The driver-age flags
(`young_driver`, `older_driver`) likewise rest on NHTSA-imputed age (a share of CRSS person ages is
imputed each year; see the CRSS survey design audit note in the Git history, commit 7ee597e), so the same
caveat applies; it was not tested here.

## 3. Models, tuning and selection

| Model | Specification |
|---|---|
| `logit_main` | Weighted pseudo-likelihood logistic regression (Newton–Cholesky), tiny ridge C = 100 — the estimator of `analysis/survey.py: SurveyLogit` with λ = 0.01 (tested to agree) |
| `logit_l2` | Same, C ∈ {10⁻⁴, 10⁻³, 10⁻², 0.1, 1, 10}, chosen on 2022 (chosen values in the table below) |
| `logit_interact` | `logit_main` + one product term per pre-specified RQ2 pair whose variables are in the stage (11 in `pre_crash`, all 13 in `pre_crash+circumstance`) |
| `hgb` | `HistGradientBoostingClassifier`, native categorical handling, learning rate 0.1, L2 1.0, max 500 iterations, early stopping on a 15% internal split of 2016–2021; grid max_leaf_nodes ∈ {15, 31} × min_samples_leaf ∈ {100, 400}; chosen setting and number of iterations per cell in the table below |
| `rf` | `RandomForestClassifier`, 100 trees, √p features, 50% row subsample, min_samples_leaf 50 (one configuration: comparison model only) |

[`tuning`, `selection.json`, `model_comparison`] The pre-specified rule picks one model per outcome × stage cell:

| Outcome | Stage | Selected model | Test AUROC (weighted) | Test Brier skill (weighted) |
|---|---|---|---|---|
| fatal | pre_crash | hgb | 0.833 | 0.028 |
| fatal | pre_crash+circumstance | hgb | 0.919 | 0.094 |
| ka | pre_crash | hgb | 0.753 | 0.072 |
| ka | pre_crash+circumstance | hgb | 0.849 | 0.139 |

The 2022 tuning results of the chosen setting of every model (the rule compares weighted log
loss and AUROC; tolerance 1% and 0.005) are:

| Outcome | Stage | Model | Chosen setting | 2022 weighted log loss | 2022 weighted AUROC |
|---|---|---|---|---|---|
| fatal | pre_crash | logit_main | {'C': 100.0} | 0.0345 | 0.811 |
| fatal | pre_crash | logit_l2 | {'C': 1.0} | 0.0345 | 0.811 |
| fatal | pre_crash | logit_interact | {'C': 100.0} | 0.0344 | 0.813 |
| fatal | pre_crash | hgb | {'learning_rate': 0.1, 'max_leaf_nodes': 15, 'min_samples_leaf': 100, 'n_iter': 118} | 0.0337 | 0.838 |
| fatal | pre_crash | rf | {'min_samples_leaf': 50} | 0.0342 | 0.831 |
| fatal | pre_crash+circumstance | logit_main | {'C': 100.0} | 0.0303 | 0.890 |
| fatal | pre_crash+circumstance | logit_l2 | {'C': 10.0} | 0.0303 | 0.890 |
| fatal | pre_crash+circumstance | logit_interact | {'C': 100.0} | 0.0302 | 0.892 |
| fatal | pre_crash+circumstance | hgb | {'learning_rate': 0.1, 'max_leaf_nodes': 31, 'min_samples_leaf': 100, 'n_iter': 120} | 0.0289 | 0.913 |
| fatal | pre_crash+circumstance | rf | {'min_samples_leaf': 50} | 0.0305 | 0.904 |
| ka | pre_crash | logit_main | {'C': 100.0} | 0.1300 | 0.729 |
| ka | pre_crash | logit_l2 | {'C': 1.0} | 0.1300 | 0.729 |
| ka | pre_crash | logit_interact | {'C': 100.0} | 0.1297 | 0.731 |
| ka | pre_crash | hgb | {'learning_rate': 0.1, 'max_leaf_nodes': 31, 'min_samples_leaf': 400, 'n_iter': 175} | 0.1270 | 0.757 |
| ka | pre_crash | rf | {'min_samples_leaf': 50} | 0.1292 | 0.751 |
| ka | pre_crash+circumstance | logit_main | {'C': 100.0} | 0.1170 | 0.824 |
| ka | pre_crash+circumstance | logit_l2 | {'C': 1.0} | 0.1170 | 0.824 |
| ka | pre_crash+circumstance | logit_interact | {'C': 100.0} | 0.1168 | 0.825 |
| ka | pre_crash+circumstance | hgb | {'learning_rate': 0.1, 'max_leaf_nodes': 15, 'min_samples_leaf': 100, 'n_iter': 195} | 0.1130 | 0.844 |
| ka | pre_crash+circumstance | rf | {'min_samples_leaf': 50} | 0.1165 | 0.840 |

The selected and all other fitted models are those trained on 2016–2021 (not refitted on 2022),
so the test years evaluate exactly the saved models.

## 4. Weighted versus unweighted metrics

CRSS samples crashes with unequal probabilities: injury, motorcycle, non-motorist and
newer-vehicle crashes are over-sampled (the within-PSU sampling strata are defined by injury
severity, vehicle type and vehicle age), and each crash carries a weight equal to the number of police-reported
crashes it represents. **Weighted** metrics estimate performance in the population of
police-reported crashes; they are the relevant ones for any statement about crashes in the
United States. **Unweighted** metrics describe performance on the sampled records. Because
the models are fitted with weights, their predictions are calibrated to the population, so
on the sample they under-predict (unweighted observed/expected, circumstance stage, fatal:
1.8–1.8 for the logistic and boosted models, 2.2 for the random forest;
pre-crash 2.7–2.7 and 3.0) and the
reliability curves lie above the diagonal (`figures/ml/calibration_*.png`). Discrimination
is lower unweighted (fatal, circumstance stage, boosting: AUROC 0.872 vs 0.919 weighted)
because the sample's non-fatal crashes are more often injury crashes, which are harder to
separate from fatal ones. Unweighted metrics are reported for completeness and as a
design-dependence check; they are not population estimates.

## 5. Test-set performance (2023–2024)

### 5.1 Model comparison — fatal, weighted (estimated; 95% PSU-bootstrap CIs) [`metrics_test`, `model_comparison`]

| Stage | Model | AUROC | Average precision (prevalence 0.0060) | Brier skill | Log loss | Calibration slope | Observed / expected |
|---|---|---|---|---|---|---|---|
| pre_crash | logit_main | 0.815 (0.795–0.831) | 0.052 (0.043–0.061) | 0.022 (0.016–0.027) | 0.0317 | 1.02 (0.96–1.08) | 1.04 (0.94–1.14) |
|  | logit_l2 | 0.815 (0.795–0.831) | 0.052 (0.043–0.061) | 0.022 (0.016–0.027) | 0.0317 | 1.03 (0.97–1.09) | 1.04 (0.94–1.14) |
|  | logit_interact | 0.818 (0.798–0.834) | 0.052 (0.044–0.063) | 0.023 (0.017–0.029) | 0.0316 | 1.02 (0.96–1.09) | 1.04 (0.94–1.14) |
|  | **hgb** (selected) | 0.833 (0.817–0.850) | 0.058 (0.050–0.068) | 0.028 (0.022–0.033) | 0.0311 | 1.04 (0.99–1.10) | 1.06 (0.97–1.16) |
|  | rf | 0.828 (0.811–0.845) | 0.051 (0.044–0.061) | 0.020 (0.018–0.023) | 0.0316 | 1.30 (1.20–1.40) | 1.05 (0.95–1.17) |
| pre_crash+circumstance | logit_main | 0.903 (0.893–0.912) | 0.131 (0.112–0.150) | 0.071 (0.058–0.082) | 0.0272 | 1.05 (1.02–1.08) | 1.02 (0.95–1.09) |
|  | logit_l2 | 0.903 (0.893–0.912) | 0.131 (0.112–0.150) | 0.071 (0.058–0.082) | 0.0272 | 1.05 (1.02–1.09) | 1.02 (0.95–1.10) |
|  | logit_interact | 0.904 (0.894–0.913) | 0.133 (0.115–0.154) | 0.072 (0.059–0.085) | 0.0271 | 1.05 (1.01–1.08) | 1.02 (0.94–1.09) |
|  | **hgb** (selected) | 0.919 (0.910–0.928) | 0.166 (0.144–0.187) | 0.094 (0.080–0.106) | 0.0260 | 1.04 (1.01–1.07) | 1.04 (0.98–1.12) |
|  | rf | 0.913 (0.904–0.923) | 0.141 (0.122–0.160) | 0.054 (0.049–0.058) | 0.0276 | 1.53 (1.46–1.59) | 1.06 (0.98–1.15) |

Expected calibration error (20 equal-weight risk groups) is 0.0006–0.0009 (pre-crash) and
0.0008–0.0008 (circumstance) for the logistic and boosted models, against
0.0016 and 0.0027 for the random forest.

**Calibration by risk level** [`calibration_by_risk_tier`, `calibration_curves`]. Overall
observed/expected and the calibration slope are dominated by the high-risk crashes, which hold
most of the deaths; within tiers of predicted risk the test-year picture is less even (fatal,
weighted, observed/expected with 95% CI):

| Stage | Model | Lowest 50% of predicted risk | 50th–80th percentile | Highest 20% |
|---|---|---|---|---|
| pre_crash | logit_main | 0.82 (0.64–1.01) | 1.03 (0.88–1.25) | 1.09 (0.99–1.19) |
|  | hgb | 0.79 (0.59–0.98) | 0.95 (0.81–1.11) | 1.15 (1.06–1.24) |
| pre_crash+circumstance | logit_main | 0.58 (0.42–0.77) | 0.81 (0.64–0.99) | 1.09 (1.03–1.17) |
|  | hgb | 0.48 (0.31–0.63) | 0.88 (0.75–1.06) | 1.10 (1.03–1.18) |
|  | rf | 0.29 (0.19–0.40) | 0.53 (0.44–0.64) | 1.32 (1.24–1.43) |

In the circumstance stage the lowest-risk half of crashes holds 5.3% (boosting) to
6.0% (main-effects logistic) of the expected deaths, and its observed fatal share is
0.48 (boosting) and 0.58 (logistic) of the share the
models predict; the highest-risk fifth has observed/expected 1.10 (boosting). The
absolute errors are small (boosting: predicted 0.06% vs observed 0.03% in the lowest half),
but predicted fatal shares for the lowest-risk configurations, and ratios that use them, are
overstated by the factor shown (up to about two-fold or more). The same pattern, slightly weaker, holds for the
main-effects logistic model, which is close to calibrated within these tiers on its own
training years and already shows the pattern in 2022 (an in-sample and validation-year check,
not tabulated); it is therefore mostly a shift between the training and later years rather
than a property of boosting (for boosting, in-sample tiers cannot separate it from
overfitting). KA shows the same direction (lowest half, boosting and logistic,
observed/expected 0.66 and 0.72 in the circumstance stage).

**KA, weighted** (prevalence 0.031): pre-crash AUROC 0.725 (logit_main), 0.726
(logit_interact), 0.753 (0.743–0.763) (hgb), 0.747 (rf); circumstance stage 0.830 (0.820–0.843)
(logit_main), 0.831 (logit_interact), 0.849 (0.839–0.859) (hgb), 0.846 (rf). Brier skill 0.063 / 0.072 (pre-crash,
logit_main / hgb) and 0.121 / 0.139 (circumstance). The KA models' observed/expected in the
test years is 0.93–0.95 (pre-crash) and 0.93–0.95 (circumstance; hgb circumstance
0.932 (0.891–0.984)), i.e. below 1 (slight over-prediction), and their calibration slopes are
1.06–1.12 for the logistic and boosted models
(a slope above 1 means predictions slightly too spread), against 1.34 and 1.42 for the random forest.

**Paired differences** (same bootstrap replicates; [`paired_differences`]):

* Boosting vs main-effects logistic, fatal: AUROC 0.019 (0.014–0.024) pre-crash and
  0.016 (0.012–0.022) circumstance; Brier skill 0.006 (0.002–0.009) and
  0.023 (0.017–0.029); average precision 0.035 (0.025–0.045) in the circumstance stage.
  KA: AUROC 0.028 (0.023–0.035) and 0.019 (0.012–0.027).
* The 13 pre-specified interaction terms add little (`logit_interact` vs `logit_main`): fatal AUROC 0.003 (0.002–0.004) pre-crash
  and 0.001 (0.001–0.002) circumstance; Brier skill 0.001 (0.000–0.002) and 0.002 (-0.000 to 0.004).
* L2 tuning changes nothing measurable (`logit_l2` vs `logit_main`, fatal AUROC 0.0000 (-0.0002 to 0.0001) pre-crash and 0.0000 (-0.0000 to 0.0000) circumstance).
* The random forest discriminates better than logistic (circumstance AUROC 0.010 (0.005–0.016)) but its
  Brier skill is lower (-0.017 (-0.025 to -0.008)) because its probabilities are compressed
  towards the mean (calibration slope 1.5).
* Adding crash configuration raises AUROC by 0.086 (0.074–0.099) (hgb) and 0.088 (0.075–0.102)
  (logit_main) for fatal and Brier skill by 0.066 (0.055–0.076) / 0.049 (0.039–0.059): crash type is by far the most
  informative recorded circumstance.

### 5.2 By year and subgroup (fatal, circumstance stage, weighted) [`metrics_test`]

| Domain | n (fatal) | hgb AUROC | logit_main AUROC | hgb observed/expected | logit_main observed/expected |
|---|---|---|---|---|---|
| 2023 | 50,103 (1,134) | 0.919 (0.910–0.928) | 0.904 (0.893–0.914) | 1.06 (0.97–1.16) | 1.03 (0.93–1.12) |
| 2024 | 51,658 (1,101) | 0.920 (0.908–0.930) | 0.901 (0.886–0.913) | 1.03 (0.93–1.12) | 1.01 (0.90–1.11) |
| Urban (PSU) | 76,402 (1,505) | 0.919 (0.908–0.931) | 0.905 (0.893–0.917) | 1.07 (0.99–1.17) | 1.04 (0.96–1.14) |
| Rural (PSU) | 25,359 (730) | 0.914 (0.902–0.928) | 0.893 (0.879–0.908) | 1.00 (0.89–1.11) | 0.99 (0.85–1.09) |
| Multi-vehicle | 67,751 (956) | 0.929 (0.916–0.941) | 0.916 (0.901–0.929) | 0.94 (0.86–1.03) | 0.96 (0.87–1.06) |
| Single-vehicle | 24,612 (772) | 0.839 (0.817–0.858) | 0.809 (0.788–0.827) | 1.07 (0.96–1.19) | 1.02 (0.92–1.14) |
| Pedestrian / cyclist | 9,398 (507) | 0.854 (0.829–0.876) | 0.829 (0.804–0.852) | 1.25 (1.11–1.39) | 1.15 (1.00–1.29) |
| Motorcycle involved | 6,132 (347) | 0.750 (0.723–0.775) | 0.718 (0.685–0.749) | 1.21 (1.09–1.36) | 1.12 (1.00–1.27) |
| No motorcycle | 92,800 (1,836) | 0.912 (0.901–0.922) | 0.894 (0.881–0.904) | 1.01 (0.94–1.09) | 1.00 (0.92–1.09) |
| Not hit-and-run | 88,633 (2,043) | 0.917 (0.907–0.926) | 0.898 (0.887–0.909) | 1.11 (1.04–1.19) | 1.08 (1.00–1.16) |
| Hit-and-run | 13,128 (192) | 0.944 (0.927–0.962) | 0.940 (0.919–0.957) | 0.61 (0.45–0.77) | 0.61 (0.44–0.77) |

Performance is stable across the two test years. Fatal shares among motorcycle and
pedestrian/cyclist crashes in 2023–2024 were higher than the models (trained on 2016–2021)
predict: observed/expected 1.12–1.25 for the logistic and boosted models
(more for the random forest, 1.72 for pedestrians and cyclists), and hit-and-run crashes were *less* often fatal
than predicted (observed/expected 0.61 for boosting; hit-and-run status is not an input; the models see it only through the proxy unknowns of §2). Within crash families, discrimination is weaker than
overall because much of the overall AUROC comes from separating families (pedestrian vs
rear-end). In the pre-crash stage the subgroup calibration by crash family is necessarily
poor (pedestrian/cyclist observed/expected 12.5 for boosting): those models do not know the crash type.

### 5.3 Risk thresholds (fatal; thresholds fixed on 2022 predictions) [`thresholds`]

Counts are unweighted test records (2023–2024); "per year" values are estimated
police-reported crashes per year; ratios are weighted with bootstrap CIs.

| Model (circumstance stage) | Rule (2022 threshold) | Threshold | Flagged | Sensitivity | PPV | TP (records) | FP (records) | FN (records) | FP per year (est.) | FN per year (est.) |
|---|---|---|---|---|---|---|---|---|---|---|
| logit_main | top 1% of 2022 crashes (weighted) | 0.076 | 1.0% | 0.29 (0.26–0.32) | 0.174 (0.157–0.189) | 637 | 2,774 | 1,598 | 50,465 | 26,354 |
| logit_main | top 5% of 2022 crashes (weighted) | 0.021 | 4.9% | 0.57 (0.54–0.60) | 0.070 (0.064–0.076) | 1,246 | 10,806 | 989 | 279,349 | 16,000 |
| logit_main | 50% recall in 2022 (weighted) | 0.024 | 4.2% | 0.54 (0.51–0.57) | 0.077 (0.070–0.084) | 1,175 | 9,574 | 1,060 | 237,709 | 17,079 |
| hgb | top 1% of 2022 crashes (weighted) | 0.080 | 1.0% | 0.31 (0.29–0.34) | 0.182 (0.170–0.196) | 707 | 2,603 | 1,528 | 51,971 | 25,374 |
| hgb | top 5% of 2022 crashes (weighted) | 0.021 | 4.9% | 0.59 (0.57–0.62) | 0.072 (0.066–0.079) | 1,320 | 9,868 | 915 | 282,443 | 15,108 |
| hgb | 50% recall in 2022 (weighted) | 0.030 | 3.4% | 0.52 (0.49–0.56) | 0.092 (0.085–0.100) | 1,151 | 7,264 | 1,084 | 189,922 | 17,762 |

Even the best model flags many non-fatal crashes for every fatal one: at the 1% threshold the
weighted PPV of boosting (circumstance stage) is 18.2%, i.e. about
1 in 5 flagged crashes is fatal, and at the 5% threshold 1 in 14; this is a property of a
low-prevalence outcome (0.60% of crashes), not a defect. The thresholds carry over from 2022 closely
(the top-1% rule flags 1.0% of test crashes, the top-5% rule
4.9%). These are descriptive operating points, not recommended decision rules.

## 6. Temporal stability and feature-set sensitivity

**Trained on 2016–2019, evaluated on each later year** [`temporal_stability`,
`figures/ml/temporal_stability_*.png`]. Fatal, circumstance stage; boosting (hgb) and, for
comparison, the main-effects logistic model:

| Evaluation year | hgb AUROC | hgb observed/expected | hgb calibration slope | logit_main AUROC | logit_main observed/expected |
|---|---|---|---|---|---|
| 2020 | 0.867 (0.847–0.885) | 1.13 (1.04–1.22) | 0.88 (0.83–0.93) | 0.856 | 1.15 |
| 2021 | 0.906 (0.886–0.919) | 1.11 (1.03–1.20) | 0.96 (0.91–1.01) | 0.893 | 1.13 |
| 2022 | 0.903 (0.892–0.913) | 1.17 (1.09–1.29) | 0.95 (0.91–0.99) | 0.886 | 1.15 |
| 2023 | 0.914 (0.904–0.924) | 1.11 (1.02–1.20) | 1.01 (0.98–1.05) | 0.902 | 1.07 |
| 2024 | 0.913 (0.900–0.927) | 1.07 (0.97–1.17) | 1.00 (0.96–1.06) | 0.899 | 1.03 |

Models trained before 2020 under-predict the higher fatal share
of police-reported crashes after 2020 (RQ5): observed/expected is above 1 in every later year
(boosting 1.07–1.17). The 2020 calibration slope
(0.88 (0.83–0.93)) and AUROC dip coincide with the pandemic change in traffic. KA models show
the reverse drift (observed/expected 0.91–0.98 from 2021). These refits reuse the boosting
hyper-parameters tuned on 2022 (number of trees re-chosen by early stopping within 2016–2019),
so the 2020–2022 evaluations borrow a small amount of information from 2022 through the
hyper-parameter choice (not through any fitted value). Ranking is stable; the level drifts
(fatal observed/expected up to 1.17), so absolute probabilities should be read with year-specific
calibration in mind. Models trained on 2016–2021 under-predicted 2022 by a similar margin
(validation observed/expected 1.11–1.15 for fatal, all models and both stages, from the 2022 tuning rows) and were closer in 2023–2024
(test observed/expected 1.02–1.06, boosting and logistic, both stages).

**Alternative feature sets** (fatal, circumstance stage, refitted on 2016–2021, evaluated on
2023–2024) [`feature_sensitivity`]:

| Variant | Model | AUROC | Average precision | Brier skill | Observed / expected | Δ AUROC vs main (paired 95% CI) | Δ Brier skill vs main (paired 95% CI) |
|---|---|---|---|---|---|---|---|
| Main feature set | hgb | 0.919 (0.910–0.928) | 0.166 | 0.094 | 1.04 (0.98–1.12) | — | — |
|  | logit_main | 0.903 (0.893–0.912) | 0.131 | 0.071 | 1.02 (0.95–1.09) | — | — |
| Without speeding and imputed alcohol | hgb | 0.904 (0.894–0.913) | 0.143 | 0.080 | 1.06 (0.99–1.15) | -0.016 (-0.021 to -0.011) | -0.014 (-0.018 to -0.010) |
|  | logit_main | 0.889 (0.877–0.899) | 0.116 | 0.063 | 1.03 (0.95–1.12) | -0.014 (-0.019 to -0.010) | -0.008 (-0.013 to -0.003) |
| Plus police-reported drugs and distraction | hgb | 0.922 (0.913–0.930) | 0.177 | 0.100 | 0.91 (0.85–0.99) | 0.002 (-0.001 to 0.006) | 0.006 (-0.001 to 0.015) |
|  | logit_main | 0.908 (0.898–0.917) | 0.140 | 0.076 | 0.87 (0.80–0.94) | 0.005 (0.002–0.008) | 0.005 (0.001–0.012) |
| Police-reported instead of imputed alcohol | hgb | 0.918 (0.907–0.928) | 0.169 | 0.094 | 0.93 (0.86–1.01) | -0.002 (-0.006 to 0.003) | -0.000 (-0.015 to 0.014) |
|  | logit_main | 0.903 (0.890–0.913) | 0.136 | 0.075 | 0.88 (0.81–0.97) | -0.000 (-0.006 to 0.006) | 0.005 (-0.005 to 0.014) |
| Proxy-blind (unknown time of day, motorcycle, heavy vehicle, speeding and missing vehicle age imputed) | hgb | 0.916 (0.907–0.926) | 0.160 | 0.090 | 1.05 (0.98–1.13) | -0.003 (-0.005 to -0.001) | -0.004 (-0.007 to -0.001) |
|  | logit_main | 0.901 (0.889–0.911) | 0.127 | 0.069 | 1.02 (0.95–1.10) | -0.002 (-0.004 to -0.001) | -0.002 (-0.004 to -0.000) |

* Dropping police-reported speeding and imputed alcohol changes AUROC by -0.014 (logistic) and
  -0.016 (boosting): they carry
  information beyond crash configuration, but severity-dependent ascertainment means part of
  it may reflect more thorough recording in severe crashes (`docs/limitations.md` §2).
* Adding police-reported drug and distraction fields changes discrimination by
  +0.002 (boosting) and +0.005 (logistic) AUROC; using police-reported instead of imputed alcohol changes it by
  -0.002 and -0.000. The first two variants break calibration in the test years
  (observed/expected 0.91 and 0.87 with drugs and distraction; 0.93 and 0.88 with police-reported alcohol): these fields have coding breaks (2017–2020) and severity-dependent unknown
  rates, which is why they are not model inputs.
* The proxy-blind refit, in which unknowns that mostly mark hit-and-run crashes carry no
  information, changes AUROC by -0.003 (-0.005 to -0.001) (boosting) and
  -0.002 (-0.004 to -0.001) (logistic) and Brier skill by -0.004 (-0.007 to -0.001) (boosting): the hit-and-run proxy contributes a small, measurable part of the
  boosted model's probability accuracy and little to ranking. The comparison with the
  main models therefore changes no conclusion of this report.

## 7. Interpretation (model-predicted; not causal)

**Permutation importance** (weighted: the permuted input is replaced by draws from its
weighted test distribution; increase in weighted log loss as a percentage of the baseline, 3 repeats) [`permutation_importance`,
`figures/ml/permutation_importance_fatal.png`]. Fatal; inputs in the order of the boosted circumstance-stage ranking at
the time of writing (the table, not the order, is authoritative). Crash type is moved together
with the vehicle count, and speed limit as band and mph together; the vehicle count is drawn
within crash type, so it is the count's value *given* crash type and no impossible crash is created:

| Input | Circumstance stage, hgb | Circumstance stage, logit_main | Pre-crash stage, hgb | Pre-crash stage, logit_main |
|---|---|---|---|---|
| `crash_type` | 42.3% | 34.5% | — | — |
| `speed_limit` | 11.7% | 7.8% | 6.5% | 5.1% |
| `any_motorcycle` | 7.3% | 6.3% | 6.0% | 5.5% |
| `junction` | 4.4% | 3.9% | 1.8% | 1.2% |
| `alcohol_im` | 4.2% | 3.6% | 5.3% | 4.7% |
| `speeding` | 2.9% | 1.9% | 1.8% | 1.2% |
| `light` | 1.9% | 0.5% | 1.4% | 1.0% |
| `any_heavy_truck` | 1.4% | 1.7% | 1.0% | 1.1% |
| `tod` | 1.4% | 0.9% | 1.4% | 0.8% |
| `region` | 1.1% | 0.1% | 1.4% | 0.4% |
| `older_driver` | 1.1% | 1.0% | 0.8% | 0.7% |
| `surface` | 1.0% | 0.7% | 0.4% | 0.3% |
| `oldest_vehicle_age` | 0.9% | 0.8% | 1.0% | 0.8% |
| `n_vehicles` | 0.5% | 0.3% | — | — |
| `urbanicity` | 0.4% | 0.5% | 0.8% | 0.4% |
| `weekend` | 0.2% | 0.1% | 0.1% | 0.1% |
| `weather` | 0.1% | 0.2% | 0.1% | 0.1% |
| `young_driver` | 0.1% | 0.0% | 0.2% | 0.1% |
| `work_zone` | 0.0% | 0.0% | 0.0% | 0.0% |
| `interstate` | -0.0% | 0.1% | 0.3% | 0.3% |

Importance measures how much a model *relies* on an input to rank recorded
crashes; it is not the input's causal effect, and correlated inputs share or trade importance
(light and time of day, speed limit and interstate).

**Partial dependence** [`partial_dependence`, `ice_curves`,
`figures/ml/partial_dependence_fatal.png`; circumstance stage, averaged over 3,000 weight-proportional test
crashes]. Selected values of the speed-limit and oldest-vehicle-age curves
(model-predicted probability of a fatal crash):

| Input and value | hgb | logit_main | logit_interact |
|---|---|---|---|
| Speed limit 15 mph | 0.0022 | 0.0016 | 0.0017 |
| Speed limit 30 mph | 0.0036 | 0.0036 | 0.0037 |
| Speed limit 45 mph | 0.0076 | 0.0071 | 0.0071 |
| Speed limit 55 mph | 0.0138 | 0.0122 | 0.0124 |
| Speed limit 60 mph | 0.0129 | 0.0096 | 0.0098 |
| Speed limit 75 mph | 0.0162 | 0.0152 | 0.0157 |
| Oldest-vehicle age 0 years | 0.0049 | 0.0043 | 0.0044 |
| Oldest-vehicle age 10 years | 0.0048 | 0.0055 | 0.0056 |
| Oldest-vehicle age 16 years | 0.0060 | 0.0064 | 0.0065 |
| Oldest-vehicle age 20 years | 0.0063 | 0.0071 | 0.0071 |
| Oldest-vehicle age 30 years | 0.0067 | 0.0090 | 0.0090 |

Boosting follows the logistic band structure for speed limit, but its oldest-vehicle-age curve
flattens at older ages where the logistic model's linear term keeps rising (compare the
rows above and the full curves in `partial_dependence`).

**Implied interactions vs the logistic interaction model** [`implied_interactions`]. For each
of the 13 pre-specified RQ2 pairs (11 of them exist in the pre-crash stage), every reference crash was assigned the four exposure
combinations and the mean double difference of predicted log-odds computed. The table puts boosting's
implied interactions next to the logistic product-term coefficients (`logit_interact`; its double
difference equals the product coefficient); the two models agree where their values have the same sign and similar size.
The random forest's implied interactions are not interpreted (its compressed probabilities make them an artefact).

| Pair | Circumstance: hgb | Circumstance: logit_interact | Pre-crash: hgb | Pre-crash: logit_interact |
|---|---|---|---|---|
| speeding x dark_unlit | -0.01 | -0.11 | -0.20 | -0.05 |
| speeding x wet | -0.06 | -0.47 | +0.00 | -0.16 |
| speeding x alcohol | +0.29 | +0.15 | -0.10 | -0.14 |
| alcohol x dark_unlit | -0.11 | -0.17 | -0.11 | -0.12 |
| high_speed_road x dark_unlit | -0.11 | -0.28 | -0.23 | -0.38 |
| motorcycle x speeding | +0.07 | -0.15 | +0.21 | +0.03 |
| motorcycle x alcohol | +0.05 | +0.02 | -0.19 | -0.33 |
| young_driver x late_night | +0.02 | +0.14 | -0.01 | +0.17 |
| older_driver x angle | +0.09 | +0.08 | — | — |
| heavy_truck x high_speed_road | +0.35 | +0.13 | +0.32 | +0.25 |
| rural x dark_unlit | +0.03 | -0.18 | -0.18 | -0.39 |
| weekend x late_night | -0.15 | -0.39 | -0.21 | -0.41 |
| pedestrian x dark_unlit | +0.60 | +0.62 | — | — |

**Screen for other interactions and confirmation.** A Friedman H screen of all input pairs of
the boosted fatal model (log-odds scale, 1,000 weight-proportional **2022** crashes, i.e.
discovery data disjoint from the test years) ranks pairs by H² [`interaction_screen`].
Pairs that are pre-specified or structurally dependent (Cramér's V
> 0.5, e.g. crash type × vehicle count) were not carried forward. For the top three remaining
pairs, the cell with the largest boosting double difference (≥ 30 training fatal crashes in
each cell used) was tested in a transparent survey-weighted logistic model on the
**independent 2023–2024 data**, with all circumstance-stage covariates plus vehicle-age bands
(vehicle count omitted when the pair involves crash type, as in `analysis/severity.py`),
design-based Wald F tests (Taylor linearisation, 42 design df = 67 variance PSUs − 25 strata), standardised margins and Holm
adjustment across all candidates in the table. Two non-linearity checks (oldest-vehicle age, speed-limit
bands) were tested alongside [`pattern_confirmation`].

**The screen's candidates changed between runs.** The pairs the screen carries forward depend on the
fitted boosting model and the 2022 discovery sample, and they differed in an earlier run of this
module (for example, a speeding × angle-collision interaction was a candidate then and is not among the
current ones). The candidates below are therefore exploratory leads generated by one run,
confirmed or not in independent data, not a fixed list of established interactions; a pattern should be
read as a finding only if it is also robust to re-running the screen.

Interactions (the boosting log-odds double difference is on the screen data; survey estimates are
product-term log odds ratios on 2023–2024, with the additive contrast on the risk scale):

| Candidate (screened on 2016–2022 crashes, tested on 2023–2024) | Boosting log-odds double difference | Survey product-term log OR (95% CI) | Ratio of ORs | Additive interaction contrast (95% CI) | Wald p | Holm p | Boosting estimate inside survey CI | Verdict |
|---|---|---|---|---|---|---|---|---|
| speed_limit=40-45 x crash_type=pedestrian (refs 30-35, mv_rear_end) | +1.79 | 0.32 (-0.08 to 0.72) | 1.38 | 0.071 (0.038–0.105) | 0.11 | 0.11 | False | not confirmed (Holm p>=0.05); boosting magnitude outside the survey 95% CI |
| junction=intersection x crash_type=mv_head_on (refs non_junction, mv_rear_end) | -1.84 | -1.76 (-2.21 to -1.31) | 0.17 | -0.050 (-0.064 to -0.036) | 9e-10 | 4.5e-09 | True | supported (Holm p<0.05, same direction) |
| any_motorcycle=yes x crash_type=sv_rollover_first (refs no, mv_rear_end) | -2.55 | -2.20 (-2.87 to -1.52) | 0.11 | -0.008 (-0.020 to 0.003) | 5.8e-08 | 2.3e-07 | True | supported (Holm p<0.05, same direction) |

Standardised adjusted fatal risks behind the additive contrasts (predictive margins over all
2023–2024 crashes; "first factor" is the first factor named in the candidate with the second at its
reference level, and vice versa):

| Candidate | Both references | First factor only | Second factor only | Both factors |
|---|---|---|---|---|
| speed_limit=40-45 x crash_type=pedestrian (refs 30-35, mv_rear_end) | 0.09% | 0.13% | 8.75% | 15.95% |
| junction=intersection x crash_type=mv_head_on (refs non_junction, mv_rear_end) | 0.17% | 0.11% | 5.85% | 0.77% |
| any_motorcycle=yes x crash_type=sv_rollover_first (refs no, mv_rear_end) | 0.12% | 1.62% | 1.17% | 1.84% |

Departures from the logistic form (non-linearity checks):

| Candidate | Wald F | Numerator df | Holm p | Boosting estimate | Boosting estimate measures | Survey odds ratios (95% CI) | Verdict |
|---|---|---|---|---|---|---|---|
| oldest-vehicle age: departure from linearity (age bands beyond a linear term) | 3.91 | 4 | 0.028 | +0.17 | boosting PD log-odds, age 30 minus age 18 (logit_main, linear: 0.314) | veh_age_band[4-7]: OR 1.18 (0.863-1.61); veh_age_band[8-12]: OR 1.07 (0.801-1.43); veh_age_band[13-17]: OR 1.49 (1.07-2.06); veh_age_band[18+]: OR 1.58 (1.01-2.46) | departure from the logistic form supported (Holm p<0.05); boosting shape: 2 of 4 terms confirmed, 0 contradicted, 0 outside the survey 95% CI |
| speed limit: differences within the 10-mph bands (25/35/45/55/65/75+ vs lower value) | 3.24 | 6 | 0.028 | +0.09 | boosting PD log-odds 35 minus 30 mph; all within-band contrasts: 25-20: -0.129, 35-30: 0.090, 45-40: 0.107, 55-50: 0.396, 65-60: 0.019, 75-70: 0.234 | sl_25_in_band: OR 1.29 (0.656-2.52); sl_35_in_band: OR 1.88 (1.35-2.61); sl_45_in_band: OR 1.19 (0.87-1.64); sl_55_in_band: OR 0.943 (0.66-1.35); sl_65_in_band: OR 0.946 (0.591-1.52); sl_75plus_in_band: OR 0.599 (0.354-1.01) | departure from the logistic form supported (Holm p<0.05); boosting shape: 1 of 6 terms confirmed, 0 contradicted, 3 outside the survey 95% CI |

Survey estimates are adjusted associations on the test years (design-based); adjusted risks are
standardised predictive margins over all 2023–2024 crashes. Interactions with a "supported" verdict
are crash-type-specific effects that the main-effects logistic model cannot represent and that
none of the 13 pre-specified pairs covers. How much of boosting's advantage over the logistic models
such effects explain was not quantified (no logistic model with these terms was evaluated on the test
years). They describe *severity given a recorded crash*. Any mechanism (for instance that a head-on
crash at an intersection is often a lower-speed turning conflict while a non-junction head-on is a
higher-speed lane departure) is a hypothesis, not tested with these data (travel and impact speeds are not
recorded). None of this is causal or says anything about how often such crashes occur.

## 8. Model selection and recommended use

The rule, pre-specified in the module docstring rather than the research plan, selects **boosting** in every outcome and stage cell
(the table in §3; `tests/test_reports_in_sync.py` fails if that stops being true, so this sentence cannot go stale
unnoticed). It is adequate
(fatal, test years: calibration slope 1.04 pre-crash and 1.04 circumstance, observed/expected 1.06 and 1.04; this overall calibration nets under-prediction in crashes without a hit-and-run,
observed/expected 1.11 (1.04–1.19), against over-prediction in hit-and-run crashes, 0.61; §5.2),
better than the main-effects logistic model on every proper scoring rule (paired CIs exclude
zero, §5.1) and better than the other logistic variants by similar margins. The gain is moderate (fatal AUROC 0.019 (0.014–0.024) pre-crash and 0.016 (0.012–0.022) circumstance; Brier skill 0.006 (0.002–0.009) and 0.023 (0.017–0.029)). It does not come from the
RQ2 interactions, which boosting reproduces and the logistic interaction model already
contains; the screen points to crash-type-specific effects (§7), some of which were confirmed in the independent test years
(see the verdicts there; the candidates are exploratory leads). Consequences:

* **Risk stratification of recorded crashes and the interface:** boosting, circumstance stage
  when crash configuration is known, pre-crash stage otherwise.
* **Explanation and inference:** the survey logistic models of RQ1/RQ2, whose predictions are
  nearly as good (AUROC lower by 0.016 (0.012–0.022) in the circumstance stage, similarly calibrated, including the same low-risk
  over-prediction in the test years) and whose coefficients have
  design-based standard errors. The confirmatory analyses above show which specific
  boosting-detected patterns those models should add.
* **What the comparison with the interacted logistic model does and does not show.** The statement
  above that the gain over the logistic models "does not come from the RQ2 interactions" is partly
  answered by `severity/fatal_effect_modification` (added after the red-team review): the crash-type
  interactions it tests are large and statistically clear for exceeding the limit, alcohol,
  motorcycles and large trucks. For "too fast for conditions" there is no detectable difference
  between single- and multi-vehicle crashes (homogeneity p = 0.84) but finer crash types do
  differ (p = 0.026); both p-values are in the table, and a non-significant test is not evidence
  that the ratios are equal. That table estimates
  effect modification within the survey model; it is not a prediction comparison. The head-to-head
  comparison of boosting against a logistic model that includes the crash-type interactions (AUROC
  and the other proper scoring rules, with paired intervals) **was not done**, so it remains
  untested whether boosting's advantage disappears once those interactions are in the logistic model.
* L2 tuning changes nothing measurable. The random forest discriminates slightly better than the
  logistic models (§5.1) but has lower Brier skill and was a single untuned configuration, so it
  brings nothing that would change the selection; this says nothing about a tuned forest.

## 9. Model cards

Common to all models — **Target:** P(fatal) (or P(KA)) for a police-reported crash, given its
recorded circumstances. **Population:** CRSS police-reported crashes on US trafficways,
2016–2024, with determinable outcome; estimates refer to the weighted population of
police-reported crashes. **Training data:** CRSS 2016–2021, 313,277 crashes (6,422 fatal,
39,789 KA), survey weights as sample weights; preprocessing fitted on these years only.
**Validation:** 2022 for tuning and thresholds; 2023–2024 test as in §5–6; temporal stability
from 2016–2019 fits. **Appropriate use:** describing how the fatal share of recorded crashes
varies with recorded circumstances; comparing model classes; ranking recorded crashes for
research summaries; generating hypotheses for confirmatory survey analyses. **Inappropriate
use:** probability of crashing or risk per trip or mile; causal effect of changing an input
(speed limit, lighting, enforcement); decisions about individual people, drivers or
enforcement targets; crashes not reported to police; years far from 2016–2024 without
recalibration; reading permutation importance as preventability. **Shared limitations:**
police-reported behaviours (speeding, alcohol) are recorded differently by severity (speeding judged after the crash; alcohol imputed by NHTSA with an undocumented model);
some "unknown" inputs partly encode hit-and-run (§2); the fatal share drifts over time (§6);
CRSS urbanicity describes the sampling area, not the road; outcome is NHTSA's single
imputation (imputation variance not propagated).

| | `logit_main` | `logit_l2` | `logit_interact` | `hgb` | `rf` |
|---|---|---|---|---|---|
| Form | Additive on the log-odds scale; one coefficient per level | Same with tuned ridge (C per cell in §3) | Additive + 11 (pre-crash) or 13 product terms for the pre-specified RQ2 pairs | Boosted trees (iterations and leaves per cell in §3), any interaction | 100 trees averaged |
| Inputs | Stage inputs, one-hot + standardised numeric with missing indicators | Same | Same + products | Ordinal codes (native categorical splits) + numeric with missing indicators | One-hot |
| Fatal test AUROC (pre / circ.) | 0.815 / 0.903 | 0.815 / 0.903 | 0.818 / 0.904 | 0.833 / 0.919 | 0.828 / 0.913 |
| Fatal calibration slope (pre / circ.) | 1.02 / 1.05 | 1.03 / 1.05 | 1.02 / 1.05 | 1.04 / 1.04 | 1.30 / 1.53 |
| Strengths | Transparent; matches the survey estimator; design-based CIs available (delta method) | — | Tests pre-specified interactions explicitly | Best discrimination and scoring; calibrated overall (slope near 1), but over-predicts the lowest-risk half of test crashes (§5.1) | Good ranking |
| Specific limitations | Misses crash-type-specific effects (§7) | No gain over `logit_main` | Gains are negligible | Opaque; uncertainty only by refitting; extrapolates flatly outside the data | Compressed, poorly calibrated probabilities: do not use as probabilities |
| Use | Explanation, sensitivity checks | None beyond comparison | RQ2 cross-check | Selected model; interface | Comparison only |

Saved models: `outputs/models/ml/{outcome}__{stage}__{model}.joblib` (each a `FittedModel`
holding the training-fitted preprocessing and the estimator) and
`outputs/models/ml/interface_fatal.joblib` (the interface bundle).

## 10. Interface: `predict_crash_fatal_risk(conditions)`

`nhtsa_stats.models.severity_ml.predict_crash_fatal_risk(conditions: dict) -> dict` returns
the selected (boosted) model's predicted P(fatal) for a police-reported crash with the given
recorded conditions, with:

* **Standardisation.** Conditions not given are averaged over 5,000 weight-proportional
  2023–2024 crashes (listed in `marginalized_over`). Structurally linked inputs are drawn
  jointly (crash type with vehicle count; speed-limit band with mph) so the average never
  contains an impossible crash.
* **Uncertainty range.** 95% interval from 20 refits of the boosted model on Rao–Wu
  PSU-bootstrap replicates of the training years (SE on the logit scale, t with 19 df); the
  main-effects logistic prediction with its design-based delta-method interval; and the range
  across the four model classes (`model_range`). The intervals reflect sampling uncertainty of
  the fitted model only — not misspecification, measurement error or drift (§6).
* **Refusals.** Unknown or non-permitted inputs (including `YEAR` and `hit_and_run`),
  category values not seen in training, numbers outside the training range, and impossible
  configurations (e.g. a single-vehicle rollover with two vehicles) return
  `status = "refused"` with the reason and the allowed values.
* **Flags.** Levels with fewer than 30 training fatal crashes, and "unknown" values of the
  hit-and-run proxy inputs.
* **Labels.** `label` ("model-predicted, conditional on a police-reported crash"),
  `population`, a `caveat` string (which also notes the test-year subgroup and risk-tier
  miscalibration of §5.1–5.2), and the model's test performance.

Predictions are model-predicted, use the 2023–2024 crash mix for unspecified inputs, and are returned with the boosted
model's refit interval and the main-effects logistic model's design-based interval. They are not tabulated in this document because they
come from the saved bundle, not from an output table; call the function to read them. Examples of
conditions to try: `{}` (the average police-reported crash), `{"speed_limit_mph": 25}` and `65`, `{"any_motorcycle": "yes"}`,
motorcycle with speeding and alcohol, `{"crash_type": "mv_rear_end"}` and `"pedestrian"` (with `"light": "dark_not_lighted"`
and a speed limit), and head-on collisions at an intersection versus away from a junction. Where the two models differ most,
the difference is crash-type-specific structure that the main-effects model lacks (pedestrian crashes in the dark, the
pre-specified pedestrian × dark-unlit pair that the logistic interaction model also contains: §7 implied interactions; and
head-on collisions by junction location, a candidate in the §7 confirmation table). A request
with `any_motorcycle = "unknown"` returns a prediction with a proxy flag; `light = "purple"` and
`speed_limit_mph = 120` are refused.

## 11. Limitations specific to the prediction models

* **Conditional on a reported crash.** Nothing here concerns crash occurrence; a condition
  with a high predicted fatal share may be rare or may prevent many crashes.
* **Ascertainment.** Speeding, alcohol and unknown codes are recorded after the crash and recorded
  differently when someone dies; their predictive value is partly a recording effect. Police-judged
  speeding is flagged `recorded_after_crash` in the variable registry; NHTSA-imputed alcohol is
  registered as pre-crash but may carry outcome information. Refitting without speeding and imputed
  alcohol changes the boosted model's circumstance-stage AUROC by -0.016 (-0.021 to -0.011)
  [`feature_sensitivity`], so part of the discrimination rests on them.
* **Hit-and-run proxy.** Bounded by the proxy-blind refit (§6) but not removed from the
  primary models; the cleaner fix is NHTSA-imputed body type and model year upstream.
* **Drift.** The fatal share among police-reported crashes rose after 2020; models trained on
  earlier years under-predict later years (observed/expected up to 1.17, §6), and fatal shares in
  motorcycle and pedestrian/cyclist crashes in 2023–2024 exceed predictions (observed/expected 1.12–1.25, §5.2). In
  the test years the lowest-risk half of crashes was over-predicted (observed/expected 0.48 for boosting) and the
  top fifth under-predicted (1.10, §5.1), so risk ratios between low- and high-risk
  configurations are understated.
* **Imputed outcome.** `MAXSEV_IM` is a single imputation; its variance is not propagated.
* **Imputed alcohol input.** Where police-reported alcohol is unknown, `alcohol_im` is NHTSA's
  imputation, whose model is undocumented; its gradient by fatal status among imputed records
  is as steep as among police-reported ones (§2), so it may carry outcome information. The
  refit with police-reported alcohol (§6) bounds the effect on discrimination; the driver-age
  flags rest on NHTSA-imputed age in the same way (not tested).
* **Temporal-stability hyper-parameters.** The 2016–2019 refits reuse the boosting settings
  tuned on 2022 (§6).
* **Interaction screen.** The H screen sets each input to each level for all reference crashes;
  for pairs that involve the vehicle count alone this creates some impossible crashes (crash
  type is not moved with it), so those screen values are approximate. Permutation importance
  draws the vehicle count within crash type and is not affected.
* **Bootstrap scope.** CIs cover sampling variation of the test crashes given the fitted
  models (and, in the interface, refitting on bootstrap replicates); they do not include
  hyper-parameter selection.
* **Confirmation scope.** Only the screened candidates in the §7 table were tested; patterns outside the
  screen were not, a non-significant test is not evidence of no interaction, and the candidates
  themselves change between runs of the screen.

## 12. Outputs and reproduction

`uv run nhtsa analyze ml` (or `nhtsa_stats.models.severity_ml.run()`) rebuilds everything; the last run took
473 s of wall time and 13,393 s of CPU time [`run_info.json`]. Boosting is much faster with a single OpenMP thread when other processes share the
CPUs (`OMP_NUM_THREADS=1`); thread settings, runtime and CPU time are recorded in
`run_info.json`. Seeds derive from `config.RANDOM_SEED`.

| Table (`outputs/tables/ml/`) | Content |
|---|---|
| `feature_sets` | Inputs per stage with registry timing; excluded variables and why |
| `hit_and_run_proxy` | Hit-and-run share among crashes with each input unknown |
| `alcohol_imputation_check` | Imputed alcohol by fatal status, police-reported vs imputed records |
| `tuning`, `selection.json` | 2022 tuning results and the selection rule outcome |
| `metrics_test` | Every metric × model × stage × outcome × domain, weighted and unweighted, with bootstrap CIs and reliability flags |
| `model_comparison` | Wide comparison (all crashes) |
| `paired_differences` | Model and stage differences on paired replicates |
| `calibration_curves` | 20-group reliability curves with CIs |
| `calibration_by_risk_tier` | Observed/expected within the lowest 50%, 50th–80th percentile and top 20% of predicted risk, with CIs |
| `thresholds` | Confusion matrices at the three thresholds |
| `temporal_stability` | Models trained 2016–2019, evaluated 2020–2024 by year |
| `feature_sensitivity` | Alternative feature sets incl. proxy-blind, with paired differences |
| `permutation_importance`, `partial_dependence`, `ice_curves`, `implied_interactions`, `interaction_screen` | Interpretation (model-predicted) |
| `pattern_confirmation` | Confirmatory survey-weighted tests (adjusted associations, test years) |
| `run_info.json` | Rows, events, prevalences, runtime, thread settings |

Figures (`outputs/figures/ml/`): `calibration_fatal`, `calibration_ka`, `model_comparison`,
`temporal_stability_fatal`, `temporal_stability_ka`, `permutation_importance_fatal`,
`partial_dependence_fatal`.

## Phase 2 models

Phase-2 models are explanatory survey logistic models (no tuning), documented in
`docs/methodology.md` §12. Validation specific to them:

* **Reproduction of Phase 1.** The speeding lattice's model with the six model-A blocks
  reproduces the Phase-1 adjusted exceedance RR exactly (5.21; compare the model-A row of the speeding lattice with `severity/fatal_speeding_type`).
* **Convergence and support.** Every factorial model records convergence and the number of
  withheld combinations (`multifactor/analyses`).
* **Predictive contribution.** `contributions/predictive` uses the Phase-1 temporal split
  (train 2016–2021, test 2023–2024) with a design-weighted pseudo-R² and AUROC; the full logistic
  model's test AUROC is close to the Phase-1 main-effects survey logistic model with configuration.
  Uncertainty: PSU-within-stratum bootstrap of the test set with the model fixed (training
  variability not included).
