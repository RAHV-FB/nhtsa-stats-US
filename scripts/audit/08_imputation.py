import polars as pl
from nhtsa_stats.ingestion.cache import load_table
pl.Config.set_tbl_formatting("ASCII_MARKDOWN"); pl.Config.set_tbl_rows(300); pl.Config.set_tbl_hide_dataframe_shape(True); pl.Config.set_tbl_hide_column_data_types(True); pl.Config.set_tbl_cols(40); pl.Config.set_tbl_width_chars(250)
PAIRS = [('HOUR','HOUR_IM',[99]),('MINUTE','MINUTE_IM',[99]),('DAY_WEEK','WKDY_IM',[9]),('LGT_COND','LGTCON_IM',[8,9]),('WEATHER','WEATHR_IM',[98,99]),
         ('MAN_COLL','MANCOL_IM',[98,99]),('HARM_EV','EVENT1_IM',[98,99]),('RELJCT1','RELJCT1_IM',[8,9]),('RELJCT2','RELJCT2_IM',[98,99]),
         ('MAX_SEV','MAXSEV_IM',[9]),('NUM_INJ','NO_INJ_IM',[99]),('ALCOHOL','ALCHL_IM',[8,9])]
cols = sorted({c for p in PAIRS for c in p[:2]})
a = load_table('CRSS','accident',columns=['CASENUM','WEIGHT'] + cols)
a = a.with_columns(pl.col('MAX_SEV').replace_strict({0:'0_O',1:'1_C',2:'2_B',3:'3_A',4:'4_K',5:'5_U',9:'5_U',6:'6_other',8:'6_other'}, default='?').alias('sev'),
                   pl.col('MAXSEV_IM').replace_strict({0:'0_O',1:'1_C',2:'2_B',3:'3_A',4:'4_K',5:'5_U',6:'6_other',8:'6_other'}, default='?').alias('sev_im'))
W = pl.col('WEIGHT')
rows = []
for o, im, unk in PAIRS:
    d = a.filter(pl.col(im).is_not_null())
    s = d.group_by('YEAR').agg(
        pl.len().alias('n'),
        (pl.col(o).is_in(unk).mean()*100).round(2).alias('pct_orig_unknown'),
        ((pl.col(o)!=pl.col(im)).mean()*100).round(2).alias('pct_im_differs'),
        ((~pl.col(o).is_in(unk)) & (pl.col(o)!=pl.col(im))).sum().alias('n_known_but_changed'),
        (pl.col(o).is_in(unk) & (pl.col(o)==pl.col(im))).sum().alias('n_unknown_not_imputed'),
        pl.col(im).is_in(unk).sum().alias('n_im_still_unknown_code'),
    ).sort('YEAR')
    print(f'### {o} -> {im}'); print(s)
    ch = d.filter((~pl.col(o).is_in(unk)) & (pl.col(o)!=pl.col(im)))
    if ch.height:
        print('known-but-changed examples (orig -> im):'); print(ch.group_by([o, im]).len().sort('len', descending=True).head(12))
    # weighted imputation share by severity (pooled, years with IM)
    sv = d.group_by('sev').agg(((pl.col(o).is_in(unk).cast(pl.Float64)*W).sum()/W.sum()*100).round(2).alias('w_pct_imputed'), pl.len().alias('n')).sort('sev')
    print('weighted % imputed by MAX_SEV (pooled):', dict(zip(sv['sev'].to_list(), sv['w_pct_imputed'].to_list())))
# Distribution of imputed values vs known values (pooled 2016-2024 weighted)
for o, im, unk in [('LGT_COND','LGTCON_IM',[8,9]),('WEATHER','WEATHR_IM',[98,99]),('RELJCT2','RELJCT2_IM',[98,99]),('RELJCT1','RELJCT1_IM',[8,9]),('MAX_SEV','MAXSEV_IM',[9]),('ALCOHOL','ALCHL_IM',[9]),('MAN_COLL','MANCOL_IM',[98,99])]:
    d = a.filter(pl.col(im).is_not_null()).with_columns(pl.col(o).is_in(unk).alias('imp'))
    t = d.group_by(['imp', im]).agg(W.sum().alias('w')).with_columns((pl.col('w')/pl.col('w').sum().over('imp')*100).round(1).alias('pct')).pivot(on='imp', index=im, values='pct').sort(im)
    print(f'## {im}: weighted % distribution among imputed (true) vs observed (false)'); print(t)
# MAX_SEV imputation within 2019 relation to... ALCOHOL code 8 handling
print(a.filter(pl.col('ALCOHOL')==8).group_by(['ALCHL_IM']).len())
print(a.filter(pl.col('MAX_SEV')==8).group_by(['ALCOHOL','ALCHL_IM']).len())
