"""BODY_TYP harmonised grouping; verify vs VPICBODYCLASS (2020+), veh_aux A_BODY, GVWR, ROLLOVER=8."""
import polars as pl
pl.Config.set_tbl_rows(200); pl.Config.set_tbl_cols(40); pl.Config.set_tbl_width_chars(320); pl.Config.set_fmt_str_lengths(50)
def grp(c):
    return (pl.when(c.is_between(1,13)|(c==17)).then(pl.lit("01_car"))
     .when(c.is_in([14,15,16,19])).then(pl.lit("02_suv"))
     .when(c.is_in([30,31,32,33,34,39])).then(pl.lit("03_pickup"))
     .when(c.is_in([20,21,22,28,29])).then(pl.lit("04_van"))
     .when(c.is_in([40,41,42,45,48])).then(pl.lit("05_lt_other"))
     .when(c==49).then(pl.lit("06_light_unk"))
     .when(c.is_in([50,51,52,55,58,59])).then(pl.lit("07_bus"))
     .when(c.is_in([60,61,62,63,64,65,66,67,71,72,78])).then(pl.lit("08_medhvy_truck"))
     .when(c.is_in([73,79])).then(pl.lit("09_truck_unk"))
     .when(c.is_between(80,89)).then(pl.lit("10_mc_moped"))
     .when(c.is_between(90,97)).then(pl.lit("11_other"))
     .when(c.is_in([98,99])).then(pl.lit("99_missing")).otherwise(pl.lit("??")))
frames=[]
for src in ["FARS","CRSS"]:
    key = ["ST_CASE","VEH_NO"] if src=="FARS" else ["CASENUM","VEH_NO"]
    for y in range(2016,2025):
        cols = ["BODY_TYP","ROLLOVER","ROLINLOC"] + (["VPICBODYCLASS","ICFINALBODY","GVWR_FROM","GVWR_TO"] if y>=2020 else ["GVWR"])
        v = pl.scan_parquet(f"data/interim/{src}/vehicle/{y}.parquet").select(key+cols).collect()
        a = pl.scan_parquet(f"data/interim/{src}/veh_aux/{y}.parquet").select(key+["A_BODY"]).collect()
        v = v.join(a, on=key, how="left").with_columns(pl.lit(src).alias("source"), pl.lit(y).alias("year")).drop(key)
        frames.append(v)
d = pl.concat(frames, how="diagonal").with_columns(grp(pl.col("BODY_TYP")).alias("bgrp"))
print("?? codes:", d.filter(pl.col("bgrp")=="??")["BODY_TYP"].unique().to_list())
# share by group per source-year
t = d.group_by("source","year","bgrp").len().with_columns((100*pl.col("len")/pl.col("len").sum().over("source","year")).round(2).alias("pct"))
t = t.with_columns((pl.col("source").str.slice(0,1)+pl.col("year").cast(pl.Utf8).str.slice(2,2)).alias("sy"))
print(t.pivot(on="sy", index="bgrp", values="pct").sort("bgrp"))
# A_BODY vs bgrp
print("== A_BODY (veh_aux, unlabelled) x harmonised group, pooled")
x = d.group_by("A_BODY","bgrp").len().pivot(on="bgrp", index="A_BODY", values="len").sort("A_BODY")
print(x.select(["A_BODY"]+sorted([c for c in x.columns if c!="A_BODY"])))
# VPICBODYCLASS vs bgrp (2020+)
cb = pl.read_csv("outputs/audit/codebook.csv", infer_schema_length=0).filter((pl.col("variable")=="VPICBODYCLASS")&(pl.col("table")=="vehicle")).select(pl.col("code").cast(pl.Int64).alias("VPICBODYCLASS"), pl.col("label")).unique("VPICBODYCLASS")
z = d.filter(pl.col("year")>=2020).join(cb, on="VPICBODYCLASS", how="left")
top = z.group_by("bgrp","label").len().with_columns((100*pl.col("len")/pl.col("len").sum().over("bgrp")).round(1).alias("pct")).sort("bgrp","len",descending=[False,True])
print("== top VPICBODYCLASS labels within each harmonised BODY_TYP group (2020-2024 pooled)")
print(top.group_by("bgrp", maintain_order=True).head(4))
# ROLLOVER 8 (2022+) by group
print("== ROLLOVER=8 'Not Applicable' (2022+) by group: share of group")
print(d.filter(pl.col("year")>=2022).group_by("source","bgrp").agg(pl.len(), (pl.col("ROLLOVER")==8).mean().mul(100).round(2).alias("pct_rollover8")).sort("source","bgrp"))
print("ROLLOVER=8 rows: share that are mc/other:", d.filter((pl.col("year")>=2022)&(pl.col("ROLLOVER")==8)).group_by("bgrp").len().sort("len",descending=True).rows())
# GVWR (2016-19) by group; GVWR_FROM vs TO
print("== GVWR (2016-2019) by group (row %)")
print(d.filter(pl.col("year")<=2019).group_by("bgrp","GVWR").len().with_columns((100*pl.col("len")/pl.col("len").sum().over("bgrp")).round(1).alias("p")).pivot(on="GVWR", index="bgrp", values="p").sort("bgrp"))
print("== GVWR_FROM vs GVWR_TO agreement (2020+)")
g = d.filter(pl.col("year")>=2020)
print(g.group_by("source").agg(pl.len(), (pl.col("GVWR_FROM")==pl.col("GVWR_TO")).mean().mul(100).round(2).alias("pct_equal"),
   ((pl.col("GVWR_FROM")==11)&(pl.col("GVWR_TO")==12)).mean().mul(100).round(2).alias("pct_1to2"), (pl.col("GVWR_FROM")>pl.col("GVWR_TO")).mean().mul(100).round(3).alias("pct_from_gt_to")))
print(g.filter(pl.col("GVWR_FROM")!=pl.col("GVWR_TO")).group_by("source","GVWR_FROM","GVWR_TO").len().sort("len",descending=True).head(12))
print("== GVWR_FROM by group (2020+, row %)")
print(g.group_by("bgrp","GVWR_FROM").len().with_columns((100*pl.col("len")/pl.col("len").sum().over("bgrp")).round(1).alias("p")).pivot(on="GVWR_FROM", index="bgrp", values="p").sort("bgrp"))
print("== ICFINALBODY != 0 by group")
print(g.group_by("bgrp").agg(pl.len(), (pl.col("ICFINALBODY")!=0).mean().mul(100).round(2).alias("pct_ic_nonzero")).sort("bgrp"))
