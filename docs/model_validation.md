# Prediction-model validation (RQ8)

This document is the validation report and the set of model cards for the severity-prediction
models in `src/nhtsa_stats/models/severity_ml.py` (module `ml`). Every number below (except
the interface examples of §10, which are calls to the saved interface bundle) is read
from an output table in `outputs/tables/ml/` (named in brackets) and was produced by
`nhtsa_stats.models.severity_ml.run()`; figures are in `outputs/figures/ml/` and fitted
models in `outputs/models/ml/` (git-ignored).

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
| Population | CRSS police-reported crashes (all severities; national probability sample), 2016–2024, with a determinable maximum severity (`MAXSEV_IM` not 5/6/8) |
| Unit | Crash |
| Outcomes | `fatal` = imputed maximum severity K vs O/C/B/A (primary); `ka` = K or A vs O/C/B (secondary). Processed outcomes (project definition v1.2); never inputs |
| Split | Train 2016–2021 (311,700 crashes; 6,422 fatal; 39,789 KA) · validation 2022 (53,828; 1,301; 7,180) — tuning, selection and thresholds only · test 2023–2024 (101,480; 2,235; 13,376) — never used for a choice |
| Inputs | Registry-checked pre-crash variables (stage `pre_crash`), plus crash type and vehicle count (stage `pre_crash+circumstance`); `YEAR` is not an input |
| Preprocessing | One-hot / ordinal encoders, median imputation, missing indicators and scaling fitted on the training years only |
| Models | (1) logistic, main effects; (2) L2 logistic, C tuned on 2022; (3) logistic + the 13 pre-specified RQ2 interaction products; (4) histogram gradient boosting, small grid tuned on 2022, early stopping on an internal split of the training years; (5) random forest, one modest configuration |
| Weights | Survey weights (`WEIGHT`, normalised to mean 1) as sample weights in every fit; metrics both weighted and unweighted |
| Uncertainty | Rao–Wu rescaled bootstrap of variance PSUs (`PSU_VAR`, 67) within strata (`PSUSTRAT`, 25), 200 replicates, seed `config.RANDOM_SEED`; paired model differences on the same replicates |
| Selection | Pre-specified on 2022: first of logit_main < logit_l2 < logit_interact < hgb < rf whose weighted log loss is within 1% of the best and weighted AUROC within 0.005 of the best |

Weighted fatal prevalence (estimated share of police-reported crashes that are fatal):
0.556% (train), 0.663% (2022), 0.602% (test); unweighted sample shares 2.06%, 2.42%, 2.20%.
KA: 3.20%, 3.31%, 3.13% weighted; 12.8%, 13.3%, 13.2% unweighted [`run_info.json`].

## 2. Inputs and leakage control

**Stage `pre_crash`** (17 categorical + 2 numeric): region, CRSS urbanicity, time of day,
weekend, light, weather, surface, speed-limit band, interstate, junction, work zone, driver
15–20 involved, driver 65+ involved, motorcycle involved, medium/heavy truck or bus involved,
speeding-related (police), alcohol-involved (NHTSA-imputed); posted speed limit in mph and age
of the oldest vehicle, each with a missing indicator. **Stage `pre_crash+circumstance`** adds
crash type (10 levels) and number of vehicles in transport. Tri-state indicators enter as
yes / no / unknown; unknown is never "no". The full list with registry timing and declared
levels is in [`feature_sets`].

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
| Oldest-vehicle age missing | 2.4% | 96.6% | 10.9% | 17.7% |
| Motorcycle involvement unknown | 3.6% | 95.2% | 9.8% | 26.9% |
| Heavy-vehicle involvement unknown | 3.8% | 91.4% | 9.8% | 27.2% |
| Time of day unknown | 0.6% | 71.0% | 12.5% | 3.4% |
| Speeding unknown | 4.1% | 68.4% | 10.5% | 21.7% |
| All other unknowns (light, weather, surface, speed limit, junction, interstate, driver age) | — | 13.9–31.3% | 12.5–12.9% | — |

These inputs are kept as specified (unknown is information about the record, and recoding it to
"no" would be worse), but three checks bound their influence: (i) a **proxy-blind refit**
(§6) in which the five proxy inputs' unknowns are replaced, in training and test data, by
draws from the weighted training distribution of known values, so they carry no information;
(ii) evaluation **stratified by hit-and-run status** (used only to split the test set, never
as an input); (iii) the interface flags any request that sets one of these inputs to
"unknown".

**Imputed alcohol.** `alcohol_im` equals the police-reported alcohol field where that is known
and is NHTSA's imputation where it is unknown (14% of weighted training crashes in 2016–2018,
36% in 2019–2021); the imputation model is not documented. Among *imputed* records the
weighted share imputed "yes" is 6.7 (2016–2018) and 4.2 (2019–2021) times higher in fatal than
in non-fatal crashes, against 6.4 and 5.5 among police-reported records
[`alcohol_imputation_check`; training years]. An imputation that ignored severity would show a
much flatter gradient, so the imputed values very likely depend on severity or on
severity-related fields, and may carry outcome information into this input. The input is kept
because it is registered pre-crash and is the project's adjustment variable, but its effect is
bounded by the refit that uses the police-reported field (with its "unknown" level) instead:
test AUROC changes by −0.001 (boosting) and 0.000 (logistic) (§6). The driver-age flags
(`young_driver`, `older_driver`) likewise rest on NHTSA-imputed age (about 5–8% of CRSS person
ages are imputed each year; `docs/audit/crss_survey_design.md`), so the same caveat applies;
it was not tested here.

## 3. Models, tuning and selection

| Model | Specification | Tuned on 2022 (weighted log loss) |
|---|---|---|
| `logit_main` | Weighted pseudo-likelihood logistic regression (Newton–Cholesky), tiny ridge C = 100 — the estimator of `analysis/survey.py: SurveyLogit` with λ = 0.01 (tested to agree) | — |
| `logit_l2` | Same, C ∈ {10⁻⁴, 10⁻³, 10⁻², 0.1, 1, 10} | chosen C: 1 (pre-crash, both outcomes; KA circumstance) or 10 (fatal circumstance) — i.e. essentially no shrinkage helps |
| `logit_interact` | `logit_main` + one product term per pre-specified RQ2 pair whose variables are in the stage (11 in `pre_crash`, all 13 in `pre_crash+circumstance`) | — |
| `hgb` | `HistGradientBoostingClassifier`, native categorical handling, learning rate 0.1, L2 1.0, max 500 iterations, early stopping on a 15% internal split of 2016–2021; grid max_leaf_nodes ∈ {15, 31} × min_samples_leaf ∈ {100, 400} | fatal: (31, 400; 89 iterations) pre-crash, (31, 100; 121) circumstance · KA: (15, 400; 170), (15, 400; 215) |
| `rf` | `RandomForestClassifier`, 100 trees, √p features, 50% row subsample, min_samples_leaf 50 (one configuration: comparison model only) | — |

[`tuning`, `selection.json`] The pre-specified rule selected **boosting in all four
outcome × stage cells**: the logistic models' 2022 weighted log loss was 2.1–5.1% above
boosting's (tolerance 1%) and their AUROC 0.020–0.026 lower (tolerance 0.005). The selected
and all other fitted models are those trained on 2016–2021 (not refitted on 2022), so the test
years evaluate exactly the saved models.

## 4. Weighted versus unweighted metrics

CRSS samples crashes with unequal probabilities: injury, motorcycle, non-motorist and
newer-vehicle crashes are over-sampled (the within-PSU sampling strata are defined by injury
severity, vehicle type and vehicle age), and each crash carries a weight equal to the number of police-reported
crashes it represents. **Weighted** metrics estimate performance in the population of
police-reported crashes; they are the relevant ones for any statement about crashes in the
United States. **Unweighted** metrics describe performance on the sampled records. Because
the models are fitted with weights, their predictions are calibrated to the population, so
on the sample they under-predict (unweighted observed/expected 1.8–2.7 for fatal; 3.0 for the
pre-crash random forest) and the
reliability curves lie above the diagonal (`figures/ml/calibration_*.png`). Discrimination
is lower unweighted (fatal, circumstance stage, boosting: AUROC 0.874 vs 0.921 weighted)
because the sample's non-fatal crashes are more often injury crashes, which are harder to
separate from fatal ones. Unweighted metrics are reported for completeness and as a
design-dependence check; they are not population estimates.

## 5. Test-set performance (2023–2024)

### 5.1 Model comparison — fatal, weighted (estimated; 95% PSU-bootstrap CIs) [`metrics_test`, `model_comparison`]

| Stage | Model | AUROC | Average precision (prevalence 0.0060) | Brier skill | Log loss | Calibration slope | Observed / expected |
|---|---|---|---|---|---|---|---|
| pre_crash | logit_main | 0.815 (0.795–0.832) | 0.052 (0.044–0.062) | 0.022 (0.016–0.027) | 0.0318 | 1.02 (0.96–1.09) | 1.03 (0.94–1.14) |
| | logit_l2 | 0.815 (0.795–0.832) | 0.052 (0.044–0.062) | 0.022 (0.016–0.028) | 0.0318 | 1.03 (0.97–1.09) | 1.03 (0.94–1.14) |
| | logit_interact | 0.818 (0.798–0.835) | 0.052 (0.044–0.064) | 0.023 (0.017–0.029) | 0.0317 | 1.02 (0.96–1.09) | 1.03 (0.94–1.14) |
| | **hgb** (selected) | 0.835 (0.820–0.849) | 0.058 (0.048–0.070) | 0.028 (0.022–0.034) | 0.0311 | 1.01 (0.96–1.07) | 1.05 (0.96–1.15) |
| | rf | 0.828 (0.811–0.844) | 0.051 (0.044–0.061) | 0.020 (0.018–0.023) | 0.0317 | 1.30 (1.21–1.40) | 1.05 (0.95–1.16) |
| pre_crash+circumstance | logit_main | 0.903 (0.893–0.912) | 0.132 (0.112–0.152) | 0.071 (0.058–0.084) | 0.0272 | 1.05 (1.01–1.08) | 1.02 (0.94–1.09) |
| | logit_l2 | 0.903 (0.893–0.912) | 0.132 (0.113–0.152) | 0.071 (0.058–0.084) | 0.0272 | 1.05 (1.02–1.09) | 1.02 (0.94–1.09) |
| | logit_interact | 0.904 (0.895–0.914) | 0.134 (0.116–0.156) | 0.073 (0.060–0.085) | 0.0271 | 1.05 (1.01–1.08) | 1.01 (0.94–1.09) |
| | **hgb** (selected) | 0.921 (0.912–0.929) | 0.165 (0.143–0.188) | 0.093 (0.080–0.107) | 0.0260 | 1.03 (1.00–1.06) | 1.04 (0.97–1.11) |
| | rf | 0.912 (0.900–0.922) | 0.136 (0.119–0.154) | 0.054 (0.050–0.058) | 0.0276 | 1.51 (1.44–1.57) | 1.04 (0.97–1.14) |

Expected calibration error (20 equal-weight risk groups) is 0.0006–0.0008 for the logistic and
boosted models and 0.0016–0.0027 for the random forest.

**Calibration by risk level** [`calibration_by_risk_tier`, `calibration_curves`]. Overall
observed/expected and the calibration slope are dominated by the high-risk crashes, which hold
most of the deaths; within tiers of predicted risk the test-year picture is less even (fatal,
weighted, observed/expected with 95% CI):

| Stage | Model | Lowest 50% of predicted risk | 50th–80th percentile | Highest 20% |
|---|---|---|---|---|
| pre_crash | logit_main | 0.82 (0.64–1.02) | 1.03 (0.86–1.24) | 1.09 (0.98–1.19) |
| | hgb | 0.80 (0.62–0.98) | 1.05 (0.86–1.25) | 1.09 (1.00–1.19) |
| pre_crash+circumstance | logit_main | 0.57 (0.41–0.75) | 0.81 (0.65–0.99) | 1.09 (1.02–1.16) |
| | hgb | 0.47 (0.32–0.63) | 0.85 (0.70–1.02) | 1.09 (1.03–1.17) |
| | rf | 0.30 (0.19–0.41) | 0.52 (0.41–0.64) | 1.31 (1.22–1.41) |

In the circumstance stage the lowest-risk half of crashes (about 5–6% of the expected deaths)
had roughly half the fatal share the models predict, and the top fifth about 9% more. The
absolute errors are small (boosting: predicted 0.06% vs observed 0.03% in the lowest half),
but predicted fatal shares for the lowest-risk configurations, and ratios that use them, are
overstated by up to about two-fold. The same pattern, slightly weaker, holds for the
main-effects logistic model, which is close to calibrated within these tiers on its own
training years and already shows the pattern in 2022 (an in-sample and validation-year check,
not tabulated); it is therefore mostly a shift between the training and later years rather
than a property of boosting (for boosting, in-sample tiers cannot separate it from
overfitting). KA shows the same direction (lowest half 0.68–0.84 for the logistic and
boosted models).

**KA, weighted** (prevalence 0.031): pre-crash AUROC 0.725 (logit_main), 0.726
(logit_interact), 0.752 (0.742–0.762; hgb), 0.748 (rf); circumstance stage 0.830
(0.820–0.843), 0.831, 0.849 (0.839–0.858), 0.846. Brier skill 0.063 / 0.071 (pre-crash,
logit_main / hgb) and 0.121 / 0.141 (circumstance). All KA models over-predict slightly in
the test years (observed/expected 0.93–0.95; hgb circumstance 0.930, 0.888–0.977) and their
calibration slopes are 1.08–1.11 (predictions slightly too spread), except the random forest
(1.34–1.45).

**Paired differences** (same bootstrap replicates; [`paired_differences`]):

* Boosting vs main-effects logistic, fatal: AUROC +0.020 (0.014 to 0.026) pre-crash and
  +0.018 (0.013 to 0.023) circumstance; Brier skill +0.006 (0.002 to 0.009) and +0.021
  (0.016 to 0.028); average precision +0.033 (0.024 to 0.042) in the circumstance stage.
  KA: AUROC +0.028 (0.023 to 0.034) and +0.018 (0.012 to 0.026).
* The 13 pre-specified interaction terms add little: AUROC +0.003 (0.002 to 0.004) pre-crash
  and +0.001 (0.001 to 0.002) circumstance for fatal; Brier skill +0.001 (CIs touching 0).
* L2 tuning changes nothing measurable (all differences < 0.0002).
* The random forest discriminates better than logistic (circumstance AUROC +0.009) but its
  Brier skill is lower (−0.017, −0.026 to −0.009) because its probabilities are compressed
  towards the mean (calibration slope 1.5).
* Adding crash configuration raises AUROC by 0.086 (0.075 to 0.097; hgb) and 0.088
  (logit_main) for fatal and Brier skill by 0.065 / 0.049: crash type is by far the most
  informative recorded circumstance.

### 5.2 By year and subgroup (fatal, circumstance stage, weighted) [`metrics_test`]

| Domain | n (fatal) | hgb AUROC | logit_main AUROC | hgb observed/expected | logit_main observed/expected |
|---|---|---|---|---|---|
| 2023 | 49,972 (1,134) | 0.921 (0.912–0.930) | 0.904 | 1.06 (0.96–1.15) | 1.03 |
| 2024 | 51,508 (1,101) | 0.920 (0.908–0.931) | 0.901 | 1.02 (0.92–1.11) | 1.01 |
| Urban (PSU) | 76,178 (1,505) | 0.921 | 0.905 | 1.06 | 1.03 |
| Rural (PSU) | 25,302 (730) | 0.916 | 0.893 | 1.00 | 0.985 |
| Multi-vehicle | 67,632 (956) | 0.930 (0.918–0.941) | 0.916 | 0.94 (0.86–1.04) | 0.96 |
| Single-vehicle | 24,504 (772) | 0.843 (0.821–0.864) | 0.809 | 1.06 (0.96–1.18) | 1.01 |
| Pedestrian / cyclist | 9,344 (507) | 0.857 (0.832–0.880) | 0.828 | 1.20 (1.07–1.34) | 1.14 (0.99–1.28) |
| Motorcycle involved | 6,083 (347) | 0.749 (0.719–0.774) | 0.718 | 1.24 (1.11–1.40) | 1.12 (1.00–1.27) |
| No motorcycle | 92,574 (1,836) | 0.914 | 0.894 | 1.00 | 1.00 |
| Not hit-and-run | 88,392 (2,043) | 0.919 (0.908–0.928) | 0.899 | 1.11 (1.03–1.18) | 1.08 (1.00–1.16) |
| Hit-and-run | 13,088 (192) | 0.943 (0.922–0.962) | 0.940 | 0.60 (0.44–0.76) | 0.61 (0.44–0.77) |

Performance is stable across the two test years. Fatal shares among motorcycle and
pedestrian/cyclist crashes in 2023–2024 were higher than the models (trained on 2016–2021)
predict, by 12–24% depending on the model, and hit-and-run crashes were *less* often fatal
than predicted (hit-and-run status is not an input; the models see it only through the proxy unknowns of §2). Within crash families, discrimination is weaker than
overall because much of the overall AUROC comes from separating families (pedestrian vs
rear-end). In the pre-crash stage the subgroup calibration by crash family is necessarily
poor (pedestrian/cyclist observed/expected ≈ 12): those models do not know the crash type.

### 5.3 Risk thresholds (fatal; thresholds fixed on 2022 predictions) [`thresholds`]

Counts are unweighted test records (2023–2024); "per year" values are estimated
police-reported crashes per year; ratios are weighted with bootstrap CIs.

| Model (circumstance stage) | Rule (threshold) | Flagged | Sensitivity | PPV | TP / FP / FN (records) | FP per year (est.) | FN per year (est.) |
|---|---|---|---|---|---|---|---|
| hgb | top 1% of 2022 risk (0.082) | 1.0% | 0.31 (0.29–0.34) | 0.19 (0.17–0.20) | 705 / 2,537 / 1,530 | 50,756 | 25,419 |
| hgb | top 5% (0.021) | 4.9% | 0.60 (0.57–0.63) | 0.075 (0.069–0.081) | 1,340 / 9,782 / 895 | 277,535 | 14,627 |
| hgb | 50% recall in 2022 (0.031) | 3.2% | 0.51 (0.49–0.54) | 0.097 (0.091–0.105) | 1,142 / 6,901 / 1,093 | 174,942 | 18,113 |
| logit_main | top 1% (0.076) | 1.0% | 0.29 (0.26–0.32) | 0.17 (0.16–0.19) | 640 / 2,766 / 1,595 | 50,392 | 26,329 |
| logit_main | top 5% (0.021) | 4.9% | 0.57 (0.54–0.60) | 0.070 (0.064–0.076) | 1,248 / 10,771 / 987 | 278,991 | 15,990 |
| logit_main | 50% recall in 2022 (0.024) | 4.2% | 0.54 (0.51–0.57) | 0.078 (0.071–0.085) | 1,180 / 9,573 / 1,055 | 237,348 | 16,991 |

Even the best model flags four to five non-fatal crashes for every fatal one at the 1%
threshold and about twelve at the 5% threshold; this is a property of a 0.6% outcome, not a
defect. The thresholds carry over from 2022 almost exactly (top-1% rule flags 1.0% of test
crashes). These are descriptive operating points, not recommended decision rules.

## 6. Temporal stability and feature-set sensitivity

**Trained on 2016–2019, evaluated on each later year** [`temporal_stability`,
`figures/ml/temporal_stability_*.png`]. Fatal, circumstance stage, boosting: AUROC 0.867
(0.846–0.886) in 2020, then 0.907, 0.905, 0.915, 0.914 (2021–2024); main-effects logistic
0.856, 0.893, 0.887, 0.902, 0.899. Observed/expected was 1.11 (1.02–1.20) in 2020, 1.10, 1.15
(1.06–1.25), 1.08 and 1.04 — models trained before 2020 under-predict the higher fatal share
of police-reported crashes after 2020 (RQ5), most in 2020–2022. The 2020 calibration slope
(0.90, 0.84–0.95) and AUROC dip coincide with the pandemic change in traffic. KA models show
the reverse drift (observed/expected 0.91–0.98 from 2021). These refits reuse the boosting
hyper-parameters tuned on 2022 (number of trees re-chosen by early stopping within 2016–2019),
so the 2020–2022 evaluations borrow a small amount of information from 2022 through the
hyper-parameter choice (not through any fitted value). Ranking is stable; the level drifts
by up to about 15–20%, so absolute probabilities should be read with year-specific
calibration in mind. Models trained on 2016–2021 under-predicted 2022 by a similar margin
(validation observed/expected 1.11–1.15 for fatal) and were within 2–5% in 2023–2024.

**Alternative feature sets** (fatal, circumstance stage, refitted on 2016–2021, evaluated on
2023–2024) [`feature_sensitivity`]:

| Variant | Model | AUROC | Average precision | Brier skill | Observed / expected | Δ AUROC vs main (paired 95% CI) | Δ Brier skill vs main |
|---|---|---|---|---|---|---|---|
| Main feature set | hgb | 0.921 (0.912–0.929) | 0.165 | 0.093 | 1.04 | — | — |
| | logit_main | 0.903 (0.893–0.912) | 0.132 | 0.071 | 1.02 | — | — |
| Without speeding and imputed alcohol | hgb | 0.904 (0.894–0.914) | 0.143 | 0.080 | 1.05 | −0.016 (−0.023 to −0.011) | −0.013 (−0.016 to −0.009) |
| | logit_main | 0.889 (0.878–0.899) | 0.117 | 0.063 | 1.03 | −0.014 (−0.019 to −0.010) | −0.008 (−0.013 to −0.003) |
| Plus police-reported drugs and distraction | hgb | 0.923 (0.915–0.930) | 0.179 | 0.102 | 0.92 (0.86–1.00) | +0.002 (−0.001 to +0.006) | +0.009 (+0.004 to +0.015) |
| | logit_main | 0.908 (0.899–0.917) | 0.141 | 0.076 | 0.87 (0.80–0.94) | +0.005 (+0.002 to +0.008) | +0.005 (+0.001 to +0.011) |
| Police-reported instead of imputed alcohol | hgb | 0.919 (0.909–0.929) | 0.172 | 0.095 | 0.92 (0.85–0.99) | −0.001 (−0.007 to +0.005) | +0.002 (−0.014 to +0.015) |
| | logit_main | 0.903 (0.890–0.914) | 0.137 | 0.076 | 0.88 (0.81–0.97) | 0.000 (−0.006 to +0.007) | +0.005 (−0.005 to +0.014) |
| Proxy-blind (unknown time of day, motorcycle, heavy vehicle, speeding and missing vehicle age imputed) | hgb | 0.919 (0.910–0.928) | 0.154 | 0.086 | 1.05 | −0.002 (−0.004 to +0.000) | −0.007 (−0.010 to −0.005) |
| | logit_main | 0.901 (0.889–0.911) | 0.129 | 0.069 | 1.02 | −0.002 (−0.004 to −0.001) | −0.002 (−0.004 to 0.000) |

* Dropping police-reported speeding and imputed alcohol costs 0.014–0.016 AUROC: they carry
  information beyond crash configuration, but severity-dependent ascertainment means part of
  it may reflect more thorough recording in severe crashes (`docs/limitations.md` §2).
* Adding police-reported drug and distraction fields slightly raises discrimination (AUROC
  +0.002 to +0.005); using police-reported instead of imputed alcohol leaves it unchanged
  (−0.001 to 0.000). Both break calibration in the test years (observed/expected
  0.87–0.92): these fields have coding breaks (2017–2020) and severity-dependent unknown
  rates, which is why they are not model inputs.
* The proxy-blind refit, in which unknowns that mostly mark hit-and-run crashes carry no
  information, loses only 0.002 AUROC (boosting: −0.004 to
  +0.000; logistic: −0.004 to −0.001) and 0.007 Brier skill (boosting; −0.010 to −0.005; average
  precision −0.011): the hit-and-run proxy contributes a small, measurable part of the
  boosted model's probability accuracy and almost nothing to ranking. The comparison with the
  main models therefore changes no conclusion of this report.

## 7. Interpretation (model-predicted; not causal)

**Permutation importance** (weighted: the permuted input is replaced by draws from its
weighted test distribution; increase in weighted log loss, 3 repeats) [`permutation_importance`,
`figures/ml/permutation_importance_fatal.png`]. Fatal, circumstance stage, boosting: crash
type (moved together with the vehicle count) 43.6%, speed limit (band and mph together) 12.5%,
motorcycle involvement 7.4%, junction 4.7%, imputed alcohol 4.4%, speeding 3.0%, light 1.9%,
heavy vehicle 1.4%, older driver 1.3%, time of day 1.3%, surface 1.2%; all others below 1%
(oldest-vehicle age 0.9%, region 0.9%, vehicle count 0.5% — drawn within crash type, so it is
the count's value *given* crash type and no impossible crash is created — urbanicity 0.5%,
weather 0.3%, young driver 0.1%, weekend 0.1%, interstate and work zone ≈ 0). The main-effects logistic model ranks the inputs almost
identically (crash type 34.5%, speed limit 8.2%, motorcycle 6.2%, junction 3.9%, alcohol
3.6%). In the pre-crash stage the leading inputs are speed limit (6.9%), motorcycle (6.1%) and
alcohol (5.2%). Importance measures how much a model *relies* on an input to rank recorded
crashes; it is not the input's causal effect, and correlated inputs share or trade importance
(light and time of day, speed limit and interstate).

**Partial dependence** [`partial_dependence`, `ice_curves`,
`figures/ml/partial_dependence_fatal.png`; averaged over 3,000 weight-proportional test
crashes]. Speed limit: boosting 0.0025 at 15 mph, 0.0040 at 30, 0.0083 at 45, 0.0143 at 55,
0.0135 at 60 and 0.0176 at 75 mph, closely following the logistic band structure (0.0017 →
0.0157). Oldest-vehicle age: boosting is flat to about 10 years (≈ 0.0053–0.0061), rises to
≈ 0.0070 by 16 years and then plateaus (0.0076 at 30 years), whereas the logistic model's
linear term keeps rising (0.0048 at 0 to 0.0097 at 30 years).

**Implied interactions vs the logistic interaction model** [`implied_interactions`]. For each
of the 13 pre-specified RQ2 pairs, every reference crash was assigned the four exposure
combinations and the mean double difference of predicted log-odds computed. Boosting's
implied interactions agree with the logistic product-term coefficients: correlation 0.84 in
both stages, same sign for 11 of 11 pairs (pre-crash) and 11 of 13 (circumstance); the two
sign disagreements are small (motorcycle × alcohol −0.21 vs +0.02; speeding × dark-unlit
+0.03 vs −0.10). The largest are the same in both (circumstance-stage values; in the pre-crash
stage speeding × alcohol is −0.11 boosting, −0.14 logistic): pedestrian × dark-unlit (+0.81 boosting,
+0.63 logistic), heavy vehicle × 50+ mph road (+0.35, +0.13), speeding × alcohol (+0.21,
+0.14); and on the negative side speeding × wet (−0.15, −0.47) and weekend × late night
(−0.13, −0.39). The random forest's implied interactions are uniformly negative, an artefact of
its compressed probabilities, and are not interpreted.

**Screen for other interactions and confirmation.** A Friedman H screen of all input pairs of
the boosted fatal model (log-odds scale, 1,000 weight-proportional **2022** crashes, i.e.
discovery data disjoint from the test years) ranked crash-type pairs highest (speed limit ×
crash type, junction × crash type, speeding × crash type, motorcycle × crash type)
[`interaction_screen`]. Pairs that are pre-specified or structurally dependent (Cramér's V
> 0.5, e.g. crash type × vehicle count) were not carried forward. For the top three remaining
pairs, the cell with the largest boosting double difference (≥ 30 training fatal crashes in
each cell used) was tested in a transparent survey-weighted logistic model on the
**independent 2023–2024 data**, with all circumstance-stage covariates plus vehicle-age bands
(vehicle count omitted when the pair involves crash type, as in `analysis/severity.py`),
design-based Wald F tests (Taylor linearisation, 42 df), standardised margins and Holm
adjustment across the five candidates [`pattern_confirmation`]:

| Candidate (screened on 2016–2022, tested on 2023–2024) | Boosting estimate | Survey estimate (95% CI) | Additive interaction contrast | Holm p | Verdict |
|---|---|---|---|---|---|
| Intersection × head-on (refs: non-junction, rear-end) | log-odds double difference −1.89 | product-term log OR −1.76 (−2.21 to −1.31); ratio of ORs 0.17 | −0.050 (−0.065 to −0.036) | < 0.001 | **Supported** (boosting estimate inside the survey CI): adjusted fatal risk 0.8% for head-on crashes at intersections vs 5.9% away from junctions (rear-end: 0.11% vs 0.18%) |
| Speeding × angle collision (refs: not speeding, rear-end) | +1.07 | +0.74 (+0.36 to +1.13); ratio of ORs 2.1 | +0.020 (+0.012 to +0.028) | 0.001 | **Supported** (boosting estimate inside the survey CI): speeding is associated with a larger excess fatal risk in angle than in rear-end collisions (adjusted risks 2.8% vs 0.65% for angle; 0.28% vs 0.13% for rear-end) |
| 40–45 mph road × pedestrian (refs: 30–35 mph, rear-end) | +1.49 | +0.32 (−0.08 to +0.72) | +0.071 (+0.037 to +0.105) | 0.11 | **Not confirmed** on the multiplicative (odds) scale, and the boosting magnitude lies outside the survey 95% CI; the additive contrast is large because pedestrian risk is high (16.0% vs 8.8% for pedestrians; 0.13% vs 0.09% for rear-end) |
| Oldest-vehicle age: departure from a linear log-odds trend | flat to ~10 years, rising to ~16, then a plateau | bands beyond a linear term: F = 3.83 on 4 df; shape vs 0–3 years: OR 1.20 (0.90–1.62) 4–7, 1.12 (0.86–1.45) 8–12, 1.60 (1.24–2.06) 13–17, 1.77 (1.33–2.34) 18+ | — | 0.028 | **Supported** (non-linear); every boosting band contrast lies inside its survey CI, and 2 of 4 (13–17, 18+) are significant in the same direction, none contradicted. These band contrasts show the age gradient, not the plateau specifically: the survey ORs still rise from 13–17 (1.60) to 18+ (1.77), and the data cannot distinguish a plateau from a continued rise |
| Speed limit: differences within the 10-mph bands | 35 vs 30 mph +0.17; 55 vs 50 +0.38; 75 vs 70 +0.19 (log-odds) | F = 3.38 on 6 df; 35 vs 30 mph OR 1.90 (1.37–2.64); 55 vs 50 OR 0.95 (0.67–1.35); 75+ vs 70 OR 0.60 (0.35–1.01) | — | 0.028 | **Departure supported, boosting shape not reproduced**: within-band differences exist, but only 1 of 6 boosting contrasts (35 vs 30 mph) has the same sign and a CI excluding 0 (and the survey OR is larger than boosting's 1.18); for 35, 55 and 75+ mph the boosting contrast lies outside the survey 95% CI; none has a significant opposite sign |

Survey estimates are adjusted associations on the test years (design-based); adjusted risks are
standardised predictive margins over all 2023–2024 crashes. The two confirmed interactions
are crash-type-specific effects that the main-effects logistic model cannot represent and that
none of the 13 pre-specified pairs covers. Because crash-type pairs dominate the H screen,
such effects are a likely source of much of boosting's advantage; how much of the gap they
close was not quantified (no logistic model with these terms was evaluated on the test years).
They describe *severity given a recorded crash*. A plausible reading, not tested with these
data (travel and impact speeds are not recorded), is that an intersection head-on is often a
lower-speed turning conflict and a non-junction head-on a higher-speed lane departure, and
that "speeding" in an angle crash marks a vehicle entering a crossing path fast. None of this
is causal or says anything about how often such crashes occur.

## 8. Model selection and recommended use

The pre-specified rule selects **boosting** for both outcomes and stages; it is adequate
(calibration slope 1.01–1.03 and observed/expected 1.04–1.05 for fatal in the test years;
this overall calibration nets under-prediction in crashes without a hit-and-run,
observed/expected 1.11 (1.03–1.18), against over-prediction in hit-and-run crashes, 0.60; §5.2),
better than the main-effects logistic model on every proper scoring rule (paired CIs exclude
zero) and better than the other logistic variants by similar margins. The gain is moderate (AUROC +0.02, Brier skill +0.006 to +0.021). It does not come from the
RQ2 interactions, which boosting reproduces and the logistic interaction model already
contains; the screen points to crash-type-specific effects (§7), two of which were confirmed. Consequences:

* **Risk stratification of recorded crashes and the interface:** boosting, circumstance stage
  when crash configuration is known, pre-crash stage otherwise.
* **Explanation and inference:** the survey logistic models of RQ1/RQ2, whose predictions are
  nearly as good (AUROC within 0.02, similarly calibrated, including the same low-risk
  over-prediction in the test years) and whose coefficients have
  design-based standard errors. The confirmatory analyses above show which specific
  boosting-detected patterns those models should add.
* L2 tuning and the random forest bring nothing over the simpler alternatives.

## 9. Model cards

Common to all models — **Target:** P(fatal) (or P(KA)) for a police-reported crash, given its
recorded circumstances. **Population:** CRSS police-reported crashes on US trafficways,
2016–2024, with determinable maximum severity; estimates refer to the weighted population of
police-reported crashes. **Training data:** CRSS 2016–2021, 311,700 crashes (6,422 fatal,
39,789 KA), survey weights as sample weights; preprocessing fitted on these years only.
**Validation:** 2022 for tuning and thresholds; 2023–2024 test as in §5–6; temporal stability
from 2016–2019 fits. **Appropriate use:** describing how the fatal share of recorded crashes
varies with recorded circumstances; comparing model classes; ranking recorded crashes for
research summaries; generating hypotheses for confirmatory survey analyses. **Inappropriate
use:** probability of crashing or risk per trip or mile; causal effect of changing an input
(speed limit, lighting, enforcement); decisions about individual people, drivers or
enforcement targets; crashes not reported to police; years far from 2016–2024 without
recalibration; reading permutation importance as preventability. **Shared limitations:**
police-reported behaviours (speeding, alcohol) are recorded more thoroughly in severe crashes;
some "unknown" inputs partly encode hit-and-run (§2); the fatal share drifts over time (§6);
CRSS urbanicity describes the sampling area, not the road; outcome is NHTSA's single
imputation (imputation variance not propagated).

| | `logit_main` | `logit_l2` | `logit_interact` | `hgb` | `rf` |
|---|---|---|---|---|---|
| Form | Additive on the log-odds scale; one coefficient per level | Same with tuned ridge (C = 1 or 10) | Additive + 11 (pre-crash) or 13 product terms for the pre-specified RQ2 pairs | Boosted trees (89–215 trees, 15–31 leaves), any interaction | 100 trees averaged |
| Inputs | Stage inputs, one-hot + standardised numeric with missing indicators | Same | Same + products | Ordinal codes (native categorical splits) + numeric with missing indicators | One-hot |
| Fatal test AUROC (pre / circ.) | 0.815 / 0.903 | 0.815 / 0.903 | 0.818 / 0.904 | 0.835 / 0.921 | 0.828 / 0.912 |
| Fatal calibration slope (pre / circ.) | 1.02 / 1.05 | 1.03 / 1.05 | 1.02 / 1.05 | 1.01 / 1.03 | 1.30 / 1.51 |
| Strengths | Transparent; matches the survey estimator; design-based CIs available (delta method) | — | Tests pre-specified interactions explicitly | Best discrimination and scoring; calibrated overall (slope ≈ 1), but over-predicts the lowest-risk half of test crashes about two-fold (§5.1) | Good ranking |
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

Examples (model-predicted, 2023–2024 crash mix for unspecified inputs; boosted model with
its refit interval; main-effects logistic model with its design-based interval):

| Conditions | Stage | Boosting P(fatal) (95% interval) | Logistic P(fatal) (95% CI) |
|---|---|---|---|
| none (average police-reported crash) | pre-crash | 0.57% (0.53–0.62) | 0.58% (0.52–0.63) |
| speed limit 25 mph | pre-crash | 0.25% (0.21–0.31) | 0.25% (0.20–0.31) |
| speed limit 65 mph | pre-crash | 1.08% (0.89–1.31) | 0.87% (0.69–1.08) |
| motorcycle involved | pre-crash | 3.78% (3.33–4.28) | 4.31% (3.90–4.77) |
| motorcycle + speeding + alcohol | pre-crash | 17.3% (12.8–22.9) | 19.2% (16.0–22.7) |
| rear-end collision | circumstance | 0.19% (0.15–0.25) | 0.15% (0.13–0.19) |
| pedestrian crash | circumstance | 12.4% (9.5–16.1) | 11.2% (10.0–12.6) |
| pedestrian crash, dark and unlit | circumstance | 19.1% (14.7–24.5) | 13.5% (11.8–15.4) |
| pedestrian crash, dark and unlit, 45 mph | circumstance | 22.3% (16.7–29.1) | 15.0% (12.9–17.4) |
| head-on collision at an intersection | circumstance | 0.85% (0.57–1.28) | 1.71% (1.48–1.97) |
| head-on collision away from a junction | circumstance | 7.8% (6.5–9.3) | 4.0% (3.3–4.8) |

Where the two models differ most the difference is crash-type-specific structure that the
main-effects model lacks: pedestrian crashes in the dark (the pre-specified pedestrian ×
dark-unlit pair, which the logistic interaction model also contains; §7 implied interactions)
and head-on collisions by location (the intersection × head-on interaction confirmed in §7). A request
with `any_motorcycle = "unknown"` returns 0.44% with a proxy flag; `light = "purple"` and
`speed_limit_mph = 120` are refused.

## 11. Limitations specific to the prediction models

* **Conditional on a reported crash.** Nothing here concerns crash occurrence; a condition
  with a high predicted fatal share may be rare or may prevent many crashes.
* **Ascertainment.** Speeding, alcohol and unknown codes are recorded after the crash and more
  thoroughly when someone dies; their predictive value is partly a recording effect.
* **Hit-and-run proxy.** Bounded by the proxy-blind refit (§6) but not removed from the
  primary models; the cleaner fix is NHTSA-imputed body type and model year upstream.
* **Drift.** The fatal share among police-reported crashes rose after 2020; models trained on
  earlier years under-predict later years by up to about 15–20%, and fatal shares in
  motorcycle and pedestrian/cyclist crashes in 2023–2024 exceed predictions by 12–24%. In
  the test years the lowest-risk half of crashes was over-predicted about two-fold and the
  top fifth under-predicted by about 9% (§5.1), so risk ratios between low- and high-risk
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
* **Confirmation scope.** Only the five screened candidates were tested; patterns outside the
  screen were not, and a non-significant test is not evidence of no interaction.

## 12. Outputs and reproduction

`uv run nhtsa analyze ml` (or `nhtsa_stats.models.severity_ml.run()`) rebuilds everything in
about 11–13 minutes of wall time on a shared 4-CPU machine (about 12 CPU-minutes; peak
memory 2.0 GB). Boosting is much faster with a single OpenMP thread when other processes share the
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
