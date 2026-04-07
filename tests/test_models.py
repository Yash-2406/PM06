"""Tests for app.domain.models."""

import pytest

from app.domain.enums import CaseStatus, FieldConfidence, WorkType
from app.domain.models import (
    Case,
    ExtractionResult,
    Material,
    ValidationCheck,
    ValidationResult,
)


class TestExtractionResult:
    def test_is_found_true(self):
        r = ExtractionResult(value="hello", confidence=FieldConfidence.HIGH, source="regex_match")
        assert r.is_found is True

    def test_is_found_false(self):
        r = ExtractionResult(value=None, confidence=FieldConfidence.LOW, source="not_found")
        assert r.is_found is False

    def test_ui_icon(self):
        r = ExtractionResult(value="x", confidence=FieldConfidence.HIGH, source="test")
        assert r.ui_icon == "✓"


class TestValidationResult:
    def test_is_blocked_with_blocking_failure(self):
        checks = [
            ValidationCheck(field="f", rule="r", passed=False, message="bad", is_blocking=True),
        ]
        vr = ValidationResult(checks=checks)
        assert vr.is_blocked is True

    def test_is_blocked_no_failures(self):
        checks = [
            ValidationCheck(field="f", rule="r", passed=True, message="", is_blocking=True),
        ]
        vr = ValidationResult(checks=checks)
        assert vr.is_blocked is False

    def test_has_warnings(self):
        checks = [
            ValidationCheck(field="f", rule="r", passed=False, message="warn", is_blocking=False),
        ]
        vr = ValidationResult(checks=checks)
        assert vr.has_warnings is True
        assert vr.is_blocked is False


class TestCase:
    def test_defaults(self):
        c = Case()
        assert c.order_no is None
        assert c.status == CaseStatus.PENDING
        assert c.materials == []

    def test_with_fields(self, sample_case):
        assert sample_case.order_no == "000070012345"
        assert sample_case.work_type == WorkType.LT_STANDARD
        assert len(sample_case.materials) == 2


class TestMaterial:
    def test_all_optional(self):
        m = Material()
        assert m.description is None
        assert m.quantity is None

    def test_with_values(self):
        m = Material(description="Cable", quantity=10, unit="MTR")
        assert m.description == "Cable"
        assert m.quantity == 10
