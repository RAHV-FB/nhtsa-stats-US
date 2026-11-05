"""Shared helpers for P07: build the case frame, fit the project's case model, margins."""
import sys, itertools
import numpy as np, pandas as pd
from nhtsa_stats.analysis import cases, multifactor
from nhtsa_stats.analysis.survey import ModelSpec, SurveyLogit, logit_ci

CASE = dict(speeding="exceeded_limit", alcohol="yes", unbelted="yes", night="night", single_vehicle="yes")
REF = {n: lv[0] for n, (_, lv) in cases.GRID.items()}

def scen_funcs(factors, scenarios):
    out = {}
    for s in scenarios:
        a = {factors[n][0]: v for n, v in s.items()}
        out[cases.scenario_key(s)] = lambda d, a=a: d.assign(**a)
    return out

def fit_alt(df, design, factors, products="all", extra_cov=None, covs=None, outcome="drv_killed"):
    """Like cases.fit but with choice of product set: 'all' (project), 'pairs' (<=2-way), 'main'."""
    covs = cases.COVARIATES if covs is None else covs
    cols = list(dict.fromkeys([*(c for c, _ in factors.values()), *covs]))
    work = df[[*cols, outcome]].copy()
    for c in cols:
        work[c] = np.asarray(work[c], dtype=object)
    cells, cd = cases.collapse_cells(work, design, cols, outcome)
    cats = {}
    for c in cols:
        fl = next((lv for col, lv in factors.values() if col == c), None)
        ref = fl[0] if fl else pd.Series(work[c]).value_counts().index[0]
        cats[c] = [ref, *sorted((v for v in pd.unique(work[c]) if v != ref), key=str)]
    observed = {n: (col, cats[col]) for n, (col, _) in factors.items()}
    prods = cases._products(observed)
    if products == "pairs":
        prods = [p for p in prods if len(p) <= 2]
    elif products == "main":
        prods = []
    m = SurveyLogit(ModelSpec(categorical=cats, products=prods),
                    ridge=cases.RIDGE * len(cells) / len(work))
    m.fit(cells, cells[outcome].to_numpy(float), cd)
    return m, cells, cd, prods
