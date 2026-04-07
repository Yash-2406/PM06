"""Validation edge-case tests — comprehensive coverage of all 17 checks.

Tests blocking, warning, and cross-field checks with boundary values.
"""

from __future__ import annotations

import pytest

from app.domain.enums import WorkType
from app.domain.models import Case, FeederDetail, Material
from app.services.validator_service import ValidatorService


@pytest.fixture
def v():
    return ValidatorService()


def _valid_case(**overrides) -> Case:
    """Build a fully-valid case, then override specific fields."""
    defaults = dict(
        order_no="60038419",
        notification_no="1234567890",
        applicant_name="Test User",
        address="123 Test Street, Near Market, Delhi",
        pin_code="110001",
        zone="411",
        district="CVL",
        wbs_no="CE/N0000/00134",
        load_applied="5 kW",
        category="DOMESTIC",
        work_type=WorkType.LT_STANDARD,
        grand_total=125000.50,
        scope_of_work="LT extension from pole 123 towards premises for 200 meters.",
        materials=[Material(description="Cable", quantity=100, unit="MTR")],
        feeder_details=[FeederDetail(sr_no=1, acb_no=101, loading_amps=250.0)],
    )
    defaults.update(overrides)
    return Case(**defaults)


# ── BLOCKING checks ─────────────────────────────────────────────


class TestBlockingOrderNo:
    def test_valid_order_no(self, v):
        result = v.validate(_valid_case())
        checks = {c.field: c for c in result.checks}
        assert checks["order_no"].passed

    def test_missing_order_no_blocks(self, v):
        result = v.validate(_valid_case(order_no=None))
        assert result.is_blocked
        fields = [c.field for c in result.blocking_failures]
        assert "order_no" in fields

    def test_empty_order_no_blocks(self, v):
        result = v.validate(_valid_case(order_no=""))
        assert result.is_blocked

    def test_whitespace_order_no_blocks(self, v):
        result = v.validate(_valid_case(order_no="   "))
        assert result.is_blocked


class TestBlockingNotificationNo:
    def test_bare_10_digits_passes(self, v):
        result = v.validate(_valid_case(notification_no="1234567890"))
        checks = {c.field: c for c in result.checks}
        assert checks["notification_no"].passed

    def test_nc_prefixed_passes(self, v):
        result = v.validate(_valid_case(notification_no="N/C 1234567890"))
        checks = {c.field: c for c in result.checks}
        assert checks["notification_no"].passed

    def test_9_digits_fails(self, v):
        result = v.validate(_valid_case(notification_no="123456789"))
        checks = {c.field: c for c in result.checks}
        assert not checks["notification_no"].passed

    def test_11_digits_with_embedded_10_passes(self, v):
        # Contains a 10-digit substring
        result = v.validate(_valid_case(notification_no="12345678901"))
        checks = {c.field: c for c in result.checks}
        assert checks["notification_no"].passed

    def test_empty_fails(self, v):
        result = v.validate(_valid_case(notification_no=""))
        assert result.is_blocked

    def test_none_fails(self, v):
        result = v.validate(_valid_case(notification_no=None))
        assert result.is_blocked


class TestBlockingApplicantName:
    def test_valid_name(self, v):
        checks = {c.field: c for c in v.validate(_valid_case()).checks}
        assert checks["applicant_name"].passed

    def test_single_char_fails(self, v):
        result = v.validate(_valid_case(applicant_name="A"))
        checks = {c.field: c for c in result.checks}
        assert not checks["applicant_name"].passed

    def test_none_fails(self, v):
        result = v.validate(_valid_case(applicant_name=None))
        assert result.is_blocked


class TestBlockingAddress:
    def test_valid_address(self, v):
        checks = {c.field: c for c in v.validate(_valid_case()).checks}
        assert checks["address"].passed

    def test_short_address_fails(self, v):
        result = v.validate(_valid_case(address="ab"))
        checks = {c.field: c for c in result.checks}
        assert not checks["address"].passed


class TestBlockingZone:
    def test_valid_zone(self, v):
        checks = {c.field: c for c in v.validate(_valid_case()).checks}
        assert checks["zone"].passed

    def test_empty_zone_blocks(self, v):
        result = v.validate(_valid_case(zone=""))
        assert result.is_blocked


class TestBlockingGrandTotal:
    def test_positive_passes(self, v):
        checks = {c.field: c for c in v.validate(_valid_case()).checks}
        assert checks["grand_total"].passed

    def test_zero_blocks(self, v):
        result = v.validate(_valid_case(grand_total=0))
        assert result.is_blocked

    def test_negative_blocks(self, v):
        result = v.validate(_valid_case(grand_total=-100))
        assert result.is_blocked

    def test_none_blocks(self, v):
        result = v.validate(_valid_case(grand_total=None))
        assert result.is_blocked


class TestBlockingLoadApplied:
    def test_valid(self, v):
        checks = {c.field: c for c in v.validate(_valid_case()).checks}
        assert checks["load_applied"].passed

    def test_empty_blocks(self, v):
        result = v.validate(_valid_case(load_applied=""))
        assert result.is_blocked


class TestBlockingWorkType:
    def test_valid(self, v):
        checks = {c.field: c for c in v.validate(_valid_case()).checks}
        assert checks["work_type"].passed

    def test_none_blocks(self, v):
        result = v.validate(_valid_case(work_type=None))
        assert result.is_blocked


# ── WARNING checks ──────────────────────────────────────────────


class TestWarningPinCode:
    def test_valid_delhi_pin(self, v):
        checks = {c.field: c for c in v.validate(_valid_case(pin_code="110001")).checks}
        assert checks["pin_code"].passed

    def test_another_delhi_pin(self, v):
        checks = {c.field: c for c in v.validate(_valid_case(pin_code="100001")).checks}
        assert checks["pin_code"].passed

    def test_non_delhi_pin_warns(self, v):
        result = v.validate(_valid_case(pin_code="560001"))
        warnings = [c.field for c in result.warnings]
        assert "pin_code" in warnings

    def test_empty_pin_warns(self, v):
        result = v.validate(_valid_case(pin_code=""))
        warnings = [c.field for c in result.warnings]
        assert "pin_code" in warnings


class TestWarningCategory:
    def test_domestic_passes(self, v):
        checks = {c.field: c for c in v.validate(_valid_case(category="DOMESTIC")).checks}
        assert checks["category"].passed

    def test_commercial_passes(self, v):
        checks = {c.field: c for c in v.validate(_valid_case(category="COMMERCIAL")).checks}
        assert checks["category"].passed

    def test_unknown_category_warns(self, v):
        result = v.validate(_valid_case(category="BIZARRE"))
        warnings = [c.field for c in result.warnings]
        assert "category" in warnings

    def test_none_category_warns(self, v):
        result = v.validate(_valid_case(category=None))
        warnings = [c.field for c in result.warnings]
        assert "category" in warnings


class TestWarningMaterials:
    def test_with_materials_passes(self, v):
        checks = {c.field: c for c in v.validate(_valid_case()).checks}
        assert checks["materials"].passed

    def test_empty_materials_warns(self, v):
        result = v.validate(_valid_case(materials=[]))
        warnings = [c.field for c in result.warnings]
        assert "materials" in warnings


class TestWarningScope:
    def test_long_scope_passes(self, v):
        checks = {c.field: c for c in v.validate(_valid_case()).checks}
        assert checks["scope_of_work"].passed

    def test_short_scope_warns(self, v):
        result = v.validate(_valid_case(scope_of_work="short"))
        warnings = [c.field for c in result.warnings]
        assert "scope_of_work" in warnings


class TestWarningCostRange:
    def test_within_range_passes(self, v):
        case = _valid_case(work_type=WorkType.LT_STANDARD, grand_total=50000)
        checks = {c.field: c for c in v.validate(case).checks}
        assert checks["grand_total_range"].passed

    def test_below_lower_bound_warns(self, v):
        case = _valid_case(work_type=WorkType.LT_STANDARD, grand_total=100)
        result = v.validate(case)
        warnings = [c.field for c in result.warnings]
        assert "grand_total_range" in warnings

    def test_above_upper_bound_warns(self, v):
        case = _valid_case(work_type=WorkType.LT_STANDARD, grand_total=99_000_000)
        result = v.validate(case)
        warnings = [c.field for c in result.warnings]
        assert "grand_total_range" in warnings

    def test_dt_augmentation_higher_bounds(self, v):
        case = _valid_case(
            work_type=WorkType.DT_AUGMENTATION,
            grand_total=40_000_000,
            existing_dt_capacity="200 KVA",
            new_transformer_rating="400 KVA",
        )
        checks = {c.field: c for c in v.validate(case).checks}
        assert checks["grand_total_range"].passed

    def test_none_grand_total_passes_range(self, v):
        # grand_total=None won't be checked for range (blocked separately)
        case = _valid_case(grand_total=None)
        checks = {c.field: c for c in v.validate(case).checks}
        assert checks["grand_total_range"].passed


class TestWarningFeederDetails:
    def test_with_feeders_passes(self, v):
        checks = {c.field: c for c in v.validate(_valid_case()).checks}
        assert checks["feeder_details"].passed

    def test_empty_feeders_warns(self, v):
        result = v.validate(_valid_case(feeder_details=[]))
        warnings = [c.field for c in result.warnings]
        assert "feeder_details" in warnings


# ── CROSS-FIELD checks ──────────────────────────────────────────


class TestCrossFieldZoneDistrict:
    def test_matching_zone_district(self, v):
        # Zone 411 belongs to CVL district
        case = _valid_case(zone="411", district="CVL")
        checks = {c.field: c for c in v.validate(case).checks}
        assert checks["zone_district"].passed

    def test_mismatched_zone_district_warns(self, v):
        # Zone 411 belongs to CVL, not NRL
        case = _valid_case(zone="411", district="NRL")
        result = v.validate(case)
        warnings = [c.field for c in result.warnings]
        assert "zone_district" in warnings

    def test_empty_zone_skips_check(self, v):
        # Empty zone → skip (blocked separately)
        case = _valid_case(zone="", district="CVL")
        checks = {c.field: c for c in v.validate(case).checks}
        assert checks["zone_district"].passed

    def test_empty_district_skips_check(self, v):
        case = _valid_case(zone="411", district="")
        checks = {c.field: c for c in v.validate(case).checks}
        assert checks["zone_district"].passed


class TestCrossFieldDTUpgrade:
    def test_non_dt_skips(self, v):
        case = _valid_case(work_type=WorkType.LT_STANDARD)
        checks = {c.field: c for c in v.validate(case).checks}
        assert checks["dt_upgrade"].passed

    def test_dt_with_both_capacities_passes(self, v):
        case = _valid_case(
            work_type=WorkType.DT_AUGMENTATION,
            existing_dt_capacity="200 KVA",
            new_transformer_rating="400 KVA",
        )
        checks = {c.field: c for c in v.validate(case).checks}
        assert checks["dt_upgrade"].passed

    def test_dt_missing_existing_warns(self, v):
        case = _valid_case(
            work_type=WorkType.DT_AUGMENTATION,
            existing_dt_capacity=None,
            new_transformer_rating="400 KVA",
        )
        result = v.validate(case)
        warnings = [c.field for c in result.warnings]
        assert "dt_upgrade" in warnings

    def test_dt_missing_new_warns(self, v):
        case = _valid_case(
            work_type=WorkType.DT_AUGMENTATION,
            existing_dt_capacity="200 KVA",
            new_transformer_rating=None,
        )
        result = v.validate(case)
        warnings = [c.field for c in result.warnings]
        assert "dt_upgrade" in warnings


class TestCrossFieldDistrictPresent:
    def test_zone_and_district_both_present(self, v):
        result = v.validate(_valid_case())
        # The field name is "district" (when zone empty) or "district_from_zone"
        district_checks = [c for c in result.checks if c.field in ("district", "district_from_zone")]
        assert len(district_checks) == 1
        assert district_checks[0].passed


# ── Aggregate scenarios ─────────────────────────────────────────


class TestValidationAggregates:
    def test_fully_valid_case_not_blocked(self, v):
        result = v.validate(_valid_case())
        assert not result.is_blocked

    def test_all_fields_missing_all_block(self, v):
        result = v.validate(Case())
        assert result.is_blocked
        assert len(result.blocking_failures) >= 6  # at least 6 blocking checks

    def test_total_check_count(self, v):
        result = v.validate(_valid_case())
        # 8 blocking + 6 warning + 3 cross-field = 17
        assert len(result.checks) == 17
