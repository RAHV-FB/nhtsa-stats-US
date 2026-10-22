import sys; sys.path.insert(0,'.')
from util import *
for var in ['V_CONFIG','CARGO_BT','HAZ_INV','HAZ_REL','TOW_VEH']:
    for ch in label_changes('FARS','vehicle',var): print(var,'label change',ch)
ve=load_table('FARS','vehicle',columns=['YEAR','BODY_TYP','V_CONFIG','CARGO_BT','HAZ_INV','HAZ_REL','GVWR','GVWR_FROM'])
trk=ve.filter(pl.col('BODY_TYP').is_between(60,79))
print('FARS trucks (BODY_TYP 60-79) per year:',trk.group_by('YEAR').len().sort('YEAR').rows())
show(trk,'V_CONFIG','FARS','vehicle')
show(trk,'CARGO_BT','FARS','vehicle')
print('HAZ_INV among trucks:'); show(trk,'HAZ_INV','FARS','vehicle')
print('V_CONFIG among non-trucks: share 0:',ve.filter(~pl.col('BODY_TYP').is_between(50,79)).select((pl.col('V_CONFIG')==0).mean()).item())
