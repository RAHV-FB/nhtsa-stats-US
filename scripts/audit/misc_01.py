import sys; sys.path.insert(0,'.')
from util import *
K=['YEAR','ST_CASE','VEH_NO']
ve=load_table('FARS','vehicle',columns=K+['TOW_VEH','TRLR1VIN'])
tr=load_table('FARS','vpictrailerdecode',columns=K+['TRAILER_NO','TRAILERTYPECONNECTION','TRAILERBODYTYPE'])
pw=load_table('FARS','parkwork',columns=K)
t=tr.select(K).unique()
print('trailer-decode vehicles in vehicle:',t.join(ve,on=K,how='semi').height,' in parkwork:',t.join(pw,on=K,how='semi').height,' total:',t.height)
tv=ve.filter(pl.col('TOW_VEH').is_in([1,2,3,4])).join(t.with_columns(pl.lit(1).alias('h')),on=K,how='left')
print('vehicles towing (TOW_VEH 1-4) with a trailer decode row:',tv.group_by('YEAR').agg(pl.col('h').is_not_null().mean().round(3),pl.len()).sort('YEAR').rows())
print('TRAILERBODYTYPE null share:',tr['TRAILERBODYTYPE'].null_count()/tr.height)
