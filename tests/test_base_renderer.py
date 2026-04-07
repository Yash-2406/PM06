"""Tests for base_renderer pick_pole_ref and _is_pole_code logic."""

from __future__ import annotations

import pytest
from app.builders.renderers.base_renderer import _is_pole_code, pick_pole_ref


class TestIsPoleCode:
    """_is_pole_code detects valid pole/substation code patterns."""

    def test_ht_prefix(self):
        assert _is_pole_code("HT517-63/21A") is True

    def test_u_prefix(self):
        assert _is_pole_code("U511-49/17") is True

    def test_uht_prefix(self):
        assert _is_pole_code("UHT512-27") is True

    def test_bare_numeric_dash(self):
        assert _is_pole_code("511-65/5") is True

    def test_bare_numeric_slash(self):
        assert _is_pole_code("523/1/1") is True

    def test_short_code(self):
        assert _is_pole_code("AB123") is True

    def test_empty_string(self):
        assert _is_pole_code("") is False

    def test_none_value(self):
        assert _is_pole_code(None) is False

    def test_generic_text(self):
        assert _is_pole_code("Near Market") is False

    def test_short_number(self):
        assert _is_pole_code("12") is False

    def test_letters_only(self):
        assert _is_pole_code("ABCDEF") is False


class TestPickPoleRef:
    """pick_pole_ref prefers tapping_pole codes, falls back to substation_name."""

    def test_valid_tp_wins(self):
        result = pick_pole_ref("HT517-63", "SS411 Substation, Block A")
        assert result == "HT517-63"

    def test_invalid_tp_falls_to_sn(self):
        result = pick_pole_ref("Near Market", "HT411-27")
        assert result == "HT411-27"

    def test_both_invalid_returns_tp(self):
        result = pick_pole_ref("Near Market", "Behind School")
        assert result == "Near Market"

    def test_both_none_returns_placeholder(self):
        assert pick_pole_ref(None, None) == "[Pole No.]"

    def test_both_empty_returns_placeholder(self):
        assert pick_pole_ref("", "") == "[Pole No.]"

    def test_tp_none_sn_valid(self):
        result = pick_pole_ref(None, "HT523-10")
        assert result == "HT523-10"

    def test_tp_none_sn_invalid(self):
        result = pick_pole_ref(None, "Some Place")
        assert result == "Some Place"

    def test_strips_trailing_period(self):
        result = pick_pole_ref("HT517-63.", None)
        assert result == "HT517-63"

    def test_sn_comma_stripped(self):
        """Substation name part after comma is stripped."""
        result = pick_pole_ref(None, "HT411-27, Block A")
        assert result == "HT411-27"

    def test_tp_whitespace_stripped(self):
        result = pick_pole_ref("  HT517-63  ", None)
        assert result == "HT517-63"
