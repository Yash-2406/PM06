"""Database edge case tests — integrity, corruption, migrations, close."""

from __future__ import annotations

import sqlite3
import pytest
from pathlib import Path

from app.data.database import Database, CURRENT_SCHEMA_VERSION
from app.domain.exceptions import DBCorruptionError


class TestDatabaseIntegrity:
    def test_integrity_check_passes(self, db):
        # This is confirmed by db fixture succeeding, but explicit test:
        result = db.connection.execute("PRAGMA integrity_check").fetchone()
        assert result[0] == "ok"

    def test_foreign_keys_enabled(self, db):
        result = db.connection.execute("PRAGMA foreign_keys").fetchone()
        assert result[0] == 1


class TestDatabaseConnection:
    def test_connection_property_before_init(self, tmp_path):
        database = Database(tmp_path / "test.db")
        with pytest.raises(RuntimeError, match="not initialised"):
            _ = database.connection

    def test_close_and_access(self, tmp_path):
        database = Database(tmp_path / "test.db")
        database.initialise()
        database.close()
        # After close, connection should be None
        assert database._conn is None

    def test_double_close(self, tmp_path):
        database = Database(tmp_path / "test.db")
        database.initialise()
        database.close()
        database.close()  # Should not raise

    def test_reopen_after_close(self, tmp_path):
        database = Database(tmp_path / "test.db")
        database.initialise()
        database.close()
        database.initialise()
        result = database.connection.execute("SELECT 1").fetchone()
        assert result[0] == 1


class TestDatabaseSchema:
    def test_schema_version_stored(self, db):
        row = db.connection.execute(
            "SELECT value FROM db_metadata WHERE key='schema_version'"
        ).fetchone()
        assert int(row[0]) == CURRENT_SCHEMA_VERSION

    def test_created_at_stored(self, db):
        row = db.connection.execute(
            "SELECT value FROM db_metadata WHERE key='created_at'"
        ).fetchone()
        assert row[0] is not None

    def test_all_indexes_exist(self, db):
        cursor = db.connection.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'"
        )
        indexes = {row[0] for row in cursor.fetchall()}
        assert "idx_cases_order_no" in indexes
        assert "idx_cases_status" in indexes
        assert "idx_cases_district" in indexes
        assert "idx_audit_case_id" in indexes


class TestDatabaseCorruptionHandling:
    def test_handle_corruption_renames_and_reinitialises(self, tmp_path):
        db_path = tmp_path / "test.db"
        database = Database(db_path)
        database.initialise()
        database.close()

        # Reopen and trigger corruption handling
        database2 = Database(db_path)
        corrupt_path = database2.handle_corruption()
        assert corrupt_path.exists()
        assert ".corrupt_" in corrupt_path.name
        # handle_corruption re-initialises, so db_path exists again
        assert db_path.exists()

    def test_corrupt_db_raises_on_pragma(self, tmp_path):
        """A truly corrupt file causes sqlite3.DatabaseError during initialise."""
        db_path = tmp_path / "corrupt.db"
        db_path.write_bytes(b"NOT A DATABASE FILE AT ALL")
        database = Database(db_path)
        with pytest.raises(sqlite3.DatabaseError):
            database.initialise()


class TestDatabaseMigrations:
    def test_migration_idempotent(self, tmp_path):
        """Running initialise twice should not fail."""
        db_path = tmp_path / "test.db"
        db1 = Database(db_path)
        db1.initialise()
        db1.close()

        db2 = Database(db_path)
        db2.initialise()  # should not raise
        row = db2.connection.execute(
            "SELECT value FROM db_metadata WHERE key='schema_version'"
        ).fetchone()
        assert int(row[0]) == CURRENT_SCHEMA_VERSION
        db2.close()

    def test_old_schema_version_triggers_migration(self, tmp_path):
        """Manually set schema_version=0, then re-init should migrate to current."""
        db_path = tmp_path / "test.db"
        db = Database(db_path)
        db.initialise()
        db.connection.execute(
            "UPDATE db_metadata SET value='0' WHERE key='schema_version'"
        )
        db.connection.commit()
        db.close()

        db2 = Database(db_path)
        db2.initialise()
        row = db2.connection.execute(
            "SELECT value FROM db_metadata WHERE key='schema_version'"
        ).fetchone()
        assert int(row[0]) == CURRENT_SCHEMA_VERSION
        db2.close()


class TestDatabaseRowFactory:
    def test_row_factory_dict_access(self, db):
        db.connection.execute(
            "INSERT INTO cases (order_no, notification_no) VALUES (?, ?)",
            ("TEST001", "NC001"),
        )
        db.connection.commit()
        row = db.connection.execute("SELECT * FROM cases LIMIT 1").fetchone()
        assert row["order_no"] == "TEST001"
        assert row["notification_no"] == "NC001"
