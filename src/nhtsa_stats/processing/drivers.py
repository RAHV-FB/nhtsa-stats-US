"""Driver-level analytic datasets and the person-to-driver linkage (Phase 2).

Phase 1 described behaviours only as crash-level "any driver" flags.  Behaviour belongs to a
driver, restraint to an occupant and death to a person, so Phase 2 needs one row per
in-transport vehicle carrying *its own* driver's recorded behaviour, plus an explicit link from
every person to the driver whose behaviour concerns them.

Datasets written to ``data/processed`` (rebuilt by ``nhtsa features``):

``crss_driver``       one row per CRSS in-transport vehicle (2016-2024) with its driver's
                      speeding type, alcohol (imputed ``V_ALCH_IM`` and police ``VEH_ALCH``),
                      police-reported drugs, restraint, age, sex and injury; occupant counts and
                      deaths of the own vehicle; deaths outside it; behaviour of the *other*
                      drivers in the crash; crash covariates and survey design fields.
``fars_driver``       the same for FARS, plus measured BAC and test status, the ten
                      multiply-imputed BAC >= .08 indicators, drug-test status and drug-class
                      positivity from toxicology, and prior speeding / DWI convictions.
``crss_person_link``  one row per CRSS occupant or non-motorist: the vehicle whose driver's
                      behaviour concerns the person (own vehicle for occupants, the striking
                      vehicle ``STR_VEH`` for non-motorists) and the person's relation to it.

Unknown codes stay unknown (tri-state 1 / 0 / null, or an explicit ``unknown`` level); a
vehicle with no driver record keeps its row with null driver fields.

Drug toxicology (FARS) follows the audit recipe in ``docs/audit/alcohol_drugs.md`` §4.3-4.4 and
§8: the 3-digit result scheme applies to 2016-2021 and the 4-digit scheme from 2022 (verified:
no code of the other scheme occurs in either period); the 2018+ ``drugs`` table is
deduplicated; caffeine, nicotine, cotinine, non-psychoactive substances (9000-9994), anabolic
steroids and "other drug" are not counted as psychoactive positives; test status comes from
the results, not the specimen code.  Detection is not impairment.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

import polars as pl

from nhtsa_stats import config
from nhtsa_stats.ingestion.cache import load_table
from nhtsa_stats.processing import features as ft
from nhtsa_stats.processing import harmonize as h

log = logging.getLogger(__name__)

OCCUPANT_TYPES = ft.OCCUPANT_TYPES
NONMOTORIST_TYPES = ft.NONMOTORIST_TYPES

# --------------------------------------------------------------------------------------
# FARS drug-result codes
# --------------------------------------------------------------------------------------
# Class bands of DRUGRES; (low, high) inclusive.  Old (3-digit) scheme: 2016-2021.
OLD_SCHEME_LAST_YEAR = 2021
DRUG_CLASSES: tuple[str, ...] = (
    "narcotic",
    "depressant",
    "stimulant",
    "hallucinogen",
    "cannabinoid",
    "dissociative",
    "inhalant",
)
OLD_BANDS: dict[str, tuple[int, int]] = {
    "narcotic": (100, 295),
    "depressant": (300, 399),
    "stimulant": (400, 495),
    "hallucinogen": (500, 595),
    "cannabinoid": (600, 695),
    "dissociative": (700, 795),
    "steroid": (800, 899),
    "inhalant": (900, 995),
}
NEW_BANDS: dict[str, tuple[int, int]] = {
    "narcotic": (1000, 1997),
    "depressant": (2000, 2997),
    "stimulant": (3000, 3997),
    "hallucinogen": (4000, 4997),
    "cannabinoid": (5000, 5997),
    "dissociative": (6000, 6997),
    "inhalant": (7000, 7997),
    "steroid": (8000, 8997),
    "non_psychoactive": (9000, 9994),
}
# New-scheme stimulant codes that are not impairing drugs.
NEW_NON_IMPAIRING = (3026, 3034, 3066)  # caffeine, cotinine, nicotine
CARBOXY_THC = 5062  # inactive cannabis metabolite (new scheme)
# Special result codes (old / new scheme).
NEGATIVE = (1,)
NOT_GIVEN = (0,)
NOT_REPORTED = (95, 9995)
OTHER_DRUG = (996, 9996)
TESTED_RESULT_UNKNOWN = (997, 9997)
POSITIVE_TYPE_UNKNOWN = (998, 9998)
UNKNOWN_IF_TESTED = (999, 9999)


def drug_class_expr(code: str = "DRUGRES", year: str = "YEAR") -> pl.Expr:
    """Class of one DRUGRES code: a psychoactive class, or one of 'negative', 'not_given',
    'not_reported', 'other', 'non_psychoactive', 'steroid', 'tested_unknown',
    'positive_unknown_type', 'unknown_if_tested'."""
    c, y = pl.col(code), pl.col(year)
    expr = (
        pl.when(c.is_in(NOT_GIVEN))
        .then(pl.lit("not_given"))
        .when(c.is_in(NEGATIVE))
        .then(pl.lit("negative"))
        .when(c.is_in(NOT_REPORTED))
        .then(pl.lit("not_reported"))
        .when(c.is_in(OTHER_DRUG))
        .then(pl.lit("other"))
        .when(c.is_in(TESTED_RESULT_UNKNOWN))
        .then(pl.lit("tested_unknown"))
        .when(c.is_in(POSITIVE_TYPE_UNKNOWN))
        .then(pl.lit("positive_unknown_type"))
        .when(c.is_in(UNKNOWN_IF_TESTED))
        .then(pl.lit("unknown_if_tested"))
        .when((y > OLD_SCHEME_LAST_YEAR) & c.is_in(NEW_NON_IMPAIRING))
        .then(pl.lit("non_psychoactive"))
    )
    for name, (lo, hi) in OLD_BANDS.items():
        expr = expr.when((y <= OLD_SCHEME_LAST_YEAR) & c.is_between(lo, hi)).then(pl.lit(name))
    for name, (lo, hi) in NEW_BANDS.items():
        expr = expr.when((y > OLD_SCHEME_LAST_YEAR) & c.is_between(lo, hi)).then(pl.lit(name))
    return expr.otherwise(pl.lit("unclassified"))


PSYCHOACTIVE = (*DRUG_CLASSES, "positive_unknown_type")
TESTED_CLASSES = (
    *PSYCHOACTIVE,
    "negative",
    "other",
    "non_psychoactive",
    "steroid",
    "tested_unknown",
)


def summarise_drug_results(long: pl.DataFrame, keys: Sequence[str]) -> pl.DataFrame:
    """Per-person drug-test status and class positivity from a long table of results.

    ``long`` has ``keys``, ``YEAR`` (in keys), ``DRUGRES`` and optionally ``DRUGQTY`` (2023+:
    3 = presumptive positive).  Exact duplicate rows must already be removed.

    Status: ``tested`` if any result is a test outcome (negative, a class, other, tested with
    unknown result); else ``unknown_if_tested`` (999/9999), else ``not_reported`` (95/9995),
    else ``not_tested``.  ``drug_any`` (psychoactive positive) is 1 if any psychoactive class or
    'positive, type unknown' is found; 0 if tested with a known result and none found; null
    otherwise (untested, tested with only unknown results, or an unspecified "other drug"
    without any psychoactive class).
    """
    keys = list(keys)
    d = long.with_columns(drug_class_expr().alias("cls"))
    if "DRUGQTY" not in d.columns:
        d = d.with_columns(pl.lit(None, dtype=pl.Int64).alias("DRUGQTY"))
    psy = pl.col("cls").is_in(PSYCHOACTIVE)
    known_result = pl.col("cls").is_in([c for c in TESTED_CLASSES if c != "tested_unknown"])
    aggs = [
        pl.col("cls").is_in(TESTED_CLASSES).any().alias("_tested"),
        (pl.col("cls") == "unknown_if_tested").any().alias("_unk"),
        (pl.col("cls") == "not_reported").any().alias("_nr"),
        known_result.any().alias("_known"),
        (pl.col("cls") == "other").any().alias("_other"),
        psy.any().alias("_pos"),
        # 2023+: positive only through presumptive screens (DRUGQTY 3 on every positive row).
        (psy & (pl.col("DRUGQTY") != 3)).any().alias("_pos_confirmed"),
        # Cannabis positivity only through the inactive metabolite carboxy-THC (new scheme).
        ((pl.col("cls") == "cannabinoid") & (pl.col("DRUGRES") != CARBOXY_THC))
        .any()
        .alias("_cann_active"),
        *[(pl.col("cls") == c).any().alias(f"_c_{c}") for c in DRUG_CLASSES],
        psy.sum().alias("_n_pos_rows"),
    ]
    g = d.group_by(keys).agg(aggs)
    status = (
        pl.when(pl.col("_tested"))
        .then(pl.lit("tested"))
        .when(pl.col("_unk"))
        .then(pl.lit("unknown_if_tested"))
        .when(pl.col("_nr"))
        .then(pl.lit("not_reported"))
        .otherwise(pl.lit("not_tested"))
        .alias("drug_test_status")
    )
    # "Other drug" (996 / 9996) is unspecified and may be psychoactive (it held 9-18% of
    # tested killed drivers before the 2022 recoding), so a person whose only non-negative
    # results are "other" is indeterminate rather than negative.
    determinate = pl.col("_pos") | (pl.col("_tested") & pl.col("_known") & ~pl.col("_other"))

    def flag(cond: pl.Expr) -> pl.Expr:
        return pl.when(determinate).then(cond.cast(pl.Int8)).otherwise(pl.lit(None, dtype=pl.Int8))

    out = g.with_columns(
        status,
        flag(pl.col("_pos")).alias("drug_any"),
        *[flag(pl.col(f"_c_{c}")).alias(f"drug_{c}") for c in DRUG_CLASSES],
        pl.when(pl.col("_pos") & (pl.col("YEAR") >= 2023) & ~pl.col("_pos_confirmed"))
        .then(pl.lit(1, dtype=pl.Int8))
        .when(pl.col("_pos"))
        .then(pl.lit(0, dtype=pl.Int8))
        .alias("drug_presumptive_only"),
        pl.when(pl.col("_c_cannabinoid") & ~pl.col("_cann_active") & (pl.col("YEAR") > 2021))
        .then(pl.lit(1, dtype=pl.Int8))
        .when(pl.col("_c_cannabinoid"))
        .then(pl.lit(0, dtype=pl.Int8))
        .alias("drug_carboxy_thc_only"),
    )
    return out.select(
        [
            *keys,
            "drug_test_status",
            "drug_any",
            *[f"drug_{c}" for c in DRUG_CLASSES],
            "drug_presumptive_only",
            "drug_carboxy_thc_only",
        ]
    )


def fars_drug_results(years: Sequence[int]) -> pl.DataFrame:
    """Per-person drug results for FARS: person columns DRUGRES1-3 (2016-2017) and the
    deduplicated long ``drugs`` table (2018+)."""
    keys = ["YEAR", "ST_CASE", "VEH_NO", "PER_NO"]
    parts = []
    early = [y for y in years if y <= 2017]
    late = [y for y in years if y >= 2018]
    if early:
        p = load_table("FARS", "person", early, [*keys[1:], "DRUGRES1", "DRUGRES2", "DRUGRES3"])
        parts.append(
            p.unpivot(index=keys, on=["DRUGRES1", "DRUGRES2", "DRUGRES3"], value_name="DRUGRES")
            .drop("variable")
            .with_columns(pl.lit(None, dtype=pl.Int64).alias("DRUGQTY"))
            # Unused slots repeat 0 'not given' when another slot has a result; harmless.
            .filter(pl.col("DRUGRES").is_not_null())
        )
    if late:
        d = load_table("FARS", "drugs", late, [*keys[1:], "DRUGSPEC", "DRUGRES", "DRUGQTY"])
        d = d.unique().drop("DRUGSPEC")
        parts.append(d.with_columns(pl.col("DRUGQTY").cast(pl.Int64)))
    long = pl.concat([x.select([*keys, "DRUGRES", "DRUGQTY"]) for x in parts])
    return summarise_drug_results(long, keys)


# --------------------------------------------------------------------------------------
# Alcohol test status (FARS ALC_RES; audit §8 alc_test_status)
# --------------------------------------------------------------------------------------
def alcohol_test_status(col: str = "ALC_RES") -> pl.Expr:
    c = pl.col(col)
    return (
        pl.when(c.is_between(0, 940))
        .then(pl.lit("tested_result"))
        .when(c == 997)
        .then(pl.lit("tested_result_unknown"))
        .when(c == 998)
        .then(pl.lit("tested_positive_no_value"))
        .when(c == 996)
        .then(pl.lit("not_tested"))
        .when(c == 995)
        .then(pl.lit("not_reported"))
        .otherwise(pl.lit("unknown_if_tested"))
    )


# --------------------------------------------------------------------------------------
# Generic driver-level construction (shared by FARS and CRSS)
# --------------------------------------------------------------------------------------
def tri_any(col: str) -> pl.Expr:
    """1 if any row has col = 1, 0 if every row is known 0, null otherwise (empty -> null)."""
    c = pl.col(col)
    return (
        pl.when((c == 1).any())
        .then(pl.lit(1, dtype=pl.Int8))
        .when((c.null_count() == 0) & (pl.len() > 0))
        .then(pl.lit(0, dtype=pl.Int8))
        .otherwise(pl.lit(None, dtype=pl.Int8))
    )


def vehicle_occupants(per: pl.DataFrame, kv: list[str], killed: str = "killed") -> pl.DataFrame:
    """Occupant counts and deaths per vehicle (drivers + passengers + unknown occupants)."""
    occ = per.filter(pl.col("PER_TYP").is_in(OCCUPANT_TYPES))
    return occ.group_by(kv).agg(
        pl.len().alias("n_occupants_veh"),
        (pl.col(killed) == 1).sum().alias("n_killed_veh"),
        (pl.col("PER_TYP") != 1).sum().alias("n_passengers_veh"),
        ((pl.col("PER_TYP") != 1) & (pl.col(killed) == 1)).sum().alias("n_passengers_killed_veh"),
    )


def driver_rows(per: pl.DataFrame, kv: list[str], columns: Sequence[str]) -> pl.DataFrame:
    """The driver record (PER_TYP 1) of each vehicle, ``columns`` prefixed ``drv_``.

    A vehicle has at most one driver record (verified in tests on the real data); if several
    were present the lowest PER_NO is used.
    """
    d = per.filter(pl.col("PER_TYP") == 1).sort([*kv, "PER_NO"]).unique(subset=kv, keep="first")
    return d.select([*kv, *[pl.col(c).alias(f"drv_{c}") for c in columns]])


def other_vehicle_flags(veh: pl.DataFrame, kc: list[str], flags: Sequence[str]) -> pl.DataFrame:
    """For each vehicle, tri-state 'any *other* in-transport vehicle in the crash has flag = 1'
    and the number of other vehicles.  Vehicles alone in the crash get null flags and
    ``n_other_vehicles`` = 0 (no other driver exists, which is not the same as 'no')."""
    kv = [*kc, "VEH_NO"]
    base = veh.select([*kv, *flags])
    pairs = base.join(base, on=kc, suffix="_o").filter(pl.col("VEH_NO") != pl.col("VEH_NO_o"))
    agg = pairs.group_by(kv).agg(
        pl.len().alias("n_other_vehicles"),
        *[tri_any(f"{f}_o").alias(f"other_{f}") for f in flags],
    )
    out = base.select(kv).join(agg, on=kv, how="left")
    return out.with_columns(pl.col("n_other_vehicles").fill_null(0))


def other_level(flag: str) -> pl.Expr:
    """'none' (no other vehicle) / 'no' / 'yes' / 'unknown' label for an other-driver flag."""
    return (
        pl.when(pl.col("n_other_vehicles") == 0)
        .then(pl.lit("no_other_vehicle"))
        .when(pl.col(flag) == 1)
        .then(pl.lit("yes"))
        .when(pl.col(flag) == 0)
        .then(pl.lit("no"))
        .otherwise(pl.lit(h.UNKNOWN))
    )


def _speeding_cat() -> pl.Expr:
    return pl.col("veh_speeding_type").alias("own_speeding_type")


def _tri_label(col: str) -> pl.Expr:
    return (
        pl.when(pl.col(col) == 1)
        .then(pl.lit("yes"))
        .when(pl.col(col) == 0)
        .then(pl.lit("no"))
        .otherwise(pl.lit(h.UNKNOWN))
    )


# --------------------------------------------------------------------------------------
# CRSS
# --------------------------------------------------------------------------------------
CRSS_CRASH_COLS = [
    "YEAR",
    "case_id",
    "WEIGHT",
    "PSUSTRAT",
    "PSU_VAR",
    "region",
    "urbanicity",
    "tod",
    "night",
    "weekend",
    "light",
    "weather",
    "surface",
    "speed_limit",
    "interstate",
    "junction",
    "work_zone",
    "crash_type",
    "n_vehicles",
    "any_motorcycle",
    "any_heavy_truck",
    "young_driver",
    "older_driver",
    "speeding",
    "speeding_type",
    "alcohol",
    "alcohol_im",
    "drugs",
    "hit_and_run",
    "n_killed",
    "n_ka",
    "fatal",
    "ka",
    "fatal_cc",
]
DRIVER_PERSON_COLS = [
    "PER_NO",
    "kabco",
    "age",
    "age_band",
    "sex",
    "killed",
    "killed_or_serious",
    "restraint",
    "helmet",
    "pr_alcohol",
    "pr_drugs",
    "seat",
]


def build_crss_driver(
    years: Sequence[int], crash: pl.DataFrame
) -> tuple[pl.DataFrame, pl.DataFrame]:
    """CRSS driver file and person link table (``crash`` = processed crss_crash)."""
    kc, kv = ["YEAR", "CASENUM"], ["YEAR", "CASENUM", "VEH_NO"]
    veh = ft.vehicle_level("CRSS", years)
    per = ft.person_level("CRSS", years)
    per = per.with_columns(h.age_band("age_im").alias("age_band_im"))
    drv = driver_rows(per, kv, [*DRIVER_PERSON_COLS, "age_im", "age_band_im", "PERALCH_IM"])
    occ = vehicle_occupants(per, kv)
    other = other_vehicle_flags(
        veh.with_columns(
            (pl.col("veh_speeding_type") == "exceeded_limit_or_racing")
            .cast(pl.Int8)
            .alias("exceeded"),
        ),
        kc,
        ["veh_speeding", "veh_alcohol_im", "exceeded"],
    )
    out = (
        veh.select(
            [
                *kv,
                "body",
                "veh_age_band",
                "veh_speeding",
                "veh_speeding_type",
                "veh_alcohol",
                "veh_alcohol_im",
                "hit_and_run",
                "distracted",
                "speed_limit_mph",
            ]
        )
        .join(drv, on=kv, how="left")
        .join(occ, on=kv, how="left")
        .join(other, on=kv, how="left")
        .with_columns(
            pl.col("n_occupants_veh").fill_null(0),
            pl.col("n_killed_veh").fill_null(0),
            pl.col("n_passengers_veh").fill_null(0),
            pl.col("n_passengers_killed_veh").fill_null(0),
            _speeding_cat(),
            (pl.col("drv_PER_NO").is_not_null()).cast(pl.Int8).alias("has_driver_record"),
            _tri_label("veh_alcohol_im").alias("own_alcohol_im"),
            _tri_label("veh_alcohol").alias("own_alcohol_police"),
            _tri_label("drv_pr_drugs").alias("own_drugs_police"),
            other_level("other_veh_speeding").alias("other_speeding"),
            other_level("other_veh_alcohol_im").alias("other_alcohol_im"),
            other_level("other_exceeded").alias("other_exceeded"),
        )
        .rename({"CASENUM": "case_id"})
    )
    out = out.join(crash.select(CRSS_CRASH_COLS), on=["YEAR", "case_id"], how="left")
    out = out.with_columns(
        (pl.col("n_killed") - pl.col("n_killed_veh")).alias("n_killed_outside_veh"),
    )
    link = person_link("CRSS", years, per)
    return out, link


def person_link(source: str, years: Sequence[int], per: pl.DataFrame) -> pl.DataFrame:
    """Each occupant / non-motorist -> the vehicle whose driver's behaviour concerns them.

    Occupants (PER_TYP 1, 2, 9) link to their own vehicle; relation 'driver' or 'passenger'.
    Non-motorists link to their striking vehicle (``STR_VEH`` > 0), relation 'non_motorist';
    ``STR_VEH`` 0 (not struck by an in-transport vehicle / unknown) leaves the link null.
    """
    case = ft.CASE[source]
    keys = ["YEAR", case, "VEH_NO", "PER_NO"]
    strv = load_table(source, "person", years, [*keys[1:], "STR_VEH"])
    p = per.filter(pl.col("PER_TYP").is_in([*OCCUPANT_TYPES, *NONMOTORIST_TYPES])).select(
        [*keys, "PER_TYP"]
    )
    p = p.join(strv, on=keys, how="left")
    occupant = pl.col("PER_TYP").is_in(OCCUPANT_TYPES)
    out = p.with_columns(
        pl.when(occupant)
        .then(pl.col("VEH_NO"))
        .when(pl.col("STR_VEH").is_between(1, 998))
        .then(pl.col("STR_VEH"))
        .otherwise(pl.lit(None))
        .cast(pl.Int64)
        .alias("linked_veh_no"),
        pl.when(pl.col("PER_TYP") == 1)
        .then(pl.lit("driver"))
        .when(occupant)
        .then(pl.lit("passenger"))
        .otherwise(pl.lit("non_motorist"))
        .alias("relation"),
    )
    return out.rename({case: "case_id"}).select(
        ["YEAR", "case_id", "VEH_NO", "PER_NO", "PER_TYP", "relation", "linked_veh_no"]
    )


# --------------------------------------------------------------------------------------
# FARS
# --------------------------------------------------------------------------------------
FARS_CRASH_COLS = [
    "YEAR",
    "case_id",
    "STATE",
    "rural",
    "interstate",
    "tod",
    "night",
    "weekend",
    "light",
    "weather",
    "surface",
    "speed_limit",
    "junction",
    "crash_type",
    "n_vehicles",
    "any_motorcycle",
    "any_heavy_truck",
    "speeding",
    "speeding_type",
    "FATALS",
    "n_killed",
]


def build_fars_driver(years: Sequence[int], crash: pl.DataFrame) -> pl.DataFrame:
    """FARS driver file (``crash`` = processed fars_crash)."""
    kc, kv, kp = (
        ["YEAR", "ST_CASE"],
        ["YEAR", "ST_CASE", "VEH_NO"],
        [
            "YEAR",
            "ST_CASE",
            "VEH_NO",
            "PER_NO",
        ],
    )
    veh = ft.vehicle_level("FARS", years)
    per = ft.person_level("FARS", years)
    extra = load_table("FARS", "person", years, [*kp[1:], "ALC_RES", "DSTATUS"])
    drugs = fars_drug_results(years)
    bac = ft.mi_bac("miper", years, kp, "p")
    implicates = [f"p_P{i}" for i in range(1, 11)]
    bac = bac.select(
        [
            *kp,
            "p_p08",
            *[
                (pl.col(c) >= 8).cast(pl.Int8).alias(f"bac08_mi_{i}")
                for i, c in enumerate(implicates, 1)
            ],
        ]
    )
    per = (
        per.join(
            extra.drop([c for c in extra.columns if c in per.columns and c not in kp]),
            on=kp,
            how="left",
        )
        .join(drugs, on=kp, how="left")
        .join(bac, on=kp, how="left")
        .with_columns(
            alcohol_test_status("ALC_RES").alias("alc_test_status"),
            pl.when(pl.col("ALC_RES").is_between(80, 940))
            .then(pl.lit(1, dtype=pl.Int8))
            .when(pl.col("ALC_RES").is_between(0, 79))
            .then(pl.lit(0, dtype=pl.Int8))
            .alias("bac08_measured"),
        )
    )
    drv_cols = [
        *DRIVER_PERSON_COLS,
        "alc_test_status",
        "bac08_measured",
        "p_p08",
        *[f"bac08_mi_{i}" for i in range(1, 11)],
        "drug_test_status",
        "drug_any",
        *[f"drug_{c}" for c in DRUG_CLASSES],
        "drug_presumptive_only",
        "drug_carboxy_thc_only",
    ]
    drv = driver_rows(per, kv, drv_cols)
    occ = vehicle_occupants(per, kv)
    vflags = veh.with_columns(
        (pl.col("veh_speeding_type") == "exceeded_limit_or_racing").cast(pl.Int8).alias("exceeded")
    )
    # Driver BAC >= .08 (MI expected value) as a 0/1 flag for the other-driver summary uses the
    # implicate mean > 0.5; the expected value itself is kept for counts.
    vflags = vflags.join(
        drv.select([*kv, (pl.col("drv_p_p08") > 0.5).cast(pl.Int8).alias("bac08_mi_major")]),
        on=kv,
        how="left",
    )
    other = other_vehicle_flags(vflags, kc, ["veh_speeding", "exceeded", "bac08_mi_major"])
    out = (
        veh.select(
            [
                *kv,
                "body",
                "veh_age_band",
                "veh_speeding",
                "veh_speeding_type",
                "veh_alcohol",
                "hit_and_run",
                "speed_limit_mph",
                "DEATHS",
                "L_STATUS",
                "PREV_DWI",
                "PREV_SPD",
            ]
        )
        .join(drv, on=kv, how="left")
        .join(occ, on=kv, how="left")
        .join(other, on=kv, how="left")
        .with_columns(
            pl.col("n_occupants_veh").fill_null(0),
            pl.col("n_killed_veh").fill_null(0),
            pl.col("n_passengers_veh").fill_null(0),
            pl.col("n_passengers_killed_veh").fill_null(0),
            _speeding_cat(),
            (pl.col("drv_PER_NO").is_not_null()).cast(pl.Int8).alias("has_driver_record"),
            _tri_label("drv_pr_drugs").alias("own_drugs_police"),
            _tri_label("drv_pr_alcohol").alias("own_alcohol_police"),
            other_level("other_veh_speeding").alias("other_speeding"),
            other_level("other_exceeded").alias("other_exceeded"),
            other_level("other_bac08_mi_major").alias("other_bac08"),
            # PREV_SPD / PREV_DWI: number of prior convictions (0-97); 98 no driver, 99 unknown.
            pl.when(pl.col("PREV_SPD").is_between(0, 97))
            .then(pl.col("PREV_SPD"))
            .alias("prior_speeding_convictions"),
            pl.when(pl.col("PREV_DWI").is_between(0, 97))
            .then(pl.col("PREV_DWI"))
            .alias("prior_dwi_convictions"),
        )
        .rename({"ST_CASE": "case_id"})
    )
    out = out.join(crash.select(FARS_CRASH_COLS), on=["YEAR", "case_id"], how="left")
    return out.with_columns(
        (pl.col("n_killed") - pl.col("n_killed_veh")).alias("n_killed_outside_veh")
    )


def build_all(years: Sequence[int] = config.YEARS) -> dict[str, pl.DataFrame]:
    out = {}
    crss_crash = pl.read_parquet(config.PROCESSED_DIR / "crss_crash.parquet")
    fars_crash = pl.read_parquet(config.PROCESSED_DIR / "fars_crash.parquet")
    crss_driver, link = build_crss_driver(years, crss_crash)
    fars_driver = build_fars_driver(years, fars_crash)
    for name, df in (
        ("crss_driver", crss_driver),
        ("crss_person_link", link),
        ("fars_driver", fars_driver),
    ):
        df.write_parquet(config.PROCESSED_DIR / f"{name}.parquet", compression="zstd")
        log.info("wrote %s: %d rows x %d cols", name, df.height, df.width)
        out[name] = df
    return out
