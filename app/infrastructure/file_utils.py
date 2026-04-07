"""File I/O utility functions.

Atomic writes, file-type validation via magic bytes, safe path helpers.
"""

from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path
from typing import Optional

from app.domain.constants import PDF_MAGIC, XLSX_MAGIC
from app.domain.enums import FileType
from app.domain.exceptions import FileTypeError
from app.infrastructure.logger import get_logger

logger = get_logger(__name__)

# Magic byte signatures for file type validation
_MAGIC_MAP: dict[FileType, bytes] = {
    FileType.SCHEME_PDF: PDF_MAGIC,
    FileType.SITE_VISIT_PDF: PDF_MAGIC,
    FileType.PM06_EXCEL: XLSX_MAGIC,
}


def validate_file_type(file_path: Path | str, expected_type: FileType | str) -> bool | None:
    """Validate a file's magic bytes match the expected file type.

    Args:
        file_path: Path to the file to validate.
        expected_type: Expected FileType enum value or string like 'pdf', 'xlsx'.

    Returns:
        True if valid, False if magic bytes don't match.
        Raises FileNotFoundError if file does not exist.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Resolve string type to FileType enum for magic lookup
    if isinstance(expected_type, str):
        _type_map = {"pdf": FileType.SCHEME_PDF, "xlsx": FileType.PM06_EXCEL}
        expected_type = _type_map.get(expected_type.lower())
        if expected_type is None:
            return True  # no validation rule for this type string

    expected_magic = _MAGIC_MAP.get(expected_type)
    if expected_magic is None:
        return True  # no validation rule for this type

    with open(file_path, "rb") as f:
        header = f.read(max(len(expected_magic), 8))

    return header.startswith(expected_magic)


def atomic_write_bytes(target_path: Path, data: bytes) -> None:
    """Write bytes to a file atomically.

    Writes to a temporary file in the same directory, then uses
    os.replace() to atomically swap it into place.
    """
    target_path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        dir=str(target_path.parent),
        prefix=f".{target_path.stem}_",
        suffix=".tmp",
    )
    try:
        with os.fdopen(fd, "wb") as tmp_file:
            tmp_file.write(data)
        os.replace(tmp_path, str(target_path))
        logger.info("Atomic write completed: %s", target_path)
    except BaseException:
        # Clean up temp file on any failure
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def compute_file_hash(file_path: Path | str) -> str:
    """Compute SHA-256 hash of a file for change detection / audit."""
    file_path = Path(file_path)
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha.update(chunk)
    return sha.hexdigest()


def ensure_directory(dir_path: Path) -> Path:
    """Create directory (and parents) if it does not exist, then return it."""
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


def detect_file_type(file_path: Path) -> Optional[FileType]:
    """Detect FileType from magic bytes. Returns None if unrecognised."""
    if not file_path.exists():
        return None
    with open(file_path, "rb") as f:
        header = f.read(8)
    if header.startswith(PDF_MAGIC):
        return FileType.SCHEME_PDF  # caller decides SCHEME vs SITE_VISIT
    if header.startswith(XLSX_MAGIC):
        return FileType.PM06_EXCEL
    return None
