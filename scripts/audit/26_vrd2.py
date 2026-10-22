import sys; sys.path.insert(0, "scripts/audit")
from helpers import *
c = pl.col
K = ["YEAR", "ST_CASE", "VEH_NO"]
src = sys.argv[1] if len(sys.argv) > 1 else "FARS"
df = aux_main("FARS", "veh", ["A_VRD"], ["ACC_TYPE"])
vs = load_table("FARS", "vsoe", columns=["ST_CASE", "VEH_NO", "SOE", "VEVENTNUM"])
NONH = [60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 79]
for dep in [[63, 64, 65, 68, 71, 79], [63, 64, 71, 79], [63, 64, 65, 68, 71, 79, 69]]:
    v = vs.with_columns(c("SOE").is_in(dep).alias("isdep"), (~c("SOE").is_in(NONH)).alias("harm"))
    first_h = v.filter(c("harm")).group_by(K).agg(c("VEVENTNUM").min().alias("fh"))
    v2 = v.join(first_h, on=K, how="left")
    g = v2.group_by(K).agg((c("isdep") & ((c("VEVENTNUM") < c("fh")) | c("fh").is_null())).any().alias("dep_pre"))
    x = df.join(g, on=K, how="left").with_columns(c("dep_pre").fill_null(False))
    d = agree(x, pl.when(c("dep_pre")).then(1).otherwise(2), "A_VRD", f"A_VRD = departure {dep} before first harmful event")
d = d.filter(c("_pred") != c("A_VRD"))
print(d.group_by(["_pred", "A_VRD", "ACC_TYPE"]).agg(pl.len()).sort("len", descending=True).head(15))
