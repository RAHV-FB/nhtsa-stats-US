"""Locate and validate the raw FARS/CRSS archives.

Archive names follow ``{FARS|CRSS}{year}[National][Auxiliary]{CSV|CVS}.zip`` (the 2019 CRSS
auxiliary file is distributed as ``...AuxiliaryCVS.zip``).  Each archive is classified by
source, year and kind (``main`` or ``aux``).  Validation checks that the file is a real ZIP
(not an un-fetched Git LFS pointer), that every member passes its CRC check and, when the
committed LFS pointer is available, that the SHA-256 matches it.
"""

from __future__ import annotations

import hashlib
import re
import subprocess
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from nhtsa_stats import config

ARCHIVE_RE = re.compile(
    r"^(?P<source>FARS|CRSS)(?P<year>\d{4})(?:National)?(?P<aux>Auxiliary)?C(?:SV|VS)\.zip$",
    re.IGNORECASE,
)
LFS_POINTER_PREFIX = b"version https://git-lfs.github.com/spec/v1"


class ArchiveError(RuntimeError):
    """Raised when an archive is missing, unfetched or corrupt."""


@dataclass(frozen=True)
class Archive:
    path: Path
    source: str
    year: int
    kind: str  # "main" | "aux"
    size_bytes: int = field(compare=False)

    @property
    def key(self) -> str:
        return f"{self.source}_{self.year}_{self.kind}"


def parse_archive_name(name: str) -> tuple[str, int, str] | None:
    m = ARCHIVE_RE.match(name)
    if not m:
        return None
    return m["source"].upper(), int(m["year"]), "aux" if m["aux"] else "main"


def discover_archives(raw_dir: Path | None = None) -> list[Archive]:
    raw_dir = raw_dir or config.RAW_DIR
    out: list[Archive] = []
    for p in sorted(raw_dir.glob("*.zip")):
        parsed = parse_archive_name(p.name)
        if parsed is None:
            continue
        source, year, kind = parsed
        out.append(Archive(p, source, year, kind, p.stat().st_size))
    return sorted(out, key=lambda a: (a.source, a.year, a.kind))


def is_lfs_pointer(path: Path) -> bool:
    with path.open("rb") as fh:
        return fh.read(len(LFS_POINTER_PREFIX)) == LFS_POINTER_PREFIX


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while block := fh.read(chunk):
            h.update(block)
    return h.hexdigest()


def committed_lfs_oid(path: Path) -> str | None:
    """Return the SHA-256 recorded in the committed Git LFS pointer, if retrievable."""
    try:
        rel = path.resolve().relative_to(config.PROJECT_ROOT)
        txt = subprocess.run(
            ["git", "show", f"HEAD:{rel.as_posix()}"],
            cwd=config.PROJECT_ROOT,
            capture_output=True,
            check=True,
            timeout=30,
        ).stdout
    except (ValueError, subprocess.SubprocessError, OSError):
        return None
    m = re.search(rb"oid sha256:([0-9a-f]{64})", txt)
    return m.group(1).decode() if m else None


def validate_archive(archive: Archive, check_lfs: bool = True) -> dict:
    """Validate one archive and return a provenance record.

    Raises ArchiveError if the file is an LFS pointer, not a ZIP, or fails CRC checks.
    """
    if is_lfs_pointer(archive.path):
        raise ArchiveError(
            f"{archive.path.name} is a Git LFS pointer; run `git lfs pull` to fetch the data."
        )
    if not zipfile.is_zipfile(archive.path):
        raise ArchiveError(f"{archive.path.name} is not a ZIP archive")
    with zipfile.ZipFile(archive.path) as zf:
        bad = zf.testzip()
        if bad is not None:
            raise ArchiveError(f"{archive.path.name}: CRC failure in member {bad}")
        members = [i for i in zf.infolist() if not i.is_dir()]
    digest = sha256_file(archive.path)
    lfs_oid = committed_lfs_oid(archive.path) if check_lfs else None
    if lfs_oid is not None and lfs_oid != digest:
        raise ArchiveError(f"{archive.path.name}: SHA-256 differs from committed LFS pointer")
    return {
        "archive": archive.path.name,
        "source": archive.source,
        "year": archive.year,
        "kind": archive.kind,
        "size_bytes": archive.size_bytes,
        "sha256": digest,
        "lfs_oid_match": None if lfs_oid is None else lfs_oid == digest,
        "n_members": len(members),
        "members": [
            {"name": i.filename, "uncompressed_bytes": i.file_size, "crc": f"{i.CRC:08x}"}
            for i in members
        ],
    }
