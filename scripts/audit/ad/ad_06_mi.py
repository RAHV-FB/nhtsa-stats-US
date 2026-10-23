"""MIPER structure: coverage by PER_TYP, relation of implicates to ALC_RES where measured, units, variability."""
import polars as pl
OUT = "outputs/cache/audit/out_ad"
pl.Config.set_tbl_rows(100); pl.Config.set_tbl_width_chars(250); pl.Config.set_tbl_cols(30)
df = pl.read_parquet(f"{OUT}/fars_person.parquet")
P = [f"P{i}" for i in range(1,11)]
df = df.with_columns(pl.col("in_miper").fill_null(0))
print("coverage by PER_TYP (all years):")
print(df.group_by("PER_TYP").agg(pl.len(), pl.col("in_miper").mean().round(4)).sort("PER_TYP"))
print("coverage by year for drivers (PER_TYP=1) and pedestrians (5):")
print(df.filter(pl.col("PER_TYP").is_in([1,5,6])).group_by(["YEAR","PER_TYP"]).agg(pl.len(), pl.col("in_miper").mean().round(4)).sort(["PER_TYP","YEAR"]).pivot(on="PER_TYP", index="YEAR", values="in_miper"))
m = df.filter(pl.col("in_miper")==1)
meas = m.filter(pl.col("ALC_RES")<=940)
meas = meas.with_columns((pl.col("ALC_RES")/10).alias("res_h"))
# implicate equality
eq_all = meas.with_columns(pl.all_horizontal([pl.col(c)==pl.col("P1") for c in P]).alias("all_eq"))
print("measured BAC persons in miper:", meas.height, " all 10 implicates identical:", eq_all["all_eq"].mean())
for rule,expr in [("floor(ALC_RES/10)", (pl.col("ALC_RES")//10)), ("round(ALC_RES/10)", (pl.col("ALC_RES")/10).round(0).cast(pl.Int64)),
                  ("ceil", (pl.col("ALC_RES")/10).ceil().cast(pl.Int64))]:
    print(rule, "match P1:", meas.select((expr==pl.col("P1")).mean()).item())
x = meas.with_columns((pl.col("ALC_RES")//10).alias("fl"), (pl.col("ALC_RES")/10).round(0).cast(pl.Int64).alias("rd"))
bad = x.filter((pl.col("fl")!=pl.col("P1")) & (pl.col("rd")!=pl.col("P1")))
print("neither floor nor round match:", bad.height)
print(bad.group_by(["YEAR"]).len().sort("YEAR"))
print(bad.select(["YEAR","PER_TYP","ALC_STATUS","ATST_TYP","ALC_RES","P1","P2","P3"]).head(20))
print("year-wise floor-match rate and round-match rate:")
print(x.group_by("YEAR").agg((pl.col("fl")==pl.col("P1")).mean().alias("floor"), (pl.col("rd")==pl.col("P1")).mean().alias("round"), pl.len()).sort("YEAR"))
# implicate variability for non-measured
nm = m.filter(pl.col("ALC_RES")>940)
nm = nm.with_columns(pl.all_horizontal([pl.col(c)==pl.col("P1") for c in P]).alias("all_eq"),
                     pl.mean_horizontal([ (pl.col(c)>=8).cast(pl.Float64) for c in P]).alias("p08"))
print("non-measured persons in miper by ALC_RES code: n, share all implicates equal, mean P(BAC>=.08)")
print(nm.group_by("ALC_RES").agg(pl.len(), pl.col("all_eq").mean().round(4), pl.col("p08").mean().round(4)).sort("ALC_RES"))
print("all-equal among measured:", eq_all.group_by("YEAR").agg(pl.col("all_eq").mean()).sort("YEAR"))
# which ALC_RES codes appear among persons in miper
print(m.group_by(pl.when(pl.col("ALC_RES")<=940).then(pl.lit("measured")).otherwise(pl.col("ALC_RES").cast(pl.Utf8)).alias("c")).len().sort("c"))
# P values range
print(m.select([pl.col(c).max() for c in P]))
print(m.select([pl.col(c).min() for c in P]))
