"""W03: reproduce 66.3% (.15+), 23.7% invalid licence, 7.4% prior DWI among FARS drivers with MI BAC>=.08,
then attack: (A) measured vs imputed BAC, (B) unknown-code bounds on DWI, (C) age mix vs BAC-zero,
(D) state heterogeneity of record coding, (E) DWI among .15+ vs .08-.14, (F) licence-valid base.
Read the printed tables."""
import polars as pl
from nhtsa_stats.analysis import deaths as D

d = D.build_driver_frame()
per = D.load_table("FARS","person",None,["YEAR","ST_CASE","VEH_NO","PER_NO","PER_TYP","AGE","SEX","ALC_RES","ALC_STATUS","ALC_DET"]).filter(pl.col("PER_TYP")==1)
d = d.join(per.select("YEAR","ST_CASE","VEH_NO","PER_NO","AGE","SEX","ALC_RES","ALC_STATUS"), on=["YEAR","ST_CASE","VEH_NO","PER_NO"], how="left")
if "YEAR" not in d.columns: print("no YEAR")
P=[f"P{m}" for m in range(1,11)]
print("drivers",d.height)
d = d.with_columns(
  pl.mean_horizontal(*[(pl.col(c)>=8).cast(pl.Float64) for c in P]).alias("p08"),
  pl.mean_horizontal(*[(pl.col(c)>=15).cast(pl.Float64) for c in P]).alias("p15"),
  pl.mean_horizontal(*[(pl.col(c)==0).cast(pl.Float64) for c in P]).alias("p0"),
  (pl.col("ALC_RES").is_between(0,95)).alias("meas"),
  pl.col("PREV_DWI").is_between(0,97).alias("dwi_k"),
  (pl.col("PREV_DWI").is_between(1,97)).alias("dwi_y"),
  pl.col("L_STATUS").is_in([0,1,2,3,4,6]).alias("lic_k"),
  pl.col("L_STATUS").is_in([0,1,2,3,4]).alias("lic_y"),
)
print(d["PREV_DWI"].value_counts().sort("PREV_DWI"))
def wshare(df, w, num, den):
    return float((df[w]*df[num].cast(pl.Float64)*df[den].cast(pl.Float64)).sum()/(df[w]*df[den].cast(pl.Float64)).sum())
# weighted by P(.08+) (approx of per-implicate mean ratio-of-sums; exact below)
def exact(df, memb, num, den):
    r=[]
    for c in P:
        m=memb(pl.col(c))
        s=df.filter(m & den)
        r.append((s.filter(num).height/ s.height))
    return sum(r)/len(r)
dwik=pl.col("dwi_k"); dwiy=pl.col("dwi_y")
print("REPRO .15+ among .08+ :", sum(df.height for df in [0] ) if False else "")
r15=[];rl=[];rd=[]
for c in P:
    s=d.filter(pl.col(c)>=8)
    r15.append(s.filter(pl.col(c)>=15).height/s.height)
    k=s.filter(pl.col("lic_k")); rl.append(k.filter(pl.col("lic_y")).height/k.height)
    k=s.filter(pl.col("dwi_k")); rd.append(k.filter(pl.col("dwi_y")).height/k.height)
print("REPRO .15+ %.4f licinv %.4f dwi %.4f"%(sum(r15)/10,sum(rl)/10,sum(rd)/10))

# A. measured vs imputed
print("\nA. measured-test status among MI .08+ (implicate 1)")
s=d.filter(pl.col("P1")>=8)
print(s.group_by("meas").agg(pl.len().alias("n"),(pl.col("P1")>=15).mean().alias("sh15"),
   pl.col("dwi_y").filter(pl.col("dwi_k")).mean().alias("dwi"),
   pl.col("lic_y").filter(pl.col("lic_k")).mean().alias("licinv")))
print(s.group_by("ALC_STATUS").agg(pl.len().alias("n")).sort("ALC_STATUS"))
# measured-only with ALC_RES>=8 (observed)
m=d.filter(pl.col("meas") & (pl.col("ALC_RES")>=8))
print("measured BAC>=.08 n=%d  .15+ %.4f  dwi %.4f  licinv %.4f"%(m.height,(m["ALC_RES"]>=15).mean(),
   m.filter(pl.col("dwi_k"))["dwi_y"].mean(), m.filter(pl.col("lic_k"))["lic_y"].mean()))
print("measured pos in non-tested? MI>=.08 & not measured share:", s.filter(~pl.col("meas")).height/s.height)
# ratio-of-sums: .15+ among MI .08+ drivers whose MI draw varies
print("share of MI-.08+ whose P1..P10 not all identical:", s.filter(pl.struct(P).map_elements(lambda x: len(set(x.values()))>1, return_dtype=pl.Boolean)).height/s.height)

# B. bounds on DWI unknown
print("\nB. DWI bounds among P1>=.08")
n=s.height; k=s.filter(pl.col("dwi_k")).height; y=s.filter(pl.col("dwi_y")).height
print("n",n,"known",k,"yes",y,"lower(unk=no)",y/n,"known-share",y/k,"upper(unk=yes)",(y+n-k)/n)
print(s.group_by("YEAR").agg(pl.len().alias("n"),(1-pl.col("dwi_k").mean()).alias("unk_dwi"),pl.col("dwi_y").filter(pl.col("dwi_k")).mean().alias("dwi")).sort("YEAR"))

# C. age
print("\nC. age mix and age-standardised DWI")
bands=[(0,21),(21,25),(25,35),(35,45),(45,55),(55,65),(65,120)]
def band(df): 
    e=pl.lit("unk")
    for lo,hi in reversed(bands): e=pl.when((pl.col("AGE")>=lo)&(pl.col("AGE")<hi)).then(pl.lit(f"{lo}-{hi}")).otherwise(e)
    return df.with_columns(e.alias("ab"))
a=band(d.filter(pl.col("AGE")<120))
t08=a.filter(pl.col("P1")>=8).group_by("ab").agg(pl.len().alias("n08"),pl.col("dwi_y").filter(pl.col("dwi_k")).mean().alias("dwi08"))
t0=a.filter(pl.col("P1")==0).group_by("ab").agg(pl.len().alias("n0"),pl.col("dwi_y").filter(pl.col("dwi_k")).mean().alias("dwi0"),pl.col("lic_y").filter(pl.col("lic_k")).mean().alias("lic0"))
t=t08.join(t0,on="ab").sort("ab")
tl=a.filter(pl.col("P1")>=8).group_by("ab").agg(pl.col("lic_y").filter(pl.col("lic_k")).mean().alias("lic08"))
t=t.join(tl,on="ab").sort("ab"); print(t)
w=t["n08"]/t["n08"].sum()
print("BAC0 DWI std to .08+ age mix: %.4f (crude 0.0184); lic %.4f (crude 0.1155)"%(float((w*t["dwi0"]).sum()),float((w*t["lic0"]).sum())))
print("DWI among .08+ age 25+ :", a.filter((pl.col("P1")>=8)&(pl.col("AGE")>=25)).filter(pl.col("dwi_k"))["dwi_y"].mean())

# D. states
print("\nD. state variation prior DWI among P1>=.08 (n>=300)")
st=s.group_by("STATE").agg(pl.len().alias("n"),pl.col("dwi_y").filter(pl.col("dwi_k")).mean().alias("dwi"),(1-pl.col("dwi_k").mean()).alias("unk")).filter(pl.col("n")>=300).sort("dwi")
print(st.head(8)); print(st.tail(8))
# E,F
print("\nE. DWI by BAC band (P1) and licence")
for lab,expr in [("08-14",(pl.col("P1")>=8)&(pl.col("P1")<15)),(".15+",pl.col("P1")>=15),(".20+",pl.col("P1")>=20)]:
    x=d.filter(expr); print(lab,x.height, x.filter(pl.col("dwi_k"))["dwi_y"].mean())
v=s.filter(pl.col("L_STATUS")==6); print("valid-licence .08+ drivers: n",v.height,"dwi",v.filter(pl.col("dwi_k"))["dwi_y"].mean())
iv=s.filter(pl.col("lic_y")); print("invalid-licence .08+: n",iv.height,"dwi",iv.filter(pl.col("dwi_k"))["dwi_y"].mean())
# prior DWI OR prior suspension 2018+ (broader record)
x=s.filter(pl.col("YEAR")>=2018)
sus=pl.any_horizontal(*[pl.col(f"PREV_SUS{i}").is_between(1,97) for i in (1,2,3)])
print("2018+ .08+: DWI or any suspension:", x.select((pl.col("dwi_y")|sus).mean()).item(), " DWI only", x.filter(pl.col("dwi_k"))["dwi_y"].mean())
# any PREV_OTH
print("tested positive (meas>=.08) with licence invalid or DWI or sus:", x.select((pl.col("dwi_y")|sus|pl.col("lic_y")).mean()).item())
