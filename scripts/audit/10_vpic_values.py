import polars as pl
pl.Config.set_tbl_rows(200); pl.Config.set_tbl_cols(30); pl.Config.set_tbl_width_chars(300); pl.Config.set_fmt_str_lengths(60)
OUT="/tmp/nhtsa-audit/out"
F = ["ELECTRONICSTABILITYCONTROL","ANTILOCKBRAKESYSTEM","TRACTIONCONTROL","FORWARDCOLLISIONWARNING","CRASHIMMINENTBRAKING","DYNAMICBRAKESUPPORT",
     "PEDESTRIANAUTOEMERGENCYBRAKING","LANEDEPARTUREWARNING","LANEKEEPINGASSISTANCE","LANECENTERINGASSISTANCE","BLINDSPOTWARNING","BLINDSPOTINTERVENTION",
     "ADAPTIVECRUISECONTROL","BACKUPCAMERA","REARAUTOMATICEMERGENCYBRAKING","AIRBAGLOCFRONT","AIRBAGLOCSIDE","AIRBAGLOCCURTAIN","AIRBAGLOCKNEE","SEATBELTTYPE","PRETENSIONER","TPMS",
     "DAYTIMERUNNINGLIGHT","AUTOMATICCRASHNOTIFICATION","EVENTDATARECORDER","SEMIAUTOHEADLAMPBEAMSWITCHING","ADAPTIVEDRIVINGBEAM","VINDECODEERROR","VEHICLETYPE","ENGINEELECTRIFICATIONLEVEL","FUELTYPEPRIMARY"]
rows=[]
for src in ["FARS","CRSS"]:
    for y in range(2016,2025):
        p = pl.scan_parquet(f"data/interim/{src}/vpicdecode/{y}.parquet").select(F).collect()
        for f in F:
            vc = p.group_by(f).len()
            for val,n in vc.iter_rows():
                rows.append((src,y,f,str(val) if val is not None else "<null>",n,p.height))
out = pl.DataFrame(rows, schema=["source","year","field","value","n","N"], orient="row").with_columns((100*pl.col("n")/pl.col("N")).round(2).alias("pct"))
out.write_csv(f"{OUT}/vpic_values.csv")
for f in F:
    x = out.filter(pl.col("field")==f).with_columns((pl.col("source").str.slice(0,1)+pl.col("year").cast(pl.Utf8).str.slice(2,2)).alias("sy"))
    print("###", f)
    print(x.pivot(on="sy", index="value", values="pct").select(["value"]+[s+str(y)[2:] for s in "FC" for y in (2016,2018,2020,2022,2024)]).sort("value"))
