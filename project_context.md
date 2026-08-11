# 🍎 Apple Watch Fitness+ Fit-Parser Context (Source of Truth)

## 1. Current Status ✅
The parser (`newmethod.py`) is **fully production-ready** and has successfully processed **160 workouts** with 100% mapping accuracy (Zero "Unknown Activity" remain). 

## 2. Core Strategy: Dynamic Workout Typing 🏃‍♂️
Instead of using brittle numeric Apple ID enums, we use a robust 3-step fallback chain to name workouts dynamically based on Fitness+ exports:
1. **Filename Extraction**: Parses `YYYY-MM-DD-TIME-{WORKOUT_NAME}-Zakaria's Apple Watch.fit` directly.
2. **Raw Binary Inspection**: Scans `.fit` files for literal strings (`b'Run', b'Walking'`) and boolean flags (`indoorIndoor: 1`).
3. **Logic Overrides**: Forces Fitness Equipment (Elliptical, Rowers) to always be "Indoor" regardless of GPS status.

## 3. Current Dataset Metrics 📊
Our `processed_workouts_final.json` currently extracts:
- **Type**: Human readable string (e.g., "Outdoor HIIT", "Indoor Walking").
- **Distance**: Total km traveled.
- **Heart Rate**: Avg and Max BPM.
- **Pace**: Min:k per kilometer.
- **Cadence**: Strides/cycles per minute (multiplied by 2 from raw FIT data).

## 4. Next Target: Metric Expansion 🧭
To create more metrics next time, we will focus on standard attributes frequently stored in Apple Watch FIT session/laps blocks that aren't parsed yet:
- **Energy**: `total_calories` and `active_calories` (Often missing from session summary, might need individual `record` parsing).
- **Vertical Gain**: `ascent`, `descent`, or `floors_climbed`.
- **Swim Metrics** (if applicable): Strokes and avg pace.
- **Intensity / HR Zones**: Calculating percentage of max heart rate for each session to categorize training zones (Zone 1 through Zone 5).

## 5. Environment & Constraints 🛠
- **Target OS**: Windows CMD / PowerShell.
- **Constraint**: Terminal output must be strictly ASCII-safe (No 📈 or ✅ emojis).
- **Env Variables**: `FIT_FOLDER` (Directory containing `.fit` files).
