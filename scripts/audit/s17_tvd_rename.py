"""TVD 2019->2020 across renamed variables (row-level code distributions, unweighted)."""
import sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
import polars as pl
from common import OUT
cs = pl.read_csv(f"{OUT}/codesets.csv", schema_overrides={"code": pl.Utf8, "label": pl.Utf8, "nlabel": pl.Utf8})
pairs = [("distract", "MDRDSTRD", "DRDISTRACT"), ("factor", "MFACTOR", "VEHICLECC"), ("maneuver", "MDRMANAV", "MANEUVER"),
         ("violatn", "MVIOLATN", "VIOLATION"), ("vision", "MVISOBSC", "VISION")]
for src in ["FARS", "CRSS"]:
    for t, a, b in pairs:
        x = cs.filter((pl.col("source") == src) & (pl.col("table") == t) & (((pl.col("variable") == a) & (pl.col("YEAR") == 2019)) | ((pl.col("variable") == b) & (pl.col("YEAR") == 2020))))
        x = x.with_columns(s=pl.col("n") / pl.col("n").sum().over("YEAR"))
        p = x.pivot(on="YEAR", index="code", values="s").fill_null(0)
        tvd = 0.5 * (p["2019"] - p["2020"]).abs().sum() * 100
        # label changes for shared codes
        l19 = dict(x.filter(pl.col("YEAR") == 2019).select("code", "nlabel").iter_rows())
        l20 = dict(x.filter(pl.col("YEAR") == 2020).select("code", "nlabel").iter_rows())
        diff = [c for c in l19 if c in l20 and l19[c] != l20[c]]
        print(src, t, f"TVD 2019->2020 = {tvd:.1f}%", "label-text changes on shared codes:", diff, "codes dropped:", sorted(set(l19) - set(l20)), "added:", sorted(set(l20) - set(l19)))
