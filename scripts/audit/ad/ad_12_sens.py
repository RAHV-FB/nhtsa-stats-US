"""FARS drivers: police-reported DRINKING vs measured BAC (sensitivity/specificity) by severity; BAC>=.08 prevalence measured vs MI; DRINKING missingness by severity."""
import polars as pl
OUT = "outputs/cache/audit/out_ad"
pl.Config.set_tbl_rows(200); pl.Config.set_tbl_width_chars(260); pl.Config.set_tbl_cols(30)
df = pl.read_parquet(f"{OUT}/fars_drivers.parquet").filter(pl.col("sev").is_in(["killed","survived"]))
P = [f"P{i}" for i in range(1,11)]
df = df.with_columns(pl.mean_horizontal([(pl.col(c)>=8).cast(pl.Float64) for c in P]).alias("mi08"),
                     pl.mean_horizontal([(pl.col(c)>=1).cast(pl.Float64) for c in P]).alias("mi01"))
# DRINKING distribution by sev (all drivers) by year
print("DRINKING code distribution (%) by sev, pooled; and by year for 8/9")
print(df.group_by(["sev","DRINKING"]).len().with_columns((100*pl.col("len")/pl.col("len").sum().over("sev")).round(2).alias("pct")).pivot(on="sev", index="DRINKING", values="pct").sort("DRINKING"))
t = df.group_by(["YEAR","sev"]).agg((pl.col("DRINKING").is_in([8,9])).mean().mul(100).round(1).alias("pct_unk")).pivot(on="sev", index="YEAR", values="pct_unk").sort("YEAR")
print(t)
m = df.filter(pl.col("alc_stat")=="measured").with_columns(
    pl.when(pl.col("ALC_RES")>=80).then(pl.lit("≥.08")).when(pl.col("ALC_RES")>=10).then(pl.lit(".01-.079")).otherwise(pl.lit("<.01")).alias("bacc"))
print("measured drivers: DRINKING x BAC class by sev (row % within BAC class)")
x = m.group_by(["sev","bacc","DRINKING"]).len().with_columns((100*pl.col("len")/pl.col("len").sum().over(["sev","bacc"])).round(1).alias("pct"))
print(x.pivot(on="DRINKING", index=["sev","bacc"], values="pct").sort(["sev","bacc"]))
print(x.pivot(on="DRINKING", index=["sev","bacc"], values="len").sort(["sev","bacc"]))
# sensitivity excluding unknown DRINKING (8,9) and treating unknown as negative
def metrics(g):
    pos = g.filter(pl.col("ALC_RES")>=80); neg = g.filter(pl.col("ALC_RES")<10)
    r = {}
    r["n_meas"] = g.height
    r["prev08_meas"] = round(100*pos.height/g.height,1)
    pk = pos.filter(pl.col("DRINKING").is_in([0,1])); nk = neg.filter(pl.col("DRINKING").is_in([0,1]))
    r["sens_known"] = round(100*pk.filter(pl.col("DRINKING")==1).height/max(pk.height,1),1)
    r["spec_known"] = round(100*nk.filter(pl.col("DRINKING")==0).height/max(nk.height,1),1)
    r["sens_unk_as_no"] = round(100*pos.filter(pl.col("DRINKING")==1).height/max(pos.height,1),1)
    r["pct_drinking_unk_among_pos"] = round(100*pos.filter(pl.col("DRINKING").is_in([8,9])).height/max(pos.height,1),1)
    r["pct_drinking_unk_among_neg"] = round(100*neg.filter(pl.col("DRINKING").is_in([8,9])).height/max(neg.height,1),1)
    d1 = g.filter(pl.col("DRINKING")==1)
    r["ppv_drinking1_bac08"] = round(100*d1.filter(pl.col("ALC_RES")>=80).height/max(d1.height,1),1)
    r["ppv_drinking1_bac01"] = round(100*d1.filter(pl.col("ALC_RES")>=10).height/max(d1.height,1),1)
    return r
rows=[]
for sev in ["killed","survived"]:
    r = metrics(m.filter(pl.col("sev")==sev)); r["sev"]=sev; r["YEAR"]="pooled"; rows.append(r)
    for y in range(2016,2025):
        r = metrics(m.filter((pl.col("sev")==sev)&(pl.col("YEAR")==y))); r["sev"]=sev; r["YEAR"]=str(y); rows.append(r)
res = pl.DataFrame(rows)
print(res.select(["sev","YEAR"]+[c for c in res.columns if c not in ("sev","YEAR")]))
res.write_csv(f"{OUT}/sens_by_sev_year.csv")
# Prevalence BAC>=.08: measured-only vs MI (all drivers) vs police DRINKING==1 (all drivers) by sev and year
print("BAC>=.08 prevalence: among measured; MI-based over all drivers; police-reported DRINKING=1 over all drivers; DR_DRINK")
pv = df.group_by(["YEAR","sev"]).agg(
    (pl.col("ALC_RES").filter(pl.col("alc_stat")=="measured")>=80).mean().mul(100).round(1).alias("meas08"),
    pl.col("mi08").mean().mul(100).round(1).alias("mi08"),
    (pl.col("DRINKING")==1).mean().mul(100).round(1).alias("police1"),
    pl.col("DR_DRINK").mean().mul(100).round(1).alias("dr_drink"),
    pl.col("mi01").mean().mul(100).round(1).alias("mi01"))
print(pv.sort(["sev","YEAR"]))
pp = df.group_by(["sev"]).agg(
    (pl.col("ALC_RES").filter(pl.col("alc_stat")=="measured")>=80).mean().mul(100).round(2).alias("meas08"),
    pl.col("mi08").mean().mul(100).round(2).alias("mi08_all"),
    pl.col("mi08").filter(pl.col("alc_stat")!="measured").mean().mul(100).round(2).alias("mi08_imputed_only"),
    (pl.col("DRINKING")==1).mean().mul(100).round(2).alias("police1"),
    pl.col("DR_DRINK").mean().mul(100).round(2).alias("dr_drink"))
print(pp)
# by imputation status: mean mi08 by alc_stat x sev
print(df.group_by(["sev","alc_stat"]).agg(pl.col("mi08").mean().mul(100).round(1), pl.len()).sort(["sev","alc_stat"]))
# among 998 drivers min implicate
print("998 drivers min over implicates:", df.filter(pl.col("ALC_RES")==998).select(pl.min_horizontal(P).min()).item())
