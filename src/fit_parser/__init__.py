"""Apple Watch Fitness+ FIT Parser.

Extracts workout metrics from .fit files exported from Apple Fitness+.
Uses sport + sub_sport fields from session blocks for workout typing.

Public API:
    parse_single_fit_file  — parse one .fit file into a Workout dict
    batch_process_directory — parse all .fit files in a folder
"""

from fit_parser.cli import main
from fit_parser.config import WORKOUT_MAP
from fit_parser.formatters import format_duration, format_hr_zone_summary, format_pace
from fit_parser.models import HRZoneDistribution, Lap, Workout
from fit_parser.parsers import batch_process_directory, parse_single_fit_file
from fit_parser.zones import (
    calculate_hr_zone,
    calculate_hr_zone_distribution,
)

__all__ = [
    "WORKOUT_MAP",
    "HRZoneDistribution",
    "Lap",
    "Workout",
    "batch_process_directory",
    "calculate_hr_zone",
    "calculate_hr_zone_distribution",
    "format_duration",
    "format_hr_zone_summary",
    "format_pace",
    "main",
    "parse_single_fit_file",
]
