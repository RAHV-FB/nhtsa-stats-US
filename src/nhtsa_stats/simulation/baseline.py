"""Observed deaths by overlapping target segment, and what the data cannot say about interventions.

Research question
    Where do road deaths concentrate -- speeding, alcohol-impaired driving, police-reported drug
    involvement, unrestrained light-vehicle occupants -- and how much do these segments overlap?
    Does the database contain any enforcement, camera, testing-programme or cost information from
    which an intervention effect could be estimated?

Population / unit
    FARS fatal crashes and the persons killed in them (census, 2016-2024; default window
    2022-2024); CRSS police-reported crashes (probability sample, design-based estimates).
    Unit of the outputs: deaths, fatal crashes and KA crashes per year.

Outputs (``outputs/tables/simulation``)
    ``baseline`` (every quantity with provenance 'observed' | 'estimated' | 'adjusted_association'
    and its source), ``baseline_annual``, ``baseline_partitions`` (deaths and crashes
    cross-classified by segment membership), ``segment_overlap`` (pairwise overlap) and
    ``inventory_enforcement_cost_fields`` (a search of the column inventory: no field measures
    an intervention or a cost).

Justified interpretation
    Counts of deaths in crashes that police coded with a behaviour, and how those counts overlap.

Not justified
    Any statement about what an intervention would or did prevent.  The database contains no
    data on cameras, enforcement, checkpoints, roadside testing, campaigns or costs, so no
    intervention effect is estimated.  Segment counts are lower bounds (unknown status is not
    counted); police-reported speeding, alcohol and drug codes are ascertained more thoroughly
    in fatal crashes; drug involvement is LOW reliability; the adjusted associations carried in
    the baseline are conditional on a reported crash and are not causal effects.
"""

from __future__ import annotations

import itertools
import json
import logging
import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

import numpy as np
import pandas as pd
import polars as pl

from nhtsa_stats import config
from nhtsa_stats.analysis import data
from nhtsa_stats.analysis.survey import SurveyDesign, svy_total
from nhtsa_stats.processing.harmonize import LPV_BODY_GROUPS
from nhtsa_stats.reporting.io import save_table, table_path

log = logging.getLogger(__name__)
MODULE = "simulation"
DEFAULT_WINDOW = (2022, 2024)

# "observed_x_imputation": a FARS census count weighted by NHTSA's multiply-imputed BAC
# probabilities (expected value over implicates), e.g. deaths in alcohol-involved crashes.
Provenance = Literal["observed", "observed_x_imputation", "estimated", "adjusted_association"]
Reliability = Literal["high", "moderate", "low"]


class MissingInputError(FileNotFoundError):
    """A required upstream output table is absent."""


# ======================================================================================
# Segments
# ======================================================================================
ALL = "all"
EXCEEDED = "exceeded_limit_or_racing"
# Light passenger vehicles as in the rest of the project (harmonize.LPV_BODY_GROUPS, which
# includes BODY_TYP 49 'light_unknown_type'), and the seats and ages of the FARS
# within-vehicle belt analysis (matched module), so that the belt estimate is applied to the
# population it was estimated in.
LPV_BODIES: tuple[str, ...] = tuple(LPV_BODY_GROUPS)
BELT_SEATS = ("front_left", "front_other", "second_row")
BELT_MIN_AGE = 13


@dataclass(frozen=True)
class SegmentDef:
    name: str
    level: Literal["crash", "person", "all"]
    fars: str
    crss: str
    reliability: Reliability
    note: str


SEGMENTS: dict[str, SegmentDef] = {
    ALL: SegmentDef(ALL, "all", "every death / fatal crash", "every crash", "high", ""),
    "speeding": SegmentDef(
        "speeding",
        "crash",
        "any in-transport vehicle with SPEEDREL 2-5 (racing, exceeded limit, too fast for "
        "conditions, unspecified)",
        "same definition (CRSS vehicle SPEEDREL)",
        "moderate",
        "Police judgement, ascertained more thoroughly in fatal crashes; mixes exceeding the "
        "limit with 'too fast for conditions'. Crashes with unknown status are NOT counted "
        "(count is a lower bound in that respect).",
    ),
    "speeding_exceeded_limit": SegmentDef(
        "speeding_exceeded_limit",
        "crash",
        "any vehicle coded 'exceeded speed limit' or 'racing' (SPEEDREL 2-3)",
        "same definition",
        "moderate",
        "The part of speeding that automated enforcement acts on. Lower bound: crashes coded "
        "'speeding, specifics unknown' may also have exceeded the limit.",
    ),
    "alcohol": SegmentDef(
        "alcohol",
        "crash",
        "expected value over NHTSA's 10 multiply-imputed BAC implicates of 1[highest driver "
        "BAC >= 0.08 g/dL] (driver_bac08_prob); crashes without a driver contribute 0",
        "NHTSA-imputed police-reported alcohol involvement ALCHL_IM (alcohol_im = 1); not a "
        "BAC threshold",
        "moderate",
        "FARS and CRSS definitions differ (BAC>=.08 vs police-reported involvement). The FARS "
        "count is an expectation over imputations, not a count of tested drivers.",
    ),
    "drugs": SegmentDef(
        "drugs",
        "crash",
        "any driver with police-reported drug involvement (DRUGS = 1)",
        "same definition",
        "low",
        "LOW reliability: drug status is unknown for about half of fatal crashes, testing is "
        "selective by injury severity and state, and presence is not impairment "
        "(docs/audit/alcohol_drugs.md 4.1, 5.5).",
    ),
    "unrestrained_lpv": SegmentDef(
        "unrestrained_lpv",
        "person",
        f"killed drivers/passengers of light passenger vehicles ({', '.join(LPV_BODIES)}), age "
        f">= {BELT_MIN_AGE}, seat {', '.join(BELT_SEATS)}, restraint 'none' (population of the "
        "within-vehicle belt estimate)",
        "same definition among CRSS occupants (estimated persons, not crashes)",
        "moderate",
        "Police-reported restraint; deaths with unknown restraint status are NOT counted. "
        "CRSS belt use among survivors is largely self-reported and likely over-reported. "
        "The primary belt estimate (double-pair comparison) comes from driver/right-front "
        "pairs; applying it to other front and second-row occupants is an extrapolation.",
    ),
}
CRASH_SEGMENTS: tuple[str, ...] = ("speeding", "speeding_exceeded_limit", "alcohol", "drugs")
PERSON_SEGMENTS: tuple[str, ...] = ("unrestrained_lpv",)
PARTITION_SEGMENTS: tuple[str, ...] = CRASH_SEGMENTS + PERSON_SEGMENTS


def _flag(s: pd.Series, value: Any) -> np.ndarray:
    """Boolean array s == value with missing values as False (missing is never 'yes')."""
    return s.eq(value).fillna(False).to_numpy(dtype=bool)


def crash_membership(crash: pd.DataFrame, source: Literal["FARS", "CRSS"]) -> pd.DataFrame:
    """Membership (0..1) of each crash in each crash-level segment.

    All memberships are 0/1 except FARS alcohol, which is the probability over imputations
    (``driver_bac08_prob``).  Unknown status gives membership 0 (it is reported separately as
    ``<segment>__unknown``), never a silent 'no' in any rate: the segment count is a count of
    crashes *coded* yes.
    """
    m = pd.DataFrame(index=crash.index)
    m["speeding"] = _flag(crash["speeding"], 1).astype(float)
    m["speeding_exceeded_limit"] = _flag(crash["speeding_type"], EXCEEDED).astype(float)
    if source == "FARS":
        m["alcohol"] = crash["driver_bac08_prob"].astype(float).fillna(0.0).clip(0.0, 1.0)
    else:
        m["alcohol"] = _flag(crash["alcohol_im"], 1).astype(float)
    m["drugs"] = _flag(crash["drugs"], 1).astype(float)
    m["speeding__unknown"] = crash["speeding"].isna().to_numpy(dtype=float)
    m["speeding_exceeded_limit__unknown"] = (
        crash["speeding_type"].isin(["unknown", "speeding_unspecified"]).to_numpy(dtype=float)
    )
    m["drugs__unknown"] = crash["drugs"].isna().to_numpy(dtype=float)
    return m


def belt_eligible_mask(person: pd.DataFrame, age_col: str = "age") -> np.ndarray:
    """LPV drivers/passengers in the seats and ages of the within-vehicle belt analysis.

    ``age_col``: FARS has no imputed age (``age``, unknown excluded, as in the matched
    module); for CRSS the project convention is NHTSA's imputed age (``age_im``).
    """
    age = pd.to_numeric(person[age_col], errors="coerce")
    return (
        person["ptype"].isin(["driver", "passenger"]).to_numpy()
        & person["body"].isin(LPV_BODIES).to_numpy()
        & person["seat"].isin(BELT_SEATS).to_numpy()
        & (age >= BELT_MIN_AGE).fillna(False).to_numpy(dtype=bool)
    )


def unrestrained_lpv_mask(person: pd.DataFrame, age_col: str = "age") -> np.ndarray:
    return belt_eligible_mask(person, age_col) & _flag(person["restraint"], "none")


# ======================================================================================
# Empirical baseline
# ======================================================================================
@dataclass(frozen=True)
class Quantity:
    """One empirical number with its provenance."""

    name: str
    value: float | None
    kind: Provenance
    source: str
    unit: str
    low: float | None = None
    high: float | None = None
    se: float | None = None
    n: int | None = None
    reliability: Reliability = "high"
    flag: str = ""
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _key(cell: frozenset[str]) -> str:
    return "+".join(sorted(cell)) if cell else "none"


def _unkey(key: str) -> frozenset[str]:
    return frozenset() if key == "none" else frozenset(key.split("+"))


@dataclass(frozen=True)
class Partition:
    """Annual counts cross-classified by segment membership (the overlap structure).

    ``cells`` maps each combination of segments (a frozenset; empty = in none of them) to the
    mean annual count of deaths / crashes in exactly that combination.  With a probabilistic
    membership (FARS alcohol) a cell is the expected count over imputations.  For a CRSS
    (``estimated``) partition ``se`` holds the design-based standard error of each cell.
    """

    measure: str
    segments: tuple[str, ...]
    cells: dict[frozenset[str], float]
    kind: Provenance
    source: str
    n: dict[frozenset[str], int] = field(default_factory=dict)
    se: dict[frozenset[str], float] = field(default_factory=dict)

    def _check(self, seg: str) -> None:
        if seg != ALL and seg not in self.segments:
            raise KeyError(f"segment {seg!r} not in the {self.measure} partition {self.segments}")

    def total(self) -> float:
        return float(sum(self.cells.values()))

    def segment_total(self, seg: str) -> float:
        self._check(seg)
        if seg == ALL:
            return self.total()
        return float(sum(v for c, v in self.cells.items() if seg in c))

    def overlap(self, *segs: str) -> float:
        """Count in *every* listed segment."""
        for s in segs:
            self._check(s)
        req = {s for s in segs if s != ALL}
        return float(sum(v for c, v in self.cells.items() if req <= c))

    def union(self, *segs: str) -> float:
        """Count in *any* listed segment."""
        for s in segs:
            self._check(s)
        if ALL in segs:
            return self.total()
        return float(sum(v for c, v in self.cells.items() if c & set(segs)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "measure": self.measure,
            "segments": list(self.segments),
            "kind": self.kind,
            "source": self.source,
            "cells": {_key(c): v for c, v in self.cells.items()},
            "n": {_key(c): v for c, v in self.n.items()},
            "se": {_key(c): v for c, v in self.se.items()},
        }

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> Partition:
        return cls(
            measure=d["measure"],
            segments=tuple(d["segments"]),
            cells={_unkey(k): float(v) for k, v in d["cells"].items()},
            kind=d["kind"],
            source=d["source"],
            n={_unkey(k): int(v) for k, v in d.get("n", {}).items()},
            se={_unkey(k): float(v) for k, v in d.get("se", {}).items()},
        )

    def cell_flag(self, cell: frozenset[str]) -> str:
        """Reliability flag of a sample-based (``estimated``) cell; '' for census counts."""
        if self.kind != "estimated":
            return ""
        n = self.n.get(cell)
        if n == 0:
            return "no_sample_records"  # e.g. structurally empty (limit-exceeding, not speeding)
        if n is not None and n < config.MIN_CELL_N:
            return "suppressed"
        v, se = self.cells[cell], self.se.get(cell)
        if se is not None and (v <= 0 or se / v > config.MAX_RSE):
            return "unstable"
        return ""

    def to_frame(self) -> pd.DataFrame:
        """Cells for publication: sample-based cells with n < 30 are suppressed (value blank)
        and RSE > 30% flagged unstable.  The full cells stay in ``to_dict`` because the
        totals are only reproduced by summing every cell."""
        flags = [self.cell_flag(c) for c in self.cells]
        vals = [
            math.nan if f == "suppressed" else v
            for f, v in zip(flags, self.cells.values(), strict=True)
        ]
        ses = [self.se.get(c, math.nan) for c in self.cells]
        return pd.DataFrame(
            {
                "measure": self.measure,
                "cell": [_key(c) for c in self.cells],
                "per_year": vals,
                "se": [
                    math.nan if f == "suppressed" else x for f, x in zip(flags, ses, strict=True)
                ],
                "n_records": [self.n.get(c) for c in self.cells],
                "flag": flags,
                "kind": self.kind,
                "source": self.source,
            }
        )


def build_partition(
    membership: pd.DataFrame,
    weight: np.ndarray,
    segments: Sequence[str],
    n_years: int,
    *,
    measure: str,
    kind: Provenance,
    source: str,
    design: SurveyDesign | None = None,
) -> Partition:
    """Cross-classify weighted records by (probabilistic) segment membership.

    Each record contributes ``weight * prod_{s in cell} m_s * prod_{s not in cell} (1 - m_s)`` to
    each cell -- exact expected counts when at most one membership is probabilistic.  With a
    survey ``design`` (``weight`` = design weight x domain/outcome indicator) the design-based
    SE of every cell total is computed as well.
    """
    mm = membership[list(segments)].to_numpy(dtype=float)
    if np.any((mm < 0) | (mm > 1)) or np.any(~np.isfinite(mm)):
        raise ValueError("memberships must be finite and within [0, 1]")
    w = np.asarray(weight, dtype=float)
    cells: dict[frozenset[str], float] = {}
    ns: dict[frozenset[str], int] = {}
    ses: dict[frozenset[str], float] = {}
    for combo in itertools.product((0, 1), repeat=len(segments)):
        pick = np.array(combo, dtype=bool)
        prob = np.prod(np.where(pick, mm, 1.0 - mm), axis=1)
        key = frozenset(s for s, c in zip(segments, combo, strict=True) if c)
        z = w * prob
        cells[key] = float(z.sum() / n_years)
        ns[key] = int(((prob > 0) & (w > 0)).sum())
        if design is not None:
            ses[key] = float(np.sqrt(design.vcov_total(z)[0, 0]) / n_years)
    return Partition(measure, tuple(segments), cells, kind, source, ns, ses)


@dataclass
class EmpiricalBaseline:
    """Empirical quantities with provenance.  See ``build_baseline``."""

    window: tuple[int, int]
    quantities: dict[str, Quantity]
    deaths: Partition
    fatal_crashes: Partition
    ka_crashes: Partition | None = None
    crashes: Partition | None = None
    annual: pd.DataFrame = field(default_factory=pd.DataFrame)
    associations: dict[str, Quantity] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    @property
    def years(self) -> tuple[int, ...]:
        return tuple(range(self.window[0], self.window[1] + 1))

    # -- accessors ----------------------------------------------------------------------
    def total_deaths(self) -> float:
        return self.deaths.total()

    def segment_deaths(self, seg: str) -> float:
        return self.deaths.segment_total(seg)

    def segment_fatal_crashes(self, seg: str) -> float | None:
        if seg in PERSON_SEGMENTS:
            return None
        return self.fatal_crashes.segment_total(seg)

    def segment_ka_crashes(self, seg: str) -> float | None:
        if self.ka_crashes is None or seg in PERSON_SEGMENTS:
            return None
        return self.ka_crashes.segment_total(seg)

    def reliability(self, seg: str) -> Reliability:
        return SEGMENTS[seg].reliability if seg in SEGMENTS else "moderate"

    def association(self, name: str) -> Quantity | None:
        return self.associations.get(name)

    # -- serialisation ------------------------------------------------------------------
    def to_frame(self) -> pd.DataFrame:
        rows = [q.to_dict() for q in self.quantities.values()]
        rows += [q.to_dict() for q in self.associations.values()]
        return pd.DataFrame(rows)

    def partitions_frame(self) -> pd.DataFrame:
        parts = [p for p in (self.deaths, self.fatal_crashes, self.ka_crashes, self.crashes) if p]
        return pd.concat([p.to_frame() for p in parts], ignore_index=True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "window": list(self.window),
            "quantities": {k: q.to_dict() for k, q in self.quantities.items()},
            "associations": {k: q.to_dict() for k, q in self.associations.items()},
            "partitions": {
                p.measure: p.to_dict()
                for p in (self.deaths, self.fatal_crashes, self.ka_crashes, self.crashes)
                if p is not None
            },
            "annual": json.loads(self.annual.to_json(orient="records")),
            "segments": {k: asdict(v) for k, v in SEGMENTS.items()},
            "notes": list(self.notes),
        }

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> EmpiricalBaseline:
        """Rebuild a baseline from ``to_dict`` output (e.g. baseline.json) without the data."""
        parts = {k: Partition.from_dict(v) for k, v in d["partitions"].items()}
        return cls(
            window=(int(d["window"][0]), int(d["window"][1])),
            quantities={k: Quantity(**v) for k, v in d["quantities"].items()},
            deaths=parts["deaths"],
            fatal_crashes=parts["fatal_crashes"],
            ka_crashes=parts.get("ka_crashes"),
            crashes=parts.get("crashes"),
            annual=pd.DataFrame(d.get("annual", [])),
            associations={k: Quantity(**v) for k, v in d.get("associations", {}).items()},
            notes=list(d.get("notes", [])),
        )

    @classmethod
    def load(cls, path: str | None = None) -> EmpiricalBaseline:
        """Load the saved baseline (outputs/tables/simulation/baseline.json)."""
        p = table_path(MODULE, "baseline").with_suffix(".json") if path is None else path
        with open(p) as fh:
            meta = json.load(fh)
        return cls.from_dict(meta.get("baseline", meta))


def _window_years(window: tuple[int, int]) -> tuple[int, ...]:
    lo, hi = int(window[0]), int(window[1])
    if lo > hi:
        raise ValueError(f"window {window} must be (first_year, last_year)")
    years = tuple(range(lo, hi + 1))
    bad = sorted(set(years) - set(config.YEARS))
    if bad:
        raise ValueError(f"years {bad} outside the data ({config.YEARS[0]}-{config.YEARS[-1]})")
    return years


def _fars_quantities(
    years: tuple[int, ...], cm: pd.DataFrame, km: pd.DataFrame, deaths: Partition
) -> dict[str, Quantity]:
    k = len(years)
    span = f"{years[0]}-{years[-1]}"
    src_c = "data/processed/fars_crash.parquet"
    src_p = "data/processed/fars_person.parquet"
    q: dict[str, Quantity] = {}

    def add(name: str, value: float, unit: str, source: str, n: int | None, **kw: Any) -> None:
        kind = "observed_x_imputation" if "alcohol" in name else "observed"
        q[name] = Quantity(name, float(value), kind, source, unit, n=n, **kw)

    add(
        "fars.deaths_per_year",
        len(km) / k,
        f"deaths/year (mean {span})",
        src_p,
        len(km),
        note="FARS census: persons killed (INJ_SEV 4, death within 30 days)",
    )
    add(
        "fars.fatal_crashes_per_year",
        len(cm) / k,
        f"fatal crashes/year (mean {span})",
        src_c,
        len(cm),
    )
    total = len(km) / k
    for seg in PARTITION_SEGMENTS:
        d = SEGMENTS[seg]
        dv = deaths.segment_total(seg)
        expect = seg == "alcohol"
        add(
            f"fars.deaths_per_year.{seg}",
            dv,
            f"deaths/year (mean {span})",
            src_c if seg != "unrestrained_lpv" else src_p,
            int((km[seg] > 0).sum()),
            reliability=d.reliability,
            note=(
                "expected value over 10 BAC implicates (n = deaths with a non-zero probability); "
                if expect
                else ""
            )
            + d.note,
        )
        add(
            f"fars.share_of_deaths.{seg}",
            dv / total,
            "share of all deaths",
            src_c if seg != "unrestrained_lpv" else src_p,
            None,
            reliability=d.reliability,
        )
        if seg in CRASH_SEGMENTS:
            add(
                f"fars.fatal_crashes_per_year.{seg}",
                cm[seg].sum() / k,
                f"fatal crashes/year (mean {span})",
                src_c,
                int((cm[seg] > 0).sum()),
                reliability=d.reliability,
            )
    for seg in ("speeding", "speeding_exceeded_limit", "drugs"):
        add(
            f"fars.deaths_per_year.{seg}.status_unknown",
            km[f"{seg}__unknown"].sum() / k,
            "deaths/year in crashes whose status is unknown"
            + (" or 'speeding, specifics unknown'" if seg == "speeding_exceeded_limit" else ""),
            src_c,
            int(km[f"{seg}__unknown"].sum()),
            note="not included in the segment count; the segment count is a lower bound",
        )
    add(
        "fars.deaths_per_year.unrestrained_lpv.status_unknown",
        km["unrestrained_lpv__unknown"].sum() / k,
        "deaths/year of belt-eligible LPV occupants with unknown restraint use",
        src_p,
        int(km["unrestrained_lpv__unknown"].sum()),
        note="not included in the segment count; the segment count is a lower bound",
    )
    for a, b in itertools.combinations(PARTITION_SEGMENTS, 2):
        if {a, b} == {"speeding", "speeding_exceeded_limit"}:
            continue
        add(
            f"fars.deaths_per_year.overlap.{a}&{b}",
            deaths.overlap(a, b),
            "deaths/year in both segments",
            src_p,
            None,
            reliability="low" if "drugs" in (a, b) else "moderate",
            note="alcohol memberships are probabilities (expected value over implicates)",
        )
    return q


def _crss_quantity(
    name: str,
    design: SurveyDesign,
    y: np.ndarray,
    domain: np.ndarray,
    n_years: int,
    unit: str,
    source: str,
    reliability: Reliability = "high",
    note: str = "",
) -> Quantity:
    est = svy_total(design, y, domain)
    n = int(((np.asarray(y) > 0) & domain).sum())
    value, se = est.estimate / n_years, est.se / n_years
    lo, hi = est.ci()
    rse = se / value if value > 0 else math.inf
    flag = "suppressed" if n < config.MIN_CELL_N else ("unstable" if rse > config.MAX_RSE else "")
    return Quantity(
        name,
        None if flag == "suppressed" else float(value),
        "estimated",
        source,
        unit,
        low=None if flag == "suppressed" else float(lo / n_years),
        high=None if flag == "suppressed" else float(hi / n_years),
        se=float(se),
        n=n,
        reliability=reliability,
        flag=flag,
        note=note,
    )


def crss_outcome_column(columns: Sequence[str], base: str) -> str:
    """Name of the NHTSA-imputed outcome in the processed file.

    ``fatal``/``ka``/``killed``/``killed_or_serious`` are imputed (MAXSEV_IM / INJSEV_IM);
    ``<base>_cc`` are the complete-case versions, used only in sensitivity analyses.
    """
    if base not in set(columns):
        raise MissingInputError(f"outcome column {base!r} not in the processed file")
    return base


def baseline_from_frames(
    fars_crash: pd.DataFrame,
    fars_person: pd.DataFrame,
    window: tuple[int, int] = DEFAULT_WINDOW,
    crss_crash: pd.DataFrame | None = None,
    crss_person: pd.DataFrame | None = None,
) -> EmpiricalBaseline:
    """Baseline quantities from in-memory frames (the testable core of ``build_baseline``).

    ``crss_crash`` / ``crss_person`` must contain *all* years (the survey design is built on
    the full sample and the window is a domain, which gives correct domain variances).
    """
    years = _window_years(window)
    k = len(years)
    fc = fars_crash[fars_crash["YEAR"].isin(years)].reset_index(drop=True)
    missing = sorted(set(years) - set(fc["YEAR"].unique()))
    if missing:
        raise ValueError(f"FARS crash data missing years {missing}")
    cm = crash_membership(fc, "FARS")
    cm["YEAR"] = fc["YEAR"].to_numpy()
    cm["case_id"] = fc["case_id"].to_numpy()

    fp = fars_person[fars_person["YEAR"].isin(years)]
    killed = fp[_flag(fp["killed"], 1)].reset_index(drop=True)
    km = killed[["YEAR", "case_id"]].merge(
        cm, on=["YEAR", "case_id"], how="left", validate="many_to_one"
    )
    if km[list(CRASH_SEGMENTS)].isna().any().any():
        raise ValueError("killed persons without a matching FARS crash record")
    eligible = belt_eligible_mask(killed)
    km["unrestrained_lpv"] = unrestrained_lpv_mask(killed).astype(float)
    km["unrestrained_lpv__unknown"] = (eligible & _flag(killed["restraint"], "unknown")).astype(
        float
    )

    deaths = build_partition(
        km,
        np.ones(len(km)),
        PARTITION_SEGMENTS,
        k,
        measure="deaths",
        kind="observed",
        source="data/processed/fars_person.parquet + fars_crash.parquet",
    )
    fatal = build_partition(
        cm,
        np.ones(len(cm)),
        CRASH_SEGMENTS,
        k,
        measure="fatal_crashes",
        kind="observed",
        source="data/processed/fars_crash.parquet",
    )
    if "FATALS" in fc.columns and int(fc["FATALS"].sum()) != len(km):
        log.warning("FARS killed persons (%d) != sum of FATALS (%d)", len(km), fc["FATALS"].sum())

    # Annual observed series (by year, not averaged).
    ann = km.groupby("YEAR").agg(
        deaths=("case_id", "size"), **{f"deaths_{s}": (s, "sum") for s in PARTITION_SEGMENTS}
    )
    ann = ann.join(
        cm.groupby("YEAR").agg(
            fatal_crashes=("case_id", "size"),
            **{f"fatal_crashes_{s}": (s, "sum") for s in CRASH_SEGMENTS},
        )
    )
    ann = ann.reset_index().assign(kind="observed", source="FARS census")

    quantities = _fars_quantities(years, cm, km, deaths)
    for _, r in ann.iterrows():
        y = int(r["YEAR"])
        quantities[f"fars.deaths.{y}"] = Quantity(
            f"fars.deaths.{y}",
            float(r["deaths"]),
            "observed",
            "data/processed/fars_person.parquet",
            "deaths",
        )
        quantities[f"fars.fatal_crashes.{y}"] = Quantity(
            f"fars.fatal_crashes.{y}",
            float(r["fatal_crashes"]),
            "observed",
            "data/processed/fars_crash.parquet",
            "fatal crashes",
        )

    ka_part = crash_part = None
    notes: list[str] = []
    if crss_crash is not None:
        ka_part, crash_part, cq, crss_annual = _crss_crash_baseline(crss_crash, years)
        quantities.update(cq)
        ann = ann.merge(crss_annual, on="YEAR", how="left")
    else:
        notes.append("CRSS crash data not supplied: KA-crash outcomes unavailable")
    if crss_person is not None:
        quantities.update(_crss_person_baseline(crss_person, years))
    return EmpiricalBaseline(
        window=(years[0], years[-1]),
        quantities=quantities,
        deaths=deaths,
        fatal_crashes=fatal,
        ka_crashes=ka_part,
        crashes=crash_part,
        annual=ann,
        notes=notes,
    )


def _crss_crash_baseline(
    crss: pd.DataFrame, years: tuple[int, ...]
) -> tuple[Partition, Partition, dict[str, Quantity], pd.DataFrame]:
    k = len(years)
    src = "data/processed/crss_crash.parquet"
    ka_col = crss_outcome_column(crss.columns, "ka")
    fatal_col = crss_outcome_column(crss.columns, "fatal")
    design = SurveyDesign.from_frame(crss)
    in_win = crss["YEAR"].isin(years).to_numpy()
    cm = crash_membership(crss, "CRSS")
    ka = _flag(crss[ka_col], 1).astype(float)
    fatal = _flag(crss[fatal_col], 1).astype(float)
    ones = np.ones(len(crss))
    span = f"{years[0]}-{years[-1]}"
    note_ka = f"KA = fatal or suspected serious injury, NHTSA-imputed maximum severity ({ka_col})"
    q: dict[str, Quantity] = {}

    def add(name: str, y: np.ndarray, unit: str, rel: Reliability = "high", note: str = "") -> None:
        q[name] = _crss_quantity(name, design, y, in_win, k, unit, src, rel, note)

    add("crss.crashes_per_year", ones, f"police-reported crashes/year (mean {span})")
    add("crss.ka_crashes_per_year", ka, f"KA crashes/year (mean {span})", note=note_ka)
    add(
        "crss.fatal_crashes_per_year",
        fatal,
        f"fatal crashes/year (mean {span})",
        note=f"CRSS estimate ({fatal_col}); compare with the FARS census count",
    )
    for seg in CRASH_SEGMENTS:
        rel = SEGMENTS[seg].reliability
        m = cm[seg].to_numpy()
        add(f"crss.crashes_per_year.{seg}", m, "crashes/year", rel, SEGMENTS[seg].crss)
        add(f"crss.ka_crashes_per_year.{seg}", m * ka, "KA crashes/year", rel, SEGMENTS[seg].crss)
        if f"{seg}__unknown" in cm:
            add(
                f"crss.crashes_per_year.{seg}.status_unknown",
                cm[f"{seg}__unknown"].to_numpy(),
                "crashes/year with unknown status"
                + (" or 'speeding, specifics unknown'" if seg == "speeding_exceeded_limit" else ""),
                rel,
            )
    w = design.weight * in_win
    ka_part = build_partition(
        cm,
        w * ka,
        CRASH_SEGMENTS,
        k,
        measure="ka_crashes",
        kind="estimated",
        source=src,
        design=design,
    )
    crash_part = build_partition(
        cm, w, CRASH_SEGMENTS, k, measure="crashes", kind="estimated", source=src, design=design
    )
    rows = []
    for y in years:
        dom = (crss["YEAR"] == y).to_numpy()
        tot = svy_total(design, ones, dom)
        kat = svy_total(design, ka, dom)
        rows.append(
            {
                "YEAR": y,
                "crss_crashes": tot.estimate,
                "crss_crashes_se": tot.se,
                "crss_ka_crashes": kat.estimate,
                "crss_ka_crashes_se": kat.se,
            }
        )
    return ka_part, crash_part, q, pd.DataFrame(rows)


def _crss_person_baseline(crss_person: pd.DataFrame, years: tuple[int, ...]) -> dict[str, Quantity]:
    k = len(years)
    src = "data/processed/crss_person.parquet"
    ka_col = crss_outcome_column(crss_person.columns, "killed_or_serious")
    design = SurveyDesign.from_frame(crss_person)
    age_col = "age_im" if "age_im" in crss_person.columns else "age"
    dom = crss_person["YEAR"].isin(years).to_numpy() & unrestrained_lpv_mask(crss_person, age_col)
    ka = _flag(crss_person[ka_col], 1).astype(float)
    note = (
        "LOW reliability: belt use of surviving occupants is largely self-reported and likely "
        "over-reported, so unrestrained occupants are under-counted"
    )
    return {
        "crss.persons_per_year.unrestrained_lpv": _crss_quantity(
            "crss.persons_per_year.unrestrained_lpv",
            design,
            np.ones(len(crss_person)),
            dom,
            k,
            "unrestrained LPV occupants in police-reported crashes/year",
            src,
            "low",
            note,
        ),
        "crss.ka_persons_per_year.unrestrained_lpv": _crss_quantity(
            "crss.ka_persons_per_year.unrestrained_lpv",
            design,
            ka,
            dom,
            k,
            "unrestrained LPV occupants killed or seriously injured/year",
            src,
            "low",
            note,
        ),
    }


# -- associations read from other modules' outputs -------------------------------------
SEVERITY_FILE = ("severity", "fatal_crude_vs_adjusted")
ASSOCIATION_SPECS: dict[str, tuple[str, dict[str, str], tuple[str, str, str]]] = {
    "speeding": (
        "{o}_crude_vs_adjusted",
        {"factor": "speeding", "level": "yes"},
        ("A_adj_rr", "A_adj_rr_low", "A_adj_rr_high"),
    ),
    "alcohol": (
        "{o}_crude_vs_adjusted",
        {"factor": "alcohol_im", "level": "yes"},
        ("A_adj_rr", "A_adj_rr_low", "A_adj_rr_high"),
    ),
    "speeding_exceeded_limit": (
        "{o}_speeding_type",
        {"level": EXCEEDED},
        ("adj_rr", "adj_rr_low", "adj_rr_high"),
    ),
}
BELT_PRIMARY = "fatality_risk_reduction_belt_given_fatal_crash"


def _read_output(module: str, name: str) -> pd.DataFrame | None:
    p = table_path(module, name)
    return pd.read_csv(p) if p.exists() else None


STALE = "stale_upstream"


def _is_stale(module: str, name: str, processed: str) -> bool:
    """True when the upstream output table was written before the processed data file it is
    computed from (i.e. the data were rebuilt and the upstream module not re-run since)."""
    out, src = table_path(module, name), config.PROCESSED_DIR / f"{processed}.parquet"
    return out.exists() and src.exists() and out.stat().st_mtime < src.stat().st_mtime


def _match(df: pd.DataFrame, **match: str) -> pd.Series | None:
    m = np.ones(len(df), dtype=bool)
    for col, v in match.items():
        if col not in df:
            return None
        m &= df[col].astype(str).to_numpy() == str(v)
    return df[m].iloc[0] if m.any() else None


def read_associations(require_severity: bool = True) -> tuple[dict[str, Quantity], list[str]]:
    """Adjusted severity RRs (CRSS model A) and the FARS within-vehicle belt estimate.

    Raises ``MissingInputError`` when the primary severity table is absent and
    ``require_severity`` is true; every other input is optional (a note is returned).
    """
    out: dict[str, Quantity] = {}
    notes: list[str] = []
    primary = table_path(*SEVERITY_FILE)
    if not primary.exists():
        msg = (
            f"{primary} not found: the adjusted severity associations come from the severity "
            "module. Run `nhtsa analyze severity` first, or call build_baseline(..., "
            "require_severity=False) to build a baseline without them."
        )
        if require_severity:
            raise MissingInputError(msg)
        notes.append(msg)
    for outcome in ("fatal", "ka"):
        for seg, (tmpl, match, (c_est, c_lo, c_hi)) in ASSOCIATION_SPECS.items():
            name = tmpl.format(o=outcome)
            df = _read_output("severity", name)
            if df is None:
                notes.append(
                    f"severity/{name}.csv absent: {outcome} association for {seg} unavailable"
                )
                continue
            r = _match(df, **match)
            if r is None or pd.isna(r.get(c_est)):
                notes.append(f"severity/{name}.csv has no row {match}")
                continue
            stale = _is_stale("severity", name, "crss_crash")
            msg = (
                f"STALE: outputs/tables/severity/{name}.csv is older than "
                "data/processed/crss_crash.parquet -- re-run the severity module, then this one"
            )
            if stale and msg not in notes:
                notes.append(msg)
            out[f"severity.{outcome}_adj_rr.{seg}"] = Quantity(
                f"severity.{outcome}_adj_rr.{seg}",
                float(r[c_est]),
                "adjusted_association",
                f"outputs/tables/severity/{name}.csv ({c_est}; {match})",
                f"adjusted risk ratio of a {outcome} outcome given a police-reported crash",
                low=float(r[c_lo]),
                high=float(r[c_hi]),
                n=int(r["n"]) if "n" in r and pd.notna(r["n"]) else None,
                reliability="moderate",
                flag=STALE if stale else "",
                note="CRSS survey logistic model A (pre-crash adjustment set), standardised "
                "margins; conditional on a crash; not a causal effect; police-reported exposure "
                "ascertained more thoroughly in severe crashes",
            )
    notes.append(
        "drugs: no adjusted severity association (exposure measurement depends on severity; "
        "not estimated by the severity module)"
    )
    belt = _read_output("matched", "belt_effect")
    belt_stale = _is_stale("matched", "belt_effect", "fars_person")
    if belt is None:
        notes.append("matched/belt_effect.csv absent: belt effectiveness must be user-supplied")
    else:
        if belt_stale:
            notes.append(
                "STALE: outputs/tables/matched/belt_effect.csv is older than "
                "data/processed/fars_person.parquet -- re-run the matched module, then this one"
            )
        for _, r in belt.iterrows():
            est = str(r["estimand"])
            if not est.startswith("fatality_risk_reduction_belt_given_fatal_crash"):
                continue
            suffix = est.removeprefix(BELT_PRIMARY).lstrip("_")
            name = "belt.fatality_reduction" + (f".{suffix}" if suffix else "")
            out[name] = Quantity(
                name,
                float(r["estimate"]),
                "adjusted_association",
                f"outputs/tables/matched/belt_effect.csv ({est})",
                "proportional reduction in P(death) belted vs unbelted, given a fatal crash",
                low=float(r["low"]),
                high=float(r["high"]),
                n=int(r["n_vehicles"]) if pd.notna(r.get("n_vehicles")) else None,
                reliability="moderate" if not suffix else "low",
                flag=STALE if belt_stale else "",
                note=f"FARS within-vehicle design ({r['method']}); "
                + (
                    "primary estimate; survivor misreporting of belt use would bias it upward"
                    if not suffix
                    else "sensitivity analysis, not an alternative primary estimate"
                ),
            )
    return out, notes


def _read_processed(name: str, columns: Sequence[str]) -> pd.DataFrame:
    """Only the listed columns that exist (the processed layout differs between builds), via
    the shared loader so the path and the missing-file message are the project's."""
    path = config.PROCESSED_DIR / f"{name}.parquet"
    if not path.exists():
        data._read(name)  # raises FileNotFoundError with the project's message
    schema = pl.read_parquet_schema(path)
    keep = [c for c in columns if c in schema]
    return data._read(name, keep).to_pandas()


def build_baseline(
    window: tuple[int, int] = DEFAULT_WINDOW,
    require_severity: bool = True,
    include_crss: bool = True,
) -> EmpiricalBaseline:
    """The baseline from data/processed (FARS census + CRSS design-based estimates) and the
    severity / matched output tables.  Every field is tagged with provenance and source."""
    fars_crash = _read_processed(
        "fars_crash",
        ["YEAR", "case_id", "FATALS", "speeding", "speeding_type", "drugs", "driver_bac08_prob"],
    )
    fars_person = _read_processed(
        "fars_person",
        ["YEAR", "case_id", "killed", "ptype", "body", "seat", "age", "restraint"],
    )
    crss_crash = crss_person = None
    if include_crss:
        design_cols = ["YEAR", "WEIGHT", "PSUSTRAT", "PSU_VAR"]
        crss_crash = _read_processed(
            "crss_crash",
            [
                *design_cols,
                "speeding",
                "speeding_type",
                "alcohol_im",
                "drugs",
                "fatal",
                "fatal_cc",
                "ka",
                "ka_cc",
            ],
        )
        crss_person = _read_processed(
            "crss_person",
            [
                *design_cols,
                "ptype",
                "body",
                "seat",
                "age",
                "age_im",
                "restraint",
                "killed_or_serious",
                "killed_or_serious_cc",
            ],
        )
    base = baseline_from_frames(fars_crash, fars_person, window, crss_crash, crss_person)
    assoc, notes = read_associations(require_severity)
    base.associations.update(assoc)
    base.notes.extend(notes)
    return base


# ======================================================================================
# Overlap between segments (observed)
# ======================================================================================
def overlap_table(baseline: EmpiricalBaseline) -> pd.DataFrame:
    """Pairwise overlap of target segments (deaths/year): in both, in either, and the share of
    each segment's deaths that is also in the other (so segment deaths cannot be added)."""
    rows = []
    for a, b in itertools.combinations(PARTITION_SEGMENTS, 2):
        da, db = baseline.segment_deaths(a), baseline.segment_deaths(b)
        both = baseline.deaths.overlap(a, b)
        rows.append(
            {
                "segment_a": a,
                "segment_b": b,
                "deaths_a": da,
                "deaths_b": db,
                "deaths_both": both,
                "deaths_either": baseline.deaths.union(a, b),
                "share_of_a_also_in_b": both / da if da else math.nan,
                "share_of_b_also_in_a": both / db if db else math.nan,
                "nested": {a, b} == {"speeding", "speeding_exceeded_limit"},
                "kind": "observed",
                "note": "alcohol membership is an expectation over BAC imputations"
                if "alcohol" in (a, b)
                else "",
            }
        )
    return pd.DataFrame(rows)


# ======================================================================================
# Inventory check: does the database contain any enforcement / cost information?
# ======================================================================================
INVENTORY_PATTERN = re.compile(
    r"CAMERA|ENFORC|CITAT|CHECKPOINT|COST|PRICE|DOLLAR|TICKET|FINE|PENAL|VIOL|POLIC|TEST|DRUG|"
    r"ALC_?ST|ALCTES|ALC_RES|ALC_DET|ATST|DSTATUS|SPEC_USE|EMER_USE|PREV_|FIRST_(?:MO|YR)|"
    r"LAST_(?:MO|YR)|SP_JUR|L_STATUS|L_COMPL|L_RESTRI|L_ENDORS|CDL_STAT|A_LIC|BUDGET|PATROL|RADAR|"
    r"LIDAR|SOBRI|BREATH|CAMPAIGN|ZONE|EMERGENCYBRAKING",
    re.IGNORECASE,
)
INVENTORY_MEANING: list[tuple[str, str]] = [
    (
        "ALC_STATUS",
        "alcohol test given to a crash-involved person (post-crash; testing depends on injury severity) -- not roadside screening of the driving population",
    ),
    ("ATST_TYP", "type of alcohol test given to a crash-involved person (post-crash)"),
    ("ALC_RES", "alcohol test result (BAC) of a crash-involved person (post-crash)"),
    ("ALC_DET", "method by which police determined a crash-involved person's alcohol involvement"),
    ("ALCTES", "alcohol test given / result of a crash-involved person (derived; post-crash)"),
    ("DRUGTST", "drug test type for a crash-involved person (post-crash)"),
    ("DRUGRES", "drug test result of a crash-involved person (post-crash toxicology)"),
    ("DRUG_DET", "method by which police determined a crash-involved person's drug involvement"),
    (
        "DRUG",
        "toxicology record of a crash-involved person (specimen, method, quantity, unit; post-crash)",
    ),
    (
        "DRUGS",
        "police-reported drug involvement of a crash-involved person (an exposure, not enforcement)",
    ),
    ("DSTATUS", "drug test status of a crash-involved person (post-crash)"),
    (
        "MVIOLATN",
        "violations charged to a crash-involved driver (consequence of the crash; not enforcement intensity)",
    ),
    (
        "VIOLATION",
        "violations charged to a crash-involved driver (consequence of the crash; not enforcement intensity)",
    ),
    (
        "PREV_",
        "prior convictions/suspensions/crashes of crash-involved drivers (FARS): driver history without an exposure denominator",
    ),
    (
        "FIRST_",
        "date of the first prior crash/suspension/conviction of a crash-involved driver (driver history)",
    ),
    (
        "LAST_",
        "date of the last prior crash/suspension/conviction of a crash-involved driver (driver history)",
    ),
    ("L_STATUS", "licence status of a crash-involved driver"),
    ("L_COMPL", "licence compliance with class of vehicle, crash-involved driver"),
    ("L_RESTRI", "licence restrictions of a crash-involved driver"),
    ("L_ENDORS", "licence endorsements of a crash-involved driver"),
    ("CDL_STAT", "commercial driver licence status of a crash-involved driver"),
    ("A_LIC", "auxiliary licence compliance/status of a crash-involved driver"),
    ("SPEC_USE", "vehicle in special use (e.g. police vehicle, taxi) -- not enforcement activity"),
    ("EMER_USE", "emergency use of a vehicle at the time of the crash"),
    ("SP_JUR", "special jurisdiction of the crash site (e.g. national park, military base)"),
    (
        "BASEPRICE",
        "vehicle base price decoded from the VIN (vPIC) -- a vehicle attribute, not a programme cost",
    ),
    (
        "BACKUPCAMERA",
        "back-up camera fitted to the vehicle (VIN decode) -- not an enforcement camera",
    ),
    ("EMERGENCYBRAKING", "automatic emergency braking fitted to the vehicle (VIN decode)"),
    (
        "ZONE",
        "location attribute of the crash (work zone; school zone for pedestrian/cyclist crashes) "
        "-- not enforcement activity",
    ),
]


def enforcement_field_search(inventory_path: str | None = None) -> pd.DataFrame:
    """Search the column inventory for enforcement- or cost-like fields and interpret each hit."""
    p = config.AUDIT_DIR / "column_inventory.csv" if inventory_path is None else inventory_path
    inv = pd.read_csv(p, usecols=["source", "year", "table", "column"])
    inv = inv[~inv["column"].str.endswith("NAME")]
    hits = inv[inv["column"].str.contains(INVENTORY_PATTERN)]
    out = (
        hits.groupby(["column"])
        .agg(
            sources=("source", lambda s: ",".join(sorted(set(s)))),
            tables=("table", lambda s: ",".join(sorted(set(s)))),
            first_year=("year", "min"),
            last_year=("year", "max"),
        )
        .reset_index()
    )

    def meaning(col: str) -> str:
        exact = dict(INVENTORY_MEANING)
        if col in exact:
            return exact[col]
        for prefix, text in INVENTORY_MEANING:
            if prefix in col:
                return text
        return "unclassified match -- inspect"

    out["meaning"] = out["column"].map(meaning)
    out["measures_intervention_or_cost"] = False
    out.attrs["n_columns_scanned"] = int(inv.groupby(["source", "table", "column"]).ngroups)
    out.attrs["n_tables_scanned"] = int(inv.groupby(["source", "table"]).ngroups)
    return out


# ======================================================================================
# run()
# ======================================================================================


def run(window: tuple[int, int] = DEFAULT_WINDOW) -> dict[str, Any]:
    """Build and save the 2022-2024 observed baseline, segment overlap and field inventory."""
    base = build_baseline(window)
    span = f"{base.window[0]}-{base.window[1]}"
    common = {
        "population": f"FARS fatal crashes and deaths {span} (census); CRSS police-reported crashes {span} (sample)",
        "inputs": [
            "data/processed/fars_crash.parquet",
            "data/processed/fars_person.parquet",
            "data/processed/crss_crash.parquet",
            "data/processed/crss_person.parquet",
            "outputs/tables/severity/*.csv",
            "outputs/tables/matched/belt_effect.csv",
        ],
    }
    # Metadata strings below (module, descriptions) are kept verbatim from the committed tables
    # so that re-running this module reproduces the same files; they still use the old names.
    meta = {"module": "nhtsa_stats.simulation.engine"}
    paths = {}
    paths["baseline"] = save_table(
        base.to_frame(),
        MODULE,
        "baseline",
        description="Layer A empirical baseline for the intervention simulator: every quantity "
        "with provenance (observed / estimated / adjusted_association) and source",
        unit="see 'unit' column",
        method="FARS counts (window mean); CRSS design-based totals (Taylor linearisation, "
        "t with 42 df; suppressed if n<30, flagged unstable if RSE>30%); associations copied "
        "from the severity and matched modules",
        extra={**meta, "baseline": base.to_dict()},
        **common,
    )
    paths["partitions"] = save_table(
        base.partitions_frame(),
        MODULE,
        "baseline_partitions",
        description="Overlap structure: annual deaths / fatal crashes (FARS, observed) and KA / "
        "all crashes (CRSS, estimated) cross-classified by target-segment membership",
        unit="deaths or crashes per year",
        method="Cells = combinations of segments; FARS alcohol membership is the mean over "
        "10 BAC implicates, so cells are expected counts. CRSS cells: design-based SE "
        "(Taylor linearisation, 42 df); value blanked and flagged 'suppressed' if n<30 "
        "sampled records, 'unstable' if RSE>30%, 'no_sample_records' if empty (the engine "
        "uses every cell, see baseline.json)",
        extra=meta,
        **common,
    )
    paths["annual"] = save_table(
        base.annual,
        MODULE,
        "baseline_annual",
        description="Observed FARS deaths and fatal crashes by year and segment; CRSS estimated "
        "crashes and KA crashes by year (with SE)",
        unit="per year",
        extra=meta,
        **common,
    )
    ov = overlap_table(base)
    paths["overlap"] = save_table(
        ov,
        MODULE,
        "segment_overlap",
        description="Observed pairwise overlap of target segments (deaths/year), the basis for "
        "combining interventions without double counting",
        unit="segment pair",
        extra=meta,
        **common,
    )
    inv = enforcement_field_search()
    paths["inventory"] = save_table(
        inv,
        MODULE,
        "inventory_enforcement_cost_fields",
        description="Search of outputs/audit/column_inventory.csv for enforcement-, testing-, "
        "camera- or cost-like fields, with the meaning of every hit",
        unit="column",
        method=f"regex {INVENTORY_PATTERN.pattern!r} over column names (label *NAME columns "
        "excluded)",
        inputs=["outputs/audit/column_inventory.csv"],
        extra={
            **meta,
            "n_columns_scanned": inv.attrs.get("n_columns_scanned"),
            "n_tables_scanned": inv.attrs.get("n_tables_scanned"),
            "conclusion": "No field measures camera deployment, enforcement intensity, "
            "checkpoints, roadside testing of the driving population, campaigns or costs.",
        },
    )
    return {
        "baseline": base,
        "segment_overlap": ov,
        "inventory": inv,
        "paths": {k: str(v) for k, v in paths.items()},
    }
