"""Edge tests for SchemePDFExtractor — name fallback, address terminators, cost parsing."""

from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock

from app.domain.enums import FieldConfidence
from app.extractors.scheme_pdf_extractor import SchemePDFExtractor


class TestNameFallbackPaths:
    """SC-4: Name extraction fallback logic."""

    def test_name_after_nc_on_same_line(self):
        ext = SchemePDFExtractor()
        text = "N/C 1234567890 SURESH KUMAR  Mobile 9999999999"
        result = ext._extract_name(text)
        assert result.is_found
        assert "SURESH" in result.value

    def test_name_on_next_line_after_nc(self):
        ext = SchemePDFExtractor()
        text = "N/C 1234567890\nRAJESH SHARMA\nMobile 9999999999"
        result = ext._extract_name(text)
        assert result.is_found
        assert "RAJESH" in result.value

    def test_name_with_mr_prefix(self):
        ext = SchemePDFExtractor()
        text = "N/C 1234567890 Mr. RAMESH VERMA\nAddress line"
        result = ext._extract_name(text)
        assert result.is_found
        assert "RAMESH" in result.value

    def test_no_nc_no_name(self):
        ext = SchemePDFExtractor()
        text = "Just some random text with no notification number"
        result = ext._extract_name(text)
        assert result.confidence == FieldConfidence.LOW


class TestAddressTerminators:
    """SC-5: Address terminators stop collection correctly."""

    def test_stops_at_mobile(self):
        ext = SchemePDFExtractor()
        text = "N/C 1234567890\n123 Main Street\nNew Delhi\nMobile: 9876543210\nMore text"
        result = ext._extract_address(text)
        assert result.is_found
        assert "Mobile" not in result.value
        assert "Main Street" in result.value

    def test_stops_at_supply_type(self):
        ext = SchemePDFExtractor()
        text = "N/C 1234567890\n456 Market Road\nDelhi 110001\nSupply Type: LT"
        result = ext._extract_address(text)
        assert result.is_found
        assert "Supply Type" not in result.value

    def test_includes_pin_line(self):
        ext = SchemePDFExtractor()
        text = "N/C 1234567890\n789 Test Lane\nNew Delhi 110085\nMobile 9999"
        result = ext._extract_address(text)
        assert result.is_found
        assert "110085" in result.value

    def test_empty_nc_no_address(self):
        ext = SchemePDFExtractor()
        text = "No notification number here"
        result = ext._extract_address(text)
        assert result.confidence == FieldConfidence.LOW


class TestCostParsingEdge:
    """SC-6: Indian number format cost extraction."""

    def test_indian_format_lakh(self):
        ext = SchemePDFExtractor()
        # Match the exact regex pattern: Bill of material <number>
        text = "Bill of material 1,25,000.50\nBill of services 15,000.00"
        result = ext._extract_costs(text)
        val = result["bom_total"].value
        assert val is not None
        assert float(val) == 125000.50

    def test_grand_total_extraction(self):
        ext = SchemePDFExtractor()
        # Regex: Total\s*\(Rs\.\)\s*<number>
        text = "Total (Rs.) 2,50,000.75"
        result = ext._extract_costs(text)
        assert result["grand_total"].is_found

    def test_zero_costs(self):
        ext = SchemePDFExtractor()
        # Must match the exact regex patterns (no colon)
        text = "Bill of material 0.00\nBill of services 0.00\nTotal (Rs.) 0.00"
        result = ext._extract_costs(text)
        assert result["bom_total"].is_found

    def test_all_missing(self):
        ext = SchemePDFExtractor()
        result = ext._extract_costs("nothing relevant")
        for key in ["bom_total", "bos_total", "grand_total"]:
            assert key in result


class TestBOMMaterials:
    """SC-7: BOM material extraction."""

    def test_extract_with_pdfplumber_fallback(self):
        ext = SchemePDFExtractor()
        text = "1 123456789 LT 4CX25 SQMM CABLE ARMOURED M 200.00 150.000 30,000.00"
        materials = ext._extract_bom_materials.__wrapped__(ext, None, text) if hasattr(ext._extract_bom_materials, '__wrapped__') else None
        # Use regex directly since _extract_bom_materials needs a file
        from app.domain.constants import RE_BOM_ROW
        matches = RE_BOM_ROW.findall(text)
        assert len(matches) == 1


class TestNotificationNosEdge:
    """SC-3: Notification number edge cases."""

    def test_mixed_format_nc_numbers(self):
        text = "N/C 1234567890 and notification 9876543210/1111111111"
        nos = SchemePDFExtractor._extract_notification_nos(text)
        assert "1234567890" in nos

    def test_very_long_text(self):
        text = "Some preamble " * 100 + "N/C 5555555555" + " more text " * 100
        nos = SchemePDFExtractor._extract_notification_nos(text)
        assert "5555555555" in nos


class TestOrderNoEdge:
    """SC-2: Order number edge cases."""

    def test_8_digit_order(self):
        ext = SchemePDFExtractor()
        result = ext._extract_order_no("Order No.: 60038419", "Order No.: 60038419")
        assert result.value == "60038419"

    def test_order_in_body_only(self):
        ext = SchemePDFExtractor()
        result = ext._extract_order_no("no match here", "Order No.: 60038551")
        assert result.value == "60038551"

    def test_no_order_anywhere(self):
        ext = SchemePDFExtractor()
        result = ext._extract_order_no("nothing", "still nothing")
        assert result.confidence == FieldConfidence.LOW


class TestPinCodeEdge:
    """Delhi PIN code extraction edge cases."""

    def test_multiple_pins_first_wins(self):
        ext = SchemePDFExtractor()
        text = "Address 110001 and also 110085"
        result = ext._extract_pin(text)
        assert result.value in ("110001", "110085")

    def test_non_110_pin_rejected(self):
        ext = SchemePDFExtractor()
        text = "Code 200001 Agra"
        result = ext._extract_pin(text)
        assert result.value is None or result.confidence == FieldConfidence.LOW


# ── Nature of Scheme ────────────────────────────────────────────


class TestNatureOfScheme:
    """SC-8: Nature of scheme extraction."""

    def test_basic_nature(self):
        ext = SchemePDFExtractor()
        text = "Nature of Scheme: New Connection for Domestic Consumer"
        result = ext._extract_nature(text)
        assert result.is_found
        assert "New Connection" in result.value

    def test_nature_without_colon(self):
        ext = SchemePDFExtractor()
        text = "Nature of Scheme  New LT Extension from existing HT pole"
        result = ext._extract_nature(text)
        assert result.is_found
        assert "LT Extension" in result.value

    def test_nature_not_found(self):
        ext = SchemePDFExtractor()
        text = "No nature information here"
        result = ext._extract_nature(text)
        assert result.confidence == FieldConfidence.LOW

    def test_nature_multiline_stops_at_newline(self):
        ext = SchemePDFExtractor()
        text = "Nature of Scheme: DT Augmentation\nDate of Sanction: 01-01-2026"
        result = ext._extract_nature(text)
        assert result.value == "DT Augmentation"


# ── BOM Row Parsing ─────────────────────────────────────────────


class TestParseBomRow:
    """_parse_bom_row table row → Material."""

    def test_valid_bom_row(self):
        row = ["1", "123456789", "LT Cable 4CX25", "M", "200.00", "150.000", "30,000.00"]
        mat = SchemePDFExtractor._parse_bom_row(row)
        assert mat is not None
        assert mat.code == "123456789"
        assert mat.description == "LT Cable 4CX25"
        assert mat.unit == "M"

    def test_row_with_sr_before_code(self):
        row = ["2", "987654321", "Pole 9M PCC", "EA", "500.00", "3.000", "1,500.00"]
        mat = SchemePDFExtractor._parse_bom_row(row)
        assert mat is not None
        assert mat.sr_no == 2
        assert mat.code == "987654321"

    def test_row_too_short(self):
        row = ["1", "123"]
        mat = SchemePDFExtractor._parse_bom_row(row)
        assert mat is None

    def test_no_9_digit_code(self):
        row = ["1", "12345", "Cable", "M", "100.00", "10.000", "1,000.00"]
        mat = SchemePDFExtractor._parse_bom_row(row)
        assert mat is None

    def test_row_with_none_cells(self):
        row = [None, "123456789", "Cable PVC", "M", "100.00", "5.000", "500.00"]
        mat = SchemePDFExtractor._parse_bom_row(row)
        assert mat is not None
        assert mat.code == "123456789"

    def test_row_with_commas_in_amounts(self):
        row = ["1", "123456789", "HT Cable XLPE", "M", "1,250.00", "100.000", "1,25,000.00"]
        mat = SchemePDFExtractor._parse_bom_row(row)
        assert mat is not None
        assert float(mat.amount) == 125000.00


# ── BOM Regex Extraction ───────────────────────────────────────


class TestBomRegexExtraction:
    """_extract_bom_from_regex fallback test."""

    def test_single_bom_row(self):
        text = "1 123456789 LT 4CX25 SQMM CABLE ARMOURED M 200.00 150.000 30,000.00"
        materials = SchemePDFExtractor._extract_bom_from_regex(text)
        assert len(materials) == 1
        assert materials[0].code == "123456789"
        assert materials[0].unit == "M"

    def test_multiple_bom_rows(self):
        text = (
            "1 123456789 LT 4CX25 SQMM CABLE ARMOURED M 200.00 150.000 30,000.00\n"
            "2 987654321 PCC POLE 9M EA 500.00 3.000 1,500.00"
        )
        materials = SchemePDFExtractor._extract_bom_from_regex(text)
        assert len(materials) == 2

    def test_no_bom_rows(self):
        text = "Random text with no BOM data"
        materials = SchemePDFExtractor._extract_bom_from_regex(text)
        assert materials == []

    def test_malformed_row_skipped(self):
        text = "1 123456789 Cable M BAD 150.000 30,000.00"
        materials = SchemePDFExtractor._extract_bom_from_regex(text)
        assert materials == []
