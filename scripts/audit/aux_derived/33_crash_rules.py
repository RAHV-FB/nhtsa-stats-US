"""Rule-based reconstruction of acc_aux variables (agreement per year)."""
import sys; sys.path.insert(0, "scripts/audit/aux_derived")
from helpers import *
c = pl.col
src = sys.argv[1]
CK = ck(src); K = ["YEAR"] + CK
if src == "FARS":
    auxc = ["A_CRAINJ", "A_CT", "A_D15_19", "A_D15_20", "A_D16_19", "A_D16_20", "A_D16_24", "A_D21_24", "A_D65PLS", "A_DIST", "A_DOW", "A_DROWSY", "A_HR", "A_INTER", "A_INTSEC", "A_JUNC", "A_LT", "A_MANCOL",
            "A_MC", "A_PED", "A_PEDAL", "A_PEDAL_F", "A_PED_F", "A_POLPUR", "A_POSBAC", "A_RD", "A_REGION", "A_RELRD", "A_ROADFC", "A_ROLL", "A_RU", "A_SBUSCR", "A_SPCRA", "A_TOD", "A_WEATHER", "A_WRONGWAY",
            "BIA", "SPJ_INDIAN", "INDIAN_RES", "TRACT", "CENSUS_2020_TRACT_FIPS"]
    mainc = ["DAY_WEEK", "HOUR", "FUNC_SYS", "RUR_URB", "RELJCT2", "REL_ROAD", "MAN_COLL", "WEATHER", "STATE", "VE_FORMS", "SP_JUR", "CF1", "CF2", "CF3"]
    DW, HR, AGE, MC_, REL2, WX = "DAY_WEEK", "HOUR", "AGE", "MAN_COLL", "RELJCT2", "WEATHER"
else:
    auxc = ["A_CRAINJ", "A_CT", "A_D15_19", "A_D15_20", "A_D16_19", "A_D16_20", "A_D16_24", "A_D21_24", "A_D65PLS", "A_DIST", "A_DOW", "A_HR", "A_INTER", "A_INTSEC", "A_JUNC", "A_LT", "A_MANCOL",
            "A_MC", "A_PED", "A_PEDAL", "A_RELRD", "A_ROLL", "A_SPCRA", "A_TOD", "A_WEATHER"]
    mainc = ["WKDY_IM", "HOUR_IM", "INT_HWY", "RELJCT2_IM", "REL_ROAD", "MANCOL_IM", "WEATHR_IM", "VE_FORMS", "MAXSEV_IM"]
    DW, HR, AGE, MC_, REL2, WX = "WKDY_IM", "HOUR_IM", "AGE_IM", "MANCOL_IM", "RELJCT2_IM", "WEATHR_IM"
df = aux_main(src, "crash", auxc, mainc)
# person aggregates
pc = ["PER_TYP", "INJ_SEV", AGE] + (["ALC_RES"] if src == "FARS" else [])
p = load_table(src, "person", columns=CK + pc)
drv = p.filter(c("PER_TYP") == 1)
A = c(AGE)
pa = drv.group_by(K).agg(*[(A.is_between(lo, hi)).any().alias(f"d{lo}_{hi}") for lo, hi in [(15, 19), (15, 20), (16, 19), (16, 20), (16, 24), (21, 24), (65, 997)]])
pp = p.group_by(K).agg((c("PER_TYP") == 5).any().alias("ped"), c("PER_TYP").is_in([6, 7]).any().alias("pedal"),
                       ((c("PER_TYP") == 5) & (c("INJ_SEV") == 4)).any().alias("ped_f"), (c("PER_TYP").is_in([6, 7]) & (c("INJ_SEV") == 4)).any().alias("pedal_f"))
df = df.join(pa, on=K, how="left").join(pp, on=K, how="left")
# vehicle aggregates (veh_aux verified 100%/99.6% at vehicle level)
vcols = ["A_BODY", "A_SPVEH", "A_VROLL"] + (["A_VRD", "A_DRDIS", "A_DRDRO", "A_SBUS", "A_WRONGWAYDRV"] if src == "FARS" else [])
va = aux_main(src, "veh", vcols, ["HIT_RUN", "BODY_TYP"] + (["HITRUN_IM", "BDYTYP_IM"] if src == "CRSS" else []))
hr = c("HITRUN_IM") if src == "CRSS" else c("HIT_RUN")
vg = va.group_by(K).agg((c("A_BODY") == 6).any().alias("lt"), (c("A_BODY") == 7).any().alias("mc"), (c("A_SPVEH") == 1).any().alias("sp"),
                        (c("A_VROLL") == 1).any().alias("roll"), (c("HIT_RUN") == 1).any().alias("hr_raw"), (hr == 1).any().alias("hr_im") if src == "CRSS" else (c("HIT_RUN") == 1).any().alias("hr_im"),
                        *([(c("A_VRD") == 1).any().alias("rd"), (c("A_DRDIS") == 1).any().alias("dis"), (c("A_DRDRO") == 1).any().alias("drow"), c("A_SBUS").is_in([1, 2]).any().alias("sbus"),
                           (c("A_WRONGWAYDRV") == 1).any().alias("ww")] if src == "FARS" else []))
df = df.join(vg, on=K, how="left")
yn = lambda e: pl.when(e.fill_null(False)).then(1).otherwise(2)
res = []
def run(name, pred, actual, sub=None):
    d = df if sub is None else df.filter(sub)
    dd = agree(d, pred, actual, name)
    return dd
for lo, hi, v in [(15, 19, "A_D15_19"), (15, 20, "A_D15_20"), (16, 19, "A_D16_19"), (16, 20, "A_D16_20"), (16, 24, "A_D16_24"), (21, 24, "A_D21_24"), (65, 997, "A_D65PLS")]:
    run(f"{v}: any driver (PER_TYP=1) with {AGE} in [{lo},{hi}]", yn(c(f"d{lo}_{hi}")), v)
run("A_PED: any PER_TYP=5", yn(c("ped")), "A_PED")
run("A_PEDAL: any PER_TYP 6/7", yn(c("pedal")), "A_PEDAL")
run("A_LT: any vehicle A_BODY=6", yn(c("lt")), "A_LT")
run("A_MC: any vehicle A_BODY=7", yn(c("mc")), "A_MC")
run("A_SPCRA: any vehicle A_SPVEH=1 (SPEEDREL 2-5)", yn(c("sp")), "A_SPCRA")
run("A_ROLL: any vehicle A_VROLL=1", yn(c("roll")), "A_ROLL")
run(f"A_HR: any vehicle {'HITRUN_IM' if src=='CRSS' else 'HIT_RUN'}=1 (HIT_RUN in 2020+ for CRSS)", yn(pl.when(c("YEAR") <= 2019).then(c("hr_im")).otherwise(c("hr_raw"))), "A_HR")
run("A_CT: VE_FORMS 1/2/3+", pl.when(c("VE_FORMS") == 1).then(1).when(c("VE_FORMS") == 2).then(2).otherwise(3), "A_CT")
tod = pl.when(c(HR) == 99).then(3).when(c(HR).is_between(6, 17)).then(1).otherwise(2)
run(f"A_TOD: {HR} 6-17->1, 0-5/18-23->2, 99->3", tod, "A_TOD")
wkend = (c(DW).is_in([1, 7])) | ((c(DW) == 6) & (c(HR).is_between(18, 23))) | ((c(DW) == 2) & (c(HR).is_between(0, 5)))
dow = pl.when(c(DW).is_in([2, 6]) & (c(HR) == 99)).then(3).when(c(DW) == 9).then(3).when(wkend).then(2).otherwise(1)
run(f"A_DOW: weekend = Fri 18:00-Mon 05:59 from {DW},{HR}; Mon/Fri with hour 99 -> 3", dow, "A_DOW")
mc = c(MC_)
run(f"A_MANCOL from {MC_}", pl.when(mc == 0).then(1).when(mc == 1).then(2).when(mc == 2).then(3).when(mc == 6).then(4).when(mc.is_in([7, 8])).then(5).when(mc.is_in([9, 10, 11])).then(6).otherwise(7), "A_MANCOL")
r2 = c(REL2)
run(f"A_JUNC from {REL2}", pl.when(r2.is_in([2, 3])).then(1).when(r2 == 1).then(2).when(r2.is_in([98, 99])).then(4).otherwise(3), "A_JUNC")
run(f"A_INTSEC from {REL2}", pl.when(r2.is_in([2, 3])).then(1).when(r2.is_in([98, 99])).then(3).otherwise(2), "A_INTSEC")
rr = c("REL_ROAD")
relrd = (pl.when(rr.is_in([1, 11]) | ((rr == 7) & (c("YEAR") >= 2020))).then(1).when(rr == 2).then(2).when(rr == 3).then(3).when(rr.is_in([98, 99])).then(6)
         .when((rr == 12) & (c("YEAR") <= 2019) & pl.lit(src == "CRSS")).then(6).otherwise(4))
d = run("A_RELRD from REL_ROAD (7: <=2019->4, 2020+->1; CRSS 12: <=2019->6)", relrd, "A_RELRD")
mismatch(d, "A_RELRD", ["YEAR", "REL_ROAD"], 6)
wmap = {1: 1, 2: 2, 3: 3, 4: 4, 5: 6, 6: 10, 7: 11, 8: 12, 10: 13, 11: 14, 12: 15, 98: 99, 99: 99}
run(f"A_WEATHER from {WX} (1-4 same; 5->6; 6->10; 7->11; 8->12; 10->13; 11->14; 12->15; 98/99->99)", c(WX).replace_strict(wmap, default=None), "A_WEATHER", sub=c("A_WEATHER").is_not_null())
if src == "FARS":
    run("A_CRAINJ == 1 (all FARS crashes)", pl.lit(1), "A_CRAINJ")
    run("A_INTER: FUNC_SYS 1->1, 2-7->2, 96/98/99->3", pl.when(c("FUNC_SYS") == 1).then(1).when(c("FUNC_SYS").is_between(2, 7)).then(2).otherwise(3), "A_INTER")
    run("A_ROADFC: FUNC_SYS 1..4 same, 5/6->5, 7->6, 96/98/99->7", c("FUNC_SYS").replace_strict({1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 5, 7: 6}, default=7), "A_ROADFC")
    run("A_RU: RUR_URB 1->1, 2->2, 6/8/9->3", c("RUR_URB").replace_strict({1: 1, 2: 2}, default=3), "A_RU")
    run("A_PED_F: any pedestrian with INJ_SEV=4", yn(c("ped_f")), "A_PED_F")
    run("A_PEDAL_F: any PER_TYP 6/7 with INJ_SEV=4", yn(c("pedal_f")), "A_PEDAL_F")
    run("A_RD: any vehicle A_VRD=1", yn(c("rd")), "A_RD")
    run("A_DIST: any vehicle A_DRDIS=1", yn(c("dis")), "A_DIST")
    run("A_DROWSY: any vehicle A_DRDRO=1", yn(c("drow")), "A_DROWSY")
    run("A_WRONGWAY: any vehicle A_WRONGWAYDRV=1 (2020+)", yn(c("ww")), "A_WRONGWAY", sub=c("YEAR") >= 2020)
    run("A_SBUSCR: any vehicle A_SBUS in (1,2) (2021+)", yn(c("sbus")), "A_SBUSCR", sub=c("YEAR") >= 2021)
    crf = load_table("FARS", "crashrf", years=[2020, 2021, 2022, 2023, 2024], columns=["ST_CASE", "CRASHRF"]).group_by(K).agg((c("CRASHRF") == 20).any().alias("pp"))
    df = df.join(crf, on=K, how="left")
    pol = pl.when(c("YEAR") <= 2019).then(c("CF1").is_in([20]) | c("CF2").is_in([20]) | c("CF3").is_in([20])).otherwise(c("pp").fill_null(False))
    run("A_POLPUR: CF1-3 = 20 (<=2019) / CRASHRF = 20 (2020+)", yn(pol), "A_POLPUR")
    dr = p.filter(c("PER_TYP") == 1).group_by(K).agg((c("ALC_RES").is_between(1, 940) | (c("ALC_RES") == 998)).any().alias("pos"), (c("ALC_RES") == 0).all().alias("allzero"))
    df = df.join(dr, on=K, how="left")
    d = run("A_POSBAC: any driver ALC_RES 1-940/998 ->1; all drivers ALC_RES=0 or no driver ->2; else 3", pl.when(c("pos").fill_null(False)).then(1).when(c("allzero").fill_null(True)).then(2).otherwise(3), "A_POSBAC")
    mismatch(d, "A_POSBAC", ["YEAR"], 5)
    reg = {1: [9, 23, 25, 33, 44, 50], 2: [34, 36, 42], 3: [10, 11, 21, 24, 37, 51, 54], 4: [1, 12, 13, 45, 47], 5: [17, 18, 26, 27, 39, 55], 6: [22, 28, 35, 40, 48], 7: [5, 19, 20, 29, 31], 8: [8, 32, 38, 46, 49, 56], 9: [4, 6, 15], 10: [2, 16, 30, 41, 53]}
    smap = {s: r for r, ss in reg.items() for s in ss}
    run("A_REGION from STATE (CT=9 -> region 2 for <=2020, region 1 for 2021+)", pl.when((c("STATE") == 9) & (c("YEAR") <= 2020)).then(2).otherwise(c("STATE").replace_strict(smap, default=None)), "A_REGION")
    run("SPJ_INDIAN: SP_JUR == 3", pl.when(c("SP_JUR") == 3).then(1).otherwise(0), "SPJ_INDIAN")
    run("INDIAN_RES: BIA==1 or SP_JUR==3", pl.when((c("BIA") == 1) | (c("SP_JUR") == 3)).then(1).otherwise(0), "INDIAN_RES")
    run("TRACT: CENSUS_2020_TRACT_FIPS non-null", pl.when(c("CENSUS_2020_TRACT_FIPS").is_not_null()).then(1).otherwise(0), "TRACT", sub=c("YEAR") >= 2020)
else:
    run("A_CRAINJ: MAXSEV_IM 4->4; 1,2,3,5->2; 0,6,8->3", c("MAXSEV_IM").replace_strict({4: 4, 1: 2, 2: 2, 3: 2, 5: 2, 0: 3, 6: 3, 8: 3}, default=None), "A_CRAINJ")
    run("A_INTER: INT_HWY 1->1, 0->2, 9->3", c("INT_HWY").replace_strict({1: 1, 0: 2, 9: 3}, default=None), "A_INTER")
    dis = load_table("CRSS", "distract", years=[2020, 2021, 2022, 2023, 2024], columns=["CASENUM", "DRDISTRACT"]).group_by(K).agg((~c("DRDISTRACT").is_in([0, 16, 96, 99])).any().alias("dis"))
    df = df.join(dis, on=K, how="left")
    run("A_DIST (2020+): any DRDISTRACT not in {0,16,96,99}", yn(c("dis")), "A_DIST", sub=c("YEAR") >= 2020)
