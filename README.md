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
>
> **Phase 2** — how overlapping factors (speeding, alcohol, drugs, restraint) combine and which
> associations survive adjustment and bias analysis: `reports/factor_contributions.md`,
> `reports/speeding_confounding.md`, `reports/alcohol_drugs_restraints.md`,
> `reports/multifactor_interactions.md`, `reports/case_comparisons.md`; plan in
> `docs/research_plan_phase2.md`.

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

A clean `nhtsa all` from the raw archives took 84 minutes on a 4-core machine: about 3
minutes to build the datasets, then the analyses, dominated by the confounding lattices
(34 min), person-level models (12 min), severity and interaction models (9 min each), the
prediction models (8 min) and the within-vehicle bootstraps (7 min). Expect longer when other
processes compete for the cores. The pipeline is deterministic: a clean rebuild reproduces
the processed datasets exactly and the output tables to the last digit or so (multi-threaded
numerical libraries can change the final digits). Individual steps:

| Command | What it does | Output |
|---|---|---|
| `nhtsa ingest` | Validate archives (LFS pointer check, CRC, SHA-256 vs committed pointer) and convert changed ones to typed Parquet (incremental) | `data/interim/` (git-ignored) |
| `nhtsa inventory` | Tables, columns, embedded codebook, availability matrix | `outputs/audit/*.csv` |
| `nhtsa validate` | 841 relational-integrity checks; exits non-zero on structural failure | `outputs/audit/integrity_checks.csv` |
| `nhtsa features` | Harmonised analytic datasets | `data/processed/` (git-ignored) |
| `nhtsa analyze [module …]` | Run analyses (`nhtsa list` shows modules) | `outputs/tables/<module>/`, `outputs/figures/` |
| `nhtsa analyze speeding drugs multifactor restraint_behaviour contributions stages cases` | Phase-2 modules (about 75 minutes on 4 cores; the speeding lattices take most of it) | `outputs/tables/<module>/` |

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
  processing/             harmonised code mappings (+ leakage registry), analytic datasets,
                          driver-level files and person-to-driver links (Phase 2)
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

## Phase 2 findings: overlapping factors

All conditional on a police-reported crash; associations, not effects. Details, intervals and
caveats in the Phase-2 reports (every number there is rendered from `outputs/tables/`).

1. **Official factor counts overlap and cannot be added.** In FARS 2016–2024, deaths in
   speeding-related crashes, crashes with a driver at BAC ≥ .08, crashes with a drug-positive
   driver and unbelted-occupant deaths sum to 109% of all deaths, while 65% of deaths involve any
   of them; about 70% of the deaths counted under each factor also involve another.
2. **Alcohol does not explain away speeding.** Exceeding the limit has a crude fatal risk ratio
   of 10.0; alcohol accounts for about 9% of its log (4–16% depending on the adjustment order),
   and 69% remains after every recorded circumstance. Without alcohol the adjusted risk ratio is
   6.5, *higher* than with alcohol (3.3). Speeding likewise explains little of alcohol's
   association (4%).
3. **The unit matters.** In single-vehicle crashes no departure from multiplicativity is detected
   for one driver's exceedance and alcohol; at crash level the combination is sub-multiplicative,
   possibly because different drivers and crash types are pooled. A struck pedestrian's death is
   much more weakly (and imprecisely) associated with the striking driver's recorded speeding or
   alcohol than an occupant's death, once road speed limit and light are held fixed.
4. **Drugs cannot be ranked.** Drug testing follows survival and suspicion (62% of killed vs 19%
   of surviving drivers), police co-record drugs with alcohol several times more often than
   toxicology finds them together, and the CRSS drug risk ratio ranges from 1.7 to 73 depending
   only on how unknowns are allocated.
5. **Belts act at a different stage.** Within the same vehicle the belt risk ratio (about 0.34)
   does not change with the driver's speeding and is only slightly lower with a drinking driver
   (it does differ between single- and multi-vehicle crashes); across crashes the unbelted risk
   ratio falls from 46 (crude) to 28 (with the driver's own behaviour) and 19 (with crash
   configuration).
6. **No defensible single ranking.** Exceeding the limit ranks first on adjusted risk (P ≈ 0.97);
   alcohol ranks first on deaths involved and attributed burden; predictive importance depends
   on the measure. The
   hypothesised ranking drugs > alcohol > belts > speeding is not supported.
7. **No individual attribution.** The case explorer shows that "shares" of a modelled risk
   change with scale and order and often require combinations that do not exist in the data.

New interface pages: *Factor contributions*, *Multiple-factor explorer*, *Case comparison*.

## What this project cannot tell you

The databases contain no exposure (trips, miles), enforcement, camera, testing-programme or
cost data. Therefore they cannot estimate crash rates per mile or trip, the effect of any
enforcement programme, or lives saved by an intervention. The simulator makes the required
assumptions explicit, computes conditional projections and break-even thresholds, and never
presents them as measured effects. Details: `docs/limitations.md`,
`docs/policy_assumptions.md`.

## Working on this project with Claude Code

`CLAUDE.md` holds the rules for Claude Code sessions in this repository. To save usage,
subagents use the cheapest model that can do the job:

- `haiku`: quick writing and simple checks (the default).
- `sonnet`: all coding, simple or complex, and routine checking.
- `opus`: only the final review before a push.

`CLAUDE.md` also lists the data and reporting conventions and the checks to run before a push.

## Licence

MIT (see `LICENSE`). FARS and CRSS are public NHTSA data products.


## Public research website

The project also includes a polished, responsive **Road Evidence** public website in [website/](website/), built directly from the committed statistical outputs. It complements rather than replaces the nine-page Streamlit research interface.

Features include searchable supported findings, interactive charts with source tables, explanations of overlapping risk factors, a clearly hypothetical policy target calculator, and an in-browser library of eleven full research reports. Public data files are synchronized from canonical outputs; CI rejects stale copies.

Run locally from the repository root: first run `python website/tools/sync_public_data.py --check`, then `python -m http.server 8000 --directory website` and visit http://localhost:8000. Automated smoke tests: `node --test website/tests/site.test.mjs`.

[Website details and deployment instructions](website/README.md). GitHub Pages publishing requires one-time configuration in Repository Settings → Pages → Source: GitHub Actions; do not assume the public URL is live until deployment is confirmed.
