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


def _domain(a: it.Exposure, b: it.Exposure) -> str | None:
    """Standardisation population: a multi-vehicle crash type can only be assigned to
    multi-vehicle crashes, so such pairs are standardised over those (as registered pairs are)."""
    for e in (a, b):
        if e.var == "crash_type" and any(
            str(lv).startswith("mv_") for lv in (*e.exposed, *e.reference)
        ):
            return "multi_vehicle"
    return None


@st.cache_data(show_spinner="Fitting survey-weighted interaction model (20-90 s)…")
def _fit_pair(
    a_var, a_exp, a_ref, b_var, b_exp, b_ref, outcome, covset, domain=None, extra=()
) -> dict:
    df, design = severity.load(outcome)
    comb = it.Combination(
        "custom",
        (it.Exposure(a_var, a_exp, a_ref, a_var), it.Exposure(b_var, b_exp, b_ref, b_var)),
        covset,
        extra_covariates=tuple(extra),
        domain=domain,
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
            small = n < config.MIN_CELL_N  # suppressed: no estimates shown
            rows.append(
                {
                    "A": "exposed" if sa else "reference",
                    "B": "exposed" if sb else "reference",
                    "sample_n": n,
                    "events": ev,
                    "crashes_per_year": None
                    if small
                    else round(svy_total(design, np.ones(design.n), dom).estimate / n_years, -2),
                    "crude_rate": "—" if small else fmt_pct(est.estimate, 3),
                    "flag": "suppressed" if small else ("few events" if ev < 20 else ""),
                }
            )
    st.subheader("Observed cells (CRSS, weighted)")
    kind_note("estimated")
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    known = np.isfinite(ia) & np.isfinite(ib)
    oe = {}
    event_tag = "fatal crashes" if outcome == "fatal" else "fatal-or-serious (KA) crashes"
    for tag, dom in (("all crashes", known), (event_tag, known & (y == 1))):
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

    def key(e: it.Exposure) -> tuple:  # levels picked in any order are the same exposure
        return (e.var, frozenset(e.exposed), frozenset(e.reference))

    reg = None  # (Combination, pre-computed row) when the selection is a registered pair
    swapped = None  # registered pair chosen with A and B the other way round
    if pre is not None:
        for comb in it.PAIRS:
            ea, eb = comb.exposures
            hit = pre[pre["pair"] == comb.name]
            if not len(hit):
                continue
            # Ordered match: the "RR of A given B" rows are not symmetric in A and B.
            if (key(ea), key(eb)) == (key(a), key(b)):
                reg = (comb, hit.iloc[0].to_dict())
            elif (key(ea), key(eb)) == (key(b), key(a)):
                swapped = comb
    if swapped is not None:
        st.caption(
            f"This pair is registered as '{swapped.name}' with the factors the other way round; "
            "swap Factor A and Factor B to see its pre-computed estimate."
        )
    sets = ["A", "B"]
    covset = st.radio(
        "Adjustment set",
        sets,
        index=sets.index(reg[0].covariates) if reg else 0,
        horizontal=True,
        format_func=lambda s: "Pre-crash (A)" if s == "A" else "Pre-crash + configuration (B)",
    )
    # A pre-computed row is shown only for the adjustment set it was estimated with.
    match = reg[1] if reg and reg[0].covariates == covset else None
    if match is None:
        if reg:
            st.caption(
                f"The pre-computed estimate for '{reg[0].name}' uses adjustment set "
                f"{reg[0].covariates}. With set {covset} the model is fitted on demand; that "
                "estimate is exploratory and not multiplicity-adjusted."
            )
        else:
            st.caption(
                "Not a pre-specified pair: estimates are exploratory and not multiplicity-adjusted."
            )
        if st.button("Fit adjusted model"):
            match = _fit_pair(
                a.var,
                a.exposed,
                a.reference,
                b.var,
                b.exposed,
                b.reference,
                outcome,
                covset,
                domain=reg[0].domain if reg else _domain(a, b),
                extra=reg[0].extra_covariates if reg else (),
            )
    elif reg[0].prespecified:
        n_reg = sum(c.prespecified for c in it.PAIRS)
        st.caption(
            f"Pre-specified pair '{reg[0].name}' (pre-computed; Holm adjustment across the "
            f"{n_reg} registered pairs)."
        )
    else:
        st.caption(
            f"Exploratory pair '{reg[0].name}' (pre-computed; added at implementation, not "
            "multiplicity-adjusted)."
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
                    f"{m['product_or_low']:.2f}–{m['product_or_high']:.2f} "
                    f"(unadjusted p={m['product_p']:.3g})",
                ],
            ],
            columns=["Measure", "Estimate", "95% CI"],
        )
        st.table(res)
        if pd.notna(m.get("ic_p_holm")):
            st.caption(
                f"Holm-adjusted p-values: additive interaction {m['ic_p_holm']:.3g}; ratio of risk "
                f"ratios {m['ratio_of_rr_p_holm']:.3g}."
            )
        st.caption(
            "Additive interaction > 0: the joint excess risk exceeds the sum of the separate excesses. Ratio of RRs "
            "> 1: super-multiplicative. Both are statistical interactions conditional on a reported crash, not "
            "proof of causal synergy; behavioural factors are recorded more thoroughly in severe crashes."
        )
