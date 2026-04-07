"""Tests for app.infrastructure.config_manager."""

from pathlib import Path

import pytest

from app.infrastructure.config_manager import ConfigManager


class TestConfigManager:
    def test_singleton_returns_same_instance(self):
        # Reset singleton for test
        ConfigManager._instance = None
        c1 = ConfigManager()
        c2 = ConfigManager()
        assert c1 is c2
        ConfigManager._instance = None  # cleanup

    def test_output_dir_default(self):
        ConfigManager._instance = None
        config = ConfigManager()
        assert isinstance(config.output_dir, Path)
        ConfigManager._instance = None

    def test_zone_district_map_loaded(self):
        ConfigManager._instance = None
        config = ConfigManager()
        zone_map = config.zone_district_map
        assert isinstance(zone_map, dict)
        ConfigManager._instance = None

    def test_wbs_map_loaded(self):
        ConfigManager._instance = None
        config = ConfigManager()
        wbs_map = config.wbs_map
        assert isinstance(wbs_map, dict)
        ConfigManager._instance = None
