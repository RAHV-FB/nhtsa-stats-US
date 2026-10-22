"""Per source-year code distributions of every column in acc_aux/veh_aux/per_aux."""
import polars as pl
from pathlib import Path
OUT = Path("/tmp/nhtsa-audit/out_aux")
rows = []
for src in ["FARS", "CRSS"]:
    for tab in ["acc_aux", "veh_aux", "per_aux"]:
        for y in range(2016, 2025):
            p = Path(f"/home/user/nhtsa-stats-US/data/interim/{src}/{tab}/{y}.parquet")
            df = pl.read_parquet(p)
            n = df.height
            for c in df.columns:
                if c in ("ST_CASE", "CASENUM", "WEIGHT", "YEAR", "VEH_NO", "PER_NO"):
                    continue
                s = df[c]
                nd = s.n_unique()
                if nd > 60:
                    rows.append(dict(source=src, table=tab, year=y, var=c, code="__MANY__", n=n, nnull=s.null_count(),
                                     dtype=str(s.dtype), nd=nd, mn=str(s.min()), mx=str(s.max())))
                    continue
                vc = s.value_counts().sort(c)
                for code, k in vc.iter_rows():
                    rows.append(dict(source=src, table=tab, year=y, var=c, code=str(code), n=k, nnull=s.null_count(),
                                     dtype=str(s.dtype), nd=nd, mn="", mx=""))
out = pl.DataFrame(rows)
out.write_csv(OUT / "aux_dist.csv")
print(out.height)
