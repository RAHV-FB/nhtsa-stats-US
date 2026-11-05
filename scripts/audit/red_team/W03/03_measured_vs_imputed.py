"""Attack A (corrected scale): ALC_RES is thousandths (0-940, 995=.95+; 996-999 not tested/unknown).
How much of the 66.3% .15+ / 7.4% DWI / 23.7% invalid-licence rests on measured vs MI-imputed BAC?
Also: fully-measured 'drunk' (ALC_RES>=80) subset, and implicate-wise stability."""
import polars as pl
from nhtsa_stats.analysis import deaths as D
d=D.build_driver_frame()
per=D.load_table("FARS","person",None,["YEAR","ST_CASE","VEH_NO","PER_NO","ALC_RES","AGE"])
d=d.join(per,on=["YEAR","ST_CASE","VEH_NO","PER_NO"],how="left")
d=d.with_columns((pl.col("ALC_RES")<=995).alias("meas"),
  pl.col("L_STATUS").is_in([0,1,2,3,4,6]).alias("lk"),pl.col("L_STATUS").is_in([0,1,2,3,4]).alias("ly"),
  pl.col("PREV_DWI").is_between(0,97).alias("dk"),pl.col("PREV_DWI").is_between(1,97).alias("dy"))
P=[f"P{m}" for m in range(1,11)]
def stats(df,flag15="P1"):
    return dict(n=df.height,sh15=(df[flag15]>=15).mean(),lic=df.filter(pl.col("lk"))["ly"].mean(),dwi=df.filter(pl.col("dk"))["dy"].mean())
res={}
s=d.filter(pl.col("P1")>=8)
print("MI .08+ (P1): n",s.height," measured share",s["meas"].mean())
print("  measured:",stats(s.filter(pl.col("meas"))))
print("  imputed-only:",stats(s.filter(~pl.col("meas"))))
# measured .08+ by actual result
m=d.filter(pl.col("meas")&(pl.col("ALC_RES")>=80))
m=m.with_columns(pl.when(pl.col("ALC_RES")==995).then(95).otherwise(pl.col("ALC_RES")//10).alias("bh"))
print("measured ALC_RES>=.080: n",m.height,"sh15",(m["bh"]>=15).mean(),"lic",m.filter(pl.col("lk"))["ly"].mean(),"dwi",m.filter(pl.col("dk"))["dy"].mean())
# drivers killed vs survived? person inj not loaded; skip. Test rate by BAC group
print("tested share overall (ALC_RES<=995):",d["meas"].mean())
# among measured, whole-sample positives: share of ALL measured drivers >=.08
print("measured positive rate among tested:",(m.height/d["meas"].sum()))
# per-implicate range of the three headline numbers
for c in P:
    x=d.filter(pl.col(c)>=8); 
    print(c,"n",x.height,"sh15 %.4f"%(x.filter(pl.col(c)>=15).height/x.height))
# imputed-only: .15+ share is model output. Bound: if imputed-only drivers had measured-like distribution?
# Counterfactual: replace imputed .15+ share by the measured share
mm=s.filter(pl.col("meas"))["P1"].ge(15).mean(); w=s["meas"].mean()
print("measured-only .15+ among MI .08+:",mm, " measured-weight",w)
# MI imputation relies on severity? tested rate by P1 group year
print(s.group_by("YEAR").agg(pl.col("meas").mean().alias("meas_sh")).sort("YEAR"))
