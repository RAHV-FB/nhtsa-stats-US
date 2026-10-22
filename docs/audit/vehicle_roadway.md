# Audit appendix: vehicle and roadway variables (FARS and CRSS, 2016-2024)

Scope: the vehicle-level tables (`vehicle`, `veh_aux`, `vpicdecode`) of FARS and CRSS, 2016-2024. Status: audit only. No
data or source code was modified. Every number below was computed from the typed Parquet cache
(`data/interim/{FARS|CRSS}/{table}/{year}.parquet`) or from `outputs/audit/codebook.csv`. The scripts are listed in §12.

---

## 1. Purpose and scope

This appendix records, for every vehicle-level and roadway variable likely to enter a severity analysis:

* where the variable is available (source × year);
* what each code means, and the evidence for that meaning. The only in-archive documentation is the embedded `<VAR>NAME`
  label columns, summarised in `codebook.csv`. CRSS 2016-2018 and all `*_aux` tables have no labels;
* coding and definition breaks between years;
* which codes are missing or uninformative, how often they occur by year, and whether that rate depends on crash or
  vehicle severity;
* a reliability verdict and an implementable harmonised definition;
* a timing class (**PRE-CRASH**, **CRASH-CIRCUMSTANCE**, **POST-CRASH / OUTCOME-DERIVED**) for leakage control in
  severity models.

Speeding and alcohol are only noted here. Their detailed audit belongs to the behaviour domain.

### 1.1 Evidence conventions

* **Label evidence (L):** the code-to-label pair appears in `codebook.csv` for that source-year. Labels were compared after
  normalisation (lower case, alphanumerics only). A difference in normalised text is reported in full and judged
  *cosmetic* or *meaning-changing*.
* **Distribution evidence (D):** the share of each code per source-year. Year-to-year change is measured as total
  variation distance (TVD).
* **Cross-tab evidence (X):** the meaning of a code is confirmed by cross-tabulation against an independently labelled
  variable. Examples are BODY_TYP against vPIC body class, veh_aux A_* against their source variables, and ROLLOVER=8
  against body type.
* **UNVERIFIED:** used whenever a meaning rests only on general NHTSA familiarity and could not be confirmed with the
  data.
* CRSS percentages are **weighted by `WEIGHT`** unless marked "unw.". FARS is a census, so its percentages are row
  shares.

---

## 2. Tables, keys and join structure

| table | FARS key | CRSS key | rows/year (FARS) | rows/year (CRSS) | labels |
|---|---|---|---|---|---|
| vehicle (in-transport MVs) | YEAR, ST_CASE, VEH_NO | CASENUM, VEH_NO | 51,623–61,802 | 82,149–97,625 | FARS all years; CRSS 2019+ only |
| veh_aux (derived A_*) | same | same | = vehicle | = vehicle | none |
| vpicdecode (VIN decode, 200–204 cols) | same | same | 50,415–60,659 | 74,823–93,528 | none (string values are self-describing) |
| parkwork (parked/working MVs) | same | same | 1,404–1,772 | 2,267–3,261 | – |

* The `vehicle` table contains only in-transport motor vehicles. `UNITTYPE` = 1 ("Motor Vehicle In-Transport (Inside
  or Outside the Trafficway)") in 100% of rows, every source-year (L, D). Parked and working vehicles are in `parkwork`.
* **vpicdecode → vehicle is 1:0..1, not 1:1.** The key (case, VEH_NO) is unique in vpicdecode in every source-year.
  Every vpicdecode row that does not match a vehicle row matches a `parkwork` row: 1,319/1,319 (FARS 2016),
  1,454/1,454 (FARS 2024), 2,096/2,096 (CRSS 2016), 1,944/1,944 (CRSS 2024). Use a left join from vehicle and filter
  vpicdecode to in-transport keys.

  | source | vehicles with a vpicdecode row (%) by year 2016…2024 |
  |---|---|
  | FARS | 97.5, 97.8, 97.5, 97.7, 97.7, 98.2, 98.2, 98.2, 98.4 |
  | CRSS | 95.0, **90.4**, 96.6, 96.7, 96.9, 96.9, 96.4, **85.6**, **86.0** |

  Coverage is about 0% for model year < 1981 and about 0–4% for MOD_YEAR 9998/9999. It is 34–55% for hit-and-run
  vehicles. vpicdecode MODELYEAR equals MOD_YEAR in 99.6–100% of matched rows.
* The vehicle-file VIN is truncated to 12 characters (≥ 99.8% of rows have length 12), so a full re-decode is
  impossible.

### 2.1 Variable availability (from `variable_availability.csv`, confirmed by load)

| variable | FARS | CRSS | note |
|---|---|---|---|
| BODY_TYP, MOD_YEAR, NUMOCCS, UNITTYPE, HIT_RUN, TOW_VEH, SPEC_USE, EMER_USE, BUS_USE, DR_PRES | 2016–24 | 2016–24 | |
| GVWR | 2016–19 | 2016–19 | replaced by GVWR_FROM/GVWR_TO |
| GVWR_FROM, GVWR_TO, ICFINALBODY, VPICBODYCLASS, VPICMAKE, VPICMODEL, TRLR1–3GVWR | 2020–24 | 2020–24 | new in 2020 |
| VSPD_LIM, VTRAFWAY, VNUM_LAN, VALIGN, VPROFILE, VSURCOND, VTRAFCON, VTCONT_F | 2016–24 | 2016–24 | |
| VPAVETYP | 2016–24 | **absent** | FARS only |
| TRAV_SP, P_CRASH1–3, PCRASH4–5, ACC_TYPE, IMPACT1, M_HARM, HARM_EV, MAN_COLL | 2016–24 | 2016–24 | HARM_EV/MAN_COLL are crash-level copies |
| ACC_CONFIG | **2023 only** | **2023 only** | not in 2024 files |
| ROLLOVER, ROLINLOC, DEFORMED, TOWED, FIRE_EXP, J_KNIFE, SPEEDREL | 2016–24 | 2016–24 | |
| UNDERIDE → UNDEROVERRIDE | 2016–20 → 2021–24 | – → 2021–24 | |
| DEATHS | 2016–24 | – | FARS only |
| MAX_VSEV, NUM_INJV, VEH_ALCH, design vars, *_IM | – | 2016–24 | BDYTYP_IM 2016–20, HITRUN_IM 2016–19 |
| DR_SF1–4, VEH_SC1–2 | 2016–19 | 2016–19 | moved to driverrf/vehiclesf tables from 2020 |

---

## 3. Timing classification (leakage control)

| class | variables | rule for severity models |
|---|---|---|
| **PRE-CRASH (vehicle)** | BODY_TYP / harmonised body group, VPICBODYCLASS / vPIC BODYCLASS, ICFINALBODY, GVWR / GVWR_FROM / GVWR_TO, MOD_YEAR → vehicle age, MDLYR_IM, NUMOCCS, TOW_VEH, SPEC_USE, EMER_USE, BUS_USE, DR_PRES, vPIC equipment fields | admissible as exposures or confounders |
| **PRE-CRASH (roadway/environment)** | VSPD_LIM, VTRAFWAY, VNUM_LAN, VALIGN, VPROFILE, VPAVETYP, VSURCOND, VTRAFCON, VTCONT_F | admissible. Note that recording completeness is outcome-dependent (§9) |
| **PRE-CRASH behaviour, ascertained post-crash** | TRAV_SP, SPEEDREL, VEH_ALCH | admissible in principle. Ascertainment is strongly outcome-dependent (§9), so treat as MNAR |
| **CRASH-CIRCUMSTANCE** | P_CRASH1 (pre-event movement), P_CRASH2 (critical event), P_CRASH3 (avoidance), PCRASH4 (stability), PCRASH5 (pre-impact location), ACC_TYPE / ACC_CONFIG, IMPACT1, HARM_EV, MAN_COLL, J_KNIFE | mediators of severity. Include only in "given the crash configuration" models, never in total-effect models of pre-crash exposures |
| **POST-CRASH / OUTCOME-DERIVED** | ROLLOVER, ROLINLOC, DEFORMED, TOWED, FIRE_EXP, UNDERIDE / UNDEROVERRIDE, M_HARM (chosen as the *most harmful* event, so defined by the outcome), HIT_RUN (post-crash driver behaviour), DEATHS, MAX_VSEV, MXVSEV_IM, NUM_INJV, NUMINJ_IM, veh_aux A_VROLL | never as predictors of injury severity. Outcome or descriptive use only |

---

## 4. Vehicle-type variables

### 4.1 BODY_TYP (vehicle body type), both sources, 2016–2024. PRE-CRASH

**Code list:** 71 distinct codes over 2016–2024. The labels used (L, latest wording) and the harmonised group:

| harmonised group | BODY_TYP codes (label evidence) |
|---|---|
| car | 1 Convertible; 2 2-door sedan/hardtop/coupe; 3 3-door/2-door hatchback; 4 4-door sedan/hardtop; 5 5-door/4-door hatchback; 6 Station wagon (excluding van and truck based); 7 Hatchback, doors unknown; 8 Sedan/hardtop, doors unknown; 9 Other or unknown automobile type; 10 Auto-based pickup; 11 Auto-based panel; 12 Large limousine; 13 Three-wheel automobile; 17 3-door coupe |
| SUV / utility | 14 Compact utility; 15 Large utility; 16 Utility station wagon; 19 Utility vehicle, unknown body type |
| pickup | 30 Compact pickup (GVWR < 4,500) [2016 only]; 31 Standard pickup (4,500–10,000) [2016 only]; 32 Pickup with slide-in camper [2016–17]; 33 Convertible pickup; 34 Light pickup [2017+]; 39 Unknown (pickup-style) light conventional truck |
| van | 20 Minivan; 21 Large van; 22 Step-van ≤ 10,000 lbs; 28 Other van; 29 Unknown van type |
| light truck, other | 40 Cab-chassis based; 41 (no label anywhere: 1 row, CRSS 2017, **UNVERIFIED**); 42 Light-vehicle-based motor home; 45 Other light conventional truck; 48 Unknown light truck type |
| light vehicle, type unknown | 49 Unknown light vehicle type (automobile, utility, van or light truck) |
| bus | 50 School; 51 Intercity; 52 Transit; 55 Van-based bus > 10,000; 58 Other bus; 59 Unknown bus |
| medium/heavy truck | 60 Step van > 10,000; 61 Single-unit 10,001–19,500; 62 Single-unit 19,501–26,000; 63 Single-unit > 26,000; 64 Single-unit, GVWR unknown; 65 Medium/heavy-vehicle motor home; 66 Truck-tractor; 67 Medium/heavy pickup > 10,000; 71/72 Unknown if single-unit or combination (medium/heavy); 78 Unknown medium/heavy truck type |
| truck, weight class unknown | 73 Camper/motor home, unknown truck type/GVWR; 79 Unknown truck type (light/medium/heavy) |
| motorcycle/moped | 80 Two-wheel motorcycle; 81 Moped; 82 Three-wheel motorcycle (2 rear wheels); 83 Off-road motorcycle; 84 Motor scooter [2017+]; 85 Unenclosed 3-wheel / autocycle; 86 Enclosed 3-wheel; 87 Unknown 3-wheel type; 88 Other motored cycle; 89 Unknown motored cycle type |
| other | 90 ATV/ATC; 91 Snowmobile; 92 Farm equipment; 93 Construction equipment; 94 LSV/NEV; 95 Golf cart; 96 ROV (2024: MOHUV or ROV); 97 Other vehicle type |
| missing | 98 Not Reported; 99 Unknown body type |

**Cross-check of the grouping (X):**

* Against vPIC body class (2020–24, vehicle.VPICBODYCLASS):
  * SUV group → 97.4% "SUV/MPV" + 1.8% "CUV";
  * pickup → 98.2% "Pickup";
  * van → 57.3% Minivan, 25.5% Cargo Van, 14.9% Van;
  * bus → 50.4% Bus, 32.8% School Bus, 11.6% school-bus chassis;
  * medium/heavy → 51.0% Truck-Tractor, 20.0% Truck, 11.8% Pickup (code 67 heavy pickups);
  * motorcycle → 100% "Motorcycle - *" classes in the top 4;
  * other → ATV 40.2%, ROV 30.3%, farm 14.6%.
* Against veh_aux A_BODY (unlabelled, pooled): A_BODY 1 ↔ car; 2 ↔ pickup; 3 ↔ SUV; 4 ↔ van; 5 ↔ light truck other;
  6 ↔ medium/heavy truck (83,349 rows, 0 cars); 7 ↔ motorcycle (79,952); 8 ↔ bus (5,974); 9 ↔ other/unknown. The A_BODY
  labels themselves are **UNVERIFIED** (no label column), but the partition matches.
* ROLLOVER = 8 "Not Applicable" (2022+) falls only on the motorcycle group (FARS 97.8%, CRSS 98.6% of that group; 0% of
  every other group).

**Group shares (% of vehicles):**

| group | F16 | F17 | F20 | F24 | C16 | C17 | C18 | C20 | C24 |
|---|---|---|---|---|---|---|---|---|---|
| car | 39.99 | 40.05 | 38.54 | 34.01 | 53.05 | 52.35 | 50.89 | 48.25 | 41.76 |
| SUV | 16.26 | 16.87 | 18.27 | 22.11 | 19.26 | 20.03 | 19.09 | 20.81 | 27.31 |
| pickup | 16.53 | 16.39 | 16.19 | 15.97 | 12.08 | 11.88 | 11.62 | 12.82 | 11.91 |
| van | 4.56 | 4.17 | 3.32 | 3.29 | 4.95 | 4.78 | 4.47 | 4.10 | 3.68 |
| light vehicle unknown (49) | 0.07 | 0.04 | 0.09 | 0.08 | 0.71 | 0.95 | **3.22** | 2.72 | 3.75 |
| medium/heavy truck | 8.69 | 9.12 | 8.97 | 9.47 | 4.01 | 4.19 | 5.04 | 4.48 | 4.61 |
| truck, weight unknown (73, 79) | 0.04 | 0.04 | 0.00 | 0.02 | 0.06 | 0.08 | 0.17 | 0.06 | **1.15** |
| motorcycle/moped | 10.37 | 10.13 | 10.55 | 11.36 | 3.08 | 3.01 | 2.92 | 4.32 | 3.56 |
| other | 1.11 | 0.97 | 1.32 | 1.22 | 0.08 | 0.08 | 0.08 | 0.13 | 0.09 |
| missing (98, 99) | 1.57 | 1.59 | 2.43 | 2.08 | 1.78 | 1.79 | 1.71 | 1.93 | 1.53 |

(These are unweighted row shares, used to show coding behaviour.)

**Coding breaks:**

1. **Pickups, 2016→2017.** In 2016 pickups were coded 30 "Compact pickup" (FARS 3.26%, CRSS 2.51%) and 31 "Standard
   pickup" (FARS 13.18%, CRSS 9.12%). From 2017 they are coded 34 "Light Pickup" (FARS 16.26%, CRSS 10.98%), and 30/31
   no longer appear. The TVD of the CRSS distribution is 0.144 for 2016→17 against 0.027–0.043 for other year pairs.
   At group level the pickup share is continuous (16.53 → 16.39 FARS). Code 32 (slide-in camper) ends in 2017.
2. **Motorcycles, 2016→2017.** FARS 2016 code 80 was labelled "Motorcycle" and code 88 "…mini-bikes, motor scooters,
   pocket motorcycles". From 2017, 80 is "Two Wheel Motorcycle (excluding motor scooters)" and new codes 84 Motor
   Scooter (0.38%), 85, 86 and 87 appear. Code 82 changed from "Three-wheel Motorcycle or Moped" to "Three-wheel
   Motorcycle (2 Rear Wheels)". These are meaning changes within the group, and the group share is stable.
3. **Code 96, 2024:** "Recreational Off-Highway Vehicle" was broadened to "Multipurpose Off-Highway Utility Vehicles
   [MOHUV] or ROV" (L, meaning-changing, still within "other").
4. Label rewording for codes 22, 55, 60–63, 67, 71, 72 (2016–17 "> 26,000 lbs" against 2018+ "greater than 26,000
   lbs.") is cosmetic. The rewording of 42 and 65 ("Truck based" → "Vehicle Based Motor Home", 2020) and of 73 ("unknown
   truck type" → "unknown GVWR", 2022) is minor.
5. **CRSS "unknown type" codes inflate over time (unw.).** Code 49 rose from 0.71% (2016) and 0.95% (2017) to 3.22% (2018) and
   2.7–3.8% after that. Code 79 rose from 0.06% (2020) to 0.54% (2021) and 1.03–1.15% (2022–24). Code 9 "Other or
   unknown automobile" rose from 2.92% (2021) to 5.17–5.71% (2022–24). In FARS these codes stay below 0.2%. For code
   79, VIN decode shows 68.5% "Pickup" (2020–24) and GVWR_FROM = 98 "Not Reported" for 96.1% of them. Code 79 therefore
   appears when GVWR is not reported, not when the body is unknown (X).
6. **Station wagon (6) is mostly crossover SUVs by VIN.** vpicdecode BODYCLASSID ∈ {7 SUV/MPV, 8 CUV} for 75.9–86.4%
   (FARS) and 83.3–88.7% (CRSS) of BODY_TYP = 6 in every year 2016–2024. For BODY_TYP 5 (5-door hatchback) the share is
   3.8–7.2%. For BODY_TYP 4 (sedan) it is ≤ 1.0%. For BODY_TYP 14 (utility) it is 99.0–99.9%. The veh_aux derived body
   class switched to using vPIC in 2020: A_BODY = 3 (utility) for BODY_TYP 6 is 0.0% in 2016–19 and 81.8–87.2% in
   2020–24 (X). **A_BODY therefore has a definitional break in 2020** and must not be used for trends that cross it.

**Missing / unknown:** 98 + 99 = 1.6–2.4% (FARS) and 1.5–2.3% weighted (CRSS). Adding the type-unknown codes 49, 79,
97, 98 and 99 gives 1.7–2.6% (FARS) but 3.1% (C16) rising to 6.3–6.6% (C22–24).

* **Hit-and-run drives missingness.** 85.4% of FARS and 93.5% of CRSS BODY_TYP 98/99 rows are hit-and-run vehicles.
  BODY_TYP is missing for 38.4% (FARS) and 23.9% (CRSS) of hit-and-run vehicles, against 0.28% and 0.12% of other
  vehicles.
* **By severity:**

  | stratum | BODY_TYP missing |
  |---|---|
  | FARS, vehicle with ≥ 1 death | 0.34% |
  | FARS, vehicle without a death | 3.81% |
  | CRSS MAX_VSEV K / A / B / C / O | 0.16 / 0.04 / 0.03 / 0.14 / 0.85% |
  | CRSS MAX_VSEV unknown | 27.6% |

**Reliability:** HIGH at group level, MEDIUM for the car/SUV boundary (code 6) and for CRSS "unknown light/truck"
codes after 2018.

**Recommendation:** use the harmonised group above. Hold "light vehicle, type unknown" (49) and "truck, weight unknown"
(73, 79) as separate levels or as missing; never fold them into a known group. Run a sensitivity analysis that moves
BODY_TYP 6 to SUV when vpicdecode BODYCLASSID ∈ {7, 8}. That field is available in all years.

### 4.2 VPICBODYCLASS / vpicdecode BODYCLASS(ID). PRE-CRASH

* vehicle.VPICBODYCLASS exists only in 2020–24, with 71 codes labelled with vPIC class names (L). The vpicdecode
  BODYCLASS / BODYCLASSID pair exists in **all years 2016–24**: 0% null among vpicdecode rows, 50–55 classes.
* Agreement between VPICBODYCLASS and BODYCLASSID among matched rows:
  * FARS 2020–24: 99.94–100%;
  * CRSS 2020: 94.5%; CRSS 2021: 93.2%; CRSS 2022: 91.0%;
  * CRSS 2023–24: 99.99–100%.
* **Inconsistency (CRSS 2021–22):** VPICBODYCLASS = 999 "Unknown" for 4,306 (2021) and 6,874 (2022) vehicles that have
  a clean vpicdecode decode (VINDECODEERROR "0"; mostly BODYCLASSID 7 SUV or 13 Sedan).
* CRSS 2023–24 have no such inconsistency, but 14–16% of vehicles have no vpicdecode row.
* Hence VPICBODYCLASS 999 "Unknown" (CRSS, unw.): 4.9% (2020), 6.5% (2021), 9.9–10.3% (2022–24). The FARS value is
  about 1.7–2.2%.
* vPIC body class is missing for 2.3% of CRSS K vehicles and 7.8% of O vehicles, so it is more complete for severe
  crashes.

**Reliability:** HIGH where a decode exists. Coverage differs by year in CRSS.

**Recommendation:** derive the VIN body class from `vpicdecode.BODYCLASSID` (left join, all years). Use it to validate
or split BODY_TYP, not to replace it.

### 4.3 ICFINALBODY. PRE-CRASH

* 2020–24 only.
* 0 = "Not Applicable" for 98.2–99.1% of vehicles. Other codes give the final-stage body of incomplete vehicles: 11
  Truck, 60 Pickup, 66 Truck-Tractor, 9 Van, 73 School bus, 108 Motorhome, 128 Ambulance (2021+), 130 Fire apparatus
  (2021+), 998 Not Reported, 999 Unknown.
* Non-zero for 16.6% of the medium/heavy group, 14.5% of buses, 12.4% of "light truck other" and 0.0% of cars (X).

**Reliability:** MEDIUM. **Use:** descriptive only, for heavy and special vehicles.

### 4.4 GVWR (2016–19) and GVWR_FROM / GVWR_TO (2020–24). PRE-CRASH

* **GVWR (L):**

  | code | label | FARS share | CRSS share |
  |---|---|---|---|
  | 0 | Not Applicable | 87.9–90.4% | 93.1–94.5% |
  | 1 | 10,000 lbs. or less | | |
  | 2 | 10,001–26,000 | | |
  | 3 | 26,001 or more | | |
  | 8 | Not Reported | | |
  | 9 | Unknown / "Reported as Unknown" (2018+) | | |

  Code 0 covers essentially all cars, SUVs, pickups, vans and motorcycles (99.4–100% of those groups, X). The scheme
  measures GVWR only for trucks and buses.
* **GVWR_FROM / GVWR_TO (L):** 11–18 = Class 1 (≤ 6,000) … Class 8 (≥ 33,001), 98 Not Reported, 99 Reported as Unknown.
  **Every vehicle** gets a class, for example cars are 99.2% Class 1.
* **Break:** scope and scale changed in 2020. The two schemes can be bridged only at 3 levels, with cut points at
  10,000 and 26,000 lbs, which coincide (Class 2 upper bound = 10,000; Class 6 upper bound = 26,000).
* **FROM/TO disagree in CRSS.** FROM = TO for 86.3% of CRSS rows against 99.3% of FARS rows. The CRSS discrepancy is
  mostly FROM = 11, TO = 12 (13.0% of rows). FROM > TO never occurs.
* **Missing:**
  * GVWR 8/9: FARS 0.33–0.37% (2016–18), **1.72%** (2019); CRSS 1.3–2.3%.
  * GVWR_FROM 98/99: FARS 2.1–2.6%; CRSS 2.4–3.3%.
  * GVWR "Reported as Unknown" jumped in 2019: FARS 9 rose from 0.26% to 1.67%, CRSS from 0.29% to 1.54%.
  * By severity: FARS GVWR_FROM missing 0.54% (death) against 4.33% (no death); CRSS K 0.43% against O 1.70% against
    unknown 28.5%.

**Recommendation:** use `gvwr3` (≤ 10k / 10–26k / > 26k) only within the truck and bus groups. Classify light vehicles
by body group.

### 4.5 MOD_YEAR, MDLYR_IM and vehicle age. PRE-CRASH

* **Codes:** 4-digit model year (L in labelled years, label = the year itself). 9998 = "Not Reported", 9999 = "Unknown"
  (L, CRSS 2019+, FARS all years). CRSS 2016–18 use the same two codes (D: identical code set, no other ≥ 9000 values).
* **Missing:**

  | source | 9998 | 9999 |
  |---|---|---|
  | FARS | 0.01–0.05% (2016–19) → 0.29–0.49% (2020–24) | 2.26–2.80% |
  | CRSS (unw.) | 0.16–0.86% | 3.56–4.20% |

  Combined weighted share: FARS 2.3% (2016) → 3.0% (2024); CRSS 4.4% → 4.7–5.1%.
* **Severity and hit-and-run:** MOD_YEAR is missing for 46.2% (FARS) and 58.8% (CRSS) of hit-and-run vehicles. These
  account for 73.9% and 92.7% of all MOD_YEAR missingness. Among non-hit-and-run vehicles the FARS rate is 1.02% (death
  vehicle) against 0.46% (no death). CRSS non-hit-and-run, weighted: K 0.89%, A 0.72%, B 0.35%, C 0.23%, O 0.22%.
* **Vehicle age** = YEAR − MOD_YEAR:

  | source | mean age 2016 → 2024 | median | p90 |
  |---|---|---|---|
  | FARS | 10.5 → 11.4 years | 10–11 | 19 → 22 |
  | CRSS (unw.) | 8.4 → 9.1 years | 7–8 | 17 → 19 |

  * Age −1 (the next model year sold in the calendar year) occurs for 1,862 FARS and 3,030 CRSS vehicles. This is
    plausible.
  * Age ≤ −2 occurs for only 2 FARS rows (2020: MY 2022; 2022: MY 2024).
  * Age ≥ 30: 7,106 FARS and 4,721 CRSS rows.
* **MDLYR_IM** (CRSS only) equals MOD_YEAR in 100% of rows with a known MOD_YEAR in every year. It has no 9998/9999 and
  equals veh_aux A_MOD_YR in 100% of rows. In FARS, A_MOD_YR equals MOD_YEAR, including 9998/9999.

**Reliability:** HIGH.

**Recommendation:** `veh_age = YEAR − MOD_YEAR`; recode −1 → 0 with a flag, ≤ −2 → missing, 9998/9999 → missing. For
CRSS weighted estimates, MDLYR_IM is an acceptable single imputation. Report its use.

### 4.6 NUMOCCS (number of occupants). PRE-CRASH

* **Codes:** the count (0 = "None", 1, 2, …). The label is the number (L). 99 = "Unknown". No 97/98 observed. CRSS
  2016–18 contain counts up to 95 and 99 only. Codes 53, 59, 60, 62, 75 and 95 occur once each and are unlabelled, but
  they lie in a numeric range.
* **Break for hit-and-run vehicles.** FARS 2016 coded 70.1% of hit-and-run vehicles NUMOCCS = 1 and 12.8% as 99. From
  2017 it is 26.8% = 1 and 59.8% = 99 (2024: 27.9% and 61.6%). In CRSS the share of hit-and-run vehicles coded 1 went
  57.0% (2016) → 36.1% (2017) → 8.4% (2018) → 3.6% (2024). As a result, overall NUMOCCS = 99 is 0.58% (F16) against
  2.42% (F17) and 2.1% (C16) against 5.35% (C18) and 6.9% (C24) unw.
* Among non-hit-and-run vehicles, 99 is ≤ 0.18% in every year.
* **By severity:** FARS 0.14% (death) against 5.31% (no death). CRSS weighted: K 0.18%, O 3.46%, unknown MAX_VSEV
  71.9%.

**Recommendation:** set NUMOCCS to missing for hit-and-run vehicles in **all** years. The 2016 value 1 is a default, not
an observation. **Reliability:** HIGH for non-hit-and-run vehicles, LOW for hit-and-run vehicles.

### 4.7 HIT_RUN. POST-CRASH (driver behaviour)

* **Codes:** 0 No, 1 Yes, 9 "Unknown" (2016–17) / "Reported as Unknown" (2018–19) (L).
* **Code 9 was removed from 2020** in both sources (FARS 0.19% in 2016, 0.05% in 2019; CRSS ≤ 0.01%).
* Yes: FARS 3.76–3.95% (2016–19) and 4.72–4.97% (2020–24). CRSS (unw.) 5.95–6.15% (2016–19) and 7.20–7.65% (2020–24).
  The step at 2020 is larger than the removed 9-share, so it is a real change or a definitional change. That question
  is **UNVERIFIED**.
* HITRUN_IM (CRSS 2016–19) equals HIT_RUN where it is known.

**Use:** a hit-and-run flag explains most vehicle-attribute missingness, so keep it as a stratifier. Do not use it as a
severity predictor.

### 4.8 TOW_VEH. PRE-CRASH

* **Codes (L):** 0 none; 1–3 one/two/three or more trailers; 4 yes, number unknown; 5/6 towing another MV (fixed /
  non-fixed linkage); 7 "Trailing Unit Other than a Trailer or Another Motor Vehicle" (new 2022); 9 Unknown.
* Labels changed "Trailing Units" → "Trailers" in 2022. Together with the new code 7, this narrows codes 0–4 to true
  trailers (meaning-changing, small: code 7 ≤ 0.03%).
* Unknown: FARS 0.21–0.61%; CRSS 0.08–0.88% (C24 0.88% weighted).

**Reliability:** HIGH. **Harmonise:** none / trailer(s) / towing MV / other; 9 → missing.

### 4.9 SPEC_USE, EMER_USE, BUS_USE. PRE-CRASH

* **SPEC_USE (L):** 0 none; 1 taxi; 2 school transport; 3 other bus; 4 military; 5 police; 6 ambulance; 7 fire truck;
  8 non-transport emergency; 10–12 incident response (2019+, replacing 13 "Incident Response" ≤ 2018); 19 vehicle
  sharing (2020+); 20 ride-hailing (2019+); 21 mail carrier; 22 public utility; 23 rental truck > 10,000 (2019+);
  98 Not Reported; 99 Unknown.
  * **Breaks:** code 98 disappears from 2021, and code 0 is relabelled "No Special Use **Noted**". In CRSS, 98 was
    0.7–2.4% and code 0 rose from 96.49% (2020) to 97.71% (2021). Not-reported is therefore merged into 0 from 2021,
    which is meaning-changing.
  * Missing (98, 99): FARS 0.36–1.00%; CRSS 1.3–3.6%.
* **EMER_USE (L):** 0 Not Applicable; 2–3 non-emergency; 4–6 emergency operation; 8 Not Reported; 9 Unknown. Stable.
  Missing 0.3–0.7% (FARS) and 0.36–1.86% (CRSS).
* **BUS_USE (L):** 0 Not a Bus; 1 School; 4 Intercity; 5 Charter/Tour; 6 Transit; 7 Shuttle; 8 Modified for personal
  use; 97 Bus, Unknown Use (2022+); 98, 99.
  * **Break 2019:** 99 rose from 0.27–0.36% (FARS 2016–18) to 1.70–2.51% (2019–24). The cause is a scope change: from
    2019 vehicles of unknown body type get 99 instead of 0. Of the BUS_USE = 99 rows in 2019+, 11,757 have BODY_TYP 99
    and 4,423 have 98 (X).
  * From 2020, a few bus-bodied vehicles are coded 0.

**Recommendation:** use SPEC_USE groups (emergency = 5–8, 10–12; bus use = 2–3; taxi / ride-hail = 1, 20). Treat 0 as
"none or not noted". Use BUS_USE only conditional on a bus body type.

### 4.10 DR_PRES. PRE-CRASH

* **Codes:** 0 "No Driver Present/Not Applicable", 1 Yes, 9 Unknown (L). Yes = 99.3–99.5% (FARS) and 99.75–99.82%
  (CRSS). Unknown ≤ 0.02%.
* DR_PRES = 0 rows carry 0 / 8 "No driver present" codes in P_CRASH1–3, PCRASH4–5 and SPEEDREL. These are
  not-applicable codes, not missing.

---

## 5. Roadway variables (vehicle-level roadway at the vehicle's pre-crash location). PRE-CRASH

All roadway variables share code 0 = "Non-Trafficway or Driveway Access" (FARS 0.6–1.1%, CRSS 2.1–2.8%). This is a
legitimate category, not missing. Every variable has the pair "Not Reported" (8 or 98) and "Unknown" (9 or 99). In
FARS 2016–17 the label is "Unknown"; from 2018 (and in CRSS 2019+) it is "Reported as Unknown". This is a clarifying
rewording; the code is unchanged.

### 5.1 VSPD_LIM (posted speed limit)

* **Codes (L):** 0 "No Statutory Limit/Non-Trafficway or Driveway Access"; 5, 10, …, 80 in 5 mph steps (85 occurs in
  FARS 2017–21 and 90 once in CRSS 2020); 98 Not Reported; 99 Reported as Unknown.
* The CRSS 2016–18 code set is identical (D). The CRSS 2016 share of 65 mph (3.14%) is lower than 2017 (5.35%). This is
  probably a sampling effect, **UNVERIFIED**.
* **Missing (98 + 99):**

  | source | 2016 | 2018 | 2020 | 2022 | 2024 |
  |---|---|---|---|---|---|
  | FARS | 3.18% | 3.14% | 4.17% | 3.84% | 3.93% |
  | CRSS (weighted) | 12.8% | 14.6% | 14.3% | 15.2% | 15.4% |

  98 dominates: CRSS unw. 11.4–15.4%.
* **By severity:** none in FARS (3.52% in both strata). In CRSS it is strongly differential: K 6.4%, A 12.4%, B 8.4%,
  C 14.8%, O 14.0%, unknown 23.1%. This persists after excluding hit-and-run vehicles: K 6.4%, O 13.8%.

**Reliability:** HIGH in FARS. In CRSS, MEDIUM, and missingness is MNAR with respect to severity.

**Recommendation:** numeric mph for 5–90. Keep 0 as a separate "no statutory limit / non-trafficway" level. 98/99 →
missing. Add an explicit missing indicator in CRSS models.

### 5.2 VTRAFWAY (trafficway description)

* **Codes (L):** 0; 1 Two-way not divided; 2 Two-way divided, unprotected median; 3 Two-way divided, positive barrier;
  4 One-way; 5 Two-way not divided with continuous left-turn lane; 6 Entrance/exit ramp; **7 "Two-Way Divided, Unknown
  if Unprotected Median or Positive Median Barrier" (new 2022)**; 8; 9.
* **Breaks:**
  * **2016→2017:** code 2 was "Two-Way, Divided, Unprotected (Painted > 4 Feet) Median" in FARS 2016. The painted-width
    qualifier was dropped in 2017 (meaning-changing). FARS code 2 moved 17.1% → 20.1% and code 3 moved 16.3% → 14.2%.
  * **2022:** new code 7 takes 9.0–12.6% in CRSS (2022–24), and CRSS code 3 drops from 20.5% (2021) to 11.6% (2022).
    In FARS code 7 is 0.5–1.2%.
  * "Divided" is comparable only as 2 + 3 + 7.
* **Missing (8 + 9):**
  * FARS 0.28% (2016) → 0.86% (2024).
  * CRSS (weighted) 19.6% (2016), 21.1% (2019), 12.9% (2024).
  * CRSS by severity: K 6.9%, A 11.8%, B 10.9%, C 16.7%, O 17.0%.

**Reliability:** HIGH (FARS), MEDIUM (CRSS).

**Recommendation:** 4 levels: undivided (1, 5), divided (2, 3, 7), one-way (4), ramp (6); 0 separate; 8/9 missing.

### 5.3 VNUM_LAN (number of travel lanes)

* **Codes (L):** 0; 1–6 lanes; 7 = "Seven or more lanes"; 8; 9. Stable.
* **Missing:**
  * FARS 0.46% (2016) → 1.05–1.65% (2018+).
  * **CRSS 26.5%** (2016), 32.7% (2018), 22.8% (2024), weighted.
  * CRSS by severity: K 16.7%, A 20.4%, B 19.5%, C 24.8%, O 28.3%.

**Reliability:** HIGH in FARS. LOW–MEDIUM in CRSS: about a quarter missing, and outcome-dependent.

### 5.4 VALIGN (roadway alignment)

* **Codes (L):** 0; 1 Straight; 2 Curve right; 3 Curve left; 4 Curve, unknown direction; 8; 9. Stable.
* **Missing:**
  * FARS 1.7–2.6%.
  * CRSS 6.0% (2016), **8.4–9.4% (2017–19)**, 3.1–3.9% (2020–24) weighted. This is a step change at 2020.
  * In CRSS, curve-unknown-direction (4) fell from 1.5% to 0.6%.
  * CRSS by severity: K 3.3%, O 4.9%, unknown 14.5%.

**Recommendation:** straight / curve (2, 3, 4) / non-trafficway; 8/9 missing.

### 5.5 VPROFILE (grade)

* **Codes (L):** 0; 1 Level; 2 Grade, unknown slope; 3 Hillcrest; 4 Sag; 5 Uphill; 6 Downhill; 8; 9. Stable.
* **Missing (8 + 9):** rising in both sources.
  * FARS 7.2% (2016) → 10.3% (2024).
  * CRSS 14.8% (2016) → 17.0% (2024).
  * CRSS by severity: K 11.9%, O 14.3%, unknown 28.3%.
* FARS code 2 (grade, unknown slope) falls 9.8% → 8.0%.

**Recommendation:** level / grade (2, 5, 6) / crest or sag (3, 4); 8/9 missing. **Reliability:** MEDIUM.

### 5.6 VPAVETYP (pavement type), FARS only

* **Codes (L):** 0; 1 Concrete; 2 Blacktop/asphalt; 3 Brick; 4 Slag/gravel/stone; 5 Dirt; 7 Other; 8 Not Reported;
  9 Unknown.
* **Missing 23.8–28.1%**, rising (23.8% in 2016, 28.1% in 2021). By severity: 24.5% (death) against 28.1% (no death).
* Not present in CRSS. **Reliability:** LOW (a quarter missing). Avoid as a covariate.

### 5.7 VSURCOND (roadway surface condition)

* **Codes (L):** 0; 1 Dry; 2 Wet; 3 Snow; 4 Ice/Frost; 5 Sand; 6 Water (standing or moving); 7 Oil; 8 Other; 10 Slush;
  11 Mud, dirt or gravel; 98 Not Reported; 99 Unknown. Stable code set and labels.
* **Break in CRSS 2020 (missingness, not definition):** "Not Reported" (98) is 0.77–1.84% (2016–19) and then **6.18%
  (2020), 8.96% (2021), 9.2–9.3% (2022–23), 12.32% (2024)** unw. Weighted missing (98 + 99): 1.2% (2016), 2.2% (2019),
  6.2% (2020), 12.3% (2024). The "Dry" share falls 79.8% → 72.4% and "Wet" 13.4% → 11.3% (2019 → 2024 unw.). Not-reported
  replaces both.
* FARS missing 0.9% (2016) → 2.0% (2024).
* **By severity:**
  * CRSS (pooled) K 3.8%, A 5.0%, B 5.6%, C 5.8%, O 5.3%, unknown 14.9%.
  * Per year the gap widens: 2024 K 5.8% against O 11.3%.
  * FARS 1.72% (death) against 1.37% (no death).

**Recommendation:** dry (1) / wet (2, 6) / snow-ice (3, 4, 10) / other (5, 7, 8, 11) / non-trafficway (0); 98/99
missing. In CRSS 2020+ always model the missing level. **Reliability:** HIGH (FARS); MEDIUM and deteriorating (CRSS).

### 5.8 VTRAFCON (traffic control device) and VTCONT_F (device functioning)

* **VTRAFCON codes (L):** 0 No Controls; 1–4 signals (1 without and 2 with pedestrian signal; 3 pedestrian signal
  unknown; 4 flashing); 7 lane use; 8 other signal; 9 unknown signal; 20 stop sign; 21 yield; 23 school zone; 28 other
  regulatory; 29 unknown regulatory; 40 warning sign; 50 person; 65 railway crossing device; **97 Not Reported; 98
  Other** (not missing); 99 Unknown.
* **VTCONT_F (L):** 0 No Controls; 1 not functioning; 2 functioning improperly; 3 functioning properly; 4 not
  functioning or improper, specifics unknown (2019+); 8; 9. VTCONT_F = 8 mirrors VTRAFCON = 97 to within 0.05 pp.
* **Major break: not-reported replaces "No Controls".**

  | year | FARS VTRAFCON = 97 | FARS VTRAFCON = 0 | FARS 0 + 97 | CRSS 97 (unw.) | CRSS 0 (unw.) | CRSS 0 + 97 |
  |---|---|---|---|---|---|---|
  | 2016 | 0.17% | 79.97% | 80.1% | 3.57% | 60.78% | 64.4% |
  | 2017 | 0.27% | | | 3.05% | | |
  | 2018 | 2.11% | | | 2.81% | | |
  | 2019 | 3.42% | | | 7.85% | | |
  | 2020 | 8.03% | | | 14.6% | | |
  | 2021 | 13.15% | | | 15.4% | | |
  | 2022 | 17.48% | | | 14.9% | | |
  | 2023 | 18.84% | | | 16.9% | | |
  | 2024 | 19.76% | 57.74% | 77.5% | 15.5% | 47.06% | 62.5% |

  The sum of codes 0 and 97 is nearly constant, so the new not-reported code absorbs cases formerly coded "No Controls".
* **The FARS shift is state-specific.** VTRAFCON = 97 in FARS 2024: South Dakota 89.2%, Oregon 85.8%, Michigan 75.6%,
  California 72.1%, Massachusetts 71.8%, South Carolina 48.0%, Georgia 47.5%, Indiana 44.3%. 11 of 51 jurisdictions are
  at 0%. In 2016 every state was ≤ 1.8%.
* **By severity:** FARS 9.9% (death) against 9.7% (no death). CRSS weighted: K 14.0%, A 13.3%, B 10.7%, C 11.0%,
  O 10.4%. In 2021 the CRSS split was K 26.1% against O 14.9%.

**Recommendation:** do not use "No Controls" as a reference level across years. Use a binary "control device present"
(1–9, 20–65, 98) against "none or not reported" (0, 97), with 99 missing. Alternatively treat 97 as missing and include
state × year fixed effects. **Reliability:** LOW for trend analysis; MEDIUM within a year.

---

## 6. Crash-circumstance variables

### 6.1 TRAV_SP (travel speed). PRE-CRASH behaviour, ascertained post-crash

* **Codes (L):** 0 = "Stopped Motor Vehicle In-Transport", a valid 0 mph, not missing. 1–151 = mph (label "001 MPH" …
  "151 MPH"). 997 = "Greater than 151 MPH" (≤ 8 rows per year). 998 = Not Reported. 999 = Unknown / Reported as Unknown.
  CRSS 2016–18 share this code set (D).
* **Known (0–151, 997):**

  | source | known % by year |
  |---|---|
  | FARS | 37.4 (2016), 40.5 (2018), 41.3 (2019), 38.3 (2024) |
  | CRSS (weighted) | 45.0 (2016), 50.9 (2018), 44.9 (2024) |

  Missing (998 + 999):

  | source | 998 | 999 |
  |---|---|---|
  | FARS | 49–54% | 7.9–10.9% |
  | CRSS (unw.) | 45–53% | 3.1–4.8% |

* **CRSS 2017→2018 shift:** 998 fell 53.0% → 45.3%. TVD = 0.084, against 0.012–0.032 in other year pairs.
* **By severity (MNAR):**
  * FARS: missing for 64.2% of death vehicles against 57.0% of others (non-hit-and-run: 64.2% against 55.1%).
  * CRSS weighted: K 65.2%, A 60.5%, B 52.4%, C 49.9%, O 51.6%, unknown 79.0%.
  * Hit-and-run vehicles: 76.7% (FARS) and 76.0% (CRSS) missing.

**Reliability:** LOW as a covariate, because the known subset is strongly selected.

**Recommendation:** numeric mph with 0 kept as a valid value and 997 → 152 (top-coded); 998/999 → missing. Never
complete-case analyse. Use only with explicit missing-data modelling, and note that the police estimate is made after
the crash.

### 6.2 P_CRASH1 (pre-event movement). CRASH-CIRCUMSTANCE

* **Codes (L):** 0 No driver present / unknown if present; 1 Going straight; 2 Decelerating; 3 Accelerating; 4 Starting
  in road; 5 Stopped in roadway; 6 Passing; 7 Disabled/parked in lane; 8 Leaving parking; 9 Entering parking; 10 Turning
  right; 11 Turning left; 12 U-turn; 13 Backing; 14 Negotiating a curve; 15 Changing lanes; 16 Merging; 17 Successful
  avoidance manoeuvre; 98 Other; 99 Unknown.
* Stable code set. No label changes.
* Unknown: FARS 0.8–1.6%; CRSS 1.2–2.4%. By severity: CRSS K 2.7%, O 1.2%, unknown 15.3%.
* Code 17 falls in CRSS from 0.11–0.19% (2016–19) to 0.01–0.07%.
* PCRASH1_IM (CRSS) equals P_CRASH1 where known.

**Reliability:** HIGH.

### 6.3 P_CRASH2 (critical pre-crash event). CRASH-CIRCUMSTANCE

* **Codes (L):** 57 codes in blocks:
  * 1–9 this vehicle's loss of control (1 tyre, 2 stalled, 3/4 vehicle failure, 5 poor road conditions, 6 too fast for
    conditions, 8 other, 9 unknown cause);
  * 10–14 this vehicle departing lane or road;
  * 15–21 this vehicle turning, crossing, decelerating, backing or U-turn;
  * 50–59 other vehicle in lane;
  * 60–64 other vehicle encroaching from an adjacent or opposite lane, shoulder or median;
  * 65–78 other vehicle from a crossing street, driveway or entrance;
  * 80–85 pedestrian / pedalcyclist;
  * 87–89 animal;
  * 90–92 object;
  * 98 Other; 99 Unknown.
* **Label changes 2019 (meaning-changing, small):**
  * 5 "Poor road conditions" → "**Suddenly Encountered** Poor road conditions";
  * 6 "Traveling too fast for conditions" → "…**or Road Configuration**";
  * 59 adds "/Speed".
* Unknown 0.4–1.7%. CRSS 2018 is the high point at 1.48% unw.

**Recommendation:** collapse to the blocks above. Do not compare code 6 across 2018/2019 at fine level.
**Reliability:** HIGH (blocks).

### 6.4 P_CRASH3 (attempted avoidance manoeuvre). CRASH-CIRCUMSTANCE

* **Codes (L):** 0 no driver; 1 No avoidance manoeuvre; 5 Releasing brakes; 6/7 Steering left/right; 8/9 Braking and
  steering left/right; 10–12 Accelerating (± steering); 15 Braking, unknown steering; 16 Braking; 98 Other; **99
  "Unknown/Not Reported"**.
* **Missing is dominant and rising:**

  | source | 2016 | 2017 | 2018 | 2019–24 |
  |---|---|---|---|---|
  | FARS 99 | 55.8% | 62.5% | 67.3% | 64.4–66.4% |
  | FARS 1 "No avoidance" | 25.7% | 20.1% | 16.9% | |
  | CRSS 99 (weighted) | 70.9% | 72.6% | 69.6% | 71.5–76.1% |

  "No avoidance manoeuvre" was partly recoded to unknown. The 2016 → 2018 FARS shift is a coding-practice break.
* **By severity:** FARS 69.7% (death) against 58.6% (no death). CRSS K 82.6%, A 78.3%, B 74.0%, C 66.6%, O 72.3%.

**Reliability:** LOW.

### 6.5 PCRASH4 (pre-impact stability). CRASH-CIRCUMSTANCE

* **Codes (L):** 0 no driver; 1 Tracking; 2 Skidding longitudinally; 3/4 Skidding laterally clockwise /
  counter-clockwise; 5 lateral, direction unknown; 7 Other loss of control; 9 "Precrash stability unknown".
* **Unstable unknown rate (code 9):**

  | source | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 |
  |---|---|---|---|---|---|---|---|---|---|
  | FARS | 10.2% | 12.3% | **20.5%** | 18.4% | 14.6% | 12.4% | 8.9% | 8.4% | 7.5% |
  | CRSS (weighted) | 7.7% | | | | | | | | 1.4% |

  The "Tracking" share mirrors it (FARS 68.5% in 2018, 83.9% in 2024). TVD between CRSS and FARS for the same year rises
  from 0.107 (2016) to 0.232 (2018).
* **By severity:** FARS 14.9% (death) against 9.8%. CRSS K 14.7%, A 10.1%, B 6.1%, C 3.3%, O 2.9%. Even per year the
  K/O ratio is about 5–7×.

**Reliability:** LOW for trends; MEDIUM within a year.

### 6.6 PCRASH5 (pre-impact location). CRASH-CIRCUMSTANCE

* **Codes (L):** 0; 1 Stayed in original lane; 2 Stayed on roadway, left lane; 3 Stayed on roadway, not known if left
  lane; 4 Departed roadway; 5 Remained off roadway; 6 Returned to roadway; 7 Entered roadway; 9 Unknown.
* Unknown: FARS 1.0–1.8%; CRSS 0.2–0.8%.
* CRSS code 7 drops from 1.8–2.1% (2016–19) to 0.4–0.7% (2020+). Possible coding change, **UNVERIFIED**.

**Reliability:** HIGH.

### 6.7 ACC_TYPE (crash type) and ACC_CONFIG. CRASH-CIRCUMSTANCE

* **ACC_TYPE codes (L).** Labels carry a category letter prefix (e.g. "E34-Same Trafficway, Same Direction-…"). The
  letter-to-code partition was verified over all 15 labelled source-years:

  | letter | codes | category |
  |---|---|---|
  | A | 1–5 | single driver, right roadside departure |
  | B | 6–10 | single driver, left roadside departure |
  | C | 11–16 | single driver, forward impact |
  | D | 20–33 | same trafficway, same direction, rear end |
  | E | 34–43 | same direction, forward impact |
  | F | 44–49 | same direction, angle/sideswipe |
  | G | 50–53 | opposite direction, head-on |
  | H | 54–63 | opposite direction, forward impact |
  | I | 64–67 | opposite direction, angle/sideswipe |
  | J | 68–75 | changing trafficway, turn across path |
  | K | 76–85 | turn into path |
  | L | 86–91 | intersecting straight paths |
  | M | 0 No impact; 92/93 backing; 98 Other crash type; 99 Unknown | miscellaneous |

* The code set is stable. Codes that drop in and out of single years have ≤ 26 rows.
* Unknown (99): FARS 0.38–0.50%; CRSS 0.56–0.93%. "Other crash type" (98) is a substantive category: FARS 13.4–14.7%,
  CRSS 7.9–9.3%.
* **ACC_CONFIG** exists **only in 2023** in both sources. It uses 3-digit codes 0, 101–103, 201–209, 301–306, 401–416,
  501+ with labels. It is a re-specification of crash configuration and cannot be harmonised across years.

**Reliability:** HIGH (ACC_TYPE letter groups).

### 6.8 IMPACT1 (initial contact point). CRASH-CIRCUMSTANCE

* **Codes (L):** 0 Non-collision; 1–12 clock points; 13 Top; 14 Undercarriage; 18 Cargo/vehicle parts set in motion; 19
  "Other Objects (or Person, 2019+) Set-In-Motion"; 20 "Object set in motion, unknown if cargo or other" (2017+); 61–63
  Left / Left-front / Left-back side; 81–83 Right / Right-front / Right-back side; 98 Not Reported; 99 Unknown.
* **Clock-to-side grouping (X via veh_aux A_IMP1):**

  | A_IMP1 | IMPACT1 codes |
  |---|---|
  | 1 | {0} |
  | 2 | {1, 11, 12} |
  | 3 | {2, 3, 4, 81, 82, 83} |
  | 4 | {5, 6, 7} |
  | 5 | {8, 9, 10, 61, 62, 63} |
  | 6 | {13, 14, 18, 19, 20} |
  | 7 | unknown |

  This supports front / right / rear / left / other.
* **Shift in the side-code split:** CRSS impacts coded as side zones 61–63/81–83 rose from 7.0% (2016) to 9.9% (2019),
  then fell to 5.2% (2024) (unw.). The split between zone codes and clock
  points varies by year, so only the grouped side variable is comparable across years.
* Missing (98 + 99): FARS 4.2–5.3%; CRSS 1.4–2.6%. By severity: CRSS K 5.0% against O 1.2%. FARS 5.5% (death) against
  4.1%.
* IMPACT1_IM equals IMPACT1 where known.

**Recommendation:** front (1, 11, 12) / right (2–4, 81–83) / rear (5–7) / left (8–10, 61–63) / other (13, 14, 18–20) /
non-collision (0); 98/99 missing. **Reliability:** HIGH.

### 6.9 M_HARM (most harmful event). POST-CRASH / OUTCOME-DERIVED

* **Codes (L):** 1 Rollover; 2 Fire; 3 Immersion; 4 Gas inhalation; 5 Fell/jumped; 6 Injured in vehicle; 7 Other
  non-collision; 8 Pedestrian; 9 Pedalcyclist; 10 Railway vehicle; 11 Live animal; 12 MV in transport; 14 Parked MV;
  15 Non-motorist on personal conveyance; 16–18 thrown, falling or other non-fixed object; 19–59 fixed objects; 45
  Working MV; 49 Ridden animal; 51 Jackknife; 54 MV in transport strikes or is struck by cargo; 55 MV in motion outside
  trafficway; 72 Cargo/equipment loss; 73 Fallen object; 74 Road vehicle on rails; **91 Unknown object not fixed, 93
  Unknown fixed object (new 2017); 98 "Harmful Event, Details Not Reported" (new 2019)**; 99 Unknown.
* Missing (98 + 99) ≤ 0.3%.
* The label of 72 changed in 2018 from "(harmful to this vehicle)" to "[harmful]". Minor meaning broadening.
* "Most harmful" is chosen by consequence, so the variable is outcome-defined. Use HARM_EV (first harmful event,
  crash-level) as the circumstance variable instead.

---

## 7. Post-crash / outcome variables

### 7.1 ROLLOVER and ROLINLOC. POST-CRASH

* **Codes 2016–21 (L):** 0 No Rollover; 1 Rollover, tripped; 2 Rollover, untripped; 9 Rollover, unknown type. Code 9 is
  a type of rollover, not a missing value.
* **2022+ (L):** 0 No Rollover; **3 Rollover**; **8 Not Applicable**. The tripped/untripped detail is gone.
* **Code 8 = motorcycles (X).** Code 8 covers 97.8% (FARS) and 98.6% (CRSS) of BODY_TYP 80–89 in 2022–24 and 0% of any
  other group. All 27,942 code-8 rows are motorcycle/moped. Before 2022, motorcycles were coded 0 "No Rollover"
  (99.4–99.96% of motorcycles per year). FARS "No Rollover" therefore falls from 85.4% (2021) to 75.4% (2022).
* Non-motorcycle rollover rate (codes 1, 2, 3, 9):

  | source | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 |
  |---|---|---|---|---|---|---|---|---|---|
  | FARS | 17.8% | 17.0% | 16.0% | 15.8% | 17.0% | 16.2% | 15.9% | 15.1% | 15.0% |
  | CRSS (unw.) | 2.94% | | | | 3.22% (2020) | | | | 2.65% |

  This series is smooth across 2022.
* ROLINLOC (location of rollover) gets the same code 8 from 2022.
* veh_aux A_VROLL: 1 = ROLLOVER ∈ {1, 2, 3, 9}; 2 = {0, 8} (X). A_VROLL counts motorcycles as "no rollover" in all
  years.

**Harmonise:** rollover yes = {1, 2, 3, 9}, no = 0. Set motorcycles (BODY_TYP 80–89) to not applicable in all years.

### 7.2 DEFORMED (extent of damage). POST-CRASH

* **Codes (L):** 0 No damage; 2 Minor; 4 Functional; 6 Disabling; **7 "Damage Reported, Extent Unknown" (new 2022)**;
  8 Not Reported; 9 Unknown.
* **Break 2022:** code 8 collapses as code 7 appears. FARS code 8 goes 13.4% → 2.1% while code 7 is 11.8%. CRSS code 8
  goes 21.7% → 1.4% while code 7 is 20.6%. Before 2022, extent-unknown damage was coded 8.
* Codes 7 + 8 (FARS): 6.3% (2016), 12.2% (2019), 8.0% (2020), 13.4% (2021), 13.9% (2022), 16.6% (2023), 19.8% (2024).
  The 2019 and 2021 spikes are state-driven:

  | state | FARS DEFORMED = 8 in 2018 / 2019 / 2020 / 2021 / 2022 |
  |---|---|
  | Texas | 8.1 / 71.3 / 38.6 / 73.0 / 3.4% |
  | New York | 55.7–65.0% in 2018–21 |
  | Washington | 72.4 / 77.2% (2018 / 2019) |

* "Disabling" share: FARS 73.0% (2016) → 62.9% (2024), partly an artefact of the growing missing category.
* **By severity:** FARS (7 + 8 + 9) 9.9% (death) against 17.3% (no death). CRSS K 7.1%, O 22.0%, unknown 73%.

**Harmonise:** 0 / 2 / 4 / 6, with 7, 8 and 9 → missing (same rule all years). **Reliability:** MEDIUM.

### 7.3 TOWED. POST-CRASH

* **Codes (L):**
  * 2016–17: 2 Towed due to disabling damage; 3 Towed not due to disabling damage; 5 Not towed; 8; 9.
  * 2018–21: adds 7 "Towed, Unknown Reason".
  * **2022+: 6 "Towed"** replaces 2, 3 and 7.
* Binary towed ({2, 3, 6, 7}): FARS 86.3% (2016) → 84.3% (2024), smooth. CRSS 35.8–40.8%.
* Missing (8 + 9): FARS 1.1–2.1%. CRSS 2.0% (2016), 10.5% (2018), 4.1–4.8% (2020–22), 10.7–10.9% (2023–24) unw.
* **By severity, the gradient is inverted:** CRSS missing K 1.3% against O 7.6%.

**Harmonise:** towed yes / no; 8/9 → missing.

### 7.4 FIRE_EXP. POST-CRASH

* **Codes:** 0 "**No or Not Reported**", 1 Yes (L). There is no missing code, so absence and non-reporting cannot be
  separated.
* Yes: FARS 3.2–3.8%; CRSS 0.16–0.29%.

**Reliability:** MEDIUM as an outcome. Treat 0 as "not recorded as fire".

### 7.5 DEATHS (FARS). OUTCOME

* An integer count of deaths in the vehicle. No label column and no special codes (0–18 observed).
* 0 = 46.3–49.1% of FARS vehicles; ≥ 1 = 50.9–53.7%.
* Used here as the FARS vehicle-severity stratifier: vehicle with ≥ 1 death n = 261,267, without n = 240,122, pooled.

### 7.6 MAX_VSEV / MXVSEV_IM, NUM_INJV / NUMINJ_IM (CRSS). OUTCOME

* **MAX_VSEV (L):** 0 O; 1 C; 2 B; 3 A; 4 K; 5 Injured, severity unknown; 6 Died prior to crash; 8 No person involved;
  9 Unknown / Not Reported.
* K (unw.): 0.77–1.21%. Code 9 (unw.): 3.7–4.7%.
* **83.3% of MAX_VSEV = 9 vehicles are hit-and-run**, and 52.0% of hit-and-run vehicles have MAX_VSEV = 9 (X).
* MXVSEV_IM has no 9 and agrees with MAX_VSEV in 99.8–99.9% of known rows. It also re-assigns some 5s.
* NUM_INJV: a count; 98 no person; 99 = MAX_VSEV 9 exactly.
* Stable over 2016–24. TVD 2016→17 is 0.007, 2017→18 is 0.032 (CRSS 2017 is slightly atypical), 2019→20 is 0.049.

### 7.7 UNDERIDE (FARS 2016–20) → UNDEROVERRIDE (2021+, both sources). POST-CRASH

* UNDERIDE used 0 none plus detailed 1–8 and 9 unknown.
* UNDEROVERRIDE uses 0 None; 1 Underride; 2 Override; 7 Not Applicable; 8 Not Reported; 9 Unknown.
* Not Reported grows rapidly:

  | source | 2021 | 2022 | 2023 | 2024 |
  |---|---|---|---|---|
  | FARS | 4.6% | 11.2% | 15.6% | 19.1% |
  | CRSS | 13.6% | 35.1% | 47.4% | 52.5% |

**Reliability:** LOW. Exclude.

---

## 8. Behaviour notes (detailed audit belongs to the behaviour domain)

* **SPEEDREL (L):** 0 No; 2 Racing; 3 Exceeded limit; 4 Too fast for conditions; 5 Yes, specifics unknown; 8 No
  driver; 9 Unknown.
  * Unknown: FARS 3.2–5.9%, rising in 2020 to 5.4–5.9%. CRSS 4.2% (2016) → 1.4–1.7% (2018–20) → 2.9% (2024).
  * By severity: CRSS K 4.4% against O 1.7%.
  * veh_aux A_SPVEH: 1 = {2, 3, 4, 5}; 2 = {0, 8, **9**}. The derived flag merges unknown into "not speeding" (X).
* **VEH_ALCH (CRSS):** 1 Alcohol involved; 2 No; 8 No driver; 9 Reported as Unknown.
  * **Break 2019:** unknown is 8.5–10.9% weighted (2016–18), then 27.7% (2019) and 33.6–35.4% (2020–24). TVD 2018→19 =
    0.194.
  * Strong severity dependence: K 43.3% against O 22.3%. In 2021: K 54.3%, O 30.6%.
  * V_ALCH_IM (no unknowns) agrees with VEH_ALCH in 99.6–99.8% of known rows. Use the imputed version, or person-level
    alcohol tables.

---

## 9. CRSS 2016–2018 (unlabelled): can the 2019+ labels be applied?

**Method:** for each vehicle variable, list the CRSS 2016, 2017 and 2018 codes absent from every labelled CRSS 2019–24
code set and from the same-year FARS labels. Then compare TVD between adjacent years with the 2019→20 and 2020→21
baselines.

| variable | % of rows with codes absent from any label set (2016 / 2017 / 2018) | TVD 16→17 / 17→18 / 18→19 | baseline TVD 19→20 / 20→21 |
|---|---|---|---|
| BODY_TYP | 0 / 0.001 (code 41, 1 row) / 0 | **0.144** / 0.041 / 0.027 | 0.035 / 0.043 |
| MOD_YEAR | 0 / 0.003 (years 1952) / 0.001 (1933) | 0.078 / 0.081 / 0.079 | 0.078 / 0.083 |
| NUMOCCS | 0.002 / 0.003 / 0.002 (rare counts 53–95) | 0.015 / 0.019 / 0.004 | 0.012 / 0.007 |
| VSPD_LIM | 0 / 0 / 0 | 0.050 / 0.018 / 0.025 | 0.011 / 0.013 |
| VTRAFWAY | 0 / 0 / 0 | 0.041 / 0.019 / 0.032 | 0.056 / 0.029 |
| VNUM_LAN | 0 / 0 / 0 | 0.058 / 0.032 / 0.042 | 0.014 / 0.015 |
| VALIGN | 0 / 0 / 0 | 0.039 / 0.017 / 0.021 | 0.049 / 0.010 |
| VPROFILE | 0 / 0 / 0 | 0.032 / 0.012 / 0.006 | 0.017 / 0.013 |
| VSURCOND | 0 / 0 / 0 | 0.008 / 0.030 / 0.018 | 0.045 / 0.029 |
| VTRAFCON | 0 / 0 / 0 | 0.022 / 0.010 / 0.057 | 0.079 / 0.011 |
| TRAV_SP | 0 / 0 / 0.001 | 0.029 / **0.084** / 0.017 | 0.032 / 0.012 |
| P_CRASH1 / 2 / 3 | 0 | ≤ 0.034 | 0.010–0.098 |
| PCRASH4 | 0 | 0.038 / 0.008 / 0.005 | 0.025 / 0.012 |
| ACC_TYPE | 0 | 0.028 / 0.029 / 0.022 | 0.080 / 0.058 |
| IMPACT1 | 0 | 0.020 / 0.027 / 0.019 | 0.055 / 0.023 |
| ROLLOVER, DEFORMED, FIRE_EXP, HIT_RUN, TOW_VEH, SPEC_USE, EMER_USE, BUS_USE, SPEEDREL, MAX_VSEV, NUM_INJV, M_HARM | 0 | ≤ 0.035 | ≤ 0.061 |
| TOWED | 0 | 0.032 / **0.099** (new code 7 in 2018) / 0.068 | 0.052 / 0.013 |
| VEH_ALCH | 0 | 0.003 / 0.013 / **0.194** | 0.082 / 0.011 |

**Verdict:**

* For every audited variable, ≥ 99.997% of CRSS 2016–18 rows carry codes that are labelled in CRSS 2019+ or in
  same-year FARS.
* Adjacent-year TVDs are within the range seen between labelled years, except where a known coding change occurs:
  * BODY_TYP 2016: pickups 30/31 (labelled in FARS 2016), replaced by 34 from 2017;
  * TOWED 2018: new code 7;
  * VEH_ALCH 2019 break;
  * TRAV_SP not-reported 2017→18.
* **CRSS 2019 labels can be applied to CRSS 2017–18. For CRSS 2016, use same-year FARS 2016 labels where they differ**
  (BODY_TYP 30/31/32 and code 80's pre-scooter meaning).
* CRSS 2016–18 never use codes introduced in 2019+ (SPEC_USE 10–12/19–23, M_HARM 98, VTCONT_F 4). They do use codes
  retired after 2019, for example HIT_RUN 9, consistent with FARS of the same year.
* Code 41 (BODY_TYP, 1 row, CRSS 2017) is **UNVERIFIED**. Map it to missing.

---

## 10. Differential missingness summary

### 10.1 Missing / unknown rate by year (%, CRSS weighted)

| variable (missing codes) | F16 | F18 | F20 | F22 | F24 | C16 | C18 | C20 | C22 | C24 |
|---|---|---|---|---|---|---|---|---|---|---|
| BODY_TYP (98, 99) | 1.57 | 1.72 | 2.43 | 2.29 | 2.08 | 2.33 | 2.00 | 2.24 | 2.21 | 1.73 |
| BODY_TYP incl. 49, 79, 97 | 1.79 | 1.87 | 2.57 | 2.47 | 2.23 | 3.09 | 5.20 | 5.04 | 6.63 | 6.31 |
| MOD_YEAR (9998, 9999) | 2.35 | 2.47 | 3.09 | 3.07 | 2.96 | 4.36 | 4.37 | 4.97 | 5.07 | 4.72 |
| NUMOCCS (99) | 0.58 | 2.53 | 2.88 | 3.07 | 3.10 | 2.63 | 6.07 | 7.35 | 7.72 | 7.60 |
| GVWR (8, 9) / GVWR_FROM (98, 99) | 0.37 | 0.34 | 2.58 | 2.39 | 2.14 | 1.31 | 1.59 | 2.36 | 3.30 | 2.89 |
| VSPD_LIM (98, 99) | 3.18 | 3.14 | 4.17 | 3.84 | 3.93 | 12.75 | 14.58 | 14.33 | 15.15 | 15.37 |
| VTRAFWAY (8, 9) | 0.28 | 0.52 | 0.65 | 0.72 | 0.86 | 19.60 | 19.31 | 17.45 | 14.99 | 12.86 |
| VNUM_LAN (8, 9) | 0.46 | 1.18 | 1.05 | 1.24 | 1.52 | 26.51 | 32.65 | 29.18 | 28.30 | 22.75 |
| VALIGN (8, 9) | 2.58 | 2.36 | 1.68 | 2.16 | 2.00 | 6.03 | 9.42 | 3.95 | 3.29 | 3.09 |
| VPROFILE (8, 9) | 7.18 | 8.49 | 8.95 | 9.78 | 10.31 | 14.78 | 14.29 | 15.10 | 15.50 | 17.05 |
| VPAVETYP (8, 9) | 23.84 | 24.47 | 27.99 | 25.97 | 27.13 | – | – | – | – | – |
| VSURCOND (98, 99) | 0.91 | 1.39 | 1.71 | 1.74 | 1.99 | 1.17 | 1.63 | 6.24 | 9.48 | 12.31 |
| VTRAFCON (97, 99) | 0.30 | 2.28 | 8.19 | 17.62 | 20.06 | 4.35 | 3.05 | 14.90 | 15.76 | 16.34 |
| TRAV_SP (998, 999) | 62.58 | 59.49 | 60.20 | 60.25 | 61.69 | 54.96 | 49.14 | 52.04 | 52.48 | 55.14 |
| P_CRASH3 (99) | 55.83 | 67.27 | 65.38 | 65.59 | 64.35 | 70.87 | 69.61 | 75.24 | 76.09 | 71.66 |
| PCRASH4 (9) | 10.24 | 20.46 | 14.64 | 8.93 | 7.48 | 7.69 | 4.71 | 2.82 | 2.27 | 1.39 |
| IMPACT1 (98, 99) | 4.60 | 4.33 | 5.07 | 5.28 | 5.02 | 2.09 | 2.57 | 2.43 | 1.46 | 1.44 |
| DEFORMED (7, 8, 9) | 8.53 | 8.11 | 9.96 | 15.74 | 21.58 | 20.70 | 21.74 | 24.69 | 26.00 | 24.95 |
| TOWED (8, 9) | 1.10 | 1.21 | 1.49 | 1.69 | 2.10 | 2.26 | 11.10 | 5.14 | 4.59 | 11.62 |
| SPEEDREL (9) | 4.57 | 3.16 | 5.37 | 5.86 | 5.46 | 4.21 | 1.70 | 1.53 | 2.36 | 2.94 |
| VEH_ALCH (9) | – | – | – | – | – | 10.89 | 8.53 | 35.38 | 34.73 | 34.03 |

### 10.2 By severity (pooled 2016–2024)

Values are percentages missing. FARS columns are unweighted (death vehicle n = 261,267; no-death n = 240,122). CRSS
columns are the mean of yearly weighted rates; unweighted n is K 7,964, A 46,237, B 72,872, C 118,757, O 541,787,
unknown 34,985.

| variable | FARS death veh | FARS no-death veh | CRSS K | A | B | C | O | MAX_VSEV unknown |
|---|---|---|---|---|---|---|---|---|
| BODY_TYP | 0.34 | 3.81 | 0.16 | 0.04 | 0.03 | 0.14 | 0.85 | 27.6 |
| MOD_YEAR | 1.04 | 4.69 | 0.98 | 0.75 | 0.38 | 0.42 | 2.16 | 59.4 |
| NUMOCCS | 0.14 | 5.31 | 0.18 | 0.61 | 0.86 | 0.80 | 3.46 | 71.9 |
| GVWR_FROM (2020+) | 0.54 | 4.33 | 0.43 | 0.47 | 0.24 | 0.54 | 1.70 | 28.5 |
| VPICBODYCLASS (2020+) | 0.46 | 4.40 | 2.38 | 5.59 | 3.97 | 8.79 | 7.82 | 35.9 |
| VSPD_LIM | 3.52 | 3.52 | 6.43 | 12.39 | 8.35 | 14.84 | 13.97 | 23.1 |
| VTRAFWAY | 0.54 | 0.67 | 6.89 | 11.76 | 10.94 | 16.65 | 17.01 | 24.7 |
| VNUM_LAN | 1.04 | 1.27 | 16.67 | 20.37 | 19.54 | 24.81 | 28.27 | 36.2 |
| VALIGN | 1.88 | 2.33 | 3.25 | 4.03 | 4.53 | 6.05 | 4.85 | 14.5 |
| VPROFILE | 8.31 | 9.49 | 11.86 | 13.59 | 13.89 | 16.10 | 14.33 | 28.3 |
| VPAVETYP | 24.50 | 28.06 | – | – | – | – | – | – |
| VSURCOND | 1.72 | 1.37 | 3.78 | 5.04 | 5.59 | 5.81 | 5.28 | 14.9 |
| VTRAFCON | 9.93 | 9.67 | 13.99 | 13.26 | 10.71 | 10.95 | 10.38 | 20.3 |
| TRAV_SP | 64.19 | 57.03 | 65.15 | 60.54 | 52.42 | 49.87 | 51.64 | 79.0 |
| P_CRASH1 | 1.09 | 1.23 | 2.68 | 1.26 | 0.75 | 0.69 | 1.21 | 15.3 |
| P_CRASH3 | 69.69 | 58.57 | 82.64 | 78.32 | 73.98 | 66.62 | 72.31 | 92.3 |
| PCRASH4 | 14.87 | 9.76 | 14.72 | 10.05 | 6.14 | 3.31 | 2.86 | 15.1 |
| IMPACT1 | 5.47 | 4.08 | 4.96 | 3.51 | 2.00 | 1.19 | 1.18 | 16.6 |
| DEFORMED (7, 8, 9) | 9.93 | 17.28 | 7.09 | 13.86 | 12.85 | 20.45 | 22.02 | 73.0 |
| TOWED | 0.95 | 2.28 | 1.30 | 2.22 | 3.29 | 4.87 | 7.62 | 6.5 |
| SPEEDREL | 5.77 | 4.04 | 4.38 | 2.36 | 1.71 | 1.29 | 1.65 | 18.2 |
| VEH_ALCH | – | – | 43.31 | 24.69 | 20.62 | 21.15 | 22.34 | 88.4 |

**Reading:**

1. Vehicle-attribute missingness (BODY_TYP, MOD_YEAR, NUMOCCS, GVWR, VIN decode) is concentrated in hit-and-run and
   unknown-occupant vehicles. Excluding hit-and-run vehicles, CRSS weighted BODY_TYP missing is K 0.15%, O 0.11%, and
   MOD_YEAR missing is K 0.89%, O 0.22%. Severe-crash vehicles are documented slightly *better* or similarly.
2. In CRSS, roadway descriptors (speed limit, trafficway, lanes, alignment, profile) are **more** complete for K and A
   crashes than for B, C and O. For example VSPD_LIM is 6.4% missing (K) against 14.0% (O), and VTRAFWAY 6.9% against
   17.0%. Complete-case analysis would over-represent severe crashes relative to PDO crashes.
3. Behaviour and circumstance fields that require reconstruction (TRAV_SP, P_CRASH3, PCRASH4, VEH_ALCH, SPEEDREL) are
   **less** complete for K crashes. Complete-case analysis would under-represent fatal crashes.
4. In FARS, roadway missingness is essentially independent of whether the vehicle had a death. The exceptions are the
   state-driven VTRAFCON and DEFORMED patterns.

---

## 11. vpicdecode: columns, completeness, safety technology, curb weight

**Columns:** 198–204 per source-year (FARS adds STATE / STATENAME; NONLANDUSE(ID) appears 2021+ in FARS and 2022+ in
CRSS; CRSS has POLKVIN in two years). Paired `X` / `XID` columns are present: the text value plus the vPIC numeric id.
Groups:

* **Identity:** MAKE, MODEL, MODELYEAR, MANUFACTURERFULLNAME, SERIES, TRIM, VEHICLETYPE, BODYCLASS, VEHICLEDESCRIPTOR,
  VINDECODEDON, VINDECODEERROR, NOTE.
* **Dimensions / weight:** CURBWEIGHTLB, GROSSVEHICLEWEIGHTRATINGFROM / TO, GROSSCOMBWEIGHTRATING*, WHEELBASE*,
  TRACKWIDTHIN, DOORSCOUNT, SEATSCOUNT, SEATROWSCOUNT, WHEELSCOUNT, WHEELSIZE*, AXLESCOUNT, AXLECONFIGURATION,
  BUS*, TRUCKBED*, TRUCKBODYCABTYPE.
* **Powertrain:** ENGINE*, DISPLACEMENT*, FUELTYPEPRIMARY / SECONDARY, ENGINEELECTRIFICATIONLEVEL, BATTERY*, CHARGER*,
  EVDRIVEUNIT, TRANSMISSION*, DRIVETYPE, TOPSPEEDMPH.
* **Passive safety:** AIRBAGLOCFRONT / SIDE / CURTAIN / KNEE / SEATCUSHION, SEATBELTTYPE, PRETENSIONER,
  OTHERRESTRAINTSYSTEMINFO.
* **Active safety / ADAS:** ANTILOCKBRAKESYSTEM, ELECTRONICSTABILITYCONTROL, TRACTIONCONTROL, TPMS,
  FORWARDCOLLISIONWARNING, CRASHIMMINENTBRAKING (AEB), DYNAMICBRAKESUPPORT, PEDESTRIANAUTOEMERGENCYBRAKING,
  REARAUTOMATICEMERGENCYBRAKING, LANEDEPARTUREWARNING, LANEKEEPINGASSISTANCE, LANECENTERINGASSISTANCE, BLINDSPOTWARNING,
  BLINDSPOTINTERVENTION, ADAPTIVECRUISECONTROL, BACKUPCAMERA, PARKASSIST, REARCROSSTRAFFICALERT, DAYTIMERUNNINGLIGHT,
  HEADLAMPLIGHTSOURCE, SEMIAUTOHEADLAMPBEAMSWITCHING, ADAPTIVEDRIVINGBEAM, AUTOMATICCRASHNOTIFICATION, EVENTDATARECORDER,
  KEYLESSIGNITION, AUTOPEDESTRIANALERTINGSOUND, SAEAUTOMATIONLEVEL_FROM / TO, ACTIVESAFETYSYSNOTE.

**Value coding of ADAS fields** (text values observed): `Standard`, `Optional`, `Not Available`, `Not Applicable`,
null.

* `Not Applicable` is assigned to motorcycles. Its share (FARS 10.0–11.8%, CRSS 2.8–4.0%) equals VEHICLETYPE =
  "MOTORCYCLE" (10.0–11.7% and 2.8–4.0%) (X).
* `Not Available` is ≤ 0.6%.
* For **ELECTRONICSTABILITYCONTROL**, ANTILOCKBRAKESYSTEM and TRACTIONCONTROL, the non-null values are essentially only
  "Standard" (100.0% of non-null ESC in every model-year band). No vehicle is recorded as lacking ESC.

**Coverage depends on model year, so null ≠ "not equipped".** Light vehicles (VEHICLETYPE car / MPV / truck), FARS +
CRSS 2016–24 pooled:

| model-year band | n | ESC non-null | AEB (CRASHIMMINENTBRAKING) non-null | of which Std / Opt | FCW non-null | LDW non-null | backup camera non-null |
|---|---|---|---|---|---|---|---|
| < 2000 | 79,898 | 0.0% | 0.0% | – | 0.0% | 0.0% | 0.0% |
| 2000–05 | 210,108 | 0.0% | 0.0% | – | 0.0% | 0.0% | 0.0% |
| 2006–09 | 181,922 | 0.0% | 0.0% | – | 0.0% | 0.0% | 0.0% |
| 2010–12 | 135,319 | 0.0% | 0.0% | – | 0.0% | 0.0% | 0.0% |
| 2013–15 | 194,212 | 0.1% | 0.1% | – | 0.0% | 0.0% | 0.0% |
| 2016–18 | 191,885 | 51.3% | 22.9% | 57 / 43 | 22.1% | 21.5% | 49.7% |
| 2019–21 | 113,037 | 75.6% | 46.9% | 85 / 14 | 57.0% | 51.7% | 75.7% |
| 2022+ | 35,677 | 88.3% | 72.6% | 95 / 5 | 81.3% | 79.1% | 86.2% |

By single model year (FARS 2024 file), ESC = "Standard":

| MY | 2015 | 2016 | 2017 | 2018 | 2020 | 2022 | 2024 |
|---|---|---|---|---|---|---|---|
| ESC Standard | 0.2% | 2.7% | 83.2% | 72.2% | 72.1% | 85.2% | 80.4% |

ESC has been mandatory for light vehicles from about MY 2012 (general knowledge, so ESC presence for MY ≤ 2016 cannot be
read from these data). The near-zero coverage for MY 2012–2016 therefore shows that **vPIC equipment fields are
populated only for roughly MY ≥ 2017**.

* "Optional" (AEB 43% of non-null for MY 2016–18) means the feature was available but its fitment to this vehicle is
  unknown.
* The same model year decoded in different data years gives similar rates (MY 2018 ESC Standard: FARS 2020 file 68.9%,
  FARS 2024 file 72.2%). No large decode-vintage effect was detected.
* Decode dates differ by file. VINDECODEDON for 2016–19 files is Aug / Dec 2021 (re-decoded). For 2020+ files it is
  roughly 1–2 years after the data year.

**Weights:**

* **CURBWEIGHTLB** is non-null for only 0.17–1.44% of light vehicles in any source-year. **Unusable.**
* GROSSVEHICLEWEIGHTRATINGFROM (text, for example "Class 2E: 6,001 - 7,000 lb") is non-null for 64–97% of light vehicles
  depending on model year (2022+: 96.8%). It is usable as a GVWR sub-class for light trucks.
* Passive-safety fields (AIRBAGLOCFRONT, SEATBELTTYPE) are 59–85% populated (FARS 59–68%, CRSS 75–84%), with older
  vehicles less populated.

**VINDECODEERROR:** "0" for 98.8–99.3% of FARS rows. In CRSS it is 99.3% for 2016 but only 88.6–91.0% for 2018–24, the
remainder being mostly "1". The meaning of error codes 1, 10, 14 and 400 is **UNVERIFIED** (no label). Do not interpret
it beyond "non-zero = decode warning".

**Verdict:**

* Body class, vehicle type, fuel type and electrification level: usable, with ≥ 95% populated for decoded vehicles.
* ADAS and ESC fields: usable **only** as "Standard (known fitted)" against "unknown", and only for MY ≥ 2017 light
  vehicles. Never code null or Optional as "not equipped".
* Curb weight: not usable.

---

## 12. Cross-cutting findings

1. **2020 restructuring:**
   * GVWR → GVWR_FROM / TO, with a scope change from trucks only to all vehicles;
   * new ICFINALBODY and VPICBODYCLASS;
   * DR_SF and VEH_SC moved out of the vehicle table;
   * HIT_RUN lost its unknown code;
   * veh_aux A_BODY began using vPIC.
2. **2022 restructuring of outcome codes:**
   * ROLLOVER: tripped / untripped detail removed, motorcycles moved to "Not Applicable";
   * DEFORMED: code 7 added;
   * TOWED: collapsed to towed / not towed;
   * VTRAFWAY: code 7 added;
   * TOW_VEH: code 7 added.
   Harmonise at the coarser level.
3. **"Not reported" growth that substitutes for a substantive default:**
   * VTRAFCON / VTCONT_F (state-specific, from 2018);
   * VSURCOND in CRSS 2020+;
   * UNDEROVERRIDE 2021+;
   * DEFORMED 7 / 8;
   * SPEC_USE (98 merged into 0 from 2021);
   * P_CRASH3 2017–18;
   * PCRASH4 2017–2020 hump;
   * VEH_ALCH 2019.
   Trends in the substantive category are confounded by these changes.
4. **Hit-and-run vehicles** generate most vehicle-attribute missingness. NUMOCCS for them changed from a default of 1
   (2016) to unknown (2017+).
5. **CRSS roadway completeness is outcome-dependent.** K vehicles are about 2× more complete than O vehicles for speed
   limit and trafficway. FARS roadway completeness is not severity-dependent.
6. **Label rewordings 2016–17 → 2018+** ("Unknown" → "Reported as Unknown"; "> 26,000" → "greater than 26,000") are
   cosmetic. Meaning-changing rewordings:
   * BODY_TYP 80 / 82 / 88 (2017) and 96 (2024);
   * VTRAFWAY 2 (2017);
   * P_CRASH2 5 / 6 (2019);
   * SPEC_USE 0 (2021);
   * TOW_VEH 0–4 (2022);
   * IMPACT1 19 (2019);
   * M_HARM 72 (2018).
7. **CRSS 2016–18 labels:** apply CRSS 2019 labels. Use FARS 2016 for CRSS 2016 BODY_TYP 30 / 31 / 32 and the 2016
   meaning of 80 / 82 / 88.
8. **veh_aux** derived variables are unlabelled and partly redefined. A_BODY breaks in 2020; A_SPVEH merges unknown with
   "no". They are useful only as cross-checks.

---

## 13. Recommended harmonised definitions (summary)

Implementable recipes are also given in the structured summary returned with this audit. Key rules:

* Never treat 8/9, 98/99, 997/998/999 or 9998/9999 as zero or as a negative category. Codes 0 that mean "non-trafficway",
  "no driver present" or "stopped (0 mph)" are substantive, not missing.
* Harmonise to the coarsest level that is stable across 2016–24 (§§4–7). Keep explicit "type unknown" levels for CRSS
  body type.
* Classify timing per §3 before modelling.
* In CRSS, carry explicit missing-indicator levels for roadway variables and model ascertainment, rather than using
  complete cases.

---

## 14. Open questions / UNVERIFIED items

1. BODY_TYP code 41 (CRSS 2017, 1 row): no label in any year. Mapped to missing.
2. Why HIT_RUN = Yes steps up in 2020 (FARS 3.9% → 4.8%; CRSS 6.2% → 7.5%). It may be a real pandemic-era change or a
   definition change linked to removing code 9.
3. Meaning of vpicdecode VINDECODEERROR codes 1, 10, 14, 400, and why CRSS 2018+ has about 10% "1" against about 0.5% in
   FARS.
4. Why CRSS 2021–22 VPICBODYCLASS = 999 for vehicles with a clean vpicdecode decode (4,306 and 6,874 rows).
5. Meaning of the veh_aux A_* codes: the partitions were verified by cross-tab, but the labels are inferred. Why A_IMP1
   assigns some IMPACT1 98 / 99 rows to specific sides (perhaps from IMPACT1_IM).
6. Whether the CRSS PCRASH5 code 7 drop (2019→2020), CRSS VALIGN not-reported hump (2017–19) and CRSS VSPD_LIM 65 mph
   share in 2016 reflect coding or sampling changes.
7. The procedure behind FARS state-level VTRAFCON = 97 and DEFORMED = 8 surges (Texas, New York, Washington, Oregon,
   California, Michigan, South Dakota). Probably PAR-form or state data-transfer changes; not verifiable from these data.
8. ACC_CONFIG appears only in 2023 files. Its intended continuation is unknown.
9. Interpretation of vPIC "Optional" for an individual vehicle, and of null for MY ≥ 2017 (catalog gap or not fitted).

---

## 15. Reproducibility

Scripts are in `/tmp/claude-0/-home-user-nhtsa-stats-US/dd56b1ab-53ab-5c90-8154-cdf8a010f996/scratchpad/audit_scripts/`.
They are outside the repository and not committed.

| script | purpose |
|---|---|
| 01_dist.py | code × source-year counts for about 60 vehicle variables joined to labels |
| show.py, labdiff.py, codeset.py | pivots, label-text diffs (normalised), code-set changes |
| 02_modyear.py, 21_age.py | model year and vehicle age |
| 03_travsp.py | TRAV_SP special codes |
| 04_crss_unlab.py | CRSS 2016–18 overlap and TVD |
| 05_diffmiss.py, 06_diffmiss_show.py, 07_extra_miss.py, 22_sev_hr.py | missingness by year, severity, hit-and-run and state |
| 08_vpic.py, 09_vpic_orphans.py, 10_vpic_values.py, 11_vpic_my.py, 12_vpic_vintage.py, 15_bodyclass_vpic.py, 20_vpic_mismatch.py | vpicdecode join, coverage, values, model-year dependence |
| 13_bodygroup.py, 14_body_detail.py | body-group validation against vPIC, A_BODY, GVWR, ROLLOVER |
| 16_aux_checks.py, 17_im_checks.py, 18_numoccs.py, 19_rollover_mc.py | veh_aux, CRSS *_IM, NUMOCCS, rollover, towed and deformed checks |

Run each with `cd /home/user/nhtsa-stats-US && POLARS_MAX_THREADS=2 uv run python <script>`.
