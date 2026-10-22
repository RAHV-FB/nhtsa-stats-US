import polars as pl
from nhtsa_stats.ingestion.cache import load_table
pl.Config.set_tbl_formatting("ASCII_MARKDOWN"); pl.Config.set_tbl_rows(200); pl.Config.set_tbl_hide_dataframe_shape(True); pl.Config.set_tbl_hide_column_data_types(True); pl.Config.set_tbl_cols(30)
for src, k in [('FARS','ST_CASE'), ('CRSS','CASENUM')]:
    acols = [k,'VE_TOTAL','VE_FORMS','PVH_INVL','PEDS','PERMVIT','PERNOTMVIT'] + (['PERSONS','FATALS'] if src=='FARS' else ['NUM_INJ','NO_INJ_IM','MAX_SEV','MAXSEV_IM'])
    a = load_table(src,'accident',columns=acols)
    print(f'## {src} count variables: min/max/nulls by year')
    #print(a.group_by('YEAR').agg([pl.col(c).max().alias(c+'_max') for c in acols[1:]]).sort('YEAR'))
    #print(a.group_by('YEAR').agg([pl.col(c).min().alias(c+'_min') for c in acols[1:]]).sort('YEAR'))
    v = load_table(src,'vehicle',columns=[k,'VEH_NO']).group_by(['YEAR',k]).len(name='n_veh')
    pw = load_table(src,'parkwork',columns=[k,'VEH_NO']).group_by(['YEAR',k]).len(name='n_pw')
    pcols = [k,'VEH_NO','PER_NO','PER_TYP','INJ_SEV']
    p = load_table(src,'person',columns=pcols)
    pa = p.group_by(['YEAR',k]).agg((pl.col('VEH_NO')>0).sum().alias('n_per_veh'), (pl.col('VEH_NO')==0).sum().alias('n_per_nm'),
        pl.col('PER_TYP').is_in([1,2,9]).sum().alias('n_occ_mvit'), (~pl.col('PER_TYP').is_in([1,2,9])).sum().alias('n_not_mvit'),
        pl.col('PER_TYP').is_in([4,5,6,7,8,10,19]).sum().alias('n_nonmot'), (pl.col('PER_TYP')==3).sum().alias('n_parked_occ'),
        (pl.col('INJ_SEV')==4).sum().alias('n_killed'), pl.col('INJ_SEV').is_in([1,2,3,4,5]).sum().alias('n_inj_any'), pl.col('INJ_SEV').is_in([1,2,3,5]).sum().alias('n_inj_nonfatal'),
        (pl.col('INJ_SEV')==9).sum().alias('n_injunk'), pl.len().alias('n_per'))
    j = a.join(v, on=['YEAR',k], how='left').join(pw, on=['YEAR',k], how='left').join(pa, on=['YEAR',k], how='left').fill_null(0)
    checks = {
      'VE_TOTAL==VE_FORMS+PVH_INVL': pl.col('VE_TOTAL')==pl.col('VE_FORMS')+pl.col('PVH_INVL'),
      'VE_FORMS==n_vehicle_rows': pl.col('VE_FORMS')==pl.col('n_veh'),
      'PVH_INVL==n_parkwork_rows': pl.col('PVH_INVL')==pl.col('n_pw'),
      'PERMVIT==persons PER_TYP 1/2/9': pl.col('PERMVIT')==pl.col('n_occ_mvit'),
      'PERMVIT==persons VEH_NO>0': pl.col('PERMVIT')==pl.col('n_per_veh'),
      'PERNOTMVIT==persons not PER_TYP1/2/9': pl.col('PERNOTMVIT')==pl.col('n_not_mvit'),
      'PERNOTMVIT==persons VEH_NO==0': pl.col('PERNOTMVIT')==pl.col('n_per_nm'),
      'PEDS==non-motorists excl parked occ': pl.col('PEDS')==pl.col('n_nonmot'),
      'PEDS==PERNOTMVIT': pl.col('PEDS')==pl.col('PERNOTMVIT'),
    }
    if src=='FARS':
        checks['PERSONS==PERMVIT'] = pl.col('PERSONS')==pl.col('PERMVIT')
        checks['FATALS==n_killed'] = pl.col('FATALS')==pl.col('n_killed')
    else:
        checks['NUM_INJ==n_inj_any(1-5) (excl 98/99)'] = pl.when(pl.col('NUM_INJ')<98).then(pl.col('NUM_INJ')==pl.col('n_inj_any')).otherwise(None)
        checks['NUM_INJ==n_inj_nonfatal(1,2,3,5)'] = pl.when(pl.col('NUM_INJ')<98).then(pl.col('NUM_INJ')==pl.col('n_inj_nonfatal')).otherwise(None)
        checks['NUM_INJ==99 iff all persons INJ_SEV=9'] = (pl.col('NUM_INJ')==99)==((pl.col('n_injunk')==pl.col('n_per'))&(pl.col('n_per')>0))
        checks['MAX_SEV==4 iff n_killed>0'] = (pl.col('MAX_SEV')==4)==(pl.col('n_killed')>0)
        checks['NO_INJ_IM==NUM_INJ when NUM_INJ<98'] = pl.when(pl.col('NUM_INJ')<98).then(pl.col('NO_INJ_IM')==pl.col('NUM_INJ')).otherwise(None)
    res = j.with_columns(pl.col('YEAR').cast(pl.String)).group_by('YEAR').agg([e.mean().round(5).alias(n) for n, e in checks.items()]).sort('YEAR')
    print(f'## {src} consistency (share of crashes satisfying)')
    print(res.transpose(include_header=True, header_name='check', column_names='YEAR'))
    if src=='FARS':
        print('FATALS dist', j.group_by('YEAR').agg((pl.col('FATALS')==1).mean().alias('f1'), (pl.col('FATALS')>=2).mean().alias('f2p'), pl.col('FATALS').sum().alias('sumF'), pl.col('n_killed').sum().alias('sum_killed')).sort('YEAR'))
        bad = j.filter(pl.col('FATALS')!=pl.col('n_killed')).select('YEAR',k,'FATALS','n_killed').head(10); print(bad)
    else:
        print(j.filter((pl.col('NUM_INJ')<98)&(pl.col('NUM_INJ')!=pl.col('n_inj_any'))).group_by('YEAR').len().sort('YEAR'))
        print(j.filter(pl.col('NUM_INJ')>=98).group_by(['YEAR','NUM_INJ','NO_INJ_IM']).len().sort(['YEAR','NUM_INJ']).head(40))
