"""
Apple Watch Fitness+ FIT Parser
Extracts workout metrics from .fit files exported from Apple Fitness+.
Uses sport + sub_sport fields from session blocks for workout typing.
"""

import os
import json
import re
from typing import Optional
from fitparse import FitFile
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CADENCE_MULTIPLIER = 2  # Apple stores cadence as half-strides

# ---------------------------------------------------------------------------
# Sport / Sub-sport -> Human-readable workout name mapping
# ---------------------------------------------------------------------------

WORKOUT_MAP: dict[tuple[str, str], str] = {
    # Running
    ("running", "generic"): "Outdoor Run",
    ("running", "indoor_running"): "Indoor Run",
    # Walking
    ("walking", "generic"): "Outdoor Walk",
    ("walking", "indoor_walking"): "Indoor Walk",
    # Cycling
    ("cycling", "road_cycling"): "Outdoor Cycling",
    ("cycling", "mountain_cycling"): "Mountain Cycling",
    ("cycling", "indoor_cycling"): "Indoor Cycling",
    # Fitness Equipment (always indoor)
    ("fitness_equipment", "elliptical"): "Indoor Elliptical",
    ("fitness_equipment", "indoor_rowing"): "Indoor Rower",
    ("fitness_equipment", "other_cardio"): "Indoor Cardio",
    # Swimming
    ("swimming", "pool_swimming"): "Pool Swim",
    ("swimming", "open_water_swimming"): "Open Water Swim",
    # HIIT / Strength / Yoga
    ("hiit", "generic"): "HIIT",
    ("yoga", "generic"): "Yoga",
    ("core_training", "generic"): "Core Training",
    ("functional_strength_training", "generic"): "Functional Strength Training",
    ("training", "strength_training"): "Strength Training",
    ("mind_and_body", "generic"): "Mind and Body",
    ("mind_and_body", "yoga"): "Yoga",
    # Hiking
    ("hiking", "generic"): "Hiking",
    # Apple Watch numeric sport IDs (fallback for non-standard sports)
    # 53 = Dive (Apple Watch)
    ("53", "generic"): "Dive",
    # 62/70 = HIIT (Apple Watch)
    ("62", "70"): "HIIT",
    # Generic fallback
    ("generic", "generic"): "Other Workout",
}

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def format_pace(total_time_s: float, distance_m: float) -> Optional[str]:
    """Return pace as 'MM:SS' per km (e.g. '8:31')."""
    if not total_time_s or not distance_m or distance_m <= 0:
        return None
    pace_min = total_time_s / 60.0 / (distance_m / 1000.0)
    return f"{int(pace_min)}:{int((pace_min % 1) * 60):02d}"


def format_duration(seconds: float, include_hours: bool = True) -> str:
    """Return duration as 'H:MM:SS' or 'M:SS' (e.g. '1:14:55' or '10:59')."""
    if not seconds:
        return "0:00:00"
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if include_hours and h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def calculate_hr_zone(hr: int, max_hr: int) -> Optional[int]:
    """Return HR zone (1-5) for a given BPM based on max HR percentage."""
    if not hr or not max_hr:
        return None
    pct = (hr / max_hr) * 100
    if pct < 60:
        return 1
    if pct < 70:
        return 2
    if pct < 80:
        return 3
    if pct < 90:
        return 4
    return 5


def build_workout_name(sport: str, sub_sport: str) -> str:
    """Look up the human-readable workout name from sport + sub_sport."""
    return WORKOUT_MAP.get((sport, sub_sport), "Other Workout")


# ---------------------------------------------------------------------------
# FIT message parsers
# ---------------------------------------------------------------------------


def _safe_int(value) -> Optional[int]:
    """Convert FIT value to int, returning None on failure."""
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _safe_float(value) -> Optional[float]:
    """Convert FIT value to float, returning None on failure."""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def parse_session(fit_file: FitFile) -> dict:
    """Extract metrics from the session summary block."""
    metrics: dict = {}
    for message in fit_file.get_messages("session"):
        # -- Sport identification --
        sport = message.get_value("sport")
        sub_sport = message.get_value("sub_sport")
        if sport and sub_sport:
            metrics["workout_type"] = build_workout_name(str(sport), str(sub_sport))

        # -- Distance & Time --
        total_dist = message.get_value("total_distance")  # meters
        total_time = message.get_value("total_timer_time")  # seconds
        metrics["total_distance_km"] = round(total_dist / 1000.0, 2) if total_dist else None
        metrics["total_timer_time"] = format_duration(total_time or 0)
        metrics["avg_pace_min_per_km"] = format_pace(
            total_time or 0, total_dist or 0
        )

        # -- Heart Rate --
        metrics["avg_heart_rate_bpm"] = _safe_int(
            message.get_value("avg_heart_rate")
        )
        metrics["max_heart_rate_bpm"] = _safe_int(
            message.get_value("max_heart_rate")
        )
        metrics["min_heart_rate_bpm"] = _safe_int(
            message.get_value("min_heart_rate")
        )

        # -- Calories --
        # Note: Apple Watch FIT exports store ACTIVE calories in the
        # "total_calories" field. True total calories (active + BMR)
        # are NOT exported in the FIT file.
        total_cal = message.get_value("total_calories")
        if total_cal is not None:
            metrics["active_calories_kcal"] = int(total_cal)

        # -- Elevation --
        metrics["elevation_gain_meters"] = _safe_float(
            message.get_value("total_ascent")
        )

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


def parse_laps(fit_file: FitFile) -> list[dict]:
    """Extract per-lap metrics (pace, cadence, HR, power)."""
    laps: list[dict] = []
    for message in fit_file.get_messages("lap"):
        total_dist = message.get_value("total_distance")  # meters
        total_time = message.get_value("total_timer_time")  # seconds
        avg_cadence_raw = message.get_value("avg_running_cadence")
        avg_hr = message.get_value("avg_heart_rate")
        avg_power = message.get_value("avg_power")

        lap: dict = {
            "time": format_duration(total_time, include_hours=False),
            "pace": format_pace(total_time or 0, total_dist or 0),
            "heart_rate": _safe_int(avg_hr),
            "power": _safe_int(avg_power),
            "cadence": (
                int(avg_cadence_raw * CADENCE_MULTIPLIER) if avg_cadence_raw else None
            ),
        }
        laps.append(lap)
    return laps


def parse_records(fit_file: FitFile) -> dict:
    """
    Fallback: iterate individual records to recover distance and HR
    when session summary is incomplete.
    Also collects all HR values for zone analysis.
    """
    hr_values: list[int] = []
    max_distance = 0.0

    for message in fit_file.get_messages("record"):
        hr = message.get_value("heart_rate")
        if hr:
            hr_values.append(int(hr))

        dist = message.get_value("distance")  # cumulative
        if dist:
            max_distance = max(max_distance, dist)

    return {
        "total_distance_m": max_distance,
        "hr_values": hr_values,
    }


# ---------------------------------------------------------------------------
# Main parser
# ---------------------------------------------------------------------------


def parse_single_fit_file(file_path: str) -> Optional[dict]:
    """Parse a single .fit file and extract all available metrics."""
    try:
        fit_file = FitFile(file_path)
    except Exception as e:
        print(f"[SKIP] {os.path.basename(file_path)}: Error reading file ({e})")
        return None

    # -- 1. Parse session summary (primary source) --
    metrics: dict = {
        "filename": os.path.basename(file_path),
    }
    metrics.update(parse_session(fit_file))

    # -- 2. Parse laps --
    laps = parse_laps(fit_file)
    if laps:
        metrics["laps_info"] = laps

    # -- 3. Parse records (fallback for missing session data) --
    records = parse_records(fit_file)

    if metrics.get("total_distance_km") is None and records["total_distance_m"] > 0:
        metrics["total_distance_km"] = round(records["total_distance_m"] / 1000.0, 2)

    if (
        metrics.get("avg_heart_rate_bpm") is None
        and records["hr_values"]
    ):
        metrics["avg_heart_rate_bpm"] = round(
            sum(records["hr_values"]) / len(records["hr_values"]), 1
        )

    # -- 4. Calculate peak HR zone from session max --
    if metrics.get("max_heart_rate_bpm"):
        metrics["peak_hr_zone"] = calculate_hr_zone(
            metrics["max_heart_rate_bpm"], metrics["max_heart_rate_bpm"]
        )

    # -- 5. Return only if we got at least one meaningful metric --
    if (
        metrics.get("total_distance_km")
        or metrics.get("avg_heart_rate_bpm")
        or metrics.get("workout_type")
    ):
        return metrics
    return None


# ---------------------------------------------------------------------------
# Batch processing
# ---------------------------------------------------------------------------


def batch_process_directory(directory_path: str) -> list[dict]:
    """Process all .fit files in a directory and return a list of metric dicts."""
    workout_records: list[dict] = []
    print(f"Scanning directory: {directory_path}...")

    for filename in sorted(os.listdir(directory_path)):
        if not filename.lower().endswith(".fit"):
            continue

        full_path = os.path.join(directory_path, filename)
        print(f"Processing: {filename}...", end=" ")

        result = parse_single_fit_file(full_path)
        if result:
            workout_records.append(result)
            print("[SUCCESS]")
        else:
            print("[SKIPPED] No valid data")

    print(f"\nSuccessfully processed {len(workout_records)} files.")
    return workout_records


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    load_dotenv()
    FIT_FOLDER = os.getenv("FIT_FOLDER")

    if not FIT_FOLDER:
        print("Error: FIT_FOLDER environment variable is not set.")
        print('Add it to your .env file: FIT_FOLDER=//path/to/fit/files/')
        exit(1)

    if not os.path.exists(FIT_FOLDER):
        print(f"Error: Folder not found at {FIT_FOLDER}.")
        print("Please check your FIT_FOLDER path in .env.")
        exit(1)

    all_workouts_data = batch_process_directory(FIT_FOLDER)

    if all_workouts_data:
        output_file = "processed_workouts_final.json"
        with open(output_file, "w") as f:
            json.dump(all_workouts_data, f, indent=4)
        print("\n================================================")
        print(f"FINAL SYSTEM STATUS: All data saved to {output_file}")
        print("================================================")
    else:
        print("\nFAILURE: No files were processed successfully.")
