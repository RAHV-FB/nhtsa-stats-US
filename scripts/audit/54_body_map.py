import sys; sys.path.insert(0, "scripts/audit")
from helpers import *
c = pl.col
df = aux_main("FARS", "veh", ["A_BODY"], ["BODY_TYP"], years=[2016, 2017, 2018, 2019])
t = df.group_by(["BODY_TYP", "A_BODY"]).agg(pl.len().alias("n")).sort("n", descending=True).group_by("BODY_TYP").agg(c("A_BODY").first().alias("mode"), c("n").sum().alias("tot"), c("n").first().alias("nmode"))
m = t.group_by("mode").agg(c("BODY_TYP").sort().alias("codes")).sort("mode")
for r in m.iter_rows(): print("FARS 2016-19 A_BODY", r[0], "<- BODY_TYP", r[1])
print("non-modal rows:", (t["tot"] - t["nmode"]).sum(), "of", df.height)
d2 = aux_main("CRSS", "veh", ["A_BODY"], ["BDYTYP_IM"], years=[2016, 2017, 2018, 2019])
t = d2.group_by(["BDYTYP_IM", "A_BODY"]).agg(pl.len().alias("n")).sort("n", descending=True).group_by("BDYTYP_IM").agg(c("A_BODY").first().alias("mode"), c("n").sum().alias("tot"), c("n").first().alias("nmode"))
m = t.group_by("mode").agg(c("BDYTYP_IM").sort().alias("codes")).sort("mode")
for r in m.iter_rows(): print("CRSS 2016-19 A_BODY", r[0], "<- BDYTYP_IM", r[1])
print("non-modal rows:", (t["tot"] - t["nmode"]).sum(), "of", d2.height)
# 2020+ vPIC overrides: rows where A_BODY != 2016-19 mapping of BODY_TYP
mp = {b: a for a, bs in [(r[0], r[1]) for r in df.group_by(["BODY_TYP", "A_BODY"]).agg(pl.len().alias("n")).sort("n", descending=True).group_by("BODY_TYP").agg(c("A_BODY").first().alias("mode")).group_by("mode").agg(c("BODY_TYP")).iter_rows()] for b in bs}
for src in ["FARS", "CRSS"]:
    d = aux_main(src, "veh", ["A_BODY"], ["BODY_TYP", "VPICBODYCLASS"], years=[2020, 2021, 2022, 2023, 2024])
    d = d.with_columns(c("BODY_TYP").replace_strict(mp, default=9).alias("bt_map"))
    print(src, "2020+ agreement with 2016-19 BODY_TYP map:", round(100 * (d["bt_map"] == d["A_BODY"]).mean(), 2))
    x = d.filter(c("bt_map") != c("A_BODY")).group_by(["bt_map", "A_BODY"]).agg(pl.len().alias("n")).sort("n", descending=True).head(8)
    print(x.to_dicts())
    lab = labels(src, "vehicle", "VPICBODYCLASS")
    y = d.filter((c("bt_map") == 1) & (c("A_BODY") == 3)).group_by("VPICBODYCLASS").agg(pl.len().alias("n")).sort("n", descending=True).head(4)
    print("  auto->utility overrides by vPIC:", [(r[0], lab.get(r[0]), r[1]) for r in y.iter_rows()])
    y = d.filter((c("A_BODY") == 9) & (c("bt_map") != 9)).group_by(["BODY_TYP", "VPICBODYCLASS"]).agg(pl.len().alias("n")).sort("n", descending=True).head(5)
    print("  ->9 overrides:", [(r[0], r[1], lab.get(r[1]), r[2]) for r in y.iter_rows()])
