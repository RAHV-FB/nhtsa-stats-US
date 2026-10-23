import sys; sys.path.insert(0, "scripts/audit/aux_derived")
from helpers import *
c = pl.col
K = ["YEAR", "ST_CASE"]
acc = load_table("FARS", "acc_aux", columns=["ST_CASE", "A_POSBAC"])
p = aux_main("FARS", "per", ["A_ALCTES", "A_PTYPE"], ["ALC_RES", "PER_TYP", "INJ_SEV"])
for who, filt in [("drivers", c("PER_TYP") == 1), ("drivers+nonocc", c("PER_TYP").is_in([1, 5, 6, 7, 8]))]:
    g = p.filter(filt).group_by(K).agg((c("A_ALCTES") == 2).sum().alias("pos"), (c("A_ALCTES") == 1).sum().alias("zero"), (c("A_ALCTES") >= 3).sum().alias("unk"), pl.len().alias("n"))
    x = acc.join(g, on=K, how="left").with_columns(pl.all().exclude(K + ["A_POSBAC"]).fill_null(0))
    x = x.with_columns(pl.when(c("pos") > 0).then(pl.lit("pos>0")).when((c("zero") > 0) & (c("unk") == 0)).then(pl.lit("allzero")).when(c("zero") > 0).then(pl.lit("zero+unk")).when(c("n") == 0).then(pl.lit("none")).otherwise(pl.lit("allunk")).alias("pat"))
    print(who); print(x.group_by(["pat", "A_POSBAC"]).agg(pl.len()).sort(["pat", "A_POSBAC"]).pivot(on="A_POSBAC", index="pat", values="len", sort_columns=True))
