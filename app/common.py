"""Shared helpers for the Streamlit research interface: cached data, survey estimates, charts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from nhtsa_stats import config  # noqa: E402
from nhtsa_stats.analysis import data, specs  # noqa: E402
from nhtsa_stats.analysis.survey import SurveyDesign, logit_ci, svy_mean, svy_total  # noqa: E402

BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
MUTED = "#898781"
KIND_BADGE = {
    "observed": "Observed (FARS census count)",
    "estimated": "Estimated (CRSS design-based)",
    "adjusted": "Adjusted association (model-based, not causal)",
    "predicted": "Model-predicted (conditional on a reported crash)",
    "hypothetical": "Hypothetical (depends on user assumptions)",
}

FACTOR_CHOICES = {
    "light": "Light condition",
    "tod": "Time of day",
    "weekend": "Weekend",
    "weather": "Weather",
    "surface": "Road surface",
    "speed_limit": "Speed limit",
    "interstate": "Interstate",
    "junction": "Junction",
    "urbanicity": "Area (CRSS urbanicity)",
    "region": "Census region",
    "work_zone": "Work zone",
    "crash_type": "Crash type",
    "n_vehicles": "Vehicles in transport",
    "speeding": "Speeding-related (police-reported)",
    "alcohol_im": "Alcohol involved (NHTSA-imputed)",
    "alcohol": "Alcohol involved (police-reported, 2019 coding break)",
    "young_driver": "Driver aged 15-20 involved",
    "older_driver": "Driver aged 65+ involved",
    "any_motorcycle": "Motorcycle involved",
    "any_heavy_truck": "Medium/heavy truck or bus involved",
    "YEAR": "Year",
}
TRI_COLS = [c for c in specs.CRASH_TRI if c != "drugs"] + ["drugs"]


def kind_note(kind: str) -> None:
    st.caption(f"**Estimate type:** {KIND_BADGE[kind]}")


@st.cache_resource(show_spinner="Loading CRSS crash file and survey design…")
def crss_crash() -> tuple[pd.DataFrame, SurveyDesign]:
    """Full CRSS crash file (all severities) with tri-state labels and the full design."""
    df, design = data.crss_crash(outcome=None, tri_state_cols=TRI_COLS)
    return df, design


@st.cache_data(show_spinner=False)
def output_table(module: str, name: str) -> pd.DataFrame | None:
    p = config.TABLES_DIR / module / f"{name}.csv"
    return pd.read_csv(p) if p.exists() else None


@st.cache_data(show_spinner=False)
def output_json(module: str, name: str) -> dict | None:
    p = config.TABLES_DIR / module / f"{name}.json"
    return json.loads(p.read_text()) if p.exists() else None


def data_ready() -> bool:
    ok = (config.PROCESSED_DIR / "crss_crash.parquet").exists()
    if not ok:
        st.error(
            "Processed datasets not found. Build them first: `uv run nhtsa build` (and `uv run nhtsa analyze`)."
        )
    return ok


def filter_controls(df: pd.DataFrame, key: str) -> np.ndarray:
    """Year / region / area filters in one row; returns a boolean domain mask."""
    c1, c2, c3 = st.columns([2, 1, 1])
    yr = c1.slider("Years", 2016, 2024, (2016, 2024), key=f"{key}_yr")
    regions = c2.multiselect("Region", specs.CRASH_LEVELS["region"], key=f"{key}_reg")
    area = c3.multiselect("Area", ["urban", "rural"], key=f"{key}_area")
    # Combine into new arrays: under copy-on-write .to_numpy() can be read-only.
    m = df["YEAR"].between(*yr).to_numpy()
    if regions:
        m = m & df["region"].isin(regions).to_numpy()
    if area:
        m = m & df["urbanicity"].isin(area).to_numpy()
    return m


def rate_by_level(
    df: pd.DataFrame, design: SurveyDesign, factor: str, outcome: str, domain: np.ndarray
) -> pd.DataFrame:
    """Weighted crude outcome rate per level of ``factor`` within ``domain`` (design-based CI)."""
    y = df[outcome].to_numpy(float)
    known = np.isfinite(y)
    n_years = max(df.loc[domain, "YEAR"].nunique(), 1)
    levels = [
        lv
        for lv in specs.CRASH_LEVELS.get(factor, sorted(df[factor].dropna().unique()))
        if (df[factor] == lv).any()
    ]
    rows = []
    for lv in levels:
        dom = domain & known & (df[factor] == lv).to_numpy()
        n = int(dom.sum())
        if n == 0:
            continue
        est = svy_mean(design, y, dom)
        lo, hi = logit_ci(est.estimate, est.se, est.df)
        share = svy_mean(design, (df[factor] == lv).to_numpy(float), domain & known)
        tot = svy_total(design, np.ones(design.n), dom)
        events = int(np.nansum(y[dom]))
        rse = est.se / est.estimate if est.estimate > 0 else np.inf
        flag = (
            "suppressed: n < 30"
            if n < config.MIN_CELL_N
            else "unstable: < 5 events"
            if events < 5
            else "unstable: RSE > 30%"
            if rse > config.MAX_RSE
            else ""
        )
        rows.append(
            {
                "level": str(lv),
                "sample_n": n,
                "events": events,
                "crashes_per_year": tot.estimate / n_years,
                "share_of_crashes": share.estimate,
                "rate": est.estimate,
                "low": lo,
                "high": hi,
                "flag": flag,
            }
        )
    return pd.DataFrame(rows)


def point_range(
    df: pd.DataFrame,
    x: str,
    lo: str,
    hi: str,
    y: str,
    color: str = BLUE,
    log: bool = False,
    ref: float | None = None,
    title: str = "",
    x_title: str = "",
    sort: list | None = None,
) -> alt.Chart:
    scale = alt.Scale(type="log") if log else alt.Scale(zero=False)
    base = alt.Chart(df).encode(y=alt.Y(f"{y}:N", sort=sort or None, title=None))
    tip = [
        alt.Tooltip(f"{y}:N"),
        alt.Tooltip(f"{x}:Q", format=".3g"),
        alt.Tooltip(f"{lo}:Q", format=".3g"),
        alt.Tooltip(f"{hi}:Q", format=".3g"),
    ]
    rule = base.mark_rule(color=color, strokeWidth=2).encode(
        x=alt.X(f"{lo}:Q", scale=scale, title=x_title), x2=f"{hi}:Q"
    )
    pts = base.mark_point(filled=True, color=color, size=70).encode(x=f"{x}:Q", tooltip=tip)
    layers = [rule, pts]
    if ref is not None:
        layers.append(
            alt.Chart(pd.DataFrame({"r": [ref]}))
            .mark_rule(color=MUTED, strokeDash=[4, 3])
            .encode(x="r:Q")
        )
    return alt.layer(*layers).properties(title=title, height=max(40 * len(df), 140))


def fmt_pct(v: float, d: int = 2) -> str:
    return "—" if v is None or not np.isfinite(v) else f"{100 * v:.{d}f}%"
