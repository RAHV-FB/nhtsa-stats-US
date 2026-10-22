"""ZIP discovery, validation and CSV parsing on synthetic archives (software tests only)."""

from __future__ import annotations

import zipfile
from pathlib import Path

import polars as pl
import pytest

from nhtsa_stats.ingestion.archives import (
    Archive,
    ArchiveError,
    parse_archive_name,
    validate_archive,
)
from nhtsa_stats.ingestion.readers import (
    decode_bytes,
    label_columns,
    normalise_table_name,
    read_member,
    table_members,
)


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("FARS2016NationalCSV.zip", ("FARS", 2016, "main")),
        ("FARS2024NationalAuxiliaryCSV.zip", ("FARS", 2024, "aux")),
        ("CRSS2019AuxiliaryCVS.zip", ("CRSS", 2019, "aux")),  # upstream typo
        ("CRSS2020CSV.zip", ("CRSS", 2020, "main")),
        ("README.zip", None),
    ],
)
def test_parse_archive_name(name, expected):
    assert parse_archive_name(name) == expected


@pytest.mark.parametrize(
    ("member", "table"),
    [
        ("ACCIDENT.CSV", "accident"),
        ("FARS2024NationalCSV/accident.csv", "accident"),
        ("CEVENTS.csv", "cevent"),
        ("MIPER.csv", "miper"),
    ],
)
def test_normalise_table_name(member, table):
    assert normalise_table_name(member) == table


def _make_zip(path: Path, members: dict[str, bytes]) -> Path:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, data in members.items():
            zf.writestr(name, data)
    return path


def test_read_member_types_and_labels(tmp_path):
    csv = (
        b"ST_CASE,STATE,STATENAME,RAIL,WEIGHT,TWAY_ID\n"
        b'10001,1,Alabama,0000000,12.5,"SR-69"\n'
        b"10002,1,Alabama,0000000,,I-65\n"
    )
    z = _make_zip(tmp_path / "FARS2020NationalCSV.zip", {"FARS2020NationalCSV/accident.csv": csv})
    assert table_members(z) == {"accident": "FARS2020NationalCSV/accident.csv"}
    df, meta = read_member(z, "FARS2020NationalCSV/accident.csv")
    assert meta["rows"] == 2
    assert df.schema["ST_CASE"] == pl.Int64
    assert df.schema["STATENAME"] == pl.Utf8  # label column stays text
    assert df.schema["RAIL"] == pl.Utf8  # leading zeros preserved
    assert df["RAIL"][0] == "0000000"
    assert df.schema["WEIGHT"] == pl.Float64
    assert df["WEIGHT"][1] is None  # empty field -> null, never 0


def test_cp1252_fallback():
    raw = "CITYNAME\nCa\xf1on City\n".encode("cp1252")
    text, enc = decode_bytes(raw)
    assert enc == "cp1252"
    assert "Cañon" in text


def test_label_columns_require_stem():
    assert label_columns(["A", "ANAME", "ROUTENAME", "CITYNAME", "CITY"]) == {"ANAME", "CITYNAME"}


def test_validate_rejects_lfs_pointer(tmp_path):
    p = tmp_path / "FARS2016NationalCSV.zip"
    p.write_bytes(b"version https://git-lfs.github.com/spec/v1\noid sha256:abc\nsize 1\n")
    with pytest.raises(ArchiveError, match="LFS pointer"):
        validate_archive(Archive(p, "FARS", 2016, "main", p.stat().st_size), check_lfs=False)


def test_validate_accepts_zip(tmp_path):
    z = _make_zip(tmp_path / "CRSS2016CSV.zip", {"ACCIDENT.CSV": b"CASENUM\n1\n"})
    rec = validate_archive(Archive(z, "CRSS", 2016, "main", z.stat().st_size), check_lfs=False)
    assert rec["n_members"] == 1
    assert len(rec["sha256"]) == 64


def test_duplicate_table_names_rejected(tmp_path):
    z = _make_zip(tmp_path / "x.zip", {"a/ACCIDENT.CSV": b"X\n1\n", "b/accident.csv": b"X\n1\n"})
    with pytest.raises(ValueError, match="duplicate table"):
        table_members(z)
