"""Compare code sets & normalised labels per year for crash-environment variables (from codebook.csv),
and compute raw code distributions from the parquet cache (covers unlabelled CRSS 2016-2018)."""
import re, sys
import polars as pl
from nhtsa_stats.ingestion.cache import load_table

CB = pl.read_csv('/home/user/nhtsa-stats-US/outputs/audit/codebook.csv', infer_schema_length=0)
VARS = sys.argv[1].split(',')
TABLE = sys.argv[2] if len(sys.argv) > 2 else 'accident'
SOURCES = sys.argv[3].split(',') if len(sys.argv) > 3 else ['FARS', 'CRSS']

def norm(s):
    if s is None: return None
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9]+', ' ', s.lower())).strip()

for src in SOURCES:
    for v in VARS:
        try:
            df = load_table(src, TABLE, columns=[v])
        except Exception as e:
            continue
        df = df.filter(pl.col(v).is_not_null()) if df[v].dtype != pl.Null else df.head(0)
        if df.height == 0:
            continue
        dist = (df.group_by(['YEAR', v]).len().with_columns((100 * pl.col('len') / pl.col('len').sum().over('YEAR')).alias('pct')))
        years = sorted(dist['YEAR'].unique().to_list())
        cb = CB.filter((pl.col('source') == src) & (pl.col('table') == TABLE) & (pl.col('variable') == v))
        cb = cb.with_columns(pl.col('label').map_elements(norm, return_dtype=pl.String).alias('nl'))
        print(f'\n=== {src}.{TABLE}.{v} ===  years={years[0]}-{years[-1]}  n_codes_by_year=' +
              ' '.join(f"{y}:{dist.filter(pl.col('YEAR')==y).height}" for y in years))
        codes = sorted(dist[v].unique().to_list(), key=lambda x: (str(type(x)), x))
        allcb_codes = set(cb['code'].to_list())
        rows = []
        for c in codes:
            sc = str(c)
            labs = cb.filter(pl.col('code') == sc)
            # label variants
            var = labs.group_by('nl').agg(pl.col('year').sort().str.join(','), pl.col('label').first()).sort('year')
            lab_str = ' | '.join(f"[{r['year']}] {r['label']}" for r in var.iter_rows(named=True)) if var.height > 1 else (var['label'][0] if var.height else '(no label)')
            pcts = []
            for y in years:
                r = dist.filter((pl.col('YEAR') == y) & (pl.col(v) == c))
                pcts.append(f"{r['pct'][0]:5.2f}" if r.height else "    -")
            rows.append(f"{sc:>6} {' '.join(pcts)}  {lab_str}")
        print('  code ' + ' '.join(f'{str(y)[2:]:>5}' for y in years))
        print('\n'.join(rows))
