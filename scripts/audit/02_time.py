import polars as pl
from nhtsa_stats.ingestion.cache import load_table
pl.Config.set_tbl_formatting("ASCII_MARKDOWN"); pl.Config.set_tbl_rows(100); pl.Config.set_fmt_str_lengths(120); pl.Config.set_tbl_hide_dataframe_shape(True); pl.Config.set_tbl_hide_column_data_types(True)
CB = pl.read_csv('/home/user/nhtsa-stats-US/outputs/audit/codebook.csv', infer_schema_length=0)
for src, cols in [('FARS', ['HOUR','MINUTE','DAY','MONTH','DAY_WEEK']), ('CRSS', ['HOUR','MINUTE','HOUR_IM','MINUTE_IM','DAY_WEEK','WKDY_IM','MONTH'])]:
    df = load_table(src, 'accident', columns=cols)
    for v in cols:
        lim = {'HOUR':23,'HOUR_IM':23,'MINUTE':59,'MINUTE_IM':59,'DAY':31,'MONTH':12,'DAY_WEEK':7,'WKDY_IM':7}[v]
        lo = 0 if v.startswith(('HOUR','MINUTE')) else 1
        out = df.group_by('YEAR').agg(pl.len().alias('n'), pl.col(v).min().alias('min'),
                                     ((pl.col(v) < lo) | (pl.col(v) > lim)).sum().alias('n_out'),
                                     pl.col(v).filter((pl.col(v) < lo) | (pl.col(v) > lim)).unique().sort().cast(pl.String).str.join(',').alias('outcodes')).sort('YEAR')
        out = out.with_columns((100*pl.col('n_out')/pl.col('n')).round(3).alias('pct_out'))
        print(src, v); print(out)
        labs = CB.filter((pl.col('source')==src)&(pl.col('table')=='accident')&(pl.col('variable')==v)&(pl.col("code").cast(pl.Int64, strict=False)>lim))
        print(labs.select('year','code','label','n').sort('year','code'))
    # FARS: hour label check for in-range codes
    lab = CB.filter((pl.col('source')==src)&(pl.col('table')=='accident')&(pl.col('variable')=='HOUR')&(pl.col("code").cast(pl.Int64, strict=False)<=23))
    print(lab.group_by('code').agg(pl.col('label').unique().str.join(' || ')).sort(pl.col("code").cast(pl.Int64, strict=False)))
