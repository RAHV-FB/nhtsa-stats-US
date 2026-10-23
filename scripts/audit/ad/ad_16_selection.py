"""FARS: selection into testing by police report among killed vs survivors; sensitivity in high-testing states; bias illustration."""
import polars as pl
OUT = "outputs/cache/audit/out_ad"
pl.Config.set_tbl_rows(200); pl.Config.set_tbl_width_chars(260); pl.Config.set_tbl_cols(30)
df = pl.read_parquet(f"{OUT}/fars_drivers.parquet").filter(pl.col("sev").is_in(["killed","survived"]))
print("P(measured BAC | DRINKING) by sev:")
print(df.group_by(["sev","DRINKING"]).agg((pl.col("alc_stat")=="measured").mean().mul(100).round(1).alias("pct_measured"), pl.len()).sort(["sev","DRINKING"]))
st = pl.read_csv(f"{OUT}/state_testrates.csv")
for thr in [50, 70]:
    hs = st.filter((pl.col("alc_survived")>=thr)&(pl.col("alc_killed")>=thr))["STATE"].to_list()
    x = df.filter(pl.col("STATE").is_in(hs) & (pl.col("alc_stat")=="measured"))
    print(f"\nStates with >= {thr}% measured BAC in BOTH killed and surviving drivers: {sorted(hs)}")
    for sev in ["killed","survived"]:
        g = x.filter(pl.col("sev")==sev)
        pos = g.filter(pl.col("ALC_RES")>=80); neg = g.filter(pl.col("ALC_RES")<10); pos01 = g.filter(pl.col("ALC_RES")>=10)
        print(f"  {sev}: n_meas={g.height} prev08={100*pos.height/g.height:.1f} sens08(unk=no)={100*pos.filter(pl.col('DRINKING')==1).height/pos.height:.1f} "
              f"sens08(known)={100*pos.filter(pl.col('DRINKING')==1).height/max(pos.filter(pl.col('DRINKING').is_in([0,1])).height,1):.1f} "
              f"sens01(unk=no)={100*pos01.filter(pl.col('DRINKING')==1).height/pos01.height:.1f} "
              f"spec(BAC<.01, DRINKING!=1)={100*neg.filter(pl.col('DRINKING')!=1).height/neg.height:.1f} "
              f"unk(8/9)|BAC>=.08={100*pos.filter(pl.col('DRINKING').is_in([8,9])).height/pos.height:.1f} "
              f"unk(8/9)|BAC<.01={100*neg.filter(pl.col('DRINKING').is_in([8,9])).height/neg.height:.1f}")
    # also how representative: test rate in these states
    y = df.filter(pl.col("STATE").is_in(hs))
    print("  measured share in these states:", y.group_by("sev").agg((pl.col("alc_stat")=="measured").mean().mul(100).round(1)).to_dict(as_series=False))
