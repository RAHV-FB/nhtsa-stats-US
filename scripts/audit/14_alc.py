import sys; sys.path.insert(0, "scripts/audit")
from helpers import *
p = load_table("FARS", "person", columns=["ALC_RES", "ALC_RESNAME"])
print(p.filter(pl.col("ALC_RES") <= 10).group_by(["ALC_RES", "ALC_RESNAME"]).agg(pl.len(), pl.col("YEAR").min().alias("y0"), pl.col("YEAR").max().alias("y1")).sort(["ALC_RES"]))
df = aux_main("FARS", "per", ["A_ALCTES", "A_PTYPE"], ["ALC_STATUS", "ALC_RES", "INJ_SEV", "PER_TYP"])
df = df.with_columns(pl.when(pl.col("ALC_RES") == 0).then(pl.lit("0")).when(pl.col("ALC_RES").is_between(1, 939)).then(pl.lit("1-939"))
                     .otherwise(pl.col("ALC_RES").cast(pl.String)).alias("RES"))
print(df.group_by(["A_ALCTES", "ALC_STATUS", "RES"]).agg(pl.len()).sort(["A_ALCTES", "ALC_STATUS", "RES"]))
print(df.group_by(["YEAR", "A_ALCTES", "ALC_STATUS", "RES"]).agg(pl.len()).sort(["YEAR", "A_ALCTES", "ALC_STATUS", "RES"]).filter(pl.col("YEAR").is_in([2016, 2024])))
