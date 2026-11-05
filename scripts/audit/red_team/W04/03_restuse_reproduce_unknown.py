"""Reproduce the published 194,279 known / 94,400 unbelted / 48.6% from interim person+per_aux
(A_RESTUSE, project filter: PER_TYP 1/2, body in car/pickup/suv/van/light-truck-other, killed),
using the processed frame for body/killed (rows joined by position after an alignment check against
A_PTYPE/A_EJECT). Then: (a) lives/yr under the project's own bounds for unknown belt use;
(b) ejection-based imputation of the unknown group's unbelted share; (c) belted-but-ejected deaths.
Look at: reproduction lines; 'lives/yr if unknown...' lines; imputed unbelted share of unknowns."""
import polars as pl
p=pl.read_parquet("data/processed/fars_person.parquet")
a=pl.concat([pl.read_parquet(f"data/interim/FARS/per_aux/{y}.parquet") for y in range(2016,2025)],how="diagonal")
print(p.height,a.height)
# alignment check: processed YEAR vs per_aux YEAR, ejected vs A_EJECT
chk=p.select("YEAR","ejected","ptype").with_columns(a["YEAR"].alias("aY"),a["A_EJECT"].alias("aE"),a["A_PTYPE"].alias("aP"))
print("year mismatch",chk.filter(pl.col("YEAR")!=pl.col("aY")).height)
print(chk.group_by("ptype","aP").len().sort("ptype","aP"))
p=p.with_columns(a["A_RESTUSE"].alias("A_RESTUSE"))
occ=p.filter(pl.col("ptype").is_in(["driver","passenger"]) & pl.col("body").is_in(["car","pickup","suv","van","light_truck_other"]) & (pl.col("killed")==1))
print("killed pv occ",occ.height)
print(occ["A_RESTUSE"].value_counts().sort("A_RESTUSE"))
k=occ.filter(pl.col("A_RESTUSE").is_in([1,2])); u=k.filter(pl.col("A_RESTUSE")==2)
print("known",k.height,"unbelted",u.height,"share",u.height/k.height,"lives/yr",u.height*0.658495/9)
unk=occ.filter(~pl.col("A_RESTUSE").is_in([1,2])); print("unknown n",unk.height)
# crosstab of A_RESTUSE vs REST_USE-based restraint in killed pv occupants
print(occ.group_by("A_RESTUSE","restraint").len().sort("A_RESTUSE","restraint"))
# (b) ejection-based imputation
ej=lambda d,v: d.filter(pl.col("A_RESTUSE")==v)["ejected"].mean()
eb,eu,ek=ej(occ,1),ej(occ,2),unk["ejected"].mean()
print("ejected share: belted",eb,"unbelted",eu,"unknown",ek)
fu=(ek-eb)/(eu-eb); print("implied unbelted share among unknown (ejection mixture)",fu)
nunk=unk.height
print("implied total unbelted",u.height+fu*nunk,"overall share incl unknown",(u.height+fu*nunk)/occ.height,"vs known-only",u.height/k.height)
for lab,extra in (("known only",0),("ejection-imputed unknown",fu*nunk),("all unknown unbelted (upper)",nunk)):
    N=u.height+extra
    print(f"lives/yr {lab}: N_unb={N:.0f} -> {N*0.658495/9:.0f}/yr")
# unknown share rising by year
print(occ.group_by("YEAR").agg((~pl.col("A_RESTUSE").is_in([1,2])).mean().alias("unk_share"),(pl.col("A_RESTUSE")==2).sum().alias("unb"),pl.col("A_RESTUSE").is_in([1,2]).sum().alias("known")).sort("YEAR").with_columns((pl.col("unb")/pl.col("known")).alias("unb_share")))
# (c) belted but completely ejected
print("belted(A) & ejected deaths",k.filter((pl.col("A_RESTUSE")==1)&(pl.col("ejected")==1)).height,"of belted",k.filter(pl.col("A_RESTUSE")==1).height)
# unbelted deaths by restraint/age <13, rear seat, to get domain mass
d=u.with_columns(((pl.col("seat").is_in(["front_left","front_other"]))&(pl.col("age")>=13)).alias("dom"))
print("unbelted in front seat 13+:",d["dom"].sum(),d["dom"].mean())
print(d.group_by("dom","seat").len().sort("dom","seat"))
print("unbelted age<13:",u.filter(pl.col("age")<13).height,"age null",u.filter(pl.col("age").is_null()).height)
