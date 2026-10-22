import sys; sys.path.insert(0, "scripts/audit")
from helpers import *
c = pl.col
src = sys.argv[1]
if src == "FARS":
    auxc = ["A_DOW", "A_TOD", "A_INTER", "A_ROADFC", "A_RU", "A_JUNC", "A_INTSEC", "A_RELRD", "A_MANCOL", "A_WEATHER", "A_REGION", "A_CRAINJ", "A_CT", "BIA", "SPJ_INDIAN", "INDIAN_RES", "TRACT", "CENSUS_2020_TRACT_FIPS"]
    mainc = ["DAY_WEEK", "HOUR", "FUNC_SYS", "ROUTE", "RUR_URB", "RELJCT1", "RELJCT2", "TYP_INT", "REL_ROAD", "MAN_COLL", "WEATHER", "STATE", "VE_FORMS", "VE_TOTAL", "SP_JUR", "RD_OWNER"]
    pairs = [("A_TOD", "HOUR"), ("A_INTER", "FUNC_SYS"), ("A_INTER", "ROUTE"), ("A_ROADFC", "FUNC_SYS"), ("A_RU", "RUR_URB"), ("A_JUNC", "RELJCT2"), ("A_INTSEC", "RELJCT2"), ("A_INTSEC", "TYP_INT"),
             ("A_RELRD", "REL_ROAD"), ("A_MANCOL", "MAN_COLL"), ("A_WEATHER", "WEATHER"), ("A_REGION", "STATE"), ("A_CT", "VE_FORMS"), ("BIA", "SP_JUR"), ("SPJ_INDIAN", "SP_JUR"), ("INDIAN_RES", "SP_JUR"), ("BIA", "RD_OWNER")]
else:
    auxc = ["A_DOW", "A_TOD", "A_INTER", "A_JUNC", "A_INTSEC", "A_RELRD", "A_MANCOL", "A_WEATHER", "A_CRAINJ", "A_CT"]
    mainc = ["DAY_WEEK", "WKDY_IM", "HOUR", "HOUR_IM", "INT_HWY", "RELJCT1", "RELJCT1_IM", "RELJCT2", "RELJCT2_IM", "TYP_INT", "REL_ROAD", "MAN_COLL", "MANCOL_IM", "WEATHER", "WEATHR_IM", "MAX_SEV", "MAXSEV_IM", "VE_FORMS", "VE_TOTAL"]
    pairs = [("A_TOD", "HOUR_IM"), ("A_INTER", "INT_HWY"), ("A_JUNC", "RELJCT2_IM"), ("A_JUNC", "RELJCT2"), ("A_INTSEC", "RELJCT2_IM"), ("A_INTSEC", "TYP_INT"), ("A_RELRD", "REL_ROAD"), ("A_MANCOL", "MANCOL_IM"),
             ("A_WEATHER", "WEATHR_IM"), ("A_WEATHER", "WEATHER"), ("A_CRAINJ", "MAXSEV_IM"), ("A_CRAINJ", "MAX_SEV"), ("A_CT", "VE_FORMS")]
df = aux_main(src, "crash", auxc, mainc)
for a, b in pairs:
    print(f"\n######## {src} {a} x {b}")
    print(wide(df, a, b, src, "accident"))
print("A_DOW by DAY_WEEK x hour-band")
dw = "WKDY_IM" if src == "CRSS" else "DAY_WEEK"; hr = "HOUR_IM" if src == "CRSS" else "HOUR"
d = df.with_columns(pl.when(c(hr) == 99).then(99).when(c(hr) < 6).then(0).when(c(hr) < 18).then(6).otherwise(18).alias("hb"))
print(d.group_by([dw, "hb", "A_DOW"]).agg(pl.len()).sort([dw, "hb", "A_DOW"]).pivot(on="A_DOW", index=[dw, "hb"], values="len", sort_columns=True))
if src == "FARS":
    print("TRACT vs FIPS null:", df.filter(c("YEAR") >= 2020).group_by(["TRACT", c("CENSUS_2020_TRACT_FIPS").is_null().alias("fips_null")]).agg(pl.len()).to_dicts())
    print("FIPS prefix == STATE:", df.filter(c("CENSUS_2020_TRACT_FIPS").is_not_null()).select((c("CENSUS_2020_TRACT_FIPS").str.slice(0, 2).cast(pl.Int64) == c("STATE")).mean()).item())
    print("FIPS lengths:", df.filter(c("CENSUS_2020_TRACT_FIPS").is_not_null()).group_by(c("CENSUS_2020_TRACT_FIPS").str.len_chars()).agg(pl.len()).to_dicts())
