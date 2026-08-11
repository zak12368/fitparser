import os
import json
import re
from fitparse import FitFile
from dotenv import load_dotenv


def build_workout_name(sport_type: str = None, sub_sport: str = None, raw_path: str = None):
    """
    Dynamically builds a human-readable workout name (e.g., 'Outdoor Run', 'Elevated Heart Rate Walk') 
    by mapping Fitness+ filenames and explicit binary labels.
    """
    
    # 1. Primary Source: Extract directly from the Fitness+ filename pattern: "YYYY-MM-DD-HHMMSS-TYPE-BY_Zakaria"
    if raw_path:
        basename = os.path.basename(raw_path)
        # Apple Fitness+ filenames contain dashes like "-Indoor Walking-" or "-Outdoor Running-"
        name_match = re.search(r'-([A-Za-z\s]+?)-', basename)
        
        if name_match:
            base_name = name_match.group(1).strip()
    else:
        base_name = sport_type

    # 2. Secondary Source: Check raw binary bytes for explicit text strings (fallback/supplement)
    if not base_name or str(base_name).isdigit():
        if raw_path and os.path.exists(raw_path):
            with open(raw_path, 'rb') as f:
                content = f.read()
            
            # Apple FITs contain readable bytes like b'Run', b'WalkingCycling', b'MixedIntegrityWorkout'
            if b'indoorRun' in content or b'SPORT_RUNNING' in content: base_name = 'INDOORRUNNING'
            elif b'treadmill_walk' in content or b'indoorWalk' in content: base_name = 'INDOORWALKING'
            elif b'Elevated Heart Rate Walk' in content: base_name = 'ELEVATED_HEART_RATE_WALK'
            elif b'Treadmill_Cycling' in content: base_name = 'INDOORCYCLING'

    # 3. Location & Formatting Logic: Handle Apple's unique fitness naming quirks
    is_indoor = False
    
    # Check sub_sport explicitly provided or found (e.g., Apple uses "treadmill" for indoor run/walk)
    if not base_name and sub_sport and 'treadmill' in str(sub_sport).lower():
        is_indoor = True
        
    # Check internal FIT boolean flags via raw search as a safety net for missing filenames
    if not base_name and raw_path and os.path.exists(raw_path):
        with open(raw_path, 'rb') as f:
            content = f.read()
            if b'indoorIndoor: 1' in content or b'OUTDOOR_RUN: 0' in content or b'OUTDOOR_WALKING: 0' in content:
                is_indoor = True

    # Ultimate Fallback: Check the filename itself for indoor clues (e.g., "-indoor rowing-")
    if raw_path and not base_name:
        basename_lower = os.path.basename(raw_path).lower()
        if '-indoor-' in basename_lower or '_indoor_' in basename_lower:
            is_indoor = True

    # Specific Fitness+ logic: Elliptical/Stationary Bike/Rower are always "Indoor" in Apple's ecosystem
    clean_base = str(base_name).lower().replace(' ', '_')
    if not is_indoor and (clean_base == 'fitness_equipment' or clean_base == 'elliptical'):
        is_indoor = True
    
    # 4. Final Name Construction (Prevents double-prefixing like "Outdoor Indoor Run")
    if base_name and ('INDOOR' in str(base_name).upper() or 'OUTDOOR' in str(base_name).upper()):
        clean_name = str(base_name).strip().replace('_', ' ').title()
    elif base_name:
        clean_name = re.sub(r'([A-Z]+)', r'\1', base_name) # Handle acronyms (HIIT, HIIC) 
        location_modifier = "Indoor" if is_indoor else "Outdoor"
        clean_name = f"{location_modifier} {clean_name}"

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
        'total_distance_km': None,
        'avg_heart_rate_bpm': None,
        'max_heart_rate_bpm': None,
        'avg_pace_min_per_km': None,
        'avg_running_cadence': None,
        'workout_type': None,
        'lap_count': None
    }

    hr_values = []
    total_distance_meters = 0
    total_time_seconds = 0
    summary_found = False

    # Strategy A: Try parsing the master 'session' summary block first
    for message in fit_file.get_messages('session'):
        summary_found = True
        
        base_sport_type = None
        sub_sport_val = None

        # 1. Get Sport info from session (e.g., 'running')
        sport_from_msg = message.get_value('sport')
        sub_from_msg = message.get_value('sub_sport')

        # 2. Look up the explicit readable name from the Sport Message type ("Run")
        for msg in fit_file.get_messages('sport'):
            name_field = msg.get_value('name')
            if isinstance(name_field, str) and 'Sport' not in name_field: 
                base_sport_type = name_field 
                break
        
        # 3. Combine them into our new dynamic type!
        metrics['workout_type'] = build_workout_name(
            sport_type=base_sport_type or sport_from_msg,
            sub_sport=sub_from_msg or sub_sport_val,
            raw_path=file_path
        )

        # Extract metrics from the session summary
        total_dist = message.get_value('total_distance')  # in meters
        total_time = message.get_value('total_elapsed_time')  # in seconds

        # Average Heart Rate
        avg_hr = message.get_value('avg_heart_rate')
        if avg_hr:
            metrics['avg_heart_rate_bpm'] = round(float(avg_hr), 1)

        # Max Heart Rate
        max_hr_raw = message.get_value('max_heart_rate')
        if max_hr_raw:
            metrics['max_heart_rate_bpm'] = float(max_hr_raw)

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
        
        break

    # Strategy B: Fallback to individual 'record' data points if session block is incomplete
    if not summary_found or metrics['total_distance_km'] is None:
        for message in fit_file.get_messages('record'):
            hr = message.get_value('heart_rate')
            if hr:
                hr_values.append(hr)

            dist = message.get_value('distance') # cumulative distance tracker
            if dist:
                total_distance_meters = dist  

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
