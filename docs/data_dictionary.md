# Data dictionary

Three layers of documentation, from raw to analytic:

| Layer | Where | Content |
|---|---|---|
| Raw value codes | `outputs/audit/codebook.csv` (108k rows) | every code → label pair embedded in the CSVs, per source / year / table / variable, with counts |
| Raw columns | `outputs/audit/column_inventory.csv`, `outputs/audit/variable_availability.csv` | every column per table-year: type, missingness, distinct values, range; presence matrix by source-year |
| Raw tables | this document §1–2 and [`generated/inventory_tables.md`](generated/inventory_tables.md) | purpose, unit, verified key, availability, row counts |
| Harmonised variables | [`variable_harmonization.md`](variable_harmonization.md), [`generated/harmonised_variables.md`](generated/harmonised_variables.md) | definitions, code mappings, breaks, timing class |
| Analytic datasets | [`generated/processed_datasets.md`](generated/processed_datasets.md) | every column of the four processed files with type, missingness and values |

The archives include no manuals. Code meanings are taken from embedded labels; unlabelled
CRSS 2016–2018 and auxiliary files are interpreted only where verified (see
`variable_harmonization.md` §1 and `docs/audit/auxiliary_derived.md`).

## 1. Raw tables (FARS and CRSS share the structure)

Keys were verified empirically (`validation/inventory.py`, `validation/integrity.py`).
FARS case key = (YEAR, `ST_CASE`); CRSS case key = `CASENUM` (unique across years).

| Table | Unit (one row per…) | Key (beyond case) | Years | Content |
|---|---|---|---|---|
| `accident` | crash | — | all | time, location, road class (FARS), light, weather, junction, manner of collision, first harmful event, crash counts; FARS `FATALS`; CRSS design fields, `MAX_SEV`, `ALCOHOL`, `*_IM` |
| `vehicle` | in-transport vehicle | `VEH_NO` | all | body type, model year, VIN-decoded make/model, speeding (`SPEEDREL`), travel speed, roadway at the vehicle (speed limit, surface, alignment, profile, traffic control), pre-crash events, impact, rollover, damage, towing, FARS driver licence and history, CRSS `VEH_ALCH` |
| `person` | person (occupant or non-motorist) | `VEH_NO`, `PER_NO` (`VEH_NO`=0: non-motorist) | all | person type, age, sex, injury severity, seat, restraint, helmet (2019+), air bag, ejection, alcohol/drug reports and tests, striking vehicle, non-motorist location; FARS death timing (post-crash) |
| `parkwork` | parked / working vehicle | `VEH_NO` (shares numbering with `vehicle`) | all | as vehicle, for vehicles not in transport |
| `cevent` | crash event | event number | all | sequence of events in the crash |
| `vevent`, `vsoe` | vehicle event | event sequence | all | per-vehicle event sequence (in-transport **and** parked vehicles) |
| `damage` | damaged area | area code | all | areas of vehicle damage |
| `distract` | driver distraction code | code | all | `MDRDSTRD` (2016–19) → `DRDISTRACT` (2020+) |
| `drimpair` | driver impairment code | code | all | condition at time of crash (asleep, ill, alcohol/drugs…) |
| `factor` | vehicle contributing factor | code | all | `MFACTOR` → `VEHICLECC` (2020) |
| `maneuver` | driver manoeuvre | code | all | `MDRMANAV` → `DRMAN` (2020) |
| `violatn` | violation charged | code | all | `MVIOLATN` → `VIOLATION` (2020); used only in the charge-based QIE sensitivity analysis (`culp_viol`; impairment and outcome-defined charges excluded); the primary culpability definition is action-based (`culp_c1`) |
| `vision` | vision obscured | code | all | `MVISOBSC` → `VISION` (2020) |
| `crashrf`, `driverrf`, `personrf`, `vehiclesf`, `pvehiclesf` | factor rows | code | 2020+ | crash/driver/person/vehicle-related factors (earlier years: `CF1-3` in `accident`, `DR_SF1-4` and `P_SF1-3` columns) |
| `weather` | weather row | code | 2020+ | multiple atmospheric conditions (crash-level `WEATHER` also in `accident`) |
| `nmcrash`, `nmimpair`, `nmprior`, `nmdistract` | non-motorist action / condition | code | all (`nmdistract` 2019+) | non-motorist contributing actions, impairments, prior actions |
| `pbtype` | non-motorist | — | all | pedestrian/bicyclist crash typing |
| `safetyeq` | non-motorist safety equipment | code | all | helmets, lighting, reflective clothing |
| `drugs` | drug test result | specimen, result | FARS 2018+ | toxicology (contains exact duplicate rows — deduplicated before use) |
| `race` | race entry | order | FARS 2019+ | race of persons killed |
| `miacc`, `midrvacc` | crash | — | FARS all | multiply-imputed BAC (10 implicates, hundredths g/dL): highest of all persons / of drivers |
| `miper` | person | `VEH_NO`, `PER_NO` | FARS all | multiply-imputed BAC for every driver and non-motorist |
| `vpicdecode`, `vpictrailerdecode` | vehicle (VIN decode) | `VEH_NO` | all | NHTSA vPIC decode of the VIN (includes parked vehicles) |
| `acc_aux`, `veh_aux`, `per_aux` | crash / vehicle / person | as parent | all | NHTSA-derived `A_*` analytic flags (unlabelled; 1:1 with parent tables, verified) |

Row counts per table and year: [`generated/inventory_tables.md`](generated/inventory_tables.md).

## 2. Design and identification fields (CRSS)

| Field | Meaning (from labels / structure) | Use |
|---|---|---|
| `WEIGHT` | crash sampling weight; constant across a case's vehicle/person rows (verified) | all CRSS estimates |
| `PSUSTRAT` | variance stratum (25), stable 2016–2024 | Taylor linearisation strata |
| `PSU_VAR` | variance PSU (67), nested in strata, stable IDs | clusters |
| `PSU`, `PJ` | sampling PSU and police jurisdiction | not used directly |
| `STRATUM` | crash-type sampling stratum (labelled, e.g. "Stratum 10 - Other") | descriptive only |
| `REGION`, `URBANICITY` | census region; urban/rural area of the PSU | covariates |
| `*_IM` | NHTSA single imputations of selected fields (fill only unknown codes) | primary CRSS severity outcomes (`MAXSEV_IM`, `INJSEV_IM`), alcohol (`ALCHL_IM`) and driver age (`AGE_IM`); see harmonisation |

## 3. Analytic datasets (`data/processed/`, rebuilt by `nhtsa features`)

| File | Unit | Rows | Built from |
|---|---|---|---|
| `crss_crash.parquet` | CRSS crash | 468,993 | accident + vehicle/person/distract aggregates |
| `crss_person.parquet` | CRSS occupant or non-motorist | 1,154,804 | person + own vehicle + crash covariates + partner vehicle |
| `fars_crash.parquet` | FARS fatal crash | 325,922 | accident + aggregates + `midrvacc` |
| `fars_person.parquet` | FARS person | 800,688 | person + own vehicle + `miper` + crash covariates |

Phase-2 driver-level files (`processing/drivers.py`, also rebuilt by `nhtsa features`):

| File | Unit | Rows | Built from |
|---|---|---|---|
| `crss_driver.parquet` | CRSS in-transport vehicle and its driver | 825,957 | vehicle + driver person record + own-vehicle occupant counts + other drivers' behaviour + crash covariates and design |
| `fars_driver.parquet` | FARS in-transport vehicle and its driver | 501,389 | as above + measured BAC, alcohol-test status, 10 MI BAC implicates, drug-test status and class positivity (toxicology), prior convictions |
| `crss_person_link.parquet` | CRSS occupant or non-motorist | 1,154,804 | the vehicle whose driver's behaviour concerns the person: own vehicle (occupants) or striking vehicle `STR_VEH` (non-motorists) |

Column-by-column definitions: [`generated/processed_datasets.md`](generated/processed_datasets.md).

### 3.1 Phase-2 driver-level variables

Every behaviour is the *driver's own*; `drv_*` columns come from the driver's person record.

| Column | Values | Definition |
|---|---|---|
| `own_speeding_type` | no / exceeded_limit_or_racing / too_fast_for_conditions / speeding_unspecified / unknown | the vehicle's `SPEEDREL` (2/3, 4, 5, 0; 8/9 unknown) |
| `own_alcohol_im` (CRSS) | yes / no / unknown | `V_ALCH_IM` (NHTSA imputation) |
| `own_alcohol_police` | yes / no / unknown | CRSS `VEH_ALCH`; FARS driver `DRINKING` |
| `own_drugs_police` | yes / no / unknown | driver `DRUGS` (8/9 unknown) |
| `drv_restraint`, `drv_age_band(_im)`, `drv_sex`, `drv_killed`, `drv_kabco` | | driver's own person fields (CRSS severity imputed) |
| `n_occupants_veh`, `n_killed_veh`, `n_passengers_killed_veh` | counts | occupants (PER_TYP 1, 2, 9) of this vehicle and deaths among them |
| `n_killed_outside_veh` | count | crash deaths minus deaths in this vehicle (other vehicles' occupants, non-motorists) |
| `other_speeding`, `other_alcohol_im` (CRSS), `other_exceeded`, `other_bac08` (FARS) | no_other_vehicle / no / yes / unknown | any *other* in-transport vehicle's driver with the behaviour (tri-state; single-vehicle crashes are `no_other_vehicle`, never "no") |
| `drv_alc_test_status` (FARS) | tested_result / tested_result_unknown / tested_positive_no_value / not_tested / not_reported / unknown_if_tested | from `ALC_RES` (audit §8) |
| `drv_bac08_measured` (FARS) | 1 / 0 / null | `ALC_RES` 80-940 vs 0-79 |
| `drv_p_p08`, `drv_bac08_mi_1..10` (FARS) | share / 0-1 | multiply-imputed driver BAC ≥ .08 (mean over implicates; each implicate) |
| `drv_drug_test_status` (FARS) | tested / not_tested / not_reported / unknown_if_tested | from the deduplicated toxicology results (2018+ `drugs` table; 2016-17 `DRUGRES1-3`), not the specimen code |
| `drv_drug_any` (FARS) | 1 / 0 / null | any psychoactive class (narcotic, depressant, stimulant excl. caffeine/nicotine/cotinine, hallucinogen, cannabinoid, dissociative, inhalant) or "positive, type unknown"; 0 only when tested with a known result and no unspecified "other drug"; null otherwise |
| `drv_drug_<class>` (FARS) | 1 / 0 / null | class positivity (classes comparable only within 2016-2021 and within 2022-2024) |
| `drv_drug_presumptive_only`, `drv_drug_carboxy_thc_only` | 1 / 0 / null | 2023+ positives only through presumptive screens; 2022+ cannabis only as the inactive metabolite |
| `prior_speeding_convictions`, `prior_dwi_convictions` (FARS) | count / null | `PREV_SPD`, `PREV_DWI` (0-97) |
Crash-level "any X" flags use a tri-state rule: 1 if any unit has X, 0 if all units are known
not to, null otherwise. For body-type flags a vehicle of unknown body type (98/99, and the
"unknown light-vehicle type" / "unknown truck type" codes where they cannot rule the category
out) makes the flag unknown unless another vehicle confirms it.

The person files cover slightly different populations: `fars_person` keeps occupants of parked
or working vehicles (`PER_TYP` 3, about 350–480 a year, 42–67 killed) with empty vehicle
fields and role `parked_vehicle_occupant`; `crss_person` excludes them. Analyses select by
person type and role, so no estimate is affected, but raw person counts differ for this reason.
