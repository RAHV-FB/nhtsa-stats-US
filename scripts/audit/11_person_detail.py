import sys; sys.path.insert(0, "scripts/audit")
from helpers import *
src = "FARS"
df = aux_main(src, "per", ["A_RESTUSE", "A_HELMUSE", "A_PTYPE", "A_ALCTES", "A_DOA", "A_PERINJ"], ["REST_USE", "HELM_USE", "PER_TYP", "BODY_TYP", "ALC_STATUS", "ALC_RES", "DOA", "INJ_SEV"])
# body type class: motorcycle 80-89 (FARS BODY_TYP), else
df = df.with_columns(pl.when(pl.col("BODY_TYP").is_between(80, 89)).then(pl.lit("MC")).when(pl.col("BODY_TYP").is_between(1, 79)).then(pl.lit("1-79")).otherwise(pl.col("BODY_TYP").cast(pl.String)).alias("BT"))
print("A_RESTUSE x REST_USE by year-group")
for yrs in [(2016, 2017, 2018, 2019), (2020, 2021, 2022, 2023, 2024)]:
    d = df.filter(pl.col("YEAR").is_in(yrs))
    print(yrs); print(wide(d, "A_RESTUSE", "REST_USE", src, "person"))
print("A_RESTUSE x BT x A_PTYPE (2020+ code 4)")
print(df.filter(pl.col("YEAR") >= 2020).group_by(["A_RESTUSE", "A_PTYPE", "BT"]).agg(pl.len()).sort(["A_RESTUSE","A_PTYPE","BT"]))
print(df.filter(pl.col("YEAR") < 2020).group_by(["A_RESTUSE", "A_PTYPE", "BT"]).agg(pl.len()).sort(["A_RESTUSE","A_PTYPE","BT"]))
print("A_HELMUSE by year x HELM_USE (null shown)")
print(df.group_by(["YEAR", "A_HELMUSE", "HELM_USE"]).agg(pl.len()).sort(["YEAR", "A_HELMUSE", "HELM_USE"]).filter(pl.col("YEAR").is_in([2016, 2018, 2019, 2020])))
print("2016-2018 A_HELMUSE x REST_USE x BT")
print(df.filter(pl.col("YEAR") <= 2018).group_by(["A_HELMUSE", "REST_USE", "BT"]).agg(pl.len()).sort(["A_HELMUSE", "REST_USE", "BT"]))
print("2019 A_HELMUSE x HELM_USE x BT")
print(df.filter(pl.col("YEAR") == 2019).group_by(["A_HELMUSE", "HELM_USE", "BT"]).agg(pl.len()).sort(["A_HELMUSE", "HELM_USE", "BT"]))
print("2020+ A_HELMUSE x HELM_USE x BT")
print(df.filter(pl.col("YEAR") >= 2020).group_by(["A_HELMUSE", "HELM_USE", "BT"]).agg(pl.len()).sort(["A_HELMUSE", "HELM_USE", "BT"]))
