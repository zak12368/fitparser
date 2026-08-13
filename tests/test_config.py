"""Tests for workout type mapping."""

from fit_parser.config import CADENCE_MULTIPLIER, HR_ZONE_THRESHOLDS, WORKOUT_MAP


class TestWorkoutMap:
    def test_running_generic(self):
        assert WORKOUT_MAP[("running", "generic")] == "Outdoor Run"

    def test_running_indoor(self):
        assert WORKOUT_MAP[("running", "indoor_running")] == "Indoor Run"

    def test_walking_indoor(self):
        assert WORKOUT_MAP[("walking", "indoor_walking")] == "Indoor Walk"

    def test_hiit(self):
        assert WORKOUT_MAP[("hiit", "generic")] == "HIIT"

    def test_yoga(self):
        assert WORKOUT_MAP[("yoga", "generic")] == "Yoga"

    def test_dive(self):
        assert WORKOUT_MAP[("53", "generic")] == "Dive"

    def test_unknown_falls_back(self):
        assert WORKOUT_MAP.get(("unknown", "unknown"), "Other Workout") == "Other Workout"

    def test_has_mind_and_body(self):
        assert WORKOUT_MAP[("mind_and_body", "generic")] == "Mind and Body"


class TestConstants:
    def test_cadence_multiplier(self):
        assert CADENCE_MULTIPLIER == 2

    def test_hr_zone_thresholds(self):
        assert HR_ZONE_THRESHOLDS == [60, 70, 80, 90]
