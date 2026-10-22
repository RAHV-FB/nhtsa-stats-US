"""Per source-year code distributions (from data) joined to embedded labels (codebook.csv).

Writes OUT/codesets.csv and prints a compact per-variable matrix: code | label variants (with years) | n per year.
High-cardinality variables are summarised (only codes whose label is not purely numeric, or code >= 900).
"""
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import polars as pl
from common import OUT, YEARS, codebook, lt, norm

SPEC = {
    # table: [vars]
    "vehicle": ["SPEEDREL", "DR_SF1", "DR_SF2", "DR_SF3", "DR_SF4", "L_STATUS", "CDL_STAT", "L_COMPL", "L_RESTRI",
                "L_ENDORS", "L_TYPE", "PREV_ACC", "PREV_SUS", "PREV_SUS1", "PREV_SUS2", "PREV_SUS3", "PREV_DWI",
                "PREV_SPD", "PREV_OTH", "DR_DRINK", "DR_PRES", "TRAV_SP", "VSPD_LIM", "DR_HGT", "DR_WGT",
                "FIRST_MO", "FIRST_YR", "LAST_MO", "LAST_YR", "HIT_RUN", "MAX_VSEV"],
    "distract": ["MDRDSTRD", "DRDISTRACT"],
    "drimpair": ["DRIMPAIR"],
    "factor": ["MFACTOR", "VEHICLECC"],
    "maneuver": ["MDRMANAV", "MANEUVER"],
    "violatn": ["MVIOLATN", "VIOLATION"],
    "vision": ["MVISOBSC", "VISION"],
    "driverrf": ["DRIVERRF"],
    "personrf": ["PERSONRF"],
    "person": ["P_SF1", "P_SF2", "P_SF3"],
    "crashrf": ["CRASHRF"],
    "accident": ["CF1", "CF2", "CF3", "MAX_SEV"],
    "acc_aux": ["A_SPCRA", "A_DIST", "A_DROWSY"],
    "veh_aux": ["A_DRDIS", "A_DRDRO", "A_SPVEH", "A_LIC_S", "A_LIC_C", "A_CDL_S", "A_MC_L_S"],
}
HIGHCARD = {"TRAV_SP", "VSPD_LIM", "DR_HGT", "DR_WGT", "FIRST_YR", "LAST_YR"}

cb = codebook()
rows = []
for src in ["FARS", "CRSS"]:
    for table, vars_ in SPEC.items():
        avail = pl.read_csv("/home/user/nhtsa-stats-US/outputs/audit/variable_availability.csv")
        avail = avail.filter((pl.col("source") == src) & (pl.col("table") == table))
        present = set(avail["column"].to_list())
        vs = [v for v in vars_ if v in present]
        if not vs:
            continue
        df = lt(src, table, ["YEAR"] + vs)
        for v in vs:
            c = (df.filter(pl.col(v).is_not_null()).group_by("YEAR", v).len()
                 .rename({v: "code", "len": "n"}).with_columns(pl.col("code").cast(pl.Utf8)))
            c = c.with_columns(source=pl.lit(src), table=pl.lit(table), variable=pl.lit(v))
            rows.append(c)
        del df
allc = pl.concat(rows, how="diagonal")
lab = cb.select(pl.col("source"), pl.col("year").alias("YEAR"), "table", "variable", "code", "label")
allc = allc.join(lab, on=["source", "YEAR", "table", "variable", "code"], how="left")
allc = allc.with_columns(pl.col("label").map_elements(norm, return_dtype=pl.Utf8).alias("nlabel"))
allc.write_csv(f"{OUT}/codesets.csv")

# compact print
for (src, table, v), g in allc.group_by(["source", "table", "variable"], maintain_order=True):
    pass
keys_ = allc.select("source", "table", "variable").unique(maintain_order=True).sort("source", "table", "variable")
for src, table, v in keys_.iter_rows():
    g = allc.filter((pl.col("source") == src) & (pl.col("table") == table) & (pl.col("variable") == v))
    yrs = sorted(g["YEAR"].unique().to_list())
    print(f"\n### {src} {table}.{v}  years={yrs[0]}-{yrs[-1]} ({len(yrs)})")
    codes = g["code"].unique().to_list()
    try:
        codes = sorted(codes, key=lambda x: float(x))
    except ValueError:
        codes = sorted(codes)
    tot = g.group_by("YEAR").agg(pl.col("n").sum()).sort("YEAR")
    print("   totals:", dict(zip(tot["YEAR"].to_list(), tot["n"].to_list())))
    for code in codes:
        gc = g.filter(pl.col("code") == code).sort("YEAR")
        labs = gc.filter(pl.col("label").is_not_null()).group_by("nlabel").agg(
            pl.col("label").first(), pl.col("YEAR").min().alias("y0"), pl.col("YEAR").max().alias("y1"),
            pl.col("YEAR").n_unique().alias("ny"))
        if v in HIGHCARD:
            try:
                fc = float(code)
            except ValueError:
                fc = 0
            labtxt = " ".join(labs["label"].to_list())
            if fc < 900 and not any(ch.isalpha() for ch in labtxt.replace("MPH", "").replace("Inches", "")
                                    .replace("Lbs", "").replace("lbs", "").replace("inches", "").replace("mph", "")):
                continue
        cnt = {y: 0 for y in yrs}
        for y, n in zip(gc["YEAR"].to_list(), gc["n"].to_list()):
            cnt[y] = n
        lab_s = " | ".join(f"[{r['y0']}-{r['y1']}:{r['ny']}y] {r['label']}" for r in labs.sort("y0").iter_rows(named=True))
        print(f"  {code:>5} {lab_s[:160]}")
        print("        n:", " ".join(f"{cnt[y]}" for y in yrs))
