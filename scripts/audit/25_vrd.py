import sys; sys.path.insert(0, "scripts/audit")
from helpers import *
c = pl.col
K = ["YEAR", "ST_CASE", "VEH_NO"]
df = aux_main("FARS", "veh", ["A_VRD"], ["ACC_TYPE", "P_CRASH2", "HARM_EV", "M_HARM"])
vs = load_table("FARS", "vsoe", columns=["ST_CASE", "VEH_NO", "SOE", "VEVENTNUM"])
v = vs.group_by(K).agg(c("SOE").is_in([63, 64, 65, 68, 71, 79]).any().alias("soe_dep"))
df = df.join(v, on=K, how="left").with_columns(c("soe_dep").fill_null(False))
lab = labels("FARS", "vehicle", "ACC_TYPE")
t = df.group_by("ACC_TYPE").agg(pl.len().alias("n"), (c("A_VRD") == 1).mean().mul(100).round(1).alias("pctVRD1"), c("soe_dep").mean().mul(100).round(1).alias("pct_soe_dep")).sort("ACC_TYPE")
t = t.with_columns(c("ACC_TYPE").map_elements(lambda x: (lab.get(x) or "")[:60], return_dtype=pl.String).alias("label"))
print(t)
