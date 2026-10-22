"""P_CRASH2 code set in CRSS 2016-18 vs labelled CRSS 2019+; DR_WGT range."""
import sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
import polars as pl
from common import lt, codebook
cb = codebook().filter((pl.col("source") == "CRSS") & (pl.col("variable") == "P_CRASH2") & (pl.col("table") == "vehicle"))
lab = set(cb["code"].to_list())
v = lt("CRSS", "vehicle", ["YEAR", "P_CRASH2"])
for y in [2016, 2017, 2018, 2019]:
    c = v.filter(pl.col("YEAR") == y)["P_CRASH2"].cast(pl.Utf8)
    s = set(c.unique().to_list())
    print(y, "codes:", len(s), "not labelled in CRSS 2019+:", sorted(s - lab), "rows:", int(c.is_in(list(s - lab)).sum()))
f = lt("FARS", "vehicle", ["YEAR", "DR_WGT", "DR_HGT", "DR_PRES"])
d = f.filter((pl.col("DR_PRES") == 1) & (pl.col("DR_WGT") < 997))
print("DR_WGT known: p0.1", d["DR_WGT"].quantile(0.001), "median", d["DR_WGT"].median(), "p99.9", d["DR_WGT"].quantile(0.999), "min", d["DR_WGT"].min(), "max", d["DR_WGT"].max())
print("DR_HGT==998 count (label 'Other'):", f.filter(pl.col("DR_HGT") == 998).height, "of which DR_PRES!=1:", f.filter((pl.col("DR_HGT") == 998) & (pl.col("DR_PRES") != 1)).height)
