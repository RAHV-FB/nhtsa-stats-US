# Audit appendix: crash-level circumstances ("crash environment"), FARS and CRSS 2016-2024

*Data audited: typed Parquet cache `data/interim/{FARS,CRSS}/{accident,weather,crashrf,acc_aux}/{year}.parquet`, plus the
inventory files in `outputs/audit/`. Analysis scripts (not part of the package; the directory is shared with other audits) are in
`/tmp/claude-0/-home-user-nhtsa-stats-US/dd56b1ab-53ab-5c90-8154-cdf8a010f996/scratchpad/audit_scripts/`:
`01_codebook_compare.py` (code sets, labels and distributions by year), `02_time.py`, `03_weather.py`, `04_urbanicity.py`, `05_counts.py`, `05b_counts.py`,
`06_missing_by_severity.py`, `07_crashrf.py`, `08_imputation.py`, `09_concentration.py`, `10_junction.py`, `11_ruralurban.py`,
`12_crss_label_transfer.py`, `13_consistency.py`, `14_harmonised_dists.py`, `15_harmev_groups.py`.
Every number below was computed from these data. No external documentation was used. When a code's meaning comes from
the in-archive label columns (`<VAR>NAME`), the evidence is given as **[label]**; a meaning taken from a cross-tabulation or a
consistency check is given as **[xtab]**; and a meaning that could not be verified is marked **UNVERIFIED**.*

---

## 1. Purpose and scope

This appendix documents the crash-level ("environment") variables that later analyses will use as covariates, strata or
outcomes. For each variable it records:

1. which source-years contain it,
2. its codes and what they mean, with the evidence for each meaning,
3. year-to-year coding or definition breaks,
4. unknown and not-reported codes, their rates by year, and whether those rates **depend on crash severity**,
5. a reliability verdict and a harmonised definition that can be implemented across years (and across sources where
   that makes sense).

Scope: FARS `accident` (2016-2024) and `weather` (2020-2024); CRSS `accident` (2016-2024), `weather` (2020-2024) and
`crashrf` (2020-2024). FARS `crashrf` (2020-2024) is included because it replaces CF1-CF3. The unlabelled `acc_aux` tables are covered only
where they could be mistaken for one of these variables (section 4.17). Detailed alcohol (ALCOHOL/ALCHL_IM) and person-level
injury are other audits; this appendix records only their crash-level aspects.

Sizes: FARS crashes per year 34,748 / 34,560 / 33,919 / 33,487 / 35,935 / 39,785 / 39,422 / 37,769 / 36,297 (2016→2024).
CRSS sampled crashes 46,511 / 54,969 / 48,443 / 54,409 / 54,745 / 54,200 / 53,955 / 50,103 / 51,658.

## 2. Tables and variables covered

| Concept | FARS (accident unless stated) | CRSS (accident unless stated) | Years present |
|---|---|---|---|
| Time | HOUR, MINUTE, DAY, DAY_WEEK, MONTH | HOUR, MINUTE, DAY_WEEK, MONTH, HOUR_IM, MINUTE_IM, WKDY_IM | all; CRSS has no DAY |
| Light | LGT_COND | LGT_COND, LGTCON_IM | all |
| Weather | WEATHER; WEATHER1/WEATHER2 (2016-19); `weather`.WEATHER (2020-24) | same + WEATHR_IM; `weather`.WEATHER (2021-24) / **WEATHERCODE (2020)** | as stated |
| Rural/urban | RUR_URB (road level) | URBANICITY (**PSU level**, see 4.4) | all |
| Road class | FUNC_SYS, NHS, ROUTE, RD_OWNER, SP_JUR | INT_HWY | all |
| Junction | RELJCT1, RELJCT2, TYP_INT | RELJCT1, RELJCT2, TYP_INT, RELJCT1_IM (absent 2019), RELJCT2_IM | all |
| Relation to road | REL_ROAD | REL_ROAD | all |
| Work zone | WRK_ZONE | WRK_ZONE | all |
| Manner of collision | MAN_COLL | MAN_COLL, MANCOL_IM | all |
| First harmful event | HARM_EV | HARM_EV, EVENT1_IM | all |
| Counts | VE_TOTAL, VE_FORMS, PVH_INVL, PEDS, PERSONS, PERMVIT, PERNOTMVIT, FATALS | VE_TOTAL, VE_FORMS, PVH_INVL, PEDS, PERMVIT, PERNOTMVIT, NUM_INJ, NO_INJ_IM | all |
| Severity | (FATALS; person table) | MAX_SEV, MAXSEV_IM | all |
| Alcohol (note only) | (DRUNK_DR 2016-20, other audit) | ALCOHOL, ALCHL_IM | all |
| Crash factors | CF1-CF3 (2016-19); `crashrf`.CRASHRF (2020-24) | same | as stated |
| Geography | STATE (+COUNTY, CITY, LAT/LON, out of scope) | REGION (+PSU, PJ, PSUSTRAT design fields) | all |
| School bus / rail | SCH_BUS, RAIL | SCH_BUS (no RAIL) | all |

Label columns exist for FARS in all years and for CRSS only in 2019-2024. CRSS 2019 also labels CF1-3 and WEATHER1/2. For
CRSS 2020 `weather`, the code column is named `WEATHERCODE`, so `codebook.csv` contains no pairs for it. A direct
cross-tab of `WEATHERCODE` × `WEATHERNAME` gives the same 13 code-to-label pairs as accident.WEATHER.

## 3. Conventions used in this appendix

* **Unknown set** means the codes treated as missing: 8/9 or 98/99 ("Not Reported", "(Reported as) Unknown"), and for FARS
  RUR_URB, FUNC_SYS and RD_OWNER also 6/96 ("Trafficway Not in State Inventory"). Partial-information codes (for example LGT_COND 6
  "Dark - Unknown Lighting", WRK_ZONE 4 "Work Zone, Type Unknown", HARM_EV 91/93 "Unknown Object …") are reported
  separately and are **not** counted as missing.
* **FARS severity strata**: (a) crash level, FATALS = 1 (93.0 % of crashes) vs FATALS ≥ 2 (7.0 %); (b) person level,
  using `person`.INJ_SEV (4 = "Fatal Injury (K)" **[label]**). Killed = INJ_SEV 4 (n = 353,706, pooled 2016-24); survivors =
  INJ_SEV 0,1,2,3,5 (n = 434,621); injury unknown = 9 (n = 12,361). Section 4.11 shows FATALS equals the number of person
  records with INJ_SEV = 4 in 100 % of crashes in every year.
* **CRSS severity strata**: MAX_SEV is O = 0, C = 1, B = 2, A = 3, K = 4 and U = {5 "Injured, Severity Unknown", 9 "Unknown/Not Reported"} **[label 2019-24]**.
  The code set and distribution for 2016-18 are the same (section 5). In every year, MAX_SEV equals the maximum person INJ_SEV over codes 0-4 in 100 % of
  crashes. CRSS rates are **weighted by WEIGHT** unless marked "unweighted". Design-based variances, which need PSU and PSUSTRAT, are not computed here.
* **TVD** is the total-variation distance between two years' code distributions, ½Σ|p₁−p₂|. A value ≤ 0.03 is typical
  between adjacent years when nothing changed.

---

## 4. Per-variable sections

### 4.1 Time: HOUR, MINUTE, DAY_WEEK, MONTH, DAY (FARS); HOUR_IM, MINUTE_IM, WKDY_IM (CRSS)

**Codes.**
* HOUR: 0-23 = "0:00am-0:59am" … "11:00pm-11:59pm" **[label]**; 99 = "Unknown Hours" **[label]**.
* MINUTE: 0-59; 99 = "Unknown Minutes" **[label]**.
* DAY_WEEK: 1 = Sunday … 7 = Saturday **[label]**. Verified against the calendar: FARS DAY_WEEK matches the weekday of
  (YEAR, MONTH, DAY) in **100.0 %** of crashes in every year **[xtab]**.
* MONTH: 1-12 **[label]**.
* FARS DAY: 1-31, with no unknown code observed.
* No unknown code occurs for DAY_WEEK or MONTH in either source. In CRSS, WKDY_IM equals DAY_WEEK in 100 % of crashes in every year, so it is redundant.

**Unknown rates (HOUR = 99; MINUTE = 99 is the same apart from one case per year in 2016 and 2018).**

| % | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 |
|---|---|---|---|---|---|---|---|---|---|
| FARS | 0.73 | 0.76 | 0.67 | 0.73 | 0.85 | 0.75 | 0.75 | 0.72 | 0.70 |
| CRSS unweighted | 0.16 | 0.28 | 0.47 | 0.62 | 0.61 | 0.64 | 0.70 | 0.69 | 0.66 |
| CRSS weighted | 0.19 | 0.38 | 0.65 | 0.84 | 0.85 | 0.88 | 0.92 | 0.93 | 0.92 |

CRSS unknown HOUR increased about fourfold between 2016 and 2019 (unweighted 0.16 → 0.62 %) and then stayed level. This is a reporting drift, not a code change.

**Differential missingness.**
* FARS: crashes with FATALS = 1 have 0.75 % unknown, against 0.56 % for FATALS ≥ 2. At person level, 0.72 % of killed persons
  have an unknown crash hour, against **0.18 %** of survivors, a ratio of about 4 that holds in every year (2016: 0.71 vs 0.17;
  2024: 0.68 vs 0.16).
* FARS crashes with unknown hour differ sharply from the rest: 91.9 % are single-vehicle (vs 56.5 %), 64.5 % are rural (vs 41.8 %),
  43.0 % are dark-not-lighted (vs 27.1 %), and 26.2 % also have unknown light (vs 0.4 %). Missingness is clearly informative
  (unwitnessed, rural, night-time crashes).
* CRSS, weighted and pooled: O 0.47 %, C 0.20 %, B 0.34 %, A 0.31 %, K 1.29 %, **U 9.57 %**.
* CRSS HOUR_IM places 12.4 % of imputed crashes at 00-05 h, against 8.0 % of crashes with observed hour.

**Data quality.** Minutes heap on multiples of 5: 35.8-40.7 % of FARS minutes and 40.7-44.5 % of CRSS minutes fall on a
multiple of 5, where 20 % would be expected. Minute 0 alone holds 4.5-5.3 % (FARS) and 5.9-6.6 % (CRSS). Light is plausible against hour: in FARS,
0.02 % of 00-03 h crashes are coded Daylight and 0.06 % of 11-14 h crashes are coded dark. The CRSS figures are 0.58 % and 0.06 %.

**Breaks.** None in the codes. MONTH distributions in 2020-2021 are distorted by COVID: CRSS April 2020 is 3.8 % of sampled crashes
against about 8 % in other years (TVD 2019→2020 = 0.09).

**Verdict.** HOUR, DAY_WEEK and MONTH are **high** reliability. Unknown HOUR is rare but informative, so keep an explicit missing
category or impute. Use MINUTE only coarsely (heaping).

### 4.2 Light condition: LGT_COND, LGTCON_IM

**Codes [label, identical in FARS 2016-24 and CRSS 2019-24]:** 1 Daylight, 2 Dark - Not Lighted, 3 Dark - Lighted, 4 Dawn,
5 Dusk, 6 Dark - Unknown Lighting, 7 Other, 8 Not Reported, 9 Unknown (FARS 2016-17), relabelled "Reported as Unknown"
(FARS 2018+ and all CRSS labelled years). The relabel is cosmetic because 8 and 9 are distinct in every year.
LGTCON_IM has codes 1-7 only: imputation replaces 8 and 9, while 6 and 7 are kept.

**Distribution, known values** (FARS, %): daylight 47.6→45.4, dark-unlighted 27.7→26.7, dark-lighted 20.0→22.2, dawn/dusk 4.1-4.6,
dark-unknown-lighting **0.6→1.3** (2016→2024). CRSS weighted LGTCON_IM: daylight 69.9→68.2, dark-unlighted 10.1-11.6, dark-lighted 14.9→15.5,
dark-unknown-lighting 0.6-1.3.

**Unknown {8,9} %**

| | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 |
|---|---|---|---|---|---|---|---|---|---|
| FARS | 0.48 | 0.42 | 0.51 | 0.62 | 0.63 | 0.72 | 0.73 | 0.59 | 0.66 |
| CRSS weighted | 0.87 | 1.04 | 1.35 | 1.30 | 1.35 | 0.61 | 0.52 | 0.57 | 0.61 |
| FARS code 6 (partial) | 0.60 | 0.72 | 0.72 | 0.76 | 0.92 | 1.06 | 1.10 | 1.17 | 1.25 |

**Differential missingness.** FARS person level: 0.59 % of killed persons vs 0.14 % of survivors. CRSS: O 0.65, C 0.25, B 0.24, A 0.25,
K 0.49, **U 12.11** (weighted %). The imputed CRSS values are very different from the observed ones: 25.4 % of imputed crashes are
dark-not-lighted against 10.4 % of observed, and 51.1 % are daylight against 68.9 %. Unknown light is concentrated at night.

**Breaks.** None in the codes. The share in code 6 roughly doubled in both sources, a gradual reporting drift.

**Verdict.** **High** reliability.

### 4.3 Weather: WEATHER, WEATHER1/2 (2016-19), weather table (2020-24), WEATHR_IM

**Codes [label; FARS all years, CRSS 2019-24, the CRSS 2020 weather table checked by direct cross-tab]:** 1 Clear, 2 Rain, 3 Sleet or Hail, 4 Snow,
5 Fog, Smog, Smoke, 6 Severe Crosswinds, 7 Blowing Sand, Soil, Dirt, 8 Other, 10 Cloudy, 11 Blowing Snow, 12 Freezing Rain or
Drizzle, 98 Not Reported, 99 Unknown → "Reported as Unknown" (cosmetic). Code 9 is never used. WEATHER2 adds 0 "No Additional
Atmospheric Conditions". Normalised labels in the weather table match accident.WEATHER for every code and year.

**What accident.WEATHER is [xtab].** It is a single summary condition that has the same meaning in every year.
* 2016-19: WEATHER equals WEATHER1 in 99.5-99.6 % (FARS) and 99.6-99.9 % (CRSS) of crashes. Every disagreement is a crash with a second
  condition, where WEATHER takes the more specific or more severe one. For example (WEATHER1 = 10 Cloudy, WEATHER2 = 2 Rain) gives WEATHER = 2
  in 366 FARS and 406 CRSS crashes, and (2 Rain, 3 Sleet) gives 3.
* 2020-24: WEATHER equals the single weather-table row for 100 % of single-row crashes, and is always one of the rows for
  multi-row crashes (100 %). The same precedence holds: {2,10} gives 2 in 1,258 FARS and 981 CRSS crashes.
* Multiple conditions are equally common before and after the change. FARS: 1.0-1.15 % of crashes have WEATHER2 ≠ 0 (2016-19), and
  0.94-1.10 % have more than one weather row (2020-24). CRSS: 0.32-0.62 % and 0.41-0.71 %.
* Every accident crash has at least one weather-table row (no orphans).

**Unknown {98,99} %**

| | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 |
|---|---|---|---|---|---|---|---|---|---|
| FARS | 4.89 | 7.01 | 7.74 | 7.44 | 7.31 | 4.47 | 3.90 | 3.70 | 3.85 |
| FARS excl. CO, PA, VA, KS | 0.95 | 0.99 | 1.25 | 1.20 | 1.31 | 1.51 | 1.27 | 1.16 | 1.24 |
| CRSS weighted | 4.13 | 4.58 | 6.12 | 6.76 | 5.65 | 3.30 | 3.46 | 3.91 | 3.68 |

**FARS missingness depends on the state [xtab].** "Not Reported" (98) by state:

| % | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 |
|---|---|---|---|---|---|---|---|---|---|
| Virginia | 89.1 | 89.5 | 86.4 | 87.6 | 83.5 | 89.4 | 88.6 | 88.3 | 89.7 |
| Kansas | 63.3 | 66.8 | 58.6 | 61.5 | 70.2 | 62.4 | 58.2 | 59.8 | 61.1 |
| Colorado | 86.6 | 84.0 | 88.4 | 87.0 | 84.8 | 23.5 | 0.4 | 0.8 | 0.0 |
| Pennsylvania | 2.0 | 57.3 | 74.9 | 74.7 | 72.1 | 1.8 | 1.1 | 1.1 | 0.8 |

The national drop after 2020 comes from Colorado and Pennsylvania starting to report weather. Among known values, the shares are not
affected: FARS "clear" is 73.1 % (2019) and 78.2 % (2022) with all states, and 73.8 % and 78.1 % without the four states. CRSS shows the same
2018-19 wet years (rain 11.2 % and 10.6 % weighted, against 8.2-9.1 % in 2021-24). The movement among known values therefore looks like
real weather, not a coding change.
In CRSS, two PSUs with more than 90 % not reported held 1,518 of the 2,726 unweighted not-reported crashes in 2018, and 1,756 of 3,331 in 2019.

**Differential missingness.** FARS person level: killed 5.44 % vs survivors 4.47 %, with killed higher in every year (2024: 3.78 vs 2.67).
FATALS 1 vs ≥ 2: 5.57 vs 4.74 %. CRSS weighted: O 4.14, **C 2.57**, B 5.01, A 4.23, K 3.27, **U 24.23**. The pattern by severity is not monotone,
and it is extreme for crashes of unknown severity (41.1 % in 2024). WEATHR_IM among imputed crashes (clear 71.8 %, rain 9.8 %) is close to
the observed distribution (72.9 %, 9.6 %).

**Verdict.** **Medium.** Among known values the variable is consistent across years. Missingness is structural by state in FARS
(state fixed effects, or exclude VA and KS from weather analyses) and strongly linked to severity in CRSS.

### 4.4 Rural/urban: FARS RUR_URB (road level) and CRSS URBANICITY (area level)

**FARS RUR_URB [label]:** 1 Rural, 2 Urban, 6 Trafficway Not in State Inventory, 8 Not Reported, 9 Unknown.
RUR_URB = 6 coincides exactly with FUNC_SYS = 96 and with RD_OWNER = 96 (100 % agreement) **[xtab]**, so it is a road-inventory flag.
Unknown {6,8,9} by year: 0.35, 0.25, 0.29, 0.32, 0.43, 0.35, 0.31, 0.50, **0.90** %. "Not Reported" rose to 0.41 % in 2024.
FATALS 1 vs ≥ 2: 0.42 vs 0.25 %. Killed persons vs survivors: 0.40 vs 0.29 %.

**FARS trend and break.** The urban share of known values was 52.5 % (2016), 54.3, 57.3, 56.2, 58.8, 60.8, 60.2, 59.9, 59.9 % (2024).
Fixing the 2016 state mix gives almost the same series (52.5 → 59.7 %), so the change happens **within** states and in steps:
New York 54.4 → 72.2 % (2017→2018), Delaware 48.6 → 71.2 %, California 64.7 → 72.8 %, and Kansas a steady 25.3 → 46.6 %.
Steps like these fit a change in how urban boundaries are coded in the road inventory better than a shift in where crashes happen
(**UNVERIFIED** cause). Treat the urban share as not comparable across years without year terms.

**CRSS URBANICITY.** Labels: 1 "Urban Area", 2 "Rural Area" **[label 2019-24]**. There is no unknown code. The same column is repeated in
`weather` and `crashrf` next to the design fields PSU, PSUSTRAT, PSU_VAR, STRATUM and PJ. Data evidence that it is **area level, not road level** **[xtab]**:
* It is constant within every PSU in every year (0 of 53-60 PSUs mixed), constant for each PSU across all 9 years (0 of 60 mixed), and
  constant within every PSU stratum (PSUSTRAT; 0 of 24-25 mixed). It is also constant within every police jurisdiction (PJ).
* There are 39 urban and 21 rural PSUs (2017-2024, except 38 urban in 2022 when 59 PSUs contributed; 34 and 19 in 2016). 16 PSU strata are urban and 9 are rural.
* It does describe rurality. Rural PSUs, weighted, have 18.3 % dark-not-lighted crashes (urban PSUs 7.9 %), 12.7 % live-animal first harmful
  event (2.4 %) and 7.8 % interstate crashes (10.2 %).
* Weighted rural share: 25.1, 23.4, 23.1, 23.7, 27.3, 25.4, 25.7, 26.0, 26.1 %.

It is a **PSU-level, sampling-design classification**. It cannot be equated with FARS RUR_URB, which describes the crash site. Being a
stratification attribute of only 60 clusters, its effective sample size is tiny and its effects are confounded with PSU. Use it as a
design/area covariate, never as "rural road".

**Verdict.** RUR_URB: **medium** (low missingness, but definition drift). URBANICITY: **high** as an area flag, **not comparable** to RUR_URB.

### 4.5 Road class: FUNC_SYS, NHS, ROUTE, RD_OWNER, SP_JUR (FARS); INT_HWY (CRSS)

**FUNC_SYS [label]:** 1 Interstate; 2 Principal Arterial - Other Freeways and Expressways (renamed in 2023 to "Other Freeways and Expressways",
a cosmetic change); 3 Principal Arterial - Other (2023: "Other Principal Arterial", cosmetic); 4 Minor Arterial; 5 Major Collector; 6 Minor Collector;
7 Local; 96 Trafficway Not in State Inventory; 98 Not Reported; 99 Unknown.
Shares stay close to stable apart from drift in local roads (12.6 % in 2016, 14.2 % in 2017, 10.4 % in 2024) and minor arterials (20.3 → 23.2 %).
Unknown {96,98,99} = 0.49, 0.33, 0.30, 0.49, 0.57, 0.42, 0.40, 0.72, 0.98 %. FATALS 1 vs ≥ 2: 0.54 vs 0.32 %. Killed vs survivors: 0.51 vs 0.34 %.
FUNC_SYS is defined jointly with RUR_URB: all categories 1-7 occur in both rural and urban crashes.

**NHS [label]:** 0 "This section IS NOT on the NHS", 1 "IS ON", 9 "Unknown if this section is on the NHS". Unknown 0.02-0.67 %, varying
erratically by year (0.11, 0.67, 0.30, 0.05, 0.25, 0.31, 0.02, 0.06, 0.67). Consistent with FUNC_SYS: 100 % of FUNC_SYS 1 crashes, 92.5 % of
FUNC_SYS 2 and 82.2 % of FUNC_SYS 3 have NHS = 1, against 0.1-1.7 % of FUNC_SYS 4-7 **[xtab]**.

**ROUTE (signed route type) [label]. The coding changed in 2023.**
* 2016-2022 codes: 1 Interstate, 2 U.S. Highway, 3 State Highway, 4 County Road, 5 Local Street - Township, 6 Local Street - Municipality,
  7 Local Street - Frontage Road, 8 Other, 9 Unknown.
* 2023-2024 codes: 0 **Not Signed (new, 12.0 % / 10.1 %)**, 1-3 the same, 4 "County", 5 "Township", 6 "Municipal" (the wording now describes a route
  marker, not a street type), 10 Parkway/Forest Route Marker, 11 Off-Interstate Business Marker, 12 Secondary Route (2.2-2.6 %), 13 BIA, 95 Other,
  96 Trafficway Not in State Inventory, 99 Unknown/Not Reported. Codes 7, 8 and 9 were dropped.
* Effect: code 6 fell from 13.6 % (2022) to 8.4 % (2023), and "Other" went from 11.5 % (code 8, 2022) to 7.1 % (code 95, 2023).
* Unknown (9 before 2023, 99 from 2023): 0.29, 1.53, 6.14, 6.13, 5.87, 2.45, 1.65, 1.34, 2.81 %. It is state-concentrated: California 12-49 %
  in 2017-2021, Kansas 32.5 % and Wisconsin 26.5 % in 2024.
* ROUTE = 1 and FUNC_SYS = 1 agree for 96 % of crashes that have either one (2016-22: 30,960 both, 815 FUNC_SYS only, 480 ROUTE only).

**RD_OWNER [label]:** 1 State Highway Agency, 2 County, 3 Town/Township, 4 City/Municipal, 11 State Park/Forest/Reservation, 12 Local Park,
21 Other State Agency, 25 Other Local Agency, 26 Private (other than Railroad), 27 Railroad, 31 State Toll Road, 32 Local Toll Authority,
40 Other Public Instrumentality (Airport), 50 Indian Tribe Nation, 60 Other Federal Agency, 62 BIA, 63-80 other federal agencies,
95 Other [Specify] (2023+), 96 Not in State Inventory, 98 Not Reported, 99 Unknown.
**This field is often unreported, and the pattern depends on the state:** {96,98,99} = 12.9, 19.0, 18.6, 16.9, 16.5, 11.3, 10.7, 11.1, 10.6 %.
Texas is 74-83 % not reported in every year. Michigan is 90-92 % in 2016-17 and about 0 afterwards. California is 35-60 % in 2017-20.
Florida coded 1,184 crashes (3.44 % of the 2016 national total) as 25 "Other Local Agency" in 2016, then 0 % as 25 and 19.8-37.6 % not reported in
2017-20. The not-reported rate is the same for killed persons and survivors (14.06 vs 13.81 %), so this missingness is not severity-related but structural by state.

**SP_JUR [label]:** 0 None (98.9-99.4 %), 1 National Park Service, 2 Military, 3 Indian Reservation (0.71 → 0.33 %), 4 College/University Campus*,
5 Other Federal Properties*, 8 Other, 9 Unknown (0.05-0.19 %). The asterisk in labels 4 and 5 is **UNVERIFIED** in meaning.

**CRSS INT_HWY [label 2019-24]:** 0 No, 1 Yes, 9 Unknown (≤ 0.02 %). The code set is the same in 2016-18 (TVD ≤ 0.011). Evidence that it
marks a crash on an interstate **[xtab]**: weighted, only 0.28 % of INT_HWY = 1 crashes are at an intersection (RELJCT2 = 2), against 23.4 %
for INT_HWY = 0. 24.7 % are at interchange-type junctions, against 2.1 %, and 24.0 % have RELJCT1 = 1, against 3.3 %. Weighted share 7.5 % (2016),
then 9.5-10.7 %. **UNVERIFIED** whether it is based on functional class or on route signing.

**Verdict.** FUNC_SYS **high** (FARS only). NHS **high**. ROUTE **low** across 2022/2023 (use only interstate / US / state / other).
RD_OWNER **low** (heavily state-structured). INT_HWY **medium-high**. The only concept shared by FARS and CRSS is "interstate".

### 4.6 Junction: RELJCT1, RELJCT2, TYP_INT (+ RELJCT1_IM, RELJCT2_IM)

**Codes [label; FARS all years, CRSS 2019+].**
* RELJCT1 ("within interchange area"): 0 No, 1 Yes, 8 Not Reported, 9 Unknown / Reported as Unknown.
* RELJCT2: 1 Non-Junction, 2 Intersection, 3 Intersection-Related, 4 Driveway Access, 5 Entrance/Exit Ramp Related, 6 Railway Grade
  Crossing, 7 Crossover-Related, 8 Driveway Access Related, 16 Shared-Use Path Crossing, 17 Acceleration/Deceleration Lane,
  18 Through Roadway, 19 Other location within Interchange Area, 20 Entrance/Exit Ramp, 98 Not Reported, 99 Unknown.
* TYP_INT: 1 Not an Intersection, 2 Four-Way, 3 T, 4 Y, 5 Traffic Circle, 6 Roundabout, 7 Five Point or More, 10 L, **11 Other Intersection
  Type (new in 2020)**, 98 Not Reported, 99 Unknown.

**How the three fit together [xtab].**
* TYP_INT = 1 for 100 % of crashes with RELJCT2 ∈ {1,4,8,…}. TYP_INT therefore carries information only when RELJCT2 ∈ {2,3}.
* RELJCT2 ∈ {5,17,18,19,20} for 71.9 % (FARS) and 67.5 % (CRSS) of RELJCT1 = 1 crashes, against 0.3-0.4 % when RELJCT1 = 0.

**Not reported / unknown, %**

| | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 |
|---|---|---|---|---|---|---|---|---|---|
| FARS RELJCT1 {8,9} | 0.03 | 0.04 | 0.06 | 0.16 | 0.18 | 0.13 | 0.21 | 0.15 | 0.15 |
| FARS RELJCT2 {98,99} | 0.16 | 0.20 | 0.26 | 0.27 | 0.28 | 0.21 | 0.29 | 0.23 | 0.25 |
| FARS TYP_INT {98,99} | 0.21 | 0.20 | 0.29 | 0.36 | 0.35 | 0.32 | 0.48 | 0.45 | 0.45 |
| **CRSS RELJCT1** (wtd) | 1.83 | **20.06** | **29.34** | **62.02** | **8.01** | 0.30 | 0.03 | 0.09 | 0.12 |
| **CRSS RELJCT2** (wtd) | 0.74 | 2.01 | 6.09 | **28.75** | 0.20 | 0.32 | 0.05 | 0.19 | 0.18 |
| **CRSS TYP_INT** (wtd) | **9.73** | **9.08** | **11.54** | **13.12** | **8.56** | **8.17** | 0.13 | 0.26 | 0.17 |

**CRSS coding and collection breaks.**
* RELJCT1: in 2019, 30 of 60 PSUs had more than 90 % not reported, holding 23,288 of the 34,235 not-reported crashes, and 71 PJs were 100 %
  not reported. **RELJCT1_IM does not exist in 2019.** Even after imputation, the weighted interchange share rises from 1.7 % (2016) through 3.2 and 3.6 %
  (2017-18) to 6.9 % (2020) and 9.7 % (2024), roughly a sixfold change. FARS rises over the same period from 4.3 % to 6.4 %. The CRSS trend
  is mostly a coding artefact.
* RELJCT2: in 2019, 27.9 % of crashes are not reported, and the "Non-Junction" share among all crashes falls from 39.6 % (2018) to 17.1 %. Missing
  values are therefore concentrated among non-junction crashes: 93 % of 2019 crashes with RELJCT2 = 98 have TYP_INT = 1. RELJCT2_IM assigns 66.0 %
  of imputed records to non-junction, against 42.2 % of observed records.
* TYP_INT: among intersection crashes (RELJCT2 = 2), 16.1 % were not reported in 2019 and 12.7 % in 2021, against 0.1 % from 2022. Among
  intersection-related crashes the rates were 32.4 % and 25.7 %, against 0.2-0.3 %. Because of this, the four-way share among all crashes jumps
  from 24.6 % (2021) to 31.9 % (2022) (TVD 0.101).
* RELJCT2 18 "Through Roadway" and 19 jump between 2019 and 2020 (0.37 → 2.16 % and 0.13 → 0.68 %), at the same time as RELJCT1 reporting
  recovers.

**Differential missingness (CRSS, weighted).**
* TYP_INT in 2016-2021: 8.6-15.0 % for O and C crashes, 5-9 % for B, 4.3-7.6 % for A and **1.9-4.1 % for K**. Intersection type is much
  more often missing for low-severity crashes, which biases any TYP_INT × severity comparison in those years.
* RELJCT1 in 2017-2018: O 18.9/28.2 %, C 25.3/35.7 %, K 12.5/20.8 %.
* FARS: killed vs survivors 0.24 vs 0.07 % (RELJCT2) and 0.34 vs 0.22 % (TYP_INT).

**Verdict.**
* FARS RELJCT1/RELJCT2/TYP_INT: **high**.
* CRSS RELJCT2: **medium**. Use RELJCT2_IM, or a coarse intersection yes/no, and flag 2019.
* CRSS TYP_INT: **low** before 2022.
* CRSS RELJCT1: **unusable 2017-2020**, and its trend is unreliable throughout.

### 4.7 Relation to trafficway: REL_ROAD

**Codes [label]:** 1 On Roadway, 2 On Shoulder, 3 On Median, 4 On Roadside, 5 Outside Trafficway, 6 Off Roadway-Location Unknown,
7 In Parking Lane/Zone, 8 Gore, 10 Separator, 11 Continuous Left-Turn Lane, **12 Pedestrian Refuge Island or Traffic Island (new in 2018,
0.04-0.14 %)**, 98 Not Reported, 99 Unknown. The categories that code 12 previously fell into are **UNVERIFIED**.
Unknown {98,99}: FARS 0.18-0.31 %; CRSS weighted 0.01-0.10 %. Code 6 (partial): FARS 0.15-0.44 %.
FARS killed vs survivors: 0.24 vs 0.08 %. CRSS U-severity: 0.48 % against ≤ 0.17 % for the other strata.
Distribution (FARS): on roadway 60.5 → 64.3 %, roadside 30.5 → 27.5 %. CRSS weighted: on roadway 77.7-80.1 %, roadside 11.6-15.1 % (15.1 % in 2020).
**Verdict: high.**

### 4.8 Work zone: WRK_ZONE

**Codes [label, both sources]:** 0 None, 1 Construction, 2 Maintenance, 3 Utility, 4 Work Zone, Type Unknown. There is **no "unknown whether in
a work zone" code**, so 0 combines "no work zone" with "not recorded" (**UNVERIFIED** how undocumented cases are coded).
Any work zone: FARS 1.98-2.28 %; CRSS 1.48-2.26 % (unweighted). Code 4: FARS 0.49 → 0.92 % (2021) → 0.69 %; CRSS 1.14 % in 2016, otherwise 0.49-0.95 %.
**Verdict: medium.** Prevalence is reliable as "work zone noted", but type is unreliable (code 4 is 25-53 % of work-zone crashes).

### 4.9 Manner of collision: MAN_COLL, MANCOL_IM

**Codes [label]:** 0 "Not a Collision with Motor Vehicle In-Transport" (FARS 2016-18), reworded in 2019 to "The First Harmful Event was Not a
Collision with a Motor Vehicle in Transport", which makes explicit the reference to the first harmful event and keeps the same meaning
(the share of code 0 is unchanged at 60.5-61.8 %). 1 Front-to-Rear, 2 Front-to-Front, 6 Angle, 7 Sideswipe - Same Direction,
8 Sideswipe - Opposite Direction, 9 Rear-to-Side, 10 Rear-to-Rear, 11 Other, 98 Not Reported, 99 Unknown. Codes 3-5 never occur.
**Consistency with the first harmful event [xtab]:** MAN_COLL = 0 for 100 % of crashes whose first harmful event is not a motor vehicle in transport,
except HARM_EV 54 and 55. Those are events involving a motor vehicle in transport, and MAN_COLL is coded for them: 283 of 303 such FARS
exceptions and 1,335 of 1,354 CRSS exceptions are HARM_EV 54. Only 7 FARS and 6 CRSS single-vehicle crashes have MAN_COLL 1-11.
Unknown: FARS 0.20-0.34 %, CRSS weighted 0.18-0.63 %. There is no severity gradient (CRSS O 0.35, K 0.30, U 1.06 %; FARS killed 0.27,
survivors 0.30 %).
**Trend, CRSS weighted (MANCOL_IM):** rear-end 32.1-33.1 % in 2016-19, then 27.8 % (2020) and 28.2-29.0 % in 2021-24. Sideswipe in the same direction rises
from 9.9 % to 13.4 %. FARS rear-end is stable at 6.8-7.5 %. The step in 2020 coincides with COVID and with a reduction in the PJ sample
(305 PJs in 2019, 275 in 2020). **UNVERIFIED** which of these explains it.
**Verdict: high.**

### 4.10 First harmful event: HARM_EV, EVENT1_IM

**Codes [label]:** 56 codes (listed in the grouping in section 9). Code-set changes:
* **91 "Unknown Object Not Fixed" and 93 "Unknown Fixed Object" first appear in 2017** in both sources. They are absent in 2016.
* **98 "Harmful Event, Details Not Reported" first appears in 2019.**
* 72 was reworded in 2018 from "Cargo/Equipment Loss or Shift (harmful to this vehicle)" to "Cargo/Equipment Loss, Shift, or Damage [harmful]".
  **The new wording adds "Damage" and may widen the scope**, although the code is rare (0.01-0.11 %).
* 99 "Unknown" became "Reported as Unknown" (cosmetic).

Unknown {98,99}: FARS 0.05-0.23 %, CRSS weighted 0.04-0.11 %. EVENT1_IM keeps codes 91 and 93.
Grouped trends (FARS): rollover 8.9 % (2016) → 6.4 % (2024); pedestrian 16.2 → 18.2 %; pedalcyclist 2.4 → 3.0 %; fixed object 27.5-30.6 %.
CRSS weighted: motor vehicle in transport 66.8-71.8 %, fixed object 13.8-17.4 %, animal 4.6-5.8 %, pedestrian 1.0-1.3 %.
**Verdict: high.** Group the codes (section 9) so that the 2016 absence of 91 and 93 does not matter.

### 4.11 Crash-level counts

All checks below hold in 100 % of crashes in every source-year unless a figure is given **[xtab]**:

| Variable | Data-verified definition |
|---|---|
| VE_FORMS | = number of `vehicle` records = motor vehicles in transport |
| PVH_INVL | = number of `parkwork` records = parked or working vehicles |
| VE_TOTAL | = VE_FORMS + PVH_INVL |
| PERMVIT | = persons with PER_TYP ∈ {1 driver, 2 passenger, 9 unknown occupant type} = occupants of motor vehicles in transport |
| PERNOTMVIT | = all other person records (non-motorists and occupants of non-transport vehicles, PER_TYP 3) |
| PEDS | = non-motorists = PER_TYP ∈ {4,5,6,7,8,10,19} in 2016-19 and 2022-24. In 2020-21, code 8 was temporarily split into **11/12/13** (personal conveyance: motorized, non-motorized, unknown), and PEDS counts those too. It excludes PER_TYP 3 |
| PERSONS (FARS only) | = PERMVIT + occupants of non-transport vehicles = person records with VEH_NO > 0 (100 %); = PERMVIT in 99.2-99.3 % |
| FATALS (FARS only) | = number of person records with INJ_SEV = 4 (100 %). FATALS = 1 in 92.9-93.5 % of crashes |
| NUM_INJ (CRSS only) | = number of persons with INJ_SEV ∈ {1,2,3,4,5}, **including fatalities** (100 % when < 98); 98 = "No Person involved in the Crash" **[label]**; 99 = "All Persons in Crash are Unknown If Injured" (equals "all persons have INJ_SEV = 9" in 100 %) |
| NO_INJ_IM (CRSS) | = number of persons with `person`.INJSEV_IM ∈ {1..5} (100 %). It differs from NUM_INJ in 2.6-4.0 % of crashes, including 484-1,178 per year where NUM_INJ was not 99. Of these, 13-24 per year are 98 'no person' recoded to 0; the rest come from imputing unknown persons |

There are no unknown codes in the count fields apart from NUM_INJ 98/99. The FARS maxima include outliers, for example VE_FORMS 130 in 2021
and PERMVIT 133 (pile-ups). Use them truncated or on a log scale.
**Timing:** VE_FORMS, PVH_INVL, PEDS, PERMVIT and PERNOTMVIT describe involvement (crash circumstance). FATALS and NUM_INJ are **outcomes**.
PERMVIT is mechanically linked to the chance that "any person" reaches a given severity.

### 4.12 Crash severity (outcome; recorded here because the missingness analyses are stratified by it)

CRSS MAX_SEV **[label 2019-24]**: 0 No Apparent Injury (O), 1 Possible (C), 2 Suspected Minor (B), 3 Suspected Serious (A), 4 Fatal (K),
5 Injured, Severity Unknown, 6 Died Prior to Crash*, 8 No person involved, 9 Unknown/Not Reported.
* Derivation [xtab]: MAX_SEV = maximum person INJ_SEV over codes 0-4 (100 %). MAX_SEV = 9 exactly when every person has INJ_SEV = 9 (100 %).
  MAX_SEV = 5 exactly when an injured-severity-unknown person is present and all known persons are O.
* Unknown (9), unweighted: 1.52-1.86 %. Code 5: 0.71 % (2016) → 0.19-0.25 % (2022-24).
* MAXSEV_IM recomputes severity from imputed person severities. It changes **known** MAX_SEV values in 286-686 crashes per year, mostly
  0 → 1 (1,973 pooled) and 0 → 2 (738), and it keeps codes 5, 6 and 8.

### 4.13 Alcohol (CRSS ALCOHOL and ALCHL_IM; note only)

**Codes [label 2019-24]:** 1 Alcohol Involved, 2 No Alcohol Involved, 8 No applicable person, 9 Reported as Unknown.
**Coding break in 2019:** unknown (9) is 14.0, 14.4, 13.1 % in 2016-18, then **31.8 %** (2019) and 39.0-39.8 % (2020-24), with "No" falling from
80-82 % to 55-56 %. ALCHL_IM imputes every 9 and every 8, mostly to 2 (226 of 227 code-8 crashes).
Unknown is **strongly linked to severity**: weighted pooled O 28.1, C 26.1, B 25.0, A 28.7, **K 47.3, U 81.8 %**.
The imputed "alcohol involved" share is 4.4 % among imputed crashes against 5.6 % among observed. Whether the imputation model conditions on severity is
**UNVERIFIED**. Leave the details to the alcohol audit, but do not use crash-level ALCOHOL across the 2018/2019 boundary.

### 4.14 Crash-related factors: CF1-CF3 (2016-19) and the crashrf table (2020-24)

**Codes [label; FARS 2016-24, CRSS 2019-24]:** 0 None, renamed "None Noted" in 2022. The factors are 1-7 road and maintenance codes (1 Inadequate Warning…,
2 Shoulder Design, 3 Other Maintenance/Construction-Created Condition, 4 No/Obscured Pavement Marking, 5 Surface Under Water, 6 Inadequate
Construction/Poor Design, 7 Surface Washed Out), **10 Emergency Vehicle Related (new in 2021)**, 12 Distracted Driver of a Non-Contact Vehicle,
13 Aggressive Driving/Road Rage by Non-contact Vehicle Driver (**split in 2023 into 102 Aggressive Driving and 103 Road Rage**),
14 Motor Vehicle struck by falling cargo…, 15 Non-occupant struck by falling cargo…, 16 Non-occupant struck vehicle,
17 Vehicle set-in-motion by non-driver (2022: "Stopped Vehicle Set in Motion by Non-Driver"), 18 Date of Crash and Date of EMS Notification
not the same day, 19 Recent/Previous Crash Scene Nearby, 20 Police Pursuit Involved, 21 Within Designated School Zone, 22 Speed Limit is a
Statutory Limit…, 23 Indication of a Stalled/Disabled Vehicle, 24 Unstabilized Situation Began and All Harmful Events Occurred Off of the Roadway,
25 Toll Booth/Plaza Related, 26 "Backup Due to Prior Non-Recurring Incident" (renamed in 2019 to "Prior Non-Recurring Incident"), 27 Backup Due to Prior
Crash, 28 "Backup Due to Regular Congestion" (renamed in 2019 to "Regular Congestion"), 30 Obstructed Crosswalks and 31 Related to a Bus Stop (both
first seen in 2019), and 99 Unknown (≤ 2019) / 999 Reported as Unknown (FARS 2020-21, CRSS 2020).
The 2019 rewording of 26 and 28 drops the word "Backup" and so may widen the definitions (**meaning change UNVERIFIED**). Crash-level code 28 in FARS stays
at 0.18-0.27 % throughout.
CRSS uses only a subset: codes 1, 2, 4, 6, 18 and 22 never occur, so they are FARS-only items.

**Structure.** CF slots are filled in order: CF2 > 0 never occurs with CF1 = 0, and 99 never occurs alongside a real factor. In crashrf, 0 never
co-occurs with another code. A crash with more than one factor has ≥ 2 CF slots in 0.60 % of FARS crashes (2016-19), and ≥ 2 crashrf rows in 0.71 %
(2020-24). The figures for CRSS are 0.21 % and 0.33 %.
Before 2020 the limit was three slots; 13 FARS crashes in 2020-24 had 4 rows.

**Unknown handling changed.** FARS crash-level unknown (99/999) was 0.49, 1.16, 0.80, 0.74, 0.96, 0.81 % in 2016-21 and **0 from 2022**, when "None"
became "None Noted". From 2022 onwards the "none" category also contains crashes that would earlier have been "unknown". CRSS unknown was already
≤ 0.12 %.

**Crash-level prevalence, harmonised (any slot or row):**

| FARS % | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 |
|---|---|---|---|---|---|---|---|---|---|
| police pursuit (20) | 1.03 | 1.06 | 1.06 | 1.07 | 1.29 | 1.10 | 1.24 | 1.24 | 1.38 |
| struck by cargo/object from MV (14) | 2.08 | 2.14 | 2.18 | 2.17 | 2.09 | 2.38 | 2.44 | 2.39 | 2.38 |
| stalled/disabled vehicle (23) | 0.96 | 0.93 | 1.03 | 1.15 | 1.06 | 1.30 | 1.22 | 1.25 | 1.11 |
| any factor noted | 6.31 | 6.48 | 6.80 | 6.80 | 6.87 | 7.24 | 7.66 | 7.47 | 7.78 |

CRSS weighted "any factor" is 3.2-3.7 % (2016-19) and 3.8-4.4 % (2020-24). Congestion (28) was 1.46 % in 2016 and 1.16 % in 2017, then 0.21-0.83 %.
The move from CF1-3 to crashrf does not produce a step in individual codes. The rise in "any factor" includes the new code 10 (0.3-0.8 % of rows from 2021).
**Verdict: medium.** Use flags for each specific code meaning "noted" vs "not noted".

### 4.15 State and region

FARS STATE: the 50 states and DC, with codes 1-56 matching the US state FIPS **[label]**. There is no Puerto Rico. CRSS REGION **[label 2019-24]** lists its
states: 1 Northeast (PA, NJ, NY, NH, VT, RI, MA, ME, CT), 2 Midwest (OH, IN, IL, MI, WI, MN, ND, SD, NE, IA, MO, KS), 3 South (MD, DE,
DC, WV, VA, KY, TN, NC, SC, GA, FL, AL, MS, LA, AR, OK, TX), 4 West (MT, ID, WA, OR, CA, NV, NM, AZ, UT, CO, WY, AK, HI). These are the four
Census regions, and FARS STATE can be mapped onto them exactly (section 9).
The CRSS 2016 sample is a transition year: 53 PSUs, and the unweighted Northeast share is 9.0 % against 12.0-14.0 % in later years (TVD 2016→2017 = 0.061).
FARS `acc_aux`.A_REGION is **not** the Census region. It has 10 groups (UNVERIFIED meaning; possibly administrative regions), and Connecticut
appears in two of them in different years.

### 4.16 School bus and rail crossing

SCH_BUS **[label]:** 0 No, 1 Yes, with no unknown code. FARS 0.14-0.31 %, CRSS 0.26-0.66 % (unweighted), and in both sources 2020 is the lowest year.
Verification [xtab]: 89.6 % (FARS) and 84.0 % (CRSS) of SCH_BUS = 1 crashes involve a vehicle with BODY_TYP 50 "School Bus", BUS_USE 1
"School" or SPEC_USE 2 "Vehicle Used for School Transport". **0.0 %** of SCH_BUS = 0 crashes do. SCH_BUS therefore means "school-bus-related",
and about 10-16 % of these crashes have no school-bus vehicle in transport among the records (presumably the bus was not a contact vehicle; **UNVERIFIED**).

FARS RAIL (string, 7 characters): "0000000" Not Applicable (99.59-99.72 %), "9999999" Unknown (0.00-0.03 %); other values are crossing
identifiers. Of crashes with a crossing ID, 85.0 % have RELJCT2 = 6 "Railway Grade Crossing" and 77.6 % have HARM_EV = 10 "Railway Vehicle".
CRSS has no RAIL; use RELJCT2 = 6 and HARM_EV = 10 instead.

### 4.17 Auxiliary-table traps (unlabelled acc_aux)

* FARS `acc_aux`.A_WEATHER is a one-to-one recode of WEATHER (1,2,3,4,6,10-15,99, with 98 and 99 both mapped to 99). CRSS A_WEATHER exists only from 2020
  and recodes WEATHR_IM.
* FARS A_RU = 1 Rural, 2 Urban, and 3 for RUR_URB ∈ {6,8,9} (100 % match).
* **A_LT is not light condition.** It does not match LGT_COND (for example, 25,322 daylight crashes have A_LT = 1). It matches large-truck involvement:
  42,078 of 42,098 A_LT = 1 crashes, and only 609 of 283,824 A_LT = 2 crashes, have a vehicle with BODY_TYP 60-79 (labels: medium/heavy trucks).
  Treat it as "large truck involved" (**xtab-verified**, ≥ 99.8 % concordance).

---

## 5. Applying 2019+ labels to CRSS 2016-2018

| Check | Result |
|---|---|
| Codes observed in 2016-18 that are missing from the CRSS 2019 label set | none for any accident variable in this domain, apart from WEATHER2 = 99 (1 crash in 2018; not labelled in CRSS 2019 or FARS 2016-18 WEATHER2; it is labelled "Unknown" in WEATHER1, so meaning **UNVERIFIED**), CF2 = 16 and CF3 = 19, 24, 28 (all labelled in CF1 because the three slots share one code list), and NUM_INJ counts 13-29 (plain counts) |
| Codes missing from the same-year FARS label set | none (shared variables) |
| TVD 2018→2019 | ≤ 0.016 for HOUR, DAY_WEEK, MONTH, LGT_COND, WEATHER, REL_ROAD, WRK_ZONE, MAN_COLL, HARM_EV, INT_HWY, URBANICITY, SCH_BUS, MAX_SEV, STRATUM. MINUTE is 0.024, but it has 60 categories and its TVD between labelled years is 0.018-0.022. These are as small as differences between labelled years (2022→2023: 0.000-0.022 for the same variables) |
| Exceptions | RELJCT1 (TVD 0.326), RELJCT2 (0.231), ALCOHOL (0.187) and TYP_INT. These are the 2019 reporting breaks of sections 4.6 and 4.13: the size of the not-reported category changes, but the codes keep their meaning |
| Severity coding | MAX_SEV = maximum INJ_SEV, and NUM_INJ = count of INJ_SEV 1-5, hold in 100 % of 2016-18 crashes just as in 2019-24 |

**Conclusion.** The CRSS 2019 labels, and for shared variables the same-year FARS labels, apply to CRSS 2016-2018 with high confidence.

## 6. CRSS original vs imputed (*_IM) variables

| Pair | % of crashes imputed (unweighted, 2016→2024) | Known values changed? | Imputed share by MAX_SEV (weighted pooled) | Imputed vs observed distribution |
|---|---|---|---|---|
| HOUR→HOUR_IM | 0.16, 0.28, 0.47, 0.62, 0.61, 0.64, 0.70, 0.69, 0.66 | never | O 0.47, C 0.20, B 0.34, A 0.31, K 1.29, U 9.57 | more night hours (12.4 % vs 8.0 % at 0-5 h) |
| MINUTE→MINUTE_IM | same as HOUR | never | same | — |
| DAY_WEEK→WKDY_IM | 0 | never | 0 | identical |
| LGT_COND→LGTCON_IM | 0.66, 0.78, 1.04, 0.99, 0.96, 0.44, 0.36, 0.42, 0.45 | never (6 and 7 kept) | O 0.65, C 0.25, B 0.24, A 0.25, K 0.49, U 12.11 | dark-unlighted 25.4 % vs 10.4 % |
| WEATHER→WEATHR_IM | 3.40, 4.49, 5.82, 6.48, 5.28, 2.95, 3.11, 3.45, 3.13 | never | O 4.14, C 2.57, B 5.01, A 4.23, K 3.27, U 24.23 | close (clear 71.8 vs 72.9 %) |
| MAN_COLL→MANCOL_IM | 0.16-0.61 | never | 0.23-0.35, U 1.06 | far fewer non-collision (7.8 % vs 30.2 %), more angle (37.6 % vs 22.2 %) |
| HARM_EV→EVENT1_IM | 0.02-0.11 | never (91 and 93 kept) | ≤ 0.09, U 0.46 | — |
| RELJCT1→RELJCT1_IM | 1.98, 21.38, 30.96, **absent 2019**, 7.28, 0.28, 0.03, 0.09, 0.08 | never | O 7.45, C 9.98, K 4.39 | similar (5.8 % vs 6.1 % yes) |
| RELJCT2→RELJCT2_IM | 0.74, 2.08, 6.10, **27.91**, 0.16, 0.30, 0.05, 0.18, 0.14 | never | 3.85-5.38, U 6.71 | non-junction 66.0 % vs 42.2 % |
| MAX_SEV→MAXSEV_IM | 1.52-1.86 (code 9) | **yes**: 286-686 crashes per year | U 92.08 | A 5.2 % vs 2.5 % among imputed |
| NUM_INJ→NO_INJ_IM | 1.52-1.86 (code 99) | **yes**: 484-1,178 per year | — | recount of INJSEV_IM |
| ALCOHOL→ALCHL_IM | 14.08, 14.46, 13.17, **31.88**, 39.83, 39.04, 39.77, 39.22, 39.14 | 7 cases (1→2) in 2020-21 | O 28.15, K 47.39, U 81.87 | yes 4.4 % vs 5.6 % |

**Recommendations.**
1. **Weighted national descriptive estimates** of environment distributions: use the *_IM version. These are NHTSA's single imputations, so the
   variance is understated by roughly the imputed fraction, and the imputed share should be reported alongside the estimate.
2. **Severity models with an environment covariate:** use the original variable with an explicit "unknown" level, or multiple imputation
   conditioned on the outcome. Use *_IM only as a sensitivity analysis. It is **UNVERIFIED** whether NHTSA's imputation model conditions on
   MAX_SEV. If it does not, imputed values dilute associations; if it does, they reproduce them. Either way the effect is small where imputation is
   below 1 % (HOUR, LGT_COND, MAN_COLL, HARM_EV) and material for WEATHER (3-6.5 %, and 24 % in the U stratum), RELJCT1/2 and ALCOHOL.
3. **Outcome:** model MAX_SEV with codes 5 and 9 as missing, and present MAXSEV_IM as a sensitivity analysis. Do not mix the two, because MAXSEV_IM
   also changes known values.
4. For RELJCT1 in 2017-2020, use neither version.

## 7. Differential missingness by severity: summary

| Variable | FARS killed / survivors (% unknown) | FARS FATALS 1 / ≥ 2 | CRSS weighted O / C / B / A / K / U |
|---|---|---|---|
| HOUR | 0.72 / 0.18 | 0.75 / 0.56 | 0.47 / 0.20 / 0.34 / 0.31 / 1.29 / 9.57 |
| LGT_COND | 0.59 / 0.14 | 0.61 / 0.51 | 0.65 / 0.25 / 0.24 / 0.25 / 0.49 / 12.11 |
| WEATHER | 5.44 / 4.47 | 5.57 / 4.74 | 4.14 / 2.57 / 5.01 / 4.23 / 3.27 / 24.23 |
| RELJCT2 | 0.24 / 0.07 | 0.24 / 0.19 | 4.71 / 3.98 / 3.85 / 4.79 / 5.38 / 6.71 (dominated by 2019) |
| TYP_INT | 0.34 / 0.22 | 0.35 / 0.27 | 7.15 / 8.61 / 4.35 / 3.70 / 1.96 / 4.76 |
| RELJCT1 | 0.13 / 0.03 | 0.13 / 0.11 | 14.0 / 16.8 / 13.9 / 13.3 / 10.1 / 11.2 |
| REL_ROAD | 0.24 / 0.08 | 0.26 / 0.16 | 0.04 / 0.04 / 0.03 / 0.05 / 0.17 / 0.48 |
| MAN_COLL | 0.27 / 0.30 | 0.25 / 0.38 | 0.35 / 0.26 / 0.23 / 0.27 / 0.30 / 1.06 |
| RD_OWNER | 14.06 / 13.81 | 14.01 / 14.04 | n/a |
| ALCOHOL (CRSS) | — | — | 28.1 / 26.1 / 25.0 / 28.7 / 47.3 / 81.8 |

Persons with unknown injury severity in FARS (n = 12,361) are in crashes with higher unknown rates for every variable: HOUR 1.93 %, LGT_COND 2.74 %,
WEATHER 8.53 %, RD_OWNER 20.95 %, RELJCT2 2.49 %.

## 8. Cross-cutting findings

1. **Unknown crash severity in CRSS marks a poorly documented report.** Crashes coded U have 5-50 times the unknown rate of the other strata for
   HOUR, LGT_COND and WEATHER. Dropping U crashes, or dropping unknown covariates, removes the same records twice.
2. **In FARS, the time and light of fatal crashes are less often known than for survivors' crashes,** about 4 times as often missing. The cause is that
   single-vehicle, rural, night crashes are found after the fact. A complete-case analysis under-represents exactly these crashes.
3. **Missingness depends on the state** for FARS WEATHER (VA, KS, plus CO and PA until 2020), RD_OWNER (TX, MI, CA, FL) and ROUTE (CA, KS, WI).
   Any analysis that conditions on these variables needs state fixed effects or exclusion of those states.
4. **CRSS 2017-2021 junction data are compromised** (RELJCT1 not reported up to 62 % in 2019; TYP_INT not reported among intersection crashes
   until 2021). Prefer FARS for junction analyses, and restrict CRSS to RELJCT2 groups or to years ≥ 2022 for TYP_INT.
5. **Label wording is mostly cosmetic.** The 9/99 relabel "Unknown" → "Reported as Unknown" (FARS 2018), FUNC_SYS (2023) and MAN_COLL 0 (2019) are
   cosmetic. The changes that matter are ROUTE (2023 restructure), HARM_EV 72 (2018, scope), CF 26/28 (2019, scope; UNVERIFIED) and crash factor 0 "None" →
   "None Noted", which absorbed "unknown" from 2022.
6. **New codes:** HARM_EV 91/93 (2017), HARM_EV 98 (2019), REL_ROAD 12 (2018), TYP_INT 11 (2020), CRASHRF 10 (2021), CRASHRF 102/103 (2023),
   ROUTE 0/10-13/95/96/99 (2023). Person PER_TYP 11-13 existed only in 2020-21 and affect the definition of PEDS.
7. **Not the same concept in the two sources:** CRSS URBANICITY (PSU) vs FARS RUR_URB (road). CRSS INT_HWY vs FARS FUNC_SYS/ROUTE (close, but the basis is
   UNVERIFIED). There is no CRSS equivalent of FUNC_SYS, RD_OWNER, NHS, SP_JUR, RAIL or STATE.
8. **Real-world disruptions:** 2020 (COVID) shifts the MONTH distribution and the CRSS collision mix. CRSS 2016 is a transition sample (53 PSUs).
   The CRSS PJ sample shrank from 380 (2018) to 305 (2019) to 261-275 (2020-24).

## 9. Harmonised definitions (implementation recipes)

Notation: `NA` means missing (never 0). "Both" means FARS and CRSS with an identical recipe. Use `load_table(src, 'accident', columns=[...])`.

| Name | Level | Recipe | Timing |
|---|---|---|---|
| `crash_hour` | crash | HOUR; 0-23 valid, 99 → NA (both). CRSS estimates: HOUR_IM | pre-crash |
| `time_of_day` | crash | from `crash_hour`: 0-5 night, 6-9 am peak, 10-15 midday, 16-19 pm peak, 20-23 evening; NA if hour NA | pre-crash |
| `day_of_week` / `weekend` | crash | DAY_WEEK 1 = Sun … 7 = Sat; weekend = {1,7}; no NA codes | pre-crash |
| `month`, `season` | crash | MONTH 1-12; season DJF/MAM/JJA/SON; FARS also DAY | pre-crash |
| `light` | crash | LGT_COND: 1 daylight; 4,5 dawn_dusk; 3 dark_lighted; 2 dark_unlighted; 6 dark_unknown_lighting; 7, 8, 9 → NA (7 is 0.01-0.07 %). CRSS estimates: LGTCON_IM, same map | pre-crash |
| `weather` | crash | accident.WEATHER (all years): 1 clear; 10 cloudy; 2 rain; 3,4,11,12 snow_sleet_ice; 5 fog_smoke; 6,7,8 other_adverse; 98, 99 → NA. `adverse_weather` = not {1,10}. Optionally `any_precip_any_row` = any WEATHER1/WEATHER2 (≤ 2019) or any weather-table row (≥ 2020; CRSS 2020 column WEATHERCODE) in {2,3,4,11,12} | pre-crash |
| `rural_urban_road` | crash (FARS) | RUR_URB 1 rural, 2 urban, 6/8/9 → NA. Include year terms (within-state drift) | pre-crash |
| `urbanicity_psu` | PSU (CRSS) | URBANICITY 1 urban PSU, 2 rural PSU; not comparable with the row above | design / area |
| `func_class` | crash (FARS) | FUNC_SYS 1 interstate, 2 freeway_expressway, 3 other_principal_arterial, 4 minor_arterial, 5,6 collector, 7 local, 96/98/99 → NA | pre-crash |
| `interstate` | crash, both | FARS: FUNC_SYS == 1 → 1; 2-7 → 0; 96/98/99 → NA. CRSS: INT_HWY 1 → 1, 0 → 0, 9 → NA | pre-crash |
| `nhs` | crash (FARS) | NHS 0/1; 9 → NA | pre-crash |
| `route_group` | crash (FARS) | ROUTE ≤ 2022: 1 interstate, 2 us_hwy, 3 state_hwy, 4-8 other_local, 9 NA. ≥ 2023: 1, 2, 3 as before; 0, 4, 5, 6, 10, 11, 12, 13, 95 other_local; 96, 99 NA | pre-crash |
| `road_owner` | crash (FARS) | RD_OWNER 1, 11, 21, 31 state; 2 county; 3 town; 4 city; 12, 25, 32 other_local; 50, 60-80 federal_tribal; 26, 27 private_rail; 40, 95 other; 96/98/99 → NA. Use only with state fixed effects | pre-crash |
| `junction` | crash, both | RELJCT2: 1 non_junction; 2 intersection; 3 intersection_related; 4, 8 driveway; 5, 17, 18, 19, 20 interchange_ramp; 6 rail_crossing; 7, 16 other_junction; 98/99 → NA. CRSS 2019: RELJCT2_IM (flag the year) | pre-crash |
| `at_intersection` | crash, both | 1 if RELJCT2 in {2,3}; 0 if in {1,4,5,6,7,8,16-20}; NA if 98/99 | pre-crash |
| `interchange_area` | crash | RELJCT1 0/1; 8/9 → NA. CRSS: **set NA for 2017-2020** | pre-crash |
| `intersection_type` | crash | only where `at_intersection` = 1: TYP_INT 2 four_way, 3 t, 4 y, 5,6 roundabout_circle, 7 five_plus, 10 l, 11 other; 98/99 (or 1) → NA. CRSS: use years ≥ 2022 only | pre-crash |
| `rel_road` | crash, both | REL_ROAD 1, 11 on_roadway; 2 shoulder; 3, 10, 12 median_island; 4 roadside; 5 outside_trafficway; 7 parking_lane; 8 gore; 6 off_roadway_unknown; 98/99 → NA | crash circumstance |
| `work_zone` | crash, both | WRK_ZONE 1-4 → 1, 0 → 0 ("not noted"); type 1/2/3, with 4 → type NA | pre-crash |
| `collision_manner` | crash, both | MAN_COLL 0 not_mv_collision; 1 rear_end; 2 head_on; 6 angle; 7 sideswipe_same; 8 sideswipe_opp; 9, 10, 11 other_mv; 98/99 → NA. CRSS estimates: MANCOL_IM | crash circumstance |
| `first_harmful_event` | crash, both | HARM_EV: 1 rollover; 2, 3, 5, 6, 7, 44, 51, 72 other_noncollision; 12, 54, 55 mv_in_transport; 14 parked_mv; 8 pedestrian; 9 pedalcyclist; 15 other_nonmotorist; 10, 74 railway; 11, 49 animal; 16, 18, 45, 73, 91 object_not_fixed; 17, 19, 20, 21, 23, 24, 25, 26, 30-35, 38-43, 46, 48, 50, 52, 53, 57, 58, 59, 93 fixed_object; 98/99 → NA (grouping is the analyst's, based on labels) | crash circumstance |
| `n_veh_transport`, `n_parked_veh`, `n_nonmotorists`, `n_occupants_mvit`, `n_persons` | crash, both | VE_FORMS, PVH_INVL, PEDS, PERMVIT, PERMVIT + PERNOTMVIT; `single_vehicle` = VE_FORMS == 1 | crash circumstance |
| `fatalities` (FARS), `n_injured_incl_fatal` (CRSS) | crash | FATALS; NUM_INJ with 98 → 0 (no person) and 99 → NA | outcome |
| `crash_max_sev` | crash (CRSS) | MAX_SEV 0-4 → O/C/B/A/K; 5, 9 → NA; 6, 8 → exclude. Sensitivity: MAXSEV_IM | outcome |
| `cf_<code>_noted` | crash, both | ≤ 2019: any of CF1/CF2/CF3 == code; ≥ 2020: any crashrf row == code. 0 = "not noted" (includes unknown; 99/999 cannot be kept separate after 2021). Code 13 = {13} (≤ 2022) ∪ {102,103} (≥ 2023); code 10 only ≥ 2021 | crash circumstance |
| `census_region` | crash, both | CRSS REGION 1-4. FARS STATE → 1: 9, 23, 25, 33, 34, 36, 42, 44, 50; 2: 17, 18, 19, 20, 26, 27, 29, 31, 38, 39, 46, 55; 3: 1, 5, 10, 11, 12, 13, 21, 22, 24, 28, 37, 40, 45, 47, 48, 51, 54; 4: 2, 4, 6, 8, 15, 16, 30, 32, 35, 41, 49, 53, 56 | pre-crash |
| `school_bus_related` | crash, both | SCH_BUS 0/1 | crash circumstance |
| `rail_crossing` | crash | FARS: RAIL not in {"0000000", "9999999"} → 1, "0000000" → 0, "9999999" → NA. Both sources: RELJCT2 == 6 | pre-crash |

## 10. Open questions and UNVERIFIED items

* Why the FARS urban share rises within states in steps (for example NY and DE between 2017 and 2018). A change in road-inventory urban boundaries is suspected.
* Whether CRSS INT_HWY is based on functional class or on route signing. Its relationship to FARS FUNC_SYS = 1 cannot be tested because the two sources cannot be linked.
* What WRK_ZONE = 0 contains when the work-zone status was not documented. There is no unknown code.
* Which categories absorbed REL_ROAD 12 before 2018, HARM_EV 91/93 before 2017 and HARM_EV 98 before 2019.
* Whether the 2019 rewording of CF 26/28 ("Backup due to …" → "…") and the 2018 rewording of HARM_EV 72 (adding "Damage") widened the definitions.
* Meaning of the "*" in SP_JUR labels 4 and 5 and in MAX_SEV/INJ_SEV 6 "Died Prior to Crash*".
* Meaning of WEATHER2 = 99 (1 CRSS crash in 2018; no label).
* Whether NHTSA's CRSS imputation models (HOUR_IM, LGTCON_IM, WEATHR_IM, RELJCT*_IM, ALCHL_IM) condition on crash severity.
* Cause of the CRSS step in rear-end share in 2020 (32 % → 28 %, persisting through 2024): COVID traffic, or the PJ sample change from 305 to 275 PJs.
* Cause of the CRSS RELJCT1 not-reported surge in 2017-2020, and why RELJCT1_IM is absent in 2019.
* Meaning of FARS `acc_aux`.A_REGION (10 groups).
