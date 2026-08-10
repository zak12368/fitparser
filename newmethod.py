import os
import json
from fitparse import FitFile
from dotenv import load_dotenv


def parse_single_fit_file(file_path):
    """Parses a single .fit file and extracts key metrics."""
    try:
        fit_file = FitFile(file_path)
    except Exception as e:
        print(f"Skipping {os.path.basename(file_path)}: Error reading file ({e})")
        return None

    # Track metrics from session summary or calculate from raw data
    metrics = {
        "filename": os.path.basename(file_path),
        "total_distance_km": None,
        "avg_heart_rate_bpm": None,
        "max_heart_rate_bpm": None,
        "avg_pace_min_per_km": None,
        "avg_running_cadence": None,
        "workout_type": None,
        "lap_count": None
    }

    hr_values = []
    total_distance_meters = 0
    total_time_seconds = 0
    summary_found = False

    # Strategy A: Try parsing the master 'session' summary block first
    for message in fit_file.get_messages('session'):
        summary_found = True
        avg_hr = message.get_value('avg_heart_rate')
        total_dist = message.get_value('total_distance')  # in meters
        total_time = message.get_value('total_elapsed_time')  # in seconds

        # Extract average cadence (Apple Watch stores as strides/cycles, multiply by 2 for SPM)
        avg_cadence_raw = message.get_value('avg_running_cadence')
        if avg_cadence_raw:
            metrics["avg_running_cadence"] = int(avg_cadence_raw * 2)

        # Extract Max Heart Rate
        max_hr_raw = message.get_value('max_heart_rate')
        if max_hr_raw:
            metrics["max_heart_rate_bpm"] = float(max_hr_raw)

        # Extract Workout Type and Lap Count from summary block
        workout_type_val = message.get_value('workout_type') 
        if workout_type_val is not None:
            metrics["workout_type"] = str(workout_type_val)

        lap_count_val = message.get_value('num_laps')
        if lap_count_val is not None:
            metrics["lap_count"] = int(lap_count_val)

        if total_dist:
            metrics["total_distance_km"] = round(total_dist / 1000.0, 2)
        if avg_hr:
            metrics["avg_heart_rate_bpm"] = round(float(avg_hr), 1)
        if total_dist and total_time:
            pace_minutes_raw = (total_time / 60.0) / (total_dist / 1000.0)
            pace_min = int(pace_minutes_raw)
            pace_sec = int((pace_minutes_raw - pace_min) * 60)
            metrics["avg_pace_min_per_km"] = f"{pace_min}:{pace_sec:02d}"
        break

    # Strategy B: Fallback to individual 'record' data points if session block is missing
    if not summary_found:
        for message in fit_file.get_messages('record'):
            hr = message.get_value('heart_rate')
            if hr:
                hr_values.append(hr)

            dist = message.get_value('distance')
            if dist:
                total_distance_meters = dist  # cumulative distance tracker

            timestamp = message.get_value('timestamp')

        if total_distance_meters > 0:
            metrics["total_distance_km"] = round(total_distance_meters / 1000.0, 2)
        if hr_values:
            metrics["avg_heart_rate_bpm"] = round(sum(hr_values) / len(hr_values), 1)

    # Return metrics only if we successfully parsed some basic data
    if metrics["total_distance_km"] or metrics["avg_heart_rate_bpm"] or metrics["avg_running_cadence"]:
        return metrics
    return None


def batch_process_directory(directory_path):
    """Loops through a directory, processes all .fit files, and returns a list of dictionaries."""
    workout_records = []
    print(f"Scanning directory: {directory_path}...")

    for filename in os.listdir(directory_path):
        if filename.lower().endswith('.fit'):
            full_path = os.path.join(directory_path, filename)
            print(f"Processing: {filename}...", end=" ")

            result = parse_single_fit_file(full_path)
            if result:
                workout_records.append(result)
                print("✅ Done")
            else:
                print("❌ Skipped (No valid tracking metrics found)")

    print(f"\nSuccessfully processed {len(workout_records)} files.")
    return workout_records


if __name__ == "__main__":

    load_dotenv()
    FIT_FOLDER = os.getenv("FIT_FOLDER")

    if not os.path.exists(FIT_FOLDER):
        print(f"Error: Folder not found at {FIT_FOLDER}. Please create it and place .fit files inside.")
    else:
        all_workouts_data = batch_process_directory(FIT_FOLDER)

        if all_workouts_data:
            output_file = "processed_workouts_final.json"
            with open(output_file, 'w') as f:
                json.dump(all_workouts_data, f, indent=4)
            print("\n\n================================================")
            print("🎉 FINAL SYSTEM STATUS: All data processed and saved to:", output_file)
            print("================================================")
        else:
            print("\n❌ FAILURE: Failed to process any files. Review the error messages above.")
