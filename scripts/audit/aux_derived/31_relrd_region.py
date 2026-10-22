import sys; sys.path.insert(0, "scripts/audit/aux_derived")
from helpers import *
c = pl.col
for src in ["FARS", "CRSS"]:
    df = aux_main(src, "crash", ["A_RELRD"], ["REL_ROAD"])
    print(src, df.filter(c("REL_ROAD").is_in([7, 12])).group_by(["REL_ROAD", "YEAR", "A_RELRD"]).agg(pl.len()).sort(["REL_ROAD", "YEAR", "A_RELRD"]).pivot(on="A_RELRD", index=["REL_ROAD", "YEAR"], values="len", sort_columns=True))
df = aux_main("FARS", "crash", ["A_REGION"], ["STATE", "COUNTY"])
print(df.filter(c("STATE") == 9).group_by(["YEAR", "A_REGION"]).agg(pl.len()).sort(["YEAR", "A_REGION"]).pivot(on="A_REGION", index="YEAR", values="len"))
print(df.filter(c("STATE") == 9).group_by(["COUNTY", "A_REGION"]).agg(pl.len()).sort(["COUNTY", "A_REGION"]).pivot(on="A_REGION", index="COUNTY", values="len"))
