"""Docx builder helper/edge-case tests — _space_material_desc, _clean_load, _clean_address, etc."""

from __future__ import annotations

import pytest

from app.builders.docx_builder import (
    _clean_applicant_name,
    _clean_address,
    _clean_load,
    _short_capex_year,
    _space_material_desc,
    _extract_area_name,
    _select_key_materials,
    _build_scope_text,
)
from app.domain.enums import WorkType
from app.domain.models import Case, Material


# ── _space_material_desc ────────────────────────────────────────


class TestSpaceMaterialDesc:
    def test_cable_desc(self):
        assert _space_material_desc("CABLE1.1KVAL4CX25SQMM") == "CABLE 1.1KV AL 4CX25 SQMM"

    def test_transformer_desc(self):
        result = _space_material_desc("TRANSFORMER250KVA3PH11KV/433VCU")
        assert "TRANSFORMER 250KVA" in result
        assert "/ 433V" in result

    def test_pole_desc(self):
        result = _space_material_desc("POLEPCC9MLONG160KG")
        assert "POLE PCC" in result
        assert "LONG" in result
        assert "KG" in result

    def test_empty_string(self):
        assert _space_material_desc("") == ""

    def test_none_passthrough(self):
        assert _space_material_desc(None) is None

    def test_already_spaced(self):
        assert _space_material_desc("CABLE 1.1KV AL 4CX25 SQMM") == "CABLE 1.1KV AL 4CX25 SQMM"


# ── _clean_load ─────────────────────────────────────────────────


class TestCleanLoad:
    def test_with_category(self):
        assert _clean_load("01KW E-DOM") == "1 kW"

    def test_numeric_only(self):
        assert _clean_load("18") == "18 kW"

    def test_kva_to_kw(self):
        assert _clean_load("01KVA E-DOMESTIC") == "1 kW"

    def test_plus_loads(self):
        assert _clean_load("01KW +01") == "2 kW"

    def test_larger_value(self):
        assert _clean_load("60 KW") == "60 kW"

    def test_e_vehicle(self):
        assert _clean_load("5KW E-VEHICLE") == "5 kW"

    def test_domestic_freeform(self):
        assert _clean_load("2 kw Domestic of both connection") == "2 kW"

    def test_empty(self):
        assert _clean_load("") == "N/A"

    def test_none(self):
        assert _clean_load(None) == "N/A"


# ── _clean_address ──────────────────────────────────────────────


class TestCleanAddress:
    def test_removes_supply_prefix(self):
        result = _clean_address("Supply Address: 123 Main St, Delhi")
        assert not result.startswith("Supply")
        assert "123 Main St" in result

    def test_removes_landmark(self):
        result = _clean_address("123 Main St LANDMARK Near school")
        assert "LANDMARK" not in result

    def test_removes_mobile(self):
        result = _clean_address("123 St MOB NO 9999999999 extra")
        assert "MOB" not in result
        assert "9999" not in result

    def test_removes_email(self):
        result = _clean_address("123 St Email: user@example.com extra")
        assert "Email" not in result

    def test_removes_comm_address(self):
        result = _clean_address("123 St Communication Address 456 Other St")
        assert "Communication" not in result

    def test_removes_near_by_pole(self):
        result = _clean_address("123 St NEAR BY POLE NO A/123-456")
        assert "NEAR BY POLE" not in result

    def test_empty(self):
        assert _clean_address("") == ""

    def test_none(self):
        assert _clean_address(None) is None


# ── _clean_applicant_name ───────────────────────────────────────


class TestCleanApplicantName:
    def test_removes_company_prefix(self):
        assert _clean_applicant_name("Company ADITYA SETH") == "ADITYA SETH"

    def test_removes_trailing_period(self):
        assert _clean_applicant_name("JOHN DOE.") == "JOHN DOE"

    def test_empty(self):
        assert _clean_applicant_name("") == ""

    def test_none(self):
        assert _clean_applicant_name(None) == ""


# ── _short_capex_year ───────────────────────────────────────────


class TestShortCapexYear:
    def test_from_full(self):
        assert _short_capex_year("2026-27") == "26-27"

    def test_from_short(self):
        assert _short_capex_year("26-27") == "26-27"

    def test_default_calls_function(self):
        # Without argument uses get_capex_year()
        result = _short_capex_year()
        assert "-" in result
        assert len(result) == 5


# ── _extract_area_name ──────────────────────────────────────────


class TestExtractAreaName:
    def test_vpo_pattern(self):
        assert _extract_area_name("VPO Alipur, Delhi") == "ALIPUR"

    def test_village_post_office(self):
        result = _extract_area_name("Village & Post Office Village Alipur, Delhi")
        assert result == "ALIPUR"

    def test_village_simple(self):
        result = _extract_area_name("Village Holambi Kalan, North Delhi")
        assert result == "HOLAMBI"

    def test_empty(self):
        assert _extract_area_name("") == ""

    def test_no_match(self):
        assert _extract_area_name("123 Main Street Delhi") == ""


# ── _select_key_materials ───────────────────────────────────────


class TestSelectKeyMaterials:
    def test_empty_materials(self):
        case = Case(materials=[])
        assert _select_key_materials(case) == []

    def test_lt_standard_selects_cable(self):
        mats = [
            Material(description="CABLE1.1KVAL4CX25SQMM", quantity=85, unit="M"),
            Material(description="POLEPCC9MLONG160KG", quantity=2, unit="NO"),
        ]
        case = Case(materials=mats, work_type=WorkType.LT_STANDARD)
        result = _select_key_materials(case)
        assert any("CABLE" in m.description for m in result)

    def test_dt_aug_selects_transformer(self):
        mats = [
            Material(description="TRANSFORMER250KVA3PH11KV/433VCU", quantity=1, unit="NO"),
            Material(description="ACB 400A LT", quantity=1, unit="NO"),
        ]
        case = Case(materials=mats, work_type=WorkType.DT_AUGMENTATION)
        result = _select_key_materials(case)
        assert any("TRANSFORMER" in m.description for m in result)


# ── _build_scope_text ───────────────────────────────────────────


class TestBuildScopeText:
    def test_lt_standard_format(self):
        case = Case(
            materials=[Material(description="CABLE1.1KVAL4CX25SQMM", quantity=85, unit="M")],
            work_type=WorkType.LT_STANDARD,
            tapping_pole="A/123",
        )
        text = _build_scope_text(case)
        assert "pole no." in text
        assert "85" in text

    def test_no_materials_fallback(self):
        case = Case(
            materials=[],
            scope_of_work="Manual scope text",
            tapping_pole="XYZ",
        )
        text = _build_scope_text(case)
        assert text == "Manual scope text"
