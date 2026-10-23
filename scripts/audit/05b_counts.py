import polars as pl
from nhtsa_stats.ingestion.cache import load_table
pl.Config.set_tbl_formatting("ASCII_MARKDOWN"); pl.Config.set_tbl_rows(60); pl.Config.set_tbl_hide_dataframe_shape(True); pl.Config.set_tbl_hide_column_data_types(True); pl.Config.set_tbl_cols(30)
for src, k in [('FARS','ST_CASE'), ('CRSS','CASENUM')]:
    a = load_table(src,'accident',columns=[k,'PEDS','PERMVIT','PERNOTMVIT'] + (['PERSONS'] if src=='FARS' else ['NUM_INJ','NO_INJ_IM']))
    p = load_table(src,'person',columns=[k,'VEH_NO','PER_TYP','INJ_SEV'] + (['INJSEV_IM'] if src=='CRSS' else []))
    pa = p.group_by(['YEAR',k]).agg([ (pl.col('PER_TYP')==t).sum().alias(f't{t}') for t in [1,2,3,4,5,6,7,8,9,10,19]] + [pl.len().alias('nper'), (pl.col('VEH_NO')==0).sum().alias('veh0')] + ([pl.col('INJSEV_IM').is_in([1,2,3,4,5]).sum().alias('n_inj_im')] if src=='CRSS' else []))
    j = a.join(pa, on=['YEAR',k], how='left').fill_null(0)
    nm = pl.col('t4')+pl.col('t5')+pl.col('t6')+pl.col('t7')+pl.col('t8')+pl.col('t10')+pl.col('t19')
    bad = j.filter(pl.col('PEDS')!=nm)
    print(src, 'PEDS mismatches by year'); print(bad.group_by('YEAR').len().sort('YEAR'))
    print(bad.select('YEAR','PEDS','PERNOTMVIT','t3','t4','t5','t6','t7','t8','t10','t19').head(12))
    print(src,'PEDS==t5 pedestrians only?', j.group_by('YEAR').agg((pl.col('PEDS')==pl.col('t5')).mean(), (pl.col('PEDS')==nm-pl.col('t19')).mean().alias('excl19'), (pl.col('PEDS')==nm+pl.col('t3')).mean().alias('incl3')).sort('YEAR'))
    if src=='FARS':
        print('PERSONS checks', j.group_by('YEAR').agg((pl.col('PERSONS')==pl.col('PERMVIT')).mean().alias('eqPERMVIT'),(pl.col('PERSONS')==pl.col('nper')).mean().alias('eq_all'),(pl.col('PERSONS')==pl.col('PERMVIT')+pl.col('t3')).mean().alias('eq_mvit+parked'),(pl.col('PERSONS')==pl.col('nper')-pl.col('veh0')).mean().alias('eq_vehno>0')).sort('YEAR'))
        print(j.filter(pl.col('PERSONS')!=pl.col('PERMVIT')).select('YEAR','PERSONS','PERMVIT','PERNOTMVIT','t3','veh0','nper').head(8))
    else:
        print('NO_INJ_IM == count INJSEV_IM in 1-5', j.group_by('YEAR').agg((pl.col('NO_INJ_IM')==pl.col('n_inj_im')).mean()).sort('YEAR'))
