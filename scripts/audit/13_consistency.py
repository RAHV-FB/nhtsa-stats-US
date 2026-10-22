import polars as pl
from nhtsa_stats.ingestion.cache import load_table
pl.Config.set_tbl_formatting("ASCII_MARKDOWN"); pl.Config.set_tbl_rows(300); pl.Config.set_tbl_hide_dataframe_shape(True); pl.Config.set_tbl_hide_column_data_types(True); pl.Config.set_tbl_cols(40); pl.Config.set_tbl_width_chars(250); pl.Config.set_fmt_str_lengths(60)
f = load_table('FARS','accident',columns=['HOUR','MONTH','LGT_COND','MAN_COLL','HARM_EV','RAIL','RELJCT2','RELJCT1','NHS','FUNC_SYS','ROUTE','SCH_BUS','VE_FORMS','PEDS','RUR_URB'])
c = load_table('CRSS','accident',columns=['HOUR','HOUR_IM','MONTH','LGT_COND','LGTCON_IM','MAN_COLL','HARM_EV','RELJCT2','RELJCT1','INT_HWY','URBANICITY','VE_FORMS','WEIGHT','SCH_BUS'])
for nm, d in [('FARS', f), ('CRSS', c)]:
    # light vs hour plausibility
    dd = d.filter(pl.col('HOUR')<24)
    print(nm, 'Daylight share by hour band; dark(2,3,6) share in 11-14h')
    print(dd.group_by(pl.when(pl.col('HOUR').is_in([0,1,2,3])).then(pl.lit('00-03')).when(pl.col('HOUR').is_in([11,12,13,14])).then(pl.lit('11-14')).otherwise(pl.lit('other')).alias('hb')).agg(
        ((pl.col('LGT_COND')==1).mean()*100).round(2).alias('pct_daylight'), (pl.col('LGT_COND').is_in([2,3,6]).mean()*100).round(2).alias('pct_dark'), pl.len()).sort('hb'))
    # MAN_COLL vs HARM_EV
    print(nm, 'MAN_COLL==0 vs HARM_EV==12 (MVIT)')
    print(d.group_by([pl.col('HARM_EV')==12, pl.col('MAN_COLL').replace_strict({0:'0',98:'98/99',99:'98/99'}, default='1-11')]).len().sort('HARM_EV','MAN_COLL'))
    print(nm, 'single-vehicle (VE_FORMS==1) with MAN_COLL in 1-11:', d.filter((pl.col('VE_FORMS')==1)&(pl.col('MAN_COLL').is_between(1,11))).height, 'of', d.filter(pl.col('VE_FORMS')==1).height)
    print(nm, 'RELJCT1 x RELJCT2 interchange codes (18,19,20,5,17):')
    print(d.filter(pl.col('RELJCT1').is_in([0,1])).group_by('RELJCT1').agg((pl.col('RELJCT2').is_in([5,17,18,19,20]).mean()*100).round(2).alias('pct_interchange_type_rj2'), pl.len()))
print('FARS RAIL vs RELJCT2=6 / HARM_EV=10')
print(f.group_by([pl.col('RAIL')!='0000000', pl.col('RELJCT2')==6]).len().sort('RAIL'))
print(f.group_by([pl.col('RAIL')!='0000000', pl.col('HARM_EV')==10]).len().sort('RAIL'))
print('FARS NHS x FUNC_SYS (row %)')
print(f.filter(pl.col('FUNC_SYS')<=7).group_by(['FUNC_SYS','NHS']).len().with_columns((pl.col('len')/pl.col('len').sum().over('FUNC_SYS')*100).round(1)).pivot(on='NHS', index='FUNC_SYS', values='len', sort_columns=True).sort('FUNC_SYS'))
print('FARS ROUTE=1 (interstate) vs FUNC_SYS=1 (2016-2022 / 2023+)')
print(f.group_by([pl.col('YEAR')>=2023, pl.col('ROUTE')==1, pl.col('FUNC_SYS')==1]).len().sort(['YEAR','ROUTE','FUNC_SYS']))
print('CRSS INT_HWY plausibility: % RELJCT2=intersection(2), % interchange types, % RELJCT1=1, by INT_HWY (weighted)')
W = pl.col('WEIGHT')
print(c.filter(pl.col('INT_HWY').is_in([0,1])).group_by('INT_HWY').agg(((pl.col('RELJCT2')==2).cast(pl.Float64)*W).sum()/W.sum()*100, ((pl.col('RELJCT2').is_in([5,17,18,19,20])).cast(pl.Float64)*W).sum().alias('ic')/W.sum()*100, ((pl.col('RELJCT1')==1).cast(pl.Float64)*W).sum().alias('rj1')/W.sum()*100))
print('CRSS URBANICITY: weighted LGT_COND dist (%) by URBANICITY')
print(c.group_by(['URBANICITY','LGTCON_IM']).agg(W.sum()).with_columns((pl.col('WEIGHT')/pl.col('WEIGHT').sum().over('URBANICITY')*100).round(1)).pivot(on='URBANICITY', index='LGTCON_IM', values='WEIGHT').sort('LGTCON_IM'))
print('CRSS URBANICITY x INT_HWY / HARM_EV live animal (weighted %)')
print(c.group_by('URBANICITY').agg(((pl.col('INT_HWY')==1).cast(pl.Float64)*W).sum()/W.sum()*100, ((pl.col('HARM_EV')==11).cast(pl.Float64)*W).sum().alias('animal')/W.sum()*100, ((pl.col('RELJCT2')==2).cast(pl.Float64)*W).sum().alias('intersection')/W.sum()*100))
