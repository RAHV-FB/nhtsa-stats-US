# Variable harmonisation

How every analytic variable is made comparable across 2016–2024 and between FARS and CRSS.
The executable definitions are in `src/nhtsa_stats/processing/harmonize.py` (code mappings)
and `processing/features.py` (aggregation to crash/vehicle/person level); a generated
catalogue of every mapping, with its docstring, is in
[`docs/generated/harmonised_variables.md`](generated/harmonised_variables.md). The evidence
behind each decision was recorded in per-topic audit notes, now preserved in Git history at
commit 7ee597e; the consolidated audit is `docs/audit_2026-11.md`.

## 1. Principles

1. **Meanings come from the archives.** Value labels embedded in the CSVs (`<VAR>NAME`
   columns, harvested to `outputs/audit/codebook.csv`, written by `nhtsa inventory`, not tracked in Git) define codes. Where labels are absent —
   CRSS 2016–2018 and all auxiliary tables — meanings are established by (a) identical code
   sets with labelled years, (b) distributional similarity, and (c) cross-tabulation against
   labelled fields. Codes that cannot be verified are marked UNVERIFIED in the appendices and
   are not used.
2. **CRSS 2016–2018 labels**: use the *same-year FARS* labels (the two systems share element
   definitions), and CRSS 2019+ labels only for variables without a 2016/2017/2019 break. For
   every analytic variable the 2016–2018 code set is a subset of the labelled code set
   (person, injury and restraint audit note §6.2 and crash environment audit note §5; Git history, commit 7ee597e).
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
| `fatal`, `ka`, `injury`, `kabco` | crash / person | CRSS crash `MAXSEV_IM`, CRSS person `INJSEV_IM`; FARS `INJ_SEV` | K; K+A; any injury; ordinal O–K. `fatal` = 0 for codes 5 (injured, severity unknown), 6 (died before crash) and 8 (no person involved): a crash death has code 4. `ka` = 0 for 6 and 8 but stays null for 5 (that person may have had an A injury). Only person code 9 stays null. See section 5 | Imputation fills only unknown codes (person 9). Weighted imputed fatal total = FARS within 0.9% every year; unimputed `MAX_SEV` falls 0.6–12.8% short (year-dependent) | High |
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
| `distracted` | vehicle / crash | `distract.MDRDSTRD` (2016–19) → `DRDISTRACT` (2020+) | yes / no (0) / unknown (16 "no driver present / unknown if driver present", 96, 99) | Column renamed 2020 (same codes); code 1 'looked but did not see' (2016–17 only) → not distracted, section 5; unknown rose 25% → 50%+ (non-fatal) and 36% → 74% (fatal) 2017–2020 → not used as a model exposure | Low |
| `young_driver`, `older_driver` | crash | CRSS driver `AGE_IM` (NHTSA-imputed); FARS driver `AGE` | any driver 15–20 / 65+ (tri-state) | Reported age is unknown for 9.6% of CRSS crashes' drivers, and 92% of those crashes are hit-and-run: an 'unknown' level would adjust for leaving the scene (post-crash) by proxy, so CRSS uses the imputed age (unknown 0.05%). FARS has no imputed age (998/999 → unknown) | High |
| `body` | vehicle | `BODY_TYP` | car / SUV / van / pickup / other light truck / light vehicle of unknown type (49) / bus / medium-heavy truck / motorcycle / truck of unknown type (73, 79) / other / unknown (98, 99) | Pickup codes 30–32 merged into 34 (2017) — absorbed by grouping. Code 49 rises from 0.7% to ~3.7% of CRSS light-vehicle occupants from 2018 and code 79 to ~1.1% of vehicles in 2022–24, so both are kept apart from the known groups (light passenger vehicles = car, SUV, van, pickup, other light truck, unknown light type); aux `A_BODY` breaks in 2020 (not used) | High (known groups) |
| `veh_age`, `veh_age_band` | vehicle | `YEAR − MOD_YEAR` | 0–3 / 4–7 / 8–12 / 13–17 / 18+ / unknown | −1 → 0; ≤ −2 and 9998/9999 → missing | High |
| `any_motorcycle`, `any_heavy_truck`, `any_light_truck` | crash | vehicle `body` | tri-state presence flags: unknown when no vehicle confirms the category and some vehicle's body type cannot rule it out (~3–4% of crashes have a vehicle of unknown body type, mostly hit-and-run) | — | High |
| `restraint` | person | `REST_USE` + `BODY_TYP` + `SEAT_POS` | belted / none / child restraint / not applicable / unknown — **defined only for occupants of vehicles with BODY_TYP 1–79 in seat rows 1–4 (SEAT_POS 11–49) or an unrecorded seat (SEAT_POS 98/99); everyone else is not applicable** | 2016 codes 0/7 merged into 20 in 2017; helmet codes left `REST_USE` in 2019 (from 2019 every motorcyclist has 20 = "not applicable"); CRSS code 8 declines (within "belted") | Medium (survivor self-report) |
| `helmet` | person | `REST_USE` (2016–18) / `HELM_USE` (2019+) | helmet / none / unknown / not applicable — defined for motorcycle riders (BODY_TYP 80–89) only; everyone else is not applicable | Field move in 2019 handled by year | Medium |
| `seat`, `role` | person | `SEAT_POS`, `PER_TYP` | front-left / front-other / second row / third+ / cargo-exterior; driver / front_passenger / rear_passenger / cargo_exterior_passenger / passenger_seat_unknown (SEAT_POS 98/99) / non-occupant person types | `PER_TYP` 8 vs 11–13 split only 2020–21 (non-motorists) | High |
| `ejected`, `airbag_deployed`, `rollover`, `fire` | person / vehicle | `EJECTION`, `AIR_BAG`, `ROLLOVER`, `FIRE_EXP` | post-crash consequences (never covariates) | `AIR_BAG` 2016 codes 0/28; `ROLLOVER` recoded 2022 (1/2/9 → 3; 8 added; 8 → 0 for motorcycle bodies only, else null, section 5) | — |
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
(`outputs/tables/measurement/fars_crss_fatal_composition.csv`, pooled 2016–2024). Darkness,
pedestrian involvement and single-vehicle crashes agree within CRSS confidence intervals.
Motorcycle involvement (CRSS 13.9% vs FARS 15.5%) and young-driver involvement (14.0% vs 12.4%;
CRSS uses imputed, FARS reported driver age) do not. Nor do speeding-related (CRSS 20% vs FARS
27%), unknown speed limit (7.5% vs 3.0%) and unknown junction (5.7% vs 0.2%): FARS coding draws
on fuller investigation.
CRSS-based severity associations for these variables are therefore interpreted with the
measurement analysis in mind.

## 5. Recode corrections from the year-by-year label audit

Effects below are from a scratch rebuild (`NHTSA_DATA_DIR` copy of `data/interim`) compared with
the previous `data/processed`. Run `uv run nhtsa features` to refresh `data/processed`.

1. **CRSS `fatal` for `MAXSEV_IM` 5, 6, 8** (`harmonize.fatal`, `features.build_crss`). A crash with a
   crash death has maximum severity 4, so 5 (1,808 crashes), 6 (20) and 8 "No person involved" (157)
   hold none and `fatal` is 0 (was null; no null remains). `ka` is 0 for 6 and 8 and null for 5.
   Person `killed` (`INJSEV_IM`/`INJ_SEV` 5) is 0 (CRSS 2,836 persons at `INJSEV_IM` 5; nulls 2,867 → 0),
   `killed_or_serious` likewise. Complete-case `fatal_cc`/`ka_cc` follow the same rule when no person is
   INJ_SEV 9. Weighted fatal share (`WEIGHT`), old → new: 2016 0.5123% → 0.5094% (old overstated by
   0.56%), 2017 0.48%, 2018 0.42%, 2019 0.39%, 2020 0.34%, 2021 0.20%, 2022 0.21%, 2023 0.22%,
   2024 0.21% (relative overstatement). The old denominator dropped the 1,985 crashes.
2. **`distracted`** (`harmonize.distraction_flag`). Code 1 "Looked but did not see" exists only in 2016–17
   (FARS 701 vehicle rows, CRSS 1,324) and is now not distracted, like 2018+. A driver with any other
   distraction code stays distracted. Weighted CRSS driver share: 2016 9.99% → 9.06%, 2017 11.18% →
   10.50%; FARS persons (killed or not) 2016 10.16% → 9.33%, 2017 13.20% → 11.85%. 2018+ unchanged.
3. **FARS `ROLLOVER` 8 "Not applicable"** (2022–24, 18,799 vehicles; `harmonize.rollover_flag`).
   All carry `BODY_TYP` 80–89 (motorcycles, mopeds, scooters; `UNITTYPE` 1), which cannot roll over and
   which 2016–21 coded 0, so they remain 0 (explicitly, by body type); code 8 on any other body is null.
   Passenger vehicles with two front-seat occupants affected: 0 (no vehicle-level difference).
4. **`PREV_SUS1`** (`harmonize.fars_prior_suspensions`). FARS 2016–17 hold one `PREV_SUS` (all suspensions
   combined; 1 in 3,605 drivers in 2016) while 2018+ `PREV_SUS1/2/3` count by type (1 in 112 drivers), so
   they are not harmonised: 2016–17 are explicitly null (no change from the loader's silent fill).
   Consumers: only `analysis/deaths.py` reads the field (from `data/interim`, `PREV_SUS1-3`) and guards it
   with `YEAR >= 2018` (`prior_suspension`); `processing/features.py` carries it into `fars_person`, read
   by nothing else in `src/` or `app/`.
5. **`crss_driver.hit_and_run_right`** was a join-suffix duplicate of the crash-level flag; no code in
   `src/`, `app/` or `tests/` reads it (only the generated `docs/generated/processed_datasets.md` lists
   it). Removed from `drivers.CRSS_CRASH_COLS`; `hit_and_run` there is the vehicle-level flag.
6. **FARS `ALC_RES` 800–895** (10 persons; 178 in 500–939, none exceed 930) are probable entry errors. No
   code uses BAC as a continuous value: all uses are presence of a result, or thresholds at .08
   (`bac_measured`, `bac08_measured`, `m_bac08`). No plausibility cap is applied; document only. Add one
   (for example null above .50) if any mean or high-BAC band is introduced.
