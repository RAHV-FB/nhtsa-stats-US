"""Minimal with-replacement (ultimate cluster) Taylor-linearisation variance, independent of src/."""
import numpy as np, polars as pl

def _var_from_cluster_totals(ct: pl.DataFrame, zcols, strat="h", lonely="certainty"):
    """ct has one row per cluster with stratum column 'h' and cluster totals zcols. Returns covariance matrix."""
    p = len(zcols); V = np.zeros((p,p)); n_lonely = 0
    for _, g in ct.group_by(strat):
        Z = g.select(zcols).to_numpy().astype(float)
        nh = Z.shape[0]
        if nh < 2:
            n_lonely += 1
            continue  # contributes 0 (treated as certainty)
        D = Z - Z.mean(axis=0)
        V += nh/(nh-1) * D.T @ D
    return V, n_lonely

def cluster_totals(df: pl.DataFrame, zexprs: dict, strat: str, clus: str, frame: pl.DataFrame | None = None):
    """Weighted totals by (strat, clus). frame = full list of (strat, clus) to keep empty clusters."""
    ct = df.group_by([strat, clus]).agg([e.sum().alias(k) for k, e in zexprs.items()])
    if frame is not None:
        ct = frame.join(ct, on=[strat, clus], how="left").fill_null(0.0)
    return ct.rename({strat: "h"})

def svy_total(df, y, w="WEIGHT", strat="PSUSTRAT", clus="PSU_VAR"):
    frame = df.select([strat, clus]).unique()
    ct = cluster_totals(df, {"z": pl.col(w)*y}, strat, clus, frame)
    V, nl = _var_from_cluster_totals(ct, ["z"])
    est = float(df.select((pl.col(w)*y).sum()).item())
    return est, float(np.sqrt(V[0,0])), nl

def svy_ratio(df, y, x, w="WEIGHT", strat="PSUSTRAT", clus="PSU_VAR"):
    """R = sum w y / sum w x with linearised SE. y, x are polars expressions (0 outside domain)."""
    Y = float(df.select((pl.col(w)*y).sum()).item()); X = float(df.select((pl.col(w)*x).sum()).item())
    R = Y/X
    frame = df.select([strat, clus]).unique()
    ct = cluster_totals(df, {"u": pl.col(w)*(y - R*x)/X}, strat, clus, frame)
    V, nl = _var_from_cluster_totals(ct, ["u"])
    return R, float(np.sqrt(V[0,0])), nl

def design_summary(df, strat="PSUSTRAT", clus="PSU_VAR"):
    g = df.select([strat, clus]).unique()
    nh = g.group_by(strat).len()
    return dict(strata=nh.height, clusters=g.height, df=g.height-nh.height, lonely=int((nh["len"]<2).sum()))
