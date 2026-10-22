"""Section C: interaction explorer - co-occurrence, observed cells, adjusted interaction."""

from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from common import FACTOR_CHOICES, crss_crash, data_ready, fmt_pct, kind_note, output_table
from nhtsa_stats import config
from nhtsa_stats.analysis import interactions as it
from nhtsa_stats.analysis import severity, specs
from nhtsa_stats.analysis.survey import svy_mean, svy_total


def _exposure_picker(df: pd.DataFrame, label: str, key: str, default: str) -> it.Exposure:
    var = st.selectbox(
        f"{label}: variable",
        [v for v in FACTOR_CHOICES if v != "YEAR"],
        index=list(FACTOR_CHOICES).index(default),
        format_func=FACTOR_CHOICES.get,
        key=f"{key}v",
    )
    levels = [
        lv
        for lv in specs.CRASH_LEVELS.get(var, sorted(df[var].dropna().unique()))
        if (df[var] == lv).any()
    ]
    default_exp = [
        lv
        for lv in levels
        if lv in ("yes", "dark_not_lighted", "wet", "50-55", "rural", "pedestrian")
    ][:1] or levels[1:2]
    exp = st.multiselect(f"{label}: exposed levels", levels, default=default_exp, key=f"{key}e")
    ref_default = [lv for lv in levels if lv not in exp and lv != "unknown"][:1]
    ref = st.multiselect(
        f"{label}: reference levels",
        [lv for lv in levels if lv not in exp],
        default=ref_default,
        key=f"{key}r",
    )
    return it.Exposure(
        var, tuple(exp), tuple(ref), f"{FACTOR_CHOICES[var]} = {'/'.join(map(str, exp))}"
    )


@st.cache_data(show_spinner="Fitting survey-weighted interaction model (20-90 s)…")
def _fit_pair(a_var, a_exp, a_ref, b_var, b_exp, b_ref, outcome, covset) -> dict:
    df, design = severity.load(outcome)
    comb = it.Combination(
        "custom",
        (it.Exposure(a_var, a_exp, a_ref, a_var), it.Exposure(b_var, b_exp, b_ref, b_var)),
        covset,
    )
    return it.analyse_pair(df, design, outcome, comb, df["YEAR"].nunique())


def render() -> None:
    st.title("Interaction explorer")
    st.markdown(
        "Do two circumstances amplify each other? **Co-occurrence** (appearing together) is shown separately from "
        "**interaction** (whether the excess risk of one depends on the other). Interaction is reported on the "
        "additive scale (excess deaths per 1,000 crashes - what matters for burden) and the multiplicative scale."
    )
    if not data_ready():
        return
    df, design = crss_crash()
    outcome = st.radio(
        "Outcome",
        ["fatal", "ka"],
        horizontal=True,
        format_func=lambda o: "Fatal (K)" if o == "fatal" else "Fatal or serious (KA)",
    )
    c1, c2 = st.columns(2)
    with c1:
        a = _exposure_picker(df, "Factor A", "a", "speeding")
    with c2:
        b = _exposure_picker(df, "Factor B", "b", "light")
    if not (a.exposed and a.reference and b.exposed and b.reference):
        st.info("Choose exposed and reference levels for both factors.")
        return
    if a.var == b.var:
        st.warning("Choose two different variables.")
        return
    y = df[outcome].to_numpy(float)
    known_y = np.isfinite(y)
    ia, ib = it._indicator(df, a), it._indicator(df, b)
    n_years = df["YEAR"].nunique()
    rows = []
    for sa in (0, 1):
        for sb in (0, 1):
            dom = (ia == sa) & (ib == sb) & known_y
            est = svy_mean(design, y, dom)
            n = int(dom.sum())
            ev = int(np.nansum(y[dom]))
            rows.append(
                {
                    "A": "exposed" if sa else "reference",
                    "B": "exposed" if sb else "reference",
                    "sample_n": n,
                    "events": ev,
                    "crashes_per_year": round(
                        svy_total(design, np.ones(design.n), dom).estimate / n_years, -2
                    ),
                    "crude_rate": fmt_pct(est.estimate, 3),
                    "flag": "suppressed"
                    if n < config.MIN_CELL_N
                    else ("few events" if ev < 20 else ""),
                }
            )
    st.subheader("Observed cells (CRSS, weighted)")
    kind_note("estimated")
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    known = np.isfinite(ia) & np.isfinite(ib)
    oe = {}
    for tag, dom in (("all crashes", known), ("fatal crashes", known & (y == 1))):
        pa = svy_mean(design, np.nan_to_num(ia), dom).estimate
        pb = svy_mean(design, np.nan_to_num(ib), dom).estimate
        pab = svy_mean(design, np.nan_to_num(ia * ib), dom).estimate
        oe[tag] = (pab, pa * pb)
    c1, c2 = st.columns(2)
    for col, (tag, (pab, exp)) in zip((c1, c2), oe.items(), strict=True):
        col.metric(
            f"Co-occurrence among {tag}", fmt_pct(pab), help="Weighted share with both A and B"
        )
        col.caption(
            f"Expected if independent: {fmt_pct(exp)} → observed/expected = {pab / exp:.2f}"
            if exp
            else ""
        )
    if min(r["events"] for r in rows) < 20:
        st.warning(
            "At least one cell has fewer than 20 events: adjusted interaction estimates will be unstable."
        )

    st.subheader("Adjusted interaction")
    kind_note("adjusted")
    pre = output_table("interactions", f"pairs_{outcome}")
    match = None
    if pre is not None:
        for comb in it.PAIRS:
            ea, eb = comb.exposures
            if {(ea.var, ea.exposed, ea.reference), (eb.var, eb.exposed, eb.reference)} == {
                (a.var, a.exposed, a.reference),
                (b.var, b.exposed, b.reference),
            }:
                hit = pre[pre["pair"] == comb.name]
                if len(hit):
                    match = hit.iloc[0].to_dict()
    covset = st.radio(
        "Adjustment set",
        ["A", "B"],
        horizontal=True,
        format_func=lambda s: "Pre-crash (A)" if s == "A" else "Pre-crash + configuration (B)",
    )
    if match is None:
        st.caption(
            "Not a pre-specified pair: estimates are exploratory and not multiplicity-adjusted."
        )
        if st.button("Fit adjusted model"):
            match = _fit_pair(
                a.var, a.exposed, a.reference, b.var, b.exposed, b.reference, outcome, covset
            )
    else:
        st.caption(
            f"Pre-specified pair '{match['pair']}' (pre-computed, Holm-adjusted p-values available)."
        )
    if match is not None:
        m = match
        c1, c2, c3 = st.columns(3)
        c1.metric("Adjusted risk, neither", fmt_pct(m["adj_p00"], 3))
        c2.metric("Adjusted risk, both", fmt_pct(m["adj_p11"], 3))
        c3.metric(
            "RR for both vs neither",
            f"{m['rr_11_vs_00']:.2f}",
            help=f"95% CI {m['rr_11_vs_00_low']:.2f}–{m['rr_11_vs_00_high']:.2f}",
        )
        res = pd.DataFrame(
            [
                [
                    "RR of A when B absent",
                    f"{m['rr_A_given_B0']:.2f}",
                    f"{m['rr_A_given_B0_low']:.2f}–{m['rr_A_given_B0_high']:.2f}",
                ],
                [
                    "RR of A when B present",
                    f"{m['rr_A_given_B1']:.2f}",
                    f"{m['rr_A_given_B1_low']:.2f}–{m['rr_A_given_B1_high']:.2f}",
                ],
                [
                    "Additive interaction (per 1,000 crashes)",
                    f"{1000 * m['ic']:+.1f}",
                    f"{1000 * m['ic_low']:+.1f} to {1000 * m['ic_high']:+.1f}",
                ],
                ["RERI", f"{m['reri']:.2f}", f"{m['reri_low']:.2f}–{m['reri_high']:.2f}"],
                [
                    "Ratio of risk ratios (multiplicative)",
                    f"{m['ratio_of_rr']:.2f}",
                    f"{m['ratio_of_rr_low']:.2f}–{m['ratio_of_rr_high']:.2f}",
                ],
                [
                    "Product-term odds ratio",
                    f"{m['product_or']:.2f}",
                    f"{m['product_or_low']:.2f}–{m['product_or_high']:.2f} (p={m['product_p']:.3g})",
                ],
            ],
            columns=["Measure", "Estimate", "95% CI"],
        )
        st.table(res)
        st.caption(
            "Additive interaction > 0: the joint excess risk exceeds the sum of the separate excesses. Ratio of RRs "
            "> 1: super-multiplicative. Both are statistical interactions conditional on a reported crash, not "
            "proof of causal synergy; behavioural factors are recorded more thoroughly in severe crashes."
        )
