"""CRSS *_IM person variables vs their source variable: agreement where the source is known,
what the unknown codes are imputed to, per year.  Also MAX_SEV=9 composition check.
"""
import polars as pl

from nhtsa_stats.ingestion.cache import load_table

pl.Config.set_tbl_rows(60)
pl.Config.set_tbl_cols(30)
pl.Config.set_tbl_width_chars(250)
p = load_table("CRSS", "person", columns=["CASENUM", "VEH_NO", "PER_TYP", "AGE", "AGE_IM", "SEX", "SEX_IM", "SEAT_POS", "SEAT_IM",
                                          "EJECTION", "EJECT_IM", "INJ_SEV", "INJSEV_IM", "WEIGHT"])
PAIRS = [("AGE", "AGE_IM", [998, 999]), ("SEX", "SEX_IM", [8, 9]), ("SEAT_POS", "SEAT_IM", [19, 29, 39, 49, 98, 99]),
         ("EJECTION", "EJECT_IM", [7, 9]), ("INJ_SEV", "INJSEV_IM", [9])]
for src, im, unk in PAIRS:
    t = p.group_by("YEAR").agg(
        pl.len().alias("n"),
        pl.col(src).is_in(unk).sum().alias("n_src_unknown"),
        (pl.col(src).is_in(unk) & pl.col(im).is_in(unk)).sum().alias("im_still_unknown"),
        (~pl.col(src).is_in(unk) & (pl.col(src) != pl.col(im))).sum().alias("known_but_changed"),
        pl.col(im).is_null().sum().alias("im_null"),
    ).sort("YEAR")
    print(f"\n### {src} -> {im}")
    print(t)
    ch = p.filter(~pl.col(src).is_in(unk) & (pl.col(src) != pl.col(im)))
    if ch.height:
        print("  examples of known-but-changed:", ch.group_by([src, im]).len().sort("len", descending=True).head(8).to_dicts())
# where unknowns go
print("\nSEAT_POS row-unknown (19/29/39/49) -> SEAT_IM:")
print(p.filter(pl.col("SEAT_POS").is_in([19, 29, 39, 49])).group_by(["SEAT_POS", "SEAT_IM"]).len().sort(["SEAT_POS", "len"], descending=[False, True]).head(20))
print("EJECTION 7/9 -> EJECT_IM:", p.filter(pl.col("EJECTION").is_in([7, 9])).group_by(["EJECTION", "EJECT_IM"]).len().sort("len", descending=True).to_dicts())
print("SEX 8/9 -> SEX_IM:", p.filter(pl.col("SEX").is_in([8, 9])).group_by(["SEX_IM"]).len().to_dicts())
print("AGE_IM range:", p.select(pl.col("AGE_IM").min().alias("mn"), pl.col("AGE_IM").max().alias("mx")).to_dicts())
# AGE code set in unlabelled years
print("AGE special codes by year:", p.filter(pl.col("AGE") > 120).group_by(["YEAR", "AGE"]).len().sort(["YEAR", "AGE"]).to_dicts())
print("AGE max<990 by year:", p.filter(pl.col("AGE") < 990).group_by("YEAR").agg(pl.col("AGE").max()).sort("YEAR").to_dicts())
# MAX_SEV = 9 composition
a = load_table("CRSS", "accident", columns=["CASENUM", "MAX_SEV"])
agg = p.group_by(["YEAR", "CASENUM"]).agg(pl.col("INJ_SEV").filter(pl.col("INJ_SEV").is_in([0, 1, 2, 3, 4])).max().alias("mk"),
                                          pl.col("INJ_SEV").eq(9).sum().alias("n9"), pl.col("INJ_SEV").eq(5).sum().alias("n5"), pl.len().alias("np"))
j = a.join(agg, on=["YEAR", "CASENUM"], how="inner")
print("MAX_SEV x max-known (pooled):")
print(j.group_by(["MAX_SEV", "mk"]).len().pivot(on="mk", index="MAX_SEV", values="len", sort_columns=True).sort("MAX_SEV"))
