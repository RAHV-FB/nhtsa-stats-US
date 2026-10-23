import sys; sys.path.insert(0, "scripts/audit/aux_derived")
from helpers import *
for src in ["FARS", "CRSS"]:
    extra = ["AGE_IM"] if src == "CRSS" else []
    df = aux_main(src, "per", [f"A_AGE{i}" for i in range(1, 10)], ["AGE"] + extra)
    for i in range(1, 10):
        a = f"A_AGE{i}"
        for agev in ["AGE"] + extra:
            r = df.group_by(a).agg(pl.col(agev).min().alias("min"), pl.col(agev).max().alias("max"), pl.len().alias("n"),
                                   pl.col(agev).filter(pl.col(agev) < 200).max().alias("max_valid")).sort(a)
            # check overlap: for each AGE value, number of distinct codes
            amb = df.group_by(agev).agg(pl.col(a).n_unique().alias("k")).filter(pl.col("k") > 1)
            print(f"{src} {a} vs {agev}: ages mapping to >1 code: {amb.height} -> {amb.sort(agev).head(10).to_dicts()}")
            print(r.transpose(include_header=True).to_pandas().to_string(index=False, header=False))
