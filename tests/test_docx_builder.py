"""Tests for app.builders.docx_builder."""

from pathlib import Path

import pytest

from app.builders.docx_builder import DocxBuilder
from app.domain.enums import WorkType
from app.domain.models import Case, Material


class TestDocxBuilder:
    def test_build_summary_creates_file(self, tmp_path, sample_case):
        builder = DocxBuilder()
        output = tmp_path / "test_summary.docx"
        result = builder.build_summary(sample_case, output)
        assert result.exists()
        assert result.suffix == ".docx"
        assert result.stat().st_size > 0

    def test_build_summary_with_materials(self, tmp_path):
        case = Case(
            order_no="000070012345",
            notification_no="NC12345678",
            applicant_name="Test User",
            address="Test Address",
            zone="Zone-1",
            district="NRL",
            work_type=WorkType.LT_STANDARD,
            grand_total=50000,
            materials=[
                Material(description="Cable", quantity=100, unit="MTR"),
                Material(description="Pole", quantity=2, unit="NO"),
                Material(description="Box", quantity=1, unit="NO"),
                Material(description="Sundry item", quantity=5, unit="NO"),
            ],
        )
        output = tmp_path / "summary_with_mats.docx"
        result = builder = DocxBuilder()
        path = builder.build_summary(case, output)
        assert path.exists()

    def test_build_summary_dt_augmentation(self, tmp_path):
        case = Case(
            order_no="000070099999",
            notification_no="NC99999999",
            applicant_name="DT User",
            address="DT Address",
            work_type=WorkType.DT_AUGMENTATION,
            existing_dt_capacity="200 KVA",
            new_transformer_rating="400 KVA",
            acb_description="ACB 400A",
            grand_total=250000,
        )
        builder = DocxBuilder()
        output = tmp_path / "dt_summary.docx"
        path = builder.build_summary(case, output)
        assert path.exists()

    def test_build_with_cost_image(self, tmp_path, sample_case):
        builder = DocxBuilder()
        # Create a minimal PNG image (1x1 white pixel)
        import struct
        import zlib

        def _make_png():
            sig = b"\x89PNG\r\n\x1a\n"
            ihdr_data = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
            ihdr_crc = zlib.crc32(b"IHDR" + ihdr_data) & 0xFFFFFFFF
            ihdr = struct.pack(">I", 13) + b"IHDR" + ihdr_data + struct.pack(">I", ihdr_crc)
            raw = zlib.compress(b"\x00\xff\xff\xff")
            idat_crc = zlib.crc32(b"IDAT" + raw) & 0xFFFFFFFF
            idat = struct.pack(">I", len(raw)) + b"IDAT" + raw + struct.pack(">I", idat_crc)
            iend_crc = zlib.crc32(b"IEND") & 0xFFFFFFFF
            iend = struct.pack(">I", 0) + b"IEND" + struct.pack(">I", iend_crc)
            return sig + ihdr + idat + iend

        png_bytes = _make_png()
        output = tmp_path / "summary_with_image.docx"
        path = builder.build_summary(sample_case, output, cost_table_image=png_bytes)
        assert path.exists()
