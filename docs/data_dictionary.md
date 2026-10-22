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
| `violatn` | violation charged | code | all | `MVIOLATN` → `VIOLATION` (2020); basis of the QIE culpability definition |
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

Column-by-column definitions: [`generated/processed_datasets.md`](generated/processed_datasets.md).
Crash-level "any X" flags use a tri-state rule: 1 if any unit has X, 0 if all units are known
not to, null otherwise. For body-type flags a vehicle of unknown body type (98/99, and the
"unknown light-vehicle type" / "unknown truck type" codes where they cannot rule the category
out) makes the flag unknown unless another vehicle confirms it.

The person files cover slightly different populations: `fars_person` keeps occupants of parked
or working vehicles (`PER_TYP` 3, about 350–480 a year, 42–67 killed) with empty vehicle
fields and role `parked_vehicle_occupant`; `crss_person` excludes them. Analyses select by
person type and role, so no estimate is affected, but raw person counts differ for this reason.
