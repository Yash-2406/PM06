"""Tests for app.services.tracker_service."""

import pytest

from app.data.case_repository import CaseRepository
from app.data.database import Database
from app.domain.enums import CaseStatus
from app.domain.models import Case
from app.services.tracker_service import TrackerService


class TestTrackerService:
    @pytest.fixture
    def tracker(self, db, tmp_path):
        from unittest.mock import MagicMock

        from app.infrastructure.config_manager import ConfigManager

        ConfigManager._instance = None
        config = ConfigManager()
        # Override tracker path to tmp
        config._config.set("General", "tracker_path", str(tmp_path / "tracker.xlsx"))
        svc = TrackerService(db=db, config=config)
        yield svc
        ConfigManager._instance = None

    def test_list_cases_empty(self, tracker):
        cases = tracker.list_cases()
        assert cases == []

    def test_get_case_not_found(self, tracker):
        result = tracker.get_case(999)
        assert result is None

    def test_get_mis_summary(self, tracker):
        summary = tracker.get_mis_summary()
        assert isinstance(summary, (dict, list))
