import polars as pl
from nhtsa_stats.ingestion.cache import load_table
pl.Config.set_tbl_formatting("ASCII_MARKDOWN"); pl.Config.set_tbl_rows(300); pl.Config.set_tbl_hide_dataframe_shape(True); pl.Config.set_tbl_hide_column_data_types(True); pl.Config.set_tbl_cols(40); pl.Config.set_tbl_width_chars(250)
for src in ['CRSS','FARS']:
    a = load_table(src,'accident',columns=['TYP_INT','RELJCT2','RELJCT1'] + (['WEIGHT','RELJCT2_IM'] if src=='CRSS' else []))
    a = a.with_columns(pl.col('RELJCT2').replace_strict({1:'1_nonjunc',2:'2_int',3:'3_intrel',4:'4_drwy',8:'8_drwyrel',98:'98_NR',99:'99_unk'}, default='other').alias('rj'),
                       pl.col('TYP_INT').replace_strict({1:'1_notint',2:'2_4way',3:'3_T',98:'98_NR',99:'99_unk'}, default='other').alias('ti'))
    for y in ([2019,2021,2022,2024] if src=='CRSS' else [2019,2024]):
        d = a.filter(pl.col('YEAR')==y)
        t = d.group_by(['rj','ti']).len().with_columns((pl.col('len')/pl.col('len').sum().over('rj')*100).round(1).alias('pct')).pivot(on='ti', index='rj', values='pct', sort_columns=True).sort('rj')
        print(f'## {src} {y}: TYP_INT distribution (row %) within RELJCT2'); print(t)
    if src=='CRSS':
        d = a.filter(pl.col('YEAR')==2019)
        print('2019 RELJCT2==98: RELJCT2_IM distribution vs RELJCT1 & TYP_INT'); print(d.filter(pl.col('RELJCT2')==98).group_by(['ti']).len().sort('ti'))
        print(d.group_by(['RELJCT1', pl.col('RELJCT2')==98]).len().sort('RELJCT1'))
