"""G02: tests 'drug status unknown for about half of fatal crashes' (policy_analysis s6) vs 63% (factor_contributions)
and whether police drugs==1 per-year 2022-24 (4,998) vs 2016-24 differ. Look at share of deaths by drugs code per period."""
import polars as pl
c=pl.read_parquet('data/processed/fars_crash.parquet',columns=['YEAR','FATALS','drugs'])
print(c['drugs'].value_counts())
for lab,lo,hi in [('2016-24',2016,2024),('2022-24',2022,2024)]:
    s=c.filter(pl.col('YEAR').is_between(lo,hi))
    g=s.group_by('drugs').agg(pl.col('FATALS').sum().alias('deaths'),pl.len().alias('crashes'))
    tot=s['FATALS'].sum();n=len(s)
    print(lab,'deaths',tot,'crashes',n,'years',hi-lo+1)
    for r in g.iter_rows(named=True): print(' ',r['drugs'],r['deaths'],round(r['deaths']/tot,3),r['crashes'],round(r['crashes']/n,3),'per yr deaths',round(r['deaths']/(hi-lo+1)))
