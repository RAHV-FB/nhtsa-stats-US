"""Model-based burden of fatal crashes associated with modifiable circumstances (RQ9).

Quantity: the *severity-pathway attributable fraction* (AF) of fatal crashes for a factor F,

    AF_F = [ sum_i w_i p_i  -  sum_i w_i p_i(F_i -> reference if F_i exposed) ] / sum_i w_i p_i

computed by g-computation from the survey-weighted logistic model A (PRE_CRASH set) over CRSS
crashes with known severity.  It is the share of fatal crashes that the model predicts would
*not* have been fatal had the exposed crashes instead had the reference level, holding every
other recorded circumstance fixed and assuming the crash still happened.

What it is not: it ignores the crash-occurrence pathway (removing speeding would also prevent
some crashes -- not identifiable here), it assumes no unmeasured confounding and correct
measurement (both doubtful for police-reported behaviours, see the measurement module), and it
is not an intervention effect.  Translating AF to deaths uses FARS observed deaths in the same
window (FARS-scaled = AF x FARS deaths), which assumes the CRSS-model fraction applies to the
FARS census; this is labelled *model-predicted, severity pathway only*.

Bias sensitivity: for speeding and alcohol the AF is recomputed after shrinking the adjusted
log risk ratio by the bias factors of the measurement module's QBA for chosen sensitivity
scenarios (approximation: AF_b = AF computed with RR_b = RR x bias factor, via the
exposed-crash formula AF = P(E|fatal) x (1 - 1/RR)).
"""

from __future__ import annotations

import dataclasses
import logging
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
import pandas as pd

from nhtsa_stats.analysis import data, severity, specs
from nhtsa_stats.analysis.survey import MarginSet
from nhtsa_stats.reporting.io import load_table as load_output
from nhtsa_stats.reporting.io import save_table

log = logging.getLogger(__name__)
MODULE = "burden"
WINDOW = (2022, 2023, 2024)


@dataclass(frozen=True)
class Shift:
    name: str
    var: str
    exposed: tuple
    target: str
    description: str
    modifiable: bool = True

    def setter(self) -> Callable[[pd.DataFrame], pd.DataFrame]:
        def f(d: pd.DataFrame) -> pd.DataFrame:
            return d.assign(
                **{self.var: np.where(d[self.var].isin(self.exposed), self.target, d[self.var])}
            )

        return f


SHIFTS = [
    Shift(
        "speeding_removed",
        "speeding",
        ("yes",),
        "no",
        "Speeding-related crashes as if not speeding-related",
    ),
    Shift(
        "alcohol_removed",
        "alcohol_im",
        ("yes",),
        "no",
        "Alcohol-involved crashes as if alcohol-free",
    ),
    Shift(
        "unlit_to_lit",
        "light",
        ("dark_not_lighted",),
        "dark_lighted",
        "Crashes in dark, unlit conditions as if the road were lit",
    ),
    Shift(
        "high_speed_roads_to_40_45",
        "speed_limit",
        ("50-55", "60-65", "70+"),
        "40-45",
        "Crashes on 50+ mph roads as if on 40-45 mph roads (speed-environment contrast)",
    ),
    Shift(
        "speeding_and_alcohol_removed",
        "speeding",
        ("yes",),
        "no",
        "Both speeding and alcohol removed (joint)",
    ),
]


TYPE_SHIFTS = [
    Shift(
        "exceeded_limit_removed",
        "speeding_type",
        ("exceeded_limit_or_racing",),
        "no",
        "Crashes with a driver exceeding the limit / racing as if not speeding-related (model with speeding type)",
    ),
    Shift(
        "too_fast_for_conditions_removed",
        "speeding_type",
        ("too_fast_for_conditions",),
        "no",
        "'Too fast for conditions' crashes as if not speeding-related (model with speeding type)",
    ),
]


def _af_rows(
    model,
    df,
    design,
    shifts,
    outcome,
    fars_deaths,
    fars_crashes,
    joint=(SHIFTS[0], SHIFTS[1]),
    scale_to_fars=True,
) -> list[dict]:
    base_m, base_z = model.margin_influence(df, None)
    rows = []
    for sh in shifts:
        if sh.name == "speeding_and_alcohol_removed":
            s1, s2 = joint[0].setter(), joint[1].setter()

            def setter(d, s1=s1, s2=s2):
                return s2(s1(d))
        else:
            setter = sh.setter()
        m, z = model.margin_influence(df, setter)
        ms = MarginSet({"obs": base_m, "cf": m}, {"obs": base_z, "cf": z}, design)
        af = ms.contrast(lambda v: (v["obs"] - v["cf"]) / v["obs"])
        lo, hi = af.ci()
        exposed = df[sh.var].isin(sh.exposed).to_numpy()
        if sh.name == "speeding_and_alcohol_removed":
            exposed = exposed | df[joint[1].var].isin(joint[1].exposed).to_numpy()
        # Only a fraction of *fatal* crashes can be scaled to FARS. Deaths assume the averted
        # fatal crashes carry the average number of deaths per FARS fatal crash.
        scale = outcome == "fatal" and scale_to_fars
        rows.append(
            {
                "shift": sh.name,
                "description": sh.description,
                "outcome": outcome,
                "n_exposed_crss": int(exposed.sum()),
                "af": af.estimate,
                "af_low": lo,
                "af_high": hi,
                "fars_deaths_per_year_window": fars_deaths,
                "fars_fatal_crashes_per_year_window": fars_crashes,
                "fars_scaled_fatal_crashes_per_year": af.estimate * fars_crashes
                if scale
                else np.nan,
                "fars_scaled_deaths_per_year": af.estimate * fars_deaths if scale else np.nan,
                "fars_scaled_deaths_low": lo * fars_deaths if scale else np.nan,
                "fars_scaled_deaths_high": hi * fars_deaths if scale else np.nan,
                "kind": "model-predicted (severity pathway only; no unmeasured confounding assumed)",
            }
        )
        log.info("AF %s = %.3f", sh.name, af.estimate)
    return rows


def attributable_fractions(outcome: str = "fatal") -> pd.DataFrame:
    df, design = severity.load(outcome)
    fars = data.fars_crash(WINDOW)
    fars_deaths = float(fars["FATALS"].sum()) / len(WINDOW)
    fars_crashes = len(fars) / len(WINDOW)
    model = severity.fit(df, design, outcome, specs.PRE_CRASH)
    rows = _af_rows(model, df, design, SHIFTS, outcome, fars_deaths, fars_crashes)
    df["speeding_type"] = df["speeding_type"].fillna("unknown")
    covs = [c if c != "speeding" else "speeding_type" for c in specs.PRE_CRASH]
    model_t = severity.fit(df, design, outcome, covs)
    rows += _af_rows(model_t, df, design, TYPE_SHIFTS, outcome, fars_deaths, fars_crashes)
    return pd.DataFrame(rows)


ALCOHOL_CODINGS = {
    "imputed": "NHTSA-imputed alcohol (ALCHL_IM), as published",
    "police_unknown_level": "police-reported alcohol, unknown kept as its own level",
    "police_complete_case": "police-reported alcohol, crashes with unknown alcohol dropped",
    "police_unknown_as_no": "police-reported alcohol, unknown counted as no alcohol",
}
PERIODS = {"2016-2024": None, "2022-2024": WINDOW}


def scaling_note(outcome: str, scaled: bool) -> str:
    """Why the FARS-scaled columns are filled or blank for a variant row."""
    if outcome != "fatal":
        return "not scaled: fractions of KA crashes are not scaled to FARS deaths"
    if not scaled:
        return (
            "not scaled: the fraction applies only to crashes with a known police alcohol field "
            "and is not extrapolated to all FARS deaths"
        )
    return "scaled to mean annual 2022-2024 FARS fatal crashes and deaths"


def af_variants(outcome: str = "fatal") -> pd.DataFrame:
    """Attributable fractions under other defensible periods and alcohol codings.

    The published fractions come from a model fitted to CRSS 2016-2024 with NHTSA-imputed
    alcohol and are scaled to 2022-24 FARS deaths.  Here the same g-computation (model A, same
    shifts) is repeated (i) on 2022-24 crashes only, the window the deaths refer to, and (ii) with
    police-reported alcohol instead of the imputed variable (unknown kept as a level, dropped, or
    counted as no).  The first row (2016-2024, imputed) reproduces the published table.
    Intervals are sampling-only and the variants are not independent of each other.
    """
    fars = data.fars_crash(WINDOW)
    fars_deaths = float(fars["FATALS"].sum()) / len(WINDOW)
    fars_crashes = len(fars) / len(WINDOW)
    rows = []
    for coding in ALCOHOL_CODINGS:
        for period, years in PERIODS.items():
            df, design = severity.load(outcome, years)
            var = "alcohol_im" if coding == "imputed" else "alcohol"
            if coding == "police_complete_case":
                keep = (df["alcohol"] != "unknown").to_numpy()
                df, design = df.loc[keep].reset_index(drop=True), design.subset(keep)
            elif coding == "police_unknown_as_no":
                df["alcohol"] = df["alcohol"].replace({"unknown": "no"})
            covs = [var if c == "alcohol_im" else c for c in specs.PRE_CRASH]
            shifts = [
                dataclasses.replace(sh, var=var) if sh.var == "alcohol_im" else sh for sh in SHIFTS
            ]
            joint = (shifts[0], shifts[1])
            model = severity.fit(df, design, outcome, covs)
            # The complete-case fraction describes only crashes with a known police alcohol
            # field; applying it to all FARS deaths would extrapolate to the dropped crashes.
            scale = coding != "police_complete_case"
            part = pd.DataFrame(
                _af_rows(
                    model, df, design, shifts, outcome, fars_deaths, fars_crashes, joint, scale
                )
            )
            part["fars_scaling_note"] = scaling_note(outcome, scale)
            part.insert(0, "alcohol_coding", coding)
            part.insert(1, "alcohol_coding_description", ALCOHOL_CODINGS[coding])
            part.insert(2, "model_period", period)
            part["n_crashes_model"] = len(df)
            part["n_events_model"] = int(df[outcome].sum())
            rows.append(part)
            log.info("AF variant %s %s %s done", outcome, coding, period)
    return pd.concat(rows, ignore_index=True)


def bias_sensitivity(af: pd.DataFrame) -> pd.DataFrame:
    """Recompute speeding/alcohol AFs with QBA-shrunk risk ratios."""
    try:
        qba = load_output("measurement", "qba_grid")
        adj = load_output("severity", "fatal_crude_vs_adjusted")
    except FileNotFoundError:
        log.warning("measurement/severity outputs missing; skipping bias sensitivity")
        return pd.DataFrame()
    rows = []
    for shift, var, level in (
        ("speeding_removed", "speeding", "yes"),
        ("alcohol_removed", "alcohol_im", "yes"),
    ):
        r = adj[(adj["factor"] == var) & (adj["level"].astype(str) == level)].iloc[0]
        rr = float(r["A_adj_rr"])
        base = af[af["shift"] == shift].iloc[0]
        # P(E | fatal) recovered from the base AF and RR: AF = pE_fatal * (1 - 1/RR)
        pe_fatal = base["af"] / (1 - 1 / rr)
        for _, q in qba[(qba["exposure"] == var) & (qba["specificity"] == 1.0)].iterrows():
            rr_b = rr * q["bias_factor"] if np.isfinite(q["bias_factor"]) else np.nan
            af_b = pe_fatal * (1 - 1 / rr_b) if np.isfinite(rr_b) and rr_b > 0 else np.nan
            rows.append(
                {
                    "shift": shift,
                    "se_fatal": q["se_fatal"],
                    "se_nonfatal": q["se_nonfatal"],
                    "adj_rr": rr,
                    "bias_factor": q["bias_factor"],
                    "adj_rr_bias_corrected": rr_b,
                    "af_bias_corrected": af_b,
                    "fars_scaled_deaths_per_year": af_b * base["fars_deaths_per_year_window"]
                    if np.isfinite(af_b)
                    else np.nan,
                    "note": "bias-corrected RR below 1: no excess severity, fraction negative"
                    if np.isfinite(af_b) and af_b < 0
                    else "",
                }
            )
    return pd.DataFrame(rows)


def run() -> dict[str, pd.DataFrame]:
    out = {"attributable_fractions_fatal": attributable_fractions("fatal")}
    out["attributable_fractions_ka"] = attributable_fractions("ka")
    out["bias_sensitivity"] = bias_sensitivity(out["attributable_fractions_fatal"])
    out["attributable_fraction_variants"] = pd.concat(
        [af_variants("fatal"), af_variants("ka")], ignore_index=True
    )
    common = dict(
        population="CRSS police-reported crashes 2016-2024 (model); FARS deaths 2022-2024 (scaling)",
        unit="crash",
        inputs=["data/processed/crss_crash.parquet", "data/processed/fars_crash.parquet"],
        method="g-computation with survey logistic model A; AF = (observed - counterfactual predicted)/observed; "
        "linearised CI; for the fatal outcome only, FARS-scaled = AF x mean annual FARS fatal crashes (or deaths) "
        "2022-2024, assuming the averted fatal crashes carry the average number of deaths per fatal crash; "
        "fractions of KA crashes are not scaled",
    )
    save_table(
        out["attributable_fractions_fatal"],
        MODULE,
        "attributable_fractions_fatal",
        description="Severity-pathway attributable fractions of fatal crashes for modifiable circumstances",
        outcome="fatal",
        **common,
    )
    save_table(
        out["attributable_fractions_ka"],
        MODULE,
        "attributable_fractions_ka",
        description="Severity-pathway attributable fractions of KA crashes",
        outcome="ka",
        **common,
    )
    save_table(
        out["attributable_fraction_variants"],
        MODULE,
        "attributable_fraction_variants",
        description="Attributable fractions refitted on 2022-2024 only and with police-reported "
        "alcohol (three codings), next to the published 2016-2024 imputed-alcohol fractions",
        outcome="fatal; ka",
        **{
            **common,
            "method": common["method"] + "; variants: model period 2016-2024 or 2022-2024, alcohol "
            "NHTSA-imputed or police-reported (unknown as a level, dropped, or as no); deaths "
            "scaling always uses the 2022-2024 FARS means; intervals cover sampling only",
        },
    )
    if len(out["bias_sensitivity"]):
        save_table(
            out["bias_sensitivity"],
            MODULE,
            "bias_sensitivity",
            description="Attributable fractions after QBA bias factors for differential ascertainment",
            outcome="fatal",
            **common,
        )
    return out
