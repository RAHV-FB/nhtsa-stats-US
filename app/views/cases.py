"""Phase 2: case-comparison explorer — what the records support about a combination of
factors, and what they cannot say about a particular death."""

from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from common import output_table

LEVELS = {
    "speeding": ["none", "exceeded_limit", "other_speeding"],
    "alcohol": ["no", "yes"],
    "unbelted": ["no", "yes"],
    "night": ["day", "night"],
    "single_vehicle": ["no", "yes"],
    "drugs": ["no", "yes"],
}
LABELS = {
    "speeding": "Driver speeding (police)",
    "alcohol": "Driver alcohol (imputed)",
    "unbelted": "Driver unbelted",
    "night": "Time",
    "single_vehicle": "Single-vehicle crash",
    "drugs": "Driver drugs (police, known-status subset)",
}


def _fmt(v: float, pct: bool = True) -> str:
    if v is None or not np.isfinite(v):
        return "—"
    return f"{100 * v:.2f}%" if pct else f"{v:.2f}"


def render() -> None:
    st.title("Case comparison")
    st.markdown(
        "Describe a case for the **driver of a light passenger vehicle**. The page shows how many comparable "
        "records exist, the observed and model-standardised probability that such a driver dies *given a "
        "police-reported crash*, and how that probability changes when each factor is absent. "
        "Report: `reports/case_comparisons.md`."
    )
    scen = output_table("cases", "scenarios")
    contr = output_table("cases", "scenario_contrasts")
    if scen is None or contr is None:
        st.info("Run `uv run nhtsa analyze cases` first.")
        return
    use_drugs = st.toggle(
        "Include police-reported drugs (restricts to drivers with known drug status)",
        key="cs_drugs",
    )
    model = "drug-known subset (police-reported drugs)" if use_drugs else "main (no drugs)"
    factors = [
        f for f in LEVELS if (f != "drugs" or use_drugs) and not (use_drugs and f == "night")
    ]
    cols = st.columns(len(factors))
    pick = {
        f: cols[i].selectbox(
            LABELS[f], LEVELS[f], index=len(LEVELS[f]) - 1 if f != "speeding" else 1, key=f"cs_{f}"
        )
        for i, f in enumerate(factors)
    }
    sub = scen[scen["model"] == model]
    for f, v in pick.items():
        sub = sub[sub[f].astype(str) == v]
    if sub.empty:
        st.warning("This combination is not on the pre-computed grid.")
        return
    r = sub.iloc[0]
    st.subheader("Evidence for this combination")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("CRSS sample drivers", f"{int(r['crss_n']):,}")
    c2.metric("…of whom died", f"{int(r['crss_deaths']):,}")
    c3.metric("Observed death rate (weighted)", _fmt(r["observed_rate"]))
    fk = r.get("fars_drivers_killed_per_year", np.nan)
    c4.metric(
        "FARS drivers killed per year with this combination",
        "—" if not np.isfinite(fk) else f"{fk:,.0f}",
    )
    if r["status"] != "supported":
        st.error(
            "Insufficient support (fewer than 30 sample drivers or 10 deaths with exactly this combination, or in "
            "the reference case). No model probability is shown: it would be an extrapolation."
        )
    else:
        st.metric(
            "Model-standardised probability the driver dies (adjusted association)",
            _fmt(r["model_risk"]),
            help=f"95% CI {_fmt(r['model_risk_low'])}–{_fmt(r['model_risk_high'])}; RR vs the case with none of the factors {r['rr_vs_reference']:.1f} ({r['rr_vs_reference_low']:.1f}–{r['rr_vs_reference_high']:.1f})",
        )
        st.caption(
            f"Mean model prediction for the drivers actually in this cell: {_fmt(r.get('predicted_in_cell', np.nan))} "
            f"(observed {_fmt(r['observed_rate'])}): the gap between these two is model misfit; the gap between "
            "the prediction in the cell and the standardised probability reflects the different road, time and "
            "driver mix of these crashes."
        )
        cc = contr[(contr["model"] == model) & (contr["scenario"] == r["scenario"])]
        if len(cc):
            st.subheader("What changes if one factor is absent (others held at the case values)")
            show = cc[
                [
                    "factor",
                    "risk_without_factor",
                    "rr_case_vs_without",
                    "rr_case_vs_without_low",
                    "rr_case_vs_without_high",
                ]
            ].copy()
            st.dataframe(show, hide_index=True)
            st.subheader("Allocations of the modelled risk difference are not unique")
            if not bool(cc["allocation_supported"].iloc[0]):
                st.warning(
                    "Some intermediate combinations needed for an allocation lack support, so no allocation is shown."
                )
            alloc = cc[
                [
                    "factor",
                    "shapley_share_risk_difference",
                    "shapley_share_log_rr",
                    "share_if_added_first",
                    "share_if_added_last",
                ]
            ]
            st.dataframe(alloc, hide_index=True)
            st.caption(
                "Shapley shares on the risk-difference scale and on the log-risk-ratio scale differ, and the share "
                "credited to a factor ranges from 'added first' to 'added last'. These are allocations of a model "
                "prediction, not the causes of anyone's death."
            )
    st.info(
        "**What cannot be inferred.** For a particular death these records cannot show which factor 'caused' it "
        "or in what proportion: the counterfactual outcome for that person is never observed, the factors are "
        "police-recorded after the crash, travel speed and crash forces are not measured, and the model "
        "describes averages over many crashes conditional on a crash having happened."
    )
    st.dataframe(pd.DataFrame([r]).T.rename(columns={r.name: "value"}), height=300)
