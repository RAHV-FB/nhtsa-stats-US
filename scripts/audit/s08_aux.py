"""Verify meaning of aux A_* driver-behaviour variables by cross-tab against labelled source variables."""
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import polars as pl
from common import OUT, lt

pl.Config.set_tbl_rows(200)
pl.Config.set_tbl_cols(30)
pl.Config.set_tbl_width_chars(250)
pl.Config.set_tbl_hide_dataframe_shape(True)
pl.Config.set_tbl_hide_column_data_types(True)


def xt(df, a, b, by_year=False):
    g = ["YEAR"] if by_year else []
    return df.group_by(g + [a, b]).len().sort(g + [a, b])


def agree(df, a, b):
    return df.group_by("YEAR").agg(pl.len().alias("n"), (pl.col(a) == pl.col(b)).sum().alias("agree"),
                                   (pl.col(a) != pl.col(b)).sum().alias("disagree")).sort("YEAR")


for src in ["FARS", "CRSS"]:
    k = ["YEAR", "ST_CASE"] if src == "FARS" else ["YEAR", "CASENUM"]
    f = pl.read_parquet(f"{OUT}/frame_{src}.parquet")
    # raw distract codes for crash-level A_DIST variants
    dis = lt(src, "distract", k + ["VEH_NO", "MDRDSTRD", "DRDISTRACT"]).unique()
    dis = dis.with_columns(code=pl.coalesce("MDRDSTRD", "DRDISTRACT"))
    v = dis.group_by(k + ["VEH_NO"]).agg(
        d_all=pl.col("code").is_in([1, 3, 4, 5, 6, 7, 9, 10, 12, 13, 14, 15, 17, 18, 19, 92, 93, 97, 98]).any(),
        d_excl1=pl.col("code").is_in([3, 4, 5, 6, 7, 9, 10, 12, 13, 14, 15, 17, 18, 19, 92, 93, 97, 98]).any(),
        d_excl1_93=pl.col("code").is_in([3, 4, 5, 6, 7, 9, 10, 12, 13, 14, 15, 17, 18, 19, 92, 97, 98]).any(),
    )
    f = f.join(v, on=k + ["VEH_NO"], how="left")
    f = f.with_columns(spv=pl.when(pl.col("SPEEDREL").is_in([2, 3, 4, 5])).then(1).otherwise(2),
                       drow=pl.when(pl.col("imp_asleep")).then(1).otherwise(2))
    print(f"\n######## {src} A_SPVEH vs SPEEDREL")
    print(xt(f, "A_SPVEH", "SPEEDREL"))
    print(agree(f, "A_SPVEH", "spv"))
    c = f.group_by(k).agg(spc=pl.col("SPEEDREL").is_in([2, 3, 4, 5]).any(), A_SPCRA=pl.col("A_SPCRA").first(),
                          A_DIST=pl.col("A_DIST").first(),
                          dall=pl.col("d_all").any(), dex=pl.col("d_excl1").any(), dex93=pl.col("d_excl1_93").any(),
                          **({"A_DROWSY": pl.col("A_DROWSY").first(), "drow": pl.col("imp_asleep").any()} if src == "FARS" else {}))
    # crashes with no vehicles in vehicle table (e.g., none) are excluded naturally
    c = c.with_columns(spc=pl.when(pl.col("spc")).then(1).otherwise(2))
    print(f"--- {src} A_SPCRA vs any vehicle SPEEDREL in 2-5")
    print(agree(c, "A_SPCRA", "spc"))
    cc = c.filter(pl.col("A_DIST").is_not_null())
    for nm in ["dall", "dex", "dex93"]:
        cc = cc.with_columns(pl.when(pl.col(nm)).then(1).otherwise(2).alias(nm + "_c"))
        print(f"--- {src} A_DIST vs any driver distracted [{nm}] (all years with A_DIST)")
        print(agree(cc, "A_DIST", nm + "_c").select("YEAR", "n", "disagree"))
    if src == "FARS":
        c = c.with_columns(drow_c=pl.when(pl.col("drow")).then(1).otherwise(2))
        print("--- FARS A_DROWSY vs any DRIMPAIR=2")
        print(agree(c, "A_DROWSY", "drow_c"))
        f2 = f.with_columns(dex_c=pl.when(pl.col("d_excl1")).then(1).otherwise(2),
                            dall_c=pl.when(pl.col("d_all")).then(1).otherwise(2))
        print("--- FARS A_DRDIS vs distract (vehicle) variants: disagreements")
        print(agree(f2, "A_DRDIS", "dex_c").select("YEAR", "n", "disagree").join(
            agree(f2, "A_DRDIS", "dall_c").select("YEAR", pl.col("disagree").alias("disagree_incl_code1")), on="YEAR"))
        print("--- FARS A_DRDRO vs DRIMPAIR=2")
        print(agree(f, "A_DRDRO", "drow"))
        for a, b in [("A_LIC_S", "L_STATUS"), ("A_LIC_C", "L_COMPL"), ("A_CDL_S", "CDL_STAT"), ("A_MC_L_S", "L_COMPL")]:
            print(f"--- FARS {a} x {b} (pooled; and 2019 vs 2020)")
            print(xt(f, a, b).pivot(on=a, index=b, values="len", sort_columns=True).sort(b))
        # A_LIC_S may combine L_STATUS with L_COMPL / L_TYPE; check 2-way within A_LIC_S==4
        print("--- FARS A_LIC_S=4 / A_LIC_S=2 by L_STATUS x L_COMPL (top)")
        print(f.filter(pl.col("A_LIC_S").is_in([2, 4])).group_by("A_LIC_S", "L_STATUS", "L_COMPL").len().sort("len", descending=True).head(20))
        # A_MC_L_S vs body type (motorcycle body types 80-89) and L_COMPL, by period
        f = f.with_columns(mc=pl.col("BODY_TYP").is_between(80, 89))
        for per, cond in [("2016-19", pl.col("YEAR") <= 2019), ("2020-24", pl.col("YEAR") >= 2020)]:
            print(f"--- FARS A_MC_L_S x (motorcycle body 80-89) x L_COMPL, {per}")
            print(f.filter(cond).group_by("A_MC_L_S", "mc", "L_COMPL").len().sort("A_MC_L_S", "mc", "L_COMPL"))
            print(f"--- FARS A_MC_L_S x L_ENDORS? (mc only) {per}")
        print("--- FARS A_CDL_S by year x CDL_STAT")
        print(f.group_by("YEAR", "A_CDL_S", "CDL_STAT").len().filter(pl.col("YEAR").is_in([2019, 2020])).sort("YEAR", "A_CDL_S", "CDL_STAT"))
