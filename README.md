# What makes US road crashes deadly? FARS and CRSS, 2016–2024

A reproducible Python research system built on the 36 NHTSA archives in `data/raw/`: **FARS**
(census of fatal crashes) and **CRSS** (national probability sample of police-reported crashes).
No other data are used. Every number in `reports/` and on the website is read from an output table
in `outputs/tables/`, each with a provenance sidecar.

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
* Belted drivers and right-front passengers died 65.8% (64.5–67.0%) less often than their unbelted
  companion (`matched/belt_effect`).
* The pooled figure averages different crash types: 50.9% in multi-vehicle angle crashes, 84.4% in
  single-vehicle rollovers (`matched/belt_by_crash_type`).
* It depends on truthful reporting by survivors. Allowing 10% of belted survivors and 5% of
  unbelted-coded deaths to be misrecorded gives 28.2% (26.4–29.9%); the reduction vanishes at
  21.2% survivor misreporting alone and 18.1% with 5% reverse error
  (`matched/belt_misreporting_two_sided_dpc`).
* Exploratory follow-up: within crash configuration, belts are somewhat *less* protective with a
  speeding driver. The ratio of belt risk ratios is 1.10 to 1.24 across four ways of layering crashes
  (lower confidence limits 1.02 or above): 1.24 (1.13–1.35) with single/multi-vehicle and rollover
  crossed (3 of 4 layers pooled), the largest of the four; the crash-type scheme pools only 3 of its 8
  crash types. Pooling crashes first gives 1.01 (0.93–1.09). The alcohol contrast is null, 1.02
  (0.93–1.11) (`restraint_behaviour/dpc_contrast_within_configuration`). The earlier unstratified
  conclusion that the belt effect does not vary with driver speeding does not hold within crash
  configuration.
* Motorcycle helmets: 30.7% (20.6–39.9%) fewer deaths among riders and passengers of the same
  motorcycle, but 455 of 4,735 pairs differ in helmet use, the pair design covers 15.7% of unhelmeted
  deaths, and the effect vanishes at 5.6% survivor misreporting
  (`matched/helmet_misreporting_dpc`, `matched/helmet_pair_coverage`).

**2. Conditional associations in CRSS that survive adjustment** (associations, not effects).
* Exceeding the limit or racing: adjusted fatal risk ratio 5.22 (4.34–6.27) under model A and 4.88
  (4.12–5.79) with crash configuration also held fixed (`severity/speeding_type_models`).
* Motorcycle involvement 8.6 (7.8–9.6); heavy truck or bus 1.91 (1.72–2.13); unlit darkness 1.74
  (1.50–2.00); driver aged 65+ 1.66 (1.51–1.81) (`severity/fatal_crude_vs_adjusted`).
* Alcohol 4.24 (3.58–5.04) with NHTSA's imputation, 5.85 (5.01–6.83) among crashes with known police
  alcohol, 2.79 (2.37–3.29) if unknown is treated as "no" (`measurement/alcohol_coding_sensitivity`).
* Pedestrians struck on 50–55 mph roads against 25 mph or less: 6.58 (4.83–8.96) adjusted, 12.2 without
  adjustment for location, light and time of day (`vulnerable/pedestrian_speed_limit_adjustment`).
* "Too fast for conditions" is a small, imprecise association: 1.06 (0.89–1.26) under model A, which
  excludes only effects beyond about ±22%, and 1.29 (1.13–1.47) under model B. **The split of speeding
  by type is exploratory.**
* Within CRSS alone, limit exceedance is over-represented among fatal crashes 8.60 (7.15–10.34) times,
  against 12.79 (10.39–15.74) for the mixed FARS/CRSS ratio; both intervals reflect CRSS sampling only
  (`speeding/crss_overrepresentation`).
* Interstates are safer than comparable roads on 50–65 mph roads, 0.57 (0.45–0.73), but not at 70+ mph,
  0.94 (0.63–1.38) (`severity/interstate_by_speed_band`). Rain and teenage drivers: see
  `severity/key_contrasts_ab` (models A and B).

**3. Measurement.**
* Killed drivers are tested for alcohol far more often than survivors (67.5% against 25.2%,
  `measurement/alcohol_testing_share`), but police-recorded alcohol, drug and distraction fields are
  more often *unknown* in fatal crashes (alcohol 47.4% against 28.2% for no-injury crashes,
  `measurement/unknown_by_severity`).
* Police reports identify BAC ≥ .08 in 87.1% of tested killed drivers and 98.2% of tested survivors, but
  survivors are tested mainly on suspicion; their sensitivity falls from 99.0% to 97.2% as testing broadens
  (`measurement/police_vs_bac_selection`).
* CRSS alcohol coding broke in 2019; the alcohol association is reported under three codings. Drug and
  distraction fields cannot support severity or trend analysis.

**4. The post-2020 rise.** The fatal share of police-reported crashes rose by a factor of 1.25
(1.14–1.37). The recorded crash mix accounts for 9–34% of it without
crash configuration (model A) and 24–49% with it (model B, where configuration may itself be a mediator),
across four specifications and two reference periods; several of the individual intervals include zero
(`trends/composition_robustness`). "Roughly a quarter to a half" is the model-B range only. The fall in
reported crashes accounts for 53.6% (29.1–78.1%) of the rise in the share, or 46.2% (28.6–63.8%) under
the complete-case outcome (`trends/denominator_share`).

**Also.** Official factor counts overlap and cannot be added: deaths in speeding, drunk-driving,
drug-positive and unbelted categories sum to at least 109% of deaths, and between 64.8% and 95.4% involve
at least one, depending on how undetermined drug status is scored (`contributions/fars_overlap_treatments`).
Drug effects cannot be ranked or estimated. Attributable fractions are model-based, change with the alcohol
coding and model period (`burden/attributable_fraction_variants`), and are not lives saved by any programme.

**Appendix: prediction models** (`docs/model_validation.md`). Boosted trees reach a test AUROC of 0.921
(0.912–0.929) for fatal crashes in 2023–2024, but they are descriptive, not a finding about causes. Police-judged
speeding and imputed alcohol are recorded after the crash; dropping both costs 0.016 AUROC
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

**Runtime.** A clean `nhtsa all` took about 84 minutes on 4 cores when timed before the Phase-2 modules
(`speeding`, `drugs`, `multifactor`, `restraint_behaviour`, `contributions`, `stages`), which add roughly
75 minutes, mostly the speeding lattices; the later modules were not timed separately. Building the datasets
from the archives takes a few minutes. The pipeline is deterministic up to the last digits of multi-threaded
numerical libraries.

## Data

| | FARS | CRSS |
|---|---|---|
| What | Every crash on a public trafficway with a death within 30 days | Probability sample of police-reported crashes, all severities |
| Years | 2016–2024 | 2016–2024 |
| Size | 325,922 fatal crashes, 353,706 deaths | 468,993 sampled crashes (about 5.3–6.8 million a year weighted) |
| Use | Counts and composition of fatal crashes; within-vehicle designs | Denominators, severity rates and models (design-based: 25 strata, 67 PSUs) |

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
