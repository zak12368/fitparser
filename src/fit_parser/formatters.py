"""Formatting utilities for pace, duration, and HR zone summaries."""


def format_pace(total_time_s: float, distance_m: float) -> str | None:
    """Return pace as 'MM:SS' per km (e.g. '8:31').

    Args:
        total_time_s: Total elapsed time in seconds.
        distance_m: Total distance in meters.

    Returns:
        Formatted pace string, or None if inputs are invalid.
    """
    if not total_time_s or not distance_m or distance_m <= 0:
        return None
    pace_min = total_time_s / 60.0 / (distance_m / 1000.0)
    return f"{int(pace_min)}:{int((pace_min % 1) * 60):02d}"


def format_duration(seconds: float, include_hours: bool = True) -> str:
    """Return duration as 'H:MM:SS' or 'MM:SS'.

    Args:
        seconds: Duration in seconds.
        include_hours: If True, show hours when > 0. Otherwise always 'MM:SS'.

    Returns:
        Formatted duration string.
    """
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if include_hours and h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def format_hr_zone_summary(zone_seconds: dict[int, float], total_seconds: float) -> str:
    """Return a human-readable ASCII summary of HR zone distribution.

    Args:
        zone_seconds: Dict mapping zone number (1-5) to elapsed seconds.
        total_seconds: Total tracked seconds across all zones.

    Returns:
        Multi-line ASCII bar chart of zone distribution.
    """
    lines: list[str] = []
    max_bar = 20
    max_sec = max(zone_seconds.values()) if zone_seconds and max(zone_seconds.values()) > 0 else 1

    for zone in range(1, 6):
        sec = zone_seconds.get(zone, 0)
        pct = (sec / total_seconds * 100) if total_seconds > 0 else 0
        bar_len = round(sec / max_sec * max_bar) if max_sec > 0 else 0
        bar = "#" * bar_len
        lines.append(f"  Zone {zone}: {sec:6.0f}s ({pct:5.1f}%) |{bar}")

    return "\n".join(lines) + f"\n  Total: {total_seconds:.0f}s tracked"
