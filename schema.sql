-- fit2json Postgres schema

CREATE TABLE IF NOT EXISTS workouts (
    id                   SERIAL PRIMARY KEY,
    filename             TEXT UNIQUE NOT NULL,
    workout_type         TEXT,
    start_time           TIMESTAMPTZ,
    total_timer_time     INTERVAL,
    total_distance_km    DOUBLE PRECISION,
    avg_pace_min_per_km  INTERVAL,
    avg_heart_rate_bpm   INTEGER,
    max_heart_rate_bpm   INTEGER,
    min_heart_rate_bpm   INTEGER,
    active_calories_kcal INTEGER,
    elevation_gain_meters DOUBLE PRECISION,
    avg_running_cadence  INTEGER,
    temperature_c        INTEGER,
    humidity_pct         DOUBLE PRECISION,
    peak_hr_zone         INTEGER,
    dominant_hr_zone     INTEGER,
    lap_count            INTEGER,
    hr_zone_distribution JSONB,
    laps_info            JSONB,
    created_at           TIMESTAMPTZ DEFAULT NOW(),
    updated_at           TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_workouts_start_time ON workouts (start_time);
CREATE INDEX IF NOT EXISTS idx_workouts_workout_type ON workouts (workout_type);
