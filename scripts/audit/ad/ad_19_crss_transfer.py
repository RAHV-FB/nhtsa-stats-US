"""CRSS 2016-2018 label transfer evidence: code sets vs CRSS 2019 / FARS same year, structural invariants, TVD of distributions."""
import polars as pl
OUT = "/tmp/nhtsa-audit/out_ad"
pl.Config.set_tbl_rows(200); pl.Config.set_tbl_width_chars(260); pl.Config.set_tbl_cols(30)
d = pl.read_csv(f"{OUT}/dist.csv", infer_schema_length=0).with_columns(pl.col("n").cast(pl.Int64), pl.col("N").cast(pl.Int64), pl.col("year").cast(pl.Int64))
for var in ["DRINKING","ALC_STATUS","ATST_TYP","DRUGS","PERALCH_IM","VEH_ALCH","V_ALCH_IM","ALCOHOL","ALCHL_IM","DRIMPAIR","NMIMPAIR"]:
    x = d.filter((pl.col("source")=="CRSS")&(pl.col("var")==var))
    sets = {y: set(x.filter(pl.col("year")==y)["code"].to_list()) for y in range(2016,2025)}
    lab19 = sets[2019]
    labelled_union = set().union(*[sets[y] for y in range(2019,2025)])
    f = d.filter((pl.col("source")=="FARS")&(pl.col("var")==var))
    out=[]
    for y in (2016,2017,2018):
        fs = set(f.filter(pl.col("year")==y)["code"].to_list()) if f.height else set()
        # TVD vs 2019 and vs 2018->2019 adjacent
        a = x.filter(pl.col("year")==y).select("code",(pl.col("n")/pl.col("N")).alias("p"))
        b = x.filter(pl.col("year")==2019).select("code",(pl.col("n")/pl.col("N")).alias("q"))
        j = a.join(b, on="code", how="full", coalesce=True).fill_null(0)
        tvd = 0.5*(j["p"]-j["q"]).abs().sum()
        out.append(f"{y}: codes not in CRSS2019-24 labelled set={sorted(sets[y]-labelled_union)}; codes not in FARS{y}={sorted(sets[y]-fs) if fs else 'n/a'}; TVD vs 2019={tvd:.3f}")
    # adjacent TVDs 2019->2020 etc for reference
    adj=[]
    for y in range(2017,2025):
        a = x.filter(pl.col("year")==y-1).select("code",(pl.col("n")/pl.col("N")).alias("p"))
        b = x.filter(pl.col("year")==y).select("code",(pl.col("n")/pl.col("N")).alias("q"))
        j = a.join(b, on="code", how="full", coalesce=True).fill_null(0)
        adj.append(f"{y-1}->{y}:{0.5*(j['p']-j['q']).abs().sum():.3f}")
    print(f"### {var}"); [print("   ",o) for o in out]; print("    adjacent TVD:", " ".join(adj))
# structural invariants in CRSS by year
p = pl.read_parquet(f"{OUT}/crss_person.parquet")
p = p.with_columns(pl.when(pl.col("ALC_RES")<=940).then(pl.lit("meas")).otherwise(pl.col("ALC_RES").cast(pl.Utf8)).alias("rc"))
print("CRSS ALC_STATUS x ALC_RES class, 2016-2018 vs 2019-2024")
print(p.with_columns((pl.col("YEAR")<=2018).alias("early")).group_by(["early","ALC_STATUS","rc"]).len().pivot(on="rc", index=["early","ALC_STATUS"], values="len", sort_columns=True).sort(["early","ALC_STATUS"]))
print("CRSS ATST_TYP x ALC_STATUS 2016-2018")
print(p.filter(pl.col("YEAR")<=2018).group_by(["ATST_TYP","ALC_STATUS"]).len().pivot(on="ALC_STATUS", index="ATST_TYP", values="len", sort_columns=True).sort("ATST_TYP"))
print("CRSS 2016-2017 DRUGTST1 x DRUGRES1 special")
print(p.filter(pl.col("YEAR")<=2017).with_columns(pl.when(pl.col("DRUGRES1").is_between(100,995)).then(pl.lit("drug")).otherwise(pl.col("DRUGRES1").cast(pl.Utf8)).alias("r1")).group_by(["DRUGTST1","r1"]).len().pivot(on="r1", index="DRUGTST1", values="len", sort_columns=True).sort("DRUGTST1"))
# CRSS measured BAC distribution early vs late among measured
m = p.filter(pl.col("ALC_RES")<=940).with_columns(pl.when(pl.col("ALC_RES")==0).then(pl.lit("0")).when(pl.col("ALC_RES")<80).then(pl.lit("1-79")).otherwise(pl.lit("80+")).alias("b"))
print(m.group_by(["YEAR","b"]).len().pivot(on="b", index="YEAR", values="len", sort_columns=True).sort("YEAR"))
