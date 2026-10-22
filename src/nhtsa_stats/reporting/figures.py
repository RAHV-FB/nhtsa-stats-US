"""Static report figures (matplotlib), drawn from the saved output tables.

Visual conventions (validated palette, see dataviz guidance): categorical series use the
first three slots blue / orange / aqua in fixed order with distinct marker shapes as secondary
encoding; reference lines and grids are muted; ratio axes are logarithmic; there is never a
second y-axis.  Every figure states population, outcome and estimate type in its title or
caption line.
"""

from __future__ import annotations

import logging

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from nhtsa_stats.reporting.io import load_table, save_figure

log = logging.getLogger(__name__)
MODULE = "figures"

BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
INK, INK2, MUTED, GRID, BASE = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
SURFACE = "#fcfcfb"
DIVERGING = ["#184f95", "#3987e5", "#9ec5f4", "#f0efec", "#f3b0ae", "#e34948", "#9c2424"]

plt.rcParams.update(
    {
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "axes.edgecolor": BASE,
        "axes.labelcolor": INK2,
        "axes.titlecolor": INK,
        "axes.titlesize": 11,
        "axes.titleweight": "bold",
        "axes.labelsize": 9,
        "xtick.color": MUTED,
        "ytick.color": INK2,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "font.family": "sans-serif",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.color": GRID,
        "grid.linewidth": 0.6,
        "legend.frameon": False,
        "legend.fontsize": 8,
    }
)


def _caption(fig, text: str) -> None:
    fig.text(0.01, -0.02, text, fontsize=7.5, color=MUTED, ha="left", va="top", wrap=True)


KEY_LEVELS = [
    ("tod", "00-05", "Time 00:00-05:59 (vs 10-15)"),
    ("weekend", "yes", "Weekend"),
    ("light", "dark_not_lighted", "Dark, unlit (vs daylight)"),
    ("light", "dark_lighted", "Dark, lit"),
    ("weather", "rain", "Rain (vs clear)"),
    ("surface", "wet", "Wet surface (vs dry)"),
    ("surface", "snow_ice", "Snow / ice surface"),
    ("speed_limit", "50-55", "Speed limit 50-55 (vs 30-35)"),
    ("speed_limit", "70+", "Speed limit 70+"),
    ("interstate", "yes", "Interstate"),
    ("junction", "intersection", "Intersection (vs non-junction)"),
    ("urbanicity", "rural", "Rural area"),
    ("young_driver", "yes", "Driver 15-20 involved"),
    ("older_driver", "yes", "Driver 65+ involved"),
    ("any_heavy_truck", "yes", "Heavy truck / bus involved"),
    ("speeding", "yes", "Speeding-related"),
    ("alcohol_im", "yes", "Alcohol involved (imputed)"),
    ("any_motorcycle", "yes", "Motorcycle involved"),
]


def forest_crude_vs_adjusted(outcome: str = "fatal") -> None:
    d = load_table("severity", f"{outcome}_crude_vs_adjusted")
    d["level"] = d["level"].astype(str)
    rows = []
    for f, lv, lab in KEY_LEVELS:
        r = d[(d["factor"] == f) & (d["level"] == lv)]
        if len(r):
            rows.append((lab, r.iloc[0]))
    fig, ax = plt.subplots(figsize=(7.2, 0.34 * len(rows) + 1.2))
    y = np.arange(len(rows))[::-1]
    series = [
        ("crude", "Crude", BLUE, "o", -0.18),
        ("A_adj", "Adjusted: pre-crash (A)", ORANGE, "s", 0.0),
        ("B_adj", "Adjusted: + configuration (B)", AQUA, "D", 0.18),
    ]
    for key, name, color, marker, off in series:
        est = np.array([r[f"{key}_rr"] for _, r in rows], dtype=float)
        lo = np.array([r[f"{key}_rr_low"] for _, r in rows], dtype=float)
        hi = np.array([r[f"{key}_rr_high"] for _, r in rows], dtype=float)
        ax.hlines(y + off, lo, hi, color=color, linewidth=1.6)
        ax.plot(
            est,
            y + off,
            marker,
            color=color,
            markersize=5,
            label=name,
            markeredgecolor=SURFACE,
            markeredgewidth=0.8,
        )
    ax.axvline(1, color=MUTED, linewidth=1, linestyle="--")
    ax.set_xscale("log")
    ax.set_xticks([0.3, 0.5, 1, 2, 5, 10])
    ax.set_xticklabels(["0.3", "0.5", "1", "2", "5", "10"])
    ax.set_yticks(y)
    ax.set_yticklabels([lab for lab, _ in rows])
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("Risk ratio for a fatal outcome, given a police-reported crash (log scale)")
    ax.set_title(
        "Crude vs adjusted associations with crash fatality (CRSS 2016-2024)", loc="left", pad=26
    )
    ax.legend(
        loc="lower left", bbox_to_anchor=(0.0, 1.0), ncols=3, borderaxespad=0.2, handletextpad=0.3
    )
    _caption(
        fig,
        "Standardised risk ratios from survey-weighted logistic models; 95% CIs (Taylor linearisation, 42 df). "
        "Associations conditional on a crash, not causal effects. Source: outputs/tables/severity.",
    )
    save_figure(fig, MODULE, f"forest_{outcome}_crude_vs_adjusted")
    plt.close(fig)


def overrepresentation() -> None:
    d = load_table("descriptive", "frequency_vs_severity")
    d = d[d["overrep_ratio"].notna() & ~d["level"].astype(str).isin(["unknown", "no"])].copy()
    pick = [
        ("crash_type", "pedestrian"),
        ("any_motorcycle", "yes"),
        ("crash_type", "sv_rollover_first"),
        ("crash_type", "mv_head_on"),
        ("speeding", "yes"),
        ("light", "dark_not_lighted"),
        ("tod", "00-05"),
        ("speed_limit", "50-55"),
        ("speed_limit", "70+"),
        ("n_vehicles", "1"),
        ("weekend", "yes"),
        ("any_heavy_truck", "yes"),
        ("older_driver", "yes"),
        ("surface", "wet"),
        ("weather", "rain"),
        ("junction", "intersection"),
        ("young_driver", "yes"),
        ("crash_type", "mv_rear_end"),
    ]
    d["level"] = d["level"].astype(str)
    rows = [
        d[(d["factor"] == f) & (d["level"] == lv)].iloc[0]
        for f, lv in pick
        if len(d[(d["factor"] == f) & (d["level"] == lv)])
    ]
    labels = [level_label(r["factor"], str(r["level"])) for r in rows]
    fig, ax = plt.subplots(figsize=(7.2, 0.33 * len(rows) + 1.3))
    y = np.arange(len(rows))[::-1]
    a = np.array([100 * r["share_all_crashes"] for r in rows])
    f = np.array([100 * r["share_fatal_fars"] for r in rows])
    ax.hlines(y, np.minimum(a, f), np.maximum(a, f), color=BASE, linewidth=2)
    ax.plot(
        a,
        y,
        "o",
        color=BLUE,
        markersize=6,
        label="Share of all police-reported crashes (CRSS, weighted)",
    )
    ax.plot(f, y, "s", color=ORANGE, markersize=6, label="Share of fatal crashes (FARS census)")
    for yi, r in zip(y, rows, strict=True):
        ax.text(
            max(100 * r["share_all_crashes"], 100 * r["share_fatal_fars"]) * 1.15,
            yi,
            f"×{r['overrep_ratio']:.1f}",
            va="center",
            fontsize=7.5,
            color=INK2,
        )
    ax.set_xscale("log")
    ax.set_xticks([0.5, 1, 2, 5, 10, 20, 50])
    ax.set_xticklabels(["0.5%", "1%", "2%", "5%", "10%", "20%", "50%"])
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.grid(axis="y", visible=False)
    ax.set_title(
        "Common in crashes vs concentrated in fatal crashes, 2016-2024", loc="left", pad=30
    )
    ax.legend(loc="lower left", bbox_to_anchor=(0.0, 1.0), ncols=1, borderaxespad=0.2)
    _caption(
        fig,
        "×n = over-representation ratio (share of fatal crashes / share of all crashes). FARS and CRSS are estimated "
        "separately, never pooled. Source: outputs/tables/descriptive/frequency_vs_severity.csv",
    )
    save_figure(fig, MODULE, "overrepresentation")
    plt.close(fig)


LEVEL_TEXT = {
    ("crash_type", "pedestrian"): "Pedestrian crash",
    ("crash_type", "sv_rollover_first"): "Single vehicle, rollover first",
    ("crash_type", "mv_head_on"): "Head-on collision",
    ("crash_type", "mv_rear_end"): "Rear-end collision",
    ("any_motorcycle", "yes"): "Motorcycle involved",
    ("speeding", "yes"): "Speeding-related",
    ("light", "dark_not_lighted"): "Dark, unlit",
    ("tod", "00-05"): "00:00-05:59",
    ("speed_limit", "50-55"): "Speed limit 50-55 mph",
    ("speed_limit", "70+"): "Speed limit 70+ mph",
    ("n_vehicles", "1"): "Single vehicle",
    ("weekend", "yes"): "Weekend",
    ("any_heavy_truck", "yes"): "Heavy truck / bus involved",
    ("older_driver", "yes"): "Driver 65+ involved",
    ("surface", "wet"): "Wet surface",
    ("weather", "rain"): "Rain",
    ("junction", "intersection"): "Intersection",
    ("young_driver", "yes"): "Driver 15-20 involved",
}


def level_label(factor: str, level: str) -> str:
    return LEVEL_TEXT.get((factor, level), f"{specs_label(factor)}: {level}")


def specs_label(factor: str) -> str:
    from nhtsa_stats.analysis.specs import LABELS

    extra = {"crash_type": "Crash type", "n_vehicles": "Vehicles"}
    return extra.get(factor, LABELS.get(factor, factor))


def trends() -> None:
    fars = load_table("descriptive", "fars_annual")
    crss = load_table("descriptive", "crss_annual")
    fig, axes = plt.subplots(1, 2, figsize=(8.6, 3.2))
    ax = axes[0]
    ax.plot(fars["YEAR"], fars["deaths"] / 1000, "-o", color=BLUE, linewidth=2, markersize=5)
    for x, v in zip(fars["YEAR"], fars["deaths"], strict=True):
        if x in (2016, 2019, 2021, 2024):
            ax.annotate(
                f"{v:,}",
                (x, v / 1000),
                textcoords="offset points",
                xytext=(0, 7),
                ha="center",
                fontsize=7.5,
                color=INK2,
            )
    ax.set_title("Deaths (FARS census, observed)", loc="left")
    ax.set_ylabel("Thousands")
    ax.set_ylim(30, 46)
    ax = axes[1]
    ax.fill_between(
        crss["YEAR"],
        100 * crss["fatal_share_low"],
        100 * crss["fatal_share_high"],
        color=BLUE,
        alpha=0.15,
        linewidth=0,
    )
    ax.plot(crss["YEAR"], 100 * crss["fatal_share"], "-o", color=BLUE, linewidth=2, markersize=5)
    ax.set_title("Fatal share of police-reported crashes (CRSS)", loc="left")
    ax.set_ylabel("% of crashes with known severity")
    ax.set_ylim(0, 0.8)
    for a in axes:
        a.set_xticks(range(2016, 2025, 2))
    _caption(
        fig,
        "Right panel: design-based estimate with 95% CI (logit-scale). The two panels use different sources and "
        "are shown side by side, not on a shared axis.",
    )
    fig.tight_layout()
    save_figure(fig, MODULE, "trends")
    plt.close(fig)


def interaction_panel() -> None:
    d = load_table("interactions", "pairs_fatal")
    d = d[d["ic"].notna()].copy()
    d = d.sort_values("ic")
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 0.33 * len(d) + 1.4), sharey=True)
    y = np.arange(len(d))
    ax = axes[0]
    ax.hlines(y, 1000 * d["ic_low"], 1000 * d["ic_high"], color=BLUE, linewidth=1.6)
    ax.plot(1000 * d["ic"], y, "o", color=BLUE, markersize=5)
    ax.axvline(0, color=MUTED, linestyle="--", linewidth=1)
    ax.set_xscale("symlog", linthresh=5, linscale=0.8)
    ticks = [-5, 0, 5, 10, 20, 50, 100, 200]
    ax.set_xticks(ticks)
    ax.set_xticklabels([str(t) for t in ticks])
    ax.set_xlabel("Additive interaction: excess fatal crashes per 1,000 (symlog)")
    ax.set_yticks(y)
    ax.set_yticklabels(d["pair"].str.replace("_", " "))
    ax.set_title("Additive scale (IC)", loc="left")
    ax = axes[1]
    ax.hlines(y, d["ratio_of_rr_low"], d["ratio_of_rr_high"], color=ORANGE, linewidth=1.6)
    ax.plot(d["ratio_of_rr"], y, "s", color=ORANGE, markersize=5)
    ax.axvline(1, color=MUTED, linestyle="--", linewidth=1)
    ax.set_xscale("log")
    ax.set_xticks([0.4, 0.6, 1, 1.5, 2])
    ax.set_xticklabels(["0.4", "0.6", "1", "1.5", "2"])
    ax.set_xlabel("Multiplicative interaction: RR11 / (RR10 x RR01) (log)")
    ax.set_title("Multiplicative scale", loc="left")
    for a in axes:
        a.grid(axis="y", visible=False)
    fig.suptitle(
        "Do circumstances amplify each other? Pre-specified pairs, fatal outcome, CRSS 2016-2024",
        x=0.01,
        ha="left",
        fontsize=11,
        fontweight="bold",
    )
    _caption(
        fig,
        "Adjusted risks from survey-weighted models with one product term per pair; 95% CIs. IC > 0: joint excess risk larger "
        "than the sum of the separate excesses. Source: outputs/tables/interactions/pairs_fatal.csv",
    )
    fig.tight_layout()
    save_figure(fig, MODULE, "interactions")
    plt.close(fig)


def qba_heatmap() -> None:
    q = load_table("measurement", "qba_grid")
    fig, axes = plt.subplots(1, 2, figsize=(8.6, 3.0))
    from matplotlib.colors import LinearSegmentedColormap, LogNorm

    cmap = LinearSegmentedColormap.from_list("div", DIVERGING)
    for ax, var, title in (
        (axes[0], "speeding", "Speeding-related"),
        (axes[1], "alcohol_im", "Alcohol involved"),
    ):
        s = q[(q["exposure"] == var) & (q["specificity"] == 1.0)]
        piv = s.pivot(index="se_fatal", columns="se_nonfatal", values="rr_corrected").sort_index(
            ascending=False
        )
        norm = LogNorm(vmin=1 / 8, vmax=8)
        ax.imshow(piv.clip(lower=1 / 8, upper=8).to_numpy(), cmap=cmap, norm=norm, aspect="auto")
        for i in range(piv.shape[0]):
            for j in range(piv.shape[1]):
                v = piv.iloc[i, j]
                ax.text(
                    j,
                    i,
                    "n/a" if not np.isfinite(v) else f"{v:.1f}",
                    ha="center",
                    va="center",
                    fontsize=7,
                    color=INK if np.isfinite(v) and 0.4 < v < 2.5 else SURFACE,
                )
        ax.set_xticks(range(piv.shape[1]))
        ax.set_xticklabels([f"{c:.1f}" for c in piv.columns])
        ax.set_yticks(range(piv.shape[0]))
        ax.set_yticklabels([f"{c:.1f}" for c in piv.index])
        ax.set_xlabel("Recording sensitivity in non-fatal crashes")
        ax.set_ylabel("Sensitivity in fatal crashes")
        ax.set_title(f"{title}: observed crude RR {s['rr_observed'].iloc[0]:.1f}", loc="left")
        ax.grid(False)
    _caption(
        fig,
        "Cells: crude fatal risk ratio after correcting for outcome-dependent under-recording (specificity 1). Blue < 1 < red. "
        "Source: outputs/tables/measurement/qba_grid.csv",
    )
    fig.tight_layout()
    save_figure(fig, MODULE, "qba_heatmap")
    plt.close(fig)


def pedestrians() -> None:
    d = load_table("vulnerable", "pedestrian_killed_contrasts")
    fig, axes = plt.subplots(1, 2, figsize=(8.6, 3.0))
    for ax, factor, title, ref in (
        (axes[0], "str_speed_limit", "Posted speed limit (mph)", "<=25"),
        (axes[1], "striking", "Striking vehicle", "car"),
    ):
        s = d[
            (d["factor"] == factor)
            & ~d["level"].isin(["unknown", "other_unknown", "none_nontrafficway"])
        ]
        if factor == "striking":
            s = s[s["n_events"] >= 20]
        x = np.arange(len(s))
        ax.vlines(x, s["adj_rr_low"], s["adj_rr_high"], color=BLUE, linewidth=1.6)
        ax.plot(x, s["adj_rr"], "o", color=BLUE, markersize=6, label="Adjusted RR")
        ax.plot(x, s["crude_rr"], "s", color=ORANGE, markersize=5, label="Crude RR", alpha=0.9)
        ax.axhline(1, color=MUTED, linestyle="--", linewidth=1)
        ax.set_yscale("log")
        ax.set_xticks(x)
        ax.set_xticklabels(s["level"], rotation=0)
        ax.set_title(f"{title} (ref: {ref})", loc="left")
        ax.grid(axis="x", visible=False)
    axes[0].set_ylabel("Risk ratio of death when struck (log)")
    axes[1].legend(loc="upper left")
    _caption(
        fig,
        "CRSS pedestrians 2016-2024 (survey-weighted, 95% CI); adjusted for speed limit, light, location, age, sex, time, "
        "region, area, alcohol, striking-vehicle speeding, year. Source: outputs/tables/vulnerable.",
    )
    fig.tight_layout()
    save_figure(fig, MODULE, "pedestrians")
    plt.close(fig)


def relative_involvement() -> None:
    d = load_table("exposure", "relative_involvement")
    s = d[
        (d["factor"] == "age_band")
        & (d["stratum"] == "all")
        & ~d["level"].isin(["unknown", "0-14"])
    ]
    order = ["15-20", "21-24", "25-34", "35-44", "45-54", "55-64", "65-74", "75+"]
    s = s.set_index("level").loc[order].reset_index()
    sev = load_table("severity", "fatal_crude_vs_adjusted")
    fig, ax = plt.subplots(figsize=(6.2, 3.0))
    x = np.arange(len(s))
    ax.vlines(x, s["rir_low"], s["rir_high"], color=BLUE, linewidth=1.6)
    ax.plot(x, s["rir"], "-o", color=BLUE, markersize=6)
    ax.axhline(1, color=MUTED, linestyle="--", linewidth=1)
    ax.set_xticks(x)
    ax.set_xticklabels(order)
    ax.set_xlabel("Driver age")
    ax.set_ylabel("Relative involvement ratio")
    ax.set_title("Who is over-involved as the culpable driver? (QIE, CRSS)", loc="left")
    del sev
    _caption(
        fig,
        "Two-vehicle crashes with exactly one culpable driver (action-based definition C1); RIR = culpable share / non-culpable "
        "share. Relative, assumption-dependent; not a crash rate. Source: outputs/tables/exposure.",
    )
    fig.tight_layout()
    save_figure(fig, MODULE, "relative_involvement_age")
    plt.close(fig)


def burden() -> None:
    d = load_table("burden", "attributable_fractions_fatal")
    labels = {
        "alcohol_removed": "Alcohol removed",
        "high_speed_roads_to_40_45": "50+ mph roads as 40-45 mph",
        "speeding_removed": "Speeding removed",
        "unlit_to_lit": "Dark-unlit as lit",
        "speeding_and_alcohol_removed": "Speeding and alcohol removed",
    }
    d = d.sort_values("af")
    fig, ax = plt.subplots(figsize=(6.6, 2.6))
    y = np.arange(len(d))
    ax.barh(y, 100 * d["af"], color=BLUE, height=0.55)
    ax.hlines(y, 100 * d["af_low"], 100 * d["af_high"], color=INK2, linewidth=1.2)
    for yi, (_, r) in zip(y, d.iterrows(), strict=True):
        ax.text(
            100 * r["af_high"] + 0.6,
            yi,
            f"{100 * r['af']:.1f}%  (~{r['fars_scaled_deaths_per_year']:,.0f}/yr)",
            va="center",
            fontsize=7.5,
            color=INK2,
        )
    ax.set_yticks(y)
    ax.set_yticklabels([labels.get(s, s) for s in d["shift"]])
    ax.set_xlim(0, 45)
    ax.set_xlabel("Share of fatal crashes (model-predicted, severity pathway only)")
    ax.grid(axis="y", visible=False)
    ax.set_title("Severity-pathway attributable fractions (hypothetical shifts)", loc="left")
    _caption(
        fig,
        "g-computation from the CRSS model; deaths scaled to mean FARS 2022-2024. Assumes the crash still occurs, no "
        "unmeasured confounding and correct measurement. Not lives saved. Source: outputs/tables/burden.",
    )
    fig.tight_layout()
    save_figure(fig, MODULE, "burden")
    plt.close(fig)


def run() -> dict:
    done = {}
    for name, fn in (
        ("forest_fatal", forest_crude_vs_adjusted),
        ("overrep", overrepresentation),
        ("trends", trends),
        ("interactions", interaction_panel),
        ("qba", qba_heatmap),
        ("pedestrians", pedestrians),
        ("qie", relative_involvement),
        ("burden", burden),
    ):
        try:
            fn()
            done[name] = "ok"
        except FileNotFoundError as exc:
            log.warning("figure %s skipped: %s", name, exc)
            done[name] = f"skipped: {exc}"
    return done
