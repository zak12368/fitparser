# Apple Watch Fitness Data Parser - Project Context

## 1. Overview
The objective of this project is to process raw fitness tracking data exported from an Apple Watch and convert it into a structured JSON format for analysis or backup purposes.

## 2. Technical Stack
- **Language**: Python 3
- **Core Library**: `fitparse` (to read/parse `.fit` binary files).
- **Configuration**: `python-dotenv` (to locate the input folder via environment variables).

## 3. Input Data
- **Format**: FIT files (`.fit`) exported from Apple Watch via Apps/Fitness+ or similar export methods.
- **Source Directory**: Defined by the environment variable `FIT_FOLDER`.

## 4. Extracted Metrics (`processed_workouts_final.json`)
The script currently extracts the following metrics from the `.fit` session summary data ("Strategy A"):

| Key Name | Data Type | Notes/Conversions |
| :--- | :--- | :--- |
| `filename` | String | The original file name. |
| `total_distance_km` | Float | Converted from meters to kilometers (2 decimals). |
| `avg_heart_rate_bpm` | Float | Average heart rate during the session. |
| `max_heart_rate_bpm` | Float | Peak heart rate found in the session. |
| `avg_pace_min_per_km` | String | Format: `MM:SS`. Calculated as `(Elapsed Time / Distance)`, excluding pauses (Timer Time vs Elapsed Time). |
| `avg_running_cadence` | Int | **Crucial Conversion**: Apple Watch exports cadence in *Stride Cycles/Min*. This script converts it to standard *Steps Per Minute (SPM)* by multiplying raw value by 2. |
| `workout_type` | String | Derived from the session's "workout type" ID code (e.g., '37' -> Outdoor Run). |
| `lap_count` | Int | Total number of laps recorded in the session summary. |

## 5. Current Status & Known Logic
- **Cadence Logic**: The raw data (`avg_running_cadence`) provides half the value because it counts full cycles (Left + Right). We use: `math.floor(cycles * 2)`.
- **Fallback**: If the "Session" summary block is missing from a file, the script attempts to calculate averages manually by looping through all individual "record" data points ("Strategy B").
