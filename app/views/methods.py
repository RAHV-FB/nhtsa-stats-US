"""Section F: methodology, data provenance, limitations (renders the project documents)."""

from __future__ import annotations

import streamlit as st

from common import ROOT

DOCS = {
    "Limitations": "docs/limitations.md",
    "Methodology": "docs/methodology.md",
    "Research plan": "docs/research_plan.md",
    "Research plan (phase 2)": "docs/research_plan_phase2.md",
    "Data audit": "docs/data_audit.md",
    "Variable harmonisation": "docs/variable_harmonization.md",
    "Model validation": "docs/model_validation.md",
    "Policy assumptions": "docs/policy_assumptions.md",
}


def render() -> None:
    st.title("Methodology and limitations")
    st.markdown(
        "Data: NHTSA **FARS** (census of fatal crashes) and **CRSS** (probability sample of police-reported crashes), "
        "2016-2024, from the 36 archives in `data/raw/`. No external data are used. FARS and CRSS rows are never pooled."
    )
    doc = st.radio("Document", [k for k, v in DOCS.items() if (ROOT / v).exists()], horizontal=True)
    st.markdown((ROOT / DOCS[doc]).read_text())
