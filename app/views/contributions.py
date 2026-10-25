"""Phase 2: what "contribution" means — association, adjustment, prediction, attribution and
counts side by side, with the evidence quality of each factor."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from common import BLUE, ORANGE, output_table, point_range

EVIDENCE = pd.DataFrame(
    [
        {
            "factor": "Exceeded limit / racing",
            "unit": "driver (crash flag = any driver)",
            "measurement": "police judgement after the crash",
            "quality": "observed, severity-dependent recording (FARS records more than CRSS)",
        },
        {
            "factor": "Too fast for conditions / unspecified",
            "unit": "driver",
            "measurement": "police judgement",
            "quality": "observed; concentrated on wet/icy roads",
        },
        {
            "factor": "Alcohol (CRSS)",
            "unit": "driver / crash",
            "measurement": "NHTSA single imputation of police report",
            "quality": "imputed; 2019 coding break; imputation may use severity",
        },
        {
            "factor": "Alcohol (FARS)",
            "unit": "driver",
            "measurement": "measured BAC (65% of killed, 23% of surviving drivers) + multiple imputation",
            "quality": "selectively measured, multiply imputed",
        },
        {
            "factor": "Drugs (CRSS)",
            "unit": "driver",
            "measurement": "police report only; 50-70% unknown after 2019",
            "quality": "substantially missing; not usable for severity",
        },
        {
            "factor": "Drugs (FARS)",
            "unit": "driver",
            "measurement": "toxicology (62% of killed, 19% of surviving drivers tested)",
            "quality": "selectively measured; presence, not impairment",
        },
        {
            "factor": "Restraint",
            "unit": "occupant",
            "measurement": "police report, largely survivors' statements",
            "quality": "observed; survivor over-reporting of belt use likely",
        },
    ]
)


def render() -> None:
    st.title("Factor contributions")
    st.markdown(
        "A factor can matter in several different senses. This page shows them **side by side and never "
        "combines them**: how strongly a factor is associated with a fatal outcome (crude and adjusted), "
        "how much predictive information it adds, how much of a modelled burden is statistically attributed "
        "to it, and how many deaths are *counted* under it. Report: `reports/factor_contributions.md`."
    )
    with st.expander("Why no single ranking of causes is possible", expanded=True):
        st.markdown(
            "* **Different questions, different answers.** Restraint changes who dies *given* a crash; "
            "alcohol and speeding are associated with how crashes happen and how violent they are. They act at "
            "different stages and on different units (occupant vs driver vs crash).\n"
            "* **Overlap.** Many deaths involve several factors. Factor-specific counts add up to more than the "
            "deaths they describe; attributable fractions are not additive.\n"
            "* **Statistical attribution is not causation.** A Shapley share is the average change in a model "
            "quantity when a factor is added; it depends on the factor set, the reference and the scale.\n"
            "* **Measurement.** Drug involvement is too selectively measured to be ranked at all."
        )
    st.subheader("Evidence quality of each factor")
    st.dataframe(EVIDENCE, hide_index=True, width="stretch")

    nested = output_table("contributions", "nested_models")
    if nested is not None:
        st.subheader("Crude vs adjusted association (fixed sample, crash level)")
        f = st.selectbox("Factor", sorted(nested["factor"].unique()), key="ct_factor")
        sub = nested[nested["factor"] == f]
        st.altair_chart(
            point_range(
                sub,
                "rr",
                "rr_low",
                "rr_high",
                "step",
                color=BLUE,
                log=True,
                ref=1.0,
                x_title="standardised risk ratio (fatal)",
                sort=list(sub["step"]),
            ),
            width="stretch",
        )
        st.caption(
            "Adjusted association, not causal. Odds ratios from the same models are shown in the table: they "
            "diverge from risk ratios as the outcome becomes common within cells (non-collapsibility)."
        )
        st.dataframe(
            sub[["step", "rr", "rr_low", "rr_high", "rd", "odds_ratio", "share_logrr_retained"]],
            hide_index=True,
        )

    pred = output_table("contributions", "predictive")
    if pred is not None:
        st.subheader("Predictive information (train 2016-2021, test 2023-2024)")
        st.altair_chart(
            point_range(
                pred,
                "shapley_r2",
                "shapley_r2_low",
                "shapley_r2_high",
                "block",
                color=ORANGE,
                x_title="Shapley share of test pseudo-R² (log-likelihood gain)",
            ),
            width="stretch",
        )
        st.caption(
            "Predictive importance only. A block that carries information already present in another block gets "
            "little credit when removed, and Shapley values split shared information evenly."
        )
        st.dataframe(
            pred[
                [
                    "block",
                    "r2_alone",
                    "r2_drop_when_removed",
                    "shapley_r2",
                    "shapley_share",
                    "auc_alone",
                    "logloss_increase",
                ]
            ],
            hide_index=True,
        )

    burden = output_table("contributions", "burden_shapley")
    if burden is not None:
        st.subheader(
            "Statistical attribution of the fatal-crash burden (severity pathway, model-based)"
        )
        st.dataframe(
            burden[
                [
                    "player_set",
                    "quantity",
                    "estimate",
                    "estimate_low",
                    "estimate_high",
                    "fars_deaths_per_year",
                ]
            ],
            hide_index=True,
        )
        st.caption(
            "Model-predicted under no unmeasured confounding and correct measurement; not lives saved by any intervention."
        )

    ov = output_table("contributions", "fars_overlap_summary")
    if ov is not None:
        st.subheader("How official-style counts overlap (FARS deaths 2016-2024, observed)")
        st.dataframe(
            ov[["factor", "deaths", "share_of_all_deaths", "share_also_involving_another_factor"]],
            hide_index=True,
        )

    rk = output_table("contributions", "ranking")
    rp = output_table("contributions", "rank_probabilities")
    if rk is not None:
        st.subheader("Each quantity ranks the factors differently")
        st.dataframe(rk, hide_index=True)
    if rp is not None:
        st.caption(
            "Probability of each rank (joint sampling distribution of the adjusted estimates)"
        )
        st.dataframe(rp, hide_index=True)
