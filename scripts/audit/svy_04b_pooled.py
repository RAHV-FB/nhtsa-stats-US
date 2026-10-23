"""Pooled-year variance: stable PSU_VAR clusters vs year-specific clusters; year differences; person-level deff."""
import polars as pl, numpy as np
from nhtsa_stats.ingestion.cache import load_table
from svy_lib import _var_from_cluster_totals
a = load_table("CRSS","accident",years=None,columns=["CASENUM","PSUSTRAT","PSU_VAR","WEIGHT","MAXSEV_IM","ALCHL_IM"])
a = a.with_columns((pl.col("YEAR")*1000+pl.col("PSU_VAR")).alias("YPV"), (pl.col("YEAR")*100+pl.col("PSUSTRAT")).alias("YSTR"))
def ratio_lin(df, y, by_year_weightnorm=False):
    Y=(df["WEIGHT"]*y).sum(); X=df["WEIGHT"].sum(); R=Y/X
    return R, df["WEIGHT"]*(y-R)/X
def var_of(df, u, strat, clus):
    t = df.with_columns(pl.Series("u",u)).group_by([strat,clus]).agg(pl.col("u").sum()).rename({strat:"h"})
    V,_ = _var_from_cluster_totals(t,["u"]); return V[0,0]
for lab, expr in [("fatal", (pl.col("MAXSEV_IM")==4)), ("injury", pl.col("MAXSEV_IM").is_in([1,2,3,4,5])), ("alcohol", pl.col("ALCHL_IM")==1)]:
    d = a.filter(pl.col("YEAR")>=2019)
    y = d.select(expr.cast(pl.Float64)).to_series()
    # pooled proportion: sum of weights across years (average-of-years total ratio)
    R,u = ratio_lin(d,y)
    v_stable = var_of(d,u,"PSUSTRAT","PSU_VAR"); v_year = var_of(d,u,"YSTR","YPV")
    print(f"{lab} pooled 2019-24 p={R*100:.3f}%  se(stable PSU_VAR clusters)={np.sqrt(v_stable)*100:.4f}  se(year x PSU_VAR clusters)={np.sqrt(v_year)*100:.4f}  ratio={np.sqrt(v_stable/v_year):.3f}")
    # difference 2020-2019
    for y1,y0 in [(2020,2019),(2024,2019),(2021,2020)]:
        d1=a.filter(pl.col("YEAR")==y1); d0=a.filter(pl.col("YEAR")==y0)
        R1,u1=ratio_lin(d1,d1.select(expr.cast(pl.Float64)).to_series()); R0,u0=ratio_lin(d0,d0.select(expr.cast(pl.Float64)).to_series())
        dd=pl.concat([d1,d0]); uu=pl.concat([u1,-u0])
        vs=var_of(dd,uu,"PSUSTRAT","PSU_VAR"); vi=var_of(dd,uu,"YSTR","YPV")
        print(f"   diff {y1}-{y0}: {100*(R1-R0):.3f} pp  se(shared clusters)={100*np.sqrt(vs):.4f}  se(independent)={100*np.sqrt(vi):.4f}  ratio={np.sqrt(vs/vi):.3f}")
# person-level
p = load_table("CRSS","person",years=[2019,2022,2024],columns=["CASENUM","PSUSTRAT","PSU_VAR","WEIGHT","INJSEV_IM","PER_TYP"])
for y in [2019,2022,2024]:
    d=p.filter(pl.col("YEAR")==y)
    yy=d.select(pl.col("INJSEV_IM").is_in([3,4]).cast(pl.Float64)).to_series()
    R,u=ratio_lin(d,yy)
    v=var_of(d,u,"PSUSTRAT","PSU_VAR")
    d2=d.with_columns(pl.lit(1).alias("one"))
    vc=var_of(d2,u,"one","CASENUM")  # weights + crash clustering only
    srs=R*(1-R)/d.height
    print(f"person KA share {y}: p={R*100:.3f}% n={d.height} se={np.sqrt(v)*100:.4f} deff={v/srs:.2f} deff(weights+crash clusters only)={vc/srs:.2f}")
