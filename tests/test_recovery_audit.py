"""Tests for RecoveryManager and AuditLogger."""

from __future__ import annotations

import json
import pytest
from pathlib import Path

from app.data.database import Database
from app.infrastructure.audit_logger import AuditLogger
from app.infrastructure.recovery_manager import RecoveryManager


# ══════════════════════════════════════════════════════════════════
# RecoveryManager
# ══════════════════════════════════════════════════════════════════


class TestRecoveryManagerState:
    def test_initially_empty(self, tmp_path):
        rm = RecoveryManager(tmp_path / "recovery")
        assert rm._current_state == {}

    def test_update_and_clear(self, tmp_path):
        rm = RecoveryManager(tmp_path / "recovery")
        rm.update_state("file", "test.pdf")
        rm.update_state("step", 3)
        assert rm._current_state["file"] == "test.pdf"
        assert rm._current_state["step"] == 3
        rm.clear_state()
        assert rm._current_state == {}


class TestRecoveryManagerPersistence:
    def test_save_on_exit(self, tmp_path):
        rec_dir = tmp_path / "recovery"
        rm = RecoveryManager(rec_dir)
        rm.update_state("key", "value")
        rm._save_on_exit()
        files = list(rec_dir.glob("recovery_*.json"))
        assert len(files) == 1
        data = json.loads(files[0].read_text(encoding="utf-8"))
        assert data["key"] == "value"

    def test_save_on_exit_empty_state_noop(self, tmp_path):
        rec_dir = tmp_path / "recovery"
        rm = RecoveryManager(rec_dir)
        rm._save_on_exit()
        assert not rec_dir.exists() or not list(rec_dir.glob("recovery_*.json"))

    def test_has_recovery_data_false(self, tmp_path):
        rm = RecoveryManager(tmp_path / "recovery")
        assert rm.has_recovery_data() is False

    def test_has_recovery_data_true(self, tmp_path):
        rec_dir = tmp_path / "recovery"
        rec_dir.mkdir()
        (rec_dir / "recovery_20260407_120000.json").write_text("{}", encoding="utf-8")
        rm = RecoveryManager(rec_dir)
        assert rm.has_recovery_data() is True

    def test_get_latest_recovery(self, tmp_path):
        rec_dir = tmp_path / "recovery"
        rec_dir.mkdir()
        (rec_dir / "recovery_20260401_100000.json").write_text('{"old": 1}', encoding="utf-8")
        (rec_dir / "recovery_20260407_120000.json").write_text('{"new": 2}', encoding="utf-8")
        rm = RecoveryManager(rec_dir)
        data = rm.get_latest_recovery()
        assert data is not None
        assert "new" in data

    def test_get_latest_recovery_empty(self, tmp_path):
        rm = RecoveryManager(tmp_path / "recovery")
        assert rm.get_latest_recovery() is None

    def test_get_latest_recovery_corrupt_json(self, tmp_path):
        rec_dir = tmp_path / "recovery"
        rec_dir.mkdir()
        (rec_dir / "recovery_20260407_120000.json").write_text("NOT JSON", encoding="utf-8")
        rm = RecoveryManager(rec_dir)
        assert rm.get_latest_recovery() is None


class TestRecoveryManagerClearFiles:
    def test_clears_all_files(self, tmp_path):
        rec_dir = tmp_path / "recovery"
        rec_dir.mkdir()
        (rec_dir / "recovery_20260401_100000.json").write_text("{}", encoding="utf-8")
        (rec_dir / "recovery_20260407_120000.json").write_text("{}", encoding="utf-8")
        rm = RecoveryManager(rec_dir)
        rm.clear_recovery_files()
        assert list(rec_dir.glob("recovery_*.json")) == []

    def test_clear_nonexistent_dir_noop(self, tmp_path):
        rm = RecoveryManager(tmp_path / "no_such_dir")
        rm.clear_recovery_files()  # Should not raise


class TestRecoveryManagerSerialisable:
    def test_path_becomes_string(self, tmp_path):
        result = RecoveryManager._make_serialisable({"p": Path("/test/path")})
        assert result["p"] == str(Path("/test/path"))

    def test_nested_dict_list(self, tmp_path):
        data = {"items": [{"p": Path("/a")}, {"val": 42}]}
        result = RecoveryManager._make_serialisable(data)
        assert result["items"][0]["p"] == str(Path("/a"))
        assert result["items"][1]["val"] == 42


class TestRecoveryRegisterAtexit:
    def test_register_once(self, tmp_path):
        rm = RecoveryManager(tmp_path / "recovery")
        rm.register_atexit()
        assert rm._registered is True
        rm.register_atexit()  # idempotent
        assert rm._registered is True


# ══════════════════════════════════════════════════════════════════
# AuditLogger
# ══════════════════════════════════════════════════════════════════


class TestAuditLoggerWithDB:
    def test_log_and_retrieve(self, db):
        al = AuditLogger(db)
        al.log(action="TEST_ACTION", case_id=None, details="test detail")
        # Verify via raw query
        row = db.connection.execute(
            "SELECT * FROM audit_log WHERE action='TEST_ACTION'"
        ).fetchone()
        assert row is not None
        assert dict(row)["details"] == "test detail"

    def test_log_with_case_id(self, db):
        from app.data.case_repository import CaseRepository
        from app.domain.models import Case
        from app.domain.enums import CaseStatus, WorkType
        repo = CaseRepository(db)
        case_id = repo.create_case(Case(
            order_no="60001001", notification_no="1234567890",
            status=CaseStatus.PENDING,
        ))
        al = AuditLogger(db)
        al.log(action="GENERATED", case_id=case_id, details="Summary generated")
        row = db.connection.execute(
            "SELECT * FROM audit_log WHERE case_id=?", (case_id,)
        ).fetchone()
        assert dict(row)["action"] == "GENERATED"

    def test_log_with_old_new_values(self, db):
        al = AuditLogger(db)
        al.log(
            action="STATUS_CHANGE",
            old_value="Pending",
            new_value="Approved",
            engineer_name="Test Engineer",
        )
        row = db.connection.execute(
            "SELECT * FROM audit_log WHERE action='STATUS_CHANGE'"
        ).fetchone()
        assert dict(row)["old_value"] == "Pending"
        assert dict(row)["new_value"] == "Approved"
        assert dict(row)["engineer_name"] == "Test Engineer"


class TestAuditLoggerWithPath:
    def test_log_via_path(self, db, tmp_path):
        """AuditLogger constructed with a path string opens its own connection."""
        # Use the actual DB file for this test
        al = AuditLogger(db._db_path)
        al.log(action="PATH_TEST", details="via path")
        # Verify through the db connection
        row = db.connection.execute(
            "SELECT * FROM audit_log WHERE action='PATH_TEST'"
        ).fetchone()
        assert row is not None

    def test_get_history_via_path(self, db):
        """get_history opens a new connection using the stored path."""
        from app.data.case_repository import CaseRepository
        from app.domain.models import Case
        from app.domain.enums import CaseStatus
        repo = CaseRepository(db)
        case_id = repo.create_case(Case(
            order_no="60001001", notification_no="1234567890",
            status=CaseStatus.PENDING,
        ))
        al_write = AuditLogger(db)
        al_write.log(action="ACT1", case_id=case_id, details="first")
        al_write.log(action="ACT2", case_id=case_id, details="second")

        al_read = AuditLogger(db._db_path)
        history = al_read.get_history(case_id)
        assert len(history) == 2
        assert history[0]["action"] == "ACT1"
        assert history[1]["action"] == "ACT2"

    def test_get_history_empty(self, db):
        al = AuditLogger(db._db_path)
        history = al.get_history(9999)
        assert history == []
