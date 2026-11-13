# What makes US road crashes deadly? FARS and CRSS, 2016–2024

A reproducible Python research system built on the 36 NHTSA archives in `data/raw/`: **FARS**
(census of fatal crashes) and **CRSS** (national probability sample of police-reported crashes).
No other data are used. Every estimate, count and share in `reports/`, on the website and in this README is read from an output table
in `outputs/tables/`, each with a provenance sidecar. The few facts typed into the text are not results: the
number of archives, the tally of the review record and the run time. This README is generated from
`reports/templates/README.md` by `nhtsa analyze report`; edit the template, not this file.

## What the data answer, and what they cannot

The data answer four kinds of question reasonably well:

1. **Within the same vehicle in the same fatal crash, how much less often belted occupants and
   helmeted riders died**, how that varies by crash type, and how far misreported belt or helmet use
   could change it.
2. **Which circumstances stay associated with a reported crash being fatal after design-based
   adjustment in CRSS**: exceeding the limit, motorcycles, alcohol (with its coding range),
   pedestrians struck on faster roads, older drivers.
3. **How the records themselves behave**: coding breaks and selective testing.
4. **How the fatal share of reported crashes changed after 2020**, and how much of that the recorded
   crash mix explains.

They cannot answer: **crash risk per mile, trip or driver** (there is no exposure measure); **the
effect of any enforcement, camera, testing or campaign** (none is recorded); **the effect of drugs**
(testing is selective and the fields unreliable); or **any causal effect**. Everything about severity
is conditional on a police-reported crash. Intervals cover sampling error only unless stated.
Limitations: `docs/limitations.md`. An independent adversarial review weakened 21 of 31 published
findings, never in direction: `docs/red_team_2026-11.md`.

## Findings

Numbers are quoted as the named tables give them. Full text, intervals and caveats are in
`reports/findings.md` and `reports/road_deaths.md`.

**1. Belts and helmets (FARS, within the same vehicle).**
* Belted drivers and right-front passengers died {{matched/belt_effect|estimand=fatality_risk_reduction_belt_given_fatal_crash|estimate|cipct:1}} less often than their unbelted
  companion (`matched/belt_effect`).
* The pooled figure averages different crash types: {{matched/belt_by_crash_type|stratum=multi-vehicle, angle|dpc_reduction|pct:1}} in multi-vehicle angle crashes, {{matched/belt_by_crash_type|stratum=single vehicle, rollover first|dpc_reduction|pct:1}} in
  single-vehicle rollovers (`matched/belt_by_crash_type`).
* It depends on truthful reporting by survivors. Allowing 10% of belted survivors and 5% of
  unbelted-coded deaths to be misrecorded gives {{matched/belt_misreporting_two_sided_dpc|analysis=belt_driver_rf;survivor_misreport_f=0.1;death_misreport_g=0.05|reduction_1_minus_rr|cipct:1@reduction}}; the reduction vanishes at
  {{matched/belt_misreporting_two_sided_dpc|analysis=belt_driver_rf;survivor_misreport_f=0;death_misreport_g=0|tipping_f_given_g|pct:1}} survivor misreporting alone and {{matched/belt_misreporting_two_sided_dpc|analysis=belt_driver_rf;survivor_misreport_f=0;death_misreport_g=0.05|tipping_f_given_g|pct:1}} with 5% reverse error
  (`matched/belt_misreporting_two_sided_dpc`).
* Exploratory follow-up: within crash configuration, belts are somewhat *less* protective with a
  speeding driver. The ratio of belt risk ratios is {{restraint_behaviour/dpc_contrast_within_configuration|contrast=driver speeding (any) vs not speeding;layer=pooled within layers|min(ratio_of_rrs)|.2f}} to {{restraint_behaviour/dpc_contrast_within_configuration|contrast=driver speeding (any) vs not speeding;layer=pooled within layers|max(ratio_of_rrs)|.2f}} across four ways of layering crashes
  (lower confidence limits {{restraint_behaviour/dpc_contrast_within_configuration|contrast=driver speeding (any) vs not speeding;layer=pooled within layers|min(ratio_low)|.2f}} or above): {{restraint_behaviour/dpc_contrast_within_configuration|contrast=driver speeding (any) vs not speeding;adjustment=single/multi-vehicle x rollover;layer=pooled within layers|ratio_of_rrs|ci:2@ratio}} with single/multi-vehicle and rollover
  crossed ({{restraint_behaviour/dpc_contrast_within_configuration|contrast=driver speeding (any) vs not speeding;adjustment=single/multi-vehicle x rollover;layer=pooled within layers|n_layers_pooled|.0f}} of 4 layers pooled), the largest of the four; the crash-type scheme pools only {{restraint_behaviour/dpc_contrast_within_configuration|contrast=driver speeding (any) vs not speeding;adjustment=crash type;layer=pooled within layers|n_layers_pooled|.0f}} of its 8
  crash types. Pooling crashes first gives {{restraint_behaviour/dpc_contrast_within_configuration|contrast=driver speeding (any) vs not speeding;adjustment=none (unstratified)|ratio_of_rrs|ci:2@ratio}}. The alcohol contrast shows no detectable difference (p = {{restraint_behaviour/dpc_contrast_within_configuration|contrast=driver BAC >= .08 (MI) vs BAC < .08;adjustment=single/multi-vehicle x rollover;layer=pooled within layers|p|.2f}}), {{restraint_behaviour/dpc_contrast_within_configuration|contrast=driver BAC >= .08 (MI) vs BAC < .08;adjustment=single/multi-vehicle x rollover;layer=pooled within layers|ratio_of_rrs|ci:2@ratio}} (`restraint_behaviour/dpc_contrast_within_configuration`). The earlier unstratified
  conclusion that the belt effect does not vary with driver speeding does not hold within crash
  configuration.
* Motorcycle helmets: {{matched/helmet_misreporting_dpc|analysis=motorcycle_helmet;survivor_misreport_f=0;death_misreport_g=0|reduction_1_minus_rr|cipct:1@reduction}} fewer deaths among riders and passengers of the same
  motorcycle, but {{matched/helmet_pair_coverage|metric=pairs_discordant_helmet_use|count|,.0f}} of {{matched/helmet_pair_coverage|metric=pairs_operator_passenger|count|,.0f}} pairs differ in helmet use, the pair design covers {{matched/helmet_pair_coverage|metric=unhelmeted_deaths_in_pair_design|share|pct:1}} of unhelmeted
  deaths, and the effect vanishes at {{matched/helmet_misreporting_dpc|analysis=motorcycle_helmet;survivor_misreport_f=0;death_misreport_g=0|tipping_f_given_g|pct:1}} survivor misreporting
  (`matched/helmet_misreporting_dpc`, `matched/helmet_pair_coverage`).

**2. Conditional associations in CRSS that survive adjustment** (associations, not effects).
* Exceeding the limit or racing: adjusted fatal risk ratio {{severity/speeding_type_models|outcome=fatal;model=A;level=exceeded_limit_or_racing|adj_rr|.2f}} ({{severity/speeding_type_models|outcome=fatal;model=A;level=exceeded_limit_or_racing|adj_rr_low95|.2f}}–{{severity/speeding_type_models|outcome=fatal;model=A;level=exceeded_limit_or_racing|adj_rr_high95|.2f}}) under model A and {{severity/speeding_type_models|outcome=fatal;model=B;level=exceeded_limit_or_racing|adj_rr|.2f}} ({{severity/speeding_type_models|outcome=fatal;model=B;level=exceeded_limit_or_racing|adj_rr_low95|.2f}}–{{severity/speeding_type_models|outcome=fatal;model=B;level=exceeded_limit_or_racing|adj_rr_high95|.2f}})
  with crash configuration also held fixed (`severity/speeding_type_models`).
* Motorcycle involvement {{severity/fatal_crude_vs_adjusted|factor=any_motorcycle;level=yes|A_adj_rr|ci:1}}; heavy truck or bus {{severity/fatal_crude_vs_adjusted|factor=any_heavy_truck;level=yes|A_adj_rr|ci:2}}; unlit darkness {{severity/fatal_crude_vs_adjusted|factor=light;level=dark_not_lighted|A_adj_rr|ci:2}}; driver aged 65+ {{severity/fatal_crude_vs_adjusted|factor=older_driver;level=yes|A_adj_rr|ci:2}} (`severity/fatal_crude_vs_adjusted`).
* Alcohol {{measurement/alcohol_coding_sensitivity|period=2016-2024;coding=imputed (ALCHL_IM)|adj_rr|ci:2}} with NHTSA's imputation, {{measurement/alcohol_coding_sensitivity|period=2016-2024;coding=police, complete case|adj_rr|ci:2}} among crashes with known police
  alcohol, {{measurement/alcohol_coding_sensitivity|period=2016-2024;coding=police, unknown as no|adj_rr|ci:2}} if unknown is treated as "no" (`measurement/alcohol_coding_sensitivity`).
* Pedestrians struck on 50–55 mph roads against 25 mph or less: {{vulnerable/pedestrian_speed_limit_adjustment|victim=pedestrian;outcome=killed;specification=full (published);level=50-55|adj_rr|ci:2}} adjusted, {{vulnerable/pedestrian_speed_limit_adjustment|victim=pedestrian;outcome=killed;specification=without location, light and time of day;level=50-55|adj_rr|.1f}} without
  adjustment for location, light and time of day (`vulnerable/pedestrian_speed_limit_adjustment`).
* "Too fast for conditions" is a small, imprecise association: {{severity/speeding_type_models|outcome=fatal;model=A;level=too_fast_for_conditions|adj_rr|.2f}} ({{severity/speeding_type_models|outcome=fatal;model=A;level=too_fast_for_conditions|adj_rr_low95|.2f}}–{{severity/speeding_type_models|outcome=fatal;model=A;level=too_fast_for_conditions|adj_rr_high95|.2f}}) under model A, which
  excludes only effects beyond about ±{{severity/speeding_type_models|outcome=fatal;model=A;level=too_fast_for_conditions|equivalence_bound_pct|.0f}}%, and {{severity/speeding_type_models|outcome=fatal;model=B;level=too_fast_for_conditions|adj_rr|.2f}} ({{severity/speeding_type_models|outcome=fatal;model=B;level=too_fast_for_conditions|adj_rr_low95|.2f}}–{{severity/speeding_type_models|outcome=fatal;model=B;level=too_fast_for_conditions|adj_rr_high95|.2f}}) under model B. **The split of speeding
  by type is exploratory.**
* Within CRSS alone, limit exceedance is over-represented among fatal crashes {{speeding/crss_overrepresentation|speeding=exceeded_limit_or_racing|crss_only_ratio|ci:2}} times,
  against {{speeding/crss_overrepresentation|speeding=exceeded_limit_or_racing|mixed_fars_crss_ratio|ci:2@mixed_ratio}} for the mixed FARS/CRSS ratio; both intervals reflect CRSS sampling only
  (`speeding/crss_overrepresentation`).
* Interstates are safer than comparable roads on 50–65 mph roads, {{severity/interstate_by_speed_band|outcome=fatal;speed_limit_band=50-65 mph;quantity=RR interstate vs not|estimate|ci:2}}, but not at 70+ mph,
  {{severity/interstate_by_speed_band|outcome=fatal;speed_limit_band=70+ mph;quantity=RR interstate vs not|estimate|ci:2}} (`severity/interstate_by_speed_band`). Rain and teenage drivers: see
  `severity/key_contrasts_ab` (models A and B).
* Exploratory follow-up added after the red-team review: the pooled model-A risk ratios above average over very different
  crash configurations, and the relative association is larger in multi-vehicle crashes, where the baseline fatal risk is low.
  Adjusted fatal risk ratios in single-vehicle against multi-vehicle crashes: exceeding the limit {{severity/fatal_effect_modification|modifier=single vs multi-vehicle;exposure=exceeded_limit;stratum=single-vehicle|adj_rr|.1f}} against {{severity/fatal_effect_modification|modifier=single vs multi-vehicle;exposure=exceeded_limit;stratum=multi-vehicle|adj_rr|.1f}}; alcohol {{severity/fatal_effect_modification|modifier=single vs multi-vehicle;exposure=alcohol;stratum=single-vehicle|adj_rr|.1f}} against {{severity/fatal_effect_modification|modifier=single vs multi-vehicle;exposure=alcohol;stratum=multi-vehicle|adj_rr|.1f}}; motorcycle {{severity/fatal_effect_modification|modifier=single vs multi-vehicle;exposure=motorcycle;stratum=single-vehicle|adj_rr|.1f}} against {{severity/fatal_effect_modification|modifier=single vs multi-vehicle;exposure=motorcycle;stratum=multi-vehicle|adj_rr|.1f}}; large truck or bus {{severity/fatal_effect_modification|modifier=single vs multi-vehicle;exposure=large_truck;stratum=single-vehicle|adj_rr|.1f}} against {{severity/fatal_effect_modification|modifier=single vs multi-vehicle;exposure=large_truck;stratum=multi-vehicle|adj_rr|.1f}} (homogeneity p ≤ {{severity/fatal_effect_modification|modifier=single vs multi-vehicle;exposure=exceeded_limit~alcohol~motorcycle~large_truck|max(p_homogeneity_rr)|.1e}} for each). "Too fast for conditions" shows no detectable difference, {{severity/fatal_effect_modification|modifier=single vs multi-vehicle;exposure=too_fast_for_conditions;stratum=single-vehicle|adj_rr|.2f}} against {{severity/fatal_effect_modification|modifier=single vs multi-vehicle;exposure=too_fast_for_conditions;stratum=multi-vehicle|adj_rr|.2f}} (p = {{severity/fatal_effect_modification|modifier=single vs multi-vehicle;exposure=too_fast_for_conditions;stratum=single-vehicle|p_homogeneity_rr|.2f}})
  (`severity/fatal_effect_modification`). Associations conditional on a police-reported crash, not causal effects.

**3. Measurement.**
* Killed drivers are tested for alcohol far more often than survivors ({{measurement/alcohol_testing_share|driver_status=killed|share_alcohol_tested|pct:1}} against {{measurement/alcohol_testing_share|driver_status=survived|share_alcohol_tested|pct:1}},
  `measurement/alcohol_testing_share`), but police-recorded alcohol, drug and distraction fields are
  more often *unknown* in fatal crashes (alcohol {{measurement/unknown_by_severity|kabco=4;field=alcohol|pct_unknown|.1f}}% against {{measurement/unknown_by_severity|kabco=0;field=alcohol|pct_unknown|.1f}}% for no-injury crashes,
  `measurement/unknown_by_severity`).
* Police reports identify BAC ≥ .08 in {{measurement/police_vs_bac_selection|scheme=all;driver_status=killed|police_sensitivity_vs_bac08|pct:1}} of tested killed drivers and {{measurement/police_vs_bac_selection|scheme=all;driver_status=survived|police_sensitivity_vs_bac08|pct:1}} of tested survivors, but
  survivors are tested mainly on suspicion; their sensitivity falls from {{measurement/police_vs_bac_selection|scheme=state-year survivor test-rate tercile;group=low;driver_status=survived|police_sensitivity_vs_bac08|pct:1}} to {{measurement/police_vs_bac_selection|scheme=state-year survivor test-rate tercile;group=high;driver_status=survived|police_sensitivity_vs_bac08|pct:1}} as testing broadens
  (`measurement/police_vs_bac_selection`).
* CRSS alcohol coding broke in 2019; the alcohol association is reported under three codings. Drug and
  distraction fields cannot support severity or trend analysis.

**4. The post-2020 rise.** The fatal share of police-reported crashes rose by a factor of {{trends/numerator_denominator|outcome=fatal;comparison=2020-2024 vs 2016-2019;quantity=ratio_fatal_share|estimate|ci:2}}. The recorded crash mix accounts for {{trends/composition_robustness|covariate_set=A;quantity=composition_share_of_change_ref_P0~composition_share_of_change_ref_P1|min(estimate)|pct:0}} to {{trends/composition_robustness|covariate_set=A;quantity=composition_share_of_change_ref_P0~composition_share_of_change_ref_P1|max(estimate)|pct:0}} of it without
crash configuration (model A) and {{trends/composition_robustness|covariate_set=B;quantity=composition_share_of_change_ref_P0~composition_share_of_change_ref_P1|min(estimate)|pct:0}} to {{trends/composition_robustness|covariate_set=B;quantity=composition_share_of_change_ref_P0~composition_share_of_change_ref_P1|max(estimate)|pct:0}} with it (model B, where configuration may itself be a mediator),
across four specifications and two reference periods; several of the individual intervals include zero
(`trends/composition_robustness`). "Roughly a quarter to a half" is the model-B range only. The fall in
reported crashes accounts for {{trends/denominator_share|outcome=fatal;comparison=2020-2024 vs 2016-2019;quantity=denominator_share_of_log_rise|estimate|cipct:1}} of the rise in the share, or {{trends/denominator_share|outcome=fatal_cc;comparison=2020-2024 vs 2016-2019;quantity=denominator_share_of_log_rise|estimate|cipct:1}} under
the complete-case outcome (`trends/denominator_share`).

**Also.** Official factor counts overlap and cannot be added: deaths in speeding, drunk-driving,
drug-positive and unbelted categories sum to at least {{contributions/fars_overlap_summary|factor=sum of the four factor counts|share_of_all_deaths|pct:0}} of deaths, and between {{contributions/fars_overlap_treatments|drug_status_handling=undetermined = no drug|share_with_any_factor|pct:1}} and {{contributions/fars_overlap_treatments|drug_status_handling=undetermined = drug|share_with_any_factor|pct:1}} involve
at least one, depending on how undetermined drug status is scored (`contributions/fars_overlap_treatments`).
Drug effects cannot be ranked or estimated. Attributable fractions are model-based, change with the alcohol
coding and model period (`burden/attributable_fraction_variants`), and are not lives saved by any programme.

**Appendix: prediction models** (`docs/model_validation.md`). Boosted trees reach a test AUROC of {{ml/metrics_test|outcome=fatal;stage=pre_crash+circumstance;model=hgb;domain=all;weighting=weighted;metric=auroc|estimate|ci:3@ci}} for fatal crashes in 2023–2024, but they are descriptive, not a finding about causes. Police-judged
speeding and imputed alcohol are recorded after the crash; dropping both changes test AUROC by {{ml/feature_sensitivity|outcome=fatal;stage=pre_crash+circumstance;variant=without speeding and alcohol_im;model=hgb;metric=auroc|diff_vs_main|+.3f}}
(`ml/feature_sensitivity`).

**Interventions.** The policy part is an observed baseline (deaths by overlapping segment) and an evidence
ledger restating measured associations (`reports/policy_analysis.md`). It estimates no intervention effect.

## Quick start

Requirements: Python ≥ 3.11, [uv](https://docs.astral.sh/uv/), Git LFS (the archives are LFS objects).

```bash
git lfs pull                      # fetch the 36 archives (~675 MB)
uv sync --extra app               # create the environment from uv.lock
uv run nhtsa list                 # list the analysis modules
uv run nhtsa all                  # build the datasets, then run every module
uv run pytest                     # unit tests; data tests skip without the caches
uv run streamlit run app/streamlit_app.py   # research interface
```

A change to one analysis only needs `uv run nhtsa analyze <module>`; the caches and datasets are reused.

| Command | What it does |
|---|---|
| `nhtsa ingest` | Validate archives, convert changed ones to typed Parquet (`data/interim/`, git-ignored) |
| `nhtsa inventory` / `validate` | Data inventory and relational-integrity checks (`outputs/audit/`) |
| `nhtsa features` | Harmonised analytic datasets (`data/processed/`, git-ignored) |
| `nhtsa analyze [module …]` | Run modules into `outputs/tables/<module>/`. Modules: descriptive, severity, measurement, interactions, confounding, trends, person, matched, exposure, burden, vulnerable, ml, speeding, drugs, multifactor, restraint_behaviour, contributions, stages, deaths, policy, plus figures, report, site, docs |
| `nhtsa analyze report site docs` | Re-render `reports/`, the website page and generated docs from the tables |

**Runtime.** A clean `nhtsa all` takes about two hours on 4 idle cores (measured November 2026).
Building the datasets from the archives takes a few minutes; the longest modules are `confounding`
(about 32 minutes), `speeding` (16), `severity` (13), `matched` (11), `person` (10), `interactions` (9)
and `ml` (8). Re-run one module with `uv run nhtsa analyze <module>`; `uv run nhtsa status` lists tables
whose producing code or input data changed since they were written. A clean rebuild from the raw archives
in November 2026 reproduced every committed table byte for byte.

## Data

| | FARS | CRSS |
|---|---|---|
| What | Every crash on a public trafficway with a death within 30 days | Probability sample of police-reported crashes, all severities |
| Years | 2016–2024 | 2016–2024 |
| Size | {{matched/population_flow|step=all FARS person records|crashes|,.0f}} fatal crashes, {{matched/population_flow|step=all FARS person records|deaths|,.0f}} deaths | {{speeding/crss_overrepresentation|speeding=exceeded_limit_or_racing|n_crss_crashes|,.0f}} sampled crashes (about {{descriptive/crss_annual||min(crashes)|mn:1}}–{{descriptive/crss_annual||max(crashes)|mn:1}} million a year weighted) |
| Use | Counts and composition of fatal crashes; within-vehicle designs | Denominators, severity rates and models (design-based: {{descriptive/crss_design||n_strata|.0f}} strata, {{descriptive/crss_design||n_psu|.0f}} PSUs) |

FARS and CRSS rows are never pooled. CRSS weights are benchmarked to FARS fatal totals, so agreement between
them on fatal counts is partly by construction. The archives contain no manuals; variable meanings come from the
embedded value labels and verified cross-tabulation. See `docs/data_audit.md`, `docs/data_dictionary.md`,
`docs/variable_harmonization.md` and `docs/audit_2026-11.md`.

## Repository layout

```
data/raw/            36 original ZIP archives (Git LFS, unchanged)
src/nhtsa_stats/     ingestion, validation, processing (harmonisation + leakage registry), analysis,
                     models (prediction), simulation (observed baseline, evidence ledger), reporting
app/                 Streamlit research interface
docs/                research plans, audits, methodology, limitations, model validation, red-team record
reports/             rendered reports; templates/ holds the sources (edit those, not the output)
outputs/             generated tables and figures (small, committed) and the audit inventory
tests/               unit tests (synthetic fixtures) and data tests (real cache)
website/             static public site (see below)
```

Reading order: `reports/road_deaths.md` (where the deaths are), `reports/findings.md` (what makes a reported
crash deadly), `docs/limitations.md`, then the Phase-2 reports on overlapping factors
(`reports/factor_contributions.md`, `speeding_confounding.md`, `alcohol_drugs_restraints.md`,
`multifactor_interactions.md`) and `docs/research_plan.md`.

## Public website

**Road Deaths in America** is a static site, live at https://rahv-fb.github.io/nhtsa-stats-US/. The text is in
`website/templates/index.html`; every number is a placeholder that `nhtsa analyze site` fills from
`outputs/tables`, and `tests/test_site.py` fails if the committed page is stale or contains a typed number.
Details and checks: `website/README.md`.

```bash
uv run nhtsa analyze deaths site                    # refresh the tables and re-render the page
python website/tools/sync_public_data.py            # copy the downloadable CSVs into website/data/
node --test website/tests/site.test.mjs             # page structure and script tests
```

## Working with Claude Code

`CLAUDE.md` holds the rules for Claude Code sessions (cheapest sufficient model, data and reporting
conventions, checks before a push): `uv run ruff check src tests app`, `uv run ruff format --check src tests app`,
`uv run pytest -q`.

## Licence

MIT (see `LICENSE`). FARS and CRSS are public NHTSA data products.
