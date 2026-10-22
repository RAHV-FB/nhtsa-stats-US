"""FARS: ALC_STATUS x ATST_TYP x ALC_RES consistency; A_ALCTES mapping; DR_DRINK derivation; A_POSBAC mapping; DRUNK_DR."""
import polars as pl
OUT = "/tmp/nhtsa-audit/out_ad"
pl.Config.set_tbl_rows(200); pl.Config.set_tbl_width_chars(250); pl.Config.set_tbl_cols(30)
df = pl.read_parquet(f"{OUT}/fars_person.parquet")
rescat = (pl.when(pl.col("ALC_RES")==0).then(pl.lit("0 zero"))
          .when(pl.col("ALC_RES").is_between(1,79)).then(pl.lit("1-79"))
          .when(pl.col("ALC_RES").is_between(80,940)).then(pl.lit("80-940"))
          .otherwise(pl.col("ALC_RES").cast(pl.Utf8))).alias("rescat")
df = df.with_columns(rescat)
print("ALC_STATUS x rescat (all persons, all years)")
print(df.group_by(["ALC_STATUS","rescat"]).len().pivot(on="rescat", index="ALC_STATUS", values="len", sort_columns=True).sort("ALC_STATUS"))
print("ATST_TYP x rescat")
print(df.group_by(["ATST_TYP","rescat"]).len().pivot(on="rescat", index="ATST_TYP", values="len", sort_columns=True).sort("ATST_TYP"))
print("A_ALCTES x rescat")
print(df.group_by(["A_ALCTES","rescat"]).len().pivot(on="rescat", index="A_ALCTES", values="len", sort_columns=True).sort("A_ALCTES"))
print("A_ALCTES x ALC_STATUS")
print(df.group_by(["A_ALCTES","ALC_STATUS"]).len().pivot(on="ALC_STATUS", index="A_ALCTES", values="len", sort_columns=True).sort("A_ALCTES"))
d = df.filter(pl.col("PER_TYP")==1)
print("DRIVERS: DR_DRINK x DRINKING x BAC>0")
d = d.with_columns(pl.when(pl.col("ALC_RES")<=940).then(pl.when(pl.col("ALC_RES")>0).then(pl.lit("pos")).otherwise(pl.lit("zero"))).otherwise(pl.lit("nomeas")).alias("bac"))
print(d.group_by(["DR_DRINK","DRINKING","bac"]).len().pivot(on="DR_DRINK", index=["DRINKING","bac"], values="len", sort_columns=True).sort(["DRINKING","bac"]))
# exact rule test: DR_DRINK = 1 iff DRINKING==1 or (0<ALC_RES<=940) or ALC_RES==998?
for name, rule in [("DRINKING==1 | 0<BAC<=940", (pl.col("DRINKING")==1)|pl.col("ALC_RES").is_between(1,940)),
                   ("DRINKING==1 | 0<BAC<=940 | 998", (pl.col("DRINKING")==1)|pl.col("ALC_RES").is_between(1,940)|(pl.col("ALC_RES")==998)),
                   ("DRINKING==1 | 10<=BAC<=940 | 998", (pl.col("DRINKING")==1)|pl.col("ALC_RES").is_between(10,940)|(pl.col("ALC_RES")==998))]:
    r = d.with_columns(rule.cast(pl.Int64).alias("r")).group_by("YEAR").agg((pl.col("r")==pl.col("DR_DRINK")).mean().alias("agree"), (pl.col("r")!=pl.col("DR_DRINK")).sum().alias("n_dis")).sort("YEAR")
    print(name); print(r.transpose(include_header=True))
