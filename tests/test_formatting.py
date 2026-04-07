"""Tests for app.infrastructure.formatting."""

from app.infrastructure.formatting import format_indian_amount, get_capex_year, parse_indian_amount


class TestFormatIndianAmount:
    def test_lakhs(self):
        result = format_indian_amount(125000.50)
        assert "125,000" in result

    def test_crores(self):
        result = format_indian_amount(15000000)
        assert "15,000,000" in result

    def test_zero(self):
        result = format_indian_amount(0)
        assert "0" in result

    def test_small_amount(self):
        result = format_indian_amount(999)
        assert "999" in result


class TestParseIndianAmount:
    def test_with_commas(self):
        assert parse_indian_amount("1,25,000.50") == 125000.50

    def test_with_rs_prefix(self):
        result = parse_indian_amount("Rs. 1,25,000")
        assert result == 125000.0

    def test_plain_number(self):
        assert parse_indian_amount("50000") == 50000.0


class TestGetCapexYear:
    def test_returns_string(self):
        result = get_capex_year()
        assert isinstance(result, str)
        assert "-" in result  # e.g. "2024-25"
