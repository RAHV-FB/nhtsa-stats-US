"""G02: reproduce 84,207 (drug-positive driver deaths, determinate crashes) and 222,767 undetermined; compare with crash-level drugs==1 (43,552)."""
import polars as pl
d=pl.read_parquet('data/processed/fars_driver.parquet',columns=['YEAR','case_id','drv_drug_any'])
c=pl.read_parquet('data/processed/fars_crash.parquet',columns=['YEAR','case_id','FATALS','drugs'])
g=d.group_by(['YEAR','case_id']).agg((pl.col('drv_drug_any')==1).any().alias('pos'),pl.col('drv_drug_any').null_count().alias('nn'),pl.col('drv_drug_any').sum().alias('s'),pl.len().alias('n'))
g=g.join(c,on=['YEAR','case_id'],how='inner')
print('crashes joined',len(g),'of',len(c))
print('pos any driver deaths',g.filter(pl.col('pos'))['FATALS'].sum())
print('pos & determinate',g.filter(pl.col('pos')&(pl.col('nn')==0))['FATALS'].sum())
print('undetermined (nonpos w/ null)',g.filter(~pl.col('pos')&(pl.col('nn')>0))['FATALS'].sum())
print('crash drugs==1 deaths',g.filter(pl.col('drugs')==1)['FATALS'].sum())
print(g.group_by(['pos','drugs']).agg(pl.col('FATALS').sum()).sort(['pos','drugs']))
print(d['drv_drug_any'].value_counts())
