"""FARS: unknown/missing rates of aux variables by year and by severity."""
import sys; sys.path.insert(0, "scripts/audit/aux_derived")
from helpers import *
c = pl.col
K = ["YEAR", "ST_CASE"]
out = []
def rate(df, name, cond, universe, sev):
    d = df.filter(universe)
    y = d.group_by("YEAR").agg((cond.mean() * 100).round(2).alias("r"), pl.len().alias("n")).sort("YEAR")
    s = d.group_by(sev).agg((cond.mean() * 100).round(2).alias("r"), pl.len().alias("n")).sort(sev)
    row = {"var": name, **{str(k): v for k, v in zip(y["YEAR"], y["r"])}, "n_univ": d.height}
    for k, v, n in s.iter_rows():
        row[f"sev={k}"] = v
    out.append(row)
    # severity by year
    sy = d.group_by(["YEAR", sev]).agg((cond.mean() * 100).round(2).alias("r")).sort(["YEAR", sev]).pivot(on="YEAR", index=sev, values="r", sort_columns=True)
    print(f"\n{name} by severity x year"); print(sy)
# person
p = aux_main("FARS", "per", ["A_PERINJ", "A_PTYPE", "A_RESTUSE", "A_HELMUSE", "A_EJECT", "A_LOC", "A_AGE9", "A_ALCTES", "A_HISP", "A_RCAT", "A_HRACE"], ["PER_TYP", "BODY_TYP", "INJ_SEV"])
p = p.with_columns(pl.when(c("A_PERINJ") == 1).then(pl.lit("killed")).otherwise(pl.lit("survived")).alias("sev"))
OCC = c("PER_TYP").is_in([1, 2, 9]); MCR = c("BODY_TYP").is_between(80, 84) | c("BODY_TYP").is_between(87, 89); MC = c("BODY_TYP").is_between(80, 89)
rate(p, "A_RESTUSE=3 unknown | non-MC MV-in-transport occupant", c("A_RESTUSE") == 3, OCC & ~MCR, "sev")
rate(p, "A_HELMUSE=3 unknown | MC occupant (BODY_TYP 80-89)", c("A_HELMUSE") == 3, OCC & MC, "sev")
rate(p, "A_EJECT=3 unknown | MV occupant (PER_TYP 1,2,3,9)", c("A_EJECT") == 3, c("PER_TYP").is_in([1, 2, 3, 9]), "sev")
rate(p, "A_LOC=5 unknown | non-occupant (A_LOC!=1)", c("A_LOC") == 5, c("A_LOC") != 1, "sev")
rate(p, "A_AGE9=3 age unknown | all persons", c("A_AGE9") == 3, pl.lit(True), "sev")
rate(p, "A_ALCTES=5 not reported/unknown | drivers", c("A_ALCTES") == 5, c("PER_TYP") == 1, "sev")
rate(p, "A_ALCTES=3 not tested | drivers", c("A_ALCTES") == 3, c("PER_TYP") == 1, "sev")
rate(p, "A_ALCTES in (3,4,5) no usable result | drivers", c("A_ALCTES").is_in([3, 4, 5]), c("PER_TYP") == 1, "sev")
rate(p, "A_HISP=3 unknown/redacted | fatalities", c("A_HISP") == 3, c("A_PERINJ") == 1, "sev")
rate(p, "A_RCAT=8 race unknown/redacted | fatalities", c("A_RCAT") == 8, c("A_PERINJ") == 1, "sev")
rate(p, "A_HRACE=9 | fatalities", c("A_HRACE") == 9, c("A_PERINJ") == 1, "sev")
rate(p, "INJ_SEV=9 (A_PERINJ=6 hides it) | all persons", c("INJ_SEV") == 9, pl.lit(True), "sev")
# vehicle
v = aux_main("FARS", "veh", ["A_IMP1", "A_MOD_YR", "A_LIC_S", "A_LIC_C", "A_CDL_S", "A_MC_L_S", "A_BODY", "A_TOWED", "A_SPVEH"], ["DEATHS", "SPEEDREL", "DR_PRES"])
v = v.with_columns(pl.when(c("DEATHS") > 0).then(pl.lit("occupant_killed")).otherwise(pl.lit("no_occ_death")).alias("sev"))
rate(v, "A_IMP1=7 unknown | vehicles", c("A_IMP1") == 7, pl.lit(True), "sev")
rate(v, "A_MOD_YR in (9998,9999) | vehicles", c("A_MOD_YR") >= 9998, pl.lit(True), "sev")
rate(v, "A_BODY=9 other/unknown | vehicles", c("A_BODY") == 9, pl.lit(True), "sev")
rate(v, "A_LIC_S=3 unknown/no driver | non-MC vehicles", c("A_LIC_S") == 3, c("A_LIC_S") != 4, "sev")
rate(v, "A_LIC_C=3 unknown | vehicles", c("A_LIC_C") == 3, pl.lit(True), "sev")
rate(v, "A_CDL_S=3 unknown | vehicles", c("A_CDL_S") == 3, pl.lit(True), "sev")
rate(v, "A_MC_L_S=3 | MC vehicles", c("A_MC_L_S") == 3, c("A_MC_L_S") != 4, "sev")
rate(v, "A_TOWED in (3,4) | vehicles 2021+", c("A_TOWED").is_in([3, 4]), c("YEAR") >= 2021, "sev")
rate(v, "SPEEDREL in (8,9) folded into A_SPVEH=2 | vehicles", c("SPEEDREL").is_in([8, 9]), pl.lit(True), "sev")
dis = load_table("FARS", "distract", columns=["ST_CASE", "VEH_NO", "MDRDSTRD", "DRDISTRACT"]).with_columns(pl.coalesce("DRDISTRACT", "MDRDSTRD").alias("DD"))
dg = dis.group_by(K + ["VEH_NO"]).agg(c("DD").is_in([96, 99]).any().alias("dunk"), (~c("DD").is_in([0, 1, 16, 96, 99])).any().alias("dyes"))
imp = load_table("FARS", "drimpair", columns=["ST_CASE", "VEH_NO", "DRIMPAIR"]).group_by(K + ["VEH_NO"]).agg(c("DRIMPAIR").is_in([98, 99]).any().alias("iunk"), (c("DRIMPAIR") == 2).any().alias("iyes"))
v = v.join(dg, on=K + ["VEH_NO"], how="left").join(imp, on=K + ["VEH_NO"], how="left")
rate(v, "distraction unknown (96/99, no positive code) folded into A_DRDIS=2 | vehicles", c("dunk").fill_null(False) & ~c("dyes").fill_null(False), pl.lit(True), "sev")
rate(v, "DRIMPAIR 98/99 (no 'asleep') folded into A_DRDRO=2 | vehicles", c("iunk").fill_null(False) & ~c("iyes").fill_null(False), pl.lit(True), "sev")
# crash
a = load_table("FARS", "acc_aux", columns=["ST_CASE", "FATALS", "A_TOD", "A_DOW", "A_INTER", "A_ROADFC", "A_RU", "A_JUNC", "A_RELRD", "A_MANCOL", "A_WEATHER", "A_POSBAC", "A_INTSEC"])
a = a.with_columns(pl.when(c("FATALS") >= 2).then(pl.lit("2+ deaths")).otherwise(pl.lit("1 death")).alias("sev"))
for nm, cond in [("A_TOD=3", c("A_TOD") == 3), ("A_DOW=3", c("A_DOW") == 3), ("A_INTER=3", c("A_INTER") == 3), ("A_ROADFC=7", c("A_ROADFC") == 7), ("A_RU=3", c("A_RU") == 3),
                 ("A_JUNC=4", c("A_JUNC") == 4), ("A_INTSEC=3", c("A_INTSEC") == 3), ("A_RELRD=6", c("A_RELRD") == 6), ("A_MANCOL=7", c("A_MANCOL") == 7), ("A_WEATHER=99", c("A_WEATHER") == 99), ("A_POSBAC=3", c("A_POSBAC") == 3)]:
    rate(a, nm + " | crashes", cond, pl.lit(True), "sev")
t = pl.DataFrame(out)
pl.Config.set_tbl_width_chars(400)
print(t)
t.write_csv("/tmp/nhtsa-audit/out_aux/missing_fars.csv")
