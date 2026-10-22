# Audit appendix: auxiliary (derived) tables acc_aux, veh_aux and per_aux (FARS and CRSS, 2016-2024)

Scope: the three NHTSA auxiliary files in both sources, for every year from 2016 to 2024. These are the crash-level
`acc_aux`, the vehicle-level `veh_aux` and the person-level `per_aux`. The audit covers every `A_*` variable plus
`BIA`, `SPJ_INDIAN`, `INDIAN_RES`, `TRACT`, `CENSUS_2020_TRACT_FIPS`, and the key and pass-through columns.

Status: audit only. No data or source code was modified. Every number below was computed from the typed Parquet cache
(`data/interim/{FARS|CRSS}/{table}/{year}.parquet`) through `nhtsa_stats.ingestion.cache.load_table`, or from
`outputs/audit/*.csv`. The scripts are listed in section 11.

The archives contain no documentation for the auxiliary files, and the aux tables have no `*NAME` label columns in
any source or year. `outputs/audit/codebook.csv` therefore holds no rows for them. **The meaning of every code given
below was reconstructed from the data.** Each aux table was joined 1:1 to its main table, each aux variable was
cross-tabulated against labelled source fields, and an explicit rule was written. The rule's per-year agreement with
the aux value is reported. The official NHTSA label wording is not in the archive. Where this appendix gives a "name"
for a code (for example "weekend"), that name is a description of the reconstructed rule, not a quoted label.

---

## 1. Purpose and scope

The `A_*` variables are NHTSA's pre-computed analytic recodes, used for example in Traffic Safety Facts tables. They
are attractive as harmonised analytic variables because they look identical across years and, for the shared ones,
across FARS and CRSS. This appendix decides, variable by variable, whether that appearance is true. For each variable
it records:

* availability by source-year;
* the observed codes, and the meaning of each code reconstructed by cross-tabulation, with the agreement rate of the
  reconstruction rule;
* definitional breaks, meaning a change in the rule, the universe or the source field;
* which codes are Unknown or Not Applicable, how often they occur by year, and **whether that rate depends on
  severity**. For CRSS this includes "hidden" missingness: unknowns that the aux variable silently replaces with
  imputed values or folds into "No";
* a reliability verdict, and a recommendation either to use the variable directly or to rebuild it from source fields;
* a timing class for leakage control: **PRE-CRASH**, **CRASH-CIRCUMSTANCE** or **POST-CRASH / OUTCOME-DERIVED**.

### 1.1 Evidence conventions

* **R (rule reconstruction):** an explicit mapping from labelled main-table fields to the aux code, evaluated on every
  row after the 1:1 join. The result is reported as `agreement = rows where rule == aux / all rows`, per year. R 100%
  means the meaning is fully determined by the cited source fields. The labels of those source fields come from
  `codebook.csv` (FARS: all years; CRSS: 2019+).
* **FD (functional dependency):** used where a closed-form rule was impractical. It is the share of rows whose aux
  code equals the modal aux code within cells of the cited source fields.
* **D (distribution):** code shares per source-year. Year-to-year change is measured as total variation distance
  (TVD) in percentage points (pp). CRSS figures are weighted by `WEIGHT` unless marked "unw."
* **UNVERIFIED:** the meaning could not be confirmed from in-archive data.
* "Universe" is the set of rows on which a code is substantively meaningful, for example "motorcycle riders" for
  helmet use.

---

## 2. Tables, keys and 1:1 joins

### 2.1 Row counts and join verification (script `03_joins.py`)

| source | aux table | main table | key | rows 2016 … 2024 (aux = main in every year) |
|---|---|---|---|---|
| FARS | acc_aux | accident | YEAR, ST_CASE | 34,748 / 34,560 / 33,919 / 33,487 / 35,935 / 39,785 / 39,422 / 37,769 / 36,297 |
| FARS | veh_aux | vehicle | + VEH_NO | 52,714 / 53,128 / 52,286 / 51,623 / 54,552 / 61,802 / 60,765 / 58,508 / 56,011 |
| FARS | per_aux | person | + VEH_NO, PER_NO | 86,474 / 85,840 / 84,344 / 82,843 / 86,396 / 97,511 / 96,186 / 92,768 / 88,326 |
| CRSS | acc_aux | accident | YEAR, CASENUM | 46,511 / 54,969 / 48,443 / 54,409 / 54,745 / 54,200 / 53,955 / 50,103 / 51,658 |
| CRSS | veh_aux | vehicle | + VEH_NO | 82,149 / 97,625 / 86,105 / 96,717 / 94,718 / 95,785 / 94,756 / 87,461 / 90,641 |
| CRSS | per_aux | person | + VEH_NO, PER_NO | 117,759 / 138,913 / 120,230 / 135,410 / 131,962 / 133,734 / 132,175 / 122,388 / 126,159 |

The joins pass every check in all 54 source × table × year cells:

* there are 0 duplicate keys in any aux table;
* there are 0 aux keys absent from the main table and 0 main keys absent from the aux table;
* the matched count equals both row counts.

The aux tables are complete 1:1 companions of their main tables. FARS `veh_aux` covers only vehicles in the
`vehicle` file. Parked and working vehicles in `parkwork` have no aux rows.

The shared non-key columns are identical to the main table on every matched row. There are 0 mismatches for FARS
`acc_aux.STATE`, `FATALS` and `COUNTY` (2016-19), for FARS `veh_aux.STATE` and `per_aux.STATE` (2020-24), and for
CRSS `WEIGHT` in all three aux tables. **Implication:** CRSS aux rows can be weighted with their own `WEIGHT`. The
design variables (`PSU`, `PSUSTRAT`, `PSU_VAR`, `STRATUM`) are *not* in the aux files and must be joined from the main
table.

### 2.2 Column sets by year

| source.table | columns per year | changes |
|---|---|---|
| FARS acc_aux | 42 (2016-19), 44 (2020), 45 (2021-24) | 2020: +A_WRONGWAY, +TRACT, +CENSUS_2020_TRACT_FIPS, −COUNTY. 2021: +A_SBUSCR |
| FARS veh_aux | 18 (2016-19), 19 (2020), 20 (2021-24) | 2020: +A_WRONGWAYDRV, +STATE, −A_IMP2. 2021: +A_TOWED |
| FARS per_aux | 24 (2016-19), 25 (2020-24) | 2020: +STATE |
| CRSS acc_aux | 26 (2016-19), 28 (2020-24) | 2020: +A_DIST, +A_WEATHER |
| CRSS veh_aux | 9 (all years) | – |
| CRSS per_aux | 20 (all years) | – |

`FARS veh_aux.A_IMP2` (2016-19) is **100% null** in all 209,751 rows (stored as an empty string column). It carries no
information.

### 2.3 Variable inventory

| level | FARS only | both FARS and CRSS | CRSS only |
|---|---|---|---|
| crash (acc_aux) | A_DROWSY, A_PED_F, A_PEDAL_F, A_POLPUR, A_POSBAC, A_RD, A_REGION, A_ROADFC, A_RU, A_SBUSCR (2021+), A_WRONGWAY (2020+), BIA, SPJ_INDIAN, INDIAN_RES, TRACT and CENSUS_2020_TRACT_FIPS (2020+), STATE, FATALS, COUNTY (2016-19) | A_CRAINJ, A_CT, A_D15_19, A_D15_20, A_D16_19, A_D16_20, A_D16_24, A_D21_24, A_D65PLS, A_DIST (CRSS 2020+ only), A_DOW, A_HR, A_INTER, A_INTSEC, A_JUNC, A_LT, A_MANCOL, A_MC, A_PED, A_PEDAL, A_RELRD, A_ROLL, A_SPCRA, A_TOD, A_WEATHER (CRSS 2020+ only) | WEIGHT |
| vehicle (veh_aux) | A_CDL_S, A_DRDIS, A_DRDRO, A_FIRE_EXP, A_IMP2 (2016-19, empty), A_LIC_C, A_LIC_S, A_MC_L_S, A_SBUS, A_TOWED (2021+), A_VRD, A_WRONGWAYDRV (2020+), STATE (2020+) | A_BODY, A_IMP1, A_MOD_YR, A_SPVEH, A_VROLL | WEIGHT |
| person (per_aux) | A_ALCTES, A_DOA, A_HISP, A_HRACE, A_RCAT, STATE (2020+) | A_AGE1…A_AGE9, A_EJECT, A_HELMUSE, A_LOC, A_PERINJ, A_PTYPE, A_RESTUSE | WEIGHT |

No aux column contains a null in any year in which it exists, except `A_IMP2` (entirely null) and
`CENSUS_2020_TRACT_FIPS` (§5.5).

---

## 3. Headline results

1. **Every aux variable except `BIA` was reconstructed from labelled main-table fields.** Agreement is ≥ 99.96% for
   all variables except `A_VRD`, which reaches 99.57%. Most are exactly 100% in every year (tables in §4). `BIA` is a
   0/1 flag that cannot be reproduced from any in-archive field. Its meaning is **UNVERIFIED**.
2. **Same name does not mean same definition across sources.** In CRSS the aux variables are computed from the
   *imputed* `*_IM` fields wherever one exists: INJSEV_IM, EJECT_IM, AGE_IM, IMPACT1_IM, MDLYR_IM, BDYTYP_IM
   (2016-19), HITRUN_IM (2016-19), HOUR_IM, WKDY_IM, RELJCT2_IM, MANCOL_IM, MAXSEV_IM and WEATHR_IM. The CRSS versions
   therefore have no Unknown code, while the FARS versions keep one. Several variables also use different code schemes
   in the two sources: `A_PERINJ`, `A_CRAINJ`, `A_LOC` and `A_INTER`.
3. **Definitional breaks inside the "year-consistent" aux files** were found in `A_RESTUSE` (2020), `A_HELMUSE`
   (2019 and 2020), `A_BODY` (2020), `A_MC_L_S` (2020), `A_RELRD` (2020), `A_REGION` (2021), `A_POSBAC` (2020) and
   `A_HR` in CRSS (2020). `A_WEATHER` and `A_DIST` exist in CRSS only from 2020. Details are in §6.
4. **Unknown is silently merged into "No"** in `A_SPVEH`/`A_SPCRA` (SPEEDREL 8/9), `A_DRDIS`/`A_DIST` (distraction
   not reported or unknown), `A_DRDRO`/`A_DROWSY` (impairment not reported or unknown), `A_VROLL`/`A_ROLL`, `A_EJECT`
   ("not applicable" merged with "not ejected"), `A_FIRE_EXP` and `A_PERINJ` in FARS (INJ_SEV 9 merged with
   survivors). The folded-in unknown share is large and rising. For distraction it went from 31.0% of FARS vehicles in
   2016 to 66.2% in 2024. For impairment it went from 27.0% to 50.1%. It is also severity-dependent: 72.97% vs 59.09%
   in 2024 for vehicles with versus without an occupant death.
5. **Differential missingness is substantial.** Among FARS drivers, "no usable BAC" is 34.4% for killed drivers and
   77.6% for surviving drivers. Unknown helmet use among CRSS motorcycle riders is 3.4% for K and 20.3% for O
   (weighted). In CRSS 2019, 28.7% of crashes (weighted) had RELJCT2 not reported. The aux variable imputes these
   values, and in fatal crashes the share was 44.9%.

---

## 4. Per-variable sections

Each subsection lists availability, the code meanings with the reconstruction rule (R) and its agreement, and then
notes on breaks, missing codes, reliability and recommendations. Per-year agreement is 100% in every year unless the
text says otherwise. The year rows behind every figure are in `out_aux/16_*.txt`, `24_*.txt` and `33_*.txt` (§11).
Code shares quoted as "FARS 2016→2024" are unweighted row shares from `out_aux/aux_pivot.txt`.

### 4.1 Person level (per_aux)

#### A_PERINJ: person injury severity (FARS and CRSS, all years). POST-CRASH / OUTCOME

| source | code | rule (source field, label) | agreement |
|---|---|---|---|
| FARS | 1 | INJ_SEV 4 "Fatal Injury (K)" | 800,688 / 800,688 = 100% |
| FARS | 6 | INJ_SEV 0, 1, 2, 3, 5, 6 ("Died Prior to Crash"), 9 ("Unknown/Not Reported") | |
| CRSS | 2 | INJSEV_IM 3 "Suspected Serious Injury (A)" | 1,158,730 / 1,158,730 = 100% |
| CRSS | 3 | INJSEV_IM 2 (B) | |
| CRSS | 4 | INJSEV_IM 1 (C) and 5 "Injured, Severity Unknown" | |
| CRSS | 5 | INJSEV_IM 0 (O) | |
| CRSS | 7 | INJSEV_IM 4 (K) and 6 "Died Prior to Crash" | |

* The two sources use different code schemes. The FARS variable is a killed/not-killed flag. The CRSS variable is
  KABCO built on the imputed severity. Codes 1 and 6 never occur in CRSS. Codes 2-5 and 7 never occur in FARS.
* FARS killed share: 43.72% (2016), 45.15% (2020), 44.44% (2024).
* **Hidden missingness:**
  * FARS code 6 absorbs INJ_SEV 9 (unknown), which is 2.76% of non-fatal FARS persons (1.26-1.82% of all persons
    per year).
  * CRSS imputes INJ_SEV 9, which is 3.6-4.6% of persons (weighted) per year. The imputed share is highest among
    persons imputed to A: 10.2% pooled, 16.7% in 2019. It is 5.8% for K, 5.1% for B, 6.8% for C and 3.8% for O.
* **Verdict:**
  * FARS: safe as a killed/not-killed flag.
  * CRSS: usable only if imputation is acceptable. A_PERINJ cannot be told apart from observed values without the raw
    INJ_SEV, so build the outcome from INJ_SEV and keep INJSEV_IM only as a sensitivity variant.
  * Never pool the two codings without recoding.

#### A_PTYPE: person type (both, all years). PRE-CRASH (role)

| code | rule (PER_TYP) | meaning |
|---|---|---|
| 1 | 1 | driver of a motor vehicle in transport |
| 2 | 2, 9 | passenger, including unknown occupant type, of a MV in transport |
| 3 | 5 | pedestrian |
| 4 | 6, 7 | bicyclist or other pedalcyclist |
| 5 | 3, 4, 8, 10, 11, 12, 13, 19 | other or unknown: occupant of a MV *not* in transport, non-motor transport device, personal conveyance, person in a building, unknown non-motorist |

* Agreement is 100% in both sources (FARS 800,688 rows; CRSS 1,158,730 rows).
* PER_TYP 8 was split into 11/12/13 from 2021 (FARS labels). All four codes map to 5, so A_PTYPE absorbs that change.
* FARS shares 2016→2024: drivers 60.60→62.97%, passengers 30.13→26.33%, pedestrians 7.52→8.52%, pedalcyclists
  1.02→1.28%, other 0.73→0.89%.
* **Verdict:** safe to use directly. There is no unknown code; PER_TYP has no unknown-type categories outside 9 and 19.

#### A_RESTUSE: restraint use (both, all years). CRASH-CIRCUMSTANCE (pre-crash behaviour)

| period | code | rule | agreement |
|---|---|---|---|
| 2016-2019 | 1 | REST_USE ∈ {1, 2, 3, 4, 6, 8, 10, 11, 12, 97}: some belt, child seat, harness, "used type unknown", "other" | FARS 100% in all 4 years; CRSS 100% |
| 2016-2019 | 2 | REST_USE ∈ {0, 5, 7, 16, 17, 19, 20}: none used or not applicable, **and all pre-2019 helmet codes** | |
| 2016-2019 | 3 | REST_USE ∈ {29, 96, 98, 99}: unknown, **and "Not a Motor Vehicle Occupant" (96)** | |
| 2020-2024 | 4 | person is not an in-transport occupant (PER_TYP ∉ {1, 2, 9}), **or** the vehicle is a motorcycle-type (BODY_TYP 80-84 or 87-89), or REST_USE = 96 | FARS 99.994-99.998% (25 residual rows, mostly BODY_TYP 85/89/99); CRSS 100% (1 residual row) |
| 2020-2024 | 1 / 2 / 3 | otherwise: REST_USE used-set → 1; 20 → 2; 98, 99 → 3 | |

* **Break at 2020: the universe changed.** Before 2020 every person received 1/2/3. Motorcycle riders were coded 2
  ("not used"), even when their helmet codes said otherwise. Non-occupants were coded 3 ("unknown"). From 2020 both
  groups move to the new code 4. This produces a 2019→2020 TVD of 17.2 pp in FARS and 2.9 pp in CRSS (weighted).
  BODY_TYP 85 and 86 (three-wheel or enclosed autocycles) stay in the restraint universe.
* **Restricted to a fixed universe** (PER_TYP 1/2/9 and BODY_TYP not 80-84/87-89) the codes are consistent across the
  break:

  | universe | code | 2016 | 2018 | 2019 | 2020 | 2022 | 2024 |
  |---|---|---|---|---|---|---|---|
  | FARS | 1 used | 65.78 | 66.42 | 66.54 | 62.52 | 63.50 | 64.85 |
  | FARS | 2 not used | 24.62 | 23.49 | 23.51 | 26.16 | 24.59 | 23.37 |
  | FARS | 3 unknown | 9.60 | 10.09 | 9.95 | 11.32 | 11.91 | 11.78 |
  | CRSS (weighted) | 1 used | 88.82 | 88.51 | 88.36 | 86.09 | 86.37 | 85.37 |
  | CRSS (weighted) | 2 not used | 1.93 | 1.76 | 1.84 | 2.32 | 2.24 | 2.15 |
  | CRSS (weighted) | 3 unknown | 9.25 | 9.73 | 9.80 | 11.59 | 11.39 | 12.49 |

  Code 4 is ≤ 0.01% inside this universe. The 2020 dip in "used" appears in both sources inside a fixed universe. It
  is therefore not an artefact of the aux recode. It is plausibly a real change, but that is UNVERIFIED.
* **Unknown (code 3) by severity**, within the fixed universe:
  * FARS: 10.09% for killed and 11.22% for survivors, pooled; in 2024, 11.38% and 11.98%.
  * CRSS (weighted, pooled): K 16.61%, A 18.84%, B 9.76%, C 11.02%, O 10.62%. The K and A unknown rate is about 1.6
    to 1.8 times the O rate in most years. In 2019 it was K 22.74%, A 25.47%, O 9.33%. **Unknown restraint is strongly
    differential by severity in CRSS.** Complete-case belt-effectiveness estimates are biased unless the analysis
    models this.
* **Verdict:** usable *only* after restricting to the fixed universe above and treating 3 as missing. Otherwise
  rebuild from REST_USE (§9).

#### A_HELMUSE: helmet use (both, all years). CRASH-CIRCUMSTANCE

| period | code | rule | agreement |
|---|---|---|---|
| 2016-2018 (from REST_USE) | 1 | REST_USE ∈ {5, 8, 16, 19, 97} and REST_MIS ≠ 1 | FARS 100%; CRSS 100% |
| 2016-2018 | 2 | everything else, including all belted car occupants and helmet codes with REST_MIS = 1 (misuse) | |
| 2016-2018 | 3 | REST_USE ∈ {29, 96, 98, 99} | |
| 2019 (from HELM_USE) | 1 | HELM_USE ∈ {5, 16, 19} and HELM_MIS ≠ 1 | 100% |
| 2019 | 2 | HELM_USE ∈ {17, 20}, or helmet worn with misuse | |
| 2019 | 3 | HELM_USE ∈ {96, 98, 99} | |
| 2020-2024 | 4 | not (motorcycle-type BODY_TYP 80-89 and PER_TYP ∈ {1, 2, 9}) | FARS 99.994-99.998%; CRSS 99.999% |
| 2020-2024 | 1 / 2 / 3 | inside that universe, as 2019 | |

* **Two breaks.**
  * 2016-2018 artefact: REST_USE 8 ("Restraint Used - Type Unknown") and 97 ("Other") count as "helmet used" for
    *any* vehicle type. These non-motorcycle persons make up 24.9% / 18.4% / 20.6% of all `A_HELMUSE=1` rows in FARS
    2016/17/18. In CRSS the shares are 91.4% / 90.8% / 89.8% (weighted). The 2018→2019 TVD is 9.2 pp in FARS and
    13.1 pp in CRSS.
  * 2020: the universe was restricted to motorcycle riders, with code 4 for everyone else. The 2019→2020 TVD is
    92.8 pp in FARS and 99.2 pp in CRSS.
* **Restricted to motorcycle riders** (BODY_TYP 80-89, PER_TYP 1/2/9) the variable is consistent across all years:
  * FARS "used": 57.07 (2016), 58.67 (2018), 58.88 (2019), 57.68 (2020), 62.69 (2024).
  * CRSS (weighted) "used": 63.94, 61.67, 60.90, 58.50, 62.54.
  * Rebuilding helmet use directly from REST_USE (2016-18) and HELM_USE (2019+) agrees with A_HELMUSE within 0.3 pp
    in every year (script `55_harmonised_check.py`).
* **Unknown (3) among motorcycle riders:**
  * FARS: 2.68% (2016) to 3.98% (2024); killed 3.24% vs survived 5.10% pooled; in 2024, 3.55% vs 8.01%.
  * CRSS (weighted, pooled): K 3.39%, A 6.65%, B 6.88%, C 9.81%, **O 20.30%**. In 2024 the O rate was 31.81%.
  * **Unknown helmet use is concentrated among uninjured riders.** A naive complete-case comparison inflates the
    apparent helmet use of the uninjured group less than it should, so the bias direction depends on how the missing
    values are distributed.
* **Verdict:** never use unrestricted. Restrict to motorcycle riders and set code 3 to missing. Prefer rebuilding from
  source (§9).

#### A_EJECT: ejection (both, all years). POST-CRASH / OUTCOME (mechanism)

| source | code | rule | agreement |
|---|---|---|---|
| FARS | 1 | EJECTION 0 "Not Ejected" **and 8 "Not Applicable"** | 100% |
| FARS | 2 | EJECTION 1, 2, 3 (totally, partially, unknown degree) | |
| FARS | 3 | EJECTION 7 "Not Reported", 9 "Unknown" | |
| CRSS | 1 | EJECT_IM 0 and 8 | 100% |
| CRSS | 2 | EJECT_IM 1, 2, 3 | |

* Non-occupants (NA) are merged with "not ejected". The universe must be restricted to occupants before computing an
  ejection rate.
* CRSS uses the imputed value. EJECTION 7/9 (imputed) affects 3.0-8.3% of occupants per year (weighted).
* FARS unknown (3) among occupants: 0.89% (2016) to 1.27% (2024); killed 0.68% vs survived 1.55%.
* **Verdict:** usable in FARS after restricting to occupants and setting 3 to missing. For CRSS, rebuild from EJECTION
  if observed-only data are required.

#### A_LOC: non-motorist location (both, all years). CRASH-CIRCUMSTANCE

| source | code | rule (LOCATION) |
|---|---|---|
| FARS | 1 | 0 occupant |
| FARS | 2 | 1, 2, 3, 9: at intersection, any crosswalk status or unknown |
| FARS | 3 | 10, 11, 13: not at intersection, on roadway |
| FARS | 4 | 14, 16, 20, 21, 22, 23, 24, 25, 28: parking lane, bike lane, shoulder, sidewalk, median, driveway, path, non-trafficway, other |
| FARS | 5 | 98, 99: not reported or unknown |
| CRSS | 1 | 0 |
| CRSS | 2 | 1, 2, 9: at intersection in a crosswalk, or location unknown |
| CRSS | 3 | 11 only: not at intersection, on roadway, not in marked crosswalk |
| CRSS | 4 | **everything else**, including 3 (at intersection not in crosswalk), 10 and 13 (roadway), 14-28 and **98/99 (unknown)** |

* Agreement is 100% in both sources (script `16_person_rules.py`). This is the same variable name with **different
  groupings in the two sources**, and in CRSS the unknowns are folded into a substantive category.
* FARS unknown (5) among non-occupants: 1.26-1.92% per year; killed 1.57% vs survived 2.11%.
* **Verdict:** do not pool. Rebuild from LOCATION with one common grouping (§9).

#### A_AGE1 … A_AGE9: age groupings (both, all years). PRE-CRASH

FARS uses AGE. Its last code is "unknown" and corresponds to AGE 998/999. CRSS uses **AGE_IM** and has no unknown
code. Every rule agrees 100% in both sources. No AGE value maps to more than one code (script `13_age_alc_race.py`).

| variable | groups, in code order | FARS unknown code |
|---|---|---|
| A_AGE1 | 0-15, 16-24, 25-54, 55+ | 5 |
| A_AGE2 | 0-15, 16-20, 21-24, 25-34, 35+ | 6 |
| A_AGE3 | 0-3, 4-7, 8-12, 13-15, 16-20, 21-24, 25-34, 35-44, 45-54, 55-64, 65-74, 75+ | 13 |
| A_AGE4 | 0-15, 16-20, 21-24, 25-34, 35-44, 45-64, 65+ | 8 |
| A_AGE5 | 0-15, 16-20, 21-24, 25-34, 35-44, 45-54, 55-64, 65-74, 75+ | 10 |
| A_AGE6 | 0-14, 15-20, 21-24, 25-34, 35-44, 45-54, 55-64, 65-74, 75+ | 10 |
| A_AGE7 | 0-4, 5-9, 10-15, 16-20, 21-24, 25-34, 35-44, 45-54, 55-64, 65-74, 75+ | 12 |
| A_AGE8 | 0-19, 20-29, 30-39, 40-49, 50-59, 60+ | 7 |
| A_AGE9 | 0-15, 16+ | 3 |

* **FARS age unknown:** 2.22% (2016) to 2.95% (2022) to 2.55% (2024). It is strongly differential: killed 0.37% vs
  survived 4.24%. Ages of survivors in fatal crashes are recorded much less completely.
* **CRSS hidden imputation:** AGE 998/999 occurs for 6.3-8.8% of persons per year (weighted). By severity, pooled:
  K 5.5%, A 6.0%, B 4.2%, C 5.9%, O 7.5%. In 2019 it was K 11.2% and A 11.6%.
* **Verdict:** in FARS, safe as groupings, with the unknown code set to missing. For CRSS, use raw AGE when
  observed-only data are required, or A_AGE* knowing that 6-9% of values are imputed. Breaks: none.

#### A_ALCTES: alcohol test result (FARS only, all years). POST-CRASH ascertainment of a pre-crash state

| code | rule (ALC_RES; labels from the ALC_RESNAME column) | meaning |
|---|---|---|
| 1 | 0-9 (0.000-0.009 % BAC) | tested, BAC < 0.01 |
| 2 | 10-940 (0.010 % up to ".94 % or Greater") and 998 "Positive Reading with No Actual Value" | tested, BAC ≥ 0.01 |
| 3 | 996 "Test Not Given" (includes ALC_STATUS 1 "Test Refused", 83 rows) | not tested |
| 4 | 997 "AC Test Performed, Results Unknown" | tested, result unknown |
| 5 | 995 "Not Reported", 999 "(Reported as) Unknown if Tested" | unknown |

* Agreement is 100% (800,688 rows).
* The meaning of the cut is verified: the 344 rows with ALC_RES 1-9 are exactly the A_ALCTES=1 rows with nonzero BAC.
* **Missingness among drivers** (`50_missing_fars.py`):

  | category | 2016 | 2019 | 2020 | 2022 | 2023 | 2024 |
  |---|---|---|---|---|---|---|
  | code 5 (not reported or unknown) | 6.75 | 8.79 | 11.10 | 14.07 | 14.86 | 21.15 |
  | code 3 (not tested) | 44.72 | 45.61 | 44.98 | 44.60 | 43.67 | 41.30 |
  | code 5, killed drivers | 4.81 | 5.98 | 11.91 | 15.04 | 13.91 | 26.28 |
  | code 5, surviving drivers | 8.35 | 11.03 | 10.42 | 13.30 | 15.61 | 17.06 |
  | code 3, killed drivers | 21.53 | 24.16 | 22.53 | 20.18 | 20.42 | 14.32 |
  | code 3, surviving drivers | 63.90 | 62.71 | 64.03 | 64.30 | 61.99 | 62.75 |

  Pooled, no usable result (codes 3, 4 or 5) is **34.42% for killed drivers vs 77.55% for surviving drivers**. The
  2024 jump in code 5 for killed drivers, to 26.28%, together with the fall in "not tested" suggests that 2024 BAC
  results were still incomplete in this file version. That is UNVERIFIED: there is no release-status field.
* **Verdict:** the categories are reliable, but the variable is post-crash ascertained and missingness is massively
  differential. Do not use it as a covariate in models that compare killed and surviving drivers without a missingness
  model. Treat 2024 as provisional.

#### A_DOA: death at scene or en route (FARS only, all years). POST-CRASH / OUTCOME

| code | rule |
|---|---|
| 1 | DOA 7 "Died at Scene" |
| 2 | DOA 8 "Died En Route" |
| 3 | INJ_SEV = 4 and DOA = 0: fatality not at scene or en route |
| 4 | INJ_SEV = 4 and DOA = 9 "Unknown" |
| 5 | INJ_SEV ≠ 4: not a fatality, including 3 rows with DOA 9 |

* Agreement is 100%.
* Shares 2016→2024: code 1 24.63→25.12%, code 3 18.65→18.94%, code 4 0.03-0.09%.
* **Verdict:** safe. It is outcome-derived.

#### A_HISP, A_RCAT, A_HRACE: ethnicity and race (FARS only, all years; recorded for fatalities only). PRE-CRASH attribute, outcome-conditioned recording

* **A_HISP** (R 100%), from HISPANIC:
  * 0 = HISPANIC 0 "Not A Fatality (not Applicable)";
  * 1 = 7 "Non-Hispanic";
  * 2 = 1-6 (Mexican, Puerto Rican, Cuban, Central or South American, European Spanish, other Hispanic);
  * 3 = 97 "Redacted" (from 2020) or 99 "Unknown".
* **A_RCAT** (crosstab with zero off-pattern cells). Source: person.RACE for 2016-18; the `race` table for 2019+,
  where several rows or MULTRACE = 1 count as "multiple".
  * 0 = not a fatality;
  * 1 = RACE 1 White;
  * 2 = 2 Black;
  * 3 = 3 and 19 (North American or other Indian);
  * 4 = 4, 5, 7, 18, 28, 48 (Chinese, Japanese, Filipino, Asian Indian, Korean, Vietnamese);
  * 5 = 6, 38, 58 (Hawaiian, Samoan, Guamanian);
  * 6 = 97 multiple, or more than one race row;
  * 7 = 68, 78, 98 (other Asian/PI, unspecified Asian/PI, other race);
  * 8 = 99 Unknown and 96 Redacted.
* **A_HRACE** (crosstab A_HRACE × A_HISP × A_RCAT):
  * 0 = not a fatality;
  * 1 = Hispanic, any race;
  * 2 = non-Hispanic White;
  * 3 = non-Hispanic Black;
  * 4, 5, 6, 7 = AIAN, Asian, PI, multiple, *where Hispanic origin is non-Hispanic or unknown*;
  * **8 = a mixed residual**: non-Hispanic "other" (3,550), non-Hispanic race-unknown (679), **unknown-Hispanic
    White (11,212)**, unknown-Hispanic Black (1,283) and unknown-Hispanic other (318);
  * 9 = Hispanic origin unknown and race unknown (20,464).
  * Code 8 is not a substantive category.
* **Break:** the 2019 move of race to a multi-row table changes how "multiple" can arise. A_RCAT=6 rose from about
  0.1% to about 0.3% of persons. Redaction codes appear from 2020 (HISPANIC 97 is 0.79-0.92% of fatalities; race
  rows with RACE 96 number 336-379 per year).
* **Missingness among fatalities:** A_HISP=3 was 7.58% (2016), 4.58% (2017), 11.40% (2020), 8.37% (2022) and
  **18.94% (2024)**. A_RCAT=8 was 5.84% in 2016, 3.2-5.8% in 2017-2023, and **15.89% in 2024**. The 2024 jump
  probably reflects incomplete death-certificate linkage (UNVERIFIED).
* **Verdict:** use A_HISP and A_RCAT for fatality-only analyses, with codes 3 and 8 as missing. Do not use A_HRACE
  code 8 as "other race"; rebuild instead. These variables are not defined for survivors, so they cannot enter
  killed-vs-survived models.

### 4.2 Vehicle level (veh_aux)

#### A_BODY: vehicle body class (both, all years). PRE-CRASH

Code meanings come from the 2016-19 mapping of BODY_TYP (FARS) and BDYTYP_IM (CRSS). Each BODY_TYP is listed with
the A_BODY code it takes (script `54_body_map.py`):

| A_BODY | BODY_TYP codes | meaning |
|---|---|---|
| 1 | 1-11, 17 | automobile, including 9 "other/unknown automobile" and 10-11 auto-based pickup/panel |
| 2 | 30, 31, 32, 34, 39 | light pickup |
| 3 | 14, 15, 16, 19 | utility vehicle |
| 4 | 20, 21, 22, 28, 29 | van |
| 5 | 40, 41, 45, 48, 49, 79 | other or unknown light truck. FARS sends 49 "unknown light vehicle" and 79 "unknown truck type" here |
| 6 | 60-64, 66, 67, 71, 72, 78 | medium or heavy truck (this is the "large truck" behind A_LT) |
| 7 | 80-89 | motorcycle, moped, three-wheel motorcycle |
| 8 | 50-59 | bus |
| 9 | 12, 13, 42, 65, 73, 90-99 | other: limousine, three-wheel auto, motor homes, ATV, snowmobile, farm or construction equipment, golf cart, other, **98/99 not reported/unknown** |

* **Determinism and break at 2020** (FD, script `22_fd.py`):

  | source | period | A_BODY determined by | FD share |
  |---|---|---|---|
  | FARS | 2016-19 | BODY_TYP | ≥ 99.994% (10 non-modal rows of 209,751) |
  | FARS | 2020-24 | BODY_TYP alone | 98.80-99.00% |
  | FARS | 2020-24 | (BODY_TYP, VPICBODYCLASS) | 99.84-99.88% |
  | CRSS | 2016-19 | BDYTYP_IM | 100% |
  | CRSS | 2020 | BDYTYP_IM | 94.6% |
  | CRSS | 2021-24 | BDYTYP_IM | ≤ 40.7% (the field no longer exists) |
  | CRSS | 2021-24 | (BODY_TYP, VPICBODYCLASS) | 99.89-99.95% |

  **From 2020 A_BODY uses the VIN-decoded vPIC body class.** For FARS 2020-24, applying the 2016-19 BODY_TYP mapping
  agrees with A_BODY in only 96.14% of rows. The main reclassifications are:
  * BODY_TYP 5/6 (hatchback, station wagon) with vPIC "Sport Utility Vehicle (SUV)/Multi-Purpose Vehicle (MPV)" (8,033
    FARS rows) or "Crossover Utility Vehicle (CUV)" (1,764) move from 1 to 3. In CRSS the counts are 13,792 and 3,650.
  * Unknown body types with vPIC "Unknown" (999) now go to **9** (FARS: BODY_TYP 9 in 191 rows, 49 in 135). In CRSS
    this affects BODY_TYP 9 (18,009 rows), 49 (13,342) and 79 (694). Before 2020, CRSS imputed these through
    BDYTYP_IM.
* **Consequence:**
  * CRSS A_BODY=9 rises from **0.12-0.17% (2016-19) to 6.36% (2020), 8.05% (2021), 12.10% (2022), 11.69% (2023) and
    11.61% (2024)** (weighted). The 2019→2020 TVD is 11.4 pp.
  * FARS A_BODY=9 rises from 2.76-2.83% to 3.58-4.00%; the TVD is 5.7 pp. The FARS "utility" share jumps from 17.71%
    (2019) to 21.66% (2020).
  * The CRSS A_BODY=9 rise is similar across severities in 2024: fatal 8.73%, injury 11.29%, PDO 11.75%.
* **Verdict: rebuild.** Body class from BODY_TYP with the fixed 2016-19 map, applied to every year, gives a
  year-consistent police-reported class. vPIC-based reclassification can be added as an explicitly 2020+ feature.
  Keep BODY_TYP 98/99 (and 9/49/79 where the analysis needs it) as unknown, not imputed.

#### A_IMP1: initial impact point (both, all years). CRASH-CIRCUMSTANCE

| code | IMPACT1 (FARS) / IMPACT1_IM (CRSS) | meaning |
|---|---|---|
| 1 | 0 | non-collision |
| 2 | 11, 12, 1 | front |
| 3 | 2, 3, 4, 81, 82, 83 | right side |
| 4 | 5, 6, 7 | rear |
| 5 | 8, 9, 10, 61, 62, 63 | left side |
| 6 | 13, 14, 18, 19, 20 | top, undercarriage, set-in-motion objects |
| 7 | 98, 99 | not reported or unknown (FARS only) |

* Agreement is 100% (FARS 501,389 rows; CRSS 825,957).
* FARS unknown: 4.24-5.28% per year; 5.47% for vehicles with an occupant death vs 4.08% without.
* CRSS hidden imputation (IMPACT1 98/99): 1.44-2.57% per year, 4.45% in fatal crashes vs 1.97% in PDO.
* **Verdict:** in FARS, safe with 7 set to missing. For CRSS, rebuild from IMPACT1 if imputation must be avoided.

#### A_IMP2 (FARS 2016-19)

The column is entirely null in all 209,751 rows and was dropped in 2020. **Unusable.**

#### A_MOD_YR: model year (both, all years). PRE-CRASH

* FARS: A_MOD_YR = MOD_YEAR verbatim, including **9998 (not reported) and 9999 (unknown)**. Agreement is 100%.
  * The 9998/9999 share is 2.29-2.47% (2016-19) and 2.96-3.21% (2020-24). 9998 grew from 3 rows (2016) to 276
    (2024).
  * It is strongly differential: 4.69% for vehicles with no occupant death vs 1.04% with one.
* CRSS: A_MOD_YR = MDLYR_IM. Agreement is 100%; the variable is imputed. Raw MOD_YEAR 9998/9999 is 4.3-5.2% per year
  (weighted): 3.48% in fatal crashes vs 4.95% in PDO.
* **Verdict:** in FARS, usable only after setting ≥ 9998 to missing. Numeric use without that step corrupts means and
  regressions. For CRSS, use raw MOD_YEAR for observed-only data.

#### A_SPVEH: speeding-related vehicle (both, all years). CRASH-CIRCUMSTANCE

* 1 = SPEEDREL ∈ {2, 3, 4, 5} (racing, exceeded limit, too fast for conditions, specifics unknown).
* 2 = SPEEDREL ∈ {0 "No", **8 "No Driver Present/Unknown if Driver Present", 9 "Reported as Unknown"**}.
* Agreement is 100% in both sources.
* **Hidden unknown** in code 2:
  * FARS: 3.83-6.56% of vehicles per year, rising from 2020; 5.84% with an occupant death vs 5.26% without.
  * CRSS (weighted): 1.57-4.38%; 4.57% in fatal crashes vs 2.75% in PDO.
* **Verdict:** a valid "speeding reported" flag. If unknown must be separated, rebuild from SPEEDREL.

#### A_VROLL: rollover (both, all years). POST-CRASH / OUTCOME (crash mechanism)

* 1 = ROLLOVER ∈ {1, 2, 3, 9}. Code 9 is labelled "Rollover, Unknown Type", so it is a rollover.
* 2 = ROLLOVER ∈ {0 "No Rollover", 8 "Not Applicable"}.
* Agreement is 100% in both sources.
* **Verdict:** safe. There is no unknown-occurrence code in the source.

#### A_CDL_S, A_LIC_S, A_LIC_C: licence variables (FARS only, all years). PRE-CRASH

| variable | code | rule |
|---|---|---|
| A_CDL_S | 1 | CDL_STAT 6 "Valid" or 7 "Commercial Learner's Permit" |
| A_CDL_S | 2 | 0 "No (CDL)", 1-5 (suspended, revoked, expired, cancelled, disqualified), 8 "Other Not-Valid" |
| A_CDL_S | 3 | 97 "No Driver Present/Unknown", 99 "Unknown License Status" |
| A_LIC_S | 4 | **A_BODY = 7 (motorcycle)**, regardless of L_STATUS |
| A_LIC_S | 1 | otherwise L_STATUS 6 "Valid" |
| A_LIC_S | 2 | L_STATUS 0-4 (not licensed, suspended, revoked, expired, cancelled/denied) |
| A_LIC_S | 3 | L_STATUS 7 (no driver), 9 (unknown) |
| A_LIC_C | 1 | L_COMPL 1 "No license required" or 3 "Valid license for this class" |
| A_LIC_C | 2 | L_COMPL 0 "Not licensed" or 2 "No valid license for this class" |
| A_LIC_C | 3 | L_COMPL 6 (no driver), 8 (unknown if CDL required), 9 (unknown) |

* All three rules agree 100%. A_LIC_S=4 equals A_BODY=7 in all 52,451 motorcycle rows and no other rows.
* A_CDL_S=2 is "no valid CDL" for *every* vehicle, including passenger cars. It is not restricted to commercial
  vehicles.
* Since A_BODY changed in 2020, the A_LIC_S universe follows it (motorcycles are identified through A_BODY).
* Unknown rates (code 3), 2016→2024:
  * A_LIC_S among non-motorcycles: 3.67→5.07%.
  * A_LIC_C: 3.49→4.82%.
  * A_CDL_S: 3.40→4.64%.
  * All three step up by about 1 pp at 2020.
  * All are strongly differential: about 7.2-7.4% for vehicles without an occupant death vs 1.4-1.5% with one. These
    are mostly hit-and-run or no-driver vehicles.
* **2020 level shift in the source fields.** The A_LIC_S and A_LIC_C distributions shift at 2020, with TVD 4.48 and
  4.87 pp:
  * "not compliant" (A_LIC_C=2) went from 13.95% of vehicles (2019) to 17.94% (2020);
  * "not valid" (A_LIC_S=2) went from 10.78% to 13.75%.
  * The rules are unchanged (R 100% in both years), so the shift is in L_STATUS and L_COMPL themselves. Whether it is
    a coding-practice change or real is UNVERIFIED.
* **Verdict:** usable with 3 set to missing. Note the 2020 rise in unknowns.

#### A_MC_L_S: motorcycle licence status (FARS only, all years). PRE-CRASH

| period | code | rule (motorcycles only; 4 = not a motorcycle, i.e. A_BODY ≠ 7) |
|---|---|---|
| all years | 1 | L_COMPL 1 or 3 (licence valid for this class, or none required) |
| 2016-19 | 2 | L_COMPL 0 (not licensed), 2 (no valid licence for this class), 6 (no driver) |
| 2016-19 | 3 | L_COMPL 8, 9 (unknown) |
| 2020-24 | 2 | L_COMPL 0 (not licensed) only |
| 2020-24 | 3 | L_COMPL 2 (**licensed, but not valid for a motorcycle**), 6, 8, 9 |

* Agreement is 99.998% (2016-17, 1 row each) and 100% in 2018-24.
* **Break at 2020:** "has a licence but no valid motorcycle endorsement" moved from 2 to 3. Among motorcycles, code 3
  rose from 0.80-1.16% (2016-19) to 28.7-31.6% (2020-24), and code 2 fell from about 25% to about 6%. Code 3 is no
  longer "unknown".
* **Verdict: rebuild** from L_COMPL and L_STATUS for motorcycles (§9).

#### A_FIRE_EXP: fire occurrence (FARS only, all years). POST-CRASH / OUTCOME

* 1 = FIRE_EXP 0 "No or Not Reported"; **2 = FIRE_EXP 1 "Yes"**. Agreement is 100%.
* The coding is inverted relative to most aux flags (here 1 = no). The source itself merges "not reported" with
  "no".
* The fire share (code 2) is 3.22% (2016) to 3.76% (2024).
* **Verdict:** safe with care over the inverted coding.

#### A_SBUS: school bus involvement (FARS only, all years). PRE-CRASH

* 1 = school bus body: BODY_TYP 50, or (2020+) VPICBODYCLASS 71 "Incomplete - School Bus Chassis" or 73 "Bus -
  School Bus".
* 2 = another vehicle with BUS_USE 1 "School" (vans, other buses, straight trucks).
* 3 = neither.
* Agreement is 99.996% (22 residual rows). 17 of them are BODY_TYP 61 with VPICBODYCLASS 62 "Incomplete - Cutaway"
  and BUS_USE 1 (2020-24), coded 1 where the rule predicts 2.
* **Verdict:** safe. Code 1 depends partly on vPIC from 2020; the effect is negligible.

#### A_TOWED: towing (FARS only, 2021-24). POST-CRASH / OUTCOME

* 1 = TOWED 2, 3, 6, 7 (towed, for any or unknown reason); 2 = 5 "Not Towed"; 3 = 8 "Not Reported"; 4 = 9
  "Reported as Unknown". Agreement is 100% (237,086 rows).
* **The source field itself breaks:**
  * TOWED codes 2 "Towed Due to Disabling Damage" and 3 "...Not Due to Disabling Damage" exist only through 2021.
  * Code 7 "Towed, Unknown Reason" exists 2018-21.
  * Code 6 "Towed" (reason not recorded) exists only from 2022.
* A_TOWED harmonises to towed yes/no. **The "disabling damage" distinction cannot be harmonised beyond 2021.**
* Unknown (3 or 4): 1.68-2.10% per year; 2.76% for vehicles without an occupant death vs 1.03% with one.
* **Verdict:** use A_TOWED from 2021 and rebuild the same mapping from TOWED for 2016-20 (§9).

#### A_DRDIS (FARS vehicle) and A_DIST (FARS crash; CRSS crash 2020+): distraction. PRE-CRASH, but ascertained post-crash

* A_DRDIS = 1 if any `distract` row for the vehicle has a code outside {0 "Not Distracted", 1 "Looked But Did Not
  See", 16 "No Driver Present/Unknown if Driver present", 96 "Not Reported", 99 "Reported as Unknown if Distracted"};
  otherwise 2.
  * The source column is MDRDSTRD in 2016-19 and DRDISTRACT in 2020-24.
  * Agreement is 100%. Without excluding code 1 it is 99.39% in 2016 and 99.29% in 2017, the only years code 1
    occurs.
* A_DIST (FARS crash) = any vehicle A_DRDIS = 1: 99.997% (10 residual crashes).
* A_DIST (CRSS 2020+) = any DRDISTRACT ∉ {0, 16, 96, 99}: 99.994% (16 residual crashes).
* **Hidden unknown:** among FARS vehicles, the share whose only distraction codes are 96 or 99 rose from **31.0%
  (2016) to 49.9% (2017), 60.0% (2018), 62.2% (2020) and 66.2% (2024)**. All of these are coded 2. The share is higher
  for vehicles with an occupant death (66.3% vs 50.2% pooled; 72.97% vs 59.09% in 2024).
* **Verdict: do not use as a year-consistent indicator.** "2" mixes "not distracted" with a growing, differential
  "unknown". Rebuild a three-level variable (§9).

#### A_DRDRO (FARS vehicle) and A_DROWSY (FARS crash): drowsy driver. PRE-CRASH, ascertained post-crash

* A_DRDRO = 1 if any `drimpair` row has DRIMPAIR 2 "Asleep or Fatigued"; else 2. Agreement is 100%.
* A_DROWSY = any vehicle A_DRDRO = 1: 100%.
* **Hidden unknown:** vehicles whose drimpair codes are only 98 or 99 rose from 26.97% (2016) to 41.20% (2019),
  42.16% (2020) and **50.10% (2024)**. Pooled: 51.2% with an occupant death vs 31.9% without.
* **Verdict:** same as distraction. Rebuild with an explicit unknown.

#### A_VRD (FARS vehicle) and A_RD (FARS crash): roadway departure. CRASH-CIRCUMSTANCE

* A_VRD ≈ 1 if the vehicle's sequence of events (`vsoe`) contains a departure event **before its first harmful
  event**. Departure events are SOE 63 "Ran Off Roadway - Right", 64 "...Left", 65 "Cross Median", 68 "Cross
  Centerline", 69 "Re-entering Roadway", 71 "End Departure" and 79 "Ran off Roadway - Direction Unknown". Harmful
  means any SOE outside the non-harmful set {60-71, 79}.
* Agreement by rule variant:

  | rule | agreement |
  |---|---|
  | final rule above | 99.568% (per year 99.45-99.66%) |
  | departure events at any position | 90.57% |
  | ran-off-road events only | 85.50% |

* The residual 0.43% concentrates in ACC_TYPE 2 and 7 (single-driver departures after loss of control): 477 + 437
  rows coded 2 although a departure precedes harm. The exact NHTSA rule is therefore **partly UNVERIFIED**.
* A_RD (crash) = any vehicle A_VRD = 1: agreement 100%. FARS share 46.0-51.8% of crashes.
* **Verdict:** usable as NHTSA's own definition (reliability medium-high). Do not try to re-derive it exactly.

#### A_WRONGWAYDRV (FARS vehicle) and A_WRONGWAY (FARS crash), 2020-24. PRE-CRASH, ascertained post-crash

* A_WRONGWAYDRV = 1 if any `driverrf` DRIVERRF ∈ {50 "Driving Wrong Way on One-Way Trafficway", 51 "Driving on Wrong
  Side of Two-Way Trafficway"} **or** any `violatn` VIOLATION ∈ {51 "Driving wrong way on one-way road", 52 "Driving on
  left, wrong side of road, generally"}.
  * Agreement is 100% (291,638 rows).
  * Without the violation clause it is 99.89%. All 320 missing positives had VIOLATION 51/52.
* A_WRONGWAY = any vehicle A_WRONGWAYDRV = 1: 100%.
* Not available before 2020. For 2016-19 the same rule can be rebuilt from vehicle DR_SF1-DR_SF4 (codes 50, 51 carry
  the same labels in 2019) and the `violatn` table.
* **Verdict:** safe for 2020+. Rebuild for 2016-19.

### 4.3 Crash level (acc_aux)

#### A_CRAINJ: crash injury severity (both, all years). POST-CRASH / OUTCOME

* **FARS:** always 1 (325,922 / 325,922 crashes). It is a constant: every FARS crash is fatal.
* **CRSS** (from MAXSEV_IM; agreement 100%):
  * 4 = MAXSEV_IM 4 (fatal);
  * 2 = 1, 2, 3, 5 (any non-fatal injury, including severity unknown);
  * 3 = 0 (no injury), 6 (died prior to crash), 8 (no person involved).
  * Code 1 never occurs in CRSS.
* **The codes are not aligned between sources.** "Fatal" is 1 in FARS and 4 in CRSS. That is the data's own coding;
  the official labels are UNVERIFIED.
* MAX_SEV 9 (unknown) is imputed for 2.5-3.4% of CRSS crashes per year (weighted).
* **Verdict:** rebuild crash severity from MAX_SEV or MAXSEV_IM, with explicit codes.

#### A_CT: number of vehicles (both, all years). CRASH-CIRCUMSTANCE

* 1 = VE_FORMS 1, 2 = VE_FORMS 2, 3 = VE_FORMS ≥ 3. Agreement is 100%.
* Shares: FARS 2016→2024 single-vehicle 58.32→56.13%; CRSS single-vehicle 33.07% (2016, unw.).
* **Verdict:** safe. VE_FORMS counts in-transport vehicles, so parked vehicles do not count.

#### A_D15_19, A_D15_20, A_D16_19, A_D16_20, A_D16_24, A_D21_24, A_D65PLS: driver-age involvement flags (both, all years). PRE-CRASH

* 1 if any person with PER_TYP = 1 has an age in the named range (65+ for A_D65PLS); else 2.
* The age source is AGE in FARS (998/999 never in range) and **AGE_IM** in CRSS.
* Agreement is 100% for all 7 flags in both sources.
* **Hidden unknown:** in FARS a crash whose drivers all have unknown age is coded 2 ("no young driver").
  * Unknown age affects 13,230 of 497,955 FARS drivers (2.66%). **90.8% of them are drivers of hit-and-run
    vehicles.** Age is unknown for 53.9% of hit-and-run drivers vs 0.26% of other drivers.
  * In 9,138 of 325,922 FARS crashes (2.8%) every driver has unknown age (script `56_driver_age_hr.py`).
* **Verdict:** safe as NHTSA-style flags. For FARS hit-and-run crashes, "2" is not informative.

#### A_DOW: weekend (both, all years). PRE-CRASH

* 2 (weekend) = Saturday or Sunday (DAY_WEEK 7 or 1), or Friday at HOUR 18-23, or Monday at HOUR 0-5.
* 1 = all other times.
* 3 = Monday or Friday with HOUR 99 (unknown). Sat/Sun with an unknown hour are still 2.
* CRSS uses WKDY_IM and HOUR_IM. Agreement is 100%.
* FARS code 3: 0.18-0.23% per year.
* **Verdict:** safe. The weekend definition runs Friday 18:00 to Monday 05:59 and is not calendar Sat/Sun.

#### A_TOD: daytime vs nighttime (both, all years). PRE-CRASH

* 1 = HOUR 6-17; 2 = HOUR 0-5 and 18-23; 3 = HOUR 99 (FARS only). CRSS uses HOUR_IM. Agreement is 100%.
* FARS code 3: 0.67-0.85%.
* CRSS hidden imputation: HOUR 99 rose from 0.19% (2016) to 0.84-0.93% (2019-24), weighted. It is 1.33% in fatal
  crashes vs 0.45% in injury crashes.
* **Verdict:** safe. "Night" is clock-based (18:00-05:59) and not light condition.

#### A_HR: hit-and-run crash (both, all years). CRASH-CIRCUMSTANCE

* 1 = any vehicle with HIT_RUN 1 "Yes"; else 2.
* FARS uses HIT_RUN. **CRSS uses HITRUN_IM in 2016-19 and raw HIT_RUN in 2020-24**; HITRUN_IM does not exist after
  2019. Agreement is 100%.
* CRSS HIT_RUN 9 is ≤ 0.01%, so the switch has little effect on missingness. The CRSS share stepped from 10.4-10.9%
  (2016-19, unw.) to 12.6-13.3% (2020-24); the weighted TVD at 2020 is 2.56 pp. Whether that is real or the effect of
  the imputation change is UNVERIFIED.
* **Verdict:** usable. Note the 2020 step in CRSS.

#### A_INTER: interstate (both, all years; different sources). PRE-CRASH

* FARS, from FUNC_SYS: 1 = FUNC_SYS 1 "Interstate"; 2 = 2-7; 3 = 96 "Trafficway Not in State Inventory", 98, 99.
  Agreement is 100%. It is not based on ROUTE: 625 crashes with ROUTE 1 "Interstate" have A_INTER = 2.
* CRSS, from INT_HWY: 1 = 1 "Yes", 2 = 0 "No", 3 = 9 "Unknown". Agreement is 100%. CRSS code 3 is absent in 2021
  only.
* FARS code 3: 0.30-0.98%, highest in 2024.
* **Verdict:** usable within each source. Cross-source equivalence (road functional class vs a police "interstate"
  flag) is UNVERIFIED.

#### A_ROADFC (FARS): road function class. PRE-CRASH

* 1 = FUNC_SYS 1 interstate; 2 = 2 other freeway or expressway; 3 = 3 other principal arterial; 4 = 4 minor arterial;
  **5 = 5 and 6 (major and minor collector)**; 6 = 7 local; 7 = 96, 98, 99.
* Agreement is 100%. Code 7: 0.30-0.98%.
* **Verdict:** safe.

#### A_RU (FARS): rural/urban. PRE-CRASH

* 1 = RUR_URB 1 rural; 2 = 2 urban; 3 = 6, 8, 9. Agreement is 100%.
* Code 3: 0.25-0.90%, with 2024 the highest.
* The rural share falls from 47.38% (2016) to 39.08-43.68% (2019-24). The TVDs are 1.9-3.0 pp in 2017-2021. That
  reflects RUR_URB itself (census urban-area updates are UNVERIFIED as the cause); it is not an aux artefact.
* **Verdict:** safe as RUR_URB. There is no CRSS analogue in aux. CRSS URBANICITY is area-based and is covered in
  `crash_environment.md`.

#### A_JUNC and A_INTSEC: junction / intersection (both, all years). PRE-CRASH

| variable | code | rule (FARS RELJCT2; CRSS RELJCT2_IM) |
|---|---|---|
| A_JUNC | 1 | 2 "Intersection" or 3 "Intersection-Related" |
| A_JUNC | 2 | 1 "Non-Junction" |
| A_JUNC | 3 | 4-8 and 16-20 (driveway, ramp, rail crossing, crossover, interchange areas) |
| A_JUNC | 4 | 98, 99 (FARS only) |
| A_INTSEC | 1 | 2, 3 |
| A_INTSEC | 2 | everything else |
| A_INTSEC | 3 | 98, 99 (FARS only) |

* Agreement is 100% in both sources. A_INTSEC = 1 exactly when A_JUNC = 1.
* A_INTSEC is *not* based on TYP_INT: 450 FARS crashes with TYP_INT 98 have A_INTSEC = 1.
* **CRSS 2019 problem:** RELJCT2 was 98/99 for **28.75% of crashes (weighted)**, against 0.74% (2016), 6.09% (2018)
  and 0.20% (2020). By severity in 2019: fatal 44.88%, injury 25.78%, PDO 29.82%.
  * The imputation put 70.4% of those crashes into "non-junction", while 60.5% of the reported 2019 crashes were
    intersection crashes.
  * Result: CRSS A_JUNC TVDs are 6.93 pp (2018→2019) and 7.35 pp (2019→2020).
  * About 29% of CRSS 2019 A_JUNC/A_INTSEC values are model output.
* **Verdict:** in FARS, safe with 4/3 set to missing. CRSS is usable except 2019. Flag or exclude 2019, or do the
  sensitivity analysis with raw RELJCT2.

#### A_RELRD: relation to trafficway (both, all years). CRASH-CIRCUMSTANCE

| code | rule (REL_ROAD) |
|---|---|
| 1 | 1 "On Roadway", 11 "Continuous Left-Turn Lane", **and from 2020: 7 "In Parking Lane/Zone"** |
| 2 | 2 "On Shoulder" |
| 3 | 3 "On Median" |
| 4 | 4, 5, 6, 8, 10, 12; **and 2016-19: 7** |
| 6 | 98, 99; **and CRSS 2018-19: 12 "Pedestrian Refuge Island or Traffic Island"** |

* Agreement is 100% in both sources once the year-specific rules are applied (script `31_relrd_region.py`). Code 5
  never occurs.
* **Break at 2020:** "parking lane" moved from off-roadway (4) to on-roadway (1). It affects 73-100 FARS crashes per
  year and 1,203-1,726 CRSS crashes (unw.), which is about 3% of CRSS crashes.
* **CRSS 2018-19:** code 12 (26 and 30 crashes) went to *unknown* (6), but to 4 from 2020.
* **Verdict: rebuild** from REL_ROAD with a fixed rule (§9).

#### A_MANCOL: manner of collision (both, all years). CRASH-CIRCUMSTANCE

* Rule (FARS from MAN_COLL; CRSS from MANCOL_IM):
  * 1 = 0 (first harmful event not a collision with a MV in transport);
  * 2 = 1 front-to-rear;
  * 3 = 2 front-to-front;
  * 4 = 6 angle;
  * 5 = 7, 8 (sideswipe, same or opposite direction);
  * 6 = 9, 10, 11 (rear-to-side, rear-to-rear, other);
  * 7 = 98, 99 (FARS only).
* Agreement is 100%. FARS code 7: 0.20-0.34%. CRSS imputed MAN_COLL 98/99: 0.18-0.63%.
* **Verdict:** safe.

#### A_WEATHER: weather (FARS all years; CRSS 2020-24 only). PRE-CRASH

| A_WEATHER | WEATHER (FARS) / WEATHR_IM (CRSS) | label of the source code |
|---|---|---|
| 1 | 1 | Clear |
| 2 | 2 | Rain |
| 3 | 3 | Sleet or Hail |
| 4 | 4 | Snow |
| 6 | 5 | Fog, Smog, Smoke |
| 10 | 6 | Severe Crosswinds |
| 11 | 7 | Blowing Sand, Soil, Dirt |
| 12 | 8 | Other |
| 13 | 10 | Cloudy |
| 14 | 11 | Blowing Snow |
| 15 | 12 | Freezing Rain or Drizzle |
| 99 | 98, 99 | Not Reported / Unknown (FARS only) |

* Agreement is 100%. **The codes are renumbered relative to WEATHER**, so A_WEATHER code k ≠ WEATHER code k for
  k ≥ 5. Code 5 is unused. The scheme matches no other weather variable in these archives, and its official labels
  are UNVERIFIED.
* A_WEATHER is based on the single summary WEATHER field and not on WEATHER1/2 or the 2020+ `weather` table.
* FARS code 99: 4.89% (2016), 7.74% (2018), 7.31% (2020), 4.47% (2021), 3.70% (2023), 3.85% (2024). These swings
  come from WEATHER itself.
* CRSS imputation of WEATHER 98/99 (2020+): 3.3-5.7%.
* **Verdict:** usable with the explicit recode table above. For CRSS 2016-19, rebuild from WEATHR_IM/WEATHER with the
  same map; the source fields exist in all years.

#### A_LT, A_MC, A_PED, A_PEDAL, A_PED_F, A_PEDAL_F, A_ROLL, A_SPCRA: involvement flags. CRASH-CIRCUMSTANCE (A_PED_F and A_PEDAL_F are outcome)

Each flag is 1 if the condition holds for any vehicle or person in the crash, else 2:

| flag | condition | source | agreement |
|---|---|---|---|
| A_LT | A_BODY = 6 | both | 100% |
| A_MC | A_BODY = 7 | both | FARS 99.999% (3 residual crashes); CRSS 99.9998% (1) |
| A_PED | PER_TYP 5 | both | 100% |
| A_PEDAL | PER_TYP 6 or 7 | both | FARS 100%; CRSS 99.984% (74 residual crashes, 0.016%) |
| A_PED_F | pedestrian with INJ_SEV 4 | FARS | 100% |
| A_PEDAL_F | pedalcyclist with INJ_SEV 4 | FARS | 100% |
| A_ROLL | A_VROLL = 1 | both | 100% |
| A_SPCRA | A_SPVEH = 1 | both | 100% |

* A_LT and A_MC inherit the 2020 A_BODY vPIC break (§4.2). The effect on A_LT is small. Over 2020-24, 297 FARS
  vehicles whose BODY_TYP maps to 6 received A_BODY 9 (192) or 8 (105), mostly BODY_TYP 61 with an "Incomplete"
  vPIC chassis class. That is about 0.1% of vehicles.
* A_SPCRA inherits the SPEEDREL unknown-as-no folding.

#### A_POLPUR (FARS): police pursuit. CRASH-CIRCUMSTANCE

* 1 = CF1, CF2 or CF3 = 20 "Police Pursuit Involved" (2016-19), or any `crashrf` CRASHRF = 20 (2020-24). Else 2.
* Agreement is 99.997% (10 residual crashes).
* Share: 1.03-1.38%.
* **Verdict:** safe. The source moved from CF1-3 to the `crashrf` table in 2020, and the aux variable bridges that
  move.

#### A_POSBAC (FARS): any driver with a positive BAC. POST-CRASH ascertainment

* 1 = any driver (PER_TYP 1) with a positive result. **Threshold 2016-19: ALC_RES ≥ 10 (BAC ≥ .01). 2020-24: ALC_RES
  ≥ 1 (BAC ≥ .001).** ALC_RES 998 ("positive reading, no value") counts as positive in both periods.
* 2 = every driver has a valid result (ALC_RES 0-940) below the threshold, or there is no driver (629 crashes).
* 3 = otherwise, i.e. at least one driver untested or unknown and none positive.
* Agreement with the year-specific thresholds is 100% in every year. A single threshold of ≥ 1 gives 99.88-99.93%
  agreement for 2016-19; a single threshold of ≥ 10 gives 99.92-99.96% for 2020-24 (script `34_posbac2.py`).
* **Break at 2020:** BAC .001-.009 counts as positive only from 2020. It affects about 25-30 crashes per year.
* **Missingness:** code 3 is 54.29% (2016), 57.32% (2019), 58.75% (2020), 61.13% (2022) and **64.74% (2024)**. It is
  59.58% for single-fatality crashes vs 49.70% for crashes with 2 or more deaths.
* **Verdict: rebuild** from driver ALC_RES with one fixed threshold. A_POSBAC=2 ("no positive driver") is
  well-defined, but code 3 dominates and is outcome-related.

#### A_REGION (FARS): NHTSA region of the crash state. PRE-CRASH

| region | STATE FIPS codes |
|---|---|
| 1 | 9 (CT, **2021-24 only**), 23, 25, 33, 44, 50 |
| 2 | 9 (CT, **2016-20**), 34, 36, 42 |
| 3 | 10, 11, 21, 24, 37, 51, 54 |
| 4 | 1, 12, 13, 45, 47 |
| 5 | 17, 18, 26, 27, 39, 55 |
| 6 | 22, 28, 35, 40, 48 |
| 7 | 5, 19, 20, 29, 31 |
| 8 | 8, 32, 38, 46, 49, 56 |
| 9 | 4, 6, 15 |
| 10 | 2, 16, 30, 41, 53 |

* Agreement is 100% with the Connecticut switch. The break is not county-based: every CT county moves.
* The interpretation as NHTSA regional-office areas comes from general knowledge and is UNVERIFIED.
* **Verdict: rebuild** from STATE with one fixed assignment.

#### A_SBUSCR (FARS 2021-24): school-bus-related crash. CRASH-CIRCUMSTANCE

* 1 = any vehicle A_SBUS ∈ {1, 2}; else 2. Agreement is 100% (153,273 crashes). Share 0.21-0.28%.
* For 2016-20 it can be rebuilt from A_SBUS.

#### BIA, SPJ_INDIAN, INDIAN_RES, TRACT, CENSUS_2020_TRACT_FIPS (FARS). PRE-CRASH (location)

* **SPJ_INDIAN** = 1 iff SP_JUR = 3 "Indian Reservation". Agreement is 100%. Share 0.33-0.76%.
* **INDIAN_RES** = 1 iff BIA = 1 or SPJ_INDIAN = 1. Agreement is 100%.
* **BIA** (0/1; 0.61-0.77% of crashes): **meaning UNVERIFIED.** It cannot be reproduced from SP_JUR, RD_OWNER, ROUTE
  or any other in-archive field:
  * 1,231 of 1,628 SP_JUR = 3 crashes have BIA = 1;
  * 989 crashes with SP_JUR = 0 have BIA = 1;
  * of crashes with RD_OWNER 62 "Bureau of Indian Affairs", 274 have BIA = 1 and 117 have BIA = 0.
  * The most plausible reading is a geospatial point-in-polygon flag for tribal or BIA lands computed from crash
    coordinates. That cannot be checked here.
* **TRACT** (2020-24) = 1 iff CENSUS_2020_TRACT_FIPS is non-null. Agreement is 100%.
* **CENSUS_2020_TRACT_FIPS** (2020-24) is an 11-character string. It is null in 918 crashes (216 / 140 / 239 / 142 /
  181 per year). Its first two digits equal STATE in 188,277 of 188,290 non-null rows; the 13 exceptions are
  UNVERIFIED (border geocoding).
* **Verdict:** SPJ_INDIAN and TRACT/FIPS are safe. Use BIA and INDIAN_RES only descriptively, with the caveat above.
  The tract is available only from 2020; 2016-19 has COUNTY (`acc_aux.COUNTY` = `accident.COUNTY`).

---

## 5. Differential missingness: summary tables

### 5.1 FARS (unweighted %, script `50_missing_fars.py`)

| unknown or missing (universe) | 2016 | 2019 | 2020 | 2024 | killed | survived |
|---|---|---|---|---|---|---|
| A_RESTUSE=3 (non-MC in-transport occupants) | 9.60 | 9.95 | 11.32 | 11.78 | 10.09 | 11.22 |
| A_HELMUSE=3 (MC riders) | 2.68 | 3.86 | 3.40 | 3.98 | 3.24 | 5.10 |
| A_EJECT=3 (occupants) | 0.89 | 1.01 | 1.29 | 1.27 | 0.68 | 1.55 |
| A_LOC=5 (non-occupants) | 1.85 | 1.56 | 1.92 | 1.26 | 1.57 | 2.11 |
| age unknown (all persons) | 2.22 | 2.18 | 2.81 | 2.55 | 0.37 | 4.24 |
| A_ALCTES 3/4/5 (drivers) | 53.42 | 56.41 | 58.42 | 63.89 | 34.42 | 77.55 |
| INJ_SEV 9 hidden in A_PERINJ=6 (all persons) | 1.62 | 1.26 | 1.52 | 1.52 | 0 | 2.76 |
| A_HISP=3 (fatalities only) | 7.58 | 7.89 | 11.40 | 18.94 | 9.45 | n/a |

| unknown or missing (vehicles) | 2016 | 2019 | 2020 | 2024 | occupant killed | no occupant death |
|---|---|---|---|---|---|---|
| A_IMP1=7 | 4.59 | 4.72 | 5.07 | 5.02 | 5.47 | 4.08 |
| A_MOD_YR 9998/9999 | 2.35 | 2.43 | 3.09 | 2.96 | 1.04 | 4.69 |
| A_BODY=9 | 2.76 | 2.83 | 4.00 | 3.58 | 2.33 | 4.40 |
| A_LIC_S=3 (non-MC) | 3.67 | 3.85 | 4.90 | 5.07 | 1.47 | 7.23 |
| SPEEDREL 8/9 hidden in A_SPVEH=2 | 5.07 | 4.26 | 6.01 | 6.11 | 5.84 | 5.26 |
| distraction unknown hidden in A_DRDIS=2 | 31.04 | 59.87 | 62.17 | 66.16 | 66.29 | 50.16 |
| impairment unknown hidden in A_DRDRO=2 | 26.97 | 41.20 | 42.16 | 50.10 | 51.20 | 31.90 |

| unknown (crashes) | 2016 | 2019 | 2020 | 2024 | 1 death | 2+ deaths |
|---|---|---|---|---|---|---|
| A_WEATHER=99 | 4.89 | 7.44 | 7.31 | 3.85 | 5.57 | 4.74 |
| A_POSBAC=3 | 54.29 | 57.32 | 58.75 | 64.74 | 59.58 | 49.70 |
| A_INTER=3 / A_ROADFC=7 | 0.49 | 0.49 | 0.57 | 0.98 | 0.54 | 0.32 |
| A_RU=3 | 0.35 | 0.32 | 0.43 | 0.90 | 0.42 | 0.25 |
| A_TOD=3 | 0.73 | 0.73 | 0.85 | 0.70 | 0.75 | 0.56 |
| A_JUNC=4, A_INTSEC=3, A_RELRD=6, A_MANCOL=7, A_DOW=3 | ≤ 0.31 in every year | | | | | |

### 5.2 CRSS (weighted %, script `51_missing_crss.py`)

The variables in the first group are imputed inside aux. The rate shown is the share of values that are imputed, by
severity.

| field behind the aux variable | 2016 | 2019 | 2020 | 2024 | K | A | B | C | O |
|---|---|---|---|---|---|---|---|---|---|
| INJ_SEV 9 → A_PERINJ | 4.36 | 3.73 | 4.43 | 4.38 | 5.79 | 10.24 | 5.10 | 6.84 | 3.78 |
| AGE 998/999 → A_AGE* | 6.45 | 6.30 | 8.80 | 6.76 | 5.53 | 6.01 | 4.23 | 5.94 | 7.47 |
| EJECTION 7/9 → A_EJECT (occupants) | 3.02 | 6.32 | 8.26 | 4.38 | 4.67 | 8.19 | 3.41 | 4.50 | 6.11 |
| A_RESTUSE=3, visible (non-MC occupants) | 9.25 | 9.80 | 11.59 | 12.49 | 16.61 | 18.84 | 9.76 | 11.02 | 10.62 |
| A_HELMUSE=3, visible (MC riders) | 9.05 | 9.36 | 9.00 | 12.30 | 3.39 | 6.65 | 6.88 | 9.81 | 20.30 |

| field behind the aux variable (by crash severity) | 2016 | 2019 | 2020 | 2024 | fatal | injury | PDO |
|---|---|---|---|---|---|---|---|
| IMPACT1 98/99 → A_IMP1 | 2.09 | 2.30 | 2.43 | 1.44 | 4.45 | 2.16 | 1.97 |
| MOD_YEAR 9998/9999 → A_MOD_YR | 4.36 | 4.34 | 4.97 | 4.72 | 3.48 | 4.09 | 4.95 |
| A_BODY=9 (visible) | 0.17 | 0.12 | 6.36 | 11.61 | 4.26 | 5.08 | 5.44 |
| SPEEDREL 8/9 hidden in A_SPVEH=2 | 4.38 | 1.57 | 1.73 | 3.14 | 4.57 | 2.49 | 2.75 |
| MAX_SEV 9 → A_CRAINJ | 3.32 | 2.62 | 3.37 | 2.78 | 3.44 | 3.24 | 2.90 |
| HOUR 99 → A_TOD/A_DOW | 0.19 | 0.84 | 0.85 | 0.92 | 1.33 | 0.45 | 0.82 |
| RELJCT2 98/99 → A_JUNC/A_INTSEC | 0.74 | **28.75** | 0.20 | 0.18 | 5.66 | 4.13 | 4.77 |
| MAN_COLL 98/99 → A_MANCOL | 0.34 | 0.41 | 0.18 | 0.24 | 0.42 | 0.37 | 0.33 |
| WEATHER 98/99 → A_WEATHER (2020+) | n/a | n/a | 5.65 | 3.68 | 3.00 | 3.92 | 3.98 |

**Reading the tables.** The direction of dependence on severity differs by variable:

* restraint unknown is higher for K/A;
* helmet unknown is higher for O;
* FARS age, licence and model-year unknowns are higher for survivors or vehicles without a death;
* FARS distraction and impairment unknowns are higher for vehicles with a death.

There is no single "missing at random" assumption that holds across the aux variables. Each analysis needs its own
missingness handling, such as multiple imputation with outcome in the model, or bounds.

---

## 6. Coding and definitional breaks (summary)

| variable | source | when | what changed | evidence |
|---|---|---|---|---|
| A_RESTUSE | both | 2019→2020 | new code 4 (not applicable). MC riders move from 2 to 4; non-occupants move from 3 to 4 | R 100%; TVD 17.2 pp (FARS), 2.9 pp (CRSS w) |
| A_HELMUSE | both | 2018→2019 | source moves from REST_USE to HELM_USE; car occupants with REST_USE 8/97 no longer "helmeted" (artefact share 18-25% FARS, about 90% CRSS of code-1 rows) | R 100%; TVD 9.2 / 13.1 pp |
| A_HELMUSE | both | 2019→2020 | universe restricted to MC riders; code 4 added | TVD 92.8 / 99.2 pp |
| A_BODY | both | 2019→2020 | vPIC body class overrides BODY_TYP (wagons/hatchbacks to utility; unknowns to 9); CRSS stops using imputed BDYTYP_IM | FD; agreement with 2016-19 map 96.1% (FARS), 87.7% (CRSS) |
| A_LT, A_MC | both | 2020 | inherit the A_BODY change | R 100% from A_BODY |
| A_MC_L_S | FARS | 2019→2020 | L_COMPL 2 (no valid licence for class) moves from 2 to 3 | R ≥ 99.998%; code 3 1.0% → 31.6% |
| A_RELRD | both | 2019→2020 | REL_ROAD 7 (parking lane) moves from 4 to 1; CRSS REL_ROAD 12 moves from 6 to 4 | R 100% |
| A_POSBAC | FARS | 2019→2020 | positivity threshold moves from BAC ≥ .01 to ≥ .001 | R 100% with year-specific threshold |
| A_REGION | FARS | 2020→2021 | Connecticut moves from region 2 to region 1 | R 100% |
| A_HR | CRSS | 2019→2020 | imputed HITRUN_IM replaced by raw HIT_RUN | R 100%; TVD 2.6 pp |
| A_TOWED | FARS | – (exists 2021+) | source TOWED loses the "reason" codes 2/3/7 from 2022; aux harmonises to yes/no | R 100% |
| A_DRDIS / A_DIST | FARS | 2017→2018 | MDRDSTRD code 1 ("looked but did not see") exists only 2016-17 and is not counted as distraction; unknown share 31% → 66% over 2016-2024 | R 100% |
| A_WEATHER, A_DIST | CRSS | 2020 | variables first appear in CRSS acc_aux | availability matrix |
| A_WRONGWAY(DRV), TRACT, FIPS | FARS | 2020 | new variables | availability matrix |
| A_SBUSCR, A_TOWED | FARS | 2021 | new variables | availability matrix |
| A_IMP2 | FARS | 2016-19 | column present but 100% null; dropped 2020 | null count |
| A_RCAT / A_HRACE | FARS | 2018→2019 | race source moves to the multi-row `race` table; redaction codes from 2020 | crosstab |
| A_JUNC / A_INTSEC | CRSS | 2019 only | not a rule change: 28.75% of RELJCT2 not reported and imputed, which shifts the distribution | TVD 6.9 / 7.4 pp |

No break was found at 2018→2019 for any CRSS aux variable other than A_HELMUSE, and the A_JUNC shift is an imputation
effect, not a rule change.

---

## 7. CRSS 2016-2018 (unlabelled years) and cross-source label transfer

* The aux tables carry **no label columns in any source or year**, so there are no "CRSS 2019+ aux labels" to transfer.
  The code meanings in this appendix were reconstructed from the labelled main-table fields.
* For every CRSS aux variable the same reconstruction rule gives **100% agreement in 2016, 2017 and 2018 and in 2019**.
  The only exceptions are the rules that the data show changed (A_HELMUSE moves REST_USE → HELM_USE at 2019; A_RELRD
  REL_ROAD 12 is 2018-19-specific). The CRSS source codes used by those rules in 2016-18 were checked through the same
  identities, and the year-to-year TVD at 2017→2018 and 2018→2019 is ≤ 2.2 pp for every CRSS aux variable except
  A_HELMUSE and A_JUNC (explained above).
* **Conclusion:** the reconstructed meanings apply to CRSS 2016-2018 aux codes unchanged, except A_HELMUSE (REST_USE
  rule) and A_RELRD code 6.
* FARS and CRSS share the same *codes* for: A_PTYPE, A_RESTUSE, A_HELMUSE, A_AGE1-9 (except that FARS has a final
  unknown code), A_BODY, A_IMP1 (FARS has 7 = unknown), A_SPVEH, A_VROLL, A_CT, A_D*, A_DOW, A_TOD, A_HR, A_LT, A_MC,
  A_PED, A_PEDAL, A_ROLL, A_SPCRA, A_MANCOL, A_JUNC, A_INTSEC, A_RELRD and A_WEATHER.
* They **differ** for A_PERINJ (killed flag vs KABCO), A_CRAINJ (fatal = 1 vs 4), A_LOC (different groupings), A_INTER
  (FUNC_SYS vs INT_HWY) and A_EJECT (no unknown in CRSS).
* In CRSS most aux variables are imputed, while in FARS they keep explicit unknowns. Pooling FARS and CRSS aux codes
  without accounting for this mixes observed and imputed data.

---

## 8. Cross-cutting findings

1. **The aux files are deterministic recodes, not independent data.** The only exception is BIA, and A_VRD partly.
   Using an aux flag together with its source field in one model double-counts the same information.
2. **"Year-consistent" is false for at least 10 variables** (§6). The breaks cluster at 2020, the year FARS/CRSS added
   vPIC fields, the `crashrf`, `driverrf` and `weather` tables, the HELM_USE universe and the new restraint
   not-applicable code.
3. **CRSS aux variables are mostly imputed.** They hide 2-9% imputed values for injury, age, ejection, impact, model
   year and severity, and 28.75% for junction in 2019. They should be treated as single-imputation products. Variance
   estimates from them understate uncertainty.
4. **Unknown folded into "No"** (speed, distraction, drowsiness, rollover NA, ejection NA, fire not-reported, FARS
   injury unknown) makes the "No" category heterogeneous. For distraction and drowsiness the unknown share grows
   strongly over time and differs by severity. Trends in A_DIST and A_DROWSY are therefore not interpretable.
5. **Outcome-conditioned recording:** race and ethnicity are coded for fatalities only. BAC testing (A_ALCTES,
   A_POSBAC) depends heavily on the outcome: 34% vs 78% without a usable result. These must not be used as covariates
   in killed-vs-survived comparisons.
6. **2024 looks provisional** for death-certificate and toxicology fields: A_HISP unknown 18.9%, A_RCAT unknown
   15.9%, killed drivers with BAC not reported 26.3%. All roughly double 2023. Release status is UNVERIFIED.
7. **Large FARS row increase in 2021** (39,785 crashes vs 35,935 in 2020) is mirrored exactly in aux. It is not an aux
   issue.

---

## 9. Recommendations: use directly vs rebuild

| category | variables |
|---|---|
| **Safe to use directly** (deterministic, no break, unknown explicit or none) | A_PTYPE; A_AGE1-9 (FARS; set the last code to missing); A_D* flags; A_CT; A_TOD; A_DOW; A_MANCOL; A_IMP1 (FARS); A_VROLL; A_ROLL; A_PED; A_PEDAL; A_PED_F; A_PEDAL_F; A_DOA; A_FIRE_EXP (inverted coding); A_CDL_S; A_LIC_C; A_LIC_S (set 3 to missing, 4 = MC); A_SBUS; A_POLPUR; A_ROADFC; A_RU; A_INTER (within source); A_JUNC/A_INTSEC (FARS; CRSS outside 2019); A_WRONGWAYDRV/A_WRONGWAY (2020+); A_TOWED (2021+); A_HISP and A_RCAT (fatality analyses only); SPJ_INDIAN; TRACT/FIPS |
| **Usable with documented restriction** | A_RESTUSE (restrict to PER_TYP 1/2/9 and BODY_TYP not 80-84/87-89; set 3 to missing); A_HELMUSE (restrict to MC riders; set 3 to missing); A_EJECT (occupants only; FARS 3 to missing); A_SPVEH/A_SPCRA ("speeding reported" flag); A_VRD/A_RD (NHTSA definition, 99.6% reproducible); A_ALCTES (no usable result is outcome-dependent); A_WEATHER (renumbered codes) |
| **Rebuild from source** | A_BODY (and A_LT, A_MC) — vPIC break; A_MC_L_S — 2020 break; A_RELRD — 2020 break; A_POSBAC — threshold break; A_REGION — CT break; A_LOC — differs between sources; A_PERINJ and A_CRAINJ — different code schemes, CRSS imputed; A_DRDIS/A_DIST and A_DRDRO/A_DROWSY — unknown folded into No; A_HRACE — code 8 is mixed; A_HELMUSE 2016-18 — artefact; A_MOD_YR — sentinel 9998/9999 in FARS, imputed in CRSS; all CRSS imputed aux variables when observed-only data are needed |
| **Do not use** | A_IMP2 (empty); BIA (meaning UNVERIFIED) except descriptively |

Implementable recipes are given in the structured summary that accompanies this appendix, field `harmonised_variables`.
Their logic is restated briefly:

* **Restraint (person):**
  * Universe: PER_TYP ∈ {1, 2, 9} and BODY_TYP ∉ {80-84, 87-89}.
  * Mapping from REST_USE: {1, 2, 3, 4, 6, 8, 10, 11, 12, 97} → used; {0, 5, 7, 16, 17, 19, 20} → not used;
    {29, 98, 99} → missing.
  * This is the A_RESTUSE map. The pre-2019 helmet codes for ATV and other non-MC riders become "not used", which
    matches how the same riders appear in 2020+ (REST_USE 20 → A_RESTUSE 2).
* **Helmet (person):**
  * Universe: BODY_TYP 80-89 and PER_TYP ∈ {1, 2, 9}.
  * 2016-18 from REST_USE: {5, 16, 19} → used (→ not used if REST_MIS = 1); 17 → not used; {29, 98, 99} → missing;
    {8, 97} → missing (ambiguous; 17 of 17,742 MC riders in FARS 2016-18 and 13 of 8,673 in CRSS); other codes (20, belt codes) → not used.
  * 2019+ from HELM_USE: {5, 16, 19} → used (→ not used if HELM_MIS = 1); {17, 20} → not used; {98, 99} → missing.
* **Body class:** BODY_TYP with the §4.2 table (2016-19 mapping) for every year and both sources. Set 98/99 to
  missing; in CRSS consider 9/49/79 unknown too.
* **Distraction (vehicle):** 1 if any code is positive; 0 if any code is 0 and there is no positive code; missing if
  the codes are only 96/99; not applicable if 16 (no driver).
* **Drowsy driver (vehicle):** 1 if DRIMPAIR 2; 0 if DRIMPAIR 0 or another known impairment and no 2; missing if only
  98/99; not applicable if 95.
* **Relation to road:** REL_ROAD 1, 7, 11 → on roadway; 2 → shoulder; 3 → median; 4, 5, 6, 8, 10, 12 → off roadway;
  98, 99 → missing. This is the 2020+ convention, applied to all years.
* **Positive BAC (crash):** drivers only; ALC_RES 10-940 or 998 → positive (threshold .01, the 2016-19 convention);
  all drivers 0-9 → negative; otherwise missing.

---

## 10. Open questions and UNVERIFIED items

1. **BIA**: the flag's definition (presumably a geospatial tribal-land indicator) cannot be reconstructed from the
   archive.
2. **Official labels and names** of every aux code. All meanings here are reconstructed. In particular, the
   non-standard A_WEATHER numbering (5 unused; 6, 10-15, 99) and the A_CRAINJ fatal = 1 (FARS) vs 4 (CRSS) codes
   could not be confirmed against documentation.
3. **A_VRD residual 0.43%** (2,167 vehicles over 9 years, mostly ACC_TYPE 2/7). The exact NHTSA rule for vehicles
   whose departure is followed by a non-harmful or rollover event on the roadway is unknown.
4. **Residual 25 FARS rows** for A_RESTUSE/A_HELMUSE in 2020-24 (BODY_TYP 85/89/99 edge cases). NHTSA probably uses
   a motorcycle definition based on something other than BODY_TYP alone, for example vPIC or A_BODY. Not resolved.
5. **Residual crashes**: A_DIST (10 FARS, 16 CRSS), A_POLPUR (10), A_MC (3 FARS, 1 CRSS), A_PEDAL (74 CRSS),
   A_SBUS (22 vehicles). The cause is unknown and probably record-level edits after the aux file was generated.
6. **Whether 2024 FARS is a final file.** Unknown race, ethnicity and BAC roughly double in 2024.
7. **The 2020 changes** in CRSS A_HR (+2.6 pp) and the FARS/CRSS restraint-use level (−4 pp "used" inside a fixed
   universe) look real rather than coding effects, but this cannot be proven from the data.
8. **13 tract FIPS codes** whose state prefix differs from STATE.
9. **Region naming** (NHTSA regional offices) comes from general knowledge.

---

## 11. Scripts and outputs

All scripts are in
`scripts/audit/aux_derived/`.
Outputs are written to `/tmp/nhtsa-audit/out_aux/`. Run each script from the repository root with
`POLARS_MAX_THREADS=2 uv run python <script>`.

| script | purpose |
|---|---|
| helpers.py, lab.py | join helper (`aux_main`), crosstabs, the per-year agreement function, label lookup from codebook.csv |
| 01_distributions.py, 02_pivot.py | code distributions of every aux column per source-year (`aux_dist.csv`, `aux_pivot.txt`) |
| 03_joins.py | 1:1 join verification and equality of shared columns (`joins.csv`) |
| 10-17_*.py | person-level exploration and reconstruction (restraint, helmet, age, alcohol, race); final rules in `16_person_rules.py` |
| 20-27_*.py | vehicle-level exploration and reconstruction (body/vPIC FD, licence, school bus, towed, distraction, drowsy, roadway departure, wrong way); final rules in `24_veh_rules.py`, `26_vrd2.py`, `27_ww.py` |
| 30-34_*.py | crash-level exploration and reconstruction; final rules in `33_crash_rules.py` and `34_posbac2.py`; region and REL_ROAD breaks in `31_relrd_region.py` |
| 40_tvd.py | year-to-year TVD for every aux variable, CRSS weighted (`tvd.csv`) |
| 50_missing_fars.py, 51_missing_crss.py | missing and unknown rates by year and severity, including hidden imputation (`missing_*.csv`) |
| 52_misc.py, 53_junc2019.py, 54_body_map.py, 55_harmonised_check.py | redaction and helmet artefact checks; CRSS 2019 junction imputation; A_BODY mapping tables; break-free check of the harmonised restraint and helmet recodes |
| 56_driver_age_hr.py | FARS driver age unknown vs hit-and-run |
