# What makes US road crashes deadly? — FARS & CRSS 2016–2024

A reproducible Python research system that uses the 36 NHTSA archives in `data/raw/` —
**FARS** (census of fatal crashes) and **CRSS** (national probability sample of
police-reported crashes) for 2016–2024 — to study:

* which circumstances are associated with a reported crash being fatal or serious, before and
  after accounting for other circumstances;
* which circumstances *combine* to produce disproportionately severe outcomes (additive and
  multiplicative interaction, with co-occurrence kept separate);
* how far behavioural associations can be trusted, given that police record speeding,
  alcohol, drugs and restraint use differently depending on how severe a crash was;
* who dies given involvement (person-level and within-vehicle matched designs), and which
  driver groups are over-involved in crashes (quasi-induced exposure);
* what can — and cannot — be inferred about interventions such as speed cameras or roadside
  alcohol/drug testing, through an evidence ledger and a transparent, assumption-driven
  policy simulator with cost-effectiveness and break-even tools.

No external data are used. Every empirical number traces to the raw archives through code in
`src/nhtsa_stats` and an output table with a provenance sidecar. Hypothetical policy outputs
are always labelled as such.

> **Start here:** `reports/findings.md` (main results) · `docs/limitations.md` (what the data
> cannot answer) · `docs/research_plan.md` (questions and design).

## Quick start

Requirements: Python ≥ 3.11, [uv](https://docs.astral.sh/uv/), Git LFS (the archives are
LFS objects).

```bash
git lfs pull                      # fetch the 36 archives (~675 MB)
uv sync --extra app               # create the environment from uv.lock
uv run nhtsa all                  # validate → cache → inventory → integrity → datasets → analyses
uv run pytest                     # unit + data-integrity tests
uv run streamlit run app/streamlit_app.py   # research interface
```

`nhtsa all` takes roughly 30–60 minutes on a laptop (most of it survey-weighted model
fitting). Individual steps:

| Command | What it does | Output |
|---|---|---|
| `nhtsa ingest` | Validate archives (LFS pointer check, CRC, SHA-256 vs committed pointer) and convert changed ones to typed Parquet (incremental) | `data/interim/` (git-ignored) |
| `nhtsa inventory` | Tables, columns, embedded codebook, availability matrix | `outputs/audit/*.csv` |
| `nhtsa validate` | 841 relational-integrity checks; exits non-zero on structural failure | `outputs/audit/integrity_checks.csv` |
| `nhtsa features` | Harmonised analytic datasets | `data/processed/` (git-ignored) |
| `nhtsa analyze [module …]` | Run analyses (`nhtsa list` shows modules) | `outputs/tables/<module>/`, `outputs/figures/` |

Changing one analysis only requires `nhtsa analyze <module>`; the cache and datasets are
reused.

## Data

| | FARS | CRSS |
|---|---|---|
| What | Every crash on a public trafficway with a death within 30 days | Probability sample of police-reported crashes, all severities |
| Years | 2016–2024 (main + auxiliary archives) | 2016–2024 (main + auxiliary archives) |
| Crashes | 325,922 fatal crashes, 353,706 deaths | 468,993 sampled crashes (~5.3–6.8 million/yr weighted) |
| Use | Observed counts and composition of fatal crashes; within-vehicle designs | Denominators, severity rates and models (design-based: 25 strata, 67 PSUs) |

The archives contain no PDF manuals; variable meanings come from the value labels embedded
in the CSVs (harvested into `outputs/audit/codebook.csv`) and, where labels are absent (CRSS
2016–2018, all auxiliary files), from verified cross-tabulation against labelled fields. See
`docs/data_audit.md`, `docs/data_dictionary.md`, `docs/variable_harmonization.md` and the
domain appendices in `docs/audit/`.

## Repository layout

```
data/raw/                 36 original ZIP archives (Git LFS, unchanged)
src/nhtsa_stats/
  ingestion/              archive discovery, validation, CSV reading, Parquet cache
  validation/             inventory and relational-integrity checks
  processing/             harmonised code mappings (+ leakage registry) and analytic datasets
  analysis/               survey inference core and the research modules
  models/                 severity-prediction pipeline (temporal validation)
  simulation/             evidence ledger, intervention simulator, cost model
  reporting/              provenance-stamped outputs, generated documentation
app/                      Streamlit research interface
docs/                     plan, audit, dictionary, harmonisation, methodology, limitations,
                          model validation, policy assumptions (+ docs/audit/, docs/generated/)
reports/                  findings, interactions, policy analysis
outputs/                  generated tables/figures (small, committed) and audit inventory
tests/                    unit tests (synthetic fixtures) and data tests (real cache)
```

## Findings

Full report with sources, intervals and caveats: `reports/findings.md` (interactive version in
the app). In brief — all conditional on a police-reported crash, and associations, not effects:

1. **Frequency is not danger.** Pedestrian crashes are about 1% of police-reported crashes but
   about 19% of fatal ones; rain, wet roads, intersections and teenage drivers are common in
   crashes but under-represented among fatal ones.
2. **Adjustment changes the picture.** Much of the night-time excess is accounted for by
   darkness, alcohol, road type and crash configuration; rain-crashes are no less severe than
   others on the same road surface; interstates are safer than other roads with the same speed
   limit; crashes involving drivers aged 65+ are more severe once their low-risk settings are
   held constant.
3. **"Speeding" is two things.** Exceeding the limit is associated with about five times the
   fatal risk; "too fast for conditions", the larger category, shows little or no excess.
4. **The most robust associations involve objective circumstances**: motorcycles, pedestrians,
   the speed environment, unlit darkness and heavy trucks; alcohol under every coding.
5. **Some combinations amplify each other**, notably pedestrians in unlit darkness; others
   often assumed to (speeding in darkness, young drivers at night) are not detected for the
   fatal outcome.
6. **Involvement is not severity.** Teenage drivers are over-represented as the culpable party
   in two-vehicle crashes, but their crashes are less severe.
7. **Belts.** Within the same vehicle in fatal crashes, belted front-seat occupants died about
   two-thirds less often than unbelted ones; the size of that estimate depends strongly on how
   truthfully surviving occupants report belt use.
8. **The post-2020 rise** in the fatal share of crashes is only partly (roughly 30–50%)
   accounted for by the recorded crash mix; about half of the rise in the share reflects fewer
   reported non-fatal crashes.
9. **Measurement.** Police-recorded behaviours are recorded more completely in severe crashes;
   drug and distraction fields cannot support severity or trend analysis.
10. **Interventions.** The data identify no intervention effect; the policy tools show where
    deaths concentrate and what an intervention would have to achieve, under stated
    assumptions (`reports/policy_analysis.md`).

## What this project cannot tell you

The databases contain no exposure (trips, miles), enforcement, camera, testing-programme or
cost data. Therefore they cannot estimate crash rates per mile or trip, the effect of any
enforcement programme, or lives saved by an intervention. The simulator makes the required
assumptions explicit, computes conditional projections and break-even thresholds, and never
presents them as measured effects. Details: `docs/limitations.md`,
`docs/policy_assumptions.md`.

## Licence

MIT (see `LICENSE`). FARS and CRSS are public NHTSA data products.
