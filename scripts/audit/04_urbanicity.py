import polars as pl
from nhtsa_stats.ingestion.cache import load_table
pl.Config.set_tbl_formatting("ASCII_MARKDOWN"); pl.Config.set_tbl_rows(200); pl.Config.set_tbl_hide_dataframe_shape(True); pl.Config.set_tbl_hide_column_data_types(True); pl.Config.set_tbl_cols(30); pl.Config.set_fmt_str_lengths(150)
a = load_table('CRSS', 'accident', columns=['CASENUM','URBANICITY','PSU','PSU_VAR','PSUSTRAT','STRATUM','PJ','REGION','WEIGHT','INT_HWY','RELJCT2','TYP_INT','REL_ROAD','LGT_COND','HARM_EV','MAX_SEV'])
for g in ['PSU','PJ','PSUSTRAT','PSU_VAR']:
    s = a.group_by(['YEAR', g]).agg(pl.col('URBANICITY').n_unique().alias('nu'), pl.len().alias('n'))
    print(g, s.group_by('YEAR').agg(pl.len().alias('n_groups'), (pl.col('nu')>1).sum().alias('groups_mixed'), pl.col('n').filter(pl.col('nu')>1).sum().alias('crashes_in_mixed')).sort('YEAR'))
# is URBANICITY constant within PSU across years?
s = a.group_by('PSU').agg(pl.col('URBANICITY').n_unique().alias('nu'), pl.col('YEAR').n_unique().alias('ny'))
print('PSU across all years: n PSU', s.height, 'mixed', s.filter(pl.col('nu')>1).height)
print(a.group_by(['YEAR']).agg(pl.col('PSU').n_unique().alias('nPSU'), pl.col('PJ').n_unique().alias('nPJ'), pl.col('PSUSTRAT').n_unique().alias('nPSUSTRAT'), pl.col('PSU_VAR').n_unique().alias('nPSUVAR'), pl.col('STRATUM').n_unique().alias('nSTRATUM')).sort('YEAR'))
# PSUs by urbanicity per year
print(a.group_by(['YEAR','URBANICITY']).agg(pl.col('PSU').n_unique().alias('nPSU'), pl.len().alias('n'), pl.col('WEIGHT').sum().round(0).alias('wsum')).sort(['YEAR','URBANICITY']))
# PSUSTRAT x URBANICITY
print(a.filter(pl.col('YEAR')==2022).group_by(['PSUSTRAT','URBANICITY']).agg(pl.col('PSU').n_unique().alias('nPSU'), pl.len()).sort(['PSUSTRAT','URBANICITY']))
# Labels of PSUSTRAT? check codebook
cb = pl.read_csv('/home/user/nhtsa-stats-US/outputs/audit/codebook.csv', infer_schema_length=0)
print(cb.filter((pl.col('source')=='CRSS')&(pl.col('variable').is_in(['URBANICITY','PSUSTRAT','REGION']))&(pl.col('table')=='accident')).group_by(['variable','code','label']).agg(pl.col('year').sort().str.join(',')).sort(['variable','code']))
