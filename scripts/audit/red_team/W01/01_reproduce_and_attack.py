"""W01: reproduce 59.6% union / four shares / 1.51 ratio from raw interim tables via the project's
own death-frame builder (definitions), then run attacks:
 A unknown-belt handling (proportional allocation), B denominator/applicability, C composition of the
 union by who died (victim-level vs crash-level), D per-implicate union & no-midrvacc-row crashes,
 E year stability, F A_RESTUSE code detail. Look at printed blocks."""
import numpy as np, polars as pl
from nhtsa_stats.analysis import deaths as D
d = D.build_death_frame()
print("rows", d.height, "years", sorted(d["YEAR"].unique().to_list()))
N = d.height
K = D.IMPLICATES
al = np.column_stack([d[f"alc_{m}"].to_numpy() for m in K])  # n x 10
spd = d["spd"].to_numpy(); unb = d["unbelted"].to_numpy(); unh = d["unhelmeted"].to_numpy()
pv = d["pv"].to_numpy(); mc = d["mc"].to_numpy()
unk = d["restraint_unknown"].to_numpy(); hunk = d["helmet_unknown"].to_numpy()
uni = (al | spd[:,None] | unb[:,None] | unh[:,None])
print("A. union per implicate", [round(uni[:,i].mean(),4) for i in range(10)], "mean", uni.mean())
print("alc share", al.mean(), "spd", spd.mean(), "unb", unb.mean(), "unh", unh.mean())
tot = al.mean()+spd.mean()+unb.mean()+unh.mean(); print("sum", tot, "ratio", tot/uni.mean())
# A. unknown belt: allocate unknown PV occupants to unbelted at rate among known (and helmets)
known_pv = (pv & ~unk).sum(); rate = unb.sum()/known_pv
kmc = (mc & ~hunk).sum(); rmc = unh.sum()/kmc
print("A. unknown pv", unk.sum(), "rate unbelted among known", rate, "unk mc", hunk.sum(), "rate", rmc)
# expected union with unknowns allocated: P(in union | unknown, no other factor) -> prob unbelted
base_other = (al | spd[:,None]).mean(1)  # per-death fraction of implicates with alc or spd
extra = (unk * (1-base_other)).sum()*rate + (hunk*(1-base_other)).sum()*rmc
print("A. extra deaths in union if unknowns behave like knowns", extra, "-> union", (uni.mean(1).sum()+extra)/N)
# bounds: all unknown unbelted
ub = (unk*(1-base_other)).sum()
print("A. upper bound union (all unknown unbelted)", (uni.mean(1).sum()+ub+(hunk*(1-base_other)).sum())/N)
# B. denominators
print("B. unbelted/pv", unb.sum()/pv.sum(), "unbelted/known pv", rate, "unhelm/mc", unh.sum()/mc.sum(), "unhelm/known mc", rmc)
ptype = d["ptype"].to_numpy(); body = d["body"].to_numpy()
cats = {"pv_occ":pv,"mc":mc,"ped":ptype==3,"cyc":ptype==4,"other_nonocc":ptype==5,
        "lt_occ":(np.isin(ptype,[1,2]))&(body==6),"bus/other_occ":(np.isin(ptype,[1,2]))&np.isin(body,[8,9])}
print("B. union share by victim type (share of that type's deaths | share of all deaths)")
for k,m in cats.items():
    print(f"  {k:14s} n={m.sum():7d} ({m.mean():.3f}) union={uni[m].mean():.3f} alc={al[m].mean():.3f} spd={spd[m].mean():.3f}")
# victim-level vs crash-level
# victims whose own behaviour (unbelted/unhelmeted) vs crash-level only
own = unb|unh
print("C. share of union deaths via victim's own protective-device failure only(any):", (own & uni.mean(1).round().astype(bool)).sum()/uni.mean(1).sum())
crash_only = (~own)
print("C. union deaths with no victim-level factor (crash-level only):", (uni.mean(1)*crash_only).sum(), (uni.mean(1)*crash_only).sum()/uni.mean(1).sum())
for k,m in cats.items():
    print(f"  crash-level-only union among {k}: {(uni.mean(1)*crash_only)[m].sum():.0f}")
# the stricter "victim's own vehicle at fault" version using risk flags
ra = np.column_stack([d[f"risk_alc_{m}"].to_numpy() for m in K]); rs = d["risk_spd"].to_numpy()
strict = (ra | rs[:,None] | unb[:,None] | unh[:,None])
print("C. strict (risk vehicle driver BAC>=.08 / risk veh speeding / own belt/helmet) union", strict.mean(), "alc", ra.mean(), "spd", rs.mean())
# D. crashes without midrvacc row
raw = d["A1"].is_null().to_numpy()
print("D. deaths in crashes with no midrvacc record", raw.sum(), raw.mean(), "union among them (excluding alc)", (spd|unb|unh)[raw].mean())
# alc defined only where test? midrvacc A values distribution
print("D. A1 value counts", d["A1"].value_counts().sort("A1").to_pandas().to_dict("records"))
# E. by year
yr = d["YEAR"].to_numpy()
print("E. year: union, alc, spd, unb, unh, restraint_unknown")
for y in sorted(set(yr)):
    m = yr==y
    print(y, round(uni[m].mean(),3), round(al[m].mean(),3), round(spd[m].mean(),3), round(unb[m].mean(),3), round(unh[m].mean(),3), round(unk[m].mean(),3))
# F. A_RESTUSE codes among PV occupants
print(d.filter(pl.col("pv")).group_by("A_RESTUSE").len().sort("A_RESTUSE"))
print(d.filter(pl.col("mc")).group_by("A_HELMUSE").len().sort("A_HELMUSE"))
print("F. A_BODY==9/other & A_PTYPE occupants:", d.filter(pl.col("ptype").is_in([1,2])).group_by("body").len().sort("body"))
# write npz for later
np.savez("/tmp/claude-0/-home-user-nhtsa-stats-US/1c16118e-b425-5b4c-9882-66195720c5ff/scratchpad/red_team/work/W01/flags.npz", al=al,spd=spd,unb=unb,unh=unh,pv=pv,mc=mc,unk=unk,hunk=hunk,ptype=ptype,body=body,yr=yr)
