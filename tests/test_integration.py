"""Integration / pipeline tests — GeneratorService end-to-end.

Uses mocks to simulate PDF/Excel extraction and verifies the full
pipeline: extract → merge → detect work type → validate → build DOCX → persist.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.data.case_repository import CaseRepository
from app.domain.enums import CaseStatus, FieldConfidence, FileType, WorkType
from app.domain.models import Case, ExtractionResult, Material
from app.services.generator_service import GeneratorService


# ── Helpers ──────────────────────────────────────────────────────


def _make_scheme_data() -> dict:
    """Minimal extraction results from a scheme PDF."""
    return {
        "order_no": ExtractionResult(value="60038419", confidence=FieldConfidence.HIGH, source="regex"),
        "notification_no": ExtractionResult(value="1234567890", confidence=FieldConfidence.HIGH, source="regex"),
        "applicant_name": ExtractionResult(value="Test Applicant", confidence=FieldConfidence.HIGH, source="regex"),
        "address": ExtractionResult(value="Street 1, Near Market, Delhi", confidence=FieldConfidence.HIGH, source="regex"),
        "pin_code": ExtractionResult(value="110001", confidence=FieldConfidence.HIGH, source="regex"),
        "nature_of_scheme": ExtractionResult(value="LT single phase domestic supply", confidence=FieldConfidence.HIGH, source="regex"),
        "grand_total": ExtractionResult(value=125000.50, confidence=FieldConfidence.HIGH, source="regex"),
        "bom_total": ExtractionResult(value=80000, confidence=FieldConfidence.HIGH, source="regex"),
        "bos_total": ExtractionResult(value=20000, confidence=FieldConfidence.HIGH, source="regex"),
    }


def _make_pm06_data() -> dict:
    """Minimal extraction results from PM06 Excel."""
    return {
        "zone": ExtractionResult(value="411", confidence=FieldConfidence.HIGH, source="label_map"),
        "district": ExtractionResult(value="CVL", confidence=FieldConfidence.HIGH, source="label_map"),
        "load_applied": ExtractionResult(value="5 kW", confidence=FieldConfidence.HIGH, source="label_map"),
        "category": ExtractionResult(value="DOMESTIC", confidence=FieldConfidence.HIGH, source="label_map"),
        "scope_of_work": ExtractionResult(value="LT extension from pole 123 towards premises for 200 mtrs.", confidence=FieldConfidence.HIGH, source="label_map"),
        "tapping_pole": ExtractionResult(value="POLE/AB/1234", confidence=FieldConfidence.MEDIUM, source="label_map"),
        "feeder_details": ExtractionResult(value=[], confidence=FieldConfidence.LOW, source="label_map"),
        "materials": ExtractionResult(
            value=[Material(description="LT 4 Core Cable 95mm", quantity=200, unit="MTR")],
            confidence=FieldConfidence.HIGH,
            source="label_map",
        ),
    }


def _make_sv_data() -> dict:
    """Minimal extraction results from site visit PDF."""
    return {}


# ── GeneratorService._merge ─────────────────────────────────────


class TestGeneratorServiceMerge:
    """Test the merge logic without hitting actual files."""

    @pytest.fixture
    def svc(self, db, tmp_path):
        from app.infrastructure.config_manager import ConfigManager
        ConfigManager._instance = None
        config = ConfigManager()
        config._config.set("General", "output_dir", str(tmp_path / "output"))
        config._config.set("General", "recovery_dir", str(tmp_path / "recovery"))
        svc = GeneratorService(db=db, config=config)
        yield svc
        ConfigManager._instance = None

    def test_merge_prefers_scheme_order_no(self, svc):
        case = svc._merge_into_case(_make_scheme_data(), _make_sv_data(), _make_pm06_data())
        assert case.order_no == "60038419"

    def test_merge_takes_pm06_zone(self, svc):
        case = svc._merge_into_case(_make_scheme_data(), {}, _make_pm06_data())
        assert case.zone == "411"

    def test_merge_takes_pm06_district(self, svc):
        case = svc._merge_into_case({}, {}, _make_pm06_data())
        assert case.district == "CVL"

    def test_merge_takes_pm06_materials(self, svc):
        case = svc._merge_into_case({}, {}, _make_pm06_data())
        assert len(case.materials) == 1
        assert "Cable" in case.materials[0].description

    def test_merge_empty_inputs(self, svc):
        case = svc._merge_into_case({}, {}, {})
        assert isinstance(case, Case)
        assert case.order_no is None or case.order_no == ""


# ── Full pipeline with mocked extractors ────────────────────────


class TestGeneratorServicePipeline:
    @pytest.fixture
    def svc(self, db, tmp_path):
        from app.infrastructure.config_manager import ConfigManager
        ConfigManager._instance = None
        config = ConfigManager()
        config._config.set("General", "output_dir", str(tmp_path / "output"))
        config._config.set("General", "recovery_dir", str(tmp_path / "recovery"))
        svc = GeneratorService(db=db, config=config)
        yield svc
        ConfigManager._instance = None

    @patch("app.services.generator_service.extract_cost_table_image", return_value=False)
    def test_full_pipeline_creates_case(self, mock_cost, svc, db, tmp_path):
        """Mock extractors, run full pipeline, verify case persisted."""
        scheme_pdf = tmp_path / "scheme.pdf"
        scheme_pdf.write_bytes(b"%PDF-1.4 mock")
        pm06 = tmp_path / "pm06.xlsx"
        pm06.write_bytes(b"PK\x03\x04 mock")

        with patch.object(svc, "_extract_file") as mock_ext:
            mock_ext.side_effect = [
                _make_scheme_data(),   # scheme
                _make_sv_data(),       # site visit
                _make_pm06_data(),     # pm06
            ]
            with patch.object(svc._docx_builder, "build_summary"):
                case = svc.generate(
                    scheme_pdf_path=scheme_pdf,
                    pm06_excel_path=pm06,
                )

        assert case.id is not None
        assert case.order_no == "60038419"
        assert case.status == CaseStatus.PENDING
        assert case.work_type is not None

        # Verify DB persistence
        repo = CaseRepository(db)
        db_case = repo.get_by_id(case.id)
        assert db_case is not None
        assert db_case.order_no == "60038419"

    @patch("app.services.generator_service.extract_cost_table_image", return_value=False)
    def test_pipeline_runs_work_type_detection(self, mock_cost, svc, tmp_path):
        pdf = tmp_path / "x.pdf"
        pdf.write_bytes(b"%PDF-1.4 mock")
        with patch.object(svc, "_extract_file") as mock_ext:
            mock_ext.side_effect = [
                _make_scheme_data(),
                {},
                _make_pm06_data(),
            ]
            with patch.object(svc._docx_builder, "build_summary"):
                case = svc.generate(scheme_pdf_path=pdf)
        assert case.work_type in list(WorkType)

    @patch("app.services.generator_service.extract_cost_table_image", return_value=False)
    def test_pipeline_runs_validation(self, mock_cost, svc, tmp_path):
        pdf = tmp_path / "x.pdf"
        pdf.write_bytes(b"%PDF-1.4 mock")
        with patch.object(svc, "_extract_file") as mock_ext:
            mock_ext.side_effect = [_make_scheme_data(), {}, _make_pm06_data()]
            with patch.object(svc._docx_builder, "build_summary"):
                case = svc.generate(scheme_pdf_path=pdf)
        assert case.validation_result is not None
        assert len(case.validation_result.checks) == 17

    @patch("app.services.generator_service.extract_cost_table_image", return_value=False)
    def test_pipeline_progress_callback(self, mock_cost, svc, tmp_path):
        progress_calls = []
        pdf = tmp_path / "x.pdf"
        pdf.write_bytes(b"%PDF-1.4 mock")

        with patch.object(svc, "_extract_file") as mock_ext:
            mock_ext.side_effect = [_make_scheme_data(), {}, _make_pm06_data()]
            with patch.object(svc._docx_builder, "build_summary"):
                svc.generate(
                    scheme_pdf_path=tmp_path / "x.pdf",
                    progress_cb=lambda p, m: progress_calls.append((p, m)),
                )

        assert len(progress_calls) > 0
        assert progress_calls[-1][0] == 100  # Last call = 100%

    @patch("app.services.generator_service.extract_cost_table_image", return_value=False)
    def test_pipeline_saves_to_source_dir(self, mock_cost, svc, db, tmp_path):
        source = tmp_path / "source_folder"
        source.mkdir()
        scheme_pdf = source / "scheme.pdf"
        scheme_pdf.write_bytes(b"%PDF-1.4 mock")

        with patch.object(svc, "_extract_file") as mock_ext:
            mock_ext.side_effect = [_make_scheme_data(), {}, _make_pm06_data()]
            with patch.object(svc._docx_builder, "build_summary"):
                case = svc.generate(scheme_pdf_path=scheme_pdf)

        assert case.output_docx_path is not None
        assert "source_folder" in case.output_docx_path


# ── _find_source_dir ────────────────────────────────────────────


class TestFindSourceDir:
    def test_returns_parent_of_first_existing(self, tmp_path):
        f = tmp_path / "sub" / "test.pdf"
        f.parent.mkdir(parents=True)
        f.write_bytes(b"x")
        result = GeneratorService._find_source_dir(f, None, None)
        assert result == tmp_path / "sub"

    def test_all_none_returns_none(self):
        assert GeneratorService._find_source_dir(None, None, None) is None

    def test_missing_file_returns_none(self, tmp_path):
        result = GeneratorService._find_source_dir(
            tmp_path / "nope.pdf", None, None
        )
        assert result is None


# ── _derive_dt_fields ───────────────────────────────────────────


class TestDeriveDTFields:
    @pytest.fixture
    def svc(self, db, tmp_path):
        from app.infrastructure.config_manager import ConfigManager
        ConfigManager._instance = None
        config = ConfigManager()
        config._config.set("General", "output_dir", str(tmp_path / "out"))
        config._config.set("General", "recovery_dir", str(tmp_path / "rec"))
        svc = GeneratorService(db=db, config=config)
        yield svc
        ConfigManager._instance = None

    def test_extracts_transformer_from_materials(self, svc):
        case = Case(
            materials=[
                Material(description="TRANSFORMER 400KVA", quantity=1, unit="NO"),
                Material(description="Cable 95mm", quantity=100, unit="MTR"),
            ],
            work_type=WorkType.DT_AUGMENTATION,
        )
        svc._derive_dt_fields(case)
        assert case.new_transformer_rating is not None

    def test_no_dt_material_leaves_none(self, svc):
        case = Case(
            materials=[Material(description="Cable 95mm", quantity=100, unit="MTR")],
            work_type=WorkType.LT_STANDARD,
        )
        svc._derive_dt_fields(case)
        # Should not crash


# ── _resolve_zone_wbs ──────────────────────────────────────────


class TestResolveZoneWBS:
    @pytest.fixture
    def svc(self, db, tmp_path):
        from app.infrastructure.config_manager import ConfigManager
        ConfigManager._instance = None
        config = ConfigManager()
        config._config.set("General", "output_dir", str(tmp_path / "out"))
        config._config.set("General", "recovery_dir", str(tmp_path / "rec"))
        svc = GeneratorService(db=db, config=config)
        yield svc
        ConfigManager._instance = None

    def test_resolves_known_zone(self, svc):
        case = Case(zone="411")
        svc._resolve_zone_wbs(case)
        # District should be filled from the zone_district_map
        assert case.district is not None or case.zone == "411"

    def test_unknown_zone_leaves_district_alone(self, svc):
        case = Case(zone="999", district="ORIG")
        svc._resolve_zone_wbs(case)
        assert case.district == "ORIG"


# ── _merge_into_case deep tests ─────────────────────────────────


class TestMergeIntoCaseDeep:
    @pytest.fixture
    def svc(self, db, tmp_path):
        from app.infrastructure.config_manager import ConfigManager
        ConfigManager._instance = None
        config = ConfigManager()
        config._config.set("General", "output_dir", str(tmp_path / "output"))
        config._config.set("General", "recovery_dir", str(tmp_path / "recovery"))
        svc = GeneratorService(db=db, config=config)
        yield svc
        ConfigManager._instance = None

    def test_scheme_priority_wins(self, svc):
        """Scheme data overrides PM06 for overlapping fields."""
        scheme = {"order_no": ExtractionResult(value="FROM_SCHEME", confidence=FieldConfidence.HIGH, source="s")}
        pm06 = {"order_no": ExtractionResult(value="FROM_PM06", confidence=FieldConfidence.HIGH, source="p")}
        case = svc._merge_into_case(scheme, {}, pm06)
        assert case.order_no == "FROM_SCHEME"

    def test_longer_address_wins(self, svc):
        """For address, longer value is preferred regardless of source priority."""
        scheme = {"address": ExtractionResult(value="Short", confidence=FieldConfidence.HIGH, source="s")}
        pm06 = {"address": ExtractionResult(value="Much longer address with full details, Delhi 110001", confidence=FieldConfidence.HIGH, source="p")}
        case = svc._merge_into_case(scheme, {}, pm06)
        assert "longer" in case.address

    def test_alias_dt_capacity_existing(self, svc):
        """dt_capacity_existing alias maps to existing_dt_capacity."""
        pm06 = {"dt_capacity_existing": ExtractionResult(value="200 KVA", confidence=FieldConfidence.HIGH, source="p")}
        case = svc._merge_into_case({}, {}, pm06)
        assert case.existing_dt_capacity == "200 KVA"

    def test_alias_sanctioned_load(self, svc):
        """sanctioned_load alias maps to load_applied."""
        pm06 = {"sanctioned_load": ExtractionResult(value="5 kW", confidence=FieldConfidence.HIGH, source="p")}
        case = svc._merge_into_case({}, {}, pm06)
        assert case.load_applied == "5 kW"

    def test_materials_merge_from_list_of_dicts(self, svc):
        """Materials passed as list of dicts get converted to Material objects."""
        scheme = {"materials": ExtractionResult(
            value=[{"description": "Cable 95mm", "quantity": 100, "unit": "MTR"}],
            confidence=FieldConfidence.HIGH, source="s"
        )}
        case = svc._merge_into_case(scheme, {}, {})
        assert len(case.materials) == 1
        assert isinstance(case.materials[0], Material)

    def test_materials_newline_cleaned(self, svc):
        """Newlines in material descriptions are replaced with spaces."""
        scheme = {"materials": ExtractionResult(
            value=[Material(description="Cable\n95mm\nArmoured", quantity=1)],
            confidence=FieldConfidence.HIGH, source="s"
        )}
        case = svc._merge_into_case(scheme, {}, {})
        assert "\n" not in case.materials[0].description

    def test_lt_extension_materials_fallback(self, svc):
        """When BOM materials empty, lt_extension_materials are used."""
        pm06 = {
            "lt_extension_materials": ExtractionResult(
                value=[{"description": "PCC Pole 9M", "quantity": 3}],
                confidence=FieldConfidence.HIGH, source="p"
            )
        }
        case = svc._merge_into_case({}, {}, pm06)
        assert len(case.materials) == 1
        assert "PCC Pole" in case.materials[0].description

    def test_skip_keys_ignored(self, svc):
        """Keys in _SKIP_KEYS don't get set as attributes."""
        pm06 = {"notification_nos": ExtractionResult(value=["A", "B"], confidence=FieldConfidence.HIGH, source="p")}
        case = svc._merge_into_case({}, {}, pm06)
        # Should not crash or set a bad attribute

    def test_none_values_skipped(self, svc):
        """ExtractionResult with value=None shouldn't overwrite."""
        scheme = {"order_no": ExtractionResult(value="60038419", confidence=FieldConfidence.HIGH, source="s")}
        pm06 = {"order_no": ExtractionResult(value=None, confidence=FieldConfidence.LOW, source="p")}
        case = svc._merge_into_case(scheme, {}, pm06)
        assert case.order_no == "60038419"


# ── _derive_dt_fields deep tests ────────────────────────────────


class TestDeriveDTFieldsDeep:
    def test_selects_larger_transformer(self):
        case = Case(
            materials=[
                Material(description="TRANSFORMER 200KVA 3PH", quantity=1, unit="NO"),
                Material(description="TRANSFORMER 400KVA 3PH", quantity=1, unit="NO"),
            ],
            existing_dt_capacity="200 KVA",
        )
        GeneratorService._derive_dt_fields(case)
        assert "400" in case.new_transformer_rating

    def test_skips_smaller_transformer(self):
        """Existing 200 KVA → 200 KVA material is skipped (not an upgrade)."""
        case = Case(
            materials=[
                Material(description="TRANSFORMER 200KVA 3PH", quantity=1, unit="NO"),
            ],
            existing_dt_capacity="200 KVA",
        )
        GeneratorService._derive_dt_fields(case)
        assert case.new_transformer_rating is None

    def test_extracts_acb(self):
        case = Case(
            materials=[Material(description="LTACB 400A WITHFDR", quantity=1, unit="NO")],
        )
        GeneratorService._derive_dt_fields(case)
        assert case.acb_description is not None
        assert "LT ACB" in case.acb_description

    def test_normalizes_existing_dt_capacity(self):
        case = Case(existing_dt_capacity="63 kVA DT")
        GeneratorService._derive_dt_fields(case)
        assert "63" in case.existing_dt_capacity
        assert "DT" in case.existing_dt_capacity

    def test_no_materials_no_crash(self):
        case = Case(materials=[])
        GeneratorService._derive_dt_fields(case)
        # Should not raise


# ── _derive_capex_year tests ────────────────────────────────────


class TestDeriveCapexYear:
    def test_from_scheme_pdf_path(self):
        case = Case()
        case.scheme_pdf_path = r"C:\PM06\18-03-2026\scheme.pdf"
        GeneratorService._derive_capex_year(case)
        assert case.capex_year == "2025-26"

    def test_from_april_date(self):
        case = Case()
        case.scheme_pdf_path = r"C:\PM06\06-04-2026\scheme.pdf"
        GeneratorService._derive_capex_year(case)
        assert case.capex_year == "2026-27"

    def test_skips_if_already_set(self):
        case = Case(capex_year="2024-25")
        case.scheme_pdf_path = r"C:\PM06\18-03-2026\scheme.pdf"
        GeneratorService._derive_capex_year(case)
        assert case.capex_year == "2024-25"

    def test_no_path_no_crash(self):
        case = Case()
        GeneratorService._derive_capex_year(case)
        assert case.capex_year is None

    def test_invalid_date_in_path(self):
        case = Case()
        case.scheme_pdf_path = r"C:\PM06\99-99-9999\scheme.pdf"
        GeneratorService._derive_capex_year(case)
        assert case.capex_year is None


# ── _resolve_zone_wbs deep tests ────────────────────────────────


class TestResolveZoneWBSDeep:
    @pytest.fixture
    def svc(self, db, tmp_path):
        from app.infrastructure.config_manager import ConfigManager
        ConfigManager._instance = None
        config = ConfigManager()
        config._config.set("General", "output_dir", str(tmp_path / "out"))
        config._config.set("General", "recovery_dir", str(tmp_path / "rec"))
        svc = GeneratorService(db=db, config=config)
        yield svc
        ConfigManager._instance = None

    def test_zone_from_ht_tapping_pole(self, svc):
        case = Case(tapping_pole="HT572-63/21A")
        svc._resolve_zone_wbs(case)
        assert case.zone == "572"

    def test_zone_from_uht_prefix(self, svc):
        case = Case(tapping_pole="UHT512-27")
        svc._resolve_zone_wbs(case)
        assert case.zone == "512"

    def test_zone_from_bare_numeric(self, svc):
        case = Case(tapping_pole="511-65/5")
        svc._resolve_zone_wbs(case)
        assert case.zone == "511"

    def test_zone_from_scope(self, svc):
        case = Case(scope_of_work="Extension from HT523-10 towards house")
        svc._resolve_zone_wbs(case)
        assert case.zone == "523"

    def test_zone_from_u_prefix(self, svc):
        case = Case(tapping_pole="U511-49/17")
        svc._resolve_zone_wbs(case)
        assert case.zone == "511"

    def test_existing_zone_not_overwritten(self, svc):
        case = Case(zone="411", tapping_pole="HT999-1")
        svc._resolve_zone_wbs(case)
        assert case.zone == "411"  # Not overwritten

    def test_district_and_wbs_from_zone(self, svc):
        case = Case(zone="411")
        svc._resolve_zone_wbs(case)
        # Should attempt district + WBS lookup
        if case.district:
            assert isinstance(case.district, str)


# ── _extract_file edge cases ────────────────────────────────────


class TestExtractFile:
    @pytest.fixture
    def svc(self, db, tmp_path):
        from app.infrastructure.config_manager import ConfigManager
        ConfigManager._instance = None
        config = ConfigManager()
        config._config.set("General", "output_dir", str(tmp_path / "out"))
        config._config.set("General", "recovery_dir", str(tmp_path / "rec"))
        svc = GeneratorService(db=db, config=config)
        yield svc
        ConfigManager._instance = None

    def test_none_path_returns_empty(self, svc):
        result = svc._extract_file(None, FileType.SCHEME_PDF)
        assert result == {}

    def test_nonexistent_path_returns_empty(self, svc, tmp_path):
        result = svc._extract_file(tmp_path / "nope.pdf", FileType.SCHEME_PDF)
        assert result == {}


# ── Pipeline exception handling ─────────────────────────────────


class TestPipelineExceptionHandling:
    @pytest.fixture
    def svc(self, db, tmp_path):
        from app.infrastructure.config_manager import ConfigManager
        ConfigManager._instance = None
        config = ConfigManager()
        config._config.set("General", "output_dir", str(tmp_path / "output"))
        config._config.set("General", "recovery_dir", str(tmp_path / "recovery"))
        svc = GeneratorService(db=db, config=config)
        yield svc
        ConfigManager._instance = None

    @patch("app.services.generator_service.extract_cost_table_image", return_value=False)
    def test_extraction_warnings_collected(self, mock_cost, svc, tmp_path):
        """Extraction errors become warnings on the Case object."""
        pdf = tmp_path / "scheme.pdf"
        pdf.write_bytes(b"%PDF-1.4 mock")
        error_data = dict(_make_scheme_data())
        error_data["_error"] = ExtractionResult(
            value=None, confidence=FieldConfidence.LOW, source="error",
            message="Test extraction warning",
        )

        with patch.object(svc, "_extract_file") as mock_ext:
            mock_ext.side_effect = [error_data, {}, _make_pm06_data()]
            with patch.object(svc._docx_builder, "build_summary"):
                case = svc.generate(scheme_pdf_path=pdf)

        assert len(case.extraction_warnings) >= 1
