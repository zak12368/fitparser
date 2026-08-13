# Apple Watch Fitness+ FIT Parser — Project Context

## Quick Start (Next Session)

```bash
cd C:\Users\zakar\SportHealthAppleWatch

# Activate venv
.venv\Scripts\activate

# Run the parser (reads FIT_FOLDER=Z:\ from .env)
python -m fit_parser

# Override input/output
python -m fit_parser --input Z:\ --output processed_workouts_final.json

# Run tests
python -m pytest tests/ -v

# Lint + type-check
python -m ruff check src/ tests/
python -m ruff format src/ tests/
python -m mypy src/
```

**Key files:**
| Path | Purpose |
|------|---------|
| `src/fit_parser/` | Production package (9 modules, ~1060 lines) |
| `tests/` | Test suite (45 tests) |
| `pyproject.toml` | Dependencies + tool config (ruff, mypy, pytest) |
| `.env` | Environment variables (`FIT_FOLDER=Z:\`) |
| `newmethod.py` | Legacy monolithic script (reference only) |
| `processed_workouts_final.json` | Output file (163 workouts) |

---

## 1. Current Status

**Parser is production-ready.** Refactored from a monolithic script into a typed, tested, linted Python package. All quality gates pass:

| Check | Result |
|-------|--------|
| mypy (9 source files) | 0 errors |
| ruff check (lint) | 0 issues |
| ruff format | 14 files formatted |
| pytest | 45/45 passing |
| End-to-end | 163/163 FIT files parsed |

The refactored package produces **identical JSON output** to the legacy `newmethod.py` — all keys are backward-compatible.

---

## 2. Architecture (`src/fit_parser/`)

```
src/fit_parser/
├── __init__.py      # Public API exports
├── __main__.py      # python -m fit_parser entry
├── cli.py           # argparse CLI (--input, --output, --verbose)
├── config.py        # WORKOUT_MAP, constants, zone thresholds
├── models.py        # Workout, Lap, HRZoneDistribution dataclasses
├── parsers.py       # FIT message parsers (session, lap, record) — core logic
├── zones.py         # HR zone classification + time distribution
├── formatters.py    # Pace, duration, zone summary formatting
└── logger.py        # Standard logging config
```

**Design decisions:**
- Dataclasses for all models; `Workout.to_dict()` serializes to JSON
- PEP 604 union syntax (`X | None`) throughout
- Proper logging via `get_logger(__name__)` — no `print()` calls
- `.env` loaded from project root (3 levels up from `src/fit_parser/`)
- Zone thresholds are relative to workout's `max_heart_rate_bpm` (not age-based)

---

## 3. JSON Output Schema

`processed_workouts_final.json` — array of workout objects:

| Key | Type | Source | Coverage |
|-----|------|--------|----------|
| `filename` | string | FIT basename | 163/163 |
| `workout_type` | string | WORKOUT_MAP lookup | 163/163 |
| `total_distance_km` | float | session.total_distance | ~150/163 |
| `total_timer_time` | string | session.total_timer_time | 163/163 (`"H:MM:SS"` or `"M:SS"`) |
| `avg_pace_min_per_km` | string | calculated | ~150/163 (`"M:SS"`) |
| `avg_heart_rate_bpm` | int | session.avg_heart_rate | ~160/163 |
| `max_heart_rate_bpm` | int | session.max_heart_rate | ~160/163 |
| `min_heart_rate_bpm` | int | session.min_heart_rate | ~160/163 |
| `active_calories_kcal` | int | session.total_calories | ~160/163 |
| `elevation_gain_meters` | float | session.total_ascent | ~80/163 |
| `temperature_c` | int | session.avg_temperature | 151/163 |
| `humidity_pct` | float | session.SESSION WEATHER HUMIDITY / 100 | 151/163 |
| `avg_running_cadence` | int | session.avg_running_cadence × 2 | ~100/163 |
| `start_time` | string | session.start_time | 163/163 |
| `peak_hr_zone` | int | calculated | ~160/163 |
| `dominant_hr_zone` | int | most time spent | 158/163 |
| `hr_zone_distribution` | object | nested dict: `zone_{1-5}_time` + `zone_{1-5}_pct` | 158/163 |
| `laps_info` | array | per-lap split objects | 127/163 |

### `hr_zone_distribution` structure (nested object):
```json
{
  "zone_1_time": "00:00", "zone_1_pct": 0.0,
  "zone_2_time": "00:00", "zone_2_pct": 0.0,
  "zone_3_time": "04:48", "zone_3_pct": 15.6,
  "zone_4_time": "18:52", "zone_4_pct": 61.5,
  "zone_5_time": "07:02", "zone_5_pct": 22.9
}
```

### `laps_info` structure (per 1km auto-split):
```json
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
```

---

## 4. Workout Type Mapping

Resolved via `(sport, sub_sport)` lookup in `WORKOUT_MAP` (`src/fit_parser/config.py`):

| sport | sub_sport | → workout_type | count |
|-------|-----------|----------------|-------|
| walking | generic | Outdoor Walk | 67 |
| running | indoor_running | Indoor Run | 59 |
| running | generic | Outdoor Run | 20 |
| walking | indoor_walking | Indoor Walk | 4 |
| fitness_equipment | indoor_rowing | Indoor Rower | 4 |
| hiking | generic | Hiking | 2 |
| fitness_equipment | elliptical | Indoor Elliptical | 1 |
| training | strength_training | Strength Training | 1 |
| 53 | generic | Dive | 1 |
| 62 | 70 | HIIT | 1 |

**Apple Watch non-standard mappings:**
- `indoor_running` (not `treadmill_running`), `indoor_rowing` (not `magnetic_rower`)
- HIIT = numeric IDs `62`/`70`; Dive = `53`/`generic`
- Fallback: unmapped → `"Other Workout"`

---

## 5. Known Edge Cases & Gotchas

| Issue | Behaviour | Location |
|-------|-----------|----------|
| Missing HR data | Zone distribution omitted silently (2 workouts) | `parsers.py:290` |
| Missing weather data | Keys omitted silently (9 workouts: dive, indoor rowing, MyNetDiary export, walks without sensor data) | `parsers.py:100-105` |
| No running dynamics indoors | `running_dynamics` is null for indoor workouts | `parsers.py:171` |
| Cadence half-rate | Apple reports per-leg; multiplied by 2 | `CADENCE_MULTIPLIER = 2` |
| Calories are active only | BMR/resting calories not in FIT file | Apple Watch limitation |
| Humidity raw units | Stored as 0.01% — divided by 100 for `%` | `parsers.py:103` |
| `round(None)` crash | Guarded with `_round1()` helper | `parsers.py:173` |
| FIT file special chars | fitparse handles them; no rename needed | `fitparse` library |

---

## 6. Feature Status

### Done
- [x] HR zone distribution (time + pct per zone, dominant zone)
- [x] Weather extraction (temperature + humidity)
- [x] Split/lap data (enriched with HR, power, cadence, running dynamics)
- [x] Full codebase refactoring (src layout, dataclasses, type hints, tests, linting)
- [x] CLI entry point with argparse
- [x] Proper logging (structured, loguru-style)

### Deferred
- [ ] BMR/Resting calories — not available in FIT file; requires Apple Health XML
- [ ] Floors climbed — `floors_climbed` field exists in some FIT exports (low priority)
- [ ] Console ASCII zone visualization — `format_hr_zone_summary()` exists but not wired into CLI

---

## 7. Environment

- **OS:** Windows (CMD / PowerShell)
- **Python:** 3.14.0
- **Venv:** `.venv/` (use `.venv\Scripts\activate` or `.venv\Scripts\python.exe`)
- **FIT files:** `Z:\` (mapped NAS drive `\\NAS\personal_folder\Files\HealthDataApple\`)
- **Dataset:** 163 `.fit` files (March 2025 – August 2026)
- **Dependencies (runtime):** `fitparse`
- **Dependencies (dev):** `ruff`, `mypy`, `pytest`, `pytest-cov`
- **Tool config:** `pyproject.toml` (build backend: `setuptools.build_meta`)
- **Console output:** ASCII-safe (no emojis in terminal)
