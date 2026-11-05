"""Explore FARS columns for G04."""
import polars as pl
for t,y in [("veh_aux",2019),("veh_aux",2021),("acc_aux",2021),("vehicle",2019),("vehicle",2021),("per_aux",2021)]:
    d=pl.read_parquet(f"data/interim/FARS/{t}/{y}.parquet")
    print(t,y,d.shape,[c for c in d.columns if c in("A_BODY","A_LT","BODY_TYP","GVWR","GVWR_FROM","GVWR_TO","TOW_VEH","A_PTYPE","MCARR_I1","HIT_RUN","VEH_NO","M_HARM","MAX_VSEV","UNITTYPE","PER_TYP")])
