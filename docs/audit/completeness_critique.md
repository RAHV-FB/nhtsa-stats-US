# Audit appendix: completeness critique of the seven domain audits (FARS and CRSS, 2016-2024)

Scope of this appendix: what the seven domain appendices in `docs/audit/` did **not** cover, where they **contradict each
other**, and whether a sample of their **numeric claims reproduce**. Every number below was recomputed from
`data/interim` with the scripts listed in §9. No raw data or `src/` file was changed.

Evidence tags (as in the other appendices): **[L]** embedded label (`<VAR>NAME`, via `outputs/audit/codebook.csv`);
**[X]** cross-tabulation against a labelled variable; **[D]** distributional comparison; **[R]** exact reproduction of
a derived field. "w" = CRSS weighted by `WEIGHT`; "u" = unweighted.

---

## 1. Purpose and scope

1. **Coverage gaps.** A text search of all seven appendices for every column in `variable_availability.csv` found
   these never mentioned:
   * whole tables: `pbtype`, `nmcrash`, `nmprior`, `nmdistract`, `safetyeq`, `cevent`, `vevent`, `vsoe`, `damage`,
     `vehiclesf`, `pvehiclesf`, `vpictrailerdecode`. `nmimpair` appears only as a Not-Reported rate, and `parkwork` only
     as a row count.
   * FARS accident fields: EMS times (`NOT_HOUR/MIN`, `ARR_HOUR/MIN`, `HOSP_HR/MN`), `LATITUDE/LONGITUD`, `MILEPT`,
     `TWAY_ID`.
   * Vehicle fields: truck and hazmat (`V_CONFIG`, `CARGO_BT`, `HAZ_*`, `MCARR_*`, `TRLR*`).
   The person `race` table *is* covered (person appendix §4.15).
2. **Contradictions** between appendices, each resolved with code where possible (§6).
3. **Spot-checks**: 19 numeric claims were recomputed (§7).

## 2. Tables and variables covered here

| table | FARS key | CRSS key | rows/yr FARS | rows/yr CRSS | years | labels |
|---|---|---|---|---|---|---|
| pbtype | ST_CASE, VEH_NO(=0), PER_NO | CASENUM, VEH_NO(=0), PER_NO | 7,506-9,495 | 3,967-5,335 | 2016-24 | FARS all; CRSS 2019+ |
| nmcrash | + MTM_CRSH (≤2019) / NMCC (2020+) | same | 9,836-13,669 | 4,753-7,708 | 2016-24 | same |
| nmprior | + MPR_ACT / NMACTION | same | 7,886-10,058 | 4,063-5,491 | 2016-24 | same |
| nmdistract | + MNMDSTRD (2019) / NMDISTRACT (2020+) | same | 7,855-9,643 | 4,977-5,382 | **2019-24** | FARS 2019+, CRSS 2019+ |
| nmimpair | + NMIMPAIR | same | 7,636-9,664 | 4,000-5,391 | 2016-24 | same |
| safetyeq | 2016: + MSAFEQMT (long); 2017+: one row/person, wide NM* | same | 7,608-9,640 | 4,007-5,381 | 2016-24 | FARS all; CRSS 2019+ |
| cevent | ST_CASE, EVENTNUM | CASENUM, EVENTNUM | 94,082-113,745 | 79,034-93,690 | 2016-24 | same |
| vevent / vsoe | + VEH_NO, VEVENTNUM | same | 113,329-137,151 | 117,079-138,208 | 2016-24 | same |
| damage | + VEH_NO, MDAREAS (≤2019) / DAMAGE (2020+) | same | 206,835-262,344 | 163,368-203,511 | 2016-24 | same |
| vehiclesf / pvehiclesf | + VEH_NO, VEHICLESF | same | 54,552-61,803 / 1,526-1,772 | 87,463-95,785 / 2,554-3,261 | 2020-24 | 2020+ |

**Join structure [X]:**

* `pbtype` has exactly one row for every person with PER_TYP ∈ {5, 6, 7, 8, 11, 12, 13} and no other rows. Coverage is
  100% in both sources. PER_TYP 4, 10 and 19 have no row.
* `nmcrash`, `nmprior`, `nmimpair`, `safetyeq` (and `nmdistract` from 2019) cover **every** VEH_NO = 0 person, 100%.
* PBPTYPE, PBAGE and PBSEX equal person PER_TYP, AGE and SEX in 100% of rows. They are copies.
* For CRSS 2016-18 (unlabelled), every code in these tables is inside the CRSS 2019+ label set (≥ 99.95% of rows) and
  inside the same-year FARS label set (≥ 97.8%; the gaps are rare BIKECTYPE detail codes). No code-set evidence argues
  against applying labels. §6 C4 explains why code-set overlap alone is not sufficient.

---

## 3. Non-motorist tables

### 3.1 pbtype: pedestrian and bicyclist crash typing (PEDCTYPE/PEDCGP, BIKECTYPE/BIKECGP, PEDLOC, PEDPOS, BIKELOC …)

* **Who is typed [X].** Every PBPTYPE 5 person has PEDCGP ≠ 0 and BIKECGP = 0. Every PBPTYPE 6 person has
  BIKECGP ≠ 0. PBPTYPE 7 (other cyclist) is typed with the **bicycle** scheme. PBPTYPE 8 and 11-13 (personal
  conveyance) are typed with the **pedestrian** scheme (100% in both sources). Code 0 = "Not a Pedestrian" /
  "Not a Cyclist" [L] is a structural not-applicable value. PEDLOC 7 / PEDPOS 77 / BIKELOC 7 also mean not applicable.
* **Unknown codes [L]:** PEDCGP/BIKECGP 990 "Other / Unknown - Insufficient Details". PEDLOC/BIKELOC 9 "Unknown /
  Insufficient Information". PEDPOS 9 "Other/Unknown", which mixes other and unknown. PBCWALK/PBSWALK/PBSZONE 9
  "Unknown". PEDCGP 600 "Pedestrian in Roadway - Circumstances Unknown" is a *partial* unknown and stays as its own
  category.
* **Label changes [L]:**
  * PEDCGP 340 "Bus-Related" became "Bus Stop-Related" in 2017. This narrows the meaning, but code 341 counts are
    14-33 per year with no step.
  * PEDCGP 740 and PEDCTYPE 741/742 add the visual-obstruction distinction in 2020 (Dash = no obstruction, Dart-out =
    obstruction). The group code is continuous.
  * BIKECTYPE 231 adds "…or detected too late to avoid" in 2021. This broadens it, but the FARS share is
    8.9-13.8% with no step.
  * BIKECGP 240: wording only.
* **Distributions [D].** FARS pedestrians, PEDCGP %:

  | year | 750 crossing, veh. not turning | 790 crossing, turning | 400 along roadway | 100 unusual | 740 dash/dart | 600 in roadway, unk. | 990 unknown |
  |---|---|---|---|---|---|---|---|
  | 2016 | 35.20 | 4.38 | 12.73 | 11.25 | 7.09 | 7.21 | 11.77 |
  | 2019 | 37.98 | 5.03 | 13.24 | 10.46 | 6.36 | 6.03 | 11.51 |
  | 2024 | 33.61 | 4.82 | 13.66 | 11.64 | 6.57 | 7.23 | 12.56 |

  FARS PEDCGP 990 is 10.7-12.9% in every year, and BIKECGP 990 is 4.8-6.9%. CRSS (w) PEDCGP 990 is 6.2-8.8% and
  BIKECGP 990 is 1.3-2.6%.
* **Break, CRSS only [D]:** bicyclist group 110 "Loss of Control / Turning Error" falls from 10.2-10.5% (u, 2016-17) to
  4.9% (2020-21) and 2.6-3.0% (2022-24). It is driven by BIKECTYPE 112 "Motorist Turning Error - Right turn":
  90-108 rows per year in 2016-17 against 6-14 in 2022-24. Group 190 "Crossing Paths - Other" is 10.7% (w) in 2016 and
  13.1-19.8% in 2017-24, so it does not cleanly absorb the 110 decline. FARS group 110 is stable at 3.6-5.2%. The cause
  and the destination codes are UNVERIFIED. **Do not trend CRSS BIKECGP 110 across 2019→2020.**
* **Differential missingness (pooled 2016-24):**
  * PEDCGP 990: FARS killed 12.23% (n = 60,876) against 9.8% of surviving pedestrians (n = 3,712). CRSS (w) K 13.21,
    A 5.78, B 6.06, C 7.55, O 4.64.
  * BIKECGP 990 (CRSS w): K 6.11 against 1.50-2.77 for A-O.
  * PEDLOC 9: ≤ 1.6% at every KABCO level in both sources (FARS K 0.54%, CRSS K 1.30%), with no material gradient.
    It is higher only for INJ_SEV 5/9 (up to 3.5%, n ≤ 315).
  * Crash typing of fatal pedestrian crashes is therefore about twice as often "insufficient details" as for
    non-fatal ones in CRSS.
* **Reliability:** HIGH for group codes (stable code sets, continuous distributions), except the CRSS 110/190 break.
  Timing: CRASH-CIRCUMSTANCE, assigned post-crash from the police narrative.

### 3.2 nmcrash: non-motorist contributing circumstances (MTM_CRSH 2016-19 → NMCC 2020-24)

* **Codes [L], identical across the rename** (FARS 2019 vs 2020 labels): 0 None Noted; 1 Dart-Out; 2 Failure to Yield
  Right-of-Way; 3 Failure to Obey Signs/Signals/Officer; 4 In Roadway Improperly; 6 Inattentive; 9 Wrong-Way Riding or
  Walking; 11 Dash; 12 Improper Crossing (Jaywalking); 19 Not Visible (dark clothing, no lighting); 21 Other; …;
  **92 "Contributing Circumstance - No Details" (new 2021)**; 99 Unknown / Reported as Unknown. Codes 1 and 11 were
  reworded in 2019 to add the visual-obstruction distinction.
* **Structure [X]:** up to 6 (FARS) and 8 (CRSS) rows per person. Codes 0 and 99 never co-occur with another code.
  Code 92 co-occurs with other codes for 29 FARS and 5 CRSS persons.
* **Per-person rates, pedestrians + cyclists + other conveyance (PER_TYP 5-8, 11-13), %:**

  | | 2016 | 2017 | 2018 | 2019 | 2020 | 2022 | 2024 |
  |---|---|---|---|---|---|---|---|
  | FARS none noted | 29.87 | 28.16 | 27.75 | 24.65 | 25.77 | 23.99 | 22.45 |
  | FARS unknown (99) | 5.60 | 5.80 | 4.15 | 3.24 | 4.53 | 3.50 | 3.83 |
  | **FARS failure to yield (2)** | 27.84 | 28.87 | **42.20** | 45.49 | 45.51 | 48.35 | 47.72 |
  | **FARS wrong-way (9)** | 1.69 | 1.84 | 1.56 | **6.90** | 7.26 | 8.67 | 8.61 |
  | FARS jaywalking (12) | 16.70 | 18.52 | 17.41 | 17.49 | 15.05 | 17.34 | 17.33 |
  | FARS not visible (19) | 14.12 | 13.76 | 12.90 | 13.17 | 11.44 | 11.12 | 12.90 |
  | CRSS (w) none noted | 52.27 | 54.12 | 53.78 | 52.29 | 51.86 | 48.53 | 45.00 |
  | CRSS (w) failure to yield | 20.09 | 19.58 | 23.64 | 23.00 | 27.45 | 32.04 | 30.87 |
  | CRSS (w) wrong-way | 3.30 | 3.52 | 3.54 | 5.11 | 6.53 | 7.41 | 12.01 |

* **Coding breaks [D]:**
  * **FARS 2018, failure to yield:** +13.3 pp in one year (2,101 → 3,225 persons). The step is broad, not driven by one
    state: Florida +154, California +105, New York +74, Louisiana +65, Tennessee +59; Tennessee rose 7.9% → 45.8% and
    Kentucky 11.8% → 39.3%.
  * **FARS 2019, wrong-way:** 119 → 514 persons, simultaneously in Texas, Florida, South Carolina, California, New York
    and Alabama.
  * Both look like national coding-instruction changes. The cause is UNVERIFIED (no manual in the archives). The
    labels did not change. **Non-motorist "fault" shares are not comparable across 2017/2018 or 2018/2019.**
* **Differential recording [X], FARS 2020-24:**
  * Killed non-motorists: "none noted" 21.3%, failure to yield 49.7%.
  * Surviving non-motorists: 61.3% and 16.0%.
  * CRSS (w): "none noted" K 21.7% against 38.0-54.9% for A-O.
  * Contributing circumstances are recorded far more often for the dead. Treat the variable as outcome-influenced
    (POST-CRASH attribution), not as a pre-crash exposure.
* **Reliability:** LOW for trends and for killed-vs-survived comparisons; MEDIUM within a year and severity.

### 3.3 nmprior: non-motorist action prior to crash (MPR_ACT → NMACTION, 2020)

* Codes [L] are stable: 3 Crossing Roadway; 5/6 along roadway with/against traffic; 8 in roadway other; 9 adjacent
  (reworded 2018 to "Stationary and Adjacent…, Sidewalk", which broadens it); 12 disabled-vehicle related;
  16 along roadway, direction unknown (a partial unknown); 98 Not Reported; 99 Unknown.
* Not Reported is 1.3% (2016) → 3.1% (2024) in FARS, and 1.0-3.4% in CRSS (w). Unknown is 1.7-3.0% (FARS) and
  0.4-1.4% (CRSS). There is no break.
* CRSS (w) 2020-24: NR + unknown is 8.1% for K against 1.8-3.1% for A-C.
* **Reliability:** HIGH. This is the most complete non-motorist behaviour field.

### 3.4 nmdistract (2019+ only) and nmimpair

* **nmdistract [L]:** 0 Not Distracted; 96 Not Reported; 99 Reported as Unknown if Distracted; substantive codes
  2-19, 92, 93, 97, 98. The table does not exist before 2019. Per person, %:

  | | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 |
  |---|---|---|---|---|---|---|
  | FARS Not Reported | 65.74 | 73.39 | 77.83 | 75.95 | 75.65 | 74.70 |
  | FARS not distracted | 23.79 | 15.92 | 11.41 | 11.51 | 10.77 | 10.37 |
  | CRSS (w) Not Reported | 60.40 | 79.43 | 80.31 | 82.47 | 80.48 | 77.04 |

  **Unusable**: 74-82% Not Reported, and "not distracted" collapses into NR, as with driver distraction.
* **nmimpair:** the alcohol appendix reports only NR row shares. Per non-motorist (PER_TYP 5-8, 11-13), %:

  | | 2016 | 2017 | 2018 | 2019 | 2020 | 2024 |
  |---|---|---|---|---|---|---|
  | FARS NR (98) | 22.89 | 32.92 | 35.83 | 40.63 | 39.80 | 45.28 |
  | FARS unknown (99) | 25.67 | 27.06 | 28.95 | 29.85 | 26.95 | 29.11 |
  | FARS none (0) | 38.70 | 26.70 | 23.77 | 18.72 | 20.83 | 15.21 |
  | FARS alcohol/drugs (9) | 10.18 | 10.41 | 9.00 | 8.44 | 9.75 | 7.60 |
  | CRSS (w) NR | 17.49 | 21.76 | 22.61 | 39.65 | 64.35 | 65.52 |

  Unknown is strongly severity-dependent: FARS killed 29.2% against 10.9% of survivors (2020-24), and CRSS (w) K 27.7%
  against A 9.4, B 2.9, C 1.9, O 8.4. Use only "any 9" as a flag, with NA when all rows are 98/99.

### 3.5 safetyeq: non-motorist safety equipment (MSAFEQMT 2016 → NMHELMET, NMLIGHT, NMREFCLO, NMPROPAD, NMOTHPRE, NMOTHPRO 2017+)

* **Format break, 2016→2017 [L]:**
  * 2016 is long. MSAFEQMT has one row per item: 1 None Used, 2 Helmet, 3 Reflective, 4 Pads, 5 Lighting, 7 Other,
    8 Not Reported, 9 Unknown if Used. 26 FARS and 19 CRSS persons have more than one row.
  * 2017+ is one row per person with six yes/no fields: 1 No, 2 Yes, 8 Not Reported, 9 Unknown.
  * The pedalcyclist helmet is **only** here (the person appendix §4.8 flagged this table as unaudited).
* **Cyclist helmet [D], % of PER_TYP 6:**

  | | 2016* | 2017 | 2018 | 2019 | 2020 | 2022 | 2024 |
  |---|---|---|---|---|---|---|---|
  | FARS helmet yes | 16.8 | 16.48 | 15.76 | 15.24 | 18.92 | 15.53 | 13.16 |
  | FARS NR + unknown | 29.4 | 29.45 | 23.53 | 23.82 | 24.85 | 22.62 | 19.14 |
  | CRSS (w) helmet yes | 16.7 | 15.89 | 16.66 | 14.70 | 20.92 | 19.12 | 20.58 |
  | CRSS (w) NR + unknown | **63.6** | 39.88 | 37.97 | 42.12 | 39.26 | 41.76 | 38.17 |

  \*2016: helmet = any MSAFEQMT = 2; unknown = all rows ∈ {8, 9}. **CRSS 2016 is a break**: all-unknown is 56.2% (u)
  against 37.2% in 2017. FARS shows no step (29.4 → 25.6%). Drop CRSS 2016, or treat it as a separate period.
* **Pedestrian conspicuity:** NMREFCLO is Not Reported for 57.7-61.9% of FARS and 60.8-71.0% of CRSS (w) pedestrians,
  and "Yes" is about 1%. Unusable as an exposure.
* **Severity:** cyclist helmet NR/unknown is 23.2% for FARS killed cyclists, and 32.6% (K) to 44.9% (C) in CRSS (w).
  Among known status, helmet yes is 19.7% of FARS killed cyclists (n = 5,969) and 25.1-32.2% across CRSS KABCO, with no
  monotone gradient. FARS survivors (n = 183) are too few.
* When any of the six fields is NR, all six are NR for 73% of persons. NR is a person-level "not collected" state.
* **Reliability:** cyclist helmet MEDIUM (FARS) and LOW-MEDIUM (CRSS, 38-42% unknown). Other items LOW.

---

## 4. Event and damage tables

### 4.1 cevent / vevent / vsoe: sequence of events

* **Structure [R]:**
  * Every crash has ≥ 1 cevent row, and EVENTNUM is contiguous 1..n (FARS 100%; CRSS 99.996%).
  * Events per crash: FARS 1 = 33.3%, ≥ 6 = 10.3%; CRSS 1 = 65.8%.
  * Every cevent event appears in vevent (100%).
  * vsoe is an exact projection of vevent: same rows, SOE equal in 100%.
* **First harmful event [R]:**
  * SOE codes never used as HARM_EV in any year: {60-71, 79} (labels: 60 "Cargo/Equipment Loss or Shift
    (non-harmful)", 61 Equipment Failure, 62 Separation of Units, 63/64/79 Ran Off Roadway Right/Left/Unknown,
    65 Cross Median, 66 Downhill Runaway, 67 Airborne, 68 Cross Centerline, 69 Re-entering Roadway, 70 "(Non-harmful…)",
    71 End Departure).
  * HARM_EV equals the first cevent SOE outside that set in 99.9997% of FARS crashes (1 exception) and 100% of CRSS
    crashes. HARM_EV equals the EVENTNUM 1 SOE in only 50.7% (FARS) and 77.9% (CRSS).
  * Every vehicle's M_HARM appears in its own vsoe sequence (FARS 99.9996%, CRSS 100%).
  * Code 4 "Gas Inhalation" (2018-23) is never HARM_EV. Whether it counts as harmful is UNVERIFIED.
* **Code changes [L]:** the same as HARM_EV (crash appendix): 91/93 added 2017, 98 added 2019, 72 reworded 2018.
  AOI 19 adds "or Person" in 2019.
* **DATA DEFECT, CRSS 2021 vsoe.AOI [R]:**
  * Outside CRSS 2021, vsoe.AOI equals the vehicle's own area of impact from vevent (AOI1 when VNUMBER1 = VEH_NO, else
    AOI2). This holds in 100% of rows in every FARS year and every other CRSS year.
  * In CRSS 2021, for the second-listed vehicle (44,678 rows), vsoe.AOI equals **AOI1, the other vehicle's impact
    area**, in 100% of rows. It equals AOI2 in only 7.0%. That is 41,534 wrong rows, 30.75% of the 2021 vsoe rows.
  * **Derive impact areas from vevent, never from CRSS 2021 vsoe.**
* **What these tables add:**
  * Run-off-road before the first harmful event. A_VRD is built this way (aux appendix).
  * Rollover anywhere in the sequence: SOE 1, versus ROLLOVER, which changed coding in 2022.
  * Multi-impact counts.
  * Fixed-object type for every impact.
* **Reliability:** HIGH (structure verified exactly).

### 4.2 damage: areas damaged (MDAREAS 2016-19 → DAMAGE 2020-24)

* **Codes [L], unchanged across the rename:** 1-12 clock positions, 13 Top, 14 Undercarriage, 15 No Damage, 99 Damage
  Areas Unknown.
* **Structure [X]:**
  * Every in-transport vehicle has ≥ 1 row: FARS mean 4.0-4.4 rows, CRSS 1.8-2.1. Parkwork vehicles have none.
  * Codes 15 and 99 never co-occur with other codes.
  * **DEFORMED = 0 ⇒ DAMAGE = 15 in 100%** (FARS 8,030, CRSS 25,333 vehicles). Code 15 also appears for 0.3-1.1% of
    DEFORMED 8/9 vehicles.
* **Unknown (99 only), % of vehicles:** FARS 2.45-3.52%. CRSS (w) 2.49-4.17%, **except 2019: 6.98%**.
* **Differential:**
  * Hit-and-run vehicles: 31-34% unknown against 1.4-1.7% for others.
  * CRSS (w) MAX_VSEV 9: 37.5%, against 1.0-3.1% for known severity.
  * FARS: 2.4% for vehicles with a death against 3.6% without.
* **Reliability:** HIGH. An outcome/mechanism field (POST-CRASH).

### 4.3 vehiclesf / pvehiclesf (2020+) and VEH_SC1-2 (2016-19)

* VEH_SC1/VEH_SC2 (vehicle columns, 2016-19) moved to the long table vehiclesf (≤ 2 rows per vehicle; 100% coverage of
  vehicles) in 2020. This is the same pattern as crashrf/driverrf: 999 "Reported as Unknown" exists only in 2020-21
  (FARS 0.57/0.44%) and code 0 is relabelled "None" → "None Noted" in 2022 [L].
* The only analytically relevant code is 32, "Vehicle Registration for a Person with a Disability" (relabelled 2021).
  FARS: 0.72% (2016) → 0.27% (2024), a steady decline. CRSS never uses it (0.00% in every year).
* **Reliability:** LOW value. Not comparable across sources.

---

## 5. FARS-only accident and vehicle fields not covered

### 5.1 EMS times: NOT_HOUR/MIN, ARR_HOUR/MIN, HOSP_HR/MN

* **Codes [L]:**
  * Hours 0-23; 88 Not Applicable (Not Notified / Not Transported); 99 Unknown.
  * Minutes 0-59; 88; 97 "Officially Cancelled" (ARR/HOSP); 96 "Terminated Transport" (HOSP); 98 "Unknown if
    Notified / Arrived / Transported"; 99 Unknown.
* **Completeness, % of crashes:**

  | | 2016 | 2018 | 2019 | 2020 | 2022 | 2023 | 2024 |
  |---|---|---|---|---|---|---|---|
  | notification and arrival both known | 47.8 | 46.8 | 45.3 | 44.9 | 44.6 | 45.1 | **40.7** |
  | hospital arrival known | 29.4 | 26.6 | 24.8 | 21.9 | 22.8 | 23.0 | 20.4 |
  | hospital 88 (nobody transported) | 34.2 | 34.8 | 34.2 | 38.0 | 38.9 | 37.3 | 37.5 |

* **Missingness is structural by state [X]:**
  * Arrival time is unknown in more than 90% of crashes in every year for California (96.3% mean), Florida (97.1%),
    Indiana (96.6%), Virginia (98.2%, 2017-24) and South Carolina (92.2%). Texas is 84.5%.
  * Excluding the 24 state-ever-above-50% jurisdictions, unknown is 15.5-21.4%.
  * Arrival is unknown for 56.5% of urban and 48.6% of rural crashes, because the high-missing states are mostly urban.
* **Plausibility:**
  * Response time (arrival − notification, with a midnight wrap) has median 11 min (rural) and 6 min (urban), and
    p90 24 / 13 min.
  * Notification precedes the recorded crash time in 15.2% of crashes (5.2% by more than 5 min). Crash time is itself
    approximate.
* **Verdict:** usable only within reporting states, with state fixed effects. Never impute across states. An EMS
  "response time" analysis on FARS covers about 45% of fatal crashes, and that subset excludes CA, FL, TX, VA, IN and
  SC almost entirely.

### 5.2 LATITUDE / LONGITUD

* **Sentinels [L, 2016-19 only]:** 77.7777 / 777.7777 "Not Reported"; 88.8888 / 888.8888 "Not Available"; 99.9999 /
  999.9999 "Unknown" / "Reported as Unknown". In **2020-24 the label column holds only the numeric string**
  (e.g. "77.77770000"). A label-based unknown detector therefore misses them, and the sentinels must be hard-coded.
* Missing: 0.20-0.63% of crashes per year (2019 lowest, 2018 highest).

### 5.3 Truck configuration and hazmat (vehicle)

* **V_CONFIG [L], trucks BODY_TYP 60-79:**
  * Single-unit 2-axle 21.7% → 27.3%.
  * Tractor/semi-trailer 57.3% → 50.9% (2016 → 2024).
  * **New codes:** 20/21 (bus or large van, bus) from 2020. **88 "Qualifying Vehicle, Unknown Configuration" from 2021
    (1.4-1.8%).** Code 19 relabelled in 2021 from "Truck more than 10,000 lbs, cannot classify" to "Vehicle More Than
    10,000 lbs., Other". 99 Unknown is 0.2-0.9%.
  * Unknown configuration = {88, 99} from 2021, {99} before.
* **CARGO_BT:** 97 "Other" rises from 10.9% to 19.2% of trucks while 98 "Unknown Cargo Body Type" falls from 6.8% to
  3.7%. Partial reclassification; treat 97 + 98 together for trends.
* **HAZ_INV:** 2 Yes / 1 No only, with no unknown code. Yes = 2.1-3.3% of trucks.
* **vpictrailerdecode:** keyed by TRAILER_NO. It covers only 31% (2016) to 44% (2023) of FARS vehicles with
  TOW_VEH 1-4, and 551 of its 12,757 vehicles are parkwork vehicles. Do not use it for trailer prevalence.

---

## 6. Contradictions between domain appendices (resolved with code)

| # | Claim A | Claim B | Resolution (verified) |
|---|---|---|---|
| C1 | **Person** §5.1: CRSS (w) LPV-occupant restraint unknown K 10.21, A 8.53, B 5.15, C 4.96, O 6.91 (U-shaped) | **Aux** §4.1/§5.2: A_RESTUSE = 3 K 16.61, A 18.84, B 9.76, C 11.02, O 10.62 ("K/A 1.6-1.8 × O") | **Severity variable differs.** Aux stratifies by A_PERINJ, which is INJSEV_IM (imputed). That moves INJ_SEV = 9 persons, 87.7-90.7% of whom have unknown restraint, into KABCO cells. With observed INJ_SEV, the aux universe gives K 10.34, A 8.50, B 5.21, C 5.03, O 7.42, which matches the person appendix. With INJSEV_IM, the person universe gives K 15.60, A 17.24, B 8.81, C 9.42, O 9.13. Helmet shows the same effect: O 14.69% (observed) against 20.30-20.36% (imputed). **The aux "strongly differential, K/A ≈ 1.7 × O" statement is an artefact of the imputed stratifier.** Rule: report missingness by observed INJ_SEV, with 9 as its own stratum. |
| C2 | **Vehicle** §6.1: TRAV_SP missing is MNAR by severity (CRSS w K 65.2, C 49.9, O 51.6; FARS death vehicles 64.2 against 57.0) | **Driver** §4.5: TRAV_SP "known for about one-third of drivers at every severity level … driven by state rather than severity" | **Definition differs.** The driver appendix counts only 1-151/997 as known and treats 0 (stopped in-transport vehicle, a valid value [L]) as not known. TRAV_SP = 0 is 20.2% of CRSS C drivers and 15.0% of O drivers, but 1.6% of K drivers. With missing = {998, 999} (0 valid): CRSS (w) drivers K 66.0, A 61.1, B 52.9, C 50.0, O 51.5, unknown-severity 78.8; FARS killed drivers 64.9 against 57.9. **Missingness depends on severity *and* state.** The driver appendix's conclusion should be revised. |
| C3 | **Alcohol** §3.8: A_POSBAC matches "any driver BAC ≥ .01" in 99.97%; 113 deviating crashes "UNVERIFIED why" | **Aux** §4.3: threshold changed in 2020 to ALC_RES ≥ 1 (BAC ≥ .001); year-specific rule 100% | **Aux is right.** All 113 deviations are 2020-24 crashes whose only positive driver has ALC_RES 1-9, and all are coded 1. In 2016-19, 126 such crashes exist and none is coded 1. Year-specific thresholds give 100% agreement. |
| C4 | **Crash, vehicle, alcohol, survey** appendices: CRSS 2016-18 can take CRSS 2019+ labels because every code is in the 2019 label set | **Person** §6.2: apply **FARS same-year** labels, not CRSS 2019 | **Person is right for FARS-shared variables, and code-set overlap is not sufficient evidence.** REST_MIS 2016-18 codes are 100% inside the CRSS 2019 label set, yet code 0 meant "No" (all non-misusers) before 2019 and "No Indication of Mis-Use" (restraint users only) after. Rows outside the 2019 label set but inside FARS same-year labels: REST_USE 2016 5.1% (codes 7, 19, 17, 5, 0, 29), 2017-18 2.2%; AIR_BAG 2016 9.2% (0, 28); BODY_TYP 2016 11.6% (30, 31). Same-year FARS labels cover 100% / 100% / 99.99%. **Rule:** FARS same-year label first; CRSS 2019+ label only for CRSS-only variables (STRATUM, *_IM, MAX_SEV, ALCOHOL, VEH_ALCH, …); then a cross-tab signature check for known break variables. |
| C5 | **Alcohol** §5.3: surviving drivers with a measured BAC 23.0% | **Aux** §4.1: surviving drivers without a usable BAC 77.55% (that is, 22.45% usable) | **Universe differs.** INJ_SEV 9 drivers (10,558, mostly hit-and-run, rarely tested) are excluded by the alcohol appendix and included by aux. Recomputed: INJ_SEV 0-3,5 → 22.95% measured; all non-killed → 22.30% measured / 22.45% A_ALCTES 1-2. Killed: 65.25% / 65.58%; the difference is ALC_RES 998. Standardise "survivor" = INJ_SEV ∈ {0, 1, 2, 3, 5}. |
| C6 | **Person**: 2024 HISPANIC unknown 18.04%, RACE unknown 15.12%; **alcohol**: killed-driver BAC not reported 25.8% | **Aux**: A_HISP = 3 18.94%, A_RCAT = 8 15.89%, killed-driver A_ALCTES = 5 26.28% | **Definitional, all reproduce.** Aux folds Iowa redaction (HISPANIC 97 = 0.91% of 2024 fatalities; RACE 96) into unknown, and 999 "unknown if tested" into 995. Recommend reporting redacted as its own category. |
| C7 | **Survey** summary: RELJCT1 NR "21.4% (2017), 31.0% (2018), 7.3% (2020)" | **Crash**: RELJCT1 NR (w) 20.06 / 29.34 / **62.02** / 8.01 (2017-20) | Both reproduce. Survey quotes unweighted imputation rates, which cannot be computed for 2019 because RELJCT1_IM is absent. **Its summary therefore omits the worst year** (2019: 62.97% u, 62.02% w). |
| C8 | **Crash** summary: CRSS ALCOHOL unknown 13.1-14.4 / 31.8 / 39.0-39.8% | (presented beside weighted rates) | These are **unweighted**. Weighted: 15.37, 14.88, 13.18 (2016-18), 31.76 (2019), 38.34-39.83 (2020-24). The conclusion is unchanged. |
| C9 | **Vehicle**: VEH_ALCH unknown 8.5-10.9% (2016-18) | **Alcohol**: 8.3-9.7% | Weighted (vehicle) against unweighted (alcohol). Consistent. |

---

## 7. Spot-checks of numeric claims (recomputed)

| # | Appendix | Claim | Recomputed | Verdict |
|---|---|---|---|---|
| 1 | person | INJ_SEV = 4 count = FATALS in all 325,922 crashes; 353,706 fatalities | 325,922; 353,706; 0 mismatches | reproduces |
| 2 | survey | CRSS Σ WEIGHT (MAXSEV_IM = 4) = FARS fatal crashes in 2016 (34,748) and 2024 (36,297); −0.91 to −0.30% otherwise | 34,748 / 36,297 exactly; 2017 −0.91%, 2023 −0.30% | reproduces |
| 3 | vehicle | FARS VTRAFCON 97: 0.17% → 19.76%; 0: 79.97% → 57.74% | 0.17 → 19.76; 79.97 → 57.74 | reproduces |
| 4 | person | FARS REST_USE 7 = 19.05% (2016); 20 = 19.22% (2018) → 26.56% (2019) | identical | reproduces |
| 5 | driver | FARS driver distraction NR 15.9% (2016) → 51.5% (2024); Georgia 0.1 → 84.7% (2018) | identical | reproduces |
| 6 | crash | FARS WEATHER NR 7.4% (2019), 3.9% (2022); Virginia 84-90% every year | 7.44, 3.90; Virginia 83.5% in 2020 (83.5-89.9) | reproduces (Virginia range slightly off) |
| 7 | crash | CRSS RELJCT1 NR (w) 1.83 / 20.06 / 29.34 / 62.02 / 8.01 | identical | reproduces |
| 8 | crash | CRSS ALCOHOL = 9: 13.1-14.4 / 31.8 / 39.0-39.8% | unweighted identical; weighted differs (C8) | reproduces as unweighted |
| 9 | driver | SPEEDREL 8 ⇔ DR_PRES ∈ {0, 9}: 3,123 FARS, 1,824 CRSS rows | identical; 100% equivalence | reproduces |
| 10 | survey | 157 CRSS crashes without person rows are exactly the MAX_SEV = 8 crashes | 157 = 157 | reproduces |
| 11 | survey | 2016 weight CV 0.742, max/min 258; Kish deff 1.31-1.55 | identical | reproduces |
| 12 | crash | URBANICITY constant within 60 PSUs (39 urban, 21 rural) | identical | reproduces |
| 13 | vehicle | FARS HIT_RUN yes 3.9% → 4.8% in 2020 | 3.93 → 4.78 | reproduces |
| 14 | person | Iowa fatalities 2020-24 100% redacted, 1,770 persons, "343-379 per year" | 1,770, 100%; per year 343, 356, **336**, 379, 356 | reproduces (range should be 336-379) |
| 15 | alcohol | measured BAC: killed 65.3%, survivors 23.0% | 65.25%; 22.95% (survivors = INJ_SEV 0-3, 5) | reproduces with that universe (C5) |
| 16 | crash | unknown HOUR: killed 0.72% vs survivors 0.18% | 0.722 vs 0.176 (INJ_SEV 0-3); 0.225 for all non-killed | reproduces |
| 17 | person | INJ_SEV 9 = 1.3-1.8% FARS; 69% / 77% in HIT_RUN = 1 vehicles | 1.26-1.82%; 69.3% / 76.6% (u; 73.7% w) | reproduces |
| 18 | vehicle | TRAV_SP known FARS 37.4% (2016), CRSS (w) 45.0% (2016) | 37.4, 45.0 | reproduces |
| **19** | **vehicle §2** | **vpicdecode coverage of in-transport vehicles FARS 97.5-98.4%; CRSS 95.0, 90.4 (2017), 96.4-96.9, 85.6/86.0 (2023-24)** | **FARS 95.0-95.8%; CRSS 92.5, 87.7, 93.8, 94.0, 93.6, 93.9, 94.0, 83.3, 83.9** | **does not reproduce** |

**Failed check (19), explained.** The published figures equal vpicdecode rows ÷ vehicle rows (FARS 2016: 51,400 /
52,714 = 97.5%). They count the vpicdecode rows of **parkwork** vehicles, although the same section shows those rows do
not match `vehicle` (1,319 in FARS 2016). True coverage is (51,400 − 1,319) / 52,714 = 95.0%. Every vpicdecode-based
rate in the vehicle appendix that uses this denominator is overstated by about 2.5 pp. The ADAS / ESC conclusions are
unaffected.

---

## 8. Cross-cutting findings

1. **Non-motorist analyses had no audit.** The person appendix covers PER_TYP and INJ_SEV of pedestrians, but their
   crash type, behaviour, impairment, distraction and safety equipment are in six unaudited tables.
   * pbtype and nmprior are HIGH quality.
   * nmcrash has two national coding steps: failure to yield +13 pp in 2018, wrong-way ×4 in 2019.
   * nmdistract (74-82% NR) and pedestrian conspicuity (58-71% NR) are unusable.
   * Cyclist helmet is in safetyeq, not HELM_USE.
2. **Stratifying missingness by an imputed severity (INJSEV_IM / A_PERINJ / MAXSEV_IM) manufactures severity
   gradients** in any field whose unknowns co-occur with unknown injury: restraint, helmet, and probably age and
   ejection in aux §5.2. Differential-missingness tables must use the observed severity, with "unknown severity" shown
   separately.
3. **"Known" must keep structural zeros.** TRAV_SP = 0 (stopped) and DAMAGE = 15 (no damage) are valid values that
   cluster in low-severity crashes. Treating them as missing inverts severity gradients (C2).
4. **Code-set overlap is necessary but not sufficient for label transfer** (C4, REST_MIS). Same-year FARS labels are the
   safer source for CRSS 2016-18.
5. **Label columns cannot always find sentinels.** FARS 2020+ LATITUDE/LONGITUD labels are numeric strings. Codebook
   "unknown" detection must also be hard-coded per variable.
6. **CRSS 2021 vsoe.AOI is defective** for 30.75% of rows. Any table-to-table projection should be re-derived from
   its source table (vevent), not trusted.
7. **EMS times** are FARS's only pre-hospital process measure. They are missing for more than 90% of crashes in six
   large states. Any rural/urban EMS comparison is confounded by which states report.
8. **Survivor universe:** INJ_SEV 9 persons (1.3-1.8% FARS, 3.6-4.6% CRSS w, about 70% hit-and-run) must be assigned
   explicitly. The appendices disagree implicitly (C5, C1).

## 9. Recommended harmonised definitions (new variables only)

See the structured summary returned with this appendix for implementable recipes. In brief:

* `ped_crash_group` = PEDCGP (PBPTYPE 5, 8, 11-13), with 990 → NA.
* `bike_crash_group` = BIKECGP (PBPTYPE 6, 7), with 990 → NA; flag CRSS 110/190 from 2020.
* `ped_location` = PEDLOC 1-4, with 9 → NA.
* `nm_prior_action` from MPR_ACT/NMACTION (98/99 → NA).
* `nm_factor_*` flags from MTM_CRSH/NMCC, with period indicators for 2018 and 2019.
* `cyclist_helmet` from MSAFEQMT (2016) / NMHELMET (2017+).
* `first_harmful_event` and `ror_before_fh` from cevent/vevent (non-harmful SOE = {60-71, 79}).
* `damage_area_*` from MDAREAS/DAMAGE.
* `ems_response_min` from NOT_*/ARR_*.
* `truck_config` from V_CONFIG.

## 10. Open questions / UNVERIFIED

* Causes of the nmcrash steps (FARS failure to yield 2018, wrong-way 2019). They are multi-state, which suggests coding
  instructions, but there is no manual in the archives.
* Cause of the CRSS bicyclist group 110 → 190 shift (2020-22).
* Whether SOE 4 "Gas Inhalation" (2018-23) is a harmful event. It is never HARM_EV.
* Whether CRSS 2021 vsoe.AOI was corrected in a later NHTSA release (not checkable here).
* Why notification time precedes crash time in 15% of FARS crashes. Crash time may be estimated; UNVERIFIED.
* Whether V_CONFIG 88 (2021+) absorbed cases formerly coded 19 or 99. Code 19 falls from 2.3-2.4% (2019-20) to
  1.2% (2022-24), consistent but UNVERIFIED.
* CRSS 2016 safetyeq all-unknown 56% (u) against 37% (2017). A format-conversion artefact is suspected; UNVERIFIED.

## 11. Scripts

Scratch scripts are in
`/tmp/claude-0/-home-user-nhtsa-stats-US/dd56b1ab-53ab-5c90-8154-cdf8a010f996/scratchpad/audit_scripts/`, outside the
repository:

* `util.py`
* `pb_01-04.py` (pbtype)
* `nm_01-05.py` (non-motorist tables)
* `ev_01-02.py` (event tables)
* `dmg_01.py`, `vsf_01.py`, `ems_01-02.py`, `ll_01.py`, `trk_01.py`, `misc_01.py`
* `crss_lab.py`, `con_01-05.py` (contradictions)
* `spot_01-07.py` (spot-checks)
* `lab_01.py`
