"""Enumerations used across the TPDDL PM06 tool."""

from enum import Enum


class WorkType(Enum):
    """Four work-type categories with detection priority: DT_AUG > ABC > LT_HT > LT_STD."""

    LT_STANDARD = "LT_STANDARD"
    LT_HT_POLE = "LT_HT_POLE"
    DT_AUGMENTATION = "DT_AUGMENTATION"
    ABC_WIRING = "ABC_WIRING"

    @property
    def display_name(self) -> str:
        """Human-readable name for UI display."""
        _names = {
            "LT_STANDARD": "LT Line Extension (Standard)",
            "LT_HT_POLE": "LT Extension with HT/PSCC Poles",
            "DT_AUGMENTATION": "DT Augmentation",
            "ABC_WIRING": "ABC Cable + Standard Cable Mix",
        }
        return _names[self.value]

    @property
    def sub_head(self) -> str:
        """Sub-Head value for the executive summary bullet list."""
        if self == WorkType.DT_AUGMENTATION:
            return "LT Augmentation"
        return "LT Line Extension up to 5 Poles"


class CaseStatus(Enum):
    """Status lifecycle for a scheme case."""

    PENDING = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"


class FieldConfidence(Enum):
    """Confidence level of an extracted field value."""

    HIGH = "high"      # Strong regex match on structured text
    MEDIUM = "medium"  # OCR result or ambiguous source
    LOW = "low"        # Not found — user must enter manually
    MANUAL = "manual"  # User has overridden the extracted value

    @property
    def ui_icon(self) -> str:
        """Icon for the Review Extracted Data screen."""
        _icons = {"high": "\u2713", "medium": "\u26A0", "low": "\u2717", "manual": "\u270E"}
        return _icons[self.value]


class FileType(Enum):
    """Three document types accepted by the tool."""

    SCHEME_PDF = "SCHEME_PDF"
    SITE_VISIT_PDF = "SITE_VISIT_PDF"
    PM06_EXCEL = "PM06_EXCEL"