"""Multi-factor combinations at the correct observation level (Phase 2, Q4a, Q5, Q6;
docs/research_plan_phase2.md §5.3).

Every analysis states its unit and links each factor to the unit it belongs to:

* crash level  -- "any driver" behaviour flags, outcome: the crash is fatal;
* driver level -- the driver's *own* recorded speeding, alcohol and drugs, the driver's own
  belt use; outcomes: the crash is fatal (single-vehicle crashes, where the driver's behaviour
  is the only driver behaviour) or the driver dies;
* passenger level -- the behaviour of the driver *of the passenger's vehicle* and the
  passenger's own belt use; outcome: the passenger dies;
* other road users -- occupants of the other vehicle in two-vehicle crashes and pedestrians,
  linked to the driver of the vehicle that struck them (``crss_person_link``).

Factors enter via ``analysis.factorial`` (full 2^k standardised margins from a model saturated
in the factors, adjusted for pre-crash circumstances).  Cells with fewer than 30 sample units
or 10 events are withheld.

Registered family (Holm-adjusted within each scale across all interaction contrasts of the
six registered analyses): crash exceeded x alcohol; crash speeding x alcohol x night; single-
vehicle driver exceeded x alcohol; light-vehicle driver speeding x alcohol x unbelted;
passenger: driver speeding x driver alcohol x own unbelted; light-vehicle driver with known
police drug status: speeding x alcohol x drugs x unbelted.  Everything else is exploratory.

What the analyses can show: whether the excess risk of a combination exceeds (additive
interaction) or differs in ratio from (multiplicative interaction) what the single factors
imply, conditional on a reported crash and the recorded covariates.  What they cannot show:
causal synergy, or effects on whether the crash happens.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd
import polars as pl
from scipy import stats

from nhtsa_stats import config
from nhtsa_stats.analysis import confounding as cf
from nhtsa_stats.analysis import data, factorial, specs
from nhtsa_stats.analysis import speeding as sp
from nhtsa_stats.analysis.factorial import Factor
from nhtsa_stats.analysis.survey import MarginSet, SurveyDesign
from nhtsa_stats.processing.harmonize import LPV_BODY_GROUPS
from nhtsa_stats.reporting.io import save_table

log = logging.getLogger(__name__)
MODULE = "multifactor"
INPUT = [
    "data/processed/crss_crash.parquet",
    "data/processed/crss_driver.parquet",
    "data/processed/crss_person.parquet",
    "data/processed/crss_person_link.parquet",
]
UNK = "unknown"

# Crash-environment covariates (model A without the behaviours and the driver/vehicle mix,
# which are replaced by unit-specific person and vehicle covariates where appropriate).
ENV = [
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
]
MIX = ["young_driver", "older_driver", "any_motorcycle", "any_heavy_truck"]


# --------------------------------------------------------------------------------------
# Frames
# --------------------------------------------------------------------------------------
def _fill(df: pd.DataFrame, cols: Sequence[str]) -> pd.DataFrame:
    """Categorical labels without missing values: 0/1 indicators -> no/yes, YEAR -> string,
    missing -> 'unknown'."""
    for c in cols:
        if c not in df:
            continue
        s = df[c]
        if c == "YEAR":
            df[c] = s.astype(int).astype(str)
            continue
        if s.dtype.kind in "biuf":
            s = s.map({1: "yes", 0: "no"})
        df[c] = s.astype(object).where(s.notna(), UNK).astype(str)
    return df


def three_level_speeding(s: pd.Series) -> pd.Series:
    s = s.astype(str)
    return pd.Series(
        np.select(
            [
                s == "no",
                s.isin(
                    ["exceeded_limit_or_racing", "too_fast_for_conditions", "speeding_unspecified"]
                ),
            ],
            ["no", "yes"],
            UNK,
        ),
        index=s.index,
    )


def exceeded_levels(s: pd.Series) -> pd.Series:
    s = s.astype(str)
    return pd.Series(
        np.select(
            [
                s == "no",
                s == "exceeded_limit_or_racing",
                s.isin(["too_fast_for_conditions", "speeding_unspecified"]),
            ],
            ["no", "yes", "other_speeding"],
            UNK,
        ),
        index=s.index,
    )


def crash_frame() -> tuple[pd.DataFrame, SurveyDesign]:
    df, design = data.crss_crash(outcome="fatal", tri_state_cols=specs.CRASH_TRI)
    df["fatal"] = df["fatal"].astype(float)
    df["ka"] = df["ka"].astype(float)
    df["exceeded"] = exceeded_levels(df["speeding_type"])
    df["night_period"] = df["night"].map({1: "night", 0: "day"}).fillna(UNK)
    df = _fill(df, [*ENV, *MIX, "speeding", "alcohol_im", "alcohol", "drugs"])
    return df, design


DRIVER_COLS = [
    "YEAR",
    "case_id",
    "VEH_NO",
    "WEIGHT",
    "PSUSTRAT",
    "PSU_VAR",
    *ENV,
    "night",
    "n_vehicles",
    "crash_type",
    "body",
    "own_speeding_type",
    "own_alcohol_im",
    "own_alcohol_police",
    "own_drugs_police",
    "other_speeding",
    "other_alcohol_im",
    "drv_age_band_im",
    "drv_sex",
    "drv_restraint",
    "drv_killed",
    "drv_killed_or_serious",
    "has_driver_record",
    "hit_and_run",
    "fatal",
]


def driver_frame() -> tuple[pd.DataFrame, SurveyDesign]:
    """CRSS driver file with labelled factors.  The design is built from every vehicle row
    (all PSUs kept) and subset by the callers' masks."""
    df = pl.read_parquet(
        config.PROCESSED_DIR / "crss_driver.parquet", columns=list(dict.fromkeys(DRIVER_COLS))
    ).to_pandas()
    design = SurveyDesign.from_frame(df)
    df["own_speeding"] = three_level_speeding(df["own_speeding_type"])
    df["own_exceeded"] = exceeded_levels(df["own_speeding_type"])
    df["night_period"] = df["night"].map({1: "night", 0: "day"}).fillna(UNK)
    df["unbelted"] = df["drv_restraint"].map({"belted": "no", "none": "yes"}).fillna(UNK)
    df["age"] = df["drv_age_band_im"]
    df["sex"] = df["drv_sex"]
    df = _fill(df, [*ENV, "age", "sex", "body", "n_vehicles", "crash_type"])
    return df, design


def person_frame() -> tuple[pd.DataFrame, SurveyDesign]:
    """CRSS persons with (i) the own vehicle's driver behaviour and (ii) the striking vehicle's
    driver behaviour for non-motorists, from ``crss_person_link``."""
    cols = [
        "YEAR",
        "case_id",
        "VEH_NO",
        "PER_NO",
        "PER_TYP",
        "WEIGHT",
        "PSUSTRAT",
        "PSU_VAR",
        "killed",
        "age_band",
        "sex",
        "role",
        "restraint",
        "body",
        *ENV,
        "night",
        "n_vehicles",
        "crash_type",
    ]
    p = pl.read_parquet(
        config.PROCESSED_DIR / "crss_person.parquet", columns=list(dict.fromkeys(cols))
    )
    link = pl.read_parquet(config.PROCESSED_DIR / "crss_person_link.parquet").select(
        ["YEAR", "case_id", "VEH_NO", "PER_NO", "relation", "linked_veh_no"]
    )
    drv = pl.read_parquet(
        config.PROCESSED_DIR / "crss_driver.parquet",
        columns=[
            "YEAR",
            "case_id",
            "VEH_NO",
            "own_speeding_type",
            "own_alcohol_im",
            "own_drugs_police",
            "other_speeding",
            "other_alcohol_im",
            "drv_restraint",
            "body",
            "n_other_vehicles",
        ],
    ).rename(
        {
            "VEH_NO": "linked_veh_no",
            "own_speeding_type": "lnk_speeding_type",
            "own_alcohol_im": "lnk_alcohol_im",
            "own_drugs_police": "lnk_drugs_police",
            "other_speeding": "lnk_other_speeding",
            "other_alcohol_im": "lnk_other_alcohol_im",
            "drv_restraint": "lnk_driver_restraint",
            "body": "lnk_body",
            "n_other_vehicles": "lnk_n_other_vehicles",
        }
    )
    p = p.join(link, on=["YEAR", "case_id", "VEH_NO", "PER_NO"], how="left", validate="1:1")
    p = p.join(drv, on=["YEAR", "case_id", "linked_veh_no"], how="left", validate="m:1")
    df = p.to_pandas()
    design = SurveyDesign.from_frame(df)
    df["killed"] = df["killed"].astype(float)
    df["lnk_speeding"] = three_level_speeding(df["lnk_speeding_type"].fillna(UNK))
    df["lnk_exceeded"] = exceeded_levels(df["lnk_speeding_type"].fillna(UNK))
    df["unbelted"] = df["restraint"].map({"belted": "no", "none": "yes"}).fillna(UNK)
    df = _fill(
        df,
        [
            *ENV,
            "age_band",
            "sex",
            "role",
            "body",
            "lnk_body",
            "lnk_alcohol_im",
            "lnk_drugs_police",
            "n_vehicles",
            "crash_type",
        ],
    )
    return df, design


# --------------------------------------------------------------------------------------
# Analysis specifications
# --------------------------------------------------------------------------------------
SPEED_ANY = Factor("speeding", "speeding", ("yes",), ("no",), "speeding recorded (any type)")
ALC = Factor("alcohol", "alcohol_im", ("yes",), ("no",), "alcohol involved (imputed)")
EXCEEDED = Factor("exceeded", "exceeded", ("yes",), ("no",), "exceeded limit / racing")
NIGHT = Factor("night", "night_period", ("night",), ("day",), "night 21:00-05:59")
OWN_SPEED = Factor(
    "speeding", "own_speeding", ("yes",), ("no",), "driver's own speeding (any type)"
)
OWN_EXCEEDED = Factor(
    "exceeded", "own_exceeded", ("yes",), ("no",), "driver exceeded limit / racing"
)
OWN_ALC = Factor("alcohol", "own_alcohol_im", ("yes",), ("no",), "driver alcohol (imputed)")
OWN_DRUGS = Factor("drugs", "own_drugs_police", ("yes",), ("no",), "driver drugs (police-reported)")
UNBELTED = Factor("unbelted", "unbelted", ("yes",), ("no",), "person unbelted (vs belted)")
LNK_SPEED = Factor(
    "driver_speeding", "lnk_speeding", ("yes",), ("no",), "the vehicle's driver speeding"
)
LNK_ALC = Factor(
    "driver_alcohol", "lnk_alcohol_im", ("yes",), ("no",), "the vehicle's driver alcohol (imputed)"
)


@dataclass
class Analysis:
    name: str
    level: str
    population: str
    outcome_label: str
    frame: str  # crash / driver / person
    select: Callable[[pd.DataFrame], np.ndarray]
    factors: list[Factor]
    covariates: list[str]
    outcome: str
    registered: bool
    rationale: str


def _lpv(body: pd.Series) -> np.ndarray:
    return body.isin(list(LPV_BODY_GROUPS)).to_numpy()


PERSON_COVS = ["age", "sex", "body"]


ANALYSES: list[Analysis] = [
    Analysis(
        "crash_exceeded_x_alcohol",
        "crash",
        "CRSS police-reported crashes",
        "crash fatal",
        "crash",
        lambda d: np.ones(len(d), bool),
        [EXCEEDED, ALC],
        [*ENV, *MIX],
        "fatal",
        True,
        "Is limit exceedance's excess severity different when alcohol is also involved?",
    ),
    Analysis(
        "crash_speeding_x_alcohol_x_night",
        "crash",
        "CRSS police-reported crashes (time known)",
        "crash fatal",
        "crash",
        lambda d: (d["night_period"] != UNK).to_numpy(),
        [SPEED_ANY, ALC, NIGHT],
        [c for c in [*ENV, *MIX] if c not in ("tod", "light")],
        "fatal",
        True,
        "Do the two behaviours combine differently at night? (time-of-day and light are "
        "part of what night means and are not adjusted for)",
    ),
    Analysis(
        "sv_driver_exceeded_x_alcohol",
        "driver",
        "Drivers in single-vehicle crashes (the only driver behaviour in the crash)",
        "crash fatal",
        "driver",
        lambda d: (
            (d["n_vehicles"] == "1") & (d["has_driver_record"] == 1) & d["fatal"].notna()
        ).to_numpy(),
        [OWN_EXCEEDED, OWN_ALC],
        [*ENV, *PERSON_COVS],
        "fatal",
        True,
        "Single-vehicle crashes give an unambiguous link between one driver's behaviour and "
        "the crash outcome",
    ),
    Analysis(
        "lpv_driver_speeding_x_alcohol_x_unbelted",
        "driver",
        "Drivers of light passenger vehicles (belt use belted, none or unknown)",
        "driver killed",
        "driver",
        lambda d: (
            _lpv(d["body"])
            & d["drv_restraint"].isin(["belted", "none", UNK]).to_numpy()
            & d["drv_killed"].notna().to_numpy()
        ),
        [OWN_SPEED, OWN_ALC, UNBELTED],
        [*ENV, *PERSON_COVS, "other_speeding", "other_alcohol_im"],
        "drv_killed",
        True,
        "All three factors belong to the same person: the driver's own behaviour and belt",
    ),
    Analysis(
        "passenger_driver_speeding_x_driver_alcohol_x_unbelted",
        "passenger",
        "Passengers of light passenger vehicles aged 15+ (belt use belted, none or unknown)",
        "passenger killed",
        "person",
        lambda d: (
            (d["relation"] == "passenger")
            & _lpv(d["body"])
            & d["restraint"].isin(["belted", "none", UNK]).to_numpy()
            & ~d["age_band"].isin(["0-14"]).to_numpy()
            & d["killed"].notna().to_numpy()
        ),
        [LNK_SPEED, LNK_ALC, UNBELTED],
        [*ENV, "age_band", "sex", "role", "body"],
        "killed",
        True,
        "The passenger bears the driver's behaviour but chooses only their own belt use",
    ),
    Analysis(
        "lpv_driver_drugs_known_4way",
        "driver",
        "Drivers of light passenger vehicles with known police drug status (a selected subset)",
        "driver killed",
        "driver",
        lambda d: (
            _lpv(d["body"])
            & d["drv_restraint"].isin(["belted", "none", UNK]).to_numpy()
            & d["drv_killed"].notna().to_numpy()
            & d["own_drugs_police"].isin(["yes", "no"]).to_numpy()
        ),
        [OWN_SPEED, OWN_ALC, OWN_DRUGS, UNBELTED],
        [*ENV, *PERSON_COVS, "other_speeding", "other_alcohol_im"],
        "drv_killed",
        True,
        "Four factors of one person; restricted to recorded drug status, which is itself "
        "selected (see the drugs module)",
    ),
    # ---- exploratory ----
    Analysis(
        "crash_exceeded_x_alcohol_ka",
        "crash",
        "CRSS police-reported crashes",
        "crash fatal or serious (KA)",
        "crash",
        lambda d: np.ones(len(d), bool),
        [EXCEEDED, ALC],
        [*ENV, *MIX],
        "ka",
        False,
        "KA outcome check",
    ),
    Analysis(
        "crash_exceeded_x_alcohol_police",
        "crash",
        "CRSS police-reported crashes (police alcohol coding; unknown kept as a level)",
        "crash fatal",
        "crash",
        lambda d: np.ones(len(d), bool),
        [EXCEEDED, Factor("alcohol", "alcohol", ("yes",), ("no",), "alcohol (police)")],
        [*ENV, *MIX],
        "fatal",
        False,
        "Alcohol coding check",
    ),
    Analysis(
        "lpv_driver_exceeded_x_alcohol_x_unbelted",
        "driver",
        "Drivers of light passenger vehicles",
        "driver killed",
        "driver",
        lambda d: (
            _lpv(d["body"])
            & d["drv_restraint"].isin(["belted", "none", UNK]).to_numpy()
            & d["drv_killed"].notna().to_numpy()
        ),
        [OWN_EXCEEDED, OWN_ALC, UNBELTED],
        [*ENV, *PERSON_COVS, "other_speeding", "other_alcohol_im"],
        "drv_killed",
        False,
        "Exceedance instead of any speeding",
    ),
    Analysis(
        "lpv_driver_speeding_x_alcohol_x_unbelted_config",
        "driver",
        "Drivers of light passenger vehicles",
        "driver killed",
        "driver",
        lambda d: (
            _lpv(d["body"])
            & d["drv_restraint"].isin(["belted", "none", UNK]).to_numpy()
            & d["drv_killed"].notna().to_numpy()
        ),
        [OWN_SPEED, OWN_ALC, UNBELTED],
        [*ENV, *PERSON_COVS, "other_speeding", "other_alcohol_im", "crash_type", "n_vehicles"],
        "drv_killed",
        False,
        "Adds crash configuration (a mediator of speeding and alcohol)",
    ),
]


# --------------------------------------------------------------------------------------
# Who dies?  The same driver behaviour against different victims
# --------------------------------------------------------------------------------------
@dataclass
class VictimSpec:
    name: str
    description: str
    frame: str
    select: Callable[[pd.DataFrame], np.ndarray]
    behaviour_cols: tuple[str, str]  # (speeding, alcohol) columns of the responsible driver
    covariates: list[str]
    outcome: str


VICTIMS: list[VictimSpec] = [
    VictimSpec(
        "crash fatal (any driver's behaviour)",
        "Crash level: anyone died; behaviour of any driver",
        "crash",
        lambda d: np.ones(len(d), bool),
        ("speeding", "alcohol_im"),
        [*ENV, *MIX],
        "fatal",
    ),
    VictimSpec(
        "driver killed (own behaviour)",
        "Drivers of light vehicles; their own speeding and alcohol",
        "driver",
        lambda d: _lpv(d["body"]) & d["drv_killed"].notna().to_numpy(),
        ("own_speeding", "own_alcohol_im"),
        [*ENV, *PERSON_COVS, "unbelted", "other_speeding", "other_alcohol_im"],
        "drv_killed",
    ),
    VictimSpec(
        "passenger killed (their driver's behaviour)",
        "Passengers aged 15+ of light vehicles; the driver of their vehicle",
        "person",
        lambda d: (
            (d["relation"] == "passenger")
            & _lpv(d["body"])
            & ~d["age_band"].isin(["0-14"]).to_numpy()
            & d["killed"].notna().to_numpy()
        ),
        ("lnk_speeding", "lnk_alcohol_im"),
        [*ENV, "age_band", "sex", "role", "body", "unbelted"],
        "killed",
    ),
    VictimSpec(
        "other-vehicle occupant killed (the other driver's behaviour)",
        "Occupants of light vehicles in two-vehicle crashes; the *other* vehicle's driver "
        "(own driver's behaviour adjusted)",
        "person",
        lambda d: (
            d["relation"].isin(["driver", "passenger"]).to_numpy()
            & _lpv(d["body"])
            & (d["lnk_n_other_vehicles"] == 1).to_numpy()
            & d["killed"].notna().to_numpy()
            & ~d["age_band"].isin(["0-14"]).to_numpy()
        ),
        ("oth_speeding", "oth_alcohol_im"),
        [*ENV, "age_band", "sex", "role", "body", "unbelted", "lnk_speeding", "lnk_alcohol_im"],
        "killed",
    ),
    VictimSpec(
        "pedestrian killed (striking driver's behaviour)",
        "Pedestrians struck by an in-transport vehicle; that vehicle's driver",
        "person",
        lambda d: (
            (d["PER_TYP"] == 5).to_numpy()
            & d["killed"].notna().to_numpy()
            & d["linked_veh_no"].notna().to_numpy()
        ),
        ("lnk_speeding", "lnk_alcohol_im"),
        [*ENV, "age_band", "sex", "lnk_body"],
        "killed",
    ),
]


def _other_vehicle_behaviour(df: pd.DataFrame) -> pd.DataFrame:
    """For occupants in two-vehicle crashes: the other vehicle's driver speeding and alcohol."""
    df["oth_speeding"] = df["lnk_other_speeding"].fillna(UNK).replace({"no_other_vehicle": UNK})
    df["oth_alcohol_im"] = df["lnk_other_alcohol_im"].fillna(UNK).replace({"no_other_vehicle": UNK})
    return df


def _victim_record(
    v: VictimSpec, df: pd.DataFrame, design: SurveyDesign, covariates: Sequence[str]
) -> dict:
    """One row of the victims table: the factorial speeding x alcohol model of ``v`` fitted with
    the given covariates."""
    mask = v.select(df)
    sub, sd = df.loc[mask].reset_index(drop=True), design.subset(mask)
    s_col, a_col = v.behaviour_cols
    factors = [
        Factor("speeding", s_col, ("yes",), ("no",)),
        Factor("alcohol", a_col, ("yes",), ("no",)),
    ]
    covs = [c for c in covariates if c not in (s_col, a_col)]
    res = factorial.fit_factorial(sub, sd, factors, covs, v.outcome)
    mt = factorial.margins_table(res).set_index("key")
    it = factorial.interaction_table(res).iloc[0]
    rec = {
        "victim": v.name,
        "population": v.description,
        "n": res.n_rows,
        "n_events": res.n_events,
        "risk_neither": mt.loc["00", "adj_risk"],
        "risk_neither_low": mt.loc["00", "adj_risk_low"],
        "risk_neither_high": mt.loc["00", "adj_risk_high"],
    }
    for key, lab in (("10", "speeding_only"), ("01", "alcohol_only"), ("11", "both")):
        rec[f"risk_{lab}"] = mt.loc[key, "adj_risk"]
        for c in ("rr_vs_none", "rd_vs_none"):
            rec[f"{c.split('_')[0]}_{lab}"] = mt.loc[key, c]
            rec[f"{c.split('_')[0]}_{lab}_low"] = mt.loc[key, f"{c}_low"]
            rec[f"{c.split('_')[0]}_{lab}_high"] = mt.loc[key, f"{c}_high"]
        rec[f"n_{lab}"] = int(mt.loc[key, "n"])
        rec[f"events_{lab}"] = int(mt.loc[key, "n_events"])
    rec.update(
        additive_contrast=it["additive_contrast"],
        additive_contrast_low=it["additive_contrast_low"],
        additive_contrast_high=it["additive_contrast_high"],
        multiplicative_ratio=it["multiplicative_ratio"],
        multiplicative_ratio_low=it["multiplicative_ratio_low"],
        multiplicative_ratio_high=it["multiplicative_ratio_high"],
        flag=it["flag"],
    )
    return rec


def victims_table(frames: dict) -> pd.DataFrame:
    rows = []
    for v in VICTIMS:
        df, design = frames[v.frame]
        rows.append(_victim_record(v, df, design, v.covariates))
        log.info("victims: %s done", v.name)
    return pd.DataFrame(rows)


# Covariates that exist and mean the same for every person-level unit (driver, passenger,
# other-vehicle occupant, pedestrian): the crash environment and the victim's own age band and
# sex.  Excluded because they are not defined for every unit or change meaning between units:
# the victim's belt use (none for pedestrians), vehicle body (the victim's vehicle, or the
# striking vehicle for pedestrians), seat role, the other driver's behaviour, and the driver /
# vehicle mix of the crash (a crash-level quantity).
COMMON_COVARIATES = [*ENV, "age_band", "sex"]
COMMON_CONFIG_COVARIATES = [*COMMON_COVARIATES, "crash_type", "n_vehicles"]


def victims_common_spec_table(frames: dict) -> pd.DataFrame:
    """Speeding and alcohol of the responsible driver against the four person-level victims
    under ONE adjustment specification for all units, next to the unit-specific specification
    of ``victims``.  The crash-level row is omitted (no victim covariates exist for a crash).

    Specifications:
    * ``unit-specific (published)`` -- the covariates of ``victims``, which differ by unit
      (belt use, body type, role, other driver's behaviour...);
    * ``common`` -- crash environment + victim age band + victim sex, identical for all units;
    * ``common + crash configuration`` -- the above plus crash type and number of vehicles
      (a possible mediator of both behaviours).
    Same populations, outcomes and estimator as ``victims``; only the covariates differ."""
    rows = []
    specs_ = [
        ("unit-specific (published)", None),
        ("common: environment + victim age band + sex", COMMON_COVARIATES),
        ("common + crash configuration", COMMON_CONFIG_COVARIATES),
    ]
    for v in VICTIMS[1:]:
        df, design = frames[v.frame]
        if "age_band" not in df:
            df = df.assign(age_band=df["age"])  # driver frame carries the band as ``age``
        for label, covs in specs_:
            use = v.covariates if covs is None else covs
            rec = _victim_record(v, df, design, use)
            rows.append(
                {
                    "specification": label,
                    "covariates": ",".join(c for c in use if c not in v.behaviour_cols),
                    **rec,
                }
            )
            log.info("victims common: %s / %s done", v.name, label)
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------------------
# Speeding within alcohol strata, with and without crash configuration
# --------------------------------------------------------------------------------------
def speeding_alcohol_strata_configuration(
    outcomes: Sequence[str] = ("fatal", "ka"),
) -> pd.DataFrame:
    """Adjusted RR of speeding exposures within strata of imputed alcohol, with and without
    crash configuration (crash type, number of vehicles) in the adjustment set.

    The ``speeding/strata`` rows (6.5 without alcohol vs 3.3 with alcohol for exceedance) use
    the environment blocks only.  This table refits the same stratified models with the
    configuration block added; the first specification reproduces the published rows
    (an internal check).  Crash configuration may be a mediator of speeding (speeding is
    more common in single-vehicle crashes), so neither specification is the 'true' one."""
    df, design = sp.load_frame()
    cd = cf.cluster_design(design)
    t = cd.tcrit()
    masks = sp.strata_definitions(df)["alcohol_imputed"][0]
    rows = []
    for outcome in outcomes:
        for ex_name in ("exceeded", "speeding_any"):
            ex = sp.EXPOSURES[ex_name]
            for spec_label, add_cfg in (
                ("published strata specification (no crash configuration)", False),
                ("+ crash configuration", True),
            ):
                blocks = [b for b in ex.blocks if b not in ("configuration", "alcohol")]
                if add_cfg:
                    blocks.append("configuration")
                fits, recs = {}, []
                for label, mask in masks.items():
                    sub, sd = df.loc[mask].reset_index(drop=True), design.subset(mask)
                    for c in sub.columns:
                        if isinstance(sub[c].dtype, pd.CategoricalDtype):
                            sub[c] = sub[c].cat.remove_unused_categories()
                    known = sub[outcome].notna()
                    exposed = (sub[ex.column].astype(str) == ex.exposed) & known
                    f = cf.fit_subset(sub, sd, ex, blocks, outcome)
                    fits[label] = f
                    ms = MarginSet({"lr": f.log_rr}, {"lr": f.t_log_rr}, cd)
                    lr, se = cf.linear_contrast(ms, {"lr": 1.0})
                    recs.append(
                        {
                            "exposure": ex_name,
                            "outcome": outcome,
                            "specification": spec_label,
                            "stratum": f"alcohol: {label}",
                            "n_crashes": int(known.sum()),
                            "n_exposed": int(exposed.sum()),
                            "n_exposed_events": int(sub.loc[exposed, outcome].sum()),
                            "adj_rate_exposed": f.m_exposed,
                            "adj_rate_reference": f.m_reference,
                            "rr": float(np.exp(lr)),
                            "rr_low": float(np.exp(lr - t * se)),
                            "rr_high": float(np.exp(lr + t * se)),
                            "rd": f.m_exposed - f.m_reference,
                            "blocks": cf.subset_key(blocks),
                            "ratio_alcohol_to_no_alcohol": np.nan,
                            "ratio_low": np.nan,
                            "ratio_high": np.nan,
                            "ratio_p": np.nan,
                        }
                    )
                fa_, fb = fits["no alcohol"], fits["alcohol"]
                ms = MarginSet(
                    {"a": fa_.log_rr, "b": fb.log_rr}, {"a": fa_.t_log_rr, "b": fb.t_log_rr}, cd
                )
                dd, se = cf.linear_contrast(ms, {"b": 1.0, "a": -1.0})
                recs[-1].update(
                    ratio_alcohol_to_no_alcohol=float(np.exp(dd)),
                    ratio_low=float(np.exp(dd - t * se)),
                    ratio_high=float(np.exp(dd + t * se)),
                    ratio_p=float(2 * stats.t.sf(abs(dd / se), cd.df)),
                )
                rows.extend(recs)
                log.info("strata+config %s/%s/%s done", outcome, ex_name, spec_label)
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------------------
def run_analyses(frames: dict) -> dict[str, pd.DataFrame]:
    margins, inter, singles, meta = [], [], [], []
    for a in ANALYSES:
        df, design = frames[a.frame]
        mask = a.select(df)
        sub, sd = df.loc[mask].reset_index(drop=True), design.subset(mask)
        res = factorial.fit_factorial(sub, sd, a.factors, a.covariates, a.outcome)
        for tab, sink in (
            (factorial.margins_table(res), margins),
            (factorial.interaction_table(res), inter),
            (factorial.single_factor_table(res), singles),
        ):
            tab.insert(0, "registered", a.registered)
            tab.insert(0, "level", a.level)
            tab.insert(0, "analysis", a.name)
            sink.append(tab)
        meta.append(
            {
                "analysis": a.name,
                "level": a.level,
                "registered": a.registered,
                "population": a.population,
                "outcome": a.outcome_label,
                "factors": "; ".join(f"{f.name}: {f.label}" for f in a.factors),
                "covariates": ",".join(a.covariates),
                "n": res.n_rows,
                "n_events": res.n_events,
                "share_of_frame": float(mask.mean()),
                "n_params": res.meta["n_params"],
                "converged": res.meta["converged"],
                "n_suppressed_cells": len(res.suppressed),
                "rationale": a.rationale,
            }
        )
        log.info("multifactor %s done (n=%d)", a.name, len(sub))
    inter_df = pd.concat(inter, ignore_index=True)
    reg = inter_df["registered"]
    for col in ("additive_contrast_p", "multiplicative_ratio_p"):
        inter_df[col + "_holm"] = np.nan
        inter_df.loc[reg, col + "_holm"] = factorial.holm(inter_df.loc[reg, col]).to_numpy()
    return {
        "margins": pd.concat(margins, ignore_index=True),
        "interactions": inter_df,
        "single_factor": pd.concat(singles, ignore_index=True),
        "analyses": pd.DataFrame(meta),
    }


def load_frames() -> dict[str, tuple[pd.DataFrame, SurveyDesign]]:
    crash = crash_frame()
    drv = driver_frame()
    per_df, per_design = person_frame()
    per_df = _other_vehicle_behaviour(per_df)
    return {"crash": crash, "driver": drv, "person": (per_df, per_design)}


def run() -> dict[str, pd.DataFrame]:
    frames = load_frames()
    out = run_analyses(frames)
    method = (
        "Survey logistic model with all factor main effects, a product for every combination "
        "of non-reference factor levels (unknown included), and categorical covariates; standardised margins for all 2^k "
        "combinations (g-computation over the analysis population); Taylor linearisation on "
        "25 strata / 67 PSUs (t, 42 df); cells with < 30 units or < 10 events withheld; Holm "
        "across the registered family per scale"
    )
    pop = "CRSS 2016-2024; unit and population per analysis (see multifactor/analyses)"
    save_table(
        out["analyses"],
        MODULE,
        "analyses",
        description="Specification, population and support of every factorial analysis",
        population=pop,
        unit="analysis",
        method=method,
        inputs=INPUT,
    )
    save_table(
        out["margins"],
        MODULE,
        "margins",
        description="Standardised risk of every factor combination, with observed support and crude rate",
        population=pop,
        unit="combination",
        outcome="per analysis",
        method=method,
        inputs=INPUT,
    )
    save_table(
        out["interactions"],
        MODULE,
        "interactions",
        description="Pairwise, three- and four-way additive and multiplicative interaction contrasts",
        population=pop,
        unit="contrast",
        outcome="per analysis",
        method=method,
        inputs=INPUT,
    )
    save_table(
        out["single_factor"],
        MODULE,
        "single_factor",
        description="RR and RD of each factor within each combination of the other factors",
        population=pop,
        unit="contrast",
        outcome="per analysis",
        method=method,
        inputs=INPUT,
    )
    vic = victims_table(frames)
    save_table(
        vic,
        MODULE,
        "victims",
        description="Speeding and alcohol of the responsible driver against different victims: crash, driver, passenger, other-vehicle occupant, pedestrian",
        population=pop,
        unit="per row",
        outcome="death of the person in each row",
        method=method,
        inputs=INPUT,
    )
    out["victims"] = vic
    vc = victims_common_spec_table(frames)
    save_table(
        vc,
        MODULE,
        "victims_common_spec",
        description="Responsible driver's speeding and alcohol against driver, passenger, other-vehicle occupant and pedestrian victims under the unit-specific specification and under one common adjustment specification (environment, victim age band, sex; and with crash configuration)",
        population=pop,
        unit="per row",
        outcome="death of the person in each row",
        method=method,
        inputs=INPUT,
    )
    out["victims_common_spec"] = vc
    sc = speeding_alcohol_strata_configuration()
    save_table(
        sc,
        MODULE,
        "speeding_alcohol_strata_configuration",
        description="Adjusted RR of limit exceedance (and any speeding) within strata of imputed alcohol with and without crash configuration in the adjustment set; the first specification reproduces speeding/strata",
        population="CRSS police-reported crashes 2016-2024 with known imputed severity",
        unit="crash",
        outcome="fatal; fatal or serious (KA)",
        method="Model-A-type survey logistic fits within alcohol strata (speeding.stratified_table specification), optionally plus crash type and number of vehicles; standardised RR; Taylor linearisation (42 df); ratio of the two strata RRs by joint linearisation",
        inputs=INPUT,
    )
    out["speeding_alcohol_strata_configuration"] = sc
    return out
