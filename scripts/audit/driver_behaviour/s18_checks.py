"""Spot checks: L_STATUS=6 & L_COMPL=2 composition; CRSS personrf zero share."""
import sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
import polars as pl
from common import OUT, lt
f = pl.read_parquet(f"{OUT}/frame_FARS.parquet", columns=["YEAR", "DR_PRES", "L_STATUS", "L_COMPL", "BODY_TYP", "L_ENDORS"])
x = f.filter((pl.col("DR_PRES") == 1) & (pl.col("L_STATUS") == 6) & (pl.col("L_COMPL") == 2))
print("L_STATUS=6 & L_COMPL=2:", x.height, "motorcycle body 80-89:", x.filter(pl.col("BODY_TYP").is_between(80, 89)).height,
      "truck/bus 50-79:", x.filter(pl.col("BODY_TYP").is_between(50, 79)).height)
for src in ["FARS", "CRSS"]:
    p = lt(src, "personrf", ["YEAR", "PERSONRF"])
    print(src, "personrf share 0:", round((p["PERSONRF"] == 0).mean() * 100, 2))
