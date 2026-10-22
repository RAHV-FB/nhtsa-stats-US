"""DR_ZIP special codes and label check; DR_PRES x SPEEDREL=8; LBDNS 2018 vs distract code."""
import sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
import polars as pl
from common import OUT, lt
pl.Config.set_tbl_rows(100); pl.Config.set_tbl_hide_dataframe_shape(True); pl.Config.set_tbl_hide_column_data_types(True)
for src in ["FARS", "CRSS"]:
    yrs = [2019, 2024]
    try:
        v = lt(src, "vehicle", ["YEAR", "DR_ZIP", "DR_ZIPNAME", "DR_PRES"], years=yrs)
    except Exception as e:
        print("no DR_ZIPNAME", e); v = lt(src, "vehicle", ["YEAR", "DR_ZIP", "DR_PRES"], years=yrs)
    special = v.filter((pl.col("DR_ZIP") >= 99990) | (pl.col("DR_ZIP") < 501))
    print(src); print(special.group_by([c for c in special.columns if c not in ("DR_PRES",)]).agg(pl.len(), (pl.col("DR_PRES")==1).sum().alias("drv_present")).sort("YEAR","DR_ZIP"))
    f = pl.read_parquet(f"{OUT}/frame_{src}.parquet", columns=["YEAR", "DR_PRES", "SPEEDREL", "DR_ZIP", "DRV_INJ_SEV"] + (["MAX_SEV","WEIGHT"] if src=="CRSS" else []))
    print(f.group_by("DR_PRES", "SPEEDREL").len().filter((pl.col("SPEEDREL") == 8) | (pl.col("DR_PRES") != 1)).sort("DR_PRES", "SPEEDREL"))
    print("DR_ZIP 99999 share by year (driver present):")
    print(f.filter(pl.col("DR_PRES")==1).group_by("YEAR").agg((pl.col("DR_ZIP")==99999).mean().mul(100).round(2).alias("pct99999"), (pl.col("DR_ZIP")==99997).mean().mul(100).round(2).alias("pct99997"), (pl.col("DR_ZIP")==99998).mean().mul(100).round(2).alias("pct99998"), (pl.col("DR_ZIP")==0).mean().mul(100).round(3).alias("pct0")).sort("YEAR"))
