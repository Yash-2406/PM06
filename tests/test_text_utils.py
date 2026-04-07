"""Tests for app.infrastructure.text_utils."""

from app.infrastructure.text_utils import (
    clean_scope_text,
    normalise_dt_capacity,
    normalise_label,
    strip_pdf_headers,
)


class TestStripPdfHeaders:
    def test_removes_page_numbers(self):
        text = "Page No.: 1 Order No.: 12345678\nSome content"
        result = strip_pdf_headers(text)
        assert "Page No." not in result
        assert "Some content" in result

    def test_preserves_content(self):
        text = "Normal content here"
        result = strip_pdf_headers(text)
        assert "Normal content here" in result


class TestNormaliseLabel:
    def test_removes_colons(self):
        assert normalise_label("Name :") == "name"

    def test_lowercases(self):
        assert normalise_label("APPLICANT NAME") == "applicant name"

    def test_strips_whitespace(self):
        assert normalise_label("  Zone  ") == "zone"


class TestNormaliseDtCapacity:
    def test_standard_format(self):
        result = normalise_dt_capacity("400 KVA DT")
        assert "400" in result
        assert "kVA" in result

    def test_none_input(self):
        result = normalise_dt_capacity(None)
        assert result is None


class TestCleanScopeText:
    def test_cleans_extra_whitespace(self):
        result = clean_scope_text("LT  extension   from   pole")
        # Should reduce multiple spaces
        assert "  " not in result or result == "LT extension from pole"
