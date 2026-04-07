"""Text utility functions for the TPDDL PM06 tool.

All regex patterns are compiled at MODULE LEVEL.
"""

from __future__ import annotations

import re
from typing import Optional

from app.domain.constants import RE_LOGO_TEXT, RE_PAGE_HEADER

# Additional text-normalisation patterns
_RE_MULTI_SPACE: re.Pattern[str] = re.compile(r"\s+")
_RE_NON_WORD: re.Pattern[str] = re.compile(r"[^\w\s]")


def strip_pdf_headers(text: str) -> str:
    """Remove SAP page headers and logo text from concatenated PDF text.

    Must be called on the FULL concatenated text from all pages
    BEFORE any field extraction begins (Rule SC-1).
    """
    text = RE_PAGE_HEADER.sub("", text)
    text = RE_LOGO_TEXT.sub("", text)
    return text


def normalise_label(text: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace.

    Used by PM06 Excel label-value map builder.
    """
    text = text.lower().strip()
    text = _RE_NON_WORD.sub(" ", text)
    text = _RE_MULTI_SPACE.sub(" ", text)
    return text.strip()


def safe_decode_text(raw: bytes, encoding: str = "utf-8") -> str:
    """Decode bytes to string, falling back to latin-1 then replacing errors."""
    try:
        return raw.decode(encoding)
    except UnicodeDecodeError:
        try:
            return raw.decode("latin-1")
        except UnicodeDecodeError:
            return raw.decode(encoding, errors="replace")


def normalise_dt_capacity(raw: str | None) -> str | None:
    """Normalise DT capacity strings to canonical form.

    Examples: '400 kVA DT' / '400KVA' / '400kva' / '400  kVA DT'
    all become '400 kVA DT'.
    """
    if raw is None:
        return None
    raw = str(raw).strip()
    if not raw:
        return raw
    match = re.search(r"(\d+(?:\.\d+)?)", raw)
    if not match:
        return raw
    num = match.group(1)
    # Remove only non-significant trailing zeros after decimal point
    if '.' in num:
        num = num.rstrip('0').rstrip('.')
    return f"{num} kVA DT"


def clean_scope_text(text: str) -> str:
    """Clean up spacing and capitalisation in scope-of-work text."""
    text = _RE_MULTI_SPACE.sub(" ", text.strip())
    return text


def extract_zone_from_text(text: str) -> Optional[str]:
    """Try to find a zone number (3 or 4 digits) in text."""
    match = re.search(r"\b(\d{3,4})\b", text)
    return match.group(1) if match else None
