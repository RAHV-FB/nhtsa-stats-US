"""Measured-only comparison (ALC_RES<=940): prior DWI / invalid licence by measured BAC band; 'record of any kind' reading
(DWI or invalid licence or, 2018+, suspension); speeding groups; state-level lower tail excluded."""
import polars as pl
from nhtsa_stats.analysis import deaths as D
d=D.build_driver_frame()
per=D.load_table("FARS","person",None,["YEAR","ST_CASE","VEH_NO","PER_NO","ALC_RES"])
d=d.join(per,on=["YEAR","ST_CASE","VEH_NO","PER_NO"],how="left").with_columns(
 pl.col("L_STATUS").is_in([0,1,2,3,4,6]).alias("lk"),pl.col("L_STATUS").is_in([0,1,2,3,4]).alias("ly"),
 pl.col("PREV_DWI").is_between(0,97).alias("dk"),pl.col("PREV_DWI").is_between(1,97).alias("dy"),
 pl.col("PREV_SPD").is_between(0,97).alias("sk"),pl.col("PREV_SPD").is_between(1,97).alias("sy"))
m=d.filter(pl.col("ALC_RES")<=940)
def row(lab,x): print("%-22s n=%6d dwi=%.4f inv=%.4f"%(lab,x.height,x.filter(pl.col("dk"))["dy"].mean(),x.filter(pl.col("lk"))["ly"].mean()))
row("measured 0",m.filter(pl.col("ALC_RES")==0))
row("measured .01-.07",m.filter(pl.col("ALC_RES").is_between(10,79)))
row("measured .08-.14",m.filter(pl.col("ALC_RES").is_between(80,149)))
row("measured .15+",m.filter(pl.col("ALC_RES")>=150))
row("measured .20+",m.filter(pl.col("ALC_RES")>=200))
row("measured .08+",m.filter(pl.col("ALC_RES")>=80))
# whole-sample 'any record' for MI .08+ implicate 1, 2018+
s=d.filter((pl.col("P1")>=8)&(pl.col("YEAR")>=2018))
sus=pl.any_horizontal(*[pl.col(f"PREV_SUS{i}").is_between(1,97) for i in (1,2,3)])
print("2018+ MI.08+: any of DWI/invalid licence/suspension:",s.select((pl.col("dy")|pl.col("ly")|sus).mean()).item())
print("2018+ MI.08+: DWI or invalid licence:",s.select((pl.col("dy")|pl.col("ly")).mean()).item())
# prior speeding among measured .08+ and speeders
sp=d.filter(pl.col("spveh")==1); ns=d.filter((pl.col("spveh")==2)&(pl.col("P1")==0))
for lab,x in [("speeding",sp),("neither",ns)]:
    print(lab,x.height,"inv %.4f spd %.4f"%(x.filter(pl.col("lk"))["ly"].mean(),x.filter(pl.col("sk"))["sy"].mean()))
# speeding with measured BAC 0 only vs neither
sp0=d.filter((pl.col("spveh")==1)&(pl.col("P1")==0)); print("speeding & BAC0:",sp0.height,"inv %.4f spd %.4f"%(sp0.filter(pl.col("lk"))["ly"].mean(),sp0.filter(pl.col("sk"))["sy"].mean()))
print("speeding share also .08+ (P1):",sp.select((pl.col("P1")>=8).mean()).item())
