import polars as pl
pl.Config.set_tbl_rows(100); pl.Config.set_tbl_cols(40); pl.Config.set_tbl_width_chars(300)
PAIRS = [("MOD_YEAR","MDLYR_IM",[9998,9999]),("BODY_TYP","BDYTYP_IM",[98,99]),("HIT_RUN","HITRUN_IM",[9]),("IMPACT1","IMPACT1_IM",[98,99]),
         ("P_CRASH1","PCRASH1_IM",[99]),("MAX_VSEV","MXVSEV_IM",[9]),("NUM_INJV","NUMINJ_IM",[99]),("VEH_ALCH","V_ALCH_IM",[9]),("M_HARM","VEVENT_IM",[98,99])]
rows=[]
for y in range(2016,2025):
    lf = pl.scan_parquet(f"data/interim/CRSS/vehicle/{y}.parquet"); have = lf.collect_schema().names()
    a = pl.scan_parquet(f"data/interim/CRSS/veh_aux/{y}.parquet").select("CASENUM","VEH_NO","A_MOD_YR").collect()
    cols = sorted({c for p in PAIRS for c in p[:2] if c in have})
    d = lf.select(["CASENUM","VEH_NO"]+cols).collect().join(a, on=["CASENUM","VEH_NO"], how="left")
    for o,im,miss in PAIRS:
        if o not in have or im not in have: continue
        known = d.filter(~pl.col(o).is_in(miss)); unk = d.filter(pl.col(o).is_in(miss))
        rows.append(dict(year=y, orig=o, im=im, pct_unknown=round(100*unk.height/d.height,2), agree_when_known=round(100*(known[o]==known[im]).mean(),3),
                         im_has_unknown_codes=int(d[im].is_in(miss).sum()), n_distinct_im=d[im].n_unique()))
    if "MDLYR_IM" in have:
        rows.append(dict(year=y, orig="A_MOD_YR", im="MDLYR_IM", pct_unknown=None, agree_when_known=round(100*(d["A_MOD_YR"]==d["MDLYR_IM"]).mean(),3), im_has_unknown_codes=None, n_distinct_im=None))
r = pl.DataFrame(rows)
print(r.pivot(on="year", index=["orig","im"], values="agree_when_known"))
print(r.pivot(on="year", index=["orig","im"], values="im_has_unknown_codes"))
