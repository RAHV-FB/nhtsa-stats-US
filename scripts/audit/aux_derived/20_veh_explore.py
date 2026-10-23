import sys; sys.path.insert(0, "scripts/audit/aux_derived")
from helpers import *
src = sys.argv[1]
if src == "FARS":
    auxc = ["A_BODY", "A_IMP1", "A_MOD_YR", "A_SPVEH", "A_VROLL", "A_CDL_S", "A_LIC_C", "A_LIC_S", "A_MC_L_S", "A_FIRE_EXP", "A_SBUS", "A_TOWED"]
    mainc = ["BODY_TYP", "IMPACT1", "MOD_YEAR", "SPEEDREL", "ROLLOVER", "CDL_STAT", "L_STATUS", "L_COMPL", "L_TYPE", "L_ENDORS", "FIRE_EXP", "BUS_USE", "TOWED", "DR_PRES"]
    pairs = [("A_BODY", "BODY_TYP"), ("A_IMP1", "IMPACT1"), ("A_SPVEH", "SPEEDREL"), ("A_VROLL", "ROLLOVER"), ("A_CDL_S", "CDL_STAT"), ("A_LIC_S", "L_STATUS"),
             ("A_LIC_C", "L_COMPL"), ("A_MC_L_S", "L_TYPE"), ("A_MC_L_S", "L_ENDORS"), ("A_FIRE_EXP", "FIRE_EXP"), ("A_SBUS", "BUS_USE"), ("A_TOWED", "TOWED")]
else:
    auxc = ["A_BODY", "A_IMP1", "A_MOD_YR", "A_SPVEH", "A_VROLL"]
    mainc = ["BODY_TYP", "BDYTYP_IM", "IMPACT1", "IMPACT1_IM", "MOD_YEAR", "MDLYR_IM", "SPEEDREL", "ROLLOVER"]
    pairs = [("A_BODY", "BODY_TYP"), ("A_BODY", "BDYTYP_IM"), ("A_IMP1", "IMPACT1_IM"), ("A_SPVEH", "SPEEDREL"), ("A_VROLL", "ROLLOVER")]
df = aux_main(src, "veh", auxc, mainc)
for a, b in pairs:
    print(f"\n######## {src} {a} x {b}")
    print(wide(df, a, b, src, "vehicle"))
