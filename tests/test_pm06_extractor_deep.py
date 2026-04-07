"""Deep tests for PM06ExcelExtractor — tapping pole, LT extension materials, edge cases."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.domain.enums import FieldConfidence
from app.extractors.pm06_excel_extractor import PM06ExcelExtractor


class TestTappingPoleStrategy1:
    """Row-scan for pole code in row containing 'tapping' keyword."""

    def test_pole_code_in_row(self):
        ext = PM06ExcelExtractor()
        ws = MagicMock()
        ws.iter_rows.return_value = [
            (1, "Tapping Point", "Pole", "HT572-63/21A", None),
        ]
        label_map = {}
        result = ext._extract_tapping_pole(ws, label_map)
        assert result.value == "HT572-63/21A"
        assert result.confidence == FieldConfidence.HIGH

    def test_uht_prefix(self):
        ext = PM06ExcelExtractor()
        ws = MagicMock()
        ws.iter_rows.return_value = [
            (1, "Tapping Point", "Pole", "UHT512-27", None),
        ]
        result = ext._extract_tapping_pole(ws, {})
        assert result.value == "UHT512-27"

    def test_bare_numeric_code(self):
        ext = PM06ExcelExtractor()
        ws = MagicMock()
        ws.iter_rows.return_value = [
            (1, "Tapping Point", "Pole", "511-65/5", None),
        ]
        result = ext._extract_tapping_pole(ws, {})
        assert result.value == "511-65/5"

    def test_garbage_value_skipped_uses_last_cell(self):
        ext = PM06ExcelExtractor()
        ws = MagicMock()
        ws.iter_rows.return_value = [
            (1, "Tapping Point", "Pole", "Near Transformer Room Block C", None),
        ]
        result = ext._extract_tapping_pole(ws, {})
        assert result.value is not None
        assert "Transformer" in result.value


class TestTappingPoleStrategy2:
    """Fallback to label_map lookup."""

    def test_label_map_tapping(self):
        ext = PM06ExcelExtractor()
        ws = MagicMock()
        ws.iter_rows.return_value = []
        label_map = {"tapping point": "HT517-63/21A"}
        result = ext._extract_tapping_pole(ws, label_map)
        assert result.value == "HT517-63/21A"

    def test_garbage_in_label_map_skipped(self):
        ext = PM06ExcelExtractor()
        ws = MagicMock()
        ws.iter_rows.return_value = []
        label_map = {"tapping point": "Pole"}
        result = ext._extract_tapping_pole(ws, label_map)
        # "Pole" is garbage — should fall through to strategy 3 or not_found
        assert result.confidence == FieldConfidence.LOW or result.value != "Pole"


class TestTappingPoleStrategy3:
    """Mine pole code from substation/scope/reason text."""

    def test_pole_from_scope_text(self):
        ext = PM06ExcelExtractor()
        ws = MagicMock()
        ws.iter_rows.return_value = []
        label_map = {
            "tapping point": "Pole",  # garbage
            "scope of work": "LT extension from HT572-63/21A towards premises",
        }
        result = ext._extract_tapping_pole(ws, label_map)
        assert "572" in result.value

    def test_pole_from_station_name(self):
        ext = PM06ExcelExtractor()
        ws = MagicMock()
        ws.iter_rows.return_value = []
        label_map = {
            "station name": "HT411-27, Block A Complex",
        }
        result = ext._extract_tapping_pole(ws, label_map)
        assert "411" in result.value

    def test_not_found_returns_low(self):
        ext = PM06ExcelExtractor()
        ws = MagicMock()
        ws.iter_rows.return_value = []
        result = ext._extract_tapping_pole(ws, {})
        assert result.confidence == FieldConfidence.LOW


class TestLTExtensionMaterials:
    """PM-8: LT extension materials sub-table."""

    def test_basic_extraction(self):
        ws = MagicMock()
        ws.iter_rows.return_value = [
            ("Sr", "Length of LT line extension Material", "Qty"),
            (1, "PCC Pole 9M", 3.0),
            (2, "LT Cable 4Cx95mm", 200.0),
            ("Reason for work", None, None),
        ]
        materials = PM06ExcelExtractor._extract_lt_extension_materials(ws)
        assert len(materials) == 2
        assert materials[0]["description"] == "PCC Pole 9M"
        assert materials[0]["quantity"] == 3.0
        assert materials[1]["description"] == "LT Cable 4Cx95mm"

    def test_stops_at_reason(self):
        ws = MagicMock()
        ws.iter_rows.return_value = [
            ("Sr", "Length of LT line extension Material", "Qty"),
            (1, "PCC Pole 9M", 3.0),
            ("Reason for scheme", None, None),
            (2, "Cable 95mm", 100.0),  # Should not be captured
        ]
        materials = PM06ExcelExtractor._extract_lt_extension_materials(ws)
        assert len(materials) == 1

    def test_empty_section(self):
        ws = MagicMock()
        ws.iter_rows.return_value = [("Other header", None, None)]
        materials = PM06ExcelExtractor._extract_lt_extension_materials(ws)
        assert materials == []

    def test_material_without_quantity(self):
        ws = MagicMock()
        ws.iter_rows.return_value = [
            ("Sr", "Length of LT line extension Material", "Qty"),
            (1, "PCC Pole 9M", None),
        ]
        materials = PM06ExcelExtractor._extract_lt_extension_materials(ws)
        assert len(materials) == 1
        assert materials[0]["quantity"] is None


# ── PM-1: _find_format_sheet ────────────────────────────────────


class TestFindFormatSheet:
    """Tests for sheet discovery by name and header fallback."""

    def test_exact_name_match(self):
        wb = MagicMock()
        wb.sheetnames = ["Format", "Sheet2"]
        wb.__getitem__ = MagicMock(return_value="ws_format")
        result = PM06ExcelExtractor._find_format_sheet(wb)
        assert result == "ws_format"

    def test_trailing_space_name(self):
        wb = MagicMock()
        wb.sheetnames = ["Format ", "Sheet2"]
        ws = MagicMock()
        wb.__getitem__ = MagicMock(return_value=ws)
        result = PM06ExcelExtractor._find_format_sheet(wb)
        assert result is not None

    def test_case_insensitive_name(self):
        wb = MagicMock()
        wb.sheetnames = ["FORMAT", "Sheet2"]
        wb.__getitem__ = MagicMock(return_value="ws")
        result = PM06ExcelExtractor._find_format_sheet(wb)
        assert result is not None

    def test_fallback_to_header_content(self):
        """If no 'Format' sheet, check A1 for 'format of lt'."""
        wb = MagicMock()
        wb.sheetnames = ["Sheet1", "Data"]

        ws1 = MagicMock()
        cell_a1 = MagicMock()
        cell_a1.value = "Format of LT Line Extension"
        ws1.cell.return_value = cell_a1

        ws2 = MagicMock()
        cell_a1_2 = MagicMock()
        cell_a1_2.value = "Some Other Header"
        ws2.cell.return_value = cell_a1_2

        wb.__getitem__ = MagicMock(side_effect=lambda name: ws1 if name == "Sheet1" else ws2)
        result = PM06ExcelExtractor._find_format_sheet(wb)
        assert result == ws1

    def test_no_match_returns_none(self):
        wb = MagicMock()
        wb.sheetnames = ["Data", "Summary"]

        ws1 = MagicMock()
        cell = MagicMock()
        cell.value = "Sales Report"
        ws1.cell.return_value = cell

        ws2 = MagicMock()
        cell2 = MagicMock()
        cell2.value = None
        ws2.cell.return_value = cell2

        wb.__getitem__ = MagicMock(side_effect=lambda name: ws1 if name == "Data" else ws2)
        result = PM06ExcelExtractor._find_format_sheet(wb)
        assert result is None


# ── PM-3: _build_label_value_map ────────────────────────────────


class TestBuildLabelValueMap:
    """Tests for label-value map construction."""

    def test_basic_label_value(self):
        ws = MagicMock()
        ws.iter_rows.return_value = [
            ("Order Number", "60038419", None),
            ("Consumer Name", "Ram Kumar", None),
        ]
        result = PM06ExcelExtractor._build_label_value_map(ws)
        assert len(result) >= 2

    def test_value_in_later_column(self):
        ws = MagicMock()
        ws.iter_rows.return_value = [
            ("Address", None, None, "123 Main Street Delhi"),
        ]
        result = PM06ExcelExtractor._build_label_value_map(ws)
        # Should find value skipping None columns
        found = any("123" in str(v) for v in result.values())
        assert found

    def test_empty_rows_skipped(self):
        ws = MagicMock()
        ws.iter_rows.return_value = [
            (None, None, None),
            ("", None, None),
            ("X", None, None),  # Too short (1 char) to be a label
        ]
        result = PM06ExcelExtractor._build_label_value_map(ws)
        assert len(result) == 0

    def test_duplicate_labels_first_wins(self):
        ws = MagicMock()
        ws.iter_rows.return_value = [
            ("Zone", "411", None),
            ("Zone", "999", None),
        ]
        result = PM06ExcelExtractor._build_label_value_map(ws)
        # First value should win
        zone_val = None
        for k, v in result.items():
            if "zone" in k:
                zone_val = v
                break
        assert zone_val == "411"

    def test_label_in_column_b(self):
        ws = MagicMock()
        ws.iter_rows.return_value = [
            (1, "DT Capacity", "100 KVA", None),
        ]
        result = PM06ExcelExtractor._build_label_value_map(ws)
        found = any("100" in str(v) for v in result.values())
        assert found


# ── PM-5: _find_scope_of_work ───────────────────────────────────


class TestFindScopeOfWork:
    """Tests for three-strategy scope extraction."""

    def test_strategy1_label_map(self):
        ws = MagicMock()
        ws.iter_rows.return_value = []
        label_map = {"scope of work": "LT extension from HT572-63 towards premise for 200 meters"}
        result = PM06ExcelExtractor._find_scope_of_work(ws, label_map)
        assert result is not None
        assert "LT extension" in result

    def test_strategy1_short_scope_skipped(self):
        ws = MagicMock()
        ws.iter_rows.return_value = []
        label_map = {"scope of work": "NA"}  # Too short (<= 5 chars)
        result = PM06ExcelExtractor._find_scope_of_work(ws, label_map)
        assert result is None

    def test_strategy2_proximity_scan(self):
        ws = MagicMock()
        ws.iter_rows.return_value = [
            ("Scope of Work", None, "LT extension from HT572 towards new consumer premises"),
        ]
        label_map = {}  # Strategy 1 won't find anything
        result = PM06ExcelExtractor._find_scope_of_work(ws, label_map)
        assert result is not None
        assert "LT extension" in result

    def test_strategy3_keyword_ranking(self):
        ws = MagicMock()
        ws.iter_rows.return_value = [
            ("Some unrelated", None, None),
            (None, "LT extension from pole towards premises for electrification of new consumer", None),
        ]
        label_map = {}
        result = PM06ExcelExtractor._find_scope_of_work(ws, label_map)
        assert result is not None
        assert "extension" in result.lower()

    def test_no_scope_found(self):
        ws = MagicMock()
        ws.iter_rows.return_value = [
            ("Name", "Value", None),
        ]
        result = PM06ExcelExtractor._find_scope_of_work(ws, {})
        assert result is None


# ── PM-6: _extract_feeder_details ───────────────────────────────


class TestExtractFeederDetails:
    """Tests for feeder sub-table extraction."""

    def test_basic_feeder_extraction(self):
        ws = MagicMock()
        ws.iter_rows.return_value = [
            ("Sr", "ACB No", "Loading Amps"),
            (1, 101, 250.0),
            (2, 102, 300.0),
            ("Tapping Point", None, None),
        ]
        feeders = PM06ExcelExtractor._extract_feeder_details(ws)
        assert len(feeders) == 2
        assert feeders[0].sr_no == 1
        assert feeders[0].acb_no == 101
        assert feeders[0].loading_amps == 250.0

    def test_stops_at_tapping_keyword(self):
        ws = MagicMock()
        ws.iter_rows.return_value = [
            ("Sr", "ACB No", "Loading Amps"),
            (1, 101, 250.0),
            ("Tapping Point", "Pole", "HT572-63/21A"),
            (2, 102, 300.0),  # Should not be captured
        ]
        feeders = PM06ExcelExtractor._extract_feeder_details(ws)
        assert len(feeders) == 1

    def test_no_feeder_section(self):
        ws = MagicMock()
        ws.iter_rows.return_value = [
            ("Name", "Value", None),
            ("Order", "60038419", None),
        ]
        feeders = PM06ExcelExtractor._extract_feeder_details(ws)
        assert feeders == []

    def test_feeder_with_two_nums_no_loading(self):
        ws = MagicMock()
        ws.iter_rows.return_value = [
            ("Sr", "ACB No", "Loading Amps"),
            (1, 101),
        ]
        feeders = PM06ExcelExtractor._extract_feeder_details(ws)
        # Only 2 nums but needs >= 2
        assert len(feeders) == 1
        assert feeders[0].loading_amps is None


# ── PM-4: _find_field fuzzy matching ────────────────────────────


class TestFindField:
    def test_all_keywords_match(self):
        label_map = {"dt capacity existing": "100 KVA"}
        result = PM06ExcelExtractor._find_field(label_map, ["dt", "capacity"])
        assert result == "100 KVA"

    def test_partial_keywords_no_match(self):
        label_map = {"order number": "60038419"}
        result = PM06ExcelExtractor._find_field(label_map, ["dt", "capacity"])
        assert result is None

    def test_single_keyword(self):
        label_map = {"consumer address": "123 Street"}
        result = PM06ExcelExtractor._find_field(label_map, ["address"])
        assert result == "123 Street"
