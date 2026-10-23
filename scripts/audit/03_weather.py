import polars as pl
from nhtsa_stats.ingestion.cache import load_table
pl.Config.set_tbl_formatting("ASCII_MARKDOWN"); pl.Config.set_tbl_rows(200); pl.Config.set_tbl_hide_dataframe_shape(True); pl.Config.set_tbl_hide_column_data_types(True); pl.Config.set_tbl_cols(30)
for src, key in [('FARS', ['YEAR','ST_CASE']), ('CRSS', ['YEAR','CASENUM'])]:
    a = load_table(src, 'accident', columns=key[1:] + ['WEATHER','WEATHER1','WEATHER2'] + (['WEATHR_IM'] if src=='CRSS' else []))
    pre = a.filter(pl.col('YEAR') <= 2019)
    print(f'## {src} 2016-2019: WEATHER vs WEATHER1 (agree share)')
    print(pre.group_by('YEAR').agg((pl.col('WEATHER')==pl.col('WEATHER1')).mean().alias('agree_W_W1'), (pl.col('WEATHER2')!=0).mean().alias('has_W2')).sort('YEAR'))
    dis = pre.filter(pl.col('WEATHER')!=pl.col('WEATHER1'))
    print('disagreements WEATHER1, WEATHER2 -> WEATHER (all years pooled)')
    print(dis.group_by(['WEATHER1','WEATHER2','WEATHER']).len().sort('len', descending=True).head(25))
    # when W2 !=0 and agree
    agr2 = pre.filter((pl.col('WEATHER2')!=0)&(pl.col('WEATHER')==pl.col('WEATHER1')))
    print('W2!=0 but WEATHER==WEATHER1:')
    print(agr2.group_by(['WEATHER1','WEATHER2']).len().sort('len', descending=True).head(25))
    # weather table
    wcols = key[1:] + (['WEATHER','WEATHERCODE'] if src=='CRSS' else ['WEATHER'])
    w = load_table(src, 'weather', years=[2020,2021,2022,2023,2024], columns=wcols)
    if src=='CRSS':
        w = w.with_columns(pl.coalesce('WEATHER','WEATHERCODE').alias('WEATHER')).drop('WEATHERCODE')
    print(f'## {src} weather table rows per crash')
    rpc = w.group_by(key).len()
    print(rpc.group_by(['YEAR','len']).len(name='n_crashes').sort(['YEAR','len']))
    print('weather table code distribution by year (%)')
    d = w.group_by(['YEAR','WEATHER']).len().with_columns((100*pl.col('len')/pl.col('len').sum().over('YEAR')).round(2).alias('pct'))
    print(d.pivot(on='YEAR', index='WEATHER', values='pct', sort_columns=True).sort('WEATHER'))
    post = a.filter(pl.col('YEAR') >= 2020).select(key + ['WEATHER'])
    # crashes in accident not in weather table
    j = post.join(w.group_by(key).agg(pl.col('WEATHER').sort().alias('wl'), pl.len().alias('nrow')), on=key, how='left')
    print('accident crashes with no weather row:', j.filter(pl.col('nrow').is_null()).group_by('YEAR').len().sort('YEAR'))
    j1 = j.filter(pl.col('nrow')==1).with_columns(pl.col('wl').list.first().alias('w1'))
    print('single-row crashes: WEATHER(accident)==weather row share by year')
    print(j1.group_by('YEAR').agg((pl.col('WEATHER')==pl.col('w1')).mean()).sort('YEAR'))
    print('single-row disagreements:'); print(j1.filter(pl.col('WEATHER')!=pl.col('w1')).group_by(['w1','WEATHER']).len().sort('len',descending=True).head(15))
    jm = j.filter(pl.col('nrow')>1).with_columns(pl.col('wl').cast(pl.List(pl.String)).list.join(',').alias('wl_s'))
    print('multi-row: weather list -> accident WEATHER')
    print(jm.group_by(['wl_s','WEATHER']).len().sort('len',descending=True).head(30))
    print('multi-row: is accident WEATHER one of the rows?', jm.select(pl.col('wl').list.contains(pl.col('WEATHER')).mean()))
