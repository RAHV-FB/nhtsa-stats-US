# Where US road deaths concentrate: FARS 2016–2024

*Every number in this report is read from `outputs/tables/` when it is rendered
(`nhtsa analyze report`); each section names its source tables. Estimate types: **observed**
(FARS census counts, no sampling error), **estimated (MI)** (averaged over NHTSA's ten blood
alcohol imputations, with an imputation standard error in the tables), **survey estimate** (CRSS,
design-based 95% confidence intervals) and **model-based** (lives that belts or helmets would
have been expected to save). Nothing here is a causal effect of a policy.*

This report starts from the deaths themselves rather than from crash severity: which
behaviours, people, vehicles and places account for the {{deaths/segments|segment=all|deaths|,.0f}}
people killed on US public roads from 2016 to 2024. It is the basis of the public website
(`website/`). The severity models behind `reports/findings.md` answer a different question (how
much more likely a police-reported crash is to be fatal under given circumstances) and are cited
here where they add the size of an association.

## Summary

1. **{{deaths/segments|segment=any_of_four|share_of_all|pct:1}} of deaths involved at least one of
   four behaviours** that road-safety policy targets: a driver at a blood alcohol concentration
   of .08 or more ({{deaths/segments|segment=alcohol_impaired|share_of_all|pct:1}}), a
   speeding-related crash ({{deaths/segments|segment=speeding|share_of_all|pct:1}}), an unbelted
   car, SUV, pickup or van occupant ({{deaths/segments|segment=unbelted|share_of_all|pct:1}}) or
   an unhelmeted motorcyclist ({{deaths/segments|segment=unhelmeted|share_of_all|pct:1}}).
2. **Between {{deaths/victim_roles_bac_basis|basis=measured_bac_only;group=alcohol_impaired;role=not_risk_driver|share_of_group|pct:1}} and {{deaths/victim_roles_bac_basis|basis=all_bac_measured_and_imputed;group=alcohol_impaired;role=not_risk_driver|share_of_group|pct:1}} of the people
   killed in drunk-driving crashes were not the drunk driver**: the lower figure counts only drivers
   with a measured blood alcohol result, the higher adds drivers whose BAC NHTSA imputed. Of the
   drivers at .08 or more, {{deaths/driver_bac_imputed_share|period=2016-2024|share_imputed|pct:1}} have an imputed rather than a measured BAC.
   {{deaths/victim_roles|group=speeding;role=not_risk_driver|share_of_group|pct:1}} of those
   killed in speeding crashes were not the speeding driver.
3. **Drunk drivers in fatal crashes were heavily impaired and often unlicensed, but seldom had a
   recent conviction**: {{deaths/driver_records|group=bac_08_plus;indicator=bac_15_plus|share|pct:1}}
   were at .15 or more and {{deaths/driver_records|group=bac_08_plus;indicator=licence_invalid|share|pct:1}}
   had no valid licence, but only {{deaths/driver_records|group=bac_08_plus;indicator=prior_dwi|share|pct:1}}
   had a DWI conviction on record from the previous five years
   ({{deaths/driver_records_measured_bac|group=bac_08_plus_measured_only;indicator=prior_dwi|share|pct:1}} among drivers with a measured BAC, {{deaths/driver_records_measured_bac|group=bac_08_plus_imputed_only;indicator=prior_dwi|share|pct:1}} among imputed).
4. **{{deaths/restraint|dimension=overall;level=all|unbelted_share|pct:1}} of passenger-vehicle
   occupants killed with known belt use were unbelted.** On the project's within-vehicle
   effectiveness estimates, up to about {{deaths/potential_lives|measure=seat_belts;scenario=as_recorded|lives_per_year|rnd:-2}}
   of them a year (average of 2016–2024) would have been expected to survive had they been belted
   (model-based), as recorded and excluding the {{deaths/potential_lives_context|metric=unknown_belt_use_deaths|deaths|,.0f}} deaths with unknown belt use.
   The figure depends heavily on how accurately belt use is recorded: about
   {{deaths/potential_lives|measure=seat_belts;scenario=misreport_10pct|lives_per_year|rnd:-2}} if one in ten belted survivors was
   misrecorded and {{deaths/potential_lives|measure=seat_belts;scenario=misreport_20pct|lives_per_year|rnd:-2}} if one in five. It
   also applies a front-seat estimate to deaths of which {{deaths/potential_lives_context|metric=unbelted_deaths_single_occupant_vehicle|share|pct:0}} were in single-occupant vehicles, where
   no within-vehicle comparison exists.
5. **Pedestrian deaths are concentrated** on the roadway away from intersections
   ({{deaths/pedestrians|dimension=location;level=midblock_roadway|share|pct:1}}), in darkness
   (only {{deaths/pedestrians|dimension=light;level=daylight|share|pct:1}} in daylight) and on
   arterial roads; {{deaths/pedestrians|dimension=hit_and_run;level=yes|share|pct:1}} were
   hit-and-runs.
6. **Vehicle age**: occupants of vehicles 18 or more years old had an adjusted risk of death in a
   police-reported crash {{person/lpv_killed_crude_vs_adjusted|population=lpv;outcome=killed;factor=veh_age_band;level=18+|A_adj_rr|ci:2}}
   times that of occupants of vehicles 0–3 years old ({{person/lpv_killed_crude_vs_adjusted|population=lpv;outcome=killed;factor=veh_age_band;level=18+|B_adj_rr|ci:2}} when the
   crash type and number of vehicles are also held fixed), and their share of occupant deaths rose
   from {{deaths/vehicle_age|YEAR=2016;band=18+|share|pct:1}} (2016) to
   {{deaths/vehicle_age|YEAR=2024;band=18+|share|pct:1}} (2024).
7. **The 2019–2021 rise was among the steepest for risky driving** (deaths in crashes with a driver
   without a valid licence {{deaths/segments|segment=invalid_licence_crash|pct_change_2019_2021|pctsign:1}},
   drunk driving {{deaths/segments|segment=alcohol_impaired|pct_change_2019_2021|pctsign:1}},
   all deaths {{deaths/segments|segment=all|pct_change_2019_2021|pctsign:1}}). By 2024
   passenger-vehicle occupant deaths were {{deaths/segments|segment=pv_occupants|pct_change_2019_2024|pctsign:1}}
   against 2019, motorcyclist deaths {{deaths/segments|segment=motorcyclists|pct_change_2019_2024|pctsign:1}}
   and pedestrian deaths {{deaths/segments|segment=pedestrians|pct_change_2019_2024|pctsign:1}}.

---

## 1. Data and definitions

*Module `src/nhtsa_stats/analysis/deaths.py`; tables `outputs/tables/deaths/`.*

* **Population.** Every person with `INJ_SEV` = 4 in the FARS person files 2016–2024
  ({{deaths/segments|segment=all|deaths|,.0f}}; {{deaths/segments|segment=all|deaths_2019|,.0f}}
  in 2019, {{deaths/segments|segment=all|deaths_2021|,.0f}} in 2021,
  {{deaths/segments|segment=all|deaths_2024|,.0f}} in 2024).
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

{{mdtable:deaths/behaviour_summary|row=alcohol~speeding~unbelted~unhelmeted~any~none|row:Behaviour:;deaths:Deaths 2016–2024:,.0f;share_of_all:Share of all deaths:pct:1;deaths_no_other_factor:Deaths with no other of the four:,.0f}}

The four shares sum to {{deaths/behaviour_summary|row=sum_of_factors|share_of_all|pct:1}} of
deaths against a union of {{deaths/behaviour_summary|row=any|share_of_all|pct:1}} (overcount
ratio {{deaths/behaviour_summary|row=sum_of_factors|overcount_ratio|.2f}}).
{{deaths/behaviour_summary|row=exactly_1|share_of_all|pct:1}} of deaths involved exactly one,
{{deaths/behaviour_summary|row=exactly_2|share_of_all|pct:1}} exactly two and
{{deaths/behaviour_summary|row=three_or_more|share_of_all|pct:1}} three. Crashes with both a
drunk driver and speeding (not necessarily by the same driver) accounted for
{{deaths/segments|segment=alcohol_and_speeding|share_of_all|pct:1}} of deaths. The union is a lower bound in one respect, because belt use is unknown for
{{deaths/segments|segment=restraint_unknown|share_of_all|pct:1}} of all deaths.

*Relation to earlier tables.* `contributions/fars_overlap_summary` (Phase 2) reports a union of
four factors that includes "driver drug-positive (determinate crashes only)". Drug testing is
selective and differs by state (`docs/limitations.md`), so this report leaves drugs out and adds
unhelmeted motorcyclists, the other victim-protection behaviour that is recorded at the scene. Its
alcohol and speeding counts are identical to that table's.

Distraction-affected crashes ({{deaths/segments|segment=distracted|share_of_all|pct:1}} of deaths)
and drowsy driving ({{deaths/segments|segment=drowsy|share_of_all|pct:1}}) are coded but rarely
established after a crash; they are not counted.

## 3. Drunk driving

*Sources: `deaths/victim_roles`, `deaths/driver_records`.*

{{deaths/segments|segment=alcohol_impaired|deaths|,.0f}} deaths (estimated (MI); about
{{deaths/segments|segment=alcohol_impaired|per_year|rnd:-2}} a year) were in crashes with a
driver at .08 or more.

{{mdtable:deaths/victim_roles|group=alcohol_impaired|role:Role:;deaths:Deaths:,.0f;share_of_group:Share:pct:1}}

Who was killed depends on how the drunk driver is identified. Of the drivers at .08 or more,
{{deaths/driver_bac_imputed_share|period=2016-2024|share_imputed|pct:1}} have a BAC that NHTSA imputed rather than a measured test result
(`deaths/driver_bac_imputed_share`). Restricting to measured results (`deaths/victim_roles_bac_basis`),
the share of deaths who were not the drunk driver is lower. Neither basis is a proven bound on the
true share. The measured-only figure is plausibly too low, because surviving drunk drivers are tested
less often than killed ones, so measured cases over-represent drivers who died; the all-BAC figure
depends on NHTSA's undocumented imputation model. The two bases show how much the answer depends on
the choice, not a range that contains the truth:

{{mdtable:deaths/victim_roles_bac_basis|group=alcohol_impaired|basis:BAC basis:;role:Role:;deaths:Deaths:,.0f;share_of_group:Share:pct:1}}

Drivers in fatal crashes, by blood alcohol (share of drivers with a known record):

{{mdtable:deaths/driver_records|group=bac_08_plus|indicator:Indicator:;share:BAC .08 or more:pct:1;n_known:Drivers with known status:,.0f}}

{{mdtable:deaths/driver_records|group=bac_zero|indicator:Indicator:;share:BAC zero:pct:1;n_known:Drivers with known status:,.0f}}

The same shares for drivers at .08 or more by how the BAC was obtained (`deaths/driver_records_measured_bac`):

{{mdtable:deaths/driver_records_measured_bac||group:BAC basis:;indicator:Indicator:;share:Share:pct:1;n_known:Drivers with known status:,.0f}}

Only {{deaths/driver_records|group=bac_08_plus;indicator=prior_dwi|share|pct:1}} of drunk
drivers had a DWI conviction in the five years before the crash
({{deaths/driver_records|group=bac_zero;indicator=prior_dwi|share|pct:1}} of drivers with no
alcohol). Driver records count convictions, not arrests, and can miss out-of-state offences and
offences reduced by plea, so this share is a lower bound on prior impaired driving. Among drivers
with a measured BAC the share is higher ({{deaths/driver_records_measured_bac|group=bac_08_plus_measured_only;indicator=prior_dwi|share|pct:1}}, against
{{deaths/driver_records_measured_bac|group=bac_08_plus_imputed_only;indicator=prior_dwi|share|pct:1}} for imputed BAC), which may reflect testing being more likely when the
police suspect a driver. Even so, most drunk drivers in fatal crashes had no recent conviction for
programmes aimed at convicted drivers to act on.

## 4. Seat belts

*Sources: `deaths/restraint`, `deaths/potential_lives`, `matched/belt_effect`.*

{{mdtable:deaths/restraint|dimension=overall~time_of_day~vehicle~area~sex~age_band~role|dimension:Dimension:;level:Level:;killed:Occupants killed:,.0f;known:Belt use known:,.0f;unbelted_share:Unbelted (of known):pct:1;share_if_unknown_protected:Lower bound:pct:1;share_if_unknown_unprotected:Upper bound:pct:1}}

The bounds count every occupant with unknown belt use as belted (lower) or unbelted (upper).

*Lives belts would have saved (model-based).* The within-vehicle (double pair comparison)
effectiveness from `matched/belt_effect` is applied to the
{{deaths/potential_lives|measure=seat_belts;scenario=as_recorded|deaths_without|,.0f}} unbelted
occupants killed. Because survivors who were unbelted are sometimes recorded as belted, the
estimate is shown under four recording scenarios (`misreport` = share of belted survivors assumed
misrecorded):

{{mdtable:deaths/potential_lives|measure=seat_belts|scenario:Scenario:;effectiveness:Effectiveness:pct:1;lives:Lives 2016–2024:,.0f;lives_per_year:Per year (2016–2024 average):,.0f;lives_per_year_low:Per year, low:,.0f;lives_per_year_high:Per year, high:,.0f}}

The "as recorded" row excludes the {{deaths/potential_lives_context|metric=unknown_belt_use_deaths|deaths|,.0f}} killed occupants whose belt
use is unknown ({{deaths/potential_lives_context|metric=unknown_belt_use_deaths|share|pct:1}} of passenger-vehicle occupant deaths), who are in
neither the belted nor the unbelted count (`deaths/potential_lives_context`). Of the
{{deaths/potential_lives_context|metric=unbelted_deaths|deaths|,.0f}} unbelted deaths, {{deaths/potential_lives_context|metric=unbelted_deaths_single_occupant_vehicle|share|pct:1}}
were in vehicles with one recorded occupant, where no within-vehicle comparison exists.

The scenarios above are one-sided: they move only belted survivors. Misrecording can also run the other
way (unbelted-coded deaths who were truly belted). With 10% of belted survivors and 5% of unbelted-coded
deaths misrecorded, the effectiveness is {{matched/belt_misreporting_two_sided_dpc|analysis=belt_driver_rf;survivor_misreport_f=0.1;death_misreport_g=0.05|reduction_1_minus_rr|pct:0}} instead of
{{matched/belt_misreporting_two_sided_dpc|analysis=belt_driver_rf;survivor_misreport_f=0;death_misreport_g=0|reduction_1_minus_rr|pct:0}}, and it vanishes at about
{{matched/belt_misreporting_two_sided_dpc|analysis=belt_driver_rf;survivor_misreport_f=0;death_misreport_g=0|tipping_f_given_g|pct:0}}
misrecorded survivors alone (`matched/belt_misreporting_two_sided_dpc`). The pooled effectiveness also
averages very different crash types: from {{matched/belt_by_crash_type|partition=crash type|min(dpc_reduction)|pct:0}} in
multi-vehicle angle crashes to {{matched/belt_by_crash_type|partition=crash type|max(dpc_reduction)|pct:0}} in
single-vehicle rollovers (`matched/belt_by_crash_type`).

The effectiveness was estimated for drivers and right-front passengers aged 13 and over and is
applied to every seat and age. These are expectations for the people who died, not the effect of any policy.

## 5. Speed

*Sources: `deaths/victim_roles`, `deaths/driver_records`, `severity/fatal_speeding_type`.*

{{mdtable:deaths/victim_roles|group=speeding|role:Role:;deaths:Deaths:,.0f;share_of_group:Share:pct:1}}

In CRSS, crashes in which a driver exceeded the limit or was racing had an adjusted risk of being
fatal {{severity/fatal_speeding_type|outcome=fatal;factor=speeding_type;level=exceeded_limit_or_racing|adj_rr|ci:2}}
times that of comparable crashes without speeding; "too fast for conditions" had
{{severity/fatal_speeding_type|outcome=fatal;factor=speeding_type;level=too_fast_for_conditions|adj_rr|ci:2}}
(model A of `reports/findings.md`, finding 3; the speeding-type split is exploratory, and the
"too fast for conditions" ratio is {{severity/speeding_type_models|outcome=fatal;model=B;level=too_fast_for_conditions|adj_rr|.2f}}
when crash configuration is also held fixed, so it is a small association rather than none). Speeding drivers in fatal crashes had no valid
licence in {{deaths/driver_records|group=speeding;indicator=licence_invalid|share|pct:1}} of cases
(drivers neither speeding nor at any BAC: {{deaths/driver_records|group=neither;indicator=licence_invalid|share|pct:1}})
and a speeding conviction in the previous five years in
{{deaths/driver_records|group=speeding;indicator=prior_speeding|share|pct:1}}
({{deaths/driver_records|group=neither;indicator=prior_speeding|share|pct:1}}).

## 6. Pedestrians

*Sources: `deaths/pedestrians`, `vulnerable/pedestrian_killed_contrasts`.*

{{mdtable:deaths/pedestrians|dimension=light~location~road_class~speed_limit~area~hit_and_run~pedestrian_bac|dimension:Dimension:;level:Level:;deaths:Deaths:,.0f;share:Share of pedestrian deaths:pct:1}}

`speed_limit` is the posted limit for the striking vehicle; `pedestrian_bac` is the pedestrian's
own imputed blood alcohol (estimated (MI)). In CRSS, the share of struck pedestrians who died rose
from {{vulnerable/pedestrian_killed_contrasts|victim=pedestrian;outcome=killed;factor=str_speed_limit;level=<=25|crude_rate|pct:1}}
on roads limited to 25 mph or less to {{vulnerable/pedestrian_killed_contrasts|victim=pedestrian;outcome=killed;factor=str_speed_limit;level=50-55|crude_rate|pct:1}}
at 50–55 mph (adjusted risk ratio {{vulnerable/pedestrian_killed_contrasts|victim=pedestrian;outcome=killed;factor=str_speed_limit;level=50-55|adj_rr|ci:1}};
{{vulnerable/pedestrian_speed_limit_adjustment|victim=pedestrian;outcome=killed;specification=without location, light and time of day;level=50-55|adj_rr|ci:1}}
without adjustment for location, light and time of day). The striking vehicle's speed limit is unknown for
{{vulnerable/speed_limit_missingness|victim=pedestrian;outcome=killed;group=not|estimate|pct:0}} of struck pedestrians who survived
but only {{vulnerable/speed_limit_missingness|victim=pedestrian;outcome=killed;group=fatal / outcome|estimate|pct:0}} of those who died
(`vulnerable/speed_limit_missingness`), so crude shares who died by limit are not comparable with the adjusted ratios.

## 7. Motorcycles

*Sources: `deaths/helmet`, `deaths/potential_lives`, `matched/double_pair_comparison`.*

{{mdtable:deaths/helmet|dimension=overall~year~role|dimension:Dimension:;level:Level:;killed:Killed:,.0f;known:Helmet use known:,.0f;unhelmeted_share:Unhelmeted (of known):pct:1}}

In fatal crashes, among rider–passenger pairs on the same motorcycle, a helmet was associated with a
{{matched/double_pair_comparison|analysis=motorcycle_helmet;misreport_fraction=0;component=combined (inverse-variance weighted)|reduction_1_minus_rr|cipct:0@reduction}}
reduction in the risk of death (`reduction_1_minus_rr`, double pair comparison). Applied to the
{{deaths/potential_lives|measure=helmets;scenario=as_recorded|deaths_without|,.0f}} unhelmeted
motorcyclists killed, about {{deaths/potential_lives|measure=helmets;scenario=as_recorded|lives_per_year|,.0f}}
a year on average over 2016–2024 ({{deaths/potential_lives|measure=helmets;scenario=as_recorded|lives_per_year_low|,.0f}}–{{deaths/potential_lives|measure=helmets;scenario=as_recorded|lives_per_year_high|,.0f}})
would have been expected to survive with a helmet (model-based); this excludes the
{{deaths/potential_lives_context|metric=unknown_helmet_use_deaths|deaths|,.0f}} deaths with unknown helmet use.

Treat this figure with more caution than the seat-belt one:

* **It is fragile to misreporting** (`matched/helmet_misreporting_dpc`). If 5% of helmeted-coded survivors
  were in fact unhelmeted the reduction would be {{matched/helmet_misreporting_dpc|analysis=motorcycle_helmet;survivor_misreport_f=0.05;death_misreport_g=0|reduction_1_minus_rr|cipct:0@reduction}};
  it vanishes at about {{matched/helmet_misreporting_dpc|analysis=motorcycle_helmet;survivor_misreport_f=0;death_misreport_g=0|tipping_f_given_g|pct:0}}
  survivor misreporting, or {{matched/helmet_misreporting_dpc|analysis=motorcycle_helmet;survivor_misreport_f=0;death_misreport_g=0|tipping_g_given_f|pct:0}}
  of unhelmeted-coded deaths who were truly helmeted.
* **It rests on few pairs and covers few of the deaths** (`matched/helmet_pair_coverage`). Only
  {{matched/helmet_pair_coverage|metric=pairs_discordant_helmet_use|count|,.0f}} operator–passenger pairs differ in
  helmet use. {{matched/helmet_pair_coverage|metric=unhelmeted_deaths_in_pair_design|share|pct:0}} of the unhelmeted motorcyclist deaths were in
  an operator–passenger pair of any kind (not only the discordant pairs) and {{matched/helmet_pair_coverage|metric=unhelmeted_deaths_single_rider_motorcycle|share|pct:0}} were on single-rider motorcycles, so
  applying the estimate to all unhelmeted deaths assumes that riders with a passenger are representative of solo riders.
  (The {{matched/helmet_pair_coverage|metric=unhelmeted_motorcyclist_deaths|count|,.0f}} unhelmeted deaths in this coverage table differ from the
  {{deaths/potential_lives_context|metric=unhelmeted_deaths|deaths|,.0f}} in the potential-lives table because the matched module defines
  motorcycle and no helmet from the harmonised BODY_TYP 80–89 and REST_USE/HELM_USE codes, the deaths module from the
  FARS auxiliary variables A_BODY = 7 and A_HELMUSE = 2.)

## 8. Vehicles

*Sources: `person/lpv_killed_crude_vs_adjusted`, `deaths/vehicle_age`, `deaths/victim_roles`.*

Occupants of light passenger vehicles in police-reported crashes (CRSS), adjusted risk of death by
vehicle age (model A: occupant age, sex, seat role, belt use, vehicle body, the other vehicle's
body, and the pre-crash crash set; model B adds crash type and number of vehicles, which may
partly reflect the vehicle itself):

{{mdtable:person/lpv_killed_crude_vs_adjusted|population=lpv;outcome=killed;factor=veh_age_band|level:Vehicle age:;rate:Crude rate:pct:3;crude_rr:Crude RR:.2f;A_adj_rr:Adjusted RR, model A:ci:2;B_adj_rr:Adjusted RR, model B:ci:2}}

Share of passenger-vehicle occupants killed (known model year) by vehicle age, FARS:

{{mdtable:deaths/vehicle_age|YEAR=2016~2019~2024~2016-2024;band=0-3~4-7~8-12~13-17~18+|YEAR:Year:;band:Vehicle age:;deaths:Deaths:,.0f;share:Share:pct:1}}

The rising 18+ share partly reflects the ageing of the fleet; FARS has no fleet counts.

Who died in crashes involving a large truck:

{{mdtable:deaths/victim_roles|group=large_truck|role:Role:;deaths:Deaths:,.0f;share_of_group:Share:pct:1}}

That most of those killed were not the truck driver describes who was in the crash, not who was at fault.
The share mixes crashes between a truck and a passenger vehicle with single-truck crashes, and nothing in
this report attributes fault.

## 9. Change since 2019

*Source: `deaths/segments`. The 2019–2021 rises in risky-driving groups were among the steepest of the
groups shown; a ranking depends on how the groups are defined (the invalid-licence group combines
expired, cancelled, suspended, revoked and unlicensed drivers).*

{{mdtable:deaths/segments|segment=all~any_of_four~alcohol_impaired~speeding~unbelted~unhelmeted~invalid_licence_crash~hit_and_run~pv_occupants~motorcyclists~pedestrians~cyclists~large_truck_crash~rural~urban~night|segment:Group:;deaths_2019:2019:,.0f;deaths_2021:2021:,.0f;deaths_2024:2024:,.0f;pct_change_2019_2021:2019→2021:pctsign:1;pct_change_2019_2024:2019→2024:pctsign:1;estimate_type:Type:}}

The share of drivers in fatal crashes without a valid licence was
{{deaths/driver_records_by_year|YEAR=2019;group=all;indicator=licence_invalid|share|pct:1}} in
2019, {{deaths/driver_records_by_year|YEAR=2020;group=all;indicator=licence_invalid|share|pct:1}}
in 2020 and {{deaths/driver_records_by_year|YEAR=2024;group=all;indicator=licence_invalid|share|pct:1}}
in 2024 (`deaths/driver_records_by_year`). FARS has no exposure, so these are changes in counts,
not in risk per mile.

## 10. States

*Source: `deaths/states` (all states; the website has a sortable version).*

{{mdtable:deaths/states||state:State:;deaths:Deaths 2016–2024:,.0f;pct_change_2019_2024:2019→2024:pctsign:0;alcohol_impaired_share:Drunk driving:pct:0;speeding_share:Speeding:pct:0;unbelted_share_known:Unbelted (known):pct:0;unhelmeted_share_known:No helmet (known):pct:0;pedestrian_share:Pedestrians:pct:0;rural_share:Rural:pct:0}}

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
