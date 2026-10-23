# Audit appendix: driver behaviour and contributing factors (FARS and CRSS, 2016-2024)

Scope: driver behaviour, contributing-factor and driver-history variables in FARS and CRSS, 2016-2024. This covers
the multi-row factor tables (`distract`, `drimpair`, `factor`, `maneuver`, `violatn`, `vision`, `driverrf`, `personrf`,
`crashrf`), the driver fields of the `vehicle` table (SPEEDREL, TRAV_SP, VSPD_LIM, DR_SF1-4, the FARS licence and
driving-record block, DR_HGT, DR_WGT, DR_ZIP), the crash-level CF1-3, the person-level P_SF1-3, and the derived `*_aux`
flags A_SPCRA, A_DIST, A_DROWSY, A_SPVEH, A_DRDIS, A_DRDRO, A_LIC_S, A_LIC_C, A_CDL_S and A_MC_L_S.

Status: audit only. No data or source code was modified. Every number below was computed from the typed Parquet cache
(`data/interim/{FARS|CRSS}/{table}/{year}.parquet`) or from `outputs/audit/codebook.csv`. The scripts are listed in §20.

---

## 1. Purpose and scope

For every driver-behaviour variable likely to enter a severity, risk-factor or quasi-induced-exposure (QIE) analysis,
this appendix records:

* where the variable is available (source × year);
* what each code means, and the evidence for that meaning;
* coding and definition breaks between years;
* which codes are missing or uninformative (Unknown, Not Reported, No Driver), how often they occur, and **whether that
  rate depends on crash or driver severity**;
* whether the multi-row tables can be reduced to one row per vehicle without losing information;
* a timing class for leakage control. The classes are **PRE-CRASH** (administrative record existing before the crash),
  **CRASH-CIRCUMSTANCE** (a description of the crash coded after the event by police or NHTSA analysts) and
  **POST-CRASH / OUTCOME-DERIVED** (legal or medical consequences);
* a reliability verdict and an implementable harmonised definition (§17);
* a defensible culpability indicator for QIE (§16).

Out of scope: alcohol and drug *test results* (person ALC_*, DRUG*, and the FARS `drugs` table), which belong to the
substance domain, and non-motorist distraction (`nmdistract`). P_CRASH1-2 belong to the vehicle audit; P_CRASH2 is used
here only as an input to culpability (§16).

### 1.1 Evidence conventions

* **L (label):** the code→label pair appears in `codebook.csv`, or in the embedded `<VAR>NAME` column, for that
  source-year. Labels were compared after normalisation (lower case, alphanumerics only). `codebook.csv` lists only
  codes that occur in the data.
* **D (distribution):** code shares per source-year. Year-to-year change is the total variation distance (TVD) in
  percentage points (pp).
* **X (cross-tab):** the meaning is confirmed by cross-tabulation against an independently labelled variable. For
  example, A_SPVEH × SPEEDREL, SPEEDREL=8 × DR_PRES, or TRAV_SP − VSPD_LIM × SPEEDREL.
* **UNVERIFIED:** the meaning rests on general familiarity with NHTSA conventions and could not be confirmed from the
  data.
* **Driver** means an in-transport vehicle row with `DR_PRES = 1` (driver present). Unless stated otherwise, rates are
  computed over drivers.
* FARS percentages are row shares (FARS is a census). CRSS percentages are **weighted by `WEIGHT`** unless marked
  "unw.". Design-based standard errors (PSU/PSUSTRAT) were not needed for these descriptive audit numbers. They must be
  used in inference.
* Severity strata: CRSS crash `MAX_SEV` (0 = O, 1 = C, 2 = B, 3 = A, 4 = K; 5/6/8/9 = "unk/other"). FARS: the driver's
  own `INJ_SEV`, coded killed (4), survived (0-3, 5) or unknown (9, or no person row).

---

## 2. Tables, keys and availability

### 2.1 Table structure

| table | key (FARS: +YEAR, ST_CASE; CRSS: CASENUM) | rows/yr FARS | rows/yr CRSS | labels |
|---|---|---|---|---|
| vehicle (SPEEDREL, TRAV_SP, VSPD_LIM, DR_SF1-4, licence block) | VEH_NO | 51,623-61,802 | 82,149-97,625 | FARS all; CRSS 2019+ |
| distract | VEH_NO + MDRDSTRD (≤2019) / DRDISTRACT (2020+) | 51,651-61,826 | 82,178-97,657 | same |
| drimpair | VEH_NO + DRIMPAIR | 51,797-62,007 | 82,259-97,728 | same |
| factor | VEH_NO + MFACTOR (≤2019) / VEHICLECC (2020+) | 51,682-61,893 | 82,181-97,658 | same |
| maneuver | VEH_NO + MDRMANAV (≤2019) / MANEUVER (2020+) | 51,632-61,806 | 82,105-97,628 | same |
| violatn | VEH_NO + MVIOLATN (≤2019) / VIOLATION (2020+) | 55,088-66,261 | 87,788-103,926 | same |
| vision | VEH_NO + MVISOBSC (≤2019) / VISION (2020+) | 51,676-61,834 | 82,132-97,643 | same |
| driverrf (2020+) | VEH_NO + DRIVERRF | 60,366-68,116 | 88,844-98,392 | yes |
| personrf (2020+) | VEH_NO + PER_NO + PERSONRF | 86,409-97,523 | 122,396-133,742 | yes |
| crashrf (2020+) | CRASHRF | 36,197-40,096 | 50,292-54,879 | yes |
| veh_aux / acc_aux | VEH_NO / crash | = vehicle / accident | = vehicle / accident | **none** |

Every in-transport vehicle has **at least one row** in each of distract, drimpair, factor, maneuver, violatn and vision,
in every source-year (0 unmatched vehicles, X). Every driverrf vehicle (2020+) likewise has at least one row. The
multi-row keys are unique (`table_inventory.csv`). The exception is CRSS 2018 `maneuver`: its key is CASENUM + VEH_NO,
so it holds at most one row per vehicle, while other years hold up to 2-3. The effect is ≤ 0.01% of vehicles (§3).

### 2.2 Renamings and replacements

| concept | 2016-2019 | 2020-2024 | evidence |
|---|---|---|---|
| distraction | distract.MDRDSTRD | distract.DRDISTRACT | same codes; TVD 2019→2020 = 2.6 pp FARS, 3.0 pp CRSS |
| vehicle contributing factor | factor.MFACTOR | factor.VEHICLECC | code 98 removed (§9.3); TVD 7.5 pp FARS, **24.0 pp CRSS** |
| driver manoeuvre to avoid | maneuver.MDRMANAV | maneuver.MANEUVER | TVD 1.4 / 4.6 pp |
| violations charged | violatn.MVIOLATN | violatn.VIOLATION | TVD 1.3 / 3.3 pp |
| vision obscured | vision.MVISOBSC | vision.VISION | TVD 0.4 / 0.3 pp |
| driver-related factors | vehicle.DR_SF1-DR_SF4 (wide, ≤ 4 codes) | driverrf.DRIVERRF (long, ≤ 9 codes) | §7 |
| person-related factors | person.P_SF1-P_SF3 | personrf.PERSONRF | §10 |
| crash-related factors | accident.CF1-CF3 | crashrf.CRASHRF | §10 |
| previous suspensions (FARS) | PREV_SUS (2016-17) | PREV_SUS1, PREV_SUS2, PREV_SUS3 (2018+) | §11.4 |

### 2.3 Availability gaps that constrain cross-source work

* **CRSS has none of the driver licence or history variables.** L_STATUS, L_COMPL, L_TYPE, L_RESTRI, L_ENDORS,
  CDL_STAT, PREV_*, FIRST_*/LAST_*, DR_HGT, DR_WGT and DR_DRINK are FARS-only (`variable_availability.csv`).
* CRSS `veh_aux` contains A_SPVEH only. A_DRDIS, A_DRDRO, A_LIC_S, A_LIC_C, A_CDL_S and A_MC_L_S are FARS-only.
  CRSS `acc_aux` has A_SPCRA (2016-24) and A_DIST (**2020-24 only**). It has no A_DROWSY.
* **The CRSS driver-related-factor code list is a strict subset of FARS** (§7.3). Most "driver error" codes (failure to
  yield 38, disobey control 39, improper lane use 28, following improperly 26, …) are never used in CRSS.
* No driver-behaviour variable has a CRSS `*_IM` imputed version.

---

## 3. Multi-row tables: can they be pivoted to one row per vehicle? (key analysis 3)

The codes of each table were grouped into five classes: *none* (0), *substantive*, *unknown* (Reported as Unknown),
*not reported* (NR) and *no driver*. The class codes are listed in §17. Per vehicle and year:

| table | % vehicles with > 1 row (FARS) | (CRSS) | max rows | none + substantive | unknown + substantive | NR + anything | no-driver + other rows |
|---|---|---|---|---|---|---|---|
| distract | 0.03-0.11 | 0.03-0.06 | 4 / 3 | 0 (1 vehicle, FARS 2017) | 0 | 0 | 0 |
| drimpair | 0.29-0.41 | 0.09-0.16 | 3 / 3 | 0 | 0 | 0 | 0 |
| factor | 0.09-0.12 | 0.02-0.09 | 14 / 14 | 0 | 0 | 0 | 0 |
| maneuver | 0.01-0.02 | 0.00-0.01 | 2 / 3 | 0 | 0 | 0 | 0 |
| vision | 0.05-0.10 | 0.02-0.04 | 4 / 3 | 0 | 0 | 0 | 0 |
| **violatn** | **3.56-4.20** | **4.09-4.98** | 13 / 17 | 0 | **8-46 / yr** (FARS), **105-213 / yr** (CRSS) | 0 | 0 |
| **driverrf** (2020+) | **8.14-8.94** | **0.98-2.55** | 9 / 6 | 0 | 0 | 0 | 0 |
| DR_SF1-4 (2016-19) | ≥ 2 non-zero slots: 12.3-13.1, incl. the 99×4 unknown pattern (3.9-4.7) | 3.8-5.7, incl. 99×4 (1.1-4.4) | 4 (cap) | 0 | 0 | – | – |

Conclusions:

1. **The none, unknown, NR and no-driver classes never co-occur with substantive codes.** The exceptions are one
   FARS 2017 vehicle with both distract 0 and a distraction code, and violatn, where "Unknown Violation(s)" (99) is listed next to specific violations for 8-46 FARS and 105-213 CRSS
   vehicles per year. A per-vehicle category variable (substantive / none / unknown / NR / no-driver) is therefore
   lossless. For violatn, give the substantive class precedence over 99.
2. **Pivoting to indicator columns is lossless. Pivoting to a single code is not**, for violatn (3.6-5.0% of vehicles
   carry multiple charges) and driverrf (8-9% of FARS drivers). Use one indicator per code group (any-of), never the
   "first" code.
3. **DR_SF1-4 are filled left to right.** There are 0 cases of DR_SF1 = 0 with DR_SF2 ≠ 0. "Unknown" (99) is written
   into all four slots. Of FARS drivers in 2016, 4.92% have four non-zero slots, but 4.66% are the 99-99-99-99 unknown
   pattern. The four-slot cap therefore truncates only about 0.26% of FARS drivers. In 2020-24, 290 FARS drivers (about
   0.1%) have ≥ 5 driverrf codes, which the old format could not have held.

---

## 4. Speeding: SPEEDREL, TRAV_SP, VSPD_LIM

### 4.1 Availability and codes

SPEEDREL is in `vehicle` for both sources and every year. Its code set is identical in all 18 source-years:
{0, 2, 3, 4, 5, 8, 9}.

| code | label (L) | class | evidence |
|---|---|---|---|
| 0 | No | no | L |
| 2 | Yes, Racing | yes | L |
| 3 | Yes, Exceeded Speed Limit | yes | L; X: 97.4% (FARS) and 91.3% (CRSS) of code-3 drivers with known speeds have TRAV_SP > VSPD_LIM |
| 4 | Yes, Too Fast for Conditions | yes | L; X: only 60.5% (FARS) and 18.5% (CRSS) over the limit, as the definition implies |
| 5 | Yes, Specifics Unknown | yes | L |
| 8 | No Driver Present/Unknown if Driver Present | not applicable | X: SPEEDREL = 8 ⇔ DR_PRES ∈ {0, 9}. FARS 3,075 + 48 = 3,123 rows, CRSS 1,798 + 26 = 1,824 rows, with no exceptions |
| 9 | FARS 2016-17 "Unknown"; FARS 2018+ and CRSS 2019+ "Reported as Unknown" | unknown | L |

**X-verification of the "yes" set across all 18 source-years, including unlabelled CRSS 2016-18:**
`veh_aux.A_SPVEH = 1 ⇔ SPEEDREL ∈ {2, 3, 4, 5}` with 0 disagreements in every source-year. `acc_aux.A_SPCRA = 1 ⇔`
some vehicle in the crash has SPEEDREL ∈ {2, 3, 4, 5}, again with 0 disagreements in every source-year.

### 4.2 Coding changes

* **2018 label change on code 9**, from "Unknown" to "Reported as Unknown" (FARS). It coincides with a level drop in
  code-9 use: FARS 4.54% → 3.18% of drivers (2017 → 2018), and CRSS 3.35% → 1.70%. This is meaning-relevant: the new
  wording restricts code 9 to cases where the report itself says "unknown", in line with the wider introduction of a
  separate "Not Reported" convention in 2018 (§5). SPEEDREL has no Not Reported code. Where a PAR is silent on speed,
  the case was presumably coded 0 ("No"). That is **UNVERIFIED**, but SPEEDREL=0 drivers include 10.3% (FARS) and 2.6%
  (CRSS) whose recorded TRAV_SP is ≥ 10 mph over the limit (§4.4).
* **2020 level shift in FARS:** "yes" rose from 17.26% to 19.30%, driven by code 5 (2.66% → 3.49%) and code 2 (0.16% →
  0.27%). "Unknown" rose from 3.72% to 5.40% and stayed at 5.4-5.9% through 2024. CRSS shows no comparable break
  ("yes" 5.36% → 6.29% in 2020, then back to 5.4-5.8%). The FARS shift may be partly real (pandemic-era speeding), but a
  coding contribution cannot be excluded.
* **CRSS 2016-17** used code 9 more often (4.22%, 3.35%) and code 5 less often (0.42%, 0.80%) than 2018+. TVD
  2016→2017 = 1.1 pp and 2017→2018 = 1.9 pp (unweighted), so the code set is stable. See §13.

### 4.3 Rates by year (drivers)

| year | FARS yes | FARS unknown (9) | CRSS yes (wtd) | CRSS unknown (9) |
|---|---|---|---|---|
| 2016 | 17.93 | 4.59 | 5.78 | 4.22 |
| 2017 | 17.21 | 4.54 | 6.20 | 3.35 |
| 2018 | 16.94 | 3.18 | 5.86 | 1.70 |
| 2019 | 17.26 | 3.72 | 5.36 | 1.36 |
| 2020 | 19.30 | 5.40 | 6.29 | 1.53 |
| 2021 | 18.61 | 5.77 | 5.82 | 2.03 |
| 2022 | 18.43 | 5.90 | 5.38 | 2.37 |
| 2023 | 18.67 | 5.70 | 5.68 | 2.72 |
| 2024 | 18.78 | 5.50 | 5.46 | 2.94 |

Mix of "yes" subtypes: FARS 2016 is 7.41% exceeded limit, 8.01% too fast, 2.35% specifics unknown and 0.16% racing.
CRSS 2016 is 0.66%, 4.69%, 0.42% and 0.01%. In CRSS, "speeding" is overwhelmingly "too fast for conditions": 76-81% of CRSS "yes" is code 4, against 41-45% in
FARS (2016 and 2024).

### 4.4 Severity dependence (key analysis 2)

**CRSS, by crash MAX_SEV (weighted % of drivers):**

| MAX_SEV | 2016-19 yes | 2016-19 unknown | 2020-24 yes | 2020-24 unknown |
|---|---|---|---|---|
| O | 5.30 | 2.33 | 4.99 | 2.28 |
| C | 6.18 | 1.59 | 6.51 | 1.92 |
| B | 7.70 | 1.67 | 7.60 | 2.32 |
| A | 10.13 | 1.68 | 11.10 | 3.06 |
| K | 12.14 | **3.42** | 15.31 | **3.79** |
| unk/other | 5.83 | **25.55** | 7.08 | 6.72 |

By year, code-9 use in K crashes runs 2.2-5.7%, against 1.2-3.7% in O crashes. In 2024 it is 5.72% (K) against 2.93%
(O). **"Yes" doubles to triples from O to K, and "unknown" is about 1.5× higher in fatal crashes.** It is higher still
when crash severity itself is unknown (25.6% in 2016-19).

**FARS, by the driver's own outcome:**

| group | 2016-19 yes | 2016-19 unknown | 2020-24 yes | 2020-24 unknown |
|---|---|---|---|---|
| driver killed | 26.54 | 4.61 | 28.60 | 7.05 |
| driver survived | 9.84 | 2.60 | 10.70 | 3.71 |
| driver injury unknown | 11.28 | 27.49 | 12.79 | 23.86 |

"Unknown" is 1.8-1.9× higher for killed drivers, and about 7× higher when the driver's injury is unknown. That group is
mostly hit-and-run drivers (§11). Crossing CRSS by the driver's own INJ_SEV gives the same gradient: unknown 1.25% (C),
1.61% (O), 2.36% (A), 4.82% (K), 18.47% (unknown injury).

### 4.5 TRAV_SP and VSPD_LIM: availability and use as validation

Codes (L, every year). TRAV_SP: 0 = stopped in-transport vehicle; 1-151 = mph ("001 MPH" …); 997 = > 151 mph;
998 = Not Reported; 999 = (Reported as) Unknown. VSPD_LIM: 0 = no statutory limit or non-trafficway; 5-80 in steps of
5 = mph; 98 = Not Reported; 99 = (Reported as) Unknown. The CRSS 2016-18 code sets match the labelled years. TVD for
TRAV_SP 2017→2018 is 8.4 pp (CRSS), driven by Not Reported.

**How often is travel speed known (1-151 or 997, % of drivers)?**

| | O | C | B | A | K | unk |
|---|---|---|---|---|---|---|
| CRSS 2016-19 | 32.4 | 28.4 | 34.5 | 32.9 | 33.4 | 17.8 |
| CRSS 2020-24 | 33.8 | 30.6 | 38.9 | 35.6 | 36.1 | 14.3 |

In FARS, travel speed is known for 33.9% / 33.1% of killed drivers (2016-19 / 2020-24) and 36.2% / 37.7% of survivors.
TRAV_SP = 998 (Not Reported) covers 48-55% of drivers in every stratum. CRSS VSPD_LIM is known for 82-92% of drivers
(91.9% in K, 83.7% in O, 2016-19). FARS VSPD_LIM is known for 95-96%.

**Travel speed is missing for about two-thirds of drivers, and the missingness is driven by state reporting practice
rather than by severity.** Across FARS states, the share of drivers with a known TRAV_SP has a 10th percentile of 1.2%,
a median of 18.5% and a 90th percentile of 81.4% (pooled 2016-24). Examples: South Carolina 93.1%, Florida 85.3%,
Texas 2.6%, Washington 0.5%. Known speeds are heaped: 82.6-84.7% (FARS) and 91.9-93.8% (CRSS) are multiples of 5, and
33-36% (FARS) or 24-27% (CRSS) equal the posted limit exactly.

**Validation of SPEEDREL against TRAV_SP − VSPD_LIM** (drivers with both known, moving, pooled 2016-24):

| SPEEDREL | FARS n | FARS % over limit | FARS % ≥ 10 over | CRSS n (unw.) | CRSS % over | CRSS % ≥ 10 over |
|---|---|---|---|---|---|---|
| 0 No | 133,034 | 20.2 | 10.3 | 234,985 | 6.0 | 2.6 |
| 2 Racing | 369 | 94.0 | 91.9 | 78 | 77.2 | 76.1 |
| 3 Exceeded limit | 18,904 | **97.4** | 91.6 | 2,808 | **91.3** | 75.7 |
| 4 Too fast for conditions | 13,316 | 60.5 | 49.3 | 15,903 | 18.5 | 10.6 |
| 5 Specifics unknown | 2,982 | 85.9 | 76.9 | 1,428 | 44.5 | 35.3 |
| 9 Unknown | 2,870 | 36.6 | 22.7 | 3,150 | 11.1 | 6.6 |

The share of drivers coded "yes" rises monotonically with the recorded excess. FARS: 4.9% (below the limit), 5.9% (at
it), 19.8% (5-9 over), 40.1% (10-14), 68.5% (20-29), 81.2% (≥ 30). CRSS: 6.1%, 6.0%, 18.5%, 27.7%, 46.3%, 51.0%.

Verdict: TRAV_SP **confirms the meaning of code 3** and the yes/no direction. It **cannot validate SPEEDREL at
population level**. It is known for about one-third of drivers, mostly in a few states, and it is itself a post-crash
estimate, heaped at round numbers and at the limit. In FARS, 18% of drivers with an unknown or unreported TRAV_SP are
still coded speeding "yes", against 21% when TRAV_SP is known. Code 9 is concentrated where TRAV_SP is unknown (11.2%,
against 1.7% when known). A "TRAV_SP > limit" indicator is not a substitute for SPEEDREL: it is missing not at random
and depends on state.

### 4.6 State dependence (FARS)

Pooled 2016-24, the state share of drivers coded speeding has a 10th percentile of 12.9%, a median of 19.7% and a 90th
percentile of 26.7%. Code-9 use ranges from 0.1% (South Carolina) and 0.3% (Texas) to 34.7% (Connecticut) and 35.8%
(Minnesota). Analyses pooling states should include state fixed effects, or at least check robustness to them.

**Reliability: medium.** The code set and the "yes" definition are stable and X-verified in 18 source-years. Weaknesses:
it is a police judgement; FARS levels shift in 2020; the unknown rate depends on severity and state; and FARS and CRSS
differ greatly in the subtype mix. **Timing: CRASH-CIRCUMSTANCE** (a post-crash judgement about pre-crash behaviour).

---

## 5. Distraction: distract.MDRDSTRD (2016-19) / DRDISTRACT (2020-24)

### 5.1 Codes (L: FARS every year, CRSS 2019+)

| code | label | class |
|---|---|---|
| 0 | Not Distracted | none |
| 1 | Looked But Did Not See (**2016-17 only**) | see below |
| 3, 4 | By Other Occupant(s); By a Moving Object in Vehicle | yes |
| 5, 6, 15 | While Talking or Listening to / While Manipulating / Other Mobile Phone Related ("Cellular" until 2018, "Mobile" from 2019, a cosmetic change) | yes (phone) |
| 7, 9, 10 | Audio/climate controls; other integral controls; device or object brought into vehicle | yes |
| 12, 13, 14 | Outside person/object/event; eating or drinking; smoking related | yes |
| 17, 18, 19 | Distraction/Inattention; Distraction/Careless; Careless/Inattentive | yes (generic) |
| 92, 93 | Distraction (Distracted), Details Unknown; Inattention (Inattentive), Details Unknown | yes (generic) |
| 97, 98 | Lost in Thought / Day dreaming; Other Distraction ("[Specify:]" added 2019, cosmetic) | yes |
| 16 | No Driver Present/Unknown if Driver present | no driver (count equals SPEEDREL = 8 every year, X) |
| 96 | Not Reported | **NR** |
| 99 | "Unknown if Distracted" (FARS 2016-17); "Reported as Unknown if Distracted" (2018+) | unknown |

**X-verification of the "distracted" set.** In FARS, `veh_aux.A_DRDIS = 1` equals "any distract code in {3-7, 9, 10,
12-15, 17-19, 92, 93, 97, 98}" with **0 disagreements in all 9 years**. Including code 1 produces 322 (2016) and 378
(2017) disagreements. `acc_aux.A_DIST` matches "any driver in the crash distracted (same set)" with 0-4 disagreements
per year (FARS) and 0-9 (CRSS 2020-24). Dropping code 93 instead produces 974-1,322 (FARS) and 2,424-2,962 (CRSS)
disagreements. So NHTSA's own derived flag counts 93 ("inattention, details unknown") as distracted and excludes 1
("looked but did not see").

**Code 1 → driver-related factor 10.** Code 1 is used in 2016-17 only: FARS 322 and 379 rows, CRSS 703 and 621 rows.
It disappears in both sources in 2018, the year DR_SF code 10 "Looked But Did Not See" appears (FARS 243, CRSS 904
DR_SF1 rows in 2018; 0 before). Drivers with DR_SF = 10 in 2018-19 have distract codes 0 (FARS 310), 96 (145), 99 (69),
93 (23) and others. Harmonise code 1 to **not distracted, with an LBDNS flag** (§17).

### 5.2 The "Not Reported" break (the main finding of this domain)

**Category shares among drivers, %. "S" = distracted, "S/(S+none)" = distracted share among drivers coded yes or no.**

| year | FARS S | none | unknown | NR | S/(S+none) | CRSS S | none | unknown | NR | S/(S+none) |
|---|---|---|---|---|---|---|---|---|---|---|
| 2016 | 6.81 | 61.99 | 15.30 | **15.90** | 9.9 | 8.51 | 76.66 | 7.55 | **7.29** | 10.0 |
| 2017 | 6.52 | 43.27 | 15.82 | 34.39 | 13.1 | 8.66 | 68.77 | 7.50 | 15.08 | 11.2 |
| 2018 | 5.21 | 34.35 | 13.47 | 46.97 | 13.2 | 8.02 | 59.91 | 5.25 | 26.83 | 11.8 |
| 2019 | 5.81 | 33.98 | 13.73 | 46.48 | 14.6 | 8.36 | 39.84 | 4.28 | 47.51 | 17.3 |
| 2020 | 5.49 | 31.93 | 13.83 | 48.74 | 14.7 | 7.65 | 38.33 | 5.50 | 48.51 | 16.6 |
| 2021 | 5.45 | 29.39 | 14.24 | 50.92 | 15.6 | 7.58 | 37.73 | 5.96 | 48.74 | 16.7 |
| 2022 | 5.19 | 28.82 | 15.03 | 50.96 | 15.3 | 6.35 | 39.07 | 5.34 | 49.25 | 14.0 |
| 2023 | 5.41 | 29.79 | 15.08 | 49.71 | 15.4 | 7.35 | 37.08 | 5.44 | 50.13 | 16.5 |
| 2024 | 5.44 | 27.96 | 15.12 | **51.48** | 16.3 | 6.86 | 37.55 | 4.38 | **51.21** | 15.5 |

(S in 2016-17 includes code 1. Excluding it gives FARS 6.20 / 5.81 and CRSS 7.72 / 8.13.)

* "Not Distracted" was replaced by "Not Reported" step by step, **state by state**, between 2016 and 2020. The share of
  drivers coded distracted barely moved (FARS 5.2-6.2%, CRSS 6.4-8.4%, code 1 excluded). The **distracted share among
  drivers coded yes or no** rose artefactually from 9.9% to 16.3% (FARS) and from 10.0% to 15.5% (CRSS).
* **Evidence that the break is state-driven (FARS, NR % of drivers by state and year):** Georgia 0.1 (2016) → 3.9 →
  84.7 (2018); Pennsylvania 0.1 → 84.1 (2017); Texas 0.0 → 71.3 (2017) → 93.0 (2024); Illinois 1.2 → 77.4 (2017) → 7.2
  (2020) → 0.9 (2024); Mississippi 99.1 (2016) → 2.8 (2020); Nebraska 0.0 → 96.6 (2018-2020) → 1.0 (2021); California
  26.3 → 65.5 (2020) → 95.1 (2024); Florida < 1% in every year. The number of states with NR > 50% went 5 (2016), 11,
  19, 22, 22, 21, 19, 20, 20 (2024). The number with NR < 5% went 33 → 19. **CRSS:** the median PSU NR share was 0.6%
  (2016), 2.6%, 3.3%, 26.5% (2019) and 79.0% (2020). The number of PSUs with NR > 90% went 0 (2016) → 16 (2019) → 19-20
  (2020-24).
* Interpretation: "Not Distracted" (0) and "Not Reported" (96) are **not exchangeable across states or years**. A
  driver coded 0 in 2016 Georgia may correspond to a driver coded 96 in 2018 Georgia. The sharp state-level timing
  points to a change in coding conventions or police report forms. The precise rule is **UNVERIFIED**, because no
  manual is in the archive.

### 5.3 Severity dependence

| | FARS killed | FARS survived | CRSS K | CRSS A | CRSS B | CRSS C | CRSS O |
|---|---|---|---|---|---|---|---|
| distracted, 2016-19 | 5.55 | 6.62 | 5.45 | 7.63 | 8.34 | 9.22 | 8.30 |
| unknown, 2016-19 | **21.77** | 7.82 | **14.91** | 6.36 | 5.37 | 4.96 | 5.71 |
| NR, 2016-19 | 38.40 | 33.84 | 23.68 | 23.62 | 22.12 | 24.11 | 24.57 |
| distracted, 2020-24 | 5.11 | 5.66 | 4.49 | 6.31 | 7.65 | 7.74 | 7.06 |
| unknown, 2020-24 | **21.37** | 8.39 | **14.40** | 7.53 | 4.86 | 4.80 | 5.10 |
| NR, 2020-24 | 52.36 | 48.33 | 53.94 | 50.88 | 44.78 | 54.07 | 48.60 |

**Strongly differential.** "Unknown if distracted" is 2.6-2.8× higher for killed than for surviving FARS drivers, and
about 3× higher in CRSS fatal crashes than in O crashes. Killed drivers cannot be interviewed. The raw "distracted"
share is therefore *lower* in fatal crashes (CRSS K 4.5-5.5% against O 7.1-8.3%). That gradient is an artefact of
ascertainment and must not be read as distraction being protective.

**Reliability:** "distracted = yes" is low-medium (stable code set, X-verified, but under-ascertained in fatal
crashes). "Not distracted" is **low** (state- and year-dependent NR substitution). **Timing: CRASH-CIRCUMSTANCE**
(police judgement).

---

## 6. Driver impairment: drimpair.DRIMPAIR

### 6.1 Codes (L)

| code | label | class |
|---|---|---|
| 0 | None/Apparently Normal | none |
| 1 | Ill, Blackout | yes (ill) |
| 2 | Asleep or Fatigued | yes (**drowsy**) |
| 3, 4, 5 | Walking with a Cane or Crutches; Paraplegic or in a Wheelchair ("Restricted To" until 2016, cosmetic); Impaired Due to Previous Injury | yes (physical) |
| 6 | Deaf (≤ 2020) → **Deaf/Hard of Hearing** (FARS 2021+, CRSS 2022+) | yes (physical). The wording broadens the meaning; counts are ≤ 27 per year |
| 7 | Blind (≤ 2020) → **Blind/Low Vision** (2021+) | yes (physical). Broadened meaning, ≤ 11 per year |
| 8 | Emotional (depressed, angry, disturbed, etc.) | yes (emotional) |
| 9 | Under the Influence of Alcohol, Drugs or Medication | yes (influence) |
| 10, 96 | Physical Impairment - No Details; Other Physical Impairment | yes (physical) |
| 95 | No Driver Present/Unknown if Driver Present | no driver (= SPEEDREL 8 counts, X) |
| 98 | Not Reported | **NR** |
| 99 | Unknown if Impaired (FARS 2016-17) → Reported as Unknown if Impaired (2018+) | unknown |

X-verification: FARS `veh_aux.A_DRDRO = 1 ⇔ any DRIMPAIR = 2` (0 disagreements, 9 years). FARS `acc_aux.A_DROWSY = 1 ⇔`
any vehicle in the crash has DRIMPAIR = 2 (0 disagreements, 9 years). CRSS has no drowsy aux flag.

### 6.2 Not Reported break and rates

| year | FARS S | none | unk | NR | CRSS S | none | unk | NR |
|---|---|---|---|---|---|---|---|---|
| 2016 | 14.81 | 58.08 | 20.73 | **6.37** | 3.79 | 87.19 | 6.06 | **2.97** |
| 2017 | 14.71 | 50.60 | 19.99 | 14.70 | 3.62 | 84.94 | 5.09 | 6.34 |
| 2018 | 13.87 | 48.12 | 19.81 | 18.20 | 3.29 | 86.16 | 3.98 | 6.56 |
| 2019 | 13.80 | 44.76 | 19.96 | 21.48 | 3.28 | 71.28 | 4.35 | 21.09 |
| 2020 | 15.21 | 42.36 | 20.51 | 21.92 | 4.37 | 53.22 | 4.96 | 37.46 |
| 2022 | 14.60 | 37.42 | 20.38 | 27.59 | 3.72 | 53.83 | 5.21 | 37.24 |
| 2024 | 13.50 | 36.07 | 19.38 | **31.05** | 3.68 | 52.00 | 5.16 | **39.16** |

The same mechanism as distraction applies. The number of FARS states with drimpair NR < 5% fell from 41 (2016) to 25
(2024). The number with > 50% rose from 4 to 12. The median CRSS PSU NR share went 0.5% (2016) → 2.6% (2019) → 8.0%
(2020) → 12.8% (2024). The number of PSUs with > 90% NR went 0 → 14-16.

Specific substantive codes (% of drivers) are fairly stable:

* drowsy (2): FARS 0.98-1.39%, CRSS 0.69-0.93%;
* ill (1): FARS 0.85-1.21%, CRSS 0.34-0.48%;
* influence (9): FARS 9.85-11.89%, CRSS 1.96-2.69%;
* emotional (8): FARS 0.29-0.44%, CRSS 0.12-0.24%.

### 6.3 Severity dependence

| | FARS killed | FARS survived | CRSS K | CRSS A | CRSS B | CRSS C | CRSS O |
|---|---|---|---|---|---|---|---|
| any impairment, 2016-19 | 18.80 | 10.91 | 12.85 | 12.13 | 7.04 | 3.64 | 2.73 |
| unknown, 2016-19 | **34.26** | 7.11 | **18.78** | 4.80 | 3.07 | 3.13 | 4.31 |
| NR, 2016-19 | 15.02 | 15.03 | 8.89 | 7.84 | 6.98 | 9.54 | 9.10 |
| unknown, 2020-24 | **33.30** | 7.57 | **21.90** | 6.44 | 3.51 | 3.36 | 5.08 |
| NR, 2020-24 | 25.15 | 28.48 | 34.35 | 37.68 | 32.75 | 46.01 | 36.14 |

Pooled 2016-24, the drowsy share is 1.31% (FARS killed) against 1.08% (survived), and 0.94% (CRSS K) against 0.68% (O).
"Under the influence" is 13.85% against 8.57% (FARS) and 9.21% against 1.78% (CRSS K vs O).

**Unknown impairment status is about 4.5× higher for killed drivers, and 4-6× higher in CRSS fatal crashes.** Any
analysis of impairment by severity must treat unknown separately. It cannot be collapsed to "not impaired".

**Reliability:** drowsy and influence "yes" medium; "none" low (NR break). **Timing: CRASH-CIRCUMSTANCE** (police
judgement, partly informed by post-crash tests for code 9).

---

## 7. Driver-related factors: DR_SF1-4 (2016-19) and driverrf.DRIVERRF (2020-24)

### 7.1 Code changes (L, FARS)

| code | 2016-2019 label | 2020-2024 label | judgement |
|---|---|---|---|
| 0 | None | None (2020-21) → **None Noted** (2022+) | meaning-relevant: see 999 |
| 6 | Careless Driving | Careless Driving, Inattentive Operation, Improper Driving, Driving Without Due Care | **broadened**. FARS prevalence 6.5% (2019) → 7.4% (2020) → 8.9% (2022); CRSS 7.6% → 7.3% → 8.5% (2024) |
| 8 | Aggressive Driving / Road Rage | same until 2022; **split 2023** into 102 Aggressive Driving + 103 Road Rage | merge 8 ∪ 102 ∪ 103 |
| 9 | Emergency Services Personnel (2018 only) | → 94-97 (EMS, Fire, Tow, Transportation) from 2019 | not a driver behaviour |
| 10 | Looked But Did Not See (**new 2018**; was distract code 1) | same | §5.1 |
| 29 | "Intentional Illegal Driving on Road Shoulder, in Ditch, on Sidewalk or on Median" (≤ 2018) | Intentional Illegal Driving Off the Roadway (2019+) | cosmetic |
| 34 | **Passing on Right Side** | **Improper Passing Location** | **meaning change** |
| 37 | Police Pursuing this Driver or Police Officer in Pursuit | same until 2022; **split 2023** into 104/105 | merge |
| 55, 56, 57, 60 | (new 2017) Improper management of controls; object interference; tire-related problems; alcohol and/or drug test refused | same | 60 is a post-crash act |
| 91 | Non-Traffic Violation Charged - manslaughter, homicide … | used in 2020 only (711 rows), absent 2021+ | **post-crash legal** |
| 99 / 999 | 99 (Reported as) Unknown, written in all 4 slots | **999 Reported as Unknown in 2020-21 only**; absent 2022+ | **break** |
| 107 | – | Driver Required to Use Ignition Interlock Device (2024) | new |

**The 2022 unknown break.** FARS drivers with only the "none" code were 59.9% in 2021 and 62.8% in 2022. The +3.0 pp
matches the disappearance of 999, which had covered 3.08% of drivers in 2021. In 2022+, an unknown driver-factor status
is folded into **0 "None Noted"**, and the label change says as much. CRSS: 999 covered 0.10% (2020) and 0.06% (2021).
**Before 2022, code 0 means "no factor"; from 2022 it means "no factor noted".**

### 7.2 Prevalence (% of drivers)

| year | FARS any substantive | FARS unknown | FARS 6 | 38 FTY | 39 disobey | 28 lane | 36 erratic | 58 overcorrect | 10 LBDNS | CRSS any | CRSS unknown | CRSS 6 | CRSS 36 | CRSS 10 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2016 | 37.78 | 4.66 | 5.26 | 7.07 | 3.99 | 7.57 | 3.87 | 3.81 | – | 6.31 | 4.41 | 4.78 | 1.60 | – |
| 2019 | 37.10 | 3.86 | 6.53 | 7.34 | 4.06 | 6.67 | 3.73 | 3.10 | 0.48 | 10.71 | 1.20 | 7.57 | 2.34 | 1.38 |
| 2020 | 37.39 | 3.57 | 7.41 | 6.84 | 4.21 | 6.29 | 4.47 | 3.27 | 0.25 | 10.48 | 0.10 | 7.32 | 2.01 | 0.23 |
| 2022 | 37.17 | 0 | 8.93 | 7.44 | 4.27 | 5.73 | 3.81 | 2.86 | 0.23 | 10.29 | 0 | 7.29 | **0.69** | 0.20 |
| 2024 | 36.26 | 0 | 7.57 | 8.37 | 4.69 | 5.17 | 4.29 | 2.66 | 0.31 | 11.51 | 0 | 8.48 | 0.88 | 0.17 |

Further breaks: LBDNS (10) halved in 2020 in both sources (FARS 0.48 → 0.25; CRSS 1.38 → 0.23). CRSS "erratic,
reckless" (36) fell from 2.38% (2021) to 0.69% (2022). CRSS "unknown" fell from 4.41% (2016) to 1.20% (2019).

### 7.3 FARS and CRSS code lists are not comparable

CRSS uses only {0, 6, 8, 9 (2018), 10 (2018+), 16, 18, 20-24, 29 (2019+), 32, 36, 37, 50, 51, 54-60, 91, 94-97, 99/999,
100-107}. It **never** uses 26-28, 30-31, 33-35, 38-42, 45, 47-48, 52-53, 73-74, 77-89. Those include all the
"rules-of-the-road" errors and environmental factors. Consequently "any driver factor" covers 36-38% of FARS drivers but
6-12% of CRSS drivers. Cross-source work must restrict itself to the common subset {6, 8/102/103, 10, 36, 50, 51, 58}
(§16), plus 18, 29 and 55-57 if needed.

Severity (2020-24): driverrf "any" is 45.5% for killed FARS drivers against 30.1% for survivors, and 14.3% (CRSS K)
against 10.5% (O). Unknown in 2020-21 is 1.6% (killed) against 0.7% (survived).

**Reliability: low to medium.** The code set changed in 2018, 2020, 2022 and 2023. "None" changed meaning in 2022.
FARS and CRSS lists differ. **Timing: CRASH-CIRCUMSTANCE** (police or analyst judgement). Exceptions: 60 (test
refused) and 91 (charged) are **POST-CRASH**; 89 (multi-state record), 19 and 73-74 (licence compliance) are
administrative.

---

## 8. Violations charged: violatn.MVIOLATN / VIOLATION

Codes (L) form the same frame in all years: 0 None; 1-10 serious/reckless (1 manslaughter or homicide, 2 willful
reckless, 3 unsafe reckless, 4 inattentive/careless, 5 fleeing police, 7 hit-and-run, 8 fail to give aid, 9 serious
violation resulting in death, 10 use of telecommunications device); 11-19 impairment; 21-29 speed; 31-49
signals/signs/turn/yield; 51-69 lane/passing/following; 71-76 licence/registration/insurance; 79-93 non-moving or
equipment; **95 No Driver; 97 Not Reported; 99 Unknown Violation(s)**; 98 Other moving violation.

Label changes: code 4 gained "…, driving without due care" in 2020 (broadened wording). Code 17 "Circumvention of
Ignition Interlock Device" was added in 2024 (5 rows). Rare codes appear and disappear (25, 32, 55, 63, 66, 67, 85;
≤ 3 rows). CRSS 2016-18 codes are all labelled by CRSS 2019+, except code 67 in 2017 (2 rows) and 2018 (1 row), which
FARS 2021 labels "Motorcyclist attached to another vehicle".

| | FARS any charge | FARS unknown | FARS NR | CRSS any charge | CRSS unknown | CRSS NR |
|---|---|---|---|---|---|---|
| 2016 | 8.61 | 1.39 | 0.31 | 23.10 | 0.93 | 1.13 |
| 2020 | 9.70 | 1.03 | 0.58 | 22.96 | 0.82 | 0.05 |
| 2024 | 8.99 | 0.26 | 0.72 | 21.68 | 0.97 | 0.02 |

**Outcome dependence.** Pooled 2016-24, FARS drivers carry any charge in 1.93% (2016-19) and 2.57% (2020-24) of cases
when killed, against 14.94% and 15.29% when they survived. CRSS: 8.4% / 7.9% in K crashes against 29.2% / 26.2% in A
crashes. Within FARS two-vehicle crashes with exactly one killed and one surviving driver, **2.56%** of killed drivers
were charged against **11.6-12.4%** of survivors, while the action-based culpability measure (§16) puts the killed
driver at fault more often (66.7% against 39.4-43.0%). Dead drivers are essentially never charged. Charges also reflect
prosecutorial outcomes. Codes 1 and 9 (homicide, "resulting in death") can only exist after a death.

**Reliability:** high as a record of charges. **Invalid as a measure of driver behaviour in severity analyses.**
**Timing: POST-CRASH / OUTCOME-DERIVED.**

---

## 9. Vision obscured, avoidance manoeuvre, vehicle contributing factors

### 9.1 vision.MVISOBSC / VISION

Codes (L): 0 No Obstruction Noted; 1-14 specific obstructions (weather, glare, design, structures, vegetation,
vehicles, splash, defrost, lighting, interior, mirrors (new 2017), windshield, angles); 97 Vision Obscured - No Details;
98 Other Visual Obstruction (substantive, **not** NR); 95 No driver; 99 Unknown. **There is no Not Reported code**, so
"0" absorbs silence.

Rates: obscured 2.5-3.0% (FARS) and 1.9-2.3% (CRSS). Unknown 2.7-4.1% (FARS) and 1.0-1.4% (CRSS 2018+), but 5.12%
(2016) and 2.95% (2017) in CRSS. Unknown is 4.3% for killed drivers against 2.0% for survivors (FARS 2016-19), and 4.6%
(K) against 2.2% (O) in CRSS. **Reliability: medium-low** ("no obstruction noted" is not "none"). **Timing:
CRASH-CIRCUMSTANCE.**

### 9.2 maneuver.MDRMANAV / MANEUVER

Codes (L): 0 Driver Did Not Maneuver to Avoid; 1 Object; 2 Poor Road Conditions; 3 Live Animal; 4 "Motor Vehicle"
(≤ 2019), reworded "Contact Motor Vehicle (In this crash)" in 2020 (clarifying); 5 Non-Motorist; 92 Phantom/Non-Contact
MV; 95 No driver; 98 NR; 99 Unknown.

**Not Reported dominates:** FARS 53.6% (2016) to 64-67% (2018-24); CRSS 63.9-76.3%. For FARS states with NR > 50%, the
count went 19 (2016) → 31-38. NR is 69-74% for killed drivers against 56-58% for survivors. **Reliability: low; do not
use** except as "avoidance manoeuvre recorded" with explicit missingness. **Timing: CRASH-CIRCUMSTANCE.**

### 9.3 factor.MFACTOR / VEHICLECC

Codes (L): 0 None (≤ 2019) → **None Noted** (2020+); 1-17 vehicle defects (tires, brakes, steering, …, 17 "No
Details"); 97 Other; **98 Not Reported (≤ 2019 only)**; 99 Unknown.

**Break in 2020:** code 98 disappears and is absorbed by 0. FARS NR 7.44% (2019) → 0 and "none" 85.7% → 92.4%. CRSS NR
23.8% (2019; up from 2.95% in 2016) → 0 and "none" 69.7% → 93.4%. CRSS TVD 2019→2020 = 24.0 pp. Defects are recorded
for 1.7-2.2% (FARS) and 1.3-1.9% (CRSS) of drivers. They are higher in fatal crashes (FARS killed 2.6% vs survived
1.7%), where the unknown share is also higher (6.3% vs 3.3%).

**Harmonise 2016-19 code 98 into "none noted".** That is the only way to match 2020+, at the cost of treating "not
reported" as "none noted", which is what 2020+ does implicitly. **Timing: CRASH-CIRCUMSTANCE** (post-crash inspection).

---

## 10. Person- and crash-level factors (P_SF1-3 → personrf, CF1-3 → crashrf)

* **P_SF1-3 / PERSONRF** concern almost entirely non-motorists and passengers: interfering with driver,
  construction/EMS/police personnel, non-motorist pushing a vehicle, portable electronic devices (non-motorist), and
  similar. 99.0-99.5% of FARS and 99.6% of CRSS person rows are 0. They are not driver-behaviour variables. Breaks: 999 Reported as Unknown in
  2020-21 only (202 and 177 rows), then absent; 0 → "None Noted" (2022); new codes 100-105 (2022-23). In CRSS 2016-18,
  a handful of codes (21, 32, 86-93; ≤ 82 rows per year) are not labelled by CRSS 2019+. They are labelled by FARS in
  the same year for 86 and 92, and **UNVERIFIED** for the rest.
* **CF1-3 / CRASHRF** are crash-level road and environment flags. The driver-relevant codes are 13 "Aggressive Driving /
  Road Rage by Non-contact Vehicle Driver" (2016-22, **split 2023** into 102/103), 12 "Distracted Driver of a
  Non-Contact Vehicle" (≤ 4 per year) and 20 "Police Pursuit Involved" (FARS 343-500 per year). 999 Reported as Unknown
  appears in 2020-21 only (344 and 322), then is folded into 0 "None Noted" from 2022. **Timing: CRASH-CIRCUMSTANCE.**

---

## 11. FARS driver licence and driving record (FARS only; vehicle table)

### 11.1 Codes (L, identical code sets 2016-2024 unless noted)

| variable | substantive codes | no driver | unknown / other |
|---|---|---|---|
| L_STATUS | 0 Not licensed; 1 Suspended; 2 Revoked; 3 Expired; 4 Canceled or denied; 6 Valid | 7 | 9 Unknown License Status |
| L_COMPL | 0 Not licensed; 1 No license required for this class; 2 No valid license for this class; 3 Valid license for this class | 6 | 8 Unknown if CDL/endorsement required; 9 Unknown |
| CDL_STAT | 0 No (CDL); 1 Suspended; 2 Revoked; 3 Expired; 4 Cancelled/Denied; 5 Disqualified; 6 Valid; 7 Learner's Permit → "Commercial Learner's Permit (CLP)" (2018, clarifying); 8 Other Not-Valid | 97 | 99 |
| L_TYPE | 0 Not Licensed; 1 Full; 2 Intermediate; 7 Learner's Permit; 8 Temporary | 6 | 9 |
| L_RESTRI | 0 No Restrictions or N/A; 1 Complied; 2 Not Complied | 7 | **3 Restrictions, Compliance Unknown (21.7-24.3%!)**; 9 |
| L_ENDORS | 0 Not required; 1 Required, complied; 2 Required, not complied | 7 | 3 Required, compliance unknown; 9 |
| PREV_ACC, PREV_DWI, PREV_SPD, PREV_OTH | counts (label = number; observed max 14 / 10 / 14 / 59) | 998 | 99 Unknown. PREV_ACC also has **98 Crashes Not Reported on Driving Record** |
| PREV_SUS (2016-17); PREV_SUS1/2/3 (2018+) | counts | 998 | 99 |
| FIRST_MO/YR, LAST_MO/YR | month (0 = No Record) and year of first/last prior event | 98 / 9998 | 99 / 9999 |
| DR_HGT (inches), DR_WGT (lbs) | known range 25-104 in (median 69), 40-630 lb (median 180) | DR_HGT 998, labelled "Other" but **100% DR_PRES ≠ 1** (3,123 of 3,123); DR_WGT 997 | 999 |
| DR_ZIP | 5-digit ZIP; 0 = not a US resident | 99997 | 99999 Unknown → "Reported as Unknown"; **99998 Not Reported (new 2020)** |
| DR_DRINK | 0 No; 1 Yes | – | **no unknown code**: "No" includes unknown |

Cross-tabs (X): L_STATUS = 0 ⇔ L_TYPE = 0 (27,772 of 27,772). L_STATUS = 9 coincides almost entirely with L_TYPE = 9
and L_COMPL = 9. Of drivers with L_STATUS 1-4, 97-98% have L_COMPL = 2, consistent. 10,199 drivers with L_STATUS = 6
(valid) have L_COMPL = 2 (no valid licence *for this vehicle class*). Of these, 7,773 (76%) are motorcycles
(BODY_TYP 80-89) and 1,014 are trucks or buses (§12).

### 11.2 Rates by year (drivers, %)

| year | L_STATUS invalid (0-4) | L_STATUS unknown | driving record unknown (99) | PREV_ACC = 98 | ≥ 1 prior DWI | ≥ 1 prior speeding | DR_HGT unknown | DR_WGT unknown | L_RESTRI = 3 |
|---|---|---|---|---|---|---|---|---|---|
| 2016 | 12.71 | 2.90 | 3.48 | 8.49 | 3.53 | 19.97 | 14.36 | 35.19 | 23.61 |
| 2017 | 12.74 | 2.86 | 3.47 | 8.56 | 3.38 | 19.31 | 13.70 | 34.24 | 23.77 |
| 2018 | 12.49 | 3.09 | 3.73 | 8.22 | 3.08 | 18.71 | 14.20 | 34.85 | 24.08 |
| 2019 | 12.66 | 3.00 | 3.66 | 8.32 | 2.97 | 18.09 | 14.02 | 34.85 | 24.25 |
| 2020 | **16.03** | 3.85 | 4.59 | **4.54** | 3.24 | 17.60 | **19.68** | **39.96** | 21.68 |
| 2021 | 15.54 | 3.98 | 4.67 | 4.34 | 2.85 | 16.83 | 20.03 | 40.11 | 22.83 |
| 2022 | 14.33 | 4.09 | 4.84 | 4.34 | 2.63 | 16.15 | 19.09 | 39.35 | 23.42 |
| 2023 | 13.95 | 3.94 | 4.69 | 4.19 | 2.34 | 16.07 | 19.48 | 39.41 | 23.41 |
| 2024 | 13.39 | 4.00 | 4.92 | 4.40 | 2.48 | 15.93 | 19.14 | 39.61 | 24.16 |

Breaks in 2020:

* L_STATUS invalid +3.4 pp. "Not licensed" went from 2,389 to 3,390 and "expired" from 598 to 973. This may be partly
  real (pandemic licensing backlogs and extensions), but it is **UNVERIFIED**.
* PREV_ACC = 98 halved. This is almost entirely **Georgia, 86.5% (2019) → 0.2% (2020)**. Connecticut, Mississippi,
  Montana, New Mexico and Utah keep 68-87%.
* DR_HGT and DR_WGT unknown jumped by 5 pp.
* L_RESTRI = 3 dropped by 2.6 pp, then recovered.

**Joint missingness.** PREV_ACC, PREV_DWI, PREV_SPD, PREV_OTH and PREV_SUS(1) = 99 are the **same drivers** in
2016-2023: the "all five = 99" count equals each single count (for example 1,826 in 2016, 2,919 in 2022). In 2024 the
counts diverge by 2-31 drivers (2,708-2,739). FIRST_YR = 9999 agrees to within 3-22 drivers. Record-unknown also
overlaps L_STATUS = 9 for 82-100% of the latter. These variables share a single "driver record obtained" switch.

### 11.3 Severity and hit-and-run dependence

| group (pooled 2016-24) | n | L_STATUS unknown | record unknown | invalid licence | ≥ 1 prior DWI | DR_HGT unknown | DR_WGT unknown |
|---|---|---|---|---|---|---|---|
| driver killed | 222,856 | 0.93 | 1.60 | 17.56 | 4.22 | 13.96 | 33.11 |
| driver survived | 264,519 | 2.95 | 3.70 | 10.95 | 1.92 | 17.57 | 39.67 |
| driver injury unknown | 10,891 | **71.68** | **72.23** | 6.67 | 0.96 | 75.57 | 80.86 |
| hit-and-run vehicle | 22,315 | **54.01** | **54.74** | 17.29 | 3.05 | 62.35 | 72.46 |
| not hit-and-run | 475,951 | 1.19 | 1.89 | 13.65 | 2.92 | 15.11 | 36.00 |

Missingness here is **inversely** related to fatality: records of killed drivers are retrieved more completely
(record unknown 1.2-1.9% for killed against 3.1-4.5% for survivors in every year). It is concentrated in hit-and-run
drivers, who are unidentified. Excluding unknowns therefore removes most hit-and-run drivers, a selective subgroup with
high invalid-licence rates (17.3% even among those known). Unknown for unknown-injury drivers rose from 54.3% (2016) to
77.7% (2024).

### 11.4 PREV_SUS split (2018)

PREV_SUS (2016-17) was replaced by PREV_SUS1-3. **D:** among drivers with a known record, the distribution of the old
total in 2016-17 (0: 84.78%, 1: 7.14%, 2: 3.26%, 3: 1.64%, 4: 0.94%, ≥ 5: 2.24%) matches that of SUS1 + SUS2 + SUS3 in
2018-19 (85.57, 6.78, 3.01, 1.55, 0.98, 2.11). The share with any suspension is 15.22% against 14.43%. So the three new
variables **decompose** the old total. Their individual meanings carry no labels (labels are the numbers themselves). By
cross-tab (2018-24 drivers):

* SUS2 ≥ 1 (n = 6,564): 65.6% have ≥ 1 prior DWI, against 1.8% of SUS2 = 0. This strongly suggests DWI-related
  suspensions.
* SUS1 ≥ 1 (n = 665): 50.5% prior DWI and 43.0% prior speeding.
* SUS3 ≥ 1 (n = 43,378): 15.4% prior DWI and 36.6% prior speeding, the general or other category.

**The meanings of PREV_SUS1-3 are UNVERIFIED.** Only "any previous suspension" (sum > 0) is harmonisable across 2016-24.

**Timing: PRE-CRASH** (administrative records), although whether a record was retrieved depends on post-crash events
(hit-and-run). The look-back window of the PREV_* counts is **UNVERIFIED** (no label states it).

---

## 12. Derived aux flags: meanings verified by cross-tab (X)

| aux | source(s) | verified definition | disagreements |
|---|---|---|---|
| A_SPVEH | veh_aux FARS + CRSS, 2016-24 | 1 = SPEEDREL ∈ {2-5}; 2 = otherwise (0, 8, 9) | **0** in all 18 source-years |
| A_SPCRA | acc_aux FARS + CRSS, 2016-24 | 1 = ≥ 1 vehicle with SPEEDREL ∈ {2-5}; 2 = none | **0** in all 18 |
| A_DIST | acc_aux FARS 2016-24, CRSS **2020-24** | 1 = ≥ 1 driver with distract code ∈ {3-7, 9, 10, 12-15, 17-19, 92, 93, 97, 98}; code 1 not included | FARS 0-4 per year; CRSS 0-9 per year |
| A_DRDIS | veh_aux FARS | same set, vehicle level | **0** in 9 years (322/378 if code 1 is included) |
| A_DROWSY | acc_aux FARS | 1 = ≥ 1 driver with DRIMPAIR = 2 | **0** |
| A_DRDRO | veh_aux FARS | 1 = DRIMPAIR = 2 | **0** |
| A_LIC_S | veh_aux FARS | 1 = L_STATUS 6 (valid); 2 = L_STATUS 0-4 (invalid); 3 = L_STATUS 7 or 9 (no driver or unknown); **4 = motorcycle operator** (status carried by A_MC_L_S) | A_LIC_S = 4 ⇔ A_MC_L_S ≠ 4: 52,451 of 52,451 |
| A_LIC_C | veh_aux FARS | 1 = L_COMPL ∈ {1, 3}; 2 = L_COMPL ∈ {0, 2}; 3 = L_COMPL ∈ {6, 8, 9} | exact partition |
| A_CDL_S | veh_aux FARS | 1 = CDL_STAT ∈ {6, 7} (valid CDL or CLP); **2 = CDL_STAT ∈ {0-5, 8} (no CDL *or* invalid CDL)**; 3 = CDL_STAT ∈ {97, 99} | exact partition |
| A_MC_L_S | veh_aux FARS | 4 = not a motorcycle (BODY_TYP not 80-89; 18 exceptions in 501,389 rows); 1 = motorcyclist with L_COMPL ∈ {1, 3} | see break below |

**A_MC_L_S definitional break in 2020.** Motorcyclists with L_COMPL = 2 (licence not valid for a motorcycle) were coded
A_MC_L_S = 2 in 2016-19 (5,149 rows) and **3** in 2020-24 (9,042 rows). Code 2 now holds only L_COMPL = 0 (not
licensed), and code 3 also holds L_COMPL = 9 (unknown). Counts per year: code 2 falls from 1,552 (2019) to 344 (2020),
and code 3 rises from 52 to 1,817. The aux labels are absent, so the names of codes 2 and 3 are **UNVERIFIED**. Their
composition is verified. **Do not use A_MC_L_S across 2019/2020.** Rebuild it from L_COMPL and BODY_TYP.

---

## 13. CRSS 2016-2018 (unlabelled): can 2019+ and FARS labels be applied?

| variable | codes not labelled by CRSS 2019+ (rows) | labelled by same-year FARS? | TVD 16→17 / 17→18 / 18→19 (unw.) | additional X evidence | verdict |
|---|---|---|---|---|---|
| SPEEDREL | none | – | 1.1 / 1.9 / 0.8 | A_SPVEH and A_SPCRA reproduce the 2-5 = yes rule exactly; SPEEDREL 8 count = DR_PRES ∈ {0, 9} count (146, 226, 178) | **apply 2019+ labels** |
| MDRDSTRD | 1 (703 in 2016, 621 in 2017) | yes, "Looked But Did Not See" | 8.3 / 13.0 / 21.2 | 16 = no-driver count matches; code 1 vanishes in 2018 as DR_SF 10 appears in both sources | apply; TVD is the NR break (§5.2), not a label change |
| DRIMPAIR | none | – | 3.6 / 1.2 / 15.0 | 95 count = no-driver count | apply; NR break |
| MFACTOR | none | – | 0.7 / 7.9 / 13.4 | – | apply; NR break |
| MDRMANAV | none | – | 7.1 / 3.7 / 3.5 | 2018 holds one row per vehicle only | apply |
| MVIOLATN | 67 (2017: 2; 2018: 1) | 67 labelled by FARS 2021 only | 2.6 / 2.9 / 1.6 | 95 count = no-driver count | apply |
| MVISOBSC | none | – | 2.2 / 1.5 / 0.2 | – | apply |
| DR_SF1-4 | 9 (2018: 38 rows in DR_SF1); a few other codes in DR_SF2-4 (≤ 11 rows/yr) | 9 yes (FARS 2018 "Emergency Services Personnel"); the others are labelled in CRSS DR_SF1 2019 (same code frame) | 1.9 / 1.7 / 1.7 (DR_SF1) | – | apply |
| TRAV_SP, VSPD_LIM | 0-1 codes | – | 2.9 / 8.4 / 1.7; 5.0 / 1.8 / 2.5 | – | apply |
| P_CRASH2 | none (57 codes every year) | – | – | pair structure identical (§16) | apply |
| MAX_SEV | none | – | 1.0 / 4.6 / 1.1 | – | apply |

There is no evidence of any code being reused with a different meaning in CRSS 2016-18. The large TVDs reflect the
"Not Reported" practice change, which affects the same codes with the same labels in FARS.

---

## 14. Severity-dependent missingness: summary (key analysis 2)

| indicator (2020-24 unless stated) | "unknown" among killed (FARS) / K (CRSS) | among survivors (FARS) / O (CRSS) | ratio | direction of bias if unknown is treated as "no" |
|---|---|---|---|---|
| SPEEDREL unknown | 7.05 / 3.79 | 3.71 / 2.28 | 1.9 / 1.7 | speeding understated in fatal crashes |
| distraction unknown | 21.37 / 14.40 | 8.39 / 5.10 | 2.5 / 2.8 | distraction understated in fatal crashes (raw gradient reversed) |
| impairment unknown | 33.30 / 21.90 | 7.57 / 5.08 | 4.4 / 4.3 | impairment understated in fatal crashes |
| vision unknown (2016-19) | 4.26 / 4.60 | 1.96 / 2.23 | 2.2 / 2.1 | small |
| vehicle-factor unknown | 6.42 / 6.66 | 3.42 / 4.63 | 1.9 / 1.4 | small |
| driverrf unknown (2020-21 only) | 1.62 / 0.04 | 0.73 / 0.03 | – | small; invisible from 2022 |
| TRAV_SP known | 33.12 / 36.07 | 37.69 / 33.80 | ~1 | not severity-driven; state-driven |
| FARS only: L_STATUS unknown / record unknown (pooled 2016-24) | 0.93 / 1.60 (killed) | 2.95 / 3.70 (survived) | 0.3 / 0.4 | reversed: survivors and hit-and-run drivers missing |
| violation charged (yes) | 2.57 / 7.86 | 15.29 / 20.65 | 0.17 / 0.38 | outcome-dependent by construction |

In addition, every indicator has 4-28× higher unknown rates when the crash or driver severity itself is unknown
(CRSS MAX_SEV 9; FARS INJ_SEV 9 or no person row). Those cases are dominated by hit-and-run.

---

## 15. Timing and outcome-influence classification (key analysis 4)

| variable | who records it, and when | class | outcome-influence risk |
|---|---|---|---|
| L_STATUS, L_COMPL, L_TYPE, CDL_STAT, L_RESTRI, L_ENDORS | licensing record, retrieved post-crash | **PRE-CRASH** (objective) | retrieval completeness depends on hit-and-run and identification (§11.3) |
| PREV_ACC/SUS/DWI/SPD/OTH, FIRST/LAST_* | driving record | **PRE-CRASH** (objective) | same; Georgia-specific PREV_ACC = 98 |
| DR_HGT, DR_WGT, DR_ZIP | licence record or PAR | **PRE-CRASH** | 34-40% unknown weight |
| P_CRASH2 (critical event), ACC_TYPE | analyst reconstruction of crash geometry | **CRASH-CIRCUMSTANCE**, relatively objective | low |
| SPEEDREL, TRAV_SP | police judgement or estimate | CRASH-CIRCUMSTANCE (judgement) | **medium**: more investigation in fatal crashes |
| DRDISTRACT, DRIMPAIR, VISION, MANEUVER, DRIVERRF / DR_SF | police judgement, often from interviews | CRASH-CIRCUMSTANCE (judgement) | **high**: interviews impossible with dead drivers, so unknowns are elevated |
| DRIMPAIR = 9; DRIVERRF 60 (test refused) | partly from post-crash tests | CRASH-CIRCUMSTANCE / POST-CRASH | high |
| VEHICLECC / MFACTOR | post-crash inspection | CRASH-CIRCUMSTANCE | medium (inspections more likely after fatal crashes) |
| VIOLATION / MVIOLATN; DR_SF / DRIVERRF 91 | charging decision | **POST-CRASH / OUTCOME-DERIVED** | **very high**: dead drivers almost never charged; codes 1 and 9 presuppose death |
| HIT_RUN | post-crash behaviour | POST-CRASH | n/a |

---

## 16. Culpability indicator for quasi-induced exposure (key analysis 5)

### 16.1 Requirements

A QIE "not-at-fault" driver must be a quasi-random sample of drivers on the road. The definition must therefore:

* be available with the same meaning in FARS and CRSS, 2016-24;
* use **positive evidence** for both "culpable" and "non-culpable", with unknowns kept as "undetermined";
* avoid post-crash and outcome-derived inputs (charges);
* exclude any risk factor the QIE analysis will study. For example, if distraction or impairment is the exposure, it
  must not define culpability.

### 16.2 Inputs

* **SPEEDREL** (§4): yes = {2-5}; no = {0}; unknown = {9}.
* **P_CRASH2, critical pre-crash event** (vehicle table, both sources, all years). CRSS 2016-18 uses the same 57 codes.
  The roles were verified with code-pair cross-tabs in two-vehicle crashes:
  * rear-end pairs are 50/51/52 + 53: the striking vehicle has "other vehicle stopped / slower / decelerating in lane",
    and the struck vehicle has "other vehicle with higher speed". They are 36.5% of weighted CRSS pairs and 12.1% of
    FARS pairs;
  * left turn across path is 15 + 62/67;
  * straight crossing is 17 + 66;
  * lane departure into oncoming traffic is 10 + 62 (19.4% of FARS pairs);
  * head-on pairs coded 54 + 54 are ambiguous (4.5% of FARS pairs).

  Classes used:

  | class | P_CRASH2 codes |
  |---|---|
  | culpable | {6, 8, 9, 10-17, 19, 20, 21, 50, 51, 52}: own control loss (excluding mechanical and road causes), own lane departure, turning or crossing, backing, U-turn, or striking a slower or stopped vehicle in own lane |
  | non-culpable | {53, 55, 56, 60-78}: struck from behind, or the other vehicle encroached or was backing |
  | neutral, not at fault | {1-5, 18}: tyre, engine or vehicle failure, poor road, own deceleration |
  | ambiguous | {54, 59, 80-92} |
  | unknown | {98, 99} |

* **Driver-related error codes common to FARS and CRSS:** {6, 8, 102, 103, 36, 50, 51, 58} in DR_SF1-4 (2016-19) or
  DRIVERRF (2020-24), plus "looked but did not see" (distract 1 in 2016-17; DR_SF / DRIVERRF 10 from 2018).

### 16.3 Definition C1 (recommended; action-based)

* **culpable** if SPEEDREL ∈ {2-5}, or P_CRASH2 is in the culpable class, or a common error code or LBDNS is present;
* **non-culpable** if not culpable, **and** SPEEDREL = 0, **and** P_CRASH2 is in the non-culpable or neutral class,
  **and** there is no driver-factor unknown code (99 in 2016-19, 999 in 2020-21);
* **undetermined** otherwise.

Sample: crashes with exactly two vehicle rows (equal to accident VE_FORMS = 2 in 100% of crashes), both DR_PRES = 1, and
PEDS = 0. That gives FARS 110,731 crashes (of 116,831 two-vehicle crashes) and CRSS 278,771 sampled crashes (of
280,665).

### 16.4 Results: share of two-vehicle crashes with exactly one culpable and one non-culpable driver

| | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | pooled |
|---|---|---|---|---|---|---|---|---|---|---|
| FARS C1 | 76.81 | 75.89 | 75.64 | 75.41 | 72.29 | 72.02 | 71.87 | 72.15 | 70.98 | **73.56** |
| FARS: both culpable | 9.43 | 10.60 | 10.19 | 10.73 | 12.26 | 12.53 | 13.51 | 14.10 | 15.26 | 12.16 |
| CRSS C1 (wtd) | 90.84 | 90.49 | 90.34 | 90.39 | 88.45 | 90.57 | 90.64 | 89.77 | 90.26 | **90.24** |
| CRSS: both culpable | 4.91 | 4.20 | 3.98 | 4.66 | 6.33 | 4.86 | 4.69 | 5.46 | 5.13 | 4.87 |

Pooled residual categories: FARS both non-culpable 1.49% and ≥ 1 undetermined 12.79%. CRSS 1.08% and 3.82%.

**By CRSS MAX_SEV (2016-19 / 2020-24):** O 90.2 / 90.0; C 92.3 / 90.7; B 90.6 / 90.0; A 89.1 / 86.2; **K 82.0 / 78.8**.
The K value is close to FARS (75.9 / 71.9), which is consistent. The share falls with severity because "both culpable"
and "undetermined" rise. FARS crashes in which **both** drivers died are 58.8-65.3% resolvable, with 29-33%
undetermined. Crashes with a hit-and-run vehicle: FARS 63.3% and CRSS 89.5%.

**Sensitivity:**

| definition | FARS (by year) | CRSS (by year) |
|---|---|---|
| a0: P_CRASH2 alone | 79.8-82.7 | 89.6-92.4 |
| a1: P_CRASH2 + SPEEDREL | 71.6-77.9 | 88.8-91.5 |
| C2: C1 + impairment {1, 2, 9} or distraction as culpable; NR/unknown not blocking | 69.4-75.0 | 88.0-90.2 |
| C2-strict: C1 + impairment/distraction, with unknown or NR state → undetermined | **23.5-55.5**, collapsing with the NR break (55.5 in 2016 → 31.2 in 2018 → 23.5 in 2024) | **35.4-81.5**, collapsing likewise |
| C3: C1 + moving / speed / DWI / reckless violation charged | 70.5-76.2 | 88.1-90.3 |

C2-strict shows that requiring known distraction or impairment status is **not viable** after 2017. C3 adds little and
imports outcome dependence (§8).

### 16.5 Caveats

1. **The FARS decline from 76.8% to 71.0% is driven by "both culpable" rising (9.4% → 15.3%).** Among two-vehicle-crash
   drivers, the speeding share rose from 11.8% to 14.6% (the FARS 2020 SPEEDREL shift, §4.2) and the error-code share
   from 11.4% to 13.8% (code 6 broadened, §7.1). P_CRASH2 stays flat at 46.4-48.3%. For trend work, use a0/a1, or
   include year effects.
2. **Within-crash outcome asymmetry.** In FARS crashes with one killed and one surviving driver, C1 marks the killed
   driver culpable in 66.7% of cases and the survivor in 39.4-43.0%. This may be genuine: in lane-departure and
   wrong-way crashes the at-fault driver is often the one who dies. It may also reflect investigation asymmetry. The two
   cannot be separated with these data (**UNVERIFIED**). The P_CRASH2 component alone shows the same asymmetry (57.6%
   against 34.7-40.7%), so it is not created by SPEEDREL.
3. **FARS and CRSS have different sampling frames.** FARS is restricted to fatal crashes. CRSS not-at-fault drivers
   approximate the general driving population much better. Do not pool the two for QIE exposure estimates.
4. **The common error-code subset discards FARS-only information** (failure to yield, disobeying controls, lane
   misuse). In a FARS-only analysis the code list can be extended. That was not evaluated here.

---

## 17. Recommended harmonised definitions

All indicators are at driver level (one row per vehicle, DR_PRES = 1). In every recipe:

* **NA_unknown** = coded unknown;
* **NA_nr** = coded Not Reported;
* **exclude** = no driver present.

Never map NA to 0.

| name | recipe | timing | reliability |
|---|---|---|---|
| `speeding_related` | vehicle.SPEEDREL, both sources, 2016-24: {2, 3, 4, 5} → 1; 0 → 0; 9 → NA_unknown; 8 → exclude (⇔ DR_PRES ∈ {0, 9}). Subtype `speeding_type`: 2 racing, 3 over limit, 4 too fast for conditions, 5 unspecified. Check: equals veh_aux.A_SPVEH == 1 | crash-circumstance | medium |
| `distracted` | distract table; code = MDRDSTRD (≤ 2019) or DRDISTRACT (2020+); dedupe and aggregate per vehicle. Any code ∈ {3-7, 9, 10, 12-15, 17-19, 92, 93, 97, 98} → 1; else any 0 or 1 → 0 (set `lbdns_flag` = 1 if code 1); else 99 → NA_unknown; else 96 → NA_nr; 16 → exclude. Equals A_DRDIS (FARS). Options: `distracted_phone` = {5, 6, 15}; `distracted_generic` = {17, 18, 19, 92, 93} | crash-circumstance | yes: low-medium; **"no": low** |
| `drowsy` | drimpair: any 2 → 1; else any of {0, 1, 3-10, 96} → 0; else 99 → NA_unknown; 98 → NA_nr; 95 → exclude. Equals A_DRDRO | crash-circumstance | medium (yes) |
| `impaired_influence` | drimpair: any 9 → 1; same rules otherwise | crash-circumstance | medium (yes) |
| `impaired_ill` / `impaired_emotional` / `impaired_physical` | drimpair codes 1 / 8 / {3, 4, 5, 6, 7, 10, 96}; same rules | crash-circumstance | low (rare) |
| `license_invalid` (FARS only) | vehicle.L_STATUS: {0, 1, 2, 3, 4} → 1; 6 → 0; 9 → NA_unknown; 7 → exclude. Variant `license_invalid_for_class`: L_COMPL {0, 2} → 1; {1, 3} → 0; {8, 9} → NA; 6 → exclude (= A_LIC_C). Add a 2020+ indicator or year effects | pre-crash | medium-high (2020 level shift) |
| `prior_dwi_conviction` (FARS) | PREV_DWI: 1-97 → 1; 0 → 0; 99 → NA_unknown; 998 → exclude | pre-crash | medium-high |
| `prior_speeding_conviction` (FARS) | PREV_SPD: same rule | pre-crash | medium-high |
| `prior_suspension_any` (FARS) | 2016-17: PREV_SUS 1-97 → 1, 0 → 0. 2018+: any of PREV_SUS1-3 in 1-97 → 1, all three 0 → 0. 99 → NA; 998 → exclude | pre-crash | medium |
| `prior_crash_any` (FARS) | PREV_ACC 1-97 → 1; 0 → 0; **98 → NA_not_on_record** (state-specific; Georgia ≤ 2019); 99 → NA; 998 → exclude | pre-crash | low-medium |
| `driver_error_common` | 2016-19 DR_SF1-4, 2020+ driverrf: any of {6, 8, 102, 103, 36, 50, 51, 58} → 1. Else all codes 0 → 0 (note that 0 means "none noted" from 2022). Else 99 (≤ 2019) or 999 (2020-21) → NA_unknown | crash-circumstance | low-medium |
| `lbdns` (looked but did not see) | 2016-17 distract = 1; 2018-19 DR_SF* = 10; 2020+ DRIVERRF = 10 | crash-circumstance | low (2020 drop) |
| `vision_obscured` | vision: any of {1-14, 97, 98} → 1; any 0 → 0; 99 → NA_unknown; 95 → exclude | crash-circumstance | medium-low |
| `vehicle_defect` | factor: any of {1-17, 97} → 1; any 0, **or 98 (2016-19)** → 0 ("none noted"); 99 → NA_unknown | crash-circumstance | medium-low |
| `avoid_maneuver` | maneuver: any of {1-5, 92} → 1; 0 → 0; 98 → NA_nr (54-76%); 99 → NA; 95 → exclude | crash-circumstance | **low; avoid** |
| `violation_moving_charged` | violatn: any of {2-6, 10-16, 18, 19, 21-29, 31-69, 93, 98} → 1. Substantive codes take precedence over 99. Else 0 → 0; 99 → NA; 97 → NA_nr; 95 → exclude | **post-crash** | do not use for severity |
| `culpable_c1` | §16.3 | crash-circumstance | medium |

Implementation notes:

* Dedupe each multi-row table on all columns before pivoting. No exact duplicates were found in these tables, but the
  FARS `drugs` table has them.
* Aggregate with any-of. No information is lost (§3).
* For CRSS, carry WEIGHT, PSU, PSU_VAR and PSUSTRAT (or STRATUM) from the vehicle row.
* For distraction and impairment analyses, **include state × period fixed effects in FARS**, or restrict to state-years
  with NR < 5% (FARS distraction: 33 states in 2016, 17-21 states in 2018-24). In CRSS, include PSU or year effects.

---

## 18. Cross-cutting findings

1. **The "Not Reported" expansion (2016-2020) is the dominant coding break.** It affects distraction, impairment,
   manoeuvre and (≤ 2019) vehicle factors, in both FARS and CRSS. It is state- or PSU-specific and abrupt. Substantive
   "yes" codes stay stable, while "none" codes collapse. Any analysis that uses "none" as a reference category, or
   reports "share among known", has an artefactual trend.
2. **"None" changes meaning.** VEHICLECC 0 became "None Noted" in 2020, absorbing NR. DRIVERRF, PERSONRF and CRASHRF 0
   became "None Noted" in 2022, absorbing the 999 "Reported as Unknown" category used in 2020-21. From those years
   "none" means "nothing recorded".
3. **"Unknown" changes meaning in 2018** ("Unknown" → "Reported as Unknown") across SPEEDREL, DRIMPAIR, distract,
   factor, maneuver, vision, DR_SF, TRAV_SP and VSPD_LIM. The rates of SPEEDREL and distract unknown dropped at the same
   time.
4. **Ascertainment is severity-dependent in opposite directions.** Behavioural unknowns are 2-4.5× higher for killed
   drivers (no interview). Administrative unknowns are lower for killed drivers and concentrated in hit-and-run drivers.
   Charges are almost absent for killed drivers.
5. **The FARS and CRSS driver-factor code lists differ** (§7.3), and CRSS lacks licence and history variables. Of the
   behaviour indicators, only SPEEDREL, distraction, DRIMPAIR, VISION, violations and the common error subset are
   cross-source.
6. **Speeding definitions differ in practice**: about 80% of CRSS "yes" is "too fast for conditions", against about
   45% in FARS. Speed and limit data validate the label but cannot measure prevalence.
7. **The aux flags are faithful deterministic recodes** of labelled variables, except for A_MC_L_S, whose definition
   changed in 2020. A_LIC_S = 4 means "motorcycle".

---

## 19. Open questions and UNVERIFIED items

* The exact rule behind "Not Reported" vs "Not Distracted" / "None" (PAR field absent? analyst instruction?) and the
  state-specific adoption dates (§5.2, §6.2). The data show only the timing.
* Whether SPEEDREL = 0 includes PARs silent on speed. There is no NR code; 10.3% of FARS SPEEDREL = 0 drivers with known
  speeds were ≥ 10 mph over the limit.
* The meanings of PREV_SUS1, PREV_SUS2 and PREV_SUS3. SUS2 is DWI-associated (65.6% with prior DWI); only the sum is
  verified.
* The look-back window of PREV_* counts and of FIRST/LAST_YR.
* Whether the 2020 increases in FARS invalid licences (12.7% → 16.0%), speeding "yes" (17.3% → 19.3%) and DR_HGT/WGT
  unknown are real or coding.
* The names of A_MC_L_S codes 2 and 3 after 2020. Their composition is verified.
* DR_HGT 998 is labelled "Other" but is 100% no-driver rows. The label is presumably wrong; treat 998 as "no driver".
* Why CRSS 2018 `maneuver` holds one row per vehicle.
* CRSS 2016-18 P_SF codes 21, 32, 87, 89-91 and 93 (≤ 82 rows per year), and CF2/CF3 codes 16, 24 and 28 (≤ 3 rows):
  no label in any source-year.
* The culpability asymmetry between killed and surviving drivers (§16.5). Whether it is real or reflects investigation
  asymmetry cannot be established with these data.

---

## 20. Scripts (exploratory checks, not part of the package)

Directory: `scripts/audit/driver_behaviour/`.
Run them with `POLARS_MAX_THREADS=2 uv run python <script>` from the repository root. Outputs are written to `outputs/cache/audit/out/`.

| script | content |
|---|---|
| `common.py` | loader wrapper, label normalisation |
| `s01_codesets.py` | per source-year code counts from the data, joined to labels → `codesets.csv` |
| `s02_build_frame.py` | vehicle/driver audit frame with pivoted multi-row tables → `frame_{FARS,CRSS}.parquet` |
| `s03_pivot.py` | pivotability (§3) |
| `s04_speed.py` | SPEEDREL, TRAV_SP, VSPD_LIM (§4) |
| `s05_distract_impair.py` | category shares by year, severity, state and PSU (§5, §6, §8, §9) |
| `s06_zip.py` | DR_ZIP special codes; SPEEDREL = 8 × DR_PRES |
| `s07_label_transfer.py`, `s17_tvd_rename.py` | CRSS 2016-18 label transfer; TVDs (§13, §2.2) |
| `s08_aux.py`, `s09_licaux.py` | aux flag verification (§12) |
| `s10_license_history.py` | FARS licence and record (§11) |
| `s14_drf.py` | DR_SF / DRIVERRF breaks (§7) |
| `s11_culpability.py`, `s12_pc2pairs.py`, `s13_culp_decomp.py`, `s15_pc2_crss.py`, `s16_culp_pooled.py` | culpability (§16) |
