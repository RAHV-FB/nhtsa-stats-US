# Data audit

Audit of the 36 NHTSA archives in `data/raw/` before any substantive modelling. Numeric
tables are generated from code ([`generated/inventory_tables.md`](generated/inventory_tables.md));
domain-by-domain evidence is in the appendices under [`audit/`](audit/):

| Appendix | Scope |
|---|---|
| [`audit/crash_environment.md`](audit/crash_environment.md) | time, light, weather, rural/urban, road class, junction, work zone, manner of collision, harmful events, crash counts, crash-related factors |
| [`audit/vehicle_roadway.md`](audit/vehicle_roadway.md) | body type, model year, roadway at the vehicle, travel speed, pre-crash events, impact, post-crash vehicle outcomes, VIN decode |
| [`audit/person_injury_restraint.md`](audit/person_injury_restraint.md) | person type, age, sex, KABCO, seat, restraint, helmet, air bag, ejection, death timing, non-motorist location |
| [`audit/alcohol_drugs.md`](audit/alcohol_drugs.md) | police-reported alcohol/drugs, test status and results, multiply-imputed BAC, toxicology |
| [`audit/driver_behaviour_factors.md`](audit/driver_behaviour_factors.md) | speeding, distraction, impairment, violations, driver factors, licence history, culpability |
| [`audit/auxiliary_derived.md`](audit/auxiliary_derived.md) | the unlabelled `A_*` derived variables, reconstructed by cross-tabulation |
| [`audit/crss_survey_design.md`](audit/crss_survey_design.md) | CRSS strata, PSUs, weights, design effects, imputation, FARS–CRSS comparability |

## 1. Repository and archive inventory

* Initial state: two commits (initial commit; data upload), a licence, `.gitattributes`
  routing `*.zip` through Git LFS, and 36 archives as LFS pointers. No code, documentation or
  environment existed. `git lfs pull` retrieved 675 MB.
* **Integrity**: every archive's SHA-256 equals the OID in its committed LFS pointer; every
  ZIP member passes its CRC check (`ingestion/archives.py`, `outputs/audit/archive_inventory.csv`).
* **Classification**: 9 years × {FARS, CRSS} × {main, auxiliary}. One upstream naming quirk
  (`CRSS2019AuxiliaryCVS.zip`) is handled by the name parser.
* **Contents**: 544 CSV tables in total. FARS main archives contain 24 tables (2016–17), 25
  (2018, `drugs` added), 27 (2019, `race`, `nmdistract`) and 33 (2020+, factor tables and
  `weather`); CRSS 21 → 22 (2019) → 28 (2020+). Member names vary in case and directory prefix
  between years; CRSS 2019 calls the crash-event table `cevents`. 35 of 544 files are
  Windows-1252 encoded, the rest UTF-8 (with BOM).
* **No documentation files** (manuals, PDFs, codebooks) are included. Value labels embedded
  in the CSVs as `<VAR>NAME` columns are the in-archive documentation; they are absent from
  CRSS 2016–2018 and from every auxiliary table.

Machine-readable outputs: `outputs/audit/{archive,table,column}_inventory.csv`,
`codebook.csv` (every code-label pair with counts), `variable_availability.csv`
(variable × source-year matrix), `integrity_checks.csv`.

## 2. Volumes

| | FARS | CRSS (sample) |
|---|---|---|
| Crashes | 325,922 (33,487–39,785 per year) | 468,993 (46,511–54,969 per year) |
| Vehicles in transport | 501,389 | 825,957 |
| Persons | 800,688 | 1,158,730 (1,154,804 occupants of in-transport vehicles and non-motorists in the analytic file) |
| Deaths | 353,706 (36,355 in 2019 → 43,230 in 2021 → 39,254 in 2024) | — |
| Weighted crashes | — | 5.25 million (2020) – 6.82 million (2016) per year |

## 3. Relational integrity

Keys were derived from the data, not assumed: for every table the shortest unique key was
found (crash; + vehicle; + person; + coded value or sequence for multi-row tables). All 841
checks across 18 source-years pass (`validation/integrity.py`):

* primary keys unique in `accident`, `vehicle`, `person` and the auxiliary tables;
* every child record has its parent (crash, vehicle, person) — **with one structural rule**:
  `vevent`, `vsoe` and `vpicdecode` also describe parked/working vehicles, whose `VEH_NO`
  shares the numbering of in-transport vehicles; every such "orphan" is a `parkwork` vehicle
  (verified), so these tables are filtered to in-transport vehicles before vehicle joins;
* auxiliary tables are exactly 1:1 with their parents;
* joining persons to vehicles to crashes never changes the person count (no inflation);
* crash-level counts reconcile exactly with child records: `VE_FORMS`, `VE_TOTAL`
  (+ parked), `PERMVIT`, FARS `FATALS` = persons with `INJ_SEV` = 4 in **all** 325,922 crashes,
  vehicle `DEATHS` = killed occupants; CRSS `MAX_SEV` = most severe known person KABCO;
* CRSS design fields (`WEIGHT`, `PSU`, `PSU_VAR`, `PSUSTRAT`, `STRATUM`) are identical
  across a case's crash, vehicle and person rows; all weights are positive.

The only data defect found: FARS `drugs` contains exact duplicate rows (193–2,888 per year,
2018–2024), removed before use.

## 4. Year-to-year comparability

Code sets of unlabelled CRSS 2016–2018 match labelled years for every analytic variable;
distributions are stable (total-variation distance ≤ 2.4 pp) except where a documented
reporting break occurs. The breaks that matter for this project:

| Break | Effect | Handling |
|---|---|---|
| CRSS alcohol (2019) | "unknown" 12–14% → 32–40% of crashes; unknown is outcome-dependent | imputed `ALCHL_IM` for adjustment; sensitivity by coding and period |
| CRSS drugs (2019–2020), distraction (2017–2020) | unknown shares rise to 50–74% | descriptive only |
| CRSS junction (2017–2021; worst 2019) | 28% of 2019 crashes not reported | coarse groups, unknown level, no CRSS junction trends |
| Restraint (2017 merge; 2019 helmet move) | code 20 means "none or not applicable" | restraint defined only for belted seats |
| Body type (2017 pickups; 2017 scooters) | code merges/splits | grouping |
| Rollover / damage / towing (2022) | recodes | post-crash, not modelled |
| FARS 2024 toxicology | ~26% of killed drivers' test status not reported | 2024 alcohol figures flagged |

Full catalogue: [`variable_harmonization.md`](variable_harmonization.md) §3.

## 5. Missing and unreliable information

* **Differential missingness by severity** is the rule for behavioural fields. CRSS alcohol
  is "unknown" in 28% of no-injury crashes but 47% of fatal crashes; restraint is unknown for
  ~5% of uninjured but ~10% of killed occupants; FARS time, light and weather are less often
  known for fatal crashes found after the fact (single-vehicle, rural, night).
* **Testing is selective**: 59–74% of killed drivers are alcohol-tested vs 21–29% of
  survivors; survivors are tested on suspicion (71.5% tested when police report drinking vs
  21.9% otherwise). Drug-test rates vary by state from 9% to 93%.
* **Police reports vs measurement**: among tested FARS drivers, police-reported drinking
  detects BAC ≥ .08 in 87% (killed) and 98% (survived) of cases where the report is known;
  counting unknown as "no", only 63% of killed drivers' high BACs are reported.
* **State-dependent missingness** in FARS: weather "not reported" 84–90% in Virginia,
  58–70% in Kansas; road owner, route and traffic-control fields vary by state.
* **Unknown crash severity** (CRSS MAX_SEV 9, ~1.5–1.9%) marks poorly documented reports with
  5–50 times the unknown rate of other fields.

Consequences are quantified in `outputs/tables/measurement/` and summarised in
[`limitations.md`](limitations.md).

## 6. FARS and CRSS: sampling frames and the no-pooling rule

FARS is a census of fatal crashes; CRSS is a probability sample of police-reported crashes
(including fatal ones). The CRSS weights are calibrated to FARS through NHTSA's imputed
maximum severity: weighted `MAXSEV_IM` = 4 crashes equal the FARS count exactly in 2016 and
2024 and within 0.9% in every other year. The unimputed `MAX_SEV`, which ignores persons of
unknown severity, falls 0.6–12.8% short by year — the reason CRSS outcomes use the imputed
severity (research plan v1.2). The two systems still record some attributes differently for
the same fatal crashes (§4 of `variable_harmonization.md`). Therefore:

* **counts of fatal crashes and deaths come from FARS only**;
* **severity rates and models come from CRSS only**, with design-based inference
  (25 variance strata `PSUSTRAT`, 67 variance PSUs `PSU_VAR`, stable IDs 2016–2024, at least two
  PSUs per stratum, 42 design degrees of freedom);
* rows are never concatenated across systems; cross-system quantities (over-representation
  ratios, FARS-scaled burden) are ratios of separately estimated quantities and are labelled.

Details of the design analysis, including design effects and imputation, are in
[`audit/crss_survey_design.md`](audit/crss_survey_design.md).

Key design facts verified there: `PSU_VAR` is nested in `PSUSTRAT` in every year, keeps its
stratum across years and leaves no stratum with a single PSU (the sampling `PSU` would, in
stratum 20); 2016 has 54 variance PSUs, 2017 and 2022 have 66, other years 67. Pooled
analyses must use the shared `PSU_VAR` identifiers — year-specific clusters understate the
SE of pooled proportions by a factor of about 2. `STRATUM` (crash-type sampling strata) must
not be used as a variance stratum. Design effects under the correct design are 1.1–2.2 for
the fatal share, 3.4–11.5 for KA and 105–175 for the rural-PSU share.

## 7. Completeness review of the audit

An independent critic checked the seven domain appendices against the full column
inventory ([`audit/completeness_critique.md`](audit/completeness_critique.md)). It covered
the twelve tables no appendix had discussed (`pbtype`, `nmcrash`, `nmprior`, `nmdistract`,
`safetyeq`, `cevent`, `vevent`, `vsoe`, `damage`, `vehiclesf`, `pvehiclesf`,
`vpictrailerdecode`), the FARS EMS times and coordinates, resolved nine contradictions
between appendices with code and recomputed 19 numeric claims (18 reproduced; the vPIC
decode coverage was overstated by ~2.5 points because parked vehicles' decode rows were
counted). Rules adopted from it:

* differential missingness by severity is computed on the *recorded* severity, with unknown
  severity as its own stratum — stratifying by imputed severity moves crashes of unknown
  severity, which have the most unknown fields, into the KABCO cells;
* for CRSS 2016–2018 (no labels) same-year FARS labels are used first; overlapping code sets
  alone do not prove an unchanged meaning (e.g. `REST_MIS` code 0 changed meaning in 2019);
* non-motorist contributing circumstances (`nmcrash`) are recorded far more often for the
  dead and have national coding steps in 2018–2019, so they are not used; FARS EMS times
  are missing for more than half of crashes and almost entirely for several states, so no
  EMS analysis is attempted;
* travel speed (`TRAV_SP`) is missing for more than half of drivers and more often in severe
  crashes, so it is not used.
