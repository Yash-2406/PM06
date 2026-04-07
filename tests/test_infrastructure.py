"""Infrastructure tests — file_utils, text_utils, formatting, audit, backup, recovery."""

from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from app.domain.enums import FileType
from app.infrastructure.file_utils import (
    atomic_write_bytes,
    compute_file_hash,
    ensure_directory,
    validate_file_type,
)
from app.infrastructure.formatting import (
    format_indian_amount,
    get_capex_year,
    parse_indian_amount,
)
from app.infrastructure.text_utils import (
    clean_scope_text,
    normalise_dt_capacity,
    normalise_label,
    strip_pdf_headers,
)


# ── file_utils ──────────────────────────────────────────────────


class TestValidateFileTypeFull:
    def test_valid_pdf_magic(self, tmp_path):
        f = tmp_path / "test.pdf"
        f.write_bytes(b"%PDF-1.7 content here")
        assert validate_file_type(f, FileType.SCHEME_PDF) is True

    def test_invalid_pdf_magic(self, tmp_path):
        f = tmp_path / "test.pdf"
        f.write_bytes(b"NOT_PDF content")
        assert validate_file_type(f, FileType.SCHEME_PDF) is False

    def test_valid_xlsx_magic(self, tmp_path):
        f = tmp_path / "test.xlsx"
        f.write_bytes(b"PK\x03\x04 excel zip contents")
        assert validate_file_type(f, FileType.PM06_EXCEL) is True

    def test_site_visit_uses_pdf_magic(self, tmp_path):
        f = tmp_path / "sv.pdf"
        f.write_bytes(b"%PDF-1.4 site visit")
        assert validate_file_type(f, FileType.SITE_VISIT_PDF) is True

    def test_string_type_pdf(self, tmp_path):
        f = tmp_path / "test.pdf"
        f.write_bytes(b"%PDF-1.4 content")
        assert validate_file_type(str(f), "pdf") is True

    def test_string_type_xlsx(self, tmp_path):
        f = tmp_path / "test.xlsx"
        f.write_bytes(b"PK\x03\x04 content")
        assert validate_file_type(str(f), "xlsx") is True

    def test_unknown_string_type_returns_true(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_bytes(b"text content")
        assert validate_file_type(str(f), "txt") is True

    def test_file_not_found_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            validate_file_type(tmp_path / "nope.pdf", "pdf")


class TestAtomicWriteBytes:
    def test_writes_content(self, tmp_path):
        target = tmp_path / "out.bin"
        atomic_write_bytes(target, b"hello world")
        assert target.read_bytes() == b"hello world"

    def test_creates_parent_dirs(self, tmp_path):
        target = tmp_path / "sub" / "deep" / "file.bin"
        atomic_write_bytes(target, b"nested")
        assert target.read_bytes() == b"nested"

    def test_overwrites_existing(self, tmp_path):
        target = tmp_path / "exists.bin"
        target.write_bytes(b"old")
        atomic_write_bytes(target, b"new")
        assert target.read_bytes() == b"new"


class TestComputeFileHashFull:
    def test_sha256_deterministic(self, tmp_path):
        f = tmp_path / "test.bin"
        f.write_bytes(b"deterministic")
        h1 = compute_file_hash(f)
        h2 = compute_file_hash(f)
        assert h1 == h2
        assert len(h1) == 64  # SHA-256 hex length

    def test_different_content_different_hash(self, tmp_path):
        f1 = tmp_path / "a.bin"
        f2 = tmp_path / "b.bin"
        f1.write_bytes(b"content_a")
        f2.write_bytes(b"content_b")
        assert compute_file_hash(f1) != compute_file_hash(f2)

    def test_empty_file(self, tmp_path):
        f = tmp_path / "empty.bin"
        f.write_bytes(b"")
        h = compute_file_hash(f)
        assert isinstance(h, str) and len(h) == 64


class TestEnsureDirectory:
    def test_creates_dir(self, tmp_path):
        d = tmp_path / "newdir" / "sub"
        result = ensure_directory(d)
        assert result.exists()
        assert result.is_dir()

    def test_existing_dir_ok(self, tmp_path):
        result = ensure_directory(tmp_path)
        assert result == tmp_path


# ── text_utils ──────────────────────────────────────────────────


class TestStripPdfHeadersFull:
    def test_removes_page_order_header(self):
        text = "Page No.: 1 Order No.: 60038419\nBody text"
        result = strip_pdf_headers(text)
        assert "Page No." not in result
        assert "Body text" in result

    def test_removes_tata_power_logo(self):
        text = "TATA POWER-DDL\nBody text"
        result = strip_pdf_headers(text)
        assert "TATA POWER" not in result

    def test_preserves_normal_content(self):
        text = "Normal content without headers"
        assert strip_pdf_headers(text) == text

    def test_multiple_headers_stripped(self):
        text = (
            "Page No.: 1 Order No.: 60038419\n"
            "Body page 1\n"
            "Page No.: 2 Order No.: 60038419\n"
            "Body page 2"
        )
        result = strip_pdf_headers(text)
        assert "Page No." not in result
        assert "Body page 1" in result
        assert "Body page 2" in result


class TestNormaliseLabelFull:
    def test_lowercases(self):
        assert normalise_label("APPLICANT NAME") == "applicant name"

    def test_strips_colons(self):
        assert normalise_label("Name:") == "name"

    def test_strips_periods(self):
        result = normalise_label("Order No.")
        assert "." not in result

    def test_collapses_spaces(self):
        result = normalise_label("  Existing   DT  ")
        assert "  " not in result

    def test_empty_string(self):
        assert normalise_label("") == ""


class TestNormaliseDtCapacityFull:
    def test_standard_format(self):
        result = normalise_dt_capacity("400 KVA DT")
        assert "400" in result
        assert "kVA" in result

    def test_no_space(self):
        result = normalise_dt_capacity("400KVA")
        assert "400" in result

    def test_mixed_case(self):
        result = normalise_dt_capacity("400kva")
        assert "400" in result

    def test_with_extra_spaces(self):
        result = normalise_dt_capacity("400  kVA  DT")
        assert "400" in result

    def test_none_returns_none(self):
        assert normalise_dt_capacity(None) is None

    def test_empty_string(self):
        result = normalise_dt_capacity("")
        # Should return None or empty — not crash
        assert result is None or result == ""


class TestCleanScopeTextFull:
    def test_collapses_spaces(self):
        result = clean_scope_text("LT  extension   from   pole")
        assert "  " not in result

    def test_strips_whitespace(self):
        result = clean_scope_text("  text  ")
        assert result == "text" or result.strip() == "text"


# ── formatting ──────────────────────────────────────────────────


class TestFormatIndianAmountFull:
    def test_lakhs(self):
        result = format_indian_amount(125000.50)
        assert "125,000" in result

    def test_crores(self):
        result = format_indian_amount(15000000)
        assert "15,000,000" in result

    def test_zero(self):
        assert "0" in format_indian_amount(0)

    def test_negative(self):
        result = format_indian_amount(-5000)
        assert "-" in result

    def test_decimal_input(self):
        result = format_indian_amount(Decimal("123456.78"))
        assert "123,456" in result

    def test_string_input(self):
        result = format_indian_amount("50000")
        assert "50,000" in result

    def test_small_amount(self):
        result = format_indian_amount(42)
        assert "42" in result


class TestParseIndianAmountFull:
    def test_plain_number(self):
        assert parse_indian_amount("50000") == Decimal("50000")

    def test_with_commas(self):
        result = parse_indian_amount("1,25,000.50")
        assert result == Decimal("125000.50")

    def test_with_rs_prefix(self):
        result = parse_indian_amount("Rs. 1,25,000")
        assert result == Decimal("125000")

    def test_with_rupee_symbol(self):
        result = parse_indian_amount("₹ 50,000")
        assert result == Decimal("50000")

    def test_invalid_returns_none(self):
        assert parse_indian_amount("not a number") is None

    def test_empty_returns_none(self):
        assert parse_indian_amount("") is None


class TestGetCapexYearFull:
    def test_returns_string_format(self):
        result = get_capex_year()
        assert isinstance(result, str)
        parts = result.split("-")
        assert len(parts) == 2

    def test_march_is_previous_fy(self):
        result = get_capex_year(date(2026, 3, 15))
        assert result == "2025-26"

    def test_april_is_current_fy(self):
        result = get_capex_year(date(2026, 4, 1))
        assert result == "2026-27"

    def test_december_is_current_fy(self):
        result = get_capex_year(date(2026, 12, 31))
        assert result == "2026-27"

    def test_january_is_previous_fy(self):
        result = get_capex_year(date(2027, 1, 15))
        assert result == "2026-27"


# ── AuditLogger ─────────────────────────────────────────────────


class TestAuditLogger:
    def test_log_and_retrieve(self, db, tmp_path):
        from app.infrastructure.audit_logger import AuditLogger
        # AuditLogger.get_history needs a path, not a Database object
        audit = AuditLogger(db)
        audit.log(action="GENERATE", case_id=1, details="Test generation")
        # Use db path for get_history (it opens a new connection)
        audit2 = AuditLogger(db._db_path)
        history = audit2.get_history(1)
        assert len(history) >= 1
        assert history[0]["action"] == "GENERATE"

    def test_log_multiple_actions(self, db):
        from app.infrastructure.audit_logger import AuditLogger
        audit = AuditLogger(db)
        audit.log(action="GENERATE", case_id=1)
        audit.log(action="APPROVED", case_id=1)
        audit.log(action="STATUS_CHANGE", case_id=1, old_value="Pending", new_value="Approved")
        audit2 = AuditLogger(db._db_path)
        history = audit2.get_history(1)
        assert len(history) >= 3

    def test_log_with_engineer_name(self, db):
        from app.infrastructure.audit_logger import AuditLogger
        audit = AuditLogger(db)
        audit.log(action="GENERATE", case_id=1, engineer_name="Yash")
        audit2 = AuditLogger(db._db_path)
        history = audit2.get_history(1)
        assert history[0]["engineer_name"] == "Yash"


# ── BackupManager ───────────────────────────────────────────────


class TestBackupManager:
    def test_create_backup(self, tmp_path):
        from app.infrastructure.backup_manager import BackupManager
        db_path = tmp_path / "test.db"
        db_path.write_bytes(b"sqlite data")
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        backup_dir = tmp_path / "backups"

        mgr = BackupManager(db_path, output_dir, backup_dir)
        zip_path = mgr.create_backup()
        assert zip_path.exists()
        assert zip_path.suffix == ".zip"

    def test_list_backups_empty(self, tmp_path):
        from app.infrastructure.backup_manager import BackupManager
        mgr = BackupManager(tmp_path / "db.db", tmp_path, tmp_path / "backups")
        assert mgr.list_backups() == []

    def test_list_backups_returns_created(self, tmp_path):
        from app.infrastructure.backup_manager import BackupManager
        db = tmp_path / "test.db"
        db.write_bytes(b"data")
        out = tmp_path / "output"
        out.mkdir()
        bak = tmp_path / "backups"

        mgr = BackupManager(db, out, bak)
        p1 = mgr.create_backup()
        backups = mgr.list_backups()
        assert len(backups) >= 1
        assert backups[0].suffix == ".zip"


# ── RecoveryManager ─────────────────────────────────────────────


class TestRecoveryManager:
    def test_initial_state_empty(self, tmp_path):
        from app.infrastructure.recovery_manager import RecoveryManager
        mgr = RecoveryManager(tmp_path / "recovery")
        assert not mgr.has_recovery_data()

    def test_update_and_clear_state(self, tmp_path):
        from app.infrastructure.recovery_manager import RecoveryManager
        mgr = RecoveryManager(tmp_path / "recovery")
        mgr.update_state("order_no", "60038419")
        assert mgr._current_state["order_no"] == "60038419"
        mgr.clear_state()
        assert mgr._current_state == {}

    def test_save_on_exit_creates_file(self, tmp_path):
        from app.infrastructure.recovery_manager import RecoveryManager
        mgr = RecoveryManager(tmp_path / "recovery")
        mgr.update_state("test_key", "test_value")
        mgr._save_on_exit()
        recovery_files = list((tmp_path / "recovery").glob("recovery_*.json"))
        assert len(recovery_files) == 1
        data = json.loads(recovery_files[0].read_text())
        assert data["test_key"] == "test_value"

    def test_save_on_exit_empty_state_no_file(self, tmp_path):
        from app.infrastructure.recovery_manager import RecoveryManager
        mgr = RecoveryManager(tmp_path / "recovery")
        mgr._save_on_exit()
        recovery_dir = tmp_path / "recovery"
        if recovery_dir.exists():
            assert list(recovery_dir.glob("recovery_*.json")) == []
