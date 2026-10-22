import sys; sys.path.insert(0, "scripts/audit")
from helpers import *
c = pl.col
K = ["YEAR", "ST_CASE", "VEH_NO"]
Y = [2020, 2021, 2022, 2023, 2024]
df = aux_main("FARS", "veh", ["A_WRONGWAYDRV"], ["P_CRASH1", "P_CRASH2", "VTRAFWAY", "ACC_TYPE"], years=Y)
drf = load_table("FARS", "driverrf", years=Y, columns=["ST_CASE", "VEH_NO", "DRIVERRF"]).group_by(K).agg(c("DRIVERRF").is_in([50, 51]).any().alias("ww_rf"))
vio = load_table("FARS", "violatn", years=Y, columns=["ST_CASE", "VEH_NO", "VIOLATION"]).group_by(K).agg(c("VIOLATION").is_in([51, 52]).any().alias("ww_vio"))
df = df.join(drf, on=K, how="left").join(vio, on=K, how="left").with_columns(c("ww_rf").fill_null(False), c("ww_vio").fill_null(False))
m = df.filter((c("A_WRONGWAYDRV") == 1) & ~c("ww_rf"))
print("aux=1 but no DRIVERRF 50/51:", m.height)
for col in ["ww_vio", "P_CRASH2", "P_CRASH1", "VTRAFWAY", "ACC_TYPE"]:
    print(col, m.group_by(col).agg(pl.len()).sort("len", descending=True).head(8).to_dicts())
print("P_CRASH2 labels:", {k: v for k, v in labels("FARS", "vehicle", "P_CRASH2").items() if k in m["P_CRASH2"].unique().to_list()})
# Compare: rows with P_CRASH2 == wrong-way code among all
d = agree(df, pl.when(c("ww_rf") | c("ww_vio")).then(1).otherwise(2), "A_WRONGWAYDRV", "A_WRONGWAYDRV = DRIVERRF 50/51 OR VIOLATION 51/52")
mismatch(d, "A_WRONGWAYDRV", ["ww_rf", "ww_vio"], 5)
