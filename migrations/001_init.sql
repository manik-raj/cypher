-- Cypher initial schema (phase 1 tables + phase 2 tracking tables).

CREATE TABLE admin_user (
    id            SERIAL PRIMARY KEY,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE app_setting (
    key        TEXT PRIMARY KEY,
    value      TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE alert (
    id                     SERIAL PRIMARY KEY,
    name                   TEXT NOT NULL,
    alert_type             TEXT NOT NULL CHECK (alert_type IN ('conditional', 'scheduled')),
    status                 TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'paused')),
    trading_pair           TEXT NOT NULL,
    exchange_primary       TEXT NOT NULL,
    exchange_secondary     TEXT,
    -- conditional alerts: how often to evaluate the condition(s)
    check_interval_minutes INTEGER,
    -- scheduled alerts: daily at a time, or every N hours (IST-aligned)
    schedule_kind          TEXT CHECK (schedule_kind IN ('daily', 'interval')),
    daily_time_ist         TIME,
    interval_hours         INTEGER,
    condition_logic        TEXT NOT NULL DEFAULT 'AND' CHECK (condition_logic IN ('AND', 'OR')),
    last_checked_at        TIMESTAMPTZ,
    last_triggered_at      TIMESTAMPTZ,
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE alert_condition (
    id             SERIAL PRIMARY KEY,
    alert_id       INTEGER NOT NULL REFERENCES alert(id) ON DELETE CASCADE,
    -- left side is a single exchange's funding fee, or the (primary - secondary) difference
    left_metric    TEXT NOT NULL CHECK (left_metric IN ('funding_fee', 'difference')),
    left_exchange  TEXT,
    operator       TEXT NOT NULL CHECK (operator IN ('>', '>=', '<', '<=', '==')),
    -- right side is a constant value, or another exchange's funding fee
    right_type     TEXT NOT NULL CHECK (right_type IN ('constant', 'exchange')),
    right_value    NUMERIC,
    right_exchange TEXT,
    position       INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX idx_alert_condition_alert ON alert_condition(alert_id);

CREATE TABLE alert_history (
    id              SERIAL PRIMARY KEY,
    alert_id        INTEGER NOT NULL REFERENCES alert(id) ON DELETE CASCADE,
    triggered_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    message_text    TEXT,
    snapshot        JSONB,
    delivery_status TEXT NOT NULL CHECK (delivery_status IN ('sent', 'failed')),
    error           TEXT
);
CREATE INDEX idx_alert_history_alert ON alert_history(alert_id, triggered_at DESC);

-- Phase 2 tables (created now so phase 2 needs no schema rework).
CREATE TABLE tracker (
    id                SERIAL PRIMARY KEY,
    trading_pair      TEXT NOT NULL,
    frequency_minutes INTEGER NOT NULL,
    status            TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'paused')),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE funding_snapshot (
    id                   SERIAL PRIMARY KEY,
    tracker_id           INTEGER REFERENCES tracker(id) ON DELETE CASCADE,
    trading_pair         TEXT NOT NULL,
    exchange             TEXT NOT NULL,
    funding_rate         NUMERIC,
    next_collection_time BIGINT,
    captured_at_ist      TIMESTAMPTZ NOT NULL DEFAULT now(),
    raw                  JSONB
);
CREATE INDEX idx_funding_snapshot_pair ON funding_snapshot(trading_pair, captured_at_ist DESC);
