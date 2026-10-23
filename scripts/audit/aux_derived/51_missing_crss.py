"""CRSS: visible-unknown and hidden-imputed rates behind aux variables, weighted, by year and severity."""
import sys; sys.path.insert(0, "scripts/audit/aux_derived")
from helpers import *
c = pl.col
K = ["YEAR", "CASENUM"]
out = []
def rate(df, name, cond, universe, sev="sev"):
    d = df.filter(universe).with_columns(cond.cast(pl.Float64).fill_null(0).alias("_c"))
    wr = lambda: (100 * (c("_c") * c("WEIGHT")).sum() / c("WEIGHT").sum()).round(2)
    y = d.group_by("YEAR").agg(wr().alias("r")).sort("YEAR")
    s = d.group_by(sev).agg(wr().alias("r"), pl.len().alias("n")).sort(sev)
    row = {"var": name, **{str(k): v for k, v in zip(y["YEAR"], y["r"])}, "n_univ": d.height}
    for k, v, n in s.iter_rows():
        row[f"{k}"] = v
    out.append(row)
    sy = d.group_by(["YEAR", sev]).agg(wr().alias("r")).sort(["YEAR", sev]).pivot(on="YEAR", index=sev, values="r", sort_columns=True)
    print(f"\n{name} (weighted %) by severity x year"); print(sy)
sevmap = {7: "1_K", 2: "2_A", 3: "3_B", 4: "4_C", 5: "5_O"}
p = aux_main("CRSS", "per", ["A_PERINJ", "A_RESTUSE", "A_HELMUSE", "A_EJECT", "WEIGHT"], ["INJ_SEV", "AGE", "EJECTION", "PER_TYP", "BODY_TYP", "SEX", "SEAT_POS"])
p = p.with_columns(c("A_PERINJ").replace_strict(sevmap, default="?").alias("sev"))
OCC = c("PER_TYP").is_in([1, 2, 9]); MCR = c("BODY_TYP").is_between(80, 84) | c("BODY_TYP").is_between(87, 89); MC = c("BODY_TYP").is_between(80, 89)
rate(p, "INJ_SEV=9 imputed into A_PERINJ | persons", c("INJ_SEV") == 9, pl.lit(True))
rate(p, "AGE 998/999 imputed into A_AGE* | persons", c("AGE") >= 998, pl.lit(True))
rate(p, "EJECTION 7/9 imputed into A_EJECT | occupants", c("EJECTION").is_in([7, 9]), c("PER_TYP").is_in([1, 2, 3, 9]))
rate(p, "A_RESTUSE=3 unknown | non-MC occupants", c("A_RESTUSE") == 3, OCC & ~MCR)
rate(p, "A_HELMUSE=3 unknown | MC occupants", c("A_HELMUSE") == 3, OCC & MC)
v = aux_main("CRSS", "veh", ["A_BODY", "A_IMP1", "A_MOD_YR", "WEIGHT"], ["IMPACT1", "MOD_YEAR", "BODY_TYP", "SPEEDREL", "HIT_RUN", "MAX_VSEV"])
acc = load_table("CRSS", "acc_aux", columns=["CASENUM", "A_CRAINJ"])
v = v.join(acc, on=K).with_columns(c("A_CRAINJ").replace_strict({4: "1_fatal", 2: "2_injury", 3: "3_PDO"}, default="?").alias("sev"))
rate(v, "IMPACT1 98/99 imputed into A_IMP1 | vehicles", c("IMPACT1").is_in([98, 99]), pl.lit(True))
rate(v, "MOD_YEAR 9998/9999 imputed into A_MOD_YR | vehicles", c("MOD_YEAR") >= 9998, pl.lit(True))
rate(v, "BODY_TYP unknown-type codes (9,19,29,39,48,49,59,78,79,89,98,99) | vehicles", c("BODY_TYP").is_in([9, 19, 29, 39, 48, 49, 59, 78, 79, 89, 98, 99]), pl.lit(True))
rate(v, "A_BODY=9 other/unknown | vehicles", c("A_BODY") == 9, pl.lit(True))
rate(v, "SPEEDREL 8/9 folded into A_SPVEH=2 | vehicles", c("SPEEDREL").is_in([8, 9]), pl.lit(True))
rate(v, "HIT_RUN=9 (raw) | vehicles", c("HIT_RUN") == 9, pl.lit(True))
a = aux_main("CRSS", "crash", ["A_CRAINJ", "A_INTER", "A_RELRD", "WEIGHT"], ["HOUR", "DAY_WEEK", "RELJCT2", "MAN_COLL", "WEATHER", "MAX_SEV", "INT_HWY", "REL_ROAD"])
a = a.with_columns(c("A_CRAINJ").replace_strict({4: "1_fatal", 2: "2_injury", 3: "3_PDO"}, default="?").alias("sev"))
rate(a, "MAX_SEV=9 imputed into A_CRAINJ | crashes", c("MAX_SEV") == 9, pl.lit(True))
rate(a, "HOUR=99 imputed into A_TOD/A_DOW | crashes", c("HOUR") == 99, pl.lit(True))
rate(a, "DAY_WEEK=9 imputed into A_DOW | crashes", c("DAY_WEEK") == 9, pl.lit(True))
rate(a, "RELJCT2 98/99 imputed into A_JUNC/A_INTSEC | crashes", c("RELJCT2").is_in([98, 99]), pl.lit(True))
rate(a, "MAN_COLL 98/99 imputed into A_MANCOL | crashes", c("MAN_COLL").is_in([98, 99]), pl.lit(True))
rate(a, "WEATHER 98/99 imputed into A_WEATHER (2020+) | crashes", c("WEATHER").is_in([98, 99]), c("YEAR") >= 2020)
rate(a, "A_INTER=3 (INT_HWY=9) | crashes", c("A_INTER") == 3, pl.lit(True))
rate(a, "A_RELRD=6 unknown | crashes", c("A_RELRD") == 6, pl.lit(True))
pl.Config.set_tbl_width_chars(400)
t = pl.DataFrame(out); print(t)
t.write_csv("outputs/cache/audit/out_aux/missing_crss.csv")
