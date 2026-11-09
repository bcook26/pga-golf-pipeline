-- Warehouse schema. Idempotent: safe to run against an existing database.
CREATE SCHEMA IF NOT EXISTS golf;

CREATE TABLE IF NOT EXISTS golf.players (
    player_id    VARCHAR(20)  PRIMARY KEY,
    display_name VARCHAR(255) NOT NULL,
    is_active    BOOLEAN,
    country      VARCHAR(100),
    player_bio   TEXT,
    primary_tour VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS golf.stats_reference (
    stat_id   VARCHAR(20)  PRIMARY KEY,
    stat_name VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS golf.player_stats (
    player_id        VARCHAR(20) NOT NULL,
    season           INTEGER     NOT NULL,
    stat_id          VARCHAR(20) NOT NULL,
    stat_name        VARCHAR(255),
    stat_value       NUMERIC,
    rank             INTEGER,
    category         TEXT,
    above_or_below   VARCHAR(20),
    field_average    NUMERIC,
    supporting_stat  VARCHAR(255),
    supporting_value VARCHAR(255),
    player_name      VARCHAR(255),
    details          JSONB,  -- every column the source returned for this stat
    PRIMARY KEY (player_id, season, stat_id),
    CONSTRAINT fk_player_stats_player
        FOREIGN KEY (player_id) REFERENCES golf.players (player_id)
);

-- for databases created before `details` existed
ALTER TABLE golf.player_stats ADD COLUMN IF NOT EXISTS details JSONB;

CREATE INDEX IF NOT EXISTS ix_player_stats_season_stat
    ON golf.player_stats (season, stat_id);

-- Audit log: one row per (pipeline run, season) used for backfill/incremental
-- decisions and observability.
CREATE TABLE IF NOT EXISTS golf.etl_runs (
    run_id      BIGSERIAL PRIMARY KEY,
    pipeline    VARCHAR(50) NOT NULL,          -- 'players' | 'stats'
    mode        VARCHAR(20) NOT NULL,          -- 'incremental' | 'backfill'
    season      INTEGER,
    status      VARCHAR(20) NOT NULL,          -- running|success|failed|skipped
    rows_loaded INTEGER,
    detail      TEXT,
    started_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_etl_runs_lookup
    ON golf.etl_runs (pipeline, season, status);

-- Data-quality check results, one row per check per (run, season). A 'fail'
-- aborts the load for that season; 'warn' is recorded and surfaced in the UI.
CREATE TABLE IF NOT EXISTS golf.data_quality_results (
    result_id  BIGSERIAL PRIMARY KEY,
    run_id     BIGINT REFERENCES golf.etl_runs (run_id) ON DELETE CASCADE,
    season     INTEGER,
    check_name VARCHAR(60) NOT NULL,
    status     VARCHAR(10) NOT NULL CHECK (status IN ('pass', 'warn', 'fail')),
    observed   DOUBLE PRECISION,
    threshold  TEXT,
    detail     TEXT,
    checked_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_dq_latest
    ON golf.data_quality_results (season, check_name, checked_at DESC);
