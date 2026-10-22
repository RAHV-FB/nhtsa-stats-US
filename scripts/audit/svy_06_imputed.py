"""CRSS *_IM vs originals: share imputed by year; whether only unknown codes are filled; recodes; by severity."""
import polars as pl, pandas as pd, re
from nhtsa_stats.ingestion.cache import load_table
pd.set_option("display.width",260); pd.set_option("display.max_columns",40); pd.set_option("display.max_rows",500)
cb = pl.read_csv("/home/user/nhtsa-stats-US/outputs/audit/codebook.csv", infer_schema_length=0).filter(pl.col("source")=="CRSS")
PAIRS = {"accident": [("DAY_WEEK","WKDY_IM"),("HOUR","HOUR_IM"),("MINUTE","MINUTE_IM"),("HARM_EV","EVENT1_IM"),("MAN_COLL","MANCOL_IM"),
            ("RELJCT1","RELJCT1_IM"),("RELJCT2","RELJCT2_IM"),("LGT_COND","LGTCON_IM"),("WEATHER","WEATHR_IM"),("MAX_SEV","MAXSEV_IM"),
            ("NUM_INJ","NO_INJ_IM"),("ALCOHOL","ALCHL_IM")],
         "vehicle": [("BODY_TYP","BDYTYP_IM"),("HIT_RUN","HITRUN_IM"),("IMPACT1","IMPACT1_IM"),("MOD_YEAR","MDLYR_IM"),("MAX_VSEV","MXVSEV_IM"),
            ("NUM_INJV","NUMINJ_IM"),("P_CRASH1","PCRASH1_IM"),("M_HARM","VEVENT_IM"),("VEH_ALCH","V_ALCH_IM")],
         "person": [("AGE","AGE_IM"),("SEX","SEX_IM"),("INJ_SEV","INJSEV_IM"),("SEAT_POS","SEAT_IM"),("EJECTION","EJECT_IM"),("DRINKING","PERALCH_IM")]}
UNK = re.compile(r"unknown|not reported|reported as unknown", re.I)
def unk_codes(table, var):
    x = cb.filter((pl.col("table")==table)&(pl.col("variable")==var)).select(["code","label"]).unique()
    codes = sorted({int(c) for c,l in x.iter_rows() if l and UNK.search(l)})
    return codes, {int(c):l for c,l in x.iter_rows()}
sev = load_table("CRSS","accident",years=None,columns=["CASENUM","MAXSEV_IM","WEIGHT"]).rename({"MAXSEV_IM":"SEVC"})
summary=[]; details=[]
for table, pairs in PAIRS.items():
    cols = ["CASENUM"] + sorted({c for p in pairs for c in p}) + (["INJSEV_IM"] if table=="person" else [])
    cols = list(dict.fromkeys(cols))
    df = load_table("CRSS", table, years=None, columns=cols).join(sev, on=["YEAR","CASENUM"], how="left")
    for orig, im in pairs:
        uc, labs = unk_codes(table, orig)
        d = df.filter(pl.col(im).is_not_null() & pl.col(orig).is_not_null())
        # deterministic map of known codes: modal IM per orig code over all years
        ct = d.group_by([orig, im]).agg(pl.len().alias("n"))
        tot = ct.group_by(orig).agg(pl.col("n").sum().alias("N"))
        mode = ct.sort("n", descending=True).group_by(orig).first().join(tot, on=orig).with_columns((pl.col("n")/pl.col("N")).alias("share"))
        det = mode.filter(pl.col("share")>=0.995).select([orig, pl.col(im).alias("map_im")])
        nondet = mode.filter(pl.col("share")<0.995).sort("N", descending=True)
        d2 = d.join(det, on=orig, how="left").with_columns(
            pl.col(orig).is_in(uc).alias("unk"),
            (pl.col(orig)!=pl.col(im)).alias("diff"),
            (pl.col("map_im").is_not_null() & (pl.col(im)!=pl.col("map_im"))).alias("dev_from_map"))
        g = d2.group_by("YEAR").agg(pl.len().alias("n"), (pl.col("unk").mean()*100).round(2).alias("pct_unk"),
              (pl.col("diff").mean()*100).round(2).alias("pct_im_ne_orig"),
              ((pl.col("diff") & ~pl.col("unk")).mean()*100).round(3).alias("pct_known_changed"),
              ((pl.col("unk") & (pl.col(im).is_in(uc))).sum()).alias("unk_left_unk"),
              (pl.col("dev_from_map").mean()*100).round(3).alias("pct_dev_detmap")).sort("YEAR")
        for r in g.iter_rows(named=True):
            summary.append(dict(table=table, orig=orig, im=im, unk_codes=str(uc), **r))
        # nondeterministic known codes (excluding unknown codes)
        nd = nondet.filter(~pl.col(orig).is_in(uc))
        details.append((table, orig, im, uc, [labs.get(c,"?") for c in uc], nd.head(8).to_dicts(), mode.filter(pl.col(orig).is_in(uc)).to_dicts()))
        # severity dependence of imputation (unknown share by crash MAXSEV_IM), 2019-2024 pooled + 2016-18 pooled
        s = d2.group_by(["SEVC"]).agg(pl.len().alias("n"), (pl.col("unk").mean()*100).round(2).alias("pct_unk")).sort("SEVC")
        details.append(("SEV", orig, im, s.to_dicts()))
    del df
S = pl.DataFrame(summary)
S.write_csv("/tmp/nhtsa-audit/svy_06_imputed.csv")
print(S.to_pandas().to_string(index=False))
for x in details:
    print(x)
