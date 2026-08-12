import os
import json
import re
from fitparse import FitFile
from dotenv import load_dotenv
from dataclasses import dataclass

@dataclass
class LapInfo:
    time: float = None
    pace: str = None
    heart_rate: int = None
    power: int = None
    cadence: int = None

def calculate_hr_zone(hr, max_hr):
    """Calculates the heart rate zone (1-5) based on percentage of Max HR."""
    if not hr or not max_hr: 
        return None
    try:
        pct = (hr / max_hr) * 100
        if pct < 60: return 1
        elif pct < 70: return 2
        elif pct < 80: return 3
        elif pct < 90: return 4
        else: return 5
    except ZeroDivisionError:
        return None


def build_workout_name(sport_type: str = None, sub_sport: str = None, raw_path: str = None):
    """
    Dynamically builds a human-readable workout name (e.g., 'Outdoor Run', 'Elevated Heart Rate Walk') 
    by mapping Fitness+ filenames and explicit binary labels.
    """
    if 'running' in sport_type and 'generic' in sub_sport:
        clean_name = 'Outdoor Run'
    else:
        clean_name = 'Unknown'
    return clean_name


def parse_single_fit_file(file_path):
    """Parses a single .fit file and extracts key metrics."""
    try:
        fit_file = FitFile(file_path)
    except Exception as e:
        print(f"[SKIP] {os.path.basename(file_path)}: Error reading file ({e})")
        return None

    # Track metrics from session summary or calculate from raw data
    metrics = {
        'filename': os.path.basename(file_path),
        
        # Existing Metrics
        'total_distance_km': None,
        'total_calories': None,
        'total_timer_time': None,
        'total_elapsed_time': None,
        'min_heart_rate_bpm': None,
        'avg_heart_rate_bpm': None,
        'max_heart_rate_bpm': None,
        'avg_temperature': None,
        'start_time': None,
        'timestamp': None,
        'sport': None,
        'sub_sport': None,
        'avg_running_cadence': None,
        'avg_power': None,
        'total_ascent': None,
        'lap_count' : None,
        'SESSION INDOOR' : None,
        'SESSION WEATHER HUMIDITY': None,

        # NEW Target Metrics (Expansion Phase)

        'avg_pace_min_per_km': None,
        'workout_type': None,
        'active_calories_kcal': None,
        'elevation_gain_meters': 0.0,
        'peak_hr_zone': None,
        'laps_info': None,
    }
    hr_values = []
    total_distance_meters = 0
    lap_count_val = 0
    laps_info = []
    
    # Accumulators for fallback parsing (Strategy B)
    session_calories_sum = 0
    active_calories_sum = 0
    ascent_sum = 0.0
    descent_sum = 0.0

    summary_found = False

    # Strategy A: Try parsing the master 'session' summary block first
    for message in fit_file.get_messages('session'):
        summary_found = True
        
        base_sport_type = None
        sub_sport_val = None

        # 1. Get Sport info from session (e.g., 'fitness_equipment, elliptical')
        sport_from_msg = message.get_value('sport')
        sub_from_msg = message.get_value('sub_sport')

        # 3. Combine them into our new dynamic type!
        metrics['workout_type'] = build_workout_name(
            sport_type=sport_from_msg,
            sub_sport=sub_from_msg,
            raw_path=file_path
        )

        # Extract metrics from the session summary
        total_dist = message.get_value('total_distance')  # in meters
        total_time = message.get_value('total_timer_time')  # in seconds

        # Average Heart Rate
        avg_hr = message.get_value('avg_heart_rate')
        if avg_hr:
            metrics['avg_heart_rate_bpm'] = avg_hr

        # Max Heart Rate & Zone
        max_hr_raw = message.get_value('max_heart_rate')
        min_hr_raw = message.get_value('min_heart_rate')
        if max_hr_raw:
            metrics['max_heart_rate_bpm'] = max_hr_raw
            # Calculate Peak Zone for the session duration
            metrics['peak_hr_zone'] = calculate_hr_zone(metrics['max_heart_rate_bpm'], metrics['max_heart_rate_bpm'])
        if min_hr_raw:
            metrics['min_heart_rate_bpm'] = min_hr_raw

        # NEW: Extract Calories (Usually present in Session Summary block)
        calories = message.get_value('total_calories')
        if calories is not None:
            metrics['total_calories_kcal'] = int(calories)
            
        active_cals = message.get_value('active_calories')
        if active_cals is not None:
            metrics['active_calories_kcal'] = int(active_cals)

        # NEW: Extract Elevation from Session Summary
        ascent_raw = message.get_value('total_ascent')
        if ascent_raw: 
            metrics['elevation_gain_meters'] = float(ascent_raw)

        # Pace calculation (only Apple Watch Running exports usually contain elapsed time & distance in session)
        if total_dist and total_time and total_dist > 0:
            pace_minutes_raw = (total_time / 60.0) / (total_dist / 1000.0)
            pace_min = int(pace_minutes_raw)
            pace_sec = int((pace_minutes_raw - pace_min) * 60)
            metrics['avg_pace_min_per_km'] = f'{pace_min}:{pace_sec:02d}'
        
        # Cadence & Distance fallbacks
        if total_dist and total_dist > 0:
            metrics['total_distance_km'] = round(total_dist / 1000.0, 2)
            
        avg_cadence_raw = message.get_value('avg_running_cadence')
        if avg_cadence_raw:
            metrics['avg_running_cadence'] = int(avg_cadence_raw * 2) # Apple stores as strides/cycles

        lap_count_val = message.get_value('num_laps')
        if lap_count_val is not None:
            metrics['lap_count'] = int(lap_count_val)
        
        break # Break after session processing as it handles most summaries

    # Strategy B: Fallback to LAPS/RECORDS if Session was missing data (Addressing Context Point 4 - Expansion Target)
    if metrics['active_calories_kcal'] is None:
        
        # 1. Loop through Laps (Crucial for Energy and Elevation if Summary missed them)
        total_laps = 0
        for message in fit_file.get_messages('lap'):
            total_laps += 1
            lap_info = {
                # Existing Metrics
                'time': None,
                'pace': None,
                'heart_rate': None,
                'power': None,
                'cadence': None,
            }

            # Extract metrics from the session summary
            total_dist = message.get_value('total_distance')  # in meters
            total_time = message.get_value('total_timer_time')  # in seconds

            avg_lap_raw_cadence = message.get_value('avg_running_cadence')
            if avg_lap_raw_cadence:
                lap_info['cadence'] = int(avg_lap_raw_cadence * 2)

            if total_dist and total_time and total_dist > 0:
                pace_minutes_raw = (total_time / 60.0) / (total_dist / 1000.0)
                pace_min = int(pace_minutes_raw)
                pace_sec = int((pace_minutes_raw - pace_min) * 60)
                lap_info['pace'] = f'{pace_min}:{pace_sec:02d}'

            laps_info.append(lap_info)
        metrics['laps_info'] = laps_info

    # Record fallbacks for raw data points
    for message in fit_file.get_messages('record'):
        hr = message.get_value('heart_rate')
        if hr:
            hr_values.append(hr)

        dist = message.get_value('distance') # cumulative distance tracker
        if dist:
            total_distance_meters = max(total_distance_meters, dist)  

    # Apply fallback metrics if session parsing was empty
    if metrics['total_distance_km'] is None and total_distance_meters > 0:
        metrics['total_distance_km'] = round(total_distance_meters / 1000.0, 2)
        
    if metrics['avg_heart_rate_bpm'] is None and hr_values:
        metrics['avg_heart_rate_bpm'] = round(sum(hr_values) / len(hr_values), 1)

    # Return metrics only if we successfully parsed some basic data
    if metrics['total_distance_km'] or metrics['avg_heart_rate_bpm'] or metrics['workout_type']:
        return metrics
    return None


def batch_process_directory(directory_path):
    """Loops through a directory, processes all .fit files, and returns a list of dictionaries."""
    workout_records = []
    print(f'Scanning directory: {directory_path}...')

    for filename in os.listdir(directory_path):
        if filename.lower().endswith('.fit'):
            full_path = os.path.join(directory_path, filename)
            print(f'Processing: {os.path.basename(filename)}...', end=' ')

            result = parse_single_fit_file(full_path)
            if result:
                workout_records.append(result)
                print('[SUCCESS]')
            else:
                print('[SKIPPED] No valid data')

    print(f'\nSuccessfully processed {len(workout_records)} files.')
    return workout_records


if __name__ == '__main__':

    load_dotenv()
    FIT_FOLDER = os.getenv('FIT_FOLDER')

    if not os.path.exists(FIT_FOLDER):
        print(f'Error: Folder not found at {FIT_FOLDER}. Please create it and place .fit files inside.')
    else:
        all_workouts_data = batch_process_directory(FIT_FOLDER)

        if all_workouts_data:
            output_file = 'processed_workouts_final.json'
            with open(output_file, 'w') as f:
                json.dump(all_workouts_data, f, indent=4)
            print('\n\n================================================')
            print('FINAL SYSTEM STATUS: All data processed and saved to:', output_file)
            print('================================================')
        else:
            print('\nFAILURE: Failed to process any files. Review the error messages above.')