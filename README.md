# Apple Watch Fitness FIT Parser

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Ruff](https://img.shields.io/badge/lint-ruff-red.svg)](https://docs.astral.sh/ruff/)
[![mypy](https://img.shields.io/badge/types-mypy-blue.svg)](https://mypy.readthedocs.io/)

Parse `.fit` workout files exported from **Apple Fitness** into structured JSON containing workout metrics, heart rate zones, split times, and running dynamics.

## Overview

Apple Watch exports workouts as `.fit` files (binary format from Garmin's FIT SDK). This tool extracts all relevant training data and produces clean, queryable JSON — making it easy to analyze your fitness data, import it into other tools, or build dashboards.

## Features

- **Workout classification** — maps Apple Watch sport/sub-sport pairs to human-readable labels (Outdoor Run, Indoor Rower, HIIT, etc.)
- **Heart rate zones** — calculates time and percentage in each of 5 zones based on max HR, plus peak and dominant zone
- **Split/lap data** — per-km auto-splits with pace, distance, calories, speed, heart rate, power, cadence, and running dynamics
- **Running dynamics** — vertical oscillation, stance time, step length, vertical ratio (for outdoor runs)
- **Weather data** — temperature and humidity extracted when available
- **Batch processing** — parse an entire folder of `.fit` files in one run
- **Typed & tested** — full type hints (strict mypy), 45 passing tests, ruff linted and formatted

## Installation

```bash
cd SportHealthAppleWatch

# Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows CMD
.venv\Scripts\Activate.ps1      # Windows PowerShell
source .venv/bin/activate       # macOS/Linux

# Install dependencies
pip install -e ".[dev]"
```

### Dependencies

| Package | Purpose |
|---------|---------|
| `fitparse` | Parse Garmin FIT binary files |
| `python-dotenv` | Load `.env` configuration |
| `ruff` | Linting and formatting (dev) |
| `mypy` | Static type checking (dev) |
| `pytest`, `pytest-cov` | Testing and coverage (dev) |

## Usage

### Command Line

```bash
# Basic usage (reads FIT_FOLDER from .env)
python -m fit_parser

# Specify input and output explicitly
python -m fit_parser --input Z:\ --output workouts.json

# Verbose logging
python -m fit_parser --input Z:\ --output workouts.json --verbose
```

### Environment Variables

Create a `.env` file in the project root:

```env
FIT_FOLDER=Z:\
```

Or override via the `--input` flag.

### Programmatic API

```python
from fit_parser import parse_single_fit_file, batch_process_directory

# Parse a single file
workout = parse_single_fit_file("path/to/workout.fit")
print(workout.workout_type)       # "Outdoor Run"
print(workout.avg_heart_rate_bpm) # 155
print(workout.to_dict())          # Serializes to dict for JSON

# Parse a directory
all_workouts = batch_process_directory("Z:\\fitness_exports\\")
```

## Output Schema

The output is a JSON array of workout objects. Here's a sample:

```json
{
  "filename": "2025-03-24-180624-Elliptical.fit",
  "workout_type": "Indoor Elliptical",
  "total_distance_km": 3.2,
  "total_timer_time": "32:36",
  "avg_pace_min_per_km": "10:11",
  "avg_heart_rate_bpm": 170,
  "max_heart_rate_bpm": 199,
  "min_heart_rate_bpm": 145,
  "active_calories_kcal": 383,
  "elevation_gain_meters": 0.0,
  "temperature_c": 1,
  "humidity_pct": 84.0,
  "avg_running_cadence": 92,
  "start_time": "2025-03-24 22:06:24",
  "peak_hr_zone": 5,
  "dominant_hr_zone": 4,
  "hr_zone_distribution": {
    "zone_1_time": "00:00", "zone_1_pct": 0.0,
    "zone_2_time": "00:00", "zone_2_pct": 0.0,
    "zone_3_time": "04:48", "zone_3_pct": 15.6,
    "zone_4_time": "18:52", "zone_4_pct": 61.5,
    "zone_5_time": "07:02", "zone_5_pct": 22.9
  },
  "laps_info": [
    {
      "time": "06:30",
      "pace": "6:30",
      "distance_km": 1.0,
      "calories": 85,
      "avg_speed_kmh": 9.2,
      "heart_rate": { "avg": 165, "max": 180, "min": 140 },
      "power": { "avg": 250, "max": 400 },
      "cadence": { "avg": 160, "max": 180 },
      "strides": 430,
      "running_dynamics": {
        "vertical_oscillation_mm": 100.0,
        "stance_time_ms": 250.0,
        "step_length_mm": 1500.0,
        "vertical_ratio_pct": 6.7
      }
    }
  ]
}
```

### Heart Rate Zones

Zones are calculated as percentages of the workout's **max heart rate** (not age-based):

| Zone | Range | Description |
|------|-------|-------------|
| 1 | <60% | Very light |
| 2 | 60–69% | Light |
| 3 | 70–79% | Moderate |
| 4 | 80–89% | Hard |
| 5 | ≥90% | Maximum |

### Workout Types

The parser maps Apple Watch `(sport, sub_sport)` pairs to readable labels:

| Workout Type | Sport | Sub-Sport |
|--------------|-------|-----------|
| Outdoor Run | running | generic |
| Indoor Run | running | indoor_running |
| Outdoor Walk | walking | generic |
| Indoor Walk | walking | indoor_walking |
| Indoor Rower | fitness_equipment | indoor_rowing |
| Indoor Elliptical | fitness_equipment | elliptical |
| Hiking | hiking | generic |
| Strength Training | training | strength_training |
| HIIT | 62 (numeric) | 70 (numeric) |
| Dive | 53 (numeric) | generic |

Unmapped combinations default to `"Other Workout"`.

## Project Structure

```
src/fit_parser/
├── __init__.py      # Public API exports
├── __main__.py      # python -m fit_parser entry
├── cli.py           # argparse CLI (--input, --output, --verbose)
├── config.py        # WORKOUT_MAP, constants, zone thresholds
├── models.py        # Workout, Lap, HRZoneDistribution dataclasses
├── parsers.py       # FIT message parsers (session, lap, record)
├── zones.py         # HR zone classification + time distribution
├── formatters.py    # Pace, duration, zone summary formatting
└── logger.py        # Structured logging configuration
```

## Quality Gates

All checks must pass before merging:

```bash
# Lint
python -m ruff check src/ tests/

# Format
python -m ruff format src/ tests/

# Type check
python -m mypy src/

# Test with coverage
python -m pytest tests/ -v
```

## Known Limitations

- **BMR/Resting calories** — not stored in Apple Watch FIT exports (would require Apple Health XML)
- **Floors climbed** — available in some FIT files but not currently extracted
- **Indoor workouts** — no running dynamics or elevation data (GPS not available)
- **Cadence** — Apple reports per-leg; the parser multiplies by 2 to get full strides

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Make your changes and add tests
4. Run all quality gates (`ruff`, `mypy`, `pytest`)
5. Submit a pull request

## License

MIT — see [LICENSE](LICENSE) for details.
