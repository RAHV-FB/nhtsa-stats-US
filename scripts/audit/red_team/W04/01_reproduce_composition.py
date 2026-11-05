"""Reproduce 48.6% unbelted / 94,400 / 6,907 per yr from processed fars_person, then show the
composition of the 94,400 (seat, age, ejection, body) vs the DPC domain (driver/RF, 13+).
Also the unknown-belt group's profile vs known. Look at: reproduction line, domain share."""
import polars as pl
p=pl.read_parquet("data/processed/fars_person.parquet")
occ=p.filter(pl.col("ptype").is_in(["driver","passenger"]) & pl.col("body").is_in(["car","pickup","suv","van","light_truck_other"]) & (pl.col("killed")==1))
print("killed pv occ",occ.height)
print(occ["restraint"].value_counts())
kn=occ.filter(pl.col("restraint").is_in(["belted","none"]))
unb=kn.filter(pl.col("restraint")=="none")
print("known",kn.height,"unbelted",unb.height,"share",unb.height/kn.height)
print("lives/yr as recorded",unb.height*0.658495/9)
dom=(pl.col("seat").is_in(["front_left","front_other"])&(pl.col("age")>=13))
print("unbelted in domain driver/FR 13+ (note: FR passenger = front_other)",unb.filter(dom).height, unb.filter(dom).height/unb.height)
print(unb.group_by("seat").len().sort("len",descending=True).with_columns((pl.col("len")/unb.height).alias("sh")))
print(unb.group_by(pl.col("age")<13).len(), unb.filter(pl.col("age").is_null()).height)
print(unb.group_by("ejected").len())
print("ejected share among known by belt", kn.group_by(["restraint"]).agg(pl.col("ejected").mean().alias("ejmean"),pl.len()))
# unknown vs known profile
print(occ.group_by("restraint").agg(pl.col("ejected").mean().alias("ej"),pl.col("age").mean().alias("age"),(pl.col("seat")=="second_row").mean().alias("rear"),pl.col("night").mean().alias("night"),pl.len()))
print(occ.group_by("restraint").agg((pl.col("ALC_RES")>=80).mean().alias("bac80_raw")))
