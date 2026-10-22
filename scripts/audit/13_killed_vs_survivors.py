"""Restraint-unknown share: killed vs surviving LPV occupants (FARS rows; CRSS weighted), by year.
Reads out/restraint_by_sev_{FARS,CRSS}.csv written by 09_restraint_detail.py."""
import polars as pl
OUT = "/tmp/nhtsa-audit/out"
pl.Config.set_tbl_rows(40); pl.Config.set_tbl_width_chars(250); pl.Config.set_tbl_cols(30)
for src in ("FARS", "CRSS"):
    d = pl.read_csv(f"{OUT}/restraint_by_sev_{src}.csv")
    grp = (pl.when(pl.col("sev") == "K").then(pl.lit("K")).when(pl.col("sev") == "A").then(pl.lit("A"))
           .when(pl.col("sev").is_in(["B", "C", "O"])).then(pl.lit("BCO")).when(pl.col("sev").is_in(["U5", "U9"])).then(pl.lit("sev_unk")).otherwise(pl.lit("other")))
    d = d.with_columns(grp.alias("g"), (pl.col("r") == "unknown").alias("u"))
    def tab(by):
        t = d.group_by(by).agg((pl.col("w") * pl.col("u")).sum().alias("wu"), pl.col("w").sum().alias("w"), pl.col("n").sum().alias("n"),
                               (pl.col("n") * pl.col("u")).sum().alias("nu"))
        return t.with_columns((100 * pl.col("wu") / pl.col("w")).round(2).alias("pct"))
    t = tab(["YEAR", "g"])
    print(f"### {src}: % restraint unknown (98/99), LPV occupants, by year x group")
    print(t.pivot(on="g", index="YEAR", values="pct").select(["YEAR", "K", "A", "BCO", "sev_unk"]).sort("YEAR"))
    s = tab(["g"])
    print(s.select(["g", "n", "nu", "pct"]).sort("g"))
    # survivors pooled (A,BCO) vs K, odds ratio
    k = s.filter(pl.col("g") == "K").row(0, named=True)
    sv = s.filter(pl.col("g").is_in(["A", "BCO"])).select(pl.col("wu").sum(), pl.col("w").sum()).row(0)
    pk, ps = k["wu"] / k["w"], sv[0] / sv[1]
    print(f"  K {100*pk:.2f}% vs survivors(KABCO A-O) {100*ps:.2f}%  OR={pk/(1-pk)/(ps/(1-ps)):.2f}")
