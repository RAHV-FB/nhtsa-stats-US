# Variable harmonisation

How every analytic variable is made comparable across 2016–2024 and between FARS and CRSS.
The executable definitions are in `src/nhtsa_stats/processing/harmonize.py` (code mappings)
and `processing/features.py` (aggregation to crash/vehicle/person level); a generated
catalogue of every mapping, with its docstring, is in
[`docs/generated/harmonised_variables.md`](generated/harmonised_variables.md). The evidence
behind each decision is in the domain audit appendices under [`docs/audit/`](audit/).

## 1. Principles

1. **Meanings come from the archives.** Value labels embedded in the CSVs (`<VAR>NAME`
   columns, harvested to `outputs/audit/codebook.csv`) define codes. Where labels are absent —
   CRSS 2016–2018 and all auxiliary tables — meanings are established by (a) identical code
   sets with labelled years, (b) distributional similarity, and (c) cross-tabulation against
   labelled fields. Codes that cannot be verified are marked UNVERIFIED in the appendices and
   are not used.
2. **CRSS 2016–2018 labels**: use the *same-year FARS* labels (the two systems share element
   definitions), and CRSS 2019+ labels only for variables without a 2016/2017/2019 break. For
   every analytic variable the 2016–2018 code set is a subset of the labelled code set
   (`docs/audit/person_injury_restraint.md` §6.2, `crash_environment.md` §5).
3. **Unknown is never "no".** Not reported / unknown / not applicable codes map to an explicit
   `unknown` (or `not_applicable`) category, or to null in tri-state indicators.
4. **Breaks are handled where they occur, not averaged away**: by grouping codes so that the
   group is stable, by restricting the population for which a code is meaningful, by using a
   consistently defined alternative field, or by excluding the variable from trend claims.
5. **Timing class for leakage control**: every variable is registered as pre-crash, crash
   circumstance, post-crash or outcome (`harmonize.REGISTRY`).
6. **Same concept, same recipe in both sources**; where FARS and CRSS measure *different*
   concepts (CRSS urbanicity is the sampling area; FARS rural/urban is the road), they are
   kept apart.

## 2. Harmonised analytic variables

| Variable | Level | Source fields (both sources unless noted) | Harmonised categories | Breaks / issues handled | Reliability |
|---|---|---|---|---|---|
| `fatal`, `ka`, `injury`, `kabco` | crash / person | CRSS crash `MAXSEV_IM`, CRSS person `INJSEV_IM`; FARS `INJ_SEV` | K; K+A; any injury; ordinal O–K. Codes 5 (injured, severity unknown), 6 (died before crash), 8 → null | Imputation fills only unknown codes (person 9). Weighted imputed fatal total = FARS within 0.9% every year; unimputed `MAX_SEV` falls 0.6–12.8% short (year-dependent) | High |
| `fatal_cc`, `ka_cc`; `killed_cc`, `killed_or_serious_cc` | crash / person | CRSS `MAX_SEV`, `INJ_SEV` | Strict complete case: crash negative only if no person has `INJ_SEV` 9 (and, for KA, 5); ~8% of crashes null | Sensitivity only: levels and trends differ from the imputed outcome | — |
| `light`, `dark` | crash | `LGT_COND` | daylight / dawn-dusk / dark-lit / dark-unlit / dark-unknown lighting / unknown | Code 6 drifts upward slowly; no break | High |
| `weather` | crash | `WEATHER` | clear / cloudy / rain (incl. freezing) / snow-sleet / fog / other / unknown | FARS 2016–19 `WEATHER1/2`; 2020+ multi-row `weather` table — the crash-level `WEATHER` field is available all years in both sources and used throughout | Medium (CRSS 3–6% unknown) |
| `surface` | crash (from vehicles) | `VSURCOND` | dry / wet (incl. water) / snow-ice-slush / other / unknown | CRSS vehicle-level "not reported" rises every year from 2020: 6.3% (2020), 9.1%, 9.4%, 9.5%, 12.5% (2024); crash-level unknown 1.2% (2016) → 3.2% (2020) → 6.4% (2024) → explicit unknown level; not interpretable as a trend | High (when known) |
| `speed_limit` | crash (max over vehicles) | `VSPD_LIM` | ≤25 / 30–35 / 40–45 / 50–55 / 60–65 / 70+ / no statutory limit (non-trafficway) / unknown | Code 0 kept separate from unknown | High (CRSS unknown 14%) |
| `tod`, `night`, `weekend` | crash | `HOUR`, `DAY_WEEK` | 5 time bands; night = 21:00–05:59; Sat/Sun | 2020 month distribution distorted by COVID (not used) | High |
| `junction` | crash | `RELJCT2` | non-junction / intersection(-related) / driveway / interchange / other / unknown | **CRSS 2019: 28% not reported, concentrated among non-junction crashes**; CRSS `RELJCT1`/`TYP_INT` unusable before 2020/2022 → only `RELJCT2` groups used, year effects in models, no CRSS junction trends | Medium (CRSS), high (FARS) |
| `work_zone` | crash | `WRK_ZONE` | yes / no | 0 conflates "none" and "not recorded" (UNVERIFIED) | Medium |
| `interstate` | crash | CRSS `INT_HWY`; FARS `FUNC_SYS`=1 | yes / no / unknown | Different source fields; not compared across sources | Medium |
| `urbanicity` | crash | CRSS `URBANICITY` | urban / rural *area* (PSU) | Not the road; not comparable with FARS `RUR_URB` | High as defined |
| `rural` | crash | FARS `RUR_URB` | rural / urban road | FARS urban share drifts 52.5% → 59.9%; use with year terms | Medium |
| `region` | crash | CRSS `REGION` | 4 census regions | FARS `A_REGION` is *not* census region (10 groups) — not used | High |
| `collision`, `crash_type`, `n_vehicles` | crash | `MAN_COLL`, `HARM_EV`, `REL_ROAD`, `VE_FORMS`, person types | crash-type hierarchy: pedestrian > cyclist > single vehicle (rollover first / off roadway / on roadway) > multi-vehicle (head-on / angle / rear-end / sideswipe / other) | `MAN_COLL` 0 relabelled 2019 (cosmetic); `HARM_EV` 72 scope change 2018 (minor) | High |
| `speeding`, `veh_speeding` | crash / vehicle | `SPEEDREL` | yes (2–5) / no (0) / unknown (8 "no driver present / unknown if driver present", 9) | Codes stable; ascertainment depends strongly on severity (FARS records more than CRSS for the same fatal crashes); unknown is 64% hit-and-run crashes | Medium (direction), low (magnitude) |
| `alcohol_im` | crash | CRSS `ALCHL_IM` | yes / no | Equals `ALCOHOL` in 99.998% of known rows; **but** pre-2019 non-reports were coded "No" and never imputed, so imputed prevalence among O-crashes rises at 2019 → period-specific sensitivity analysis | Medium |
| `alcohol` | crash | CRSS `ALCOHOL` | yes / no / unknown | **2019 coding break**: unknown 12–14% → 32–40%; unknown is outcome-dependent (47% of fatal crashes) → sensitivity only | Low for trends |
| `driver_bac08_prob`, `p_p08` | crash / person | FARS `midrvacc` A1–A10, `miper` P1–P10 | mean over 10 implicates of BAC ≥ .08 g/dL | Implicates in hundredths, `ALC_RES` in thousandths (verified 99.97%); FARS 2024 toxicology incomplete (~26% killed drivers not reported) | High (FARS) |
| `drugs` | crash / person | `DRUGS` (police) | yes / no / unknown | **2019–2020 breaks**; unknown 40–70%; testing selective; presence ≠ impairment → descriptive only, never a model exposure | Low |
| `distracted` | vehicle / crash | `distract.MDRDSTRD` (2016–19) → `DRDISTRACT` (2020+) | yes / no (0) / unknown (16 "no driver present / unknown if driver present", 96, 99) | Column renamed 2020 (same codes); code 1 only 2016–17; unknown rose 25% → 50%+ (non-fatal) and 36% → 74% (fatal) 2017–2020 → not used as a model exposure | Low |
| `young_driver`, `older_driver` | crash | CRSS driver `AGE_IM` (NHTSA-imputed); FARS driver `AGE` | any driver 15–20 / 65+ (tri-state) | Reported age is unknown for 9.6% of CRSS crashes' drivers, and 92% of those crashes are hit-and-run: an 'unknown' level would adjust for leaving the scene (post-crash) by proxy, so CRSS uses the imputed age (unknown 0.05%). FARS has no imputed age (998/999 → unknown) | High |
| `body` | vehicle | `BODY_TYP` | car / SUV / van / pickup / other light truck / light vehicle of unknown type (49) / bus / medium-heavy truck / motorcycle / truck of unknown type (73, 79) / other / unknown (98, 99) | Pickup codes 30–32 merged into 34 (2017) — absorbed by grouping. Code 49 rises from 0.7% to ~3.7% of CRSS light-vehicle occupants from 2018 and code 79 to ~1.1% of vehicles in 2022–24, so both are kept apart from the known groups (light passenger vehicles = car, SUV, van, pickup, other light truck, unknown light type); aux `A_BODY` breaks in 2020 (not used) | High (known groups) |
| `veh_age`, `veh_age_band` | vehicle | `YEAR − MOD_YEAR` | 0–3 / 4–7 / 8–12 / 13–17 / 18+ / unknown | −1 → 0; ≤ −2 and 9998/9999 → missing | High |
| `any_motorcycle`, `any_heavy_truck`, `any_light_truck` | crash | vehicle `body` | tri-state presence flags: unknown when no vehicle confirms the category and some vehicle's body type cannot rule it out (~3–4% of crashes have a vehicle of unknown body type, mostly hit-and-run) | — | High |
| `restraint` | person | `REST_USE` + `BODY_TYP` + `SEAT_POS` | belted / none / child restraint / not applicable / unknown — **defined only for vehicles with BODY_TYP 1–79 in seat rows 1–4** | 2016 codes 0/7 merged into 20 in 2017; helmet codes left `REST_USE` in 2019 (from 2019 every motorcyclist has 20 = "not applicable"); CRSS code 8 declines (within "belted") | Medium (survivor self-report) |
| `helmet` | person | `REST_USE` (2016–18) / `HELM_USE` (2019+) | helmet / none / unknown / not applicable | Field move in 2019 handled by year | Medium |
| `seat`, `role` | person | `SEAT_POS`, `PER_TYP` | front-left / front-other / second row / third+ / cargo-exterior; driver / front passenger / rear passenger / other | `PER_TYP` 8 vs 11–13 split only 2020–21 (non-motorists) | High |
| `ejected`, `airbag_deployed`, `rollover`, `fire` | person / vehicle | `EJECTION`, `AIR_BAG`, `ROLLOVER`, `FIRE_EXP` | post-crash consequences (never covariates) | `AIR_BAG` 2016 codes 0/28; `ROLLOVER` recoded 2022 (1/2/9 → 3; 8 added) | — |
| `culp_c1` (QIE, primary) | driver | `SPEEDREL`, `P_CRASH2`, driver factors `DR_SF1-4` (2016–19) / `driverrf` (2020+), `distract` 1 (2016–17) | culpable: speeding, culpable pre-crash event class, or common error code (6, 8, 102, 103, 36, 50, 51, 58; looked-but-did-not-see); non-culpable: none of these, SPEEDREL = 0, non-culpable/neutral pre-crash event, no 'unknown' driver-factor code; else undetermined | driver factor 99/999 unknown codes (999 only 2020–21; folded into 0 'None noted' from 2022); 2023 split of code 8 into 102/103 | Medium |
| `culp_viol` (QIE, sensitivity) | driver | `violatn.MVIOLATN` (2016–19) / `VIOLATION` (2020+) | any moving violation charged / none / unknown | **outcome-dependent** (dead drivers are rarely charged); column rename 2020 | Low for QIE |
| `striking` (non-motorists) | person | person `STR_VEH` → vehicle `BODY_TYP` | car / SUV / pickup / van / large / motorcycle / other | linked for 100% of CRSS non-motorists | High |
| `location` (non-motorists) | person | `LOCATION` | intersection crosswalk / intersection other / mid-block / other / unknown | code set stable 2016–2024 in both sources | High |

## 3. Coding breaks catalogue

| Year | Source | Variable | Nature | Handling |
|---|---|---|---|---|
| 2017 | both | `REST_USE` 0/7 → 20 | merge of "none" with "not applicable" | restraint defined only in belted seats of belt-equipped vehicles |
| 2017 | both | `BODY_TYP` 30/31/32 → 34 | pickup merge | grouped |
| 2017 | both | `AIR_BAG` 0 → 20 | "not applicable" absorbed into "not deployed" | post-crash; mapped for completeness |
| 2017–2020 | CRSS | distraction | unknown share rises steeply | excluded from models and trends |
| 2017–2021 | CRSS | `RELJCT1`, `TYP_INT` | heavy non-reporting | not used |
| 2019 | CRSS | `RELJCT2` | 28% not reported | unknown level; year effects; no junction trends |
| 2019 | CRSS | `ALCOHOL`, `VEH_ALCH`, `DRINKING` | non-reports move from "No" to "Unknown" | imputed version + period sensitivity |
| 2019–2020 | CRSS | `DRUGS` | unknown jumps | descriptive only |
| 2019 | both | helmet codes leave `REST_USE` | field move | `helmet_use` by year |
| 2020 | both | distract/factor/maneuver/violatn/vision column renames; `crashrf`, `driverrf`, `weather` tables introduced | renames | coalesced |
| 2020 | CRSS | `VSURCOND` "not reported" 6% | reporting | unknown level |
| 2022 | both | `ROLLOVER` recode; `DEFORMED` 8 → 7 | recode | post-crash only |
| 2023 | FARS | `ROUTE` restructure | recode | not used |
| 2024 | FARS | toxicology "not reported" ~26% of killed drivers | incomplete | 2024 BAC flagged |

## 4. Where FARS and CRSS differ for the same concept

The share of *fatal* crashes with each attribute was compared between CRSS (weighted) and
FARS (census) — the same population measured by two processes
(`outputs/tables/measurement/fars_crss_fatal_composition.csv`). Darkness, pedestrian and
motorcycle involvement, single-vehicle crashes and young-driver involvement agree within CRSS
confidence intervals. Speeding-related (CRSS 21% vs FARS 27%), unknown speed limit (6.7% vs
3.3%) and unknown junction (5.4% vs 0.2%) do not: FARS coding draws on fuller investigation.
CRSS-based severity associations for these variables are therefore interpreted with the
measurement analysis in mind.
