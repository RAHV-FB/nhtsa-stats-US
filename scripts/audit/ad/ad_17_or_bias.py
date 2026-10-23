"""FARS: killed-vs-survived odds ratios for alcohol under different measures (BAC, police report unk-as-no, complete-case, MI), all states and high-testing states."""
import polars as pl, math
OUT = "outputs/cache/audit/out_ad"
df = pl.read_parquet(f"{OUT}/fars_drivers.parquet").filter(pl.col("sev").is_in(["killed","survived"]))
P = [f"P{i}" for i in range(1,11)]
def OR(x, ycol):
    k = x.filter(pl.col("sev")=="killed")[ycol].mean(); s = x.filter(pl.col("sev")=="survived")[ycol].mean()
    return round((k/(1-k))/(s/(1-s)),2), round(100*k,1), round(100*s,1)
def mi_or(x):
    ors=[]
    for c in P:
        x2 = x.with_columns((pl.col(c)>=8).cast(pl.Float64).alias("y"))
        ors.append(math.log(OR(x2,"y")[0]))
    return round(math.exp(sum(ors)/len(ors)),2)
groups = {"all states": df, "8 high-testing states": df.filter(pl.col("STATE").is_in([2,5,22,29,30,31,33,46])), "MT+SD": df.filter(pl.col("STATE").is_in([30,46]))}
for g, x in groups.items():
    x = x.with_columns((pl.col("ALC_RES")>=80).cast(pl.Float64).alias("bac08"), (pl.col("DRINKING")==1).cast(pl.Float64).alias("pol1"))
    m = x.filter(pl.col("alc_stat")=="measured")
    print(f"== {g}: n={x.height}")
    print("  measured only, BAC>=.08: OR,pK,pS =", OR(m,"bac08"))
    print("  measured only, police DRINKING=1 (unk as no):", OR(m,"pol1"))
    print("  measured only, police complete-case:", OR(m.filter(pl.col("DRINKING").is_in([0,1])),"pol1"))
    print("  ALL drivers, police DRINKING=1 (unk as no):", OR(x,"pol1"))
    print("  ALL drivers, police complete-case:", OR(x.filter(pl.col("DRINKING").is_in([0,1])),"pol1"))
    print("  ALL drivers, DR_DRINK:", OR(x.with_columns(pl.col("DR_DRINK").cast(pl.Float64)),"DR_DRINK"))
    print("  ALL drivers, MI BAC>=.08 (geometric mean OR over 10 implicates):", mi_or(x))
