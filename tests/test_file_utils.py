"""Tests for app.infrastructure.file_utils."""

from pathlib import Path

import pytest

from app.infrastructure.file_utils import compute_file_hash, validate_file_type


class TestValidateFileType:
    def test_valid_pdf(self, tmp_path):
        f = tmp_path / "test.pdf"
        f.write_bytes(b"%PDF-1.4 some content")
        assert validate_file_type(str(f), "pdf") is True

    def test_invalid_pdf(self, tmp_path):
        f = tmp_path / "test.pdf"
        f.write_bytes(b"not a pdf file")
        assert validate_file_type(str(f), "pdf") is False

    def test_valid_xlsx(self, tmp_path):
        f = tmp_path / "test.xlsx"
        f.write_bytes(b"PK\x03\x04 some content")
        assert validate_file_type(str(f), "xlsx") is True


class TestComputeFileHash:
    def test_consistent_hash(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello world")
        h1 = compute_file_hash(str(f))
        h2 = compute_file_hash(str(f))
        assert h1 == h2

    def test_different_content_different_hash(self, tmp_path):
        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.txt"
        f1.write_text("hello")
        f2.write_text("world")
        assert compute_file_hash(str(f1)) != compute_file_hash(str(f2))
