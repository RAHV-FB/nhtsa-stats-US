"""Section A: the main supported findings, each with effect size, denominator and caveats."""

from __future__ import annotations

import json

import streamlit as st

from common import KIND_BADGE, ROOT, output_table


def render() -> None:
    st.title("Research findings")
    st.markdown(
        "What makes police-reported crashes in the US deadly, which conditions intensify that risk, and what the "
        "FARS/CRSS data can and cannot say about interventions (2016-2024). Each finding states its population, "
        "denominator, estimate type and main limitations. Full report: `reports/findings.md`."
    )
    path = ROOT / "reports" / "findings.json"
    if not path.exists():
        st.info(
            "`reports/findings.json` not found — run the analyses and write the findings registry."
        )
        return
    findings = json.loads(path.read_text())
    kinds = sorted({f.get("kind", "adjusted") for f in findings})
    pick = st.multiselect(
        "Show estimate types", kinds, default=kinds, format_func=lambda k: KIND_BADGE.get(k, k)
    )
    for i, f in enumerate(findings, 1):
        if f.get("kind", "adjusted") not in pick:
            continue
        with st.expander(f"{i}. {f['title']}", expanded=i <= 3):
            st.markdown(f"**Finding.** {f['statement']}")
            c1, c2 = st.columns([3, 2])
            with c1:
                st.markdown(f"**Effect size.** {f.get('effect', '')}")
                st.markdown(f"**Uncertainty.** {f.get('uncertainty', '')}")
                st.markdown(f"**Population / period.** {f.get('population', '')}")
                st.markdown(f"**Denominator.** {f.get('denominator', '')}")
                st.markdown(f"**Adjusted for.** {f.get('adjustment', '')}")
                st.markdown(f"**Robustness.** {f.get('robustness', '')}")
                st.markdown(f"**Limitations.** {f.get('limitations', '')}")
                st.caption(
                    f"Estimate type: {KIND_BADGE.get(f.get('kind', 'adjusted'), f.get('kind'))} · "
                    f"Evidence: {f.get('evidence', '')}"
                )
            with c2:
                fig = f.get("figure")
                if fig and (ROOT / fig).exists():
                    st.image(str(ROOT / fig))
                tab = f.get("table")
                if tab:
                    mod, name = tab.split("/")
                    df = output_table(mod, name.removesuffix(".csv"))
                    if df is not None:
                        st.caption(f"Supporting table: `outputs/tables/{tab}`")
                        st.dataframe(df.head(12), height=240, use_container_width=True)
