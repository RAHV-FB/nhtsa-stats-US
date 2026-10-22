import sys; sys.path.insert(0, "scripts/audit")
from helpers import *
c = pl.col
a = aux_main("CRSS", "crash", ["A_JUNC", "WEIGHT"], ["RELJCT2", "RELJCT2_IM"], years=[2018, 2019, 2020])
a = a.with_columns(c("RELJCT2").is_in([98, 99]).alias("unk"))
t = a.group_by(["YEAR", "unk", "A_JUNC"]).agg(c("WEIGHT").sum().alias("w"))
t = t.join(t.group_by(["YEAR", "unk"]).agg(c("w").sum().alias("tw")), on=["YEAR", "unk"]).with_columns((100 * c("w") / c("tw")).round(1).alias("pct"))
print(t.sort(["YEAR", "unk", "A_JUNC"]).pivot(on="A_JUNC", index=["YEAR", "unk"], values="pct", sort_columns=True))
print(a.group_by("YEAR").agg((c("unk").cast(pl.Float64) * c("WEIGHT")).sum() / c("WEIGHT").sum() * 100).sort("YEAR"))
