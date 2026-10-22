"""ALC_RES: code->label pairs from embedded labels, FARS all years + CRSS 2019+; units check; special codes."""
import polars as pl, re
from nhtsa_stats.ingestion.cache import load_table
pl.Config.set_tbl_rows(200); pl.Config.set_fmt_str_lengths(80); pl.Config.set_tbl_width_chars(250)
for src in ["FARS","CRSS"]:
    df = load_table(src, "person", years=None, columns=["ALC_RES","ALC_RESNAME"])
    g = df.group_by(["YEAR","ALC_RES","ALC_RESNAME"]).len()
    # special codes
    print(f"### {src} special codes (>=900)")
    sp = g.filter(pl.col("ALC_RES")>=900).sort(["ALC_RES","YEAR"])
    print(sp.pivot(on="YEAR", index=["ALC_RES","ALC_RESNAME"], values="len", sort_columns=True))
    # check label pattern for numeric codes: code c -> "0.ccc % BAC"
    num = g.filter((pl.col("ALC_RES")<940) & pl.col("ALC_RESNAME").is_not_null())
    num = num.with_columns(pl.col("ALC_RESNAME").str.extract(r"([0-9]*\.[0-9]+)",1).cast(pl.Float64).alias("labval"))
    num = num.with_columns((pl.col("labval")*1000).round(0).cast(pl.Int64).alias("lab_x1000"))
    bad = num.filter(pl.col("lab_x1000")!=pl.col("ALC_RES"))
    print(f"{src}: labelled numeric code-label pairs: {num.height}; mismatches code != 1000*label value: {bad.height}")
    print(bad.head(20))
    # distinct label suffixes
    print(num.with_columns(pl.col("ALC_RESNAME").str.replace_all(r"[0-9.]","").alias("suffix")).group_by(["YEAR","suffix"]).agg(pl.col("len").sum()).sort(["YEAR","suffix"]))
    print(g.filter(pl.col("ALC_RES").is_in([0,1,10,80,939,940])).sort(["ALC_RES","YEAR"]))
