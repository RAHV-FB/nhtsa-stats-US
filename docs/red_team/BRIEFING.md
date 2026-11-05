# Red-team briefing — read all of this before you start

`$RT` below means `/tmp/claude-0/-home-user-nhtsa-stats-US/1c16118e-b425-5b4c-9882-66195720c5ff/scratchpad/red_team`.
The repository is `/home/user/nhtsa-stats-US` (run everything from there).

## Your role

You are one of about 33 independent red-team reviewers attacking a published research project on
US road deaths built only from NHTSA's FARS (census of fatal crashes) and CRSS (probability sample
of police-reported crashes), 2016–2024. Each reviewer has one target: a single published finding,
or one cross-cutting dimension (leakage, bias, uncertainty, model assumptions, significance,
reproducibility). You work alone and never see the other reviewers' work.

Try hard to show that your target is wrong, overstated, fragile, or irreproducible. Report
honestly when it survives: a failed attack is a valid and valuable result. Don't invent
objections. Every objection needs a concrete failure scenario and evidence.

## Project map

* `README.md`, `CLAUDE.md`: overview and conventions.
* Code: `src/nhtsa_stats/` (`analysis/`, `models/severity_ml.py`, `processing/` (harmonisation,
  leakage registry, analytic datasets, driver linkage), `simulation/`, `reporting/`).
* Reports: `reports/*.md` are rendered from `reports/templates/*.md`. Every number is a
  placeholder looked up in `outputs/tables/`. Public website: `website/templates/index.html`,
  rendered to `website/index.html` from the same tables. Don't fetch the live site.
* Tables: `outputs/tables/<module>/<name>.csv`, each with a `.json` provenance sidecar.
* Documented caveats: `docs/limitations.md`, plus the caveat paragraphs in each report. Method:
  `docs/methodology.md`. Design and pre-registration: `docs/research_plan.md` (RQ1–RQ10, with a
  change log) and `docs/research_plan_phase2.md`. ML: `docs/model_validation.md`. Domain audits:
  `docs/audit/*.md`. Previous audit: `docs/audit_2026-11.md`.
* Register of the published findings with their IDs and sources: `$RT/FINDINGS_REGISTER.md`.

## Data (already built; never rebuild, never modify)

* `data/raw/*.zip`: the 36 original NHTSA archives.
* `data/interim/{FARS,CRSS}/<table>/<year>.parquet`: a typed copy of every raw CSV table
  (accident, vehicle, person, the multi-row tables, the auxiliary `*_aux` tables, FARS `miacc`,
  `midrvacc`, `miper` multiple-imputation BAC, `drugs`, and so on). Raw variable names are kept.
* `data/processed/`: harmonised analytic datasets.

  | File | Rows × columns |
  |---|---|
  | `crss_crash` | 468,993 × 87 |
  | `crss_person` | 1,154,804 × 83 |
  | `crss_driver` | 825,957 × 75 |
  | `crss_person_link` | person-to-driver links |
  | `fars_crash` | 325,922 × 69 |
  | `fars_person` | 800,688 × 70 |
  | `fars_driver` | 501,389 × 86 |

* `outputs/cache/` does not exist, so the confounding/speeding lattice caches and fitted ML
  models are absent. Don't recompute full lattices or the full ML pipeline.

### Useful entry points

The project's own code, importable when you run through `rt_py`:

```python
from nhtsa_stats.analysis import data, severity, specs, survey
# CRSS crashes, outcome 'fatal' | 'ka' | 'fatal_cc' | 'ka_cc'; returns the survey design
df, design = severity.load("fatal")
# model A (pre-crash set), about 5 s; model B adds specs.CIRCUMSTANCE
m = severity.fit(df, design, "fatal", specs.PRE_CRASH)
lv = severity.observed_levels(df, "light", specs.CRASH_LEVELS["light"])
# standardised margins and RRs, about 2 s
tab = severity.factor_contrasts(m, df, "light", lv)
```

For example, this reproduces the published dark-unlit RR of 1.74 (1.50–2.00). `survey.py` has
`SurveyDesign` (`WEIGHT`, `PSUSTRAT`, `PSU_VAR`, 42 df), `svy_total`, `svy_mean`,
`proportion_table`, `SurveyLogit(...).margins(...)` returning a `MarginSet`
(`.estimate`, `.log_ratio`, `.difference`) and `interaction_contrasts`. FARS loaders:
`data.fars_crash()`, `data.fars_person()`. Each module's `run()` writes into `outputs/`, so never
call `run()` or `nhtsa analyze` unless `NHTSA_OUTPUT_DIR` points into `$RT/work/<ID>/`.

## Hard rules

1. **The repository is read-only for you.** Write only to:
   * your script directory `scripts/audit/red_team/<ID>/`;
   * your scratch directory `$RT/work/<ID>/`;
   * your report `$RT/reports/<ID>.md`.

   Never modify `src/`, `tests/`, `reports/`, `docs/`, `outputs/`, `data/`, `website/`, `app/`,
   `README.md` or any other file. Run no git command that changes state (`add`, `commit`,
   `checkout`, `stash`, `reset`, `clean`). `git log`, `git show` and `git diff` are fine.
2. **All compute goes through the throttle.** Every Python process that loads `data/processed`
   or `data/interim` runs as:

   ```bash
   $RT/bin/rt_py scripts/audit/red_team/<ID>/NN_name.py
   ```

   Give that Bash call `timeout: 600000`. The machine has 4 cores shared by all reviewers;
   `rt_py` admits 4 single-threaded jobs at a time, caps memory and stops a job after 420 s.
   * Exit code 75 means no slot came free: wait about 30 s and retry.
   * Exit code 124 means the job timed out: split it or subsample.
   * Never bypass `rt_py` for data work. Never use multiprocessing or `n_jobs > 1`. Never run
     `nhtsa all`, full lattices, the full ML pipeline, or bootstraps above 200 replicates or
     5 minutes.
   * Reading the small committed CSV/JSON files in `outputs/tables/` with a quick
     `.venv/bin/python -c ...` is fine without `rt_py`.
3. **No network.**
4. **Never fabricate numbers.** Every number in your report must be one of:
   * printed by a script you ran (cite the script path);
   * read from a committed file (cite the table and row/column, or the report section).

   Outside knowledge (literature, NHTSA practice) may motivate an attack, but it is not evidence
   from these data. Label it as outside knowledge.
5. **Scripts** are self-contained and run from the repository root. Each prints its results and
   may also write CSVs to `$RT/work/<ID>/`. Name them `01_….py`, `02_….py`, and so on. Start
   each with a short docstring: which claim it tests, how, and what to look at in the output.
6. **Don't re-verify committed tables against a rerun of the project's own code** (the
   previous audit did that: all 156 tables were identical). The reproducibility reviewer is the
   exception. Do reproduce your target's headline number(s) first, by your own computation or by
   reading the code, so you know exactly which estimand you are attacking. Spend the rest of
   your effort on attacks.

## Attack checklist (apply what is relevant)

* **Data leakage.** Information that is post-crash, outcome-dependent, or from the test period
  entering as an input, a stratifier, a weight or an imputation. Examples: fields coded after or
  because of the outcome, imputations that use severity, weights calibrated on the outcome,
  train/test contamination.
* **Biases.**
  * Selection: the frame is police-reported crashes; FARS is fatal crashes only (a collider).
  * Measurement: misclassification that differs by severity, testing or ascertainment selection,
    survivor self-report.
  * Missing data: unknown codes, imputation, complete-case choices.
  * Other: coding breaks across years, Simpson's paradox, ecological fallacy, definitional
    choices.
* **Uncertainty.** Are the intervals correct (design-based variance, df, clusters, imputation
  variance, bootstrap unit)? Which variance components are missing? Small cells? Many analysis
  choices?
* **Model assumptions.** Specification (link, main effects, categorisation), positivity,
  mutual adjustment (the "Table 2 fallacy"), mediators vs confounders, collapsibility, the
  standardisation population, matched-design assumptions, the reference in a decomposition.
* **Statistical significance.** "No effect", "no interaction" or "unchanged" claims drawn from
  non-significance (was equivalence shown? what was the power?). Multiplicity. Forking paths and
  exploratory results presented as confirmatory. "Intervals overlap" reasoning. Implied tests that
  were never run.
* **Reproducibility.** Can the number be regenerated? Does the report or site text say what the
  table says? Are there manual steps? Is the result sensitive to seeds, thresholds or
  definitions?
* **Alternative explanations.** Would a reasonable alternative definition, population, period,
  outcome or adjustment set reverse the claim or change it materially?

Try at least 5 distinct attacks, at least 3 of them empirical (run on the data).

## Verdict scale

* **REFUTED**: the claim, as published, is false or not supported by the data.
* **WEAKENED**: the direction stands, but the published magnitude, certainty, generality or
  wording is materially overstated, or a material caveat is missing from both the report and
  `docs/limitations.md`.
* **SURVIVES**: serious attacks were tried and failed; at most minor wording issues remain.
* **NOT TESTABLE**: these data cannot decide it (say what would be needed).

Give a confidence (high, medium or low) for your verdict.

## Report format

Your final message is the report: at most about 1,000 words plus tables. Also save it to
`$RT/reports/<ID>.md`.

1. **Target**: the claim, quoted, with its source (file and section, table).
2. **Reproduction**: did you reproduce the headline numbers? Give values and the script.
3. **Attacks**: a table with columns # | dimension | hypothesis | test (script) | result
   (numbers) | damage (none / minor / material / fatal) | already disclosed? (where).
4. **Verdict and confidence**, then one paragraph on the single most damaging issue.
5. **Recommended correction**, if any: wording, caveat or analysis.
6. **Scripts**: list them with a one-line description each.
