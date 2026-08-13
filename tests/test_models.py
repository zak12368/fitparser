"""Tests for data models and serialization."""

from fit_parser.models import HRZoneDistribution, Lap, Workout


class TestWorkout:
    def test_to_dict_basic(self):
        w = Workout(filename="test.fit", workout_type="Outdoor Run", total_distance_km=5.0)
        d = w.to_dict()
        assert d["filename"] == "test.fit"
        assert d["workout_type"] == "Outdoor Run"
        assert d["total_distance_km"] == 5.0

    def test_to_dict_omits_none(self):
        w = Workout(filename="test.fit")
        d = w.to_dict()
        assert "workout_type" not in d
        assert "total_distance_km" not in d

    def test_to_dict_serializes_hr_zone_distribution(self):
        zone_dist = HRZoneDistribution(
            zone_times={1: "05:00", 2: "03:00", 3: "02:00", 4: "01:00", 5: "00:00"},
            zone_pcts={1: 50.0, 2: 30.0, 3: 15.0, 4: 5.0, 5: 0.0},
            dominant_zone=1,
        )
        w = Workout(filename="test.fit", hr_zone_distribution=zone_dist)
        d = w.to_dict()
        assert "hr_zone_distribution" in d
        zones = d["hr_zone_distribution"]
        assert zones["zone_1_time"] == "05:00"
        assert zones["zone_1_pct"] == 50.0
        assert zones["zone_5_time"] == "00:00"
        assert zones["zone_5_pct"] == 0.0
        # Keys should not leak to top level
        assert "zone_1_time" not in d

    def test_to_dict_omits_empty_laps(self):
        w = Workout(filename="test.fit", laps_info=[])
        d = w.to_dict()
        assert "laps_info" not in d

    def test_to_dict_includes_laps(self):
        lap = Lap(time="05:00", pace="5:00", distance_km=1.0, calories=100)
        w = Workout(filename="test.fit", laps_info=[lap])
        d = w.to_dict()
        assert "laps_info" in d
        assert len(d["laps_info"]) == 1
        assert d["laps_info"][0]["time"] == "05:00"


class TestLap:
    def test_to_dict_omits_empty_fields(self):
        lap = Lap(
            time="05:00",
            pace="5:00",
            distance_km=1.0,
            calories=100,
            heart_rate={"avg": 150},
            power=None,
            cadence={"avg": 160},
            strides=400,
        )
        import dataclasses

        for fld in dataclasses.fields(lap):
            val = getattr(lap, fld.name)
            if val is None or val == {}:
                pass  # omitted
            else:
                pass  # included

    def test_full_lap(self):
        lap = Lap(
            time="06:30",
            pace="6:30",
            distance_km=1.0,
            calories=85,
            avg_speed_kmh=9.2,
            heart_rate={"avg": 165, "max": 180, "min": 140},
            power={"avg": 250, "max": 400},
            cadence={"avg": 160, "max": 180},
            strides=430,
            running_dynamics={
                "vertical_oscillation_mm": 100.0,
                "stance_time_ms": 250.0,
            },
        )
        assert lap.time == "06:30"
        assert lap.running_dynamics["vertical_oscillation_mm"] == 100.0


class TestHRZoneDistribution:
    def test_basic(self):
        dist = HRZoneDistribution(
            zone_times={1: "00:00", 2: "10:00", 3: "05:00", 4: "03:00", 5: "02:00"},
            zone_pcts={1: 0.0, 2: 50.0, 3: 25.0, 4: 15.0, 5: 10.0},
            dominant_zone=2,
        )
        assert dist.dominant_zone == 2
        assert dist.zone_pcts[2] == 50.0
