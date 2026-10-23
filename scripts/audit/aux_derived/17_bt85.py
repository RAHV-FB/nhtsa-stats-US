import sys; sys.path.insert(0, "scripts/audit/aux_derived")
from helpers import *
for src in ["FARS", "CRSS"]:
    df = aux_main(src, "per", ["A_RESTUSE", "A_HELMUSE"], ["BODY_TYP", "REST_USE", "HELM_USE", "HELM_MIS", "REST_MIS", "PER_TYP"], years=[2020, 2021, 2022, 2023, 2024])
    print(src, "MC 80-89 2020+")
    print(df.filter(pl.col("BODY_TYP").is_between(80, 89)).group_by(["BODY_TYP", "A_RESTUSE", "A_HELMUSE", "HELM_USE"]).agg(pl.len()).sort(pl.all().exclude("len")))
    print(src, "helmeted MC by HELM_MIS")
    print(df.filter(pl.col("BODY_TYP").is_between(80, 89) & pl.col("HELM_USE").is_in([5, 16, 19])).group_by(["A_HELMUSE", "HELM_MIS"]).agg(pl.len()).sort(pl.all().exclude("len")))
    d16 = aux_main(src, "per", ["A_HELMUSE"], ["BODY_TYP", "REST_USE", "REST_MIS"], years=[2016, 2017, 2018])
    print(src, "2016-18 helmet codes by REST_MIS")
    print(d16.filter(pl.col("REST_USE").is_in([5, 16, 19, 8, 97])).group_by(["A_HELMUSE", "REST_USE", "REST_MIS"]).agg(pl.len()).sort(pl.all().exclude("len")))
