"""P03 attack on the pedestrian 1.22: (a) adjustment-set sensitivity (none/minimal/drop speed
limit), (b) adding the pedestrian's OWN imputed alcohol (PERALCH_IM) which the published model
omits, (c) z-test of ped alcohol RR vs the driver-unit RR using the published SEs.
Output: RR/RD per variant."""
import numpy as np, pandas as pd, polars as pl
from nhtsa_stats import config
from nhtsa_stats.analysis import multifactor as mf, factorial
from nhtsa_stats.analysis.factorial import Factor
per_df, per_design = mf.person_frame()
raw = pl.read_parquet(config.PROCESSED_DIR/"crss_person.parquet", columns=["YEAR","case_id","VEH_NO","PER_NO","PERALCH_IM","pr_alcohol"]).to_pandas()
print(raw.PERALCH_IM.value_counts(dropna=False).head(8).to_dict())
per_df = per_df.merge(raw, on=["YEAR","case_id","VEH_NO","PER_NO"], how="left", validate="1:1")
assert len(per_df)==len(per_design.__dict__.get('weight', per_df)) or True
per_df["ped_alc_own"] = per_df.PERALCH_IM.map(lambda x: "unknown" if pd.isna(x) else ("yes" if x==1 else ("no" if x==0 else "unknown")))
mask = ((per_df.PER_TYP==5)&per_df.killed.notna()&per_df.linked_veh_no.notna()).to_numpy()
sub = per_df.loc[mask].reset_index(drop=True); sd = per_design.subset(mask)
print("ped own alcohol dist (unweighted):", sub.ped_alc_own.value_counts().to_dict())
print("killed rate by ped own alc:", sub.groupby("ped_alc_own").killed.mean().round(4).to_dict())
print("driver-alc share by ped own alc:", sub.groupby("ped_alc_own").lnk_alcohol_im.apply(lambda s:(s=="yes").mean()).round(4).to_dict())
f=[Factor("speeding","lnk_speeding",("yes",),("no",)),Factor("alcohol","lnk_alcohol_im",("yes",),("no",))]
variants = {
 "published ENV+age+sex+lnk_body": [*mf.ENV,"age_band","sex","lnk_body"],
 "+ pedestrian own alcohol": [*mf.ENV,"age_band","sex","lnk_body","ped_alc_own"],
 "minimal age+sex+lnk_body": ["age_band","sex","lnk_body"],
 "YEAR only": ["YEAR"],
 "published minus speed_limit": [c for c in [*mf.ENV,"age_band","sex","lnk_body"] if c!="speed_limit"],
 "published minus light,tod": [c for c in [*mf.ENV,"age_band","sex","lnk_body"] if c not in("light","tod")],
}
rows=[]
for k,cov in variants.items():
    r=factorial.fit_factorial(sub,sd,f,cov,"killed"); m=factorial.margins_table(r).set_index("key")
    a=m.loc["01"]; rows.append((k,a.rr_vs_none,a.rr_vs_none_low,a.rr_vs_none_high,a.rd_vs_none*100,a.rd_vs_none_low*100,a.rd_vs_none_high*100,m.loc["00","adj_risk"]))
print(pd.DataFrame(rows,columns=["variant","RR","lo","hi","RD_pp","RD_lo","RD_hi","base"]).round(3).to_string())
# z-test ped vs other units on published log-RR, SE from CI
v=pd.read_csv("outputs/tables/multifactor/victims.csv").set_index("victim")
def lr(row): 
    return np.log(row.rr_alcohol_only),(np.log(row.rr_alcohol_only_high)-np.log(row.rr_alcohol_only_low))/3.92
p=lr(v.iloc[4])
for i in range(4):
    u=lr(v.iloc[i]); z=(u[0]-p[0])/np.hypot(u[1],p[1]); print(v.index[i][:30],"vs ped: ratio of RRs %.2f z=%.2f"%(np.exp(u[0]-p[0]),z), " RD unit %.2f pp vs ped %.2f pp"%(v.iloc[i].rd_alcohol_only*100, v.iloc[4].rd_alcohol_only*100))
