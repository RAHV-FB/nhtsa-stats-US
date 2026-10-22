import sys; sys.path.insert(0, "scripts/audit")
from helpers import *
c = pl.col
K = ["YEAR", "ST_CASE"]
acc = load_table("FARS", "acc_aux", columns=["ST_CASE", "A_POSBAC"])
p = load_table("FARS", "person", columns=["ST_CASE", "PER_TYP", "ALC_RES"]).filter(c("PER_TYP") == 1)
for thr in [1, 5, 10]:
    dr = p.group_by(K).agg((c("ALC_RES").is_between(thr, 940) | (c("ALC_RES") == 998)).any().alias("pos"),
                           (c("ALC_RES").is_between(0, 940)).all().alias("alltested"))
    x = acc.join(dr, on=K, how="left")
    agree(x, pl.when(c("pos").fill_null(False)).then(1).when(c("alltested").fill_null(True)).then(2).otherwise(3), "A_POSBAC", f"A_POSBAC thr={thr}: any driver ALC_RES>={thr} ->1; all drivers tested (0-940) ->2; else 3")
x2 = acc.join(p.group_by(K).agg(pl.col("ALC_RES").sort().alias("res")), on=K, how="left")
