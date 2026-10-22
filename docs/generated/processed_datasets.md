# Generated dictionary of the analytic datasets

_Generated from `data/processed/*.parquet` by `nhtsa_stats.reporting.docs_gen`. Upper-case columns are raw NHTSA fields carried through unchanged (meanings: `outputs/audit/codebook.csv`); lower-case columns are harmonised (definitions: `docs/generated/harmonised_variables.md`). Do not edit by hand._

## `crss_crash` — 468,993 rows × 84 columns

| column | type | % null | values | timing |
|---|---|---|---|---|
| `case_id` | Int64 | 0.0 | 201600014311 – 202406762464 | id |
| `PSU` | Int64 | 0.0 | 10 – 83 | raw |
| `PSU_VAR` | Int64 | 0.0 | 10 – 214 | design |
| `PSUSTRAT` | Int64 | 0.0 | 1 – 25 | design |
| `STRATUM` | Int64 | 0.0 | 2 – 10 | raw |
| `PJ` | Int64 | 0.0 | 45 – 4155 | raw |
| `WEIGHT` | Float64 | 0.0 | 3.86191308 – 994.507448 | design |
| `REGION` | Int64 | 0.0 | 1 – 4 | raw |
| `URBANICITY` | Int64 | 0.0 | 1 – 2 | raw |
| `VE_TOTAL` | Int64 | 0.0 | 1 – 15 | raw |
| `VE_FORMS` | Int64 | 0.0 | 1 – 15 | raw |
| `PVH_INVL` | Int64 | 0.0 | 0 – 12 | raw |
| `PEDS` | Int64 | 0.0 | 0 – 12 | raw |
| `PERMVIT` | Int64 | 0.0 | 0 – 75 | raw |
| `PERNOTMVIT` | Int64 | 0.0 | 0 – 15 | raw |
| `NUM_INJ` | Int64 | 0.0 | 0 – 99 | raw |
| `MONTH` | Int64 | 0.0 | 1 – 12 | raw |
| `DAY_WEEK` | Int64 | 0.0 | 1 – 7 | raw |
| `HOUR` | Int64 | 0.0 | 0 – 99 | raw |
| `HARM_EV` | Int64 | 0.0 | 1 – 99 | raw |
| `MAN_COLL` | Int64 | 0.0 | 0 – 99 | raw |
| `RELJCT2` | Int64 | 0.0 | 1 – 99 | raw |
| `REL_ROAD` | Int64 | 0.0 | 1 – 99 | raw |
| `TYP_INT` | Int64 | 0.0 | 1 – 99 | raw |
| `WRK_ZONE` | Int64 | 0.0 | 0 – 4 | raw |
| `LGT_COND` | Int64 | 0.0 | 1 – 9 | raw |
| `WEATHER` | Int64 | 0.0 | 1 – 99 | raw |
| `INT_HWY` | Int64 | 0.0 | 0 – 9 | raw |
| `MAX_SEV` | Int64 | 0.0 | 0 – 9 | raw |
| `MAXSEV_IM` | Int64 | 0.0 | 0 – 8 | raw |
| `ALCOHOL` | Int64 | 0.0 | 1 – 9 | raw |
| `ALCHL_IM` | Int64 | 0.0 | 1 – 2 | raw |
| `LGTCON_IM` | Int64 | 0.0 | 1 – 7 | raw |
| `WEATHR_IM` | Int64 | 0.0 | 1 – 12 | raw |
| `HOUR_IM` | Int64 | 0.0 | 0 – 23 | raw |
| `WKDY_IM` | Int64 | 0.0 | 1 – 7 | raw |
| `YEAR` | Int64 | 0.0 | 2016 – 2024 | design |
| `speeding` | Int8 | 3.5 | 0 – 1 | pre_crash |
| `hit_and_run` | Int8 | 0.0 | 0 – 1 | crash_circumstance |
| `distracted` | Int8 | 45.8 | 0 – 1 | pre_crash |
| `rollover_any` | Int8 | 0.0 | 0 – 1 | post_crash |
| `fire_any` | Int8 | 0.0 | 0 – 1 | post_crash |
| `any_motorcycle` | Int8 | 0.0 | 0 – 1 | pre_crash |
| `any_heavy_truck` | Int8 | 0.0 | 0 – 1 | pre_crash |
| `any_light_truck` | Int8 | 0.0 | 0 – 1 |  |
| `speed_limit_mph` | Int64 | 15.5 | 5 – 90 |  |
| `speed_limit_zero` | Boolean | 0.0 | 2 distinct |  |
| `surface` | String | 0.0 | dry, other, snow_ice, unknown, wet | pre_crash |
| `oldest_vehicle_age` | Int64 | 2.6 | 0 – 60 | pre_crash |
| `n_veh_in_transport` | UInt32 | 0.0 | 1 – 15 |  |
| `any_pedestrian` | Int8 | 0.0 | 0 – 1 | crash_circumstance |
| `any_cyclist` | Int8 | 0.0 | 0 – 1 | crash_circumstance |
| `any_nonmotorist` | Int8 | 0.0 | 0 – 1 |  |
| `n_killed` | UInt32 | 0.0 | 0 – 6 | outcome |
| `n_ka` | UInt32 | 0.0 | 0 – 9 |  |
| `n_occupants` | UInt32 | 0.0 | 0 – 75 |  |
| `young_driver` | Int8 | 9.6 | 0 – 1 | pre_crash |
| `older_driver` | Int8 | 9.7 | 0 – 1 | pre_crash |
| `drugs` | Int8 | 42.5 | 0 – 1 | pre_crash |
| `driver_pr_alcohol` | Int8 | 29.7 | 0 – 1 |  |
| `n_drivers` | UInt32 | 0.1 | 1 – 15 |  |
| `light` | String | 0.0 | dark_lighted, dark_not_lighted, dark_unknown_lighting, dawn_dusk, daylight, unknown | pre_crash |
| `dark` | Int8 | 0.7 | 0 – 1 | pre_crash |
| `weather` | String | 0.0 | clear, cloudy, fog, other, rain, snow_sleet, unknown | pre_crash |
| `tod` | String | 0.0 | 00-05, 06-09, 10-15, 16-19, 20-23, unknown | pre_crash |
| `night` | Int8 | 0.5 | 0 – 1 | pre_crash |
| `weekend` | Int8 | 0.0 | 0 – 1 | pre_crash |
| `junction` | String | 0.0 | driveway, interchange, intersection, non_junction, other, unknown | pre_crash |
| `work_zone` | Int8 | 0.0 | 0 – 1 | pre_crash |
| `collision` | String | 0.0 | angle, head_on, not_mv_collision, other_mv, rear_end, sideswipe, unknown | crash_circumstance |
| `n_vehicles` | String | 0.0 | 1, 2, 3+ | crash_circumstance |
| `speed_limit` | String | 0.0 | 30-35, 40-45, 50-55, 60-65, 70+, <=25, none_nontrafficway, unknown | pre_crash |
| `crash_type` | String | 0.0 | cyclist, mv_angle, mv_head_on, mv_other, mv_rear_end, mv_sideswipe, pedestrian, sv_off_roadway, sv_on_roadway, sv_rollov | crash_circumstance |
| `fatal` | Int8 | 2.2 | 0 – 1 | outcome |
| `ka` | Int8 | 2.2 | 0 – 1 | outcome |
| `injury` | Int8 | 1.8 | 0 – 1 | outcome |
| `kabco` | Int8 | 2.2 | 0 – 4 | outcome |
| `fatal_im` | Int8 | 0.4 | 0 – 1 | outcome |
| `ka_im` | Int8 | 0.4 | 0 – 1 | outcome |
| `alcohol` | Int8 | 30.4 | 0 – 1 | pre_crash |
| `alcohol_im` | Int8 | 0.0 | 0 – 1 | pre_crash |
| `region` | String | 0.0 | midwest, northeast, south, west | pre_crash |
| `urbanicity` | String | 0.0 | rural, urban | pre_crash |
| `interstate` | Int8 | 0.0 | 0 – 1 | pre_crash |

## `crss_person` — 1,154,804 rows × 82 columns

| column | type | % null | values | timing |
|---|---|---|---|---|
| `case_id` | Int64 | 0.0 | 201600014311 – 202406762464 | id |
| `VEH_NO` | Int64 | 0.0 | 0 – 15 | raw |
| `PER_NO` | Int64 | 0.0 | 1 – 75 | raw |
| `PER_TYP` | Int64 | 0.0 | 1 – 19 | raw |
| `BODY_TYP` | Int64 | 3.8 | 1 – 99 | raw |
| `AGE` | Int64 | 0.0 | 0 – 999 | raw |
| `SEX` | Int64 | 0.0 | 1 – 9 | raw |
| `INJ_SEV` | Int64 | 0.0 | 0 – 9 | raw |
| `SEAT_POS` | Int64 | 0.0 | 0 – 99 | raw |
| `REST_USE` | Int64 | 0.0 | 0 – 99 | raw |
| `REST_MIS` | Int64 | 0.0 | 0 – 8 | raw |
| `AIR_BAG` | Int64 | 0.0 | 0 – 99 | raw |
| `EJECTION` | Int64 | 0.0 | 0 – 9 | raw |
| `DRINKING` | Int64 | 0.0 | 0 – 9 | raw |
| `DRUGS` | Int64 | 0.0 | 0 – 9 | raw |
| `ALC_STATUS` | Int64 | 0.0 | 0 – 9 | raw |
| `ALC_RES` | Int64 | 0.0 | 0 – 999 | raw |
| `AGE_IM` | Int64 | 0.0 | 0 – 120 | raw |
| `SEX_IM` | Int64 | 0.0 | 1 – 2 | raw |
| `INJSEV_IM` | Int64 | 0.0 | 0 – 6 | raw |
| `EJECT_IM` | Int64 | 0.0 | 0 – 8 | raw |
| `PERALCH_IM` | Int64 | 0.0 | 0 – 1 | raw |
| `SEAT_IM` | Int64 | 0.0 | 0 – 56 | raw |
| `HELM_USE` | Int64 | 32.5 | 5 – 99 | raw |
| `YEAR` | Int64 | 0.0 | 2016 – 2024 | design |
| `ptype` | String | 0.0 | cyclist, driver, other_nonmotorist, passenger, pedestrian |  |
| `age` | Int64 | 6.3 | 0 – 120 | pre_crash |
| `sex` | String | 0.0 | female, male, unknown | pre_crash |
| `killed` | Int8 | 3.7 | 0 – 1 | outcome |
| `killed_or_serious` | Int8 | 3.7 | 0 – 1 | outcome |
| `injured` | Int8 | 3.5 | 0 – 1 |  |
| `kabco` | Int8 | 3.7 | 0 – 4 | outcome |
| `seat` | String | 0.0 | cargo_exterior_other, front_left, front_other, second_row, third_row_plus, unknown | pre_crash |
| `restraint` | String | 0.0 | belted, child_restraint, none, not_applicable, unknown | pre_crash |
| `helmet` | String | 0.0 | helmet, none, not_applicable, unknown | pre_crash |
| `ejected` | Int8 | 11.4 | 0 – 1 | post_crash |
| `pr_alcohol` | Int8 | 41.5 | 0 – 1 |  |
| `pr_drugs` | Int8 | 51.4 | 0 – 1 |  |
| `alc_tested` | Int8 | 17.2 | 0 – 1 |  |
| `bac_measured` | Float64 | 99.1 | 0.0 – 0.92 |  |
| `airbag_deployed` | Int8 | 12.2 | 0 – 1 | post_crash |
| `age_band` | String | 0.0 | 0-14, 15-20, 21-24, 25-34, 35-44, 45-54, 55-64, 65-74, 75+, unknown | pre_crash |
| `killed_im` | Int8 | 0.2 | 0 – 1 |  |
| `killed_or_serious_im` | Int8 | 0.2 | 0 – 1 |  |
| `body` | String | 3.8 | bus, car, light_truck_other, medium_heavy_truck, motorcycle, other, pickup, suv, unknown, van | pre_crash |
| `veh_age` | Int64 | 7.0 | 0 – 60 |  |
| `veh_age_band` | String | 3.8 | 0-3, 13-17, 18+, 4-7, 8-12, unknown | pre_crash |
| `veh_speeding` | Int8 | 5.8 | 0 – 1 | pre_crash |
| `veh_alcohol` | Int8 | 27.4 | 0 – 1 | pre_crash |
| `veh_alcohol_im` | Int8 | 3.8 | 0 – 1 |  |
| `distracted` | Int8 | 45.4 | 0 – 1 | pre_crash |
| `veh_speed_limit_mph` | Int64 | 19.7 | 5 – 90 |  |
| `veh_rollover` | Int8 | 3.8 | 0 – 1 |  |
| `WEIGHT` | Float64 | 0.0 | 3.86191308 – 994.507448 | design |
| `PSUSTRAT` | Int64 | 0.0 | 1 – 25 | design |
| `PSU_VAR` | Int64 | 0.0 | 10 – 214 | design |
| `STRATUM` | Int64 | 0.0 | 2 – 10 | raw |
| `region` | String | 0.0 | midwest, northeast, south, west | pre_crash |
| `urbanicity` | String | 0.0 | rural, urban | pre_crash |
| `light` | String | 0.0 | dark_lighted, dark_not_lighted, dark_unknown_lighting, dawn_dusk, daylight, unknown | pre_crash |
| `dark` | Int8 | 0.5 | 0 – 1 | pre_crash |
| `weather` | String | 0.0 | clear, cloudy, fog, other, rain, snow_sleet, unknown | pre_crash |
| `surface` | String | 0.0 | dry, other, snow_ice, unknown, wet | pre_crash |
| `speed_limit` | String | 0.0 | 30-35, 40-45, 50-55, 60-65, 70+, <=25, none_nontrafficway, unknown | pre_crash |
| `tod` | String | 0.0 | 00-05, 06-09, 10-15, 16-19, 20-23, unknown | pre_crash |
| `night` | Int8 | 0.3 | 0 – 1 | pre_crash |
| `weekend` | Int8 | 0.0 | 0 – 1 | pre_crash |
| `junction` | String | 0.0 | driveway, interchange, intersection, non_junction, other, unknown | pre_crash |
| `interstate` | Int8 | 0.0 | 0 – 1 | pre_crash |
| `work_zone` | Int8 | 0.0 | 0 – 1 | pre_crash |
| `n_vehicles` | String | 0.0 | 1, 2, 3+ | crash_circumstance |
| `crash_type` | String | 0.0 | cyclist, mv_angle, mv_head_on, mv_other, mv_rear_end, mv_sideswipe, pedestrian, sv_off_roadway, sv_on_roadway, sv_rollov | crash_circumstance |
| `collision` | String | 0.0 | angle, head_on, not_mv_collision, other_mv, rear_end, sideswipe, unknown | crash_circumstance |
| `speeding` | Int8 | 3.3 | 0 – 1 | pre_crash |
| `alcohol` | Int8 | 29.1 | 0 – 1 | pre_crash |
| `alcohol_im` | Int8 | 0.0 | 0 – 1 | pre_crash |
| `any_heavy_truck` | Int8 | 0.0 | 0 – 1 | pre_crash |
| `any_motorcycle` | Int8 | 0.0 | 0 – 1 | pre_crash |
| `crash_fatal` | Int8 | 1.3 | 0 – 1 |  |
| `crash_ka` | Int8 | 1.3 | 0 – 1 |  |
| `other_vehicle_body` | String | 0.0 | bus, car, light_truck_other, medium_heavy_truck, motorcycle, none_or_multi, other, pickup, suv, unknown, van |  |
| `role` | String | 0.0 | cyclist, driver, front_passenger, other_nonmotorist, other_passenger, pedestrian, rear_passenger | pre_crash |

## `fars_crash` — 325,922 rows × 66 columns

| column | type | % null | values | timing |
|---|---|---|---|---|
| `case_id` | Int64 | 0.0 | 10001 – 560121 | id |
| `STATE` | Int64 | 0.0 | 1 – 56 | raw |
| `VE_TOTAL` | Int64 | 0.0 | 1 – 130 | raw |
| `VE_FORMS` | Int64 | 0.0 | 1 – 130 | raw |
| `PVH_INVL` | Int64 | 0.0 | 0 – 20 | raw |
| `PEDS` | Int64 | 0.0 | 0 – 73 | raw |
| `PERSONS` | Int64 | 0.0 | 0 – 133 | raw |
| `PERMVIT` | Int64 | 0.0 | 0 – 133 | raw |
| `PERNOTMVIT` | Int64 | 0.0 | 0 – 73 | raw |
| `FATALS` | Int64 | 0.0 | 1 – 20 | raw |
| `MONTH` | Int64 | 0.0 | 1 – 12 | raw |
| `DAY_WEEK` | Int64 | 0.0 | 1 – 7 | raw |
| `HOUR` | Int64 | 0.0 | 0 – 99 | raw |
| `RUR_URB` | Int64 | 0.0 | 1 – 9 | raw |
| `FUNC_SYS` | Int64 | 0.0 | 1 – 99 | raw |
| `HARM_EV` | Int64 | 0.0 | 1 – 99 | raw |
| `MAN_COLL` | Int64 | 0.0 | 0 – 99 | raw |
| `RELJCT2` | Int64 | 0.0 | 1 – 99 | raw |
| `REL_ROAD` | Int64 | 0.0 | 1 – 99 | raw |
| `TYP_INT` | Int64 | 0.0 | 1 – 99 | raw |
| `WRK_ZONE` | Int64 | 0.0 | 0 – 4 | raw |
| `LGT_COND` | Int64 | 0.0 | 1 – 9 | raw |
| `WEATHER` | Int64 | 0.0 | 1 – 99 | raw |
| `YEAR` | Int64 | 0.0 | 2016 – 2024 | design |
| `speeding` | Int8 | 6.6 | 0 – 1 | pre_crash |
| `hit_and_run` | Int8 | 0.1 | 0 – 1 | crash_circumstance |
| `distracted` | Int8 | 64.7 | 0 – 1 | pre_crash |
| `rollover_any` | Int8 | 0.0 | 0 – 1 | post_crash |
| `fire_any` | Int8 | 0.0 | 0 – 1 | post_crash |
| `any_motorcycle` | Int8 | 0.0 | 0 – 1 | pre_crash |
| `any_heavy_truck` | Int8 | 0.0 | 0 – 1 | pre_crash |
| `any_light_truck` | Int8 | 0.0 | 0 – 1 |  |
| `speed_limit_mph` | Int64 | 3.3 | 5 – 85 |  |
| `speed_limit_zero` | Boolean | 0.0 | 2 distinct |  |
| `surface` | String | 0.0 | dry, other, snow_ice, unknown, wet | pre_crash |
| `oldest_vehicle_age` | Int64 | 2.9 | 0 – 60 | pre_crash |
| `n_veh_in_transport` | UInt32 | 0.0 | 1 – 130 |  |
| `alcohol_driver` | Int8 | 0.0 | 0 – 1 |  |
| `any_pedestrian` | Int8 | 0.0 | 0 – 1 | crash_circumstance |
| `any_cyclist` | Int8 | 0.0 | 0 – 1 | crash_circumstance |
| `any_nonmotorist` | Int8 | 0.0 | 0 – 1 |  |
| `n_killed` | UInt32 | 0.0 | 1 – 20 | outcome |
| `n_ka` | UInt32 | 0.0 | 1 – 56 |  |
| `n_occupants` | UInt32 | 0.0 | 0 – 133 |  |
| `young_driver` | Int8 | 4.0 | 0 – 1 | pre_crash |
| `older_driver` | Int8 | 3.9 | 0 – 1 | pre_crash |
| `drugs` | Int8 | 47.3 | 0 – 1 | pre_crash |
| `driver_pr_alcohol` | Int8 | 36.7 | 0 – 1 |  |
| `n_drivers` | UInt32 | 0.2 | 1 – 129 |  |
| `a_p08` | Float64 | 0.2 | 0.0 – 1.0 |  |
| `a_p01` | Float64 | 0.2 | 0.0 – 1.0 |  |
| `light` | String | 0.0 | dark_lighted, dark_not_lighted, dark_unknown_lighting, dawn_dusk, daylight, unknown | pre_crash |
| `dark` | Int8 | 0.6 | 0 – 1 | pre_crash |
| `weather` | String | 0.0 | clear, cloudy, fog, other, rain, snow_sleet, unknown | pre_crash |
| `tod` | String | 0.0 | 00-05, 06-09, 10-15, 16-19, 20-23, unknown | pre_crash |
| `night` | Int8 | 0.7 | 0 – 1 | pre_crash |
| `weekend` | Int8 | 0.0 | 0 – 1 | pre_crash |
| `junction` | String | 0.0 | driveway, interchange, intersection, non_junction, other, unknown | pre_crash |
| `work_zone` | Int8 | 0.0 | 0 – 1 | pre_crash |
| `collision` | String | 0.0 | angle, head_on, not_mv_collision, other_mv, rear_end, sideswipe, unknown | crash_circumstance |
| `n_vehicles` | String | 0.0 | 1, 2, 3+ | crash_circumstance |
| `speed_limit` | String | 0.0 | 30-35, 40-45, 50-55, 60-65, 70+, <=25, none_nontrafficway, unknown | pre_crash |
| `crash_type` | String | 0.0 | cyclist, mv_angle, mv_head_on, mv_other, mv_rear_end, mv_sideswipe, pedestrian, sv_off_roadway, sv_on_roadway, sv_rollov | crash_circumstance |
| `rural` | Int8 | 0.4 | 0 – 1 | pre_crash |
| `interstate` | Int8 | 0.5 | 0 – 1 | pre_crash |
| `driver_bac08_prob` | Float64 | 0.2 | 0.0 – 1.0 |  |

## `fars_person` — 800,688 rows × 70 columns

| column | type | % null | values | timing |
|---|---|---|---|---|
| `case_id` | Int64 | 0.0 | 10001 – 560121 | id |
| `VEH_NO` | Int64 | 0.0 | 0 – 130 | raw |
| `PER_NO` | Int64 | 0.0 | 1 – 73 | raw |
| `PER_TYP` | Int64 | 0.0 | 1 – 19 | raw |
| `BODY_TYP` | Int64 | 9.6 | 1 – 99 | raw |
| `AGE` | Int64 | 0.0 | 0 – 999 | raw |
| `SEX` | Int64 | 0.0 | 1 – 9 | raw |
| `INJ_SEV` | Int64 | 0.0 | 0 – 9 | raw |
| `SEAT_POS` | Int64 | 0.0 | 0 – 99 | raw |
| `REST_USE` | Int64 | 0.0 | 0 – 99 | raw |
| `REST_MIS` | Int64 | 0.0 | 0 – 8 | raw |
| `AIR_BAG` | Int64 | 0.0 | 0 – 99 | raw |
| `EJECTION` | Int64 | 0.0 | 0 – 9 | raw |
| `DRINKING` | Int64 | 0.0 | 0 – 9 | raw |
| `DRUGS` | Int64 | 0.0 | 0 – 9 | raw |
| `ALC_STATUS` | Int64 | 0.0 | 0 – 9 | raw |
| `ALC_RES` | Int64 | 0.0 | 0 – 999 | raw |
| `DOA` | Int64 | 0.0 | 0 – 9 | raw |
| `HOSPITAL` | Int64 | 0.0 | 0 – 9 | raw |
| `HELM_USE` | Int64 | 32.1 | 5 – 99 | raw |
| `YEAR` | Int64 | 0.0 | 2016 – 2024 | design |
| `ptype` | String | 0.0 | cyclist, driver, other_nonmotorist, parked_vehicle_occupant, passenger, pedestrian |  |
| `age` | Int64 | 2.5 | 0 – 119 | pre_crash |
| `sex` | String | 0.0 | female, male, unknown | pre_crash |
| `killed` | Int8 | 1.8 | 0 – 1 | outcome |
| `killed_or_serious` | Int8 | 1.8 | 0 – 1 | outcome |
| `injured` | Int8 | 1.5 | 0 – 1 |  |
| `kabco` | Int8 | 1.8 | 0 – 4 | outcome |
| `seat` | String | 0.0 | cargo_exterior_other, front_left, front_other, second_row, third_row_plus, unknown | pre_crash |
| `restraint` | String | 0.0 | belted, child_restraint, none, not_applicable, unknown | pre_crash |
| `helmet` | String | 0.0 | helmet, none, not_applicable, unknown | pre_crash |
| `ejected` | Int8 | 17.8 | 0 – 1 | post_crash |
| `pr_alcohol` | Int8 | 49.6 | 0 – 1 |  |
| `pr_drugs` | Int8 | 57.1 | 0 – 1 |  |
| `alc_tested` | Int8 | 10.2 | 0 – 1 |  |
| `bac_measured` | Float64 | 65.8 | 0.0 – 0.93 |  |
| `airbag_deployed` | Int8 | 15.1 | 0 – 1 | post_crash |
| `age_band` | String | 0.0 | 0-14, 15-20, 21-24, 25-34, 35-44, 45-54, 55-64, 65-74, 75+, unknown | pre_crash |
| `body` | String | 10.0 | bus, car, light_truck_other, medium_heavy_truck, motorcycle, other, pickup, suv, unknown, van | pre_crash |
| `veh_age` | Int64 | 11.9 | 0 – 60 |  |
| `veh_age_band` | String | 10.0 | 0-3, 13-17, 18+, 4-7, 8-12, unknown | pre_crash |
| `veh_speeding` | Int8 | 14.0 | 0 – 1 | pre_crash |
| `veh_alcohol` | Int8 | 10.0 | 0 – 1 | pre_crash |
| `distracted` | Int8 | 61.9 | 0 – 1 | pre_crash |
| `veh_speed_limit_mph` | Int64 | 14.0 | 5 – 85 |  |
| `veh_rollover` | Int8 | 10.0 | 0 – 1 |  |
| `DEATHS` | Int64 | 10.0 | 0 – 18 | raw |
| `L_STATUS` | Int64 | 10.0 | 0 – 9 | raw |
| `PREV_DWI` | Int64 | 10.0 | 0 – 998 | raw |
| `PREV_SPD` | Int64 | 10.0 | 0 – 998 | raw |
| `PREV_SUS1` | Int64 | 29.5 | 0 – 998 | raw |
| `p_p08` | Float64 | 28.3 | 0.0 – 1.0 |  |
| `p_p01` | Float64 | 28.3 | 0.0 – 1.0 |  |
| `STATE` | Int64 | 0.0 | 1 – 56 | raw |
| `rural` | Int8 | 0.3 | 0 – 1 | pre_crash |
| `interstate` | Int8 | 0.4 | 0 – 1 | pre_crash |
| `light` | String | 0.0 | dark_lighted, dark_not_lighted, dark_unknown_lighting, dawn_dusk, daylight, unknown | pre_crash |
| `dark` | Int8 | 0.4 | 0 – 1 | pre_crash |
| `weather` | String | 0.0 | clear, cloudy, fog, other, rain, snow_sleet, unknown | pre_crash |
| `surface` | String | 0.0 | dry, other, snow_ice, unknown, wet | pre_crash |
| `speed_limit` | String | 0.0 | 30-35, 40-45, 50-55, 60-65, 70+, <=25, none_nontrafficway, unknown | pre_crash |
| `tod` | String | 0.0 | 00-05, 06-09, 10-15, 16-19, 20-23, unknown | pre_crash |
| `night` | Int8 | 0.4 | 0 – 1 | pre_crash |
| `weekend` | Int8 | 0.0 | 0 – 1 | pre_crash |
| `n_vehicles` | String | 0.0 | 1, 2, 3+ | crash_circumstance |
| `crash_type` | String | 0.0 | cyclist, mv_angle, mv_head_on, mv_other, mv_rear_end, mv_sideswipe, pedestrian, sv_off_roadway, sv_on_roadway, sv_rollov | crash_circumstance |
| `speeding` | Int8 | 5.9 | 0 – 1 | pre_crash |
| `FATALS` | Int64 | 0.0 | 1 – 20 | raw |
| `other_vehicle_body` | String | 0.0 | bus, car, light_truck_other, medium_heavy_truck, motorcycle, none_or_multi, other, pickup, suv, unknown, van |  |
| `role` | String | 0.0 | cyclist, driver, front_passenger, other_nonmotorist, other_passenger, parked_vehicle_occupant, pedestrian, rear_passenge | pre_crash |
