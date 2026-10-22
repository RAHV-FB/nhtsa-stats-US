# Audit appendix: CRSS sampling design, weights, imputation and FARS–CRSS comparability (2016–2024)

*Data audited: the typed Parquet cache `data/interim/CRSS/{accident,vehicle,person,acc_aux,veh_aux,per_aux,…}/{year}.parquet`
(all 30 CRSS tables for the cross-table consistency check), `data/interim/FARS/{accident,person}/{year}.parquet`, and the
inventory files in `outputs/audit/`. The analysis scripts are in
`scripts/audit/`. That directory is shared with
other audits, and the scripts for this appendix are the `svy_*` files: `svy_lib.py` (an independent with-replacement Taylor
variance estimator that does not use `src/`), `svy_01_structure.py`, `svy_01b_rest.py` (strata, PSUs and nesting), `svy_02_weights.py`
(weights), `svy_03_fars_compare.py` (FARS benchmark), `svy_04_deff.py`, `svy_04b_pooled.py` (design effects and pooled years),
`svy_05_consistency.py` (cross-table consistency), `svy_06_imputed.py` (`*_IM` variables), `svy_07_stratum_meaning.py` (STRATUM and
MAX_SEV verification), `svy_08_imputed_fatal_and_2020.py`, `svy_09_weight_cells.py`, `svy_10_codesets.py`, `svy_11_totals_se.py` and
`svy_12_psu_heterogeneity.py`.
Every number below was computed from these data. No external documentation was used, and the archives contain no manuals.
Evidence tags: **[label]** means the in-archive `<VAR>NAME` label column (CRSS 2019–2024 only); **[xtab]** means a
cross-tabulation or structural check computed here; **[general]** means general survey-statistics knowledge, used only to
form a hypothesis or to justify a method and never as evidence for what a code means; **UNVERIFIED** means the claim could not be checked in the data.*

---

## 1. Purpose and scope

Every design-based CRSS estimate in this project depends on the design fields: the weight, the variance strata, the variance
clusters and the crash-type sampling stratum. A wrong choice biases point estimates or makes standard errors wrong by large factors.
This appendix:

1. documents each design field (availability, codes and meanings with evidence, changes between years, missing values, reliability),
2. determines **which fields to use as variance strata and clusters** for Taylor linearisation, and why,
3. describes the weights (distribution, totals, calibration, changes within years) and measures the **design effects**,
4. checks that the design fields are **identical across all tables** for a case,
5. compares CRSS with the FARS census (fatal crashes and fatalities) and sets rules for **which source to use for which quantity**,
6. audits the CRSS **`*_IM` imputed variables** against their originals,
7. lists **design changes by year** that affect trend analysis, including 2016 and the 2020–2021 pandemic years.

Out of scope: what the substantive variables mean (covered by the other appendices in `docs/audit/`). Alcohol coding is covered
only to the extent that it affects imputation shares.

## 2. Tables and variables covered

| Field | CRSS tables | Years | Label column? | FARS equivalent |
|---|---|---|---|---|
| `CASENUM` (case key) | all 31 tables (`vpicdecode`/`vpictrailerdecode` have only CASENUM, no design fields) | 2016–2024 | no | `ST_CASE` (not linkable, see §7) |
| `PSUSTRAT` | accident, vehicle, person and 23 other event/factor tables | 2016–2024 | **no** | none |
| `PSU` | same | 2016–2024 | **no** | none |
| `PSU_VAR` | same | 2016–2024 | **no** | none |
| `PJ` | same | 2016–2024 | **no** | none |
| `STRATUM` | same | 2016–2024 | `STRATUMNAME` 2019–2024 | none |
| `REGION` | same | 2016–2024 | `REGIONNAME` 2019–2024 | derivable from `STATE` (§4.6) |
| `URBANICITY` | same | 2016–2024 | `URBANICITYNAME` 2019–2024 | none (FARS `RUR_URB` is a road attribute, §4.7) |
| `WEIGHT` | same **plus** `acc_aux`, `veh_aux`, `per_aux` | 2016–2024 | no | none (FARS is a census, implicit weight 1) |
| `MAX_SEV`, `MAXSEV_IM` | accident | 2016–2024 | 2019–2024 | none (FARS: all crashes fatal, `FATALS`) |
| `A_CRAINJ` | acc_aux | 2016–2024 | no | none |
| 27 `*_IM` variables | accident (12), vehicle (9), person (6) | see §8 | 2019–2024 | none (FARS uses multiple-imputation BAC files, out of scope) |

Tables that exist only from 2020 (crashrf, driverrf, personrf, pvehiclesf, vehiclesf, weather) carry the design fields in
2020–2024, and nmdistract carries them in 2019–2024 (`outputs/audit/variable_availability.csv`). The aux tables carry `WEIGHT` but not
`PSU`, `PSU_VAR`, `PSUSTRAT`, `STRATUM`, `PJ`, `REGION` or `URBANICITY`.

Sample sizes (sampled crashes per year): 46,511 / 54,969 / 48,443 / 54,409 / 54,745 / 54,200 / 53,955 / 50,103 / 51,658 (2016→2024).
No design field has a null value, and no `WEIGHT` is ≤ 0, in any table-year (`column_inventory.csv`, `svy_05`).

## 3. Key findings (summary)

1. **Variance strata = `PSUSTRAT`, clusters = `PSU_VAR`, weight = `WEIGHT`** (with-replacement, ultimate-cluster Taylor linearisation).
   `PSU_VAR` is nested in `PSUSTRAT` in every year and every PSU belongs to exactly one `PSUSTRAT`. `PSU_VAR` equals `PSU` everywhere except
   `PSUSTRAT` 20. That stratum contains a **single PSU (56)**, which `PSU_VAR` splits into 8 pseudo-PSUs, and each of these is
   exactly one `PJ` code. With `PSU_VAR` there is **no lonely PSU in any year**. With `PSU`, stratum 20 is lonely in every year.
2. **The design is not constant.** 2016 has 24 strata, 53 PSUs and 54 `PSU_VAR`s (30 design degrees of freedom), and some PSUs have
   only 4–8 months of crashes. 2017 has 66 `PSU_VAR`s (df 41), 2018–2021 and 2023–2024 have 67 (df 42), and 2022 has 66 (df 41,
   PSU 61 absent). The number of distinct PJs falls from 380–382 (2017–18) to 261–275 (2020–24).
3. **`STRATUM` is a crash-type stratum used within PSUs. It is not a variance stratum.** Labels and cross-tabulations agree on its meaning.
   Treating it as a variance stratum while ignoring clustering underestimates variances by a factor of up to about 70
   (injury share deff 0.23 instead of 16.0 in 2024). `STRATUM` is assigned from crash outcomes (injury severity), so it is outcome-derived.
4. **Weights are calibrated to FARS.** The weighted count of crashes with `MAXSEV_IM = 4` equals the FARS fatal-crash count **exactly** in
   2016 (34,748) and 2024 (36,297), and matches it within −0.91% to −0.30% in 2017–2023. **By REGION** it is exact for all four
   regions in 2024. In 2016 it is exact for regions 1 and 3 and for regions 2+4 combined. The calibration factor is visible
   inside cells: within a PJ × STRATUM × MONTH cell, fatal crashes carry a different weight from non-fatal crashes. Weighted `MAX_SEV = 4`
   (not imputed) is **0.6–12.8% below** FARS.
5. **Design effects are large and depend on the outcome.** For the fatal-crash share, deff is 1.1–2.2. For the KA share it is 3.4–11.5,
   for the alcohol share 4.4–14.7, for the non-motorist share 6.9–10.9, and for the **any-injury share 13–27**. For rural (a PSU-level
   variable) it is 105–175. For the person-level KA share it is 6.5–7.6.
6. **The same PSUs are sampled every year.** In pooled multi-year analyses, clusters must be `PSU_VAR` and must **not** be year-specific.
   Year-specific clusters understate the SE of a pooled 2019–24 proportion by a factor of 2.1–2.2. They overstate the SE of
   year-to-year differences by a factor of 1.6–3.6.
7. **Design fields agree across tables.** `WEIGHT`, `PSU`, `PSU_VAR`, `PSUSTRAT`, `STRATUM`, `PJ`, `REGION` and `URBANICITY` agree for
   every row of all 30 tables that carry them, 2016–2024, and no row lacks a matching accident case. The 157 cases with no person rows are exactly the
   157 crashes with `MAX_SEV = 8` ("No person involved").
8. **`*_IM` variables mostly fill only fully-unknown codes.** They keep every known value and keep "partially known" codes such as
   `INJ_SEV = 5`, `LGT_COND = 6` and `HARM_EV = 91/93`. The exceptions are the **crash- and vehicle-level aggregates** (`MAXSEV_IM`, `NO_INJ_IM`,
   `MXVSEV_IM`, `NUMINJ_IM`). These are recomputed from imputed person severities, so they change known originals in 0.5–2.2% of
   records. `MAX_SEV` and `MAXSEV_IM` are **exact deterministic functions** of person `INJ_SEV` and `INJSEV_IM` in every year
   (0 mismatches in 468,993 crashes).
9. **Missingness and imputation depend on severity.** Unknown crash severity (`MAX_SEV = 9`) occurs almost only in the no-injury
   sampling strata 7, 9 and 10 (1.0–7.1%), against ≤ 0.15% in the injury strata. The crash alcohol variable is unknown in 47.2% of fatal crashes
   against 29–31% of non-fatal crashes (pooled 2016–24). Imputed-fatal crashes (`MAXSEV_IM = 4`, `MAX_SEV ≠ 4`) carry high weights and
   make up 0.6%–12.2% of the weighted fatal total, depending on the year.
10. **2020 and 2021 have changes within the year.** In April 2020 the sample fell to 2,097 crashes (4,310 in April 2019) and weighted crashes fell 53%.
    From June 2020 the sampling rates were raised: the median weight fell from about 136 to about 94, and the median weight in stratum 9 fell from 166 to 96.
    In 2021 the rates were low from January to July (median stratum-9 weight 179–182) and high from August (93–100). Weighted national totals were 6.76 M (2019),
    5.25 M (2020) and 6.10 M (2021).

---

## 4. Per-variable sections

### 4.1 `CASENUM` (case key)

* **Availability:** every CRSS table in every year.
* **Structure [xtab]:** a 12-digit integer whose first 4 digits equal `YEAR` in all 468,993 accident rows (`CASENUM // 10^8 == YEAR`,
  0 exceptions). It is unique across all years (468,993 distinct values), so `CASENUM` alone is a global key. It is good practice to join on
  (`YEAR`, `CASENUM`).
* **Coverage [xtab]:** every vehicle-table case is in accident, and every accident case has ≥ 1 vehicle row. 157 accident cases
  (15/20/17/24/19/13/21/11/17 by year) have **no person rows**. These are exactly the 157 crashes with `MAX_SEV = 8` (**[label]** "No person
  involved"). `person` and `per_aux` therefore cover 468,836 cases.
* **Reliability: high.**

### 4.2 `PSUSTRAT`: first-stage (PSU) stratum, the variance stratum

* **Availability:** CRSS only, 2016–2024. **No label column in any year**, so the meaning comes from structure only.
* **Codes:** integers 1–25. 2016 has **24** codes (23 absent). 2017–2024 have all 25 (`svy_10`).
* **Structure [xtab] (`svy_01`, `svy_01b`):**
  * Each PSU belongs to exactly one `PSUSTRAT`, both within and across years (0 PSUs in > 1 stratum).
  * Each `PSUSTRAT` contains PSUs of **one REGION and one URBANICITY** (0 strata with > 1 value of either). Together with the
    REGION labels this gives the partition below. The stratification is therefore region × urban/rural, with finer splits that are
    **UNVERIFIED** (no label).

| REGION [label] | Urban PSUSTRATs (URBANICITY = 1) | Rural PSUSTRATs (URBANICITY = 2) |
|---|---|---|
| 1 Northeast | 1, 2, 3 | 4, 5 |
| 2 Midwest | 6, 7, 8 | 9 |
| 3 South | 10, 11, 12, 13, 14, 15 | 16, 17, 18, 19 |
| 4 West | 20, 21, 22, 23 | 24, 25 |

* **PSU_VARs per PSUSTRAT by year** (strata not listed have the same count in all years: str 2, 10, 14 and 21 have 3; str 3–8, 11, 12,
  16–19, 22, 24 and 25 have 2):

| PSUSTRAT | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 3 | 4 | 4 | 4 | 4 | 4 | **3** | 4 | 4 |
| 9 | **3** | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 |
| 13 | **2** | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 |
| 15 | **2** | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 |
| 20 | **2** | **7** | 8 | 8 | 8 | 8 | 8 | 8 | 8 |
| 23 | **absent** | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 |

* **Lonely strata:** with `PSU_VAR` as the cluster, the minimum is 2 PSU_VARs per stratum in every year, so there are **no lonely PSUs**. With `PSU` as the cluster,
  **PSUSTRAT 20 has a single PSU (56) in every year**.
* **Weighted crashes by PSUSTRAT** (thousands, selected strata): str 1: 151 (2016), 265, 348, 349, 204, 251, 223, 290, 282;
  str 21: **335 (2016)**, 190, 194, 190, 142, 158, 161, 179, 175; str 20: 179, 158, 165, 129, 108, 94, 94, 95, **71** (2024). Total variation
  distance of the weighted PSUSTRAT distribution against 2019: **0.117 (2016)**, 0.051, 0.026, –, 0.055, 0.048, 0.053, 0.050, 0.056.
* **Missing / unknown codes:** none (0 nulls; no sentinel codes).
* **Reliability: high** as a variance stratum. Its finer meaning (beyond region × urbanicity) is **UNVERIFIED**.
* **Harmonised:** `crss_var_stratum = PSUSTRAT` unchanged. The IDs are stable across years and can be used as they are in pooled analyses.

### 4.3 `PSU` (first-stage unit) and `PSU_VAR` (variance PSU)

* **Availability:** CRSS only, 2016–2024. No labels.
* **Codes:** `PSU` takes values 10–83 (60 distinct in 2017–21 and 2023–24, 59 in 2022, 53 in 2016). `PSU_VAR` takes values 10–83 plus 189, 205, 206, 208–211 and 214
  (67 distinct in 2018–21 and 2023–24, 66 in 2017 and 2022, 54 in 2016).
* **Nesting [xtab] (`svy_01b`):**
  * `PSU_VAR` is nested in `PSUSTRAT` in every year (0 `PSU_VAR`s in > 1 stratum) and keeps the **same stratum in every year**
    (`PSU_VAR` → `PSUSTRAT` is a fixed map across 2016–2024).
  * `PSU_VAR == PSU` for every row outside `PSUSTRAT` 20.
  * **`PSU` 56 is the only PSU in `PSUSTRAT` 20** (REGION 4 West, URBANICITY 1 urban). It is split into `PSU_VAR` 189, 205, 206, 208, 209, 210, 211 and 214,
    and **each of these PSU_VARs is exactly one PJ with the same code** (PJ 189 is PSU_VAR 189, and so on). The number of PSU 56 rows with `PSU ≠ PSU_VAR` is
    619 / 1,532 / 1,408 / 1,265 / 1,511 / 925 / 977 / 887 / 700 (2016→2024).
  * Interpretation **[general]**: a stratum containing a single PSU is a certainty (self-representing) PSU. Its police jurisdictions are then the first
    sampling units, and the data producer supplies them as pseudo-PSUs for variance estimation. The data support this: there is one PSU, the
    `PSU_VAR`s map one-to-one to PJs, and the stratum is large and urban. That PSU 56 is a certainty selection is otherwise **UNVERIFIED**.
* **Per-year design summary** (`svy_01`, `svy_04`):

| Year | Sampled crashes | PSUSTRAT | PSU | PSU_VAR | PJ | df = PSU_VAR − PSUSTRAT | Lonely strata (PSU) | Lonely strata (PSU_VAR) | Smallest PSU_VAR (cases) |
|---|---|---|---|---|---|---|---|---|---|
| 2016 | 46,511 | 24 | 53 | 54 | 327 | **30** | 1 (str 20) | 0 | 148 (205) |
| 2017 | 54,969 | 25 | 60 | 66 | 382 | **41** | 1 | 0 | 30 (209) |
| 2018 | 48,443 | 25 | 60 | 67 | 380 | 42 | 1 | 0 | 19 (209) |
| 2019 | 54,409 | 25 | 60 | 67 | 305 | 42 | 1 | 0 | 28 (209) |
| 2020 | 54,745 | 25 | 60 | 67 | 275 | 42 | 1 | 0 | 23 (209) |
| 2021 | 54,200 | 25 | 60 | 67 | 272 | 42 | 1 | 0 | 26 (209) |
| 2022 | 53,955 | 25 | 59 | 66 | 264 | **41** | 1 | 0 | 23 (209) |
| 2023 | 50,103 | 25 | 60 | 67 | 261 | 42 | 1 | 0 | 26 (209) |
| 2024 | 51,658 | 25 | 60 | 67 | 270 | 42 | 1 | 0 | 26 (209) |

* **PSU and PSU_VAR changes between years [xtab]:**
  * 2016: PSUs 14 (str 9), 53 (str 15), 61 (str 1), 64 and 68 (str 23, so the whole stratum is absent), 77 (str 9) and 83 (str 13) are absent, and stratum 20
    has only `PSU_VAR` 205 and 206. Several PSUs are partial: `PSU_VAR` 80 has crashes in only 4 months, 13 in 7, 72 in 8, and 20 and 31 in 11.
    Case counts differ sharply from later years (`PSU_VAR` 72: 296 against ≥ 1,021 later; 80: 218 against ≥ 944; 35: 2,469 against ≤ 1,342).
  * 2017: `PSU_VAR` 210 is absent, and 209 has only 10 months.
  * 2020: `PSU_VAR` 61 has 203 cases (631 in 2019), and `PSU_VAR`s 31, 50, 72, 80 and 209 have 11 months each.
  * 2021: `PSU_VAR` 206 falls to 171 cases (724 in 2020), and 61 has 11 months.
  * 2022: **PSU 61 is absent** (stratum 1 has 3 PSUs).
  * 2024: `PSU_VAR`s 205 and 209 have 11 months. The `PSU_VAR`s of PSU 56 shrink (214: 353 cases in 2017 against 57 in 2024; 189: 169 against 62).
* **Missing / unknown codes:** none.
* **Reliability: high.** Clusters are stable and correctly nested. Several clusters are very small (`PSU_VAR` 209 has 19–30 crashes a year),
  which makes domain estimates for West-urban subgroups unstable.
* **Harmonised:** `crss_var_cluster = PSU_VAR` unchanged. It is globally unique and stable, so it must **not** be combined with `YEAR` in pooled analyses (§6.4).

### 4.4 `PJ` (second-stage unit)

* **Availability:** CRSS only. No labels. Values range from 45 to 4,155. There are 433 distinct codes over 2016–2024, and 327 / 382 / 380 / 305 / 275 / 272 / 264 / 261 / 270 per year.
* **Structure [xtab]:** `PJ` is nested in `PSU` both within and across years (0 of 433 PJs in > 1 PSU). There are 1–9 PJs per `PSU_VAR` (median 5–6). In
  stratum 20, `PJ == PSU_VAR`. The codes are not a simple function of PSU (`PJ // 100 == PSU` for 0% of pairs).
* **Meaning:** the name and its nesting under PSU fit a *police jurisdiction* used as the second-stage sampling unit. **UNVERIFIED** (no label).
* **Changes:** the number of sampled PJs falls by 31% from 2018 (380) to 2023 (261). This is a design change that increases clustering
  within PSUs. It does not change the ultimate-cluster variance formula but reduces effective sample size.
* **Use:** diagnostics only. Do **not** use PJ as the variance cluster outside stratum 20 (§6.2).
* **Reliability: high** as an identifier. Meaning **UNVERIFIED**.

### 4.5 `STRATUM`: crash-type sampling stratum (within PSU)

* **Availability:** CRSS 2016–2024. `STRATUMNAME` exists 2019–2024, with identical label text in all 26 tables that carry it.
* **Codes and labels [label, 2019–2024], with verification [xtab] (`svy_07`; percentages of sampled crashes in the stratum, 2019–24 pooled, with 2016–18 in brackets):**

| Code | Label | Verification |
|---|---|---|
| 2 | Stratum 2 - Not a MV Occupant Any Injury | 98.1% (98.7%) have an injured non-occupant (`PER_TYP` ∈ {4,5,6,7,8,10} with `INJ_SEV` 1–5). Any injury 99.9% (99.6%) |
| 3 | Stratum 3 - Motorcycle Any Injury | 99.8% (99.3%) involve `BODY_TYP` 80–89 (motorcycles **[label]**). Any injury 100% (99.5%) |
| 4 | Stratum 4 - LMY PV Serious Injury | `MAX_SEV` ∈ {3 A, 4 K} 99.5% (97.9%). Passenger vehicle (`BODY_TYP` 1–49) 99.7%. Youngest PV ≤ 4 model years old 99.5% (98.0%) |
| 5 | Stratum 5 - NLMY PV Serious Injury | KA 99.7% (98.6%). Youngest PV ≤ 4 years 12.6% (15.2%), median youngest-PV age 10 |
| 6 | Stratum 6 - LMY PV Minor Injury | `MAX_SEV` ∈ {1 C, 2 B} 99.3% (98.0%). Youngest PV ≤ 4 years 99.6% (99.2%) |
| 7 | Stratum 7 - M/H Truck or Bus | 98.5% (97.2%) involve `BODY_TYP` 50–78 (buses and medium/heavy trucks **[label]**). Any injury 15.8% (15.4%) |
| 8 | Stratum 8 - NLMY PV Minor Injury | BC 99.3% (97.7%). Youngest PV ≤ 4 years 15.8% (18.5%) |
| 9 | Stratum 9 - LMY PV No Injuries in Crash | Any injury 0.2% (0.6%). Youngest PV ≤ 4 years 99.3% (98.9%) |
| 10 | Stratum 10 - Other | Any injury 0.4% (0.8%). Youngest PV ≤ 4 years 0.2% (0.7%), so these are mainly non-LMY no-injury crashes |

  * "LMY" (late model year) is consistent with **youngest passenger vehicle at most 4 model years older than the crash year**.
    The share of crashes meeting this is 97.2–99.7% in strata 4, 6 and 9 in every year and 0.1–0.9% in stratum 10. The distribution of
    youngest-PV age in stratum 4 is concentrated on ages 0 to 4 (2,051–2,785 crashes per age, plus 114 at age −1), with ≤ 22 crashes at any single age of 5 or more. The exact rule is **UNVERIFIED**.
    The 11–20% of stratum-5/8 crashes (by year) that contain a PV ≤ 4 years old show that the stratum is assigned from information available when
    the crash is sampled (the police report). It is not recomputed from final coded data. **[xtab]**
  * The precedence between strata (for example, a truck crash with an injured pedestrian) is **UNVERIFIED**. Stratum 2 contains 3.2% truck/bus crashes and
    stratum 4 contains 9.9%.
  * **Code 1 never occurs** (any year, any table). Its meaning is **UNVERIFIED**.
* **Level [xtab]:** all nine codes occur in every PSU in every year, so STRATUM cuts across PSUs. It is a within-PSU (crash-stage)
  stratification and not a first-stage one.
* **CRSS 2016–2018 (unlabelled):** the code set is identical (2–10). The unweighted distribution differs from 2019 by a total variation distance of
  0.044 / 0.043 / 0.016 (2016/17/18), within the 2020–24 range of 0.037–0.055. The composition checks above give the same pattern in 2016–18 as in
  2019–24. **The 2019+ labels can be applied to 2016–2018.**
* **Distribution [xtab]:** sampled shares are stable (stratum 9: 21.3–24.5%; stratum 10: 19.4–22.7%), except stratum 3 (motorcycle)
  at 7.0% in 2020 (4.8–5.9% in other years). Weighted shares (%):

| STRATUM | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 |
|---|---|---|---|---|---|---|---|---|---|
| 2 | 2.3 | 2.0 | 1.9 | 2.0 | 1.9 | 1.8 | 2.1 | 2.1 | 2.3 |
| 3 | 1.4 | 1.3 | 1.1 | 1.1 | 1.5 | 1.4 | 1.3 | 1.3 | 1.4 |
| 4 | 0.4 | 0.4 | 0.4 | 0.4 | 0.4 | 0.4 | 0.4 | 0.3 | 0.3 |
| 5 | 1.4 | 1.6 | 1.4 | 1.3 | 1.6 | 1.6 | 1.5 | 1.4 | 1.4 |
| 6 | 7.5 | 7.4 | 7.3 | 7.2 | 6.8 | 6.6 | 6.0 | 5.7 | 5.3 |
| 7 | 6.2 | 7.0 | 7.5 | 7.8 | 7.9 | 8.4 | 8.9 | 8.7 | 9.0 |
| 8 | 15.0 | 14.1 | 13.2 | 13.2 | 14.3 | 14.1 | 14.0 | 14.1 | 14.0 |
| 9 | 28.8 | 29.5 | 30.6 | 30.9 | 27.0 | 27.1 | 25.6 | 24.9 | 23.9 |
| 10 | 37.1 | 36.7 | 36.6 | 36.3 | 38.7 | 38.7 | 40.2 | 41.4 | 42.4 |

  The weighted drift (stratum 9 down from 30.9% to 23.9%, stratum 10 up from 36.3% to 42.4% over 2019→2024) is partly real (the vehicle fleet ages,
  so fewer crashes are LMY) and partly reflects how the strata are defined. Weighted TVD against 2019 is 0.089 in 2024. Trends in STRATUM shares are therefore **not** severity trends.
* **Missing / unknown codes:** none.
* **Reliability:** high as a design variable. **It must not be used as an analytic covariate in severity models**, because it is built from the
  outcome (injury severity) and from vehicle model year as known at sampling.
* **Harmonised:** `crss_crash_stratum` = STRATUM 2–10 with the labels above, for all years. Use it only for weighting diagnostics and
  for checking allocation.

### 4.6 `REGION`

* **Codes [label, 2019–24]:** 1 "Northeast (PA, NJ, NY, NH, VT, RI, MA, ME, CT)"; 2 "Midwest (OH, IN, IL, MI, WI, MN, ND, SD, NE, IA, MO, KS)";
  3 "South (MD, DE, DC, WV, VA, KY, TN, NC, SC, GA, FL, AL, MS, LA, AR, OK, TX)"; 4 "West (MT, ID, WA, OR, CA, NV, NM, AZ, UT, CO, WY, AK, HI)".
  The text is identical in all 26 tables and all labelled years.
* **2016–2018:** the code set is identical. REGION is constant within each PSU across **all** years (0 PSUs with > 1 REGION), so the
  labels transfer through the PSU. **The labels apply to 2016–2018.**
* **Level:** PSU attribute (constant within PSU and within PSUSTRAT).
* **Weighted crashes (thousands):** Northeast 656 / 740 / 887 / 909 / 643 / 761 / 762 / 780 / 832; Midwest 1,419 / 1,360 / 1,315 / 1,314 / 1,059 / 1,174 / 1,141 / 1,119 / 1,217;
  South 3,425 / 3,268 / 3,457 / 3,463 / 2,733 / 3,259 / 3,121 / 3,300 / 3,289; **West 1,321 / 1,084 / 1,076 / 1,070 / 816 / 908 / 906 / 939 / 843** (2016→2024).
  Northeast rises by 27% between 2016 and 2024 while West falls by 36%. With only 4–8 PSU_VARs per region-urbanicity cell, regional trends are sensitive to
  changes in PSU participation (for example PSU 56 in the West, §4.3). The cause is **UNVERIFIED**.
* **FARS mapping:** FARS `STATE` (labelled with state names in all years) can be mapped to REGION using the state abbreviations in the REGION labels.
  All 51 FARS STATE codes present are mapped (0 unmapped crashes). The abbreviation → name step uses general knowledge and is checked against the FARS label text.
* **Missing:** none. **Reliability: high.**
* **Harmonised:** `region4` = CRSS `REGION`. For FARS, `STATE` → region using the lists in the REGION labels (recipe in §12).

### 4.7 `URBANICITY`

* **Codes [label, 2019–24]:** 1 "Urban Area", 2 "Rural Area". The code set is the same in 2016–18, and the value is constant within PSU across all years, so **the labels transfer**.
* **Level [xtab]:** **PSU (area) attribute**, constant within every PSU and every PSUSTRAT (§4.2). It does **not** describe where the crash happened.
  FARS `RUR_URB` describes the roadway and is not comparable (see `crash_environment.md` §4.4).
* **Weighted rural share (%):** 25.1 / 23.4 / 23.1 / 23.7 / 27.3 / 25.4 / 25.7 / 26.0 / 26.1. The SE is about 2.0–2.4 points (deff 105–175, §6.3), because the
  variable is constant within clusters.
* **Missing:** none. **Reliability:** high as a design attribute, low as a crash-location covariate.
* **Harmonised:** `crss_psu_urbanicity` (1 urban, 2 rural). Never merge it with FARS `RUR_URB`.

### 4.8 `WEIGHT`

* **Availability:** CRSS all years, in every table that has design fields plus `acc_aux`, `veh_aux` and `per_aux`. Float. No label.
* **Meaning:** case (crash) sampling weight. Every vehicle and person row of a case carries the crash weight (0 mismatches, §5), so person-
  and vehicle-level totals are crash-weight-expanded counts of police-reported persons and vehicles. **[xtab]**
* **Distribution by year (`svy_02`):**

| Year | n | Σ WEIGHT (est. crashes) | min | p1 | p5 | median | mean | p95 | p99 | max | CV | Kish n_eff | 1+CV² (deff_w) | max/min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2016 | 46,511 | 6,821,129 | 3.86 | 12.84 | 23.36 | 142.96 | 146.66 | 316.27 | 540.79 | 994.51 | 0.742 | 29,992 | 1.55 | 257.6 |
| 2017 | 54,969 | 6,452,285 | 6.61 | 10.91 | 22.23 | 128.47 | 117.38 | 209.93 | 250.14 | 481.29 | 0.599 | 40,447 | 1.36 | 72.8 |
| 2018 | 48,443 | 6,734,416 | 12.09 | 13.78 | 27.34 | 160.19 | 139.02 | 241.37 | 270.09 | 586.07 | 0.562 | 36,800 | 1.32 | 48.5 |
| 2019 | 54,409 | 6,755,841 | 10.68 | 12.66 | 24.15 | 138.33 | 124.17 | 215.57 | 236.50 | 519.52 | 0.554 | 41,626 | 1.31 | 48.6 |
| 2020 | 54,745 | 5,250,837 | 8.23 | 10.75 | 14.92 | 95.30 | 95.91 | 215.52 | 239.51 | 483.95 | 0.692 | 37,002 | 1.48 | 58.8 |
| 2021 | 54,200 | 6,102,936 | 7.38 | 13.62 | 16.26 | 97.37 | 112.60 | 235.08 | 262.74 | 797.29 | 0.687 | 36,820 | 1.47 | 108.0 |
| 2022 | 53,955 | 5,930,496 | 8.77 | 10.52 | 21.52 | 121.50 | 109.92 | 206.37 | 245.46 | 520.82 | 0.599 | 39,695 | 1.36 | 59.4 |
| 2023 | 50,103 | 6,138,359 | 8.31 | 11.19 | 23.35 | 137.71 | 122.51 | 223.42 | 247.73 | 473.54 | 0.608 | 36,587 | 1.37 | 57.0 |
| 2024 | 51,658 | 6,180,241 | 8.65 | 11.17 | 24.45 | 129.72 | 119.64 | 225.21 | 249.16 | 575.22 | 0.626 | 37,116 | 1.39 | 66.5 |

  The 2016 maximum (994.5) belongs to the 2016 crashes of PJ 268 (PSU_VAR 49, PSUSTRAT 21, STRATUM 10).
* **By STRATUM (median weight):** strata 2–5 (injury, non-motorist, motorcycle, KA) have medians of 11–31. Strata 6 and 8 (BC) have 34–160.
  Strata 7, 9 and 10 (truck/bus and no-injury) have 96–240. The stratum-10 median weight is 15–20× the stratum-4 median (for example 223.9 against 11.3 in 2024),
  so serious-injury crashes are heavily **oversampled**. The unweighted fatal share is 2.1% (2024: 1,101 / 51,658) against a weighted share of 0.59%.
* **By MAX_SEV (median weight):** O 137–190, C 40–73, B 33–68, A 17–28, K 20–34, unknown (9) 172–235.
* **Estimated national crash totals with design SE** (thousands, `svy_11`; PSUSTRAT/PSU_VAR; RSE in brackets):

| Class | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 |
|---|---|---|---|---|---|---|---|---|---|
| All crashes | 6,821 ± 378 (5.5%) | 6,452 ± 355 | 6,734 ± 334 | 6,756 ± 341 | 5,251 ± 244 (4.6%) | 6,103 ± 297 | 5,930 ± 348 | 6,138 ± 341 | 6,180 ± 347 (5.6%) |
| O (MAXSEV_IM=0) | 4,667 | 4,526 | 4,804 | 4,802 | 3,618 | 4,333 | 4,223 | 4,401 | 4,464 |
| C (=1) | 1,211 | 1,084 | 1,094 | 1,105 | 863 | 925 | 899 | 879 | 852 |
| B (=2) | 688 | 604 | 604 | 621 | 562 | 640 | 600 | 652 | 659 |
| A (=3) | 183.1 | 172.9 | 170.6 | 168.2 | 154.7 | 153.0 | 156.9 | 154.5 | 156.8 |
| K (=4) | 34.7 ± 2.1 | 34.2 ± 2.6 | 33.7 ± 2.2 | 33.2 ± 2.2 | 35.8 ± 2.2 | 39.5 ± 2.7 | 39.2 ± 2.5 | 37.7 ± 2.5 | 36.3 ± 2.3 |
| Injured, sev. unknown (=5) | 34.8 (RSE 40%) | 27.0 | 24.9 | 21.8 | 14.4 | 9.7 (56%) | 8.5 | 11.5 | 9.4 |
| `MAX_SEV`=9 (all persons unknown) | 226.6 | 206.4 | 169.1 | 176.9 | 176.9 | 190.7 | 183.2 | 187.4 | 172.1 |

  The K row's SE ignores calibration (see below). The true sampling variance of the calibrated K total is close to 0.
* **Calibration to FARS [xtab] (`svy_03`, `svy_09`):** the weighted `MAXSEV_IM = 4` total matches the FARS fatal-crash count (§7.1) by year and
  by REGION. Within cells defined by PJ × STRATUM × MONTH, the weight of fatal (`MAXSEV_IM = 4`) crashes differs from that of non-fatal crashes by a
  factor that is near-constant within a region-year. For example, in 2018 Northeast the factor is 0.9435 in all 25 cells. Region-year medians run from 0.87 to 1.78. Adding
  "fatal (IM) yes/no" to the PJ × STRATUM × MONTH cell reduces the rows in cells with more than one distinct weight from 1,683–9,576 to 63–5,534.
  **Conclusion:** the weights include a final adjustment that benchmarks imputed-fatal crashes to FARS by region (in 2016, Midwest and West were combined).
  The exact procedure (for example raking or post-stratification, and any other control totals) is **UNVERIFIED**.
* **Changes within a year [xtab] (`svy_08`):** in 2016–2019 and 2022–2024 the monthly median weight is flat within a year (for example 2022: 120–124).
  * **2020:** median 149 in January, then 109 (May) and **94–95 from June to December**. The stratum-9 median falls from 163–166 to 95–96 in June, so the sampling
    fraction rose by about 70% at mid-year.
  * **2021:** median 132–167 from January to July, then **92–94 from August to December**. The stratum-9 median is 179–182 until July and 93–100 from August.
  * Therefore any monthly, seasonal or day-of-week analysis of 2020–2021 **must be weighted**. For example, in 2021 October has 2.1× as many sampled crashes
    as February (6,336 against 2,997), but only 1.35× as many weighted crashes (585.6k against 434.3k).
* **Missing / invalid:** none. All weights are > 0 and finite.
* **Reliability: high.** The weights are internally consistent and the FARS calibration is verified. Weight variability is moderate (deff_w 1.31–1.55).
  Weights above 500 occur in 2016, 2018, 2019, 2021, 2022 and 2024 and are rare: p99 is 236–541.
* **Harmonised:** `crss_weight = WEIGHT` (crash weight, applied to every row of a case). For pooled multi-year **annual-average** totals,
  divide by the number of years. Do not trim or rescale the weights, because that breaks the FARS calibration.

### 4.9 `MAX_SEV`, `MAXSEV_IM` (crash maximum injury severity) and `A_CRAINJ`

These are not design fields, but they define the severity domains used for the weight tables, the FARS comparison and every "by-severity"
missingness check, so their exact definition is recorded here.

* **Codes [label 2019–24, identical every year]:** 0 "No Apparent Injury (O)", 1 "Possible Injury (C)", 2 "Suspected Minor Injury (B)",
  3 "Suspected Serious Injury (A)", 4 "Fatal Injury (K)", 5 "Injured, Severity Unknown", 6 "Died Prior to Crash*", 8 "No person involved",
  9 "Unknown/Not Reported". `MAXSEV_IM` has the same codes without 9.
* **Derivation [xtab] (`svy_07`, `svy_10`; 0 mismatches in all 468,993 crashes, each year 2016–2024):**
  `MAX_SEV = 8` if the case has no person rows. Otherwise it is `9` if every person has `INJ_SEV = 9`. Otherwise it is the maximum `INJ_SEV` over persons
  with codes 0–4. If that maximum is 0 or undefined and some person has `INJ_SEV = 5`, the result is `5`. If it is undefined and no person has 5, the result is `6`.
  `MAXSEV_IM` follows the same rule applied to `INJSEV_IM`.
  * **Consequence:** `MAX_SEV` ignores persons with unknown severity when at least one other person is known, so **known `MAX_SEV` codes are lower bounds**.
    Pooled over 2016–24, 14,147 crashes with `MAX_SEV = 0`, 6,638 with 1, 4,599 with 2, 2,109 with 3 and 368 with 4 contain at least one `INJ_SEV = 9` person.
  * Because the derivation is deterministic and the code set is the same, **the 2019+ labels apply to 2016–2018** (and FARS `INJ_SEV` labels for the same codes are
    the same text in 2016–2024, apart from cosmetic spacing in FARS 2016, "Suspected Minor Injury(B)").
* **Unknown rates:** `MAX_SEV = 9` is 1.83 / 1.80 / 1.52 / 1.62 / 1.86 / 1.71 / 1.81 / 1.85 / 1.66% of sampled crashes, and **3.32 / 3.20 / 2.51 / 2.62 / 3.37 / 3.12 / 3.09 / 3.05 / 2.78%
  weighted** (2016→2024). `MAX_SEV = 5` falls steadily from 0.47% (2016) to 0.14% (2022–24) weighted, which is a coding drift.
* **Unknown severity depends on the sampling stratum [xtab]:** `MAX_SEV = 9` is 5.2–7.1% of stratum-10 crashes, 1.0–2.1% of stratum 9 and 1.4–1.9% of
  stratum 7, but ≤ 0.15% in the injury strata 2–6 and 8 in every year. When imputed, 66.6% of `MAX_SEV = 9` crashes become O.
* **Imputed-fatal crashes [xtab] (`svy_08`):** crashes with `MAXSEV_IM = 4` and `MAX_SEV ≠ 4` number 10 / 31 / 11 / 31 / 30 / 9 / 17 / 4 / 5 sampled crashes,
  carrying **1,574 / 3,927 / 2,120 / 4,044 / 3,889 / 1,680 / 2,368 / 386 / 219** weighted crashes (mean weight 44–193). That is 4.5%, 11.5%, 6.3%, 12.2%, 10.9%, 4.3%, 6.0%,
  1.0% and 0.6% of the weighted fatal total. Pooled, 53 of these 148 crashes are in stratum 10 (12,157 of 20,206 weighted, 60%), and 51 had `MAX_SEV = 9`.
  No crash with `MAX_SEV = 4` has `MAXSEV_IM ≠ 4`. **Trends in weighted `MAX_SEV = 4` are therefore distorted by year-to-year variation in imputation.** Use `MAXSEV_IM`.
* **`A_CRAINJ` (acc_aux, unlabelled) [xtab]:** a deterministic recode of `MAXSEV_IM`. Code 4 is `MAXSEV_IM = 4` (9,958 crashes). Code 2 is `MAXSEV_IM` ∈ {1,2,3,5}. Code 3 is
  `MAXSEV_IM` ∈ {0,6,8}. Code 1 never occurs. The pattern is the same in every year. The categories (fatal / non-fatal injury / no injury) are verified by cross-tabulation, but the label wording is **UNVERIFIED**.
* **Reliability:** `MAXSEV_IM` high, `MAX_SEV` medium (it is a lower bound and its unknowns are concentrated in high-weight strata).
* **Harmonised:** see recipes `crash_max_sev_im` and `crash_max_sev_obs` in §12.

---

## 5. Consistency of design fields across tables (`svy_05`)

All 30 CRSS tables with `CASENUM` were joined to `accident` on (`YEAR`, `CASENUM`), 2016–2024, and every design field present in each table was compared.

| Result | Value |
|---|---|
| Rows checked | 17,422,170 rows in 30 tables. 16,646,694 of them are in the 28 tables that carry design fields; the 2 vPIC tables were checked for orphan keys only. Examples: person 1,158,730; vevent and vsoe 1,160,806; damage 1,676,876; per_aux 1,158,730; veh_aux 825,957 |
| Rows whose CASENUM is absent from accident | **0** in every table-year |
| `WEIGHT` mismatches (abs. diff > 1e-6) | **0** (person `WEIGHT` is bit-identical to accident `WEIGHT`: max abs diff 0.0) |
| `PSU`, `PSU_VAR`, `PSUSTRAT`, `STRATUM`, `PJ`, `REGION`, `URBANICITY` mismatches | **0** in every table that carries them |
| `WEIGHT` nulls | 0 |

**Verdict:** for any table, the design fields can be taken from that table or from `accident`. Aux tables need `accident` for strata and
clusters.

---

## 6. Variance estimation: choice of strata and clusters, and design effects

### 6.1 Recommended specification

* **Estimator:** with-replacement Taylor linearisation using ultimate clusters **[general]**:
  `V(t̂) = Σ_h n_h/(n_h−1) Σ_i (z_hi − z̄_h)²`, where `z_hi` is the weighted total of the linearised variable in variance PSU `i` of stratum `h`.
  For ratios and proportions, linearise `u_k = w_k (y_k − R x_k)/X̂`.
* **Strata:** `PSUSTRAT`. **Clusters:** `PSU_VAR`. **Weight:** `WEIGHT`.
* **Degrees of freedom:** number of `PSU_VAR`s minus number of `PSUSTRAT`s in the data being analysed: 30 (2016), 41 (2017, 2022), 42 (other years).
  For a pooled set of years (2017+ or 2016+) it is 67 − 25 = 42, because the cluster IDs are shared across years. Use t-quantiles with these df.
* **Domains:** compute variances over the **full design** with the outcome set to 0 outside the domain. Do not drop rows, because that drops PSUs
  with no domain members and understates the variance. `svy_lib.svy_ratio` does this by keeping every (stratum, cluster) pair.
* **Lonely PSUs:** none under this specification in any year, so no adjustment is needed.

### 6.2 Evidence for this choice

1. `PSUSTRAT` partitions the PSUs, not the crashes within PSUs. Every PSU belongs to exactly one stratum, and strata are homogeneous in REGION ×
   URBANICITY (§4.2). This is how a first-stage stratification looks **[xtab + general]**.
2. `PSU_VAR` is nested in `PSUSTRAT`, equals `PSU` outside stratum 20, and in stratum 20 splits the single PSU 56 into its PJs (§4.3).
   Using `PSU` makes stratum 20 a lonely PSU. Its variance contribution then becomes 0 (certainty treatment) and the sampling of PJs inside the
   certainty PSU is ignored. Effect: the 2016 non-motorist-share deff falls from 9.03 (PSU_VAR) to 4.99 (PSU) and the 2016 injury-share deff
   from 25.7 to 20.0. In 2017–2024, using `PSU` understates the variance by 0–17%: the largest gap is in the non-motorist share
   (2018: 5.67 against 6.85; 2020: 9.06 against 10.86), and for the injury share it is 0–8%.
3. `STRATUM` is **not** a first-stage stratum. **[xtab]** All nine crash-type strata occur inside every PSU in every year
   (53–60 PSUs, 100%), and inside 95.5–100% of `PSU_VAR`s. The exceptions are small PJ-level `PSU_VAR`s of PSU 56, with at least 6 strata each. The label wording describes crash types.
   It stratifies the final (crash) stage. Under the ultimate-cluster approximation its effect is already captured in the cluster totals
   **[general]**. Using `STRATUM` as the variance stratum with crashes as independent units (specification E) gives, for the fatal, KA, injury and
   non-motorist shares in 2024, deff 0.23–0.47 where specification A gives 1.7–16.0, so standard errors would be **2–8× too small**.
4. `PJ` (specification D) is a second-stage unit. Ultimate-cluster variance uses first-stage units **[general]**. Using PJs gives variances that are
   not consistent with the correct ones: some are lower (injury 9.9 against 16.0 in 2024) and some higher (rural 434 against 136).
5. Ignoring strata (specification C, clusters only) overstates variances: injury deff 20.1 against 16.0, rural 978 against 136 (2024).

### 6.3 Design effects (deff = V_design / V_SRS with V_SRS = p(1−p)/n using the weighted p; `svy_04`)

**Specification A (PSUSTRAT/PSU_VAR), crash level, by year.** The weighted p (%) is shown with its design SE (percentage points) and deff.

| Proportion | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 |
|---|---|---|---|---|---|---|---|---|---|
| Fatal: `MAXSEV_IM`=4 / all | 0.509 (0.035) **1.12** | 0.531 (0.044) **2.01** | 0.500 (0.037) **1.32** | 0.492 (0.035) **1.34** | 0.681 (0.047) **1.77** | 0.647 (0.047) **1.85** | 0.661 (0.051) **2.18** | 0.613 (0.045) **1.70** | 0.587 (0.044) **1.73** |
| Fatal (observed): `MAX_SEV`=4 / `MAX_SEV` 0–5 | 0.503 **1.19** | 0.486 **1.61** | 0.481 **1.25** | 0.444 **1.18** | 0.629 **1.56** | 0.640 **1.98** | 0.642 **1.86** | 0.626 **1.87** | 0.601 **1.86** |
| KA: `MAXSEV_IM` ∈ {3,4} | 3.19 (0.19) **5.67** | 3.21 (0.26) **11.47** | 3.03 (0.14) **3.38** | 2.98 (0.17) **5.35** | 3.63 (0.18) **5.11** | 3.15 (0.16) **4.44** | 3.31 (0.18) **5.62** | 3.13 (0.16) **4.02** | 3.13 (0.17) **4.80** |
| Any injury: `MAXSEV_IM` 1–5 / all | 31.5 (1.09) **25.7** | 29.8 (0.81) **17.4** | 28.6 (0.75) **13.4** | 28.9 (0.84) **18.9** | 31.0 (0.96) **23.7** | 29.0 (0.90) **21.2** | 28.7 (1.01) **26.8** | 28.3 (0.88) **18.9** | 27.7 (0.79) **16.0** |
| Any injury (observed): `MAX_SEV` 1–5 / 0–5 | 30.3 **23.9** | 29.1 **18.9** | 27.5 **14.2** | 27.1 **15.4** | 29.0 **18.3** | 28.3 **21.5** | 27.9 **26.5** | 27.3 **17.7** | 27.1 **17.6** |
| Alcohol involved: `ALCHL_IM`=1 | 4.84 (0.30) **9.10** | 4.34 (0.24) **7.54** | 4.14 (0.19) **4.37** | 4.49 (0.26) **8.66** | 6.41 (0.39) **13.6** | 5.96 (0.39) **14.7** | 6.06 (0.35) **11.5** | 5.52 (0.32) **10.1** | 5.50 (0.33) **10.9** |
| Non-motorist involved: `PERNOTMVIT`>0 | 3.10 (0.24) **9.03** | 2.78 (0.22) **10.1** | 2.77 (0.20) **6.85** | 2.83 (0.22) **9.49** | 2.73 (0.23) **10.9** | 2.60 (0.21) **9.04** | 3.04 (0.20) **7.14** | 3.05 (0.23) **9.02** | 3.15 (0.24) **9.95** |
| Rural PSU: `URBANICITY`=2 | 25.1 (2.06) **105** | 23.4 (2.39) **175** | 23.1 (2.06) **116** | 23.7 (1.97) **117** | 27.3 (2.02) **113** | 25.4 (1.94) **107** | 25.7 (2.37) **158** | 26.0 (2.25) **132** | 26.1 (2.25) **136** |

Person level (`INJSEV_IM` ∈ {3,4} among all persons, `svy_04b`): p = 1.44% / 1.63% / 1.55%, deff = **6.97 / 7.62 / 6.52** (2019 / 2022 / 2024). The deff
that accounts for weights and clustering by crash only is 0.61–0.67, so almost all of the design effect comes from the PSUs.

**Alternative specifications, 2024** (deff; A is the recommended specification):

| Proportion | A PSUSTRAT/PSU_VAR | B PSUSTRAT/PSU | C no strata/PSU_VAR | D PSUSTRAT/PJ | E STRATUM/crash | F weights only |
|---|---|---|---|---|---|---|
| Fatal (IM) | 1.73 | 1.67 | 2.12 | 1.46 | 0.47 | 0.50 |
| KA (IM) | 4.80 | 4.59 | 5.60 | 3.73 | 0.33 | 0.50 |
| Any injury (IM) | 15.98 | 15.86 | 20.12 | 9.92 | 0.23 | 1.08 |
| Alcohol (IM) | 10.91 | 10.77 | 19.28 | 10.80 | 1.34 | 1.35 |
| Non-motorist | 9.95 | 9.63 | 17.72 | 5.89 | 0.47 | 0.66 |
| Rural PSU | 135.5 | 135.5 | 978.2 | 434.0 | 1.40 | 1.41 |

The same alternatives in 2016: non-motorist A 9.03, B **4.99**, C 22.5, D 7.75, E 0.60, F 0.82; injury A 25.7, B **20.0**, C 35.9, D 14.2.

**Why the injury-share deff is so large [xtab] (`svy_12`):** the PSU-level weighted injury share ranges from 14.0% to 69.6% in 2019 (interquartile range
24.6–37.3%) and from 15.2% to 64.6% in 2024. PSUs differ enormously in the share of their police-reported crashes that involve injury. A plausible explanation is local
thresholds for reporting property-damage-only crashes, which is **UNVERIFIED**. The effective sample size for an injury share is therefore about
51,658 / 16 ≈ 3,200 crashes, not 51,658. The fatal share is less heterogeneous (PSU range 0–3.3%) and is oversampled, so its deff is about 1.1–2.2.
Fatal shares are, however, partly fixed by calibration (§7.1).

**Calibration caveat [general + xtab]:** the formulas above ignore the FARS benchmarking of fatal crashes. For the weighted fatal *total*, the true
variance is about 0 at the calibration level (region-year). Taylor SEs (2.1–2.7 thousand) are therefore conservative. For ratios that contain the
fatal total (fatal share = FARS-fixed numerator / estimated total) most of the true variance comes from the denominator.

### 6.4 Pooled years: stable clusters (`svy_04b`)

The same `PSU_VAR`s (and therefore the same PSUs and PJs) are sampled every year, so estimates from different years are positively correlated.

| Quantity | Estimate | SE, clusters = `PSU_VAR` shared across years | SE, clusters = `YEAR`×`PSU_VAR` (wrong) | Ratio |
|---|---|---|---|---|
| Fatal share, pooled 2019–24 | 0.610% | 0.0388 | 0.0183 | **2.12** |
| Injury share, pooled 2019–24 | 28.87% | 0.819 | 0.366 | **2.24** |
| Alcohol share, pooled 2019–24 | 5.62% | 0.307 | 0.140 | **2.20** |
| Fatal share, 2020 − 2019 | +0.189 pp | 0.0355 | 0.0583 | 0.61 |
| Injury share, 2020 − 2019 | +2.17 pp | 0.609 | 1.280 | 0.48 |
| Injury share, 2021 − 2020 | −2.07 pp | 0.361 | 1.316 | **0.27** |
| Alcohol share, 2020 − 2019 | +1.92 pp | 0.280 | 0.466 | 0.60 |

**Rule:** for pooled analyses and for tests of differences between years, use `PSUSTRAT` / `PSU_VAR` without a year suffix.
Treating years as independent understates pooled SEs by about half and makes trend tests far too conservative.

---

## 7. FARS against CRSS

### 7.1 Fatal crashes and fatalities (`svy_03`)

FARS: `accident` rows per year (= fatal crashes), `FATALS` summed, and the number of `person` rows with `INJ_SEV = 4` **[label "Fatal Injury (K)"]**.
`Σ FATALS` equals the number of `INJ_SEV = 4` persons in every year, and no FARS crash has `FATALS = 0`.

| Year | FARS fatal crashes | CRSS sampled `MAX_SEV`=4 crashes | CRSS weighted `MAX_SEV`=4 (SE) | Diff. | z | CRSS weighted **`MAXSEV_IM`=4** | Diff. |
|---|---|---|---|---|---|---|---|
| 2016 | 34,748 | 903 | 33,174 (2,129) | −4.5% | −0.74 | **34,748** | **0.00%** |
| 2017 | 34,560 | 1,004 | 30,320 (2,151) | −12.3% | −1.97 | 34,247 | −0.91% |
| 2018 | 33,919 | 873 | 31,534 (2,046) | −7.0% | −1.17 | 33,654 | −0.78% |
| 2019 | 33,487 | 948 | 29,200 (1,870) | −12.8% | −2.29 | 33,244 | −0.73% |
| 2020 | 35,935 | 1,387 | 31,877 (1,950) | −11.3% | −2.08 | 35,766 | −0.47% |
| 2021 | 39,785 | 1,185 | 37,828 (2,544) | −4.9% | −0.77 | 39,508 | −0.70% |
| 2022 | 39,422 | 1,284 | 36,853 (2,223) | −6.5% | −1.16 | 39,221 | −0.51% |
| 2023 | 37,769 | 1,130 | 37,268 (2,581) | −1.3% | −0.19 | 37,654 | −0.30% |
| 2024 | 36,297 | 1,096 | 36,078 (2,292) | −0.6% | −0.10 | **36,297** | **0.00%** |

| Year | FARS fatalities | CRSS weighted `INJ_SEV`=4 persons (SE) | Diff. | CRSS weighted `INJSEV_IM`=4 (SE) | Diff. |
|---|---|---|---|---|---|
| 2016 | 37,806 | 35,803 (2,192) | −5.3% | 37,377 (2,212) | −1.1% |
| 2017 | 37,473 | 33,453 (2,565) | −10.7% | 37,415 (2,925) | −0.2% |
| 2018 | 36,835 | 34,172 (2,220) | −7.2% | 36,291 (2,343) | −1.5% |
| 2019 | 36,355 | 31,386 (2,009) | −13.7% | 35,430 (2,339) | −2.5% |
| 2020 | 39,007 | 34,577 (2,240) | −11.4% | 38,466 (2,431) | −1.4% |
| 2021 | 43,230 | 41,675 (2,783) | −3.6% | 43,356 (2,916) | +0.3% |
| 2022 | 42,721 | 39,514 (2,500) | −7.5% | 42,044 (2,812) | −1.6% |
| 2023 | 41,025 | 40,772 (2,863) | −0.6% | 41,158 (2,802) | +0.3% |
| 2024 | 39,254 | 38,459 (2,452) | −2.0% | 38,678 (2,494) | −1.5% |

**By REGION** (FARS `STATE` mapped through the REGION labels; CRSS weighted `MAXSEV_IM = 4`):

| Year | Northeast FARS / CRSS | Midwest | South | West |
|---|---|---|---|---|
| 2016 | 3,672 / 3,672 | 6,718 / 5,845 (−13.0%) | 16,838 / 16,838 | 7,520 / 8,393 (+11.6%); **Midwest+West: 14,238 / 14,238** |
| 2017 | 3,610 / 3,603 | 6,768 / 6,768 | 16,610 / 16,572 | 7,572 / 7,304 (−3.5%) |
| 2019 | 3,279 / 3,275 | 6,376 / 6,373 | 16,454 / 16,352 | 7,378 / 7,244 (−1.8%) |
| 2021 | 3,965 / 3,972 | 7,459 / 7,459 | 19,480 / 19,437 | 8,881 / 8,640 (−2.7%) |
| 2023 | 3,729 / 3,732 | 7,078 / 7,071 | 18,279 / 18,289 | 8,683 / 8,562 (−1.4%) |
| 2024 | 3,756 / 3,756 | 6,879 / 6,879 | 17,473 / 17,473 | 8,189 / 8,189 |

The largest absolute regional gap per year (MAXSEV_IM) is 13.0% in 2016 (because two regions were collapsed), then 3.5%, 2.9%, 1.8%, 1.8%, 2.7%, 1.5% and 1.4% in 2017–2023, and 0.0% in 2024.
Interpretation: CRSS weights are benchmarked so that weighted imputed-fatal crashes equal FARS counts by region. The small negative residuals in
2017–2023, which are largest in the West, are consistent with benchmarking to an **earlier release of FARS** than the files here. That explanation is
**UNVERIFIED**. The FARS file versions cannot be determined from the data.

### 7.2 Implications

1. **Never pool FARS and CRSS records.** CRSS contains 873–1,387 sampled fatal crashes a year that are also in FARS (a census), and there is no
   linking key: CRSS has no `STATE`, `ST_CASE`, `COUNTY` or `DAY`, and FARS has no `CASENUM`, `PSU` or `WEIGHT`. Pooling would double-count fatal crashes,
   mix a census (weight 1, no sampling variance) with a sample, and mix code definitions that are similarly named but differ in level
   (for example `URBANICITY` against `RUR_URB`).
2. **Fatality and fatal-crash counts, and anything that describes fatal crashes in detail, come from FARS.** The CRSS fatal total is not an independent
   estimate, because it is calibrated to FARS. CRSS fatal subgroups rest on only about 900–1,400 sampled crashes (RSE 6.1–7.5% even for the national total). CRSS
   `MAX_SEV = 4` without imputation is biased low by up to 12.8%.
3. **Severity distributions and rates per police-reported crash come from CRSS**, using `MAXSEV_IM` (or `INJSEV_IM` for persons), the full
   design and design-based SEs. FARS has no non-fatal denominator. A "fatal share" from CRSS is effectively the FARS count divided by the CRSS estimate of all crashes,
   so its uncertainty comes from the denominator.
4. **Person-level fatalities in CRSS** (`INJSEV_IM = 4`) are within −2.5% to +0.3% of FARS but are **not** calibrated. Do not report them as counts.
5. **Regional fatal counts in CRSS 2016** do not match FARS by region (Midwest −13.0%, West +11.6%) because the calibration combined those regions. Do not
   use CRSS 2016 for regional fatal-share analyses.
6. Whether CRSS `INJ_SEV = 4` follows the same 30-day rule as FARS is **UNVERIFIED** (the label text "Fatal Injury (K)" is identical).

---

## 8. CRSS `*_IM` imputed variables (`svy_06`)

Method: for each pair (original → `*_IM`) and year, the cross-tabulation was formed. *Imputed* means records whose `*_IM` differs from the original.
*Known changed* means records whose original code is not an unknown code but whose `*_IM` differs. Unknown codes were identified from 2019+ label text matching
"Unknown", "Not Reported" or "Reported as Unknown", and the same codes were applied to 2016–18. For each original code, the share of records that map to its most common `*_IM` value was used to classify
the code as **deterministic** (≥ 99.5% to one value) or **distributed** (imputed).

### 8.1 Share of records where `*_IM` ≠ original (%)

| Pair | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 |
|---|---|---|---|---|---|---|---|---|---|
| accident.DAY_WEEK → WKDY_IM | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| accident.HOUR → HOUR_IM (and MINUTE → MINUTE_IM) | 0.16 | 0.28 | 0.47 | 0.62 | 0.61 | 0.64 | 0.70 | 0.69 | 0.66 |
| accident.HARM_EV → EVENT1_IM | 0.05 | 0.07 | 0.02 | 0.07 | 0.11 | 0.06 | 0.09 | 0.11 | 0.07 |
| accident.MAN_COLL → MANCOL_IM | 0.33 | 0.49 | 0.61 | 0.39 | 0.16 | 0.17 | 0.20 | 0.27 | 0.20 |
| accident.RELJCT1 → RELJCT1_IM | 1.98 | **21.38** | **30.96** | (no `_IM`) | 7.28 | 0.28 | 0.03 | 0.09 | 0.08 |
| accident.RELJCT2 → RELJCT2_IM | 0.74 | 2.08 | 6.10 | **27.91** | 0.16 | 0.30 | 0.05 | 0.18 | 0.14 |
| accident.LGT_COND → LGTCON_IM | 0.66 | 0.78 | 1.04 | 0.99 | 0.96 | 0.44 | 0.36 | 0.42 | 0.45 |
| accident.WEATHER → WEATHR_IM | 3.40 | 4.49 | 5.82 | 6.48 | 5.28 | 2.95 | 3.11 | 3.45 | 3.13 |
| accident.MAX_SEV → MAXSEV_IM | 2.75 | 2.46 | 2.39 | 2.89 | 3.10 | 2.24 | 2.43 | 2.51 | 2.24 |
| accident.NUM_INJ → NO_INJ_IM | 3.36 | 3.01 | 2.87 | 3.59 | 4.01 | 2.74 | 2.95 | 2.94 | 2.60 |
| accident.ALCOHOL → ALCHL_IM | 14.08 | 14.46 | 13.17 | **31.88** | **39.84** | 39.04 | 39.77 | 39.22 | 39.14 |
| vehicle.BODY_TYP → BDYTYP_IM | 2.54 | 2.82 | 5.09 | 4.69 | 4.71 | (dropped) | – | – | – |
| vehicle.HIT_RUN → HITRUN_IM | 0.01 | 0.01 | 0.01 | 0.01 | (dropped) | – | – | – | – |
| vehicle.IMPACT1 → IMPACT1_IM | 2.01 | 2.51 | 2.62 | 2.39 | 2.52 | 1.71 | 1.43 | 1.76 | 1.47 |
| vehicle.MOD_YEAR → MDLYR_IM | 3.72 | 3.79 | 4.02 | 4.03 | 4.65 | 4.68 | 4.62 | 4.77 | 4.43 |
| vehicle.MAX_VSEV → MXVSEV_IM | 4.43 | 4.27 | 3.79 | 3.95 | 4.51 | 4.56 | 4.79 | 4.66 | 4.31 |
| vehicle.NUM_INJV → NUMINJ_IM | 4.65 | 4.52 | 4.01 | 4.20 | 4.75 | 4.82 | 5.06 | 4.91 | 4.55 |
| vehicle.P_CRASH1 → PCRASH1_IM | 1.52 | 2.08 | 1.90 | 1.87 | 1.71 | 1.24 | 1.01 | 1.57 | 1.45 |
| vehicle.M_HARM → VEVENT_IM | 0.03 | 0.04 | 0.02 | 0.04 | 0.07 | 0.04 | 0.06 | 0.06 | 0.05 |
| vehicle.VEH_ALCH → V_ALCH_IM | 9.89 | 9.66 | 8.51 | **27.93** | **35.45** | 34.60 | 34.75 | 34.29 | 34.31 |
| person.AGE → AGE_IM | 5.42 | 6.91 | 5.66 | 5.61 | **8.12** | 6.55 | 6.14 | 6.35 | 6.06 |
| person.SEX → SEX_IM | 3.41 | 4.19 | 3.93 | 4.10 | 4.57 | 4.53 | 4.78 | 4.85 | 4.52 |
| person.INJ_SEV → INJSEV_IM | 3.45 | 3.46 | 3.03 | 3.15 | 3.66 | 3.64 | 3.79 | 3.82 | 3.59 |
| person.SEAT_POS → SEAT_IM | 1.29 | 1.68 | 1.54 | 1.41 | 1.43 | 1.64 | 1.64 | 1.91 | 2.10 |
| person.EJECTION → EJECT_IM | 2.08 | 6.41 | 6.32 | 5.60 | 7.30 | 6.40 | 3.51 | 3.45 | 3.56 |
| person.DRINKING → PERALCH_IM | 29.75 | 29.77 | 27.98 | **43.03** | **48.55** | 48.28 | 48.33 | 48.28 | 48.28 |

Availability of the `_IM` variables (`variable_availability.csv`): `RELJCT1_IM` is absent in 2019, `HITRUN_IM` exists only in 2016–2019 and `BDYTYP_IM` only in 2016–2020.
All others are present in 2016–2024. The labels for `*_IM` exist only in 2019–2024.

### 8.2 Does imputation fill only unknown codes? [xtab]

* **Yes, known values are never changed (0.000% "known changed" in every year)** for WKDY_IM, HOUR_IM, MINUTE_IM, EVENT1_IM, MANCOL_IM, RELJCT1_IM, RELJCT2_IM,
  LGTCON_IM, WEATHR_IM, BDYTYP_IM, HITRUN_IM, IMPACT1_IM, MDLYR_IM, PCRASH1_IM, VEVENT_IM, AGE_IM, SEX_IM, INJSEV_IM, SEAT_IM, EJECT_IM and PERALCH_IM.
* **Partly-unknown codes are kept, not imputed (deterministic identity mapping):** `HARM_EV`/`M_HARM` 91 "Unknown Object Not Fixed" and 93 "Unknown Fixed Object";
  `LGT_COND` 6 "Dark - Unknown Lighting" (3,908 of 3,908 kept); `INJ_SEV` 5 "Injured, Severity Unknown" (2,624 of 2,624 kept); `MAX_SEV`/`MAX_VSEV` 5 (98.2% and 99.8% kept);
  `BODY_TYP` "unknown subtype" codes 7, 8, 9, 19, 29, 39, 48, 59, 64, 71, 72, 73, 78, 87 and 89 (100% kept). Only 49 "Unknown light vehicle type", 79 "Unknown truck type
  (light/medium/heavy)", 98 and 99 are distributed (0% kept; 27, 20, 34 and 43 distinct imputed values); `IMPACT1` 20; `SEAT_POS` 53;
  `EJECTION` 3 "Ejected - Unknown Degree"; `P_CRASH1` 0 "No Driver Present / Unknown if Driver Present". Analysts must still treat these codes as partly unknown in the `_IM` variables.
* **Fully-unknown codes (8/9, 98/99, 998/999, 9998/9999) are always replaced.** The most common imputed values are: `ALCOHOL` 9 → 2 "No Alcohol Involved"
  (95.1%), `VEH_ALCH` 9 → 2 (96.7%), `DRINKING` 8 → 0 (98.6%) and 9 → 0 (94.8%), `EJECTION` 7 "Not Reported" → 0 (99.6%) and 9 → 0 (98.6%), `RELJCT1` 8 → 0 (94.4%),
  `INJ_SEV` 9 → 0 (73.8%), `MAX_SEV` 9 → 0 (66.6%), `WEATHER` 98 → 1 Clear (72.7%), and `MOD_YEAR` 9999 spread over model years (largest single value 6.2%).
  **Imputation for ejection and alcohol is close to "unknown means no".** Shares estimated from these variables depend heavily on that rule, which is a strong
  assumption that is **UNVERIFIED** as a model.
* **Aggregates change known values:** `MAXSEV_IM` (known changed 0.52–1.26% per year), `NO_INJ_IM` (0.94–2.15%), `MXVSEV_IM` (0.09–0.20%) and `NUMINJ_IM` (0.32–0.45%).
  The reason is that they are recomputed from person-level `INJSEV_IM`, which imputes persons with unknown severity in crashes whose other persons are known
  (the exact derivation for `MAXSEV_IM` is in §4.9). For example, 1.4% of `MAX_SEV = 0` crashes have `MAXSEV_IM > 0`.
* `ALCOHOL` 8 "No applicable person" is mapped deterministically, which accounts for the 0.03–0.06% "known changed" for that pair.
* **Coding breaks visible in the imputation shares:** the alcohol variables (`ALCOHOL`, `VEH_ALCH`, `DRINKING`) more than double their unknown share in 2019 and again in 2020.
  `RELJCT1` (2017–18, 2020) and `RELJCT2` (2019) have temporary bursts of "Not Reported", and `EJECTION` unknowns jump in 2017 and fall in 2022. These come from
  the original variables (see `alcohol_drugs.md` and `crash_environment.md`). They mean that **the share of each `*_IM` value that is imputed changes by year,
  so trends in `*_IM` variables partly reflect imputation**.

### 8.3 Imputation depends on severity [xtab] (share of records with unknown original, pooled 2016–24, by crash `MAXSEV_IM`)

| Original | O | C | B | A | K |
|---|---|---|---|---|---|
| `ALCOHOL` = 9 | 29.3 | 31.1 | 30.2 | 30.7 | **47.2** |
| `VEH_ALCH` = 9 (vehicles) | 25.1 | 25.6 | 25.5 | 26.2 | **35.7** |
| `DRINKING` ∈ {8,9} (persons) | 39.2 | 43.4 | 42.0 | 44.1 | **51.7** |
| `AGE` ∈ {998,999} (persons) | **7.09** | 6.12 | 6.02 | 4.59 | 4.05 |
| `SEX` ∈ {8,9} | **5.01** | 3.90 | 4.04 | 3.25 | 2.74 |
| `EJECTION` ∈ {7,9} (+3) | 5.43 | 5.01 | 4.63 | 4.34 | 3.15 |
| `MOD_YEAR` ∈ {9998,9999} | 4.58 | 4.23 | 4.50 | 3.13 | 2.74 |
| `IMPACT1` ∈ {98,99} (+20) | 1.75 | 1.85 | 2.49 | 2.89 | **4.00** |
| `HOUR` = 99 | 0.72 | 0.30 | 0.41 | 0.36 | **1.20** |
| `WEATHER` ∈ {98,99} | 4.34 | 2.81 | 5.32 | 4.94 | 3.73 |
| `INJ_SEV` = 9 (persons) | 3.43 | 3.80 | 3.85 | 3.25 | 2.61 |

Person `INJ_SEV = 9` by **sampling stratum**, a severity proxy assigned before coding: strata 2 (non-occupant, 5.8–7.5%) and 10 (other, 5.9–7.3%) are highest,
followed by 7 (3.1–3.8%), 9 (2.8–4.2%), 8 (1.7–2.1%), 6 (1.3–2.0%), 3 (1.7–2.3%) and 4/5 (0.8–1.4%). The imputed values depend on the stratum. A person with unknown severity
becomes K with probability 1.32% in KA strata 4/5, 0.43% in BC strata 6/8 and 0.33% in no-injury strata 7/9/10. They become A with probability 4.45%, 2.82% and 3.28%.
The imputation is therefore conditional on crash attributes, but the model itself is **UNVERIFIED**.

---

## 9. Design changes by year that affect trend analysis

| Year | Change (evidence) | Consequence |
|---|---|---|
| **2016** | 24 strata (str 23 absent); 53 PSUs; 54 PSU_VARs (stratum 20 split into only 2); PSU_VARs 80, 13 and 72 cover only 4, 7 and 8 months; weight CV 0.742, max/min 258, deff_w 1.55; weighted PSUSTRAT TVD against 2019 is 0.117; fatal calibration combined Midwest+West | Highest variance and lowest df (30). Regional and PSU-level 2016 estimates are not comparable. Use 2016 only for national estimates, and flag them |
| 2017 | PSU_VAR 210 absent (stratum 20 has 7); df 41; KA-share deff 11.5 (other years 3.4–5.7) | Slightly fewer clusters |
| 2018→2023 | Distinct PJs fall from 380 to 261 | More clustering within PSU. Effective n falls even when sampled crashes do not |
| **2020** | Annual n flat (54,745) but monthly n 2,097 in April (4,310 in 2019); sampling fractions raised from June (median weight 136 → 94); stratum-3 share 7.0% (otherwise 4.8–5.9%); sampled fatal crashes 1,387 (948 in 2019); PSU_VAR 61 has 203 cases; 5 PSU_VARs with 11 months; weighted total 5.25 M (−22%) | Pandemic changes in exposure and design together. Use weights for all within-year analyses. The SE of 2020 vs 2019 contrasts must use shared clusters (§6.4) |
| **2021** | Sampling rates low January–July (stratum-9 median weight 182), high August–December (93); monthly n 2,997–6,336; CV 0.687; max weight 797 | Same as 2020 |
| 2022 | PSU 61 absent (stratum 1 has 3 PSUs); df 41; weights flat within the year | Minor |
| 2016→2024 | Weighted crashes in certainty PSU 56 (stratum 20) fall from 179k to 71k, and its sample falls from 1,532 (2017) to 700 (2024); West weighted crashes fall 36% while the Northeast rises 27% | Regional trends are fragile, and the cause is **UNVERIFIED** |

National totals for 2017–2024 are comparable in design terms (same 25 strata and 66–67 PSU_VARs), as long as `MAXSEV_IM` (calibrated) is used for fatal counts.

---

## 10. Differential missingness by severity (summary)

* **Design fields:** 0% missing at every severity and in every year, so they introduce no bias.
* **Crash severity itself:** `MAX_SEV = 9` is concentrated in no-injury sampling strata (stratum 10 5.2–7.1%, against ≤ 0.15% in injury strata). Weighted it is 2.5–3.4% of
  crashes. Complete-case severity analyses that drop `MAX_SEV = 9` therefore **under-represent no-injury crashes and inflate injury shares**. The observed injury
  share (`MAX_SEV` 1–5 among 0–5) is 27.1–30.3%, against 27.7–31.5% for `MAXSEV_IM` 1–5 among all crashes. This happens because some imputed crashes receive injury codes, while
  `MAX_SEV` known codes are lower bounds (§4.9).
* **Imputed-fatal contribution:** 0.6–12.2% of weighted fatal crashes by year (§4.9). Trends in `MAX_SEV = 4` are distorted.
* **Alcohol** is unknown much more often in fatal crashes (47.2% against about 30%), so `ALCHL_IM` in fatal crashes depends more heavily on imputation than in
  non-fatal crashes. **Age and sex** are unknown more often in low-severity crashes (O 7.1% / 5.0% against K 4.1% / 2.7%).
* Year-specific details for the substantive variables are in the other `docs/audit/*.md` appendices.

---

## 11. Cross-cutting findings

1. Statements elsewhere in the repository that CRSS has "25 strata / 67 clusters, stable 2016–2024, df 42" (`docs/data_audit.md`, docstring of
   `src/nhtsa_stats/analysis/survey.py`) are **correct only for pooled data and for 2018–2021 and 2023–2024**. Single-year analyses of 2016 have
   24/54 (df 30), and analyses of 2017 and 2022 have 25/66 (df 41). The df should be computed from the data, not hard-coded.
2. CRSS weights carry a **FARS benchmark**. This keeps CRSS fatal counts consistent with FARS but means that CRSS cannot independently validate FARS counts. It also means the
   fatal/non-fatal weight ratio inside a cell is not purely a design ratio.
3. **`STRATUM` and `WEIGHT` are outcome-dependent**, because the strata are built from injury severity and the weights from strata plus fatal calibration. A
   regression of severity on covariates that uses the weights is valid for design-based (census-parameter) inference. Using `STRATUM` as a covariate is not.
4. Design effects for injury-related proportions are 5–27. With 42 df, subgroup estimates quickly reach RSE > 30% and should be suppressed
   (for example the "injured, severity unknown" total, which has RSE 31–56%).
5. Every design field is identical across all tables, so person- and vehicle-level analyses need no re-merge of design information.
6. `*_IM` variables are the right choice for estimating totals and shares, because they are consistent with the calibrated weights. For each `*_IM` used, report
   its imputed share, which reaches 39–49% for alcohol variables after 2019.

## 12. Harmonised definitions (implementation recipes)

All recipes are applied to the CRSS tables in `data/interim/CRSS/<table>/<year>.parquet` and join on (`YEAR`, `CASENUM`).

| Name | Level | Recipe |
|---|---|---|
| `crss_var_stratum` | crash (copied to every row) | `PSUSTRAT` as Int (1–25; 23 absent in 2016). No recode. Never add a year suffix |
| `crss_var_cluster` | crash | `PSU_VAR` as Int. It is globally unique (no need to nest by stratum), and the same ID across years refers to the same unit, so use it as is in pooled data |
| `crss_weight` | crash | `WEIGHT` (Float64, > 0). Use the row's own `WEIGHT` in every table (identical to accident). For an annual average over k pooled years, multiply by 1/k |
| `crss_design_df` | analysis | `n_distinct(PSU_VAR) − n_distinct(PSUSTRAT)` over the analysed years (30 / 41 / 42 / 42 / 42 / 42 / 41 / 42 / 42; pooled 2016–24: 42) |
| `crss_crash_stratum` | crash | `STRATUM` 2–10 → labels in §4.5 (all years). Code 1 does not occur. Diagnostic use only, not a covariate |
| `region4` | crash | CRSS: `REGION` 1–4 (Northeast / Midwest / South / West). FARS: `STATE` → 1 for {9,23,25,33,34,36,42,44,50}; 2 for {17,18,19,20,26,27,29,31,38,39,46,55}; 3 for {1,5,10,11,12,13,21,22,24,28,37,40,45,47,48,51,54}; 4 for {2,4,6,8,15,16,30,32,35,41,49,53,56} |
| `crss_psu_urbanicity` | PSU | `URBANICITY` 1 urban, 2 rural (PSU attribute). Do not harmonise with FARS `RUR_URB` |
| `crash_max_sev_im` | crash | `MAXSEV_IM`: 0→O, 1→C, 2→B, 3→A, 4→K, 5→"injury, severity unknown", 6→"died prior to crash" (exclude from injury analyses), 8→"no person" (exclude from person-based analyses). Same in all years |
| `crash_max_sev_obs` | crash | `MAX_SEV`: as above, with 9 → missing (never treated as O). Flag `max_sev_lower_bound = any person INJ_SEV == 9` |
| `crash_fatal` | crash | CRSS: `MAXSEV_IM == 4`. FARS: every accident row is fatal. Counts come from FARS; shares per crash come from CRSS |
| `crash_injury_any` | crash | CRSS: `MAXSEV_IM ∈ {1,2,3,4,5}` = 1; `∈ {0}` = 0; 6 and 8 excluded |
| `crash_injury_class_aux` | crash | `acc_aux.A_CRAINJ`: 4 fatal, 2 non-fatal injury (MAXSEV_IM 1/2/3/5), 3 no injury (MAXSEV_IM 0/6/8) |
| `person_inj_sev_im` | person | CRSS `INJSEV_IM` 0–4 KABCO, 5 injured unknown, 6 died prior. FARS `INJ_SEV` same codes, with 9 → missing |
| `<var>_imputed` | as variable | `1` if original ∈ its fully-unknown set (ALCOHOL 9; VEH_ALCH 9; DRINKING 8,9; AGE 998,999; SEX 8,9; INJ_SEV 9; MAX_SEV 9; MAX_VSEV 9; NUM_INJ 99; NUM_INJV 99; SEAT_POS 98,99 + 19/29/39/49 when changed; EJECTION 7,9; MOD_YEAR 9998,9999; BODY_TYP 49,79,98,99; IMPACT1 98,99; P_CRASH1 99; HARM_EV/M_HARM 98,99; MAN_COLL 98,99; RELJCT1 8,9; RELJCT2 98,99; LGT_COND 8,9; WEATHER 98,99; HOUR/MINUTE 99), else `0`. In practice `(*_IM != original)` gives the same result except for the aggregates and `ALCOHOL` 8 |
| `crss_design_period` | crash | `YEAR==2016` → "phase-in"; 2017–2019 → "standard"; 2020–2021 → "within-year rate change"; 2022–2024 → "standard". Use as a sensitivity stratum in trend models |
| `fars_fatal_crashes`, `fars_fatalities` | year | FARS `accident` row count; `Σ FATALS` (= count of `person.INJ_SEV == 4`) |

Variance code (pseudo):
```
z = WEIGHT * linearised_y        # u_k for ratios
T = sum z by (PSUSTRAT, PSU_VAR) # keep all (stratum, cluster) pairs of the analysed years, zero-filled
V = sum_h n_h/(n_h-1) * sum_i (T_hi - mean_h T)^2
df = n_clusters - n_strata ; CI uses t_df
```

## 13. Open questions and UNVERIFIED items

1. Meaning of `PSUSTRAT` beyond region × urbanicity (sub-stratifiers), and of `PSU`/`PSU_VAR` codes. There are no labels.
2. That `PJ` means "police jurisdiction" and that PSU 56 is a certainty PSU. The structure fits both, but there are no labels.
3. The exact rule assigning crashes to STRATUM (precedence among non-motorist, motorcycle, truck/bus and PV strata, and the exact LMY model-year window). The
   data suggest "newest PV ≤ 4 model years before crash year", but this is not confirmed. The meaning of the absent code 1 is also unknown.
4. The exact weighting procedure: base weights, non-response adjustment, the calibration method, and whether there are control totals other than fatal crashes by region.
   The FARS release used for benchmarking is unknown, so the −0.3% to −0.9% residuals in 2017–2023 are unexplained.
5. The reasons for the 2020 and 2021 changes in sampling rate within the year, for the fall in PJs, and for the decline of PSU 56 and the West region.
6. The imputation models behind the `*_IM` variables (which predictors, hot-deck or model-based, single or multiple imputation). The data show only single imputed values
   and their conditional distributions.
7. Whether CRSS `INJ_SEV = 4` (K) uses the FARS 30-day death criterion.
8. Variance estimation that accounts for calibration (for example replicate weights). Replicate weights are not supplied in these files, so Taylor SEs for
   fatal totals are conservative.
