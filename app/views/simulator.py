"""Section E: policy simulator (wired to nhtsa_stats.simulation.engine)."""

from __future__ import annotations

import streamlit as st


def render() -> None:
    st.title("Policy simulator")
    try:
        from nhtsa_stats.simulation import engine  # noqa: F401
    except ImportError:
        st.info("The simulation engine is not installed yet.")
        return
    st.info("Simulator interface under construction.")
