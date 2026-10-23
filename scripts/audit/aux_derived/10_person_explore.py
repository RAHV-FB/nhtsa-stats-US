import sys; sys.path.insert(0, "scripts/audit/aux_derived")
from helpers import *
src = sys.argv[1]
auxc = ["A_PERINJ", "A_PTYPE", "A_RESTUSE", "A_HELMUSE", "A_EJECT", "A_LOC"] + [f"A_AGE{i}" for i in range(1, 10)]
if src == "FARS": auxc += ["A_ALCTES", "A_DOA", "A_HISP", "A_HRACE", "A_RCAT"]
mainc = ["INJ_SEV", "PER_TYP", "REST_USE", "HELM_USE", "EJECTION", "LOCATION", "AGE", "BODY_TYP"]
if src == "FARS": mainc += ["ALC_STATUS", "DOA", "HISPANIC", "ALC_RES"]
df = aux_main(src, "per", auxc, mainc)
for a, b in [("A_PERINJ", "INJ_SEV"), ("A_PTYPE", "PER_TYP"), ("A_RESTUSE", "REST_USE"), ("A_HELMUSE", "HELM_USE"),
             ("A_EJECT", "EJECTION"), ("A_LOC", "LOCATION")] + ([("A_ALCTES", "ALC_STATUS"), ("A_DOA", "DOA"), ("A_HISP", "HISPANIC")] if src == "FARS" else []):
    print(f"\n######## {src} {a} x {b}")
    print(wide(df, a, b, src, "person"))
