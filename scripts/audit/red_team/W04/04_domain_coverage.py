"""How much of the 94.4k unbelted deaths lie where the DPC can measure effectiveness?
(a) share of unbelted deaths (A_RESTUSE==2) in single-occupant vehicles (no within-vehicle comparator);
(b) unknown-belt share among survivors vs deaths (differential ascertainment; DPC drops unknown pairs);
(c) stratified lives using stratum-specific DPC effectiveness (body type; ejection) from 02 output
    (hard-coded from 02_dpc_transport.csv), vs the single 65.8%.
Look at: (a) share single-occupant; (b) unknown shares; (c) stratified totals vs 6,908/yr."""
import polars as pl
p=pl.read_parquet("data/processed/fars_person.parquet")
a=pl.concat([pl.read_parquet(f"data/interim/FARS/per_aux/{y}.parquet") for y in range(2016,2025)],how="diagonal")
p=p.with_columns(a["A_RESTUSE"].alias("A"))
occ=p.filter(pl.col("ptype").is_in(["driver","passenger"]))
occ=occ.with_columns(pl.len().over(["YEAR","case_id","VEH_NO"]).alias("n_occ"))
lpv=occ.filter(pl.col("body").is_in(["car","pickup","suv","van","light_truck_other"]))
k=lpv.filter(pl.col("killed")==1); u=k.filter(pl.col("A")==2)
print("unbelted deaths",u.height)
print(u.group_by(pl.col("n_occ").clip(1,3)).len().sort("n_occ").with_columns((pl.col("len")/u.height).alias("share")))
print("belted deaths by n_occ",k.filter(pl.col("A")==1).group_by(pl.col("n_occ").clip(1,3)).len().sort("n_occ"))
# (b) unknown restraint share, adults front seats, by outcome
fr=lpv.filter(pl.col("seat").is_in(["front_left","front_other"])&(pl.col("age")>=13)&pl.col("killed").is_not_null())
print(fr.group_by("killed").agg(pl.len(),(pl.col("restraint")=="unknown").mean().alias("unk_REST_USE"),(pl.col("A")==3).mean().alias("unk_A")))
# survivors only: unbelted share among known
s=fr.filter((pl.col("killed")==0)&pl.col("restraint").is_in(["belted","none"]))
print("survivor unbelted share (known, front 13+)",(s["restraint"]=="none").mean(), s.height)
# (c) stratified lives
E_body={"car":0.6028,"suv":0.7228,"pickup":0.7391,"van":0.5892,"light_truck_other":0.6585}
uu=u.group_by("body").len()
tot=sum(r["len"]*E_body[r["body"]] for r in uu.iter_rows(named=True)); print("body-stratified lives/yr",tot/9, uu)
ee=u.group_by("ejected").len(); print(ee)
E_ej={0:0.5464,1:0.7947}
tot2=sum(r["len"]*E_ej.get(r["ejected"],0.6585) for r in ee.iter_rows(named=True)); print("ejection-stratified lives/yr",tot2/9)
print("single 65.85%: ",u.height*0.658495/9)
