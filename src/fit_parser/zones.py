"""HR zone calculation logic.

Heart rate zones are calculated as a percentage of the workout's
maximum heart rate (not age-based max), preserving the original
Apple Watch relative zone model.

Zone 1: <60% of max HR
Zone 2: 60-69%
Zone 3: 70-79%
Zone 4: 80-89%
Zone 5: >=90%
"""

from datetime import datetime

from fit_parser.config import HR_ZONE_THRESHOLDS


def calculate_hr_zone(hr: int, max_hr: int) -> int | None:
    """Return HR zone (1-5) for a given BPM based on max HR percentage.

    Args:
        hr: Current heart rate in BPM.
        max_hr: Maximum heart rate for the workout.

    Returns:
        Zone number 1-5, or None if inputs are invalid.
    """
    if not hr or not max_hr:
        return None

    pct = (hr / max_hr) * 100
    for zone, threshold in enumerate(HR_ZONE_THRESHOLDS, start=1):
        if pct < threshold:
            return zone
    return 5


def calculate_hr_zone_distribution(
    hr_timestamps: list[tuple[datetime, int]],
    max_hr: int,
) -> dict[int, float] | None:
    """Calculate time spent in each HR zone (1-5) using consecutive record timestamps.

    Allocates elapsed seconds between consecutive records to the HR zone
    of the *preceding* record's BPM.

    Args:
        hr_timestamps: List of (datetime, bpm) tuples sorted by time.
        max_hr: Maximum heart rate for zone threshold calculation.

    Returns:
        Dict mapping zone number (1-5) to total seconds, or None if
        insufficient data.
    """
    if not hr_timestamps or not max_hr or len(hr_timestamps) < 2:
        return None

    zone_seconds: dict[int, float] = {z: 0.0 for z in range(1, 6)}

    for i in range(1, len(hr_timestamps)):
        prev_ts, prev_hr = hr_timestamps[i - 1]
        curr_ts, _curr_hr = hr_timestamps[i]

        elapsed = (curr_ts - prev_ts).total_seconds()
        if elapsed <= 0:
            continue

        zone = calculate_hr_zone(prev_hr, max_hr)
        if zone:
            zone_seconds[zone] += elapsed

    return zone_seconds
