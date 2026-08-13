"""Tests for HR zone calculations."""

from datetime import datetime, timedelta

from fit_parser.zones import calculate_hr_zone, calculate_hr_zone_distribution


class TestCalculateHRZone:
    def test_zone_1_below_60_pct(self):
        assert calculate_hr_zone(100, 200) == 1  # 50%

    def test_zone_2_at_60_pct(self):
        assert calculate_hr_zone(120, 200) == 2  # 60%

    def test_zone_3_at_75_pct(self):
        assert calculate_hr_zone(150, 200) == 3  # 75%

    def test_zone_4_at_85_pct(self):
        assert calculate_hr_zone(170, 200) == 4  # 85%

    def test_zone_5_at_90_pct(self):
        assert calculate_hr_zone(180, 200) == 5  # 90%

    def test_zone_5_above_90_pct(self):
        assert calculate_hr_zone(200, 200) == 5  # 100%

    def test_zero_hr_returns_none(self):
        assert calculate_hr_zone(0, 200) is None

    def test_zero_max_returns_none(self):
        assert calculate_hr_zone(150, 0) is None


class TestCalculateHRZoneDistribution:
    def _make_timestamps(self, bpm_values: list[int]) -> list[tuple[datetime, int]]:
        base = datetime(2025, 1, 1, 12, 0, 0)
        return [(base + timedelta(seconds=i * 10), bpm) for i, bpm in enumerate(bpm_values)]

    def test_basic_distribution(self):
        # 3 records at 100, 150, 180 BPM with 10s gaps, max_hr=200
        # Zone 1 (100 BPM): 10s
        # Zone 3 (150 BPM): 10s
        # Zone 5 (180 BPM): 10s (not allocated — last record has no next interval)
        timestamps = self._make_timestamps([100, 150, 180])
        result = calculate_hr_zone_distribution(timestamps, 200)
        assert result is not None
        assert result[1] == 10.0  # 10s at zone 1
        assert result[3] == 10.0  # 10s at zone 3

    def test_empty_timestamps_returns_none(self):
        assert calculate_hr_zone_distribution([], 200) is None

    def test_single_timestamp_returns_none(self):
        timestamps = self._make_timestamps([150])
        assert calculate_hr_zone_distribution(timestamps, 200) is None

    def test_zero_max_hr_returns_none(self):
        timestamps = self._make_timestamps([150, 160])
        assert calculate_hr_zone_distribution(timestamps, 0) is None

    def test_all_zones_initialized(self):
        timestamps = self._make_timestamps([150, 150])
        result = calculate_hr_zone_distribution(timestamps, 200)
        assert result is not None
        assert set(result.keys()) == {1, 2, 3, 4, 5}

    def test_negative_elapsed_skipped(self):
        base = datetime(2025, 1, 1, 12, 0, 0)
        timestamps = [
            (base, 150),
            (base - timedelta(seconds=5), 160),  # negative gap
        ]
        result = calculate_hr_zone_distribution(timestamps, 200)
        assert result is not None
        assert result[3] == 0.0  # no time allocated
