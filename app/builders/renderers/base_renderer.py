"""Abstract base renderer — Strategy pattern: one class per work type.

Each renderer provides 4 text blocks used in the Executive Summary.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional


def _is_pole_code(val: str) -> bool:
    """Check if value looks like a pole/substation code with letter prefix or numeric format."""
    import re
    if not val:
        return False
    # Starts with letter(s) followed by 3+ digits (HT517, U517, etc.)
    if re.match(r'[A-Za-z]+\d{3}', val):
        return True
    # Numeric pole code like "523-53/1/1"
    if re.match(r'\d{3}[-/]', val):
        return True
    return False


def pick_pole_ref(tapping_pole: str | None, substation_name: str | None) -> str:
    """Pick the best pole reference for 'from pole no. X' text.

    Prefers tapping_pole when it has a valid code.
    Falls back to substation_name if tapping_pole is missing/generic.
    """
    tp = (tapping_pole or "").strip().rstrip(".")
    sn = (substation_name or "").strip().rstrip(".")
    # Strip substation name part after comma
    if ',' in sn:
        sn = sn.split(',')[0].strip()
    tp_is_code = _is_pole_code(tp)
    sn_is_code = _is_pole_code(sn)

    # Always prefer tapping_pole when it's a valid code — it's the explicit field
    if tp_is_code:
        return tp
    elif sn_is_code:
        return sn
    else:
        return tp or sn or "[Pole No.]"


class BaseRenderer(ABC):
    """Abstract base for work-type-specific text generation."""

    @abstractmethod
    def capex_title(
        self,
        notification_no: str,
        existing_dt_capacity: Optional[str] = None,
        new_transformer_rating: Optional[str] = None,
        acb_description: Optional[str] = None,
    ) -> str:
        """Return the CAPEX title line for the executive summary."""
        ...

    @abstractmethod
    def existing_scenario(self, notification_no: str, **kwargs) -> str:
        """Return the Existing Scenario paragraph."""
        ...

    @abstractmethod
    def proposed_scenario(
        self,
        tapping_pole: Optional[str],
        existing_dt_capacity: Optional[str],
        new_transformer_rating: Optional[str] = None,
        acb_description: Optional[str] = None,
        substation_name: Optional[str] = None,
    ) -> str:
        """Return the Proposed Scenario paragraph."""
        ...

    @abstractmethod
    def sub_head(self) -> str:
        """Return the Sub-Head value for the bullet list."""
        ...
