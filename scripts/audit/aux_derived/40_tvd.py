"""Year-to-year total variation distance (pp) of every aux variable; CRSS weighted by WEIGHT."""
import sys; sys.path.insert(0, "scripts/audit/aux_derived")
from helpers import *
from pathlib import Path
c = pl.col
rows = []
for src in ["FARS", "CRSS"]:
    for tab in ["acc_aux", "veh_aux", "per_aux"]:
        frames = [pl.read_parquet(f"/home/user/nhtsa-stats-US/data/interim/{src}/{tab}/{y}.parquet") for y in YEARS]
        cols = sorted({x for f in frames for x in f.columns if x.startswith("A_") and x not in ("A_MOD_YR", "A_IMP2")})
        for v in cols:
            dist = {}
            for y, f in zip(YEARS, frames):
                if v not in f.columns:
                    continue
                d = f.group_by(v).agg(c("WEIGHT").sum().alias("w") if src == "CRSS" else pl.len().cast(pl.Float64).alias("w"))
                tot = d["w"].sum()
                dist[y] = {k: 100 * x / tot for k, x in d.iter_rows()}
            ys = sorted(dist)
            for a, b in zip(ys[:-1], ys[1:]):
                keys = set(dist[a]) | set(dist[b])
                tvd = 0.5 * sum(abs(dist[a].get(k, 0) - dist[b].get(k, 0)) for k in keys)
                rows.append(dict(source=src, table=tab, var=v, y0=a, y1=b, tvd=round(tvd, 2), new_codes=str(sorted(set(dist[b]) - set(dist[a]))), dropped=str(sorted(set(dist[a]) - set(dist[b])))))
t = pl.DataFrame(rows)
t.write_csv(f"/tmp/nhtsa-audit/out_aux/tvd.csv")
w = t.pivot(on="y1", index=["source", "table", "var"], values="tvd", sort_columns=True)
print(w.filter(pl.max_horizontal(pl.all().exclude(["source", "table", "var"])) >= 2.0))
print(t.filter((c("new_codes") != "[]") | (c("dropped") != "[]")).select("source", "var", "y0", "y1", "new_codes", "dropped"))
