# Audit appendix: person-level injury, restraint and demographic variables (FARS and CRSS, 2016-2024)

Scope: the person tables of FARS and CRSS (`person`), the FARS `race` table, and the `per_aux` derived restraint, injury
and person-type fields, which are used only as a cross-check. Years 2016-2024. Status: audit only. No data or source
code was modified. Every number below was computed from the typed Parquet cache
(`data/interim/{FARS|CRSS}/{table}/{year}.parquet`) or from `outputs/audit/codebook.csv`. The scripts are listed in §9.

---

## 1. Purpose and scope

This appendix records, for every person-level variable likely to enter a severity analysis (outcome, exposure or
covariate):

* where the variable is available (source × year);
* what each code means, and the evidence for that meaning;
* coding and definition breaks between years;
* which codes are missing or uninformative, how often they occur by year, and **whether that rate depends on injury
  severity**;
* a reliability verdict and an implementable harmonised definition;
* a timing class for leakage control: **PRE-CRASH**, **CRASH-CIRCUMSTANCE**, or **POST-CRASH / OUTCOME-DERIVED**.

Alcohol and drug test result fields in the person table (ALC_*, DRUG*, ATST_TYP, PERALCH_IM) belong to the behaviour
domain and are covered here only where they matter for this domain (DSTATUS, §4.16). The vehicle-descriptor copies in
the person table (MAKE, BODY_TYP, MOD_YEAR, ROLLOVER, IMPACT1, etc.) belong to the vehicle audit. BODY_TYP is used here
only to define vehicle classes (§2.3).

### 1.1 Evidence conventions

* **L (label):** the code→label pair appears in `codebook.csv` for that source-year. Labels were compared after
  normalisation (lower case, alphanumerics only). Every normalised difference is reported and judged *cosmetic* or
  *meaning-changing*. `codebook.csv` lists **only codes that occur in the data**. "Code absent in year y" therefore
  means "not used in y", not necessarily "not defined in y".
* **D (distribution):** the share of each code per source-year. Year-to-year change is the total variation distance
  (TVD), in percentage points (pp).
* **X (cross-tab):** the meaning is confirmed by cross-tabulation against an independently labelled variable, for
  example REST_USE × BODY_TYP, DSTATUS × DRUGTST1, or INJ_SEV × accident.FATALS.
* **UNVERIFIED:** the meaning rests only on general familiarity with NHTSA conventions and could not be confirmed
  from the data.
* FARS percentages are row shares (FARS is a census). CRSS percentages are **weighted by `WEIGHT`** unless marked
  "unw."; unweighted n is given where it matters.

---

## 2. Tables, keys and structure

### 2.1 Tables and row counts

| table | key | FARS rows/yr 2016…2024 | CRSS rows/yr 2016…2024 | labels |
|---|---|---|---|---|
| person | case + VEH_NO + PER_NO | 86,474 / 85,840 / 84,344 / 82,843 / 86,396 / 97,511 / 96,186 / 92,768 / 88,326 | 117,759 / 138,913 / 120,230 / 135,410 / 131,962 / 133,734 / 132,175 / 122,388 / 126,159 | FARS all years; CRSS 2019+ only |
| race (FARS) | + RACE (1..n rows per person) | 2019: 82,993 … 2024: 88,517 | – | 2019+ (ORDER/MULTRACE labelled only 2020+) |
| per_aux | as person | = person | = person | none |

* The key (case, VEH_NO, PER_NO) is unique in every source-year (`table_inventory.csv`). per_aux joins 1:1 to person,
  with a 100.0% match rate in both sources.
* Column counts change: FARS person has 129 columns (2016-17), 118 (2018; DRUGTST/DRUGRES dropped), 119 (2019; RACE
  moved out, HELM_USE/HELM_MIS added) and 126 (2020-24). In 2020 vPIC/GVWR/ICFINALBODY were added and P_SF1-3 dropped.
  From 2022 DEVTYPE/DEVMOTOR were added and ALC_DET/DRUG_DET dropped. CRSS person has 61 columns (2016-17), 54 (2018;
  DSTATUS and DRUGTST/DRUGRES dropped), 102 (2019; labels added), 108 (2020-21) and 112 (2022+).

### 2.2 Occupant / non-occupant structure (VEH_NO = 0)

PER_TYP × (VEH_NO = 0), pooled 2016-2024 (L for PER_TYP labels):

| PER_TYP | label | FARS VEH_NO=0 | FARS VEH_NO>0 | CRSS VEH_NO=0 | CRSS VEH_NO>0 |
|---|---|---|---|---|---|
| 1 | Driver of a MV in-transport | 0 | 497,955 | 0 | 824,055 |
| 2 | Passenger of a MV in-transport | 0 | 221,721 | 0 | 286,602 |
| 9 | Unknown occupant type in a MV in-transport | 0 | 907 | 0 | 216 |
| 3 | Occupant of a MV not in-transport | 0 | 3,590 | 0 | 3,926 |
| 4 | Occupant of a non-motor-vehicle transport device | 537 | 0 | 135 | 0 |
| 5 | Pedestrian | 64,710 | 0 | 24,966 | 0 |
| 6 | Bicyclist | 8,907 | 0 | 16,310 | 0 |
| 7 | Other cyclist / other pedalcyclist | 100 | 0 | 80 | 0 |
| 8, 11, 12, 13 | Personal conveyance (see §4.1) | 1,932 | 0 | 2,317 | 0 |
| 10 | Person in/on a building | 323 | 0 | 115 | 0 |
| 19 | Unknown type of non-motorist | 6 | 0 | 8 | 0 |

Verified structural rules (0 violations in every source-year, 2016-2024; script `04_structure.py`):

* VEH_NO = 0 ⇔ PER_TYP ∈ {4, 5, 6, 7, 8, 10, 11, 12, 13, 19}.
* VEH_NO = 0 ⇔ SEAT_POS = 0 ⇔ REST_USE = 96 ⇔ AIR_BAG = 97 ⇔ REST_MIS = 8 ⇔ (2019+) HELM_USE = 96. Also
  VEH_NO > 0 ⇔ LOCATION = 0. All non-motorists have EJECTION = 8.
* Every occupant row with PER_TYP 1, 2 or 9 matches a `vehicle` row (in-transport). Every PER_TYP 3 row matches a
  `parkwork` row and none matches `vehicle`. **PER_TYP 3 persons have VEH_NO > 0 but their vehicle is in `parkwork`.**
* Non-motorists: STR_VEH > 0 and matches an in-transport `vehicle` row in 100% of rows, every year. Occupants:
  STR_VEH = 0 in 100% of rows.
* FARS accident.PERMVIT = count(PER_TYP ∈ {1, 2, 9}) and PERNOTMVIT = count(VEH_NO = 0) + count(PER_TYP = 3). Both
  hold with 0 mismatching crashes in every year.
* In-transport vehicles with no person row: 0.40-0.59% per year (FARS) and 0.16-0.22% (CRSS).

Non-motorist share of persons: FARS 8.86% (2016) rising to 10.21% (2024). Non-motorists are 18.9% (2016) to 21.6%
(2024) of FARS fatalities. CRSS weighted non-motorist share is 0.85-1.07% (unw. 3.3-4.4%), so non-motorists are
oversampled in CRSS.

### 2.3 Vehicle class used in this appendix

The vehicle class is taken from person.BODY_TYP (FARS 2019 labels, L): 1-49 automobiles, utility vehicles, vans and
light trucks (**LPV**); 50-59 buses; 60-79 medium/heavy trucks; 80-89 motorcycles and mopeds ("Two Wheel Motorcycle",
"Moped", "Three-wheel Motorcycle", "Off-road Motorcycle", "Motor Scooter", …); 90-97 other (ATV, snowmobile, farm and
construction equipment, LSV, golf cart, ROV, other); 98/99 not reported/unknown. The stability of BODY_TYP is audited in
`docs/audit/vehicle_roadway.md`.

---

## 3. Availability matrix (person-domain variables)

`1` = column present (from `variable_availability.csv`). `L` = labels exist (CRSS has no labels before 2019).

| variable | FARS 16 17 18 | FARS 19-24 | CRSS 16-18 | CRSS 19-24 | notes |
|---|---|---|---|---|---|
| PER_TYP, AGE, SEX, INJ_SEV, SEAT_POS, REST_USE, REST_MIS, AIR_BAG, EJECTION, HOSPITAL, LOCATION, STR_VEH | 1 1 1 L | 1 L | 1 (no L) | 1 L | STR_VEH has no label column in any source-year |
| AGE_IM, SEX_IM, INJSEV_IM, SEAT_IM, EJECT_IM | – | – | 1 | 1 L | CRSS only |
| HELM_USE, HELM_MIS | – | 1 L | – | 1 L | helmet was in REST_USE before 2019 |
| EJ_PATH, EXTRICAT, DOA, DEATH_DA/MO/YR/HR/MN/TM, LAG_HRS, LAG_MINS, WORK_INJ, HISPANIC | 1 L | 1 L | – | – | FARS only |
| RACE (person table) | 1 L (2016-18) | – | – | – | moved to `race` table in 2019 |
| race.RACE / ORDER / MULTRACE | – | 1 (2019+) | – | – | ORDER/MULTRACE labelled 2020+ |
| DSTATUS | 1 L | 1 L | 1 (2016-17 only) | – | drug-test status (§4.16) |
| DEVTYPE, DEVMOTOR | – | 2022+ | – | 2022+ | non-motorist device detail |
| per_aux A_PTYPE, A_RESTUSE, A_HELMUSE, A_PERINJ, A_EJECT, A_LOC, A_AGE1-9 | 1 | 1 | 1 | 1 | never labelled; FARS also has A_HISP, A_HRACE, A_RCAT, A_DOA, A_ALCTES |

---

## 4. Per-variable sections

### 4.1 PER_TYP (person type)

**Codes (L, FARS 2016-24 and CRSS 2019-24):** see the table in §2.2. Label changes:

| code | change | judgement |
|---|---|---|
| 7 | "Other Cyclist" (FARS -2021, CRSS 2019-21) → "Other Pedalcyclist" (2022+) | cosmetic clarification |
| 8 | "Persons on Personal Conveyances" (2016) → "Person on Personal Conveyances" (2017-19) → "Person on a Personal Conveyance" (2022+) | cosmetic |
| 10 | "Persons In/On Buildings" → "Person In/On a Building" (2022+) | cosmetic |

**Coding break (meaning-changing, D + L).** In 2020-2021 code 8 is not used. Personal-conveyance users are split
into 11 "Motorized", 12 "Non-Motorized" and 13 "Unknown if Motorized". From 2022 code 8 returns, and the motorised
split moves to DEVMOTOR (§4.18).

| FARS persons | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 |
|---|---|---|---|---|---|---|---|---|---|
| PER_TYP 8 | 186 | 173 | 154 | 209 | 0 | 0 | 263 | 248 | 284 |
| PER_TYP 11+12+13 | 0 | 0 | 0 | 0 | 189 | 226 | 0 | 0 | 0 |

The CRSS counts behave the same way: 2020: 11/12/13 = 111/97/26; 2022: 8 = 345. Code 19 ("Unknown type of
non-motorist") is very rare (FARS 6 rows, CRSS 8).

**CRSS 2016-2018 (unlabelled).** All observed codes are in the CRSS 2019+ label set and in the same-year FARS label
set. TVD against CRSS 2019 is 1.83, 1.35 and 0.29 pp. **Apply the FARS/CRSS 2019 labels.**

**Unknowns:** 9 is an occupant whose role is unknown (FARS 0.06-0.17% of persons) and 19 is a non-motorist whose type
is unknown. There is no person with PER_TYP missing.

**Harmonised definition (`person_role`):** driver = 1; passenger = 2; occupant_role_unknown = 9; parked_mv_occupant = 3;
pedestrian = 5; pedalcyclist = 6, 7; personal_conveyance = 8, 11, 12, 13; other_nonmotorist = 4, 10, 19. The per_aux
cross-check (§4.19) shows NHTSA's derived A_PTYPE groups 9 with passengers and 3 with "other non-occupants".

**Verdict:** high reliability. Timing: PRE-CRASH. The one break, codes 8/11/12/13, disappears once the
personal-conveyance codes are pooled.

---

### 4.2 INJ_SEV (police-reported KABCO) and INJSEV_IM

**Codes (L, identical code set in FARS 2016-24 and CRSS 2019-24):** 0 No Apparent Injury (O); 1 Possible Injury (C);
2 Suspected Minor Injury (B); 3 Suspected Serious Injury (A); 4 Fatal Injury (K); 5 Injured, Severity Unknown; 6 Died
Prior to Crash*; 9 Unknown/Not Reported. The only label difference is cosmetic: FARS 2016 has "Suspected Minor
Injury(B)" without the space. INJSEV_IM (CRSS) has codes 0-6 with the same labels and no code 9.

**Distribution (% of persons):**

| code | FARS 2016 | 2018 | 2020 | 2022 | 2024 | CRSS(w) 2016 | 2018 | 2020 | 2022 | 2024 |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 O | 24.33 | 25.49 | 25.37 | 26.02 | 26.58 | 78.26 | 80.50 | 78.26 | 79.27 | 79.64 |
| 1 C | 8.62 | 8.37 | 7.06 | 6.96 | 6.66 | 10.72 | 9.73 | 9.92 | 9.27 | 8.67 |
| 2 B | 11.37 | 10.90 | 10.03 | 10.39 | 10.51 | 5.01 | 4.72 | 5.67 | 5.36 | 5.76 |
| 3 A | 10.04 | 9.87 | 10.56 | 10.18 | 10.06 | 1.15 | 1.06 | 1.28 | 1.22 | 1.19 |
| 4 K | 43.72 | 43.67 | 45.15 | 44.41 | 44.44 | 0.22 | 0.21 | 0.28 | 0.28 | 0.26 |
| 5 inj. sev. unknown | 0.28 | 0.35 | 0.32 | 0.22 | 0.22 | 0.28 | 0.19 | 0.14 | 0.09 | 0.09 |
| 6 died prior | 3 rows | 1 | 2 | 3 | 3 | ≈0 (31 rows pooled) | | | | |
| 9 unknown | 1.62 | 1.35 | 1.52 | 1.82 | 1.52 | 4.36 | 3.59 | 4.43 | 4.52 | 4.38 |

The maximum year-to-year TVD is 1.7 pp (FARS) and 2.4 pp (CRSS 2019→2020). There is no coding break. CRSS 2016-18
use the same 8 codes. Their TVD against CRSS 2019 is 2.32, 1.73 and 0.32 pp, so **the 2019 labels apply.**

**Reconciliation with crash- and vehicle-level counts (FARS)** (`07_injsev_reconcile.py`):

| year | crashes | Σ FATALS | Σ persons with INJ_SEV = 4 | crashes where count(INJ_SEV=4) ≠ FATALS | vehicles where count(occupant K) ≠ vehicle.DEATHS |
|---|---|---|---|---|---|
| 2016 | 34,748 | 37,806 | 37,806 | 0 | 0 |
| 2017 | 34,560 | 37,473 | 37,473 | 0 | 0 |
| 2018 | 33,919 | 36,835 | 36,835 | 0 | 0 |
| 2019 | 33,487 | 36,355 | 36,355 | 0 | 0 |
| 2020 | 35,935 | 39,007 | 39,007 | 0 | 0 |
| 2021 | 39,785 | 43,230 | 43,230 | 0 | 0 |
| 2022 | 39,422 | 42,721 | 42,721 | 0 | 0 |
| 2023 | 37,769 | 41,025 | 41,025 | 0 | 0 |
| 2024 | 36,297 | 39,254 | 39,254 | 0 | 0 |

* Every FARS crash has at least one K. INJ_SEV = 6 (died prior to crash, 23 rows over 9 years) is **not** counted in
  FATALS.
* The 30-day rule is consistent with the data: the maximum observed LAG_HRS among K persons is 717-720 h in every year.
  The rule itself is UNVERIFIED as documentation, because no manual is in the archive.
* **CRSS:** accident.MAX_SEV equals the maximum known person INJ_SEV (0-4) in 100% of crashes with MAX_SEV 0-4
  (458,907 crashes). MAX_SEV = 9 occurs only when **no** person has a known 0-4 severity (8,166 crashes). MAX_SEV = 5
  occurs when the best known severity is O or nothing is known and someone is coded 5 (1,743). MAX_SEV = 0 crashes
  still contain a person with INJ_SEV = 9 in 6.4% of cases. **Unknown-severity persons are therefore ignored when any
  other person's severity is known.**

**Codes 5, 6, 9 (unknown / not KABCO):**

* **5** "Injured, Severity Unknown" is known to be injured (≥ C) but cannot be placed on the ordinal scale.
* **6** "Died Prior to Crash" is not a crash injury. FARS has 23 rows and CRSS 31 rows. Exclude these persons from
  injury analyses; do not count them as K.
* **9** "Unknown/Not Reported" is concentrated in hit-and-run vehicles. 69.3% of FARS occupants and 76.6% of CRSS
  occupants with INJ_SEV = 9 are in a vehicle with vehicle.HIT_RUN = 1 (L: 1 = "Yes"), against 2.7% and 2.9% of other
  occupants. 61.7% (FARS) and 62.8% (CRSS) of INJ_SEV = 9 persons also have both AGE and SEX unknown. They are mostly
  unidentified drivers (FARS: 10,558 of 12,338 are PER_TYP 1).

**INJSEV_IM (CRSS):** equals INJ_SEV wherever INJ_SEV ≠ 9 (0 disagreements, all years). INJ_SEV = 9 is imputed to
0/1/2/3/4/5 = 30,019 / 6,496 / 2,582 / 1,210 / 151 / 218 (pooled, unw.). **INJSEV_IM still contains 5 and 6**, so it
does not complete the KABCO scale.

**Severity-dependent missingness:** by construction INJ_SEV = 9 *is* the missingness of the outcome. Its weighted share
in CRSS is 3.6-4.6% per year. Other variables are far more often unknown when INJ_SEV = 9 (§5.1): FARS AGE unknown is
67% when INJ_SEV = 9 and 0.4-4.3% for K/A/B/C/O; CRSS restraint unknown is 87.7% against 5-10%.

**Recommended harmonised outcomes (person level):**

| name | definition | 5 | 6 | 9 |
|---|---|---|---|---|
| `killed` | 1 if INJ_SEV = 4; 0 if INJ_SEV ∈ {0, 1, 2, 3} | missing (or 0 in a sensitivity run: injured but not reported as K) | excluded | missing |
| `ka` | 1 if INJ_SEV ∈ {3, 4}; 0 if ∈ {0, 1, 2} | missing | excluded | missing |
| `kabco` | ordinal 0 (O) … 4 (K) | missing (interval-censored ≥ C) | excluded | missing |
| `injured` | 1 if INJ_SEV ∈ {1, 2, 3, 4, 5}; 0 if = 0 | 1 | excluded | missing |

For CRSS, offer INJSEV_IM as a sensitivity outcome (5/6 still need the same treatment). For FARS remember that every
person is in a fatal crash: FARS O/C/B/A are **survivors of fatal crashes**, not a sample of all crash survivors.

**Verdict:** high reliability, with no definitional break 2016-2024. Timing: **OUTCOME**. The KABCO labels have the
same text across sources, but FARS and CRSS cover different populations.

---

### 4.3 AGE and AGE_IM

**Codes (L):** 0 "Less than One Year"; 1…120 "n Years"; 998 "Not Reported"; 999 "Unknown" (FARS 2016-17) / "Reported
as Unknown" (FARS 2018+, CRSS 2019+). The 999 relabelling is a general 2018 change (§6.1). It does not change the
meaning: the 999 counts move smoothly (FARS 1,218 / 1,175 / 1,104 in 2016-18). The maximum valid age observed is
100-119 (FARS) and 106-120 (CRSS). No values fall between 121 and 997.

**CRSS 2016-18 (unlabelled):** the same structure (998 and 999 present; maximum valid age 116/116/117), so the 2019
labels apply.

**Unknown rates (998 + 999, % of persons):**

| | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 |
|---|---|---|---|---|---|---|---|---|---|
| FARS | 2.22 | 2.21 | 2.32 | 2.18 | 2.81 | 2.88 | 2.95 | 2.55 | 2.55 |
| CRSS (w) | 6.45 | 7.76 | 6.43 | 6.30 | 8.80 | 7.78 | 7.00 | 7.19 | 6.76 |

**Strongly severity-dependent** (pooled 2016-24):

| INJ_SEV | K | A | B | C | O | 5 | 9 |
|---|---|---|---|---|---|---|---|
| FARS % AGE unknown | 0.37 | 0.76 | 0.66 | 0.91 | 4.28 | 8.13 | 67.32 |
| CRSS % AGE unknown (w) | 1.67 | 1.50 | 1.43 | 1.85 | 4.54 | 6.71 | 75.48 |

**AGE_IM (CRSS):** equals AGE wherever AGE < 998 (0 disagreements). Every 998/999 is imputed into 0-120 (no residual
unknown).

**Checks:** drivers aged under 14: FARS 20-48 per year, CRSS 12-34 (unw.). These are plausible rare events and are kept.

**Harmonised definition:** `age_years` = AGE if 0 ≤ AGE ≤ 120, else null (998, 999). For CRSS, `age_years_im` =
AGE_IM. Do not band unknown ages into a numeric band; keep an explicit "unknown" level.

**Verdict:** high reliability. Timing: PRE-CRASH. Missingness is differential: highest for uninjured and
unknown-injury persons, so complete-case age analyses under-represent O and hit-and-run persons.

---

### 4.4 SEX and SEX_IM

**Codes (L):** 1 Male; 2 Female; 8 Not Reported; 9 Unknown (FARS 2016-17) / Reported as Unknown (2018+). **No other
category exists in any source-year 2016-2024.** The only observed codes are {1, 2, 8, 9} in FARS 2016-24 and CRSS
2016-24 (D), including the unlabelled CRSS 2016-18. SEX_IM has codes {1, 2} only.

**Unknown rates (8 + 9, %):** FARS 1.74-2.50 per year. CRSS (w) 4.23 (2016) to 5.65 (2023). The CRSS increase comes
from code 8: 1.38% (2016) → 2.96% (2017) → 3.6-4.0% (2020+), against code 9 at 2.85% → 1.5-1.8%. The **2016→2017
shift between 8 and 9 in CRSS** (TVD 1.6 pp) is a reporting change, not a meaning change; both codes map to missing.

**By severity (pooled):** FARS K 0.20, A 0.25, B 0.28, C 0.50, O 3.60, 9 62.18. CRSS K 0.57, A 0.53, B 0.54, C 0.66,
O 2.90, 9 61.92.

**SEX_IM:** equals SEX where SEX ∈ {1, 2} (0 disagreements). Every 8/9 is imputed (pooled: 28,320 → male, 21,843 →
female).

**Harmonised:** `sex` = male (1), female (2), missing (8, 9). For CRSS, `sex_im` = SEX_IM.

**Verdict:** high reliability. Timing: PRE-CRASH. Missingness is concentrated in O and INJ_SEV = 9 persons.

---

### 4.5 SEAT_POS and SEAT_IM

**Codes (L, identical FARS 2016-24 and CRSS 2019-24):** 0 Not a MV Occupant; 11/12/13 Front Seat Left/Middle/Right;
18 Front Seat Other; 19 Front Seat Unknown; 21/22/23/28/29 the same for the Second Seat; 31-39 Third Seat; 41-49 Fourth
Seat; 50 Sleeper Section of Cab (Truck); 51 Other Passenger in enclosed passenger or cargo area; 52 … unenclosed …;
53 … unknown whether or not enclosed; 54 Trailing Unit; 55 Riding on Exterior of Vehicle; 56 Appended to a Motor
Vehicle for Motion; 98 Not Reported; 99 Unknown (2016-17) / Reported as Unknown (2018+).

* Code 56 is first used in 2019 (FARS 2019+, CRSS 2019-20 and 2022-24). It is absent from FARS 2016-18 and from CRSS
  2016-18, so persons "appended to a vehicle" were coded elsewhere before 2019 (UNVERIFIED where). FARS has 4-8 rows
  per year and CRSS 1-5.
* Codes 48/49 are rare (FARS ≤ 12 rows per year, CRSS ≤ 4) and are not used every year.
* CRSS 2016-18 observed codes are a subset of the FARS same-year labels (FARS 2018 has no observed 49, but its label is
  known from 2016-17). TVD against CRSS 2019 is 1.99, 1.35 and 0.35 pp. **Labels apply.**

**Consistency:** PER_TYP 1 sits in SEAT_POS 11 in ≥ 99.97% of drivers (FARS 497,901 of 497,955; CRSS 823,782 of
824,055). The rest are 13 (FARS 44, CRSS 265), 12 or unknown. A passenger in seat 11 occurs 153 times (FARS) and 48
times (CRSS).

**Unknown rates** (98/99 only / including the row-known-position-unknown codes 19, 29, 39, 49), occupants:

| | 2016 | 2018 | 2020 | 2022 | 2024 |
|---|---|---|---|---|---|
| FARS | 1.31 / 1.57 | 1.25 / 1.45 | 1.28 / 1.50 | 1.46 / 1.70 | 1.20 / 1.50 |
| CRSS (w) | 1.39 / 1.58 | 1.48 / 1.74 | 1.37 / 1.56 | 1.51 / 1.80 | 1.86 / 2.25 |

By severity (pooled, 98/99): FARS K 0.87, A 1.95, B 1.08, C 1.05, O 1.58, 9 4.56. CRSS K 0.85, A 0.51, B 0.45,
C 0.57, O 1.55, 9 4.83. **SEAT_IM** never contains 19/29/39/49/98/99. Row-unknown codes are imputed within the row in
almost all cases (19 → 13 in 1,308 of 1,390 rows; 29 → 21/22/23), and known positions are never changed.

**Harmonised:** `seat_row` = front {11, 12, 13, 18, 19}, second {21, 22, 23, 28, 29}, third_plus {31, 32, 33, 38, 39,
41, 42, 43, 48, 49}, cargo_exterior {50, 51, 52, 53, 54, 55, 56}, not_occupant {0}, missing {98, 99}. `seat_side` =
left {11, 21, 31, 41}, middle {12, 22, 32, 42}, right {13, 23, 33, 43}, other {18, 28, 38, 48}, missing {19, 29, 39,
49, 98, 99}.

**Verdict:** high reliability. Timing: PRE-CRASH. Unknown rates stay below 2.3%, with a mild excess among A-injured
persons in FARS.

---

### 4.6 REST_USE (restraint system use): the most important coding breaks in this domain

**Codes and labels by year (L, FARS; CRSS 2019+ identical):**

| code | label | FARS years observed | CRSS years |
|---|---|---|---|
| 0 | Not Applicable | **2016 only** | 2016 only (unlabelled) |
| 1 | Shoulder Belt Only Used | all | all |
| 2 | Lap Belt Only Used | all | all |
| 3 | Shoulder and Lap Belt Used | all | all |
| 4 | Child Restraint Type Unknown | all | all |
| 5 | DOT-Compliant Motorcycle Helmet | **2016-2018 only** | 2016-18 |
| 6 | Racing-Style Harness Used | 2019+ (≤ 0.01%) | 2019, 2020, 2021, 2024 |
| 7 | None Used | **2016 only** | 2016 only |
| 8 | Restraint Used - Type Unknown | all | all |
| 10 / 11 / 12 | Child Restraint System Forward Facing / Rear Facing / Booster Seat | all | all |
| 16 | Helmet, Other than DOT-Compliant Motorcycle Helmet | **2016-2018 only** | 2016-18 |
| 17 | No Helmet | **2016-2018 only** | 2016-18 |
| 19 | Helmet, Unknown if DOT Compliant | **2016-2018 only** | 2016-18 |
| 20 | None Used / Not Applicable | **2017+** | 2017+ |
| 29 | Unknown if Helmet Worn | **2016-2018 only** | 2016-18 |
| 96 | Not a Motor Vehicle Occupant | all | all |
| 97 | Other | all | all |
| 98 | Not Reported | all | all |
| 99 | Unknown (2016-17) → Reported as Unknown (2018+) | all | all |

The label of 11 differs only by a double space (cosmetic).

**FARS distribution (% of all persons):**

| code | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 |
|---|---|---|---|---|---|---|---|---|---|
| 0 | 1.19 | – | – | – | – | – | – | – | – |
| 3 | 50.73 | 52.45 | 51.43 | 51.51 | 48.25 | 49.39 | 49.06 | 49.53 | 49.94 |
| 7 | 19.05 | – | – | – | – | – | – | – | – |
| 8 | 1.19 | 0.81 | 0.92 | 1.01 | 0.82 | 0.86 | 0.62 | 0.31 | 0.26 |
| 5+16+17+19+29 (helmet) | 7.54 | 7.35 | 7.29 | – | – | – | – | – | – |
| 20 | – | 19.25 | 19.22 | 26.56 | 29.11 | 28.01 | 27.59 | 27.50 | 27.02 |
| 98 | 0.87 | 0.90 | 1.37 | 1.16 | 1.26 | 1.34 | 1.46 | 1.23 | 1.16 |
| 99 | 7.25 | 7.11 | 7.13 | 7.21 | 8.17 | 8.13 | 8.42 | 8.43 | 8.52 |

Year-to-year TVD: 2016→17 21.2 pp, 2018→19 7.7 pp, other years ≤ 3.7 pp. These are two structural breaks.

**Break 1 (2016 → 2017): codes 0 and 7 are merged into 20.** Evidence (D + X): in 2016, 0 + 7 = 20.24% of persons; in
2017, 20 = 19.25%. The 2016 code 0 is concentrated where no belt exists. Among FARS 2016 LPV occupants, REST_USE = 0
for 48.9% of cargo/exterior positions (SEAT_POS 50-56) but only 0.08% of the front row. Among FARS 2016 bus occupants,
0 = 46.7% and 7 = 24.3%; in 2017, 20 = 59.8%. **From 2017, "20" no longer separates "no belt used" from "no belt
available / not applicable."** For LPV occupants the absorbed share is small (0.45 pp in 2016). For buses, cargo-area
riders and "other" vehicles it dominates.

**Break 2 (2018 → 2019): helmet codes leave REST_USE.** Evidence (X): in 2016-18, codes 5/16/17/19/29 occur **only** for
motorcycle-class (BODY_TYP 80-89) and other-class (90-97, ATVs and similar) occupants. They never occur for LPV, bus or
truck occupants. From 2019, motorcycle-class occupants have REST_USE = 20 ("None Used/Not Applicable") in 99.9% of
rows (FARS 39,719 of 39,759; CRSS 21,024 of 21,044), and the helmet moves to HELM_USE (§4.8). REST_USE = 20 rises from
19.2% to 26.6% of all FARS persons (+7.3 pp, which matches the 7.3-7.5% formerly in helmet codes). **A naive mapping of
20 → "unbelted" turns every 2019+ motorcyclist into an "unbelted occupant".** The current helper
`nhtsa_stats.processing.harmonize.restraint_use` does exactly this when it is not restricted to belt-equipped
vehicles (§6.6).

**Break 3 (gradual, CRSS): code 8 "Restraint Used - Type Unknown" falls** from 5.31% (2016) → 4.49 → 3.50 → 1.01 (2019)
→ 0.24-0.35% (2020+), while code 3 rises from 77.1% to 79-81% (w). FARS also falls, from 1.19% (2016) to 0.26%
(2024). This is a reporting-practice change inside the "belted" group. It matters only if belt **type** is analysed.

**CRSS 2016-18 (unlabelled):** the code sets equal FARS same-year sets: 2016 contains 0, 5, 7, 16, 17, 19, 29; 2017-18
contain 5, 16, 17, 19, 29 and 20 but not 0/7. The same cross-tab pattern holds: in CRSS 2016-18 helmet codes appear
only for motorcycle/other classes, and 2016 code 0 sits on buses (13.3%) and cargo areas (31.8%). **Use the FARS
same-year labels for CRSS 2016-18, not the CRSS 2019 labels.** Five to seven codes in CRSS 2016-18 (0.65-2.70% of
weight) do not exist in the 2019+ label set.

**Unknown codes:** 98 Not Reported, 99 (Reported as) Unknown, 97 "Other". The meaning of 97 is not restraint-specific
and is UNVERIFIED; per_aux A_RESTUSE groups 97 with "used" (§4.19). It is ≤ 0.11% of persons. Unknown rates and their
dependence on severity are given in §5.1.

**Harmonised definitions:**

* `restraint_detail` (occupants, VEH_NO > 0): lap_shoulder = 3; shoulder_only = 1; lap_only = 2; belt_type_unknown = 8;
  racing_harness = 6; child_restraint = 4, 10, 11, 12; none_or_na = 7 (2016), 20 (2017+); belt_na = 0 (2016);
  helmet_code = 5, 16, 17, 19, 29 (2016-18; these are **not** belt information); other = 97; missing = 98, 99;
  not_occupant = 96.
* `restrained` (binary, **only for occupants of belt-equipped vehicles: BODY_TYP 1-49, optionally also 50-79, and
  SEAT_POS 11-49**): 1 = {1, 2, 3, 6, 8, 4, 10, 11, 12}; 0 = {7, 20}; missing = {0, 97, 98, 99}. Exclude motorcycle and
  other-class occupants (BODY_TYP 80-97) and cargo/exterior positions (SEAT_POS 50-56). For them "20" means "not
  applicable".
* Report the 2017+ residual ambiguity: 20 includes "not applicable" in a few LPV cases (0.45 pp of 2016 LPV occupants
  were in code 0).

**Verdict:** medium reliability. The codes are stable *after* the three breaks are handled, but restraint use is
police-reported. Unknown status is not ignorable: it rises over time (§5.1) and is tied to unknown injury and
hit-and-run. Timing: PRE-CRASH behaviour, **ascertained post-crash** by police; see §5.1 for the reporting-bias caveat.

---

### 4.7 REST_MIS (restraint misuse)

**Codes (L):** FARS 2016-18: 0 "No", 1 "Yes", 8 "Not a Motor Vehicle Occupant". 2019+ (FARS and CRSS): 0 "No
Indication of Mis-Use" (→ "Misuse" 2021+, cosmetic), 1 "Yes, Indication of Mis-Use", **7 "None Used/Not Applicable"
(new)**, 8 "Not a Motor Vehicle Occupant".

**Coding break (meaning-changing, X):** cross-tabulated with REST_USE (`09_restraint_detail.py`):

| era (FARS) | REST_USE group | REST_MIS 0 | 1 | 7 | 8 |
|---|---|---|---|---|---|
| 2016-18 | belted / child | 136,608 / 5,680 | 412 / 247 | – | – |
| 2016-18 | none, NA(0), helmet codes, unknown (98/99) | 49,215 / 1,033 / 18,865 / 21,065 | 0 / 0 / 102 / 0 | – | – |
| 2019+ | belted / child | 273,024 / 10,389 | 4,710 / 569 | – | – |
| 2019+ | none (20) / unknown (98/99) | – | – | 150,386 / 51,324 | – |

Before 2019, "0" is assigned to every occupant without misuse, including non-users and unknown-use persons. From 2019
it applies only to restraint users, and non-users and unknown-use persons get 7. The share with misuse = 1 rises from
0.3% to 0.9-1.1% of FARS persons (TVD 2018→19 35.7 pp). The share of **belted** persons with misuse rises from 0.30%
(2016-18) to 1.70% (2019+) in FARS and from 0.25-0.50% to 1.42% in CRSS (unw.). This is either a real reporting change or a
definitional change. UNVERIFIED which.

**Harmonised:** `restraint_misuse` defined only for restraint users (REST_USE ∈ {1, 2, 3, 4, 6, 8, 10, 11, 12}): 1 =
REST_MIS 1; 0 = REST_MIS 0; otherwise NA. Expect a level shift in 2019; do not pool across 2018/2019 without a year
effect.

**Verdict:** low reliability for trends, medium within era. Timing: POST-CRASH (inspection-based).

---

### 4.8 Helmet use: HELM_USE / HELM_MIS (2019+) and REST_USE helmet codes (2016-18)

**HELM_USE codes (L, FARS and CRSS 2019-24, stable):** 5 DOT-Compliant Motorcycle Helmet; 16 Helmet, Other than
DOT-Compliant; 17 No Helmet; 19 Helmet, Unknown if DOT-Compliant; 20 Not Applicable; 96 Not a MV Occupant; 98 Not
Reported; 99 Reported as Unknown if Helmet Worn. These are the same numeric codes as the 2016-18 REST_USE helmet codes
(5, 16, 17, 19), except that the 2016-18 "Unknown if Helmet Worn" is 29 while the 2019+ unknown is 99.

**Evidence the series splice (X):** motorcycle-class occupants, FARS, % within class:

| | 2016 (REST_USE) | 2017 | 2018 | 2019 (HELM_USE) | 2024 |
|---|---|---|---|---|---|
| DOT helmet (5) | 22.79 | 23.62 | 21.84 | 24.89 | 33.06 |
| other helmet (16) | 2.90 | 2.90 | 3.00 | 3.01 | 2.78 |
| helmet, DOT unknown (19) | 31.82 | 33.25 | 34.19 | 31.69 | 27.95 |
| no helmet (17) | 39.66 | 37.28 | 37.62 | 36.50 | 32.12 |
| unknown (29 or 98/99) | 2.69 | 2.76 | 3.22 | 3.86 | 3.98 |

The levels are continuous across 2018/2019. A gradual shift from 19 toward 5 is visible after 2021.

HELM_USE is also filled for other-class vehicles (ATV, ROV, etc.). In 2019+ FARS, 10 ROV occupants (BODY_TYP 96) have
both a belt code and a helmet code. Before 2019 one field could hold only one of the two.

**HELM_MIS** (2019+) has the same structure as REST_MIS 2019+: 0/1 only for helmet users, and 7 for 17/20/98/99
(X, `09_restraint_detail.py`).

**Unknown rates (motorcycle-class occupants, 29/97/98/99):** FARS 2.8-4.0% per year. CRSS (w) 6.6-12.3%, rising.
**Severity-dependent** (pooled): FARS K 3.27, A 3.96, B 4.48, C 6.25, O 8.61, 9 42.6. CRSS K 3.35, A 6.10, B 6.58,
C 8.24, O 14.69, 9 75.05. Helmet status is known best for the dead.

**Harmonised:** `helmet` (motorcycle class BODY_TYP 80-89, occupants): source = REST_USE if YEAR ≤ 2018 else HELM_USE.
helmeted = {5, 16, 19}; dot_helmet = {5}; unhelmeted = {17}; missing = {29, 97, 98, 99} and 20 (2019+ HELM_USE = 20 for a
motorcyclist: FARS 0.05-0.10%, CRSS 0.12-0.44%). Not applicable for non-motorcycle occupants unless other-class
helmets are studied. Pedalcyclist helmets are not in the person table; they are in the non-motorist safety-equipment
table `safetyeq`, which was not audited here.

**Verdict:** high reliability for motorcyclists once spliced. The unknown share is small in FARS but larger and rising
in CRSS. Timing: PRE-CRASH (police-ascertained).

---

### 4.9 AIR_BAG (air bag deployment)

**Codes (L):** 1 Deployed-Front; 2 Deployed-Side; 3 Deployed-Curtain; 7 Deployed-Other (knee, air belt); 8
Deployed-Combination; 9 Deployment-Unknown Location; 20 Not Deployed; 97 Not a MV Occupant; 98 Not Reported; 99
Deployment Unknown (2016-17) / Reported as Deployment Unknown (2018+). **2016 only:** 0 "Not Applicable" and 28
"Switched Off".

**Break (2016 → 2017, meaning-changing, D + X):** FARS code 0 is 21.10% in 2016 and absent from 2017, while code 20
goes from 30.96% to 50.73%. CRSS: 0 = 7.37% (2016), and 20 goes from 65.8% to 75.0%. In FARS 2016, AIR_BAG = 0 covers
100% of motorcyclists, 89% of bus occupants, 48% of medium/heavy-truck occupants, 54% of LPV rear-seat and 89% of LPV
cargo-area occupants, and 32% of LPV occupants in model years before 1998. These are all positions or vehicles without
a fitted air bag. In 2017 the same groups are coded 20: motorcyclists 98.5%, LPV rear seat 73.3%. **From 2017, 20 =
"not deployed or no air bag at this position".**

Other drift: code 1 (front only) falls from 19.6% to 7.4% and 8 (combination) rises from 8.6% to 19.8% of FARS
persons (2016→2024). This is plausibly fleet change. Code 9 rises from 3.5% to 10.8-12.1%.

**Unknown (98/99) for LPV occupants:** FARS 4.9-6.6%, CRSS 14.0% (2016) → 5.9-7.1% (2019+).

**Harmonised:** `airbag_deployed` = 1 if {1, 2, 3, 7, 8, 9}; 0 if {20} (2017+) or {0, 20, 28} (2016); missing {98, 99};
NA {97}. Do not interpret 0 as "air bag present and not deployed".

**Verdict:** medium. Timing: **POST-CRASH** (deployment is a crash consequence). Use it only as a mediator, never as a
covariate in severity models.

---

### 4.10 EJECTION, EJECT_IM, EJ_PATH

**EJECTION codes (L, stable):** 0 Not Ejected; 1 Totally Ejected; 2 Partially Ejected; 3 Ejected - Unknown Degree; 7
Not Reported; 8 Not Applicable; 9 Unknown if Ejected (2016-17) / Reported as Unknown if Ejected (2018+).

* **8 = Not Applicable** applies to 100% of non-motorists and to motorcycle-class occupants (FARS 100% in 2016, 97.2%
  in 2024; CRSS 100% → 98.0%). The small 2024 share of motorcyclists coded 0/1 is new (FARS 1.41% "not ejected", 0.99%
  "totally ejected"). The cause is UNVERIFIED.
* Unknown (7 + 9) among non-motorcycle occupants: FARS 0.97-1.64%. CRSS 3.04% (2016) → 7.49% (2017) → 6.3-8.3% (2017-21)
  → 4.3-4.4% (2022-24). **The CRSS level shifts in 2017 and 2022 are driven by code 7 ("Not Reported")** (D).
* Severity dependence: FARS K 0.82, A 1.07, B 0.68, C 0.51, O 1.36, 9 18.2. CRSS K 1.22, A 1.34, B 0.92, C 1.13, O 4.92,
  9 40.1.

**EJECT_IM (CRSS):** equals EJECTION wherever it is not 7/9. Of the 7/9 rows, 57,813 of 58,080 (99.5%) are imputed to 0
"Not Ejected". EJECT_IM is effectively "unknown → not ejected".

**EJ_PATH (FARS only, L stable):** 0 Not Applicable; 1-8 path (side door, side window, windshield, back window, back
door, roof opening, roof, other); 9 Ejection Path Unknown. Path 9 = 5.3-6.4% of persons.

**Harmonised:** `ejected` = 1 {1, 2, 3}; 0 {0}; NA {8}; missing {7, 9}.

**Verdict:** medium (FARS high, CRSS unknown share unstable). Timing: **POST-CRASH** (consequence of crash forces
and restraint). Never use it as a pre-crash covariate.

---

### 4.11 EXTRICAT (FARS only)

**Codes (L, stable):** 0 Not Extricated or Not Applicable; 1 Extricated; 9 Unknown. Code 0 merges "not extricated"
with "not applicable" (non-motorists). Extricated: 8.6-9.9% of persons. Unknown (occupants): 2.24-3.16% per year,
strongly severity-dependent: K 4.22, A 3.85, B 1.73, C 1.31, O 0.42.

**Verdict:** medium. Timing: **POST-CRASH** (rescue operation). It reflects entrapment, which is downstream of crash
severity.

---

### 4.12 DOA, DEATH_*, LAG_HRS / LAG_MINS (FARS only): outcome-derived, leakage

**Codes (L):**
* DOA: 0 Not Applicable; 7 Died at Scene; 8 Died En Route; 9 Unknown. **7/8 occur only for INJ_SEV = 4** (X). K
  persons: 7 = 200,162, 8 = 2,522, 0 = 150,559 (died later), 9 = 463.
* DEATH_MO/DA/HR/MN: 88 "Not Applicable (Non-Fatal)", 97 "Redacted" (2020+), 99 "Unknown". DEATH_YR: 8888 / 9997 /
  9999. DEATH_TM: 8888 NA, 9797 Redacted, 9999 Unknown, and HH99 when the minute is unknown (e.g. 2399).
* LAG_HRS: 0-720 hours; **999 is labelled "Unknown" but is also the value for every non-fatal person** (446,982 non-K
  rows, all = 999). LAG_MINS: 0-59; 99 "Unknown", with the same dual use.
* Among K: LAG_HRS = 999 for 1,864-2,294 per year (4.3-6.2%), and LAG_HRS = 0 for 63-67%. 976 deaths occurred in the
  calendar year after the crash.

**Consistency (X):** every non-K person has DEATH_YR = 8888 and LAG_HRS = 999. Every K person has DEATH_YR equal to the
crash year or the next year, 9999 (319) or 9997 (1,770).

**Redaction (2020+):** all 1,770 fatalities in STATE = 19 (Iowa; label L), 343-379 per year 2020-2024, have DEATH_* =
97/9997/9797, HISPANIC = 97, WORK_INJ = 7 and race-table RACE = 96 / MULTRACE = 7 / ORDER = 97. LAG_HRS, DOA and AGE
are **not** redacted for Iowa.

**Verdict:** these fields are deterministic functions of the outcome (K and timing of death). Timing: **POST-CRASH /
OUTCOME-DERIVED. Exclude them from every predictor set.** LAG_HRS/DOA are valid only as outcomes, for example
"died at scene" or survival time among K.

---

### 4.13 HOSPITAL (transport for treatment)

**Codes (L):** 0 Not Transported (FARS -2019, CRSS 2019) → "Not Transported for Treatment" (2020+), a wording
clarification; 1 EMS Air; 2 Law Enforcement; 3 EMS Unknown Mode; 4 Transported Unknown Source; 5 EMS Ground; 6 Other; 8
Not Reported; 9 Unknown (2016-17) / Reported as Unknown (2018+). The code set is stable. The FARS share of code 0 rises
from 54.76% (2019) to 57.16% (2020), and CRSS falls from 90.40% to 88.89%. This coincides with the relabelling, but
2020 also had a different crash mix, so whether the relabelling caused the shift is UNVERIFIED. Code 4 rises in FARS
2024 (0.51% in 2023 → 1.44%).

**Deterministic link to the outcome (X):** INJ_SEV = 0 ⇒ HOSPITAL = 0 in **100%** of rows in both sources (FARS
204,815 of 204,815; CRSS 769,933 of 769,933). Unknown (8/9) is therefore 0% for O persons. For injured persons it is
FARS A 1.33, B 2.02, C 3.23 and CRSS A 3.51, B 4.74, C 5.38.

**Verdict:** medium. Timing: **POST-CRASH / outcome-derived** (it encodes the injury classification). Do not use it as
a predictor of severity.

---

### 4.14 LOCATION (non-motorist location at time of crash)

**Codes (L, stable):** 0 Occupant of a MV; 1 At Intersection - In Marked Crosswalk; 2 At Intersection - In Unmarked /
Unknown if Marked Crosswalk (label gains "In" in 2021, cosmetic); 3 At Intersection - Not In Crosswalk; 9 At
Intersection - Unknown location; 10 Not at Intersection - In Marked Crosswalk; 11 Not at Intersection - On Roadway,
Not in Marked Crosswalk; 13 … On Roadway, Crosswalk Availability Unknown; 14 Parking Lane/Zone; 16 Bicycle Lane; 20
Shoulder/Roadside; 21 Sidewalk; 22 Median/Crossing Island; 23 Driveway Access; 24 Shared-Use Path; 25 Non-Trafficway
Area; 28 Other; 98 Not Reported; 99 Unknown Location (2016-17) / Reported as Unknown Location (2018+). Code 12 is never
observed.

LOCATION = 0 ⇔ occupant (0 violations). Among non-motorists, the unknown share (98/99) is FARS 1.26-1.92% and CRSS
0.74-2.10%. It is not strongly severity-dependent in FARS: K 1.57, A 1.37, B 1.78, C 1.99.

**Harmonised:** `nm_location` for VEH_NO = 0 only: intersection_crosswalk {1, 2}; intersection_other {3}; intersection_unknown
{9}; midblock_crosswalk {10}; midblock_roadway {11, 13}; parking {14}; bike_lane {16}; shoulder_roadside {20};
sidewalk {21}; median {22}; driveway {23}; shared_path {24}; non_trafficway {25}; other {28}; missing {98, 99}.

**Verdict:** high. Timing: CRASH-CIRCUMSTANCE.

---

### 4.15 WORK_INJ, HISPANIC, RACE (FARS; death-certificate fields, fatalities only)

**Availability is outcome-defined (X):** HISPANIC = 0 "Not A Fatality (not Applicable)", WORK_INJ = 8 "Not Applicable
(not a fatality)" and RACE = 0 "Not a Fatality" hold for **exactly** the persons with INJ_SEV ≠ 4 (0 exceptions,
2016-2024). Any use of these as predictors in FARS leaks the outcome perfectly.

**HISPANIC codes (L, stable except redaction):** 1 Mexican; 2 Puerto Rican; 3 Cuban; 4 Central or South American;
5 European Spanish; 6 Hispanic, Origin Not Specified or Other Origin; 7 Non-Hispanic; 97 Redacted (2020+, Iowa); 99
Unknown. **WORK_INJ:** 0 No; 1 Yes; 7 Redacted (2020+); 8 NA (non-fatal); 9 Unknown.

Unknown among fatalities:

| % of K | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 |
|---|---|---|---|---|---|---|---|---|---|
| HISPANIC 99 | 7.58 | 4.58 | 4.97 | 7.89 | 10.52 | 11.28 | 7.58 | 7.51 | **18.04** |
| WORK_INJ 9 | 6.62 | 3.23 | 3.88 | 6.59 | 8.98 | 10.68 | 4.35 | 3.33 | **13.51** |
| RACE 99 (first listed) | 5.84* | 3.23* | 3.96* | 5.15 | 4.29 | 4.31 | 5.07 | 4.63 | **15.12** |

\*2016-18 come from person.RACE (single race code per person); 2019+ use the first-listed race-table row. The 2024 spike is state-concentrated:
California HISPANIC = 99 went from 152 to 2,967 of 3,876 fatalities, and Wisconsin from 2 to 561 of 595. New York is
high in both 2023 and 2024 (802 → 976 of 1,101).

**RACE: table move and label changes (2019, meaning-changing for some codes, L):**

| code | 2016-18 (person.RACE) | 2019+ (race.RACE) | judgement |
|---|---|---|---|
| 2 | Black | Black or African American | cosmetic |
| 3 | American Indian (includes Aleuts and Eskimos / Alaska Native) | North American Indian or Alaska Native | wording, same group |
| 6 | Hawaiian (includes Part-Hawaiian) | Native Hawaiian | **meaning may change** ("part-Hawaiian" dropped) |
| 19 | Other Indian (…except American or Asian Indians) | … except North American or Asian Indians | cosmetic |
| 58 | Guamanian | Guamanian or Chamorro | wording |
| 97 | Multiple Races (individual races not specified) | Multiple Races Unspecified | cosmetic |
| 98 | All other races | Other Race | cosmetic |
| 96 | – | Redacted (2020+) | new |

**Race table structure (2019+):** every person has ≥ 1 row (0 persons without a row, 0 orphan rows). Non-fatal persons
have one row with RACE = 0. Fatalities with more than one race have one row per race. 130-168 persons per year have
more than one row, and MULTRACE = 1 flags 138-191 per year. 2019 ORDER/MULTRACE are present but unlabelled; they take
the same values as in 2020+.

**Harmonised:** `hispanic` (K only): hispanic {1-6}, non_hispanic {7}, missing {99, 97}. `race` (K only): from
person.RACE (2016-18) or the race table with ORDER = 1 (2019+), with multiracial = MULTRACE = 1 or RACE = 97 → white
{1}, black {2}, aian {3}, asian_pi {4, 5, 6, 7, 18, 28, 38, 48, 58, 68, 78}, other {19, 98}, multiracial, missing {99,
96}. `work_related` (K only): 1 {1}, 0 {0}, missing {7, 9}.

**Verdict:** low-to-medium. These fields are available only for fatalities, have state-specific 2024 incompleteness, and
include Iowa redaction. Timing: demographic (pre-crash) **content**, but **outcome-defined availability**. Usable
only in K-only analyses (e.g. composition of deaths), never as predictors of K.

---

### 4.16 DSTATUS (drug toxicology test status; not "death status")

**Meaning (X):** FARS 2016-17 DSTATUS × DRUGTST1 (L): DSTATUS 0 "Test Not Given" ↔ DRUGTST1 0 "Test Not Given"
(103,724); DSTATUS 2 "Test Given" ↔ DRUGTST1 1/2/3/7/8 (blood, urine, both, unknown type, other); 8 ↔ 6 "Not Reported";
9 ↔ 9 "Unknown if Tested". Code 1 "Test Refused" exists only in FARS 2016 (65 rows) and CRSS 2016. CRSS has DSTATUS only
in 2016-17, with no labels, but the same code set as FARS same-year.

**Severity dependence (FARS):** a test is given to 50-60% of K and 9-12% of non-K. DSTATUS = 8 (not reported) among
K: 5.3-7.5% (2016-19), 12-14% (2020-23), **30.7% in 2024**. The 2024 spike is concentrated in Texas (52 → 2,102),
Florida (437 → 2,080), California (1,041 → 2,040) and North Carolina (556 → 1,399).

**Verdict:** behaviour-domain field. Testing depends on the outcome. Timing: **POST-CRASH**. Do not use it as a
covariate.

---

### 4.17 STR_VEH (striking vehicle of a non-motorist)

No label column in any source-year. Values: occupants 0 (100%). Non-motorists > 0 and equal to the VEH_NO of an
in-transport vehicle in the same crash (100% match, every year). Use it to attach the striking vehicle's attributes to
a pedestrian or cyclist. Timing: CRASH-CIRCUMSTANCE. Verdict: high.

---

### 4.18 DEVTYPE / DEVMOTOR (2022+)

These non-motorist device variables (L: DEVTYPE 3 Bicycle, 5 Mobility Aid Device, 9 Standing or Seated Scooter, …; 96
Occupant of a MV; DEVMOTOR 1 Not Motorized, 2 Motorized, 3 Unknown/Not Reported if Motorized, 8 Occupant) replace
PER_TYP 11/12/13. In 2022-23 they are filled only for non-motorists, with no 96/8 codes (FARS 9,640 and 9,349 rows
non-null). From 2024 they are filled for every person (occupants = 96/8). PER_TYP 8 × DEVMOTOR (2022-24, FARS):
not motorized 171, motorized 390, unknown 234. Bicyclists (PER_TYP 6) also receive DEVMOTOR (FARS motorized 263).
Timing: PRE-CRASH.

---

### 4.19 per_aux cross-check (unlabelled; meanings inferred by cross-tabulation)

None of the A_* codes has a label in the archives. The meanings below are **inferred** from exact cross-tabulations
(`11_per_aux.py`). The category names are therefore UNVERIFIED, but the groupings are exact.

| A_* | inferred grouping (source codes) | notes |
|---|---|---|
| A_PTYPE | 1 = PER_TYP 1; 2 = {2, 9}; 3 = 5; 4 = {6, 7}; 5 = {3, 4, 8, 10-13, 19} | identical FARS/CRSS |
| A_RESTUSE | 1 = {1, 2, 3, 4, 6, 8, 10, 11, 12, **97**}; 2 = {0, 7, 20}; 3 = {98, 99} (+ non-occupants and some motorcyclists in 2016-18); **4 (2019+ only)** = motorcyclists (FARS 33,725) and non-occupants (45,482), plus ≈ 0.3% of LPV rows | **its own 2019 break**: not-applicable moved from 2/3 to 4 |
| A_HELMUSE | motorcyclists: 1 = {5, 16, 19}; 2 = {17}; 3 = {29, 98, 99}; 4 (2019+) = NA | about 1% of 5/19 → 2 (helmet misuse cases, UNVERIFIED) |
| A_PERINJ | FARS: 1 = K, 6 = everything else. CRSS (from INJSEV_IM): 2 = A, 3 = B, 4 = C ∪ 5, 5 = O, 7 = K ∪ 6 | CRSS aux uses **imputed** severity |
| A_EJECT | FARS: 1 = {0, **8**}; 2 = {1, 2, 3}; 3 = {7, 9}. CRSS uses EJECT_IM (no unknown) | groups "not applicable" with "not ejected" |
| A_AGE1 | 1 = 0-15, 2 = 16-24, 3 = 25-54, 4 = 55+, 5 = unknown (FARS); CRSS uses AGE_IM (no unknown level) | |
| A_HISP / A_HRACE / A_RCAT (FARS) | A_HISP 0 = non-fatal, 1 = non-Hispanic (7), 2 = Hispanic (1-6), 3 = unknown/redacted (99, 97); A_HRACE/A_RCAT = 0 for every non-fatal person | outcome-defined availability |

Conclusions: (i) the per_aux groupings agree with the person-level codes. (ii) NHTSA's derived restraint and ejection
variables also pool "not applicable" with substantive categories in some eras. (iii) CRSS aux variables are built from
the *_IM imputations. per_aux is a cross-check only; harmonise from the person-level source codes.

---

## 5. Key analyses

### 5.1 Restraint-use reporting by injury severity and year (differential missingness)

Population: MV-in-transport occupants (PER_TYP 1, 2, 9) of light passenger vehicles (BODY_TYP 1-49). Unknown =
REST_USE ∈ {98, 99}. Adding 97 changes no cell by more than 0.4 pp.

**FARS (% unknown, rows):**

| year | K | A | B | C | O | 5 | 9 |
|---|---|---|---|---|---|---|---|
| 2016 | 8.33 | 8.23 | 6.21 | 5.92 | 10.01 | 23.19 | 43.76 |
| 2017 | 8.70 | 8.28 | 5.47 | 5.31 | 9.46 | 21.25 | 49.50 |
| 2018 | 8.51 | 7.72 | 6.49 | 6.79 | 9.96 | 24.76 | 54.99 |
| 2019 | 8.74 | 7.98 | 6.45 | 7.26 | 9.93 | 20.81 | 64.41 |
| 2020 | 10.28 | 10.07 | 7.35 | 7.94 | 10.36 | 26.14 | 62.12 |
| 2021 | 10.17 | 10.35 | 7.25 | 7.30 | 10.48 | 18.99 | 63.29 |
| 2022 | 10.61 | 10.12 | 7.24 | 7.63 | 11.35 | 23.90 | 66.47 |
| 2023 | 11.05 | 11.30 | 7.57 | 7.56 | 10.27 | 24.18 | 66.49 |
| 2024 | 11.25 | 10.68 | 6.64 | 7.61 | 11.13 | 22.37 | 68.58 |
| pooled (n) | 9.76 (215,438) | 9.47 (71,389) | 6.75 (72,610) | 6.98 (51,563) | 10.36 (163,059) | 22.88 (1,569) | 59.59 (6,144) |

**CRSS (% unknown, weighted):**

| year | K | A | B | C | O | 5 | 9 |
|---|---|---|---|---|---|---|---|
| 2016 | 11.02 | 7.06 | 5.04 | 4.39 | 5.32 | 9.02 | 86.63 |
| 2017 | 8.33 | 7.22 | 4.66 | 4.29 | 5.96 | 17.41 | 71.39 |
| 2018 | 8.74 | 5.95 | 4.36 | 4.28 | 6.42 | 13.72 | 91.86 |
| 2019 | 6.65 | 7.94 | 4.41 | 4.62 | 6.49 | 13.89 | 90.42 |
| 2020 | 9.72 | 9.28 | 5.86 | 5.59 | 7.62 | 15.73 | 88.41 |
| 2021 | 10.16 | 9.17 | 5.24 | 5.43 | 7.17 | 17.16 | 87.71 |
| 2022 | 10.96 | 10.21 | 5.28 | 5.32 | 7.26 | 17.64 | 90.04 |
| 2023 | 11.15 | 9.80 | 5.83 | 5.50 | 8.08 | 18.66 | 91.94 |
| 2024 | 14.77 | 11.10 | 5.67 | 5.88 | 8.50 | 27.88 | 93.00 |
| pooled (unw. n) | 10.21 (7,098) | 8.53 (44,216) | 5.15 (75,592) | 4.96 (141,850) | 6.91 (712,609) | 15.05 (1,824) | 87.72 (27,937) |

The CRSS K cells rest on 659-1,008 unweighted persons per year, so the single-year K values carry sampling noise.

Findings:

1. **Missingness is U-shaped in severity and is not ignorable.** It is lowest for B/C, higher for O, higher again for
   A/K, and very high for unknown-severity persons. Killed vs surviving occupants: FARS K 9.76% against survivors (A-O)
   8.96%, odds ratio 1.10. CRSS K 10.21% against 6.64%, OR 1.60. CRSS by crash MAX_SEV (pooled): K-crash 9.37, A 9.00,
   B 7.27, C 7.01, O 8.78.
2. **Unknown restraint co-occurs with unknown injury.** 52% (FARS) and 85% (CRSS, w) of persons with INJ_SEV ∈ {5, 9}
   have unknown restraint. These persons are mainly in hit-and-run vehicles (§4.2). Complete-case restraint analyses
   therefore also drop most unknown-outcome persons.
3. **Upward trend.** The overall LPV-occupant unknown share rises from 8.76% (2016) to 10.89% (2024) in FARS and from
   7.69% to 11.21% in CRSS (w). The FARS increase is mostly a step in 2020 (9.06 → 10.21). CRSS "Not Reported" (98)
   rises steadily, 1.97 → 4.89%.
4. **Within-role:** passengers have higher unknown rates than drivers (FARS K: drivers 9.30, passengers 11.03; CRSS O:
   6.38 vs 8.43). PER_TYP 9 (occupant role unknown) is 30-75% unknown.

**Restrained share among known status** (belt or child restraint ÷ (restrained + none)), LPV occupants:

| | K | A | B | C | O |
|---|---|---|---|---|---|
| FARS 2016 | 52.23 | 69.33 | 81.03 | 89.47 | 95.60 |
| FARS 2024 | 51.54 | 68.96 | 83.71 | 88.58 | 94.94 |
| CRSS 2016 (w) | 53.42 | 80.31 | 92.78 | 97.75 | 98.94 |
| CRSS 2024 (w) | 49.57 | 77.61 | 93.13 | 97.18 | 98.50 |

**Reporting-bias caveat (UNVERIFIED with these data).** The steep gradient (≈ 50% restrained among K against ≈ 98.5%
among CRSS O) is consistent with both a true protective effect and over-reporting of belt use by or for surviving
occupants. Police often record survivor belt use from self-report, while for the dead they rely on inspection. These
data contain no independent measure of belt use, so the size of this bias cannot be estimated here. Mitigations:

* within-vehicle designs (§5.5), which hold the reporting officer and crash constant;
* sensitivity analyses that assign unknowns to "unrestrained";
* restricting to K vs A, where both are typically examined rather than self-reported (UNVERIFIED assumption);
* never comparing FARS-K restraint with CRSS-O restraint as if measured identically.

### 5.2 INJ_SEV = 4 vs accident.FATALS (FARS)

There is perfect reconciliation in every year (table in §4.2): 0 crashes with a mismatch out of 325,922 crashes and
353,706 fatalities. Vehicle-level DEATHS also has 0 mismatches. Died-prior persons (INJ_SEV = 6) are excluded from
FATALS. NUMOCCS equals the number of occupant person rows for 96.6-99.3% of vehicles. The remainder are almost entirely
NUMOCCS = 99 (unknown; 306 in 2016, 1,235-1,963 per year from 2017). 13-57 vehicles per year have a known NUMOCCS that
differs from the row count.

### 5.3 Occupant vs non-occupant structure

See §2.2. Occupant-only fields are cleanly set to their "not an occupant" codes for non-motorists (0 violations). Key
recommendations:

* Define occupants as VEH_NO > 0 **and** PER_TYP ∈ {1, 2, 9}, which excludes the 3,590 (FARS) and 3,926 (CRSS)
  parked-vehicle occupants whose vehicles live in `parkwork`.
* Join non-motorists to their striking vehicle via STR_VEH.
* Pedestrian/cyclist "restraint" is structurally 96. Their protective equipment is in `safetyeq` (not audited here).

### 5.4 Recommended harmonised person-outcome definitions

See the table in §4.2. Summary rules:

* **K** = INJ_SEV 4. **KA** = {3, 4}. **Ordinal KABCO** = 0-4.
* Code **5** is "injured, severity unknown". Set it to missing in K/KA/KABCO and to 1 in "any injury". As a K/KA
  sensitivity check, treat 5 as non-K / non-KA: in FARS, K is reconciled with FATALS, so no K is hidden in 5.
* Code **6** is excluded: not a crash casualty, and not in FATALS.
* Code **9** is missing. Do not recode to O. In CRSS, INJSEV_IM provides a model-based single imputation, but it keeps
  5 and 6 and should be used only as a sensitivity analysis because single imputation understates variance.
* For CRSS crash-level severity use MAX_SEV, which ignores unknown persons when any person is known, or MAXSEV_IM.
* FARS person-level non-K outcomes describe survivors of fatal crashes. A FARS "KA vs BCO" model is conditional on a
  fatal crash having occurred.

### 5.5 FARS within-vehicle designs (belted vs unbelted occupants of the same vehicle)

Eligible person: LPV occupant (PER_TYP 1, 2, 9; BODY_TYP 1-49) with known restraint (REST_USE ∈ belted/child/none
codes) and known KABCO (INJ_SEV 0-4). Eligible vehicle: ≥ 2 eligible persons. Script `10_within_vehicle.py`.

| year | LPVs | LPVs with ≥2 occupants | ≥2 known restraint & injury | … and all known seat | …with K-discordant outcome | …with KA-discordant outcome | …with adult (16+) belted & unbelted | …restraint- and K-discordant | driver + RF passenger both known | …and ≥1 K |
|---|---|---|---|---|---|---|---|---|---|---|
| 2016 | 40,842 | 14,095 | 12,527 | 12,424 | 6,346 | 4,492 | 2,311 | 1,832 | 11,010 | 6,630 |
| 2017 | 41,093 | 13,829 | 12,373 | 12,257 | 6,211 | 4,345 | 2,130 | 1,667 | 10,831 | 6,347 |
| 2018 | 40,303 | 13,209 | 11,750 | 11,637 | 5,756 | 3,997 | 2,044 | 1,622 | 10,209 | 5,931 |
| 2019 | 39,566 | 12,908 | 11,577 | 11,458 | 5,601 | 3,760 | 2,026 | 1,542 | 10,093 | 5,784 |
| 2020 | 41,479 | 13,257 | 11,628 | 11,490 | 5,730 | 3,794 | 2,074 | 1,597 | 10,190 | 5,948 |
| 2021 | 47,057 | 14,873 | 13,058 | 12,908 | 6,227 | 4,176 | 2,189 | 1,653 | 11,378 | 6,439 |
| 2022 | 45,893 | 14,237 | 12,434 | 12,298 | 5,881 | 3,852 | 2,103 | 1,592 | 10,821 | 6,097 |
| 2023 | 44,174 | 13,720 | 12,089 | 11,951 | 5,634 | 3,739 | 1,964 | 1,511 | 10,476 | 5,813 |
| 2024 | 42,067 | 12,922 | 11,419 | 11,278 | 5,277 | 3,451 | 1,785 | 1,326 | 9,929 | 5,465 |
| **pooled** | 382,474 | 123,050 | **108,855** | 107,701 | 52,663 | 35,606 | **18,626** | **14,342** | 94,937 | 54,454 |

* 108,855 vehicles (281,357 persons) are usable for conditional (vehicle fixed-effect) models. The informative strata
  for a belt effect on death, with both restraint and fatal outcome discordant, number **14,342 vehicles** pooled
  (1,326-1,832 per year).
* Loss: among occupants of 2+-occupant LPVs, 8.5-10.7% have unknown restraint, 1.0-1.4% unknown injury, and 2.7-3.4%
  unknown or row-only seat position. Restraint is the binding constraint.
* Seat position among eligible persons is known for 98.2-98.7% (pooled: driver 107,434; other front 97,342; second
  row 65,288; third+ 4,895; cargo/exterior 2,165; unknown 4,233). Seat-adjusted pairwise (driver vs right-front) designs
  have 94,937 vehicles with both positions known, 54,454 of them with ≥ 1 death.
* Caveat: selection into FARS requires a death in the crash, not necessarily in this vehicle. Conditional estimates
  are valid within the fatal-crash population. The restraint unknown rate is itself severity-dependent (§5.1), so
  report how sensitive estimates are to excluding vehicles with any unknown-restraint occupant.

---

## 6. Cross-cutting findings

### 6.1 Year-specific coding breaks

| year | variables | change | type |
|---|---|---|---|
| 2016→2017 | REST_USE | 0 "Not Applicable" + 7 "None Used" merged into 20 "None Used / Not Applicable" | meaning-changing |
| 2016→2017 | AIR_BAG | 0 "Not Applicable" absorbed into 20 "Not Deployed"; 28 "Switched Off" disappears | meaning-changing |
| 2016→2017 | DSTATUS | 1 "Test Refused" disappears | minor |
| 2017→2018 | AGE, SEX, SEAT_POS, REST_USE, AIR_BAG, EJECTION, HOSPITAL, LOCATION, DSTATUS | "Unknown" → "Reported as Unknown" (999/9/99) | wording only; no distribution jump (e.g. FARS REST_USE 99: 7.25 / 7.11 / 7.13%) |
| 2017→2018 | person (FARS, CRSS) | DRUGTST/DRUGRES columns dropped; CRSS DSTATUS dropped | availability |
| 2018→2019 | REST_USE / HELM_USE / HELM_MIS | helmet codes move out of REST_USE; motorcyclists become REST_USE 20 | meaning-changing for REST_USE; splice for helmet |
| 2018→2019 | REST_MIS | new code 7; 0 restricted to restraint users | meaning-changing |
| 2018→2019 | RACE | moves to race table (multi-row); labels 3, 6, 58, 97, 98 reworded | partly meaning-changing (6) |
| 2019→2020 | PER_TYP | 8 split into 11/12/13 (2020-21 only) | meaning-changing (reversible by pooling) |
| 2020+ | HISPANIC, WORK_INJ, DEATH_*, race | "Redacted" codes for Iowa fatalities (100% of Iowa K) | availability |
| 2022 | PER_TYP / DEVTYPE / DEVMOTOR | 8 returns; motorised split moves to DEVMOTOR | splice |
| 2024 | DEVTYPE / DEVMOTOR | filled for all persons (occupants 96 / 8) | availability |
| 2024 | HISPANIC, WORK_INJ, RACE, DSTATUS (FARS) | state-concentrated jumps in unknown / not reported (e.g. CA HISPANIC 77% unknown; TX DSTATUS 51% not reported) | data completeness |
| 2019+ (CRSS gradual) | REST_USE 8 | "Restraint used, type unknown" falls from 5.3% to 0.3% | reporting practice |
| 2017, 2022 (CRSS) | EJECTION 7 | "Not Reported" steps 2.6 → 7.1% (2017) and 7.0 → 3.7% (2022) | reporting practice |

### 6.2 CRSS 2016-2018 (unlabelled)

For every shared categorical person variable (PER_TYP, SEX, INJ_SEV, SEAT_POS, REST_USE, REST_MIS, AIR_BAG, EJECTION,
HOSPITAL, LOCATION, DSTATUS, and all *_IM variables) **every observed code exists in the FARS same-year label set**.
The only exceptions are codes absent from that FARS year but labelled in an adjacent FARS year: SEAT_POS 49 in 2018 and
LOCATION 24 in 2017. Cross-tab signatures match FARS: helmet codes only on motorcycles, 2016 code 0 on buses and cargo
areas, and AIR_BAG 0 on 99% of motorcyclists in 2016. TVD against CRSS 2019 is ≤ 2.4 pp for all variables without a
documented break. **Rule: label CRSS year y with FARS year y labels. CRSS 2019 labels are valid for 2016-18 only for
variables without a 2016/2017/2019 break.** REST_USE (2016-18), AIR_BAG (2016) and REST_MIS (2016-18) must use the
FARS same-year labels.

### 6.3 Differential missingness: summary

| variable (FARS; CRSS w) | lowest-unknown group | highest-unknown KABCO group | INJ_SEV 9 |
|---|---|---|---|
| REST_USE (LPV occ.) | B/C (FARS 6.8-7.0%; CRSS 5.0-5.2%) | K (9.8%; 10.2%) and O (FARS 10.4%) | 59.6% / 87.7% |
| Helmet (moto) | K (3.3%; 3.4%) | O (8.6%; 14.7%) | 42.6% / 75.1% |
| AGE | K (0.4%) / B (1.4% CRSS) | O (4.3%; 4.5%) | 67.3% / 75.5% |
| SEX | K/A (0.2%; 0.5%) | O (3.6%; 2.9%) | 62.2% / 61.9% |
| SEAT_POS | K (0.9%) / B (0.45% CRSS) | A (2.0% FARS) / O (1.6% CRSS) | 4.6% / 4.8% |
| AIR_BAG (LPV) | B/C (3.7-3.9%) / B (3.4% CRSS) | K (6.6%; 6.5%) | 42.9% / 84.2% |
| EJECTION (occ.) | C (0.5%) / B (0.9% CRSS) | O (1.4%; 4.9%) | 18.2% / 40.1% |
| HOSPITAL | O (0%: deterministic) | C (3.2%; 5.4%) | 9.9% / 15.8% |

### 6.4 Leakage classification

| class | variables |
|---|---|
| OUTCOME | INJ_SEV, INJSEV_IM, A_PERINJ, (crash) MAX_SEV/MAXSEV_IM/FATALS |
| POST-CRASH / OUTCOME-DERIVED (never predictors) | DOA, DEATH_DA/MO/YR/HR/MN/TM, LAG_HRS, LAG_MINS, HOSPITAL (deterministic for O), EXTRICAT, EJECTION, EJECT_IM, EJ_PATH, AIR_BAG, REST_MIS, HELM_MIS, DSTATUS (test given 50-60% K vs 9-12% non-K), WORK_INJ, HISPANIC, RACE / race table, A_DOA, A_HISP, A_HRACE, A_RCAT (availability = K exactly) |
| PRE-CRASH (police-ascertained after the crash; reporting may depend on outcome) | REST_USE, HELM_USE, SEAT_POS, SEAT_IM, AGE, AGE_IM, SEX, SEX_IM, PER_TYP, DEVTYPE, DEVMOTOR |
| CRASH-CIRCUMSTANCE | LOCATION (non-motorists), STR_VEH |

### 6.5 Imputed CRSS variables (*_IM)

All five person *_IM variables equal their source wherever the source is known (0 disagreements in 1.16 M rows). They
fill only the unknown codes: AGE 998/999 → 0-120; SEX 8/9 → 1/2; SEAT 19/29/39/49/98/99 → specific seats; EJECTION 7/9
→ 99.5% "not ejected"; INJ_SEV 9 → 0-5. They are single imputations: a model using them must not be read as having no
missing data. EJECT_IM in particular encodes "unknown ⇒ not ejected".

### 6.6 Implications for existing project code (not modified; state of `src/` as read on 2026-10-22)

`src/nhtsa_stats/processing/harmonize.py`:

* `restraint_use()` maps 20 → "none" for every occupant. For 2019+ motorcyclists (REST_USE = 20 for 99.9%) and for
  bus/cargo occupants (where 20 mostly means "not applicable") this produces false "unrestrained" values. It also
  breaks the 2018/2019 series unless callers restrict to BODY_TYP 1-49 and seat positions 11-49.
* `helmet_use()` sends 2016-18 REST_USE 97 ("Other") for motorcyclists to "not_applicable". It should be unknown.
  2019+ HELM_USE 20 for a motorcyclist should be unknown, not "not_applicable".
* `features.py` AIR_BAG mapping (1-9 deployed, 20 not deployed) leaves 2016 code 0/28 as null and does not flag that
  20 means "not deployed or no air bag" from 2017.
* The `sex()` docstring mentions a code 3. No such code exists in any year 2016-2024.
* The leakage registry lists `restraint` and `seat` as pre-crash, which is correct. It should also register HOSPITAL,
  DOA, LAG_*, DEATH_*, EXTRICAT, HISPANIC, RACE, WORK_INJ and DSTATUS as outcome-derived if they are ever exposed.

---

## 7. Open questions / UNVERIFIED items

1. **Belt-use over-reporting by survivors.** Not measurable with these data (§5.1). The size of the bias is UNVERIFIED.
2. **Meaning of REST_USE 97 "Other"** (≤ 0.11%). per_aux treats it as "used". Its substantive content is UNVERIFIED.
3. **Code 6 "Racing-Style Harness"** is observed only from 2019. Whether it existed (unused) before is UNVERIFIED,
   because the codebook lists only observed codes.
4. **SEAT_POS 56** ("Appended to a MV for motion") is first observed in 2019. Where such persons were coded earlier is
   UNVERIFIED.
5. **REST_MIS / HELM_MIS 2019 level shift** (belted-with-misuse 0.3% → 1.7%): real reporting change or definitional?
   UNVERIFIED.
6. **HOSPITAL 2020 shift**, coinciding with the "Not Transported for Treatment" relabel: cause UNVERIFIED.
7. **Motorcyclist EJECTION ≠ 8 in 2024** (≈ 2.8% of FARS motorcycle occupants): a new coding instruction or error?
   UNVERIFIED.
8. **2024 FARS completeness** (HISPANIC/RACE/WORK_INJ unknown, DSTATUS not reported) is concentrated in a few states.
   Whether later file versions backfill these is UNVERIFIED. Treat 2024 death-certificate and toxicology fields as
   provisional.
9. **The 30-day death window** is consistent with LAG_HRS ≤ 720 but not documented in the archive (UNVERIFIED as a
   rule).
10. **per_aux category names** (all A_* codes) are inferred groupings. The label text is UNVERIFIED.
11. **CRSS HIT_RUN coding** in 2016-18 (used in §4.2) was assumed to follow FARS (1 = Yes). It belongs to the vehicle
    audit.
12. **Pedalcyclist / pedestrian protective equipment** (`safetyeq`) was not audited.

---

## 8. Reliability verdicts (summary)

| variable | verdict | main reason |
|---|---|---|
| PER_TYP | high | clean structure; only the 8 ↔ 11/12/13 split |
| INJ_SEV | high | stable codes; perfect FATALS reconciliation; 9 = 1.3-1.8% (FARS), 3.6-4.6% (CRSS) |
| AGE / SEX | high | stable; unknown concentrated in O and INJ_SEV 9 |
| SEAT_POS | high | < 2.3% unknown |
| REST_USE | medium | three breaks (2017 merge, 2019 helmet split, CRSS code-8 decline); unknown 8-12% and severity-dependent |
| REST_MIS | low (trend) / medium (within era) | 2019 redefinition |
| Helmet (REST_USE→HELM_USE) | high (FARS) / medium (CRSS) | clean splice; CRSS unknown rising to 12% |
| AIR_BAG | medium; post-crash | 2017 merge of NA into "not deployed" |
| EJECTION | medium; post-crash | CRSS "not reported" unstable |
| EXTRICAT, HOSPITAL, DOA, DEATH_*, LAG_* | post-crash / outcome-derived | leakage |
| HISPANIC / RACE / WORK_INJ | low-medium; fatalities only | outcome-defined availability; 2024 gaps; Iowa redaction |
| LOCATION, STR_VEH | high | clean |

---

## 9. Scripts and outputs

All scripts are in `scripts/audit/`
and were run with `POLARS_MAX_THREADS=2 uv run python <script> [FARS|CRSS]`.

| script | purpose |
|---|---|
| `01_codebook_dump.py` | code→label per year with normalised-label comparison |
| `02_distributions.py` | code distributions per source-year (CRSS weighted) and year-to-year TVD |
| `03_crss_unlabelled_check.py` | CRSS 2016-18 code sets vs CRSS 2019 / FARS same-year labels; TVD |
| `04_structure.py` | occupant / non-occupant consistency, joins to vehicle / parkwork, STR_VEH |
| `05_restraint_by_body.py` | REST_USE / HELM_USE / AIR_BAG / EJECTION by vehicle class |
| `06_missing_by_severity.py` | unknown rates by year × INJ_SEV (and CRSS MAX_SEV) |
| `07_injsev_reconcile.py` | FATALS / DEATHS / MAX_SEV reconciliation; death-field consistency; HOSPITAL × INJ_SEV |
| `08_crss_imputed.py` | *_IM vs source variables |
| `09_restraint_detail.py` | REST_MIS / HELM_MIS cross-tabs; restraint by severity |
| `10_within_vehicle.py` | FARS within-vehicle design counts |
| `11_per_aux.py` | per_aux A_* inference by cross-tab |
| `12_misc.py` | race table, DSTATUS meaning, PER_TYP / DEVMOTOR, seat vs role, age checks |
| `13_killed_vs_survivors.py` | restraint unknown, killed vs survivors |
| `14_na_codes_by_seat.py` | 2016 NA codes by seat row / model year |

Intermediate CSVs (`dist_*.csv`, `missing_by_sev_*.csv`, `restraint_by_sev_*.csv`, `within_vehicle_FARS.csv`,
`crss_unlabelled_check.csv`) are in the sibling `out/` directory.
