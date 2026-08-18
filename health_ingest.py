#!/usr/bin/env python3
"""Scan health JSON files and upsert daily metrics into PostgreSQL.

Expects files matching Daily_Overall_Metrics_*.json and Daily_Weight_Metrics_*.json
in the /input volume. Parses each file and upserts into daily_activity, daily_weight,
and daily_sleep tables (date as unique key).
"""

import glob
import json
import os
import sys
import psycopg2
from datetime import datetime
from psycopg2.extras import execute_values

HEALTH_SCHEMA_PATH = os.getenv("HEALTH_SCHEMA_PATH", "/health_schema.sql")
INPUT_DIR = os.getenv("HEALTH_INPUT_DIR", "/input")

PG_HOST = os.getenv("PG_HOST", "postgres")
PG_PORT = os.getenv("PG_PORT", "5432")
PG_DATABASE = os.getenv("PG_DATABASE", "fit2json")
PG_USER = os.getenv("PG_USER", "fit2json")
PG_PASSWORD = os.getenv("PG_PASSWORD", "")

# Metric name → (table, column) mapping
ACTIVITY_METRICS = {
    "step_count": "step_count",
    "active_energy": "active_energy_kcal",
    "basal_energy_burned": "resting_energy_burned_kcal",
    "walking_heart_rate_average": "walking_heart_rate_avg_bpm",
    "respiratory_rate": "respiratory_rate",
    "heart_rate_variability": "hrv_ms",
    "blood_oxygen_saturation": "blood_oxygen_pct",
}

WEIGHT_METRICS = {
    "weight_body_mass": "weight_kg",
    "body_mass_index": "bmi",
    "lean_body_mass": "lean_body_mass_kg",
    "body_fat_percentage": "body_fat_pct",
}


def parse_timestamp(ts_str):
    """Parse timestamp strings like '2026-08-16 00:00:00 -0400'."""
    if not ts_str:
        return None
    try:
        return datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S %z")
    except ValueError:
        try:
            return datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            print(f"  WARNING: could not parse timestamp '{ts_str}', storing as NULL")
            return None


def extract_date_from_file(filepath):
    """Try to extract date from filename like Daily_Overall_Metrics_2026-08-17.json."""
    basename = os.path.basename(filepath)
    parts = basename.replace(".json", "").split("_")
    for part in parts:
        try:
            return datetime.strptime(part, "%Y-%m-%d").date()
        except ValueError:
            continue
    return None


def ensure_schema(conn):
    """Create tables and indexes if they don't exist."""
    with open(HEALTH_SCHEMA_PATH) as f:
        sql = f.read()
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()
    print(f"Schema ensured from {HEALTH_SCHEMA_PATH}")


def upsert_activity(conn, records):
    """Upsert daily_activity records keyed by date."""
    if not records:
        return 0
    sql = """
        INSERT INTO daily_activity (
            date, step_count, active_energy_kcal, resting_energy_burned_kcal,
            walking_heart_rate_avg_bpm, respiratory_rate, hrv_ms,
            blood_oxygen_pct, source
        ) VALUES %s
        ON CONFLICT (date) DO UPDATE SET
            step_count                  = EXCLUDED.step_count,
            active_energy_kcal          = EXCLUDED.active_energy_kcal,
            resting_energy_burned_kcal  = EXCLUDED.resting_energy_burned_kcal,
            walking_heart_rate_avg_bpm  = EXCLUDED.walking_heart_rate_avg_bpm,
            respiratory_rate            = EXCLUDED.respiratory_rate,
            hrv_ms                      = EXCLUDED.hrv_ms,
            blood_oxygen_pct            = EXCLUDED.blood_oxygen_pct,
            source                      = EXCLUDED.source,
            updated_at                  = NOW()
    """
    rows = []
    for r in records:
        rows.append((
            r["date"],
            r.get("step_count"),
            r.get("active_energy_kcal"),
            r.get("resting_energy_burned_kcal"),
            r.get("walking_heart_rate_avg_bpm"),
            r.get("respiratory_rate"),
            r.get("hrv_ms"),
            r.get("blood_oxygen_pct"),
            r.get("source"),
        ))
    with conn.cursor() as cur:
        execute_values(cur, sql, rows, page_size=50)
    conn.commit()
    return len(rows)


def upsert_weight(conn, records):
    """Upsert daily_weight records keyed by date."""
    if not records:
        return 0
    sql = """
        INSERT INTO daily_weight (
            date, weight_kg, bmi, lean_body_mass_kg, body_fat_pct, source
        ) VALUES %s
        ON CONFLICT (date) DO UPDATE SET
            weight_kg         = EXCLUDED.weight_kg,
            bmi               = EXCLUDED.bmi,
            lean_body_mass_kg = EXCLUDED.lean_body_mass_kg,
            body_fat_pct      = EXCLUDED.body_fat_pct,
            source            = EXCLUDED.source,
            updated_at        = NOW()
    """
    rows = []
    for r in records:
        rows.append((
            r["date"],
            r.get("weight_kg"),
            r.get("bmi"),
            r.get("lean_body_mass_kg"),
            r.get("body_fat_pct"),
            r.get("source"),
        ))
    with conn.cursor() as cur:
        execute_values(cur, sql, rows, page_size=50)
    conn.commit()
    return len(rows)


def upsert_sleep(conn, records):
    """Upsert daily_sleep records keyed by date."""
    if not records:
        return 0
    sql = """
        INSERT INTO daily_sleep (
            date, total_sleep_hr, deep_hr, rem_hr, core_hr, awake_hr,
            in_bed_hr, asleep_hr, sleep_start, sleep_end,
            in_bed_start, in_bed_end, source
        ) VALUES %s
        ON CONFLICT (date) DO UPDATE SET
            total_sleep_hr = EXCLUDED.total_sleep_hr,
            deep_hr        = EXCLUDED.deep_hr,
            rem_hr         = EXCLUDED.rem_hr,
            core_hr        = EXCLUDED.core_hr,
            awake_hr       = EXCLUDED.awake_hr,
            in_bed_hr      = EXCLUDED.in_bed_hr,
            asleep_hr      = EXCLUDED.asleep_hr,
            sleep_start    = EXCLUDED.sleep_start,
            sleep_end      = EXCLUDED.sleep_end,
            in_bed_start   = EXCLUDED.in_bed_start,
            in_bed_end     = EXCLUDED.in_bed_end,
            source         = EXCLUDED.source,
            updated_at     = NOW()
    """
    rows = []
    for r in records:
        rows.append((
            r["date"],
            r.get("total_sleep_hr"),
            r.get("deep_hr"),
            r.get("rem_hr"),
            r.get("core_hr"),
            r.get("awake_hr"),
            r.get("in_bed_hr"),
            r.get("asleep_hr"),
            r.get("sleep_start"),
            r.get("sleep_end"),
            r.get("in_bed_start"),
            r.get("in_bed_end"),
            r.get("source"),
        ))
    with conn.cursor() as cur:
        execute_values(cur, sql, rows, page_size=50)
    conn.commit()
    return len(rows)


def parse_overall_metrics(filepath):
    """Parse Daily_Overall_Metrics_*.json and return activity + sleep records."""
    with open(filepath) as f:
        data = json.load(f)

    file_date = extract_date_from_file(filepath)
    if not file_date:
        print(f"  WARNING: could not extract date from {filepath}, skipping")
        return [], []

    activity = {"date": file_date}
    sleep = {"date": file_date}
    source_parts = []

    metrics = data.get("data", {}).get("metrics", [])
    for metric in metrics:
        name = metric.get("name")
        entries = metric.get("data", [])
        if not entries:
            continue

        entry = entries[0]  # first (usually only) entry
        if entry.get("source"):
            src = entry["source"]
            if src and src not in source_parts:
                source_parts.append(src)

        if name == "sleep_analysis":
            sleep["total_sleep_hr"] = entry.get("totalSleep")
            sleep["deep_hr"] = entry.get("deep")
            sleep["rem_hr"] = entry.get("rem")
            sleep["core_hr"] = entry.get("core")
            sleep["awake_hr"] = entry.get("awake")
            sleep["in_bed_hr"] = entry.get("inBed")
            sleep["asleep_hr"] = entry.get("asleep")
            sleep["sleep_start"] = parse_timestamp(entry.get("sleepStart"))
            sleep["sleep_end"] = parse_timestamp(entry.get("sleepEnd"))
            sleep["in_bed_start"] = parse_timestamp(entry.get("inBedStart"))
            sleep["in_bed_end"] = parse_timestamp(entry.get("inBedEnd"))
        elif name in ACTIVITY_METRICS:
            col = ACTIVITY_METRICS[name]
            qty = entry.get("qty")
            # Convert to int for integer columns
            if col in ("step_count", "walking_heart_rate_avg_bpm"):
                activity[col] = int(qty) if qty else None
            else:
                activity[col] = qty

    activity["source"] = "|".join(source_parts) if source_parts else None
    sleep["source"] = "|".join(source_parts) if source_parts else None
    return [activity], [sleep]


def parse_weight_metrics(filepath):
    """Parse Daily_Weight_Metrics_*.json and return weight records."""
    with open(filepath) as f:
        data = json.load(f)

    file_date = extract_date_from_file(filepath)
    if not file_date:
        print(f"  WARNING: could not extract date from {filepath}, skipping")
        return []

    weight = {"date": file_date}
    source_parts = []

    metrics = data.get("data", {}).get("metrics", [])
    for metric in metrics:
        name = metric.get("name")
        entries = metric.get("data", [])
        if not entries:
            continue

        entry = entries[0]
        if entry.get("source"):
            src = entry["source"]
            if src and src not in source_parts:
                source_parts.append(src)

        if name in WEIGHT_METRICS:
            col = WEIGHT_METRICS[name]
            weight[col] = entry.get("qty")

    weight["source"] = "|".join(source_parts) if source_parts else None
    return [weight]


def main():
    conn = None
    try:
        # Find all health JSON files
        patterns = [
            os.path.join(INPUT_DIR, "Daily_Overral_Metrics_*.json"),
            os.path.join(INPUT_DIR, "Daily_Weight_Metrics_*.json"),
        ]
        files = []
        for pat in patterns:
            files.extend(glob.glob(pat))

        if not files:
            print(f"WARNING: No health JSON files found in {INPUT_DIR}")
            sys.exit(0)

        print(f"Found {len(files)} health file(s) in {INPUT_DIR}")

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

        # Parse all files
        all_activity = []
        all_weight = []
        all_sleep = []

        for filepath in sorted(files):
            basename = os.path.basename(filepath)
            print(f"\nProcessing: {basename}")

            if "Overral" in basename:
                activity, sleep = parse_overall_metrics(filepath)
                all_activity.extend(activity)
                all_sleep.extend(sleep)
            elif "Weight" in basename:
                weight = parse_weight_metrics(filepath)
                all_weight.extend(weight)
            else:
                print(f"  Skipping unknown file type: {basename}")

        # Upsert into database
        activity_count = upsert_activity(conn, all_activity)
        weight_count = upsert_weight(conn, all_weight)
        sleep_count = upsert_sleep(conn, all_sleep)

        print(f"\n--- Results ---")
        print(f"Activity records upserted: {activity_count}")
        print(f"Weight records upserted:   {weight_count}")
        print(f"Sleep records upserted:    {sleep_count}")

        # Summary counts
        with conn.cursor() as cur:
            for table in ("daily_activity", "daily_weight", "daily_sleep"):
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                total = cur.fetchone()[0]
                cur.execute(f"SELECT MIN(date), MAX(date) FROM {table}")
                min_date, max_date = cur.fetchone()
                print(f"  {table}: {total} rows ({min_date} to {max_date})")

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
