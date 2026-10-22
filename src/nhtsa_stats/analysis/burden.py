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


def _af_rows(model, df, design, shifts, outcome, fars_deaths, fars_crashes) -> list[dict]:
    base_m, base_z = model.margin_influence(df, None)
    rows = []
    for sh in shifts:
        if sh.name == "speeding_and_alcohol_removed":
            s1, s2 = SHIFTS[0].setter(), SHIFTS[1].setter()

            def setter(d, s1=s1, s2=s2):
                return s2(s1(d))
        else:
            setter = sh.setter()
        m, z = model.margin_influence(df, setter)
        ms = MarginSet({"obs": base_m, "cf": m}, {"obs": base_z, "cf": z}, design)
        af = ms.contrast(lambda v: (v["obs"] - v["cf"]) / v["obs"])
        lo, hi = af.ci()
        exposed = df[sh.var].isin(sh.exposed).to_numpy()
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
                "fars_scaled_deaths_per_year": af.estimate * fars_deaths,
                "fars_scaled_deaths_low": lo * fars_deaths,
                "fars_scaled_deaths_high": hi * fars_deaths,
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
                }
            )
    return pd.DataFrame(rows)


def run() -> dict[str, pd.DataFrame]:
    out = {"attributable_fractions_fatal": attributable_fractions("fatal")}
    out["attributable_fractions_ka"] = attributable_fractions("ka")
    out["bias_sensitivity"] = bias_sensitivity(out["attributable_fractions_fatal"])
    common = dict(
        population="CRSS police-reported crashes 2016-2024 (model); FARS deaths 2022-2024 (scaling)",
        unit="crash",
        inputs=["data/processed/crss_crash.parquet", "data/processed/fars_crash.parquet"],
        method="g-computation with survey logistic model A; AF = (observed - counterfactual predicted)/observed; "
        "linearised CI; FARS-scaled = AF x mean annual FARS deaths 2022-2024",
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
