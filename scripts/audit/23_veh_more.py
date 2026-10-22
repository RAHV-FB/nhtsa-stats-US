import sys; sys.path.insert(0, "scripts/audit")
from helpers import *
c = pl.col
df = aux_main("FARS", "veh", ["A_BODY", "A_MC_L_S", "A_LIC_S", "A_LIC_C", "A_SBUS", "A_TOWED", "A_MOD_YR"],
              ["BODY_TYP", "L_STATUS", "L_COMPL", "L_TYPE", "L_ENDORS", "BUS_USE", "TOWED", "MOD_YEAR", "DR_PRES", "SPEC_USE"])
print("A_LIC_S=4 vs A_BODY==7:", df.group_by(["A_LIC_S", (c("A_BODY") == 7).alias("isMC")]).agg(pl.len()).sort(["A_LIC_S", "isMC"]).to_dicts())
mc = df.filter(c("A_BODY") == 7)
print("non-MC A_MC_L_S distribution:", df.filter(c("A_BODY") != 7).group_by("A_MC_L_S").agg(pl.len()).to_dicts())
for yrs in [(2016, 2019), (2020, 2024)]:
    d = mc.filter(c("YEAR").is_between(*yrs))
    print(yrs, "MC A_MC_L_S x L_STATUS x L_COMPL")
    print(d.group_by(["A_MC_L_S", "L_STATUS", "L_COMPL"]).agg(pl.len()).sort(pl.all().exclude("len")).filter(c("len") > 3))
print("A_SBUS x BUS_USE x BODY_TYP (non-3)")
print(df.filter(c("A_SBUS") != 3).group_by(["A_SBUS", "BUS_USE", "BODY_TYP"]).agg(pl.len()).sort(pl.all().exclude("len")))
print(df.filter((c("BUS_USE") == 1)).group_by(["A_SBUS", "BODY_TYP"]).agg(pl.len()).sort(pl.all().exclude("len")))
print("TOWED codes by year:")
print(df.group_by(["YEAR", "TOWED"]).agg(pl.len()).sort(["YEAR", "TOWED"]).pivot(on="YEAR", index="TOWED", values="len", sort_columns=True))
print(df.filter(c("YEAR") >= 2021).group_by(["A_TOWED", "TOWED"]).agg(pl.len()).sort(pl.all().exclude("len")))
print("A_MOD_YR vs MOD_YEAR mismatches:", df.filter(c("A_MOD_YR") != c("MOD_YEAR")).group_by(["YEAR", "MOD_YEAR", "A_MOD_YR"]).agg(pl.len()).sort("len", descending=True).head(10))
print("MOD_YEAR >= 9998 by year:", df.group_by("YEAR").agg((c("MOD_YEAR") >= 9998).sum().alias("n9998p"), (c("MOD_YEAR") == 9998).sum().alias("n9998"), (c("MOD_YEAR") == 9999).sum().alias("n9999"), (c("A_MOD_YR") == 9999).sum().alias("aux9999"), pl.len()).sort("YEAR").to_dicts())
