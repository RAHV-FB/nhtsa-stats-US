<!-- Generated from reports/templates/road_deaths.md by `nhtsa analyze report`; every number is looked up in outputs/tables. Edit the template, not this file. -->

# Where US road deaths concentrate: FARS 2016–2024

*Every number in this report is read from `outputs/tables/` when it is rendered
(`nhtsa analyze report`); each section names its source tables. Estimate types: **observed**
(FARS census counts, no sampling error), **estimated (MI)** (averaged over NHTSA's ten blood
alcohol imputations, with an imputation standard error in the tables), **survey estimate** (CRSS,
design-based 95% confidence intervals) and **model-based** (lives that belts or helmets would
have been expected to save). Nothing here is a causal effect of a policy.*

This report starts from the deaths themselves rather than from crash severity: which
behaviours, people, vehicles and places account for the 353,706
people killed on US public roads from 2016 to 2024. It is the basis of the public website
(`website/`). The severity models behind `reports/findings.md` answer a different question (how
much more likely a police-reported crash is to be fatal under given circumstances) and are cited
here where they add the size of an association.

## Summary

1. **59.6% of deaths involved at least one of
   four behaviours** that road-safety policy targets: a driver at a blood alcohol concentration
   of .08 or more (29.9%), a
   speeding-related crash (27.9%), an unbelted
   car, SUV, pickup or van occupant (26.7%) or
   an unhelmeted motorcyclist (5.3%).
2. **Between 27.4% and 39.4% of the people
   killed in drunk-driving crashes were not the drunk driver**: the lower figure counts only drivers
   with a measured blood alcohol result, the higher adds drivers whose BAC NHTSA imputed. Of the
   drivers at .08 or more, 40.8% have an imputed rather than a measured BAC.
   37.4% of those
   killed in speeding crashes were not the speeding driver.
3. **Drunk drivers in fatal crashes were heavily impaired and often unlicensed, but seldom had a
   recent conviction**: 66.3%
   were at .15 or more and 23.7%
   had no valid licence, but only 7.4%
   had a DWI conviction on record from the previous five years
   (9.5% among drivers with a measured BAC, 4.1% among imputed).
4. **48.6% of passenger-vehicle
   occupants killed with known belt use were unbelted.** On the project's within-vehicle
   effectiveness estimates, up to about 6,900
   of them a year (average of 2016–2024) would have been expected to survive had they been belted
   (model-based), as recorded and excluding the 20,998 deaths with unknown belt use.
   The figure depends heavily on how accurately belt use is recorded: about
   4,000 if one in ten belted survivors was
   misrecorded and 500 if one in five. It
   also applies a front-seat estimate to deaths of which 61% were in single-occupant vehicles, where
   no within-vehicle comparison exists.
5. **Pedestrian deaths are concentrated** on the roadway away from intersections
   (72.6%), in darkness
   (only 19.9% in daylight) and on
   arterial roads; 23.1% were
   hit-and-runs.
6. **Vehicle age**: occupants of vehicles 18 or more years old had an adjusted risk of death in a
   police-reported crash 2.22 (1.99–2.48)
   times that of occupants of vehicles 0–3 years old (1.76 (1.59–1.94) when the
   crash type and number of vehicles are also held fixed), and their share of occupant deaths rose
   from 18.0% (2016) to
   30.5% (2024).
7. **The 2019–2021 rise was among the steepest for risky driving** (deaths in crashes with a driver
   without a valid licence +44.0%,
   drunk driving +33.4%,
   all deaths +18.9%). By 2024
   passenger-vehicle occupant deaths were +1.5%
   against 2019, motorcyclist deaths +23.5%
   and pedestrian deaths +12.9%.

---

## 1. Data and definitions

*Module `src/nhtsa_stats/analysis/deaths.py`; tables `outputs/tables/deaths/`.*

* **Population.** Every person with `INJ_SEV` = 4 in the FARS person files 2016–2024
  (353,706; 36,355
  in 2019, 43,230 in 2021,
  39,254 in 2024).
* **NHTSA analytical definitions** from the FARS auxiliary files, verified by cross-tabulation
  against the labelled main-file variables: person type `A_PTYPE`, vehicle body `A_BODY`
  (passenger vehicles = cars, pickups, SUVs, vans and other light trucks), belt use `A_RESTUSE`,
  helmet use `A_HELMUSE`, speeding-related crash `A_SPCRA`, speeding vehicle `A_SPVEH`, large truck
  `A_LT`, rural/urban `A_RU`, time of day `A_TOD`, road function class `A_ROADFC`, hit-and-run
  `A_HR`.
* **Alcohol.** A drunk-driving (alcohol-impaired-driving) crash has a driver with imputed blood
  alcohol concentration of .08 or more in NHTSA's multiple imputation (`MIDRVACC`; person level
  `MIPER`). Every alcohol quantity is computed in each of the ten implicates and averaged; the
  tables give the imputation standard error sqrt((1 + 1/10) B). Crashes without an imputation
  record count as not alcohol-impaired.
* **Driver records** (`L_STATUS`, `PREV_DWI`, `PREV_SPD`, `PREV_ACC`, `PREV_SUS1–3`) come from
  state driver files: convictions, suspensions and crashes in the five years before the crash.
  Suspensions are coded from 2018 only. Unknown codes are excluded from each share's base.
* **Victim roles.** For the deaths in a group of crashes, the "risk vehicle" is the vehicle whose
  driver was at .08 or more (per implicate), the vehicle police coded as speeding, or the large
  truck. Each death is classed as that vehicle's driver, its passenger, an occupant of another
  vehicle, a pedestrian or cyclist, or another non-occupant.

## 2. Four behaviours

*Sources: `deaths/behaviour_summary`, `deaths/behaviour_overlap`, `deaths/segments`.*

| Behaviour | Deaths 2016–2024 | Share of all deaths | Deaths with no other of the four |
|---|---|---|---|
| alcohol | 105,821 | 29.9% | 39,640 |
| speeding | 98,693 | 27.9% | 37,320 |
| unbelted | 94,400 | 26.7% | 38,382 |
| unhelmeted | 18,789 | 5.3% | 8,316 |
| any | 210,946 | 59.6% | — |
| none | 142,760 | 40.4% | — |

The four shares sum to 89.8% of
deaths against a union of 59.6% (overcount
ratio 1.51).
35.0% of deaths involved exactly one,
19.2% exactly two and
5.5% three. Crashes with both a
drunk driver and speeding (not necessarily by the same driver) accounted for
11.4% of deaths. The union is a lower bound in one respect, because belt use is unknown for
5.9% of all deaths.

*Relation to earlier tables.* `contributions/fars_overlap_summary` (Phase 2) reports a union of
four factors that includes "driver drug-positive (determinate crashes only)". Drug testing is
selective and differs by state (`docs/limitations.md`), so this report leaves drugs out and adds
unhelmeted motorcyclists, the other victim-protection behaviour that is recorded at the scene. Its
alcohol and speeding counts are identical to that table's.

Distraction-affected crashes (8.3% of deaths)
and drowsy driving (1.8%) are coded but rarely
established after a crash; they are not counted.

## 3. Drunk driving

*Sources: `deaths/victim_roles`, `deaths/driver_records`.*

105,821 deaths (estimated (MI); about
11,800 a year) were in crashes with a
driver at .08 or more.

| Role | Deaths | Share |
|---|---|---|
| risk_driver | 64,112 | 60.6% |
| risk_passenger | 13,669 | 12.9% |
| other_vehicle_occupant | 16,225 | 15.3% |
| pedestrian_or_cyclist | 11,318 | 10.7% |
| other_nonoccupant | 498 | 0.5% |
| not_risk_driver | 41,709 | 39.4% |

Who was killed depends on how the drunk driver is identified. Of the drivers at .08 or more,
40.8% have a BAC that NHTSA imputed rather than a measured test result
(`deaths/driver_bac_imputed_share`). Restricting to measured results (`deaths/victim_roles_bac_basis`),
the share of deaths who were not the drunk driver is lower. Neither basis is a proven bound on the
true share. The measured-only figure is plausibly too low, because surviving drunk drivers are tested
less often than killed ones, so measured cases over-represent drivers who died; the all-BAC figure
depends on NHTSA's undocumented imputation model. The two bases show how much the answer depends on
the choice, not a range that contains the truth:

| BAC basis | Role | Deaths | Share |
|---|---|---|---|
| all_bac_measured_and_imputed | total | 105,821 | 100.0% |
| all_bac_measured_and_imputed | risk_driver | 64,112 | 60.6% |
| all_bac_measured_and_imputed | risk_passenger | 13,669 | 12.9% |
| all_bac_measured_and_imputed | other_vehicle_occupant | 16,225 | 15.3% |
| all_bac_measured_and_imputed | pedestrian_or_cyclist | 11,318 | 10.7% |
| all_bac_measured_and_imputed | other_nonoccupant | 498 | 0.5% |
| all_bac_measured_and_imputed | not_risk_driver | 41,709 | 39.4% |
| all_bac_measured_and_imputed | outside_risk_vehicle | 28,040 | 26.5% |
| measured_bac_only | total | 65,323 | 100.0% |
| measured_bac_only | risk_driver | 47,434 | 72.6% |
| measured_bac_only | risk_passenger | 7,555 | 11.6% |
| measured_bac_only | other_vehicle_occupant | 7,929 | 12.1% |
| measured_bac_only | pedestrian_or_cyclist | 2,202 | 3.4% |
| measured_bac_only | other_nonoccupant | 203 | 0.3% |
| measured_bac_only | not_risk_driver | 17,889 | 27.4% |
| measured_bac_only | outside_risk_vehicle | 10,334 | 15.8% |

Drivers in fatal crashes, by blood alcohol (share of drivers with a known record):

| Indicator | BAC .08 or more | Drivers with known status |
|---|---|---|
| licence_invalid | 23.7% | 96,248 |
| unlicensed | 9.0% | 96,248 |
| suspended_or_revoked | 12.2% | 96,248 |
| expired_or_cancelled | 2.5% | 96,248 |
| prior_dwi | 7.4% | 95,411 |
| prior_speeding | 21.4% | 95,411 |
| prior_suspension | 20.1% | 75,665 |
| prior_crash | 19.0% | 89,788 |
| bac_15_plus | 66.3% | 100,692 |

| Indicator | BAC zero | Drivers with known status |
|---|---|---|
| licence_invalid | 11.6% | 366,045 |
| unlicensed | 4.8% | 366,045 |
| suspended_or_revoked | 5.2% | 366,045 |
| expired_or_cancelled | 1.5% | 366,045 |
| prior_dwi | 1.8% | 363,505 |
| prior_speeding | 17.3% | 363,503 |
| prior_suspension | 10.4% | 285,419 |
| prior_crash | 17.5% | 340,024 |
| bac_15_plus | 0.0% | 378,020 |

The same shares for drivers at .08 or more by how the BAC was obtained (`deaths/driver_records_measured_bac`):

| BAC basis | Indicator | Share | Drivers with known status |
|---|---|---|---|
| bac_08_plus_all | licence_invalid | 23.7% | 96,248 |
| bac_08_plus_all | prior_dwi | 7.4% | 95,411 |
| bac_08_plus_all | prior_speeding | 21.4% | 95,411 |
| bac_08_plus_measured_only | licence_invalid | 25.7% | 59,048 |
| bac_08_plus_measured_only | prior_dwi | 9.5% | 58,507 |
| bac_08_plus_measured_only | prior_speeding | 22.7% | 58,507 |
| bac_08_plus_imputed_only | licence_invalid | 20.4% | 37,200 |
| bac_08_plus_imputed_only | prior_dwi | 4.1% | 36,904 |
| bac_08_plus_imputed_only | prior_speeding | 19.5% | 36,904 |

Only 7.4% of drunk
drivers had a DWI conviction in the five years before the crash
(1.8% of drivers with no
alcohol). Driver records count convictions, not arrests, and can miss out-of-state offences and
offences reduced by plea, so this share is a lower bound on prior impaired driving. Among drivers
with a measured BAC the share is higher (9.5%, against
4.1% for imputed BAC), which may reflect testing being more likely when the
police suspect a driver. Even so, most drunk drivers in fatal crashes had no recent conviction for
programmes aimed at convicted drivers to act on.

## 4. Seat belts

*Sources: `deaths/restraint`, `deaths/potential_lives`, `matched/belt_effect`.*

| Dimension | Level | Occupants killed | Belt use known | Unbelted (of known) | Lower bound | Upper bound |
|---|---|---|---|---|---|---|
| overall | all | 215,277 | 194,279 | 48.6% | 43.9% | 53.6% |
| time_of_day | day | 109,528 | 101,043 | 41.4% | 38.1% | 45.9% |
| time_of_day | night | 104,138 | 91,828 | 56.3% | 49.7% | 61.5% |
| time_of_day | unknown | 1,611 | 1,408 | 64.8% | 56.6% | 69.2% |
| vehicle | car | 113,715 | 102,205 | 44.8% | 40.3% | 50.4% |
| vehicle | pickup | 39,394 | 35,867 | 60.1% | 54.7% | 63.7% |
| vehicle | suv | 52,393 | 47,418 | 49.1% | 44.4% | 53.9% |
| vehicle | van | 9,467 | 8,514 | 42.2% | 38.0% | 48.0% |
| vehicle | other_light_truck | 308 | 275 | 62.2% | 55.5% | 66.2% |
| area | rural | 110,336 | 102,303 | 50.1% | 46.4% | 53.7% |
| area | urban | 104,431 | 91,545 | 46.8% | 41.1% | 53.4% |
| area | unknown | 510 | 431 | 62.4% | 52.7% | 68.2% |
| sex | male | 141,194 | 126,533 | 52.9% | 47.4% | 57.8% |
| sex | female | 73,878 | 67,602 | 40.6% | 37.1% | 45.6% |
| sex | unknown | 205 | 144 | 50.7% | 35.6% | 65.4% |
| age_band | <16 | 8,077 | 7,197 | 42.5% | 37.9% | 48.8% |
| age_band | 16-24 | 42,268 | 37,281 | 56.6% | 49.9% | 61.7% |
| age_band | 25-34 | 40,739 | 36,079 | 60.1% | 53.2% | 64.7% |
| age_band | 35-54 | 54,179 | 48,875 | 53.3% | 48.1% | 57.9% |
| age_band | 55-74 | 45,713 | 42,169 | 39.2% | 36.2% | 43.9% |
| age_band | 75+ | 23,927 | 22,440 | 26.1% | 24.5% | 30.7% |
| age_band | unknown | 374 | 238 | 49.2% | 31.3% | 67.6% |
| role | driver | 162,121 | 147,057 | 48.4% | 43.9% | 53.2% |
| role | passenger | 53,156 | 47,222 | 49.1% | 43.7% | 54.8% |

The bounds count every occupant with unknown belt use as belted (lower) or unbelted (upper).

*Lives belts would have saved (model-based).* The within-vehicle (double pair comparison)
effectiveness from `matched/belt_effect` is applied to the
94,400 unbelted
occupants killed. Because survivors who were unbelted are sometimes recorded as belted, the
estimate is shown under four recording scenarios (`misreport` = share of belted survivors assumed
misrecorded):

| Scenario | Effectiveness | Lives 2016–2024 | Per year (2016–2024 average) | Per year, low | Per year, high |
|---|---|---|---|---|---|
| as_recorded | 65.8% | 62,162 | 6,907 | 6,769 | 7,027 |
| misreport_5pct | 52.5% | 49,538 | 5,504 | 5,347 | 5,641 |
| misreport_10pct | 37.9% | 35,769 | 3,974 | 3,792 | 4,130 |
| misreport_20pct | 4.4% | 4,118 | 458 | 206 | 671 |

The "as recorded" row excludes the 20,998 killed occupants whose belt
use is unknown (9.8% of passenger-vehicle occupant deaths), who are in
neither the belted nor the unbelted count (`deaths/potential_lives_context`). Of the
94,400 unbelted deaths, 60.7%
were in vehicles with one recorded occupant, where no within-vehicle comparison exists.

The scenarios above are one-sided: they move only belted survivors. Misrecording can also run the other
way (unbelted-coded deaths who were truly belted). With 10% of belted survivors and 5% of unbelted-coded
deaths misrecorded, the effectiveness is 28% instead of
66%, and it vanishes at about
21%
misrecorded survivors alone (`matched/belt_misreporting_two_sided_dpc`). The pooled effectiveness also
averages very different crash types: from 51% in
multi-vehicle angle crashes to 84% in
single-vehicle rollovers (`matched/belt_by_crash_type`).

The effectiveness was estimated for drivers and right-front passengers aged 13 and over and is
applied to every seat and age. These are expectations for the people who died, not the effect of any policy.

## 5. Speed

*Sources: `deaths/victim_roles`, `deaths/driver_records`, `severity/fatal_speeding_type`.*

| Role | Deaths | Share |
|---|---|---|
| risk_driver | 61,811 | 62.6% |
| risk_passenger | 15,853 | 16.1% |
| other_vehicle_occupant | 15,134 | 15.3% |
| pedestrian_or_cyclist | 5,515 | 5.6% |
| other_nonoccupant | 380 | 0.4% |
| not_risk_driver | 36,882 | 37.4% |

In CRSS, crashes in which a driver exceeded the limit or was racing had an adjusted risk of being
fatal 5.22 (4.34–6.27)
times that of comparable crashes without speeding; "too fast for conditions" had
1.06 (0.89–1.26)
(model A of `reports/findings.md`, finding 3; the speeding-type split is exploratory, and the
"too fast for conditions" ratio is 1.29
when crash configuration is also held fixed, so it is a small association rather than none). Speeding drivers in fatal crashes had no valid
licence in 24.0% of cases
(drivers neither speeding nor at any BAC: 10.0%)
and a speeding conviction in the previous five years in
23.7%
(16.4%).

## 6. Pedestrians

*Sources: `deaths/pedestrians`, `vulnerable/pedestrian_killed_contrasts`.*

| Dimension | Level | Deaths | Share of pedestrian deaths |
|---|---|---|---|
| light | daylight | 12,101 | 19.9% |
| light | dark_lighted | 23,995 | 39.4% |
| light | dark_not_lighted | 21,214 | 34.8% |
| light | dark_unknown_lighting | 994 | 1.6% |
| light | dawn_dusk | 2,203 | 3.6% |
| light | other_unknown | 369 | 0.6% |
| location | at_intersection | 10,143 | 16.7% |
| location | midblock_roadway | 44,189 | 72.6% |
| location | roadside_shoulder_median_parking | 3,439 | 5.6% |
| location | sidewalk_or_off_road | 2,035 | 3.3% |
| location | unknown | 1,070 | 1.8% |
| road_class | interstate_freeway | 9,866 | 16.2% |
| road_class | principal_arterial | 23,349 | 38.4% |
| road_class | minor_arterial | 14,253 | 23.4% |
| road_class | collector | 6,887 | 11.3% |
| road_class | local | 6,054 | 9.9% |
| road_class | unknown | 467 | 0.8% |
| speed_limit | <=25 | 5,538 | 9.1% |
| speed_limit | 30-35 | 14,618 | 24.0% |
| speed_limit | 40-45 | 18,240 | 30.0% |
| speed_limit | 50-55 | 9,967 | 16.4% |
| speed_limit | 60+ | 9,192 | 15.1% |
| speed_limit | unknown | 3,321 | 5.5% |
| area | urban | 50,190 | 82.4% |
| area | rural | 10,240 | 16.8% |
| area | unknown | 446 | 0.7% |
| hit_and_run | yes | 14,044 | 23.1% |
| hit_and_run | no | 46,832 | 76.9% |
| pedestrian_bac | bac_08_plus | 18,230 | 29.9% |
| pedestrian_bac | under_08 | 42,646 | 70.1% |

`speed_limit` is the posted limit for the striking vehicle; `pedestrian_bac` is the pedestrian's
own imputed blood alcohol (estimated (MI)). In CRSS, the share of struck pedestrians who died rose
from 2.2%
on roads limited to 25 mph or less to 33.1%
at 50–55 mph (adjusted risk ratio 6.6 (4.8–9.0);
12.2 (9.1–16.5)
without adjustment for location, light and time of day). The striking vehicle's speed limit is unknown for
30% of struck pedestrians who survived
but only 11% of those who died
(`vulnerable/speed_limit_missingness`), so crude shares who died by limit are not comparable with the adjusted ratios.

## 7. Motorcycles

*Sources: `deaths/helmet`, `deaths/potential_lives`, `matched/double_pair_comparison`.*

| Dimension | Level | Killed | Helmet use known | Unhelmeted (of known) |
|---|---|---|---|---|
| overall | all | 51,254 | 49,589 | 37.9% |
| year | 2016 | 5,337 | 5,193 | 40.4% |
| year | 2017 | 5,226 | 5,081 | 38.6% |
| year | 2018 | 5,038 | 4,883 | 38.1% |
| year | 2019 | 5,044 | 4,867 | 38.4% |
| year | 2020 | 5,620 | 5,446 | 39.6% |
| year | 2021 | 6,144 | 5,944 | 40.0% |
| year | 2022 | 6,251 | 6,024 | 37.5% |
| year | 2023 | 6,366 | 6,147 | 35.3% |
| year | 2024 | 6,228 | 6,004 | 34.0% |
| role | rider | 48,541 | 46,978 | 37.0% |
| role | passenger | 2,713 | 2,611 | 53.2% |

In fatal crashes, among rider–passenger pairs on the same motorcycle, a helmet was associated with a
31% (20–40%)
reduction in the risk of death (`reduction_1_minus_rr`, double pair comparison). Applied to the
18,789 unhelmeted
motorcyclists killed, about 641
a year on average over 2016–2024 (417–835)
would have been expected to survive with a helmet (model-based); this excludes the
1,665 deaths with unknown helmet use.

Treat this figure with more caution than the seat-belt one:

* **It is fragile to misreporting** (`matched/helmet_misreporting_dpc`). If 5% of helmeted-coded survivors
  were in fact unhelmeted the reduction would be 4% (-9 to 14%);
  it vanishes at about 6%
  survivor misreporting, or 5%
  of unhelmeted-coded deaths who were truly helmeted.
* **It rests on few pairs and covers few of the deaths** (`matched/helmet_pair_coverage`). Only
  455 operator–passenger pairs differ in
  helmet use. 16% of the unhelmeted motorcyclist deaths were in
  an operator–passenger pair of any kind (not only the discordant pairs) and 84% were on single-rider motorcycles, so
  applying the estimate to all unhelmeted deaths assumes that riders with a passenger are representative of solo riders.
  (The 18,336 unhelmeted deaths in this coverage table differ from the
  18,789 in the potential-lives table because the matched module defines
  motorcycle and no helmet from the harmonised BODY_TYP 80–89 and REST_USE/HELM_USE codes, the deaths module from the
  FARS auxiliary variables A_BODY = 7 and A_HELMUSE = 2.)

## 8. Vehicles

*Sources: `person/lpv_killed_crude_vs_adjusted`, `deaths/vehicle_age`, `deaths/victim_roles`.*

Occupants of light passenger vehicles in police-reported crashes (CRSS), adjusted risk of death by
vehicle age (model A: occupant age, sex, seat role, belt use, vehicle body, the other vehicle's
body, and the pre-crash crash set; model B adds crash type and number of vehicles, which may
partly reflect the vehicle itself):

| Vehicle age | Crude rate | Crude RR | Adjusted RR, model A | Adjusted RR, model B |
|---|---|---|---|---|
| 0-3 | 0.097% | 1.00 | 1.00 (1.00–1.00) | 1.00 (1.00–1.00) |
| 4-7 | 0.134% | 1.38 | 1.25 (1.13–1.40) | 1.18 (1.06–1.32) |
| 8-12 | 0.161% | 1.66 | 1.35 (1.22–1.49) | 1.21 (1.09–1.34) |
| 13-17 | 0.269% | 2.77 | 1.81 (1.62–2.01) | 1.52 (1.37–1.67) |
| 18+ | 0.419% | 4.32 | 2.22 (1.99–2.48) | 1.76 (1.59–1.94) |
| unknown | 0.407% | 4.20 | 2.09 (1.03–4.22) | 2.19 (1.18–4.04) |

Share of passenger-vehicle occupants killed (known model year) by vehicle age, FARS:

| Year | Vehicle age | Deaths | Share |
|---|---|---|---|
| 2016 | 0-3 | 3,042 | 12.8% |
| 2016 | 4-7 | 2,813 | 11.8% |
| 2016 | 8-12 | 6,903 | 29.1% |
| 2016 | 13-17 | 6,715 | 28.3% |
| 2016 | 18+ | 4,272 | 18.0% |
| 2016-2024 | 0-3 | 27,452 | 12.8% |
| 2016-2024 | 4-7 | 33,562 | 15.6% |
| 2016-2024 | 8-12 | 47,122 | 21.9% |
| 2016-2024 | 13-17 | 54,728 | 25.5% |
| 2016-2024 | 18+ | 51,980 | 24.2% |
| 2019 | 0-3 | 3,022 | 13.5% |
| 2019 | 4-7 | 3,512 | 15.7% |
| 2019 | 8-12 | 4,683 | 21.0% |
| 2019 | 13-17 | 6,281 | 28.1% |
| 2019 | 18+ | 4,822 | 21.6% |
| 2024 | 0-3 | 2,630 | 11.6% |
| 2024 | 4-7 | 3,787 | 16.7% |
| 2024 | 8-12 | 5,116 | 22.6% |
| 2024 | 13-17 | 4,229 | 18.7% |
| 2024 | 18+ | 6,910 | 30.5% |

The rising 18+ share partly reflects the ageing of the fleet; FARS has no fleet counts.

Who died in crashes involving a large truck:

| Role | Deaths | Share |
|---|---|---|
| risk_driver | 7,064 | 15.0% |
| risk_passenger | 1,225 | 2.6% |
| other_vehicle_occupant | 33,478 | 71.0% |
| pedestrian_or_cyclist | 5,151 | 10.9% |
| other_nonoccupant | 257 | 0.5% |
| not_risk_driver | 40,111 | 85.0% |

That most of those killed were not the truck driver describes who was in the crash, not who was at fault.
The share mixes crashes between a truck and a passenger vehicle with single-truck crashes, and nothing in
this report attributes fault.

## 9. Change since 2019

*Source: `deaths/segments`. The 2019–2021 rises in risky-driving groups were among the steepest of the
groups shown; a ranking depends on how the groups are defined (the invalid-licence group combines
expired, cancelled, suspended, revoked and unlicensed drivers).*

| Group | 2019 | 2021 | 2024 | 2019→2021 | 2019→2024 | Type |
|---|---|---|---|---|---|---|
| all | 36,355 | 43,230 | 39,254 | +18.9% | +8.0% | observed |
| alcohol_impaired | 10,196 | 13,599 | 11,904 | +33.4% | +16.8% | estimated (MI) |
| speeding | 9,592 | 12,498 | 11,288 | +30.3% | +17.7% | observed |
| any_of_four | 20,864 | 26,725 | 23,234 | +28.1% | +11.4% | estimated (MI) |
| unbelted | 9,523 | 11,878 | 9,758 | +24.7% | +2.5% | observed |
| unhelmeted | 1,870 | 2,375 | 2,043 | +27.0% | +9.3% | observed |
| pv_occupants | 22,372 | 26,466 | 22,713 | +18.3% | +1.5% | observed |
| motorcyclists | 5,044 | 6,144 | 6,228 | +21.8% | +23.5% | observed |
| pedestrians | 6,272 | 7,470 | 7,080 | +19.1% | +12.9% | observed |
| cyclists | 859 | 976 | 1,103 | +13.6% | +28.4% | observed |
| large_truck_crash | 5,032 | 5,821 | 5,340 | +15.7% | +6.1% | observed |
| rural | 16,288 | 17,339 | 16,006 | +6.5% | −1.7% | observed |
| urban | 19,946 | 25,749 | 22,905 | +29.1% | +14.8% | observed |
| night | 18,573 | 23,242 | 20,971 | +25.1% | +12.9% | observed |
| hit_and_run | 2,037 | 2,917 | 2,758 | +43.2% | +35.4% | observed |
| invalid_licence_crash | 6,964 | 10,025 | 7,875 | +44.0% | +13.1% | observed |

The share of drivers in fatal crashes without a valid licence was
13.0% in
2019, 16.7%
in 2020 and 13.9%
in 2024 (`deaths/driver_records_by_year`). FARS has no exposure, so these are changes in counts,
not in risk per mile.

## 10. States

*Source: `deaths/states` (all states; the website has a sortable version).*

| State | Deaths 2016–2024 | 2019→2024 | Drunk driving | Speeding | Unbelted (known) | No helmet (known) | Pedestrians | Rural |
|---|---|---|---|---|---|---|---|---|
| AL | 8,755 | +3% | 28% | 27% | 58% | 13% | 12% | 59% |
| AK | 657 | +4% | 29% | 42% | 49% | 37% | 18% | 56% |
| AZ | 10,042 | +26% | 31% | 33% | 53% | 49% | 21% | 32% |
| AR | 5,296 | +18% | 26% | 23% | 54% | 60% | 11% | 63% |
| CA | 36,315 | +4% | 30% | 31% | 38% | 7% | 26% | 30% |
| CO | 5,971 | +15% | 30% | 36% | 54% | 57% | 14% | 40% |
| CT | 2,713 | +24% | 38% | 35% | 50% | 54% | 19% | 14% |
| DE | 1,156 | −5% | 27% | 30% | 47% | 37% | 22% | 40% |
| DC | 312 | +104% | 32% | 46% | 59% | 38% | 37% | 0% |
| FL | 29,743 | −1% | 26% | 10% | 45% | 48% | 22% | 24% |
| GA | 14,369 | −6% | 25% | 20% | 50% | 10% | 17% | 36% |
| HI | 942 | −6% | 34% | 46% | 52% | 63% | 27% | 17% |
| ID | 2,171 | +6% | 28% | 22% | 58% | 49% | 7% | 74% |
| IL | 10,425 | +17% | 32% | 38% | 46% | 66% | 16% | 34% |
| IN | 7,956 | +3% | 27% | 26% | 46% | 73% | 11% | 58% |
| IA | 3,157 | +6% | 32% | 21% | 45% | 73% | 7% | 72% |
| KS | 3,690 | −17% | 25% | 23% | 51% | 61% | 8% | 63% |
| KY | 6,923 | −3% | 23% | 17% | 52% | 65% | 11% | 66% |
| LA | 7,293 | +3% | 29% | 24% | 57% | 17% | 18% | 45% |
| ME | 1,437 | +13% | 32% | 28% | 52% | 66% | 10% | 80% |
| MD | 5,028 | +8% | 31% | 27% | 45% | 18% | 24% | 18% |
| MA | 3,321 | +8% | 33% | 30% | 62% | 6% | 20% | 7% |
| MI | 9,600 | +11% | 27% | 26% | 39% | 50% | 15% | 39% |
| MN | 3,700 | +31% | 26% | 28% | 38% | 67% | 11% | 57% |
| MS | 6,380 | +17% | 22% | 15% | 52% | 18% | 12% | 68% |
| MO | 8,687 | +8% | 28% | 37% | 63% | 31% | 12% | 52% |
| MT | 1,822 | +12% | 38% | 36% | 63% | 60% | 8% | 83% |
| NE | 2,100 | +1% | 29% | 19% | 62% | 12% | 8% | 70% |
| NV | 3,231 | +37% | 30% | 31% | 45% | 11% | 24% | 29% |
| NH | 1,114 | +32% | 32% | 40% | 69% | 65% | 10% | 54% |
| NJ | 5,589 | +20% | 23% | 24% | 45% | 11% | 29% | 11% |
| NM | 3,798 | −4% | 30% | 37% | 54% | 54% | 21% | 56% |
| NY | 9,546 | +18% | 30% | 32% | 37% | 14% | 26% | 30% |
| NC | 13,813 | +11% | 28% | 32% | 47% | 8% | 15% | 57% |
| ND | 929 | −10% | 36% | 26% | 61% | 74% | 7% | 84% |
| OH | 10,789 | 0% | 34% | 23% | 55% | 69% | 12% | 42% |
| OK | 6,120 | +1% | 26% | 26% | 53% | 65% | 12% | 61% |
| OR | 4,765 | +9% | 34% | 31% | 35% | 7% | 16% | 56% |
| PA | 10,450 | +6% | 28% | 40% | 58% | 52% | 15% | 45% |
| RI | 556 | −9% | 39% | 46% | 54% | 58% | 19% | 19% |
| SC | 9,494 | +3% | 34% | 41% | 53% | 66% | 16% | 59% |
| SD | 1,189 | +43% | 32% | 28% | 66% | 69% | 8% | 83% |
| TN | 10,614 | +5% | 26% | 17% | 48% | 9% | 13% | 42% |
| TX | 36,034 | +15% | 40% | 33% | 45% | 46% | 18% | 39% |
| UT | 2,546 | +12% | 22% | 30% | 44% | 50% | 14% | 42% |
| VT | 586 | +26% | 30% | 38% | 57% | 10% | 9% | 84% |
| VA | 7,910 | +10% | 29% | 31% | 55% | 6% | 14% | 55% |
| WA | 5,706 | +36% | 34% | 32% | 41% | 4% | 19% | 42% |
| WV | 2,458 | −2% | 24% | 28% | 52% | 39% | 9% | 63% |
| WI | 5,393 | +5% | 32% | 32% | 48% | 69% | 9% | 63% |
| WY | 1,115 | −27% | 30% | 36% | 59% | 58% | 6% | 81% |
| US | 353,706 | +8% | 30% | 28% | 49% | 38% | 17% | 43% |

Shares describe the composition of each state's deaths, not death rates. Speeding coding practice
differs between police agencies.

## 11. Limitations specific to this report

* **No exposure.** Counts and shares only; no rates per mile, trip or person.
* **Recording.** Behaviours are recorded after the crash and recorded differently by severity: killed
  drivers are tested far more often, while police-recorded alcohol, drug and distraction fields are more
  often unknown in fatal crashes. Belt and helmet use of survivors can be misrecorded, in either direction
  (sections 4 and 7); alcohol is imputed for untested drivers, and measured-BAC-only figures are shown
  where they differ (section 3).
* **Drivers' records** count convictions in the driver's state file and miss arrests, plea
  reductions and out-of-state offences.
* **Lives-saved figures are model-based** expectations for the people who died, using within-vehicle
  effectiveness estimates; they are not effects of a law, campaign or enforcement programme.
* **Associations.** A behaviour present in a fatal crash did not necessarily cause it.

See `docs/limitations.md` for the project-wide list.
