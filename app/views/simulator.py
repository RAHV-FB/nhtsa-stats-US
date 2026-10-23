"""Section E: policy simulator -- hypothetical scenarios on top of the empirical baseline.

Layer A (the baseline) is read from outputs/tables/simulation/baseline.json and is empirical:
observed FARS counts, CRSS design-based estimates and adjusted associations. Everything that
describes an intervention -- coverage, behavioural response, effects on crash occurrence and
severity, costs -- is entered by the user. Nothing has a default effect size, and every result
is labelled hypothetical together with the assumptions that produced it.
"""

from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

from common import BLUE, KIND_BADGE

MECHANISMS = {
    "speed": "Automated speed enforcement (cameras)",
    "impaired": "Roadside alcohol or drug checks",
    "restraint": "Seat-belt enforcement",
    "generic": "Other intervention (relative reduction you specify)",
}
SEGMENT_LABELS = {
    "all": "All road deaths",
    "speeding": "Speeding-related crashes (any type)",
    "speeding_exceeded_limit": "Crashes with a driver exceeding the limit / racing",
    "alcohol": "Crashes with a driver at BAC >= 0.08 (FARS imputed)",
    "drugs": "Crashes with police-reported drug involvement (LOW reliability)",
    "unrestrained_lpv": "Unbelted light-vehicle occupant deaths",
}


def _modules():
    try:
        from nhtsa_stats.simulation import costs, engine
    except ImportError:
        return None, None
    return engine, costs


@st.cache_resource
def _baseline():
    engine, _ = _modules()
    return engine.EmpiricalBaseline.load()


def _fmt(x, d: int = 0) -> str:
    return "n/a" if x is None else f"{x:,.{d}f}"


# ------------------------------------------------------------------------------ Layer A
def _baseline_section(engine, base) -> None:
    st.subheader("A. What the data show (empirical baseline)")
    st.caption(
        f"Mean per year over {base.window[0]}-{base.window[1]}. Deaths are observed FARS counts, "
        "except alcohol (BAC >= 0.08), which is an expected value over NHTSA's 10 multiply-imputed "
        "BAC values rather than a census count. KA crashes are CRSS design-based estimates. "
        "Segment counts exclude deaths whose status is unknown, so they are lower bounds."
    )
    rows = []
    for seg in ("all", *engine.PARTITION_SEGMENTS):
        ka = base.segment_ka_crashes(seg) if seg != "all" else None
        rows.append(
            {
                "Segment": SEGMENT_LABELS.get(seg, seg),
                "Reliability": base.reliability(seg),
                "Deaths per year (observed)": base.total_deaths()
                if seg == "all"
                else base.segment_deaths(seg),
                "Share of all deaths": None
                if seg == "all"
                else base.segment_deaths(seg) / base.total_deaths(),
                "KA crashes per year (estimated)": ka,
            }
        )
    st.dataframe(
        pd.DataFrame(rows),
        hide_index=True,
        width="stretch",
        column_config={
            "Deaths per year (observed)": st.column_config.NumberColumn(format="%,.0f"),
            "Share of all deaths": st.column_config.NumberColumn(format="percent"),
            "KA crashes per year (estimated)": st.column_config.NumberColumn(format="%,.0f"),
        },
    )
    st.info(
        "The 36 archives contain no records of cameras, checks, enforcement intensity, campaigns "
        "or costs. No result below is an estimated effect of any intervention: each follows from "
        "the assumptions you enter. See `docs/policy_assumptions.md`."
    )


# ------------------------------------------------------------------------- Layer B / C
def _param(engine, label: str, key: str, help_: str, lo: float, hi: float, step: float = 0.01):
    """Low / central / high inputs -> Param (None until a central value is entered)."""
    c1, c2, c3 = st.columns(3)
    kw = dict(min_value=lo, max_value=hi, step=step, format="%.3f")
    central = c2.number_input(f"{label}: central", value=None, key=f"{key}_c", help=help_, **kw)
    low = c1.number_input(f"{label}: low", value=None, key=f"{key}_lo", **kw)
    high = c3.number_input(f"{label}: high", value=None, key=f"{key}_hi", **kw)
    if central is None:
        return None
    try:
        return engine.Param(
            central, central if low is None else low, central if high is None else high
        )
    except ValueError as exc:
        st.error(f"{label}: {exc}")
        return None


def _units(label: str, key: str):
    c1, c2 = st.columns(2)
    cur = c1.number_input(
        f"{label}: current", value=None, min_value=0.0, step=1.0, key=f"{key}_cur"
    )
    new = c2.number_input(
        f"{label}: proposed", value=None, min_value=0.0, step=1.0, key=f"{key}_new"
    )
    return cur, new


def _coverage(engine, key: str):
    form = st.radio(
        "How does coverage grow with deployment?",
        ["Linear up to a cap", "Saturating (diminishing returns)"],
        key=f"{key}_form",
        horizontal=True,
        help="Doubling the units does not double the effect: coverage is capped or saturates.",
    )
    if form.startswith("Linear"):
        per = _param(
            engine,
            "Coverage per unit",
            f"{key}_per",
            "share of target exposure per unit",
            0.0,
            1.0,
            0.001,
        )
        cap = _param(
            engine, "Maximum coverage", f"{key}_cap", "leave empty for no cap below 100%", 0.0, 1.0
        )
        if per is None:
            return None
        return engine.LinearCappedCoverage(per, cap if cap is not None else 1.0)
    rate = _param(
        engine,
        "Saturation rate k per unit",
        f"{key}_k",
        "coverage = max x (1 - exp(-k x units))",
        0.0,
        10.0,
        0.001,
    )
    mx = _param(engine, "Maximum coverage", f"{key}_max", "leave empty for 100%", 0.0, 1.0)
    if rate is None:
        return None
    return engine.SaturatingCoverage(rate, mx if mx is not None else 1.0)


def _severity(engine, base, segment: str, key: str):
    choice = st.radio(
        "Severity effect (relative reduction in P(fatal | crash) for affected crashes)",
        ["Enter my own", "Use the adjusted association 1 - 1/RR (assumes it is causal)"],
        key=f"{key}_sevsrc",
        horizontal=True,
    )
    if choice.startswith("Use"):
        try:
            p = engine.severity_effect_from_association(base, segment)
        except engine.MissingInputError as exc:
            st.warning(str(exc))
            return None
        st.caption(f"Range from the adjusted association: {p.description}. {p.source}.")
        return p
    return _param(engine, "Severity effect", f"{key}_sev", "", -1.0, 1.0)


def _build(engine, base, key: str):
    """Collect one intervention's inputs; return a Scenario or None while inputs are missing."""
    kind = st.selectbox(
        "Intervention", list(MECHANISMS), format_func=MECHANISMS.get, key=f"{key}_kind"
    )
    try:
        if kind == "speed":
            seg = st.selectbox(
                "Target segment",
                ["speeding_exceeded_limit", "speeding"],
                format_func=SEGMENT_LABELS.get,
                key=f"{key}_seg",
            )
            cur, new = _units("Camera units", key)
            cov = _coverage(engine, key)
            resp = _param(
                engine,
                "Behavioural response",
                f"{key}_resp",
                "relative reduction in speeding within covered exposure",
                0.0,
                1.0,
            )
            occ = _param(
                engine,
                "Crash-occurrence effect",
                f"{key}_occ",
                "relative reduction in crash frequency of exposure whose speeding is removed",
                -1.0,
                1.0,
            )
            sev = _severity(engine, base, seg, key)
            halo = _param(
                engine,
                "Halo (spillover)",
                f"{key}_halo",
                "exposure affected outside coverage, as a multiple of it; empty = none",
                0.0,
                10.0,
            )
            if None in (cur, new, cov):
                return None
            mech = engine.SpeedEnforcement(
                cur,
                new,
                cov,
                resp,
                occ,
                sev,
                halo=halo if halo is not None else 0.0,
                target_segment=seg,
            )
        elif kind == "impaired":
            seg = st.selectbox(
                "Target segment",
                ["alcohol", "drugs"],
                format_func=SEGMENT_LABELS.get,
                key=f"{key}_seg",
            )
            cur, new = _units("Checks per year", key)
            cov = _coverage(engine, key)
            det = _param(engine, "Perceived detection probability", f"{key}_det", "", 0.0, 1.0)
            ela = _param(
                engine,
                "Deterrence elasticity",
                f"{key}_ela",
                "-d ln(prevalence) / d(perceived detection risk)",
                0.0,
                100.0,
                0.1,
            )
            occ = _param(engine, "Crash-occurrence effect", f"{key}_occ", "", -1.0, 1.0)
            sev = (
                _severity(engine, base, seg, key)
                if seg == "alcohol"
                else _param(engine, "Severity effect", f"{key}_sev", "", -1.0, 1.0)
            )
            if None in (cur, new, cov):
                return None
            mech = engine.ImpairedDrivingEnforcement(
                cur, new, cov, det, ela, occ, sev, target_segment=seg
            )
        elif kind == "restraint":
            conv = _param(
                engine,
                "Share of unbelted occupants who would buckle up",
                f"{key}_conv",
                "",
                0.0,
                1.0,
            )
            src = st.selectbox(
                "Belt effectiveness",
                [
                    "Layer A within-vehicle association (assumes it is causal)",
                    "Same, if 5% of belted survivors were unbelted",
                    "Same, if 10% were",
                    "Same, if 20% were",
                    "Enter my own",
                ],
                key=f"{key}_beltsrc",
                help="FARS within-vehicle estimate given a fatal crash; the misreporting rows show its sensitivity.",
            )
            variants = {
                "Layer A within-vehicle association (assumes it is causal)": None,
                "Same, if 5% of belted survivors were unbelted": "misreport_f05",
                "Same, if 10% were": "misreport_f10",
                "Same, if 20% were": "misreport_f20",
            }
            if src == "Enter my own":
                eff = _param(engine, "Belt effectiveness", f"{key}_eff", "", 0.0, 1.0)
            else:
                eff = engine.belt_effectiveness_param(base, variants[src])
                st.caption(
                    f"{eff.description}: {eff.central:.3f} ({eff.low:.3f}-{eff.high:.3f}). {eff.source}."
                )
            ratio = _param(
                engine,
                "Converters' benefit relative to average unbelted occupant",
                f"{key}_ratio",
                "empty = 1 (same)",
                0.0,
                2.0,
            )
            mech = engine.RestraintEnforcement(conv, eff, ratio if ratio is not None else 1.0)
        else:
            seg = st.selectbox(
                "Target segment",
                ["all", *engine.PARTITION_SEGMENTS],
                format_func=SEGMENT_LABELS.get,
                key=f"{key}_seg",
            )
            red = _param(
                engine, "Relative reduction in target-segment deaths", f"{key}_red", "", -1.0, 1.0
            )
            mech = engine.GenericIntervention(seg, red)
    except engine.MissingAssumptionError as exc:
        st.caption(f"Waiting for inputs: {exc}")
        return None
    except (TypeError, ValueError) as exc:
        st.error(str(exc))
        return None
    return engine.Scenario(key, mech)


# ------------------------------------------------------------------------------ Layer D
def _results(engine, base, scenario) -> None:
    res = engine.evaluate(scenario, base)
    st.caption(f"**Estimate type:** {KIND_BADGE['hypothetical']}")
    c1, c2, c3 = st.columns(3)
    c1.metric("Deaths prevented per year", _fmt(res["deaths_prevented"]))
    pct = res["pct_change_deaths"]
    c2.metric("Change in all road deaths", "n/a" if pct is None else f"{pct:+.2f}%")
    c3.metric("KA crashes prevented per year", _fmt(res["ka_crashes_prevented"]))
    st.write(
        f"Target segment: **{SEGMENT_LABELS.get(res['target_segment'], res['target_segment'])}** "
        f"({_fmt(res['baseline_target_deaths_per_year'])} deaths a year); relative reduction "
        f"{100 * res['relative_reduction_target_deaths']:.1f}%."
    )
    for n in res["notes"]:
        st.warning(n)
    with st.expander("Causal chain and assumptions used"):
        st.markdown("\n".join(f"- {s}" for s in res["chain_description"]))
        st.dataframe(pd.DataFrame(res["assumptions"]), hide_index=True, width="stretch")
        st.markdown("\n".join(f"- {s}" for s in res["structural_assumptions"]))
    params = scenario.parameters(base)
    if any(not p.is_fixed for p in params.values()):
        tor = engine.tornado(scenario, base)
        _tornado_chart(tor)
        mc = engine.monte_carlo(scenario, base, n_draws=5000)
        s = mc.summary[mc.summary["outcome"] == "deaths_prevented"].iloc[0]
        st.write(
            f"Monte Carlo over your ranges (5,000 draws, independent parameters): median "
            f"{_fmt(s['p50'])} deaths prevented a year, 90% of draws between {_fmt(s['p5'])} and "
            f"{_fmt(s['p95'])}. {mc.note}"
        )
    else:
        st.caption("Enter low/high values to see one-way sensitivity and a Monte Carlo range.")


def _tornado_chart(tor: pd.DataFrame) -> None:
    if tor.empty:
        return
    low_col = next(c for c in tor.columns if c.endswith("_at_low"))
    high_col = next(c for c in tor.columns if c.endswith("_at_high"))
    d = tor.assign(lo=tor[[low_col, high_col]].min(axis=1), hi=tor[[low_col, high_col]].max(axis=1))
    chart = (
        alt.Chart(d)
        .mark_bar(color=BLUE, cornerRadius=4, height=14)
        .encode(
            y=alt.Y(
                "parameter:N", sort=alt.EncodingSortField("swing", order="descending"), title=None
            ),
            x=alt.X("lo:Q", title="Deaths prevented per year (parameter at its low / high)"),
            x2="hi:Q",
            tooltip=[
                "parameter",
                alt.Tooltip(low_col, format=",.0f"),
                alt.Tooltip(high_col, format=",.0f"),
            ],
        )
        .properties(
            height=34 * len(d) + 20,
            title="One-way sensitivity (other parameters at central values)",
        )
    )
    st.altair_chart(chart, width="stretch")


def _combination(engine, base, s1, s2) -> None:
    st.subheader("Both interventions together")
    rule = st.radio(
        "Deaths that fall in both target segments",
        ["multiplicative", "max"],
        format_func={
            "multiplicative": "Act independently (1 - (1-e1)(1-e2))",
            "max": "Fully redundant (largest effect only)",
        }.get,
        horizontal=True,
    )
    res = engine.combine([s1, s2], base, overlap=rule)
    c1, c2, c3 = st.columns(3)
    c1.metric("Deaths prevented per year (combined)", _fmt(res["deaths_prevented"]))
    c2.metric("Naive sum of separate projections", _fmt(res["deaths_prevented_naive_sum"]))
    c3.metric("Double counting avoided", _fmt(res["double_counting_avoided"]))
    st.caption(
        f"{_fmt(res['deaths_in_all_target_segments_per_year'])} deaths a year fall in both target "
        f"segments (observed overlap). {res['overlap_assumption']}"
    )


def _costs(engine, costs, base, scenario) -> None:
    with st.expander("Costs, cost-effectiveness and break-even (your inputs; no default prices)"):
        c1, c2 = st.columns(2)
        inv = c1.number_input(
            "Initial investment", value=None, min_value=0.0, step=1000.0, key="cost_inv"
        )
        op = c2.number_input(
            "Annual operating cost", value=None, min_value=0.0, step=1000.0, key="cost_op"
        )
        life = c1.number_input(
            "Service life (years)", value=None, min_value=1.0, step=1.0, key="cost_life"
        )
        rate = c2.number_input(
            "Discount rate",
            value=None,
            min_value=0.0,
            max_value=0.5,
            step=0.005,
            format="%.3f",
            key="cost_rate",
        )
        thr = st.number_input(
            "Cost-effectiveness threshold (cost per death prevented you would accept)",
            value=None,
            min_value=0.0,
            step=10000.0,
            key="cost_thr",
        )
        if None in (inv, op, life, rate):
            st.caption("Enter all four cost inputs (any currency) to compute cost-effectiveness.")
            return
        prog = costs.ProgrammeCosts(inv, op, life, rate, label=scenario.name)
        res = engine.evaluate(scenario, base)
        ce = costs.cost_effectiveness(prog, res["deaths_prevented"], res["ka_crashes_prevented"])
        st.write(
            f"Equivalent annual cost: **{_fmt(ce['equivalent_annual_cost'])}**. Cost per death "
            f"prevented: **{_fmt(ce['cost_per_death_prevented'])}** (hypothetical)."
        )
        if thr:
            st.write(
                f"To meet {thr:,.0f} per death prevented, the programme must prevent at least "
                f"**{costs.breakeven_deaths(prog.equivalent_annual_cost(), thr):,.1f}** deaths a year."
            )
            ranged = [
                k for k, p in scenario.parameters(base).items() if not k.startswith("coverage.")
            ]
            target = st.selectbox("Solve for the minimum value of", ranged, key="cost_param")
            try:
                be = costs.breakeven_parameter(scenario, base, target, prog, thr)
            except (KeyError, ValueError, RuntimeError) as exc:
                st.warning(str(exc))
            else:
                value = "none" if be["value"] is None else f"{be['value']:.4g}"
                st.write(f"`{target}`: {be['interpretation']} -> **{value}** ({be['basis']}).")


def render() -> None:
    st.title("Policy simulator")
    st.markdown(
        "Explore what an intervention **would have to achieve**, and what it **would achieve if** "
        "your assumptions held. Empirical inputs come from the data; every effect and cost comes "
        "from you."
    )
    engine, costs = _modules()
    if engine is None:
        st.info("The simulation engine is not installed.")
        return
    try:
        base = _baseline()
    except FileNotFoundError:
        st.info("Run `uv run nhtsa analyze policy` to build the empirical baseline first.")
        return
    _baseline_section(engine, base)
    st.subheader("B-C. Your intervention and assumptions")
    tab1, tab2 = st.tabs(["Intervention 1", "Intervention 2 (optional, for combinations)"])
    with tab1:
        s1 = _build(engine, base, "one")
    with tab2:
        s2 = (
            _build(engine, base, "two")
            if st.checkbox("Add a second intervention", key="two_on")
            else None
        )
    st.subheader("D. Projected outcomes (hypothetical)")
    if s1 is None:
        st.info("Enter the required inputs of intervention 1 to see projected outcomes.")
        return
    _results(engine, base, s1)
    if s2 is not None:
        _combination(engine, base, s1, s2)
    _costs(engine, costs, base, s1)
    st.caption(
        f"Baseline: {base.window[0]}-{base.window[1]} means, held static (no secular trend). "
        "Outputs are steady-state annual values."
    )
