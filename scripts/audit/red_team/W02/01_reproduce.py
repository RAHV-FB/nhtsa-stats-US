"""W02 claim: 39.4% of deaths in drunk-driving crashes, 37.4% speeding, 85.0% large-truck were not the
risk-vehicle driver. Independent reproduction from raw FARS interim tables (person, vehicle, miper,
midrvacc, veh_aux, acc_aux) WITHOUT deaths.py. Look at: shares vs outputs/tables/deaths/victim_roles.csv,
and whether MIDRVACC membership == 'any driver P_m>=8' in miper."""
import polars as pl
from nhtsa_stats.ingestion.cache import load_table
K=["YEAR","ST_CASE"]; IM=list(range(1,11))
per=load_table("FARS","person",None,["ST_CASE","VEH_NO","PER_NO","PER_TYP","INJ_SEV"])
pa=load_table("FARS","per_aux",None,["ST_CASE","VEH_NO","PER_NO","A_PTYPE"])
mi=load_table("FARS","miper",None,["ST_CASE","VEH_NO","PER_NO"]+[f"P{m}" for m in IM])
va=load_table("FARS","veh_aux",None,["ST_CASE","VEH_NO","A_SPVEH","A_BODY"])
ca=load_table("FARS","acc_aux",None,["ST_CASE","A_SPCRA","A_LT"])
md=load_table("FARS","midrvacc",None,["ST_CASE"]+[f"A{m}" for m in IM])
p=per.join(pa,on=K+["VEH_NO","PER_NO"],how="left").join(mi,on=K+["VEH_NO","PER_NO"],how="left")
# driver BAC by vehicle (own computation): PER_TYP==1
drv=p.filter(pl.col("PER_TYP")==1).select(K+["VEH_NO"]+[pl.col(f"P{m}").alias(f"d{m}") for m in IM])
# crash membership by own computation
cm=drv.group_by(K).agg([(pl.col(f"d{m}")>=8).any().alias(f"c{m}") for m in IM])
d=p.filter(pl.col("INJ_SEV")==4).join(va,on=K+["VEH_NO"],how="left").join(ca,on=K,how="left").join(drv,on=K+["VEH_NO"],how="left").join(cm,on=K,how="left").join(md,on=K,how="left")
print("deaths",d.height)
# membership consistency
for m in (1,5,10):
    own=d[f"c{m}"].fill_null(False); off=(d[f"A{m}"]>=8).fill_null(False)
    print(f"impl {m}: own-member deaths {int(own.sum())}, MIDRVACC-member {int(off.sum())}, disagree {int((own!=off).sum())}")
def roles(riskcol_expr, member_expr):
    r=riskcol_expr.fill_null(False); t=pl.col("A_PTYPE")
    return (member_expr, pl.when((t==1)&r).then(pl.lit("drv")).when((t==2)&r).then(pl.lit("pass")).when(t.is_in([1,2])).then(pl.lit("othveh")).when(t.is_in([3,4])).then(pl.lit("ped")).otherwise(pl.lit("oth")))
out=[]
for m in IM:
    mem=(pl.col(f"A{m}")>=8).fill_null(False); rk=pl.col(f"d{m}")>=8
    _,rl=roles(rk,mem)
    x=d.filter(mem).with_columns(rl.alias("role")).group_by("role").len()
    tot=x["len"].sum(); dr=x.filter(pl.col("role")=="drv")["len"].sum()
    out.append((tot,1-dr/tot))
print("ALC mean total",sum(o[0] for o in out)/10,"mean not-driver share",sum(o[1] for o in out)/10)
for name,mem,rk in [("SPEED",pl.col("A_SPCRA")==1,pl.col("A_SPVEH")==1),("TRUCK",pl.col("A_LT")==1,pl.col("A_BODY")==6)]:
    _,rl=roles(rk,mem)
    x=d.filter(mem).with_columns(rl.alias("role")).group_by("role").len().sort("role")
    tot=x["len"].sum(); print(name,"total",tot,dict(zip(x["role"],x["len"])),"not-driver share",1-x.filter(pl.col("role")=="drv")["len"].sum()/tot)
print("years per-year deaths /9 for alc:", sum(o[0] for o in out)/10/9)
