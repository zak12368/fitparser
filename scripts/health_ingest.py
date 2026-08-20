#!/usr/bin/env python3
"""Scan health JSON files and upsert daily metrics into PostgreSQL.

Supports both single-day and bulk (date-range) files:
  Daily_Overall_Metrics_YYYY-MM-DD.json        (single day)
  Daily_Overall_Metrics-YYYY-MM-DD-YYYY-MM-DD.json  (bulk range)
  Daily_Weight_Metrics_*.json / Daily_Weight_Metrics-*.json

Dates are read from each entry's "date" field — filename is not used for dates.
Multiple sleep sessions on the same day are aggregated (durations summed,
start/end timestamps kept earliest/latest).

Upserts into daily_activity, daily_weight, and daily_sleep tables (date as unique key).
"""

import glob
import json
import os
import sys
from collections import defaultdict
from datetime import datetime
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import execute_values

load_dotenv()
HEALTH_SCHEMA_PATH = os.getenv("HEALTH_SCHEMA_PATH")
INPUT_DIR = os.getenv("HEALTH_INPUT_PATH")

PG_HOST = os.getenv("PG_HOST")
PG_PORT = os.getenv("PG_PORT")
PG_DATABASE = os.getenv("PG_DATABASE")
PG_USER = os.getenv("PG_USER")
PG_PASSWORD = os.getenv("PG_PASSWORD")

# Metric name → column mapping
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

INTEGER_COLUMNS = {"step_count", "walking_heart_rate_avg_bpm"}


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


def _add_source(sources: list, source: str | None):
    """Add a source string to a list if non-empty and not already present."""
    if source and source not in sources:
        sources.append(source)


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
    """Parse a Daily_Overall_Metrics file (single-day or bulk range).

    Iterates every entry in every metric, reads the date from the entry itself,
    and groups by date.  Multiple sleep sessions on the same day are aggregated.

    Returns (activity_records: list[dict], sleep_records: list[dict]).
    """
    with open(filepath) as f:
        data = json.load(f)

    # Accumulate per-date: {date: {col: val, ...}, date: ...}
    activity_accum = defaultdict(lambda: {"source_parts": []})
    sleep_accum = defaultdict(lambda: {"sessions": [], "source_parts": []})

    metrics = data.get("data", {}).get("metrics", [])
    for metric in metrics:
        name = metric.get("name")
        entries = metric.get("data", [])

        for entry in entries:
            ts = parse_timestamp(entry.get("date", ""))
            if ts is None:
                continue
            entry_date = ts.date()
            source = entry.get("source")

            if name == "sleep_analysis":
                session = {
                    "total_sleep_hr": entry.get("totalSleep"),
                    "deep_hr": entry.get("deep"),
                    "rem_hr": entry.get("rem"),
                    "core_hr": entry.get("core"),
                    "awake_hr": entry.get("awake"),
                    "in_bed_hr": entry.get("inBed"),
                    "asleep_hr": entry.get("asleep"),
                    "sleep_start": parse_timestamp(entry.get("sleepStart")),
                    "sleep_end": parse_timestamp(entry.get("sleepEnd")),
                    "in_bed_start": parse_timestamp(entry.get("inBedStart")),
                    "in_bed_end": parse_timestamp(entry.get("inBedEnd")),
                }
                sleep_accum[entry_date]["sessions"].append(session)
                _add_source(sleep_accum[entry_date]["source_parts"], source)

            elif name in ACTIVITY_METRICS:
                col = ACTIVITY_METRICS[name]
                qty = entry.get("qty")
                if col in INTEGER_COLUMNS:
                    qty = int(qty) if qty else None
                activity_accum[entry_date][col] = qty
                _add_source(activity_accum[entry_date]["source_parts"], source)

    # ---- Build final activity records ----
    final_activity = []
    for d, rec in activity_accum.items():
        sources = rec.pop("source_parts", [])
        rec["date"] = d
        rec["source"] = "|".join(sources) if sources else None
        final_activity.append(rec)

    # ---- Aggregate sleep sessions per day ----
    final_sleep = []
    for d, rec in sleep_accum.items():
        sessions = rec["sessions"]
        if not sessions:
            continue
        sources = rec["source_parts"]

        if len(sessions) == 1:
            rec_out = sessions[0].copy()
            rec_out["date"] = d
            rec_out["source"] = "|".join(sources) if sources else None
        else:
            # Multiple sessions: sum durations, earliest start / latest end
            rec_out = {
                "date": d,
                "total_sleep_hr": sum((s.get("total_sleep_hr") or 0) for s in sessions),
                "deep_hr": sum((s.get("deep_hr") or 0) for s in sessions),
                "rem_hr": sum((s.get("rem_hr") or 0) for s in sessions),
                "core_hr": sum((s.get("core_hr") or 0) for s in sessions),
                "awake_hr": sum((s.get("awake_hr") or 0) for s in sessions),
                "in_bed_hr": sum((s.get("in_bed_hr") or 0) for s in sessions),
                "asleep_hr": sum((s.get("asleep_hr") or 0) for s in sessions),
                "sleep_start": min(
                    (s["sleep_start"] for s in sessions if s.get("sleep_start")),
                    default=None,
                ),
                "sleep_end": max(
                    (s["sleep_end"] for s in sessions if s.get("sleep_end")),
                    default=None,
                ),
                "in_bed_start": min(
                    (s["in_bed_start"] for s in sessions if s.get("in_bed_start")),
                    default=None,
                ),
                "in_bed_end": max(
                    (s["in_bed_end"] for s in sessions if s.get("in_bed_end")),
                    default=None,
                ),
                "source": "|".join(sources) if sources else None,
            }
        final_sleep.append(rec_out)

    print(f"    → {len(final_activity)} activity record(s), {len(final_sleep)} sleep record(s)")
    return final_activity, final_sleep


def parse_weight_metrics(filepath):
    """Parse a Daily_Weight_Metrics file (single-day or bulk range).

    Iterates every entry in every metric, reads the date from the entry itself,
    and groups by date.

    Returns weight_records: list[dict].
    """
    with open(filepath) as f:
        data = json.load(f)

    weight_accum = defaultdict(lambda: {"source_parts": []})

    metrics = data.get("data", {}).get("metrics", [])
    for metric in metrics:
        name = metric.get("name")
        entries = metric.get("data", [])

        for entry in entries:
            ts = parse_timestamp(entry.get("date", ""))
            if ts is None:
                continue
            entry_date = ts.date()
            source = entry.get("source")

            if name in WEIGHT_METRICS:
                col = WEIGHT_METRICS[name]
                weight_accum[entry_date][col] = entry.get("qty")
                _add_source(weight_accum[entry_date]["source_parts"], source)

    # Build final weight records
    final_weight = []
    for d, rec in weight_accum.items():
        sources = rec.pop("source_parts", [])
        rec["date"] = d
        rec["source"] = "|".join(sources) if sources else None
        final_weight.append(rec)

    print(f"    → {len(final_weight)} weight record(s)")
    return final_weight


def main():
    conn = None
    try:
        # Glob patterns — match both single-day (_date.json) and bulk (-date-range.json)
        patterns = [
            os.path.join(INPUT_DIR, "Daily_Overall_Metrics*.json"),
            os.path.join(INPUT_DIR, "Daily_Weight_Metrics*.json"),
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

            if "Weight" in basename:
                weight = parse_weight_metrics(filepath)
                all_weight.extend(weight)
            elif "Overall" in basename:
                activity, sleep = parse_overall_metrics(filepath)
                all_activity.extend(activity)
                all_sleep.extend(sleep)
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
