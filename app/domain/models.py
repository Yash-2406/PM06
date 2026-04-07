"""Domain models for the TPDDL PM06 tool.

Pure Python dataclasses. No I/O whatsoever — these are value objects
passed between layers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Generic, Optional, TypeVar

from app.domain.enums import CaseStatus, FieldConfidence, WorkType

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Extraction result wrapper — EVERY extraction function returns this
# ---------------------------------------------------------------------------


@dataclass
class ExtractionResult(Generic[T]):
    """Wraps an extracted value with its confidence and provenance."""

    value: Optional[T]
    confidence: FieldConfidence
    source: str  # "regex_match", "label_map", "ocr", "not_found"
    message: Optional[str] = None

    @property
    def is_found(self) -> bool:
        """True when a usable value was extracted."""
        return self.value is not None

    @property
    def ui_icon(self) -> str:
        """Icon character for the Review Extracted Data screen."""
        return self.confidence.ui_icon


# ---------------------------------------------------------------------------
# Applicant information
# ---------------------------------------------------------------------------


@dataclass
class ApplicantInfo:
    """Consumer / applicant details extracted from source documents."""

    name: str
    address: str
    notification_no: str  # primary (10-digit string)
    all_notification_nos: list[str]  # all found, for multi-applicant
    zone_code: str
    district_code: str
    pin_code: Optional[str] = None
    sanctioned_load_kw: Optional[str] = None
    area_type: Optional[str] = None  # "Electrified" / "Un-electrified"


# ---------------------------------------------------------------------------
# Scheme / order information
# ---------------------------------------------------------------------------


@dataclass
class SchemeInfo:
    """PM06 order and cost information."""

    order_no: str
    wbs_no: str
    capex_year: str
    sub_head: str
    work_type: WorkType
    estimated_cost: Decimal
    bom_total: Decimal
    bos_total: Decimal
    eif_total: Decimal = Decimal("0")
    rrc_total: Decimal = Decimal("0")
    nature_of_scheme: Optional[str] = None
    dt_capacity_existing: Optional[str] = None  # e.g. "400 kVA DT"
    dt_code: Optional[str] = None
    tapping_pole: Optional[str] = None
    scope_of_work: Optional[str] = None  # from PM06 Excel


# ---------------------------------------------------------------------------
# Bill of Materials row
# ---------------------------------------------------------------------------


@dataclass
class Material:
    """Single BOM line item from the Scheme Copy PDF."""

    description: Optional[str] = None
    code: Optional[str] = None
    unit: Optional[str] = None
    quantity: Optional[float] = None
    unit_rate: Optional[float] = None
    amount: Optional[float] = None
    sr_no: Optional[int] = None


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


@dataclass
class ValidationCheck:
    """Single verification check result (FR-02)."""

    field: str
    rule: str
    passed: bool
    message: str
    is_blocking: bool = True


@dataclass
class ValidationResult:
    """Aggregate verification result containing all checks."""

    checks: list[ValidationCheck] = field(default_factory=list)

    @property
    def is_blocked(self) -> bool:
        """True if any blocking check has failed."""
        return any(c.is_blocking and not c.passed for c in self.checks)

    @property
    def has_warnings(self) -> bool:
        """True if any non-blocking check has failed."""
        return any(not c.is_blocking and not c.passed for c in self.checks)

    @property
    def blocking_failures(self) -> list[ValidationCheck]:
        """All blocking checks that failed."""
        return [c for c in self.checks if c.is_blocking and not c.passed]

    @property
    def warnings(self) -> list[ValidationCheck]:
        """All non-blocking checks that failed."""
        return [c for c in self.checks if not c.is_blocking and not c.passed]


# ---------------------------------------------------------------------------
# Feeder detail from PM06 Excel sub-table
# ---------------------------------------------------------------------------


@dataclass
class FeederDetail:
    """One row from the feeder sub-table in PM06 Excel."""

    sr_no: float
    acb_no: float
    loading_amps: Optional[float] = None


# ---------------------------------------------------------------------------
# Top-level case aggregate
# ---------------------------------------------------------------------------


@dataclass
class Case:
    """Top-level aggregate representing one scheme processing case.

    Uses flat fields so services and builders can access attributes
    without navigating nested objects.
    """

    id: Optional[int] = None

    # Applicant
    applicant_name: Optional[str] = None
    address: Optional[str] = None
    pin_code: Optional[str] = None
    notification_no: Optional[str] = None
    all_notification_nos: list[str] = field(default_factory=list)
    zone: Optional[str] = None
    district: Optional[str] = None
    category: Optional[str] = None
    load_applied: Optional[str] = None
    area_type: Optional[str] = None

    # Scheme / Order
    order_no: Optional[str] = None
    wbs_no: Optional[str] = None
    work_type: Optional[WorkType] = None
    nature_of_scheme: Optional[str] = None
    scope_of_work: Optional[str] = None
    capex_year: Optional[str] = None
    proposal_type: Optional[str] = None
    detailed_reason: Optional[str] = None
    dt_loading: Optional[str] = None

    # Cost fields
    grand_total: Optional[float] = None
    bom_total: Optional[float] = None
    bos_total: Optional[float] = None
    eif_total: Optional[float] = None
    rrc_total: Optional[float] = None

    # DT / Pole info
    existing_dt_capacity: Optional[str] = None
    new_transformer_rating: Optional[str] = None
    acb_description: Optional[str] = None
    tapping_pole: Optional[str] = None
    substation_name: Optional[str] = None
    dt_code: Optional[str] = None

    # Materials
    materials: list[Material] = field(default_factory=list)
    major_materials: list[Material] = field(default_factory=list)

    # Feeder details
    feeder_details: list[FeederDetail] = field(default_factory=list)

    # Processing metadata
    status: CaseStatus = CaseStatus.PENDING
    validation_result: Optional[ValidationResult] = None
    correction_details: Optional[str] = None

    # File paths
    scheme_pdf_path: Optional[str] = None
    site_visit_pdf_path: Optional[str] = None
    pm06_excel_path: Optional[str] = None
    output_docx_path: Optional[str] = None
    cost_table_image_path: Optional[str] = None

    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # Extraction diagnostics (not persisted — transient, for Review Tab only)
    extraction_warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Tracker row — mirrors New_Connection_FY26.xlsx columns exactly
# ---------------------------------------------------------------------------


@dataclass
class TrackerRow:
    """One row in the tracker Excel file."""

    sl_no: int
    scheme_no: str
    n_no: str
    district: str
    zone: str
    date_received: str  # dd-mm-yyyy
    date_processed: str  # dd-mm-yyyy
    status: str
    remarks: str
    amount_rs: str  # Indian formatted string
    correction_suggested: str = ""
    correction_details: str = ""