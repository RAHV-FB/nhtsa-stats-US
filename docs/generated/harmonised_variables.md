# Generated catalogue of harmonised analytic variables

_Generated from `processing/harmonize.py` (REGISTRY and mapping docstrings). Do not edit by hand._

Timing classes: `pre_crash` and `crash_circumstance` may enter severity models; `post_crash` and `outcome` may not (enforced by `assert_no_leakage`).

## Leakage registry

| variable | timing | level | note |
|---|---|---|---|
| any_cyclist | crash_circumstance | crash |  |
| any_pedestrian | crash_circumstance | crash |  |
| collision | crash_circumstance | crash |  |
| crash_type | crash_circumstance | crash |  |
| n_vehicles | crash_circumstance | crash |  |
| other_vehicle_body | crash_circumstance | person | body group of the other vehicle in a two-vehicle crash (implies the crash configuration) |
| other_vehicle_heavy | crash_circumstance | vehicle |  |
| PSUSTRAT | design | crash |  |
| PSU_VAR | design | crash |  |
| WEIGHT | design | crash |  |
| YEAR | design | crash | survey/calendar year |
| case_id | id | crash |  |
| fatal | outcome | crash |  |
| fatal_cc | outcome | crash | complete-case sensitivity |
| injury | outcome | crash |  |
| ka | outcome | crash |  |
| ka_cc | outcome | crash | complete-case sensitivity |
| kabco | outcome | crash |  |
| killed | outcome | person |  |
| killed_cc | outcome | person | complete-case sensitivity |
| killed_or_serious | outcome | person |  |
| killed_or_serious_cc | outcome | person | complete-case sensitivity |
| n_injured | outcome | crash |  |
| n_killed | outcome | crash |  |
| n_sev_injured_unknown | outcome | crash | persons with INJ_SEV 5 |
| n_sev_unknown | outcome | crash | persons with INJ_SEV 9 (unknown) |
| airbag_deployed | post_crash | person |  |
| ejected | post_crash | person | consequence of crash forces and restraint |
| fire_any | post_crash | crash |  |
| hit_and_run | post_crash | crash | driver behaviour after the crash (leaving the scene) |
| rollover_any | post_crash | crash | crash outcome mechanism |
| towed_any | post_crash | crash | towing is decided after the crash |
| age | pre_crash | person |  |
| age_band | pre_crash | person |  |
| alcohol | pre_crash | crash | police-reported; ascertainment varies with severity |
| alcohol_im | pre_crash | crash | NHTSA multiple-imputation-based single imputation |
| any_heavy_truck | pre_crash | crash |  |
| any_motorcycle | pre_crash | crash |  |
| body | pre_crash | vehicle |  |
| dark | pre_crash | crash |  |
| distracted | pre_crash | crash | police-reported |
| drugs | pre_crash | crash | police-reported; very incomplete |
| helmet | pre_crash | person |  |
| interstate | pre_crash | crash |  |
| junction | pre_crash | crash |  |
| light | pre_crash | crash |  |
| location | pre_crash | person | non-motorist's location at the crash |
| night | pre_crash | crash |  |
| older_driver | pre_crash | crash |  |
| oldest_vehicle_age | pre_crash | crash |  |
| region | pre_crash | crash |  |
| restraint | pre_crash | person | police-reported; misreporting by survivors |
| role | pre_crash | person |  |
| rural | pre_crash | crash | FARS road-level rural/urban |
| seat | pre_crash | person |  |
| sex | pre_crash | person |  |
| speed_limit | pre_crash | crash |  |
| speeding | pre_crash | crash | police judgement recorded after the crash |
| speeding_type | pre_crash | crash | exceeded limit/racing vs too fast for conditions vs unspecified |
| str_speed_limit | pre_crash | person | posted limit of the striking vehicle's road |
| str_speeding | pre_crash | person | striking vehicle speeding-related (police) |
| striking | pre_crash | person | body type of the striking vehicle |
| surface | pre_crash | crash |  |
| tod | pre_crash | crash |  |
| urbanicity | pre_crash | crash | CRSS area-level (PSU) urban/rural |
| veh_age_band | pre_crash | vehicle |  |
| veh_alcohol | pre_crash | vehicle |  |
| veh_speeding | pre_crash | vehicle |  |
| weather | pre_crash | crash |  |
| weekend | pre_crash | crash |  |
| work_zone | pre_crash | crash |  |
| young_driver | pre_crash | crash |  |

## Code mappings

### `fatal(col: 'str' = 'INJ_SEV') -> 'pl.Expr'`

1 = fatal (K); 0 = O/C/B/A; null = 5, 6, 8, 9 (severity unknown / not a crash death).

### `killed_or_serious(col: 'str' = 'INJ_SEV') -> 'pl.Expr'`

1 = K or A; 0 = O/C/B; null = 5, 6, 8, 9.

### `any_injury(col: 'str' = 'INJ_SEV') -> 'pl.Expr'`

1 = K/A/B/C or injured-severity-unknown (5); 0 = O; null = 6, 8, 9.

### `kabco(col: 'str' = 'INJ_SEV') -> 'pl.Expr'`

Ordinal 0 (O) .. 4 (K); null otherwise.

### `light_condition(col: 'str' = 'LGT_COND') -> 'pl.Expr'`

1 daylight; 2 dark-not lighted; 3 dark-lighted; 4 dawn; 5 dusk; 6 dark-unknown
lighting; 7 other; 8 not reported; 9 unknown.

### `is_dark(col: 'str' = 'LGT_COND') -> 'pl.Expr'`

1 = any dark condition (2, 3, 6); 0 = daylight/dawn/dusk (1, 4, 5); null otherwise.

### `weather(col: 'str' = 'WEATHER') -> 'pl.Expr'`

Crash-level atmospheric condition (WEATHER: 1 clear, 2 rain, 3 sleet/hail, 4 snow,
5 fog/smog/smoke, 6 crosswinds, 7 blowing sand, 8 other, 10 cloudy, 11 blowing snow,
12 freezing rain/drizzle, 98 not reported, 99 unknown).

### `surface_condition(col: 'str' = 'VSURCOND') -> 'pl.Expr'`

Roadway surface (vehicle table): 1 dry; 2 wet, 6 standing/moving water; 3 snow,
4 ice/frost, 10 slush; 0 non-trafficway, 5 sand, 7 oil, 8 other, 11 mud/dirt/gravel;
98 not reported; 99 unknown.

### `speed_limit_band(col: 'str' = 'VSPD_LIM') -> 'pl.Expr'`

Posted speed limit in mph (5-90); 0 = no statutory limit / non-trafficway (kept as its
own level: mostly parking lots and driveways, not an unknown limit); 98 not reported;
99 unknown.

### `speed_limit_mph(col: 'str' = 'VSPD_LIM') -> 'pl.Expr'`



### `junction(col: 'str' = 'RELJCT2') -> 'pl.Expr'`

RELJCT2: 1 non-junction; 2 intersection, 3 intersection-related; 4 driveway access,
8 driveway-access related; 5 ramp related, 17-20 interchange elements; 6 rail crossing,
7 crossover, 16 shared-use path crossing; 98/99 unknown.

### `work_zone(col: 'str' = 'WRK_ZONE') -> 'pl.Expr'`

0 none; 1 construction, 2 maintenance, 3 utility, 4 type unknown (all = work zone).

### `time_of_day(col: 'str' = 'HOUR') -> 'pl.Expr'`

HOUR 0-23; 99 unknown.

### `night(col: 'str' = 'HOUR') -> 'pl.Expr'`

1 = 21:00-05:59; 0 = 06:00-20:59; null = unknown hour (99).

### `weekend(col: 'str' = 'DAY_WEEK') -> 'pl.Expr'`

DAY_WEEK 1 = Sunday ... 7 = Saturday; 9 unknown.

### `manner_of_collision(col: 'str' = 'MAN_COLL') -> 'pl.Expr'`

0 first harmful event not a collision with a motor vehicle in transport; 1 front-to-
rear; 2 front-to-front; 6 angle; 7/8 sideswipe; 9 rear-to-side; 10 rear-to-rear;
11 other; 98/99 unknown.

### `body_group(col: 'str' = 'BODY_TYP') -> 'pl.Expr'`

Vehicle category from BODY_TYP (98 not reported / 99 unknown -> unknown).

Pickup codes 30-32 (compact/standard/camper pickup) were merged into 34 'light pickup'
from 2017; grouping them removes that break.

### `is_light_passenger_vehicle(col: 'str' = 'BODY_TYP') -> 'pl.Expr'`



### `vehicle_age(model_year: 'str' = 'MOD_YEAR', year: 'str' = 'YEAR') -> 'pl.Expr'`

Crash year minus model year (model year 9998/9999 unknown); -1 allowed (next-year
models sold early); null outside [-1, 60].

### `vehicle_age_band(age: 'str' = 'veh_age') -> 'pl.Expr'`



### `speeding_related(col: 'str' = 'SPEEDREL') -> 'pl.Expr'`

SPEEDREL: 0 no; 2 racing, 3 exceeded limit, 4 too fast for conditions, 5 specifics
unknown (all = yes); 8 no driver present / unknown if driver present; 9 unknown.
Code 8 is unknown: it cannot distinguish a driverless vehicle from an unknown driver.

### `speeding_type(col: 'str' = 'SPEEDREL') -> 'pl.Expr'`



### `hit_and_run(col: 'str' = 'HIT_RUN') -> 'pl.Expr'`



### `person_type(col: 'str' = 'PER_TYP') -> 'pl.Expr'`

1 driver; 2 passenger; 9 unknown occupant type (in transport); 3 occupant of a
parked/working vehicle; 5 pedestrian; 6 bicyclist, 7 other pedalcyclist; 4, 8, 10-13, 19
other non-motorists (personal conveyances, persons in buildings, unknown type).

### `age_years(col: 'str' = 'AGE') -> 'pl.Expr'`

AGE in years (0 = under 1); 998 not reported; 999 unknown.

### `age_band(col: 'str' = 'age') -> 'pl.Expr'`



### `sex(col: 'str' = 'SEX') -> 'pl.Expr'`

1 male; 2 female; 3 (later years, if present) other; 8 not reported; 9 unknown.

### `seat_row(col: 'str' = 'SEAT_POS') -> 'pl.Expr'`

SEAT_POS: 11 driver seat (front left); 12/13/18/19 other front; 21-29 second row;
31-49 third/fourth row; 50-56 sleeper/cargo/exterior/trailing; 0 not an occupant;
98/99 unknown.

### `restraint_use(col: 'str' = 'REST_USE') -> 'pl.Expr'`

Occupant restraint (meaningful for occupants of vehicles fitted with belts).

belted: 1 shoulder only, 2 lap only, 3 lap+shoulder, 6 racing harness, 8 restraint used
type unknown; child_restraint: 4, 10, 11, 12; none: 7 (2016 'None Used'), 20 (2017+
'None Used/Not Applicable'); helmet codes 5/16/17/19/29 (motorcyclists, 2016-2018 only)
and 0 (2016 'Not applicable') / 96 (not an MV occupant) -> not_applicable;
97 other / 98 not reported / 99 unknown -> unknown.

### `restraint_in_belted_seat(rest_col: 'str' = 'REST_USE', body_col: 'str' = 'BODY_TYP', seat_col: 'str' = 'SEAT_POS') -> 'pl.Expr'`

Restraint use restricted to occupants of belt-equipped vehicles in belted seating rows.

From 2017 code 20 means "none used *or* not applicable", and from 2019 every motorcyclist has
REST_USE = 20 (helmets moved to HELM_USE).  Belt information is therefore only meaningful for
occupants of vehicles with BODY_TYP 1-79 (light vehicles, buses, trucks) seated in rows 1-4
(SEAT_POS 11-49) or in an unrecorded seat (98/99: the occupant is inside the vehicle, so
the recorded belt use still applies); everyone else (motorcycles 80-89, other 90-97,
cargo/exterior/trailing positions 50-56, unknown body) is ``not_applicable``.  See
docs/audit/person_injury_restraint.md §4.6.

### `helmet_use(rest_col: 'str' = 'REST_USE', helm_col: 'str' = 'HELM_USE', year: 'str' = 'YEAR', body_col: 'str' = 'BODY_TYP') -> 'pl.Expr'`

Motorcycle helmet use harmonised across the 2019 move from REST_USE to HELM_USE.

2016-2018 (REST_USE) and 2019+ (HELM_USE): 5 DOT-compliant helmet, 16 other helmet,
19 helmet unknown if DOT-compliant -> helmet; 17 no helmet -> none; 29 / 98 / 99 ->
unknown; everything else (20 not applicable, 96 non-occupant, belt codes) -> not_applicable.
Defined for motorcycle riders (BODY_TYP 80-89) only; before 2019 REST_USE 98/99 would
otherwise make every other occupant's helmet 'unknown'.

### `ejected(col: 'str' = 'EJECTION') -> 'pl.Expr'`

POST-CRASH: 0 not ejected; 1 totally, 2 partially ejected; 3 ejected unknown degree;
7 not reported? / 8 not applicable / 9 unknown -> null.  Used only as a mediator.

### `police_reported(col: 'str') -> 'pl.Expr'`

DRINKING / DRUGS person fields: 0 no; 1 yes; 8 not reported; 9 unknown.

### `crss_alcohol(col: 'str' = 'ALCOHOL') -> 'pl.Expr'`

CRSS ALCOHOL / VEH_ALCH: 1 involved; 2 not involved; 8 no applicable person /
no driver present; 9 unknown.  ALCHL_IM / V_ALCH_IM use 1/2 only (imputed).

### Vehicle body groups (`BODY_TYP`)

| group | BODY_TYP codes |
|---|---|
| car | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 17 |
| suv | 14, 15, 16, 19 |
| van | 20, 21, 22, 28, 29 |
| pickup | 30, 31, 32, 33, 34, 39 |
| light_truck_other | 40, 41, 42, 45, 48 |
| light_unknown_type | 49 |
| bus | 50, 51, 52, 55, 58, 59 |
| medium_heavy_truck | 60, 61, 62, 63, 64, 66, 67, 71, 72, 78 |
| motorcycle | 80, 81, 82, 83, 84, 85, 86, 87, 88, 89 |
| truck_unknown_type | 73, 79 |
| other | 65, 90, 91, 92, 93, 94, 95, 96, 97 |
