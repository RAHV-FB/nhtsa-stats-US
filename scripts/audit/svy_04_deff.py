"""Design effects for key CRSS crash-level proportions under alternative variance specifications."""
import polars as pl, pandas as pd, numpy as np
from nhtsa_stats.ingestion.cache import load_table
from svy_lib import svy_ratio, design_summary
pd.set_option("display.width",250); pd.set_option("display.max_columns",40); pd.set_option("display.max_rows",400)
def P(d): print(d.to_pandas().to_string(index=False))
a = load_table("CRSS","accident",years=None,columns=["CASENUM","PSUSTRAT","PSU_VAR","PSU","PJ","STRATUM","WEIGHT","MAX_SEV","MAXSEV_IM","ALCHL_IM","URBANICITY","PERNOTMVIT"])
a = a.with_columns(pl.lit(1).alias("ONE_STR"), pl.col("CASENUM").alias("CASE_CL"))
one = pl.lit(1.0)
props = {
 "fatal_IM (MAXSEV_IM=4 / all)": ((pl.col("MAXSEV_IM")==4).cast(pl.Float64), one),
 "fatal_obs (MAX_SEV=4 / MAX_SEV 0-5)": ((pl.col("MAX_SEV")==4).cast(pl.Float64), pl.col("MAX_SEV").is_in([0,1,2,3,4,5]).cast(pl.Float64)),
 "KA_IM (MAXSEV_IM in 3,4)": (pl.col("MAXSEV_IM").is_in([3,4]).cast(pl.Float64), one),
 "inj_IM (MAXSEV_IM 1-5 / all)": (pl.col("MAXSEV_IM").is_in([1,2,3,4,5]).cast(pl.Float64), one),
 "inj_obs (MAX_SEV 1-5 / 0-5)": (pl.col("MAX_SEV").is_in([1,2,3,4,5]).cast(pl.Float64), pl.col("MAX_SEV").is_in([0,1,2,3,4,5]).cast(pl.Float64)),
 "alcohol_IM (ALCHL_IM=1)": ((pl.col("ALCHL_IM")==1).cast(pl.Float64), one),
 "nonmotorist (PERNOTMVIT>0)": ((pl.col("PERNOTMVIT")>0).cast(pl.Float64), one),
 "rural (URBANICITY=2)": ((pl.col("URBANICITY")==2).cast(pl.Float64), one),
}
specs = {"A: PSUSTRAT/PSU_VAR": ("PSUSTRAT","PSU_VAR"), "B: PSUSTRAT/PSU": ("PSUSTRAT","PSU"), "C: none/PSU_VAR": ("ONE_STR","PSU_VAR"),
         "D: PSUSTRAT/PJ": ("PSUSTRAT","PJ"), "E: STRATUM/case": ("STRATUM","CASE_CL"), "F: none/case (wt only)": ("ONE_STR","CASE_CL")}
rows=[]
for y in range(2016,2025):
    d = a.filter(pl.col("YEAR")==y)
    for nm,(num,den) in props.items():
        dd = d.filter(d.select(den.cast(pl.Boolean)).to_series()) if nm.startswith(("fatal_obs","inj_obs")) else d
        n = dd.height
        r = dict(YEAR=y, prop=nm, n=n)
        for sn,(s,c) in specs.items():
            p, se, nl = svy_ratio(d, num, den, strat=s, clus=c)
            r["p"]=p; r[sn]=se
        # unweighted SRS se using weighted p
        srs = np.sqrt(r["p"]*(1-r["p"])/n)
        r["se_srs"]=srs
        rows.append(r)
res = pl.DataFrame(rows)
out = res.with_columns((pl.col("p")*100).round(3).alias("p_%"), (pl.col("A: PSUSTRAT/PSU_VAR")*100).round(3).alias("se_A_%"),
    ((pl.col("A: PSUSTRAT/PSU_VAR")/pl.col("se_srs"))**2).round(2).alias("deff_A"),
    ((pl.col("B: PSUSTRAT/PSU")/pl.col("se_srs"))**2).round(2).alias("deff_B"),
    ((pl.col("C: none/PSU_VAR")/pl.col("se_srs"))**2).round(2).alias("deff_C"),
    ((pl.col("D: PSUSTRAT/PJ")/pl.col("se_srs"))**2).round(2).alias("deff_D"),
    ((pl.col("E: STRATUM/case")/pl.col("se_srs"))**2).round(2).alias("deff_E"),
    ((pl.col("F: none/case (wt only)")/pl.col("se_srs"))**2).round(2).alias("deff_F"))
P(out.select(["YEAR","prop","n","p_%","se_A_%","deff_A","deff_B","deff_C","deff_D","deff_E","deff_F"]).sort(["prop","YEAR"]))
res.write_csv("outputs/cache/audit/svy_04_deff.csv")
print("design summaries per year (A and B)")
for y in range(2016,2025):
    d = a.filter(pl.col("YEAR")==y)
    print(y, "A", design_summary(d,"PSUSTRAT","PSU_VAR"), "B", design_summary(d,"PSUSTRAT","PSU"), "D", design_summary(d, "PSUSTRAT","PJ"))
