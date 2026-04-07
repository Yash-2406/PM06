"""Tests for app.builders.work_type_detector."""

from app.builders.work_type_detector import detect_work_type
from app.domain.enums import WorkType
from app.domain.models import Material


class TestDetectWorkType:
    def test_dt_augmentation_from_nature(self):
        mats = [Material(description="Some Cable")]
        result = detect_work_type(mats, "DT AUGMENTATION from 200 KVA to 400 KVA")
        assert result == WorkType.DT_AUGMENTATION

    def test_dt_augmentation_from_transformer_material(self):
        mats = [Material(description="TRANSFORMER 400 KVA")]
        result = detect_work_type(mats, "")
        assert result == WorkType.DT_AUGMENTATION

    def test_abc_wiring(self):
        mats = [Material(description="ABC 4x150 Cable")]
        result = detect_work_type(mats, "")
        assert result == WorkType.ABC_WIRING

    def test_lt_ht_pole(self):
        mats = [Material(description="2X25 HT Cable")]
        result = detect_work_type(mats, "")
        assert result == WorkType.LT_HT_POLE

    def test_default_lt_standard(self):
        mats = [Material(description="Regular LT Cable")]
        result = detect_work_type(mats, "")
        assert result == WorkType.LT_STANDARD

    def test_empty_inputs(self):
        result = detect_work_type([], "")
        assert result == WorkType.LT_STANDARD

    def test_priority_dt_over_abc(self):
        mats = [
            Material(description="TRANSFORMER 400 KVA"),
            Material(description="ABC Cable"),
        ]
        result = detect_work_type(mats, "")
        assert result == WorkType.DT_AUGMENTATION
