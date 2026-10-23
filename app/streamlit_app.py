"""Research interface for the NHTSA FARS/CRSS road-safety study.

Run with:  uv run streamlit run app/streamlit_app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

APP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(APP_DIR))

import common  # noqa: E402,F401  (adds src/ to sys.path)
from views import (  # noqa: E402
    cases,
    contributions,
    factors,
    findings,
    interactions,
    methods,
    multifactor,
    severity_model,
    simulator,
)

st.set_page_config(page_title="US crash severity research", layout="wide")

pages = [
    st.Page(findings.render, title="Findings", default=True),  # served at the root URL
    st.Page(factors.render, title="Factor explorer", url_path="factors"),
    st.Page(interactions.render, title="Interaction explorer", url_path="interactions"),
    st.Page(contributions.render, title="Factor contributions", url_path="contributions"),
    st.Page(multifactor.render, title="Multiple-factor explorer", url_path="multifactor"),
    st.Page(cases.render, title="Case comparison", url_path="cases"),
    st.Page(severity_model.render, title="Severity model", url_path="severity"),
    st.Page(simulator.render, title="Policy simulator", url_path="simulator"),
    st.Page(methods.render, title="Methodology & limitations", url_path="methods"),
]
st.sidebar.caption(
    "FARS & CRSS 2016-2024 · empirical estimates are labelled observed / estimated / adjusted / predicted; "
    "simulator outputs are hypothetical."
)
st.navigation(pages).run()
