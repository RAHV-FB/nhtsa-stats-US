import polars as pl
from nhtsa_stats.ingestion.cache import load_table
pl.Config.set_tbl_formatting("ASCII_MARKDOWN"); pl.Config.set_tbl_rows(300); pl.Config.set_tbl_hide_dataframe_shape(True); pl.Config.set_tbl_hide_column_data_types(True); pl.Config.set_tbl_cols(40); pl.Config.set_tbl_width_chars(250)
HG = {}
for c in [1]: HG[c] = 'rollover'
for c in [2,3,5,6,7,51,72,44]: HG[c] = 'other_noncollision'
for c in [12,54,55]: HG[c] = 'mv_in_transport'
HG[14] = 'parked_mv'
HG[8] = 'pedestrian'
for c in [9]: HG[c] = 'pedalcyclist'
for c in [15]: HG[c] = 'other_nonmotorist'
for c in [10,74]: HG[c] = 'railway'
for c in [11,49]: HG[c] = 'animal'
for c in [16,18,45,73,91]: HG[c] = 'object_not_fixed'
for c in [17,19,20,21,23,24,25,26,30,31,32,33,34,35,38,39,40,41,42,43,46,48,50,52,53,57,58,59,93]: HG[c] = 'fixed_object'
for c in [98,99]: HG[c] = None
MC = {0:'not_mv_collision',1:'rear_end',2:'head_on',6:'angle',7:'sideswipe_same',8:'sideswipe_opposite',9:'other_mv',10:'other_mv',11:'other_mv'}
RR = {1:'on_roadway',11:'on_roadway',2:'shoulder',3:'median_island',10:'median_island',12:'median_island',4:'roadside',5:'outside_trafficway',7:'parking_lane',8:'gore',6:'off_roadway_unknown'}
f = load_table('FARS','accident',columns=['HARM_EV','MAN_COLL','REL_ROAD']).with_columns(pl.lit(1.0).alias('WEIGHT'))
c = load_table('CRSS','accident',columns=['HARM_EV','EVENT1_IM','MAN_COLL','REL_ROAD','WEIGHT'])
allcodes = set(f['HARM_EV'].unique().to_list()) | set(c['HARM_EV'].unique().to_list())
print('HARM_EV codes not mapped:', sorted(x for x in allcodes if x not in HG))
def dist(d, col, mp):
    x = d.with_columns(pl.col(col).replace_strict(mp, default='__unmapped').alias('cat')).filter(pl.col('cat').is_not_null())
    return x.group_by(['YEAR','cat']).agg(pl.col('WEIGHT').sum()).with_columns((pl.col('WEIGHT')/pl.col('WEIGHT').sum().over('YEAR')*100).round(2)).pivot(on='YEAR', index='cat', values='WEIGHT', sort_columns=True).sort('cat')
for nm, d in [('FARS', f), ('CRSS(weighted)', c)]:
    print(f'## {nm} HARM_EV group % (known)'); print(dist(d,'HARM_EV',HG))
    print(f'## {nm} MAN_COLL group % (known)'); print(dist(d,'MAN_COLL',MC))
    print(f'## {nm} REL_ROAD group % (known)'); print(dist(d,'REL_ROAD',RR))
