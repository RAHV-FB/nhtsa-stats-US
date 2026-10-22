import polars as pl
d = pl.concat([pl.scan_parquet(f"data/interim/CRSS/vehicle/{y}.parquet").select("MAX_VSEV","HIT_RUN","WEIGHT").collect() for y in range(2016,2025)])
print("CRSS share hit-run among MAX_VSEV=9:", round(100*d.filter(pl.col("MAX_VSEV")==9)["HIT_RUN"].eq(1).mean(),1), " share of hit-run with MAX_VSEV=9:", round(100*d.filter(pl.col("HIT_RUN")==1)["MAX_VSEV"].eq(9).mean(),1))
# re-run key CRSS K vs O missing comparisons excluding hit-run vehicles
x = pl.concat([pl.scan_parquet(f"data/interim/CRSS/vehicle/{y}.parquet").select("MAX_VSEV","HIT_RUN","WEIGHT","VSPD_LIM","TRAV_SP","VTRAFWAY","MOD_YEAR","BODY_TYP").collect() for y in range(2016,2025)]).filter(pl.col("HIT_RUN")!=1)
s = {0:"O",1:"C",2:"B",3:"A",4:"K"}
print(x.filter(pl.col("MAX_VSEV").is_in(list(s))).group_by("MAX_VSEV").agg(pl.len(),
   *[((pl.col(c).is_in(m).cast(pl.Float64)*pl.col("WEIGHT")).sum()/pl.col("WEIGHT").sum()*100).round(2).alias(c) for c,m in [("VSPD_LIM",[98,99]),("TRAV_SP",[998,999]),("VTRAFWAY",[8,9]),("MOD_YEAR",[9998,9999]),("BODY_TYP",[98,99])]]).sort("MAX_VSEV").rows())
f = pl.concat([pl.scan_parquet(f"data/interim/FARS/vehicle/{y}.parquet").select("DEATHS","HIT_RUN","MOD_YEAR","BODY_TYP","TRAV_SP").collect() for y in range(2016,2025)]).filter(pl.col("HIT_RUN")!=1)
print("FARS non-hit-run:", f.group_by(pl.col("DEATHS")>0).agg(pl.len(), pl.col("MOD_YEAR").is_in([9998,9999]).mean().mul(100).round(2), pl.col("BODY_TYP").is_in([98,99]).mean().mul(100).round(2).alias("b"), pl.col("TRAV_SP").is_in([998,999]).mean().mul(100).round(2).alias("t")).rows())
