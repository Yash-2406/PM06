"""Tests for app.data.database and app.data.case_repository."""

import pytest

from app.data.case_repository import CaseRepository
from app.data.database import Database
from app.domain.enums import CaseStatus
from app.domain.models import Case


class TestDatabase:
    def test_creates_tables(self, db):
        conn = db.connection
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = {row[0] for row in cursor.fetchall()}
        assert "cases" in tables
        assert "source_files" in tables
        assert "generated_docs" in tables
        assert "audit_log" in tables
        assert "db_metadata" in tables

    def test_wal_mode(self, db):
        conn = db.connection
        cursor = conn.execute("PRAGMA journal_mode")
        mode = cursor.fetchone()[0]
        assert mode.lower() == "wal"


class TestCaseRepository:
    def test_create_and_retrieve(self, db, sample_case):
        repo = CaseRepository(db)
        case_id = repo.create_case(sample_case)
        assert case_id is not None

        retrieved = repo.get_by_id(case_id)
        assert retrieved is not None
        assert retrieved.order_no == "000070012345"

    def test_get_by_order_no(self, db, sample_case):
        repo = CaseRepository(db)
        repo.create_case(sample_case)
        retrieved = repo.get_by_order_no("000070012345")
        assert retrieved is not None

    def test_list_all(self, db, sample_case):
        repo = CaseRepository(db)
        repo.create_case(sample_case)
        cases = repo.list_all()
        assert len(cases) >= 1

    def test_update_status(self, db, sample_case):
        repo = CaseRepository(db)
        case_id = repo.create_case(sample_case)
        repo.update_status(case_id, CaseStatus.APPROVED)
        retrieved = repo.get_by_id(case_id)
        assert retrieved.status == CaseStatus.APPROVED

    def test_count_by_district_status(self, db, sample_case):
        repo = CaseRepository(db)
        repo.create_case(sample_case)
        counts = repo.count_by_district_status()
        assert isinstance(counts, list)
