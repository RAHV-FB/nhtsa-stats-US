"""CRSS weighted fatal crashes / fatalities vs FARS census counts, with design SEs."""
import polars as pl, pandas as pd, numpy as np
from nhtsa_stats.ingestion.cache import load_table
from svy_lib import svy_total, design_summary
pd.set_option("display.width",250); pd.set_option("display.max_columns",40); pd.set_option("display.max_rows",400)
def P(d): print(d.to_pandas().to_string(index=False))
fa = load_table("FARS","accident",years=None,columns=["ST_CASE","STATE","FATALS"])
fp = load_table("FARS","person",years=None,columns=["ST_CASE","VEH_NO","PER_NO","INJ_SEV"])
f = fa.group_by("YEAR").agg(pl.len().alias("fars_crashes"), pl.col("FATALS").sum().alias("fars_FATALS_sum"), (pl.col("FATALS")==0).sum().alias("fars_fatals0")).join(
    fp.group_by("YEAR").agg((pl.col("INJ_SEV")==4).sum().alias("fars_persons_K")), on="YEAR").sort("YEAR")
ca = load_table("CRSS","accident",years=None,columns=["CASENUM","PSUSTRAT","PSU_VAR","WEIGHT","MAX_SEV","MAXSEV_IM","REGION"])
cp = load_table("CRSS","person",years=None,columns=["CASENUM","VEH_NO","PER_NO","PSUSTRAT","PSU_VAR","WEIGHT","INJ_SEV","INJSEV_IM"])
rows=[]
for y in range(2016,2025):
    a = ca.filter(pl.col("YEAR")==y); p = cp.filter(pl.col("YEAR")==y)
    r = dict(YEAR=y, crss_n_fatal=int((a["MAX_SEV"]==4).sum()), crss_n_fatal_im=int((a["MAXSEV_IM"]==4).sum()))
    for nm, df, expr in [("K_crash", a, (pl.col("MAX_SEV")==4).cast(pl.Float64)), ("K_crash_im", a, (pl.col("MAXSEV_IM")==4).cast(pl.Float64)),
                          ("K_pers", p, (pl.col("INJ_SEV")==4).cast(pl.Float64)), ("K_pers_im", p, (pl.col("INJSEV_IM")==4).cast(pl.Float64))]:
        est, se, nl = svy_total(df, expr)
        r[nm]=round(est,1); r[nm+"_se"]=round(se,0)
    r["crss_n_Kpers"]=int((p["INJ_SEV"]==4).sum())
    rows.append(r)
c = pl.DataFrame(rows)
m = f.join(c, on="YEAR")
m = m.with_columns(
    ((pl.col("K_crash")/pl.col("fars_crashes")-1)*100).round(1).alias("pct_diff_crash"),
    ((pl.col("K_crash_im")/pl.col("fars_crashes")-1)*100).round(2).alias("pct_diff_crash_im"),
    ((pl.col("K_pers")/pl.col("fars_persons_K")-1)*100).round(1).alias("pct_diff_pers"),
    ((pl.col("K_pers_im")/pl.col("fars_persons_K")-1)*100).round(1).alias("pct_diff_pers_im"),
    ((pl.col("K_crash")-pl.col("fars_crashes"))/pl.col("K_crash_se")).round(2).alias("z_crash"),
    ((pl.col("K_pers")-pl.col("fars_persons_K"))/pl.col("K_pers_se")).round(2).alias("z_pers"),
)
print("FARS vs CRSS"); P(m.select(["YEAR","fars_crashes","fars_FATALS_sum","fars_persons_K","fars_fatals0","crss_n_fatal","crss_n_fatal_im","crss_n_Kpers"]))
P(m.select(["YEAR","fars_crashes","K_crash","K_crash_se","pct_diff_crash","z_crash","K_crash_im","K_crash_im_se","pct_diff_crash_im"]))
P(m.select(["YEAR","fars_persons_K","K_pers","K_pers_se","pct_diff_pers","z_pers","K_pers_im","K_pers_im_se","pct_diff_pers_im"]))
print("exact K_crash_im values:"); print(c.select(["YEAR","K_crash_im"]).to_pandas().to_string(index=False))
# region comparison using REGION label state lists
reg = {1:"PA NJ NY NH VT RI MA ME CT",2:"OH IN IL MI WI MN ND SD NE IA MO KS",3:"MD DE DC WV VA KY TN NC SC GA FL AL MS LA AR OK TX",4:"MT ID WA OR CA NV NM AZ UT CO WY AK HI"}
ab = {"AL":1,"AK":2,"AZ":4,"AR":5,"CA":6,"CO":8,"CT":9,"DE":10,"DC":11,"FL":12,"GA":13,"HI":15,"ID":16,"IL":17,"IN":18,"IA":19,"KS":20,"KY":21,"LA":22,"ME":23,"MD":24,"MA":25,"MI":26,"MN":27,"MS":28,"MO":29,"MT":30,"NE":31,"NV":32,"NH":33,"NJ":34,"NM":35,"NY":36,"NC":37,"ND":38,"OH":39,"OK":40,"OR":41,"PA":42,"RI":44,"SC":45,"SD":46,"TN":47,"TX":48,"UT":49,"VT":50,"VA":51,"WA":53,"WV":54,"WI":55,"WY":56}
st2reg = {ab[s]:r for r,l in reg.items() for s in l.split()}
print("states mapped:", len(st2reg))
fr = fa.with_columns(pl.col("STATE").replace_strict(st2reg, default=None).alias("REGION")).group_by(["YEAR","REGION"]).agg(pl.len().alias("fars"))
print("FARS unmapped states:", fa.filter(~pl.col("STATE").is_in(list(st2reg))).height)
cr = ca.group_by(["YEAR","REGION"]).agg((pl.col("WEIGHT")*(pl.col("MAXSEV_IM")==4)).sum().round(0).alias("crss_im"), (pl.col("WEIGHT")*(pl.col("MAX_SEV")==4)).sum().round(0).alias("crss"))
x = fr.join(cr, on=["YEAR","REGION"]).with_columns(((pl.col("crss_im")/pl.col("fars")-1)*100).round(1).alias("pct_im"),((pl.col("crss")/pl.col("fars")-1)*100).round(1).alias("pct")).sort(["YEAR","REGION"])
print("Fatal crashes by region: FARS vs CRSS (MAXSEV_IM=4 / MAX_SEV=4)"); P(x)
