"""Person-level FARS drug test summary for 2016-2024 (2016-17 from person DRUGTST/DRUGRES 1-3; 2018+ from deduped drugs table).
Output: out_ad/fars_drug_person.parquet"""
import polars as pl
from nhtsa_stats.ingestion.cache import load_table
OUT = "outputs/cache/audit/out_ad"
pl.Config.set_tbl_rows(200); pl.Config.set_tbl_width_chars(250); pl.Config.set_tbl_cols(30)
K = ["YEAR","ST_CASE","VEH_NO","PER_NO"]
def drug_class(c, scheme):
    # returns class label expression for a DRUGRES code column c
    if scheme=="old":
        return (pl.when(c.is_between(100,295)).then(pl.lit("narcotic"))
                .when(c.is_between(300,399)).then(pl.lit("depressant"))
                .when(c.is_between(400,495)).then(pl.lit("stimulant"))
                .when(c.is_between(500,595)).then(pl.lit("hallucinogen"))
                .when(c.is_between(600,695)).then(pl.lit("cannabinoid"))
                .when(c.is_between(700,795)).then(pl.lit("pcp_dissoc"))
                .when(c.is_between(800,899)).then(pl.lit("steroid"))
                .when(c.is_between(900,995)).then(pl.lit("inhalant"))
                .when(c==996).then(pl.lit("other"))
                .when(c==997).then(pl.lit("res_unknown")).when(c==998).then(pl.lit("pos_type_unknown"))
                .when(c==999).then(pl.lit("unk_if_tested")).when(c==95).then(pl.lit("not_reported"))
                .when(c==0).then(pl.lit("not_given")).when(c==1).then(pl.lit("negative")).otherwise(pl.lit("UNMAPPED")))
    return (pl.when(c.is_between(1000,1997)).then(pl.lit("narcotic"))
            .when(c.is_between(2000,2997)).then(pl.lit("depressant"))
            .when(c.is_in([3026,3034,3066])).then(pl.lit("caff_nicotine"))
            .when(c.is_between(3000,3997)).then(pl.lit("stimulant"))
            .when(c.is_between(4000,4997)).then(pl.lit("hallucinogen"))
            .when(c.is_between(5000,5997)).then(pl.lit("cannabinoid"))
            .when(c.is_between(6000,6997)).then(pl.lit("pcp_dissoc"))
            .when(c.is_between(7000,7997)).then(pl.lit("inhalant"))
            .when(c.is_between(8000,8997)).then(pl.lit("steroid"))
            .when(c.is_between(9000,9994)).then(pl.lit("other_np"))
            .when(c==9996).then(pl.lit("other"))
            .when(c==9997).then(pl.lit("res_unknown")).when(c==9998).then(pl.lit("pos_type_unknown"))
            .when(c==9999).then(pl.lit("unk_if_tested")).when(c==9995).then(pl.lit("not_reported"))
            .when(c==0).then(pl.lit("not_given")).when(c==1).then(pl.lit("negative")).otherwise(pl.lit("UNMAPPED")))
# 2018+
d = load_table("FARS","drugs",years=None,columns=["ST_CASE","VEH_NO","PER_NO","DRUGSPEC","DRUGRES"]).unique()
d = pl.concat([d.filter(pl.col("YEAR")<=2021).with_columns(drug_class(pl.col("DRUGRES"),"old").alias("cls")),
               d.filter(pl.col("YEAR")>=2022).with_columns(drug_class(pl.col("DRUGRES"),"new").alias("cls"))])
d = d.with_columns((pl.col("cls")=="cannabinoid").alias("is_cann"),
                   ((pl.col("YEAR")>=2022)&(pl.col("DRUGRES")==5062)).alias("is_cthc"))
# old 2016-17
p = load_table("FARS","person",years=[2016,2017],columns=["ST_CASE","VEH_NO","PER_NO","DRUGTST1","DRUGRES1","DRUGRES2","DRUGRES3"])
long = pl.concat([p.select(K+[pl.col(f"DRUGRES{i}").alias("DRUGRES"), pl.col("DRUGTST1").alias("DRUGSPEC")]) for i in (1,2,3)])
long = long.with_columns(drug_class(pl.col("DRUGRES"),"old").alias("cls"), pl.lit(False).alias("is_cann"), pl.lit(False).alias("is_cthc"))
long = long.with_columns((pl.col("cls")=="cannabinoid").alias("is_cann"))
print("2016-17 DRUGTST1 x DRUGRES1 class:")
print(p.with_columns(drug_class(pl.col("DRUGRES1"),"old").alias("c1")).group_by(["DRUGTST1","c1"]).len().pivot(on="c1", index="DRUGTST1", values="len", sort_columns=True).sort("DRUGTST1"))
# drop the filler 'not_given' rows of DRUGRES2/3 for tested persons: keep rows whose cls is informative
allrows = pl.concat([long.select(K+["DRUGRES","cls","is_cann","is_cthc"]), d.select(K+["DRUGRES","cls","is_cann","is_cthc"])])
print("UNMAPPED codes:", allrows.filter(pl.col("cls")=="UNMAPPED").group_by(["YEAR","DRUGRES"]).len())
DRUGCL = ["narcotic","depressant","stimulant","hallucinogen","cannabinoid","pcp_dissoc","inhalant","steroid"]
agg = allrows.group_by(K).agg(
    pl.col("cls").is_in(DRUGCL+["caff_nicotine","other_np","other","pos_type_unknown","negative","res_unknown"]).any().alias("tested"),
    pl.col("cls").is_in(["not_reported"]).any().alias("any_notrep"),
    pl.col("cls").is_in(["unk_if_tested"]).any().alias("any_unkif"),
    pl.col("cls").is_in(["not_given"]).all().alias("all_notgiven"),
    pl.col("cls").is_in(DRUGCL).any().alias("pos_class"),
    (pl.col("cls")=="pos_type_unknown").any().alias("pos_unk"),
    pl.col("cls").is_in(["other","other_np","caff_nicotine"]).any().alias("pos_other"),
    (pl.col("cls")=="negative").any().alias("any_neg"),
    (pl.col("cls")=="res_unknown").any().alias("any_resunk"),
    *[(pl.col("cls")==c).any().alias(f"cls_{c}") for c in DRUGCL+["caff_nicotine","other_np","other"]],
    (pl.col("is_cann")&~pl.col("is_cthc")).any().alias("pos_cann_excl_cthc"),
)
agg = agg.with_columns(
    pl.when(pl.col("tested")).then(pl.lit("tested"))
     .when(pl.col("any_unkif")).then(pl.lit("unknown_if_tested"))
     .when(pl.col("any_notrep")).then(pl.lit("not_reported"))
     .when(pl.col("all_notgiven")).then(pl.lit("not_tested")).otherwise(pl.lit("other")).alias("drug_test_status"),
    pl.when(pl.col("pos_class")).then(pl.lit("positive_class"))
     .when(pl.col("pos_unk")).then(pl.lit("positive_type_unknown"))
     .when(pl.col("pos_other")).then(pl.lit("other_only"))
     .when(pl.col("any_neg")).then(pl.lit("negative"))
     .when(pl.col("any_resunk")).then(pl.lit("results_unknown")).otherwise(None).alias("drug_result"))
print(agg.group_by(["YEAR","drug_test_status"]).len().pivot(on="drug_test_status", index="YEAR", values="len", sort_columns=True).sort("YEAR"))
print(agg.filter(pl.col("tested")).group_by(["YEAR","drug_result"]).len().pivot(on="drug_result", index="YEAR", values="len", sort_columns=True).sort("YEAR"))
# conflicting: negative + positive within person
print("persons with negative row and positive row:", agg.filter(pl.col("any_neg") & pl.col("pos_class")).group_by("YEAR").len().sort("YEAR").to_dict(as_series=False))
agg.write_parquet(f"{OUT}/fars_drug_person.parquet")
