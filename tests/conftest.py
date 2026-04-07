"""Pytest configuration and shared fixtures."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from app.data.database import Database
from app.domain.enums import CaseStatus, WorkType
from app.domain.models import Case, Material


@pytest.fixture
def tmp_dir(tmp_path):
    """Provide a temporary directory."""
    return tmp_path


@pytest.fixture
def db(tmp_path):
    """Provide a fresh in-memory-like SQLite database."""
    db_path = tmp_path / "test.db"
    database = Database(db_path)
    database.initialise()
    return database


@pytest.fixture
def sample_case() -> Case:
    """Provide a sample Case with minimal populated fields."""
    return Case(
        order_no="000070012345",
        notification_no="NC1234567890",
        applicant_name="John Doe",
        address="123 Test Street, Near Test Market, Delhi",
        pin_code="110001",
        zone="Zone-1",
        district="NRL",
        wbs_no="CE/N0000/00137",
        load_applied="5 kW",
        category="DOMESTIC",
        work_type=WorkType.LT_STANDARD,
        grand_total=125000.50,
        scope_of_work="LT extension from pole no. 123 towards applicant premises.",
        materials=[
            Material(description="LT 4 Core ABC Cable", quantity=100, unit="MTR"),
            Material(description="8 Mtr PSCC Pole", quantity=3, unit="NO"),
        ],
        status=CaseStatus.PENDING,
    )


@pytest.fixture
def sample_materials() -> list[Material]:
    """Provide a list of sample materials."""
    return [
        Material(description="LT 4 Core ABC Cable 95 sq mm", quantity=100, unit="MTR", code="123456789"),
        Material(description="8 Mtr PSCC Pole", quantity=3, unit="NO", code="987654321"),
        Material(description="Distribution Box 400A", quantity=1, unit="NO"),
    ]
