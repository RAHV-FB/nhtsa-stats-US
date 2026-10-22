"""Bias-analysis arithmetic (software tests on synthetic counts)."""

from __future__ import annotations

import numpy as np
import pytest

from nhtsa_stats.analysis.measurement import corrected_rr


def test_perfect_classification_returns_observed_rr():
    a, b, c, d = 30.0, 970.0, 10.0, 990.0
    rr_obs = (a / (a + b)) / (c / (c + d))
    assert corrected_rr(a, b, c, d, 1.0, 1.0) == pytest.approx(rr_obs)


def test_known_misclassification_is_undone():
    # Truth: exposed 1000 (60 fatal), unexposed 4000 (40 fatal) -> RR = 6.
    A, B, C, D = 60.0, 940.0, 40.0, 3960.0
    se_f, se_n = 0.9, 0.5
    a = A * se_f
    c = C + A * (1 - se_f)
    b = B * se_n
    d = D + B * (1 - se_n)
    assert corrected_rr(a, b, c, d, se_f, se_n) == pytest.approx(6.0)


def test_lower_nonfatal_sensitivity_shrinks_rr():
    a, b, c, d = 50.0, 950.0, 50.0, 3950.0
    rr_low = corrected_rr(a, b, c, d, 1.0, 0.5)
    rr_high = corrected_rr(a, b, c, d, 1.0, 1.0)
    assert rr_low < rr_high


def test_impossible_correction_returns_nan():
    assert np.isnan(corrected_rr(5.0, 10.0, 1.0, 1.0, 1.0, 0.05))
