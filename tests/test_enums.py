"""Tests for app.domain.enums."""

from app.domain.enums import CaseStatus, FieldConfidence, FileType, WorkType


class TestWorkType:
    def test_display_name(self):
        assert WorkType.LT_STANDARD.display_name == "LT Line Extension (Standard)"
        assert WorkType.DT_AUGMENTATION.display_name == "DT Augmentation"

    def test_sub_head(self):
        assert "LT Line Extension" in WorkType.LT_STANDARD.sub_head

    def test_all_members(self):
        assert len(WorkType) == 4


class TestCaseStatus:
    def test_values(self):
        assert CaseStatus.PENDING.value == "Pending"
        assert CaseStatus.APPROVED.value == "Approved"
        assert CaseStatus.REJECTED.value == "Rejected"


class TestFieldConfidence:
    def test_ui_icon(self):
        assert FieldConfidence.HIGH.ui_icon == "✓"
        assert FieldConfidence.MEDIUM.ui_icon == "⚠"
        assert FieldConfidence.LOW.ui_icon == "✗"
        assert FieldConfidence.MANUAL.ui_icon == "✎"


class TestFileType:
    def test_values(self):
        assert FileType.SCHEME_PDF.value == "SCHEME_PDF"
        assert FileType.PM06_EXCEL.value == "PM06_EXCEL"
