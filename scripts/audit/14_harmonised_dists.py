import polars as pl
from nhtsa_stats.ingestion.cache import load_table
pl.Config.set_tbl_formatting("ASCII_MARKDOWN"); pl.Config.set_tbl_rows(300); pl.Config.set_tbl_hide_dataframe_shape(True); pl.Config.set_tbl_hide_column_data_types(True); pl.Config.set_tbl_cols(40); pl.Config.set_tbl_width_chars(250)
WX = {1:'clear',10:'cloudy',2:'rain',3:'snow_sleet_ice',4:'snow_sleet_ice',11:'snow_sleet_ice',12:'snow_sleet_ice',5:'fog_smoke',6:'other_adverse',7:'other_adverse',8:'other_adverse'}
LT = {1:'daylight',2:'dark_unlighted',3:'dark_lighted',4:'dawn_dusk',5:'dawn_dusk',6:'dark_unknown_lighting',7:'other'}
f = load_table('FARS','accident',columns=['STATE','WEATHER','LGT_COND']).with_columns(pl.lit(1.0).alias('WEIGHT'))
c = load_table('CRSS','accident',columns=['WEATHER','WEATHR_IM','LGT_COND','LGTCON_IM','WEIGHT'])
def dist(d, col, mp, by='YEAR'):
    x = d.with_columns(pl.col(col).replace_strict(mp, default=None).alias('cat')).filter(pl.col('cat').is_not_null())
    return x.group_by([by,'cat']).agg(pl.col('WEIGHT').sum()).with_columns((pl.col('WEIGHT')/pl.col('WEIGHT').sum().over(by)*100).round(1)).pivot(on=by, index='cat', values='WEIGHT', sort_columns=True).sort('cat')
print('## FARS weather (known only) % by year, all states'); print(dist(f,'WEATHER',WX))
print('## FARS weather (known only), excluding CO(8), PA(42), VA(51), KS(20)'); print(dist(f.filter(~pl.col('STATE').is_in([8,42,51,20])),'WEATHER',WX))
print('## FARS weather NR % excl those 4 states'); print(f.filter(~pl.col('STATE').is_in([8,42,51,20])).group_by('YEAR').agg((pl.col('WEATHER').is_in([98,99]).mean()*100).round(2)).sort('YEAR'))
print('## CRSS weather (known only, weighted) % by year'); print(dist(c,'WEATHER',WX))
print('## CRSS WEATHR_IM (weighted) % by year'); print(dist(c,'WEATHR_IM',WX))
print('## FARS light (known) %'); print(dist(f,'LGT_COND',LT))
print('## CRSS light (LGTCON_IM, weighted) %'); print(dist(c,'LGTCON_IM',LT))
