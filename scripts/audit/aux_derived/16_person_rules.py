"""Rule-based reconstruction of per_aux variables with per-year agreement rates."""
import sys; sys.path.insert(0, "scripts/audit/aux_derived")
from helpers import *
c = pl.col
src = sys.argv[1]
auxc = ["A_PERINJ", "A_PTYPE", "A_RESTUSE", "A_HELMUSE", "A_EJECT", "A_LOC"] + [f"A_AGE{i}" for i in range(1, 10)]
mainc = ["INJ_SEV", "PER_TYP", "REST_USE", "HELM_USE", "HELM_MIS", "REST_MIS", "EJECTION", "LOCATION", "AGE", "BODY_TYP"]
if src == "FARS":
    auxc += ["A_ALCTES", "A_DOA", "A_HISP"]; mainc += ["ALC_STATUS", "ALC_RES", "DOA", "HISPANIC"]
else:
    mainc += ["INJSEV_IM", "EJECT_IM", "AGE_IM"]
df = aux_main(src, "per", auxc, mainc)
MC = c("BODY_TYP").is_between(80, 89)
OCC = c("PER_TYP").is_in([1, 2, 9])
USED = [1, 2, 3, 4, 6, 8, 10, 11, 12, 97]
res = {}
def run(name, pred, actual):
    d = agree(df, pred, actual, name)
    return d
if src == "FARS":
    run("A_PERINJ", pl.when(c("INJ_SEV") == 4).then(1).otherwise(6), "A_PERINJ")
    run("A_DOA", pl.when(c("DOA") == 7).then(1).when(c("DOA") == 8).then(2).when(c("INJ_SEV") != 4).then(5).when(c("DOA") == 9).then(4).otherwise(3), "A_DOA")
    run("A_HISP", pl.when(c("HISPANIC") == 0).then(0).when(c("HISPANIC") == 7).then(1).when(c("HISPANIC").is_between(1, 6)).then(2).otherwise(3), "A_HISP")
    run("A_ALCTES", pl.when(c("ALC_RES").is_between(0, 9)).then(1).when(c("ALC_RES").is_between(10, 940) | (c("ALC_RES") == 998)).then(2)
        .when(c("ALC_RES") == 996).then(3).when(c("ALC_RES") == 997).then(4).otherwise(5), "A_ALCTES")
    run("A_EJECT", pl.when(c("EJECTION").is_in([0, 8])).then(1).when(c("EJECTION").is_in([1, 2, 3])).then(2).otherwise(3), "A_EJECT")
    run("A_LOC", pl.when(c("LOCATION") == 0).then(1).when(c("LOCATION").is_in([1, 2, 3, 9])).then(2).when(c("LOCATION").is_in([10, 11, 13])).then(3)
        .when(c("LOCATION").is_in([98, 99])).then(5).otherwise(4), "A_LOC")
    AGEV = "AGE"
else:
    run("A_PERINJ", c("INJSEV_IM").replace_strict({3: 2, 2: 3, 1: 4, 5: 4, 0: 5, 4: 7, 6: 7}, default=None), "A_PERINJ")
    run("A_EJECT", pl.when(c("EJECT_IM").is_in([0, 8])).then(1).when(c("EJECT_IM").is_in([1, 2, 3])).then(2).otherwise(3), "A_EJECT")
    run("A_LOC", pl.when(c("LOCATION") == 0).then(1).when(c("LOCATION").is_in([1, 2, 9])).then(2).when(c("LOCATION") == 11).then(3).otherwise(4), "A_LOC")
    AGEV = "AGE_IM"
run("A_PTYPE", c("PER_TYP").replace_strict({1: 1, 2: 2, 9: 2, 5: 3, 6: 4, 7: 4}, default=5), "A_PTYPE")
pre = pl.when(c("REST_USE").is_in(USED)).then(1).when(c("REST_USE").is_in([0, 5, 7, 16, 17, 19, 20])).then(2).otherwise(3)
MCR = c("BODY_TYP").is_between(80, 84) | c("BODY_TYP").is_between(87, 89)
post = pl.when(~OCC | MCR | c("REST_USE").is_in([96])).then(4).when(c("REST_USE").is_in(USED)).then(1).when(c("REST_USE") == 20).then(2).otherwise(3)
d = run("A_RESTUSE (pre-2020 rule <=2019; 2020+ rule: 4 if not PER_TYP 1/2/9 or BODY_TYP 80-84/87-89)", pl.when(c("YEAR") <= 2019).then(pre).otherwise(post), "A_RESTUSE")
mismatch(d, "A_RESTUSE", ["YEAR", "PER_TYP", "BODY_TYP", "REST_USE"], 12) if src else None
h16 = pl.when(c("REST_USE").is_in([5, 8, 16, 19, 97]) & (c("REST_MIS") == 1)).then(2).when(c("REST_USE").is_in([5, 8, 16, 19, 97])).then(1).when(c("REST_USE").is_in([29, 96, 98, 99])).then(3).otherwise(2)
h19 = pl.when(c("HELM_USE").is_in([5, 16, 19]) & (c("HELM_MIS") == 1)).then(2).when(c("HELM_USE").is_in([5, 16, 19])).then(1).when(c("HELM_USE").is_in([17, 20])).then(2).otherwise(3)
h20 = pl.when(~(MC & OCC)).then(4).when(c("HELM_USE").is_in([5, 16, 19]) & (c("HELM_MIS") == 1)).then(2).when(c("HELM_USE").is_in([5, 16, 19])).then(1).when(c("HELM_USE").is_in([98, 99])).then(3).otherwise(2)
d = run("A_HELMUSE (<=2018 REST_USE rule; 2019 HELM_USE rule; 2020+ MC-only rule)", pl.when(c("YEAR") <= 2018).then(h16).when(c("YEAR") == 2019).then(h19).otherwise(h20), "A_HELMUSE")
mismatch(d, "A_HELMUSE", ["YEAR", "BODY_TYP", "HELM_USE", "HELM_MIS", "REST_USE"], 15)
# Ages
A = c(AGEV)
unk = A >= 998
def cut(br, unknown_code):
    e = pl.when(unk).then(unknown_code if unknown_code else None)
    for i, hi in enumerate(br):
        e = e.when(A <= hi).then(i + 1)
    return e.otherwise(len(br) + 1)
specs = {1: [15, 24, 54], 2: [15, 20, 24, 34], 3: [3, 7, 12, 15, 20, 24, 34, 44, 54, 64, 74], 4: [15, 20, 24, 34, 44, 64],
         5: [15, 20, 24, 34, 44, 54, 64, 74], 6: [14, 20, 24, 34, 44, 54, 64, 74], 7: [4, 9, 15, 20, 24, 34, 44, 54, 64, 74],
         8: [19, 29, 39, 49, 59], 9: [15]}
for k, br in specs.items():
    run(f"A_AGE{k} from {AGEV} cut {br}", cut(br, len(br) + 2 if src == "FARS" else None), f"A_AGE{k}")
