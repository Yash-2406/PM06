"""Case repository — CRUD operations for the cases table.

All SQL is parameterised. No raw string interpolation.
Repository pattern: services call this, never raw SQL.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from app.domain.enums import CaseStatus, WorkType
from app.domain.models import Case
from app.infrastructure.logger import get_logger

if TYPE_CHECKING:
    from app.data.database import Database

logger = get_logger(__name__)


class CaseRepository:
    """SQLite CRUD repository for scheme cases."""

    def __init__(self, db: "Database | sqlite3.Connection") -> None:
        # Accept either a Database wrapper or a raw sqlite3.Connection
        from app.data.database import Database as _DB
        if isinstance(db, _DB):
            self._conn = db.connection
        else:
            self._conn = db

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    def create_case(self, case: Case) -> int:
        """Insert a new case and return its id.

        Uses a transaction to ensure atomicity.
        """
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Ensure NOT NULL fields have defaults
        if not case.order_no:
            case.order_no = "UNKNOWN"
        if not case.notification_no:
            case.notification_no = "UNKNOWN"

        def _to_float(val) -> float | None:
            """Convert Decimal/str/int/float to float for SQLite binding."""
            if val is None:
                return None
            return float(val)

        with self._conn:
            cursor = self._conn.execute(
                """INSERT INTO cases (
                    order_no, notification_no, all_notification_nos,
                    applicant_name, address, pin_code,
                    zone_code, district_code, wbs_no,
                    work_type, area_type, capex_year,
                    estimated_cost, bom_total, bos_total, eif_total, rrc_total,
                    dt_capacity_existing, dt_code, tapping_pole,
                    scope_of_work, status, remarks, correction_details,
                    date_received, date_processed, generated_doc_path,
                    created_at, updated_at
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )""",
                (
                    case.order_no,
                    case.notification_no,
                    ",".join(case.all_notification_nos) if case.all_notification_nos else "",
                    case.applicant_name,
                    case.address,
                    case.pin_code,
                    case.zone,
                    case.district,
                    case.wbs_no,
                    case.work_type.value if case.work_type else None,
                    case.area_type,
                    None,  # capex_year
                    _to_float(case.grand_total),
                    _to_float(case.bom_total),
                    _to_float(case.bos_total),
                    _to_float(case.eif_total),
                    _to_float(case.rrc_total),
                    case.existing_dt_capacity,
                    case.dt_code,
                    case.tapping_pole,
                    case.scope_of_work,
                    case.status.value,
                    None,
                    case.correction_details,
                    now[:10],
                    now[:10],
                    case.output_docx_path,
                    now,
                    now,
                ),
            )
            case_id = cursor.lastrowid
            case.id = case_id
        logger.info("Created case id=%d, order_no=%s", case_id, case.order_no)
        return case_id

    # ------------------------------------------------------------------
    # Row → Case conversion
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_case(row: dict) -> Case:
        """Convert a DB row dict into a Case dataclass."""
        wt = None
        if row.get("work_type"):
            try:
                wt = WorkType(row["work_type"])
            except ValueError:
                pass
        status = CaseStatus.PENDING
        if row.get("status"):
            try:
                status = CaseStatus(row["status"])
            except ValueError:
                pass
        created_at = None
        if row.get("created_at"):
            try:
                created_at = datetime.strptime(row["created_at"], "%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError):
                pass
        updated_at = None
        if row.get("updated_at"):
            try:
                updated_at = datetime.strptime(row["updated_at"], "%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError):
                pass
        return Case(
            id=row.get("id"),
            order_no=row.get("order_no"),
            notification_no=row.get("notification_no"),
            applicant_name=row.get("applicant_name"),
            address=row.get("address"),
            pin_code=row.get("pin_code"),
            zone=row.get("zone_code"),
            district=row.get("district_code"),
            wbs_no=row.get("wbs_no"),
            work_type=wt,
            area_type=row.get("area_type"),
            grand_total=row.get("estimated_cost"),
            bom_total=row.get("bom_total"),
            bos_total=row.get("bos_total"),
            eif_total=row.get("eif_total"),
            rrc_total=row.get("rrc_total"),
            existing_dt_capacity=row.get("dt_capacity_existing"),
            dt_code=row.get("dt_code"),
            tapping_pole=row.get("tapping_pole"),
            scope_of_work=row.get("scope_of_work"),
            status=status,
            correction_details=row.get("correction_details"),
            output_docx_path=row.get("generated_doc_path"),
            created_at=created_at,
            updated_at=updated_at,
        )

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get_by_order_no(self, order_no: str) -> Optional[Case]:
        """Find a case by its 8-digit Order Number."""
        cursor = self._conn.execute(
            "SELECT * FROM cases WHERE order_no = ? ORDER BY created_at DESC LIMIT 1",
            (order_no,),
        )
        row = cursor.fetchone()
        return self._row_to_case(dict(row)) if row else None

    def get_by_id(self, case_id: int) -> Optional[Case]:
        """Retrieve a case by its primary key."""
        cursor = self._conn.execute("SELECT * FROM cases WHERE id = ?", (case_id,))
        row = cursor.fetchone()
        return self._row_to_case(dict(row)) if row else None

    def list_all(
        self,
        district: Optional[str] = None,
        zone: Optional[str] = None,
        status: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> list[Case]:
        """List cases with optional filters."""
        query = "SELECT * FROM cases WHERE 1=1"
        params: list = []

        if district:
            query += " AND district_code = ?"
            params.append(district)
        if zone:
            query += " AND zone_code = ?"
            params.append(zone)
        if status:
            query += " AND status = ?"
            params.append(status)
        if date_from:
            query += " AND date_received >= ?"
            params.append(date_from)
        if date_to:
            query += " AND date_received <= ?"
            params.append(date_to)

        query += " ORDER BY created_at DESC"
        cursor = self._conn.execute(query, params)
        return [self._row_to_case(dict(row)) for row in cursor.fetchall()]

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update_status(
        self,
        case_id: int,
        status: CaseStatus,
        remarks: Optional[str] = None,
        correction_details: Optional[str] = None,
    ) -> None:
        """Update case status and optional remarks."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._conn:
            self._conn.execute(
                """UPDATE cases SET
                    status = ?,
                    remarks = COALESCE(?, remarks),
                    correction_details = COALESCE(?, correction_details),
                    updated_at = ?
                WHERE id = ?""",
                (status.value, remarks, correction_details, now, case_id),
            )
        logger.info("Updated case id=%d status=%s", case_id, status.value)

    def update_generated_doc(self, case_id: int, doc_path: str) -> None:
        """Record the generated document path."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._conn:
            self._conn.execute(
                "UPDATE cases SET generated_doc_path = ?, updated_at = ? WHERE id = ?",
                (doc_path, now, case_id),
            )

    def update_case_fields(self, case_id: int, fields: dict) -> None:
        """Update arbitrary fields on a case (for manual overrides)."""
        if not fields:
            return
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        allowed = {
            "applicant_name", "address", "pin_code", "zone_code",
            "district_code", "wbs_no", "work_type", "area_type",
            "estimated_cost", "dt_capacity_existing", "dt_code",
            "tapping_pole", "scope_of_work", "status", "remarks",
            "correction_details", "notification_no",
        }
        safe_fields = {k: v for k, v in fields.items() if k in allowed}
        if not safe_fields:
            return
        safe_fields["updated_at"] = now
        set_clause = ", ".join(f"{k} = ?" for k in safe_fields)
        values = list(safe_fields.values()) + [case_id]
        with self._conn:
            self._conn.execute(
                f"UPDATE cases SET {set_clause} WHERE id = ?", values
            )
        logger.info("Updated fields %s on case id=%d", list(safe_fields.keys()), case_id)

    # ------------------------------------------------------------------
    # Source files
    # ------------------------------------------------------------------

    def add_source_file(
        self, case_id: int, file_type: str, file_path: str, file_hash: str
    ) -> None:
        """Record a source file associated with a case."""
        with self._conn:
            self._conn.execute(
                """INSERT INTO source_files (case_id, file_type, file_path, file_hash)
                   VALUES (?, ?, ?, ?)""",
                (case_id, file_type, file_path, file_hash),
            )

    def add_generated_doc(
        self, case_id: int, doc_path: str, engineer_name: str
    ) -> None:
        """Record a generated document."""
        with self._conn:
            self._conn.execute(
                """INSERT INTO generated_docs (case_id, doc_path, engineer_name)
                   VALUES (?, ?, ?)""",
                (case_id, doc_path, engineer_name),
            )

    # ------------------------------------------------------------------
    # MIS / aggregation
    # ------------------------------------------------------------------

    def count_by_district_status(self) -> list[dict]:
        """Return counts grouped by district and status for MIS report."""
        cursor = self._conn.execute(
            """SELECT district_code, status, COUNT(*) as count
               FROM cases
               GROUP BY district_code, status
               ORDER BY district_code, status"""
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_next_sl_no(self) -> int:
        """Return the next serial number for tracker rows."""
        row = self._conn.execute(
            "SELECT COALESCE(MAX(id), 0) + 1 as next_sl FROM cases"
        ).fetchone()
        return row["next_sl"]

    def count_and_sum_all(self) -> tuple[int, float]:
        """Return (total_case_count, total_estimated_cost) via SQL."""
        row = self._conn.execute(
            "SELECT COUNT(*) as cnt, COALESCE(SUM(estimated_cost), 0) as total FROM cases"
        ).fetchone()
        return int(row["cnt"]), float(row["total"])

    def count_by_status(self) -> dict[str, int]:
        """Return {status_value: count} via SQL aggregation."""
        cursor = self._conn.execute(
            "SELECT COALESCE(status, 'UNKNOWN') as st, COUNT(*) as cnt "
            "FROM cases GROUP BY status"
        )
        return {row["st"]: int(row["cnt"]) for row in cursor.fetchall()}

    def count_by_district(self) -> dict[str, int]:
        """Return {district_code: count} via SQL aggregation."""
        cursor = self._conn.execute(
            "SELECT COALESCE(district_code, 'UNKNOWN') as dt, COUNT(*) as cnt "
            "FROM cases GROUP BY district_code ORDER BY district_code"
        )
        return {row["dt"]: int(row["cnt"]) for row in cursor.fetchall()}

    def count_by_zone(self) -> dict[str, int]:
        """Return {zone_code: count} via SQL aggregation."""
        cursor = self._conn.execute(
            "SELECT COALESCE(zone_code, 'UNKNOWN') as zn, COUNT(*) as cnt "
            "FROM cases GROUP BY zone_code ORDER BY zone_code"
        )
        return {row["zn"]: int(row["cnt"]) for row in cursor.fetchall()}

    def count_by_work_type(self) -> dict[str, int]:
        """Return {work_type: count} via SQL aggregation."""
        cursor = self._conn.execute(
            "SELECT COALESCE(work_type, 'UNKNOWN') as wt, COUNT(*) as cnt "
            "FROM cases GROUP BY work_type ORDER BY work_type"
        )
        return {row["wt"]: int(row["cnt"]) for row in cursor.fetchall()}

    def sum_by_district(self) -> dict[str, float]:
        """Return {district_code: total_estimated_cost} via SQL."""
        cursor = self._conn.execute(
            "SELECT COALESCE(district_code, 'UNKNOWN') as dt, "
            "COALESCE(SUM(estimated_cost), 0) as total "
            "FROM cases GROUP BY district_code ORDER BY district_code"
        )
        return {row["dt"]: float(row["total"]) for row in cursor.fetchall()}

    def sum_by_status(self) -> dict[str, float]:
        """Return {status: total_estimated_cost} via SQL."""
        cursor = self._conn.execute(
            "SELECT COALESCE(status, 'UNKNOWN') as st, "
            "COALESCE(SUM(estimated_cost), 0) as total "
            "FROM cases GROUP BY status"
        )
        return {row["st"]: float(row["total"]) for row in cursor.fetchall()}

    def count_by_month(self) -> list[dict]:
        """Return [{month: 'YYYY-MM', count: N, amount: X}] for trend."""
        cursor = self._conn.execute(
            "SELECT COALESCE(strftime('%Y-%m', created_at), 'UNKNOWN') as month, "
            "COUNT(*) as cnt, COALESCE(SUM(estimated_cost), 0) as total "
            "FROM cases GROUP BY month ORDER BY month"
        )
        return [dict(row) for row in cursor.fetchall()]
