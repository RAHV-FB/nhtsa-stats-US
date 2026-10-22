"""Year-consistent harmonised definitions of analytic variables.

Every function returns a Polars expression that maps raw NHTSA codes to a small set of
documented categories.  Code meanings come from the value labels embedded in the CSVs
(``outputs/audit/codebook.csv``); the evidence for each mapping and every year-specific
break is recorded in ``docs/variable_harmonization.md``.

Conventions
-----------
* Unknown / not reported / not applicable codes become the category ``"unknown"`` (for
  categorical variables) or null (for binary indicators and numbers) -- never 0 / "no".
* Binary indicators are Int8 with values 1 (yes), 0 (no) and null (unknown).
* The ``REGISTRY`` at the bottom classifies each harmonised variable by when its information
  exists relative to the crash.  Severity models may use only ``pre_crash`` and
  ``crash_circumstance`` variables; ``post_crash`` and ``outcome`` variables are rejected by
  :func:`assert_no_leakage`.
"""

from __future__ import annotations

from dataclasses import dataclass

import polars as pl

UNKNOWN = "unknown"


def _map(col: str, mapping: dict[str, list[int]], default: str = UNKNOWN) -> pl.Expr:
    """Map integer codes to categories; codes not listed -> ``default``."""
    expr = None
    for label, codes in mapping.items():
        cond = pl.col(col).is_in(codes)
        expr = (
            pl.when(cond).then(pl.lit(label))
            if expr is None
            else expr.when(cond).then(pl.lit(label))
        )
    assert expr is not None
    return expr.otherwise(pl.lit(default))


def binary(col: str, yes: list[int], no: list[int]) -> pl.Expr:
    return (
        pl.when(pl.col(col).is_in(yes))
        .then(pl.lit(1, dtype=pl.Int8))
        .when(pl.col(col).is_in(no))
        .then(pl.lit(0, dtype=pl.Int8))
        .otherwise(pl.lit(None, dtype=pl.Int8))
    )


# --------------------------------------------------------------------------------------
# Outcomes (KABCO).  INJ_SEV / MAX_SEV: 0 O, 1 C, 2 B, 3 A, 4 K, 5 injured severity
# unknown, 6 died prior to crash, 8 no person involved (MAX_SEV), 9 unknown.
# --------------------------------------------------------------------------------------
def fatal(col: str = "INJ_SEV") -> pl.Expr:
    """1 = fatal (K); 0 = O/C/B/A; null = 5, 6, 8, 9 (severity unknown / not a crash death)."""
    return binary(col, yes=[4], no=[0, 1, 2, 3])


def killed_or_serious(col: str = "INJ_SEV") -> pl.Expr:
    """1 = K or A; 0 = O/C/B; null = 5, 6, 8, 9."""
    return binary(col, yes=[3, 4], no=[0, 1, 2])


def any_injury(col: str = "INJ_SEV") -> pl.Expr:
    """1 = K/A/B/C or injured-severity-unknown (5); 0 = O; null = 6, 8, 9."""
    return binary(col, yes=[1, 2, 3, 4, 5], no=[0])


def kabco(col: str = "INJ_SEV") -> pl.Expr:
    """Ordinal 0 (O) .. 4 (K); null otherwise."""
    return pl.when(pl.col(col).is_between(0, 4)).then(pl.col(col).cast(pl.Int8)).otherwise(None)


# --------------------------------------------------------------------------------------
# Crash circumstances (accident table; codes identical FARS/CRSS and stable 2016-2024)
# --------------------------------------------------------------------------------------
def light_condition(col: str = "LGT_COND") -> pl.Expr:
    """1 daylight; 2 dark-not lighted; 3 dark-lighted; 4 dawn; 5 dusk; 6 dark-unknown
    lighting; 7 other; 8 not reported; 9 unknown."""
    return _map(
        col,
        {
            "daylight": [1],
            "dark_lighted": [3],
            "dark_not_lighted": [2],
            "dark_unknown_lighting": [6],
            "dawn_dusk": [4, 5],
        },
    )


def is_dark(col: str = "LGT_COND") -> pl.Expr:
    """1 = any dark condition (2, 3, 6); 0 = daylight/dawn/dusk (1, 4, 5); null otherwise."""
    return binary(col, yes=[2, 3, 6], no=[1, 4, 5])


def weather(col: str = "WEATHER") -> pl.Expr:
    """Crash-level atmospheric condition (WEATHER: 1 clear, 2 rain, 3 sleet/hail, 4 snow,
    5 fog/smog/smoke, 6 crosswinds, 7 blowing sand, 8 other, 10 cloudy, 11 blowing snow,
    12 freezing rain/drizzle, 98 not reported, 99 unknown)."""
    return _map(
        col,
        {
            "clear": [1],
            "cloudy": [10],
            "rain": [2, 12],
            "snow_sleet": [3, 4, 11],
            "fog": [5],
            "other": [6, 7, 8],
        },
    )


def surface_condition(col: str = "VSURCOND") -> pl.Expr:
    """Roadway surface (vehicle table): 1 dry; 2 wet, 6 standing/moving water; 3 snow,
    4 ice/frost, 10 slush; 0 non-trafficway, 5 sand, 7 oil, 8 other, 11 mud/dirt/gravel;
    98 not reported; 99 unknown."""
    return _map(
        col,
        {
            "dry": [1],
            "wet": [2, 6],
            "snow_ice": [3, 4, 10],
            "other": [0, 5, 7, 8, 11],
        },
    )


def speed_limit_band(col: str = "VSPD_LIM") -> pl.Expr:
    """Posted speed limit in mph (5-90); 0 = no statutory limit / non-trafficway (kept as its
    own level: mostly parking lots and driveways, not an unknown limit); 98 not reported;
    99 unknown."""
    c = pl.col(col)
    return (
        pl.when(c == 0)
        .then(pl.lit("none_nontrafficway"))
        .when(c.is_between(1, 25))
        .then(pl.lit("<=25"))
        .when(c.is_between(26, 35))
        .then(pl.lit("30-35"))
        .when(c.is_between(36, 45))
        .then(pl.lit("40-45"))
        .when(c.is_between(46, 55))
        .then(pl.lit("50-55"))
        .when(c.is_between(56, 65))
        .then(pl.lit("60-65"))
        .when(c.is_between(66, 95))
        .then(pl.lit("70+"))
        .otherwise(pl.lit(UNKNOWN))
    )


def speed_limit_mph(col: str = "VSPD_LIM") -> pl.Expr:
    return pl.when(pl.col(col).is_between(5, 95)).then(pl.col(col)).otherwise(None)


def junction(col: str = "RELJCT2") -> pl.Expr:
    """RELJCT2: 1 non-junction; 2 intersection, 3 intersection-related; 4 driveway access,
    8 driveway-access related; 5 ramp related, 17-20 interchange elements; 6 rail crossing,
    7 crossover, 16 shared-use path crossing; 98/99 unknown."""
    return _map(
        col,
        {
            "non_junction": [1],
            "intersection": [2, 3],
            "driveway": [4, 8],
            "interchange": [5, 17, 18, 19, 20],
            "other": [6, 7, 16],
        },
    )


def work_zone(col: str = "WRK_ZONE") -> pl.Expr:
    """0 none; 1 construction, 2 maintenance, 3 utility, 4 type unknown (all = work zone)."""
    return binary(col, yes=[1, 2, 3, 4], no=[0])


def time_of_day(col: str = "HOUR") -> pl.Expr:
    """HOUR 0-23; 99 unknown."""
    c = pl.col(col)
    return (
        pl.when(c.is_between(6, 9))
        .then(pl.lit("06-09"))
        .when(c.is_between(10, 15))
        .then(pl.lit("10-15"))
        .when(c.is_between(16, 19))
        .then(pl.lit("16-19"))
        .when(c.is_between(20, 23))
        .then(pl.lit("20-23"))
        .when(c.is_between(0, 5))
        .then(pl.lit("00-05"))
        .otherwise(pl.lit(UNKNOWN))
    )


def night(col: str = "HOUR") -> pl.Expr:
    """1 = 21:00-05:59; 0 = 06:00-20:59; null = unknown hour (99)."""
    c = pl.col(col)
    return (
        pl.when(c.is_between(0, 5) | c.is_between(21, 23))
        .then(pl.lit(1, dtype=pl.Int8))
        .when(c.is_between(6, 20))
        .then(pl.lit(0, dtype=pl.Int8))
        .otherwise(None)
    )


def weekend(col: str = "DAY_WEEK") -> pl.Expr:
    """DAY_WEEK 1 = Sunday ... 7 = Saturday; 9 unknown."""
    return binary(col, yes=[1, 7], no=[2, 3, 4, 5, 6])


def manner_of_collision(col: str = "MAN_COLL") -> pl.Expr:
    """0 first harmful event not a collision with a motor vehicle in transport; 1 front-to-
    rear; 2 front-to-front; 6 angle; 7/8 sideswipe; 9 rear-to-side; 10 rear-to-rear;
    11 other; 98/99 unknown."""
    return _map(
        col,
        {
            "not_mv_collision": [0],
            "rear_end": [1],
            "head_on": [2],
            "angle": [6],
            "sideswipe": [7, 8],
            "other_mv": [9, 10, 11],
        },
    )


# --------------------------------------------------------------------------------------
# Vehicles
# --------------------------------------------------------------------------------------
BODY_GROUPS: dict[str, list[int]] = {
    "car": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 17],
    "suv": [14, 15, 16, 19],
    "van": [20, 21, 22, 28, 29],
    "pickup": [30, 31, 32, 33, 34, 39],
    "light_truck_other": [40, 41, 42, 45, 48, 49],
    "bus": [50, 51, 52, 55, 58, 59],
    "medium_heavy_truck": [60, 61, 62, 63, 64, 66, 67, 71, 72, 78],
    "motorcycle": [80, 81, 82, 83, 84, 85, 86, 87, 88, 89],
    "other": [65, 73, 79, 90, 91, 92, 93, 94, 95, 96, 97],
}


def body_group(col: str = "BODY_TYP") -> pl.Expr:
    """Vehicle category from BODY_TYP (98 not reported / 99 unknown -> unknown).

    Pickup codes 30-32 (compact/standard/camper pickup) were merged into 34 'light pickup'
    from 2017; grouping them removes that break.
    """
    return _map(col, BODY_GROUPS)


def is_light_passenger_vehicle(col: str = "BODY_TYP") -> pl.Expr:
    return pl.col(col).is_between(1, 49)


def vehicle_age(model_year: str = "MOD_YEAR", year: str = "YEAR") -> pl.Expr:
    """Crash year minus model year (model year 9998/9999 unknown); -1 allowed (next-year
    models sold early); null outside [-1, 60]."""
    age = pl.col(year) - pl.col(model_year)
    return pl.when(pl.col(model_year).is_between(1900, 2030) & age.is_between(-1, 60)).then(
        age.clip(lower_bound=0)
    )


def vehicle_age_band(age: str = "veh_age") -> pl.Expr:
    c = pl.col(age)
    return (
        pl.when(c.is_between(0, 3))
        .then(pl.lit("0-3"))
        .when(c.is_between(4, 7))
        .then(pl.lit("4-7"))
        .when(c.is_between(8, 12))
        .then(pl.lit("8-12"))
        .when(c.is_between(13, 17))
        .then(pl.lit("13-17"))
        .when(c >= 18)
        .then(pl.lit("18+"))
        .otherwise(pl.lit(UNKNOWN))
    )


def speeding_related(col: str = "SPEEDREL") -> pl.Expr:
    """SPEEDREL: 0 no; 2 racing, 3 exceeded limit, 4 too fast for conditions, 5 specifics
    unknown (all = yes); 8 no driver present / unknown if driver present; 9 unknown.
    Code 8 is treated as 'no' (no driver to speed is the dominant case) -- see harmonisation
    doc; sensitivity analyses treat it as unknown."""
    return binary(col, yes=[2, 3, 4, 5], no=[0, 8])


def speeding_type(col: str = "SPEEDREL") -> pl.Expr:
    return _map(
        col,
        {
            "no": [0, 8],
            "exceeded_limit_or_racing": [2, 3],
            "too_fast_for_conditions": [4],
            "speeding_unspecified": [5],
        },
    )


def hit_and_run(col: str = "HIT_RUN") -> pl.Expr:
    return binary(col, yes=[1], no=[0])


# --------------------------------------------------------------------------------------
# Persons
# --------------------------------------------------------------------------------------
def person_type(col: str = "PER_TYP") -> pl.Expr:
    """1 driver; 2 passenger; 9 unknown occupant type (in transport); 3 occupant of a
    parked/working vehicle; 5 pedestrian; 6 bicyclist, 7 other pedalcyclist; 4, 8, 10-13, 19
    other non-motorists (personal conveyances, persons in buildings, unknown type)."""
    return _map(
        col,
        {
            "driver": [1],
            "passenger": [2, 9],
            "parked_vehicle_occupant": [3],
            "pedestrian": [5],
            "cyclist": [6, 7],
            "other_nonmotorist": [4, 8, 10, 11, 12, 13, 19],
        },
    )


def age_years(col: str = "AGE") -> pl.Expr:
    """AGE in years (0 = under 1); 998 not reported; 999 unknown."""
    return pl.when(pl.col(col).is_between(0, 120)).then(pl.col(col)).otherwise(None)


AGE_BANDS = ["0-14", "15-20", "21-24", "25-34", "35-44", "45-54", "55-64", "65-74", "75+"]


def age_band(col: str = "age") -> pl.Expr:
    c = pl.col(col)
    return (
        pl.when(c.is_between(0, 14))
        .then(pl.lit("0-14"))
        .when(c.is_between(15, 20))
        .then(pl.lit("15-20"))
        .when(c.is_between(21, 24))
        .then(pl.lit("21-24"))
        .when(c.is_between(25, 34))
        .then(pl.lit("25-34"))
        .when(c.is_between(35, 44))
        .then(pl.lit("35-44"))
        .when(c.is_between(45, 54))
        .then(pl.lit("45-54"))
        .when(c.is_between(55, 64))
        .then(pl.lit("55-64"))
        .when(c.is_between(65, 74))
        .then(pl.lit("65-74"))
        .when(c >= 75)
        .then(pl.lit("75+"))
        .otherwise(pl.lit(UNKNOWN))
    )


def sex(col: str = "SEX") -> pl.Expr:
    """1 male; 2 female; 3 (later years, if present) other; 8 not reported; 9 unknown."""
    return _map(col, {"male": [1], "female": [2]})


def seat_row(col: str = "SEAT_POS") -> pl.Expr:
    """SEAT_POS: 11 driver seat (front left); 12/13/18/19 other front; 21-29 second row;
    31-49 third/fourth row; 50-56 sleeper/cargo/exterior/trailing; 0 not an occupant;
    98/99 unknown."""
    return _map(
        col,
        {
            "front_left": [11],
            "front_other": [12, 13, 18, 19],
            "second_row": [21, 22, 23, 28, 29],
            "third_row_plus": [31, 32, 33, 38, 39, 41, 42, 43, 48, 49],
            "cargo_exterior_other": [50, 51, 52, 53, 54, 55, 56],
        },
    )


def restraint_use(col: str = "REST_USE") -> pl.Expr:
    """Occupant restraint (meaningful for occupants of vehicles fitted with belts).

    belted: 1 shoulder only, 2 lap only, 3 lap+shoulder, 6 racing harness, 8 restraint used
    type unknown; child_restraint: 4, 10, 11, 12; none: 7 (2016 'None Used'), 20 (2017+
    'None Used/Not Applicable'); helmet codes 5/16/17/19/29 (motorcyclists, 2016-2018 only)
    and 0 (2016 'Not applicable') / 96 (not an MV occupant) -> not_applicable;
    97 other / 98 not reported / 99 unknown -> unknown.
    """
    return _map(
        col,
        {
            "belted": [1, 2, 3, 6, 8],
            "child_restraint": [4, 10, 11, 12],
            "none": [7, 20],
            "not_applicable": [0, 5, 16, 17, 19, 29, 96],
        },
    )


def restraint_in_belted_seat(
    rest_col: str = "REST_USE", body_col: str = "BODY_TYP", seat_col: str = "SEAT_POS"
) -> pl.Expr:
    """Restraint use restricted to occupants of belt-equipped vehicles in belted seating rows.

    From 2017 code 20 means "none used *or* not applicable", and from 2019 every motorcyclist has
    REST_USE = 20 (helmets moved to HELM_USE).  Belt information is therefore only meaningful for
    occupants of vehicles with BODY_TYP 1-79 (light vehicles, buses, trucks) seated in rows 1-4
    (SEAT_POS 11-49); everyone else (motorcycles 80-89, other 90-97, cargo/exterior/trailing
    positions 50-56, unknown body/seat) is ``not_applicable``.  See docs/audit/person_injury_restraint.md §4.6.
    """
    eligible = pl.col(body_col).is_between(1, 79) & pl.col(seat_col).is_between(11, 49)
    return pl.when(eligible).then(restraint_use(rest_col)).otherwise(pl.lit("not_applicable"))


def helmet_use(
    rest_col: str = "REST_USE", helm_col: str = "HELM_USE", year: str = "YEAR"
) -> pl.Expr:
    """Motorcycle helmet use harmonised across the 2019 move from REST_USE to HELM_USE.

    2016-2018 (REST_USE) and 2019+ (HELM_USE): 5 DOT-compliant helmet, 16 other helmet,
    19 helmet unknown if DOT-compliant -> helmet; 17 no helmet -> none; 29 / 98 / 99 ->
    unknown; everything else (20 not applicable, 96 non-occupant, belt codes) -> not_applicable.
    """
    src = pl.when(pl.col(year) <= 2018).then(pl.col(rest_col)).otherwise(pl.col(helm_col))
    return (
        pl.when(src.is_in([5, 16, 19]))
        .then(pl.lit("helmet"))
        .when(src == 17)
        .then(pl.lit("none"))
        .when(src.is_in([29, 98, 99]) | src.is_null())
        .then(pl.lit(UNKNOWN))
        .otherwise(pl.lit("not_applicable"))
    )


def ejected(col: str = "EJECTION") -> pl.Expr:
    """POST-CRASH: 0 not ejected; 1 totally, 2 partially ejected; 3 ejected unknown degree;
    7 not reported? / 8 not applicable / 9 unknown -> null.  Used only as a mediator."""
    return binary(col, yes=[1, 2, 3], no=[0])


def police_reported(col: str) -> pl.Expr:
    """DRINKING / DRUGS person fields: 0 no; 1 yes; 8 not reported; 9 unknown."""
    return binary(col, yes=[1], no=[0])


def crss_alcohol(col: str = "ALCOHOL") -> pl.Expr:
    """CRSS ALCOHOL / VEH_ALCH: 1 involved; 2 not involved; 8 no applicable person /
    no driver present; 9 unknown.  ALCHL_IM / V_ALCH_IM use 1/2 only (imputed)."""
    return binary(col, yes=[1], no=[2])


# --------------------------------------------------------------------------------------
# Leakage registry
# --------------------------------------------------------------------------------------
@dataclass(frozen=True)
class VarInfo:
    timing: str  # pre_crash | crash_circumstance | post_crash | outcome | design | id
    level: str  # crash | vehicle | driver | person
    note: str = ""


REGISTRY: dict[str, VarInfo] = {
    # identifiers / design
    "case_id": VarInfo("id", "crash"),
    "YEAR": VarInfo("design", "crash", "survey/calendar year"),
    "WEIGHT": VarInfo("design", "crash"),
    "PSUSTRAT": VarInfo("design", "crash"),
    "PSU_VAR": VarInfo("design", "crash"),
    # outcomes
    "fatal": VarInfo("outcome", "crash"),
    "ka": VarInfo("outcome", "crash"),
    "injury": VarInfo("outcome", "crash"),
    "kabco": VarInfo("outcome", "crash"),
    "fatal_im": VarInfo("outcome", "crash"),
    "ka_im": VarInfo("outcome", "crash"),
    "n_killed": VarInfo("outcome", "crash"),
    "n_injured": VarInfo("outcome", "crash"),
    "killed": VarInfo("outcome", "person"),
    "killed_or_serious": VarInfo("outcome", "person"),
    # post-crash consequences (mediators / leakage risks)
    "ejected": VarInfo("post_crash", "person", "consequence of crash forces and restraint"),
    "rollover_any": VarInfo("post_crash", "crash", "crash outcome mechanism"),
    "fire_any": VarInfo("post_crash", "crash"),
    "towed_any": VarInfo("post_crash", "crash", "towing is decided after the crash"),
    "airbag_deployed": VarInfo("post_crash", "person"),
    # pre-crash
    "region": VarInfo("pre_crash", "crash"),
    "urbanicity": VarInfo("pre_crash", "crash", "CRSS area-level (PSU) urban/rural"),
    "rural": VarInfo("pre_crash", "crash", "FARS road-level rural/urban"),
    "tod": VarInfo("pre_crash", "crash"),
    "night": VarInfo("pre_crash", "crash"),
    "weekend": VarInfo("pre_crash", "crash"),
    "light": VarInfo("pre_crash", "crash"),
    "dark": VarInfo("pre_crash", "crash"),
    "weather": VarInfo("pre_crash", "crash"),
    "surface": VarInfo("pre_crash", "crash"),
    "speed_limit": VarInfo("pre_crash", "crash"),
    "interstate": VarInfo("pre_crash", "crash"),
    "junction": VarInfo("pre_crash", "crash"),
    "work_zone": VarInfo("pre_crash", "crash"),
    "speeding": VarInfo("pre_crash", "crash", "police judgement recorded after the crash"),
    "speeding_type": VarInfo("pre_crash", "crash", "exceeded limit/racing vs too fast for conditions vs unspecified"),
    "alcohol": VarInfo("pre_crash", "crash", "police-reported; ascertainment varies with severity"),
    "alcohol_im": VarInfo(
        "pre_crash", "crash", "NHTSA multiple-imputation-based single imputation"
    ),
    "drugs": VarInfo("pre_crash", "crash", "police-reported; very incomplete"),
    "distracted": VarInfo("pre_crash", "crash", "police-reported"),
    "hit_and_run": VarInfo(
        "crash_circumstance", "crash", "driver behaviour after the crash; excluded from models"
    ),
    "any_motorcycle": VarInfo("pre_crash", "crash"),
    "any_heavy_truck": VarInfo("pre_crash", "crash"),
    "any_pedestrian": VarInfo("crash_circumstance", "crash"),
    "any_cyclist": VarInfo("crash_circumstance", "crash"),
    "young_driver": VarInfo("pre_crash", "crash"),
    "older_driver": VarInfo("pre_crash", "crash"),
    "oldest_vehicle_age": VarInfo("pre_crash", "crash"),
    "n_vehicles": VarInfo("crash_circumstance", "crash"),
    "collision": VarInfo("crash_circumstance", "crash"),
    "crash_type": VarInfo("crash_circumstance", "crash"),
    # person-level
    "age": VarInfo("pre_crash", "person"),
    "age_band": VarInfo("pre_crash", "person"),
    "sex": VarInfo("pre_crash", "person"),
    "role": VarInfo("pre_crash", "person"),
    "seat": VarInfo("pre_crash", "person"),
    "restraint": VarInfo("pre_crash", "person", "police-reported; misreporting by survivors"),
    "helmet": VarInfo("pre_crash", "person"),
    "body": VarInfo("pre_crash", "vehicle"),
    "veh_age_band": VarInfo("pre_crash", "vehicle"),
    "veh_speeding": VarInfo("pre_crash", "vehicle"),
    "veh_alcohol": VarInfo("pre_crash", "vehicle"),
    "other_vehicle_heavy": VarInfo("crash_circumstance", "vehicle"),
}

MODEL_ALLOWED_TIMINGS = {"pre_crash", "crash_circumstance"}


def assert_no_leakage(features: list[str], allowed: set[str] | None = None) -> None:
    """Raise if any model feature is post-crash, an outcome, an id, or unregistered."""
    allowed = allowed or MODEL_ALLOWED_TIMINGS
    bad = []
    for f in features:
        info = REGISTRY.get(f)
        if info is None or info.timing not in allowed:
            bad.append((f, None if info is None else info.timing))
    if bad:
        raise ValueError(f"features not permitted in a severity model: {bad}")
