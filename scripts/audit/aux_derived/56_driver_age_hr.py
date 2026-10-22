"""FARS: driver age unknown and its relation to hit-and-run vehicles."""
import sys; sys.path.insert(0, "scripts/audit/aux_derived")
from helpers import *
c = pl.col
p = load_table("FARS", "person", columns=["ST_CASE", "VEH_NO", "PER_TYP", "AGE"]).filter(c("PER_TYP") == 1)
v = load_table("FARS", "vehicle", columns=["ST_CASE", "VEH_NO", "HIT_RUN"])
d = p.join(v, on=["YEAR", "ST_CASE", "VEH_NO"], how="left")
unk = d.filter(c("AGE") >= 998)
print("drivers:", d.height, "age unknown:", unk.height, f"({100*unk.height/d.height:.2f}%)")
print("share of unknown-age drivers in hit-and-run vehicles:", round(100 * (unk["HIT_RUN"] == 1).mean(), 1))
print("age-unknown rate among hit-and-run drivers:", round(100 * (d.filter(c("HIT_RUN") == 1)["AGE"] >= 998).mean(), 1), "non-HR:", round(100 * (d.filter(c("HIT_RUN") != 1)["AGE"] >= 998).mean(), 2))
a = load_table("FARS", "acc_aux", columns=["ST_CASE", "A_D16_24"])
g = d.group_by(["YEAR", "ST_CASE"]).agg((c("AGE") >= 998).all().alias("all_unk"))
x = a.join(g, on=["YEAR", "ST_CASE"], how="left")
print("crashes where every driver has unknown age:", x.filter(c("all_unk").fill_null(False)).height, "of", x.height)
