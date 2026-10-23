"""Section B: factor explorer - descriptive (live, filterable) and adjusted (pre-computed)."""

from __future__ import annotations

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from common import (
    BLUE,
    FACTOR_CHOICES,
    ORANGE,
    crss_crash,
    data_ready,
    filter_controls,
    fmt_pct,
    kind_note,
    output_table,
    point_range,
    rate_by_level,
)


def render() -> None:
    st.title("Factor explorer")
    st.markdown(
        "How often is a crash with a given characteristic fatal (or fatal/serious), and how does that change once "
        "other circumstances are taken into account? **Frequency is not danger**: a factor can be common in fatal "
        "crashes simply because it is common in all crashes."
    )
    if not data_ready():
        return
    df, design = crss_crash()
    c1, c2 = st.columns([2, 1])
    factor = c1.selectbox("Factor", list(FACTOR_CHOICES), format_func=FACTOR_CHOICES.get, index=0)
    outcome = c2.radio(
        "Outcome",
        ["fatal", "ka"],
        horizontal=True,
        format_func=lambda o: "Fatal (K)" if o == "fatal" else "Fatal or serious (KA)",
    )
    st.subheader("1 · Descriptive (CRSS, survey-weighted, filterable)")
    dom = filter_controls(df, "fx")
    tab = rate_by_level(df, design, factor, outcome, dom)
    if tab.empty:
        st.warning("No crashes in this selection.")
        return
    kind_note("estimated")
    shown = tab[~tab["flag"].str.startswith("suppressed")]
    if len(shown) < len(tab):
        st.warning(f"{len(tab) - len(shown)} level(s) suppressed (fewer than 30 sample crashes).")
    chart = point_range(
        shown.assign(
            rate_pct=100 * shown["rate"], low_pct=100 * shown["low"], high_pct=100 * shown["high"]
        ),
        "rate_pct",
        "low_pct",
        "high_pct",
        "level",
        color=BLUE,
        x_title=f"% of crashes that were {'fatal' if outcome == 'fatal' else 'fatal or serious'} (95% CI)",
        sort=list(shown["level"]),
    )
    st.altair_chart(chart, width="stretch")
    nice = tab.assign(
        share_of_crashes=tab["share_of_crashes"].map(fmt_pct),
        rate=tab["rate"].map(lambda v: fmt_pct(v, 3)),
        ci=[
            f"{fmt_pct(a, 3)} – {fmt_pct(b, 3)}"
            for a, b in zip(tab["low"], tab["high"], strict=True)
        ],
        crashes_per_year=tab["crashes_per_year"].round(-2).astype(int).astype(str),
    )[["level", "sample_n", "events", "crashes_per_year", "share_of_crashes", "rate", "ci", "flag"]]
    # Suppressed levels (< 30 sample crashes): counts only, no estimates.
    sup = tab["flag"].str.startswith("suppressed").to_numpy()
    nice.loc[sup, ["crashes_per_year", "share_of_crashes", "rate", "ci"]] = "—"
    st.dataframe(nice, hide_index=True, width="stretch")
    st.caption(
        "sample_n = unweighted CRSS crashes; crashes_per_year = weighted national estimate (police-reported); "
        "CIs from Taylor linearisation over 67 PSUs in 25 strata (t, 42 df)."
    )

    st.subheader("2 · Adjusted associations (pooled 2016-2024, not filterable)")
    kind_note("adjusted")
    adj = output_table("severity", f"{outcome}_crude_vs_adjusted")
    if adj is None:
        st.info("Run `nhtsa analyze severity` to produce adjusted estimates.")
        return
    a = adj[adj["factor"] == factor].copy()
    if a.empty:
        st.info("No adjusted estimates for this factor.")
        return
    a["level"] = a["level"].astype(str)
    long = []
    for key, name in (
        ("crude", "Crude"),
        ("A_adj", "Adjusted: pre-crash (A)"),
        ("B_adj", "Adjusted: + configuration (B)"),
    ):
        if f"{key}_rr" in a and a[f"{key}_rr"].notna().any():
            long.append(
                pd.DataFrame(
                    {
                        "level": a["level"],
                        "model": name,
                        "rr": a[f"{key}_rr"],
                        "low": a[f"{key}_rr_low"],
                        "high": a[f"{key}_rr_high"],
                    }
                )
            )
    ld = pd.concat(long)
    ld = ld[np.isfinite(ld["rr"])]
    base = alt.Chart(ld).encode(
        y=alt.Y("level:N", sort=list(a["level"]), title=None, axis=alt.Axis(labelOverlap=False)),
        yOffset="model:N",
        color=alt.Color(
            "model:N",
            scale=alt.Scale(
                domain=["Crude", "Adjusted: pre-crash (A)", "Adjusted: + configuration (B)"],
                range=[BLUE, ORANGE, "#1baf7a"],
            ),
            legend=alt.Legend(orient="top", title=None),
        ),
    )
    rules = base.mark_rule(strokeWidth=2).encode(
        x=alt.X("low:Q", scale=alt.Scale(type="log"), title="Risk ratio vs reference (log)"),
        x2="high:Q",
    )
    pts = base.mark_point(filled=True, size=60).encode(
        x="rr:Q",
        tooltip=[
            "level",
            "model",
            alt.Tooltip("rr:Q", format=".2f"),
            alt.Tooltip("low:Q", format=".2f"),
            alt.Tooltip("high:Q", format=".2f"),
        ],
    )
    ref = (
        alt.Chart(pd.DataFrame({"r": [1.0]}))
        .mark_rule(strokeDash=[4, 3], color="#898781")
        .encode(x="r:Q")
    )
    st.altair_chart(
        alt.layer(rules, pts, ref).properties(height=max(66 * len(a), 180)),
        width="stretch",
    )
    st.caption(
        f"Reference level: **{a['level'].iloc[0]}**. Model A adjusts for year, region, area, time, weekend, light, "
        "weather, surface, speed limit, interstate, junction, work zone, young/older driver, motorcycle, heavy truck, "
        "speeding and alcohol (imputed). Model B adds crash type and number of vehicles (possible mediators). "
        "Standardised risk ratios (g-computation); conditional on a reported crash; not causal effects."
    )
    with st.expander("Table"):
        st.dataframe(a, hide_index=True, width="stretch")
