import polars as pl
from nhtsa_stats.ingestion.cache import load_table
pl.Config.set_tbl_formatting("ASCII_MARKDOWN"); pl.Config.set_tbl_rows(300); pl.Config.set_tbl_hide_dataframe_shape(True); pl.Config.set_tbl_hide_column_data_types(True); pl.Config.set_tbl_cols(40); pl.Config.set_tbl_width_chars(250); pl.Config.set_fmt_str_lengths(40)
# CRSS: concentration of not-reported by PSU
c = load_table('CRSS','accident',columns=['CASENUM','PSU','PJ','RELJCT1','RELJCT2','TYP_INT','WEATHER','ALCOHOL'])
for v, codes in [('RELJCT1',[8]),('RELJCT2',[98]),('TYP_INT',[98]),('WEATHER',[98])]:
    g = c.group_by(['YEAR','PSU']).agg(pl.col(v).is_in(codes).mean().alias('r'), pl.len().alias('n'))
    s = g.group_by('YEAR').agg(pl.len().alias('nPSU'), (pl.col('r')>0.9).sum().alias('PSU_>90%'), (pl.col('r')<0.01).sum().alias('PSU_<1%'), ((pl.col('r')>=0.01)&(pl.col('r')<=0.9)).sum().alias('PSU_mid'),
        (pl.col('n')*pl.col('r')).sum().alias('n_unk'), (pl.col('n')*pl.col('r')).filter(pl.col('r')>0.9).sum().alias('n_unk_in_>90%PSU')).sort('YEAR')
    print(f'## CRSS {v} not-reported concentration by PSU'); print(s)
    # same at PJ level
    g2 = c.group_by(['YEAR','PJ']).agg(pl.col(v).is_in(codes).mean().alias('r'), pl.len().alias('n'))
    s2 = g2.group_by('YEAR').agg(pl.len().alias('nPJ'), (pl.col('r')==1).sum().alias('PJ_all'), (pl.col('r')==0).sum().alias('PJ_none'), (pl.col('n')*pl.col('r')).filter(pl.col('r')==1).sum().alias('n_unk_in_allPJ'), (pl.col('n')*pl.col('r')).sum().alias('n_unk')).sort('YEAR')
    print(f'## CRSS {v} by PJ'); print(s2)
# FARS by state
f = load_table('FARS','accident',columns=['ST_CASE','STATE','WEATHER','RD_OWNER','ROUTE','RUR_URB','FUNC_SYS'])
cb = pl.read_csv('/home/user/nhtsa-stats-US/outputs/audit/codebook.csv', infer_schema_length=0)
st = cb.filter((pl.col('source')=='FARS')&(pl.col('variable')=='STATE')&(pl.col('table')=='accident')).select(pl.col('code').cast(pl.Int64).alias('STATE'), pl.col('label').alias('st')).unique('STATE')
f = f.join(st, on='STATE', how='left')
for v, e in [('WEATHER', pl.col('WEATHER')==98), ('RD_OWNER', pl.col('RD_OWNER')==98), ('ROUTE', pl.when(pl.col('YEAR')<=2022).then(pl.col('ROUTE')==9).otherwise(pl.col('ROUTE')==99))]:
    g = f.with_columns(e.alias('u')).group_by(['YEAR','st']).agg((pl.col('u').mean()*100).round(1).alias('r'), pl.col('u').sum().alias('nu'))
    tot = g.group_by('YEAR').agg(pl.col('nu').sum().alias('tot'))
    top = g.join(tot, on='YEAR').with_columns((pl.col('nu')/pl.col('tot')*100).round(1).alias('share'))
    # states that are top contributors in any year
    keep = top.filter(pl.col('share')>=8)['st'].unique().to_list()
    print(f'## FARS {v} unknown: % within state by year, for states contributing >=8% of unknowns in some year')
    print(top.filter(pl.col('st').is_in(keep)).pivot(on='YEAR', index='st', values='r', sort_columns=True).sort('st'))
    print('n states with >50% unknown per year:', g.group_by('YEAR').agg((pl.col('r')>50).sum().alias('n_states_gt50'), (pl.col('r')==0).sum().alias('n_states_zero')).sort('YEAR'))
