-- health metrics Postgres schema (daily activity, weight, sleep)

CREATE TABLE IF NOT EXISTS daily_activity (
    id                          SERIAL PRIMARY KEY,
    date                        DATE UNIQUE NOT NULL,
    step_count                  INTEGER,
    active_energy_kcal          DOUBLE PRECISION,
    resting_energy_burned_kcal  DOUBLE PRECISION,
    walking_heart_rate_avg_bpm  INTEGER,
    respiratory_rate            DOUBLE PRECISION,
    hrv_ms                      DOUBLE PRECISION,
    blood_oxygen_pct            DOUBLE PRECISION,
    source                      TEXT,
    created_at                  TIMESTAMPTZ DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_daily_activity_date ON daily_activity (date DESC);

CREATE TABLE IF NOT EXISTS daily_weight (
    id                      SERIAL PRIMARY KEY,
    date                    DATE UNIQUE NOT NULL,
    weight_kg               DOUBLE PRECISION,
    bmi                     DOUBLE PRECISION,
    lean_body_mass_kg       DOUBLE PRECISION,
    body_fat_pct            DOUBLE PRECISION,
    source                  TEXT,
    created_at              TIMESTAMPTZ DEFAULT NOW(),
    updated_at              TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_daily_weight_date ON daily_weight (date DESC);

CREATE TABLE IF NOT EXISTS daily_sleep (
    id            SERIAL PRIMARY KEY,
    date          DATE UNIQUE NOT NULL,
    total_sleep_hr DOUBLE PRECISION,
    deep_hr       DOUBLE PRECISION,
    rem_hr        DOUBLE PRECISION,
    core_hr       DOUBLE PRECISION,
    awake_hr      DOUBLE PRECISION,
    in_bed_hr     DOUBLE PRECISION,
    asleep_hr     DOUBLE PRECISION,
    sleep_start   TIMESTAMPTZ,
    sleep_end     TIMESTAMPTZ,
    in_bed_start  TIMESTAMPTZ,
    in_bed_end    TIMESTAMPTZ,
    source        TEXT,
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    updated_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_daily_sleep_date ON daily_sleep (date DESC);
