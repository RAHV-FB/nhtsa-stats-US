import polars as pl
from nhtsa_stats.ingestion.cache import load_table
pl.Config.set_tbl_formatting("ASCII_MARKDOWN"); pl.Config.set_tbl_rows(300); pl.Config.set_tbl_hide_dataframe_shape(True); pl.Config.set_tbl_hide_column_data_types(True); pl.Config.set_tbl_cols(40); pl.Config.set_tbl_width_chars(250)
f = load_table('FARS','accident',columns=['ST_CASE','STATE','RUR_URB','FUNC_SYS','RD_OWNER','NHS','ROUTE','LGT_COND'])
print('RUR_URB x FUNC_SYS (2016-24 pooled counts)')
print(f.group_by(['RUR_URB','FUNC_SYS']).len().pivot(on='RUR_URB', index='FUNC_SYS', values='len', sort_columns=True).sort('FUNC_SYS'))
print('RUR_URB=6 <=> FUNC_SYS=96 ?', f.select(((pl.col('RUR_URB')==6)==(pl.col('FUNC_SYS')==96)).mean()), ' RD_OWNER=96 <=> RUR_URB=6', f.select(((pl.col('RUR_URB')==6)==(pl.col('RD_OWNER')==96)).mean()))
print('ROUTE=96 vs RUR_URB=6 (2023+):', f.filter(pl.col('YEAR')>=2023).group_by([pl.col('ROUTE')==96, pl.col('RUR_URB')==6]).len())
# urban share by state change 2016 -> 2019 -> 2021 -> 2024
cb = pl.read_csv('/home/user/nhtsa-stats-US/outputs/audit/codebook.csv', infer_schema_length=0)
st = cb.filter((pl.col('source')=='FARS')&(pl.col('variable')=='STATE')&(pl.col('table')=='accident')).select(pl.col('code').cast(pl.Int64).alias('STATE'), pl.col('label').alias('st')).unique('STATE')
g = f.filter(pl.col('RUR_URB').is_in([1,2])).group_by(['YEAR','STATE']).agg(((pl.col('RUR_URB')==2).mean()*100).round(1).alias('urb'), pl.len().alias('n'))
p = g.pivot(on='YEAR', index='STATE', values='urb', sort_columns=True).join(st, on='STATE').with_columns((pl.col('2024')-pl.col('2016')).round(1).alias('d16_24'), (pl.col('2018')-pl.col('2017')).round(1).alias('d17_18'),(pl.col('2021')-pl.col('2020')).round(1).alias('d20_21'),(pl.col('2023')-pl.col('2022')).round(1).alias('d22_23'))
print('states with largest |urban share change| 2016->2024 (%)'); print(p.sort(pl.col('d16_24').abs(), descending=True).select('st','2016','2017','2018','2019','2020','2021','2022','2023','2024','d16_24').head(15))
nat = f.filter(pl.col('RUR_URB').is_in([1,2])).group_by('YEAR').agg(((pl.col('RUR_URB')==2).mean()*100).round(2).alias('urban_pct_known')).sort('YEAR'); print(nat)
# Reweight: urban share holding 2016 state mix constant
w16 = g.filter(pl.col('YEAR')==2016).select('STATE', pl.col('n').alias('n16'))
std = g.join(w16, on='STATE').group_by('YEAR').agg(((pl.col('urb')*pl.col('n16')).sum()/pl.col('n16').sum()).round(2).alias('urban_pct_std_2016_state_mix')).sort('YEAR'); print(std)
# light condition by RUR_URB
print(f.filter(pl.col('RUR_URB').is_in([1,2])).group_by(['RUR_URB','LGT_COND']).len().with_columns((pl.col('len')/pl.col('len').sum().over('RUR_URB')*100).round(1)).pivot(on='RUR_URB', index='LGT_COND', values='len').sort('LGT_COND'))
# RD_OWNER 25 in 2016 by state
print(f.filter((pl.col('YEAR')<=2017)&(pl.col('RD_OWNER')==25)).join(st,on='STATE').group_by(['YEAR','st']).len().sort('len',descending=True).head(6))
