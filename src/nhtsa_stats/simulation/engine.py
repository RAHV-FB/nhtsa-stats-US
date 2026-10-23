"""Intervention simulation engine (RQ10) -- tooling for transparent "what would it take" analysis.

Research question
    Given the observed burden of deaths in segments that candidate interventions target
    (speeding, alcohol-impaired driving, police-reported drug involvement, unrestrained
    light-vehicle occupants), how many deaths / fatal crashes / KA crashes *would* be prevented
    under explicitly stated assumptions about an intervention's coverage, behavioural response,
    and effects on crash occurrence and severity -- and how large would those effects have to be
    to matter?

Population / unit
    Layer A: FARS fatal crashes and the persons killed in them (census, 2016-2024; default
    window 2022-2024); CRSS police-reported crashes (probability sample, design-based
    estimates).  Unit of the outputs: deaths, fatal crashes and KA crashes per year.

Outcome
    Hypothetical annual deaths, fatal crashes and KA crashes prevented relative to a static
    baseline equal to the window mean; percentage change vs baseline; sensitivity summaries.

Method -- four layers
    A. ``EmpiricalBaseline``: observed FARS counts by year and segment, the overlap between
       segments (cross-classified "partitions" of deaths and crashes), CRSS design-based
       estimates of all and KA crashes per segment (Taylor linearisation, 42 df), the adjusted
       severity associations (CRSS model A risk ratios) and the FARS within-vehicle belt
       estimate.  Every field carries a provenance tag ('observed' | 'estimated' |
       'adjusted_association') and its source table.
    B. Mechanisms: explicit causal chains per intervention type (``SpeedEnforcement``,
       ``ImpairedDrivingEnforcement``, ``RestraintEnforcement``, ``GenericIntervention``) with
       user-defined coverage functions (``LinearCappedCoverage``, ``SaturatingCoverage``).
    C. Assumptions: every effect, coverage, response, deterrence and timing parameter is a
       user-supplied ``Param`` (point, low/central/high, uniform or triangular distribution).
       No default effect size is provided, except that belt effectiveness defaults to the
       FARS within-vehicle estimate (treated as causal by assumption, and labelled so) when
       none is supplied; optional parameters default to *neutral* values (no halo, no cap
       below 100%, converters benefit as much as other unbelted occupants).
    D. Outcomes: point projections, multi-year projections with ramp-up and decay, ranges over
       parameter corners, one-way (tornado) sensitivity, Monte Carlo summaries, and
       combinations of interventions on overlapping segments without double counting
       (multiplicative survival within each cell of the observed segment partition).

Justified interpretation
    "If an intervention reduced X by a, with coverage c ..., the arithmetic implies about N
    deaths per year fewer than the 2022-2024 average, all else equal."  Threshold outputs
    ("the share of speeding-related deaths that would have to be prevented to cut all deaths
    by 1%") are arithmetic on observed counts and need no effect-size assumption.

Not justified
    Any statement that an intervention *will* or *did* prevent N deaths.  The database contains
    no data on cameras, enforcement, checkpoints, roadside testing, campaigns or costs, so no
    intervention effect is estimated here.  Adjusted severity associations are conditional on a
    reported crash and are not causal effects; converting them into severity effects (helper
    ``severity_effect_from_association``) is an explicit user choice labelled as a strong
    assumption.  Police-reported speeding, alcohol and drug codes are ascertained more
    thoroughly in fatal crashes; drug involvement is LOW reliability.
"""

from __future__ import annotations

import itertools
import json
import logging
import math
import re
from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass, field, replace
from typing import Any, ClassVar, Literal

import numpy as np
import pandas as pd
import polars as pl
from scipy import optimize

from nhtsa_stats import config
from nhtsa_stats.analysis import data
from nhtsa_stats.analysis.survey import SurveyDesign, svy_total
from nhtsa_stats.processing.harmonize import LPV_BODY_GROUPS
from nhtsa_stats.reporting.io import save_table, table_path

log = logging.getLogger(__name__)
MODULE = "simulation"
HYPOTHETICAL = "hypothetical"
DEFAULT_WINDOW = (2022, 2024)

# "observed_x_imputation": a FARS census count weighted by NHTSA's multiply-imputed BAC
# probabilities (expected value over implicates), e.g. deaths in alcohol-involved crashes.
Provenance = Literal["observed", "observed_x_imputation", "estimated", "adjusted_association"]
Reliability = Literal["high", "moderate", "low"]
Overlap = Literal["multiplicative", "max", "naive_sum"]
ArrayLike = float | np.ndarray


class MissingInputError(FileNotFoundError):
    """A required upstream output table is absent."""


class MissingAssumptionError(ValueError):
    """A required user assumption was not supplied (the engine has no default effect sizes,
    except the empirical belt-effectiveness estimate)."""


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
# Layer A -- empirical baseline
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

    def prevented(
        self, effects: Sequence[tuple[str, ArrayLike]], overlap: Overlap = "multiplicative"
    ) -> ArrayLike:
        """Count prevented when each (target segment, relative reduction) acts on its segment.

        Within each cell the interventions acting on it combine by ``overlap``:

        * ``multiplicative`` (default): a death survives every intervention independently,
          prevented share 1 - prod(1 - e_i) -- no double counting;
        * ``max``: only the largest effect applies (interventions fully redundant on shared
          deaths) -- a lower bound for shared cells;
        * ``naive_sum``: sum of effects (what adding separate projections implies) -- shown only
          to quantify double counting; it can exceed the deaths available.
        """
        for seg, _ in effects:
            self._check(seg)
        total: ArrayLike = 0.0
        for cell, count in self.cells.items():
            active = [np.asarray(e, dtype=float) for seg, e in effects if seg == ALL or seg in cell]
            if not active or count == 0:
                continue
            if overlap == "multiplicative":
                surv = np.ones_like(active[0])
                for e in active:
                    surv = surv * (1.0 - e)
                frac = 1.0 - surv
            elif overlap == "max":
                frac = np.maximum.reduce(np.broadcast_arrays(*active))
            elif overlap == "naive_sum":
                frac = sum(active)
            else:
                raise ValueError(f"unknown overlap rule {overlap!r}")
            total = total + count * frac
        return total if np.ndim(total) else float(total)

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
        engine's arithmetic needs every cell to reproduce the total."""
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
    """Layer A: empirical quantities with provenance.  See ``build_baseline``."""

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

    @property
    def belt_effectiveness(self) -> Quantity | None:
        return self.associations.get("belt.fatality_reduction")

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
    """Layer A quantities from in-memory frames (the testable core of ``build_baseline``).

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
    """Layer A from data/processed (FARS census + CRSS design-based estimates) and the
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
# Layer C -- assumptions
# ======================================================================================
DISTRIBUTIONS = ("fixed", "uniform", "triangular")


@dataclass(frozen=True)
class Param:
    """A user assumption: point value with optional low/high range and distribution.

    ``Param(0.2)`` is a fixed value; ``Param(0.2, 0.1, 0.4)`` a triangular range (mode 0.2);
    ``Param(0.2, 0.1, 0.4, "uniform")`` a uniform range (central used for point projections
    and as the tornado base).  ``bounds`` is the admissible domain, set by the mechanism.
    """

    central: float
    low: float | None = None
    high: float | None = None
    distribution: str | None = None
    unit: str = ""
    description: str = ""
    source: str = "user assumption"
    bounds: tuple[float, float] = (-math.inf, math.inf)

    def __post_init__(self) -> None:
        if self.central is None:
            raise MissingAssumptionError("a Param needs a central value")
        c = float(self.central)
        lo = c if self.low is None else float(self.low)
        hi = c if self.high is None else float(self.high)
        if not all(math.isfinite(x) for x in (c, lo, hi)):
            raise ValueError("Param values must be finite")
        if not lo <= c <= hi:
            raise ValueError(f"Param needs low <= central <= high, got {lo}, {c}, {hi}")
        dist = self.distribution or ("fixed" if lo == hi else "triangular")
        if dist not in DISTRIBUTIONS:
            raise ValueError(f"distribution must be one of {DISTRIBUTIONS}, got {dist!r}")
        if dist == "fixed" and lo != hi:
            raise ValueError("a 'fixed' Param cannot have a range")
        if lo == hi:
            dist = "fixed"
        b_lo, b_hi = self.bounds
        if lo < b_lo or hi > b_hi:
            raise ValueError(f"Param range [{lo}, {hi}] outside admissible bounds [{b_lo}, {b_hi}]")
        object.__setattr__(self, "central", c)
        object.__setattr__(self, "low", lo)
        object.__setattr__(self, "high", hi)
        object.__setattr__(self, "distribution", dist)

    @classmethod
    def range(
        cls, low: float, central: float, high: float, distribution: str = "triangular", **kw: Any
    ) -> Param:
        return cls(central, low, high, distribution, **kw)

    @property
    def is_fixed(self) -> bool:
        return self.distribution == "fixed"

    def sample(self, rng: np.random.Generator, n: int) -> np.ndarray:
        if self.distribution == "fixed":
            return np.full(n, self.central)
        if self.distribution == "uniform":
            return rng.uniform(self.low, self.high, n)
        return rng.triangular(self.low, self.central, self.high, n)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["bounds"] = list(self.bounds)
        return d


def _param(
    x: Param | float | None,
    name: str,
    bounds: tuple[float, float],
    *,
    owner: str,
    description: str = "",
    unit: str = "",
) -> Param:
    if x is None:
        raise MissingAssumptionError(
            f"{owner}: '{name}' is required ({description}). The engine provides no default "
            "effect sizes -- supply a value or a low/central/high range (Param)."
        )
    p = x if isinstance(x, Param) else Param(float(x))
    return replace(
        p,
        bounds=bounds,
        description=p.description or description,
        unit=p.unit or unit,
    )


def _nonneg(x: float, name: str, owner: str) -> float:
    v = float(x)
    if not math.isfinite(v) or v < 0:
        raise ValueError(f"{owner}: {name} must be a finite non-negative number, got {x!r}")
    return v


SHARE = (0.0, 1.0)
SIGNED_SHARE = (-1.0, 1.0)
POSITIVE = (0.0, math.inf)


@dataclass(frozen=True)
class Timing:
    """Implementation ramp-up and decay (user inputs; no defaults).

    Implementation multiplier in year t = 1, 2, ...: ``min(1, t / ramp_years)`` (1 when
    ``ramp_years`` = 0) times ``(1 - decay_per_year) ** max(0, t - max(1, ramp_years))``.
    ``Timing.immediate()`` is the explicit "full effect from year 1, no decay" choice.
    """

    ramp_years: Param | float
    decay_per_year: Param | float

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "ramp_years",
            _param(
                self.ramp_years,
                "ramp_years",
                (0.0, 50.0),
                owner="Timing",
                unit="years",
                description="years until the full effect is reached (0 = immediate)",
            ),
        )
        object.__setattr__(
            self,
            "decay_per_year",
            _param(
                self.decay_per_year,
                "decay_per_year",
                SHARE,
                owner="Timing",
                unit="share/year",
                description="proportional decline of the effect per year after full implementation",
            ),
        )

    @classmethod
    def immediate(cls) -> Timing:
        return cls(0.0, 0.0)

    def parameters(self) -> dict[str, Param]:
        return {"timing.ramp_years": self.ramp_years, "timing.decay_per_year": self.decay_per_year}  # type: ignore[dict-item]

    @staticmethod
    def multiplier(t: int, ramp: ArrayLike, decay: ArrayLike) -> ArrayLike:
        if t < 1:
            raise ValueError("implementation years start at 1")
        ramp = np.asarray(ramp, dtype=float)
        decay = np.asarray(decay, dtype=float)
        up = np.where(ramp > 0, np.minimum(1.0, t / np.where(ramp > 0, ramp, 1.0)), 1.0)
        down = (1.0 - decay) ** np.maximum(0.0, t - np.maximum(1.0, ramp))
        out = up * down
        return out if out.ndim else float(out)


# ======================================================================================
# Layer B -- mechanisms
# ======================================================================================
class Coverage(ABC):
    """Maps deployed units to the share of target exposure covered (0..1).

    Coverage is *not* proportional to units in general: a capped linear function stops growing
    at its cap, and a saturating function has diminishing returns from the first unit, so
    doubling units does not double coverage (see ``doubling_table``).
    """

    form: ClassVar[str]

    @abstractmethod
    def parameters(self) -> dict[str, Param]: ...

    @abstractmethod
    def evaluate(self, units: ArrayLike, v: Mapping[str, ArrayLike]) -> ArrayLike:
        """Coverage at ``units`` given parameter values ``v`` (keys as in ``parameters``)."""

    def __call__(self, units: ArrayLike, v: Mapping[str, ArrayLike] | None = None) -> ArrayLike:
        vals = {k: p.central for k, p in self.parameters().items()}
        vals.update(v or {})
        return self.evaluate(units, vals)


@dataclass(frozen=True)
class LinearCappedCoverage(Coverage):
    """coverage = min(cap, per_unit * units).  Proportional until the cap binds."""

    per_unit: Param | float
    cap: Param | float = 1.0  # neutral: no cap below 100%
    form: ClassVar[str] = "linear_capped"

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "per_unit",
            _param(
                self.per_unit,
                "per_unit",
                SHARE,
                owner="LinearCappedCoverage",
                unit="share of target exposure per unit",
                description="share of target exposure covered by each unit",
            ),
        )
        object.__setattr__(
            self,
            "cap",
            _param(
                self.cap,
                "cap",
                SHARE,
                owner="LinearCappedCoverage",
                unit="share",
                description="maximum attainable coverage",
            ),
        )

    def parameters(self) -> dict[str, Param]:
        return {"per_unit": self.per_unit, "cap": self.cap}  # type: ignore[dict-item]

    def evaluate(self, units: ArrayLike, v: Mapping[str, ArrayLike]) -> ArrayLike:
        return np.minimum(np.asarray(v["cap"]), np.asarray(v["per_unit"]) * np.asarray(units))


@dataclass(frozen=True)
class SaturatingCoverage(Coverage):
    """coverage = max_coverage * (1 - exp(-rate * units)).  Diminishing returns throughout."""

    rate: Param | float
    max_coverage: Param | float = 1.0  # neutral: saturates at 100%
    form: ClassVar[str] = "saturating"

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "rate",
            _param(
                self.rate,
                "rate",
                POSITIVE,
                owner="SaturatingCoverage",
                unit="1/unit",
                description="saturation rate k per unit deployed",
            ),
        )
        object.__setattr__(
            self,
            "max_coverage",
            _param(
                self.max_coverage,
                "max_coverage",
                SHARE,
                owner="SaturatingCoverage",
                unit="share",
                description="asymptotic maximum coverage",
            ),
        )

    def parameters(self) -> dict[str, Param]:
        return {"rate": self.rate, "max_coverage": self.max_coverage}  # type: ignore[dict-item]

    def evaluate(self, units: ArrayLike, v: Mapping[str, ArrayLike]) -> ArrayLike:
        k = np.asarray(v["rate"])
        return np.asarray(v["max_coverage"]) * (1.0 - np.exp(-k * np.asarray(units)))


def doubling_table(coverage: Coverage, units: Sequence[float]) -> pd.DataFrame:
    """Coverage at u and 2u (central parameter values): the ratio is < 2 once saturation or a
    cap matters -- doubling units never more than doubles coverage, and usually less."""
    u = np.asarray(units, dtype=float)
    c1 = np.asarray(coverage(u), dtype=float)
    c2 = np.asarray(coverage(2 * u), dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = np.where(c1 > 0, c2 / c1, np.nan)
        marginal = np.where(u > 0, (c2 - c1) / u, np.nan)
    return pd.DataFrame(
        {
            "form": coverage.form,
            "units": u,
            "coverage": c1,
            "coverage_at_double_units": c2,
            "doubling_ratio": ratio,
            "marginal_coverage_per_extra_unit": marginal,
            "kind": HYPOTHETICAL,
        }
    )


@dataclass
class SegmentEffect:
    """Relative reductions within the target segment (None = not defined / not supplied)."""

    deaths: ArrayLike
    fatal_crashes: ArrayLike | None
    ka_crashes: ArrayLike | None
    chain: dict[str, ArrayLike] = field(default_factory=dict)


def _behaviour_chain(b: ArrayLike, occ: ArrayLike, sev: ArrayLike) -> ArrayLike:
    """Share of target-segment outcomes prevented when a share ``b`` of the targeted behaviour
    is removed and the affected exposure then crashes (1-occ) times as often with (1-sev) times
    the probability of the outcome per crash."""
    return np.asarray(b) * (1.0 - (1.0 - np.asarray(occ)) * (1.0 - np.asarray(sev)))


class Mechanism(ABC):
    """An intervention's causal chain from deployment to relative reduction in target deaths."""

    kind: ClassVar[str]
    target_segment: str
    allowed_segments: ClassVar[tuple[str, ...]]

    def _check_segment(self) -> None:
        if self.target_segment not in self.allowed_segments:
            raise ValueError(
                f"{type(self).__name__}: target_segment must be one of {self.allowed_segments}, "
                f"got {self.target_segment!r}"
            )

    @abstractmethod
    def parameters(self, baseline: EmpiricalBaseline | None = None) -> dict[str, Param]: ...

    @abstractmethod
    def effect(self, v: Mapping[str, ArrayLike], baseline: EmpiricalBaseline) -> SegmentEffect: ...

    @abstractmethod
    def chain_description(self) -> list[str]: ...


def _sev_ka_param(x: Param | float | None, owner: str) -> Param | None:
    if x is None:
        return None
    return _param(
        x,
        "severity_effect_ka",
        SIGNED_SHARE,
        owner=owner,
        description="relative reduction in P(KA | crash) for affected crashes",
    )


@dataclass
class SpeedEnforcement(Mechanism):
    """Automated speed enforcement (cameras).

    Chain: units (current -> proposed) -> coverage c(u) of target exposure -> effective share
    E = min(1, (1 + halo) * c), where ``halo`` is the exposure affected outside the covered
    exposure as a multiple of it (0 = none; the halo vanishes with coverage) -> speeding
    prevalence S(u) = S0 * (1 - response * E(u)), so relative to the observed baseline
    (current deployment) the share of target speeding removed is
    B = 1 - (1 - response*E_new) / (1 - response*E_cur) -> deaths in the target segment fall by
    B * [1 - (1 - occurrence_effect)(1 - severity_effect)].
    """

    units_current: float
    units_proposed: float
    coverage: Coverage
    behavioural_response: Param | float | None = None
    occurrence_effect: Param | float | None = None
    severity_effect: Param | float | None = None
    severity_effect_ka: Param | float | None = None
    halo: Param | float = 0.0  # neutral: no effect outside covered exposure
    target_segment: str = "speeding_exceeded_limit"
    kind: ClassVar[str] = "speed_enforcement"
    allowed_segments: ClassVar[tuple[str, ...]] = ("speeding", "speeding_exceeded_limit")

    def __post_init__(self) -> None:
        o = "SpeedEnforcement"
        self._check_segment()
        self.units_current = _nonneg(self.units_current, "units_current", o)
        self.units_proposed = _nonneg(self.units_proposed, "units_proposed", o)
        if not isinstance(self.coverage, Coverage):
            raise TypeError(f"{o}: coverage must be a Coverage function")
        self.behavioural_response = _param(
            self.behavioural_response,
            "behavioural_response",
            SHARE,
            owner=o,
            description="relative reduction in speeding prevalence within covered exposure",
        )
        self.occurrence_effect = _param(
            self.occurrence_effect,
            "occurrence_effect",
            SIGNED_SHARE,
            owner=o,
            description="relative reduction in crash frequency of exposure whose speeding is removed",
        )
        self.severity_effect = _param(
            self.severity_effect,
            "severity_effect",
            SIGNED_SHARE,
            owner=o,
            description="relative reduction in P(fatal | crash) for crashes whose speeding is removed",
        )
        self.severity_effect_ka = _sev_ka_param(self.severity_effect_ka, o)
        self.halo = _param(
            self.halo,
            "halo",
            (0.0, 10.0),
            owner=o,
            unit="multiple of covered exposure",
            description="exposure also affected outside coverage, as a multiple of the covered "
            "exposure (spillover/halo; 0 = none)",
        )

    def parameters(self, baseline: EmpiricalBaseline | None = None) -> dict[str, Param]:
        p = {f"coverage.{k}": v for k, v in self.coverage.parameters().items()}
        p.update(
            behavioural_response=self.behavioural_response,
            occurrence_effect=self.occurrence_effect,
            severity_effect=self.severity_effect,
            halo=self.halo,
        )
        if self.severity_effect_ka is not None:
            p["severity_effect_ka"] = self.severity_effect_ka
        return p  # type: ignore[return-value]

    def effect(self, v: Mapping[str, ArrayLike], baseline: EmpiricalBaseline) -> SegmentEffect:
        cv = {k.removeprefix("coverage."): x for k, x in v.items() if k.startswith("coverage.")}
        c_cur = self.coverage.evaluate(self.units_current, cv)
        c_new = self.coverage.evaluate(self.units_proposed, cv)
        h, b = np.asarray(v["halo"]), np.asarray(v["behavioural_response"])
        e_cur = np.minimum(1.0, (1.0 + h) * c_cur)
        e_new = np.minimum(1.0, (1.0 + h) * c_new)
        denom = 1.0 - b * e_cur
        safe = np.where(denom > 0, denom, 1.0)
        removed = np.where(denom > 0, 1.0 - (1.0 - b * e_new) / safe, 0.0)
        d = _behaviour_chain(removed, v["occurrence_effect"], v["severity_effect"])
        ka = (
            _behaviour_chain(removed, v["occurrence_effect"], v["severity_effect_ka"])
            if "severity_effect_ka" in v
            else None
        )
        return SegmentEffect(
            deaths=d,
            fatal_crashes=d,
            ka_crashes=ka,
            chain={
                "coverage_current": c_cur,
                "coverage_proposed": c_new,
                "effective_share_current": e_cur,
                "effective_share_proposed": e_new,
                "share_of_target_speeding_removed": removed,
            },
        )

    def chain_description(self) -> list[str]:
        return [
            f"units deployed: {self.units_current:g} -> {self.units_proposed:g}",
            f"coverage function: {self.coverage.form}",
            "effective share of target exposure affected E = min(1, (1 + halo) * c)",
            "share of target-segment speeding removed B = 1-(1-response*E_new)/(1-response*E_cur)",
            "target deaths prevented share = B*[1-(1-occurrence_effect)*(1-severity_effect)]",
            "fatal crashes: same share (deaths per fatal crash in the segment assumed unchanged)",
        ]


@dataclass
class ImpairedDrivingEnforcement(Mechanism):
    """Roadside alcohol or drug checks.

    Chain: checks/year (current -> proposed) -> coverage c(checks) of impaired-driving exposure
    -> perceived detection risk r = detection_probability * c -> deterrence: prevalence
    P(r) = P0 * exp(-deterrence_elasticity * r), so the share of target impaired driving
    removed is B = 1 - exp(-elasticity * (r_new - r_cur)) -> deaths in the target segment fall
    by B * [1 - (1 - occurrence_effect)(1 - severity_effect)].
    """

    checks_current: float
    checks_proposed: float
    coverage: Coverage
    detection_probability: Param | float | None = None
    deterrence_elasticity: Param | float | None = None
    occurrence_effect: Param | float | None = None
    severity_effect: Param | float | None = None
    severity_effect_ka: Param | float | None = None
    target_segment: str = "alcohol"
    kind: ClassVar[str] = "impaired_driving_enforcement"
    allowed_segments: ClassVar[tuple[str, ...]] = ("alcohol", "drugs")

    def __post_init__(self) -> None:
        o = "ImpairedDrivingEnforcement"
        self._check_segment()
        self.checks_current = _nonneg(self.checks_current, "checks_current", o)
        self.checks_proposed = _nonneg(self.checks_proposed, "checks_proposed", o)
        if not isinstance(self.coverage, Coverage):
            raise TypeError(f"{o}: coverage must be a Coverage function")
        self.detection_probability = _param(
            self.detection_probability,
            "detection_probability",
            SHARE,
            owner=o,
            description="P(an impaired driver passing a check is detected), as perceived",
        )
        self.deterrence_elasticity = _param(
            self.deterrence_elasticity,
            "deterrence_elasticity",
            POSITIVE,
            owner=o,
            unit="per unit of perceived risk",
            description="-d ln(impaired-driving prevalence) / d(perceived detection risk)",
        )
        self.occurrence_effect = _param(
            self.occurrence_effect,
            "occurrence_effect",
            SIGNED_SHARE,
            owner=o,
            description="relative reduction in crash frequency of deterred trips",
        )
        self.severity_effect = _param(
            self.severity_effect,
            "severity_effect",
            SIGNED_SHARE,
            owner=o,
            description="relative reduction in P(fatal | crash) for deterred trips' crashes",
        )
        self.severity_effect_ka = _sev_ka_param(self.severity_effect_ka, o)

    def parameters(self, baseline: EmpiricalBaseline | None = None) -> dict[str, Param]:
        p = {f"coverage.{k}": v for k, v in self.coverage.parameters().items()}
        p.update(
            detection_probability=self.detection_probability,
            deterrence_elasticity=self.deterrence_elasticity,
            occurrence_effect=self.occurrence_effect,
            severity_effect=self.severity_effect,
        )
        if self.severity_effect_ka is not None:
            p["severity_effect_ka"] = self.severity_effect_ka
        return p  # type: ignore[return-value]

    def effect(self, v: Mapping[str, ArrayLike], baseline: EmpiricalBaseline) -> SegmentEffect:
        cv = {k.removeprefix("coverage."): x for k, x in v.items() if k.startswith("coverage.")}
        c_cur = self.coverage.evaluate(self.checks_current, cv)
        c_new = self.coverage.evaluate(self.checks_proposed, cv)
        det = np.asarray(v["detection_probability"])
        r_cur, r_new = det * c_cur, det * c_new
        removed = 1.0 - np.exp(-np.asarray(v["deterrence_elasticity"]) * (r_new - r_cur))
        d = _behaviour_chain(removed, v["occurrence_effect"], v["severity_effect"])
        ka = (
            _behaviour_chain(removed, v["occurrence_effect"], v["severity_effect_ka"])
            if "severity_effect_ka" in v
            else None
        )
        return SegmentEffect(
            deaths=d,
            fatal_crashes=d,
            ka_crashes=ka,
            chain={
                "coverage_current": c_cur,
                "coverage_proposed": c_new,
                "perceived_risk_current": r_cur,
                "perceived_risk_proposed": r_new,
                "share_of_target_impaired_driving_removed": removed,
            },
        )

    def chain_description(self) -> list[str]:
        return [
            f"checks/year: {self.checks_current:g} -> {self.checks_proposed:g}",
            f"coverage function: {self.coverage.form}",
            "perceived detection risk r = detection_probability * coverage",
            "share of target impaired driving removed B = 1 - exp(-elasticity*(r_new - r_cur))",
            "target deaths prevented share = B*[1-(1-occurrence_effect)*(1-severity_effect)]",
        ]


@dataclass
class RestraintEnforcement(Mechanism):
    """Seat-belt enforcement.

    Chain: share of currently unbelted occupants (in the target segment) who would be belted
    (``conversion_share``) x belt effectiveness (proportional reduction in P(death) given the
    crash; default: Layer A within-vehicle estimate if available) x ``converter_benefit_ratio``
    (converters' benefit relative to the average unbelted occupant; neutral default 1).
    """

    conversion_share: Param | float | None = None
    belt_effectiveness: Param | float | None = None
    converter_benefit_ratio: Param | float = 1.0
    target_segment: str = "unrestrained_lpv"
    kind: ClassVar[str] = "restraint_enforcement"
    allowed_segments: ClassVar[tuple[str, ...]] = ("unrestrained_lpv",)

    def __post_init__(self) -> None:
        o = "RestraintEnforcement"
        self._check_segment()
        self.conversion_share = _param(
            self.conversion_share,
            "conversion_share",
            SHARE,
            owner=o,
            description="share of currently unbelted occupants who would be belted",
        )
        if self.belt_effectiveness is not None:
            self.belt_effectiveness = _param(
                self.belt_effectiveness,
                "belt_effectiveness",
                SHARE,
                owner=o,
                description="proportional reduction in P(death | crash) belted vs unbelted",
            )
        self.converter_benefit_ratio = _param(
            self.converter_benefit_ratio,
            "converter_benefit_ratio",
            (0.0, 10.0),
            owner=o,
            description="converters' belt benefit relative to the average unbelted occupant (1 = same)",
        )

    def parameters(self, baseline: EmpiricalBaseline | None = None) -> dict[str, Param]:
        eff = self.belt_effectiveness
        if eff is None:
            if baseline is not None and baseline.belt_effectiveness is not None:
                eff = _param(
                    belt_effectiveness_param(baseline),
                    "belt_effectiveness",
                    SHARE,
                    owner="RestraintEnforcement",
                )
            else:
                raise MissingAssumptionError(
                    "RestraintEnforcement: belt_effectiveness not supplied and no within-vehicle "
                    "estimate (outputs/tables/matched/belt_effect.csv) in the baseline"
                )
        return {
            "conversion_share": self.conversion_share,  # type: ignore[dict-item]
            "belt_effectiveness": eff,  # type: ignore[dict-item]
            "converter_benefit_ratio": self.converter_benefit_ratio,  # type: ignore[dict-item]
        }

    def effect(self, v: Mapping[str, ArrayLike], baseline: EmpiricalBaseline) -> SegmentEffect:
        benefit = np.minimum(
            1.0, np.asarray(v["belt_effectiveness"]) * np.asarray(v["converter_benefit_ratio"])
        )
        d = np.asarray(v["conversion_share"]) * benefit
        return SegmentEffect(
            deaths=d,
            fatal_crashes=None,
            ka_crashes=None,
            chain={"benefit_per_converted_occupant": benefit},
        )

    def chain_description(self) -> list[str]:
        return [
            "target: unbelted LPV occupant deaths (FARS, population of the belt estimate)",
            "deaths prevented share = conversion_share * min(1, belt_effectiveness * converter_benefit_ratio)",
            "fatal crashes and KA crashes prevented: not defined (a prevented death need not "
            "prevent the crash; the within-vehicle estimate is conditional on a fatal crash)",
        ]


@dataclass
class GenericIntervention(Mechanism):
    """User-specified relative reduction in target-segment deaths (and optionally fatal and KA
    crashes) -- for interventions with no explicit chain (lighting, speed limits, campaigns)."""

    target_segment: str
    relative_reduction_deaths: Param | float | None = None
    relative_reduction_fatal_crashes: Param | float | None = None
    relative_reduction_ka: Param | float | None = None
    kind: ClassVar[str] = "generic"
    allowed_segments: ClassVar[tuple[str, ...]] = (ALL, *PARTITION_SEGMENTS)

    def __post_init__(self) -> None:
        o = "GenericIntervention"
        self._check_segment()
        self.relative_reduction_deaths = _param(
            self.relative_reduction_deaths,
            "relative_reduction_deaths",
            SIGNED_SHARE,
            owner=o,
            description="relative reduction in target-segment deaths",
        )
        if self.relative_reduction_fatal_crashes is not None:
            if self.target_segment in PERSON_SEGMENTS:
                raise ValueError(f"{o}: fatal-crash effects need a crash-level segment")
            self.relative_reduction_fatal_crashes = _param(
                self.relative_reduction_fatal_crashes,
                "relative_reduction_fatal_crashes",
                SIGNED_SHARE,
                owner=o,
                description="relative reduction in target fatal crashes",
            )
        if self.relative_reduction_ka is not None:
            if self.target_segment in PERSON_SEGMENTS:
                raise ValueError(f"{o}: KA-crash effects need a crash-level segment")
            self.relative_reduction_ka = _param(
                self.relative_reduction_ka,
                "relative_reduction_ka",
                SIGNED_SHARE,
                owner=o,
                description="relative reduction in target KA crashes",
            )

    def parameters(self, baseline: EmpiricalBaseline | None = None) -> dict[str, Param]:
        p = {"relative_reduction_deaths": self.relative_reduction_deaths}
        if self.relative_reduction_fatal_crashes is not None:
            p["relative_reduction_fatal_crashes"] = self.relative_reduction_fatal_crashes
        if self.relative_reduction_ka is not None:
            p["relative_reduction_ka"] = self.relative_reduction_ka
        return p  # type: ignore[return-value]

    def effect(self, v: Mapping[str, ArrayLike], baseline: EmpiricalBaseline) -> SegmentEffect:
        return SegmentEffect(
            deaths=np.asarray(v["relative_reduction_deaths"]),
            fatal_crashes=v.get("relative_reduction_fatal_crashes"),
            ka_crashes=v.get("relative_reduction_ka"),
        )

    def chain_description(self) -> list[str]:
        return [f"user-specified relative reduction in '{self.target_segment}' outcomes"]


# -- helpers converting Layer A associations into (explicitly assumed) parameters --------
def severity_effect_from_association(
    baseline: EmpiricalBaseline, segment: str, outcome: Literal["fatal", "ka"] = "fatal"
) -> Param:
    """``1 - 1/RR`` from the adjusted severity association, as a triangular Param over its CI.

    HYPOTHETICAL by construction: it treats an adjusted association *conditional on a crash*
    as a causal, fully reversible effect of removing the factor -- a strong assumption the data
    cannot verify (residual confounding, differential ascertainment by severity).
    """
    q = baseline.association(f"severity.{outcome}_adj_rr.{segment}")
    if q is None or q.value is None:
        raise MissingInputError(f"no adjusted {outcome} association for segment {segment!r}")
    conv = [1.0 - 1.0 / x for x in (q.low, q.value, q.high)]  # type: ignore[operator]
    return Param(
        conv[1],
        min(conv),
        max(conv),
        "triangular",
        unit="relative reduction",
        description=f"1 - 1/RR, RR = {q.value:.3g} ({q.low:.3g}-{q.high:.3g})",
        source=f"ASSUMES the adjusted association is causal: {q.source}",
    )


def belt_effectiveness_param(baseline: EmpiricalBaseline, variant: str | None = None) -> Param:
    """Belt effectiveness from the FARS within-vehicle estimate (triangular over its CI).

    ``variant`` selects a misreporting sensitivity row (e.g. 'misreport_f10').  The estimate is
    conditional on a fatal crash, which matches its use on deaths in fatal crashes.
    """
    name = "belt.fatality_reduction" + (f".{variant}" if variant else "")
    q = baseline.association(name)
    if q is None or q.value is None:
        raise MissingInputError(f"{name} not available in the baseline")
    lo = max(0.0, float(q.low if q.low is not None else q.value))
    hi = min(1.0, float(q.high if q.high is not None else q.value))
    return Param(
        min(max(q.value, lo), hi),
        lo,
        hi,
        "triangular",
        unit="relative reduction in P(death | fatal crash)",
        description="belt effectiveness given a fatal crash (FARS within-vehicle design)",
        source=(
            "ASSUMES the Layer A within-vehicle association is causal and applies to those who "
            f"would buckle up: {q.source}"
        ),
    )


# ======================================================================================
# Layer D -- outcomes
# ======================================================================================
STRUCTURAL_ASSUMPTIONS = [
    "Static baseline: counts stay at the window mean in the absence of the intervention.",
    "Relative effects are homogeneous within the target segment (including deaths shared with "
    "other segments).",
    "Unknown-status deaths/crashes are outside the segment (segment counts are lower bounds).",
    "No displacement, risk compensation or exposure change beyond what the parameters encode.",
]
COMBINATION_ASSUMPTIONS = {
    "multiplicative": "Shared deaths: interventions act independently (multiplicative survival "
    "1 - prod(1 - e_i)) within each cell of the observed segment overlap.",
    "max": "Shared deaths: interventions fully redundant (only the largest effect applies).",
    "naive_sum": "Shared deaths counted once per intervention (DOUBLE COUNTING; reference only).",
}


@dataclass
class Scenario:
    """One intervention: a mechanism plus optional timing (needed for multi-year projections)."""

    name: str
    mechanism: Mechanism
    timing: Timing | None = None

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[A-Za-z0-9_\-]+", self.name):
            raise ValueError("scenario names may contain letters, digits, '_' and '-' only")

    @property
    def target_segment(self) -> str:
        return self.mechanism.target_segment

    def parameters(self, baseline: EmpiricalBaseline | None = None) -> dict[str, Param]:
        p = dict(self.mechanism.parameters(baseline))
        if self.timing is not None:
            p.update(self.timing.parameters())
        return p


def _as_list(scenarios: Scenario | Sequence[Scenario]) -> list[Scenario]:
    out = [scenarios] if isinstance(scenarios, Scenario) else list(scenarios)
    if not out:
        raise ValueError("no scenarios given")
    names = [s.name for s in out]
    if len(set(names)) != len(names):
        raise ValueError(f"scenario names must be unique, got {names}")
    return out


def flat_parameters(
    scenarios: Scenario | Sequence[Scenario], baseline: EmpiricalBaseline
) -> dict[str, Param]:
    """All parameters; names are prefixed '<scenario>.' when there is more than one scenario."""
    sc = _as_list(scenarios)
    prefix = len(sc) > 1
    out: dict[str, Param] = {}
    for s in sc:
        for k, p in s.parameters(baseline).items():
            out[f"{s.name}.{k}" if prefix else k] = p
    return out


def _resolve(params: Mapping[str, Param], overrides: Mapping[str, ArrayLike] | None) -> dict:
    v: dict[str, ArrayLike] = {k: p.central for k, p in params.items()}
    for k, x in (overrides or {}).items():
        if k not in params:
            raise KeyError(f"unknown parameter {k!r}; parameters are {sorted(params)}")
        b_lo, b_hi = params[k].bounds
        arr = np.asarray(x, dtype=float)
        if np.any(arr < b_lo) or np.any(arr > b_hi) or np.any(~np.isfinite(arr)):
            raise ValueError(f"{k}={x!r} outside admissible bounds [{b_lo}, {b_hi}]")
        v[k] = x
    return v


def _scenario_values(s: Scenario, v: Mapping[str, ArrayLike], prefix: bool) -> dict:
    if not prefix:
        return dict(v)
    pre = f"{s.name}."
    return {k.removeprefix(pre): x for k, x in v.items() if k.startswith(pre)}


def _outcomes(
    scenarios: list[Scenario],
    baseline: EmpiricalBaseline,
    v: Mapping[str, ArrayLike],
    overlap: Overlap = "multiplicative",
    year: int | None = None,
) -> dict[str, Any]:
    """Core evaluation shared by evaluate / combine / tornado / Monte Carlo (vectorised)."""
    prefix = len(scenarios) > 1
    effects: list[tuple[Scenario, SegmentEffect, ArrayLike]] = []
    for s in scenarios:
        sv = _scenario_values(s, v, prefix)
        eff = s.mechanism.effect(sv, baseline)
        if year is None:
            mult: ArrayLike = 1.0
        else:
            if s.timing is None:
                raise MissingAssumptionError(
                    f"scenario {s.name!r}: multi-year projection needs Timing(ramp_years, "
                    "decay_per_year) (use Timing.immediate() for full effect from year 1)"
                )
            mult = Timing.multiplier(year, sv["timing.ramp_years"], sv["timing.decay_per_year"])
        effects.append((s, eff, mult))

    def scaled(e: ArrayLike, m: ArrayLike) -> np.ndarray:
        return np.asarray(e, dtype=float) * np.asarray(m, dtype=float)

    death_fx = [(s.target_segment, scaled(e.deaths, m)) for s, e, m in effects]
    out: dict[str, Any] = {
        "deaths_prevented": baseline.deaths.prevented(death_fx, overlap),
        "deaths_prevented_naive_sum": baseline.deaths.prevented(death_fx, "naive_sum"),
    }
    fatal_fx = [
        (s.target_segment, scaled(e.fatal_crashes, m))
        for s, e, m in effects
        if e.fatal_crashes is not None and s.target_segment not in PERSON_SEGMENTS
    ]
    out["fatal_crashes_prevented"] = (
        baseline.fatal_crashes.prevented(fatal_fx, overlap) if fatal_fx else None
    )
    out["fatal_crashes_scenarios"] = [s.name for s, e, _ in effects if e.fatal_crashes is not None]
    ka_fx = [
        (s.target_segment, scaled(e.ka_crashes, m))
        for s, e, m in effects
        if e.ka_crashes is not None and s.target_segment not in PERSON_SEGMENTS
    ]
    out["ka_crashes_prevented"] = (
        baseline.ka_crashes.prevented(ka_fx, overlap)
        if ka_fx and baseline.ka_crashes is not None
        else None
    )
    out["ka_crashes_scenarios"] = [
        s.name
        for s, e, _ in effects
        if e.ka_crashes is not None and baseline.ka_crashes is not None
    ]
    out["effects"] = effects
    return out


def _assumption_records(params: Mapping[str, Param], v: Mapping[str, ArrayLike]) -> list[dict]:
    recs = []
    for k, p in params.items():
        x = v[k]
        recs.append(
            {
                "parameter": k,
                "value_used": float(x) if np.ndim(x) == 0 else None,
                "low": p.low,
                "central": p.central,
                "high": p.high,
                "distribution": p.distribution,
                "unit": p.unit,
                "source": p.source,
                "description": p.description,
            }
        )
    return recs


def _pct(x: ArrayLike | None, base: float | None) -> ArrayLike | None:
    if x is None or not base:
        return None
    return -100.0 * np.asarray(x) / base if np.ndim(x) else -100.0 * float(x) / base


def _float(x: Any) -> float | None:
    return None if x is None else float(x)


def evaluate(
    scenario: Scenario,
    baseline: EmpiricalBaseline,
    values: Mapping[str, float] | None = None,
) -> dict[str, Any]:
    """Hypothetical steady-state annual outcome of one scenario (full implementation)."""
    params = scenario.parameters(baseline)
    v = _resolve(params, values)
    res = _outcomes([scenario], baseline, v)
    _, eff, _ = res["effects"][0]
    seg = scenario.target_segment
    ka_all = baseline.quantities.get("crss.ka_crashes_per_year")
    notes = []
    if baseline.reliability(seg) == "low":
        notes.append(f"target segment '{seg}' is LOW reliability: {SEGMENTS[seg].note}")
    if res["ka_crashes_prevented"] is None:
        notes.append(
            "KA crashes prevented not computed (no KA effect defined/supplied, person-level "
            "segment, or no CRSS baseline)"
        )
    if res["fatal_crashes_prevented"] is None:
        notes.append("fatal crashes prevented not defined for this mechanism/segment")
    return {
        "kind": HYPOTHETICAL,
        "scenario": scenario.name,
        "mechanism": scenario.mechanism.kind,
        "target_segment": seg,
        "target_reliability": baseline.reliability(seg),
        "baseline_window": f"{baseline.window[0]}-{baseline.window[1]}",
        "baseline_deaths_per_year": baseline.total_deaths(),
        "baseline_target_deaths_per_year": baseline.segment_deaths(seg),
        "baseline_target_fatal_crashes_per_year": baseline.segment_fatal_crashes(seg),
        "baseline_target_ka_crashes_per_year": baseline.segment_ka_crashes(seg),
        "relative_reduction_target_deaths": float(eff.deaths),
        "deaths_prevented": float(res["deaths_prevented"]),
        "fatal_crashes_prevented": _float(res["fatal_crashes_prevented"]),
        "ka_crashes_prevented": _float(res["ka_crashes_prevented"]),
        "pct_change_deaths": _pct(res["deaths_prevented"], baseline.total_deaths()),
        "pct_change_fatal_crashes": _pct(
            res["fatal_crashes_prevented"], baseline.fatal_crashes.total()
        ),
        "pct_change_ka_crashes": _pct(
            res["ka_crashes_prevented"], ka_all.value if ka_all is not None else None
        ),
        "chain": {k: float(np.asarray(x)) for k, x in eff.chain.items()},
        "chain_description": scenario.mechanism.chain_description(),
        "assumptions": _assumption_records(params, v),
        "structural_assumptions": list(STRUCTURAL_ASSUMPTIONS),
        "notes": notes,
    }


def combine(
    scenarios: Sequence[Scenario],
    baseline: EmpiricalBaseline,
    overlap: Overlap = "multiplicative",
    values: Mapping[str, float] | None = None,
) -> dict[str, Any]:
    """Joint steady-state outcome of several interventions without double counting.

    Shared deaths (e.g. a death in a crash that is both speeding-related and alcohol-involved)
    are counted once: within each cell of the observed overlap partition the interventions
    acting on that cell combine by ``overlap``.  The naive sum of separate projections and the
    double counting it implies are reported alongside.
    """
    sc = _as_list(scenarios)
    params = flat_parameters(sc, baseline)
    v = _resolve(params, values)
    res = _outcomes(sc, baseline, v, overlap)
    singles = {
        s.name: float(baseline.segment_deaths(s.target_segment) * np.asarray(e.deaths, dtype=float))
        for s, e, _ in res["effects"]
    }
    segs = sorted({s.target_segment for s in sc})
    shared = baseline.deaths.overlap(*segs) if len(segs) > 1 else baseline.segment_deaths(segs[0])
    excluded = [s.name for s in sc if s.name not in res["fatal_crashes_scenarios"]]
    ka_all = baseline.quantities.get("crss.ka_crashes_per_year")
    return {
        "kind": HYPOTHETICAL,
        "scenarios": [s.name for s in sc],
        "target_segments": [s.target_segment for s in sc],
        "overlap_rule": overlap,
        "overlap_assumption": COMBINATION_ASSUMPTIONS[overlap],
        "deaths_in_all_target_segments_per_year": shared,
        "deaths_in_any_target_segment_per_year": baseline.deaths.union(*segs),
        "deaths_prevented_by_scenario_alone": singles,
        "deaths_prevented": float(res["deaths_prevented"]),
        "deaths_prevented_naive_sum": float(res["deaths_prevented_naive_sum"]),
        "double_counting_avoided": float(res["deaths_prevented_naive_sum"])
        - float(res["deaths_prevented"]),
        "fatal_crashes_prevented": _float(res["fatal_crashes_prevented"]),
        "fatal_crashes_excludes": excluded,
        "ka_crashes_prevented": _float(res["ka_crashes_prevented"]),
        "pct_change_deaths": _pct(res["deaths_prevented"], baseline.total_deaths()),
        "pct_change_ka_crashes": _pct(
            res["ka_crashes_prevented"], ka_all.value if ka_all is not None else None
        ),
        "assumptions": _assumption_records(params, v),
        "structural_assumptions": [*STRUCTURAL_ASSUMPTIONS, COMBINATION_ASSUMPTIONS[overlap]],
    }


def project(
    scenarios: Scenario | Sequence[Scenario],
    baseline: EmpiricalBaseline,
    horizon_years: int,
    overlap: Overlap = "multiplicative",
    values: Mapping[str, float] | None = None,
) -> pd.DataFrame:
    """Year-by-year hypothetical outcomes with ramp-up and decay (Timing required)."""
    if int(horizon_years) < 1:
        raise ValueError("horizon_years must be >= 1")
    sc = _as_list(scenarios)
    params = flat_parameters(sc, baseline)
    v = _resolve(params, values)
    rows = []
    for t in range(1, int(horizon_years) + 1):
        res = _outcomes(sc, baseline, v, overlap, year=t)
        rows.append(
            {
                "year_index": t,
                "deaths_prevented": float(res["deaths_prevented"]),
                "fatal_crashes_prevented": _float(res["fatal_crashes_prevented"]),
                "ka_crashes_prevented": _float(res["ka_crashes_prevented"]),
            }
        )
    out = pd.DataFrame(rows)
    out["cumulative_deaths_prevented"] = out["deaths_prevented"].cumsum()
    out["kind"] = HYPOTHETICAL
    out["scenarios"] = "+".join(s.name for s in sc)
    out["overlap_rule"] = overlap if len(sc) > 1 else ""
    out["assumptions"] = "; ".join(f"{k}={float(v[k]):.6g}" for k in params)
    return out


OUTCOMES = ("deaths_prevented", "fatal_crashes_prevented", "ka_crashes_prevented")


def _is_timing(name: str) -> bool:
    return name.split(".")[-2:-1] == ["timing"] or name.startswith("timing.")


def _sensitivity_outcomes(
    sc: list[Scenario],
    baseline: EmpiricalBaseline,
    v: Mapping[str, ArrayLike],
    overlap: Overlap,
    horizon_years: int | None,
) -> dict[str, Any]:
    """Steady-state annual outcomes, or cumulative (undiscounted) outcomes over a horizon."""
    if horizon_years is None:
        return _outcomes(sc, baseline, v, overlap)
    if int(horizon_years) < 1:
        raise ValueError("horizon_years must be >= 1")
    tot: dict[str, Any] = dict.fromkeys(OUTCOMES, 0.0)
    for t in range(1, int(horizon_years) + 1):
        res = _outcomes(sc, baseline, v, overlap, year=t)
        for o in OUTCOMES:
            tot[o] = None if res[o] is None or tot[o] is None else tot[o] + np.asarray(res[o])
    return tot


def tornado(
    scenarios: Scenario | Sequence[Scenario],
    baseline: EmpiricalBaseline,
    outcome: str = "deaths_prevented",
    overlap: Overlap = "multiplicative",
    horizon_years: int | None = None,
) -> pd.DataFrame:
    """One-way sensitivity: each ranged parameter at its low and high, others at central.

    Steady state by default (timing parameters are then irrelevant and omitted); with
    ``horizon_years`` the outcome is the cumulative total over the horizon, including timing.
    """
    if outcome not in OUTCOMES:
        raise ValueError(f"outcome must be one of {OUTCOMES}")
    sc = _as_list(scenarios)
    params = flat_parameters(sc, baseline)
    centre = _sensitivity_outcomes(sc, baseline, _resolve(params, None), overlap, horizon_years)
    if centre[outcome] is None:
        raise ValueError(f"{outcome} is not defined for these scenarios")
    label = outcome if horizon_years is None else f"cumulative_{outcome}_{int(horizon_years)}y"
    rows = []
    for k, p in params.items():
        if horizon_years is None and _is_timing(k):
            continue
        lo, hi = (
            _sensitivity_outcomes(sc, baseline, _resolve(params, {k: x}), overlap, horizon_years)[
                outcome
            ]
            for x in (p.low, p.high)
        )
        rows.append(
            {
                "parameter": k,
                "low": p.low,
                "central": p.central,
                "high": p.high,
                f"{label}_at_low": float(lo),
                f"{label}_at_central": float(centre[outcome]),
                f"{label}_at_high": float(hi),
                "swing": abs(float(hi) - float(lo)),
                "source": p.source,
            }
        )
    out = pd.DataFrame(rows).sort_values("swing", ascending=False, kind="stable")
    out["kind"] = HYPOTHETICAL
    return out.reset_index(drop=True)


def corner_range(
    scenarios: Scenario | Sequence[Scenario],
    baseline: EmpiricalBaseline,
    overlap: Overlap = "multiplicative",
    max_params: int = 14,
    horizon_years: int | None = None,
) -> dict[str, Any]:
    """Minimum and maximum of each outcome over all low/high combinations of the ranged
    parameters -- the exact range when outcomes are monotone in each parameter.  Steady state
    by default (timing parameters ignored); cumulative over ``horizon_years`` if given."""
    sc = _as_list(scenarios)
    params = flat_parameters(sc, baseline)
    ranged = [
        k
        for k, p in params.items()
        if not p.is_fixed and (horizon_years is not None or not _is_timing(k))
    ]
    if len(ranged) > max_params:
        raise ValueError(f"{len(ranged)} ranged parameters: too many corners (max {max_params})")
    grid = np.array(list(itertools.product((0, 1), repeat=len(ranged))), dtype=bool)
    v: dict[str, ArrayLike] = {k: p.central for k, p in params.items()}
    for j, k in enumerate(ranged):
        v[k] = np.where(grid[:, j], params[k].high, params[k].low)
    res = _sensitivity_outcomes(sc, baseline, v, overlap, horizon_years)
    out: dict[str, Any] = {
        "kind": HYPOTHETICAL,
        "basis": "steady state (annual)"
        if horizon_years is None
        else f"cumulative over {int(horizon_years)} years",
        "ranged_parameters": ranged,
        "assumptions": [{"parameter": k, **p.to_dict()} for k, p in params.items()],
    }
    for o in OUTCOMES:
        x = res[o]
        out[o] = None if x is None else {"min": float(np.min(x)), "max": float(np.max(x))}
    return out


@dataclass
class MonteCarloResult:
    draws: pd.DataFrame
    summary: pd.DataFrame
    seed: int
    n_draws: int
    assumptions: list[dict] = field(default_factory=list)
    kind: str = HYPOTHETICAL
    note: str = (
        "Assumption uncertainty only: parameters drawn independently from their ranges; "
        "FARS counts are a census and CRSS sampling error is reported separately in Layer A."
    )


def monte_carlo(
    scenarios: Scenario | Sequence[Scenario],
    baseline: EmpiricalBaseline,
    n_draws: int = 10_000,
    seed: int = config.RANDOM_SEED,
    overlap: Overlap = "multiplicative",
    horizon_years: int | None = None,
) -> MonteCarloResult:
    """Monte Carlo over the parameter distributions (independent draws, fixed seed)."""
    sc = _as_list(scenarios)
    params = flat_parameters(sc, baseline)
    rng = np.random.default_rng(seed)
    v = {k: p.sample(rng, n_draws) for k, p in params.items()}
    res = _outcomes(sc, baseline, v, overlap)
    draws = pd.DataFrame(v)
    for o in OUTCOMES:
        if res[o] is not None:
            draws[o] = np.broadcast_to(res[o], (n_draws,))
    if horizon_years is not None:
        cum = _sensitivity_outcomes(sc, baseline, v, overlap, horizon_years)
        for o in OUTCOMES:
            if cum[o] is not None:
                draws[f"cumulative_{o}_{int(horizon_years)}y"] = np.broadcast_to(cum[o], (n_draws,))
    rows = []
    for o in [c for c in draws.columns if c not in params]:
        x = draws[o].to_numpy(dtype=float)
        q = np.percentile(x, [2.5, 5, 50, 95, 97.5])
        rows.append(
            {
                "outcome": o,
                "mean": float(x.mean()),
                "sd": float(x.std(ddof=1)) if n_draws > 1 else 0.0,
                "p2_5": q[0],
                "p5": q[1],
                "p50": q[2],
                "p95": q[3],
                "p97_5": q[4],
                "share_draws_positive": float((x > 0).mean()),
                "kind": HYPOTHETICAL,
            }
        )
    assumptions = [{"parameter": k, **p.to_dict()} for k, p in params.items()]
    return MonteCarloResult(draws, pd.DataFrame(rows), int(seed), int(n_draws), assumptions)


# -- solving for parameters ------------------------------------------------------------
def solve_monotone(
    fn: Callable[[float], float],
    target: float,
    bounds: tuple[float, float],
    n_grid: int = 65,
) -> dict[str, Any]:
    """Where fn(x) crosses ``target`` within ``bounds`` (grid bracketing + Brent's method).

    Status: 'solved' (``value`` = first crossing point), 'met_throughout_bounds' (fn >= target
    everywhere in the bounds) or 'not_achievable' (fn < target throughout the bounds).
    ``direction`` reports whether fn increases ('increasing': ``value`` is the *minimum
    required*) or decreases ('decreasing': ``value`` is the *maximum allowed*, e.g. a decay
    rate) through the crossing.
    """
    lo, hi = (float(b) for b in bounds)
    if not (math.isfinite(lo) and math.isfinite(hi) and lo < hi):
        raise ValueError(f"search bounds must be finite with lo < hi, got {bounds}")
    xs = np.linspace(lo, hi, n_grid)
    ys = np.array([fn(float(x)) for x in xs])
    g = ys - target
    base = {
        "target": float(target),
        "bounds": [lo, hi],
        "min_outcome_in_bounds": float(ys.min()),
        "max_outcome_in_bounds": float(ys.max()),
    }
    if np.all(g >= 0):
        return {**base, "status": "met_throughout_bounds", "value": lo, "direction": None}
    if np.all(g < 0):
        return {**base, "status": "not_achievable", "value": None, "direction": None}
    if g[0] < 0:  # increasing through the target: the root is the minimum value required
        i, direction = int(np.nonzero(g >= 0)[0][0]), "increasing"
    else:  # decreasing through the target: the root is the maximum value allowed
        i, direction = int(np.nonzero(g < 0)[0][0]), "decreasing"
    root = optimize.brentq(lambda x: fn(x) - target, xs[i - 1], xs[i], xtol=1e-12)
    return {**base, "status": "solved", "value": float(root), "direction": direction}


def search_bounds(p: Param, bounds: tuple[float, float] | None) -> tuple[float, float]:
    if bounds is not None:
        return bounds
    lo, hi = p.bounds
    lo = lo if math.isfinite(lo) else min(0.0, p.low or 0.0)
    hi = hi if math.isfinite(hi) else max(10.0 * abs(p.high or 0.0), 1.0)
    return lo, hi


def solve_scenario_parameter(
    scenarios: Scenario | Sequence[Scenario],
    baseline: EmpiricalBaseline,
    parameter: str,
    target: float,
    outcome: str = "deaths_prevented",
    bounds: tuple[float, float] | None = None,
    overlap: Overlap = "multiplicative",
    values: Mapping[str, float] | None = None,
) -> dict[str, Any]:
    """Value of one parameter at which ``outcome`` reaches ``target`` (others at central or
    ``values``).  Search bounds default to the parameter's admissible domain (finite part)."""
    sc = _as_list(scenarios)
    params = flat_parameters(sc, baseline)
    if parameter not in params:
        raise KeyError(f"unknown parameter {parameter!r}; parameters are {sorted(params)}")
    fixed = dict(values or {})

    def fn(x: float) -> float:
        r = _outcomes(sc, baseline, _resolve(params, {**fixed, parameter: x}), overlap)[outcome]
        if r is None:
            raise ValueError(f"{outcome} not defined for these scenarios")
        return float(r)

    res = solve_monotone(fn, target, search_bounds(params[parameter], bounds))
    return {"kind": HYPOTHETICAL, "parameter": parameter, "outcome": outcome, **res}


# ======================================================================================
# Threshold analysis needing no effect-size assumptions
# ======================================================================================
def required_share_table(
    baseline: EmpiricalBaseline,
    segments: Sequence[str] = PARTITION_SEGMENTS,
    reductions_pct: Sequence[float] = (1.0, 2.0, 5.0, 10.0),
) -> pd.DataFrame:
    """Share of each segment's deaths that would have to be prevented to cut *all* deaths by
    p% -- arithmetic on observed counts (no effect sizes).  Values above 100% mean the target
    cannot be reached through that segment alone."""
    total = baseline.total_deaths()
    rows = []
    for seg in segments:
        d = baseline.segment_deaths(seg)
        for p in reductions_pct:
            need = total * p / 100.0
            share = need / d if d > 0 else math.inf
            rows.append(
                {
                    "segment": seg,
                    "reliability": baseline.reliability(seg),
                    "segment_deaths_per_year": d,
                    "all_deaths_per_year": total,
                    "segment_share_of_all_deaths": d / total,
                    "reduction_of_all_deaths_pct": p,
                    "deaths_to_prevent_per_year": need,
                    "required_share_of_segment_deaths": share,
                    "feasible_through_segment_alone": bool(share <= 1.0),
                    "kind": HYPOTHETICAL,
                    "assumptions": "none beyond a static baseline (arithmetic on observed counts)",
                }
            )
    return pd.DataFrame(rows)


def breakeven_share_grid(
    baseline: EmpiricalBaseline,
    required_deaths: Sequence[float] = (1, 2, 5, 10, 20, 50, 100, 200, 500, 1000),
    segments: Sequence[str] = PARTITION_SEGMENTS,
) -> pd.DataFrame:
    """For a programme whose break-even requires R deaths prevented per year (R = equivalent
    annual cost / cost-effectiveness threshold, both user-supplied), the share of each segment's
    deaths that must be prevented.  No prices or effect sizes are assumed."""
    rows = []
    for seg in segments:
        d = baseline.segment_deaths(seg)
        for r in required_deaths:
            rows.append(
                {
                    "segment": seg,
                    "reliability": baseline.reliability(seg),
                    "segment_deaths_per_year": d,
                    "required_deaths_prevented_per_year": float(r),
                    "required_share_of_segment_deaths": r / d if d > 0 else math.inf,
                    "required_pct_of_all_deaths": 100.0 * r / baseline.total_deaths(),
                    "kind": HYPOTHETICAL,
                }
            )
    return pd.DataFrame(rows)


def conditional_threshold_table(
    baseline: EmpiricalBaseline, reduction_pct: float = 1.0
) -> pd.DataFrame:
    """Required behaviour change per p% of all deaths IF the empirical Layer-A estimates were
    the intervention's effect: belt effectiveness for restraint (with misreporting variants) and
    the severity-only pathway ``1 - 1/RR`` for speeding/alcohol (occurrence effect set to 0).

    Labelled hypothetical: treating these estimates as causal effects of a behaviour change is
    an assumption the data cannot verify; no user effect sizes enter.
    """
    need = baseline.total_deaths() * reduction_pct / 100.0
    rows = []
    belts = {
        k: q for k, q in baseline.associations.items() if k.startswith("belt.fatality_reduction")
    }
    d_unb = baseline.segment_deaths("unrestrained_lpv")
    for k, q in belts.items():
        for which, eff in (("estimate", q.value), ("ci_low", q.low), ("ci_high", q.high)):
            if eff is None or eff <= 0:
                continue
            rows.append(
                {
                    "segment": "unrestrained_lpv",
                    "empirical_input": k,
                    "input_point": which,
                    "input_value": eff,
                    "required_quantity": "share of unbelted occupants (in fatal crashes) who must buckle up",
                    "required_value": need / (d_unb * eff),
                    "reduction_of_all_deaths_pct": reduction_pct,
                    "deaths_to_prevent_per_year": need,
                    "kind": HYPOTHETICAL,
                    "assumptions": "belt estimate (conditional on a fatal crash) applies causally "
                    "to converters; static baseline",
                    "source": q.source,
                    "input_flag": q.flag,
                }
            )
    for seg in ("speeding", "speeding_exceeded_limit", "alcohol"):
        q = baseline.association(f"severity.fatal_adj_rr.{seg}")
        if q is None or q.value is None:
            continue
        d = baseline.segment_deaths(seg)
        for which, rr in (("estimate", q.value), ("ci_low", q.low), ("ci_high", q.high)):
            if rr is None or rr <= 1:
                continue
            sev = 1.0 - 1.0 / rr
            rows.append(
                {
                    "segment": seg,
                    "empirical_input": f"severity.fatal_adj_rr.{seg}",
                    "input_point": which,
                    "input_value": rr,
                    "required_quantity": "share of target-segment crashes whose factor must be "
                    "removed (severity pathway only)",
                    "required_value": need / (d * sev),
                    "reduction_of_all_deaths_pct": reduction_pct,
                    "deaths_to_prevent_per_year": need,
                    "kind": HYPOTHETICAL,
                    "assumptions": "adjusted RR (conditional on a crash) treated as causal and "
                    "reversible; no crash-occurrence effect; static baseline"
                    + (
                        "; RR is for police-reported (imputed) alcohol involvement while the "
                        "deaths segment is driver BAC>=.08"
                        if seg == "alcohol"
                        else ""
                    ),
                    "source": q.source,
                    "input_flag": q.flag,
                }
            )
    out = pd.DataFrame(rows)
    if len(out):
        out["attainable"] = out["required_value"] <= 1.0
    return out


def overlap_table(baseline: EmpiricalBaseline) -> pd.DataFrame:
    """Pairwise overlap of target segments (deaths/year): both, either, and the double counting
    a naive sum of 'all segment deaths prevented' would imply."""
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
def _fmt(x: float | None, d: int = 0) -> str:
    return "n/a" if x is None or (isinstance(x, float) and not math.isfinite(x)) else f"{x:,.{d}f}"


def run(window: tuple[int, int] = DEFAULT_WINDOW) -> dict[str, Any]:
    """Build and save the 2022-2024 baseline and the assumption-free threshold analysis."""
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
    req = required_share_table(base)
    paths["required"] = save_table(
        req,
        MODULE,
        "threshold_required_share",
        description="HYPOTHETICAL threshold arithmetic: share of each segment's deaths that would "
        "have to be prevented to reduce all deaths by 1/2/5/10% (no effect sizes assumed)",
        unit="segment",
        method="required share = p% x all deaths / segment deaths (window means)",
        extra=meta,
        **common,
    )
    grid = breakeven_share_grid(base)
    paths["breakeven_grid"] = save_table(
        grid,
        MODULE,
        "threshold_breakeven_grid",
        description="HYPOTHETICAL: share of segment deaths that must be prevented when break-even "
        "requires R deaths prevented per year (R = annualised cost / user threshold)",
        unit="segment x R",
        extra=meta,
        **common,
    )
    cond = conditional_threshold_table(base)
    paths["conditional"] = save_table(
        cond,
        MODULE,
        "threshold_conditional_on_empirical_estimates",
        description="HYPOTHETICAL: behaviour change needed per 1% of all deaths IF the Layer-A "
        "belt estimate / adjusted severity RRs were causal effects (severity pathway only)",
        unit="segment x empirical input",
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
    demo = pd.concat(
        [
            doubling_table(SaturatingCoverage(rate=1.0), [0.25, 0.5, 1.0, 2.0, 3.0]),
            doubling_table(LinearCappedCoverage(per_unit=0.25, cap=0.6), [0.5, 1.0, 2.0, 3.0]),
        ],
        ignore_index=True,
    )
    demo["note"] = (
        "Mathematical property of the coverage functions in dimensionless units (rate=1, or "
        "per_unit=0.25 with cap 0.6); NOT an empirical coverage estimate"
    )
    paths["doubling"] = save_table(
        demo,
        MODULE,
        "coverage_doubling_demo",
        description="Why doubling units does not double coverage: coverage at u and 2u for the "
        "saturating and capped-linear forms (dimensionless illustration)",
        unit="units (dimensionless)",
        extra=meta,
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
    summary = write_summary(base, req, cond, ov, inv)
    return {
        "baseline": base,
        "threshold_required_share": req,
        "threshold_breakeven_grid": grid,
        "threshold_conditional": cond,
        "segment_overlap": ov,
        "coverage_doubling_demo": demo,
        "inventory": inv,
        "paths": {k: str(v) for k, v in paths.items()} | {"summary": str(summary)},
    }


def write_summary(
    base: EmpiricalBaseline,
    req: pd.DataFrame,
    cond: pd.DataFrame,
    ov: pd.DataFrame,
    inv: pd.DataFrame,
) -> str:
    """outputs/tables/simulation/SUMMARY.md from the computed tables (numbers never typed)."""
    q = base.quantities
    a = base.associations
    span = f"{base.window[0]}-{base.window[1]}"
    total = base.total_deaths()

    def qv(name: str, d: int = 0) -> str:
        x = q.get(name)
        return _fmt(x.value if x else None, d)

    def ci(name: str, d: int = 0, src: Mapping[str, Quantity] = q) -> str:
        x = src.get(name)
        if x is None or x.value is None:
            return "n/a"
        s = f"{_fmt(x.value, d)} (95% CI {_fmt(x.low, d)}-{_fmt(x.high, d)})"
        return s + (f" [{x.flag}]" if x.flag else "")

    seg_lines = []
    for seg in PARTITION_SEGMENTS:
        r1 = req[(req["segment"] == seg) & (req["reduction_of_all_deaths_pct"] == 1.0)].iloc[0]
        unk = q.get(f"fars.deaths_per_year.{seg}.status_unknown")
        ka = q.get(f"crss.ka_crashes_per_year.{seg}")
        seg_lines.append(
            f"| {seg} | {SEGMENTS[seg].reliability} | {qv(f'fars.deaths_per_year.{seg}')} | "
            f"{100 * float(r1['segment_share_of_all_deaths']):.1f}% | "
            f"{_fmt(unk.value) if unk else 'none (BAC imputed)'} | "
            f"{ci(f'crss.ka_crashes_per_year.{seg}') if ka else 'n/a (persons)'} | "
            f"{100 * float(r1['required_share_of_segment_deaths']):.1f}% |"
        )
    ov_lines = [
        f"| {r.segment_a} & {r.segment_b} | {_fmt(r.deaths_both)} | "
        f"{100 * r.share_of_a_also_in_b:.1f}% | {100 * r.share_of_b_also_in_a:.1f}% |"
        for r in ov.itertuples()
        if not r.nested
    ]
    cond_lines = [
        f"| {r.segment} | {r.empirical_input} ({r.input_point}) | {r.input_value:.3f} | "
        f"{100 * r.required_value:.1f}%{'' if r.attainable else ' (not attainable: > 100%)'} |"
        for r in cond.itertuples()
    ]
    assoc_lines = [
        f"| {k} | {_fmt(x.value, 3)} ({_fmt(x.low, 3)}-{_fmt(x.high, 3)})"
        f"{' [' + x.flag + ']' if x.flag else ''} | {x.source} |"
        for k, x in a.items()
    ]
    stale_notes = [n for n in base.notes if n.startswith("STALE")]
    stale_text = (
        "\n**Warning -- upstream tables older than the processed data** (the rows flagged "
        "`stale_upstream` above, and every number derived from them, must be regenerated "
        "after re-running the upstream module):\n\n"
        + "\n".join(f"* {n}" for n in stale_notes)
        + "\n"
        if stale_notes
        else ""
    )
    ann = base.annual
    ka_q = q.get("crss.ka_crashes_per_year")
    cf, ff = q.get("crss.fatal_crashes_per_year"), q.get("fars.fatal_crashes_per_year")
    covered = (
        cf is not None
        and ff is not None
        and None not in (cf.low, cf.high, ff.value)
        and cf.low <= ff.value <= cf.high  # type: ignore[operator]
    )
    checks = [
        f"* FARS deaths partition (32 cells) sums to {_fmt(base.deaths.total())} deaths/yr = "
        f"`fars.deaths_per_year` {qv('fars.deaths_per_year')}; fatal-crash partition sums to "
        f"{_fmt(base.fatal_crashes.total())} = {qv('fars.fatal_crashes_per_year')}.",
        f"* CRSS KA partition sums to {_fmt(base.ka_crashes.total() if base.ka_crashes else None)}"
        f" = `crss.ka_crashes_per_year` {_fmt(ka_q.value if ka_q else None)}.",
        f"* CRSS design-based estimate of fatal crashes {ci('crss.fatal_crashes_per_year')} "
        + ("contains" if covered else "does NOT contain")
        + f" the FARS census count {qv('fars.fatal_crashes_per_year')} (NHTSA-imputed "
        "severity is calibrated to FARS).",
        "* FARS alcohol segment for 2022 (expected value over implicates): "
        + _fmt(float(ann.loc[ann["YEAR"] == 2022, "deaths_alcohol"].iloc[0]))
        + " deaths (`baseline_annual.csv`)."
        if 2022 in set(ann["YEAR"])
        else "",
    ]
    year_lines = [
        f"| {int(r.YEAR)} | {int(r.deaths):,} | {int(r.fatal_crashes):,} |"
        for r in ann.itertuples()
    ]
    text = f"""# RQ10 simulation engine and cost model -- summary

Module: `nhtsa_stats.simulation.engine` (`run()`), `nhtsa_stats.simulation.costs`.
Generated from the output tables in this directory; every number below is copied from them.

**What this is.** Tooling, not inference. The database contains no camera, enforcement,
checkpoint, roadside-testing, campaign or cost data (searched: {inv.attrs.get("n_columns_scanned", "n/a")}
source-table-column combinations in {inv.attrs.get("n_tables_scanned", "n/a")} source-tables of
`outputs/audit/column_inventory.csv`, label columns excluded; {len(inv)} enforcement/cost-like
column names matched, none of which measures an intervention or a cost --
`inventory_enforcement_cost_fields.csv`). So no intervention effect is estimated here. The
engine combines an **empirical baseline** (Layer A) with **user assumptions** (Layer C)
through explicit **mechanisms** (Layer B); every simulated output is labelled
`kind = "hypothetical"` and carries the assumptions used (Layer D). No default effect sizes
or prices exist in the code, except that belt effectiveness defaults to the FARS within-vehicle
estimate (treated as causal by assumption) when the user supplies none. Assumptions and worked hypothetical examples:
`docs/policy_assumptions.md`.

## 1. Layer A baseline ({span}, window means) -- `baseline.csv`, `baseline.json`

* FARS deaths: **{qv("fars.deaths_per_year")}** per year (observed census); fatal crashes:
  **{qv("fars.fatal_crashes_per_year")}** per year.
* CRSS police-reported crashes: {ci("crss.crashes_per_year")} per year; KA crashes:
  {ci("crss.ka_crashes_per_year")}; CRSS-estimated fatal crashes {ci("crss.fatal_crashes_per_year")}
  (compare FARS census {qv("fars.fatal_crashes_per_year")}).

| Year | FARS deaths | FARS fatal crashes |
|---|---|---|
{chr(10).join(year_lines)}

Target segments (deaths are observed FARS counts, mean per year; alcohol is the expected
value over the 10 BAC implicates; KA crashes are CRSS design-based estimates, 95% CI, 42 df):

| Segment | Reliability | Deaths/yr | Share of all deaths | Deaths/yr with unknown status (not counted) | CRSS KA crashes/yr | Share of segment deaths to prevent per 1% of all deaths |
|---|---|---|---|---|---|---|
{chr(10).join(seg_lines)}

Segment definitions differ slightly between sources (FARS alcohol = driver MI-BAC >= .08;
CRSS alcohol = NHTSA-imputed police-reported involvement). Drug involvement is LOW
reliability (unknown for about half of fatal crashes, selective testing, presence is not
impairment). The unrestrained segment is restricted to the population of the within-vehicle
belt estimate (LPV occupants aged {BELT_MIN_AGE}+, front or second row); deaths with unknown
restraint use are excluded, so the count is a lower bound.

Adjusted associations carried into Layer A (not causal; conditional on a crash):

| Quantity | Estimate (95% CI) | Source |
|---|---|---|
{chr(10).join(assoc_lines)}
{stale_text}
## 2. Overlap between segments (observed) -- `segment_overlap.csv`, `baseline_partitions.csv`

| Segments | Deaths/yr in both | Share of first also in second | Share of second also in first |
|---|---|---|---|
{chr(10).join(ov_lines)}

Combining interventions uses this cross-classification: within each cell, interventions
combine by multiplicative survival (default), so shared deaths are never counted twice;
the naive sum and the double counting it implies are reported by `engine.combine`.

## 3. Assumption-free threshold analysis (hypothetical arithmetic) -- `threshold_required_share.csv`

To reduce **all** road deaths by 1% (= {_fmt(total / 100)} deaths/year) through a single segment,
the share of that segment's deaths that would have to be prevented is shown in the last column
of the table in section 1 (e.g. speeding-related {100 * float(req[(req.segment == "speeding") & (req.reduction_of_all_deaths_pct == 1)].required_share_of_segment_deaths.iloc[0]):.1f}%,
limit-exceeding speeding {100 * float(req[(req.segment == "speeding_exceeded_limit") & (req.reduction_of_all_deaths_pct == 1)].required_share_of_segment_deaths.iloc[0]):.1f}%,
alcohol BAC>=.08 {100 * float(req[(req.segment == "alcohol") & (req.reduction_of_all_deaths_pct == 1)].required_share_of_segment_deaths.iloc[0]):.1f}%).
Ten-percent reductions of all deaths would require preventing more than the whole segment
for: {", ".join(sorted(req[(req.reduction_of_all_deaths_pct == 10) & ~req.feasible_through_segment_alone].segment)) or "none"}.
`threshold_breakeven_grid.csv` gives the required share for any break-even requirement R
(= equivalent annual cost / cost-effectiveness threshold, both user-supplied).

### Conditional on the empirical estimates (still hypothetical) -- `threshold_conditional_on_empirical_estimates.csv`

If the Layer-A estimates were causal effects of the behaviour change (belt estimate given a
fatal crash; severity pathway only, `1 - 1/RR`, no crash-occurrence effect), the change needed
per 1% of all deaths would be:

| Segment | Empirical input | Input value | Required change |
|---|---|---|---|
{chr(10).join(cond_lines)}

The belt rows show how strongly the answer depends on survivor misreporting of belt use
(matched module sensitivity rows): with 10-20% misreporting the required conversion rises
steeply. The speeding/alcohol rows ignore crash prevention (which would lower the requirement)
and treat a crash-conditional association as causal (which may overstate the severity effect).

## 4. Internal consistency checks (this run)

{chr(10).join(c for c in checks if c)}

## 5. Engine capabilities (tested in `tests/test_simulation.py`, `tests/test_costs.py`)

* Mechanisms: `SpeedEnforcement` (units -> coverage -> response -> occurrence/severity),
  `ImpairedDrivingEnforcement` (checks -> coverage x detection -> deterrence elasticity),
  `RestraintEnforcement` (conversion x belt effectiveness, default from Layer A),
  `GenericIntervention`. Coverage: `LinearCappedCoverage`, `SaturatingCoverage`;
  `coverage_doubling_demo.csv` shows (dimensionless) that doubling units gives at most, and
  usually well under, double coverage.
* Outcomes: `evaluate`, `project` (ramp-up/decay), `combine` (overlap-aware), `tornado`,
  `corner_range`, `monte_carlo` (seed {config.RANDOM_SEED}), `solve_scenario_parameter`.
* Costs: capital recovery factor, PV with renewals, equivalent annual cost, cost per death /
  KA prevented, incremental (marginal) cost-effectiveness with dominance, break-even deaths,
  break-even effectiveness parameter (solved through the engine), equal-budget indifference
  curves. All prices are required inputs; no value of a statistical life is assumed.

Worked examples with invented, clearly labelled inputs (cameras, alcohol checks, their
combination, costs in abstract currency units, break-even and equal-budget indifference, belt
enforcement) are in `docs/policy_assumptions.md` section 9; they are not results.

## 6. Limitations and alternative explanations

* Static baseline: projections hold the {span} mean fixed; secular trends (FARS deaths
  peaked in 2021, `descriptive/fars_annual.csv`) are not modelled.
* Segment counts rely on police coding; behaviours are ascertained more thoroughly in fatal
  crashes, and unknown-status deaths are excluded (lower bounds). Police may also attribute
  "speeding" after the fact in severe crashes, which would push the other way; the net bias of
  the segment counts is unknown.
* Segment shares are not "preventable fractions": a death in a speeding-related crash might
  have occurred without speeding, and deaths overlap across segments (section 2).
* The FARS alcohol segment is an expectation over NHTSA's imputation model.
* Adjusted RRs are associations conditional on a crash: their use as severity effects is an
  explicit, labelled assumption; they say nothing about crash occurrence.
* The belt estimate is conditional on a fatal crash and sensitive to misreporting.
* Monte Carlo reflects assumption uncertainty only (independent parameter draws).
* Nothing here identifies the effect of any intervention.
"""
    path = config.TABLES_DIR / MODULE / "SUMMARY.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return str(path)
