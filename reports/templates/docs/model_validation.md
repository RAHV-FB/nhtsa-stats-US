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
| Outcomes | `fatal` = imputed maximum severity K vs the rest (primary): {{json:ml/run_info|outcome_definitions.fatal|}}. `ka` = K or A vs the rest (secondary): {{json:ml/run_info|outcome_definitions.ka|}}. Processed outcomes (project outcome definitions); never inputs |
| Split | Train 2016–2021 ({{json:ml/run_info|rows.fatal.train|,.0f}} crashes with a determinable fatal outcome, of which {{json:ml/run_info|events.fatal.train|,.0f}} fatal; {{json:ml/run_info|rows.ka.train|,.0f}} with a determinable KA outcome, of which {{json:ml/run_info|events.ka.train|,.0f}} KA) · validation 2022 ({{json:ml/run_info|rows.fatal.valid|,.0f}}; {{json:ml/run_info|events.fatal.valid|,.0f}} fatal; {{json:ml/run_info|events.ka.valid|,.0f}} KA) — tuning, selection and thresholds only · test 2023–2024 ({{json:ml/run_info|rows.fatal.test|,.0f}}; {{json:ml/run_info|events.fatal.test|,.0f}} fatal; {{json:ml/run_info|events.ka.test|,.0f}} KA) — never used for a choice |
| Inputs | Registry-checked pre-crash variables (stage `pre_crash`), plus crash type and vehicle count (stage `pre_crash+circumstance`); `YEAR` is not an input |
| Preprocessing | One-hot / ordinal encoders, median imputation, missing indicators and scaling fitted on the training years only |
| Models | (1) logistic, main effects; (2) L2 logistic, C tuned on 2022; (3) logistic + the 13 pre-specified RQ2 interaction products; (4) histogram gradient boosting, small grid tuned on 2022, early stopping on an internal split of the training years; (5) random forest, one modest configuration |
| Weights | Survey weights (`WEIGHT`, normalised to mean 1) as sample weights in every fit; metrics both weighted and unweighted |
| Uncertainty | Rao–Wu rescaled bootstrap of variance PSUs (`PSU_VAR`) within strata (`PSUSTRAT`), {{json:ml/run_info|n_boot|.0f}} replicates, seed `config.RANDOM_SEED` ({{json:ml/run_info|seed|.0f}}); paired model differences on the same replicates |
| Selection | Pre-specified in the module docstring (`src/nhtsa_stats/models/severity_ml.py`), not in the research plan, and applied on 2022: first of logit_main < logit_l2 < logit_interact < hgb < rf whose weighted log loss is within 1% of the best and weighted AUROC within 0.005 of the best |

Weighted fatal prevalence (estimated share of police-reported crashes that are fatal):
{{json:ml/run_info|weighted_prevalence.fatal.train|pct:3}} (train), {{json:ml/run_info|weighted_prevalence.fatal.valid|pct:3}} (2022),
{{json:ml/run_info|weighted_prevalence.fatal.test|pct:3}} (test); unweighted sample shares
{{json:ml/run_info|unweighted_prevalence.fatal.train|pct:2}}, {{json:ml/run_info|unweighted_prevalence.fatal.valid|pct:2}},
{{json:ml/run_info|unweighted_prevalence.fatal.test|pct:2}}. KA: {{json:ml/run_info|weighted_prevalence.ka.train|pct:2}},
{{json:ml/run_info|weighted_prevalence.ka.valid|pct:2}}, {{json:ml/run_info|weighted_prevalence.ka.test|pct:2}} weighted;
{{json:ml/run_info|unweighted_prevalence.ka.train|pct:1}}, {{json:ml/run_info|unweighted_prevalence.ka.valid|pct:1}},
{{json:ml/run_info|unweighted_prevalence.ka.test|pct:1}} unweighted [`run_info.json`].

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

{{mdtable:ml/hit_and_run_proxy|treated_as_proxy=True|feature:Input (unknown / missing):;weighted_share_of_crashes:Share of crashes:pct:1;hit_and_run_share_among_unknown:Hit-and-run among these:pct:1;hit_and_run_share_among_known:Hit-and-run among known:pct:1;share_of_all_hit_and_run_crashes:Share of all hit-and-run crashes:pct:1}}
| All other unknowns (light, weather, surface, speed limit, junction, interstate, driver age) | — | {{ml/hit_and_run_proxy|treated_as_proxy=False|min(hit_and_run_share_among_unknown)|pct:1}}–{{ml/hit_and_run_proxy|treated_as_proxy=False|max(hit_and_run_share_among_unknown)|pct:1}} | {{ml/hit_and_run_proxy|treated_as_proxy=False|min(hit_and_run_share_among_known)|pct:1}}–{{ml/hit_and_run_proxy|treated_as_proxy=False|max(hit_and_run_share_among_known)|pct:1}} | — |

These inputs are kept as specified (unknown is information about the record, and recoding it to
"no" would be worse), but three checks bound their influence: (i) a **proxy-blind refit**
(§6) in which the five proxy inputs' unknowns are replaced, in training and test data, by
draws from the weighted training distribution of known values, so they carry no information;
(ii) evaluation **stratified by hit-and-run status** (used only to split the test set, never
as an input); (iii) the interface flags any request that sets one of these inputs to
"unknown".

**Imputed alcohol.** `alcohol_im` equals the police-reported alcohol field where that is known
and is NHTSA's imputation where it is unknown ({{ml/alcohol_imputation_check|period=2016-2018;alcohol_im_source=imputed (police-reported unknown)|weighted_share_of_crashes|pct:0}} of weighted training crashes in 2016–2018,
{{ml/alcohol_imputation_check|period=2019-2021;alcohol_im_source=imputed (police-reported unknown)|weighted_share_of_crashes|pct:0}} in 2019–2021); the imputation model is not documented. Among *imputed* records the
weighted share imputed "yes" is {{ml/alcohol_imputation_check|period=2016-2018;alcohol_im_source=imputed (police-reported unknown)|ratio|.1f}} (2016–2018) and {{ml/alcohol_imputation_check|period=2019-2021;alcohol_im_source=imputed (police-reported unknown)|ratio|.1f}} (2019–2021) times higher in fatal than
in non-fatal crashes, against {{ml/alcohol_imputation_check|period=2016-2018;alcohol_im_source=police-reported (known)|ratio|.1f}} and {{ml/alcohol_imputation_check|period=2019-2021;alcohol_im_source=police-reported (known)|ratio|.1f}} among police-reported records
[`alcohol_imputation_check`; training years]. An imputation that ignored severity would show a
much flatter gradient, so the imputed values very likely depend on severity or on
severity-related fields, and may carry outcome information into this input. The input is kept
because it is registered pre-crash and is the project's adjustment variable, but its effect is
bounded by the refit that uses the police-reported field (with its "unknown" level) instead:
test AUROC changes by {{ml/feature_sensitivity|outcome=fatal;stage=pre_crash+circumstance;variant=police-reported alcohol instead of alcohol_im;model=hgb;metric=auroc|diff_vs_main|+.4f}} (boosting) and {{ml/feature_sensitivity|outcome=fatal;stage=pre_crash+circumstance;variant=police-reported alcohol instead of alcohol_im;model=logit_main;metric=auroc|diff_vs_main|+.4f}} (logistic) (§6). The driver-age flags
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

{{mdtable:ml/model_comparison|selected_on_2022=True|outcome:Outcome:;stage:Stage:;model:Selected model:;auroc_w:Test AUROC (weighted):.3f;brier_skill_w:Test Brier skill (weighted):.3f}}

The 2022 tuning results of the chosen setting of every model (the rule compares weighted log
loss and AUROC; tolerance 1% and 0.005) are:

{{mdtable:ml/tuning|chosen=True|outcome:Outcome:;stage:Stage:;model:Model:;params:Chosen setting:;valid_log_loss_w:2022 weighted log loss:.4f;valid_auroc_w:2022 weighted AUROC:.3f}}

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
{{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=logit_main~logit_l2~logit_interact~hgb;domain=all;weighting=unweighted;metric=oe_ratio|min(estimate)|.1f}}–{{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=logit_main~logit_l2~logit_interact~hgb;domain=all;weighting=unweighted;metric=oe_ratio|max(estimate)|.1f}} for the logistic and boosted models, {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=rf;domain=all;weighting=unweighted;metric=oe_ratio|estimate|.1f}} for the random forest;
pre-crash {{ml/metrics_test|outcome=fatal;stage=pre_crash;model=logit_main~logit_l2~logit_interact~hgb;domain=all;weighting=unweighted;metric=oe_ratio|min(estimate)|.1f}}–{{ml/metrics_test|outcome=fatal;stage=pre_crash;model=logit_main~logit_l2~logit_interact~hgb;domain=all;weighting=unweighted;metric=oe_ratio|max(estimate)|.1f}} and {{ml/metrics_test|outcome=fatal;stage=pre_crash;model=rf;domain=all;weighting=unweighted;metric=oe_ratio|estimate|.1f}}) and the
reliability curves lie above the diagonal (`figures/ml/calibration_*.png`). Discrimination
is lower unweighted (fatal, circumstance stage, boosting: AUROC {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=hgb;domain=all;weighting=unweighted;metric=auroc|estimate|.3f}} vs {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=hgb;domain=all;weighting=weighted;metric=auroc|estimate|.3f}} weighted)
because the sample's non-fatal crashes are more often injury crashes, which are harder to
separate from fatal ones. Unweighted metrics are reported for completeness and as a
design-dependence check; they are not population estimates.

## 5. Test-set performance (2023–2024)

### 5.1 Model comparison — fatal, weighted (estimated; 95% PSU-bootstrap CIs) [`metrics_test`, `model_comparison`]

| Stage | Model | AUROC | Average precision (prevalence {{ml/metrics_test|outcome=fatal;stage=pre_crash;model=hgb;domain=all;weighting=weighted;metric=prevalence|estimate|.4f}}) | Brier skill | Log loss | Calibration slope | Observed / expected |
|---|---|---|---|---|---|---|---|
| pre_crash | logit_main | {{ml/metrics_test|outcome=fatal;stage=pre_crash;model=logit_main;domain=all;weighting=weighted;metric=auroc|estimate|ci:3@ci}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash;model=logit_main;domain=all;weighting=weighted;metric=average_precision|estimate|ci:3@ci}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash;model=logit_main;domain=all;weighting=weighted;metric=brier_skill|estimate|ci:3@ci}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash;model=logit_main;domain=all;weighting=weighted;metric=log_loss|estimate|.4f}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash;model=logit_main;domain=all;weighting=weighted;metric=calibration_slope|estimate|ci:2@ci}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash;model=logit_main;domain=all;weighting=weighted;metric=oe_ratio|estimate|ci:2@ci}} |
|  | logit_l2 | {{ml/metrics_test|outcome=fatal;stage=pre_crash;model=logit_l2;domain=all;weighting=weighted;metric=auroc|estimate|ci:3@ci}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash;model=logit_l2;domain=all;weighting=weighted;metric=average_precision|estimate|ci:3@ci}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash;model=logit_l2;domain=all;weighting=weighted;metric=brier_skill|estimate|ci:3@ci}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash;model=logit_l2;domain=all;weighting=weighted;metric=log_loss|estimate|.4f}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash;model=logit_l2;domain=all;weighting=weighted;metric=calibration_slope|estimate|ci:2@ci}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash;model=logit_l2;domain=all;weighting=weighted;metric=oe_ratio|estimate|ci:2@ci}} |
|  | logit_interact | {{ml/metrics_test|outcome=fatal;stage=pre_crash;model=logit_interact;domain=all;weighting=weighted;metric=auroc|estimate|ci:3@ci}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash;model=logit_interact;domain=all;weighting=weighted;metric=average_precision|estimate|ci:3@ci}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash;model=logit_interact;domain=all;weighting=weighted;metric=brier_skill|estimate|ci:3@ci}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash;model=logit_interact;domain=all;weighting=weighted;metric=log_loss|estimate|.4f}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash;model=logit_interact;domain=all;weighting=weighted;metric=calibration_slope|estimate|ci:2@ci}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash;model=logit_interact;domain=all;weighting=weighted;metric=oe_ratio|estimate|ci:2@ci}} |
|  | **hgb** (selected) | {{ml/metrics_test|outcome=fatal;stage=pre_crash;model=hgb;domain=all;weighting=weighted;metric=auroc|estimate|ci:3@ci}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash;model=hgb;domain=all;weighting=weighted;metric=average_precision|estimate|ci:3@ci}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash;model=hgb;domain=all;weighting=weighted;metric=brier_skill|estimate|ci:3@ci}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash;model=hgb;domain=all;weighting=weighted;metric=log_loss|estimate|.4f}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash;model=hgb;domain=all;weighting=weighted;metric=calibration_slope|estimate|ci:2@ci}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash;model=hgb;domain=all;weighting=weighted;metric=oe_ratio|estimate|ci:2@ci}} |
|  | rf | {{ml/metrics_test|outcome=fatal;stage=pre_crash;model=rf;domain=all;weighting=weighted;metric=auroc|estimate|ci:3@ci}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash;model=rf;domain=all;weighting=weighted;metric=average_precision|estimate|ci:3@ci}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash;model=rf;domain=all;weighting=weighted;metric=brier_skill|estimate|ci:3@ci}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash;model=rf;domain=all;weighting=weighted;metric=log_loss|estimate|.4f}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash;model=rf;domain=all;weighting=weighted;metric=calibration_slope|estimate|ci:2@ci}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash;model=rf;domain=all;weighting=weighted;metric=oe_ratio|estimate|ci:2@ci}} |
| pre_crash+circumstance | logit_main | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=logit_main;domain=all;weighting=weighted;metric=auroc|estimate|ci:3@ci}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=logit_main;domain=all;weighting=weighted;metric=average_precision|estimate|ci:3@ci}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=logit_main;domain=all;weighting=weighted;metric=brier_skill|estimate|ci:3@ci}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=logit_main;domain=all;weighting=weighted;metric=log_loss|estimate|.4f}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=logit_main;domain=all;weighting=weighted;metric=calibration_slope|estimate|ci:2@ci}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=logit_main;domain=all;weighting=weighted;metric=oe_ratio|estimate|ci:2@ci}} |
|  | logit_l2 | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=logit_l2;domain=all;weighting=weighted;metric=auroc|estimate|ci:3@ci}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=logit_l2;domain=all;weighting=weighted;metric=average_precision|estimate|ci:3@ci}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=logit_l2;domain=all;weighting=weighted;metric=brier_skill|estimate|ci:3@ci}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=logit_l2;domain=all;weighting=weighted;metric=log_loss|estimate|.4f}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=logit_l2;domain=all;weighting=weighted;metric=calibration_slope|estimate|ci:2@ci}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=logit_l2;domain=all;weighting=weighted;metric=oe_ratio|estimate|ci:2@ci}} |
|  | logit_interact | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=logit_interact;domain=all;weighting=weighted;metric=auroc|estimate|ci:3@ci}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=logit_interact;domain=all;weighting=weighted;metric=average_precision|estimate|ci:3@ci}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=logit_interact;domain=all;weighting=weighted;metric=brier_skill|estimate|ci:3@ci}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=logit_interact;domain=all;weighting=weighted;metric=log_loss|estimate|.4f}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=logit_interact;domain=all;weighting=weighted;metric=calibration_slope|estimate|ci:2@ci}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=logit_interact;domain=all;weighting=weighted;metric=oe_ratio|estimate|ci:2@ci}} |
|  | **hgb** (selected) | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=hgb;domain=all;weighting=weighted;metric=auroc|estimate|ci:3@ci}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=hgb;domain=all;weighting=weighted;metric=average_precision|estimate|ci:3@ci}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=hgb;domain=all;weighting=weighted;metric=brier_skill|estimate|ci:3@ci}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=hgb;domain=all;weighting=weighted;metric=log_loss|estimate|.4f}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=hgb;domain=all;weighting=weighted;metric=calibration_slope|estimate|ci:2@ci}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=hgb;domain=all;weighting=weighted;metric=oe_ratio|estimate|ci:2@ci}} |
|  | rf | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=rf;domain=all;weighting=weighted;metric=auroc|estimate|ci:3@ci}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=rf;domain=all;weighting=weighted;metric=average_precision|estimate|ci:3@ci}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=rf;domain=all;weighting=weighted;metric=brier_skill|estimate|ci:3@ci}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=rf;domain=all;weighting=weighted;metric=log_loss|estimate|.4f}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=rf;domain=all;weighting=weighted;metric=calibration_slope|estimate|ci:2@ci}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=rf;domain=all;weighting=weighted;metric=oe_ratio|estimate|ci:2@ci}} |

Expected calibration error (20 equal-weight risk groups) is {{ml/metrics_test|outcome=fatal;stage=pre_crash;model=logit_main~logit_l2~logit_interact~hgb;domain=all;weighting=weighted;metric=ece|min(estimate)|.4f}}–{{ml/metrics_test|outcome=fatal;stage=pre_crash;model=logit_main~logit_l2~logit_interact~hgb;domain=all;weighting=weighted;metric=ece|max(estimate)|.4f}} (pre-crash) and
{{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=logit_main~logit_l2~logit_interact~hgb;domain=all;weighting=weighted;metric=ece|min(estimate)|.4f}}–{{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=logit_main~logit_l2~logit_interact~hgb;domain=all;weighting=weighted;metric=ece|max(estimate)|.4f}} (circumstance) for the logistic and boosted models, against
{{ml/metrics_test|outcome=fatal;stage=pre_crash;model=rf;domain=all;weighting=weighted;metric=ece|estimate|.4f}} and {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=rf;domain=all;weighting=weighted;metric=ece|estimate|.4f}} for the random forest.

**Calibration by risk level** [`calibration_by_risk_tier`, `calibration_curves`]. Overall
observed/expected and the calibration slope are dominated by the high-risk crashes, which hold
most of the deaths; within tiers of predicted risk the test-year picture is less even (fatal,
weighted, observed/expected with 95% CI):

| Stage | Model | Lowest 50% of predicted risk | 50th–80th percentile | Highest 20% |
|---|---|---|---|---|
| pre_crash | logit_main | {{ml/calibration_by_risk_tier|outcome=fatal;stage=pre_crash;model=logit_main;weighting=weighted;risk_tier=lowest 50% of predicted risk|oe_ratio|ci:2@oe}} | {{ml/calibration_by_risk_tier|outcome=fatal;stage=pre_crash;model=logit_main;weighting=weighted;risk_tier=50th-80th percentile|oe_ratio|ci:2@oe}} | {{ml/calibration_by_risk_tier|outcome=fatal;stage=pre_crash;model=logit_main;weighting=weighted;risk_tier=highest 20%|oe_ratio|ci:2@oe}} |
|  | hgb | {{ml/calibration_by_risk_tier|outcome=fatal;stage=pre_crash;model=hgb;weighting=weighted;risk_tier=lowest 50% of predicted risk|oe_ratio|ci:2@oe}} | {{ml/calibration_by_risk_tier|outcome=fatal;stage=pre_crash;model=hgb;weighting=weighted;risk_tier=50th-80th percentile|oe_ratio|ci:2@oe}} | {{ml/calibration_by_risk_tier|outcome=fatal;stage=pre_crash;model=hgb;weighting=weighted;risk_tier=highest 20%|oe_ratio|ci:2@oe}} |
| pre_crash+circumstance | logit_main | {{ml/calibration_by_risk_tier|outcome=fatal;stage=pre_crash+circumstance;model=logit_main;weighting=weighted;risk_tier=lowest 50% of predicted risk|oe_ratio|ci:2@oe}} | {{ml/calibration_by_risk_tier|outcome=fatal;stage=pre_crash+circumstance;model=logit_main;weighting=weighted;risk_tier=50th-80th percentile|oe_ratio|ci:2@oe}} | {{ml/calibration_by_risk_tier|outcome=fatal;stage=pre_crash+circumstance;model=logit_main;weighting=weighted;risk_tier=highest 20%|oe_ratio|ci:2@oe}} |
|  | hgb | {{ml/calibration_by_risk_tier|outcome=fatal;stage=pre_crash+circumstance;model=hgb;weighting=weighted;risk_tier=lowest 50% of predicted risk|oe_ratio|ci:2@oe}} | {{ml/calibration_by_risk_tier|outcome=fatal;stage=pre_crash+circumstance;model=hgb;weighting=weighted;risk_tier=50th-80th percentile|oe_ratio|ci:2@oe}} | {{ml/calibration_by_risk_tier|outcome=fatal;stage=pre_crash+circumstance;model=hgb;weighting=weighted;risk_tier=highest 20%|oe_ratio|ci:2@oe}} |
|  | rf | {{ml/calibration_by_risk_tier|outcome=fatal;stage=pre_crash+circumstance;model=rf;weighting=weighted;risk_tier=lowest 50% of predicted risk|oe_ratio|ci:2@oe}} | {{ml/calibration_by_risk_tier|outcome=fatal;stage=pre_crash+circumstance;model=rf;weighting=weighted;risk_tier=50th-80th percentile|oe_ratio|ci:2@oe}} | {{ml/calibration_by_risk_tier|outcome=fatal;stage=pre_crash+circumstance;model=rf;weighting=weighted;risk_tier=highest 20%|oe_ratio|ci:2@oe}} |

In the circumstance stage the lowest-risk half of crashes holds {{ml/calibration_by_risk_tier|outcome=fatal;stage=pre_crash+circumstance;model=hgb;weighting=weighted;risk_tier=lowest 50% of predicted risk|share_of_expected_events|pct:1}} (boosting) to
{{ml/calibration_by_risk_tier|outcome=fatal;stage=pre_crash+circumstance;model=logit_main;weighting=weighted;risk_tier=lowest 50% of predicted risk|share_of_expected_events|pct:1}} (main-effects logistic) of the expected deaths, and its observed fatal share is
{{ml/calibration_by_risk_tier|outcome=fatal;stage=pre_crash+circumstance;model=hgb;weighting=weighted;risk_tier=lowest 50% of predicted risk|oe_ratio|.2f}} (boosting) and {{ml/calibration_by_risk_tier|outcome=fatal;stage=pre_crash+circumstance;model=logit_main;weighting=weighted;risk_tier=lowest 50% of predicted risk|oe_ratio|.2f}} (logistic) of the share the
models predict; the highest-risk fifth has observed/expected {{ml/calibration_by_risk_tier|outcome=fatal;stage=pre_crash+circumstance;model=hgb;weighting=weighted;risk_tier=highest 20%|oe_ratio|.2f}} (boosting). The
absolute errors are small (boosting: predicted {{ml/calibration_by_risk_tier|outcome=fatal;stage=pre_crash+circumstance;model=hgb;weighting=weighted;risk_tier=lowest 50% of predicted risk|mean_predicted|pct:2}} vs observed {{ml/calibration_by_risk_tier|outcome=fatal;stage=pre_crash+circumstance;model=hgb;weighting=weighted;risk_tier=lowest 50% of predicted risk|observed_rate|pct:2}} in the lowest half),
but predicted fatal shares for the lowest-risk configurations, and ratios that use them, are
overstated by the factor shown (up to about two-fold or more). The same pattern, slightly weaker, holds for the
main-effects logistic model, which is close to calibrated within these tiers on its own
training years and already shows the pattern in 2022 (an in-sample and validation-year check,
not tabulated); it is therefore mostly a shift between the training and later years rather
than a property of boosting (for boosting, in-sample tiers cannot separate it from
overfitting). KA shows the same direction (lowest half, boosting and logistic,
observed/expected {{ml/calibration_by_risk_tier|outcome=ka;stage=pre_crash+circumstance;model=hgb;weighting=weighted;risk_tier=lowest 50% of predicted risk|oe_ratio|.2f}} and {{ml/calibration_by_risk_tier|outcome=ka;stage=pre_crash+circumstance;model=logit_main;weighting=weighted;risk_tier=lowest 50% of predicted risk|oe_ratio|.2f}} in the circumstance stage).

**KA, weighted** (prevalence {{ml/metrics_test|outcome=ka;stage=pre_crash;model=hgb;domain=all;weighting=weighted;metric=prevalence|estimate|.3f}}): pre-crash AUROC {{ml/metrics_test|outcome=ka;stage=pre_crash;model=logit_main;domain=all;weighting=weighted;metric=auroc|estimate|.3f}} (logit_main), {{ml/metrics_test|outcome=ka;stage=pre_crash;model=logit_interact;domain=all;weighting=weighted;metric=auroc|estimate|.3f}}
(logit_interact), {{ml/metrics_test|outcome=ka;stage=pre_crash;model=hgb;domain=all;weighting=weighted;metric=auroc|estimate|ci:3@ci}} (hgb), {{ml/metrics_test|outcome=ka;stage=pre_crash;model=rf;domain=all;weighting=weighted;metric=auroc|estimate|.3f}} (rf); circumstance stage {{ml/metrics_test|outcome=ka;stage=pre_crash+circumstance;model=logit_main;domain=all;weighting=weighted;metric=auroc|estimate|ci:3@ci}}
(logit_main), {{ml/metrics_test|outcome=ka;stage=pre_crash+circumstance;model=logit_interact;domain=all;weighting=weighted;metric=auroc|estimate|.3f}} (logit_interact), {{ml/metrics_test|outcome=ka;stage=pre_crash+circumstance;model=hgb;domain=all;weighting=weighted;metric=auroc|estimate|ci:3@ci}} (hgb), {{ml/metrics_test|outcome=ka;stage=pre_crash+circumstance;model=rf;domain=all;weighting=weighted;metric=auroc|estimate|.3f}} (rf). Brier skill {{ml/metrics_test|outcome=ka;stage=pre_crash;model=logit_main;domain=all;weighting=weighted;metric=brier_skill|estimate|.3f}} / {{ml/metrics_test|outcome=ka;stage=pre_crash;model=hgb;domain=all;weighting=weighted;metric=brier_skill|estimate|.3f}} (pre-crash,
logit_main / hgb) and {{ml/metrics_test|outcome=ka;stage=pre_crash+circumstance;model=logit_main;domain=all;weighting=weighted;metric=brier_skill|estimate|.3f}} / {{ml/metrics_test|outcome=ka;stage=pre_crash+circumstance;model=hgb;domain=all;weighting=weighted;metric=brier_skill|estimate|.3f}} (circumstance). The KA models' observed/expected in the
test years is {{ml/metrics_test|outcome=ka;stage=pre_crash;model=logit_main~logit_l2~logit_interact~hgb~rf;domain=all;weighting=weighted;metric=oe_ratio|min(estimate)|.2f}}–{{ml/metrics_test|outcome=ka;stage=pre_crash;model=logit_main~logit_l2~logit_interact~hgb~rf;domain=all;weighting=weighted;metric=oe_ratio|max(estimate)|.2f}} (pre-crash) and {{ml/metrics_test|outcome=ka;stage=pre_crash+circumstance;model=logit_main~logit_l2~logit_interact~hgb~rf;domain=all;weighting=weighted;metric=oe_ratio|min(estimate)|.2f}}–{{ml/metrics_test|outcome=ka;stage=pre_crash+circumstance;model=logit_main~logit_l2~logit_interact~hgb~rf;domain=all;weighting=weighted;metric=oe_ratio|max(estimate)|.2f}} (circumstance; hgb circumstance
{{ml/metrics_test|outcome=ka;stage=pre_crash+circumstance;model=hgb;domain=all;weighting=weighted;metric=oe_ratio|estimate|ci:3@ci}}), i.e. below 1 (slight over-prediction), and their calibration slopes are
{{ml/metrics_test|outcome=ka;stage=pre_crash;model=logit_main~logit_l2~logit_interact~hgb;domain=all;weighting=weighted;metric=calibration_slope|min(estimate)|.2f}}–{{ml/metrics_test|outcome=ka;stage=pre_crash+circumstance;model=logit_main~logit_l2~logit_interact~hgb;domain=all;weighting=weighted;metric=calibration_slope|max(estimate)|.2f}} for the logistic and boosted models
(a slope above 1 means predictions slightly too spread), against {{ml/metrics_test|outcome=ka;stage=pre_crash;model=rf;domain=all;weighting=weighted;metric=calibration_slope|estimate|.2f}} and {{ml/metrics_test|outcome=ka;stage=pre_crash+circumstance;model=rf;domain=all;weighting=weighted;metric=calibration_slope|estimate|.2f}} for the random forest.

**Paired differences** (same bootstrap replicates; [`paired_differences`]):

* Boosting vs main-effects logistic, fatal: AUROC {{ml/paired_differences|outcome=fatal;stage=pre_crash;model=hgb;comparison=vs logit_main;metric=auroc|estimate|ci:3@ci}} pre-crash and
  {{ml/paired_differences|outcome=fatal;stage=pre_crash+circumstance;model=hgb;comparison=vs logit_main;metric=auroc|estimate|ci:3@ci}} circumstance; Brier skill {{ml/paired_differences|outcome=fatal;stage=pre_crash;model=hgb;comparison=vs logit_main;metric=brier_skill|estimate|ci:3@ci}} and
  {{ml/paired_differences|outcome=fatal;stage=pre_crash+circumstance;model=hgb;comparison=vs logit_main;metric=brier_skill|estimate|ci:3@ci}}; average precision {{ml/paired_differences|outcome=fatal;stage=pre_crash+circumstance;model=hgb;comparison=vs logit_main;metric=average_precision|estimate|ci:3@ci}} in the circumstance stage.
  KA: AUROC {{ml/paired_differences|outcome=ka;stage=pre_crash;model=hgb;comparison=vs logit_main;metric=auroc|estimate|ci:3@ci}} and {{ml/paired_differences|outcome=ka;stage=pre_crash+circumstance;model=hgb;comparison=vs logit_main;metric=auroc|estimate|ci:3@ci}}.
* The 13 pre-specified interaction terms add little (`logit_interact` vs `logit_main`): fatal AUROC {{ml/paired_differences|outcome=fatal;stage=pre_crash;model=logit_interact;comparison=vs logit_main;metric=auroc|estimate|ci:3@ci}} pre-crash
  and {{ml/paired_differences|outcome=fatal;stage=pre_crash+circumstance;model=logit_interact;comparison=vs logit_main;metric=auroc|estimate|ci:3@ci}} circumstance; Brier skill {{ml/paired_differences|outcome=fatal;stage=pre_crash;model=logit_interact;comparison=vs logit_main;metric=brier_skill|estimate|ci:3@ci}} and {{ml/paired_differences|outcome=fatal;stage=pre_crash+circumstance;model=logit_interact;comparison=vs logit_main;metric=brier_skill|estimate|ci:3@ci}}.
* L2 tuning changes nothing measurable (`logit_l2` vs `logit_main`, fatal AUROC {{ml/paired_differences|outcome=fatal;stage=pre_crash;model=logit_l2;comparison=vs logit_main;metric=auroc|estimate|ci:4@ci}} pre-crash and {{ml/paired_differences|outcome=fatal;stage=pre_crash+circumstance;model=logit_l2;comparison=vs logit_main;metric=auroc|estimate|ci:4@ci}} circumstance).
* The random forest discriminates better than logistic (circumstance AUROC {{ml/paired_differences|outcome=fatal;stage=pre_crash+circumstance;model=rf;comparison=vs logit_main;metric=auroc|estimate|ci:3@ci}}) but its
  Brier skill is lower ({{ml/paired_differences|outcome=fatal;stage=pre_crash+circumstance;model=rf;comparison=vs logit_main;metric=brier_skill|estimate|ci:3@ci}}) because its probabilities are compressed
  towards the mean (calibration slope {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=rf;domain=all;weighting=weighted;metric=calibration_slope|estimate|.1f}}).
* Adding crash configuration raises AUROC by {{ml/paired_differences|outcome=fatal;stage=pre_crash+circumstance;model=hgb;comparison=circumstance stage vs pre_crash;metric=auroc|estimate|ci:3@ci}} (hgb) and {{ml/paired_differences|outcome=fatal;stage=pre_crash+circumstance;model=logit_main;comparison=circumstance stage vs pre_crash;metric=auroc|estimate|ci:3@ci}}
  (logit_main) for fatal and Brier skill by {{ml/paired_differences|outcome=fatal;stage=pre_crash+circumstance;model=hgb;comparison=circumstance stage vs pre_crash;metric=brier_skill|estimate|ci:3@ci}} / {{ml/paired_differences|outcome=fatal;stage=pre_crash+circumstance;model=logit_main;comparison=circumstance stage vs pre_crash;metric=brier_skill|estimate|ci:3@ci}}: crash type is by far the most
  informative recorded circumstance.

### 5.2 By year and subgroup (fatal, circumstance stage, weighted) [`metrics_test`]

| Domain | n (fatal) | hgb AUROC | logit_main AUROC | hgb observed/expected | logit_main observed/expected |
|---|---|---|---|---|---|
| 2023 | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=hgb;domain=year=2023;weighting=weighted;metric=auroc|n|,.0f}} ({{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=hgb;domain=year=2023;weighting=weighted;metric=auroc|n_events|,.0f}}) | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=hgb;domain=year=2023;weighting=weighted;metric=auroc|estimate|ci:3@ci}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=logit_main;domain=year=2023;weighting=weighted;metric=auroc|estimate|ci:3@ci}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=hgb;domain=year=2023;weighting=weighted;metric=oe_ratio|estimate|ci:2@ci}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=logit_main;domain=year=2023;weighting=weighted;metric=oe_ratio|estimate|ci:2@ci}} |
| 2024 | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=hgb;domain=year=2024;weighting=weighted;metric=auroc|n|,.0f}} ({{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=hgb;domain=year=2024;weighting=weighted;metric=auroc|n_events|,.0f}}) | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=hgb;domain=year=2024;weighting=weighted;metric=auroc|estimate|ci:3@ci}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=logit_main;domain=year=2024;weighting=weighted;metric=auroc|estimate|ci:3@ci}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=hgb;domain=year=2024;weighting=weighted;metric=oe_ratio|estimate|ci:2@ci}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=logit_main;domain=year=2024;weighting=weighted;metric=oe_ratio|estimate|ci:2@ci}} |
| Urban (PSU) | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=hgb;domain=urbanicity=urban;weighting=weighted;metric=auroc|n|,.0f}} ({{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=hgb;domain=urbanicity=urban;weighting=weighted;metric=auroc|n_events|,.0f}}) | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=hgb;domain=urbanicity=urban;weighting=weighted;metric=auroc|estimate|ci:3@ci}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=logit_main;domain=urbanicity=urban;weighting=weighted;metric=auroc|estimate|ci:3@ci}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=hgb;domain=urbanicity=urban;weighting=weighted;metric=oe_ratio|estimate|ci:2@ci}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=logit_main;domain=urbanicity=urban;weighting=weighted;metric=oe_ratio|estimate|ci:2@ci}} |
| Rural (PSU) | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=hgb;domain=urbanicity=rural;weighting=weighted;metric=auroc|n|,.0f}} ({{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=hgb;domain=urbanicity=rural;weighting=weighted;metric=auroc|n_events|,.0f}}) | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=hgb;domain=urbanicity=rural;weighting=weighted;metric=auroc|estimate|ci:3@ci}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=logit_main;domain=urbanicity=rural;weighting=weighted;metric=auroc|estimate|ci:3@ci}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=hgb;domain=urbanicity=rural;weighting=weighted;metric=oe_ratio|estimate|ci:2@ci}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=logit_main;domain=urbanicity=rural;weighting=weighted;metric=oe_ratio|estimate|ci:2@ci}} |
| Multi-vehicle | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=hgb;domain=crash_family=multi_vehicle;weighting=weighted;metric=auroc|n|,.0f}} ({{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=hgb;domain=crash_family=multi_vehicle;weighting=weighted;metric=auroc|n_events|,.0f}}) | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=hgb;domain=crash_family=multi_vehicle;weighting=weighted;metric=auroc|estimate|ci:3@ci}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=logit_main;domain=crash_family=multi_vehicle;weighting=weighted;metric=auroc|estimate|ci:3@ci}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=hgb;domain=crash_family=multi_vehicle;weighting=weighted;metric=oe_ratio|estimate|ci:2@ci}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=logit_main;domain=crash_family=multi_vehicle;weighting=weighted;metric=oe_ratio|estimate|ci:2@ci}} |
| Single-vehicle | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=hgb;domain=crash_family=single_vehicle;weighting=weighted;metric=auroc|n|,.0f}} ({{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=hgb;domain=crash_family=single_vehicle;weighting=weighted;metric=auroc|n_events|,.0f}}) | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=hgb;domain=crash_family=single_vehicle;weighting=weighted;metric=auroc|estimate|ci:3@ci}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=logit_main;domain=crash_family=single_vehicle;weighting=weighted;metric=auroc|estimate|ci:3@ci}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=hgb;domain=crash_family=single_vehicle;weighting=weighted;metric=oe_ratio|estimate|ci:2@ci}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=logit_main;domain=crash_family=single_vehicle;weighting=weighted;metric=oe_ratio|estimate|ci:2@ci}} |
| Pedestrian / cyclist | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=hgb;domain=crash_family=pedestrian_cyclist;weighting=weighted;metric=auroc|n|,.0f}} ({{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=hgb;domain=crash_family=pedestrian_cyclist;weighting=weighted;metric=auroc|n_events|,.0f}}) | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=hgb;domain=crash_family=pedestrian_cyclist;weighting=weighted;metric=auroc|estimate|ci:3@ci}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=logit_main;domain=crash_family=pedestrian_cyclist;weighting=weighted;metric=auroc|estimate|ci:3@ci}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=hgb;domain=crash_family=pedestrian_cyclist;weighting=weighted;metric=oe_ratio|estimate|ci:2@ci}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=logit_main;domain=crash_family=pedestrian_cyclist;weighting=weighted;metric=oe_ratio|estimate|ci:2@ci}} |
| Motorcycle involved | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=hgb;domain=motorcycle=yes;weighting=weighted;metric=auroc|n|,.0f}} ({{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=hgb;domain=motorcycle=yes;weighting=weighted;metric=auroc|n_events|,.0f}}) | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=hgb;domain=motorcycle=yes;weighting=weighted;metric=auroc|estimate|ci:3@ci}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=logit_main;domain=motorcycle=yes;weighting=weighted;metric=auroc|estimate|ci:3@ci}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=hgb;domain=motorcycle=yes;weighting=weighted;metric=oe_ratio|estimate|ci:2@ci}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=logit_main;domain=motorcycle=yes;weighting=weighted;metric=oe_ratio|estimate|ci:2@ci}} |
| No motorcycle | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=hgb;domain=motorcycle=no;weighting=weighted;metric=auroc|n|,.0f}} ({{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=hgb;domain=motorcycle=no;weighting=weighted;metric=auroc|n_events|,.0f}}) | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=hgb;domain=motorcycle=no;weighting=weighted;metric=auroc|estimate|ci:3@ci}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=logit_main;domain=motorcycle=no;weighting=weighted;metric=auroc|estimate|ci:3@ci}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=hgb;domain=motorcycle=no;weighting=weighted;metric=oe_ratio|estimate|ci:2@ci}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=logit_main;domain=motorcycle=no;weighting=weighted;metric=oe_ratio|estimate|ci:2@ci}} |
| Not hit-and-run | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=hgb;domain=hit_and_run=no;weighting=weighted;metric=auroc|n|,.0f}} ({{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=hgb;domain=hit_and_run=no;weighting=weighted;metric=auroc|n_events|,.0f}}) | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=hgb;domain=hit_and_run=no;weighting=weighted;metric=auroc|estimate|ci:3@ci}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=logit_main;domain=hit_and_run=no;weighting=weighted;metric=auroc|estimate|ci:3@ci}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=hgb;domain=hit_and_run=no;weighting=weighted;metric=oe_ratio|estimate|ci:2@ci}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=logit_main;domain=hit_and_run=no;weighting=weighted;metric=oe_ratio|estimate|ci:2@ci}} |
| Hit-and-run | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=hgb;domain=hit_and_run=yes;weighting=weighted;metric=auroc|n|,.0f}} ({{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=hgb;domain=hit_and_run=yes;weighting=weighted;metric=auroc|n_events|,.0f}}) | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=hgb;domain=hit_and_run=yes;weighting=weighted;metric=auroc|estimate|ci:3@ci}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=logit_main;domain=hit_and_run=yes;weighting=weighted;metric=auroc|estimate|ci:3@ci}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=hgb;domain=hit_and_run=yes;weighting=weighted;metric=oe_ratio|estimate|ci:2@ci}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=logit_main;domain=hit_and_run=yes;weighting=weighted;metric=oe_ratio|estimate|ci:2@ci}} |

Performance is stable across the two test years. Fatal shares among motorcycle and
pedestrian/cyclist crashes in 2023–2024 were higher than the models (trained on 2016–2021)
predict: observed/expected {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=logit_main~hgb;domain=crash_family=pedestrian_cyclist~motorcycle=yes;weighting=weighted;metric=oe_ratio|min(estimate)|.2f}}–{{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=logit_main~hgb;domain=crash_family=pedestrian_cyclist~motorcycle=yes;weighting=weighted;metric=oe_ratio|max(estimate)|.2f}} for the logistic and boosted models
(more for the random forest, {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=rf;domain=crash_family=pedestrian_cyclist;weighting=weighted;metric=oe_ratio|estimate|.2f}} for pedestrians and cyclists), and hit-and-run crashes were *less* often fatal
than predicted (observed/expected {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=hgb;domain=hit_and_run=yes;weighting=weighted;metric=oe_ratio|estimate|.2f}} for boosting; hit-and-run status is not an input; the models see it only through the proxy unknowns of §2). Within crash families, discrimination is weaker than
overall because much of the overall AUROC comes from separating families (pedestrian vs
rear-end). In the pre-crash stage the subgroup calibration by crash family is necessarily
poor (pedestrian/cyclist observed/expected {{ml/metrics_test|outcome=fatal;stage=pre_crash;model=hgb;domain=crash_family=pedestrian_cyclist;weighting=weighted;metric=oe_ratio|estimate|.1f}} for boosting): those models do not know the crash type.

### 5.3 Risk thresholds (fatal; thresholds fixed on 2022 predictions) [`thresholds`]

Counts are unweighted test records (2023–2024); "per year" values are estimated
police-reported crashes per year; ratios are weighted with bootstrap CIs.

{{mdtable:ml/thresholds|outcome=fatal;stage=pre_crash+circumstance;model=hgb~logit_main|model:Model (circumstance stage):;threshold_rule:Rule (2022 threshold):;threshold:Threshold:.3f;flagged_share:Flagged:pct:1;sensitivity:Sensitivity:ci:2;ppv:PPV:ci:3;n_tp:TP (records):,.0f;n_fp:FP (records):,.0f;n_fn:FN (records):,.0f;est_fp_per_year:FP per year (est.):,.0f;est_fn_per_year:FN per year (est.):,.0f}}

Even the best model flags many non-fatal crashes for every fatal one: at the 1% threshold the
weighted PPV of boosting (circumstance stage) is {{ml/thresholds|outcome=fatal;stage=pre_crash+circumstance;model=hgb;threshold_rule=top 1% of 2022 crashes (weighted)|ppv|pct:1}}, i.e. about
{{ml/thresholds|outcome=fatal;stage=pre_crash+circumstance;model=hgb;threshold_rule=top 1% of 2022 crashes (weighted)|ppv|oneinN}} flagged crashes is fatal, and at the 5% threshold {{ml/thresholds|outcome=fatal;stage=pre_crash+circumstance;model=hgb;threshold_rule=top 5% of 2022 crashes (weighted)|ppv|oneinN}}; this is a property of a
low-prevalence outcome ({{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=hgb;domain=all;weighting=weighted;metric=prevalence|estimate|pct:2}} of crashes), not a defect. The thresholds carry over from 2022 closely
(the top-1% rule flags {{ml/thresholds|outcome=fatal;stage=pre_crash+circumstance;model=hgb;threshold_rule=top 1% of 2022 crashes (weighted)|flagged_share|pct:1}} of test crashes, the top-5% rule
{{ml/thresholds|outcome=fatal;stage=pre_crash+circumstance;model=hgb;threshold_rule=top 5% of 2022 crashes (weighted)|flagged_share|pct:1}}). These are descriptive operating points, not recommended decision rules.

## 6. Temporal stability and feature-set sensitivity

**Trained on 2016–2019, evaluated on each later year** [`temporal_stability`,
`figures/ml/temporal_stability_*.png`]. Fatal, circumstance stage; boosting (hgb) and, for
comparison, the main-effects logistic model:

| Evaluation year | hgb AUROC | hgb observed/expected | hgb calibration slope | logit_main AUROC | logit_main observed/expected |
|---|---|---|---|---|---|
| 2020 | {{ml/temporal_stability|outcome=fatal;stage=pre_crash+circumstance;model=hgb;eval_year=2020;metric=auroc|estimate|ci:3@ci}} | {{ml/temporal_stability|outcome=fatal;stage=pre_crash+circumstance;model=hgb;eval_year=2020;metric=oe_ratio|estimate|ci:2@ci}} | {{ml/temporal_stability|outcome=fatal;stage=pre_crash+circumstance;model=hgb;eval_year=2020;metric=calibration_slope|estimate|ci:2@ci}} | {{ml/temporal_stability|outcome=fatal;stage=pre_crash+circumstance;model=logit_main;eval_year=2020;metric=auroc|estimate|.3f}} | {{ml/temporal_stability|outcome=fatal;stage=pre_crash+circumstance;model=logit_main;eval_year=2020;metric=oe_ratio|estimate|.2f}} |
| 2021 | {{ml/temporal_stability|outcome=fatal;stage=pre_crash+circumstance;model=hgb;eval_year=2021;metric=auroc|estimate|ci:3@ci}} | {{ml/temporal_stability|outcome=fatal;stage=pre_crash+circumstance;model=hgb;eval_year=2021;metric=oe_ratio|estimate|ci:2@ci}} | {{ml/temporal_stability|outcome=fatal;stage=pre_crash+circumstance;model=hgb;eval_year=2021;metric=calibration_slope|estimate|ci:2@ci}} | {{ml/temporal_stability|outcome=fatal;stage=pre_crash+circumstance;model=logit_main;eval_year=2021;metric=auroc|estimate|.3f}} | {{ml/temporal_stability|outcome=fatal;stage=pre_crash+circumstance;model=logit_main;eval_year=2021;metric=oe_ratio|estimate|.2f}} |
| 2022 | {{ml/temporal_stability|outcome=fatal;stage=pre_crash+circumstance;model=hgb;eval_year=2022;metric=auroc|estimate|ci:3@ci}} | {{ml/temporal_stability|outcome=fatal;stage=pre_crash+circumstance;model=hgb;eval_year=2022;metric=oe_ratio|estimate|ci:2@ci}} | {{ml/temporal_stability|outcome=fatal;stage=pre_crash+circumstance;model=hgb;eval_year=2022;metric=calibration_slope|estimate|ci:2@ci}} | {{ml/temporal_stability|outcome=fatal;stage=pre_crash+circumstance;model=logit_main;eval_year=2022;metric=auroc|estimate|.3f}} | {{ml/temporal_stability|outcome=fatal;stage=pre_crash+circumstance;model=logit_main;eval_year=2022;metric=oe_ratio|estimate|.2f}} |
| 2023 | {{ml/temporal_stability|outcome=fatal;stage=pre_crash+circumstance;model=hgb;eval_year=2023;metric=auroc|estimate|ci:3@ci}} | {{ml/temporal_stability|outcome=fatal;stage=pre_crash+circumstance;model=hgb;eval_year=2023;metric=oe_ratio|estimate|ci:2@ci}} | {{ml/temporal_stability|outcome=fatal;stage=pre_crash+circumstance;model=hgb;eval_year=2023;metric=calibration_slope|estimate|ci:2@ci}} | {{ml/temporal_stability|outcome=fatal;stage=pre_crash+circumstance;model=logit_main;eval_year=2023;metric=auroc|estimate|.3f}} | {{ml/temporal_stability|outcome=fatal;stage=pre_crash+circumstance;model=logit_main;eval_year=2023;metric=oe_ratio|estimate|.2f}} |
| 2024 | {{ml/temporal_stability|outcome=fatal;stage=pre_crash+circumstance;model=hgb;eval_year=2024;metric=auroc|estimate|ci:3@ci}} | {{ml/temporal_stability|outcome=fatal;stage=pre_crash+circumstance;model=hgb;eval_year=2024;metric=oe_ratio|estimate|ci:2@ci}} | {{ml/temporal_stability|outcome=fatal;stage=pre_crash+circumstance;model=hgb;eval_year=2024;metric=calibration_slope|estimate|ci:2@ci}} | {{ml/temporal_stability|outcome=fatal;stage=pre_crash+circumstance;model=logit_main;eval_year=2024;metric=auroc|estimate|.3f}} | {{ml/temporal_stability|outcome=fatal;stage=pre_crash+circumstance;model=logit_main;eval_year=2024;metric=oe_ratio|estimate|.2f}} |

Models trained before 2020 under-predict the higher fatal share
of police-reported crashes after 2020 (RQ5): observed/expected is above 1 in every later year
(boosting {{ml/temporal_stability|outcome=fatal;stage=pre_crash+circumstance;model=hgb;eval_year=2020~2021~2022~2023~2024;metric=oe_ratio|min(estimate)|.2f}}–{{ml/temporal_stability|outcome=fatal;stage=pre_crash+circumstance;model=hgb;eval_year=2020~2021~2022~2023~2024;metric=oe_ratio|max(estimate)|.2f}}). The 2020 calibration slope
({{ml/temporal_stability|outcome=fatal;stage=pre_crash+circumstance;model=hgb;eval_year=2020;metric=calibration_slope|estimate|ci:2@ci}}) and AUROC dip coincide with the pandemic change in traffic. KA models show
the reverse drift (observed/expected {{ml/temporal_stability|outcome=ka;stage=pre_crash+circumstance;model=hgb~logit_main;eval_year=2021~2022~2023~2024;metric=oe_ratio|min(estimate)|.2f}}–{{ml/temporal_stability|outcome=ka;stage=pre_crash+circumstance;model=hgb~logit_main;eval_year=2021~2022~2023~2024;metric=oe_ratio|max(estimate)|.2f}} from 2021). These refits reuse the boosting
hyper-parameters tuned on 2022 (number of trees re-chosen by early stopping within 2016–2019),
so the 2020–2022 evaluations borrow a small amount of information from 2022 through the
hyper-parameter choice (not through any fitted value). Ranking is stable; the level drifts
(fatal observed/expected up to {{ml/temporal_stability|outcome=fatal;stage=pre_crash+circumstance;model=hgb~logit_main;eval_year=2020~2021~2022~2023~2024;metric=oe_ratio|max(estimate)|.2f}}), so absolute probabilities should be read with year-specific
calibration in mind. Models trained on 2016–2021 under-predicted 2022 by a similar margin
(validation observed/expected {{ml/tuning|outcome=fatal;chosen=True|min(valid_oe_w)|.2f}}–{{ml/tuning|outcome=fatal;chosen=True|max(valid_oe_w)|.2f}} for fatal, all models and both stages, from the 2022 tuning rows) and were closer in 2023–2024
(test observed/expected {{ml/metrics_test|outcome=fatal;model=logit_main~hgb;domain=all;weighting=weighted;metric=oe_ratio|min(estimate)|.2f}}–{{ml/metrics_test|outcome=fatal;model=logit_main~hgb;domain=all;weighting=weighted;metric=oe_ratio|max(estimate)|.2f}}, boosting and logistic, both stages).

**Alternative feature sets** (fatal, circumstance stage, refitted on 2016–2021, evaluated on
2023–2024) [`feature_sensitivity`]:

| Variant | Model | AUROC | Average precision | Brier skill | Observed / expected | Δ AUROC vs main (paired 95% CI) | Δ Brier skill vs main (paired 95% CI) |
|---|---|---|---|---|---|---|---|
| Main feature set | hgb | {{ml/feature_sensitivity|outcome=fatal;stage=pre_crash+circumstance;variant=main feature set;model=hgb;metric=auroc|estimate|ci:3@ci}} | {{ml/feature_sensitivity|outcome=fatal;stage=pre_crash+circumstance;variant=main feature set;model=hgb;metric=average_precision|estimate|.3f}} | {{ml/feature_sensitivity|outcome=fatal;stage=pre_crash+circumstance;variant=main feature set;model=hgb;metric=brier_skill|estimate|.3f}} | {{ml/feature_sensitivity|outcome=fatal;stage=pre_crash+circumstance;variant=main feature set;model=hgb;metric=oe_ratio|estimate|ci:2@ci}} | — | — |
|  | logit_main | {{ml/feature_sensitivity|outcome=fatal;stage=pre_crash+circumstance;variant=main feature set;model=logit_main;metric=auroc|estimate|ci:3@ci}} | {{ml/feature_sensitivity|outcome=fatal;stage=pre_crash+circumstance;variant=main feature set;model=logit_main;metric=average_precision|estimate|.3f}} | {{ml/feature_sensitivity|outcome=fatal;stage=pre_crash+circumstance;variant=main feature set;model=logit_main;metric=brier_skill|estimate|.3f}} | {{ml/feature_sensitivity|outcome=fatal;stage=pre_crash+circumstance;variant=main feature set;model=logit_main;metric=oe_ratio|estimate|ci:2@ci}} | — | — |
| Without speeding and imputed alcohol | hgb | {{ml/feature_sensitivity|outcome=fatal;stage=pre_crash+circumstance;variant=without speeding and alcohol_im;model=hgb;metric=auroc|estimate|ci:3@ci}} | {{ml/feature_sensitivity|outcome=fatal;stage=pre_crash+circumstance;variant=without speeding and alcohol_im;model=hgb;metric=average_precision|estimate|.3f}} | {{ml/feature_sensitivity|outcome=fatal;stage=pre_crash+circumstance;variant=without speeding and alcohol_im;model=hgb;metric=brier_skill|estimate|.3f}} | {{ml/feature_sensitivity|outcome=fatal;stage=pre_crash+circumstance;variant=without speeding and alcohol_im;model=hgb;metric=oe_ratio|estimate|ci:2@ci}} | {{ml/feature_sensitivity|outcome=fatal;stage=pre_crash+circumstance;variant=without speeding and alcohol_im;model=hgb;metric=auroc|diff_vs_main|ci:3@diff_ci}} | {{ml/feature_sensitivity|outcome=fatal;stage=pre_crash+circumstance;variant=without speeding and alcohol_im;model=hgb;metric=brier_skill|diff_vs_main|ci:3@diff_ci}} |
|  | logit_main | {{ml/feature_sensitivity|outcome=fatal;stage=pre_crash+circumstance;variant=without speeding and alcohol_im;model=logit_main;metric=auroc|estimate|ci:3@ci}} | {{ml/feature_sensitivity|outcome=fatal;stage=pre_crash+circumstance;variant=without speeding and alcohol_im;model=logit_main;metric=average_precision|estimate|.3f}} | {{ml/feature_sensitivity|outcome=fatal;stage=pre_crash+circumstance;variant=without speeding and alcohol_im;model=logit_main;metric=brier_skill|estimate|.3f}} | {{ml/feature_sensitivity|outcome=fatal;stage=pre_crash+circumstance;variant=without speeding and alcohol_im;model=logit_main;metric=oe_ratio|estimate|ci:2@ci}} | {{ml/feature_sensitivity|outcome=fatal;stage=pre_crash+circumstance;variant=without speeding and alcohol_im;model=logit_main;metric=auroc|diff_vs_main|ci:3@diff_ci}} | {{ml/feature_sensitivity|outcome=fatal;stage=pre_crash+circumstance;variant=without speeding and alcohol_im;model=logit_main;metric=brier_skill|diff_vs_main|ci:3@diff_ci}} |
| Plus police-reported drugs and distraction | hgb | {{ml/feature_sensitivity|outcome=fatal;stage=pre_crash+circumstance;variant=plus drugs and distracted (police-reported);model=hgb;metric=auroc|estimate|ci:3@ci}} | {{ml/feature_sensitivity|outcome=fatal;stage=pre_crash+circumstance;variant=plus drugs and distracted (police-reported);model=hgb;metric=average_precision|estimate|.3f}} | {{ml/feature_sensitivity|outcome=fatal;stage=pre_crash+circumstance;variant=plus drugs and distracted (police-reported);model=hgb;metric=brier_skill|estimate|.3f}} | {{ml/feature_sensitivity|outcome=fatal;stage=pre_crash+circumstance;variant=plus drugs and distracted (police-reported);model=hgb;metric=oe_ratio|estimate|ci:2@ci}} | {{ml/feature_sensitivity|outcome=fatal;stage=pre_crash+circumstance;variant=plus drugs and distracted (police-reported);model=hgb;metric=auroc|diff_vs_main|ci:3@diff_ci}} | {{ml/feature_sensitivity|outcome=fatal;stage=pre_crash+circumstance;variant=plus drugs and distracted (police-reported);model=hgb;metric=brier_skill|diff_vs_main|ci:3@diff_ci}} |
|  | logit_main | {{ml/feature_sensitivity|outcome=fatal;stage=pre_crash+circumstance;variant=plus drugs and distracted (police-reported);model=logit_main;metric=auroc|estimate|ci:3@ci}} | {{ml/feature_sensitivity|outcome=fatal;stage=pre_crash+circumstance;variant=plus drugs and distracted (police-reported);model=logit_main;metric=average_precision|estimate|.3f}} | {{ml/feature_sensitivity|outcome=fatal;stage=pre_crash+circumstance;variant=plus drugs and distracted (police-reported);model=logit_main;metric=brier_skill|estimate|.3f}} | {{ml/feature_sensitivity|outcome=fatal;stage=pre_crash+circumstance;variant=plus drugs and distracted (police-reported);model=logit_main;metric=oe_ratio|estimate|ci:2@ci}} | {{ml/feature_sensitivity|outcome=fatal;stage=pre_crash+circumstance;variant=plus drugs and distracted (police-reported);model=logit_main;metric=auroc|diff_vs_main|ci:3@diff_ci}} | {{ml/feature_sensitivity|outcome=fatal;stage=pre_crash+circumstance;variant=plus drugs and distracted (police-reported);model=logit_main;metric=brier_skill|diff_vs_main|ci:3@diff_ci}} |
| Police-reported instead of imputed alcohol | hgb | {{ml/feature_sensitivity|outcome=fatal;stage=pre_crash+circumstance;variant=police-reported alcohol instead of alcohol_im;model=hgb;metric=auroc|estimate|ci:3@ci}} | {{ml/feature_sensitivity|outcome=fatal;stage=pre_crash+circumstance;variant=police-reported alcohol instead of alcohol_im;model=hgb;metric=average_precision|estimate|.3f}} | {{ml/feature_sensitivity|outcome=fatal;stage=pre_crash+circumstance;variant=police-reported alcohol instead of alcohol_im;model=hgb;metric=brier_skill|estimate|.3f}} | {{ml/feature_sensitivity|outcome=fatal;stage=pre_crash+circumstance;variant=police-reported alcohol instead of alcohol_im;model=hgb;metric=oe_ratio|estimate|ci:2@ci}} | {{ml/feature_sensitivity|outcome=fatal;stage=pre_crash+circumstance;variant=police-reported alcohol instead of alcohol_im;model=hgb;metric=auroc|diff_vs_main|ci:3@diff_ci}} | {{ml/feature_sensitivity|outcome=fatal;stage=pre_crash+circumstance;variant=police-reported alcohol instead of alcohol_im;model=hgb;metric=brier_skill|diff_vs_main|ci:3@diff_ci}} |
|  | logit_main | {{ml/feature_sensitivity|outcome=fatal;stage=pre_crash+circumstance;variant=police-reported alcohol instead of alcohol_im;model=logit_main;metric=auroc|estimate|ci:3@ci}} | {{ml/feature_sensitivity|outcome=fatal;stage=pre_crash+circumstance;variant=police-reported alcohol instead of alcohol_im;model=logit_main;metric=average_precision|estimate|.3f}} | {{ml/feature_sensitivity|outcome=fatal;stage=pre_crash+circumstance;variant=police-reported alcohol instead of alcohol_im;model=logit_main;metric=brier_skill|estimate|.3f}} | {{ml/feature_sensitivity|outcome=fatal;stage=pre_crash+circumstance;variant=police-reported alcohol instead of alcohol_im;model=logit_main;metric=oe_ratio|estimate|ci:2@ci}} | {{ml/feature_sensitivity|outcome=fatal;stage=pre_crash+circumstance;variant=police-reported alcohol instead of alcohol_im;model=logit_main;metric=auroc|diff_vs_main|ci:3@diff_ci}} | {{ml/feature_sensitivity|outcome=fatal;stage=pre_crash+circumstance;variant=police-reported alcohol instead of alcohol_im;model=logit_main;metric=brier_skill|diff_vs_main|ci:3@diff_ci}} |
| Proxy-blind (unknown time of day, motorcycle, heavy vehicle, speeding and missing vehicle age imputed) | hgb | {{ml/feature_sensitivity|outcome=fatal;stage=pre_crash+circumstance;variant=proxy-blind: hit-and-run-dominated unknowns imputed;model=hgb;metric=auroc|estimate|ci:3@ci}} | {{ml/feature_sensitivity|outcome=fatal;stage=pre_crash+circumstance;variant=proxy-blind: hit-and-run-dominated unknowns imputed;model=hgb;metric=average_precision|estimate|.3f}} | {{ml/feature_sensitivity|outcome=fatal;stage=pre_crash+circumstance;variant=proxy-blind: hit-and-run-dominated unknowns imputed;model=hgb;metric=brier_skill|estimate|.3f}} | {{ml/feature_sensitivity|outcome=fatal;stage=pre_crash+circumstance;variant=proxy-blind: hit-and-run-dominated unknowns imputed;model=hgb;metric=oe_ratio|estimate|ci:2@ci}} | {{ml/feature_sensitivity|outcome=fatal;stage=pre_crash+circumstance;variant=proxy-blind: hit-and-run-dominated unknowns imputed;model=hgb;metric=auroc|diff_vs_main|ci:3@diff_ci}} | {{ml/feature_sensitivity|outcome=fatal;stage=pre_crash+circumstance;variant=proxy-blind: hit-and-run-dominated unknowns imputed;model=hgb;metric=brier_skill|diff_vs_main|ci:3@diff_ci}} |
|  | logit_main | {{ml/feature_sensitivity|outcome=fatal;stage=pre_crash+circumstance;variant=proxy-blind: hit-and-run-dominated unknowns imputed;model=logit_main;metric=auroc|estimate|ci:3@ci}} | {{ml/feature_sensitivity|outcome=fatal;stage=pre_crash+circumstance;variant=proxy-blind: hit-and-run-dominated unknowns imputed;model=logit_main;metric=average_precision|estimate|.3f}} | {{ml/feature_sensitivity|outcome=fatal;stage=pre_crash+circumstance;variant=proxy-blind: hit-and-run-dominated unknowns imputed;model=logit_main;metric=brier_skill|estimate|.3f}} | {{ml/feature_sensitivity|outcome=fatal;stage=pre_crash+circumstance;variant=proxy-blind: hit-and-run-dominated unknowns imputed;model=logit_main;metric=oe_ratio|estimate|ci:2@ci}} | {{ml/feature_sensitivity|outcome=fatal;stage=pre_crash+circumstance;variant=proxy-blind: hit-and-run-dominated unknowns imputed;model=logit_main;metric=auroc|diff_vs_main|ci:3@diff_ci}} | {{ml/feature_sensitivity|outcome=fatal;stage=pre_crash+circumstance;variant=proxy-blind: hit-and-run-dominated unknowns imputed;model=logit_main;metric=brier_skill|diff_vs_main|ci:3@diff_ci}} |

* Dropping police-reported speeding and imputed alcohol changes AUROC by {{ml/feature_sensitivity|outcome=fatal;stage=pre_crash+circumstance;variant=without speeding and alcohol_im;model=logit_main;metric=auroc|diff_vs_main|+.3f}} (logistic) and
  {{ml/feature_sensitivity|outcome=fatal;stage=pre_crash+circumstance;variant=without speeding and alcohol_im;model=hgb;metric=auroc|diff_vs_main|+.3f}} (boosting): they carry
  information beyond crash configuration, but severity-dependent ascertainment means part of
  it may reflect more thorough recording in severe crashes (`docs/limitations.md` §2).
* Adding police-reported drug and distraction fields changes discrimination by
  {{ml/feature_sensitivity|outcome=fatal;stage=pre_crash+circumstance;variant=plus drugs and distracted (police-reported);model=hgb;metric=auroc|diff_vs_main|+.3f}} (boosting) and {{ml/feature_sensitivity|outcome=fatal;stage=pre_crash+circumstance;variant=plus drugs and distracted (police-reported);model=logit_main;metric=auroc|diff_vs_main|+.3f}} (logistic) AUROC; using police-reported instead of imputed alcohol changes it by
  {{ml/feature_sensitivity|outcome=fatal;stage=pre_crash+circumstance;variant=police-reported alcohol instead of alcohol_im;model=hgb;metric=auroc|diff_vs_main|+.3f}} and {{ml/feature_sensitivity|outcome=fatal;stage=pre_crash+circumstance;variant=police-reported alcohol instead of alcohol_im;model=logit_main;metric=auroc|diff_vs_main|+.3f}}. The first two variants break calibration in the test years
  (observed/expected {{ml/feature_sensitivity|outcome=fatal;stage=pre_crash+circumstance;variant=plus drugs and distracted (police-reported);model=hgb;metric=oe_ratio|estimate|.2f}} and {{ml/feature_sensitivity|outcome=fatal;stage=pre_crash+circumstance;variant=plus drugs and distracted (police-reported);model=logit_main;metric=oe_ratio|estimate|.2f}} with drugs and distraction; {{ml/feature_sensitivity|outcome=fatal;stage=pre_crash+circumstance;variant=police-reported alcohol instead of alcohol_im;model=hgb;metric=oe_ratio|estimate|.2f}} and {{ml/feature_sensitivity|outcome=fatal;stage=pre_crash+circumstance;variant=police-reported alcohol instead of alcohol_im;model=logit_main;metric=oe_ratio|estimate|.2f}} with police-reported alcohol): these fields have coding breaks (2017–2020) and severity-dependent unknown
  rates, which is why they are not model inputs.
* The proxy-blind refit, in which unknowns that mostly mark hit-and-run crashes carry no
  information, changes AUROC by {{ml/feature_sensitivity|outcome=fatal;stage=pre_crash+circumstance;variant=proxy-blind: hit-and-run-dominated unknowns imputed;model=hgb;metric=auroc|diff_vs_main|ci:3@diff_ci}} (boosting) and
  {{ml/feature_sensitivity|outcome=fatal;stage=pre_crash+circumstance;variant=proxy-blind: hit-and-run-dominated unknowns imputed;model=logit_main;metric=auroc|diff_vs_main|ci:3@diff_ci}} (logistic) and Brier skill by {{ml/feature_sensitivity|outcome=fatal;stage=pre_crash+circumstance;variant=proxy-blind: hit-and-run-dominated unknowns imputed;model=hgb;metric=brier_skill|diff_vs_main|ci:3@diff_ci}} (boosting): the hit-and-run proxy contributes a small, measurable part of the
  boosted model's probability accuracy and little to ranking. The comparison with the
  main models therefore changes no conclusion of this report.

## 7. Interpretation (model-predicted; not causal)

**Permutation importance** (weighted: the permuted input is replaced by draws from its
weighted test distribution; increase in weighted log loss as a percentage of the baseline, {{ml/permutation_importance|outcome=fatal;stage=pre_crash+circumstance;model=hgb;feature=crash_type|n_repeats|.0f}} repeats) [`permutation_importance`,
`figures/ml/permutation_importance_fatal.png`]. Fatal; inputs in the order of the boosted circumstance-stage ranking at
the time of writing (the table, not the order, is authoritative). Crash type is moved together
with the vehicle count, and speed limit as band and mph together; the vehicle count is drawn
within crash type, so it is the count's value *given* crash type and no impossible crash is created:

| Input | Circumstance stage, hgb | Circumstance stage, logit_main | Pre-crash stage, hgb | Pre-crash stage, logit_main |
|---|---|---|---|---|
| `crash_type` | {{ml/permutation_importance|outcome=fatal;stage=pre_crash+circumstance;model=hgb;feature=crash_type|log_loss_increase_pct|.1f}}% | {{ml/permutation_importance|outcome=fatal;stage=pre_crash+circumstance;model=logit_main;feature=crash_type|log_loss_increase_pct|.1f}}% | — | — |
| `speed_limit` | {{ml/permutation_importance|outcome=fatal;stage=pre_crash+circumstance;model=hgb;feature=speed_limit|log_loss_increase_pct|.1f}}% | {{ml/permutation_importance|outcome=fatal;stage=pre_crash+circumstance;model=logit_main;feature=speed_limit|log_loss_increase_pct|.1f}}% | {{ml/permutation_importance|outcome=fatal;stage=pre_crash;model=hgb;feature=speed_limit|log_loss_increase_pct|.1f}}% | {{ml/permutation_importance|outcome=fatal;stage=pre_crash;model=logit_main;feature=speed_limit|log_loss_increase_pct|.1f}}% |
| `any_motorcycle` | {{ml/permutation_importance|outcome=fatal;stage=pre_crash+circumstance;model=hgb;feature=any_motorcycle|log_loss_increase_pct|.1f}}% | {{ml/permutation_importance|outcome=fatal;stage=pre_crash+circumstance;model=logit_main;feature=any_motorcycle|log_loss_increase_pct|.1f}}% | {{ml/permutation_importance|outcome=fatal;stage=pre_crash;model=hgb;feature=any_motorcycle|log_loss_increase_pct|.1f}}% | {{ml/permutation_importance|outcome=fatal;stage=pre_crash;model=logit_main;feature=any_motorcycle|log_loss_increase_pct|.1f}}% |
| `junction` | {{ml/permutation_importance|outcome=fatal;stage=pre_crash+circumstance;model=hgb;feature=junction|log_loss_increase_pct|.1f}}% | {{ml/permutation_importance|outcome=fatal;stage=pre_crash+circumstance;model=logit_main;feature=junction|log_loss_increase_pct|.1f}}% | {{ml/permutation_importance|outcome=fatal;stage=pre_crash;model=hgb;feature=junction|log_loss_increase_pct|.1f}}% | {{ml/permutation_importance|outcome=fatal;stage=pre_crash;model=logit_main;feature=junction|log_loss_increase_pct|.1f}}% |
| `alcohol_im` | {{ml/permutation_importance|outcome=fatal;stage=pre_crash+circumstance;model=hgb;feature=alcohol_im|log_loss_increase_pct|.1f}}% | {{ml/permutation_importance|outcome=fatal;stage=pre_crash+circumstance;model=logit_main;feature=alcohol_im|log_loss_increase_pct|.1f}}% | {{ml/permutation_importance|outcome=fatal;stage=pre_crash;model=hgb;feature=alcohol_im|log_loss_increase_pct|.1f}}% | {{ml/permutation_importance|outcome=fatal;stage=pre_crash;model=logit_main;feature=alcohol_im|log_loss_increase_pct|.1f}}% |
| `speeding` | {{ml/permutation_importance|outcome=fatal;stage=pre_crash+circumstance;model=hgb;feature=speeding|log_loss_increase_pct|.1f}}% | {{ml/permutation_importance|outcome=fatal;stage=pre_crash+circumstance;model=logit_main;feature=speeding|log_loss_increase_pct|.1f}}% | {{ml/permutation_importance|outcome=fatal;stage=pre_crash;model=hgb;feature=speeding|log_loss_increase_pct|.1f}}% | {{ml/permutation_importance|outcome=fatal;stage=pre_crash;model=logit_main;feature=speeding|log_loss_increase_pct|.1f}}% |
| `light` | {{ml/permutation_importance|outcome=fatal;stage=pre_crash+circumstance;model=hgb;feature=light|log_loss_increase_pct|.1f}}% | {{ml/permutation_importance|outcome=fatal;stage=pre_crash+circumstance;model=logit_main;feature=light|log_loss_increase_pct|.1f}}% | {{ml/permutation_importance|outcome=fatal;stage=pre_crash;model=hgb;feature=light|log_loss_increase_pct|.1f}}% | {{ml/permutation_importance|outcome=fatal;stage=pre_crash;model=logit_main;feature=light|log_loss_increase_pct|.1f}}% |
| `any_heavy_truck` | {{ml/permutation_importance|outcome=fatal;stage=pre_crash+circumstance;model=hgb;feature=any_heavy_truck|log_loss_increase_pct|.1f}}% | {{ml/permutation_importance|outcome=fatal;stage=pre_crash+circumstance;model=logit_main;feature=any_heavy_truck|log_loss_increase_pct|.1f}}% | {{ml/permutation_importance|outcome=fatal;stage=pre_crash;model=hgb;feature=any_heavy_truck|log_loss_increase_pct|.1f}}% | {{ml/permutation_importance|outcome=fatal;stage=pre_crash;model=logit_main;feature=any_heavy_truck|log_loss_increase_pct|.1f}}% |
| `tod` | {{ml/permutation_importance|outcome=fatal;stage=pre_crash+circumstance;model=hgb;feature=tod|log_loss_increase_pct|.1f}}% | {{ml/permutation_importance|outcome=fatal;stage=pre_crash+circumstance;model=logit_main;feature=tod|log_loss_increase_pct|.1f}}% | {{ml/permutation_importance|outcome=fatal;stage=pre_crash;model=hgb;feature=tod|log_loss_increase_pct|.1f}}% | {{ml/permutation_importance|outcome=fatal;stage=pre_crash;model=logit_main;feature=tod|log_loss_increase_pct|.1f}}% |
| `region` | {{ml/permutation_importance|outcome=fatal;stage=pre_crash+circumstance;model=hgb;feature=region|log_loss_increase_pct|.1f}}% | {{ml/permutation_importance|outcome=fatal;stage=pre_crash+circumstance;model=logit_main;feature=region|log_loss_increase_pct|.1f}}% | {{ml/permutation_importance|outcome=fatal;stage=pre_crash;model=hgb;feature=region|log_loss_increase_pct|.1f}}% | {{ml/permutation_importance|outcome=fatal;stage=pre_crash;model=logit_main;feature=region|log_loss_increase_pct|.1f}}% |
| `older_driver` | {{ml/permutation_importance|outcome=fatal;stage=pre_crash+circumstance;model=hgb;feature=older_driver|log_loss_increase_pct|.1f}}% | {{ml/permutation_importance|outcome=fatal;stage=pre_crash+circumstance;model=logit_main;feature=older_driver|log_loss_increase_pct|.1f}}% | {{ml/permutation_importance|outcome=fatal;stage=pre_crash;model=hgb;feature=older_driver|log_loss_increase_pct|.1f}}% | {{ml/permutation_importance|outcome=fatal;stage=pre_crash;model=logit_main;feature=older_driver|log_loss_increase_pct|.1f}}% |
| `surface` | {{ml/permutation_importance|outcome=fatal;stage=pre_crash+circumstance;model=hgb;feature=surface|log_loss_increase_pct|.1f}}% | {{ml/permutation_importance|outcome=fatal;stage=pre_crash+circumstance;model=logit_main;feature=surface|log_loss_increase_pct|.1f}}% | {{ml/permutation_importance|outcome=fatal;stage=pre_crash;model=hgb;feature=surface|log_loss_increase_pct|.1f}}% | {{ml/permutation_importance|outcome=fatal;stage=pre_crash;model=logit_main;feature=surface|log_loss_increase_pct|.1f}}% |
| `oldest_vehicle_age` | {{ml/permutation_importance|outcome=fatal;stage=pre_crash+circumstance;model=hgb;feature=oldest_vehicle_age|log_loss_increase_pct|.1f}}% | {{ml/permutation_importance|outcome=fatal;stage=pre_crash+circumstance;model=logit_main;feature=oldest_vehicle_age|log_loss_increase_pct|.1f}}% | {{ml/permutation_importance|outcome=fatal;stage=pre_crash;model=hgb;feature=oldest_vehicle_age|log_loss_increase_pct|.1f}}% | {{ml/permutation_importance|outcome=fatal;stage=pre_crash;model=logit_main;feature=oldest_vehicle_age|log_loss_increase_pct|.1f}}% |
| `n_vehicles` | {{ml/permutation_importance|outcome=fatal;stage=pre_crash+circumstance;model=hgb;feature=n_vehicles|log_loss_increase_pct|.1f}}% | {{ml/permutation_importance|outcome=fatal;stage=pre_crash+circumstance;model=logit_main;feature=n_vehicles|log_loss_increase_pct|.1f}}% | — | — |
| `urbanicity` | {{ml/permutation_importance|outcome=fatal;stage=pre_crash+circumstance;model=hgb;feature=urbanicity|log_loss_increase_pct|.1f}}% | {{ml/permutation_importance|outcome=fatal;stage=pre_crash+circumstance;model=logit_main;feature=urbanicity|log_loss_increase_pct|.1f}}% | {{ml/permutation_importance|outcome=fatal;stage=pre_crash;model=hgb;feature=urbanicity|log_loss_increase_pct|.1f}}% | {{ml/permutation_importance|outcome=fatal;stage=pre_crash;model=logit_main;feature=urbanicity|log_loss_increase_pct|.1f}}% |
| `weekend` | {{ml/permutation_importance|outcome=fatal;stage=pre_crash+circumstance;model=hgb;feature=weekend|log_loss_increase_pct|.1f}}% | {{ml/permutation_importance|outcome=fatal;stage=pre_crash+circumstance;model=logit_main;feature=weekend|log_loss_increase_pct|.1f}}% | {{ml/permutation_importance|outcome=fatal;stage=pre_crash;model=hgb;feature=weekend|log_loss_increase_pct|.1f}}% | {{ml/permutation_importance|outcome=fatal;stage=pre_crash;model=logit_main;feature=weekend|log_loss_increase_pct|.1f}}% |
| `weather` | {{ml/permutation_importance|outcome=fatal;stage=pre_crash+circumstance;model=hgb;feature=weather|log_loss_increase_pct|.1f}}% | {{ml/permutation_importance|outcome=fatal;stage=pre_crash+circumstance;model=logit_main;feature=weather|log_loss_increase_pct|.1f}}% | {{ml/permutation_importance|outcome=fatal;stage=pre_crash;model=hgb;feature=weather|log_loss_increase_pct|.1f}}% | {{ml/permutation_importance|outcome=fatal;stage=pre_crash;model=logit_main;feature=weather|log_loss_increase_pct|.1f}}% |
| `young_driver` | {{ml/permutation_importance|outcome=fatal;stage=pre_crash+circumstance;model=hgb;feature=young_driver|log_loss_increase_pct|.1f}}% | {{ml/permutation_importance|outcome=fatal;stage=pre_crash+circumstance;model=logit_main;feature=young_driver|log_loss_increase_pct|.1f}}% | {{ml/permutation_importance|outcome=fatal;stage=pre_crash;model=hgb;feature=young_driver|log_loss_increase_pct|.1f}}% | {{ml/permutation_importance|outcome=fatal;stage=pre_crash;model=logit_main;feature=young_driver|log_loss_increase_pct|.1f}}% |
| `work_zone` | {{ml/permutation_importance|outcome=fatal;stage=pre_crash+circumstance;model=hgb;feature=work_zone|log_loss_increase_pct|.1f}}% | {{ml/permutation_importance|outcome=fatal;stage=pre_crash+circumstance;model=logit_main;feature=work_zone|log_loss_increase_pct|.1f}}% | {{ml/permutation_importance|outcome=fatal;stage=pre_crash;model=hgb;feature=work_zone|log_loss_increase_pct|.1f}}% | {{ml/permutation_importance|outcome=fatal;stage=pre_crash;model=logit_main;feature=work_zone|log_loss_increase_pct|.1f}}% |
| `interstate` | {{ml/permutation_importance|outcome=fatal;stage=pre_crash+circumstance;model=hgb;feature=interstate|log_loss_increase_pct|.1f}}% | {{ml/permutation_importance|outcome=fatal;stage=pre_crash+circumstance;model=logit_main;feature=interstate|log_loss_increase_pct|.1f}}% | {{ml/permutation_importance|outcome=fatal;stage=pre_crash;model=hgb;feature=interstate|log_loss_increase_pct|.1f}}% | {{ml/permutation_importance|outcome=fatal;stage=pre_crash;model=logit_main;feature=interstate|log_loss_increase_pct|.1f}}% |

Importance measures how much a model *relies* on an input to rank recorded
crashes; it is not the input's causal effect, and correlated inputs share or trade importance
(light and time of day, speed limit and interstate).

**Partial dependence** [`partial_dependence`, `ice_curves`,
`figures/ml/partial_dependence_fatal.png`; circumstance stage, averaged over 3,000 weight-proportional test
crashes]. Selected values of the speed-limit and oldest-vehicle-age curves
(model-predicted probability of a fatal crash):

| Input and value | hgb | logit_main | logit_interact |
|---|---|---|---|
| Speed limit 15 mph | {{ml/partial_dependence|stage=pre_crash+circumstance;model=hgb;feature=speed_limit;value=15|pd_probability|.4f}} | {{ml/partial_dependence|stage=pre_crash+circumstance;model=logit_main;feature=speed_limit;value=15|pd_probability|.4f}} | {{ml/partial_dependence|stage=pre_crash+circumstance;model=logit_interact;feature=speed_limit;value=15|pd_probability|.4f}} |
| Speed limit 30 mph | {{ml/partial_dependence|stage=pre_crash+circumstance;model=hgb;feature=speed_limit;value=30|pd_probability|.4f}} | {{ml/partial_dependence|stage=pre_crash+circumstance;model=logit_main;feature=speed_limit;value=30|pd_probability|.4f}} | {{ml/partial_dependence|stage=pre_crash+circumstance;model=logit_interact;feature=speed_limit;value=30|pd_probability|.4f}} |
| Speed limit 45 mph | {{ml/partial_dependence|stage=pre_crash+circumstance;model=hgb;feature=speed_limit;value=45|pd_probability|.4f}} | {{ml/partial_dependence|stage=pre_crash+circumstance;model=logit_main;feature=speed_limit;value=45|pd_probability|.4f}} | {{ml/partial_dependence|stage=pre_crash+circumstance;model=logit_interact;feature=speed_limit;value=45|pd_probability|.4f}} |
| Speed limit 55 mph | {{ml/partial_dependence|stage=pre_crash+circumstance;model=hgb;feature=speed_limit;value=55|pd_probability|.4f}} | {{ml/partial_dependence|stage=pre_crash+circumstance;model=logit_main;feature=speed_limit;value=55|pd_probability|.4f}} | {{ml/partial_dependence|stage=pre_crash+circumstance;model=logit_interact;feature=speed_limit;value=55|pd_probability|.4f}} |
| Speed limit 60 mph | {{ml/partial_dependence|stage=pre_crash+circumstance;model=hgb;feature=speed_limit;value=60|pd_probability|.4f}} | {{ml/partial_dependence|stage=pre_crash+circumstance;model=logit_main;feature=speed_limit;value=60|pd_probability|.4f}} | {{ml/partial_dependence|stage=pre_crash+circumstance;model=logit_interact;feature=speed_limit;value=60|pd_probability|.4f}} |
| Speed limit 75 mph | {{ml/partial_dependence|stage=pre_crash+circumstance;model=hgb;feature=speed_limit;value=75|pd_probability|.4f}} | {{ml/partial_dependence|stage=pre_crash+circumstance;model=logit_main;feature=speed_limit;value=75|pd_probability|.4f}} | {{ml/partial_dependence|stage=pre_crash+circumstance;model=logit_interact;feature=speed_limit;value=75|pd_probability|.4f}} |
| Oldest-vehicle age 0 years | {{ml/partial_dependence|stage=pre_crash+circumstance;model=hgb;feature=oldest_vehicle_age;value=0|pd_probability|.4f}} | {{ml/partial_dependence|stage=pre_crash+circumstance;model=logit_main;feature=oldest_vehicle_age;value=0|pd_probability|.4f}} | {{ml/partial_dependence|stage=pre_crash+circumstance;model=logit_interact;feature=oldest_vehicle_age;value=0|pd_probability|.4f}} |
| Oldest-vehicle age 10 years | {{ml/partial_dependence|stage=pre_crash+circumstance;model=hgb;feature=oldest_vehicle_age;value=10|pd_probability|.4f}} | {{ml/partial_dependence|stage=pre_crash+circumstance;model=logit_main;feature=oldest_vehicle_age;value=10|pd_probability|.4f}} | {{ml/partial_dependence|stage=pre_crash+circumstance;model=logit_interact;feature=oldest_vehicle_age;value=10|pd_probability|.4f}} |
| Oldest-vehicle age 16 years | {{ml/partial_dependence|stage=pre_crash+circumstance;model=hgb;feature=oldest_vehicle_age;value=16|pd_probability|.4f}} | {{ml/partial_dependence|stage=pre_crash+circumstance;model=logit_main;feature=oldest_vehicle_age;value=16|pd_probability|.4f}} | {{ml/partial_dependence|stage=pre_crash+circumstance;model=logit_interact;feature=oldest_vehicle_age;value=16|pd_probability|.4f}} |
| Oldest-vehicle age 20 years | {{ml/partial_dependence|stage=pre_crash+circumstance;model=hgb;feature=oldest_vehicle_age;value=20|pd_probability|.4f}} | {{ml/partial_dependence|stage=pre_crash+circumstance;model=logit_main;feature=oldest_vehicle_age;value=20|pd_probability|.4f}} | {{ml/partial_dependence|stage=pre_crash+circumstance;model=logit_interact;feature=oldest_vehicle_age;value=20|pd_probability|.4f}} |
| Oldest-vehicle age 30 years | {{ml/partial_dependence|stage=pre_crash+circumstance;model=hgb;feature=oldest_vehicle_age;value=30|pd_probability|.4f}} | {{ml/partial_dependence|stage=pre_crash+circumstance;model=logit_main;feature=oldest_vehicle_age;value=30|pd_probability|.4f}} | {{ml/partial_dependence|stage=pre_crash+circumstance;model=logit_interact;feature=oldest_vehicle_age;value=30|pd_probability|.4f}} |

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
| speeding x dark_unlit | {{ml/implied_interactions|stage=pre_crash+circumstance;pair=speeding x dark_unlit;model=hgb|logit_double_difference|+.2f}} | {{ml/implied_interactions|stage=pre_crash+circumstance;pair=speeding x dark_unlit;model=logit_interact|logit_double_difference|+.2f}} | {{ml/implied_interactions|stage=pre_crash;pair=speeding x dark_unlit;model=hgb|logit_double_difference|+.2f}} | {{ml/implied_interactions|stage=pre_crash;pair=speeding x dark_unlit;model=logit_interact|logit_double_difference|+.2f}} |
| speeding x wet | {{ml/implied_interactions|stage=pre_crash+circumstance;pair=speeding x wet;model=hgb|logit_double_difference|+.2f}} | {{ml/implied_interactions|stage=pre_crash+circumstance;pair=speeding x wet;model=logit_interact|logit_double_difference|+.2f}} | {{ml/implied_interactions|stage=pre_crash;pair=speeding x wet;model=hgb|logit_double_difference|+.2f}} | {{ml/implied_interactions|stage=pre_crash;pair=speeding x wet;model=logit_interact|logit_double_difference|+.2f}} |
| speeding x alcohol | {{ml/implied_interactions|stage=pre_crash+circumstance;pair=speeding x alcohol;model=hgb|logit_double_difference|+.2f}} | {{ml/implied_interactions|stage=pre_crash+circumstance;pair=speeding x alcohol;model=logit_interact|logit_double_difference|+.2f}} | {{ml/implied_interactions|stage=pre_crash;pair=speeding x alcohol;model=hgb|logit_double_difference|+.2f}} | {{ml/implied_interactions|stage=pre_crash;pair=speeding x alcohol;model=logit_interact|logit_double_difference|+.2f}} |
| alcohol x dark_unlit | {{ml/implied_interactions|stage=pre_crash+circumstance;pair=alcohol x dark_unlit;model=hgb|logit_double_difference|+.2f}} | {{ml/implied_interactions|stage=pre_crash+circumstance;pair=alcohol x dark_unlit;model=logit_interact|logit_double_difference|+.2f}} | {{ml/implied_interactions|stage=pre_crash;pair=alcohol x dark_unlit;model=hgb|logit_double_difference|+.2f}} | {{ml/implied_interactions|stage=pre_crash;pair=alcohol x dark_unlit;model=logit_interact|logit_double_difference|+.2f}} |
| high_speed_road x dark_unlit | {{ml/implied_interactions|stage=pre_crash+circumstance;pair=high_speed_road x dark_unlit;model=hgb|logit_double_difference|+.2f}} | {{ml/implied_interactions|stage=pre_crash+circumstance;pair=high_speed_road x dark_unlit;model=logit_interact|logit_double_difference|+.2f}} | {{ml/implied_interactions|stage=pre_crash;pair=high_speed_road x dark_unlit;model=hgb|logit_double_difference|+.2f}} | {{ml/implied_interactions|stage=pre_crash;pair=high_speed_road x dark_unlit;model=logit_interact|logit_double_difference|+.2f}} |
| motorcycle x speeding | {{ml/implied_interactions|stage=pre_crash+circumstance;pair=motorcycle x speeding;model=hgb|logit_double_difference|+.2f}} | {{ml/implied_interactions|stage=pre_crash+circumstance;pair=motorcycle x speeding;model=logit_interact|logit_double_difference|+.2f}} | {{ml/implied_interactions|stage=pre_crash;pair=motorcycle x speeding;model=hgb|logit_double_difference|+.2f}} | {{ml/implied_interactions|stage=pre_crash;pair=motorcycle x speeding;model=logit_interact|logit_double_difference|+.2f}} |
| motorcycle x alcohol | {{ml/implied_interactions|stage=pre_crash+circumstance;pair=motorcycle x alcohol;model=hgb|logit_double_difference|+.2f}} | {{ml/implied_interactions|stage=pre_crash+circumstance;pair=motorcycle x alcohol;model=logit_interact|logit_double_difference|+.2f}} | {{ml/implied_interactions|stage=pre_crash;pair=motorcycle x alcohol;model=hgb|logit_double_difference|+.2f}} | {{ml/implied_interactions|stage=pre_crash;pair=motorcycle x alcohol;model=logit_interact|logit_double_difference|+.2f}} |
| young_driver x late_night | {{ml/implied_interactions|stage=pre_crash+circumstance;pair=young_driver x late_night;model=hgb|logit_double_difference|+.2f}} | {{ml/implied_interactions|stage=pre_crash+circumstance;pair=young_driver x late_night;model=logit_interact|logit_double_difference|+.2f}} | {{ml/implied_interactions|stage=pre_crash;pair=young_driver x late_night;model=hgb|logit_double_difference|+.2f}} | {{ml/implied_interactions|stage=pre_crash;pair=young_driver x late_night;model=logit_interact|logit_double_difference|+.2f}} |
| older_driver x angle | {{ml/implied_interactions|stage=pre_crash+circumstance;pair=older_driver x angle;model=hgb|logit_double_difference|+.2f}} | {{ml/implied_interactions|stage=pre_crash+circumstance;pair=older_driver x angle;model=logit_interact|logit_double_difference|+.2f}} | — | — |
| heavy_truck x high_speed_road | {{ml/implied_interactions|stage=pre_crash+circumstance;pair=heavy_truck x high_speed_road;model=hgb|logit_double_difference|+.2f}} | {{ml/implied_interactions|stage=pre_crash+circumstance;pair=heavy_truck x high_speed_road;model=logit_interact|logit_double_difference|+.2f}} | {{ml/implied_interactions|stage=pre_crash;pair=heavy_truck x high_speed_road;model=hgb|logit_double_difference|+.2f}} | {{ml/implied_interactions|stage=pre_crash;pair=heavy_truck x high_speed_road;model=logit_interact|logit_double_difference|+.2f}} |
| rural x dark_unlit | {{ml/implied_interactions|stage=pre_crash+circumstance;pair=rural x dark_unlit;model=hgb|logit_double_difference|+.2f}} | {{ml/implied_interactions|stage=pre_crash+circumstance;pair=rural x dark_unlit;model=logit_interact|logit_double_difference|+.2f}} | {{ml/implied_interactions|stage=pre_crash;pair=rural x dark_unlit;model=hgb|logit_double_difference|+.2f}} | {{ml/implied_interactions|stage=pre_crash;pair=rural x dark_unlit;model=logit_interact|logit_double_difference|+.2f}} |
| weekend x late_night | {{ml/implied_interactions|stage=pre_crash+circumstance;pair=weekend x late_night;model=hgb|logit_double_difference|+.2f}} | {{ml/implied_interactions|stage=pre_crash+circumstance;pair=weekend x late_night;model=logit_interact|logit_double_difference|+.2f}} | {{ml/implied_interactions|stage=pre_crash;pair=weekend x late_night;model=hgb|logit_double_difference|+.2f}} | {{ml/implied_interactions|stage=pre_crash;pair=weekend x late_night;model=logit_interact|logit_double_difference|+.2f}} |
| pedestrian x dark_unlit | {{ml/implied_interactions|stage=pre_crash+circumstance;pair=pedestrian x dark_unlit;model=hgb|logit_double_difference|+.2f}} | {{ml/implied_interactions|stage=pre_crash+circumstance;pair=pedestrian x dark_unlit;model=logit_interact|logit_double_difference|+.2f}} | — | — |

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

{{mdtable:ml/pattern_confirmation|kind=interaction|candidate:Candidate (screened on 2016–2022 crashes, tested on 2023–2024);boosting_estimate:Boosting log-odds double difference:+.2f;survey_estimate:Survey product-term log OR (95% CI):ci:2@survey_ci;ratio_of_or:Ratio of ORs:.2f;interaction_contrast:Additive interaction contrast (95% CI):ci:3@ic;p_value:Wald p:.2g;p_holm:Holm p:.2g;boosting_within_survey_ci:Boosting estimate inside survey CI:;verdict:Verdict:}}

Standardised adjusted fatal risks behind the additive contrasts (predictive margins over all
2023–2024 crashes; "first factor" is the first factor named in the candidate with the second at its
reference level, and vice versa):

{{mdtable:ml/pattern_confirmation|kind=interaction|candidate:Candidate;p00:Both references:pct:2;p10:First factor only:pct:2;p01:Second factor only:pct:2;p11:Both factors:pct:2}}

Departures from the logistic form (non-linearity checks):

{{mdtable:ml/pattern_confirmation|kind=non-linearity|candidate:Candidate;wald_F:Wald F:.2f;df_num:Numerator df:.0f;p_holm:Holm p:.2g;boosting_estimate:Boosting estimate:+.2f;boosting_estimate_scale:Boosting estimate measures;terms_detail:Survey odds ratios (95% CI);verdict:Verdict:}}

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
(fatal, test years: calibration slope {{ml/metrics_test|outcome=fatal;stage=pre_crash;model=hgb;domain=all;weighting=weighted;metric=calibration_slope|estimate|.2f}} pre-crash and {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=hgb;domain=all;weighting=weighted;metric=calibration_slope|estimate|.2f}} circumstance, observed/expected {{ml/metrics_test|outcome=fatal;stage=pre_crash;model=hgb;domain=all;weighting=weighted;metric=oe_ratio|estimate|.2f}} and {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=hgb;domain=all;weighting=weighted;metric=oe_ratio|estimate|.2f}}; this overall calibration nets under-prediction in crashes without a hit-and-run,
observed/expected {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=hgb;domain=hit_and_run=no;weighting=weighted;metric=oe_ratio|estimate|ci:2@ci}}, against over-prediction in hit-and-run crashes, {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=hgb;domain=hit_and_run=yes;weighting=weighted;metric=oe_ratio|estimate|.2f}}; §5.2),
better than the main-effects logistic model on every proper scoring rule (paired CIs exclude
zero, §5.1) and better than the other logistic variants by similar margins. The gain is moderate (fatal AUROC {{ml/paired_differences|outcome=fatal;stage=pre_crash;model=hgb;comparison=vs logit_main;metric=auroc|estimate|ci:3@ci}} pre-crash and {{ml/paired_differences|outcome=fatal;stage=pre_crash+circumstance;model=hgb;comparison=vs logit_main;metric=auroc|estimate|ci:3@ci}} circumstance; Brier skill {{ml/paired_differences|outcome=fatal;stage=pre_crash;model=hgb;comparison=vs logit_main;metric=brier_skill|estimate|ci:3@ci}} and {{ml/paired_differences|outcome=fatal;stage=pre_crash+circumstance;model=hgb;comparison=vs logit_main;metric=brier_skill|estimate|ci:3@ci}}). It does not come from the
RQ2 interactions, which boosting reproduces and the logistic interaction model already
contains; the screen points to crash-type-specific effects (§7), some of which were confirmed in the independent test years
(see the verdicts there; the candidates are exploratory leads). Consequences:

* **Risk stratification of recorded crashes and the interface:** boosting, circumstance stage
  when crash configuration is known, pre-crash stage otherwise.
* **Explanation and inference:** the survey logistic models of RQ1/RQ2, whose predictions are
  nearly as good (AUROC lower by {{ml/paired_differences|outcome=fatal;stage=pre_crash+circumstance;model=hgb;comparison=vs logit_main;metric=auroc|estimate|ci:3@ci}} in the circumstance stage, similarly calibrated, including the same low-risk
  over-prediction in the test years) and whose coefficients have
  design-based standard errors. The confirmatory analyses above show which specific
  boosting-detected patterns those models should add.
* **What the comparison with the interacted logistic model does and does not show.** The statement
  above that the gain over the logistic models "does not come from the RQ2 interactions" is partly
  answered by `severity/fatal_effect_modification` (added after the red-team review): the crash-type
  interactions it tests are large and statistically clear for exceeding the limit, alcohol,
  motorcycles and large trucks. For "too fast for conditions" there is no detectable difference
  between single- and multi-vehicle crashes (homogeneity p = {{severity/fatal_effect_modification|outcome=fatal;exposure=too_fast_for_conditions;modifier=single vs multi-vehicle|min(p_homogeneity_rr)|.2f}}) but finer crash types do
  differ (p = {{severity/fatal_effect_modification|outcome=fatal;exposure=too_fast_for_conditions;modifier=crash type|min(p_homogeneity_rr)|.3f}}); both p-values are in the table, and a non-significant test is not evidence
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
police-reported crashes. **Training data:** CRSS 2016–2021, {{json:ml/run_info|rows.fatal.train|,.0f}} crashes ({{json:ml/run_info|events.fatal.train|,.0f}} fatal,
{{json:ml/run_info|events.ka.train|,.0f}} KA), survey weights as sample weights; preprocessing fitted on these years only.
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
| Fatal test AUROC (pre / circ.) | {{ml/metrics_test|outcome=fatal;stage=pre_crash;model=logit_main;domain=all;weighting=weighted;metric=auroc|estimate|.3f}} / {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=logit_main;domain=all;weighting=weighted;metric=auroc|estimate|.3f}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash;model=logit_l2;domain=all;weighting=weighted;metric=auroc|estimate|.3f}} / {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=logit_l2;domain=all;weighting=weighted;metric=auroc|estimate|.3f}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash;model=logit_interact;domain=all;weighting=weighted;metric=auroc|estimate|.3f}} / {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=logit_interact;domain=all;weighting=weighted;metric=auroc|estimate|.3f}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash;model=hgb;domain=all;weighting=weighted;metric=auroc|estimate|.3f}} / {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=hgb;domain=all;weighting=weighted;metric=auroc|estimate|.3f}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash;model=rf;domain=all;weighting=weighted;metric=auroc|estimate|.3f}} / {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=rf;domain=all;weighting=weighted;metric=auroc|estimate|.3f}} |
| Fatal calibration slope (pre / circ.) | {{ml/metrics_test|outcome=fatal;stage=pre_crash;model=logit_main;domain=all;weighting=weighted;metric=calibration_slope|estimate|.2f}} / {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=logit_main;domain=all;weighting=weighted;metric=calibration_slope|estimate|.2f}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash;model=logit_l2;domain=all;weighting=weighted;metric=calibration_slope|estimate|.2f}} / {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=logit_l2;domain=all;weighting=weighted;metric=calibration_slope|estimate|.2f}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash;model=logit_interact;domain=all;weighting=weighted;metric=calibration_slope|estimate|.2f}} / {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=logit_interact;domain=all;weighting=weighted;metric=calibration_slope|estimate|.2f}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash;model=hgb;domain=all;weighting=weighted;metric=calibration_slope|estimate|.2f}} / {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=hgb;domain=all;weighting=weighted;metric=calibration_slope|estimate|.2f}} | {{ml/metrics_test|outcome=fatal;stage=pre_crash;model=rf;domain=all;weighting=weighted;metric=calibration_slope|estimate|.2f}} / {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=rf;domain=all;weighting=weighted;metric=calibration_slope|estimate|.2f}} |
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
  alcohol changes the boosted model's circumstance-stage AUROC by {{ml/feature_sensitivity|outcome=fatal;stage=pre_crash+circumstance;variant=without speeding and alcohol_im;model=hgb;metric=auroc|diff_vs_main|ci:3@diff_ci}}
  [`feature_sensitivity`], so part of the discrimination rests on them.
* **Hit-and-run proxy.** Bounded by the proxy-blind refit (§6) but not removed from the
  primary models; the cleaner fix is NHTSA-imputed body type and model year upstream.
* **Drift.** The fatal share among police-reported crashes rose after 2020; models trained on
  earlier years under-predict later years (observed/expected up to {{ml/temporal_stability|outcome=fatal;stage=pre_crash+circumstance;model=hgb~logit_main;eval_year=2020~2021~2022~2023~2024;metric=oe_ratio|max(estimate)|.2f}}, §6), and fatal shares in
  motorcycle and pedestrian/cyclist crashes in 2023–2024 exceed predictions (observed/expected {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=logit_main~hgb;domain=crash_family=pedestrian_cyclist~motorcycle=yes;weighting=weighted;metric=oe_ratio|min(estimate)|.2f}}–{{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=logit_main~hgb;domain=crash_family=pedestrian_cyclist~motorcycle=yes;weighting=weighted;metric=oe_ratio|max(estimate)|.2f}}, §5.2). In
  the test years the lowest-risk half of crashes was over-predicted (observed/expected {{ml/calibration_by_risk_tier|outcome=fatal;stage=pre_crash+circumstance;model=hgb;weighting=weighted;risk_tier=lowest 50% of predicted risk|oe_ratio|.2f}} for boosting) and the
  top fifth under-predicted ({{ml/calibration_by_risk_tier|outcome=fatal;stage=pre_crash+circumstance;model=hgb;weighting=weighted;risk_tier=highest 20%|oe_ratio|.2f}}, §5.1), so risk ratios between low- and high-risk
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
{{json:ml/run_info|runtime_seconds|,.0f}} s of wall time and {{json:ml/run_info|cpu_seconds|,.0f}} s of CPU time [`run_info.json`]. Boosting is much faster with a single OpenMP thread when other processes share the
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
  reproduces the Phase-1 adjusted exceedance RR exactly ({{severity/fatal_speeding_type|factor=speeding_type;level=exceeded_limit_or_racing|adj_rr|.2f}}; compare the model-A row of the speeding lattice with `severity/fatal_speeding_type`).
* **Convergence and support.** Every factorial model records convergence and the number of
  withheld combinations (`multifactor/analyses`).
* **Predictive contribution.** `contributions/predictive` uses the Phase-1 temporal split
  (train 2016–2021, test 2023–2024) with a design-weighted pseudo-R² and AUROC; the full logistic
  model's test AUROC is close to the Phase-1 main-effects survey logistic model with configuration.
  Uncertainty: PSU-within-stratum bootstrap of the test set with the model fixed (training
  variability not included).
