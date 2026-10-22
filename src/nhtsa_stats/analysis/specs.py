"""Shared covariate sets and reference levels for every CRSS/FARS model.

Keeping one definition guarantees that crude, adjusted, interaction and machine-learning
analyses describe the same variables with the same reference categories.

Adjustment sets (see docs/methodology.md for the causal reasoning):

* ``PRE_CRASH`` -- circumstances that exist before the crash (time, light, weather, surface,
  road, area, driver age mix, vehicle mix, and the police-reported behaviours speeding and
  alcohol).  This is the main adjustment set for "total" adjusted associations.
* ``CIRCUMSTANCE`` -- crash configuration (crash type, number of vehicles).  Configuration is
  plausibly a *mediator* of several pre-crash factors (e.g. darkness -> pedestrian crash), so
  models that add it estimate associations *net of* configuration, not total associations.

Tri-state indicators enter as 'no' (reference) / 'yes' / 'unknown' so that unknown values are
neither dropped silently nor treated as 'no'; complete-case sensitivity analyses are run for
the key exposures.

Alcohol: the police-reported CRSS ``ALCOHOL`` field has a coding break in 2019 (share coded
"unknown" rose from ~12% to ~37% of non-fatal and from ~30% to ~55% of fatal crashes) and its
"unknown" category is strongly outcome-dependent.  Models therefore adjust for NHTSA's imputed
``ALCHL_IM`` (``alcohol_im``), which equals ``ALCOHOL`` in 99.998% of rows where the latter is
known and fills only the unknowns; the police-reported version is used in sensitivity analyses.
"""

from __future__ import annotations

from nhtsa_stats import config

YEAR_LEVELS = list(config.YEARS)

CRASH_LEVELS: dict[str, list] = {
    "light": [
        "daylight",
        "dawn_dusk",
        "dark_lighted",
        "dark_not_lighted",
        "dark_unknown_lighting",
        "unknown",
    ],
    "weather": ["clear", "cloudy", "rain", "snow_sleet", "fog", "other", "unknown"],
    "surface": ["dry", "wet", "snow_ice", "other", "unknown"],
    "speed_limit": ["30-35", "<=25", "40-45", "50-55", "60-65", "70+", "none_nontrafficway", "unknown"],
    "tod": ["10-15", "06-09", "16-19", "20-23", "00-05", "unknown"],
    "junction": ["non_junction", "intersection", "driveway", "interchange", "other", "unknown"],
    "urbanicity": ["urban", "rural"],
    "region": ["south", "northeast", "midwest", "west"],
    "crash_type": [
        "mv_rear_end",
        "mv_angle",
        "mv_sideswipe",
        "mv_head_on",
        "mv_other",
        "sv_on_roadway",
        "sv_off_roadway",
        "sv_rollover_first",
        "pedestrian",
        "cyclist",
    ],
    "n_vehicles": ["2", "1", "3+"],
    "speeding_type": ["no", "exceeded_limit_or_racing", "too_fast_for_conditions", "speeding_unspecified", "unknown"],
    "YEAR": YEAR_LEVELS,
}
TRI = ["no", "yes", "unknown"]
CRASH_TRI = [
    "speeding",
    "alcohol",
    "young_driver",
    "older_driver",
    "interstate",
    "work_zone",
    "weekend",
    "any_motorcycle",
    "any_heavy_truck",
    "drugs",
    "distracted",
    "alcohol_im",
]
for _v in CRASH_TRI:
    CRASH_LEVELS[_v] = TRI

PRE_CRASH = [
    "YEAR",
    "region",
    "urbanicity",
    "tod",
    "weekend",
    "light",
    "weather",
    "surface",
    "speed_limit",
    "interstate",
    "junction",
    "work_zone",
    "young_driver",
    "older_driver",
    "any_motorcycle",
    "any_heavy_truck",
    "speeding",
    "alcohol_im",
]
CIRCUMSTANCE = ["crash_type", "n_vehicles"]

# Human-readable names for tables and the interface.
LABELS: dict[str, str] = {
    "light": "Light condition",
    "weather": "Weather",
    "surface": "Road surface",
    "speed_limit": "Speed limit (mph)",
    "tod": "Time of day",
    "weekend": "Weekend (Sat/Sun)",
    "junction": "Junction",
    "urbanicity": "Area (CRSS urbanicity)",
    "region": "Census region",
    "interstate": "Interstate",
    "work_zone": "Work zone",
    "young_driver": "Driver aged 15-20 involved",
    "older_driver": "Driver aged 65+ involved",
    "any_motorcycle": "Motorcycle involved",
    "any_heavy_truck": "Medium/heavy truck or bus involved",
    "speeding": "Speeding-related (police-reported)",
    "alcohol": "Alcohol involved (police-reported)",
    "alcohol_im": "Alcohol involved (NHTSA-imputed)",
    "drugs": "Drug involvement (police-reported)",
    "distracted": "Distracted driver (police-reported)",
    "crash_type": "Crash type",
    "speeding_type": "Speeding type (police-reported)",
    "n_vehicles": "Vehicles in transport",
    "YEAR": "Year",
}

PERSON_LEVELS: dict[str, list] = {
    "age_band": [
        "25-34",
        "0-14",
        "15-20",
        "21-24",
        "35-44",
        "45-54",
        "55-64",
        "65-74",
        "75+",
        "unknown",
    ],
    "sex": ["male", "female", "unknown"],
    "role": ["driver", "front_passenger", "rear_passenger", "other_passenger"],
    "restraint": ["belted", "none", "child_restraint", "not_applicable", "unknown"],
    "body": [
        "car",
        "suv",
        "pickup",
        "van",
        "light_truck_other",
        "motorcycle",
        "bus",
        "medium_heavy_truck",
        "other",
        "unknown",
    ],
    "other_vehicle_body": [
        "none_or_multi",
        "car",
        "suv",
        "pickup",
        "van",
        "light_truck_other",
        "motorcycle",
        "bus",
        "medium_heavy_truck",
        "other",
        "unknown",
    ],
    "veh_age_band": ["0-3", "4-7", "8-12", "13-17", "18+", "unknown"],
    "veh_speeding": TRI,
    "veh_alcohol": TRI,
}
