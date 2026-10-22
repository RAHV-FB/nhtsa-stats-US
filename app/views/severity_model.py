"""Section D: conditional severity predictions from the documented survey model."""

from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from common import FACTOR_CHOICES, kind_note, output_json
from nhtsa_stats.analysis.survey import ModelSpec


def predict(model: dict, conditions: dict) -> tuple[float, float, float]:
    spec = ModelSpec(categorical=model["levels"])
    x, names = spec.design_matrix(pd.DataFrame([conditions]))
    assert names == model["terms"], "model terms do not match specification"
    beta = np.asarray(model["coef"])
    v = np.asarray(model["vcov"])
    eta = float(x[0] @ beta)
    se = float(np.sqrt(x[0] @ v @ x[0]))
    from scipy import stats

    t = stats.t.ppf(0.975, model["design_df"])

    def s(z: float) -> float:
        return 1 / (1 + np.exp(-z))

    return s(eta), s(eta - t * se), s(eta + t * se)


def render() -> None:
    st.title("Severity model")
    st.markdown(
        "Predicted probability that a **police-reported crash** with the chosen circumstances is fatal (or fatal/"
        "serious). This is the survey-weighted logistic model used for the adjusted associations, fitted to CRSS "
        "2016-2024. **It does not estimate the chance of having a crash** on a trip - the data contain no exposure."
    )
    outcome = st.radio(
        "Outcome",
        ["fatal", "ka"],
        horizontal=True,
        format_func=lambda o: "Fatal (K)" if o == "fatal" else "Fatal or serious (KA)",
    )
    which = st.radio(
        "Model",
        ["A", "B"],
        horizontal=True,
        format_func=lambda s: (
            "Pre-crash circumstances (A)" if s == "A" else "+ crash configuration (B)"
        ),
    )
    model = output_json("severity", f"model_{which}_{outcome}")
    if model is None:
        st.info("Run `nhtsa analyze severity` first.")
        return
    cols = st.columns(3)
    cond = {}
    for i, (var, levels) in enumerate(model["levels"].items()):
        label = FACTOR_CHOICES.get(var, var)
        default = levels[0] if var != "YEAR" else levels[-1]
        cond[var] = cols[i % 3].selectbox(
            label, levels, index=levels.index(default), key=f"sm_{var}"
        )
    p, lo, hi = predict(model, cond)
    ref = {v: (lv[0] if v != "YEAR" else lv[-1]) for v, lv in model["levels"].items()}
    p0, _, _ = predict(model, ref)
    kind_note("predicted")
    c1, c2 = st.columns(2)
    c1.metric(
        "Predicted probability", f"{100 * p:.2f}%", help=f"95% CI {100 * lo:.2f}% – {100 * hi:.2f}%"
    )
    c2.metric(
        "Relative to all-reference crash",
        f"{p / p0:.1f}×",
        help=f"Reference-level crash: {100 * p0:.3f}%",
    )
    st.caption(
        f"95% confidence interval {100 * lo:.2f}% – {100 * hi:.2f}% (design-based covariance; reflects sampling "
        f"uncertainty in the coefficients only, not model misspecification). Fitted on {model['n']:,} crashes with "
        f"{model['events']:,} events. Inputs marked 'unknown' reproduce the reporting pattern of crashes with "
        "missing information; they do not mean 'no'."
    )
    with st.expander("What this prediction is and is not"):
        st.markdown(
            "- **Is:** the model-predicted share of crashes with these recorded circumstances that end in the selected "
            "outcome, averaged over unrecorded variation.\n"
            "- **Is not:** a causal effect of changing any input; a trip-level crash probability; a prediction for "
            "unreported crashes.\n"
            "- Police-reported speeding and alcohol are ascertained more thoroughly in severe crashes, which inflates "
            "their apparent effect (see Methodology).\n"
            "- Temporal validation and machine-learning comparisons: `docs/model_validation.md`."
        )
    try:
        from nhtsa_stats.models import severity_ml

        if hasattr(severity_ml, "predict_crash_fatal_risk") and outcome == "fatal":
            with st.expander("Machine-learning comparison model"):
                try:
                    st.json(severity_ml.predict_crash_fatal_risk(cond))
                except Exception as exc:  # model artefacts may be absent
                    st.caption(f"ML model unavailable: {exc}")
    except ImportError:
        pass
