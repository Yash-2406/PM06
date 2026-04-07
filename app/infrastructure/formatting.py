"""Number formatting utilities for Indian currency and CAPEX year.

All public functions are pure — no I/O, no side effects.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Optional


def format_indian_amount(amount: Decimal | float | int | str) -> str:
    """Format a number with standard Western comma grouping.

    Examples:
        1234567.89  → '1,234,567.89'
        45000       → '45,000.00'
        344430.21   → '344,430.21'
    """
    try:
        amt = Decimal(str(amount))
    except (InvalidOperation, ValueError, TypeError):
        return str(amount)

    sign = "-" if amt < 0 else ""
    amt = abs(amt)
    integer_part = int(amt)
    decimal_part = f"{amt % 1:.2f}"[1:]  # ".XX"

    s = str(integer_part)
    if len(s) <= 3:
        return f"{sign}{s}{decimal_part}"

    # Standard Western grouping: groups of 3 from right
    result = ""
    for i, digit in enumerate(reversed(s)):
        if i > 0 and i % 3 == 0:
            result = "," + result
        result = digit + result

    return f"{sign}{result}{decimal_part}"


def parse_indian_amount(text: str) -> Optional[Decimal]:
    """Parse an Indian-formatted amount string to Decimal.

    Handles: '12,34,567.89', '₹ 12,34,567', '1234567.89', 'Rs.1234567'.
    Returns None on failure (never raises).
    """
    if not text:
        return None
    cleaned = str(text).replace("₹", "").replace("Rs.", "").replace("Rs", "")
    cleaned = cleaned.replace(",", "").strip()
    try:
        return Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return None


def get_capex_year(ref_date: Optional[date] = None) -> str:
    """Auto-calculate CAPEX financial year from a date.

    Financial year starts April 1.
    March 2026 → '2025-26', April 2026 → '2026-27'.

    Args:
        ref_date: Date to compute from; defaults to today.
    """
    today = ref_date or date.today()
    if today.month >= 4:
        return f"{today.year}-{str(today.year + 1)[2:]}"
    return f"{today.year - 1}-{str(today.year)[2:]}"
