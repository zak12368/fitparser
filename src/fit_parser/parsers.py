"""Core FIT message parsers.

Parses session, lap, and record messages from Apple Watch FIT files
into structured Workout data.
"""

from datetime import datetime
from typing import Any

from fitparse import FitFile

from fit_parser.config import CADENCE_MULTIPLIER, WORKOUT_MAP
from fit_parser.formatters import format_duration, format_pace
from fit_parser.logger import get_logger
from fit_parser.models import HRZoneDistribution, Lap, Workout

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Safe converters
# ---------------------------------------------------------------------------


def _safe_int(value: object | None) -> int | None:
    """Convert FIT value to int, returning None on failure."""
    if value is None:
        return None
    try:
        return int(value)  # type: ignore[call-overload, no-any-return]
    except (ValueError, TypeError):
        return None


def _safe_float(value: object | None) -> float | None:
    """Convert FIT value to float, returning None on failure."""
    if value is None:
        return None
    try:
        return float(value)  # type: ignore[arg-type]
    except (ValueError, TypeError):
        return None


def _build_workout_name(sport: str, sub_sport: str) -> str:
    """Look up the human-readable workout name from sport + sub_sport."""
    return WORKOUT_MAP.get((str(sport), str(sub_sport)), "Other Workout")


# ---------------------------------------------------------------------------
# Session parser
# ---------------------------------------------------------------------------


def _parse_session(fit_file: FitFile) -> dict[str, Any]:
    """Extract metrics from the session summary block."""
    metrics: dict[str, Any] = {}
    for message in fit_file.get_messages("session"):
        # -- Sport identification --
        sport = message.get_value("sport")
        sub_sport = message.get_value("sub_sport")
        if sport and sub_sport:
            metrics["workout_type"] = _build_workout_name(sport, sub_sport)

        # -- Distance & Time --
        total_dist = message.get_value("total_distance")  # meters
        total_time = message.get_value("total_timer_time")  # seconds
        metrics["total_distance_km"] = round(total_dist / 1000.0, 2) if total_dist else None
        metrics["total_timer_time"] = format_duration(total_time or 0)
        metrics["avg_pace_min_per_km"] = format_pace(total_time or 0, total_dist or 0)

        # -- Heart Rate --
        metrics["avg_heart_rate_bpm"] = _safe_int(message.get_value("avg_heart_rate"))
        metrics["max_heart_rate_bpm"] = _safe_int(message.get_value("max_heart_rate"))
        metrics["min_heart_rate_bpm"] = _safe_int(message.get_value("min_heart_rate"))

        # -- Calories (active only — Apple Watch FIT stores active calories) --
        total_cal = message.get_value("total_calories")
        if total_cal is not None:
            metrics["active_calories_kcal"] = int(total_cal)

        # -- Elevation --
        metrics["elevation_gain_meters"] = _safe_float(message.get_value("total_ascent"))

        # -- Weather (temperature + humidity) --
        avg_temp = message.get_value("avg_temperature")
        if avg_temp is not None:
            metrics["temperature_c"] = int(avg_temp)

        humidity_raw = message.get_value("SESSION WEATHER HUMIDITY")
        if humidity_raw is not None:
            metrics["humidity_pct"] = round(int(humidity_raw) / 100, 1)

        # -- Cadence --
        avg_cadence_raw = message.get_value("avg_running_cadence")
        if avg_cadence_raw:
            metrics["avg_running_cadence"] = int(avg_cadence_raw * CADENCE_MULTIPLIER)

        # -- Lap count --
        num_laps = message.get_value("num_laps")
        if num_laps is not None:
            metrics["lap_count"] = int(num_laps)

        # -- Timestamps --
        start_time = message.get_value("start_time")
        if start_time:
            metrics["start_time"] = str(start_time)

        # Session block is singular; stop after first
        break
    return metrics


# ---------------------------------------------------------------------------
# Lap parser
# ---------------------------------------------------------------------------


def _parse_laps(fit_file: FitFile) -> list[Lap]:
    """
    Extract per-lap (1km split) metrics.

    Apple Watch auto-splits by distance (1000 m) — these are your split times.
    Returns enriched Lap objects with HR/power/cadence as {avg, max} dicts.
    """
    laps: list[Lap] = []
    for message in fit_file.get_messages("lap"):
        total_dist = message.get_value("total_distance")  # meters
        total_time = message.get_value("total_timer_time")  # seconds

        # -- Heart rate (avg + range) --
        avg_hr = message.get_value("avg_heart_rate")
        max_hr = message.get_value("max_heart_rate")
        min_hr = message.get_value("min_heart_rate")
        hr_data = _filter_none(
            {
                "avg": _safe_int(avg_hr),
                "max": _safe_int(max_hr),
                "min": _safe_int(min_hr),
            }
        )

        # -- Power (avg + max) --
        avg_power = message.get_value("avg_power")
        max_power = message.get_value("max_power")
        power_data = (
            _filter_none(
                {
                    "avg": _safe_int(avg_power),
                    "max": _safe_int(max_power),
                }
            )
            or None
        )

        # -- Cadence (running or walking, avg + max) --
        avg_cad_raw = message.get_value("avg_running_cadence") or message.get_value("avg_cadence")
        max_cad_raw = message.get_value("max_running_cadence") or message.get_value("max_cadence")
        cad_data = _filter_none(
            {
                "avg": int(avg_cad_raw * CADENCE_MULTIPLIER) if avg_cad_raw else None,
                "max": int(max_cad_raw * CADENCE_MULTIPLIER) if max_cad_raw else None,
            }
        )

        # -- Speed (m/s -> km/h) --
        avg_speed = message.get_value("enhanced_avg_speed") or message.get_value("avg_speed")

        # -- Strides --
        total_strides = message.get_value("total_strides")

        # -- Running dynamics (outdoor running only) --
        def _round1(v: object | None) -> float | None:
            return round(float(v), 1) if v is not None else None  # type: ignore[arg-type]

        dyn = (
            _filter_none(
                {
                    "vertical_oscillation_mm": _round1(
                        message.get_value("avg_vertical_oscillation")
                    ),
                    "stance_time_ms": _round1(message.get_value("avg_stance_time")),
                    "step_length_mm": _round1(message.get_value("avg_step_length")),
                    "vertical_ratio_pct": _round1(message.get_value("avg_vertical_ratio")),
                }
            )
            or None
        )

        # -- Calories per lap --
        lap_cal = message.get_value("total_calories")

        lap = Lap(
            time=format_duration(total_time or 0, include_hours=False),
            pace=format_pace(total_time or 0, total_dist or 0),
            distance_km=round(total_dist / 1000, 2) if total_dist else None,
            calories=_safe_int(lap_cal),
            avg_speed_kmh=round(avg_speed * 3.6, 1) if avg_speed else None,
            heart_rate=hr_data,
            power=power_data,
            cadence=cad_data,
            strides=_safe_int(total_strides),
            running_dynamics=dyn,
        )
        laps.append(lap)
    return laps


# ---------------------------------------------------------------------------
# Record parser
# ---------------------------------------------------------------------------


def _parse_records(fit_file: FitFile) -> dict[str, Any]:
    """
    Iterate individual records to recover distance and HR when
    the session summary is incomplete.

    Also collects (timestamp, hr) pairs for zone distribution analysis.
    """
    hr_values: list[int] = []
    hr_timestamps: list[tuple[datetime, int]] = []
    max_distance = 0.0

    for message in fit_file.get_messages("record"):
        hr = message.get_value("heart_rate")
        timestamp = message.get_value("timestamp")
        if hr:
            hr_values.append(int(hr))
            if timestamp:
                hr_timestamps.append((timestamp, int(hr)))

        dist = message.get_value("distance")  # cumulative
        if dist:
            max_distance = max(max_distance, dist)

    return {
        "total_distance_m": max_distance,
        "hr_values": hr_values,
        "hr_timestamps": hr_timestamps,
    }


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _filter_none(d: dict[str, Any]) -> dict[str, Any]:
    """Remove None values from a dict, returning empty dict if all None."""
    return {k: v for k, v in d.items() if v is not None}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse_single_fit_file(file_path: str) -> Workout | None:
    """Parse a single .fit file and return a Workout dataclass.

    Args:
        file_path: Absolute or relative path to a .fit file.

    Returns:
        A Workout object, or None if parsing fails.
    """
    import os

    basename = os.path.basename(file_path)
    try:
        fit_file = FitFile(file_path)
    except Exception as e:
        logger.warning("Skipping %s: %s", basename, e)
        return None

    # -- 1. Parse session summary (primary source) --
    session_metrics = _parse_session(fit_file)

    # -- 2. Parse laps --
    laps = _parse_laps(fit_file)

    # -- 3. Parse records (fallback + HR zone distribution) --
    records = _parse_records(fit_file)

    # Fallback: recover distance from records if session is missing it
    if session_metrics.get("total_distance_km") is None and records["total_distance_m"] > 0:
        session_metrics["total_distance_km"] = round(records["total_distance_m"] / 1000.0, 2)

    # Fallback: recover avg HR from records
    if session_metrics.get("avg_heart_rate_bpm") is None and records["hr_values"]:
        session_metrics["avg_heart_rate_bpm"] = round(
            sum(records["hr_values"]) / len(records["hr_values"]), 1
        )

    # -- 4. Peak HR zone --
    max_hr = session_metrics.get("max_heart_rate_bpm")
    peak_zone = None
    if max_hr:
        from fit_parser.zones import calculate_hr_zone

        peak_zone = calculate_hr_zone(max_hr, max_hr)

    # -- 5. HR zone distribution --
    hr_zone_dist = None
    dominant_zone = None
    if max_hr and records.get("hr_timestamps"):
        from fit_parser.zones import calculate_hr_zone_distribution

        zone_seconds = calculate_hr_zone_distribution(records["hr_timestamps"], max_hr)
        if zone_seconds:
            total_zone_sec = sum(zone_seconds.values())
            zone_times: dict[int, str] = {}
            zone_pcts: dict[int, float] = {}
            for z in range(1, 6):
                sec = zone_seconds.get(z, 0)
                zone_times[z] = format_duration(sec, include_hours=False)
                zone_pcts[z] = round(sec / total_zone_sec * 100, 1) if total_zone_sec > 0 else 0.0

            hr_zone_dist = HRZoneDistribution(
                zone_times=zone_times,
                zone_pcts=zone_pcts,
                dominant_zone=max(zone_seconds, key=lambda k: zone_seconds[k]),
            )
            dominant_zone = hr_zone_dist.dominant_zone

    # -- 6. Build Workout --
    workout = Workout(
        filename=basename,
        peak_hr_zone=peak_zone,
        hr_zone_distribution=hr_zone_dist,
        dominant_hr_zone=dominant_zone,
        laps_info=laps,
        **session_metrics,
    )

    # Return only if we got at least one meaningful metric
    if workout.workout_type or workout.total_distance_km or workout.avg_heart_rate_bpm:
        return workout
    logger.debug("Skipping %s: no valid data extracted", basename)
    return None


def batch_process_directory(directory_path: str) -> list[Workout]:
    """Process all .fit files in a directory and return a list of Workout objects.

    Args:
        directory_path: Path to a directory containing .fit files.

    Returns:
        List of Workout objects for successfully parsed files.
    """
    import os

    workout_records: list[Workout] = []
    logger.info("Scanning directory: %s", directory_path)

    for filename in sorted(os.listdir(directory_path)):
        if not filename.lower().endswith(".fit"):
            continue

        full_path = os.path.join(directory_path, filename)
        result = parse_single_fit_file(full_path)
        if result:
            workout_records.append(result)
        else:
            logger.debug("No valid data from %s", filename)

    logger.info("Successfully processed %d files", len(workout_records))
    return workout_records
