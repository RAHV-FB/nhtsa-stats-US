"""FARS within-vehicle designs: counts of LPV vehicles with 2+ occupants having known restraint and known
injury (KABCO 0-4), seat-position availability, discordance (restraint and fatal outcome), driver+RF pairs.

Known restraint: REST_USE in belted {1,2,3,6,8}, child {4,10,11,12}, none {7,20}.
Restrained = belted or child.  Known seat: SEAT_POS in 11..56 excluding 19,29,39,49.
Adults (AGE 16-120) used for the belted-vs-unbelted discordance count.
"""
import polars as pl

from nhtsa_stats.ingestion.cache import load_table

pl.Config.set_tbl_rows(40)
pl.Config.set_tbl_cols(30)
pl.Config.set_tbl_width_chars(300)
OUT = "outputs/cache/audit/out"
p = load_table("FARS", "person", columns=["ST_CASE", "VEH_NO", "PER_NO", "PER_TYP", "BODY_TYP", "INJ_SEV", "REST_USE", "SEAT_POS", "AGE"])
p = p.filter(pl.col("PER_TYP").is_in([1, 2, 9]) & pl.col("BODY_TYP").is_between(1, 49))
p = p.with_columns(
    pl.col("REST_USE").is_in([1, 2, 3, 6, 8, 4, 10, 11, 12, 7, 20]).alias("kr"),
    pl.col("REST_USE").is_in([1, 2, 3, 6, 8, 4, 10, 11, 12]).alias("restrained"),
    pl.col("INJ_SEV").is_between(0, 4).alias("ki"),
    (pl.col("SEAT_POS").is_between(11, 56) & ~pl.col("SEAT_POS").is_in([19, 29, 39, 49])).alias("ks"),
    pl.col("AGE").is_between(16, 120).alias("adult"),
)
p = p.with_columns((pl.col("kr") & pl.col("ki")).alias("kri"), (pl.col("kr") & pl.col("ki") & pl.col("ks")).alias("kris"))
V = ["YEAR", "ST_CASE", "VEH_NO"]
v = p.group_by(V).agg(
    pl.len().alias("n_occ"),
    pl.col("kri").sum().alias("n_kri"),
    pl.col("kris").sum().alias("n_kris"),
    (pl.col("kri") & pl.col("adult") & pl.col("restrained")).sum().alias("n_adult_restr"),
    (pl.col("kri") & pl.col("adult") & ~pl.col("restrained")).sum().alias("n_adult_unrestr"),
    (pl.col("kri") & (pl.col("INJ_SEV") == 4)).sum().alias("n_kri_K"),
    (pl.col("kri") & (pl.col("INJ_SEV") != 4)).sum().alias("n_kri_notK"),
    (pl.col("kri") & (pl.col("INJ_SEV") >= 3)).sum().alias("n_kri_KA"),
    (pl.col("kri") & (pl.col("INJ_SEV") < 3)).sum().alias("n_kri_notKA"),
    # driver + right-front passenger both known restraint & injury
    (pl.col("kri") & (pl.col("SEAT_POS") == 11) & (pl.col("PER_TYP") == 1)).any().alias("drv_ok"),
    (pl.col("kri") & (pl.col("SEAT_POS") == 13)).any().alias("rf_ok"),
    ((pl.col("SEAT_POS") == 11) & (pl.col("PER_TYP") == 1)).any().alias("has_drv"),
    (pl.col("SEAT_POS") == 13).any().alias("has_rf"),
    (pl.col("INJ_SEV") == 4).any().alias("any_K"),
)
v = v.with_columns(
    (pl.col("n_kri") >= 2).alias("ge2_kri"),
    (pl.col("n_kris") >= 2).alias("ge2_kris"),
    ((pl.col("n_adult_restr") >= 1) & (pl.col("n_adult_unrestr") >= 1)).alias("restr_discord"),
    ((pl.col("n_kri_K") >= 1) & (pl.col("n_kri_notK") >= 1)).alias("K_discord"),
    ((pl.col("n_kri_KA") >= 1) & (pl.col("n_kri_notKA") >= 1)).alias("KA_discord"),
    (pl.col("drv_ok") & pl.col("rf_ok")).alias("drv_rf_ok"),
)
res = v.group_by("YEAR").agg(
    pl.len().alias("LPV_veh"),
    (pl.col("n_occ") >= 2).sum().alias("veh_ge2_occ"),
    pl.col("ge2_kri").sum().alias("veh_ge2_knownR_I"),
    pl.col("ge2_kris").sum().alias("veh_ge2_knownR_I_S"),
    (pl.col("ge2_kri") & pl.col("K_discord")).sum().alias("ge2_K_discord"),
    (pl.col("ge2_kri") & pl.col("KA_discord")).sum().alias("ge2_KA_discord"),
    (pl.col("ge2_kri") & pl.col("restr_discord")).sum().alias("adult_restr_discord"),
    (pl.col("ge2_kri") & pl.col("restr_discord") & pl.col("K_discord")).sum().alias("restr&K_discord"),
    (pl.col("has_drv") & pl.col("has_rf")).sum().alias("drv+RF_present"),
    pl.col("drv_rf_ok").sum().alias("drv+RF_known"),
    (pl.col("drv_rf_ok") & pl.col("any_K")).sum().alias("drv+RF_known_anyK"),
    pl.col("n_kri").filter(pl.col("ge2_kri")).sum().alias("persons_in_ge2"),
).sort("YEAR")
print("### FARS LPV within-vehicle design counts")
print(res)
tot = res.drop("YEAR").sum()
print("pooled:", tot.to_dicts())
res.write_csv(f"{OUT}/within_vehicle_FARS.csv")
# loss: among vehicles with >=2 occupants, share losing eligibility due to restraint unknown vs injury unknown
occ2 = p.join(v.filter(pl.col("n_occ") >= 2).select(V), on=V)
print("occupants in 2+ occupant LPVs: % unknown restraint, % unknown injury, % unknown seat (row-unknown incl.)")
print(occ2.group_by("YEAR").agg(pl.len(), (~pl.col("kr")).mean().alias("unk_restr"), (~pl.col("ki")).mean().alias("unk_inj"),
                                (~pl.col("ks")).mean().alias("unk_seat")).sort("YEAR"))
# Seat position known among kri persons in ge2 vehicles
pk = p.join(v.filter(pl.col("ge2_kri")).select(V), on=V).filter(pl.col("kri"))
print("seat known among eligible persons:", pk.group_by("YEAR").agg(pl.col("ks").mean()).sort("YEAR").to_dicts())
print("seat distribution among eligible persons (pooled):",
      pk.with_columns(pl.when(pl.col("SEAT_POS") == 11).then(pl.lit("11 driver")).when(pl.col("SEAT_POS").is_between(12, 18)).then(pl.lit("front other"))
                      .when(pl.col("SEAT_POS").is_between(21, 28)).then(pl.lit("row2")).when(pl.col("SEAT_POS").is_between(31, 48)).then(pl.lit("row3+"))
                      .when(pl.col("SEAT_POS").is_between(50, 56)).then(pl.lit("cargo/ext")).otherwise(pl.lit("unknown")).alias("s"))
      .group_by("s").len().sort("len", descending=True).to_dicts())
