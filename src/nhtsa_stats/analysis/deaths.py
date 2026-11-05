"""Where US road deaths concentrate (FARS census, NHTSA auxiliary-file definitions).

FARS is a census of fatal crashes: counts are observed and carry no sampling error.  Only the
alcohol quantities are estimated -- NHTSA multiply imputes driver/non-occupant BAC (10
implicates).  For such a quantity we report the mean over implicates and the MI standard error
sqrt((1 + 1/10) * B), B being the between-implicate variance (the within variance is 0 for a
census count).  Behaviour groups overlap (a death can be alcohol- *and* speeding-related), so
shares of different groups do not add up; ``behaviour_overlap`` / ``behaviour_summary`` give
the exclusive combinations and the union.

Variable definitions (verified by cross-tabulation against the labelled main-file variables):

* death = person with INJ_SEV == 4; ``per_aux.A_PTYPE`` 1 driver, 2 passenger, 3 pedestrian,
  4 pedalcyclist, 5 other non-occupant; ``veh_aux.A_BODY`` 1-5 passenger vehicle, 6 large truck,
  7 motorcycle, 8 bus, 9 other/unknown; belt use ``A_RESTUSE`` / helmet ``A_HELMUSE`` 1 used,
  2 not used, otherwise unknown; crash flags from ``acc_aux`` (1 = yes).
* alcohol-impaired-driving crash in implicate m: ``midrvacc.A{m}`` >= 8 (no row = not impaired).
* all results are associations/descriptions of police-reported fatal crashes, not causal effects.
"""

from __future__ import annotations

import logging

import pandas as pd
import polars as pl

from nhtsa_stats import config
from nhtsa_stats.ingestion.cache import load_table
from nhtsa_stats.processing import harmonize as h
from nhtsa_stats.reporting.io import save_table

log = logging.getLogger(__name__)
MODULE = "deaths"

K_MI = 10
IMPLICATES = list(range(1, K_MI + 1))
BAC_LIMIT = 8  # hundredths of g/dL
OBSERVED = "observed"
ESTIMATED = "estimated (MI)"

STATES: dict[int, tuple[str, str]] = {
    1: ("AL", "Alabama"),
    2: ("AK", "Alaska"),
    4: ("AZ", "Arizona"),
    5: ("AR", "Arkansas"),
    6: ("CA", "California"),
    8: ("CO", "Colorado"),
    9: ("CT", "Connecticut"),
    10: ("DE", "Delaware"),
    11: ("DC", "District of Columbia"),
    12: ("FL", "Florida"),
    13: ("GA", "Georgia"),
    15: ("HI", "Hawaii"),
    16: ("ID", "Idaho"),
    17: ("IL", "Illinois"),
    18: ("IN", "Indiana"),
    19: ("IA", "Iowa"),
    20: ("KS", "Kansas"),
    21: ("KY", "Kentucky"),
    22: ("LA", "Louisiana"),
    23: ("ME", "Maine"),
    24: ("MD", "Maryland"),
    25: ("MA", "Massachusetts"),
    26: ("MI", "Michigan"),
    27: ("MN", "Minnesota"),
    28: ("MS", "Mississippi"),
    29: ("MO", "Missouri"),
    30: ("MT", "Montana"),
    31: ("NE", "Nebraska"),
    32: ("NV", "Nevada"),
    33: ("NH", "New Hampshire"),
    34: ("NJ", "New Jersey"),
    35: ("NM", "New Mexico"),
    36: ("NY", "New York"),
    37: ("NC", "North Carolina"),
    38: ("ND", "North Dakota"),
    39: ("OH", "Ohio"),
    40: ("OK", "Oklahoma"),
    41: ("OR", "Oregon"),
    42: ("PA", "Pennsylvania"),
    44: ("RI", "Rhode Island"),
    45: ("SC", "South Carolina"),
    46: ("SD", "South Dakota"),
    47: ("TN", "Tennessee"),
    48: ("TX", "Texas"),
    49: ("UT", "Utah"),
    50: ("VT", "Vermont"),
    51: ("VA", "Virginia"),
    53: ("WA", "Washington"),
    54: ("WV", "West Virginia"),
    55: ("WI", "Wisconsin"),
    56: ("WY", "Wyoming"),
}
FIPS_TO_USPS = {k: v[0] for k, v in STATES.items()}

ALL = pl.col("YEAR").is_not_null()  # a per-row True (a bare literal would sum to 1)
KEY = ["YEAR", "ST_CASE"]
YEARS_COMPARE = (2019, 2021, 2024)

# ---------------------------------------------------------------------------------------
# Multiple-imputation aggregation primitives (pure functions)
# ---------------------------------------------------------------------------------------


def _pick(items: list, k: int):
    return items[k] if len(items) > 1 else items[0]


def mi_mean(exprs: list[pl.Expr]) -> pl.Expr:
    """Mean of a quantity over its implicates (one expression per implicate)."""
    return pl.mean_horizontal(*exprs) if len(exprs) > 1 else exprs[0].cast(pl.Float64)


def mi_se(exprs: list[pl.Expr]) -> pl.Expr:
    """MI standard error sqrt((1 + 1/K) B); 0 for a single (observed) value."""
    k = len(exprs)
    if k == 1:
        return pl.lit(0.0)
    mean = pl.mean_horizontal(*exprs)
    between = pl.sum_horizontal(*[(e - mean) ** 2 for e in exprs]) / (k - 1)
    return ((1 + 1 / k) * between).sqrt()


def _cols(name: str, k: int) -> list[pl.Expr]:
    return [pl.col(f"{name}__{i}") for i in range(k)]


def agg_sums(df: pl.DataFrame, by: list[str], items: dict[str, list[pl.Expr]]) -> pl.DataFrame:
    """Per group, the sum of each boolean/0-1 expression; columns ``name__i`` (i = implicate)."""
    aggs = [
        e.fill_null(False).cast(pl.Int64).sum().alias(f"{name}__{i}")
        for name, exprs in items.items()
        for i, e in enumerate(exprs)
    ]
    if by:
        return df.group_by(by).agg(aggs).sort(by)
    return df.select(aggs)


def ratio_exprs(num: list[pl.Expr], den: list[pl.Expr]) -> list[pl.Expr]:
    """Per-implicate ratios (null where the denominator is 0)."""
    k = max(len(num), len(den))
    return [
        pl.when(_pick(den, i) > 0).then(_pick(num, i) / _pick(den, i)).otherwise(None)
        for i in range(k)
    ]


def long_counts(
    df: pl.DataFrame, by: list[str], items: dict[str, list[pl.Expr]], key: str = "segment"
) -> pl.DataFrame:
    """Long table ``by + [key, deaths, mi_se]`` of item totals (mean/SE over implicates)."""
    wide = agg_sums(df, by, items)
    parts = []
    for name, exprs in items.items():
        cols = _cols(name, len(exprs))
        parts.append(
            wide.select(
                *by,
                pl.lit(name).alias(key),
                mi_mean(cols).cast(pl.Float64).alias("deaths"),
                mi_se(cols).alias("mi_se"),
            )
        )
    return pl.concat(parts)


def estimate_type(mi: bool) -> str:
    return ESTIMATED if mi else OBSERVED


# ---------------------------------------------------------------------------------------
# Category expressions
# ---------------------------------------------------------------------------------------


def age_band(age: str = "age") -> pl.Expr:
    c = pl.col(age)
    return (
        pl.when(c.is_null() | (c > 120))
        .then(pl.lit("unknown"))
        .when(c < 16)
        .then(pl.lit("<16"))
        .when(c < 25)
        .then(pl.lit("16-24"))
        .when(c < 35)
        .then(pl.lit("25-34"))
        .when(c < 55)
        .then(pl.lit("35-54"))
        .when(c < 75)
        .then(pl.lit("55-74"))
        .otherwise(pl.lit("75+"))
    )


AGE_BANDS = ["<16", "16-24", "25-34", "35-54", "55-74", "75+", "unknown"]


def ped_age_band(age: str = "age") -> pl.Expr:
    c = pl.col(age)
    return (
        pl.when(c.is_null() | (c > 120))
        .then(pl.lit("unknown"))
        .when(c < 15)
        .then(pl.lit("<15"))
        .when(c < 25)
        .then(pl.lit("15-24"))
        .when(c < 45)
        .then(pl.lit("25-44"))
        .when(c < 65)
        .then(pl.lit("45-64"))
        .otherwise(pl.lit("65+"))
    )


PED_AGE_BANDS = ["<15", "15-24", "25-44", "45-64", "65+", "unknown"]


def licence_category(status: str = "L_STATUS") -> pl.Expr:
    """0 not licensed, 1 suspended, 2 revoked, 3 expired, 4 cancelled/denied, 6 valid; 7/9/other
    unknown."""
    c = pl.col(status)
    return (
        pl.when(c == 0)
        .then(pl.lit("unlicensed"))
        .when(c.is_in([1, 2]))
        .then(pl.lit("suspended_or_revoked"))
        .when(c.is_in([3, 4]))
        .then(pl.lit("expired_or_cancelled"))
        .when(c == 6)
        .then(pl.lit("valid"))
        .otherwise(pl.lit("unknown"))
    )


def victim_role(ptype: pl.Expr, risk_vehicle: pl.Expr) -> pl.Expr:
    """Role of a killed person relative to the 'risk vehicle' of a behaviour group."""
    risk = risk_vehicle.fill_null(False)
    return (
        pl.when((ptype == 1) & risk)
        .then(pl.lit("risk_driver"))
        .when((ptype == 2) & risk)
        .then(pl.lit("risk_passenger"))
        .when(ptype.is_in([1, 2]))
        .then(pl.lit("other_vehicle_occupant"))
        .when(ptype.is_in([3, 4]))
        .then(pl.lit("pedestrian_or_cyclist"))
        .when(ptype == 5)
        .then(pl.lit("other_nonoccupant"))
    )


ROLES = [
    "risk_driver",
    "risk_passenger",
    "other_vehicle_occupant",
    "pedestrian_or_cyclist",
    "other_nonoccupant",
]

# FARS person.LOCATION (non-motorist location; labels in outputs/audit/codebook.csv):
#   1,2,3,9 at intersection (marked crosswalk / unmarked / not in crosswalk / unknown)
#   10,11,13 not at intersection, on the roadway (marked crosswalk / not / crosswalk unknown);
#   16 bicycle lane (a marked lane of the roadway) is counted here too
#   14 parking lane, 20 shoulder/roadside, 22 median/crossing island -> roadside group
#   21 sidewalk, 23 driveway access, 24 shared-use path, 25 non-trafficway area -> off-road
#   0 (occupant), 28 "other", 98 not reported, 99 unknown, null -> unknown
LOCATION_GROUPS = {
    "at_intersection": [1, 2, 3, 9],
    "midblock_roadway": [10, 11, 13, 16],
    "roadside_shoulder_median_parking": [14, 20, 22],
    "sidewalk_or_off_road": [21, 23, 24, 25],
}
LOCATION_LEVELS = [*LOCATION_GROUPS, "unknown"]


def location_group(col: str = "location") -> pl.Expr:
    c = pl.col(col)
    expr = None
    for name, codes in LOCATION_GROUPS.items():
        expr = (
            pl.when(c.is_in(codes)).then(pl.lit(name))
            if expr is None
            else expr.when(c.is_in(codes)).then(pl.lit(name))
        )
    return expr.otherwise(pl.lit("unknown"))


LIGHT_LEVELS = [
    "daylight",
    "dark_lighted",
    "dark_not_lighted",
    "dark_unknown_lighting",
    "dawn_dusk",
    "other_unknown",
]


def light_group(col: str = "lgt_cond") -> pl.Expr:
    c = pl.col(col)
    return (
        pl.when(c == 1)
        .then(pl.lit("daylight"))
        .when(c == 3)
        .then(pl.lit("dark_lighted"))
        .when(c == 2)
        .then(pl.lit("dark_not_lighted"))
        .when(c == 6)
        .then(pl.lit("dark_unknown_lighting"))
        .when(c.is_in([4, 5]))
        .then(pl.lit("dawn_dusk"))
        .otherwise(pl.lit("other_unknown"))
    )


# acc_aux.A_ROADFC: 1 interstate, 2 other freeway/expressway, 3 principal arterial (other),
# 4 minor arterial, 5 collector (FUNC_SYS 5 major + 6 minor collector), 6 local, 7 unknown
# (incl. FUNC_SYS 96/98/99); verified against accident.FUNC_SYS.
ROAD_LEVELS = [
    "interstate_freeway",
    "principal_arterial",
    "minor_arterial",
    "collector",
    "local",
    "unknown",
]


def road_class(col: str = "roadfc") -> pl.Expr:
    c = pl.col(col)
    return (
        pl.when(c.is_in([1, 2]))
        .then(pl.lit("interstate_freeway"))
        .when(c == 3)
        .then(pl.lit("principal_arterial"))
        .when(c == 4)
        .then(pl.lit("minor_arterial"))
        .when(c == 5)
        .then(pl.lit("collector"))
        .when(c == 6)
        .then(pl.lit("local"))
        .otherwise(pl.lit("unknown"))
    )


SPEED_LEVELS = ["<=25", "30-35", "40-45", "50-55", "60+", "unknown"]


def speed_limit_band(col: str = "str_vspd") -> pl.Expr:
    """Posted limit of the striking vehicle's road; 0 (no statutory limit), 98, 99, null unknown."""
    c = pl.col(col)
    return (
        pl.when(c.is_null() | (c <= 0) | (c >= 98))
        .then(pl.lit("unknown"))
        .when(c <= 25)
        .then(pl.lit("<=25"))
        .when(c <= 35)
        .then(pl.lit("30-35"))
        .when(c <= 45)
        .then(pl.lit("40-45"))
        .when(c <= 55)
        .then(pl.lit("50-55"))
        .otherwise(pl.lit("60+"))
    )


STRIKER_LEVELS = [
    "car",
    "suv",
    "pickup",
    "van",
    "large_truck",
    "bus",
    "motorcycle",
    "other_unknown",
]


def striking_vehicle(col: str = "str_body") -> pl.Expr:
    c = pl.col(col)
    return (
        pl.when(c == 1)
        .then(pl.lit("car"))
        .when(c == 3)
        .then(pl.lit("suv"))
        .when(c == 2)
        .then(pl.lit("pickup"))
        .when(c == 4)
        .then(pl.lit("van"))
        .when(c == 6)
        .then(pl.lit("large_truck"))
        .when(c == 8)
        .then(pl.lit("bus"))
        .when(c == 7)
        .then(pl.lit("motorcycle"))
        .otherwise(pl.lit("other_unknown"))
    )


# ---------------------------------------------------------------------------------------
# Data assembly
# ---------------------------------------------------------------------------------------


def _bac_flags(prefix: str, src: str, threshold: int = BAC_LIMIT) -> list[pl.Expr]:
    return [
        (pl.col(f"{src}{m}") >= threshold).fill_null(False).alias(f"{prefix}{m}")
        for m in IMPLICATES
    ]


def build_driver_frame() -> pl.DataFrame:
    """Drivers (PER_TYP 1) of all fatal-crash vehicles with licence, record, speeding and BAC."""
    per = load_table(
        "FARS", "person", None, ["ST_CASE", "STATE", "VEH_NO", "PER_NO", "PER_TYP"]
    ).filter(pl.col("PER_TYP") == 1)
    veh = load_table(
        "FARS",
        "vehicle",
        None,
        [
            "ST_CASE",
            "VEH_NO",
            "L_STATUS",
            "PREV_DWI",
            "PREV_SPD",
            "PREV_ACC",
            "PREV_SUS1",
            "PREV_SUS2",
            "PREV_SUS3",
        ],
    )
    vaux = load_table("FARS", "veh_aux", None, ["ST_CASE", "VEH_NO", "A_SPVEH"])
    mi = load_table(
        "FARS", "miper", None, ["ST_CASE", "VEH_NO", "PER_NO"] + [f"P{m}" for m in IMPLICATES]
    )
    d = (
        per.join(veh, on=[*KEY, "VEH_NO"], how="left")
        .join(vaux, on=[*KEY, "VEH_NO"], how="left")
        .join(mi, on=[*KEY, "VEH_NO", "PER_NO"], how="left")
    )
    return d.rename({"A_SPVEH": "spveh"})


def build_death_frame(drivers: pl.DataFrame | None = None) -> pl.DataFrame:
    """One row per person killed with every classification used by the tables."""
    drivers = build_driver_frame() if drivers is None else drivers
    per = load_table(
        "FARS",
        "person",
        None,
        ["ST_CASE", "STATE", "VEH_NO", "PER_NO", "INJ_SEV", "AGE", "SEX", "LOCATION", "STR_VEH"],
    ).filter(pl.col("INJ_SEV") == 4)
    paux = load_table(
        "FARS",
        "per_aux",
        None,
        ["ST_CASE", "VEH_NO", "PER_NO", "A_PTYPE", "A_RESTUSE", "A_HELMUSE"],
    )
    veh = (
        load_table("FARS", "vehicle", None, ["ST_CASE", "VEH_NO", "MOD_YEAR", "VSPD_LIM"])
        .join(
            load_table("FARS", "veh_aux", None, ["ST_CASE", "VEH_NO", "A_BODY", "A_SPVEH"]),
            on=[*KEY, "VEH_NO"],
            how="left",
        )
        .rename({"A_BODY": "body", "A_SPVEH": "spveh", "MOD_YEAR": "mod_year", "VSPD_LIM": "vspd"})
    )
    acc = load_table("FARS", "accident", None, ["ST_CASE", "LGT_COND"])
    caux = load_table(
        "FARS",
        "acc_aux",
        None,
        [
            "ST_CASE",
            "A_SPCRA",
            "A_LT",
            "A_RD",
            "A_HR",
            "A_DIST",
            "A_DROWSY",
            "A_POLPUR",
            "A_RU",
            "A_TOD",
            "A_INTSEC",
            "A_ROADFC",
        ],
    )
    midrv = load_table("FARS", "midrvacc", None, ["ST_CASE"] + [f"A{m}" for m in IMPLICATES])
    miper = load_table(
        "FARS", "miper", None, ["ST_CASE", "VEH_NO", "PER_NO"] + [f"P{m}" for m in IMPLICATES]
    )
    own = veh.select([*KEY, "VEH_NO", "mod_year", "body", "spveh"])
    striker = veh.select(
        *KEY,
        pl.col("VEH_NO").alias("STR_VEH"),
        pl.col("vspd").alias("str_vspd"),
        pl.col("body").alias("str_body"),
    )
    crash_inv = (
        drivers.filter(pl.col("L_STATUS").is_in([0, 1, 2, 3, 4]))
        .select(KEY)
        .unique()
        .with_columns(ALL.alias("inv_crash"))
    )
    risk_veh = drivers.select([*KEY, "VEH_NO", *[f"P{m}" for m in IMPLICATES]]).rename(
        {f"P{m}": f"rp{m}" for m in IMPLICATES}
    )
    d = (
        per.join(paux, on=[*KEY, "VEH_NO", "PER_NO"], how="left")
        .join(own, on=[*KEY, "VEH_NO"], how="left")
        .join(striker, on=[*KEY, "STR_VEH"], how="left")
        .join(acc, on=KEY, how="left")
        .join(caux, on=KEY, how="left")
        .join(midrv, on=KEY, how="left")
        .join(
            miper.rename({f"P{m}": f"pp{m}" for m in IMPLICATES}),
            on=[*KEY, "VEH_NO", "PER_NO"],
            how="left",
        )
        .join(risk_veh, on=[*KEY, "VEH_NO"], how="left")
        .join(crash_inv, on=KEY, how="left")
    )
    d = d.rename(
        {
            "A_PTYPE": "ptype",
            "AGE": "age",
            "SEX": "sex",
            "LOCATION": "location",
            "LGT_COND": "lgt_cond",
            "A_RU": "ru",
            "A_TOD": "tod",
            "A_ROADFC": "roadfc",
        }
    )
    return add_death_flags(d)


def add_death_flags(d: pl.DataFrame) -> pl.DataFrame:
    """Derive the 0/1 flags (alc_m, pbac_m, risk_alc_m, spd, unbelted, ...) from raw columns."""
    occ = pl.col("ptype").is_in([1, 2])
    pv = occ & pl.col("body").is_in([1, 2, 3, 4, 5])
    mc = occ & (pl.col("body") == 7)
    return d.with_columns(
        *[(pl.col(f"A{m}") >= BAC_LIMIT).fill_null(False).alias(f"alc_{m}") for m in IMPLICATES],
        *[(pl.col(f"pp{m}") >= BAC_LIMIT).fill_null(False).alias(f"pbac_{m}") for m in IMPLICATES],
        *[
            (pl.col(f"rp{m}") >= BAC_LIMIT).fill_null(False).alias(f"risk_alc_{m}")
            for m in IMPLICATES
        ],
        (pl.col("A_SPCRA") == 1).fill_null(False).alias("spd"),
        (pl.col("spveh") == 1).fill_null(False).alias("risk_spd"),
        (pl.col("body") == 6).fill_null(False).alias("risk_lt"),
        pv.alias("pv"),
        mc.alias("mc"),
        pl.col("inv_crash").fill_null(False),
    ).with_columns(
        (pv & (pl.col("A_RESTUSE") == 1)).alias("belted"),
        (pv & (pl.col("A_RESTUSE") == 2)).alias("unbelted"),
        (pv & ~pl.col("A_RESTUSE").is_in([1, 2])).alias("restraint_unknown"),
        (mc & (pl.col("A_HELMUSE") == 1)).alias("helmeted"),
        (mc & (pl.col("A_HELMUSE") == 2)).alias("unhelmeted"),
        (mc & ~pl.col("A_HELMUSE").is_in([1, 2])).alias("helmet_unknown"),
    )


# ---------------------------------------------------------------------------------------
# Segments (annual / segments / states)
# ---------------------------------------------------------------------------------------


def _alc() -> list[pl.Expr]:
    return [pl.col(f"alc_{m}") for m in IMPLICATES]


def segment_items() -> dict[str, list[pl.Expr]]:
    """name -> expressions (1 = observed, 10 = one per implicate) selecting the deaths in it."""
    ptype = pl.col("ptype")
    occ = ptype.is_in([1, 2])
    flag = lambda col, val: [pl.col(col) == val]  # noqa: E731
    unb, unh, spd = pl.col("unbelted"), pl.col("unhelmeted"), pl.col("spd")
    return {
        "all": [ALL],
        "alcohol_impaired": _alc(),
        "speeding": [spd],
        "any_of_four": [a | spd | unb | unh for a in _alc()],
        "alcohol_and_speeding": [a & spd for a in _alc()],
        "two_or_more": [n_flags(_factor_exprs(), i) >= 2 for i in range(K_MI)],
        "unbelted": [unb],
        "belted": [pl.col("belted")],
        "restraint_unknown": [pl.col("restraint_unknown")],
        "unhelmeted": [unh],
        "helmeted": [pl.col("helmeted")],
        "helmet_unknown": [pl.col("helmet_unknown")],
        "pv_occupants": [pl.col("pv")],
        "motorcyclists": [pl.col("mc")],
        "pedestrians": [ptype == 3],
        "cyclists": [ptype == 4],
        "other_nonoccupants": [ptype == 5],
        "large_truck_occupants": [occ & (pl.col("body") == 6)],
        "other_vehicle_occupants": [occ & pl.col("body").is_in([8, 9])],
        "large_truck_crash": flag("A_LT", 1),
        "rural": flag("ru", 1),
        "urban": flag("ru", 2),
        "night": flag("tod", 2),
        "day": flag("tod", 1),
        "roadway_departure": flag("A_RD", 1),
        "hit_and_run": flag("A_HR", 1),
        "distracted": flag("A_DIST", 1),
        "drowsy": flag("A_DROWSY", 1),
        "police_pursuit": flag("A_POLPUR", 1),
        "intersection": flag("A_INTSEC", 1),
        "invalid_licence_crash": [pl.col("inv_crash")],
    }


MI_SEGMENTS = {"alcohol_impaired", "any_of_four", "alcohol_and_speeding", "two_or_more"}


def annual_table(deaths: pl.DataFrame) -> pl.DataFrame:
    out = long_counts(deaths, ["YEAR"], segment_items())
    return out.with_columns(
        pl.col("segment")
        .is_in(list(MI_SEGMENTS))
        .map_elements(estimate_type, return_dtype=pl.Utf8)
        .alias("estimate_type")
    ).sort(["YEAR", "segment"], maintain_order=True)


def pct_change(new: pl.Expr, old: pl.Expr) -> pl.Expr:
    return pl.when(old > 0).then(new / old - 1).otherwise(None)


def segments_table(deaths: pl.DataFrame) -> pl.DataFrame:
    items = segment_items()
    pooled = long_counts(deaths, [], items)
    total = pooled.filter(pl.col("segment") == "all")["deaths"].item()
    n_years = deaths["YEAR"].n_unique()
    ann = annual_table(deaths)
    by_year = ann.pivot(on="YEAR", index="segment", values="deaths")
    ren = {str(y): f"deaths_{y}" for y in YEARS_COMPARE}
    by_year = by_year.select("segment", *ren).rename(ren)
    out = pooled.join(by_year, on="segment").with_columns(
        (pl.col("deaths") / total).alias("share_of_all"),
        (pl.col("deaths") / n_years).alias("per_year"),
        pct_change(pl.col("deaths_2021"), pl.col("deaths_2019")).alias("pct_change_2019_2021"),
        pct_change(pl.col("deaths_2024"), pl.col("deaths_2021")).alias("pct_change_2021_2024"),
        pct_change(pl.col("deaths_2024"), pl.col("deaths_2019")).alias("pct_change_2019_2024"),
        pl.col("segment")
        .is_in(list(MI_SEGMENTS))
        .map_elements(estimate_type, return_dtype=pl.Utf8)
        .alias("estimate_type"),
    )
    order = {s: i for i, s in enumerate(items)}
    return (
        out.select(
            "segment",
            "deaths",
            "share_of_all",
            "per_year",
            "deaths_2019",
            "deaths_2021",
            "deaths_2024",
            "pct_change_2019_2021",
            "pct_change_2021_2024",
            "pct_change_2019_2024",
            "mi_se",
            "estimate_type",
        )
        .with_columns(pl.col("segment").replace_strict(order, return_dtype=pl.Int64).alias("_o"))
        .sort("_o")
        .drop("_o")
    )


# ---------------------------------------------------------------------------------------
# Behaviour overlap
# ---------------------------------------------------------------------------------------

FACTORS = ["alcohol", "speeding", "unbelted", "unhelmeted"]


def _factor_exprs() -> dict[str, list[pl.Expr]]:
    return {
        "alcohol": _alc(),
        "speeding": [pl.col("spd")],
        "unbelted": [pl.col("unbelted")],
        "unhelmeted": [pl.col("unhelmeted")],
    }


def _combo_exprs(f: dict[str, list[pl.Expr]], combo: tuple[int, ...]) -> list[pl.Expr]:
    k = max(len(v) for v in f.values())
    out = []
    for i in range(k):
        e = ALL
        for name, flag in zip(FACTORS, combo, strict=True):
            col = _pick(f[name], i)
            e = e & (col if flag else ~col)
        out.append(e)
    return out


def _all_combos() -> list[tuple[int, ...]]:
    return [(a, s, u, h_) for a in (0, 1) for s in (0, 1) for u in (0, 1) for h_ in (0, 1)]


def overlap_table(deaths: pl.DataFrame) -> pl.DataFrame:
    """The 16 exclusive combinations of the four behaviour flags (MI mean over implicates)."""
    f = _factor_exprs()
    items = {"".join(map(str, c)): _combo_exprs(f, c) for c in _all_combos()}
    items["_all"] = [ALL]
    long = long_counts(deaths, [], items)
    total = long.filter(pl.col("segment") == "_all")["deaths"].item()
    rows = []
    for c in _all_combos():
        r = long.filter(pl.col("segment") == "".join(map(str, c))).row(0, named=True)
        rows.append(
            {
                **dict(zip(FACTORS, c, strict=True)),
                "deaths": r["deaths"],
                "share_of_all": r["deaths"] / total,
                "mi_se": r["mi_se"],
            }
        )
    return pl.DataFrame(rows)


def n_flags(f: dict[str, list[pl.Expr]], i: int) -> pl.Expr:
    """Number of the four behaviour flags present on a death, in implicate i."""
    return pl.sum_horizontal(*[_pick(f[n], i).fill_null(False).cast(pl.Int64) for n in FACTORS])


def summary_table(deaths: pl.DataFrame) -> pl.DataFrame:
    """Per factor, the union, the complement and the double-counting of the four factors."""
    f = _factor_exprs()
    k = K_MI
    items: dict[str, list[pl.Expr]] = {"_all": [ALL]}
    for name in FACTORS:
        items[name] = [_pick(f[name], i) for i in range(k)]
        others = [n for n in FACTORS if n != name]
        items[f"{name}__alone"] = [
            _pick(f[name], i) & ~pl.any_horizontal(*[_pick(f[o], i) for o in others])
            for i in range(k)
        ]
    anyf = [pl.any_horizontal(*[_pick(f[n], i) for n in FACTORS]) for i in range(k)]
    items["any"] = anyf
    items["none"] = [~e for e in anyf]
    items["exactly_1"] = [n_flags(f, i) == 1 for i in range(k)]
    items["exactly_2"] = [n_flags(f, i) == 2 for i in range(k)]
    items["three_or_more"] = [n_flags(f, i) >= 3 for i in range(k)]
    wide = agg_sums(deaths, [], items)

    def stat(name: str):
        c = _cols(name, 1 if name == "_all" else k)
        return wide.select(mi_mean(c).alias("m"), mi_se(c).alias("s")).row(0)

    # agg_sums casts to bool-ish counts; the sum of the four flags needs its own total
    total = stat("_all")[0]
    parts_total = deaths.select(
        [
            pl.sum_horizontal(*[_pick(f[n], i).cast(pl.Int64) for n in FACTORS]).sum().alias(str(i))
            for i in range(k)
        ]
    ).row(0)
    sum_mean = sum(parts_total) / k
    sum_se = ((1 + 1 / k) * sum((x - sum_mean) ** 2 for x in parts_total) / (k - 1)) ** 0.5
    any_mean = stat("any")[0]
    rows = []
    for name in [*FACTORS, "any", "none"]:
        m, s = stat(name)
        alone = stat(f"{name}__alone")[0] if name in FACTORS else None
        rows.append(
            {
                "row": name,
                "deaths": m,
                "share_of_all": m / total,
                "deaths_no_other_factor": alone,
                "mi_se": s,
                "overcount_ratio": None,
            }
        )
    rows.append(
        {
            "row": "sum_of_factors",
            "deaths": sum_mean,
            "share_of_all": sum_mean / total,
            "deaths_no_other_factor": None,
            "mi_se": sum_se,
            "overcount_ratio": sum_mean / any_mean,
        }
    )
    for name in ["exactly_1", "exactly_2", "three_or_more"]:
        m, sd = stat(name)
        rows.append(
            {
                "row": name,
                "deaths": m,
                "share_of_all": m / total,
                "deaths_no_other_factor": None,
                "mi_se": sd,
                "overcount_ratio": None,
            }
        )
    return pl.DataFrame(
        rows, schema_overrides={"deaths_no_other_factor": pl.Float64, "overcount_ratio": pl.Float64}
    )


# ---------------------------------------------------------------------------------------
# Victim roles
# ---------------------------------------------------------------------------------------


def role_groups() -> dict[str, tuple[list[pl.Expr], list[pl.Expr]]]:
    """group -> (membership expressions, risk-vehicle expressions), one per implicate if MI."""
    return {
        "alcohol_impaired": (_alc(), [pl.col(f"risk_alc_{m}") for m in IMPLICATES]),
        "speeding": ([pl.col("spd")], [pl.col("risk_spd")]),
        "large_truck": ([pl.col("A_LT") == 1], [pl.col("risk_lt")]),
    }


def victim_roles_table(deaths: pl.DataFrame) -> pl.DataFrame:
    ptype = pl.col("ptype")
    items: dict[str, list[pl.Expr]] = {}
    for g, (member, risk) in role_groups().items():
        k = max(len(member), len(risk))
        items[f"{g}|total"] = [_pick(member, i) for i in range(k)]
        for role in ROLES:
            items[f"{g}|{role}"] = [
                _pick(member, i) & (victim_role(ptype, _pick(risk, i)) == role) for i in range(k)
            ]
        items[f"{g}|not_risk_driver"] = [
            _pick(member, i) & (victim_role(ptype, _pick(risk, i)) != "risk_driver")
            for i in range(k)
        ]
    wide = agg_sums(deaths, [], items)
    rows = []
    for g, (member, risk) in role_groups().items():
        k = max(len(member), len(risk))
        mi = k > 1
        den = _cols(f"{g}|total", k)
        for role in [*ROLES, "not_risk_driver"]:
            num = _cols(f"{g}|{role}", k)
            share = ratio_exprs(num, den)
            r = wide.select(
                mi_mean(num).alias("deaths"),
                mi_mean(share).alias("share_of_group"),
                mi_se(share).alias("mi_se"),
            ).row(0, named=True)
            rows.append({"group": g, "role": role, **r, "estimate_type": estimate_type(mi)})
    return pl.DataFrame(rows).select(
        "group", "role", "deaths", "share_of_group", "mi_se", "estimate_type"
    )


# ---------------------------------------------------------------------------------------
# Driver records
# ---------------------------------------------------------------------------------------


def _known(col: str, unknown: tuple[int, ...]) -> pl.Expr:
    return pl.col(col).is_not_null() & ~pl.col(col).is_in(list(unknown))


def driver_indicators() -> dict[str, tuple[list[pl.Expr], pl.Expr]]:
    """indicator -> (flag expressions [1 or 10], known-status expression)."""
    lic = pl.col("L_STATUS")
    lic_known = lic.is_in([0, 1, 2, 3, 4, 6])
    sus = [pl.col(f"PREV_SUS{i}") for i in (1, 2, 3)]
    sus_ok = [c.is_not_null() & ~c.is_in([99, 998]) for c in sus]
    sus_yes = pl.any_horizontal(*[ok & (c >= 1) for c, ok in zip(sus, sus_ok, strict=True)])
    sus_known = sus_yes | pl.all_horizontal(*sus_ok)
    return {
        "licence_invalid": ([lic.is_in([0, 1, 2, 3, 4])], lic_known),
        "unlicensed": ([lic == 0], lic_known),
        "suspended_or_revoked": ([lic.is_in([1, 2])], lic_known),
        "expired_or_cancelled": ([lic.is_in([3, 4])], lic_known),
        "prior_dwi": ([pl.col("PREV_DWI") >= 1], _known("PREV_DWI", (99, 998))),
        "prior_speeding": ([pl.col("PREV_SPD") >= 1], _known("PREV_SPD", (99, 998))),
        "prior_suspension": ([sus_yes], sus_known & (pl.col("YEAR") >= 2018)),
        "prior_crash": ([pl.col("PREV_ACC") >= 1], _known("PREV_ACC", (98, 99, 998))),
        "bac_15_plus": ([pl.col(f"P{m}") >= 15 for m in IMPLICATES], ALL),
    }


def driver_groups() -> dict[str, list[pl.Expr]]:
    p = [pl.col(f"P{m}") for m in IMPLICATES]
    sp = pl.col("spveh")
    return {
        "all": [ALL],
        "bac_08_plus": [c >= BAC_LIMIT for c in p],
        "bac_01_07": [c.is_between(1, BAC_LIMIT - 1) for c in p],
        "bac_zero": [c == 0 for c in p],
        "speeding": [sp == 1],
        "not_speeding": [sp == 2],
        "neither": [(sp == 2) & (c == 0) for c in p],
    }


def driver_share_items(
    groups: dict[str, list[pl.Expr]],
    indicators: dict[str, tuple[list[pl.Expr], pl.Expr]],
    keep: set[str] | None = None,
) -> dict[str, list[pl.Expr]]:
    items: dict[str, list[pl.Expr]] = {}
    for g, member in groups.items():
        items[f"{g}|n_group"] = member
        for ind, (flag, known) in indicators.items():
            if keep is not None and ind not in keep:
                continue
            k = max(len(member), len(flag))
            items[f"{g}|{ind}|known"] = [_pick(member, i) & known for i in range(k)]
            items[f"{g}|{ind}|yes"] = [_pick(member, i) & known & _pick(flag, i) for i in range(k)]
    return items


def _share_rows(
    wide: pl.DataFrame,
    by: list[str],
    groups: dict[str, list[pl.Expr]],
    indicators: dict[str, tuple[list[pl.Expr], pl.Expr]],
    keep: set[str] | None = None,
) -> pl.DataFrame:
    parts = []
    for g, member in groups.items():
        for ind, (flag, _) in indicators.items():
            if keep is not None and ind not in keep:
                continue
            k = max(len(member), len(flag))
            yes = _cols(f"{g}|{ind}|yes", k)
            known = _cols(f"{g}|{ind}|known", k)
            share = ratio_exprs(yes, known)
            parts.append(
                wide.select(
                    *by,
                    pl.lit(g).alias("group"),
                    pl.lit(ind).alias("indicator"),
                    mi_mean(share).alias("share"),
                    mi_se(share).alias("mi_se"),
                    mi_mean(known).alias("n_known"),
                    mi_mean(_cols(f"{g}|n_group", len(member))).alias("n_group"),
                    pl.lit(estimate_type(k > 1)).alias("estimate_type"),
                )
            )
    return pl.concat(parts)


def driver_records_table(drivers: pl.DataFrame) -> pl.DataFrame:
    groups, ind = driver_groups(), driver_indicators()
    wide = agg_sums(drivers, [], driver_share_items(groups, ind))
    return _share_rows(wide, [], groups, ind)


def driver_records_by_year(drivers: pl.DataFrame) -> pl.DataFrame:
    groups = {k: v for k, v in driver_groups().items() if k in ("all", "bac_08_plus", "speeding")}
    ind = driver_indicators()
    keep = {"licence_invalid", "prior_dwi"}
    wide = agg_sums(drivers, ["YEAR"], driver_share_items(groups, ind, keep))
    return (
        _share_rows(wide, ["YEAR"], groups, ind, keep)
        .select("YEAR", "group", "indicator", "share", "n_known", "mi_se", "estimate_type")
        .sort(["group", "indicator", "YEAR"])
    )


# ---------------------------------------------------------------------------------------
# Restraint and helmet use
# ---------------------------------------------------------------------------------------


def use_table(
    df: pl.DataFrame,
    use_col: str,
    bad_name: str,
    dims: dict[str, tuple[pl.Expr, list[str] | None]],
) -> pl.DataFrame:
    """Killed occupants by dimension: ``use_col`` 1 = protected, 2 = unprotected, else unknown.

    ``unbelted_share`` = unprotected / known; the two bounds treat every unknown as protected
    (lower) or unprotected (upper)."""
    parts = []
    for dim, (expr, levels) in dims.items():
        g = (
            df.with_columns(expr.cast(pl.Utf8).alias("_level"))
            .group_by("_level")
            .agg(
                pl.len().alias("killed"),
                pl.col(use_col).is_in([1, 2]).sum().alias("known"),
                (pl.col(use_col) == 2).sum().alias(bad_name),
            )
        )
        if levels is not None:
            g = (
                pl.DataFrame({"_level": levels})
                .join(g, on="_level", how="left")
                .with_columns(pl.col("killed", "known", bad_name).fill_null(0))
            )
        else:
            g = g.sort("_level")
        parts.append(g.with_columns(pl.lit(dim).alias("dimension")).rename({"_level": "level"}))
    out = pl.concat(parts)
    killed = pl.col("killed")
    return out.select(
        "dimension",
        "level",
        "killed",
        "known",
        bad_name,
        pl.when(pl.col("known") > 0)
        .then(pl.col(bad_name) / pl.col("known"))
        .otherwise(None)
        .alias(f"{bad_name}_share"),
        pl.when(killed > 0)
        .then(1 - pl.col("known") / killed)
        .otherwise(None)
        .alias("unknown_share"),
        pl.when(killed > 0)
        .then(pl.col(bad_name) / killed)
        .otherwise(None)
        .alias("share_if_unknown_protected"),
        pl.when(killed > 0)
        .then((pl.col(bad_name) + killed - pl.col("known")) / killed)
        .otherwise(None)
        .alias("share_if_unknown_unprotected"),
        pl.when(pl.col("known") < 50).then(pl.lit("small")).otherwise(pl.lit("")).alias("flag"),
    )


def _state_expr(col: str = "STATE") -> pl.Expr:
    return pl.col(col).replace_strict(FIPS_TO_USPS, default="unknown", return_dtype=pl.Utf8)


def _years(df: pl.DataFrame) -> list[str]:
    return [str(y) for y in sorted(df["YEAR"].unique().to_list())]


def restraint_table(deaths: pl.DataFrame) -> pl.DataFrame:
    pv = deaths.filter(pl.col("pv")).with_columns(pl.col("A_RESTUSE").alias("use"))
    body = pl.col("body")
    dims = {
        "overall": (pl.lit("all"), ["all"]),
        "year": (pl.col("YEAR"), None),
        "time_of_day": (
            pl.when(pl.col("tod") == 1)
            .then(pl.lit("day"))
            .when(pl.col("tod") == 2)
            .then(pl.lit("night"))
            .otherwise(pl.lit("unknown")),
            ["day", "night", "unknown"],
        ),
        "vehicle": (
            pl.when(body == 1)
            .then(pl.lit("car"))
            .when(body == 2)
            .then(pl.lit("pickup"))
            .when(body == 3)
            .then(pl.lit("suv"))
            .when(body == 4)
            .then(pl.lit("van"))
            .otherwise(pl.lit("other_light_truck")),
            ["car", "pickup", "suv", "van", "other_light_truck"],
        ),
        "area": (
            pl.when(pl.col("ru") == 1)
            .then(pl.lit("rural"))
            .when(pl.col("ru") == 2)
            .then(pl.lit("urban"))
            .otherwise(pl.lit("unknown")),
            ["rural", "urban", "unknown"],
        ),
        "sex": (_sex_expr(), ["male", "female", "unknown"]),
        "age_band": (age_band("age"), AGE_BANDS),
        "role": (
            pl.when(pl.col("ptype") == 1).then(pl.lit("driver")).otherwise(pl.lit("passenger")),
            ["driver", "passenger"],
        ),
        "state": (_state_expr(), None),
    }
    return use_table(pv, "use", "unbelted", dims)


def _sex_expr() -> pl.Expr:
    return (
        pl.when(pl.col("sex") == 1)
        .then(pl.lit("male"))
        .when(pl.col("sex") == 2)
        .then(pl.lit("female"))
        .otherwise(pl.lit("unknown"))
    )


def helmet_table(deaths: pl.DataFrame) -> pl.DataFrame:
    mc = deaths.filter(pl.col("mc")).with_columns(pl.col("A_HELMUSE").alias("use"))
    dims = {
        "overall": (pl.lit("all"), ["all"]),
        "year": (pl.col("YEAR"), None),
        "role": (
            pl.when(pl.col("ptype") == 1).then(pl.lit("rider")).otherwise(pl.lit("passenger")),
            ["rider", "passenger"],
        ),
        "age_band": (age_band("age"), AGE_BANDS),
        "state": (_state_expr(), None),
    }
    return use_table(mc, "use", "unhelmeted", dims)


# ---------------------------------------------------------------------------------------
# Pedestrians
# ---------------------------------------------------------------------------------------


def pedestrian_table(deaths: pl.DataFrame) -> pl.DataFrame:
    ped = deaths.filter(pl.col("ptype") == 3)
    total = ped.height
    obs = {
        "light": (light_group("lgt_cond"), LIGHT_LEVELS),
        "location": (location_group("location"), LOCATION_LEVELS),
        "road_class": (road_class("roadfc"), ROAD_LEVELS),
        "speed_limit": (speed_limit_band("str_vspd"), SPEED_LEVELS),
        "area": (
            pl.when(pl.col("ru") == 1)
            .then(pl.lit("rural"))
            .when(pl.col("ru") == 2)
            .then(pl.lit("urban"))
            .otherwise(pl.lit("unknown")),
            ["urban", "rural", "unknown"],
        ),
        "hit_and_run": (
            pl.when(pl.col("A_HR") == 1).then(pl.lit("yes")).otherwise(pl.lit("no")),
            ["yes", "no"],
        ),
        "age_band": (ped_age_band("age"), PED_AGE_BANDS),
        "striking_vehicle": (striking_vehicle("str_body"), STRIKER_LEVELS),
    }
    parts = []
    for dim, (expr, levels) in obs.items():
        g = ped.with_columns(expr.alias("level")).group_by("level").agg(pl.len().alias("deaths"))
        g = (
            pl.DataFrame({"level": levels})
            .join(g, on="level", how="left")
            .with_columns(pl.col("deaths").fill_null(0).cast(pl.Float64))
        )
        parts.append(
            g.with_columns(
                pl.lit(dim).alias("dimension"),
                (pl.col("deaths") / total).alias("share"),
                pl.lit(0.0).alias("mi_se"),
                pl.lit(OBSERVED).alias("estimate_type"),
            )
        )
    bac = [pl.col(f"pbac_{m}") for m in IMPLICATES]
    items = {
        "bac_08_plus": bac,
        "under_08": [~e for e in bac],
    }
    wide = agg_sums(ped, [], items)
    for lvl in items:
        c = _cols(lvl, K_MI)
        share = ratio_exprs(c, [pl.lit(total)])
        parts.append(
            wide.select(
                pl.lit(lvl).alias("level"),
                mi_mean(c).alias("deaths"),
                pl.lit("pedestrian_bac").alias("dimension"),
                mi_mean(share).alias("share"),
                mi_se(share).alias("mi_se"),
                pl.lit(ESTIMATED).alias("estimate_type"),
            )
        )
    return pl.concat(
        [p.select("dimension", "level", "deaths", "share", "mi_se", "estimate_type") for p in parts]
    )


# ---------------------------------------------------------------------------------------
# Vehicle age
# ---------------------------------------------------------------------------------------

AGE_LEVELS = ["0-3", "4-7", "8-12", "13-17", "18+", "unknown"]


def vehicle_age_table(deaths: pl.DataFrame) -> pl.DataFrame:
    """Killed PV occupants by vehicle-age band, per year and pooled; share of known age."""
    pv = deaths.filter(pl.col("pv")).with_columns(h.vehicle_age("mod_year", "YEAR").alias("_a"))
    pv = pv.with_columns(h.vehicle_age_band("_a").alias("band"))
    pooled = pv.with_columns(pl.lit("2016-2024").alias("year_label"))
    both = pl.concat(
        [
            pv.with_columns(pl.col("YEAR").cast(pl.Utf8).alias("year_label")),
            pooled,
        ]
    )
    g = both.group_by("year_label", "band").agg(pl.len().alias("deaths"))
    labels = sorted(both["year_label"].unique().to_list())
    grid = pl.DataFrame({"YEAR": labels}).join(pl.DataFrame({"band": AGE_LEVELS}), how="cross")
    g = grid.join(
        g, left_on=["YEAR", "band"], right_on=["year_label", "band"], how="left"
    ).with_columns(pl.col("deaths").fill_null(0))
    plus = (
        g.filter(pl.col("band").is_in(["13-17", "18+"]))
        .group_by("YEAR")
        .agg(pl.col("deaths").sum())
        .with_columns(pl.lit("13+").alias("band"))
    )
    g = pl.concat([g, plus.select(g.columns)])
    known = (
        g.filter(~pl.col("band").is_in(["unknown", "13+"]))
        .group_by("YEAR")
        .agg(pl.col("deaths").sum().alias("_known"))
    )
    return (
        g.join(known, on="YEAR")
        .with_columns(
            pl.when(pl.col("band") == "unknown")
            .then(None)
            .otherwise(pl.col("deaths") / pl.col("_known"))
            .alias("share")
        )
        .drop("_known")
        .with_columns(
            pl.col("band")
            .replace_strict({b: i for i, b in enumerate([*AGE_LEVELS[:-1], "13+", "unknown"])})
            .alias("_o")
        )
        .sort(["YEAR", "_o"])
        .drop("_o")
    )


# ---------------------------------------------------------------------------------------
# States
# ---------------------------------------------------------------------------------------


def states_table(deaths: pl.DataFrame, drivers: pl.DataFrame) -> pl.DataFrame:
    yrs = {y: pl.col("YEAR") == y for y in YEARS_COMPARE}
    seg = segment_items()
    items: dict[str, list[pl.Expr]] = {
        "all": seg["all"],
        "alcohol": seg["alcohol_impaired"],
        "speeding": seg["speeding"],
        "unbelted": seg["unbelted"],
        "pv": seg["pv_occupants"],
        "mc": seg["motorcyclists"],
        "ped": seg["pedestrians"],
        "cyc": seg["cyclists"],
        "rural": seg["rural"],
        "rd": seg["roadway_departure"],
        "night": seg["night"],
        "lt": seg["large_truck_crash"],
        "hr": seg["hit_and_run"],
        "unhelmeted": seg["unhelmeted"],
        "pv_known": [pl.col("pv") & pl.col("A_RESTUSE").is_in([1, 2])],
        "mc_known": [pl.col("mc") & pl.col("A_HELMUSE").is_in([1, 2])],
        **{f"y{y}": [e] for y, e in yrs.items()},
    }

    def build(d: pl.DataFrame) -> pl.DataFrame:
        wide = agg_sums(d, ["STATE"], items)

        def m(name: str) -> pl.Expr:
            return mi_mean(_cols(name, len(items[name])))

        def share(num: str, den: str = "all") -> list[pl.Expr]:
            return ratio_exprs(_cols(num, len(items[num])), _cols(den, len(items[den])))

        return wide.select(
            "STATE",
            m("all").alias("deaths"),
            m("y2019").alias("deaths_2019"),
            m("y2021").alias("deaths_2021"),
            m("y2024").alias("deaths_2024"),
            pct_change(m("y2024"), m("y2019")).alias("pct_change_2019_2024"),
            mi_mean(share("alcohol")).alias("alcohol_impaired_share"),
            mi_se(share("alcohol")).alias("alcohol_impaired_share_mi_se"),
            mi_mean(share("speeding")).alias("speeding_share"),
            mi_mean(share("unbelted", "pv_known")).alias("unbelted_share_known"),
            (1 - m("pv_known") / m("pv")).alias("restraint_unknown_share"),
            mi_mean(share("unhelmeted", "mc_known")).alias("unhelmeted_share_known"),
            (1 - m("mc_known") / m("mc")).alias("helmet_unknown_share"),
            mi_mean(share("pv")).alias("pv_occupant_share"),
            mi_mean(share("mc")).alias("motorcyclist_share"),
            mi_mean(share("ped")).alias("pedestrian_share"),
            mi_mean(share("cyc")).alias("cyclist_share"),
            mi_mean(share("rural")).alias("rural_share"),
            mi_mean(share("rd")).alias("roadway_departure_share"),
            mi_mean(share("night")).alias("night_share"),
            mi_mean(share("lt")).alias("large_truck_crash_share"),
            mi_mean(share("hr")).alias("hit_and_run_share"),
            m("mc_known").alias("mc_known"),
            m("pv_known").alias("pv_known"),
        )

    us = build(deaths.with_columns(pl.lit(0, dtype=pl.Int64).alias("STATE")))
    st = build(deaths)
    out = pl.concat([st, us])
    lic_ind = {"licence_invalid": driver_indicators()["licence_invalid"]}
    drv_items = driver_share_items({"all": [ALL]}, lic_ind)
    d_st = agg_sums(drivers, ["STATE"], drv_items)
    d_us = agg_sums(
        drivers.with_columns(pl.lit(0, dtype=pl.Int64).alias("STATE")), ["STATE"], drv_items
    )
    lic = pl.concat([d_st, d_us]).select(
        "STATE",
        (pl.col("all|licence_invalid|yes__0") / pl.col("all|licence_invalid|known__0")).alias(
            "invalid_licence_driver_share"
        ),
    )
    out = out.join(lic, on="STATE", how="left")
    names = {k: v[1] for k, v in STATES.items()} | {0: "United States"}
    codes = {k: v[0] for k, v in STATES.items()} | {0: "US"}
    return (
        out.with_columns(
            pl.col("STATE")
            .replace_strict(codes, default=None, return_dtype=pl.Utf8)
            .alias("state"),
            pl.col("STATE")
            .replace_strict(names, default=None, return_dtype=pl.Utf8)
            .alias("state_name"),
            pl.col("STATE").alias("fips"),
        )
        .filter(pl.col("state").is_not_null())
        .select(
            "state",
            "state_name",
            "fips",
            *[c for c in out.columns if c != "STATE"],
        )
        .sort(pl.col("fips").replace(0, 999))
    )


# ---------------------------------------------------------------------------------------
# Potential lives saved (hypothetical, model-based)
# ---------------------------------------------------------------------------------------

POTENTIAL_TYPE = (
    "hypothetical (model-based: observed deaths x within-vehicle effectiveness estimate)"
)
BELT_ESTIMANDS = {
    "as_recorded": "fatality_risk_reduction_belt_given_fatal_crash",
    "misreport_5pct": "fatality_risk_reduction_belt_given_fatal_crash_misreport_f05",
    "misreport_10pct": "fatality_risk_reduction_belt_given_fatal_crash_misreport_f10",
    "misreport_20pct": "fatality_risk_reduction_belt_given_fatal_crash_misreport_f20",
}


def potential_lives_table(
    effects: list[tuple[str, str, float, float, float]],
    deaths_without: dict[str, float],
    n_years: int,
) -> pl.DataFrame:
    """effects: (measure, scenario, effectiveness, low, high); lives = deaths_without x effectiveness."""
    rows = []
    for measure, scenario, eff, lo, hi in effects:
        d = deaths_without[measure]
        rows.append(
            {
                "measure": measure,
                "scenario": scenario,
                "effectiveness": eff,
                "effectiveness_low": lo,
                "effectiveness_high": hi,
                "deaths_without": d,
                "lives": d * eff,
                "lives_low": d * lo,
                "lives_high": d * hi,
                "lives_per_year": d * eff / n_years,
                "lives_per_year_low": d * lo / n_years,
                "lives_per_year_high": d * hi / n_years,
                "estimate_type": POTENTIAL_TYPE,
            }
        )
    return pl.DataFrame(rows)


def read_effectiveness() -> list[tuple[str, str, float, float, float]] | None:
    """Within-vehicle effectiveness from the committed matched-module tables (None if missing)."""
    mdir = config.TABLES_DIR / "matched"
    try:
        belt = pd.read_csv(mdir / "belt_effect.csv").set_index("estimand")
        dpc = pd.read_csv(mdir / "double_pair_comparison.csv")
    except FileNotFoundError as e:
        log.warning("potential_lives skipped: %s", e)
        return None
    out = []
    for scen, est in BELT_ESTIMANDS.items():
        r = belt.loc[est]
        out.append(("seat_belts", scen, float(r["estimate"]), float(r["low"]), float(r["high"])))
    m = dpc[
        (dpc["analysis"] == "motorcycle_helmet")
        & (dpc["misreport_fraction"] == 0)
        & (dpc["component"] == "combined (inverse-variance weighted)")
    ]
    if m.empty:
        log.warning("potential_lives skipped: no motorcycle_helmet combined row")
        return None
    r = m.iloc[0]
    out.append(
        (
            "helmets",
            "as_recorded",
            float(r["reduction_1_minus_rr"]),
            float(r["reduction_low"]),
            float(r["reduction_high"]),
        )
    )
    return out


# ---------------------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------------------

_INPUTS_DEATH = [
    "FARS person (INJ_SEV)",
    "FARS per_aux",
    "FARS veh_aux",
    "FARS acc_aux",
    "FARS midrvacc",
    "FARS miper",
]


def run() -> dict[str, pl.DataFrame]:
    drivers = build_driver_frame()
    deaths = build_death_frame(drivers)
    log.info("deaths: %d persons killed, %d drivers", deaths.height, drivers.height)
    mi_method = (
        "Census counts; alcohol quantities are means over NHTSA's 10 BAC implicates "
        "with MI SE sqrt(1.1 * between-implicate variance)"
    )
    out = {
        "annual": annual_table(deaths),
        "segments": segments_table(deaths),
        "behaviour_overlap": overlap_table(deaths),
        "behaviour_summary": summary_table(deaths),
        "victim_roles": victim_roles_table(deaths),
        "driver_records": driver_records_table(drivers),
        "driver_records_by_year": driver_records_by_year(drivers),
        "restraint": restraint_table(deaths),
        "helmet": helmet_table(deaths),
        "pedestrians": pedestrian_table(deaths),
        "vehicle_age": vehicle_age_table(deaths),
        "states": states_table(deaths, drivers),
    }
    eff = read_effectiveness()
    if eff is not None:
        wo = {
            "seat_belts": float(deaths["unbelted"].sum()),
            "helmets": float(deaths["unhelmeted"].sum()),
        }
        out["potential_lives"] = potential_lives_table(eff, wo, deaths["YEAR"].n_unique())
    meta = {
        "potential_lives": (
            "Lives the same people would have been expected to survive had they been belted/"
            "helmeted, using the within-vehicle (double pair comparison) effectiveness from the "
            "matched module applied to all seat positions; the belt estimate is sensitive to "
            "survivors' belt use being misrecorded (misreport scenarios)",
            "person killed",
        ),
        "annual": (
            "Deaths per year in each (overlapping) segment of fatal crashes",
            "person killed",
        ),
        "segments": (
            "Pooled 2016-2024 deaths per segment with 2019/2021/2024 comparisons",
            "person killed",
        ),
        "behaviour_overlap": (
            "Exclusive combinations of alcohol-impaired-driving crash, speeding-related crash, "
            "unbelted PV occupant and unhelmeted motorcyclist among all deaths",
            "person killed",
        ),
        "behaviour_summary": (
            "Per behaviour factor, the union, the complement and the double counting of the sum",
            "person killed",
        ),
        "victim_roles": (
            "Who was killed in alcohol-impaired, speeding-related and large-truck crashes",
            "person killed",
        ),
        "driver_records": (
            "Licence status and driving record of drivers in fatal crashes by BAC / speeding group",
            "driver in a fatal crash",
        ),
        "driver_records_by_year": (
            "Invalid licence and prior-DWI share of drivers in fatal crashes by year",
            "driver in a fatal crash",
        ),
        "restraint": (
            "Belt use of killed passenger-vehicle occupants with bounds for unknown use",
            "PV occupant killed",
        ),
        "helmet": (
            "Helmet use of killed motorcyclists with bounds for unknown use",
            "motorcyclist killed",
        ),
        "pedestrians": ("Circumstances of pedestrian deaths", "pedestrian killed"),
        "vehicle_age": ("Vehicle-age bands of killed PV occupants", "PV occupant killed"),
        "states": (
            "Deaths and their composition by state, 2016-2024",
            "person killed (drivers for licence)",
        ),
    }
    for name, df in out.items():
        desc, unit = meta[name]
        save_table(
            df,
            MODULE,
            name,
            description=desc,
            population="FARS fatal crashes 2016-2024 (census)",
            unit=unit,
            outcome="death (INJ_SEV 4)",
            method=mi_method,
            inputs=_INPUTS_DEATH,
        )
    return out
