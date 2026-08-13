"""Tests for pace and duration formatting."""

from fit_parser.formatters import format_duration, format_pace


class TestFormatPace:
    def test_standard_pace(self):
        assert format_pace(300.0, 1000.0) == "5:00"

    def test_fast_pace(self):
        assert format_pace(240.0, 1000.0) == "4:00"

    def test_slow_pace_with_seconds(self):
        # 365s / 1km = 6.083 min → truncates to 6:04
        assert format_pace(365.0, 1000.0) == "6:04"

    def test_zero_distance_returns_none(self):
        assert format_pace(300.0, 0) is None

    def test_zero_time_returns_none(self):
        assert format_pace(0, 1000.0) is None

    def test_negative_distance_returns_none(self):
        assert format_pace(300.0, -100) is None

    def test_half_km(self):
        result = format_pace(150.0, 500.0)
        assert result == "5:00"


class TestFormatDuration:
    def test_simple_minutes_seconds(self):
        assert format_duration(365.0, include_hours=False) == "06:05"

    def test_with_hours_when_included(self):
        assert format_duration(3725.0, include_hours=True) == "1:02:05"

    def test_no_hours_for_under_an_hour(self):
        assert format_duration(3599.0, include_hours=True) == "59:59"

    def test_zero_seconds(self):
        assert format_duration(0, include_hours=False) == "00:00"

    def test_hours_suppressed(self):
        assert format_duration(3725.0, include_hours=False) == "02:05"

    def test_exactly_one_hour(self):
        assert format_duration(3600.0, include_hours=True) == "1:00:00"
        assert format_duration(3600.0, include_hours=False) == "00:00"
