-- GRIDFLEX Pakistan — Supabase / PostgreSQL schema
-- Flexibility Accounting Layer (financial/digital), not peer-to-peer power transfer.

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ---------------------------------------------------------------------------
-- Grid topology (illustrative)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS grid_zones (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    city TEXT NOT NULL,
    disco TEXT NOT NULL,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    peak_threshold_mw DOUBLE PRECISION NOT NULL DEFAULT 500,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS substations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    zone_id UUID NOT NULL REFERENCES grid_zones(id),
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    capacity_mw DOUBLE PRECISION NOT NULL
);

CREATE TABLE IF NOT EXISTS feeders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    substation_id UUID NOT NULL REFERENCES substations(id),
    zone_id UUID NOT NULL REFERENCES grid_zones(id),
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    capacity_mw DOUBLE PRECISION NOT NULL,
    current_loading_mw DOUBLE PRECISION NOT NULL DEFAULT 0
);

-- ---------------------------------------------------------------------------
-- Users & auth
-- ---------------------------------------------------------------------------
CREATE TYPE user_role AS ENUM (
    'residential', 'commercial', 'industrial', 'prosumer',
    'distributed_generator', 'aggregator', 'utility', 'regulator', 'admin'
);

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    role user_role NOT NULL,
    zone_id UUID REFERENCES grid_zones(id),
    feeder_id UUID REFERENCES feeders(id),
    organization TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- Participants & assets
-- ---------------------------------------------------------------------------
CREATE TYPE participant_category AS ENUM (
    'residential', 'commercial', 'industrial', 'prosumer', 'solar', 'battery'
);

CREATE TABLE IF NOT EXISTS participants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    external_ref TEXT UNIQUE,
    category participant_category NOT NULL,
    name TEXT NOT NULL,
    zone_id UUID NOT NULL REFERENCES grid_zones(id),
    feeder_id UUID REFERENCES feeders(id),
    baseload_kw DOUBLE PRECISION NOT NULL DEFAULT 0,
    flexible_kw DOUBLE PRECISION NOT NULL DEFAULT 0,
    curtailable_kw DOUBLE PRECISION NOT NULL DEFAULT 0,
    solar_kw DOUBLE PRECISION NOT NULL DEFAULT 0,
    battery_kwh DOUBLE PRECISION NOT NULL DEFAULT 0,
    battery_soc DOUBLE PRECISION NOT NULL DEFAULT 0.5,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS meters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    participant_id UUID NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
    meter_serial TEXT NOT NULL UNIQUE,
    is_simulated BOOLEAN NOT NULL DEFAULT TRUE,
    last_seen_at TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'online'
);

CREATE TABLE IF NOT EXISTS meter_readings (
    id BIGSERIAL PRIMARY KEY,
    meter_id UUID NOT NULL REFERENCES meters(id) ON DELETE CASCADE,
    ts TIMESTAMPTZ NOT NULL,
    voltage_v DOUBLE PRECISION,
    current_a DOUBLE PRECISION,
    power_kw DOUBLE PRECISION NOT NULL,
    energy_kwh DOUBLE PRECISION,
    power_factor DOUBLE PRECISION,
    frequency_hz DOUBLE PRECISION,
    solar_kw DOUBLE PRECISION DEFAULT 0,
    battery_soc DOUBLE PRECISION,
    UNIQUE (meter_id, ts)
);

CREATE INDEX IF NOT EXISTS idx_meter_readings_ts ON meter_readings(ts);

-- ---------------------------------------------------------------------------
-- Flexibility & marketplace
-- ---------------------------------------------------------------------------
CREATE TYPE flexibility_type AS ENUM (
    'demand_reduction', 'demand_shifting', 'storage_discharge',
    'storage_charge', 'generation_export', 'aggregated'
);

CREATE TYPE offer_status AS ENUM (
    'open', 'partially_filled', 'filled', 'cancelled', 'expired', 'rejected'
);

CREATE TABLE IF NOT EXISTS flexibility_offers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    participant_id UUID NOT NULL REFERENCES participants(id),
    seller_user_id UUID REFERENCES users(id),
    zone_id UUID NOT NULL REFERENCES grid_zones(id),
    feeder_id UUID REFERENCES feeders(id),
    flexibility_type flexibility_type NOT NULL,
    power_kw DOUBLE PRECISION NOT NULL,
    duration_hours DOUBLE PRECISION NOT NULL,
    energy_kwh DOUBLE PRECISION NOT NULL,
    available_from TIMESTAMPTZ NOT NULL,
    available_to TIMESTAMPTZ NOT NULL,
    min_price_pkr_per_kwh DOUBLE PRECISION NOT NULL,
    remaining_kw DOUBLE PRECISION NOT NULL,
    status offer_status NOT NULL DEFAULT 'open',
    meter_evidence_ref TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS flexibility_bids (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    buyer_user_id UUID REFERENCES users(id),
    zone_id UUID NOT NULL REFERENCES grid_zones(id),
    feeder_id UUID REFERENCES feeders(id),
    power_kw DOUBLE PRECISION NOT NULL,
    duration_hours DOUBLE PRECISION NOT NULL,
    energy_kwh DOUBLE PRECISION NOT NULL,
    needed_from TIMESTAMPTZ NOT NULL,
    needed_to TIMESTAMPTZ NOT NULL,
    max_price_pkr_per_kwh DOUBLE PRECISION NOT NULL,
    remaining_kw DOUBLE PRECISION NOT NULL,
    status offer_status NOT NULL DEFAULT 'open',
    urgency TEXT NOT NULL DEFAULT 'normal',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TYPE tx_status AS ENUM (
    'pending', 'cleared', 'verified', 'settled', 'disputed', 'rejected'
);

CREATE TABLE IF NOT EXISTS market_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    offer_id UUID REFERENCES flexibility_offers(id),
    bid_id UUID REFERENCES flexibility_bids(id),
    seller_user_id UUID,
    buyer_user_id UUID,
    zone_id UUID NOT NULL REFERENCES grid_zones(id),
    feeder_id UUID REFERENCES feeders(id),
    power_kw DOUBLE PRECISION NOT NULL,
    energy_kwh DOUBLE PRECISION NOT NULL,
    offer_price DOUBLE PRECISION NOT NULL,
    clearing_price DOUBLE PRECISION NOT NULL,
    seller_revenue_pkr DOUBLE PRECISION NOT NULL,
    buyer_cost_pkr DOUBLE PRECISION NOT NULL,
    platform_fee_pkr DOUBLE PRECISION NOT NULL,
    grid_fee_pkr DOUBLE PRECISION NOT NULL,
    status tx_status NOT NULL DEFAULT 'cleared',
    meter_evidence JSONB,
    verification_status TEXT NOT NULL DEFAULT 'pending',
    blockchain_hash TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS wallets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE REFERENCES users(id),
    flexibility_provided_kwh DOUBLE PRECISION NOT NULL DEFAULT 0,
    demand_reduction_kwh DOUBLE PRECISION NOT NULL DEFAULT 0,
    solar_surplus_kwh DOUBLE PRECISION NOT NULL DEFAULT 0,
    earnings_pkr DOUBLE PRECISION NOT NULL DEFAULT 0,
    pending_settlement_pkr DOUBLE PRECISION NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS settlements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_id UUID NOT NULL REFERENCES market_transactions(id),
    user_id UUID NOT NULL REFERENCES users(id),
    amount_pkr DOUBLE PRECISION NOT NULL,
    fee_pkr DOUBLE PRECISION NOT NULL DEFAULT 0,
    direction TEXT NOT NULL CHECK (direction IN ('credit', 'debit')),
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- Pricing, DR, fraud, forecasts, simulation
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dynamic_prices (
    id BIGSERIAL PRIMARY KEY,
    zone_id UUID NOT NULL REFERENCES grid_zones(id),
    ts TIMESTAMPTZ NOT NULL,
    price_pkr_per_kwh DOUBLE PRECISION NOT NULL,
    condition TEXT NOT NULL DEFAULT 'normal',
    peak_demand_mw DOUBLE PRECISION,
    flexibility_mw DOUBLE PRECISION,
    congestion_index DOUBLE PRECISION,
    UNIQUE (zone_id, ts)
);

CREATE TABLE IF NOT EXISTS demand_response_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    zone_id UUID NOT NULL REFERENCES grid_zones(id),
    title TEXT NOT NULL,
    starts_at TIMESTAMPTZ NOT NULL,
    ends_at TIMESTAMPTZ NOT NULL,
    target_reduction_mw DOUBLE PRECISION NOT NULL,
    achieved_reduction_mw DOUBLE PRECISION DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'scheduled',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS fraud_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    participant_id UUID REFERENCES participants(id),
    transaction_id UUID REFERENCES market_transactions(id),
    alert_type TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'medium',
    message TEXT NOT NULL,
    claimed_kwh DOUBLE PRECISION,
    observed_kwh DOUBLE PRECISION,
    status TEXT NOT NULL DEFAULT 'open',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS forecasts (
    id BIGSERIAL PRIMARY KEY,
    zone_id UUID REFERENCES grid_zones(id),
    forecast_type TEXT NOT NULL,
    horizon TEXT NOT NULL,
    ts TIMESTAMPTZ NOT NULL,
    value DOUBLE PRECISION NOT NULL,
    unit TEXT NOT NULL,
    model_name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS simulation_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    config JSONB NOT NULL,
    results JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS hourly_grid_snapshots (
    id BIGSERIAL PRIMARY KEY,
    simulation_run_id UUID REFERENCES simulation_runs(id),
    zone_id UUID REFERENCES grid_zones(id),
    hour INT NOT NULL CHECK (hour >= 0 AND hour <= 23),
    demand_mw DOUBLE PRECISION NOT NULL,
    generation_mw DOUBLE PRECISION NOT NULL,
    solar_mw DOUBLE PRECISION NOT NULL,
    battery_mw DOUBLE PRECISION NOT NULL,
    flexible_demand_mw DOUBLE PRECISION NOT NULL,
    cleared_volume_mw DOUBLE PRECISION NOT NULL DEFAULT 0,
    price_pkr DOUBLE PRECISION,
    grid_condition TEXT NOT NULL DEFAULT 'normal',
    scenario TEXT NOT NULL CHECK (scenario IN ('without_gridflex', 'with_gridflex'))
);

CREATE TABLE IF NOT EXISTS platform_config (
    key TEXT PRIMARY KEY,
    value JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO platform_config (key, value) VALUES
    ('platform_fee_pct', '0.05'),
    ('grid_fee_pct', '0.02'),
    ('normal_price_pkr', '8'),
    ('peak_price_pkr', '15'),
    ('critical_price_pkr', '25')
ON CONFLICT (key) DO NOTHING;