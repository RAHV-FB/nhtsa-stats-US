"""Rule-based reconstruction of veh_aux variables with per-year agreement."""
import sys; sys.path.insert(0, "scripts/audit")
from helpers import *
c = pl.col
src = sys.argv[1]
K = ["YEAR"] + ck(src) + ["VEH_NO"]
if src == "FARS":
    auxc = ["A_BODY", "A_IMP1", "A_MOD_YR", "A_SPVEH", "A_VROLL", "A_CDL_S", "A_LIC_C", "A_LIC_S", "A_MC_L_S", "A_FIRE_EXP", "A_SBUS", "A_TOWED", "A_DRDIS", "A_DRDRO", "A_VRD", "A_WRONGWAYDRV"]
    mainc = ["BODY_TYP", "VPICBODYCLASS", "IMPACT1", "MOD_YEAR", "SPEEDREL", "ROLLOVER", "CDL_STAT", "L_STATUS", "L_COMPL", "FIRE_EXP", "BUS_USE", "TOWED", "DR_SF1", "DR_SF2", "DR_SF3", "DR_SF4"]
else:
    auxc = ["A_BODY", "A_IMP1", "A_MOD_YR", "A_SPVEH", "A_VROLL"]
    mainc = ["IMPACT1_IM", "MDLYR_IM", "MOD_YEAR", "SPEEDREL", "ROLLOVER"]
df = aux_main(src, "veh", auxc, mainc)
IMPF = lambda e: (pl.when(e == 0).then(1).when(e.is_in([1, 11, 12])).then(2).when(e.is_in([2, 3, 4, 81, 82, 83])).then(3).when(e.is_in([5, 6, 7])).then(4)
                  .when(e.is_in([8, 9, 10, 61, 62, 63])).then(5).when(e.is_in([13, 14, 18, 19, 20])).then(6).otherwise(7))
if src == "FARS":
    agree(df, IMPF(c("IMPACT1")), "A_IMP1", "A_IMP1 FARS (0->1 noncoll;1,11,12->2 front;2-4,81-83->3 right;5-7->4 rear;8-10,61-63->5 left;13,14,18-20->6 other;98,99->7 unknown)")
    agree(df, c("MOD_YEAR"), "A_MOD_YR", "A_MOD_YR == MOD_YEAR (incl. 9998/9999)")
else:
    agree(df, IMPF(c("IMPACT1_IM")), "A_IMP1", "A_IMP1 CRSS from IMPACT1_IM (same map; no unknown)")
    agree(df, c("MDLYR_IM"), "A_MOD_YR", "A_MOD_YR == MDLYR_IM")
agree(df, pl.when(c("SPEEDREL").is_in([2, 3, 4, 5])).then(1).otherwise(2), "A_SPVEH", "A_SPVEH (SPEEDREL 2-5 ->1 else 2; 0/8/9 ->2)")
agree(df, pl.when(c("ROLLOVER").is_in([1, 2, 3, 9])).then(1).otherwise(2), "A_VROLL", "A_VROLL (ROLLOVER 1,2,3,9 ->1; 0,8 ->2)")
if src == "FARS":
    agree(df, pl.when(c("CDL_STAT").is_in([6, 7])).then(1).when(c("CDL_STAT").is_in([97, 99])).then(3).otherwise(2), "A_CDL_S", "A_CDL_S (6,7->1; 97,99->3; else 2)")
    MCV = c("A_BODY") == 7
    agree(df, pl.when(MCV).then(4).when(c("L_STATUS") == 6).then(1).when(c("L_STATUS").is_in([7, 9])).then(3).otherwise(2), "A_LIC_S", "A_LIC_S (A_BODY=7 ->4; L_STATUS 6->1; 7,9->3; 0-4->2)")
    agree(df, pl.when(c("L_COMPL").is_in([1, 3])).then(1).when(c("L_COMPL").is_in([0, 2])).then(2).otherwise(3), "A_LIC_C", "A_LIC_C (L_COMPL 1,3->1; 0,2->2; 6,8,9->3)")
    pre = pl.when(~MCV).then(4).when(c("L_COMPL").is_in([1, 3])).then(1).when(c("L_COMPL").is_in([0, 2, 6])).then(2).otherwise(3)
    post = pl.when(~MCV).then(4).when(c("L_COMPL").is_in([1, 3])).then(1).when(c("L_COMPL") == 0).then(2).otherwise(3)
    d = agree(df, pl.when(c("YEAR") <= 2019).then(pre).otherwise(post), "A_MC_L_S", "A_MC_L_S (non-MC->4; L_COMPL 1,3->1; <=2019: 0,2,6->2, 8,9->3; 2020+: 0->2, 2,6,8,9->3)")
    mismatch(d, "A_MC_L_S", ["YEAR", "L_COMPL", "L_STATUS"], 8)
    agree(df, pl.when(c("FIRE_EXP") == 1).then(2).otherwise(1), "A_FIRE_EXP", "A_FIRE_EXP (FIRE_EXP 1 ->2; 0 ->1)")
    SB = (c("BODY_TYP") == 50) | c("VPICBODYCLASS").is_in([71, 73])
    d = agree(df, pl.when(SB).then(1).when(c("BUS_USE") == 1).then(2).otherwise(3), "A_SBUS", "A_SBUS (BODY_TYP 50 or vPIC 71/73 ->1; else BUS_USE 1 ->2; else 3)")
    mismatch(d, "A_SBUS", ["YEAR", "BODY_TYP", "VPICBODYCLASS", "BUS_USE"], 8)
    d = agree(df.filter(c("YEAR") >= 2021), c("TOWED").replace_strict({2: 1, 3: 1, 6: 1, 7: 1, 5: 2, 8: 3, 9: 4}, default=None), "A_TOWED", "A_TOWED 2021+ (TOWED 2,3,6,7->1; 5->2; 8->3; 9->4)")
    # factor tables
    dis = load_table("FARS", "distract", columns=["ST_CASE", "VEH_NO", "MDRDSTRD", "DRDISTRACT"]).with_columns(pl.coalesce("DRDISTRACT", "MDRDSTRD").alias("DD"))
    for name, excl in [("excl 0,16,96,99", [0, 16, 96, 99]), ("excl 0,1,16,96,99", [0, 1, 16, 96, 99])]:
        dd = dis.group_by(K).agg((~c("DD").is_in(excl)).any().alias("dist"))
        x = df.join(dd, on=K, how="left")
        agree(x, pl.when(c("dist").fill_null(False)).then(1).otherwise(2), "A_DRDIS", f"A_DRDIS (any DRDISTRACT/MDRDSTRD not in {excl} ->1)")
    imp = load_table("FARS", "drimpair", columns=["ST_CASE", "VEH_NO", "DRIMPAIR"]).group_by(K).agg((c("DRIMPAIR") == 2).any().alias("drow"))
    x = df.join(imp, on=K, how="left")
    agree(x, pl.when(c("drow").fill_null(False)).then(1).otherwise(2), "A_DRDRO", "A_DRDRO (any DRIMPAIR==2 asleep/fatigued ->1)")
    sf = c("DR_SF1").is_in([50, 51]) | c("DR_SF2").is_in([50, 51]) | c("DR_SF3").is_in([50, 51]) | c("DR_SF4").is_in([50, 51])
    drf = load_table("FARS", "driverrf", columns=["ST_CASE", "VEH_NO", "DRIVERRF"]).group_by(K).agg(c("DRIVERRF").is_in([50, 51]).any().alias("ww"))
    x = df.join(drf, on=K, how="left").filter(c("YEAR") >= 2020)
    d = agree(x, pl.when(c("ww").fill_null(False)).then(1).otherwise(2), "A_WRONGWAYDRV", "A_WRONGWAYDRV 2020+ (any DRIVERRF 50/51 ->1)")
    mismatch(d, "A_WRONGWAYDRV", ["YEAR"], 6)
    vs = load_table("FARS", "vsoe", columns=["ST_CASE", "VEH_NO", "SOE"])
    for name, codes in [("63,64,71,79", [63, 64, 71, 79]), ("63,64,65,68,71,79", [63, 64, 65, 68, 71, 79]), ("63,64,65,71,79", [63, 64, 65, 71, 79]), ("63,64,68,71,79", [63, 64, 68, 71, 79])]:
        v = vs.group_by(K).agg(c("SOE").is_in(codes).any().alias("rd"))
        x = df.join(v, on=K, how="left")
        agree(x, pl.when(c("rd").fill_null(False)).then(1).otherwise(2), "A_VRD", f"A_VRD (any vsoe SOE in {name} ->1)")
