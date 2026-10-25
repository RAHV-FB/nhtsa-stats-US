"""Phase 2: two-, three- and four-factor combinations at the correct observation level, and
"who dies" — the same driver behaviour against different victims."""

from __future__ import annotations

import streamlit as st

from common import BLUE, output_table, point_range


def render() -> None:
    st.title("Multiple-factor explorer")
    st.markdown(
        "Each analysis links factors to the unit they belong to: crash-level flags for crash outcomes, the "
        "driver's own behaviour for the driver's death, the driver of the vehicle for a passenger's death, and "
        "the striking driver for pedestrians. Risks are standardised (model-based, conditional on a reported "
        "crash); combinations with fewer than 30 sample units or 10 deaths are withheld. "
        "Report: `reports/multifactor_interactions.md`."
    )
    meta = output_table("multifactor", "analyses")
    margins = output_table("multifactor", "margins")
    inter = output_table("multifactor", "interactions")
    if meta is None or margins is None or inter is None:
        st.info("Run `uv run nhtsa analyze multifactor` first.")
        return
    labels = {r.analysis: f"[{r.level}] {r.analysis}" for r in meta.itertuples()}
    a = st.selectbox("Analysis", list(labels), format_func=labels.get, key="mf_analysis")
    m = meta.set_index("analysis").loc[a]
    st.markdown(
        f"**Population:** {m['population']} · **Outcome:** {m['outcome']} · **n** = {int(m['n']):,} "
        f"({int(m['n_events']):,} deaths) · {'registered' if m['registered'] else 'exploratory'}"
    )
    st.caption(f"Factors — {m['factors']}. Adjusted for: {m['covariates']}.")
    sub = margins[margins["analysis"] == a].copy()
    shown = sub[sub["flag"].isna() | (sub["flag"] == "")]
    if len(shown):
        st.altair_chart(
            point_range(
                shown,
                "adj_risk",
                "adj_risk_low",
                "adj_risk_high",
                "combination",
                color=BLUE,
                x_title="standardised risk of death",
                sort=list(shown["combination"]),
            ),
            width="stretch",
        )
    st.dataframe(
        sub[
            [
                "combination",
                "n",
                "n_events",
                "crude_rate",
                "adj_risk",
                "adj_risk_low",
                "adj_risk_high",
                "rr_vs_none",
                "rd_vs_none",
                "flag",
            ]
        ],
        hide_index=True,
    )
    st.subheader("Interaction contrasts")
    st.caption(
        "Additive contrast > 0: the combination produces more excess deaths than the single factors' excesses "
        "added up. Multiplicative ratio < 1: the combination's risk ratio is smaller than the product of the "
        "separate risk ratios. A combination can be super-additive and sub-multiplicative at the same time."
    )
    st.dataframe(
        inter[inter["analysis"] == a][
            [
                "contrast",
                "additive_contrast",
                "additive_contrast_low",
                "additive_contrast_high",
                "additive_contrast_p_holm",
                "multiplicative_ratio",
                "multiplicative_ratio_low",
                "multiplicative_ratio_high",
                "multiplicative_ratio_p_holm",
                "min_cell_events",
                "flag",
            ]
        ],
        hide_index=True,
    )
    vic = output_table("multifactor", "victims")
    if vic is not None:
        st.subheader("Driver versus occupant versus other road user")
        st.caption("The same recorded driver behaviour, related to the death of different people.")
        st.dataframe(
            vic[
                [
                    "victim",
                    "n",
                    "n_events",
                    "risk_neither",
                    "rr_speeding_only",
                    "rr_alcohol_only",
                    "rr_both",
                    "additive_contrast",
                    "multiplicative_ratio",
                ]
            ],
            hide_index=True,
        )
