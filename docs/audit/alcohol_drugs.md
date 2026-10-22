# Audit appendix: alcohol and drug measurement, FARS and CRSS 2016-2024

*Data audited: typed Parquet cache `data/interim/{FARS,CRSS}/{person,vehicle,accident,drugs,drimpair,nmimpair,miper,midrvacc,miacc,acc_aux,per_aux}/{year}.parquet`,
plus the inventory files in `outputs/audit/`. The analysis scripts are not part of the package. They are in
`/tmp/claude-0/-home-user-nhtsa-stats-US/dd56b1ab-53ab-5c90-8154-cdf8a010f996/scratchpad/audit_scripts/ad/`:*

| Script | Purpose |
|---|---|
| `ad_cb.py`, `ad_02_dist.py`, `ad_show.py` | code × label × year distributions |
| `ad_01_alcres.py` | ALC_RES units and special codes |
| `ad_03_drugres_codes.py`, `ad_04_drugres_bands.py` | DRUGRES code schemes |
| `ad_05_build_fars.py`, `ad_13_build_crss.py` | person-level analysis files |
| `ad_06_mi.py`, `ad_08_crashlevel.py` | multiple-imputation tables, A_POSBAC, DRUNK_DR |
| `ad_07_consistency.py` | ALC_STATUS / ATST_TYP / ALC_RES / A_ALCTES / DR_DRINK |
| `ad_09_drugs_struct.py`, `ad_10_drug_person.py` | drugs-table structure and person-level drug summary |
| `ad_11_fars_testrates.py` | test rates by severity, year and state |
| `ad_12_sens.py`, `ad_16_selection.py`, `ad_17_or_bias.py` | police report vs BAC, selection, odds-ratio bias |
| `ad_14_crss_derive.py`, `ad_15_crss_sev.py`, `ad_19_crss_transfer.py` | CRSS derivations, severity, 2016-18 label transfer |
| `ad_18_drug_results.py`, `ad_20_misc.py` | drug results; 2024 provisional data; vitreous; crash-level comparison |

Intermediate files are in `.../scratchpad/out_ad/`.

*No external documentation was used. Evidence tags:*
- **[label]**: the meaning comes from the in-archive `<VAR>NAME` column.
- **[xtab]**: the meaning was verified by cross-tabulating against a labelled or structurally linked variable.
- **[derived-100%]**: an exact reconstruction rule was verified on every record.
- **UNVERIFIED**: the meaning could not be checked against the data.

---

## 1. Purpose and scope

This appendix covers every alcohol and drug field that later analyses might use as an exposure, covariate or outcome. For each one it
records:

1. availability by source-year;
2. codes and their meanings, with evidence;
3. coding and definition breaks;
4. unknown and not-reported codes, with rates by year and **by severity**;
5. a reliability verdict;
6. a harmonised definition.

It also answers five analytic questions:

- (§5.1) how alcohol and drug testing is selected by injury severity, year and state;
- (§5.2) how CRSS police-reported alcohol varies with crash severity and how it compares with FARS BAC;
- (§5.3) what share of FARS BAC is measured and what share is imputed;
- (§5.4) which alcohol measure can be defended for FARS and for CRSS severity models, and the direction and size of ascertainment bias;
- (§5.5) whether drug variables can be used.

**Severity definitions used throughout.**
- FARS drivers are `person` records with PER_TYP = 1 ("Driver of a Motor Vehicle In-Transport" **[label]**).
  - **Killed** = INJ_SEV 4 "Fatal Injury (K)" **[label]**: n = 222,856 drivers, 2016-2024.
  - **Survived** = INJ_SEV 0, 1, 2, 3 or 5: n = 264,519.
  - Excluded: INJ_SEV 9 (n = 10,558) and 6 "Died Prior to Crash" (n = 22).
  - FARS survivors are drivers who survived a *fatal* crash. They are not a sample of drivers in general.
- CRSS severity uses KABCO codes O = 0, C = 1, B = 2, A = 3, K = 4 **[label 2019-24]**.
  - Crash severity is accident MAX_SEV. Driver severity is the driver's own INJ_SEV.
  - CRSS percentages are **weighted by WEIGHT** unless marked otherwise. No design-based variances are computed here.

## 2. Tables and variables covered

| Concept | FARS | CRSS | Years |
|---|---|---|---|
| Police-reported alcohol | person.DRINKING | person.DRINKING | all |
| Alcohol test status / type / result | person.ALC_STATUS, ATST_TYP, ALC_RES | same | all |
| Alcohol determination method | person.ALC_DET | – | FARS 2016-21 |
| Imputed person alcohol (binary) | – | person.PERALCH_IM | all |
| Multiply-imputed BAC (10 implicates) | miper P1-P10; midrvacc A1-A10; miacc A1-A10 | – | all |
| Driver alcohol (vehicle) | vehicle.DR_DRINK (0/1) | vehicle.VEH_ALCH, V_ALCH_IM | all |
| Crash alcohol | accident.DRUNK_DR (count; 2016-20 only); acc_aux.A_POSBAC | accident.ALCOHOL, ALCHL_IM | as stated |
| Person test summary (aux) | per_aux.A_ALCTES | – | all |
| Police-reported drugs | person.DRUGS | person.DRUGS | all |
| Drug determination method | person.DRUG_DET | – | FARS 2016-21 |
| Drug tests (person columns) | person.DRUGTST1-3, DRUGRES1-3 | same | 2016-17 only |
| Drug tests (long table) | drugs: DRUGSPEC, DRUGRES (+DRUGMETHOD, DRUGQTY, DRUGUOM, DRUGACTQTY 2023-24) | – | FARS 2018-24 |
| Impairment | drimpair.DRIMPAIR, nmimpair.NMIMPAIR (code 9) | same | all |

CRSS 2016-2018 and all aux and MI tables have no label columns. FARS person.ALC_RES has labels in every year, but
`codebook.csv` collapses them (`<442 codes>`), so the labels were read directly from the Parquet files.

---

## 3. Per-variable sections: alcohol

### 3.1 DRINKING (person; police-reported alcohol involvement)

**Codes [label, FARS 2016-24 and CRSS 2019-24]:**

| Code | Label |
|---|---|
| 0 | No (Alcohol Not Involved) |
| 1 | Yes (Alcohol Involved) |
| 8 | Not Reported |
| 9 | Unknown (Police Reported) in FARS 2016-17; Reported as Unknown in FARS 2018+ and CRSS 2019+ |

The code-9 wording change is cosmetic: the FARS code-9 share is 11.4-11.8 % in 2016-19 with no step at 2018. The **unknown set is {8, 9}**.

**Distribution, all persons (%):**

| | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 |
|---|---|---|---|---|---|---|---|---|---|
| FARS 0 | 42.2 | 44.6 | 43.9 | 42.8 | 41.4 | 39.0 | 37.2 | 38.0 | 38.0 |
| FARS 1 | 9.8 | 9.9 | 9.5 | 9.5 | 10.5 | 9.9 | 9.9 | 9.3 | 9.1 |
| FARS 8 | 36.2 | 34.1 | 34.9 | 35.9 | 37.7 | 40.4 | 41.3 | 42.1 | 42.5 |
| FARS 9 | 11.8 | 11.4 | 11.7 | 11.8 | 10.4 | 10.8 | 11.6 | 10.6 | 10.4 |
| CRSS drivers 0 (wtd) | 86.9 | 87.6 | 89.4 | 70.4 | 62.1 | 63.9 | 62.9 | 64.2 | 63.8 |
| CRSS drivers 1 (wtd) | 2.24 | 2.18 | 2.03 | 1.92 | 2.49 | 2.26 | 2.31 | 2.16 | 2.14 |
| CRSS drivers 8 (wtd) | 5.4 | 5.6 | 4.6 | **23.9** | **31.4** | 29.8 | 30.9 | 29.7 | 30.4 |
| CRSS drivers 9 (wtd) | 5.5 | 4.7 | 4.0 | 3.9 | 4.0 | 4.1 | 3.9 | 4.0 | 3.7 |

**Coding break: CRSS, 2019 and 2020.**
- The share of drivers coded "Not Reported" rose from 4.6 % (2018) to 23.9 % (2019) and to 31.4 % (2020). "No" fell by the same amount.
  The "Yes" share stayed between 1.9 and 2.5 %.
- The step is present from January of each year:
  - driver code 8, unweighted: December 2018 7.1 %, January 2019 23.6 %;
  - December 2019 22.9 %, January 2020 30.6 %.
- It is the same for every injury severity (2018 → 2020: O 3.6 → 29.5 %, K 7.3 → 31.0 %).
- It is therefore a processing or coding change, not a change in behaviour. The likely mechanism is that before 2019 non-reports were
  coded 0. This is supported by the data but the mechanism itself is **UNVERIFIED**.
- Passengers are 83-90 % code 8 in every year, so the break is a driver and non-motorist phenomenon. Non-motorist code 8: 6.9 % (2018) → 32.1 % (2019) → 42.8 % (2020).
- Total-variation distance (TVD) from 2018 to 2019 is 0.151, against ≤ 0.019 between other adjacent years apart from 2019→20 (0.060).
- **Consequence:** in CRSS, "No" is not comparable across 2018/2019/2020. Only "Yes" against "not Yes" is stable.

FARS has no step change, but "Not Reported" drifts upward from 34-36 % (2016-19) to 40-42 % (2021-24).

**Differential missingness by severity, FARS drivers.**

Pooled share of each code:

| | 0 | 1 | 8 | 9 |
|---|---|---|---|---|
| Killed | 43.4 % | 18.5 % | 16.3 % | **21.8 %** |
| Survived | 67.0 % | 8.5 % | 18.9 % | 5.6 % |

Share unknown (8 or 9) by year:

| | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 |
|---|---|---|---|---|---|---|---|---|---|
| Killed | 35.6 | 33.5 | 34.5 | 35.6 | 35.6 | 40.1 | 42.7 | 41.9 | 42.6 |
| Survived | 20.0 | 18.4 | 19.7 | 20.9 | 24.0 | 26.4 | 29.1 | 30.0 | 29.9 |

**Differential missingness by severity, CRSS drivers** (weighted DRINKING = 9 by own INJ_SEV):
- O 1.6-2.7 %, C 1.0-1.7 %, B 1.1-1.7 %, A 3.6-5.1 %, **K 20.6-27.7 %** in every year.
- Code 8 does not depend on severity: in 2020-24 every level is 27-31 %.

**Validity against measured BAC** is covered in §5.4. In short, police "Yes" detects BAC ≥ .08 in 63 % of killed and 95 % of surviving tested
FARS drivers. Most of the shortfall in killed drivers comes from codes 8 and 9, not from 0.

**Verdict:** medium reliability for "Yes"; low reliability for "No" and the unknown categories. Severity-dependent ascertainment is the main threat (§5.4).

**Harmonised definition:** `alc_police_yes` = 1 if DRINKING = 1, 0 if DRINKING = 0, missing if DRINKING ∈ {8, 9}.
- For CRSS trend work that crosses 2018/19/20, use the binary "1 vs not 1".
- Report yes/no/unknown separately only within 2020-24 (or 2016-18).

### 3.2 ALC_STATUS (person; alcohol test status)

**Codes [label]:**

| Code | Label | Years |
|---|---|---|
| 0 | Test Not Given | all |
| 1 | Test Refused | **2016 only**: FARS 83, CRSS 261 |
| 2 | Test Given | all |
| 8 | Not Reported | all |
| 9 | Unknown if Tested (2016-17) / Reported as Unknown if Tested (2018+) | all |

**Evidence for structure [xtab, all persons 2016-24]:**
- FARS ALC_STATUS against ALC_RES:
  - 0 → 996 (432,314) and 995 (1);
  - 1 → 996 (83);
  - 2 → measured 0-940 (273,900), 997 (11,261), 998 (1,549), 995 (62);
  - 8 → 995 (68,235) and measured (3);
  - 9 → 999 (13,280).
  - Only 66 of 800,688 records (0.008 %) are discordant.
- CRSS: the same mapping holds with zero discordance in every year, **including the unlabelled 2016-18**.

**Code 1 removed after 2016.**
- In 2016, ATST_TYP 0 ("Test Not Given") = ALC_STATUS 0 + 1 exactly (47,892 = 47,809 + 83).
- From 2017, ATST_TYP 0 = ALC_STATUS 0 exactly (for example 47,154 = 47,154).
- So refusals were inside "not given" in ATST_TYP even in 2016. Whether refusals are coded 0 or 8 after 2016 is **UNVERIFIED**.
- Harmonise 2016 code 1 → "not tested".

**Rates, all persons (%):**

| | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 |
|---|---|---|---|---|---|---|---|---|---|
| FARS 2 given | 38.8 | 38.7 | 37.8 | 37.4 | 36.0 | 34.3 | 34.2 | 34.7 | 31.2 |
| FARS 8 not reported | 4.3 | 5.0 | 6.4 | 6.2 | 9.0 | 8.0 | 8.8 | 9.9 | **18.6** |
| FARS 9 unknown if tested | 1.45 | 1.44 | 0.68 | 1.08 | 0.52 | 2.98 | 3.39 | 2.54 | 0.38 |
| CRSS 2 given | 1.52 | 1.43 | 1.27 | 1.32 | **2.33** | 2.40 | 2.08 | 1.96 | 1.84 |
| CRSS 8 not reported | 12.9 | 18.4 | 17.0 | 16.0 | 17.7 | 17.0 | 17.8 | 18.1 | 18.0 |

**Two artefacts.**

1. **FARS 2024 is provisional for toxicology.**
   - Among killed drivers, ALC_RES = 995 is 9.4 % in 2023 and 25.8 % in 2024. It rises by month of crash (Jan 23.2 % → Dec 32.0 %).
   - It is concentrated in large states. Change from 2023 to 2024:

     | State | 2023 | 2024 |
     |---|---|---|
     | Florida | 11.2 % | 59.6 % |
     | North Carolina | 11.9 % | 57.9 % |
     | Texas | 1.6 % | 46.6 % |
     | New York | 26.9 % | 68.8 % |
     | Oklahoma | 0.4 % | 39.8 % |

   - This looks like toxicology reports not yet received when the file was frozen. The mechanism is **UNVERIFIED**.
2. **The CRSS 2020 jump in "Test Given" is mainly a recording change in two PSUs.**
   - From 2020, CRSS has 509-1,125 records per year with ALC_RES = 0 and ATST_TYP = 98 (Unknown Test Type).
   - 98.3 % of the 3,988 such records in 2020-24 come from PSU 29 (3,338) and PSU 14 (535).
   - In PSU 29 they are 35.6 % of all person records in 2020-24. Almost all are drivers with DRINKING = 0.
   - Measured BAC = 0 in CRSS went from 114-199 per year (2016-19) to 684-1,237 (2020-24).

**Verdict:** high reliability as a test-status indicator, since it is internally consistent. Its rate depends strongly on severity and state (§5.1).

**Harmonised definition:** derive test status from **ALC_RES** (§3.4), which carries the same information at finer resolution. Use ALC_STATUS only for cross-checks.

### 3.3 ATST_TYP (person; alcohol test type)

**Codes [label FARS 2016-24, CRSS 2019-24]:**

| Code | Label | Notes |
|---|---|---|
| 0 | Test Not Given | |
| 1 | Blood | |
| 2 | Breath Test (AC) | |
| 3 | Urine | |
| 4 | Vitreous | not in CRSS |
| 5 | Blood Plasma/Serum | not in CRSS |
| 6 | Blood Clot | not in CRSS |
| 7 | Liver | not in CRSS |
| 8 | Other Test Type | |
| 10 | Preliminary Breath Test (PBT) | |
| 11 | Breath Test, Unknown Type | **new in 2018** in both FARS and CRSS |
| 95 | Not Reported | |
| 98 | Unknown Test Type | |
| 99 | (Reported as) Unknown if Tested | |

- In CRSS 2016-18 the code set is a subset of the 2019+ set. TVD from 2018 to 2019 is 0.011.
- ATST_TYP = 95 sometimes has a result: 1,109 persons with ATST_TYP 95 have a measured BAC, and 6,025 measured BACs have type 98.
  "Not reported" type is therefore **not** "not tested".

**Coding break: vitreous in FARS 2020.**
- ATST_TYP 4 rose from 0.28-0.46 % of persons (2016-19) to 2.97-3.90 % (2020-24). Blood fell from 33.5 % to 28.9 %.
- The jump is simultaneous in several states. Vitreous counts, 2019 → 2020:

  | State | 2019 | 2020 |
  |---|---|---|
  | Texas | 22 | 378 |
  | Virginia | 8 | 321 |
  | Ohio | 49 | 211 |
  | California | 12 | 200 |
  | Connecticut | 8 | 175 |
  | Oklahoma | 10 | 145 |

- This pattern suggests a change in how the reported specimen is chosen when several were taken, not a change in practice. **UNVERIFIED**.
- Vitreous gives the highest share of BAC ≥ .08 among specimen types: 10,059 of 17,659 measured (57 %), against 63,576 of 233,192 (27 %) for blood.
  Vitreous testing is almost entirely post-mortem [xtab]: 17,690 of 17,725 vitreous-tested persons have INJ_SEV = 4, and 397 of 398 liver-tested persons. The high positivity reflects case mix.

**Verdict:** reliable as recorded. Specimen mix is not stable across 2019/2020.

**Harmonised definition:** `alc_test_type` groups:

| Group | Codes |
|---|---|
| blood | {1, 5, 6} |
| breath_evidential | {2} |
| breath_pbt | {10} |
| breath_unknown | {11} (2018+; was absorbed elsewhere before) |
| urine | {3} |
| vitreous | {4} |
| liver_other | {7, 8} |
| type_unknown | {98, 95 with a result} |
| not_tested | {0} |
| unknown | {95 without a result, 99} |

### 3.4 ALC_RES (person; alcohol test result)

**Units [label].**
- Every labelled numeric code c in 0-939 has the label "0.ccc % BAC". This holds for all 4,083 labelled code-year pairs in FARS and all 1,126 in CRSS 2019-24,
  with zero mismatches of label value × 1000 against code.
- ALC_RES is therefore **BAC in grams per decilitre × 1000** (% w/v = g/100 mL). Code 80 = 0.080 g/dL.

**Special codes [label]:**

| Code | Label | FARS persons, pooled |
|---|---|---|
| 940 | ".94 % or Greater" (top code) | 7 |
| 995 | Not Reported | 68,298 |
| 996 | Test Not Given | 432,397 |
| 997 | AC Test Performed, Results Unknown | 11,261 |
| 998 | Positive Reading with No Actual Value | 1,549 |
| 999 | Unknown if Tested (2016-17) / Reported as Unknown if Tested | 13,280 |

There are no "pending" codes. Pending toxicology appears to fall into 995 or 999 (see the 2024 note in §3.2).

**Values.**
- 273,903 FARS persons have a measured value.
- Median among positives is 0.168 g/dL; the 99th percentile is 0.400.
- 1,000 values are ≥ 0.40; 185 are ≥ 0.50; codes 900-930 occur once each.
- **Digit preference:** 45.0 % of positive values in 2016 are multiples of 0.010, against 10 % expected at 3-decimal precision. This falls to 31.0 % by 2024.
  Many results are reported at 2-decimal precision.
- CRSS 2016-18 code sets are numeric 0-940 plus 995-999, the same structure as 2019+. ALC_STATUS ↔ ALC_RES consistency is 100 %
  ([xtab]). Labels can be transferred (§6).

**Differential missingness:** see §5.1. Measured share of drivers: killed 65.3 %, survived 23.0 %. CRSS drivers: 0.5-1.7 % (O) to 5-13 % (K).

**Verdict:**
- FARS: high validity where measured. Measurement selection is severe for survivors and mild for killed drivers.
- CRSS: measured BAC is not usable for prevalence or severity models. There are 9,901 driver records with INJ_SEV 0-4 over 9 years (10,232 persons in all), and tested drivers are mostly police-"Yes" (§5.2).

**Harmonised definition:**

| Variable | Rule |
|---|---|
| `bac_gdl` | ALC_RES / 1000 for ALC_RES ∈ [0, 939]; 0.94 with a `bac_topcoded` flag for 940; null otherwise |
| `bac_ge08` | 1 if ALC_RES ∈ [80, 940]; 0 if ALC_RES ∈ [0, 79]; null otherwise (998 is null) |
| `bac_pos01` | 1 if ALC_RES ∈ [10, 940] or ALC_RES = 998; 0 if ALC_RES ∈ [0, 9]; null otherwise |
| `alc_test_status` | 0-940 → tested_result; 997 → tested_result_unknown; 998 → tested_positive_no_value; 996 (and ALC_STATUS 1 in 2016) → not_tested; 995 → not_reported; 999 → unknown_if_tested |

### 3.5 ALC_DET (FARS person, 2016-2021; police alcohol determination method)

**Codes [label]:**

| Code | Label |
|---|---|
| 1 | Evidential Test (breath, blood, urine) |
| 2 | Preliminary Breath Test (PBT) |
| 3 | **Behavioral** (2016-18) → **Standard Field Sobriety Test** (2019-21) — a meaning change |
| 4 | Passive Alcohol Sensor (PAS) |
| 5 | Observed |
| 6 | Breath Test, Unknown Type (2021 only) |
| 8 | Other (e.g., Saliva test) |
| 9 | Not Reported |

- Code 9 covers 79.8-82.6 % of persons every year.
- Among drivers, 97.9 % of ALC_DET = 1 records have a measured BAC ([xtab]: 50,121 of 51,205). ALC_DET = 5 "Observed" is mostly untested (11,471 of 18,758).
- The variable was dropped after 2021.

**Verdict:** low value. Do not harmonise. It documents the basis for DRINKING.

### 3.6 FARS multiply-imputed BAC: MIPER, MIDRVACC, MIACC

**Structure** (verified on every record, 2016-24):

| Table | Grain | Coverage | Columns |
|---|---|---|---|
| `miper` | person | every **driver** (PER_TYP 1: 497,955 of 497,955), every **non-motorist** (PER_TYP 5, 6, 7, 8, 10, 11, 12, 13, 19: 100 %), plus 235 of 907 PER_TYP 9 and 36 of 221,721 passengers | P1-P10 |
| `midrvacc` | crash | the 325,293 crashes with ≥ 1 driver record; 629 crashes with no driver are absent | A1-A10 |
| `miacc` | crash | all 325,922 crashes | A1-A10 |

- There are **10 implicates**. The 10 columns are separate imputations.
- **Units:** integer **hundredths of g/dL** (0-94; 94 = top code, matching ALC_RES 940).
  - For persons with a measured ALC_RES, P_k = **floor(ALC_RES / 10)** for 99.96 % (249,615 of 249,703).
  - Rounding matches only 89.2 % and ceiling 78.2 %.
  - All 10 implicates are identical for 99.97 % of measured persons. Of the 88 persons where floor() does not match, 57 are PER_TYP 9 (unknown occupant type).
- **Crash tables [derived-100%]:**
  - MIDRVACC A_k = max over drivers in the crash of P_k (100.000 % match for each k).
  - MIACC A_k = max over all `miper` persons in the crash of P_k (100.000 %).
- **Which persons are imputed:** every person with ALC_RES ∈ {995, 996, 997, 998, 999}. Their implicates vary: only 17-44 % have 10 identical values.

  Mean share of implicates ≥ 8 (i.e., ≥ .08):

  | ALC_RES | Mean P(≥ .08) |
  |---|---|
  | 995 | 0.191 |
  | 996 | 0.126 |
  | 997 | 0.318 |
  | 998 | 0.574 |
  | 999 | 0.237 |

- **Caution: code 998 is not conditioned on positivity.** For 68.1 % of the 1,429 persons with ALC_RES = 998, at least one implicate is 0.
  The imputation model's covariates are not documented in the data (**UNVERIFIED**). If it uses DRINKING as a predictor, which is likely, MI-based
  "police vs BAC" comparisons are partly circular.

**Measured vs imputed share among FARS drivers (§5.3):** 41.5 % measured pooled (206,745 of 497,955). By year: 46.4, 45.9, 44.3, 43.4, 41.3, 39.7, 39.0, 39.2,
35.9 % (2016 → 2024).

**Verdict:** the only FARS alcohol measure with complete coverage of drivers and non-motorists and with constant units across years.
Analyse with Rubin's rules over the 10 implicates.

**Harmonised definition:** `bac_mi_k` (k = 1..10) = P_k / 100 g/dL. `bac08_mi_k` = 1(P_k ≥ 8). Crash-level `crash_maxdrv_bac08_mi_k` = 1(MIDRVACC A_k ≥ 8).

### 3.7 FARS DR_DRINK (vehicle) and DRUNK_DR (accident, 2016-2020)

**DR_DRINK.**
- Codes: 0 "No", 1 "Yes" **[label]**. There is **no unknown code**.
- **[derived-100%]**: DR_DRINK = 1 ⇔ driver DRINKING = 1 **or** driver ALC_RES ∈ [1, 940].
  - Agreement is 100.000 % in each year (498k drivers).
  - Adding 998 to the rule breaks agreement (99.84-99.94 %), so 998 is not counted.
- **Unknowns are coded as "No".** Of drivers with DR_DRINK = 0:
  - 176,449 have DRINKING = 0 and no measured BAC;
  - 102,807 have DRINKING 8 or 9 and no measured BAC.
- Share = 1: 18.2, 18.0, 17.2, 17.3, 18.1, 17.5, 17.5, 17.1, 16.5 % of vehicles (2016-24).

**DRUNK_DR.**
- Present 2016-2020; null for all crashes 2021-24.
- **[derived-100%]**: DRUNK_DR = the number of drivers in the crash with DR_DRINK = 1. All 172,255 crashes 2016-20 match (0: 126,710; 1: 44,173; 2: 1,354; 3: 16; 4: 2).

**Bias.** Because the rule mixes police report with test results and testing is far more common for killed drivers, DR_DRINK
**over-states** the killed-vs-survived contrast:
- killed-vs-surviving driver OR = 4.07 nationally, against 2.75 with MI BAC ≥ .08;
- in states that test most survivors, DR_DRINK (3.65) ≈ MI (3.67) (§5.4).

**Verdict:** a convenience flag only. Not suitable as an exposure for severity contrasts. DRUNK_DR cannot be used after 2020; recompute it from DR_DRINK.

### 3.8 Aux A_ALCTES (per_aux) and A_POSBAC (acc_aux)

Neither variable has labels. Meanings were reconstructed from cross-tabulations.

**A_ALCTES** (person), **[derived-100%]** for every record 2016-24:

| Code | Meaning | Source codes |
|---|---|---|
| 1 | tested, BAC < 0.01 | ALC_RES 0-9 (178,557 zeros + 344 values 0.001-0.009) |
| 2 | tested, BAC ≥ 0.01, including 998 | 10-940 or 998 |
| 3 | not tested | 996, including 2016 refusals |
| 4 | tested, result unknown | 997 |
| 5 | unknown / not reported | 995 or 999 |

- Code-5 share rises 5.8 % (2016) → 12.4 % (2023) → **19.0 % (2024)**.
- **Verdict:** a reliable recode of ALC_RES and nothing more. Use ALC_RES directly.

**A_POSBAC** (crash) [xtab, 99.97 %]:

| Code | Meaning | Agreement |
|---|---|---|
| 1 | at least one driver with BAC ≥ 0.01 (or 998) | 71,168 of 71,281 |
| 2 | all drivers tested with BAC < 0.01 | 62,070 of 62,070 |
| 3 | otherwise (some driver untested or unknown) | 191,942 of 191,942 (43 crashes meeting this condition are coded 1) |

- 113 of the 325,293 crashes with drivers deviate. **UNVERIFIED** why.
- Code 3 rises from 54.3 % (2016) to 64.7 % (2024).
- **Verdict:** shows that crash-level BAC status is unknown for most fatal crashes. Use MIDRVACC instead.

### 3.9 CRSS PERALCH_IM, VEH_ALCH, V_ALCH_IM, ALCOHOL, ALCHL_IM

**Codes [label 2019-24]:**

| Variable | Codes |
|---|---|
| PERALCH_IM | 0 No, 1 Yes |
| VEH_ALCH | 1 Alcohol Involved, 2 No Alcohol Involved, 8 No Driver Present, 9 Reported as Unknown |
| V_ALCH_IM | 1, 2 |
| ALCOHOL | 1, 2, 8 "No applicable person", 9 "Reported as Unknown" |
| ALCHL_IM | 1, 2 |

The code sets are identical in CRSS 2016-18.

**Derivations (all years, including 2016-18):**
- **VEH_ALCH** = 1 if the driver has DRINKING = 1 or a measured BAC > 0; 2 if DRINKING = 0; 9 otherwise.
  - Agreement is 99.985-99.999 % per year.
  - Code 8 is vehicles with no driver record (1,824 of 1,902).
  - VEH_ALCH is therefore a driver-level police measure.
- **ALCOHOL** = 1 if any vehicle has VEH_ALCH = 1 or any non-motorist has DRINKING = 1; 2 if all vehicles are 2 or 8 and all non-motorists have DRINKING = 0; 9 otherwise.
  Agreement is 99.94 % (468,993 crashes).
- **Imputed versions.**
  - PERALCH_IM keeps observed DRINKING 0 and 1 exactly and imputes codes 8 and 9.
  - Share of 8 imputed "Yes": drivers 2.9 %, occupants 0.3 %, non-motorists 1.8 %. Share of 9 imputed "Yes": drivers 5.2 %, occupants 1.4 %, non-motorists 6.8 %.
  - Driver PERALCH_IM ↔ V_ALCH_IM: 100 %.
  - ALCHL_IM = 1 ⇔ any V_ALCH_IM = 1 or any non-motorist PERALCH_IM = 1 (12 exceptions in 468,993).
  - Of ALCOHOL = 9 crashes, 4.9 % are imputed 1.

**Distribution (%, unweighted, records):**

| | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 |
|---|---|---|---|---|---|---|---|---|---|
| VEH_ALCH 9 | 9.7 | 9.4 | 8.3 | **27.7** | **35.2** | 34.4 | 34.5 | 34.1 | 34.1 |
| V_ALCH_IM 1 | 3.16 | 2.88 | 2.75 | 3.01 | 4.26 | 3.93 | 3.91 | 3.64 | 3.66 |
| ALCOHOL 1 | 5.07 | 4.92 | 4.61 | 4.50 | 5.53 | 5.10 | 5.08 | 4.85 | 4.74 |
| ALCOHOL 9 | 14.0 | 14.4 | 13.1 | **31.8** | **39.8** | 39.0 | 39.7 | 39.2 | 39.1 |
| ALCHL_IM 1 | 5.97 | 5.42 | 5.20 | 5.64 | 7.72 | 7.23 | 7.21 | 6.74 | 6.63 |
| PERALCH_IM 1 (persons) | 2.53 | 2.29 | 2.22 | 2.40 | 3.44 | 3.14 | 3.12 | 2.96 | 2.91 |

- The 2019/2020 breaks come entirely from DRINKING (§3.1).
- The imputed series are the most stable across the break (TVD 2018→19 ≤ 0.004).
- ALCHL_IM jumps 5.6 → 7.7 % in 2020. The jump is real or artefactual in unknown proportions: ALCOHOL = 1 also rose 4.5 → 5.5 %, and FARS shows a 2020 rise too.
- Pre-2019 "No" absorbed most non-reports, so pre-2019 imputations had less to impute. As a result **ALCHL_IM-based severity contrasts change at 2019** (§5.2).

**Severity:** see §5.2. ALCOHOL = 9 is 30-58 % in K crashes against 12-38 % in O crashes.

**Verdict:**
- ALCHL_IM, V_ALCH_IM and PERALCH_IM are the defensible CRSS measures (single imputation; under-states variance).
- Observed ALCOHOL and VEH_ALCH with "unknown as no" are biased (§5.4).

**Harmonised definitions:**
- `crash_alc_police` (CRSS ALCOHOL; FARS analogue in §8): 1 / 0 (from 2) / NA (8) / missing (9).
- `crash_alc_imputed` (CRSS ALCHL_IM: 1 → 1, 2 → 0).
- `veh_alc_police` (CRSS VEH_ALCH; FARS analogue from driver DRINKING and BAC).

---

## 4. Per-variable sections: drugs and impairment

### 4.1 DRUGS (person; police-reported drug involvement)

**Codes [label]:**

| Code | Label |
|---|---|
| 0 | No (drugs not involved) |
| 1 | Yes (drugs involved) |
| 8 | Not Reported |
| 9 | Unknown (2016-17) / Reported as Unknown (2018+) |

The code set is identical in CRSS 2016-18.

**Distribution (%, all persons):**

| | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 |
|---|---|---|---|---|---|---|---|---|---|
| FARS 1 | 5.06 | 5.37 | 5.62 | 5.93 | 7.40 | 7.06 | 6.67 | 6.11 | 5.78 |
| FARS 8 | 42.0 | 39.9 | 41.6 | 42.8 | 43.5 | **51.8** | 54.1 | 52.9 | 52.1 |
| CRSS 1 | 0.69 | 0.60 | 0.61 | 0.53 | 0.81 | 0.63 | 0.58 | 0.52 | 0.48 |
| CRSS 8 | 26.2 | 28.1 | 28.2 | **47.2** | **62.0** | 61.4 | 61.0 | 59.6 | 60.1 |

**Breaks:**
- CRSS driver DRUGS = 8 goes from 5.0 → 7.3 → 8.9 % (2016-18) to 33.7 % (2019) to 52-53 % (2020-24). TVD is 0.190 for 2018→19 and 0.150 for 2019→20.
- FARS shows a step at 2021: code 8 rises 43.5 → 51.8 % and "No" falls 39.3 → 32.1 %.

**Severity:**
- FARS drivers, pooled: killed 0 = 41.3 %, 1 = 11.7 %, 8 = 27.7 %, **9 = 19.3 %**; survived 57.5 / 5.1 / 31.9 / 5.5 %.
- CRSS drivers, weighted DRUGS ∈ {8, 9}, 2020-24: O 49-53 %, A 56-60 %, K 60-71 %.

**Validity against FARS tests** (tested drivers only, pooled):
- Sensitivity: among drivers positive for a drug class, DRUGS = 1 in **34.8 %** of killed and **53.9 %** of survived drivers. 43 % and 21 % respectively are 8 or 9.
- Specificity: among drug-negative drivers, DRUGS = 1 in 1.7 % and 2.6 %.

**Selection:** police "Yes" drives testing of survivors. P(drug-tested | DRUGS = 1) = 82.6 %, against 17.7 % for DRUGS = 0 (killed: 94.0 vs 58.2 %).

**Verdict:** **low**. Not usable as a prevalence measure. Not usable as an exposure in severity models (§5.5). Keep only as "police noted drug involvement".

**Harmonised definition:** `drug_police_yes` = 1 if DRUGS = 1; 0 if DRUGS = 0; missing if DRUGS ∈ {8, 9}. Use "1 vs not 1" across any CRSS break.

### 4.2 DRUG_DET (FARS person, 2016-2021)

**Codes [label]:**

| Code | Label |
|---|---|
| 1 | Evidential Test (Blood, Urine) |
| 2 | Drug Recognition Expert (DRE) (wording only) |
| 3 | **Behavioral** (2016-18) → **Observed Behavior or SFST** (2019-21) |
| 7 | Other |
| 8 | Not Reported |

- The code-3 relabel is a real change: code 3 counts jump 580 → 1,421 at 2019 while code 7 falls 2,741 → 1,713.
- Among drivers, DRUG_DET = 1 ↔ drug-tested for 40,346 of 40,655 [xtab].
- Code 8 covers 84-87 % of persons.
- **Verdict:** low value. Dropped after 2021. Do not harmonise.

### 4.3 FARS drug tests in person columns, 2016-2017 (DRUGTST1-3, DRUGRES1-3); CRSS 2016-2017

**DRUGTST codes [label]:**

| Code | Label |
|---|---|
| 0 | Test Not Given |
| 1 | Blood |
| 2 | Urine |
| 3 | Both: Blood and Urine Tests |
| 6 | Not Reported |
| 7 | Unknown Test Type |
| 8 | Other Test Type |
| 9 | Unknown if Tested |

**DRUGRES1-3** use the **3-digit scheme** of §4.4. Each person can carry at most **3 results**:
- 21.1 % (2016) and 22.0 % (2017) of persons with any specific drug have all 3 slots filled;
- in 2018-21, when the long table has no cap, 10-12 % of such persons have more than 3 distinct drugs.

Positivity counts for 2016-17 are therefore truncated.

**CRSS 2016-17** has DRUGTST1-3 and DRUGRES1-3 but **no specific drug codes**. Among CRSS persons with DRUGTST1 = 1 (blood), DRUGRES1 is:

| DRUGRES1 | Count |
|---|---|
| 1 | 88 |
| 95 | 26 |
| 997 "results unknown" | 1,066 |
| 998 | 144 |

There are no 100-995 codes. **CRSS contains no drug test results in any year.**

### 4.4 FARS `drugs` table, 2018-2024 (DRUGSPEC, DRUGRES, plus DRUGMETHOD, DRUGQTY, DRUGUOM, DRUGACTQTY in 2023-24)

**Structure.**
- One row per person × specimen × result. From 2023 the grain also includes testing method and quantity.
- **Every** person in `person` 2018-24 (628,374) has at least one row. Untested persons carry a DRUGSPEC 0 / DRUGRES 0 row.
- **Exact duplicate rows** (all columns identical):

  | Year | Rows | Exact duplicates |
  |---|---|---|
  | 2018 | 99,097 | 1,037 |
  | 2019 | 98,899 | 1,956 |
  | 2020 | 107,141 | 2,497 |
  | 2021 | 119,171 | 2,888 |
  | 2022 | 122,943 | 193 |
  | 2023 | 134,659 | 600 |
  | 2024 | 128,399 | 748 |

  Deduplicate on all columns before use.
- In 2023-24, rows that differ only in DRUGMETHOD, DRUGQTY or DRUGACTQTY share (key, DRUGSPEC, DRUGRES):
  127,114 unique of 134,059 deduplicated rows in 2023.
- After deduplication: 558,712 persons (88.9 %) have one row; the maximum is over 20.

**DRUGSPEC [label]:**

| Code | Label | Notes |
|---|---|---|
| 0 | Test Not Given | |
| 1 | Whole Blood | |
| 2 | Urine | |
| 11 | Blood Plasma / Serum | |
| 12 | Blood Clot | |
| 13 | Oral Fluids | from 2019 |
| 14 | Vitreous | 581 rows (2018) → 1,825 (2024) |
| 15 | Liver | |
| 96 | Not Reported | |
| 97 | Unknown Specimen | 262 rows (2018) → 1,575 (2024) |
| 98 | Other Specimen | |
| 99 | Reported as Unknown if Tested | **10,727 rows in 2024** against 497-3,194 before |

DRUGSPEC 96 rows sometimes carry real results (974 drug rows and 829 negatives). **Test status must come from DRUGRES, not DRUGSPEC.**

**DRUGRES uses two code schemes [label]:**

| Meaning | 2016-2021 scheme | 2022-2024 scheme |
|---|---|---|
| Test not given | 0 | 0 |
| Negative | 1 "Tested, No Drugs Found/Negative" | 1 (same label 2022; **"None Detected/Below Threshold" 2023-24**) |
| Not reported | 95 | **9995** |
| Other drug | 996 "Other Drug" | 9996 "Other Drug (Specify:)" |
| Tested, results unknown | 997 | 9997 |
| Positive, type unknown | 998 | 9998 |
| Unknown if tested | 999 | 9999 |
| Narcotics / opioids | 100-295 (anchor 295 "Narcotics, Type Unknown") | 1000-1997 (anchor 1997 "Narcotic Analgesics, Type Unknown [Opioids/Opiates]") |
| Depressants | 300-399 (anchor 395) | 2000-2997 (anchor 2997) — now includes antidepressants, antipsychotics, diphenhydramine, dextromethorphan, methanol |
| Stimulants | 400-495 (anchor 495) | 3000-3997 (anchor 3997) — **includes Caffeine 3026, Cotinine 3034, Nicotine 3066** |
| Hallucinogens | 500-595 (includes Ketamine 522, MDMA) | 4000-4997 |
| Cannabinoids | 600-695 | 5000-5997 — includes **inactive metabolite carboxy-THC 5062** (12,649 rows) |
| PCP / dissociatives | 700-795 "PCP" | 6000-6997 "Dissociative Anesthetic" (Ketamine 6001, PCP 6002, Propofol 6007) |
| Anabolic steroids | 800-899 (labels are testosterone derivatives; no anchor; **UNVERIFIED** class name) | 8000-8997 (only 8040, the same label as old 840) |
| Inhalants | 900-995 | 7000-7997 |
| Other non-psychoactive | (inside 996, **UNVERIFIED**) | 9000-9994: acetaminophen, ibuprofen, naloxone, lidocaine, carboxyhemoglobin, amlodipine, … |

Class names come from the "x95 / x997 … Type Unknown" anchor labels and the member drug labels **[label]**. No code falls outside these bands in any year.

**2023+ quantity fields [label]:**
- DRUGQTY: 0, 1 "None Detected/Below Threshold", 2 "Actual Drug Quantity", **3 "Presumptive Positive"**, 4 "Drugs Detected, Unknown Testing Method", 96, 97, 98 "…Unknown Quantity", 99.
- DRUGUOM: −9 N/A, 1 mg/dL, 2 mg/L, 3 mcg/mL, 4 gm%, 5 ng/mL, 6 mcg/L, 7 %, 8 Other.
- DRUGACTQTY: numeric, range −99 to 680,000, in mixed units.
- Of drug-class-positive killed drivers, **10.9 % (2023) and 8.7 % (2024) are positive only through presumptive (screen) results.** The figures for survivors are 15.4 % and 10.9 %.

**Drugs per positive person:**

| Years | Mean distinct drugs | Share > 3 | Note |
|---|---|---|---|
| 2016-17 | 1.75 | — | capped at 3 |
| 2018-21 | 2.0-2.1 | 10-12 % | |
| 2022-24 | 2.6-2.8 | 22-27 % | |

**Class positivity among drug-tested killed drivers (%, persons):**

| | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 |
|---|---|---|---|---|---|---|---|---|---|
| Any of 8 classes | 35.4 | 37.9 | 38.1 | 39.5 | 44.2 | 44.2 | 48.0 | 48.6 | 50.2 |
| Cannabinoid | 17.6 | 18.6 | 20.2 | 21.6 | 25.8 | 25.7 | 25.4 | 26.5 | 26.5 |
| … excluding carboxy-THC-only | | | | | | | 23.3 | 24.4 | 24.6 |
| Narcotic | 8.4 | 8.6 | 8.4 | 8.3 | 9.2 | 9.2 | 9.9 | 9.7 | 9.5 |
| Depressant | 8.5 | 7.7 | 7.5 | 6.9 | 6.7 | 6.3 | **13.0** | 13.3 | 14.8 |
| Stimulant (excl. caffeine, nicotine) | 11.6 | 13.7 | 14.6 | 15.3 | 18.3 | 18.2 | 17.6 | 17.1 | 17.6 |
| PCP / dissociative | 0.2 | 0.2 | 0.3 | 0.3 | 0.5 | 0.4 | **2.0** | 1.8 | 2.1 |
| Caffeine / nicotine / cotinine | – | – | – | – | – | – | 8.4 | 11.2 | 11.9 |
| "Other" 996 / 9996 | 8.6 | 10.3 | 15.1 | 17.0 | 17.6 | 18.0 | **2.7** | 3.8 | 4.3 |

The 2022 shift of mass from "Other" into named classes (depressant ×2, dissociative ×5) is a **coding artefact**. So are the 2017/2018 cap
removal and the 2023 presumptive positives.

**Verdict:**
- The `drugs` table gives valid *detection* data for tested persons, killed drivers especially.
- Detection is not impairment: inactive metabolites, nicotine and caffeine are included, presumptive screens are included from 2023, and there is no per-drug impairment threshold.
- Drug classes are comparable only within 2018-2021 and within 2022-2024, with 2023+ presumptive results flagged.
- Positivity is not comparable across states (§5.1).

### 4.5 DRIMPAIR / NMIMPAIR (code 9, alcohol and drugs combined)

- Code 9 = "Under the Influence of Alcohol, Drugs or Medication" **[label]**. It is a **single combined code**: alcohol and drugs cannot be separated.
- Both tables have multiple rows per driver or non-motorist.
- Code 9 share of rows:
  - FARS DRIMPAIR 9.8-11.8 %;
  - CRSS DRIMPAIR 2.4-3.2 %;
  - NMIMPAIR: FARS 7.5-10.2 %, CRSS 2.1-3.9 %.
- **Coding break:** "None/Apparently Normal" (0) moves into "Not Reported" (98):

  | Share of rows | 2016 | 2018 | 2019 | 2020 | 2024 |
  |---|---|---|---|---|---|
  | FARS DRIMPAIR 98 | 6.3 % | 18.0 % | | | 30.8 % |
  | CRSS DRIMPAIR 98 | 2.5 % | 6.4 % | 21.0 % | 37.4 % | 39.4 % |
  | CRSS NMIMPAIR 98 | | 23.1 % | 40.4 % | 64.6 % | |

- Among FARS drivers, any DRIMPAIR = 9 occurs for 66.4 % of DRINKING = 1 and 56.1 % of DRUGS = 1, against 2.9 % of DRINKING = 0.
- Code 9 is more common for killed drivers (12.8-15.2 % per year) than for survivors (7.7-9.4 %).
- **Verdict:** low. Usable only as a "police noted impairment by alcohol/drugs" flag, coded "any 9 vs not". Exposed to the same ascertainment problems as DRINKING. The 0/98 split cannot be used.

---

## 5. Key analyses

### 5.1 Selection into alcohol and drug testing, FARS drivers (killed vs survived)

**Alcohol: % of drivers with a measured BAC (ALC_RES 0-940):**

| | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 |
|---|---|---|---|---|---|---|---|---|---|
| Killed | 71.0 | 71.3 | 68.8 | 67.6 | 62.9 | 62.7 | 62.6 | 63.7 | 58.0 |
| Survived | 26.6 | 25.7 | 25.2 | 24.6 | 23.9 | 21.7 | 20.6 | 20.4 | 19.0 |
| Killed, 995 (not reported) | 3.1 | 3.7 | 4.8 | 4.6 | 11.2 | 8.8 | 9.6 | 9.4 | **25.8** |
| Survived, 995 | 6.7 | 8.2 | 10.6 | 10.1 | 10.1 | 10.7 | 11.6 | 14.8 | 16.9 |
| Killed, 999 (unknown if tested) | 1.7 | 1.6 | 0.8 | 1.4 | 0.7 | 4.6 | 5.5 | 4.5 | 0.5 |
| Killed, 996 (not tested) | 21.5 | 21.0 | 22.9 | 24.2 | 22.5 | 21.7 | 20.2 | 20.4 | 14.3 |
| Survived, 996 | 63.1 | 62.3 | 61.5 | 62.2 | 62.9 | 64.3 | 63.4 | 61.3 | 62.0 |
| n killed | 23,715 | 23,757 | 23,045 | 22,747 | 24,860 | 27,555 | 26,929 | 25,612 | 24,636 |
| n survived | 27,480 | 27,947 | 27,897 | 27,662 | 28,147 | 32,378 | 31,906 | 31,286 | 29,816 |

**Drugs: % drug-tested** (2016-17 from DRUGTST and DRUGRES; 2018+ from deduplicated `drugs`; "tested" = any informative DRUGRES):

| | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 |
|---|---|---|---|---|---|---|---|---|---|
| Killed | 63.7 | 65.6 | 64.6 | 63.7 | 60.5 | 59.7 | 60.5 | 61.7 | 55.1 |
| Survived | 20.8 | 20.4 | 20.0 | 20.1 | 19.8 | 17.7 | 17.1 | 17.1 | 14.7 |
| Killed, unknown if tested | 1.4 | 1.8 | 0.7 | 1.3 | 0.8 | 4.7 | 5.4 | 4.5 | **21.7** |

Pooled: drug-tested 61.6 % of killed and 18.5 % of survived drivers.

**Selection on suspicion.** Share with measured BAC by police DRINKING code:

| | DRINKING = 1 | DRINKING = 0 | DRINKING = 8 | DRINKING = 9 |
|---|---|---|---|---|
| Survivors | 71.5 % | 21.9 % | 5.4 % | 21.2 % |
| Killed | 86.9 % | 62.2 % | 47.8 % | 65.9 % |

- For survivors, testing follows police suspicion. For killed drivers it is close to routine.
- **The state-level signature of selection:** across the 51 jurisdictions, survivor test rate vs BAC ≥ .08 among tested survivors has Spearman ρ = **−0.86** (Pearson −0.73).
  - Low-testing tertile (mean 10.4 % tested): 35.7 % of tested survivors are ≥ .08.
  - High-testing tertile (52.3 % tested): 12.1 %.
  - For killed drivers ρ = −0.05: positivity is 33.9 / 32.2 / 32.3 % across tertiles with 52.5 / 76.0 / 86.0 % tested.

**States, pooled 2016-24** (FARS STATE codes, labels from STATENAME):
- **Survivor BAC measured %:**
  - Lowest: Virginia 0.9, Massachusetts 3.4, West Virginia 3.8, South Carolina 7.0, North Carolina 7.7.
  - Median 23.0.
  - Highest: South Dakota 84.7, Montana 78.5, Louisiana 65.3, Nebraska 62.7, Missouri 60.8.
- **Killed BAC measured %:**
  - Lowest: Mississippi 28.9, Michigan 42.7, Indiana 43.8, Kansas 46.0.
  - Median 76.4.
  - Highest: Massachusetts 92.1.
  - In Indiana (56.8 vs 43.8) and South Dakota (84.7 vs 80.5), survivors are tested *more* than killed drivers.
- **Killed drug-tested %:** North Carolina **8.9**, Mississippi 22.0, Maine 30.9, Nebraska 31.4; median 73.2; Massachusetts 93.1.
  - For killed drivers, state drug-test rate and positivity among tested have Spearman ρ = **+0.38** (2016-21). States that test more find more, which points to differences in test panels or labs.
- **State-years with killed BAC measured < 50 %:** 4 (2016), 3, 4, 7, 9 (2020). Survivor BAC measured < 50 % in 41-43 of 51 jurisdictions each year 2020-24.

### 5.2 CRSS police-reported alcohol by crash severity, and comparison with FARS

**Weighted % by MAX_SEV:**

| Year | ALCOHOL=1 O | C | B | A | K | ALCOHOL=9 O | K | ALCHL_IM=1 O | A | K | complete-case K |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2016 | 3.27 | 4.26 | 7.34 | 13.18 | 19.77 | 13.7 | 29.7 | 3.90 | 14.32 | 28.34 | 28.16 |
| 2017 | 3.22 | 3.44 | 7.76 | 12.44 | 20.15 | 13.6 | 30.5 | 3.56 | 13.01 | 27.46 | 29.30 |
| 2018 | 2.89 | 3.50 | 7.47 | 13.29 | 19.26 | 11.6 | 34.1 | 3.26 | 14.00 | 30.04 | 29.20 |
| 2019 | 2.70 | 3.58 | 7.01 | 14.54 | 16.75 | 30.7 | 46.9 | 3.54 | 15.83 | 28.53 | 31.56 |
| 2020 | 3.53 | 4.17 | 7.97 | 13.78 | 16.80 | 38.4 | 54.9 | 5.45 | 16.22 | 27.51 | 37.28 |
| 2021 | 3.29 | 3.81 | 7.22 | 13.87 | 15.81 | 36.9 | 56.6 | 5.07 | 16.30 | 25.35 | 36.42 |
| 2022 | 3.34 | 3.79 | 7.58 | 13.27 | 18.16 | 38.0 | 57.9 | 5.11 | 15.35 | 28.53 | 43.18 |
| 2023 | 3.13 | 3.37 | 7.50 | 12.56 | 16.43 | 37.0 | 55.3 | 4.64 | 14.43 | 26.62 | 36.79 |
| 2024 | 2.96 | 4.11 | 6.86 | 12.39 | 16.70 | 38.1 | 53.8 | 4.53 | 14.84 | 25.46 | 36.17 |

**CRSS drivers by own INJ_SEV (weighted):**

| Measure | O | C | B | A | K |
|---|---|---|---|---|---|
| DRINKING = 1 | 1.6-2.0 % | 2.1-2.7 % | 5.8-7.1 % | 10.1-12.4 % | 11.7-15.6 % |
| Alcohol test given | 1.0-2.3 % | | | 6.7-10.2 % | 26.4-35.0 % |
| Measured BAC | 0.5-1.7 % | | | | 5.2-12.7 % |

- Testing in CRSS is almost entirely suspicion-driven. Weighted test rate is 53.7 % for DRINKING = 1 against 0.7 % for DRINKING = 0 in B/C/O crashes; 60.4 % against 4.5 % in K/A.
- Tested CRSS drivers are 42-50 % BAC ≥ .08 at every severity level (O: 45.0 %, n = 5,922 pooled).

**Comparison with FARS** (all fatal crashes; % of crashes):

| | 2016 | 2018 | 2020 | 2022 | 2024 |
|---|---|---|---|---|---|
| FARS, CRSS ALCOHOL rule (any driver or non-motorist DRINKING = 1 or BAC > 0) | 32.3 | 31.3 | 31.7 | 31.0 | 29.0 |
| FARS, any driver DRINKING = 1 (police only) | 19.4 | 18.7 | 20.2 | 19.3 | 18.3 |
| FARS A_POSBAC = 1 (measured driver BAC ≥ .01) | 23.0 | 22.0 | 22.2 | 21.7 | 19.7 |
| FARS MIDRVACC ≥ .08 (MI mean) | 28.6 | 28.8 | 29.8 | 31.0 | 29.9 |
| FARS MIDRVACC ≥ .01 | 33.8 | 33.7 | 35.0 | 36.6 | 35.0 |
| CRSS K crashes, ALCOHOL = 1 | 19.8 | 19.3 | 16.8 | 18.2 | 16.7 |
| CRSS K crashes, ALCHL_IM = 1 | 28.3 | 30.0 | 27.5 | 28.5 | 25.5 |

- CRSS K-crash ALCOHOL = 1 (16-20 %) matches FARS police-only (18-20 %). It is **about 0.55 times** what FARS records with the identical CRSS
  rule once BAC tests are included (29-32 %). CRSS records a BAC for only 5-13 % of killed drivers.
- CRSS ALCHL_IM in K crashes (25-30 %) is close to FARS MI driver BAC ≥ .08 (28-31 %).
- CRSS has only 873-1,387 K crashes per year and was not designed for fatal-crash estimates.

### 5.3 Measured vs imputed BAC in FARS

| Measure | Killed drivers | Surviving drivers |
|---|---|---|
| Measured BAC (pooled) | 65.3 % (145,403) | 23.0 % (60,720) |
| Imputed: not tested (996) | 20.9 % | 62.6 % |
| Imputed: 995 | 9.1 % | 11.2 % |
| Imputed: 999 | 2.5 % | 1.1 % |
| Imputed: 997 | 1.9 % | 2.0 % |
| Imputed: 998 | 0.3 % | 0.2 % |
| BAC ≥ .08 among measured | 32.6 % | **19.7 %** |
| BAC ≥ .08, MI over all drivers | 28.8 % | 12.8 % |
| BAC ≥ .08, MI over imputed drivers only | 21.5 % | 10.7 % |
| Police DRINKING = 1 | 18.5 % | 8.5 % |
| DR_DRINK = 1 | 28.5 % | 8.9 % |

- Overall, **41.5 % of FARS drivers have a measured BAC and 58.5 % are imputed**. The measured share falls from 46.4 % (2016) to 35.9 % (2024).
- Among survivors, the measured-only ≥ .08 rate (19.7 %) is 1.5 times the MI rate (12.8 %), a direct consequence of selection.
- Among killed drivers the gap is small (32.6 vs 28.8 %). The not-tested killed drivers are imputed lower (18.6 %).

### 5.4 Which alcohol measure is defensible, and how ascertainment biases severity associations

**Validity of police DRINKING against measured BAC, FARS drivers** (pooled 2016-24; year-to-year range in brackets):

| | Killed | Survived |
|---|---|---|
| n with measured BAC | 145,403 | 60,720 |
| BAC ≥ .08 among measured | 32.6 % | 19.7 % |
| Sensitivity for BAC ≥ .08, 8 and 9 counted as not-yes | **63.0 %** (60.2-65.5) | **95.2 %** (93.9-96.8) |
| Sensitivity for BAC ≥ .08, among DRINKING ∈ {0, 1} | 87.1 % (85.5-89.0) | 98.2 % (97.6-98.9) |
| DRINKING ∈ {8, 9} among BAC ≥ .08 | 27.7 % | 3.0 % |
| DRINKING ∈ {8, 9} among BAC < .01 | 37.3 % | 11.6 % |
| Specificity (BAC < .01 → DRINKING = 0, knowns) | 96.2 % | 95.9 % |
| PPV of DRINKING = 1 for BAC ≥ .08 / ≥ .01 | 83.5 / 94.0 % | 71.1 / 89.8 % |

**Minimal-selection comparison.**
- The comparison uses 8 states where ≥ 50 % of *both* killed and surviving drivers have a measured BAC: Alaska, Arkansas, Louisiana, Missouri,
  Montana, Nebraska, New Hampshire and South Dakota. Measured shares there are 78.4 % (killed) and 63.0 % (survived).
- Results:

  | | Killed | Survived |
  |---|---|---|
  | n | 14,896 | 12,141 |
  | Prevalence BAC ≥ .08 | 31.3 % | 9.9 % |
  | Sensitivity, unknown counted as no | **65.6 %** | **92.5 %** |
  | Sensitivity, among known | 90.7 % | 97.3 % |
  | Specificity | 98.2 % | 98.5 % |

- In Montana and South Dakota (≥ 70 % tested in both groups), sensitivity is 90.4 % against 98.6 %.
- **Police report under-detects alcohol in killed drivers.** The difference comes mainly from "unknown" coding for drivers who died: 27.6 % of ≥ .08 killed drivers are coded 8 or 9, against 4.9 % of survivors.

**Killed-vs-survived odds ratios for alcohol in FARS** (the "true" contrast is best approximated by measured BAC in the 8 high-testing states):

| Measure | All states | 8 high-testing states | MT + SD |
|---|---|---|---|
| Measured BAC ≥ .08 (tested only) | 1.97 | **4.14** | 4.99 |
| Police DRINKING = 1, unknown as no (all drivers) | 2.44 | 2.33 | 2.96 |
| Police DRINKING = 1, complete case (all drivers) | 3.36 | 3.47 | 3.68 |
| DR_DRINK (police or BAC > 0) | **4.07** | 3.65 | 3.41 |
| MI BAC ≥ .08 (geometric mean of 10 implicate ORs) | 2.75 | 3.67 | 4.11 |

How to read the table:
1. Measured-only BAC is biased toward the null nationally (1.97), because survivors are tested on suspicion.
2. Police "unknown as no" is attenuated by about 40 % on the log scale: 2.33 against 4.14. ln 2.33 / ln 4.14 = 0.60.
3. Complete-case police is less biased (3.47).
4. DR_DRINK is biased away from the null where testing differs by severity (4.07 nationally against MI 2.75), because killed drivers get BAC-based detection and survivors mostly do not.
5. MI is closest to the reference in high-testing states (3.67 against 4.14) and is the only measure with full coverage.

**Recommendation (a): FARS fatal-crash characteristics.**
- Use the **MIPER / MIDRVACC implicates** (BAC ≥ .08 and ≥ .01) with Rubin's rules.
- Use measured ALC_RES only in a sensitivity analysis restricted to killed drivers or to high-testing states.
- Do not use DRINKING, DR_DRINK, DRUNK_DR or A_POSBAC as exposures across severity groups.
- Exclude or flag FARS 2024 toxicology (25.8 % of killed drivers "not reported").

**Recommendation (b): CRSS severity models.**
- Use **ALCHL_IM / V_ALCH_IM / PERALCH_IM** as the primary exposure.
- Run sensitivity analyses with (i) observed ALCOHOL complete-case and (ii) observed with unknown as no.
- **Never** use CRSS ALC_RES.
- Analyse 2016-18 and 2019+ separately, or add period × alcohol interactions, because of the DRINKING break.
- Estimated K-vs-O ORs, weighted crashes:

  | Coding | 2016-18 | 2020-24 |
  |---|---|---|
  | Unknown as no | 7.6 | **6.0** |
  | Complete case | 10.9 | **11.1** |
  | ALCHL_IM | 10.8 | **7.0** |

  For comparison, A vs O is 4.3-5.0 under every coding except the 2020-24 ALCHL_IM one (3.5).

**Direction and size of the CRSS bias.**
1. **Unknown-as-no attenuates the severity gradient at K.**
   - CRSS unknowns are concentrated in K: 24 % of killed drivers have DRINKING = 9, against 1-5 % for O-A.
   - In FARS, police report misses about 35 % of ≥ .08 killed drivers but about 8 % of survivors.
   - The CRSS K-crash rate (16.8 %, 2020-24) is 0.55 times the FARS rate under the same rule (≈ 30.7 %).
   - **Illustrative correction**, not an estimate:
     - Take the true K prevalence as ≈ 30.7 %.
     - Take the true O prevalence as the observed 3.24 % divided by the FARS-survivor sensitivity of 0.925, giving ≈ 3.5 %.
     - The implied K-vs-O OR is ≈ 12, against the observed 6.0, so the observed figure is attenuated about twofold.
   - This is an upper bound on the attenuation, because police sensitivity in minor non-fatal CRSS crashes is probably *below* that for survivors of FARS crashes (**UNVERIFIED**).
2. **Complete-case analysis tends to over-state K prevalence.**
   - FARS killed drivers with unknown DRINKING have lower BAC ≥ .08 (26.5 %) than those with known DRINKING (35.8 %).
   - So excluding unknowns raises K prevalence: CRSS K complete-case is 36-43 % in 2020-24, against FARS ≈ 31 %.
   - The true K-vs-O OR is therefore plausibly between the unknown-as-no and complete-case values (6-11, 2020-24). The direction is certain; the magnitude is not.
3. **A, B and C are only mildly affected.** DRINKING = 9 is 3.6-5.1 % at A against 1.6-2.7 % at O, and test rates are similar.
4. **ALCHL_IM contrasts change at 2019/2020.** Pre-2019 non-reports were mostly coded "No" and were not imputed. As a result the 2020-24 O-level
   imputed prevalence (4.5-5.5 %) is higher than 2016-18 (3.3-3.9 %), and the K-vs-O OR falls from 10.8 to 7.0.

### 5.5 Verdict on drug involvement

**Prevalence:** no. There is no defensible population or fatal-crash drug-impairment prevalence from these data.
- The only test data are FARS 2016-24. CRSS has none (§4.3).
- FARS testing covers 55-66 % of killed and 15-21 % of surviving drivers (§5.1).
- Killed-driver drug-test rates vary by state from 9 % to 93 %. Positivity rises with the state test rate (ρ = +0.38), which points to panel or lab differences.
- Positivity is detection, not impairment. It includes inactive metabolites (carboxy-THC), caffeine and nicotine (2022+), and presumptive screens (2023+).
- Drug classes break at 2017/18 (3-result cap) and 2021/22 (new code scheme), and 2024 is incomplete (21.7 % of killed drivers "unknown if tested").
- At most, report "% of drug-tested killed drivers with a detected drug of class X". Restrict to 2018-21 or 2022-24 with the class map in §8, adjust or stratify by state, and present it as a descriptive statistic for tested decedents, not as prevalence.

**Severity models:** no.
- CRSS has only police DRUGS:
  - not reported for 50-71 % of drivers in 2020-24;
  - coding breaks at 2019 and 2020;
  - sensitivity against FARS tests of only 35 % (killed) and 54 % (survivors);
  - testing of survivors driven by suspicion (82.6 % tested if DRUGS = 1, against 17.7 % if 0).
- Any CRSS severity association for drugs mixes exposure with ascertainment, and the bias cannot be corrected because CRSS has no drug imputation.
- In FARS, killed-vs-survived contrasts in drug positivity (any class among tested: killed 35-50 %, survived 27-35 %) are confounded by selective testing of survivors.
- Drug data may be used only as a descriptive covariate ("police noted drugs", DRIMPAIR 9) with explicit caveats, or in killed-driver-only FARS analyses.

---

## 6. CRSS 2016-2018 (unlabelled): can labels be applied?

| Variable | Code set 2016-18 ⊂ CRSS 2019-24 labelled set | ⊂ FARS same year | TVD vs 2019 | Structural check | Verdict |
|---|---|---|---|---|---|
| DRINKING | yes | yes | 0.14-0.15 | VEH_ALCH rule holds 99.99 % | **labels yes**; distribution no (coding break) |
| ALC_STATUS | yes, except code 1 in 2016 (261) = FARS 2016 "Test Refused" | yes | 0.010-0.031 | ↔ ALC_RES special codes 100 % | yes |
| ATST_TYP | yes (code 11 first in 2018, as in FARS) | yes | 0.011-0.032 | ↔ ALC_STATUS 100 % | yes |
| ALC_RES | numeric 0-940 + 995-999 | yes | – | ↔ ALC_STATUS 100 % | yes (units g/dL × 1000) |
| DRUGS | yes | yes | 0.19-0.21 | – | labels yes; distribution break |
| PERALCH_IM, V_ALCH_IM, ALCHL_IM | yes | n/a | ≤ 0.004 | IM ↔ observed rules 100 % | yes |
| VEH_ALCH, ALCOHOL | yes | n/a | 0.17-0.19 | derivation rules 99.9 % | labels yes; distribution break |
| DRIMPAIR, NMIMPAIR | yes | yes, except CRSS 2018 code 7 (not in FARS 2018) | 0.15-0.20 | – | labels yes; 0/98 break |
| DRUGTST1-3, DRUGRES1-3 (2016-17) | – | codes ⊂ FARS 2016-17 | – | no specific drug codes | labels yes; content empty |

Apply the CRSS 2019 labels (or same-year FARS labels) to CRSS 2016-18. The 2018→2019 distribution changes reflect the coding changes in §3.1
and §4.1 and §4.5, not different code meanings. Evidence: identical code sets, identical structural relationships, and the "Yes" shares are continuous.

---

## 7. Cross-cutting findings

1. **Severity-dependent ascertainment is the dominant problem.**
   - Killed drivers are tested routinely (BAC measured 58-71 %) but often have police alcohol coded unknown (DRINKING 9: 21.8 % FARS, ~24 % CRSS).
   - Survivors are rarely tested (19-27 %) and only when suspected.
   - Every measure that mixes police report and test result (DR_DRINK, DRUNK_DR, VEH_ALCH, ALCOHOL, A_POSBAC) inherits a severity-dependent sensitivity.
2. **"Not Reported" and "No" are not stable categories.**
   - CRSS 2019 and 2020 steps affect DRINKING, DRUGS, VEH_ALCH, ALCOHOL, DRIMPAIR and NMIMPAIR.
   - FARS shows a 2021 DRUGS step and a steady DRIMPAIR 0 → 98 drift.
   - "Yes" codes and imputed variables are continuous across these breaks.
3. **FARS 2024 toxicology is incomplete:**
   - ALC_STATUS "Not Reported" 18.6 % of persons (2023: 9.9 %);
   - A_ALCTES 5 = 19.0 %;
   - DRUGSPEC 99 = 10,727 rows;
   - killed drivers: alcohol 995 = 25.8 %, drug unknown-if-tested = 21.7 %.
4. **The FARS `drugs` table has exact duplicates** (193-2,888 per year) and **two code schemes** (3-digit 2016-21, 4-digit 2022-24). From 2023 it has a new grain (method and quantity rows) and presumptive positives.
5. **MI BAC is internally consistent:**
   - implicates are floor(ALC_RES / 10) for measured persons;
   - crash tables are exact maxima;
   - it is the only full-coverage FARS BAC.
   - It does not condition on 998 positivity, and its model covariates are undocumented.
6. **There is no separate alcohol vs drug impairment code** in DRIMPAIR or NMIMPAIR (code 9 is combined).

## 8. Recommended harmonised definitions (summary)

| Name | Level | Source | Recipe |
|---|---|---|---|
| `alc_police_yes` | person | both | DRINKING 1 → 1, 0 → 0, {8, 9} → NA; CRSS cross-period: 1 vs not 1 |
| `alc_test_status` | person | both | from ALC_RES: [0, 940] tested_result; 997 tested_result_unknown; 998 tested_pos_no_value; 996 not_tested (2016 ALC_STATUS 1 → not_tested); 995 not_reported; 999 unknown_if_tested |
| `bac_gdl`, `bac_ge08`, `bac_pos01` | person | FARS (CRSS: do not use) | ALC_RES / 1000 for 0-939, 940 → 0.94 top-coded; ≥ 80 → 1, 0-79 → 0; ≥ 10 or 998 → 1, 0-9 → 0; specials → NA |
| `bac_mi_k`, `bac08_mi_k` | person (drivers, non-motorists) | FARS miper | P_k / 100; 1(P_k ≥ 8); k = 1..10 |
| `crash_drv_bac08_mi_k` | crash | FARS midrvacc | 1(A_k ≥ 8) (crashes with no driver absent: set NA) |
| `crash_any_bac08_mi_k` | crash | FARS miacc | 1(A_k ≥ 8) |
| `alc_imputed` | person / vehicle / crash | CRSS | PERALCH_IM (0/1); V_ALCH_IM 1 → 1, 2 → 0; ALCHL_IM 1 → 1, 2 → 0 |
| `veh_alc_police` | vehicle | CRSS VEH_ALCH; FARS derived | CRSS: 1 → 1, 2 → 0, 8 → NA (no driver), 9 → NA. FARS: 1 if driver DRINKING = 1 or ALC_RES ∈ [1, 940]; 0 if DRINKING = 0; else NA |
| `crash_alc_police` | crash | CRSS ALCOHOL; FARS derived | CRSS: 1 → 1, 2 → 0, {8, 9} → NA. FARS: 1 if any driver or non-motorist (PER_TYP ∈ {1, 5, 6, 7, 8, 10, 11, 12, 13, 19}) has DRINKING = 1 or ALC_RES ∈ [1, 940]; 0 if all have DRINKING = 0; else NA |
| `alc_test_type` | person | both | §3.3 groups |
| `drug_police_yes` | person | both | DRUGS 1 → 1, 0 → 0, {8, 9} → NA |
| `drug_test_status` | person | FARS | 2016-17: any DRUGRES1-3 ∉ {0, 95, 999} → tested; all 0 → not_tested; 95 → not_reported; 999 → unknown. 2018+: deduplicated `drugs`; any DRUGRES ∉ {0, 95, 9995, 999, 9999} → tested; else 999/9999 → unknown_if_tested; else 95/9995 → not_reported; else not_tested |
| `drug_pos_<class>` | person | FARS | bands in §4.4; exclude 3026, 3034, 3066 and 9000-9994 and 996/9996 from "any class"; flag 2023+ DRUGQTY = 3-only positives; flag carboxy-THC-only (5062) |
| `impair_alc_drug_flag` | vehicle / person | both | any DRIMPAIR (or NMIMPAIR) = 9 → 1; NA if every row ∈ {98, 99} (or 95 for no driver); else 0 |

## 9. Open questions and UNVERIFIED items

- **UNVERIFIED:** why CRSS "Not Reported" for DRINKING, DRUGS and impairment jumps in January 2019 and January 2020. A processing change is inferred; no documentation is available.
- **UNVERIFIED:** whether test refusals are coded 0 (Test Not Given) or 8 after ALC_STATUS code 1 was removed in 2017.
- **UNVERIFIED:** why FARS ATST_TYP shifts to vitreous in 2020 in TX, VA, OH, CA, CT and OK at once.
- **UNVERIFIED:** whether FARS 2024 alcohol and drug "not reported" or "unknown" reflects pending toxicology (consistent with the monthly gradient and the large-state concentration).
- **UNVERIFIED:** the covariates of the FARS multiple-imputation model, including whether DRINKING is used (circularity), and why ALC_RES = 998 imputations include zeros.
- **UNVERIFIED:** the 113 crashes where A_POSBAC disagrees with the driver-BAC rule.
- **UNVERIFIED:** whether old-scheme 996 "Other Drug" contained the caffeine, nicotine and OTC substances that are coded explicitly from 2022. The 2022 drop in "Other" (18.0 → 2.7 % of tested killed drivers) is consistent with this.
- **UNVERIFIED:** the class name of DRUGRES bands 800-899 / 8000-8997 (labels are anabolic steroids; no anchor label).
- **UNVERIFIED:** why CRSS PSUs 29 and 14 record BAC = 0 with unknown test type for many drivers from 2020.
- **Open:** police sensitivity for alcohol in non-fatal (CRSS O-B) crashes cannot be estimated from these data. FARS survivors are the closest proxy and probably overstate it.
- **Open:** design-based (PSU / PSUSTRAT) standard errors for the CRSS figures were not computed. The ORs in §5.4 are point estimates.
