"""Build the harmonised analytic datasets from the interim tables.

Datasets (``data/processed``):

``crss_crash``   one row per CRSS crash (2016-2024) with survey design fields, KABCO outcomes
                 and crash-level circumstances aggregated from vehicles and persons.
``crss_person``  one row per CRSS person (motor-vehicle occupants in transport and
                 non-motorists) with person, own-vehicle and crash covariates.
``fars_crash``   one row per FARS fatal crash with the same crash covariates (as far as
                 FARS supports them) plus FARS-only fields (road-level rural/urban, function
                 class, multiply-imputed driver BAC).
``fars_person``  one row per FARS person with outcome, restraint, seat and vehicle fields --
                 the input to within-vehicle (matched) analyses.

Tri-state aggregation rule used everywhere: a crash-level "any X" flag is 1 if any unit has
X = 1, 0 if every unit has X known and = 0, and null otherwise (so unknowns are never silently
counted as "no").
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

import polars as pl

from nhtsa_stats import config
from nhtsa_stats.ingestion.cache import load_table
from nhtsa_stats.processing import harmonize as h

log = logging.getLogger(__name__)

CASE = {"FARS": "ST_CASE", "CRSS": "CASENUM"}
DRIVER_TYPES = [1]
OCCUPANT_TYPES = [1, 2, 9]
NONMOTORIST_TYPES = [4, 5, 6, 7, 8, 10, 11, 12, 13, 19]
# HARM_EV first harmful event 1 = rollover/overturn (both sources, embedded labels).
HARM_EV_ROLLOVER = 1
# REL_ROAD location of first harmful event off the travel lanes: shoulder, median, roadside,
# outside trafficway, off roadway unknown, gore, separator.
REL_ROAD_OFF = [2, 3, 4, 5, 6, 8, 10]


def any_flag(col: str) -> pl.Expr:
    """Tri-state 'any' aggregation (see module docstring)."""
    c = pl.col(col)
    return (
        pl.when((c == 1).any())
        .then(pl.lit(1, dtype=pl.Int8))
        .when(c.null_count() == 0)
        .then(pl.lit(0, dtype=pl.Int8))
        .otherwise(pl.lit(None, dtype=pl.Int8))
        .alias(col)
    )


def _keys(source: str) -> tuple[list[str], list[str], list[str]]:
    c = CASE[source]
    return ["YEAR", c], ["YEAR", c, "VEH_NO"], ["YEAR", c, "VEH_NO", "PER_NO"]


# --------------------------------------------------------------------------------------
# Vehicle- and person-derived crash-level aggregates (shared by FARS and CRSS)
# --------------------------------------------------------------------------------------
def vehicle_level(source: str, years: Sequence[int]) -> pl.DataFrame:
    """In-transport vehicles with harmonised vehicle/driver behaviour fields."""
    _, kv, _ = _keys(source)
    cols = [
        *kv[1:],
        "BODY_TYP",
        "MOD_YEAR",
        "SPEEDREL",
        "VSURCOND",
        "VSPD_LIM",
        "HIT_RUN",
        "ROLLOVER",
        "FIRE_EXP",
        "TOWED",
        "TRAV_SP",
    ]
    if source == "CRSS":
        cols += ["VEH_ALCH", "V_ALCH_IM"]
    else:
        cols += ["DR_DRINK", "DEATHS", "L_STATUS", "PREV_DWI", "PREV_SPD", "PREV_SUS1", "PREV_ACC"]
    v = load_table(source, "vehicle", years, cols)
    dist = load_table(source, "distract", years, [*kv[1:], "MDRDSTRD", "DRDISTRACT"])
    dist = (
        dist.with_columns(pl.coalesce("DRDISTRACT", "MDRDSTRD").alias("code"))
        .with_columns(
            pl.when(pl.col("code").is_in([0, 16]))
            .then(pl.lit(0, dtype=pl.Int8))
            .when(pl.col("code").is_in([96, 99]) | pl.col("code").is_null())
            .then(pl.lit(None, dtype=pl.Int8))
            .otherwise(pl.lit(1, dtype=pl.Int8))
            .alias("distracted")
        )
        .group_by(kv)
        # A driver with any substantive distraction code is distracted; with only 'not
        # distracted' codes is not; otherwise unknown.
        .agg(any_flag("distracted"))
    )
    v = v.join(dist, on=kv, how="left")
    out = v.with_columns(
        h.body_group().alias("body"),
        h.vehicle_age().alias("veh_age"),
        h.speeding_related().alias("veh_speeding"),
        h.speeding_type().alias("veh_speeding_type"),
        h.surface_condition().alias("surface"),
        h.speed_limit_mph().alias("speed_limit_mph"),
        h.hit_and_run().alias("hit_and_run"),
        # Post-crash consequences, kept only for mediation/descriptive use.
        pl.when(pl.col("ROLLOVER").is_in([1, 2, 3, 9]))
        .then(pl.lit(1, dtype=pl.Int8))
        .when(pl.col("ROLLOVER").is_in([0, 8]))
        .then(pl.lit(0, dtype=pl.Int8))
        .alias("rollover"),
        h.binary("FIRE_EXP", yes=[1], no=[0]).alias("fire"),
    )
    out = out.with_columns(h.vehicle_age_band().alias("veh_age_band"))
    if source == "CRSS":
        out = out.with_columns(
            h.crss_alcohol("VEH_ALCH").alias("veh_alcohol"),
            h.crss_alcohol("V_ALCH_IM").alias("veh_alcohol_im"),
        )
    else:
        # DR_DRINK: driver drinking (police-reported alcohol involvement) 0 no, 1 yes.
        out = out.with_columns(h.binary("DR_DRINK", yes=[1], no=[0]).alias("veh_alcohol"))
    return out


def person_level(source: str, years: Sequence[int]) -> pl.DataFrame:
    _, _, kp = _keys(source)
    cols = [
        *kp[1:],
        "PER_TYP",
        "AGE",
        "SEX",
        "INJ_SEV",
        "SEAT_POS",
        "REST_USE",
        "REST_MIS",
        "HELM_USE",
        "AIR_BAG",
        "EJECTION",
        "DRINKING",
        "DRUGS",
        "ALC_STATUS",
        "ALC_RES",
    ]
    if source == "CRSS":
        cols += ["AGE_IM", "SEX_IM", "INJSEV_IM", "EJECT_IM", "PERALCH_IM", "SEAT_IM"]
    else:
        cols += ["DOA", "HOSPITAL"]
    p = load_table(source, "person", years, cols)
    p = p.with_columns(
        h.person_type().alias("ptype"),
        h.age_years().alias("age"),
        h.sex().alias("sex"),
        h.fatal("INJ_SEV").alias("killed"),
        h.killed_or_serious("INJ_SEV").alias("killed_or_serious"),
        h.any_injury("INJ_SEV").alias("injured"),
        h.kabco("INJ_SEV").alias("kabco"),
        h.seat_row().alias("seat"),
        h.restraint_use().alias("restraint"),
        h.helmet_use().alias("helmet"),
        h.ejected().alias("ejected"),
        h.police_reported("DRINKING").alias("pr_alcohol"),
        h.police_reported("DRUGS").alias("pr_drugs"),
        pl.when(pl.col("ALC_STATUS") == 2)
        .then(pl.lit(1, dtype=pl.Int8))
        .when(pl.col("ALC_STATUS") == 0)
        .then(pl.lit(0, dtype=pl.Int8))
        .alias("alc_tested"),
        # Measured BAC (g/dL) where a result exists (ALC_RES in thousandths; >= 940 special).
        pl.when(pl.col("ALC_RES") < 940).then(pl.col("ALC_RES") / 1000).alias("bac_measured"),
        # AIR_BAG 1-9 deployed (some location), 20 not deployed.
        pl.when(pl.col("AIR_BAG").is_between(1, 9))
        .then(pl.lit(1, dtype=pl.Int8))
        .when(pl.col("AIR_BAG") == 20)
        .then(pl.lit(0, dtype=pl.Int8))
        .alias("airbag_deployed"),
    )
    p = p.with_columns(h.age_band("age").alias("age_band"))
    if source == "CRSS":
        p = p.with_columns(
            h.fatal("INJSEV_IM").alias("killed_im"),
            h.killed_or_serious("INJSEV_IM").alias("killed_or_serious_im"),
        )
    return p


def crash_aggregates(source: str, veh: pl.DataFrame, per: pl.DataFrame) -> pl.DataFrame:
    kc, kv, _ = _keys(source)
    vagg = (
        veh.sort(kv)
        .group_by(kc)
        .agg(
            any_flag("veh_speeding").alias("speeding"),
            any_flag("hit_and_run"),
            any_flag("distracted"),
            any_flag("rollover").alias("rollover_any"),
            any_flag("fire").alias("fire_any"),
            (pl.col("body") == "motorcycle").any().cast(pl.Int8).alias("any_motorcycle"),
            pl.col("body")
            .is_in(["medium_heavy_truck", "bus"])
            .any()
            .cast(pl.Int8)
            .alias("any_heavy_truck"),
            pl.col("body")
            .is_in(["suv", "pickup", "van", "light_truck_other"])
            .any()
            .cast(pl.Int8)
            .alias("any_light_truck"),
            pl.col("speed_limit_mph").max().alias("speed_limit_mph"),
            # Surface condition: first vehicle with a known value (VEH_NO order).
            pl.col("surface").filter(pl.col("surface") != h.UNKNOWN).first().alias("surface"),
            pl.col("veh_age").max().alias("oldest_vehicle_age"),
            pl.len().alias("n_veh_in_transport"),
            *([any_flag("veh_alcohol").alias("alcohol_driver")] if source == "FARS" else []),
        )
    )
    drivers = per.filter(pl.col("PER_TYP").is_in(DRIVER_TYPES))
    pagg = per.group_by(kc).agg(
        (pl.col("PER_TYP") == 5).any().cast(pl.Int8).alias("any_pedestrian"),
        pl.col("PER_TYP").is_in([6, 7]).any().cast(pl.Int8).alias("any_cyclist"),
        pl.col("PER_TYP").is_in(NONMOTORIST_TYPES).any().cast(pl.Int8).alias("any_nonmotorist"),
        (pl.col("INJ_SEV") == 4).sum().alias("n_killed"),
        pl.col("INJ_SEV").is_in([3, 4]).sum().alias("n_ka"),
        pl.col("PER_TYP").is_in(OCCUPANT_TYPES).sum().alias("n_occupants"),
    )
    dagg = (
        drivers.with_columns(
            pl.when(pl.col("age").is_between(15, 20))
            .then(1)
            .when(pl.col("age").is_not_null())
            .then(0)
            .cast(pl.Int8)
            .alias("young"),
            pl.when(pl.col("age") >= 65)
            .then(1)
            .when(pl.col("age").is_not_null())
            .then(0)
            .cast(pl.Int8)
            .alias("older"),
            (pl.col("sex") == "male").cast(pl.Int8).alias("male"),
        )
        .group_by(kc)
        .agg(
            any_flag("young").alias("young_driver"),
            any_flag("older").alias("older_driver"),
            any_flag("pr_drugs").alias("drugs"),
            any_flag("pr_alcohol").alias("driver_pr_alcohol"),
            pl.len().alias("n_drivers"),
        )
    )
    return vagg.join(pagg, on=kc, how="left").join(dagg, on=kc, how="left")


def crash_common(df: pl.DataFrame) -> pl.DataFrame:
    """Harmonised crash-circumstance columns from accident-table fields."""
    df = df.with_columns(
        h.light_condition().alias("light"),
        h.is_dark().alias("dark"),
        h.weather().alias("weather"),
        h.time_of_day().alias("tod"),
        h.night().alias("night"),
        h.weekend().alias("weekend"),
        h.junction().alias("junction"),
        h.work_zone().alias("work_zone"),
        h.manner_of_collision().alias("collision"),
        pl.when(pl.col("VE_FORMS") >= 3)
        .then(pl.lit("3+"))
        .otherwise(pl.col("VE_FORMS").cast(pl.Utf8))
        .alias("n_vehicles"),
        pl.when(pl.col("speed_limit_mph").is_not_null())
        .then(h.speed_limit_band("speed_limit_mph"))
        .otherwise(pl.lit(h.UNKNOWN))
        .alias("speed_limit"),
        pl.col("surface").fill_null(h.UNKNOWN),
    )
    # Crash type: non-motorist involvement first, then single-vehicle by location of the
    # first harmful event, then multi-vehicle by manner of collision.
    off_road = pl.col("REL_ROAD").is_in(REL_ROAD_OFF)
    df = df.with_columns(
        pl.when(pl.col("any_pedestrian") == 1)
        .then(pl.lit("pedestrian"))
        .when(pl.col("any_cyclist") == 1)
        .then(pl.lit("cyclist"))
        .when((pl.col("VE_FORMS") == 1) & (pl.col("HARM_EV") == HARM_EV_ROLLOVER))
        .then(pl.lit("sv_rollover_first"))
        .when((pl.col("VE_FORMS") == 1) & off_road)
        .then(pl.lit("sv_off_roadway"))
        .when(pl.col("VE_FORMS") == 1)
        .then(pl.lit("sv_on_roadway"))
        .when(pl.col("collision").is_in(["head_on", "angle", "rear_end", "sideswipe"]))
        .then(pl.lit("mv_") + pl.col("collision"))
        .otherwise(pl.lit("mv_other"))
        .alias("crash_type")
    )
    return df


# --------------------------------------------------------------------------------------
# CRSS
# --------------------------------------------------------------------------------------
CRSS_ACC_COLS = [
    "CASENUM",
    "PSU",
    "PSU_VAR",
    "PSUSTRAT",
    "STRATUM",
    "PJ",
    "WEIGHT",
    "REGION",
    "URBANICITY",
    "VE_TOTAL",
    "VE_FORMS",
    "PVH_INVL",
    "PEDS",
    "PERMVIT",
    "PERNOTMVIT",
    "NUM_INJ",
    "MONTH",
    "DAY_WEEK",
    "HOUR",
    "HARM_EV",
    "MAN_COLL",
    "RELJCT2",
    "REL_ROAD",
    "TYP_INT",
    "WRK_ZONE",
    "LGT_COND",
    "WEATHER",
    "INT_HWY",
    "MAX_SEV",
    "MAXSEV_IM",
    "ALCOHOL",
    "ALCHL_IM",
    "LGTCON_IM",
    "WEATHR_IM",
    "HOUR_IM",
    "WKDY_IM",
]
REGION_LABELS = {1: "northeast", 2: "midwest", 3: "south", 4: "west"}


def build_crss(years: Sequence[int] = config.YEARS) -> tuple[pl.DataFrame, pl.DataFrame]:
    acc = load_table("CRSS", "accident", years, CRSS_ACC_COLS)
    veh = vehicle_level("CRSS", years)
    per = person_level("CRSS", years)
    agg = crash_aggregates("CRSS", veh, per)
    kc, kv, kp = _keys("CRSS")
    crash = acc.join(agg, on=kc, how="left")
    crash = crash_common(crash).with_columns(
        h.fatal("MAX_SEV").alias("fatal"),
        h.killed_or_serious("MAX_SEV").alias("ka"),
        h.any_injury("MAX_SEV").alias("injury"),
        h.kabco("MAX_SEV").alias("kabco"),
        h.fatal("MAXSEV_IM").alias("fatal_im"),
        h.killed_or_serious("MAXSEV_IM").alias("ka_im"),
        h.crss_alcohol("ALCOHOL").alias("alcohol"),
        h.crss_alcohol("ALCHL_IM").alias("alcohol_im"),
        pl.col("REGION").replace_strict(REGION_LABELS, default=h.UNKNOWN).alias("region"),
        pl.col("URBANICITY")
        .replace_strict({1: "urban", 2: "rural"}, default=h.UNKNOWN)
        .alias("urbanicity"),
        h.binary("INT_HWY", yes=[1], no=[0]).alias("interstate"),
        pl.col("WEIGHT").cast(pl.Float64),
    )
    crash = crash.rename({"CASENUM": "case_id"})
    # Person file: occupants of in-transport vehicles and non-motorists.
    vcols = [
        *kv,
        "body",
        "veh_age",
        "veh_age_band",
        "veh_speeding",
        "veh_alcohol",
        "veh_alcohol_im",
        "distracted",
        "speed_limit_mph",
        "rollover",
    ]
    ccols = [
        "YEAR",
        "case_id",
        "WEIGHT",
        "PSUSTRAT",
        "PSU_VAR",
        "STRATUM",
        "region",
        "urbanicity",
        "light",
        "dark",
        "weather",
        "surface",
        "speed_limit",
        "tod",
        "night",
        "weekend",
        "junction",
        "interstate",
        "work_zone",
        "n_vehicles",
        "crash_type",
        "collision",
        "speeding",
        "alcohol",
        "alcohol_im",
        "any_heavy_truck",
        "any_motorcycle",
        "fatal",
        "ka",
    ]
    person = (
        per.filter(pl.col("PER_TYP").is_in(OCCUPANT_TYPES + NONMOTORIST_TYPES))
        .join(
            veh.select(vcols).rename(
                {"speed_limit_mph": "veh_speed_limit_mph", "rollover": "veh_rollover"}
            ),
            on=kv,
            how="left",
        )
        .rename({"CASENUM": "case_id"})
        .join(
            crash.select(ccols).rename({"fatal": "crash_fatal", "ka": "crash_ka"}),
            on=["YEAR", "case_id"],
            how="left",
        )
    )
    person = add_partner_vehicle(person, veh.rename({"CASENUM": "case_id"}), ["YEAR", "case_id"])
    person = person.with_columns(role_expr())
    return crash, person


def role_expr() -> pl.Expr:
    return (
        pl.when(pl.col("ptype") == "driver")
        .then(pl.lit("driver"))
        .when((pl.col("ptype") == "passenger") & (pl.col("seat") == "front_other"))
        .then(pl.lit("front_passenger"))
        .when(
            (pl.col("ptype") == "passenger")
            & pl.col("seat").is_in(["second_row", "third_row_plus"])
        )
        .then(pl.lit("rear_passenger"))
        .when(pl.col("ptype") == "passenger")
        .then(pl.lit("other_passenger"))
        .otherwise(pl.col("ptype"))
        .alias("role")
    )


def add_partner_vehicle(person: pl.DataFrame, veh: pl.DataFrame, kc: list[str]) -> pl.DataFrame:
    """For occupants of two-vehicle crashes, the body group of the other vehicle."""
    two = veh.group_by(kc).agg(pl.len().alias("nv")).filter(pl.col("nv") == 2)
    pair = veh.join(two, on=kc, how="semi").select([*kc, "VEH_NO", "body"])
    partner = pair.join(pair, on=kc, suffix="_other").filter(
        pl.col("VEH_NO") != pl.col("VEH_NO_other")
    )
    partner = partner.select([*kc, "VEH_NO", pl.col("body_other").alias("other_vehicle_body")])
    return person.join(partner, on=[*kc, "VEH_NO"], how="left").with_columns(
        pl.col("other_vehicle_body").fill_null("none_or_multi")
    )


# --------------------------------------------------------------------------------------
# FARS
# --------------------------------------------------------------------------------------
FARS_ACC_COLS = [
    "ST_CASE",
    "STATE",
    "VE_TOTAL",
    "VE_FORMS",
    "PVH_INVL",
    "PEDS",
    "PERSONS",
    "PERMVIT",
    "PERNOTMVIT",
    "FATALS",
    "MONTH",
    "DAY_WEEK",
    "HOUR",
    "RUR_URB",
    "FUNC_SYS",
    "HARM_EV",
    "MAN_COLL",
    "RELJCT2",
    "REL_ROAD",
    "TYP_INT",
    "WRK_ZONE",
    "LGT_COND",
    "WEATHER",
]


def mi_bac(table: str, years: Sequence[int], keys: list[str], prefix: str) -> pl.DataFrame:
    """Multiply-imputed BAC (10 implicates, hundredths of g/dL) -> per-implicate >= .08 flags
    and the mean probability across implicates (``{prefix}_p08``)."""
    cols = [f"{prefix[0].upper()}{i}" for i in range(1, 11)]
    df = load_table("FARS", table, years, [*keys[1:], *cols])
    return (
        df.with_columns(
            pl.mean_horizontal([(pl.col(c) >= 8).cast(pl.Float64) for c in cols]).alias(
                f"{prefix}_p08"
            ),
            pl.mean_horizontal([(pl.col(c) >= 1).cast(pl.Float64) for c in cols]).alias(
                f"{prefix}_p01"
            ),
        )
        .select([*keys, f"{prefix}_p08", f"{prefix}_p01", *cols])
        .rename({c: f"{prefix}_{c}" for c in cols})
    )


def build_fars(years: Sequence[int] = config.YEARS) -> tuple[pl.DataFrame, pl.DataFrame]:
    kc, kv, kp = _keys("FARS")
    acc = load_table("FARS", "accident", years, FARS_ACC_COLS)
    veh = vehicle_level("FARS", years)
    per = person_level("FARS", years)
    agg = crash_aggregates("FARS", veh, per)
    drv_bac = mi_bac("midrvacc", years, kc, "a")
    crash = acc.join(agg, on=kc, how="left").join(
        drv_bac.select([*kc, "a_p08", "a_p01"]), on=kc, how="left"
    )
    crash = (
        crash_common(crash)
        .with_columns(
            h.binary("RUR_URB", yes=[1], no=[2]).alias("rural"),
            h.binary("FUNC_SYS", yes=[1], no=[2, 3, 4, 5, 6, 7]).alias("interstate"),
            pl.col("a_p08").alias("driver_bac08_prob"),
        )
        .rename({"ST_CASE": "case_id"})
    )
    per_bac = mi_bac("miper", years, kp, "p")
    vcols = [
        *kv,
        "body",
        "veh_age",
        "veh_age_band",
        "veh_speeding",
        "veh_alcohol",
        "distracted",
        "speed_limit_mph",
        "rollover",
        "DEATHS",
        "L_STATUS",
        "PREV_DWI",
        "PREV_SPD",
        "PREV_SUS1",
    ]
    person = (
        per.join(
            veh.select(vcols).rename(
                {"speed_limit_mph": "veh_speed_limit_mph", "rollover": "veh_rollover"}
            ),
            on=kv,
            how="left",
        )
        .join(per_bac.select([*kp, "p_p08", "p_p01"]), on=kp, how="left")
        .rename({"ST_CASE": "case_id"})
        .join(
            crash.select(
                [
                    "YEAR",
                    "case_id",
                    "STATE",
                    "rural",
                    "interstate",
                    "light",
                    "dark",
                    "weather",
                    "surface",
                    "speed_limit",
                    "tod",
                    "night",
                    "weekend",
                    "n_vehicles",
                    "crash_type",
                    "speeding",
                    "FATALS",
                ]
            ),
            on=["YEAR", "case_id"],
            how="left",
        )
    )
    person = add_partner_vehicle(person, veh.rename({"ST_CASE": "case_id"}), ["YEAR", "case_id"])
    person = person.with_columns(role_expr())
    return crash, person


# --------------------------------------------------------------------------------------
def build_all(years: Sequence[int] = config.YEARS) -> dict[str, pl.DataFrame]:
    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out = {}
    crss_crash, crss_person = build_crss(years)
    fars_crash, fars_person = build_fars(years)
    for name, df in (
        ("crss_crash", crss_crash),
        ("crss_person", crss_person),
        ("fars_crash", fars_crash),
        ("fars_person", fars_person),
    ):
        df.write_parquet(config.PROCESSED_DIR / f"{name}.parquet", compression="zstd")
        log.info("wrote %s: %d rows x %d cols", name, df.height, df.width)
        out[name] = df
    return out
