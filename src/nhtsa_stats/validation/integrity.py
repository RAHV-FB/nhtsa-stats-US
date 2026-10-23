"""Relational-integrity and internal-consistency checks on the interim tables.

Every check yields one row per (check, source, year) with the number of records examined and
the number that fail.  Severity levels:

* ``fail``  -- a structural defect that would corrupt analyses (non-unique primary key,
  orphan child records, join inflation).  Pipeline builds stop on these.
* ``warn``  -- a documented inconsistency between redundant fields (e.g. a crash-level count
  that differs from the count of child records) that analyses must be robust to.
* ``pass``

Results are written to ``outputs/audit/integrity_checks.csv``.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass

import polars as pl

from nhtsa_stats import config
from nhtsa_stats.ingestion.cache import interim_path, load_table

log = logging.getLogger(__name__)

CASE = {"FARS": "ST_CASE", "CRSS": "CASENUM"}

# Child tables and the parent level they must join to.
CRASH_CHILDREN = [
    "cevent",
    "crashrf",
    "weather",
    "acc_aux",
    "miacc",
    "midrvacc",
    "parkwork",
    "vehicle",
    "person",
]
VEHICLE_CHILDREN = [
    "damage",
    "distract",
    "drimpair",
    "factor",
    "maneuver",
    "violatn",
    "vision",
    "driverrf",
    "vehiclesf",
    "veh_aux",
]
# Tables whose records describe in-transport AND parked/working vehicles.  VEH_NO numbering is
# shared between the vehicle and parkwork tables, so these must be filtered to in-transport
# vehicles (semi-join on vehicle) before being attached to vehicle-level analyses.
VEHICLE_OR_PARKED_CHILDREN = ["vevent", "vsoe", "vpicdecode"]
PERSON_CHILDREN = [
    "drugs",
    "race",
    "personrf",
    "per_aux",
    "miper",
    "nmcrash",
    "nmimpair",
    "nmprior",
    "nmdistract",
    "pbtype",
    "safetyeq",
]
# Tables that must match their parent one-to-one in both directions.
ONE_TO_ONE = {"acc_aux": "accident", "veh_aux": "vehicle", "per_aux": "person"}
DESIGN_FIELDS = ["WEIGHT", "PSU", "PSU_VAR", "PSUSTRAT", "STRATUM"]


@dataclass
class CheckResult:
    check: str
    source: str
    year: int
    table: str
    n_checked: int
    n_failed: int
    level: str  # severity if failing: "fail" | "warn"
    note: str = ""

    @property
    def status(self) -> str:
        return "pass" if self.n_failed == 0 else self.level

    def as_dict(self) -> dict:
        return {
            "check": self.check,
            "source": self.source,
            "year": self.year,
            "table": self.table,
            "n_checked": self.n_checked,
            "n_failed": self.n_failed,
            "pct_failed": round(100 * self.n_failed / self.n_checked, 4) if self.n_checked else 0.0,
            "status": self.status,
            "note": self.note,
        }


def _exists(source: str, table: str, year: int) -> bool:
    return interim_path(source, table, year).exists()


def _load(source: str, table: str, year: int, cols: list[str]) -> pl.DataFrame:
    return load_table(source, table, years=[year], columns=cols)


def duplicate_keys(df: pl.DataFrame, keys: list[str]) -> int:
    return int(df.height - df.select(keys).unique().height)


def orphan_count(child: pl.DataFrame, parent: pl.DataFrame, keys: list[str]) -> int:
    return (
        child.select(keys).unique().join(parent.select(keys).unique(), on=keys, how="anti").height
    )


def check_year(source: str, year: int) -> list[CheckResult]:
    c = CASE[source]
    res: list[CheckResult] = []
    k_crash, k_veh, k_per = [c], [c, "VEH_NO"], [c, "VEH_NO", "PER_NO"]

    acc_cols = [c, "VE_TOTAL", "VE_FORMS", "PVH_INVL", "PEDS", "PERMVIT", "PERNOTMVIT"]
    acc_cols += (
        ["FATALS", "PERSONS"] if source == "FARS" else ["MAX_SEV", "NUM_INJ", *DESIGN_FIELDS]
    )
    acc = _load(source, "accident", year, acc_cols)
    veh = _load(
        source,
        "vehicle",
        year,
        [*k_veh, *(["DEATHS"] if source == "FARS" else DESIGN_FIELDS)],
    )
    per = _load(
        source,
        "person",
        year,
        [*k_per, "INJ_SEV", "PER_TYP", *([] if source == "FARS" else DESIGN_FIELDS)],
    )
    park = _load(source, "parkwork", year, k_veh) if _exists(source, "parkwork", year) else None

    # 1. Primary keys.
    for name, df, keys in (
        ("accident", acc, k_crash),
        ("vehicle", veh, k_veh),
        ("person", per, k_per),
    ):
        res.append(
            CheckResult(
                "primary_key_unique",
                source,
                year,
                name,
                df.height,
                duplicate_keys(df, keys),
                "fail",
            )
        )

    # 2. Foreign keys / orphans.
    for t in CRASH_CHILDREN:
        if t in ("vehicle", "person"):
            df = veh if t == "vehicle" else per
        elif _exists(source, t, year):
            df = _load(source, t, year, k_crash)
        else:
            continue
        res.append(
            CheckResult(
                "fk_to_accident", source, year, t, df.height, orphan_count(df, acc, k_crash), "fail"
            )
        )
    for t in VEHICLE_CHILDREN:
        if not _exists(source, t, year):
            continue
        df = _load(source, t, year, k_veh)
        res.append(
            CheckResult(
                "fk_to_vehicle", source, year, t, df.height, orphan_count(df, veh, k_veh), "fail"
            )
        )
    parents_any = (
        veh.select(k_veh) if park is None else pl.concat([veh.select(k_veh), park.select(k_veh)])
    )
    for t in VEHICLE_OR_PARKED_CHILDREN:
        if not _exists(source, t, year):
            continue
        df = _load(source, t, year, k_veh)
        res.append(
            CheckResult(
                "fk_to_vehicle_or_parkwork",
                source,
                year,
                t,
                df.height,
                orphan_count(df, parents_any, k_veh),
                "fail",
            )
        )
    if park is not None:
        res.append(
            CheckResult(
                "parkwork_vehno_disjoint_from_vehicle",
                source,
                year,
                "parkwork",
                park.height,
                park.join(veh.select(k_veh), on=k_veh, how="semi").height,
                "fail",
                "parked and in-transport vehicles must not share a VEH_NO within a case",
            )
        )
    if _exists(source, "pvehiclesf", year) and park is not None:
        df = _load(source, "pvehiclesf", year, k_veh)
        res.append(
            CheckResult(
                "fk_to_parkwork",
                source,
                year,
                "pvehiclesf",
                df.height,
                orphan_count(df, park, k_veh),
                "fail",
            )
        )
    for t in PERSON_CHILDREN:
        if not _exists(source, t, year):
            continue
        df = _load(source, t, year, k_per)
        res.append(
            CheckResult(
                "fk_to_person", source, year, t, df.height, orphan_count(df, per, k_per), "fail"
            )
        )
    # Occupants (VEH_NO>0) must belong to an in-transport vehicle or a parked/working vehicle.
    occ = per.filter(pl.col("VEH_NO") > 0)
    res.append(
        CheckResult(
            "occupant_has_vehicle",
            source,
            year,
            "person",
            occ.height,
            orphan_count(occ, parents_any, k_veh),
            "fail",
        )
    )

    # 3. One-to-one auxiliary tables (both directions).
    parent_frames = {"accident": (acc, k_crash), "vehicle": (veh, k_veh), "person": (per, k_per)}
    for aux, parent in ONE_TO_ONE.items():
        if not _exists(source, aux, year):
            continue
        pdf, keys = parent_frames[parent]
        adf = _load(source, aux, year, keys)
        res.append(
            CheckResult(
                "aux_duplicate_key",
                source,
                year,
                aux,
                adf.height,
                duplicate_keys(adf, keys),
                "fail",
            )
        )
        res.append(
            CheckResult(
                "aux_covers_parent",
                source,
                year,
                aux,
                pdf.height,
                orphan_count(pdf, adf, keys),
                "fail",
                f"{parent} records without an {aux} record",
            )
        )

    # 4. Join inflation: person -> vehicle -> accident must keep the person row count.
    joined = per.join(veh.select(k_veh), on=k_veh, how="left").join(
        acc.select(k_crash), on=k_crash, how="left"
    )
    res.append(
        CheckResult(
            "join_no_inflation",
            source,
            year,
            "person",
            per.height,
            abs(joined.height - per.height),
            "fail",
        )
    )

    # 5. Aggregate reconciliation between crash-level counts and child records.
    nveh = veh.group_by(c).len("n_veh")
    npark = park.group_by(c).len("n_park") if park is not None else None
    a = acc.join(nveh, on=c, how="left")
    if npark is not None:
        a = a.join(npark, on=c, how="left")
    else:
        a = a.with_columns(pl.lit(0).alias("n_park"))
    a = a.with_columns(pl.col("n_veh").fill_null(0), pl.col("n_park").fill_null(0))
    res.append(
        CheckResult(
            "ve_forms_eq_vehicle_rows",
            source,
            year,
            "accident",
            a.height,
            a.filter(pl.col("VE_FORMS") != pl.col("n_veh")).height,
            "warn",
        )
    )
    res.append(
        CheckResult(
            "ve_total_eq_vehicle_plus_parked",
            source,
            year,
            "accident",
            a.height,
            a.filter(pl.col("VE_TOTAL") != pl.col("n_veh") + pl.col("n_park")).height,
            "warn",
        )
    )
    pc = per.group_by(c).agg(
        (pl.col("VEH_NO") == 0).sum().alias("n_nonocc"),
        (pl.col("INJ_SEV") == 4).sum().alias("n_killed"),
    )
    occ_mvit = occ.join(veh.select(k_veh), on=k_veh, how="semi").group_by(c).len("n_occ_mvit")
    a = a.join(pc, on=c, how="left").join(occ_mvit, on=c, how="left").fill_null(0)
    res.append(
        CheckResult(
            "permvit_eq_occupants_in_transport",
            source,
            year,
            "accident",
            a.height,
            a.filter(pl.col("PERMVIT") != pl.col("n_occ_mvit")).height,
            "warn",
        )
    )
    if source == "FARS":
        res.append(
            CheckResult(
                "fatals_eq_persons_inj_sev_4",
                source,
                year,
                "accident",
                a.height,
                a.filter(pl.col("FATALS") != pl.col("n_killed")).height,
                "warn",
                "FATALS vs count of person records with INJ_SEV=4",
            )
        )
        res.append(
            CheckResult(
                "fars_crash_has_fatality",
                source,
                year,
                "accident",
                a.height,
                a.filter(pl.col("FATALS") < 1).height,
                "fail",
            )
        )
        vd = veh.join(
            occ.filter(pl.col("INJ_SEV") == 4).group_by(k_veh).len("n_killed"), on=k_veh, how="left"
        ).with_columns(pl.col("n_killed").fill_null(0))
        res.append(
            CheckResult(
                "vehicle_deaths_eq_occupants_killed",
                source,
                year,
                "vehicle",
                vd.height,
                vd.filter(pl.col("DEATHS") != pl.col("n_killed")).height,
                "warn",
            )
        )
    else:
        # MAX_SEV must equal the most severe KABCO level among persons (codes 0-4 only).
        ms = (
            per.filter(pl.col("INJ_SEV").is_between(0, 4))
            .group_by(c)
            .agg(pl.col("INJ_SEV").max().alias("max_inj"))
        )
        m = acc.filter(pl.col("MAX_SEV").is_between(0, 4)).join(ms, on=c, how="inner")
        res.append(
            CheckResult(
                "max_sev_eq_max_person_injury",
                source,
                year,
                "accident",
                m.height,
                m.filter(pl.col("MAX_SEV") != pl.col("max_inj")).height,
                "warn",
                "crashes with MAX_SEV in 0-4 and at least one person with INJ_SEV in 0-4",
            )
        )
        # Survey design fields constant across levels for the same case.
        for name, df in (("vehicle", veh), ("person", per)):
            d = (
                df.select([c, *DESIGN_FIELDS])
                .unique()
                .join(acc.select([c, *DESIGN_FIELDS]), on=c, how="left", suffix="_acc")
            )
            bad = (
                d.filter(
                    pl.any_horizontal(
                        [pl.col(f).ne_missing(pl.col(f"{f}_acc")) for f in DESIGN_FIELDS]
                    )
                )
                .select(c)
                .unique()
                .height
            )
            res.append(
                CheckResult("design_fields_consistent", source, year, name, d.height, bad, "fail")
            )
        res.append(
            CheckResult(
                "weight_positive",
                source,
                year,
                "accident",
                acc.height,
                acc.filter(~(pl.col("WEIGHT") > 0)).height,
                "fail",
            )
        )
    return res


def run_integrity_checks(
    sources: Iterable[str] = config.SOURCES, years: Iterable[int] = config.YEARS, write: bool = True
) -> pl.DataFrame:
    rows: list[dict] = []
    for s in sources:
        for y in years:
            rows += [r.as_dict() for r in check_year(s, y)]
            log.info("integrity checks done for %s %d", s, y)
    df = pl.DataFrame(rows)
    if write:
        config.AUDIT_DIR.mkdir(parents=True, exist_ok=True)
        df.write_csv(config.AUDIT_DIR / "integrity_checks.csv")
    return df
