# 🍎 Apple Watch Fitness+ Fit-Parser Context (Source of Truth)

## 1. Current Status ✅
The parser (`newmethod.py`) is **fully production-ready** and has successfully processed **160 workouts** with 100% mapping accuracy (Zero "Other Workout" remain). 

## 2. Core Strategy: Sport/Sub-Sport Lookup Table 🏃‍♂️
Workout types are resolved via a direct `(sport, sub_sport)` lookup dictionary (`WORKOUT_MAP`). No filename extraction, no binary inspection — pure FIT protocol fields from the session message.

**Discovered Apple Watch FIT sport/sub_sport values (11 unique combos across 160 workouts):**

| sport | sub_sport | workout_type | count |
|-------|-----------|--------------|-------|
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
| hiit | generic | HIIT | 0 (mapped but unused) |

**Key mappings that differ from FIT spec defaults:**
- Apple Watch uses `indoor_running` (not `treadmill_running`) for treadmill runs
- Apple Watch uses `indoor_rowing` (not `magnetic_rower`) for rowers
- Apple Watch uses `indoor_walking` (not `treadmill_running`) for treadmill walks
- Apple Watch uses `training`/`strength_training` (not `strength_training`/`generic`)
- HIIT = numeric IDs `62`/`70`; Dive = `53`/`generic`

**Fallback:** Any unmapped combo falls through to "Other Workout".

## 3. Architecture 🏗
`newmethod.py` is modular with three parsing functions:
- **`parse_session()`** — Extracts session-level metrics (distance, time, HR, calories, elevation)
- **`parse_laps()`** — Extracts per-lap metrics (time, pace, HR, power, cadence)
- **`parse_records()`** — Fallback for distance/HR when session summary is incomplete

Helper functions:
- **`format_pace(time_s, dist_m)`** → `"M:SS"` per km (e.g. `"8:31"`)
- **`format_duration(seconds, include_hours)`** → `"H:MM:SS"` or `"M:SS"`
- **`_safe_int()`** → Returns int or None
- **`calculate_hr_zone(bpm, max_hr)`** → Zone 1-5 (percentage-based)

Constants:
- **`CADENCE_MULTIPLIER = 2`** — Apple Watch reports half-cadence (per-leg), multiply by 2 for full strides/min
- **`OUTPUT_FILE = "processed_workouts_final.json"`**

## 4. Current Dataset Metrics 📊
`processed_workouts_final.json` extracts:

| Key | Type | Source | Notes |
|-----|------|--------|-------|
| `filename` | string | FIT file basename | |
| `workout_type` | string | WORKOUT_MAP lookup | |
| `total_distance_km` | float | session.total_distance | null if no distance |
| `total_timer_time` | string | session.total_timer_time | `"H:MM:SS"` or `"M:SS"` |
| `avg_pace_min_per_km` | string | calculated | `"M:SS"` per km |
| `avg_heart_rate_bpm` | int | session.avg_heart_rate | |
| `max_heart_rate_bpm` | int | session.max_heart_rate | |
| `min_heart_rate_bpm` | int | session.min_heart_rate | |
| `active_calories_kcal` | int | session.total_calories | Apple Watch FIT stores **active calories only** in this field |
| `elevation_gain_meters` | float | session.total_ascent | null if not available |
| `avg_running_cadence` | int | session.avg_running_cadence × 2 | null if not available |
| `lap_count` | int | session.num_laps | only present if >0 laps |
| `start_time` | string | session.start_time | `"YYYY-MM-DD HH:MM:SS"` |
| `laps_info` | array | per-lap | `[{time, pace, heart_rate, power, cadence}]` |
| `peak_hr_zone` | int | calculated from max_hr | Zone 1-5 |

**Lap `laps_info` fields:**
- `time` — `"MM:SS"` format (e.g. `"08:31"`)
- `pace` — `"M:SS"` per km or null
- `heart_rate` — int or null
- `power` — int or null
- `cadence` — int or null

## 5. Critical Apple Watch FIT Behavior ⚠️

### Calories
- Apple Watch FIT exports store **active calories** in the `total_calories` field
- True total calories (active + BMR/resting) are **NOT exported** in the FIT file
- The `active_calories` field in the FIT spec is **always None** for Apple Watch exports
- Example: A run showing 920 total calories in the Fitness app will have `total_calories=780` in the FIT file (780 = active only, 140 = BMR not exported)

### Cadence
- Apple Watch reports cadence as half-cadence (per-leg strikes)
- Must multiply by 2 to get full strides-per-minute

### Duration
- Stored as raw seconds (e.g. `4495.178`)
- Formatted by `format_duration()` for output

## 6. Next Target: Metric Expansion 🧭
Potential future additions:
- **Time-in-HR-Zone distribution** — Currently peak_hr_zone is calculated from max HR only; per-record tracking needed for full zone distribution
- **BMR/Resting calories** — Not in FIT file; would need to pull from Apple Health XML or HealthKit export
- **Split times / segment data** — Additional lap-level detail
- **Weather conditions** — If exported by Apple Watch (temperature, etc.)
- **Floors climbed** — `floors_climbed` field in some FIT exports

## 7. Environment & Constraints 🛠
- **Target OS**: Windows CMD / PowerShell.
- **Constraint**: Terminal output must be strictly ASCII-safe (No 📈 or ✅ emojis in console).
- **Env Variables**: `FIT_FOLDER` (Directory containing `.fit` files), currently `Z:\` (mapped NAS drive)
- **NAS path**: `\\NAS\personal_folder\Files\HealthDataApple\` mapped to `Z:\`
- **Dataset size**: 160 `.fit` files (March 2025 – August 2026)
- **Dependencies**: `fitparse` (in `.venv`)
- **Output**: `processed_workouts_final.json` (JSON array of workout objects)
