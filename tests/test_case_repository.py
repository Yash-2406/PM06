"""Case repository aggregation / MIS tests & update methods."""

from __future__ import annotations

import pytest

from app.data.case_repository import CaseRepository
from app.domain.enums import CaseStatus, WorkType
from app.domain.models import Case


def _make_case(repo: CaseRepository, **overrides) -> int:
    defaults = dict(
        order_no="60038000",
        notification_no="1234567890",
        applicant_name="Test",
        address="123 Test St, Delhi",
        pin_code="110001",
        zone="411",
        district="CVL",
        wbs_no="CE/N0000/00134",
        load_applied="5 kW",
        category="DOMESTIC",
        work_type=WorkType.LT_STANDARD,
        grand_total=100_000,
        scope_of_work="LT extension from pole 123",
        status=CaseStatus.PENDING,
    )
    defaults.update(overrides)
    c = Case(**defaults)
    return repo.create_case(c)


# ── count_by_district_status ────────────────────────────────────


class TestCountByDistrictStatus:
    def test_empty_db(self, db):
        repo = CaseRepository(db)
        assert repo.count_by_district_status() == []

    def test_single_group(self, db):
        repo = CaseRepository(db)
        _make_case(repo, district="CVL")
        _make_case(repo, district="CVL")
        result = repo.count_by_district_status()
        assert len(result) == 1
        assert result[0]["count"] == 2

    def test_multiple_groups(self, db):
        repo = CaseRepository(db)
        _make_case(repo, order_no="60001001", district="CVL")
        _make_case(repo, order_no="60001002", district="CVL")
        _make_case(repo, order_no="60001003", district="NRL")
        c_id = _make_case(repo, order_no="60001004", district="CVL")
        repo.update_status(c_id, CaseStatus.APPROVED)
        result = repo.count_by_district_status()
        assert len(result) >= 2


# ── count_and_sum_all ───────────────────────────────────────────


class TestCountAndSumAll:
    def test_empty_db(self, db):
        repo = CaseRepository(db)
        cnt, total = repo.count_and_sum_all()
        assert cnt == 0
        assert total == 0.0

    def test_mixed_costs(self, db):
        repo = CaseRepository(db)
        _make_case(repo, order_no="60001001", grand_total=10000)
        _make_case(repo, order_no="60001002", grand_total=20000)
        _make_case(repo, order_no="60001003", grand_total=None)
        cnt, total = repo.count_and_sum_all()
        assert cnt == 3
        assert total == 30000.0


# ── count_by_status ─────────────────────────────────────────────


class TestCountByStatus:
    def test_all_statuses(self, db):
        repo = CaseRepository(db)
        c1 = _make_case(repo, order_no="60001001")
        c2 = _make_case(repo, order_no="60001002")
        c3 = _make_case(repo, order_no="60001003")
        repo.update_status(c2, CaseStatus.APPROVED)
        repo.update_status(c3, CaseStatus.REJECTED)
        result = repo.count_by_status()
        assert "Pending" in result
        assert "Approved" in result
        assert "Rejected" in result

    def test_empty_db(self, db):
        repo = CaseRepository(db)
        assert repo.count_by_status() == {}


# ── count_by_district / zone / work_type ────────────────────────


class TestCountByDistrict:
    def test_returns_dict(self, db):
        repo = CaseRepository(db)
        _make_case(repo, order_no="60001001", district="CVL")
        _make_case(repo, order_no="60001002", district="NRL")
        result = repo.count_by_district()
        assert isinstance(result, dict)
        assert result.get("CVL") == 1
        assert result.get("NRL") == 1


class TestCountByZone:
    def test_numeric_zones(self, db):
        repo = CaseRepository(db)
        _make_case(repo, order_no="60001001", zone="411")
        _make_case(repo, order_no="60001002", zone="512")
        _make_case(repo, order_no="60001003", zone="411")
        result = repo.count_by_zone()
        assert result.get("411") == 2
        assert result.get("512") == 1


class TestCountByWorkType:
    def test_known_types(self, db):
        repo = CaseRepository(db)
        _make_case(repo, order_no="60001001", work_type=WorkType.LT_STANDARD)
        _make_case(repo, order_no="60001002", work_type=WorkType.DT_AUGMENTATION)
        result = repo.count_by_work_type()
        assert "LT_STANDARD" in result
        assert "DT_AUGMENTATION" in result


# ── sum_by_district / sum_by_status ─────────────────────────────


class TestSumByDistrict:
    def test_sums(self, db):
        repo = CaseRepository(db)
        _make_case(repo, order_no="60001001", district="CVL", grand_total=100)
        _make_case(repo, order_no="60001002", district="CVL", grand_total=200)
        _make_case(repo, order_no="60001003", district="NRL", grand_total=500)
        result = repo.sum_by_district()
        assert result["CVL"] == 300.0
        assert result["NRL"] == 500.0


class TestSumByStatus:
    def test_sums(self, db):
        repo = CaseRepository(db)
        c1 = _make_case(repo, order_no="60001001", grand_total=100)
        c2 = _make_case(repo, order_no="60001002", grand_total=200)
        repo.update_status(c2, CaseStatus.APPROVED)
        result = repo.sum_by_status()
        assert "Pending" in result
        assert "Approved" in result


# ── count_by_month ──────────────────────────────────────────────


class TestCountByMonth:
    def test_returns_list_of_dicts(self, db):
        repo = CaseRepository(db)
        _make_case(repo, order_no="60001001")
        result = repo.count_by_month()
        assert isinstance(result, list)
        assert len(result) >= 1
        assert "month" in result[0]
        assert "cnt" in result[0]
        assert "total" in result[0]


# ── add_source_file / add_generated_doc ─────────────────────────


class TestSourceFileTracking:
    def test_add_source_file(self, db):
        repo = CaseRepository(db)
        case_id = _make_case(repo)
        repo.add_source_file(case_id, "SCHEME_PDF", "/path/scheme.pdf", "abc123hash")
        # Verify via raw query
        row = db.connection.execute(
            "SELECT * FROM source_files WHERE case_id = ?", (case_id,)
        ).fetchone()
        assert row is not None
        assert dict(row)["file_type"] == "SCHEME_PDF"

    def test_add_generated_doc(self, db):
        repo = CaseRepository(db)
        case_id = _make_case(repo)
        repo.add_generated_doc(case_id, "/path/to/output.docx", "TestEngineer")
        row = db.connection.execute(
            "SELECT * FROM generated_docs WHERE case_id = ?", (case_id,)
        ).fetchone()
        assert row is not None
        assert dict(row)["engineer_name"] == "TestEngineer"


# ── update_case_fields ──────────────────────────────────────────


class TestUpdateCaseFields:
    def test_updates_allowed_fields(self, db):
        repo = CaseRepository(db)
        case_id = _make_case(repo)
        repo.update_case_fields(case_id, {"applicant_name": "NEW NAME"})
        case = repo.get_by_id(case_id)
        assert case.applicant_name == "NEW NAME"

    def test_ignores_disallowed_fields(self, db):
        repo = CaseRepository(db)
        case_id = _make_case(repo)
        repo.update_case_fields(case_id, {"id": 999, "evil_field": "x"})
        case = repo.get_by_id(case_id)
        assert case.id == case_id  # unchanged

    def test_empty_dict_noop(self, db):
        repo = CaseRepository(db)
        case_id = _make_case(repo)
        repo.update_case_fields(case_id, {})
        case = repo.get_by_id(case_id)
        assert case.order_no == "60038000"

    def test_update_generated_doc(self, db):
        repo = CaseRepository(db)
        case_id = _make_case(repo)
        repo.update_generated_doc(case_id, "/new/path.docx")
        case = repo.get_by_id(case_id)
        assert case.output_docx_path == "/new/path.docx"


# ── get_next_sl_no ──────────────────────────────────────────────


class TestGetNextSlNo:
    def test_empty_returns_1(self, db):
        repo = CaseRepository(db)
        assert repo.get_next_sl_no() == 1

    def test_increments(self, db):
        repo = CaseRepository(db)
        _make_case(repo, order_no="60001001")
        _make_case(repo, order_no="60001002")
        assert repo.get_next_sl_no() == 3


# ── list_all filters ────────────────────────────────────────────


class TestListAllFilters:
    def test_filter_by_district(self, db):
        repo = CaseRepository(db)
        _make_case(repo, order_no="60001001", district="CVL")
        _make_case(repo, order_no="60001002", district="NRL")
        result = repo.list_all(district="CVL")
        assert len(result) == 1
        assert result[0].district == "CVL"

    def test_filter_by_zone(self, db):
        repo = CaseRepository(db)
        _make_case(repo, order_no="60001001", zone="411")
        _make_case(repo, order_no="60001002", zone="512")
        result = repo.list_all(zone="411")
        assert len(result) == 1

    def test_filter_by_status(self, db):
        repo = CaseRepository(db)
        c1 = _make_case(repo, order_no="60001001")
        c2 = _make_case(repo, order_no="60001002")
        repo.update_status(c2, CaseStatus.APPROVED)
        result = repo.list_all(status="Approved")
        assert len(result) == 1

    def test_no_filter_returns_all(self, db):
        repo = CaseRepository(db)
        _make_case(repo, order_no="60001001")
        _make_case(repo, order_no="60001002")
        assert len(repo.list_all()) == 2
