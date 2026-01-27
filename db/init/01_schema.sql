\connect warehouse;

-- Star schema placeholders. To be refined with real columns.

-- Dimension tables
CREATE TABLE IF NOT EXISTS dim_users (
    user_id        INT PRIMARY KEY,
    name           TEXT,
    email          TEXT,
    city           TEXT,
    country        TEXT,
    created_at     TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS dim_products (
    product_id     INT PRIMARY KEY,
    title          TEXT,
    category       TEXT,
    price          NUMERIC(12,2),
    currency       TEXT,
    created_at     TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS dim_date (
    date_id        DATE PRIMARY KEY,
    year           INT,
    month          INT,
    day            INT,
    iso_week       INT
);

-- Fact table for orders/events (cleaned)
CREATE TABLE IF NOT EXISTS fact_orders (
    event_id       BIGSERIAL PRIMARY KEY,
    order_id       INT,
    user_id        INT REFERENCES dim_users(user_id),
    product_id     INT REFERENCES dim_products(product_id),
    quantity       INT,
    price_amount   NUMERIC(12,2),
    currency       TEXT,
    event_type     TEXT,
    event_ts       TIMESTAMPTZ,
    date_id        DATE REFERENCES dim_date(date_id)
);

-- Raw event landing (minimal constraints)
CREATE TABLE IF NOT EXISTS raw_events (
    raw_id         BIGSERIAL PRIMARY KEY,
    payload        JSONB,
    ingest_ts      TIMESTAMPTZ DEFAULT NOW()
);

-- Raw batch landing tables
CREATE TABLE IF NOT EXISTS raw_products (
    raw_id     BIGSERIAL PRIMARY KEY,
    payload    JSONB,
    loaded_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS raw_users (
    raw_id     BIGSERIAL PRIMARY KEY,
    payload    JSONB,
    loaded_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS raw_orders (
    raw_id     BIGSERIAL PRIMARY KEY,
    payload    JSONB,
    loaded_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Basic indexes
CREATE INDEX IF NOT EXISTS idx_fact_orders_user ON fact_orders(user_id);
CREATE INDEX IF NOT EXISTS idx_fact_orders_product ON fact_orders(product_id);
CREATE INDEX IF NOT EXISTS idx_fact_orders_date ON fact_orders(date_id);
