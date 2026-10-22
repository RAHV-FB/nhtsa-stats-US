import sys; sys.path.insert(0,'.')
from util import *
for s,t,v in [('FARS','vsoe','SOE'),('FARS','vsoe','AOI'),('FARS','pbtype','PEDCTYPE'),('FARS','pbtype','BIKECTYPE'),('FARS','pbtype','PEDCGP'),('FARS','pbtype','BIKECGP'),('CRSS','pbtype','PEDCGP'),('FARS','pbtype','MOTMAN'),('FARS','pbtype','PEDPOS')]:
    ch=label_changes(s,t,v)
    print(s,t,v,'n label changes:',len(ch))
    for c in ch[:12]: print('   ',c)
lab=labels('FARS','vsoe','SOE')
yrs={c:(min(v),max(v)) for c,v in lab.items()}
print('SOE codes not present all years:',{c:y for c,y in yrs.items() if y!=(2016,2024)})
