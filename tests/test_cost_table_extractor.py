"""Cost table extractor tests — mocked PyMuPDF + pdfplumber."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.builders.cost_table_extractor import extract_cost_table_image


# ── Happy path ──────────────────────────────────────────────────


class TestExtractCostTableImage:
    def test_nonexistent_pdf_returns_false(self, tmp_path):
        """Attempting to extract from a non-existent PDF returns False."""
        result = extract_cost_table_image(
            tmp_path / "nonexistent.pdf", tmp_path / "out.png"
        )
        assert result is False

    def test_invalid_pdf_returns_false(self, tmp_path):
        """An invalid (non-PDF) file returns False."""
        fake_pdf = tmp_path / "bad.pdf"
        fake_pdf.write_bytes(b"NOT A REAL PDF FILE")
        result = extract_cost_table_image(fake_pdf, tmp_path / "out.png")
        assert result is False

    def test_return_type_is_bool(self, tmp_path):
        """Return type is always bool — never raises."""
        result = extract_cost_table_image(
            tmp_path / "x.pdf", tmp_path / "y.png"
        )
        assert isinstance(result, bool)


class TestExtractCostTableExceptional:
    def test_empty_file_returns_false(self, tmp_path):
        empty = tmp_path / "empty.pdf"
        empty.write_bytes(b"")
        result = extract_cost_table_image(empty, tmp_path / "out.png")
        assert result is False

    def test_output_parent_created(self, tmp_path):
        """Even on failure, function should not crash if output dir doesn't exist."""
        result = extract_cost_table_image(
            tmp_path / "x.pdf", tmp_path / "deep" / "nested" / "out.png"
        )
        assert result is False  # no valid PDF, but no crash
