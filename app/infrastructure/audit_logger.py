"""Audit logger — writes action records to the SQLite audit_log table.

Every user action and system event is recorded for traceability.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Optional

from app.infrastructure.logger import get_logger

logger = get_logger(__name__)


class AuditLogger:
    """Writes to the audit_log table in the SQLite database."""

    def __init__(self, db) -> None:
        """Accept either a Database object, a db path string, or a Path."""
        from app.data.database import Database
        if isinstance(db, Database):
            self._db = db
            self._db_path = None
        else:
            self._db = None
            self._db_path = str(db)

    def _get_connection(self) -> sqlite3.Connection:
        if self._db is not None:
            return self._db.connection
        return sqlite3.connect(self._db_path)

    def log(
        self,
        action: str,
        case_id: Optional[int] = None,
        old_value: Optional[str] = None,
        new_value: Optional[str] = None,
        details: Optional[str] = None,
        engineer_name: Optional[str] = None,
    ) -> None:
        """Record one audit entry.

        Args:
            action: e.g. 'GENERATE', 'MANUAL_OVERRIDE', 'STATUS_CHANGE'
            case_id: FK to cases table (optional for system-level events)
            old_value: Previous value before change
            new_value: New value after change
            details: Free-text description
            engineer_name: Name of the engineer performing the action
        """
        try:
            conn = self._get_connection()
            conn.execute(
                """INSERT INTO audit_log
                   (case_id, action, old_value, new_value, details,
                    performed_at, engineer_name)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    case_id,
                    action,
                    old_value,
                    new_value,
                    details,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    engineer_name,
                ),
            )
            conn.commit()
            if self._db is None:
                conn.close()
            logger.debug("Audit log: %s (case=%s)", action, case_id)
        except sqlite3.Error as e:
            logger.error("Failed to write audit log: %s", e)

    def get_history(self, case_id: int) -> list[dict]:
        """Retrieve full audit trail for a case."""
        try:
            conn = sqlite3.connect(self._db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM audit_log WHERE case_id = ? ORDER BY performed_at",
                (case_id,),
            )
            rows = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return rows
        except sqlite3.Error as e:
            logger.error("Failed to read audit log: %s", e)
            return []
