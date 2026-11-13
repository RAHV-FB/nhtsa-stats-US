"""Multiplicity adjustments over a family that is fixed in advance.

The family size ``m`` is the number of registered tests, not the number of tests that happened to
produce a p-value.  A test that could not be estimated (NaN / non-finite p) therefore stays in
the family as a test that cannot be rejected: it enters the adjustment with p = 1, it still
counts toward ``m``, and its own adjusted p-value is reported as NaN ("not estimable").
Dropping such tests instead would shrink ``m`` and make every other adjusted p-value smaller.
"""

from __future__ import annotations

import numpy as np


def _family(p) -> tuple[np.ndarray, np.ndarray]:
    vals = np.asarray(p, dtype=float)
    ok = np.isfinite(vals)
    return np.where(ok, vals, 1.0), ok


def holm(p) -> np.ndarray:
    """Holm step-down adjusted p-values over ``len(p)`` registered tests (NaN stays NaN)."""
    v, ok = _family(p)
    order = np.argsort(v, kind="stable")
    m = len(v)
    adj = np.empty(m)
    running = 0.0
    for rank, idx in enumerate(order):
        running = max(running, min(1.0, (m - rank) * v[idx]))
        adj[idx] = running
    return np.where(ok, adj, np.nan)


def benjamini_hochberg(p) -> np.ndarray:
    """Benjamini-Hochberg adjusted p-values over ``len(p)`` registered tests (NaN stays NaN)."""
    v, ok = _family(p)
    order = np.argsort(v, kind="stable")
    m = len(v)
    adj = np.empty(m)
    running = 1.0
    for rank in range(m - 1, -1, -1):
        idx = order[rank]
        running = min(running, v[idx] * m / (rank + 1))
        adj[idx] = min(running, 1.0)
    return np.where(ok, adj, np.nan)
