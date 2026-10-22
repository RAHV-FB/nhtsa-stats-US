import polars as pl
from nhtsa_stats.ingestion.cache import load_table
pl.Config.set_tbl_formatting("ASCII_MARKDOWN"); pl.Config.set_tbl_rows(300); pl.Config.set_tbl_hide_dataframe_shape(True); pl.Config.set_tbl_hide_column_data_types(True); pl.Config.set_tbl_cols(40); pl.Config.set_tbl_width_chars(250)
for src, k in [('FARS','ST_CASE'),('CRSS','CASENUM')]:
    a = load_table(src,'accident',columns=[k,'CF1','CF2','CF3'] + (['WEIGHT'] if src=='CRSS' else []))
    pre = a.filter(pl.col('YEAR')<=2019).unpivot(index=['YEAR',k], on=['CF1','CF2','CF3'], value_name='code').drop('variable')
    # how many CF slots used
    print(src, 'CF slots used per crash 2016-19:', a.filter(pl.col('YEAR')<=2019).with_columns(((pl.col('CF1')>0)&(pl.col('CF1')<99)).cast(pl.Int8).alias('c1'),((pl.col('CF2')>0)&(pl.col('CF2')<99)).cast(pl.Int8).alias('c2'),((pl.col('CF3')>0)&(pl.col('CF3')<99)).cast(pl.Int8).alias('c3')).with_columns((pl.col('c1')+pl.col('c2')+pl.col('c3')).alias('ns')).group_by('ns').len().sort('ns'))
    print('CF2>0 while CF1==0:', a.filter((pl.col('YEAR')<=2019)&(pl.col('CF1')==0)&(pl.col('CF2')>0)).height, ' CF1=99 & CF2 not 0/99:', a.filter((pl.col('YEAR')<=2019)&(pl.col('CF1')==99)&(~pl.col('CF2').is_in([0,99]))).height)
    rf = load_table(src,'crashrf',years=[2020,2021,2022,2023,2024],columns=[k,'CRASHRF']).rename({'CRASHRF':'code'})
    print(src,'crashrf rows per crash', rf.group_by(['YEAR',k]).len().group_by('len').len(name='n').sort('len'))
    print('crashrf: 0 co-occurring with other code:', rf.group_by(['YEAR',k]).agg((pl.col('code')==0).any().alias('has0'), (pl.col('code')!=0).any().alias('hasoth')).filter(pl.col('has0')&pl.col('hasoth')).height)
    allc = pl.concat([pre, rf.select(['YEAR',k,'code'])])
    crashes = a.select(['YEAR',k] + (['WEIGHT'] if src=='CRSS' else []))
    if src=='FARS': crashes = crashes.with_columns(pl.lit(1.0).alias('WEIGHT'))
    codes = [14,15,16,19,20,21,23,24,26,27,28,31]
    flags = allc.group_by(['YEAR',k]).agg([(pl.col('code')==c).any().alias(f'cf{c}') for c in codes] + [((pl.col('code')>0)&(~pl.col('code').is_in([99,999]))).any().alias('any_factor'), pl.col('code').is_in([99,999]).any().alias('unknown')])
    j = crashes.join(flags, on=['YEAR',k], how='left')
    print('crashes without any CF/crashrf row:', j.filter(pl.col('any_factor').is_null()).group_by('YEAR').len().sort('YEAR'))
    j = j.fill_null(False)
    cols = [f'cf{c}' for c in codes] + ['any_factor','unknown']
    print(src, 'crash-level % with factor (weighted for CRSS)')
    print(j.group_by('YEAR').agg([((pl.col(c).cast(pl.Float64)*pl.col('WEIGHT')).sum()/pl.col('WEIGHT').sum()*100).round(2).alias(c) for c in cols]).sort('YEAR'))
