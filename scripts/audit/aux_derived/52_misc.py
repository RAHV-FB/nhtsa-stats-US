import sys; sys.path.insert(0, "scripts/audit/aux_derived")
from helpers import *
c = pl.col
p = load_table("FARS", "person", columns=["HISPANIC", "INJ_SEV"])
print("FARS HISPANIC 97 (redacted) / 99 among fatalities by year:")
print(p.filter(c("INJ_SEV") == 4).group_by("YEAR").agg((c("HISPANIC") == 97).mean().mul(100).round(2).alias("pct97"), (c("HISPANIC") == 99).mean().mul(100).round(2).alias("pct99")).sort("YEAR").to_dicts())
r = load_table("FARS", "race", years=list(range(2019, 2025)), columns=["RACE"])
print("FARS race rows RACE 96 redacted by year:", r.group_by("YEAR").agg((c("RACE") == 96).sum().alias("n96"), (c("RACE") == 99).sum().alias("n99"), pl.len()).sort("YEAR").to_dicts())
for src in ["FARS", "CRSS"]:
    d = aux_main(src, "per", ["A_HELMUSE"] + (["WEIGHT"] if src == "CRSS" else []), ["BODY_TYP", "PER_TYP", "REST_USE"])
    w = c("WEIGHT") if src == "CRSS" else pl.lit(1.0)
    d = d.with_columns((c("WEIGHT") if src == "CRSS" else pl.lit(1.0)).alias("w"))
    print(src, "A_HELMUSE=1 among NON-motorcycle persons (artefact), weighted share of all A_HELMUSE=1, by year:")
    print(d.group_by("YEAR").agg((((c("A_HELMUSE") == 1) & ~c("BODY_TYP").is_between(80, 89).fill_null(False)).cast(pl.Float64) * c("w")).sum().alias("nonmc1"),
                                 ((c("A_HELMUSE") == 1).cast(pl.Float64) * c("w")).sum().alias("all1")).with_columns((100 * c("nonmc1") / c("all1")).round(1).alias("pct")).sort("YEAR").select("YEAR", "pct").to_dicts())
v = aux_main("FARS", "veh", ["A_IMP2"], ["IMPACT1"], years=[2016, 2017, 2018, 2019])
print("FARS A_IMP2 non-null 2016-2019:", v["A_IMP2"].drop_nulls().len(), "of", v.height)
