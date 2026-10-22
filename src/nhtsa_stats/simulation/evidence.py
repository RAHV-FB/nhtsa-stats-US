"""Evidence ledger: what the database says about each candidate intervention (RQ9).

For every intervention the ledger records, with provenance:

1. the risk factor it targets and how that factor is measured here;
2. prevalence among all police-reported crashes (CRSS) and among fatal crashes (FARS);
3. FARS deaths in the targeted segment (observed, mean of 2022-2024);
4. the adjusted severity association (CRSS model A) and its robustness to measurement error;
5. relevant interactions (pre-specified pairs with Holm-adjusted evidence);
6. who is most affected (FARS deaths in the segment by age, sex, person type, time);
7. the severity-pathway attributable fraction where computed;
8. whether the database contains *any* evidence that the intervention changes the factor
   (it never does: no enforcement, camera, testing-programme or campaign data exist);
9. the assumptions a numeric projection would require;
10. a verdict on whether a defensible numeric policy-effect estimate is possible.

The ledger is the bridge between empirical findings and the simulator: it fixes which
numbers in Layer A of the simulator are observed / estimated / adjusted associations, and which
inputs must come from the user.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from nhtsa_stats.analysis import data
from nhtsa_stats.processing import harmonize as h
from nhtsa_stats.reporting.io import load_table, save_json, save_table

log = logging.getLogger(__name__)
MODULE = "policy"
WINDOW = (2022, 2023, 2024)
LPV = list(h.LPV_BODY_GROUPS)

NO_INTERVENTION_DATA = (
    "None. The 36 archives contain no records of cameras, enforcement intensity, checkpoints, roadside tests "
    "performed, citations, campaigns or programme costs (verified against outputs/audit/column_inventory.csv)."
)


def _tab(module: str, name: str) -> pd.DataFrame | None:
    try:
        return load_table(module, name)
    except FileNotFoundError:
        log.warning("missing %s/%s", module, name)
        return None


def _row(df: pd.DataFrame | None, **match) -> pd.Series | None:
    if df is None:
        return None
    m = np.ones(len(df), dtype=bool)
    for k, v in match.items():
        m &= df[k].astype(str).to_numpy() == str(v)
    return df[m].iloc[0] if m.any() else None


def _fmt_ci(
    r: pd.Series | None, est: str, lo: str, hi: str, pct: bool = False, digits: int = 2
) -> str:
    if r is None or pd.isna(r.get(est)):
        return "not estimated"
    f = 100 if pct else 1
    suf = "%" if pct else ""
    return f"{f * r[est]:.{digits}f}{suf} ({f * r[lo]:.{digits}f}-{f * r[hi]:.{digits}f})"


def segment_deaths() -> dict[str, dict]:
    """Observed FARS deaths per year (mean 2022-2024) in each targeted segment, with profiles."""
    crash = data.fars_crash(WINDOW)
    per = data.fars_person(WINDOW)
    killed = per[per["killed"] == 1].copy()
    k = len(WINDOW)
    seg_crash = {
        "speeding": crash["speeding"] == 1,
        "alcohol_bac08": None,  # expected value over implicates, handled below
        "drugs_police_reported": crash["drugs"] == 1,
        "night_weekend": (crash["night"] == 1) & (crash["weekend"] == 1),
        "dark_unlit_pedestrian": (crash["light"] == "dark_not_lighted")
        & (crash["any_pedestrian"] == 1),
        "high_speed_road": crash["speed_limit"].isin(["50-55", "60-65", "70+"]),
    }
    out: dict[str, dict] = {}
    for name, mask in seg_crash.items():
        if name == "alcohol_bac08":
            deaths = float((crash["FATALS"] * crash["driver_bac08_prob"].fillna(0)).sum()) / k
            out[name] = {
                "deaths_per_year": deaths,
                "kind": "observed census x multiply-imputed BAC (expected value)",
            }
            continue
        ids = crash.loc[mask, ["YEAR", "case_id"]]
        kk = killed.merge(ids, on=["YEAR", "case_id"])
        out[name] = {
            "deaths_per_year": len(kk) / k,
            "fatal_crashes_per_year": int(mask.sum()) / k,
            "pct_male": 100 * (kk["sex"] == "male").mean(),
            "pct_age_15_34": 100 * kk["age"].between(15, 34).mean(),
            "pct_occupants": 100 * kk["ptype"].isin(["driver", "passenger"]).mean(),
            "kind": "observed (FARS census)",
        }
    lpv = killed[
        killed["ptype"].isin(["driver", "passenger"])
        & killed["body"].isin(LPV)
        & (killed["age"] >= 8)
    ]
    unb = lpv[lpv["restraint"] == "none"]
    out["unrestrained_lpv_occupants"] = {
        "deaths_per_year": len(unb) / k,
        "restraint_unknown_deaths_per_year": int(
            (~lpv["restraint"].isin(["belted", "none", "child_restraint"])).sum()
        )
        / k,
        "pct_male": 100 * (unb["sex"] == "male").mean(),
        "pct_age_15_34": 100 * unb["age"].between(15, 34).mean(),
        "pct_night": 100 * (unb["night"] == 1).mean(),
        "kind": "observed (FARS census; restraint police-reported)",
    }
    moto = killed[killed["body"].eq("motorcycle") & killed["ptype"].isin(["driver", "passenger"])]
    out["unhelmeted_motorcyclists"] = {
        "deaths_per_year": int((moto["helmet"] == "none").sum()) / k,
        "helmet_unknown_deaths_per_year": int((moto["helmet"] == "unknown").sum()) / k,
        "kind": "observed (FARS census)",
    }
    ped = killed[killed["ptype"] == "pedestrian"]
    out["pedestrians"] = {
        "deaths_per_year": len(ped) / k,
        "pct_dark": 100 * (ped["dark"] == 1).mean(),
        "kind": "observed (FARS census)",
    }
    return out


def measured_facts() -> dict[str, str]:
    """Numbers quoted inside ledger sentences, always read from the output tables."""
    facts: dict[str, str] = {}
    comp = _tab("measurement", "fars_crss_fatal_composition")
    r = _row(comp, YEAR="all", attribute="speeding")
    facts["speeding_crss_vs_fars"] = (
        f"CRSS records speeding in {100 * r['crss_share']:.0f}% of fatal crashes vs "
        f"{100 * r['fars_share']:.0f}% in FARS"
        if r is not None
        else ""
    )
    rr = _tab("measurement", "restraint_reporting")
    r = _row(rr, kabco=0)
    facts["belt_uninjured"] = f"{r['pct_belted_among_known']:.1f}%" if r is not None else "n/a"
    r4 = _row(rr, kabco=4)
    facts["belt_killed_none"] = f"{r4['pct_none_among_known']:.0f}%" if r4 is not None else "n/a"
    t = _tab("measurement", "fars_testing")
    if t is not None:
        nat = t[t["level"] == "national"]
        k = nat[nat["status"] == "killed"]
        sv = nat[nat["status"] == "survived"]
        facts["drug_tested"] = (
            f"killed drivers tested {k['pct_drug_tested'].min():.0f}-{k['pct_drug_tested'].max():.0f}% vs "
            f"survivors {sv['pct_drug_tested'].min():.0f}-{sv['pct_drug_tested'].max():.0f}% (2018-2024)"
        )
    u = _tab("measurement", "unknown_by_year")
    if u is not None:
        d = u[(u["field"] == "drugs") & (u["YEAR"] >= 2020)]
        facts["drug_unknown"] = f"{d['pct_unknown'].min():.0f}-{d['pct_unknown'].max():.0f}%"
    freq = _tab("descriptive", "frequency_vs_severity")
    p = _row(freq, factor="crash_type", level="pedestrian")
    facts["ped"] = (
        f"pedestrian crashes {100 * p['share_all_crashes']:.1f}% of crashes but {100 * p['share_fatal_fars']:.1f}% "
        f"of fatal crashes (over-representation x{p['overrep_ratio']:.1f})"
        if p is not None
        else ""
    )
    return facts


def build_ledger() -> pd.DataFrame:
    facts = measured_facts()
    freq = _tab("descriptive", "frequency_vs_severity")
    sev = _tab("severity", "fatal_crude_vs_adjusted")
    pairs = _tab("interactions", "pairs_fatal")
    af = _tab("burden", "attributable_fractions_fatal")
    qba = _tab("measurement", "qba_grid")
    belt = _tab("matched", "belt_effect")
    seg = segment_deaths()

    def pairs_for(token: str) -> str:
        if pairs is None:
            return "not available"
        sub = pairs[pairs["pair"].str.contains(token) & pairs["ic"].notna()]
        parts = []
        for _, r in sub.iterrows():
            add = (
                "additive excess"
                if r["ic_low"] > 0
                else ("additive deficit" if r["ic_high"] < 0 else "no clear additive interaction")
            )
            mul = (
                "super-multiplicative"
                if r["ratio_of_rr_low"] > 1
                else "sub-multiplicative"
                if r["ratio_of_rr_high"] < 1
                else "multiplicative"
            )
            explo = "" if str(r.get("prespecified", True)).lower() == "true" else " [exploratory]"
            parts.append(
                f"{r['pair']}{explo}: IC {1000 * r['ic']:+.1f}/1000 ({add}); "
                f"ratio of RRs {r['ratio_of_rr']:.2f} ({mul})"
            )
        return "; ".join(parts) if parts else "none estimated"

    def qba_text(var: str) -> str:
        if qba is None:
            return "not available"
        s = qba[(qba["exposure"] == var) & (qba["specificity"] == 1.0) & (qba["se_fatal"] == 0.8)]
        lo = s[s["se_nonfatal"] == 0.5]["rr_corrected"].iloc[0]
        hi = s[s["se_nonfatal"] == 0.8]["rr_corrected"].iloc[0]
        return (
            f"crude RR {s['rr_observed'].iloc[0]:.2f}; corrected RR {lo:.2f} if non-fatal recording sensitivity is 0.5 "
            f"and {hi:.2f} if 0.8 (fatal sensitivity 0.8)"
        )

    sp = _row(freq, factor="speeding", level="yes")
    stype = _tab("severity", "fatal_speeding_type")
    speed_rr = (
        "all speeding-related: "
        + _fmt_ci(
            _row(sev, factor="speeding", level="yes"), "A_adj_rr", "A_adj_rr_low", "A_adj_rr_high"
        )
        + "; exceeded limit / racing: "
        + _fmt_ci(
            _row(stype, level="exceeded_limit_or_racing"), "adj_rr", "adj_rr_low", "adj_rr_high"
        )
        + "; too fast for conditions: "
        + _fmt_ci(
            _row(stype, level="too_fast_for_conditions"), "adj_rr", "adj_rr_low", "adj_rr_high"
        )
    )
    al = _row(freq, factor="alcohol_im", level="yes")
    acs = _tab("measurement", "alcohol_coding_sensitivity")

    def alcohol_rr(period: str, coding: str) -> str:
        return _fmt_ci(
            _row(acs, period=period, coding=coding), "adj_rr", "adj_rr_low", "adj_rr_high"
        )

    dr = _row(freq, factor="drugs", level="yes")
    rows = [
        {
            "intervention": "Automated speed enforcement (speed cameras)",
            "target_factor": "Speeding-related crash (police judgement: exceeded limit, too fast for conditions, racing)",
            "prevalence_all_crashes": _fmt_ci(
                sp,
                "share_all_crashes",
                "share_all_crashes",
                "share_all_crashes",
                pct=True,
                digits=1,
            ).split(" (")[0]
            + " of police-reported crashes (CRSS)",
            "prevalence_fatal_crashes": f"{100 * sp['share_fatal_fars']:.1f}% of fatal crashes (FARS)"
            if sp is not None
            else "",
            "fars_deaths_per_year_in_segment": round(seg["speeding"]["deaths_per_year"]),
            "adjusted_severity_rr": speed_rr,
            "measurement_robustness": "Aggregate association FRAGILE: it mixes a strong association for exceeding "
            "the limit with none for 'too fast for conditions'. "
            + qba_text("speeding")
            + "; "
            + facts.get("speeding_crss_vs_fars", ""),
            "interactions": pairs_for("speeding"),
            "most_affected": f"{seg['speeding']['pct_male']:.0f}% of deaths male; {seg['speeding']['pct_age_15_34']:.0f}% aged 15-34",
            "severity_pathway_af": "all speeding: "
            + _fmt_ci(
                _row(af, shift="speeding_removed"), "af", "af_low", "af_high", pct=True, digits=1
            )
            + "; exceeded limit / racing only: "
            + _fmt_ci(
                _row(af, shift="exceeded_limit_removed"),
                "af",
                "af_low",
                "af_high",
                pct=True,
                digits=1,
            ),
            "evidence_intervention_changes_factor": NO_INTERVENTION_DATA,
            "assumptions_required": "cameras act on exceeding the posted limit, not on 'too fast for conditions'; "
            "camera units -> coverage of speeding exposure; behavioural response (reduction in speeding prevalence "
            "where covered; spillover); effect on crash occurrence; effect on severity of remaining crashes",
            "numeric_estimate_possible": "Only conditional/hypothetical (simulator + break-even).",
            "evidence_grade_target_association": "strong for exceeding the limit (large association); none detected for "
            "'too fast for conditions'; aggregate magnitude sensitive to ascertainment",
        },
        {
            "intervention": "Roadside alcohol testing / sobriety checkpoints",
            "target_factor": "Alcohol-involved crash (CRSS imputed police report; FARS multiply-imputed BAC >= 0.08)",
            "prevalence_all_crashes": f"{100 * al['share_all_crashes']:.1f}% of police-reported crashes (CRSS, imputed)"
            if al is not None
            else "",
            "prevalence_fatal_crashes": "see FARS driver BAC>=.08 share (descriptive/fars_composition_by_year)",
            "fars_deaths_per_year_in_segment": round(seg["alcohol_bac08"]["deaths_per_year"]),
            "adjusted_severity_rr": _fmt_ci(
                _row(sev, factor="alcohol_im", level="yes"),
                "A_adj_rr",
                "A_adj_rr_low",
                "A_adj_rr_high",
            ),
            "measurement_robustness": "Large under every coding, but the size depends on the coding: imputed "
            + alcohol_rr("2016-2018", "imputed (ALCHL_IM)")
            + " in 2016-2018 vs "
            + alcohol_rr("2019-2024", "imputed (ALCHL_IM)")
            + " in 2019-2024 (coding break); police-reported complete case "
            + alcohol_rr("2016-2024", "police, complete case")
            + ". "
            + qba_text("alcohol_im"),
            "interactions": pairs_for("alcohol"),
            "most_affected": "see FARS profile (night/weekend, young adult men; measurement module)",
            "severity_pathway_af": _fmt_ci(
                _row(af, shift="alcohol_removed"), "af", "af_low", "af_high", pct=True, digits=1
            ),
            "evidence_intervention_changes_factor": NO_INTERVENTION_DATA,
            "assumptions_required": "checks/year -> coverage; detection probability; deterrence elasticity of impaired-driving "
            "prevalence; effects on crash occurrence and severity",
            "numeric_estimate_possible": "Only conditional/hypothetical. The direction of the target association is "
            "among the most robust in the data; its size depends on alcohol coding.",
            "evidence_grade_target_association": "strong in direction (large under every coding and robust to plausible "
            "differential ascertainment); magnitude coding-dependent",
        },
        {
            "intervention": "Roadside drug testing",
            "target_factor": "Drug involvement (police-reported) / toxicology results",
            "prevalence_all_crashes": (
                f"{100 * dr['share_all_crashes']:.1f}% coded yes, but {100 * _row(freq, factor='drugs', level='unknown')['share_all_crashes']:.0f}% unknown (CRSS)"
                if dr is not None
                else ""
            ),
            "prevalence_fatal_crashes": "not estimable reliably: testing selective ("
            + facts.get("drug_tested", "")
            + ")",
            "fars_deaths_per_year_in_segment": round(
                seg["drugs_police_reported"]["deaths_per_year"]
            ),
            "adjusted_severity_rr": "NOT ESTIMATED: exposure measurement depends on severity and changed in 2019-2020; presence != impairment",
            "measurement_robustness": "UNUSABLE for severity association (crash-level unknown share "
            + facts.get("drug_unknown", "")
            + " in 2020-2024 by severity group; coding breaks 2019-2020)",
            "interactions": "not analysed (measurement)",
            "most_affected": "not reliably identifiable",
            "severity_pathway_af": "not estimated",
            "evidence_intervention_changes_factor": NO_INTERVENTION_DATA,
            "assumptions_required": "everything: prevalence of impairment, impairment-specific risk, test coverage, deterrence",
            "numeric_estimate_possible": "No defensible estimate from these data; simulator can only show what effect sizes would be required",
            "evidence_grade_target_association": "insufficient",
        },
        {
            "intervention": "Seat-belt (restraint) enforcement",
            "target_factor": "Unrestrained light-vehicle occupants",
            "prevalence_all_crashes": f"reported belt use {facts['belt_uninjured']} among uninjured CRSS occupants with known status "
            "(likely inflated by self-report)",
            "prevalence_fatal_crashes": f"{facts['belt_killed_none']} of killed CRSS LPV occupants with known status unrestrained",
            "fars_deaths_per_year_in_segment": round(
                seg["unrestrained_lpv_occupants"]["deaths_per_year"]
            ),
            "adjusted_severity_rr": (
                "within-vehicle (FARS matched): "
                + "; ".join(
                    f"{r['estimand']}: {r['estimate']:.2f} ({r['low']:.2f}-{r['high']:.2f}) [{r['method']}]"
                    for _, r in belt.iterrows()
                )
                if belt is not None and len(belt)
                else "pending matched module"
            ),
            "measurement_robustness": "survivor misreporting of belt use biases toward larger protective effects; sensitivity in matched module",
            "interactions": "restraint x age / crash type: person module",
            "most_affected": f"{seg['unrestrained_lpv_occupants']['pct_male']:.0f}% male; {seg['unrestrained_lpv_occupants']['pct_age_15_34']:.0f}% aged 15-34; "
            f"{seg['unrestrained_lpv_occupants']['pct_night']:.0f}% at night",
            "severity_pathway_af": "use belt effectiveness x unrestrained deaths in simulator",
            "evidence_intervention_changes_factor": NO_INTERVENTION_DATA,
            "assumptions_required": "share of unbelted occupants who would buckle up under enforcement; whether converters resemble "
            "other unbelted occupants (likely riskier)",
            "numeric_estimate_possible": "Closest to defensible: protection given a crash is estimated within vehicles; "
            "behaviour change remains an assumption",
            "evidence_grade_target_association": "strong for protection given a fatal crash (matched design), with misreporting caveat",
        },
        {
            "intervention": "Targeted enforcement in high-risk periods (night, weekend)",
            "target_factor": "Night (21:00-05:59) and weekend crashes",
            "prevalence_all_crashes": _fmt_ci(
                _row(freq, factor="tod", level="00-05"),
                "share_all_crashes",
                "share_all_crashes",
                "share_all_crashes",
                pct=True,
                digits=1,
            ).split(" (")[0]
            + " of crashes at 00-05",
            "prevalence_fatal_crashes": f"{100 * _row(freq, factor='tod', level='00-05')['share_fatal_fars']:.1f}% of fatal crashes at 00-05 (FARS)"
            if freq is not None
            else "",
            "fars_deaths_per_year_in_segment": round(seg["night_weekend"]["deaths_per_year"]),
            "adjusted_severity_rr": "00-05 vs 10-15: crude "
            + _fmt_ci(
                _row(sev, factor="tod", level="00-05"), "crude_rr", "crude_rr_low", "crude_rr_high"
            )
            + "; adjusted, light not held fixed "
            + _fmt_ci(
                _row(sev, factor="tod", level="00-05"),
                "Ax_adj_rr",
                "Ax_adj_rr_low",
                "Ax_adj_rr_high",
            )
            + "; adjusted, light held fixed "
            + _fmt_ci(
                _row(sev, factor="tod", level="00-05"), "A_adj_rr", "A_adj_rr_low", "A_adj_rr_high"
            ),
            "measurement_robustness": "time is well measured; the night excess is largely accounted for by alcohol, light, speed environment (confounding module)",
            "interactions": pairs_for("late_night"),
            "most_affected": "see confounding module",
            "severity_pathway_af": "not computed (time is a marker, not a modifiable cause)",
            "evidence_intervention_changes_factor": NO_INTERVENTION_DATA,
            "assumptions_required": "which behaviour the enforcement changes (alcohol, speeding) - model through those factors, not 'night'",
            "numeric_estimate_possible": "Only via the behaviour targeted (alcohol/speeding), conditional on assumptions",
            "evidence_grade_target_association": "time is a marker of risk composition rather than an independent target",
        },
        {
            "intervention": "Education / awareness campaigns",
            "target_factor": "Any behaviour",
            "prevalence_all_crashes": "n/a",
            "prevalence_fatal_crashes": "n/a",
            "fars_deaths_per_year_in_segment": np.nan,
            "adjusted_severity_rr": "n/a",
            "measurement_robustness": "n/a",
            "interactions": "n/a",
            "most_affected": "n/a",
            "severity_pathway_af": "n/a",
            "evidence_intervention_changes_factor": NO_INTERVENTION_DATA
            + " Campaign exposure is not recorded.",
            "assumptions_required": "campaign reach, behavioural change, persistence",
            "numeric_estimate_possible": "No; data cannot distinguish campaign effects from any other change",
            "evidence_grade_target_association": "n/a",
        },
        {
            "intervention": "Pedestrian safety: lighting, speed management, vehicle front-end design",
            "target_factor": "Pedestrian crashes in dark-unlit conditions and on higher-speed roads; striking-vehicle type",
            "prevalence_all_crashes": facts.get("ped", ""),
            "prevalence_fatal_crashes": f"pedestrians {seg['pedestrians']['pct_dark']:.0f}% of pedestrian deaths in the dark (FARS)",
            "fars_deaths_per_year_in_segment": round(seg["pedestrians"]["deaths_per_year"]),
            "adjusted_severity_rr": "see vulnerable module: speed-limit gradient, dark-unlit, SUV/pickup vs car",
            "measurement_robustness": "light, speed limit, location and vehicle type are objective; robust",
            "interactions": pairs_for("pedestrian"),
            "most_affected": "older pedestrians (75+), mid-block crossings, unlit roads",
            "severity_pathway_af": _fmt_ci(
                _row(af, shift="unlit_to_lit"), "af", "af_low", "af_high", pct=True, digits=1
            )
            + " (all crashes, unlit->lit)",
            "evidence_intervention_changes_factor": "None for programmes; the contrasts compare existing conditions, not interventions",
            "assumptions_required": "that adding lighting / lowering limits changes conditions to those of currently lit / lower-limit roads "
            "without changing exposure",
            "numeric_estimate_possible": "Conditional/hypothetical via the simulator's generic segment intervention",
            "evidence_grade_target_association": "strong (large, objective measures, consistent across adjustment)",
        },
    ]
    return pd.DataFrame(rows)


def run() -> dict:
    ledger = build_ledger()
    seg = segment_deaths()
    save_table(
        ledger,
        MODULE,
        "evidence_ledger",
        description="Evidence ledger: what the database can and cannot say about each candidate intervention",
        population="FARS 2022-2024 (deaths); CRSS 2016-2024 (associations)",
        unit="intervention",
        method="Assembled from descriptive, severity, measurement, interactions, burden and matched outputs",
        inputs=["outputs/tables/*"],
    )
    save_json(seg, MODULE, "segment_deaths")
    out = {"evidence_ledger": ledger, "segment_deaths": seg}
    try:  # the simulation engine's empirical baseline, if the engine is installed
        from nhtsa_stats.simulation import engine

        if hasattr(engine, "run"):
            out["engine"] = engine.run()
    except ImportError:
        log.warning("simulation engine not available")
    return out
