"""Tests for custom exception classes and ConfigManager deeper coverage."""

from __future__ import annotations

import configparser
import json
import pytest
from pathlib import Path
from unittest.mock import patch

from app.domain.exceptions import (
    TPDDLBaseError,
    ExtractionError,
    ValidationError,
    TrackerWriteError,
    DBCorruptionError,
    ConfigError,
    FileTypeError,
    OCRError,
)


# ══════════════════════════════════════════════════════════════════
# Custom exception tests
# ══════════════════════════════════════════════════════════════════


class TestTPDDLBaseError:
    def test_message_only(self):
        e = TPDDLBaseError("internal error")
        assert str(e) == "internal error"
        assert e.user_message == "internal error"

    def test_custom_user_message(self):
        e = TPDDLBaseError("internal", user_message="Friendly message")
        assert e.user_message == "Friendly message"
        assert str(e) == "internal"

    def test_is_exception(self):
        assert issubclass(TPDDLBaseError, Exception)


class TestExtractionError:
    def test_inherits_base(self):
        assert issubclass(ExtractionError, TPDDLBaseError)

    def test_can_raise_and_catch(self):
        with pytest.raises(ExtractionError):
            raise ExtractionError("PDF corrupt", user_message="Cannot read PDF")


class TestValidationError:
    def test_inherits_base(self):
        assert issubclass(ValidationError, TPDDLBaseError)

    def test_user_message(self):
        e = ValidationError("check failed", user_message="Please fix order no")
        assert e.user_message == "Please fix order no"


class TestTrackerWriteError:
    def test_inherits_base(self):
        assert issubclass(TrackerWriteError, TPDDLBaseError)

    def test_permission_error_message(self):
        e = TrackerWriteError(
            "PermissionError: file locked",
            user_message="Close Excel and retry",
        )
        assert e.user_message == "Close Excel and retry"


class TestDBCorruptionError:
    def test_inherits_base(self):
        assert issubclass(DBCorruptionError, TPDDLBaseError)


class TestConfigError:
    def test_inherits_base(self):
        assert issubclass(ConfigError, TPDDLBaseError)


class TestFileTypeError:
    def test_inherits_base(self):
        assert issubclass(FileTypeError, TPDDLBaseError)


class TestOCRError:
    def test_inherits_base(self):
        assert issubclass(OCRError, TPDDLBaseError)

    def test_default_user_message(self):
        e = OCRError("tesseract failed")
        assert e.user_message == "tesseract failed"


# ══════════════════════════════════════════════════════════════════
# ConfigManager deeper coverage
# ══════════════════════════════════════════════════════════════════

from app.infrastructure.config_manager import ConfigManager


@pytest.fixture()
def fresh_config(tmp_path, monkeypatch):
    """Create a ConfigManager pointing at a temp directory."""
    # Reset singleton
    ConfigManager._instance = None

    # Patch _ROOT_DIR
    monkeypatch.setattr("app.infrastructure.config_manager._ROOT_DIR", tmp_path)

    # Create required config directory and JSON files
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "zone_district_map.json").write_text(
        json.dumps({"NRL": [411, 412], "CVL": [511, 512]}), encoding="utf-8"
    )
    (config_dir / "wbs_map.json").write_text(
        json.dumps({
            "CE/N0000/00134": {"districts": ["NRL"]},
            "CE/N0000/00137": {"districts": ["CVL"]},
        }),
        encoding="utf-8",
    )
    (config_dir / "work_types.json").write_text(
        json.dumps({"LT_STANDARD": {"label": "LT Standard"}}), encoding="utf-8"
    )

    cm = ConfigManager()
    yield cm

    # Reset singleton for other tests
    ConfigManager._instance = None


class TestConfigManagerProperties:
    def test_root_dir(self, fresh_config, tmp_path):
        assert fresh_config.root_dir == tmp_path

    def test_engineer_name_default_empty(self, fresh_config):
        assert fresh_config.engineer_name == ""

    def test_engineer_name_setter(self, fresh_config):
        fresh_config.engineer_name = "Test Engineer"
        assert fresh_config.engineer_name == "Test Engineer"

    def test_font_size_default(self, fresh_config):
        assert fresh_config.font_size == 11

    def test_font_size_clamped(self, fresh_config):
        fresh_config.font_size = 50
        assert fresh_config.font_size == 14  # max

    def test_font_size_min(self, fresh_config):
        fresh_config.font_size = 1
        assert fresh_config.font_size == 9  # min

    def test_theme(self, fresh_config):
        assert fresh_config.theme == "litera"

    def test_is_first_run_initially(self, fresh_config):
        assert fresh_config.is_first_run is True

    def test_is_first_run_after_name_set(self, fresh_config):
        fresh_config.engineer_name = "Admin"
        assert fresh_config.is_first_run is False


class TestConfigManagerPaths:
    def test_db_path(self, fresh_config, tmp_path):
        assert fresh_config.db_path.parent == tmp_path

    def test_output_dir(self, fresh_config, tmp_path):
        assert fresh_config.output_dir.parent == tmp_path

    def test_output_dir_setter(self, fresh_config, tmp_path):
        new_dir = tmp_path / "custom_output"
        fresh_config.output_dir = new_dir
        assert fresh_config.output_dir == new_dir

    def test_logs_dir(self, fresh_config):
        assert "logs" in str(fresh_config.logs_dir).lower()

    def test_backup_dir(self, fresh_config):
        assert "backup" in str(fresh_config.backup_dir).lower()

    def test_recovery_dir(self, fresh_config):
        assert "recovery" in str(fresh_config.recovery_dir).lower()

    def test_get_path_known_keys(self, fresh_config):
        for key in ("output", "tracker", "db", "logs", "backup", "recovery", "root"):
            p = fresh_config.get_path(key)
            assert isinstance(p, Path)

    def test_get_path_unknown_returns_root(self, fresh_config, tmp_path):
        assert fresh_config.get_path("unknown_key") == tmp_path


class TestConfigManagerWindowGeometry:
    def test_default_geometry(self, fresh_config):
        g = fresh_config.window_geometry
        assert g["width"] == "1200"
        assert g["height"] == "800"

    def test_save_geometry(self, fresh_config):
        fresh_config.save_window_geometry(1600, 900, 100, 50)
        g = fresh_config.window_geometry
        assert g["width"] == "1600"
        assert g["height"] == "900"
        assert g["x"] == "100"
        assert g["y"] == "50"


class TestConfigManagerMappings:
    def test_zone_district_map_loaded(self, fresh_config):
        zdm = fresh_config.zone_district_map
        assert "NRL" in zdm
        assert 411 in zdm["NRL"]

    def test_get_district_for_zone(self, fresh_config):
        assert fresh_config.get_district_for_zone(411) == "NRL"
        assert fresh_config.get_district_for_zone(511) == "CVL"

    def test_get_district_for_unknown_zone(self, fresh_config):
        assert fresh_config.get_district_for_zone(999) is None

    def test_wbs_map_loaded(self, fresh_config):
        assert "CE/N0000/00134" in fresh_config.wbs_map

    def test_get_wbs_for_district(self, fresh_config):
        assert fresh_config.get_wbs_for_district("NRL") == "CE/N0000/00134"

    def test_get_wbs_for_unknown_district(self, fresh_config):
        assert fresh_config.get_wbs_for_district("XXX") is None

    def test_work_types_config(self, fresh_config):
        assert "LT_STANDARD" in fresh_config.work_types_config


class TestConfigManagerPersistence:
    def test_save_and_reload(self, fresh_config):
        fresh_config.engineer_name = "Saved Engineer"
        fresh_config.reload()
        assert fresh_config.engineer_name == "Saved Engineer"

    def test_set_and_get(self, fresh_config):
        fresh_config.set("Custom", "key", "value")
        assert fresh_config.get("Custom", "key") == "value"

    def test_get_fallback(self, fresh_config):
        assert fresh_config.get("NonExistent", "key", fallback="default") == "default"

    def test_save_zone_district_map(self, fresh_config, tmp_path):
        new_map = {"NRL": [411], "CVL": [511]}
        fresh_config.save_zone_district_map(new_map)
        assert fresh_config.zone_district_map == new_map
        # Verify file was written
        json_path = tmp_path / "config" / "zone_district_map.json"
        assert json_path.exists()
        data = json.loads(json_path.read_text(encoding="utf-8"))
        assert data == new_map

    def test_save_wbs_map(self, fresh_config, tmp_path):
        new_wbs = {"WBS/001": {"districts": ["NRL"]}}
        fresh_config.save_wbs_map(new_wbs)
        assert fresh_config.wbs_map == new_wbs
