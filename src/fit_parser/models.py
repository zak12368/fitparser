"""Data models for parsed FIT file data.

All models are plain dataclasses that serialize cleanly to JSON via
their `model_dump()` method or `asdict()` from the dataclasses module.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Lap:
    """Per-lap (1km split) metrics from an Apple Watch FIT file."""

    time: str  # "MM:SS"
    pace: str | None = None  # "M:SS/km" or None
    distance_km: float | None = None
    calories: int | None = None
    avg_speed_kmh: float | None = None
    heart_rate: dict[str, int] = field(default_factory=dict)
    power: dict[str, int] | None = None
    cadence: dict[str, int] = field(default_factory=dict)
    strides: int | None = None
    running_dynamics: dict[str, float] | None = None


@dataclass
class HRZoneDistribution:
    """Time-in-HR-Zone distribution for a workout."""

    zone_times: dict[int, str]  # zone_number -> "MM:SS"
    zone_pcts: dict[int, float]  # zone_number -> percentage (0-100)
    dominant_zone: int  # zone with most time


@dataclass
class Workout:
    """Complete workout record parsed from a single .fit file."""

    filename: str
    workout_type: str | None = None
    total_distance_km: float | None = None
    total_timer_time: str | None = None
    avg_pace_min_per_km: str | None = None
    avg_heart_rate_bpm: int | None = None
    max_heart_rate_bpm: int | None = None
    min_heart_rate_bpm: int | None = None
    active_calories_kcal: int | None = None
    elevation_gain_meters: float | None = None
    temperature_c: int | None = None
    humidity_pct: float | None = None
    avg_running_cadence: int | None = None
    lap_count: int | None = None
    start_time: str | None = None
    laps_info: list[Lap] = field(default_factory=list)
    peak_hr_zone: int | None = None
    hr_zone_distribution: HRZoneDistribution | None = None
    dominant_hr_zone: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to a flat JSON-serializable dict (backward compatible keys)."""
        import dataclasses

        result: dict[str, Any] = {}
        for fld in dataclasses.fields(self):
            value = getattr(self, fld.name)
            if value is None and fld.name not in ("filename",):
                continue

            # Serialize hr_zone_distribution as nested object (backward-compatible)
            if fld.name == "hr_zone_distribution" and value is not None:
                result["hr_zone_distribution"] = {
                    f"zone_{z}_time": value.zone_times.get(z)
                    for z in range(1, 6)
                }
                result["hr_zone_distribution"].update(
                    {
                        f"zone_{z}_pct": value.zone_pcts.get(z)
                        for z in range(1, 6)
                    }
                )
                continue

            # Omit empty lists
            if fld.name == "laps_info" and not value:
                continue

            # Serialize Lap dataclasses to dicts
            if fld.name == "laps_info":
                result["laps_info"] = [_lap_to_dict(x) for x in value]
                continue

            result[fld.name] = value

        return result


def _lap_to_dict(lap: Lap) -> dict[str, Any]:
    """Convert a Lap to a JSON-serializable dict, omitting empty values."""
    result: dict[str, Any] = {}
    import dataclasses

    for fld in dataclasses.fields(lap):
        value = getattr(lap, fld.name)
        if value is None or value == {}:
            continue
        result[fld.name] = value

    return result
