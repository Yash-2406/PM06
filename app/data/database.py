"""SQLite database manager with WAL mode, integrity checks, and migrations.

Zero-config, offline, single-file database for the TPDDL PM06 tool.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

from app.domain.exceptions import DBCorruptionError
from app.infrastructure.logger import get_logger

logger = get_logger(__name__)

CURRENT_SCHEMA_VERSION: int = 1

_SCHEMA_SQL: str = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=FULL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS db_metadata (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cases (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    order_no              TEXT NOT NULL,
    notification_no       TEXT NOT NULL,
    all_notification_nos  TEXT,
    applicant_name        TEXT,
    address               TEXT,
    pin_code              TEXT,
    zone_code             TEXT,
    district_code         TEXT,
    wbs_no                TEXT,
    work_type             TEXT,
    area_type             TEXT,
    capex_year            TEXT,
    estimated_cost        REAL,
    bom_total             REAL,
    bos_total             REAL,
    eif_total             REAL,
    rrc_total             REAL,
    dt_capacity_existing  TEXT,
    dt_code               TEXT,
    tapping_pole          TEXT,
    scope_of_work         TEXT,
    status                TEXT DEFAULT 'Pending',
    remarks               TEXT,
    correction_details    TEXT,
    date_received         TEXT,
    date_processed        TEXT,
    generated_doc_path    TEXT,
    created_at            TEXT DEFAULT (datetime('now','localtime')),
    updated_at            TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS source_files (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id     INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    file_type   TEXT NOT NULL CHECK(file_type IN
                ('SCHEME_PDF','SITE_VISIT_PDF','PM06_EXCEL')),
    file_path   TEXT NOT NULL,
    file_hash   TEXT,
    uploaded_at TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS generated_docs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id       INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    doc_path      TEXT NOT NULL,
    generated_at  TEXT DEFAULT (datetime('now','localtime')),
    engineer_name TEXT
);

CREATE TABLE IF NOT EXISTS audit_log (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id       INTEGER,
    action        TEXT NOT NULL,
    old_value     TEXT,
    new_value     TEXT,
    details       TEXT,
    performed_at  TEXT DEFAULT (datetime('now','localtime')),
    engineer_name TEXT
);

CREATE INDEX IF NOT EXISTS idx_cases_order_no   ON cases(order_no);
CREATE INDEX IF NOT EXISTS idx_cases_notif_no   ON cases(notification_no);
CREATE INDEX IF NOT EXISTS idx_cases_district   ON cases(district_code);
CREATE INDEX IF NOT EXISTS idx_cases_status     ON cases(status);
CREATE INDEX IF NOT EXISTS idx_audit_case_id    ON audit_log(case_id);
"""


class Database:
    """SQLite database connection manager with WAL mode and schema migrations."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    def initialise(self) -> None:
        """Create or open the database, apply schema, run integrity check."""
        db_exists = self._db_path.exists()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

        self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=FULL")
        self._conn.execute("PRAGMA foreign_keys=ON")

        if db_exists:
            self._check_integrity()

        self._apply_schema()
        self._run_migrations()
        logger.info("Database initialised: %s", self._db_path)

    def _check_integrity(self) -> None:
        """Run PRAGMA integrity_check. Raise on corruption."""
        try:
            result = self._conn.execute("PRAGMA integrity_check").fetchone()
            if result[0] != "ok":
                raise DBCorruptionError(
                    f"Database integrity check failed: {result[0]}",
                    user_message="The database file appears to be corrupted. "
                    "A backup has been created and a fresh database will be set up.",
                )
        except sqlite3.DatabaseError as e:
            raise DBCorruptionError(
                f"Cannot read database: {e}",
                user_message="The database file cannot be read. "
                "It may be corrupted. A fresh database will be created.",
            ) from e

    def _apply_schema(self) -> None:
        """Apply the full schema (CREATE IF NOT EXISTS is safe to re-run)."""
        self._conn.executescript(_SCHEMA_SQL)
        # Ensure metadata rows exist
        self._conn.execute(
            "INSERT OR IGNORE INTO db_metadata VALUES ('schema_version', ?)",
            (str(CURRENT_SCHEMA_VERSION),),
        )
        self._conn.execute(
            "INSERT OR IGNORE INTO db_metadata VALUES ('created_at', datetime('now','localtime'))",
        )
        self._conn.commit()

    def _run_migrations(self) -> None:
        """Run schema migrations if schema_version is old."""
        row = self._conn.execute(
            "SELECT value FROM db_metadata WHERE key='schema_version'"
        ).fetchone()
        current_version = int(row["value"]) if row else 0

        if current_version < CURRENT_SCHEMA_VERSION:
            # Future migrations go here as elif blocks
            self._conn.execute(
                "UPDATE db_metadata SET value=? WHERE key='schema_version'",
                (str(CURRENT_SCHEMA_VERSION),),
            )
            self._conn.commit()
            logger.info(
                "Database migrated from v%d to v%d",
                current_version,
                CURRENT_SCHEMA_VERSION,
            )

    @property
    def connection(self) -> sqlite3.Connection:
        """Return the active connection. Raises if not initialised."""
        if self._conn is None:
            raise RuntimeError("Database not initialised. Call initialise() first.")
        return self._conn

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
            logger.info("Database closed")

    def handle_corruption(self) -> Path:
        """Rename corrupt DB file and create fresh database.

        Returns the path to the renamed corrupt file.
        """
        self.close()
        from datetime import datetime

        corrupt_name = self._db_path.with_suffix(
            f".corrupt_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        )
        self._db_path.rename(corrupt_name)
        logger.warning("Corrupt DB renamed to %s", corrupt_name)
        self.initialise()
        return corrupt_name
