import polars as pl
from nhtsa_stats.ingestion.cache import load_table
pl.Config.set_tbl_formatting("ASCII_MARKDOWN"); pl.Config.set_tbl_rows(300); pl.Config.set_tbl_hide_dataframe_shape(True); pl.Config.set_tbl_hide_column_data_types(True); pl.Config.set_tbl_cols(40); pl.Config.set_tbl_width_chars(250); pl.Config.set_fmt_str_lengths(60)
CB = pl.read_csv('/home/user/nhtsa-stats-US/outputs/audit/codebook.csv', infer_schema_length=0)
V = ['HOUR','MINUTE','HOUR_IM','MINUTE_IM','DAY_WEEK','WKDY_IM','MONTH','LGT_COND','LGTCON_IM','WEATHER','WEATHER1','WEATHER2','WEATHR_IM','URBANICITY','REGION','INT_HWY',
     'RELJCT1','RELJCT1_IM','RELJCT2','RELJCT2_IM','TYP_INT','REL_ROAD','WRK_ZONE','MAN_COLL','MANCOL_IM','HARM_EV','EVENT1_IM','SCH_BUS','MAX_SEV','MAXSEV_IM','ALCOHOL','ALCHL_IM','CF1','CF2','CF3','NUM_INJ','NO_INJ_IM','STRATUM','PSUSTRAT']
a = load_table('CRSS','accident',columns=V)
out = []
for v in V:
    d = a.select('YEAR', v).filter(pl.col(v).is_not_null()).group_by(['YEAR', v]).len().with_columns((pl.col('len')/pl.col('len').sum().over('YEAR')).alias('p'))
    lab19 = set(CB.filter((pl.col('source')=='CRSS')&(pl.col('table')=='accident')&(pl.col('variable')==v)&(pl.col('year')=='2019'))['code'].to_list())
    lab_any = set(CB.filter((pl.col('source')=='CRSS')&(pl.col('table')=='accident')&(pl.col('variable')==v))['code'].to_list())
    early = set(str(x) for x in d.filter(pl.col('YEAR')<=2018)[v].to_list())
    f_lab = set(CB.filter((pl.col('source')=='FARS')&(pl.col('table')=='accident')&(pl.col('variable')==v)&(pl.col('year').is_in(['2016','2017','2018'])))['code'].to_list())
    def tvd(y1, y2):
        x = d.filter(pl.col('YEAR')==y1).select(v, pl.col('p').alias('a')).join(d.filter(pl.col('YEAR')==y2).select(v, pl.col('p').alias('b')), on=v, how='full', coalesce=True).fill_null(0)
        return round(0.5*float((x['a']-x['b']).abs().sum()), 3)
    if not lab19: continue
    out.append(dict(var=v, n_codes_16_18=len(early), codes_16_18_not_in_CRSS2019_labels=','.join(sorted(early-lab19, key=lambda s: int(s))) or '-',
                    not_in_any_CRSS_label=','.join(sorted(early-lab_any, key=lambda s: int(s))) or '-',
                    not_in_FARS_16_18_labels=(','.join(sorted(early-f_lab, key=lambda s: int(s))) or '-') if f_lab else 'n/a',
                    tvd16_17=tvd(2016,2017), tvd17_18=tvd(2017,2018), tvd18_19=tvd(2018,2019), tvd19_20=tvd(2019,2020), tvd20_21=tvd(2020,2021), tvd21_22=tvd(2021,2022), tvd22_23=tvd(2022,2023), tvd23_24=tvd(2023,2024)))
print(pl.DataFrame(out))
