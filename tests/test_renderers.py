"""Tests for renderers."""

from app.builders.renderers import get_renderer
from app.builders.renderers.dt_augmentation_renderer import DTAugmentationRenderer
from app.builders.renderers.lt_standard_renderer import LTStandardRenderer
from app.domain.enums import WorkType


class TestGetRenderer:
    def test_lt_standard(self):
        r = get_renderer(WorkType.LT_STANDARD)
        assert isinstance(r, LTStandardRenderer)

    def test_dt_augmentation(self):
        r = get_renderer(WorkType.DT_AUGMENTATION)
        assert isinstance(r, DTAugmentationRenderer)


class TestLTStandardRenderer:
    def test_capex_title(self):
        r = LTStandardRenderer()
        title = r.capex_title("NC12345678")
        assert "LT extension" in title
        assert "NC12345678" in title

    def test_existing_scenario(self):
        r = LTStandardRenderer()
        text = r.existing_scenario("NC12345678")
        assert "NC12345678" in text

    def test_proposed_scenario(self):
        r = LTStandardRenderer()
        text = r.proposed_scenario("P-123", "400 kVA DT")
        assert "P-123" in text

    def test_sub_head(self):
        r = LTStandardRenderer()
        assert "LT Line Extension" in r.sub_head()


class TestDTAugmentationRenderer:
    def test_capex_title_includes_capacity(self):
        r = DTAugmentationRenderer()
        title = r.capex_title("NC12345678", "200 KVA", "400 KVA", "ACB 400A")
        assert "200 KVA" in title
        assert "400 KVA" in title
        assert "ACB 400A" in title

    def test_sub_head(self):
        r = DTAugmentationRenderer()
        assert "Augmentation" in r.sub_head()
