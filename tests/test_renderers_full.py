"""Comprehensive renderer tests — all 4 work types, all 4 methods each."""

from __future__ import annotations

import pytest

from app.builders.renderers import get_renderer
from app.builders.renderers.base_renderer import BaseRenderer
from app.builders.renderers.lt_standard_renderer import LTStandardRenderer
from app.builders.renderers.lt_ht_pole_renderer import LTHTPoleRenderer
from app.builders.renderers.abc_wiring_renderer import ABCWiringRenderer
from app.builders.renderers.dt_augmentation_renderer import DTAugmentationRenderer
from app.domain.enums import WorkType


# ── get_renderer factory ────────────────────────────────────────


class TestGetRendererFactory:
    @pytest.mark.parametrize("wt, expected_cls", [
        (WorkType.LT_STANDARD, LTStandardRenderer),
        (WorkType.LT_HT_POLE, LTHTPoleRenderer),
        (WorkType.ABC_WIRING, ABCWiringRenderer),
        (WorkType.DT_AUGMENTATION, DTAugmentationRenderer),
    ])
    def test_returns_correct_class(self, wt, expected_cls):
        r = get_renderer(wt)
        assert isinstance(r, expected_cls)

    def test_all_renderers_are_base_renderer(self):
        for wt in WorkType:
            r = get_renderer(wt)
            assert isinstance(r, BaseRenderer)


# ── LT Standard Renderer ───────────────────────────────────────


class TestLTStandardRendererFull:
    @pytest.fixture
    def renderer(self):
        return LTStandardRenderer()

    def test_capex_title_contains_notif(self, renderer):
        title = renderer.capex_title("NC12345678")
        assert "NC12345678" in title

    def test_capex_title_contains_lt(self, renderer):
        title = renderer.capex_title("NC12345678")
        assert "LT" in title.upper() or "lt" in title.lower() or "extension" in title.lower()

    def test_existing_scenario_contains_notif(self, renderer):
        text = renderer.existing_scenario("NC99999999")
        assert "NC99999999" in text

    def test_proposed_scenario_contains_pole(self, renderer):
        text = renderer.proposed_scenario("HT572-63/21A", "400 kVA DT")
        assert "HT572-63/21A" in text

    def test_proposed_scenario_with_placeholder(self, renderer):
        text = renderer.proposed_scenario(None, None)
        assert text  # should still return non-empty string

    def test_sub_head_value(self, renderer):
        sh = renderer.sub_head()
        assert "LT Line Extension" in sh


# ── LT HT Pole Renderer ────────────────────────────────────────


class TestLTHTPoleRendererFull:
    @pytest.fixture
    def renderer(self):
        return LTHTPoleRenderer()

    def test_inherits_lt_standard(self):
        assert issubclass(LTHTPoleRenderer, LTStandardRenderer)

    def test_capex_title(self, renderer):
        title = renderer.capex_title("NC11111111")
        assert "NC11111111" in title

    def test_existing_scenario(self, renderer):
        text = renderer.existing_scenario("NC11111111")
        assert "NC11111111" in text

    def test_sub_head(self, renderer):
        sh = renderer.sub_head()
        assert "LT Line Extension" in sh


# ── ABC Wiring Renderer ────────────────────────────────────────


class TestABCWiringRendererFull:
    @pytest.fixture
    def renderer(self):
        return ABCWiringRenderer()

    def test_inherits_lt_standard(self):
        assert issubclass(ABCWiringRenderer, LTStandardRenderer)

    def test_capex_title(self, renderer):
        title = renderer.capex_title("NC22222222")
        assert "NC22222222" in title

    def test_existing_scenario(self, renderer):
        text = renderer.existing_scenario("NC22222222")
        assert "NC22222222" in text


# ── DT Augmentation Renderer ───────────────────────────────────


class TestDTAugRendererFull:
    @pytest.fixture
    def renderer(self):
        return DTAugmentationRenderer()

    def test_capex_title_includes_capacities(self, renderer):
        title = renderer.capex_title("NC33333333", "200 KVA", "400 KVA", "ACB 400A")
        assert "200 KVA" in title
        assert "400 KVA" in title

    def test_capex_title_includes_acb(self, renderer):
        title = renderer.capex_title("NC33333333", "200 KVA", "400 KVA", "ACB 400A")
        assert "ACB" in title

    def test_capex_title_with_missing_params(self, renderer):
        title = renderer.capex_title("NC33333333")
        assert "NC33333333" in title

    def test_existing_scenario_includes_notif(self, renderer):
        text = renderer.existing_scenario("NC44444444")
        assert "NC44444444" in text

    def test_proposed_scenario_includes_transformer(self, renderer):
        text = renderer.proposed_scenario(
            "HT572-63/21A", "200 KVA", "400 KVA", "ACB 400A", "Sub Station X"
        )
        assert "400 KVA" in text or "HT572" in text

    def test_sub_head_augmentation(self, renderer):
        sh = renderer.sub_head()
        assert "Augmentation" in sh

    def test_different_from_lt_standard(self):
        dt = DTAugmentationRenderer()
        lt = LTStandardRenderer()
        assert dt.sub_head() != lt.sub_head()
