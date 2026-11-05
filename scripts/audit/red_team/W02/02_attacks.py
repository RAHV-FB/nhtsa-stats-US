"""W02 attacks on 'not the drunk/speeding/truck driver' = victims. Own computation from raw FARS interim.
A1 strict-innocence: among non-driver deaths in drunk crashes, how many were passengers of the drunk vehicle,
   or themselves BAC>=.08 (MIPER) -> 'innocent' share. A2 same for speeding: victims who were in a vehicle whose
   driver was drunk (other behaviour). A3 speeding crashes (A_SPCRA=1) with no vehicle A_SPVEH=1 (all deaths forced
   to 'not risk driver'). A4 imputation: deaths in drunk crashes in all 10 implicates vs only some; not-driver share
   in each; A5 per-year shares; A6 single- vs multi-vehicle; A7 drivers lacking a MIPER row.
Outputs printed; writes per-year csv to work/W02."""
import polars as pl
from nhtsa_stats.ingestion.cache import load_table
K=["YEAR","ST_CASE"]; IM=list(range(1,11))
per=load_table("FARS","person",None,["ST_CASE","VEH_NO","PER_NO","PER_TYP","INJ_SEV"])
pa=load_table("FARS","per_aux",None,["ST_CASE","VEH_NO","PER_NO","A_PTYPE"])
mi=load_table("FARS","miper",None,["ST_CASE","VEH_NO","PER_NO"]+[f"P{m}" for m in IM])
va=load_table("FARS","veh_aux",None,["ST_CASE","VEH_NO","A_SPVEH","A_BODY"])
ca=load_table("FARS","acc_aux",None,["ST_CASE","A_SPCRA","A_LT"])
md=load_table("FARS","midrvacc",None,["ST_CASE"]+[f"A{m}" for m in IM])
acc=load_table("FARS","accident",None,["ST_CASE","VE_TOTAL"])
p=per.join(pa,on=K+["VEH_NO","PER_NO"],how="left").join(mi,on=K+["VEH_NO","PER_NO"],how="left")
print("A7 drivers (PER_TYP1) total",p.filter(pl.col("PER_TYP")==1).height,"without MIPER row (P1 null):",p.filter((pl.col("PER_TYP")==1)&pl.col("P1").is_null()).height)
drv=p.filter(pl.col("PER_TYP")==1).select(K+["VEH_NO"]+[pl.col(f"P{m}").alias(f"d{m}") for m in IM]).unique(K+["VEH_NO"])
# vehicle with drunk driver any implicate prob
d=(p.filter(pl.col("INJ_SEV")==4).join(va,on=K+["VEH_NO"],how="left").join(ca,on=K,how="left")
   .join(drv,on=K+["VEH_NO"],how="left").join(md,on=K,how="left").join(acc,on=K,how="left")
   .rename({f"P{m}":f"own{m}" for m in IM}))
# speeding-crash with no A_SPVEH vehicle
spv=va.group_by(K).agg((pl.col("A_SPVEH")==1).any().alias("anyspv"))
d=d.join(spv,on=K,how="left")
t=pl.col("A_PTYPE")
res=[]
for m in IM:
    mem=(pl.col(f"A{m}")>=8).fill_null(False); rk=(pl.col(f"d{m}")>=8).fill_null(False)
    own=(pl.col(f"own{m}")>=8).fill_null(False)
    x=d.filter(mem).with_columns(
        role=pl.when((t==1)&rk).then(pl.lit("drv")).when((t==2)&rk).then(pl.lit("pass")).when(t.is_in([1,2])).then(pl.lit("othveh")).when(t.is_in([3,4])).then(pl.lit("ped")).otherwise(pl.lit("oth")),
        ownd=own, yr=pl.col("YEAR"), multi=pl.col("VE_TOTAL")>1)
    tot=x.height
    nd=x.filter(pl.col("role")!="drv")
    res.append(dict(m=m,tot=tot,nd=nd.height,
      nd_pass=nd.filter(pl.col("role")=="pass").height,
      nd_ownd=nd.filter(pl.col("ownd")).height,
      nd_pass_ownd=nd.filter((pl.col("role")=="pass")&pl.col("ownd")).height,
      nd_ped_ownd=nd.filter((pl.col("role")=="ped")&pl.col("ownd")).height,
      nd_oth_ownd=nd.filter((pl.col("role")=="othveh")&pl.col("ownd")).height,
      single_tot=x.filter(~pl.col("multi")).height, single_nd=nd.filter(~pl.col("multi")).height,
      ))
r=pl.DataFrame(res).select(pl.all().mean())
print("A1 (means over implicates)\n",r.to_pandas().T.to_string())
r0=r.row(0,named=True)
print("share not-driver",r0["nd"]/r0["tot"])
print("share not-driver and not risk-passenger (third parties)",(r0["nd"]-r0["nd_pass"])/r0["tot"])
print("strict-innocent: not driver, not risk pass, own BAC<.08 :",(r0["nd"]-r0["nd_pass"]-r0["nd_ped_ownd"]-r0["nd_oth_ownd"])/r0["tot"])
print("strict-innocent v2: not driver, own BAC<.08 (passengers of drunk driver allowed if sober):",(r0["nd"]-r0["nd_ownd"])/r0["tot"])
print("single-vehicle crashes share of deaths",r0["single_tot"]/r0["tot"],"; their non-driver share",r0["single_nd"]/r0["single_tot"])
# A4: membership in how many implicates
cnt=d.with_columns(n=sum((pl.col(f"A{m}")>=8).fill_null(False).cast(pl.Int32) for m in IM))
print("A4 deaths by number of implicates (of 10) in which crash is drunk:",cnt.filter(pl.col("n")>0).group_by("n").len().sort("n").rows())
# role by certainty using implicate 1 roles, certain = n==10 / uncertain 0<n<10
m=1
rk=(pl.col(f"d{m}")>=8).fill_null(False)
x=cnt.filter(pl.col("n")==10).with_columns(drv=((t==1)&rk))
print("A4 always-drunk (n=10): deaths",x.height,"not-driver share (impl1)",1-x["drv"].mean())
# among crashes ever drunk, n<10: use each implicate where member
rows=[]
for m in IM:
    mem=(pl.col(f"A{m}")>=8).fill_null(False)
    rk=(pl.col(f"d{m}")>=8).fill_null(False)
    y=cnt.filter(mem&(pl.col("n")<10)).with_columns(drv=((t==1)&rk))
    rows.append((y.height,1-y["drv"].mean() if y.height else None))
print("A4 sometimes-drunk (n<10) mean deaths per implicate",sum(r[0] for r in rows)/10,"mean not-driver share",sum(r[1] for r in rows)/10)
# A5 per year
yr=[]
for m in IM:
    mem=(pl.col(f"A{m}")>=8).fill_null(False); rk=(pl.col(f"d{m}")>=8).fill_null(False)
    y=d.filter(mem).with_columns(drv=((t==1)&rk)).group_by("YEAR").agg(n=pl.len(),dr=pl.col("drv").sum()).with_columns(m=pl.lit(m))
    yr.append(y)
Y=pl.concat(yr).group_by("YEAR").agg(n=pl.col("n").mean(),dr=pl.col("dr").mean()).with_columns(nd_share=1-pl.col("dr")/pl.col("n")).sort("YEAR")
print("A5 alcohol by year\n",Y)
Y.write_csv("/tmp/claude-0/-home-user-nhtsa-stats-US/1c16118e-b425-5b4c-9882-66195720c5ff/scratchpad/red_team/work/W02/alc_by_year.csv")
for name,mem,rk in [("speed",pl.col("A_SPCRA")==1,pl.col("A_SPVEH")==1),("truck",pl.col("A_LT")==1,pl.col("A_BODY")==6)]:
    y=d.filter(mem).with_columns(drv=((t==1)&rk.fill_null(False))).group_by("YEAR").agg(n=pl.len(),dr=pl.col("drv").sum()).with_columns(nd=1-pl.col("dr")/pl.col("n")).sort("YEAR")
    print("A5",name,[ (a,round(b,3)) for a,b in zip(y["YEAR"],y["nd"])])
# A3
s=d.filter(pl.col("A_SPCRA")==1)
print("A3 speeding-crash deaths",s.height,"in crashes with no A_SPVEH==1 vehicle:",s.filter(~pl.col("anyspv").fill_null(False)).height)
# A2: speeding non-driver deaths: own-vehicle driver BAC>=.08 (impl 1..10 mean), or victim itself drunk
ss=s.filter(~((t==1)&(pl.col("A_SPVEH")==1)))
print("A2 speeding non-driver deaths",ss.height)
dr_m=[]; ow_m=[]; passerby=[]
for m in IM:
    dr_m.append(ss.filter((pl.col(f"d{m}")>=8)&(pl.col("A_SPVEH")!=1)).height)   # killed in a non-speeding vehicle whose driver was drunk
    ow_m.append(ss.filter(pl.col(f"own{m}")>=8).height)
    passerby.append(ss.filter((pl.col(f"d{m}")>=8)&(pl.col("A_SPVEH")!=1)|(pl.col(f"own{m}")>=8)).height)
print("A2 killed in non-speeding vehicle w/ drunk driver (mean):",sum(dr_m)/10,"victim own BAC>=.08 (mean):",sum(ow_m)/10,"either:",sum(passerby)/10)
print("A2 speeding crash deaths: drunk-driver-vehicle share (any):", sum(s.filter(pl.col(f'A{m}')>=8).height for m in IM)/10/s.height)
# A2b speeding non-driver victims: passengers of the speeding vehicle
print("A2 speeding: risk passengers",s.filter((t==2)&(pl.col("A_SPVEH")==1)).height,"of non-driver",ss.height)
