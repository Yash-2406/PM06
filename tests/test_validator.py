"""Tests for app.services.validator_service."""

import pytest

from app.domain.enums import WorkType
from app.domain.models import Case, Material
from app.services.validator_service import ValidatorService


@pytest.fixture
def validator():
    return ValidatorService()


class TestValidatorService:
    def test_valid_case_passes(self, validator, sample_case):
        result = validator.validate(sample_case)
        assert not result.is_blocked
        # Most checks should pass
        passed = sum(1 for c in result.checks if c.passed)
        assert passed >= 8

    def test_missing_order_no_blocks(self, validator):
        case = Case(
            notification_no="NC1234567890",
            applicant_name="Test",
            address="123 Street Delhi",
            zone="Zone-1",
            grand_total=10000,
            load_applied="5 kW",
            work_type=WorkType.LT_STANDARD,
        )
        result = validator.validate(case)
        assert result.is_blocked
        blocked_fields = [c.field for c in result.blocking_failures]
        assert "order_no" in blocked_fields

    def test_missing_notification_blocks(self, validator):
        case = Case(
            order_no="000070012345",
            applicant_name="Test",
            address="123 Street Delhi",
            zone="Zone-1",
            grand_total=10000,
            load_applied="5 kW",
            work_type=WorkType.LT_STANDARD,
        )
        result = validator.validate(case)
        assert result.is_blocked

    def test_no_materials_warning(self, validator, sample_case):
        sample_case.materials = []
        result = validator.validate(sample_case)
        warning_fields = [c.field for c in result.warnings]
        assert "materials" in warning_fields

    def test_unusual_cost_warning(self, validator, sample_case):
        sample_case.grand_total = 0.01
        result = validator.validate(sample_case)
        # Grand total is positive but below COST_LOWER_BOUND
        warning_fields = [c.field for c in result.warnings]
        assert "grand_total_range" in warning_fields

    def test_invalid_pin_warning(self, validator, sample_case):
        sample_case.pin_code = "999999"
        result = validator.validate(sample_case)
        warning_fields = [c.field for c in result.warnings]
        assert "pin_code" in warning_fields
