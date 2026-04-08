"""ValidatorService — FR-02 validation checks.

8 blocking checks + 6 warning checks + 3 cross-field checks.
Returns a ValidationResult with individual ValidationCheck items.
"""

from __future__ import annotations

import logging
import re
from typing import List, Optional

from app.domain.constants import (
    COST_LOWER_BOUND,
    COST_UPPER_BOUND,
    RE_DELHI_PIN,
    RE_NC_NOTIF,
    VALID_CATEGORIES,
    ZONE_DISTRICT_MAP,
)
from app.domain.enums import WorkType
from app.domain.models import Case, ValidationCheck, ValidationResult
from app.infrastructure.config_manager import ConfigManager

logger = logging.getLogger(__name__)

# Work-type-specific cost bounds (Rs)
_COST_BOUNDS: dict[WorkType, tuple[float, float]] = {
    WorkType.LT_STANDARD: (1_000, 10_000_000),
    WorkType.LT_HT_POLE: (5_000, 15_000_000),
    WorkType.DT_AUGMENTATION: (50_000, 50_000_000),
    WorkType.ABC_WIRING: (1_000, 10_000_000),
}


class ValidatorService:
    """Run all validation rules on a Case and return a ValidationResult."""

    def __init__(self, config: Optional[ConfigManager] = None) -> None:
        self._config = config

    def validate(self, case: Case) -> ValidationResult:
        """Execute all checks. Returns ValidationResult."""
        checks: List[ValidationCheck] = []

        # ── BLOCKING checks ─────────────────────────────────────
        checks.append(self._check_order_no(case))
        checks.append(self._check_notification_no(case))
        checks.append(self._check_applicant_name(case))
        checks.append(self._check_address(case))
        checks.append(self._check_zone(case))
        checks.append(self._check_grand_total(case))
        checks.append(self._check_load_applied(case))
        checks.append(self._check_work_type(case))

        # ── WARNING checks ──────────────────────────────────────
        checks.append(self._check_pin_code(case))
        checks.append(self._check_category(case))
        checks.append(self._check_materials(case))
        checks.append(self._check_scope(case))
        checks.append(self._check_cost_range(case))
        checks.append(self._check_feeder_details(case))

        # ── CROSS-FIELD checks (warnings) ───────────────────────
        checks.append(self._check_zone_district_match(case))
        checks.append(self._check_dt_upgrade(case))
        checks.append(self._check_district_present(case))

        result = ValidationResult(checks=checks)
        logger.info(
            "Validation: %d passed, %d failed (blocked=%s, warnings=%s)",
            sum(1 for c in checks if c.passed),
            sum(1 for c in checks if not c.passed),
            result.is_blocked,
            result.has_warnings,
        )
        return result

    # ── BLOCKING ────────────────────────────────────────────────

    @staticmethod
    def _check_order_no(case: Case) -> ValidationCheck:
        passed = bool(case.order_no and case.order_no.strip())
        return ValidationCheck(
            field="order_no",
            rule="Order No must be present",
            passed=passed,
            message="" if passed else "Order No is missing",
            is_blocking=True,
        )

    @staticmethod
    def _check_notification_no(case: Case) -> ValidationCheck:
        val = case.notification_no or ""
        # Safety: coerce list to first element if needed
        if isinstance(val, list):
            val = val[0] if val else ""
        val = val.strip()
        # Accept either N/C prefixed format or bare 10-digit number
        # (extractors store the digits only, without the N/C prefix)
        if val:
            passed = (
                bool(RE_NC_NOTIF.search(val))
                or bool(re.match(r'^\d{10}$', val))
                or bool(re.search(r'\d{10}', val))
            )
        else:
            passed = False
        return ValidationCheck(
            field="notification_no",
            rule="Notification No must be a 10-digit number",
            passed=passed,
            message="" if passed else f"Invalid or missing Notification No: '{val}'",
            is_blocking=True,
        )

    @staticmethod
    def _check_applicant_name(case: Case) -> ValidationCheck:
        passed = bool(case.applicant_name and len(case.applicant_name.strip()) >= 2)
        return ValidationCheck(
            field="applicant_name",
            rule="Applicant name must be at least 2 characters",
            passed=passed,
            message="" if passed else "Applicant name is missing or too short",
            is_blocking=True,
        )

    @staticmethod
    def _check_address(case: Case) -> ValidationCheck:
        passed = bool(case.address and len(case.address.strip()) >= 5)
        return ValidationCheck(
            field="address",
            rule="Address must be at least 5 characters",
            passed=passed,
            message="" if passed else "Address is missing or too short",
            is_blocking=True,
        )

    @staticmethod
    def _check_zone(case: Case) -> ValidationCheck:
        passed = bool(case.zone and case.zone.strip())
        return ValidationCheck(
            field="zone",
            rule="Zone must be present",
            passed=passed,
            message="" if passed else "Zone is missing",
            is_blocking=True,
        )

    @staticmethod
    def _check_grand_total(case: Case) -> ValidationCheck:
        passed = case.grand_total is not None and case.grand_total > 0
        return ValidationCheck(
            field="grand_total",
            rule="Grand Total must be a positive number",
            passed=passed,
            message="" if passed else "Grand Total is missing or zero",
            is_blocking=True,
        )

    @staticmethod
    def _check_load_applied(case: Case) -> ValidationCheck:
        passed = bool(case.load_applied and case.load_applied.strip())
        return ValidationCheck(
            field="load_applied",
            rule="Load Applied must be present",
            passed=passed,
            message="" if passed else "Load Applied is missing",
            is_blocking=True,
        )

    @staticmethod
    def _check_work_type(case: Case) -> ValidationCheck:
        passed = case.work_type is not None
        return ValidationCheck(
            field="work_type",
            rule="Work type must be detected or set",
            passed=passed,
            message="" if passed else "Work type could not be determined",
            is_blocking=True,
        )

    # ── WARNING ─────────────────────────────────────────────────

    @staticmethod
    def _check_pin_code(case: Case) -> ValidationCheck:
        pin = case.pin_code or ""
        passed = bool(RE_DELHI_PIN.match(pin))
        return ValidationCheck(
            field="pin_code",
            rule="PIN code should be a valid Delhi PIN (110xxx)",
            passed=passed,
            message="" if passed else f"PIN code looks invalid: '{pin}'",
            is_blocking=False,
        )

    @staticmethod
    def _check_category(case: Case) -> ValidationCheck:
        cat = (case.category or "").upper().strip()
        passed = cat in VALID_CATEGORIES
        return ValidationCheck(
            field="category",
            rule=f"Category should be one of {VALID_CATEGORIES}",
            passed=passed,
            message="" if passed else f"Unexpected category: '{case.category}'",
            is_blocking=False,
        )

    @staticmethod
    def _check_materials(case: Case) -> ValidationCheck:
        mats = case.materials or []
        passed = len(mats) > 0
        return ValidationCheck(
            field="materials",
            rule="At least one material should be extracted",
            passed=passed,
            message="" if passed else "No materials found — verify scheme PDF",
            is_blocking=False,
        )

    @staticmethod
    def _check_scope(case: Case) -> ValidationCheck:
        passed = bool(case.scope_of_work and len(case.scope_of_work.strip()) >= 10)
        return ValidationCheck(
            field="scope_of_work",
            rule="Scope of work should be at least 10 characters",
            passed=passed,
            message="" if passed else "Scope of work is missing or too short",
            is_blocking=False,
        )

    @staticmethod
    def _check_cost_range(case: Case) -> ValidationCheck:
        gt = case.grand_total
        if gt is None:
            return ValidationCheck(
                field="grand_total_range",
                rule="Grand Total should be within reasonable range",
                passed=True,
                message="",
                is_blocking=False,
            )
        if gt < 0:
            return ValidationCheck(
                field="grand_total_range",
                rule="Grand Total must not be negative",
                passed=False,
                message=f"Grand Total is negative (₹{gt:,.2f})",
                is_blocking=True,
            )
        # Use work-type-specific bounds when available
        lo, hi = COST_LOWER_BOUND, COST_UPPER_BOUND
        if case.work_type and case.work_type in _COST_BOUNDS:
            lo, hi = _COST_BOUNDS[case.work_type]
        passed = lo <= gt <= hi
        return ValidationCheck(
            field="grand_total_range",
            rule=f"Grand Total should be between ₹{lo:,.0f} and ₹{hi:,.0f}",
            passed=passed,
            message="" if passed else (
                f"Grand Total ₹{gt:,.2f} looks unusual for work type "
                f"{case.work_type.display_name if case.work_type else 'unknown'}"
            ),
            is_blocking=False,
        )

    @staticmethod
    def _check_feeder_details(case: Case) -> ValidationCheck:
        feeders = case.feeder_details or []
        passed = len(feeders) > 0
        return ValidationCheck(
            field="feeder_details",
            rule="At least one feeder detail should be present",
            passed=passed,
            message="" if passed else "No feeder details found — check PM06 Excel",
            is_blocking=False,
        )

    # ── CROSS-FIELD checks ──────────────────────────────────────

    @staticmethod
    def _check_zone_district_match(case: Case) -> ValidationCheck:
        """Verify that the zone code maps to the stated district."""
        zone = case.zone or ""
        district = case.district or ""
        if not zone or not district:
            return ValidationCheck(
                field="zone_district",
                rule="Zone should match district",
                passed=True,
                message="",
                is_blocking=False,
            )
        # ZONE_DISTRICT_MAP: {district_name: [zone_int, ...], ...}
        # e.g. "BDL": [507, 516, 572] means zone 572 belongs to district BDL
        matched = False
        try:
            zone_int = int(zone)
            for dist_name, zone_list in ZONE_DISTRICT_MAP.items():
                if zone_int in zone_list:
                    # Found which district this zone belongs to
                    if district == dist_name:
                        matched = True
                    break
        except ValueError:
            # Non-numeric zone (e.g. "CVL") — check as district key
            if zone in ZONE_DISTRICT_MAP:
                matched = (zone == district)
            else:
                matched = True  # Unknown format, skip check
        return ValidationCheck(
            field="zone_district",
            rule="Zone must map to stated district",
            passed=matched,
            message="" if matched else (
                f"Zone '{zone}' may not belong to district '{district}' — please verify"
            ),
            is_blocking=False,
        )

    @staticmethod
    def _check_dt_upgrade(case: Case) -> ValidationCheck:
        """For DT_AUGMENTATION, new transformer must be larger than existing."""
        if case.work_type != WorkType.DT_AUGMENTATION:
            return ValidationCheck(
                field="dt_upgrade",
                rule="DT upgrade check (DT_AUGMENTATION only)",
                passed=True,
                message="",
                is_blocking=False,
            )
        existing = case.existing_dt_capacity or ""
        new = case.new_transformer_rating or ""
        if not existing or not new:
            return ValidationCheck(
                field="dt_upgrade",
                rule="Both existing and new DT capacity required for DT Augmentation",
                passed=False,
                message="Missing existing or new DT capacity for DT Augmentation",
                is_blocking=False,
            )
        # Parse KVA values
        existing_kva = 0
        new_kva = 0
        m_e = re.search(r"(\d+)\s*[kK][vV][aA]", existing)
        m_n = re.search(r"(\d+)\s*[kK][vV][aA]", new)
        if m_e:
            existing_kva = int(m_e.group(1))
        if m_n:
            new_kva = int(m_n.group(1))
        if existing_kva == 0 or new_kva == 0:
            return ValidationCheck(
                field="dt_upgrade",
                rule="DT capacity values must be parseable",
                passed=False,
                message=f"Cannot parse KVA from existing='{existing}' / new='{new}'",
                is_blocking=False,
            )
        passed = new_kva > existing_kva
        return ValidationCheck(
            field="dt_upgrade",
            rule="New DT rating must exceed existing capacity",
            passed=passed,
            message="" if passed else (
                f"DT downgrade detected: {existing_kva} KVA → {new_kva} KVA"
            ),
            is_blocking=False,
        )

    @staticmethod
    def _check_district_present(case: Case) -> ValidationCheck:
        """District should be present when zone is present."""
        if not case.zone:
            return ValidationCheck(
                field="district",
                rule="District should be filled when zone is present",
                passed=True,
                message="",
                is_blocking=False,
            )
        passed = bool(case.district and case.district.strip())
        return ValidationCheck(
            field="district_from_zone",
            rule="District should be auto-resolved from zone",
            passed=passed,
            message="" if passed else (
                f"Zone '{case.zone}' set but district is empty — check zone mapping"
            ),
            is_blocking=False,
        )