"""A_LIC_S=4 meaning: cross-tab against body type, CDL status, L_TYPE."""
import sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
import polars as pl
from common import OUT
pl.Config.set_tbl_rows(100); pl.Config.set_tbl_hide_dataframe_shape(True); pl.Config.set_tbl_hide_column_data_types(True); pl.Config.set_tbl_width_chars(250)
f = pl.read_parquet(f"{OUT}/frame_FARS.parquet")
f = f.with_columns(bt=pl.when(pl.col("BODY_TYP").is_between(80, 89)).then(pl.lit("MC")).when(pl.col("BODY_TYP").is_between(60, 79)).then(pl.lit("truck60-79")).when(pl.col("BODY_TYP").is_between(50, 59)).then(pl.lit("bus50-59")).otherwise(pl.lit("other")))
print(f.group_by("A_LIC_S", "bt").len().pivot(on="bt", index="A_LIC_S", values="len").sort("A_LIC_S"))
print(f.group_by("A_LIC_S", "A_CDL_S").len().pivot(on="A_CDL_S", index="A_LIC_S", values="len", sort_columns=True).sort("A_LIC_S"))
print(f.group_by("A_LIC_S", "A_MC_L_S").len().pivot(on="A_MC_L_S", index="A_LIC_S", values="len", sort_columns=True).sort("A_LIC_S"))
x = f.filter(pl.col("A_LIC_S") == 4)
print("A_LIC_S=4: CDL_STAT"); print(x.group_by("CDL_STAT").len().sort("CDL_STAT"))
print("A_LIC_S=4: L_TYPE"); print(x.group_by("L_TYPE").len().sort("L_TYPE"))
# rule test: A_LIC_S==4 iff (CDL_STAT not 0/97/99?) or MC
f = f.with_columns(rule4=(pl.col("CDL_STAT").is_in([1,2,3,4,5,6,7,8])) | (pl.col("BODY_TYP").is_between(80, 89)))
print(f.group_by("A_LIC_S", "rule4").len().sort("A_LIC_S", "rule4"))
f = f.with_columns(rule4b=(pl.col("CDL_STAT").is_in([1,2,3,4,5,6,7,8])) | (pl.col("A_MC_L_S") != 4))
print(f.group_by("YEAR", "A_LIC_S", "rule4b").len().filter(pl.col("YEAR").is_in([2016, 2024])).sort("YEAR", "A_LIC_S", "rule4b"))
