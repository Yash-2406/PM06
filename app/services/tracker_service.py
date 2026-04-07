"""TrackerService — CRUD on both SQLite DB and tracker Excel.

Handles the rejection / resubmission workflow (Part 11):
  - On rejection, status → REJECTED, correction_details saved
  - On resubmission, existing row updated (same order_no), audit trail kept
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from app.data.case_repository import CaseRepository
from app.data.database import Database
from app.data.excel_repository import ExcelRepository
from app.domain.enums import CaseStatus
from app.domain.models import Case, TrackerRow
from app.infrastructure.audit_logger import AuditLogger
from app.infrastructure.config_manager import ConfigManager
from app.infrastructure.formatting import format_indian_amount
from app.services.export_service import case_to_tracker_row

logger = logging.getLogger(__name__)


class TrackerService:
    """Manages case lifecycle and tracker synchronisation."""

    def __init__(
        self,
        db: Database | None = None,
        config: ConfigManager | None = None,
    ) -> None:
        self._config = config or ConfigManager()
        self._db = db or Database(self._config.db_path)
        self._repo = CaseRepository(self._db)
        self._excel_repo = ExcelRepository(self._config.tracker_path)
        self._audit = AuditLogger(self._db)

    # ── Read ────────────────────────────────────────────────────

    def get_case(self, case_id: int) -> Optional[Case]:
        """Get a case by its DB id."""
        return self._repo.get_by_id(case_id)

    def get_case_by_order_no(self, order_no: str) -> Optional[Case]:
        """Get a case by order number (for duplicate detection)."""
        return self._repo.get_by_order_no(order_no)

    def list_cases(
        self,
        district: Optional[str] = None,
        zone: Optional[str] = None,
        status: Optional[CaseStatus] = None,
    ) -> List[Case]:
        """Return filtered list of cases."""
        return self._repo.list_all(district=district, zone=zone, status=status)

    # ── Status transitions ──────────────────────────────────────

    def approve_case(self, case_id: int, remarks: str = "") -> None:
        """Mark a case as approved and sync to tracker."""
        self._repo.update_status(case_id, CaseStatus.APPROVED)
        self._audit.log(action="APPROVED", case_id=case_id, details=remarks or "Case approved")
        self._sync_to_tracker(case_id)
        logger.info("Case %d approved", case_id)

    def reject_case(
        self, case_id: int, correction_details: str, remarks: str = ""
    ) -> None:
        """Mark a case as rejected with correction details."""
        self._repo.update_status(case_id, CaseStatus.REJECTED)
        self._repo.update_case_fields(
            case_id, {"correction_details": correction_details}
        )
        self._audit.log(
            action="REJECTED",
            case_id=case_id,
            details=f"Correction: {correction_details}. {remarks}".strip(),
        )
        self._sync_to_tracker(case_id)
        logger.info("Case %d rejected: %s", case_id, correction_details)

    def resubmit_case(self, case_id: int, remarks: str = "") -> None:
        """Move a rejected case back to pending for reprocessing."""
        self._repo.update_status(case_id, CaseStatus.PENDING)
        self._repo.update_case_fields(case_id, {"correction_details": None})
        self._audit.log(action="RESUBMITTED", case_id=case_id, details=remarks or "Resubmitted for correction")
        logger.info("Case %d resubmitted", case_id)

    # ── Tracker sync ────────────────────────────────────────────

    def update_tracker(self, tracker_file: str | Path | None = None) -> None:
        """Full sync: write ALL cases to the tracker Excel.

        Uses batch_write_rows to open/save the file only once instead
        of once per case.
        """
        if tracker_file:
            self._excel_repo = ExcelRepository(Path(tracker_file))  # noqa: E501

        cases = self._repo.list_all()
        rows = [
            case_to_tracker_row(case, sl_no=idx)
            for idx, case in enumerate(cases, start=1)
        ]
        self._excel_repo.batch_write_rows(rows)
        logger.info("Tracker synced with %d cases", len(cases))

    def _sync_to_tracker(self, case_id: int) -> None:
        """Sync a single case to the tracker Excel."""
        case = self._repo.get_by_id(case_id)
        if case is None:
            logger.warning("Case %d not found for tracker sync", case_id)
            return
        sl_no = self._excel_repo.get_max_sl_no() + 1
        row = case_to_tracker_row(case, sl_no=sl_no)
        self._excel_repo.append_or_update_row(row)

    # ── MIS data ────────────────────────────────────────────────

    def get_mis_summary(self) -> dict:
        """Return counts by district and status for the MIS tab."""
        return self._repo.count_by_district_status()