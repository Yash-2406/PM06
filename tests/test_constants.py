"""Tests for app.domain.constants — verify key constants exist and have correct types."""

from app.domain.constants import (
    APP_TITLE,
    COST_LOWER_BOUND,
    COST_UPPER_BOUND,
    MAX_MAJOR_MATERIALS,
    OCR_CONFIDENCE_THRESHOLD,
    RE_BOM_ROW,
    RE_DELHI_PIN,
    RE_NC_NOTIF,
    RE_PAGE_HEADER,
    TRACKER_COLUMNS,
    VALID_CATEGORIES,
    WT_ABC_KW,
    WT_DT_AUG_NATURE_KW,
    WT_TRANSFORMER_KW,
)
import re


class TestConstants:
    def test_app_title(self):
        assert isinstance(APP_TITLE, str)
        assert "TPDDL" in APP_TITLE

    def test_tracker_columns(self):
        assert isinstance(TRACKER_COLUMNS, list)
        assert len(TRACKER_COLUMNS) >= 10

    def test_regex_patterns_compiled(self):
        assert isinstance(RE_NC_NOTIF, re.Pattern)
        assert isinstance(RE_DELHI_PIN, re.Pattern)
        assert isinstance(RE_PAGE_HEADER, re.Pattern)
        assert isinstance(RE_BOM_ROW, re.Pattern)

    def test_nc_notif_matches(self):
        assert RE_NC_NOTIF.search("NC1234567890")
        assert not RE_NC_NOTIF.search("XY123")

    def test_delhi_pin(self):
        assert RE_DELHI_PIN.match("110001")
        assert not RE_DELHI_PIN.match("200000")

    def test_cost_bounds(self):
        assert COST_LOWER_BOUND < COST_UPPER_BOUND
        assert COST_LOWER_BOUND > 0

    def test_valid_categories(self):
        assert isinstance(VALID_CATEGORIES, set)
        assert "DOMESTIC" in VALID_CATEGORIES

    def test_work_type_keywords(self):
        assert isinstance(WT_TRANSFORMER_KW, list)
        assert isinstance(WT_DT_AUG_NATURE_KW, list)
        assert isinstance(WT_ABC_KW, list)
