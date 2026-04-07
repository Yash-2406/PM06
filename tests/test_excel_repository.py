"""Excel repository tests — tracker CRUD operations."""

from __future__ import annotations

import pytest
from pathlib import Path

from app.data.excel_repository import ExcelRepository
from app.domain.models import TrackerRow
from app.domain.constants import TRACKER_COLUMNS


def _make_row(**overrides) -> TrackerRow:
    defaults = dict(
        sl_no=1,
        scheme_no="60038419",
        n_no="NC00001234",
        district="CVL",
        zone="411",
        date_received="01-01-2026",
        date_processed="02-01-2026",
        status="Pending",
        remarks="",
        amount_rs=100000,
        correction_suggested="No",
        correction_details="",
    )
    defaults.update(overrides)
    return TrackerRow(**defaults)


# ── _ensure_tracker_exists ──────────────────────────────────────


class TestEnsureTrackerExists:
    def test_creates_new_file(self, tmp_path):
        tracker = tmp_path / "tracker.xlsx"
        repo = ExcelRepository(tracker)
        repo._ensure_tracker_exists()
        assert tracker.exists()

    def test_headers_match_columns(self, tmp_path):
        import openpyxl

        tracker = tmp_path / "tracker.xlsx"
        repo = ExcelRepository(tracker)
        repo._ensure_tracker_exists()

        wb = openpyxl.load_workbook(str(tracker))
        ws = wb["Sheet1"]
        headers = [ws.cell(row=1, column=i).value for i in range(1, len(TRACKER_COLUMNS) + 1)]
        wb.close()
        assert headers == list(TRACKER_COLUMNS)

    def test_idempotent(self, tmp_path):
        tracker = tmp_path / "tracker.xlsx"
        repo = ExcelRepository(tracker)
        repo._ensure_tracker_exists()
        size1 = tracker.stat().st_size
        repo._ensure_tracker_exists()
        size2 = tracker.stat().st_size
        assert size1 == size2


# ── get_max_sl_no ───────────────────────────────────────────────


class TestGetMaxSlNo:
    def test_empty_tracker(self, tmp_path):
        repo = ExcelRepository(tmp_path / "tracker.xlsx")
        assert repo.get_max_sl_no() == 0

    def test_after_append(self, tmp_path):
        repo = ExcelRepository(tmp_path / "tracker.xlsx")
        repo.append_row(_make_row(sl_no=5))
        assert repo.get_max_sl_no() == 5


# ── find_by_scheme_no ───────────────────────────────────────────


class TestFindBySchemeNo:
    def test_not_found(self, tmp_path):
        repo = ExcelRepository(tmp_path / "tracker.xlsx")
        assert repo.find_by_scheme_no("NONEXISTENT") is None

    def test_found_returns_row_number(self, tmp_path):
        repo = ExcelRepository(tmp_path / "tracker.xlsx")
        repo.append_row(_make_row(scheme_no="60038419"))
        row_num = repo.find_by_scheme_no("60038419")
        assert row_num == 2  # header is row 1


# ── append_row ──────────────────────────────────────────────────


class TestAppendRow:
    def test_single_row(self, tmp_path):
        repo = ExcelRepository(tmp_path / "tracker.xlsx")
        repo.append_row(_make_row(sl_no=1, scheme_no="60001001"))
        rows = repo.read_all_rows()
        assert len(rows) == 1
        assert rows[0][TRACKER_COLUMNS[1]] == "60001001"

    def test_multiple_appends(self, tmp_path):
        repo = ExcelRepository(tmp_path / "tracker.xlsx")
        for i in range(1, 4):
            repo.append_row(_make_row(sl_no=i, scheme_no=f"6000100{i}"))
        rows = repo.read_all_rows()
        assert len(rows) == 3


# ── update_row ──────────────────────────────────────────────────


class TestUpdateRow:
    def test_overwrites_data(self, tmp_path):
        repo = ExcelRepository(tmp_path / "tracker.xlsx")
        repo.append_row(_make_row(sl_no=1, scheme_no="60001001", status="Pending"))
        repo.update_row(2, _make_row(sl_no=1, scheme_no="60001001", status="Approved"))
        rows = repo.read_all_rows()
        assert rows[0][TRACKER_COLUMNS[7]] == "Approved"


# ── append_or_update_row ────────────────────────────────────────


class TestAppendOrUpdateRow:
    def test_inserts_when_new(self, tmp_path):
        repo = ExcelRepository(tmp_path / "tracker.xlsx")
        repo.append_or_update_row(_make_row(scheme_no="60001001"))
        assert len(repo.read_all_rows()) == 1

    def test_updates_when_existing(self, tmp_path):
        repo = ExcelRepository(tmp_path / "tracker.xlsx")
        repo.append_row(_make_row(scheme_no="60001001", status="Pending"))
        repo.append_or_update_row(_make_row(scheme_no="60001001", status="Approved"))
        rows = repo.read_all_rows()
        assert len(rows) == 1
        assert rows[0][TRACKER_COLUMNS[7]] == "Approved"


# ── batch_write_rows ────────────────────────────────────────────


class TestBatchWriteRows:
    def test_empty_list_noop(self, tmp_path):
        repo = ExcelRepository(tmp_path / "tracker.xlsx")
        repo.batch_write_rows([])
        assert len(repo.read_all_rows()) == 0

    def test_inserts_multiple(self, tmp_path):
        repo = ExcelRepository(tmp_path / "tracker.xlsx")
        rows = [_make_row(sl_no=i, scheme_no=f"6000100{i}") for i in range(1, 4)]
        repo.batch_write_rows(rows)
        assert len(repo.read_all_rows()) == 3

    def test_upsert_mix(self, tmp_path):
        repo = ExcelRepository(tmp_path / "tracker.xlsx")
        repo.append_row(_make_row(sl_no=1, scheme_no="60001001", status="Pending"))
        batch = [
            _make_row(sl_no=1, scheme_no="60001001", status="Approved"),
            _make_row(sl_no=2, scheme_no="60001002", status="Pending"),
        ]
        repo.batch_write_rows(batch)
        rows = repo.read_all_rows()
        assert len(rows) == 2
        statuses = {r[TRACKER_COLUMNS[1]]: r[TRACKER_COLUMNS[7]] for r in rows}
        assert statuses["60001001"] == "Approved"
        assert statuses["60001002"] == "Pending"


# ── read_all_rows ───────────────────────────────────────────────


class TestReadAllRows:
    def test_empty_tracker(self, tmp_path):
        repo = ExcelRepository(tmp_path / "tracker.xlsx")
        assert repo.read_all_rows() == []

    def test_returns_dicts_with_headers(self, tmp_path):
        repo = ExcelRepository(tmp_path / "tracker.xlsx")
        repo.append_row(_make_row())
        rows = repo.read_all_rows()
        assert isinstance(rows[0], dict)
        assert TRACKER_COLUMNS[0] in rows[0]


# ── save_backup ─────────────────────────────────────────────────


class TestSaveBackup:
    def test_creates_backup(self, tmp_path):
        repo = ExcelRepository(tmp_path / "tracker.xlsx")
        repo._ensure_tracker_exists()
        backup_dir = tmp_path / "backups"
        backup = repo.save_backup(backup_dir)
        assert backup.exists()
        assert backup.suffix == ".xlsx"

    def test_raises_if_no_tracker(self, tmp_path):
        repo = ExcelRepository(tmp_path / "tracker.xlsx")
        with pytest.raises(FileNotFoundError):
            repo.save_backup(tmp_path / "backups")
