import sys; sys.path.insert(0, "scripts/audit/aux_derived")
from helpers import *
src = "CRSS"
df = aux_main(src, "per", ["A_PERINJ", "A_EJECT", "A_RESTUSE", "A_HELMUSE", "A_PTYPE", "A_LOC"],
              ["INJ_SEV", "INJSEV_IM", "EJECTION", "EJECT_IM", "REST_USE", "HELM_USE", "HELM_MIS", "REST_MIS", "PER_TYP", "BODY_TYP", "LOCATION"])
df = df.with_columns(pl.when(pl.col("BODY_TYP").is_between(80, 89)).then(pl.lit("MC")).when(pl.col("BODY_TYP").is_between(1, 79)).then(pl.lit("1-79")).otherwise(pl.col("BODY_TYP").cast(pl.String)).alias("BT"))
print(wide(df, "A_PERINJ", "INJSEV_IM", src, "person"))
print(wide(df, "A_EJECT", "EJECT_IM", src, "person"))
print("A_LOC x LOCATION by year group")
for yrs in [(2016, 2017, 2018), (2019, 2020, 2021, 2022, 2023, 2024)]:
    print(yrs); print(wide(df.filter(pl.col("YEAR").is_in(yrs)), "A_LOC", "LOCATION", src, "person"))
for yrs in [(2016, 2017, 2018), (2019,), (2020, 2021, 2022, 2023, 2024)]:
    d = df.filter(pl.col("YEAR").is_in(yrs))
    print(yrs, "A_RESTUSE x REST_USE"); print(wide(d, "A_RESTUSE", "REST_USE", src, "person"))
    print(yrs, "A_RESTUSE x A_PTYPE x BT"); print(d.group_by(["A_RESTUSE", "A_PTYPE", "BT"]).agg(pl.len()).sort(["A_RESTUSE", "A_PTYPE", "BT"]).filter(pl.col("len") > 20))
    print(yrs, "A_HELMUSE x REST_USE/HELM_USE x BT")
    print(d.group_by(["A_HELMUSE", "REST_USE" if yrs[0] < 2019 else "HELM_USE", "BT"]).agg(pl.len()).sort(pl.all().exclude("len")).filter(pl.col("len") > 5))
