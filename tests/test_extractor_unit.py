"""Unit tests for extractors — scheme PDF, PM06 Excel, site visit, factory.

Uses mocking to isolate extractor logic from actual PDF/Excel files.
Tests regex patterns, field extraction, edge cases, and error paths.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from app.domain.enums import FieldConfidence, FileType
from app.domain.models import ExtractionResult, Material
from app.extractors.base_extractor import BaseExtractor
from app.extractors.extractor_factory import ExtractorFactory
from app.extractors.scheme_pdf_extractor import SchemePDFExtractor
from app.extractors.pm06_excel_extractor import PM06ExcelExtractor


# ── ExtractorFactory ────────────────────────────────────────────


class TestExtractorFactory:
    def test_scheme_pdf_returns_correct_type(self):
        ext = ExtractorFactory.get_extractor(FileType.SCHEME_PDF)
        assert isinstance(ext, SchemePDFExtractor)

    def test_pm06_excel_returns_correct_type(self):
        ext = ExtractorFactory.get_extractor(FileType.PM06_EXCEL)
        assert isinstance(ext, PM06ExcelExtractor)

    def test_site_visit_returns_correct_type(self):
        from app.extractors.site_visit_extractor import SiteVisitExtractor
        ext = ExtractorFactory.get_extractor(FileType.SITE_VISIT_PDF)
        assert isinstance(ext, SiteVisitExtractor)

    def test_all_file_types_registered(self):
        for ft in FileType:
            ext = ExtractorFactory.get_extractor(ft)
            assert isinstance(ext, BaseExtractor)


# ── BaseExtractor error handling ────────────────────────────────


class TestBaseExtractorErrorPaths:
    def test_file_not_found_returns_error_dict(self, tmp_path):
        ext = SchemePDFExtractor()
        result = ext.extract(tmp_path / "nonexistent.pdf")
        assert "_error" in result
        assert result["_error"].confidence == FieldConfidence.LOW

    def test_permission_error_returns_error_dict(self, tmp_path):
        ext = SchemePDFExtractor()
        fake_file = tmp_path / "locked.pdf"
        fake_file.write_bytes(b"%PDF-1.4 test")
        with patch.object(SchemePDFExtractor, "_do_extract", side_effect=PermissionError("denied")):
            result = ext.extract(fake_file)
        assert "_error" in result

    def test_generic_exception_returns_error_dict(self, tmp_path):
        ext = SchemePDFExtractor()
        fake_file = tmp_path / "bad.pdf"
        fake_file.write_bytes(b"%PDF-1.4 test")
        with patch.object(SchemePDFExtractor, "_do_extract", side_effect=RuntimeError("boom")):
            result = ext.extract(fake_file)
        assert "_error" in result
        assert "boom" in result["_error"].message


# ── SchemePDFExtractor field logic ──────────────────────────────


class TestSchemePDFOrderNo:
    """SC-2: Order number extraction."""

    def test_extract_from_page_header(self):
        ext = SchemePDFExtractor()
        raw = "Page No.: 1 Order No.: 60038419\nSome body text"
        cleaned = "Some body text"
        result = ext._extract_order_no(raw, cleaned)
        assert result.value == "60038419"
        assert result.confidence == FieldConfidence.HIGH

    def test_extract_from_body_fallback(self):
        ext = SchemePDFExtractor()
        raw = "No header here"
        cleaned = "Order No.: 60038551 some text"
        result = ext._extract_order_no(raw, cleaned)
        assert result.value == "60038551"

    def test_not_found_returns_low(self):
        ext = SchemePDFExtractor()
        result = ext._extract_order_no("no match", "no match")
        assert result.confidence == FieldConfidence.LOW
        assert result.value is None


class TestSchemePDFNotificationNos:
    """SC-3: Notification number extraction."""

    def test_single_nc_number(self):
        nos = SchemePDFExtractor._extract_notification_nos("N/C 1234567890 applicant")
        assert nos == ["1234567890"]

    def test_multiple_nc_numbers(self):
        text = "N/C 1234567890 and N/C 9876543210 two applicants"
        nos = SchemePDFExtractor._extract_notification_nos(text)
        assert "1234567890" in nos
        assert "9876543210" in nos

    def test_deduplication(self):
        text = "N/C 1234567890 line1\nN/C 1234567890 line2"
        nos = SchemePDFExtractor._extract_notification_nos(text)
        assert len(nos) == 1

    def test_slash_format(self):
        text = "N/C 1234567890/ 9876543210"
        nos = SchemePDFExtractor._extract_notification_nos(text)
        assert len(nos) >= 1

    def test_empty_text_returns_empty(self):
        nos = SchemePDFExtractor._extract_notification_nos("")
        assert nos == []


class TestSchemePDFName:
    """SC-4: Name extraction."""

    def test_name_after_nc_regex(self):
        ext = SchemePDFExtractor()
        text = "N/C 1234567890 Mr. RAJESH KUMAR\nMobile 9876543210"
        result = ext._extract_name(text)
        assert result.is_found
        assert "RAJESH" in result.value

    def test_name_not_found_returns_low(self):
        ext = SchemePDFExtractor()
        result = ext._extract_name("no notification number here")
        assert result.confidence == FieldConfidence.LOW


class TestSchemePDFAddress:
    """SC-5: Address extraction."""

    def test_address_stops_at_mobile(self):
        ext = SchemePDFExtractor()
        text = "N/C 1234567890\n123 Test Street Delhi\nMobile: 9876543210"
        result = ext._extract_address(text)
        assert result.is_found
        assert "Mobile" not in result.value

    def test_address_stops_at_email(self):
        ext = SchemePDFExtractor()
        text = "N/C 1234567890\n456 Market Road\nEmail test@test.com"
        result = ext._extract_address(text)
        assert result.is_found
        assert "Email" not in result.value


class TestSchemePDFPin:
    """SC-5: PIN code extraction."""

    def test_valid_delhi_pin(self):
        ext = SchemePDFExtractor()
        text = "Address: 110001 Delhi"
        result = ext._extract_pin(text)
        assert result.value == "110001"

    def test_non_delhi_pin_not_matched(self):
        ext = SchemePDFExtractor()
        text = "Address: 560001 Bangalore"
        result = ext._extract_pin(text)
        assert result.value is None or result.confidence == FieldConfidence.LOW


class TestSchemePDFCosts:
    """SC-6: Cost extraction."""

    def test_extracts_bom_total(self):
        ext = SchemePDFExtractor()
        text = "Bill of material 1,25,000.50\nBill of services 5,000.00"
        result = ext._extract_costs(text)
        assert "bom_total" in result
        assert result["bom_total"].is_found

    def test_extracts_grand_total(self):
        ext = SchemePDFExtractor()
        text = "Total (Rs.) 1,50,000.75"
        result = ext._extract_costs(text)
        assert "grand_total" in result
        assert result["grand_total"].is_found

    def test_missing_costs_return_not_found(self):
        ext = SchemePDFExtractor()
        result = ext._extract_costs("nothing useful here")
        for key in ["bom_total", "bos_total", "eif_total", "rrc_total", "grand_total"]:
            assert key in result


class TestSchemePDFMaterials:
    """SC-7: BOM material parsing via regex."""

    def test_parse_bom_row_regex(self):
        from app.domain.constants import RE_BOM_ROW
        text = "1 123456789 CABLE 1.1KV AL 4CX25 SQMM M 100.00 150.000 15,000.00"
        match = RE_BOM_ROW.search(text)
        assert match is not None
        assert match.group(2) == "123456789"

    def test_bom_row_multiple_materials(self):
        from app.domain.constants import RE_BOM_ROW
        text = (
            "1 123456789 CABLE 4CX25 SQMM M 100.00 150.000 15,000.00\n"
            "2 987654321 8MTR PSCC POLE NO 3.00 5,000.000 15,000.00\n"
        )
        matches = RE_BOM_ROW.findall(text)
        assert len(matches) == 2


# ── PM06ExcelExtractor ──────────────────────────────────────────


class TestPM06FindFormatSheet:
    """PM-1: Sheet name matching."""

    def test_exact_match_stripped(self):
        wb = MagicMock()
        wb.sheetnames = ["Format ", "Sheet1"]
        ws_mock = MagicMock()
        wb.__getitem__ = MagicMock(return_value=ws_mock)
        result = PM06ExcelExtractor._find_format_sheet(wb)
        assert result is not None

    def test_fallback_to_header_scan(self):
        wb = MagicMock()
        wb.sheetnames = ["Sheet1"]
        ws = MagicMock()
        ws.cell.return_value.value = "Format of LT Line Extension"
        wb.__getitem__ = MagicMock(return_value=ws)
        result = PM06ExcelExtractor._find_format_sheet(wb)
        assert result is not None

    def test_no_matching_sheet_returns_none(self):
        wb = MagicMock()
        wb.sheetnames = ["Data", "Summary"]
        ws1 = MagicMock()
        ws1.cell.return_value.value = "Some other content"
        ws2 = MagicMock()
        ws2.cell.return_value.value = "Nothing related"
        wb.__getitem__ = MagicMock(side_effect=[ws1, ws2])
        result = PM06ExcelExtractor._find_format_sheet(wb)
        assert result is None


class TestPM06LabelValueMap:
    """PM-3: Row scanning for label-value pairs."""

    def test_basic_label_value_extraction(self):
        ws = MagicMock()
        ws.iter_rows.return_value = [
            ("Order No.", "60038419", None, None, None),
            ("Consumer Name", "Rajesh Kumar", None, None, None),
        ]
        label_map = PM06ExcelExtractor._build_label_value_map(ws)
        assert "order no" in label_map
        assert label_map["order no"] == "60038419"

    def test_value_in_later_column(self):
        ws = MagicMock()
        ws.iter_rows.return_value = [
            ("DT Code", None, None, "ABC123", None),
        ]
        label_map = PM06ExcelExtractor._build_label_value_map(ws)
        assert "dt code" in label_map
        assert label_map["dt code"] == "ABC123"

    def test_first_occurrence_wins(self):
        ws = MagicMock()
        ws.iter_rows.return_value = [
            ("Zone", "411", None, None, None),
            ("Zone", "999", None, None, None),
        ]
        label_map = PM06ExcelExtractor._build_label_value_map(ws)
        assert label_map["zone"] == "411"


class TestPM06FuzzyMatching:
    """PM-4: Keyword-based field lookup."""

    def test_all_keywords_must_match(self):
        label_map = {"consumer name": "Rajesh", "consumer address": "Delhi"}
        result = PM06ExcelExtractor._find_field(label_map, ["consumer", "name"])
        assert result == "Rajesh"

    def test_partial_keyword_no_match(self):
        label_map = {"consumer address": "Delhi"}
        result = PM06ExcelExtractor._find_field(label_map, ["consumer", "name"])
        assert result is None

    def test_empty_label_map(self):
        result = PM06ExcelExtractor._find_field({}, ["order"])
        assert result is None


class TestPM06FeederDetails:
    """PM-6: Feeder sub-table extraction."""

    def test_basic_feeder_extraction(self):
        ws = MagicMock()
        ws.iter_rows.return_value = [
            ("Sr", "ACB No.", "Loading Amps"),
            (1, 101, 250.0),
            (2, 102, 180.5),
            ("Tapping Point", None, None),
        ]
        feeders = PM06ExcelExtractor._extract_feeder_details(ws)
        assert len(feeders) == 2
        assert feeders[0].acb_no == 101

    def test_feeder_stops_at_tapping(self):
        ws = MagicMock()
        ws.iter_rows.return_value = [
            ("Sr", "ACB No.", "Loading Amps"),
            (1, 101, 250.0),
            ("Tapping Pole", "HT572", None),
            (3, 103, 300.0),  # should not be included
        ]
        feeders = PM06ExcelExtractor._extract_feeder_details(ws)
        assert len(feeders) == 1

    def test_empty_feeder_section(self):
        ws = MagicMock()
        ws.iter_rows.return_value = [
            ("Some other header", None, None),
        ]
        feeders = PM06ExcelExtractor._extract_feeder_details(ws)
        assert feeders == []


class TestPM06ScopeOfWork:
    """PM-5: Three-strategy scope extraction."""

    def test_strategy_1_label_map(self):
        ws = MagicMock()
        ws.iter_rows.return_value = []
        label_map = {"scope of work": "LT extension from pole HT572 towards premises"}
        result = PM06ExcelExtractor._find_scope_of_work(ws, label_map)
        assert result is not None
        assert "LT extension" in result

    def test_strategy_2_proximity_scan(self):
        ws = MagicMock()
        ws.iter_rows.return_value = [
            ("Scope of work", None, "LT extension from pole 123 for 200 mtrs of cable"),
        ]
        result = PM06ExcelExtractor._find_scope_of_work(ws, {})
        assert result is not None

    def test_strategy_3_longest_engineering_text(self):
        ws = MagicMock()
        ws.iter_rows.return_value = [
            (None, "LT extension from pole towards premises for connection laying 250 mtrs", None),
        ]
        result = PM06ExcelExtractor._find_scope_of_work(ws, {})
        assert result is not None

    def test_no_scope_found(self):
        ws = MagicMock()
        ws.iter_rows.return_value = [("Header", "Value")]
        result = PM06ExcelExtractor._find_scope_of_work(ws, {})
        assert result is None


# ── SiteVisitExtractor ──────────────────────────────────────────


class TestSiteVisitGracefulDegradation:
    """SVF-1, SVF-5: Tesseract missing handling."""

    def test_tesseract_missing_returns_low_confidence(self, tmp_path):
        """When Tesseract unavailable, return LOW confidence for both fields."""
        from app.extractors.site_visit_extractor import SiteVisitExtractor
        ext = SiteVisitExtractor()
        # Create a minimal PDF file
        fake_pdf = tmp_path / "site_visit.pdf"
        fake_pdf.write_bytes(b"%PDF-1.4 minimal content")

        with patch("app.extractors.site_visit_extractor.TESSERACT_AVAILABLE", False):
            result = ext._do_extract(fake_pdf)
        assert result["order_no"].confidence == FieldConfidence.LOW
        assert result["notification_no"].confidence == FieldConfidence.LOW
        assert "Tesseract" in result["order_no"].message
