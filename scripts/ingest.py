#!/usr/bin/env python3
"""Read workouts.json and upsert into PostgreSQL."""

import json
import os
import sys
import psycopg2
from datetime import timedelta
from dotenv import load_dotenv
from psycopg2.extras import execute_values

load_dotenv()

FIT_INPUT_PATH = os.getenv("FIT_INPUT_PATH")
SCHEMA_PATH = os.getenv("SCHEMA_PATH")

PG_HOST = os.getenv("PG_HOST")
PG_PORT = os.getenv("PG_PORT")
PG_DATABASE = os.getenv("PG_DATABASE")
PG_USER = os.getenv("PG_USER")
PG_PASSWORD = os.getenv("PG_PASSWORD")


def ensure_schema(conn):
    """Create table and indexes if they don't exist."""
    with open(SCHEMA_PATH) as f:
        sql = f.read()
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()
    print(f"Schema ensured from {SCHEMA_PATH}")


def to_interval(time_str):
    """Convert 'HH:MM:SS' or 'MM:SS' to timedelta (psycopg2 -> INTERVAL adapter).

    Returns None if input is None/empty. timedelta is preferred over raw strings
    because psycopg2 has a built-in adapter: timedelta -> PostgreSQL INTERVAL.
    """
    if not time_str:
        return None
    parts = time_str.split(":")
    try:
        if len(parts) == 2:
            return timedelta(minutes=int(parts[0]), seconds=int(parts[1]))
        elif len(parts) == 3:
            return timedelta(
                hours=int(parts[0]),
                minutes=int(parts[1]),
                seconds=int(parts[2]),
            )
    except (ValueError, IndexError):
        print(f"  WARNING: could not parse time '{time_str}', storing as NULL")
        return None
    return None


def upsert_workouts(conn, workouts):
    """Insert or update workouts using filename as unique key."""
    sql = """
        INSERT INTO workouts (
            filename, workout_type, start_time, total_timer_time,
            total_distance_km, avg_pace_min_per_km,
            avg_heart_rate_bpm, max_heart_rate_bpm, min_heart_rate_bpm,
            active_calories_kcal, elevation_gain_meters, avg_running_cadence,
            temperature_c, humidity_pct, peak_hr_zone, dominant_hr_zone,
            lap_count, hr_zone_distribution, laps_info
        ) VALUES %s
        ON CONFLICT (filename) DO UPDATE SET
            workout_type            = EXCLUDED.workout_type,
            start_time              = EXCLUDED.start_time,
            total_timer_time        = EXCLUDED.total_timer_time,
            total_distance_km       = EXCLUDED.total_distance_km,
            avg_pace_min_per_km     = EXCLUDED.avg_pace_min_per_km,
            avg_heart_rate_bpm      = EXCLUDED.avg_heart_rate_bpm,
            max_heart_rate_bpm      = EXCLUDED.max_heart_rate_bpm,
            min_heart_rate_bpm      = EXCLUDED.min_heart_rate_bpm,
            active_calories_kcal    = EXCLUDED.active_calories_kcal,
            elevation_gain_meters   = EXCLUDED.elevation_gain_meters,
            avg_running_cadence     = EXCLUDED.avg_running_cadence,
            temperature_c           = EXCLUDED.temperature_c,
            humidity_pct            = EXCLUDED.humidity_pct,
            peak_hr_zone            = EXCLUDED.peak_hr_zone,
            dominant_hr_zone        = EXCLUDED.dominant_hr_zone,
            lap_count               = EXCLUDED.lap_count,
            hr_zone_distribution    = EXCLUDED.hr_zone_distribution,
            laps_info               = EXCLUDED.laps_info,
            updated_at              = NOW()
    """

    rows = []
    for w in workouts:
        rows.append((
            w.get("filename"),
            w.get("workout_type"),
            w.get("start_time"),
            to_interval(w.get("total_timer_time")),
            w.get("total_distance_km"),
            to_interval(w.get("avg_pace_min_per_km")),
            w.get("avg_heart_rate_bpm"),
            w.get("max_heart_rate_bpm"),
            w.get("min_heart_rate_bpm"),
            w.get("active_calories_kcal"),
            w.get("elevation_gain_meters"),
            w.get("avg_running_cadence"),
            w.get("temperature_c"),
            w.get("humidity_pct"),
            w.get("peak_hr_zone"),
            w.get("dominant_hr_zone"),
            w.get("lap_count"),
            json.dumps(w.get("hr_zone_distribution")) if w.get("hr_zone_distribution") else None,
            json.dumps(w.get("laps_info")) if w.get("laps_info") else None,
        ))

    with conn.cursor() as cur:
        execute_values(cur, sql, rows, page_size=50)
    conn.commit()
    return len(rows)


def main():
    conn = None
    try:
        # Read JSON
        print(f"Reading workouts from {FIT_INPUT_PATH}...")
        with open(FIT_INPUT_PATH) as f:
            workouts = json.load(f)
        print(f"Found {len(workouts)} workout(s)")

        # Connect to Postgres
        print(f"Connecting to postgres://{PG_USER}@{PG_HOST}:{PG_PORT}/{PG_DATABASE}...")
        conn = psycopg2.connect(
            host=PG_HOST,
            port=PG_PORT,
            database=PG_DATABASE,
            user=PG_USER,
            password=PG_PASSWORD,
            connect_timeout=10,
        )

        # Ensure schema exists
        ensure_schema(conn)

        # Upsert
        count = upsert_workouts(conn, workouts)
        print(f"Upserted {count} workout(s)")

        # Summary
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM workouts")
            total = cur.fetchone()[0]
            cur.execute("SELECT COUNT(DISTINCT workout_type) FROM workouts")
            types = cur.fetchone()[0]
            print(f"Total workouts in DB: {total} ({types} distinct types)")

    except FileNotFoundError as e:
        print(f"ERROR: File not found — {e}", file=sys.stderr)
        sys.exit(1)
    except psycopg2.OperationalError as e:
        print(f"ERROR: Cannot connect to Postgres — {e}", file=sys.stderr)
        sys.exit(1)
    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        print(f"ERROR: Database error — {e}", file=sys.stderr)
        sys.exit(1)
    except (json.JSONDecodeError, KeyError) as e:
        print(f"ERROR: Invalid JSON data — {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    main()
