-- Demo: API raw data (vor Bearbeitung) vs Warehouse data (nach Bearbeitung)
-- Run with:
-- docker exec -i de_postgres psql -U postgres -d warehouse -f /dev/stdin < docs/presentation_queries.sql

\echo '=== 1) RAW API DATA (VOR BEARBEITUNG) ==='

\echo '1a) Beispiel Rohdatensatz aus raw_products:'
SELECT
    raw_id,
    loaded_at,
    payload
FROM raw_products
ORDER BY raw_id DESC
LIMIT 1;

\echo '1b) Beispiel Rohdatensatz aus raw_users:'
SELECT
    raw_id,
    loaded_at,
    payload
FROM raw_users
ORDER BY raw_id DESC
LIMIT 1;

\echo '1c) Beispiel Rohdatensatz aus raw_orders:'
SELECT
    raw_id,
    loaded_at,
    payload
FROM raw_orders
ORDER BY raw_id DESC
LIMIT 1;

\echo '1d) Rohdaten-Volumen (zeigt: Daten kommen an):'
SELECT
    (SELECT COUNT(*) FROM raw_products) AS raw_products_cnt,
    (SELECT COUNT(*) FROM raw_users)    AS raw_users_cnt,
    (SELECT COUNT(*) FROM raw_orders)   AS raw_orders_cnt,
    (SELECT COUNT(*) FROM raw_events)   AS raw_events_cnt;

\echo '=== 2) TRANSFORMIERTE DATEN (NACH BEARBEITUNG) ==='

\echo '2a) Dimension Produkte (bereinigt/strukturiert):'
SELECT
    product_id,
    title,
    category,
    price,
    currency
FROM dim_products
ORDER BY product_id
LIMIT 10;

\echo '2b) Dimension Nutzer (bereinigt/strukturiert):'
SELECT
    user_id,
    name,
    email,
    city,
    country
FROM dim_users
ORDER BY user_id
LIMIT 10;

\echo '2c) Faktentabelle (analytisch nutzbar):'
SELECT
    event_id,
    order_id,
    user_id,
    product_id,
    quantity,
    price_amount,
    event_type,
    event_ts,
    date_id
FROM fact_orders
ORDER BY event_id DESC
LIMIT 10;

\echo '2d) Event-Typen in Fact (Streaming + Batch):'
SELECT
    event_type,
    COUNT(*) AS cnt
FROM fact_orders
GROUP BY event_type
ORDER BY cnt DESC;

\echo '=== 3) NACHWEIS: RAW -> DWH MAPPING ==='

\echo '3a) Aus raw_products extrahierte Felder vs dim_products:'
WITH rp AS (
    SELECT DISTINCT ON ((payload->>'product_id')::INT)
        (payload->>'product_id')::INT        AS product_id,
        payload->>'name'                     AS raw_name,
        payload->>'category'                 AS raw_category,
        NULLIF(payload->>'price', '')::NUMERIC AS raw_price
    FROM raw_products
    WHERE (payload->>'product_id') IS NOT NULL
    ORDER BY (payload->>'product_id')::INT, loaded_at DESC
)
SELECT
    d.product_id,
    rp.raw_name,
    d.title       AS dim_title,
    rp.raw_category,
    d.category    AS dim_category,
    rp.raw_price,
    d.price       AS dim_price
FROM dim_products d
LEFT JOIN rp ON rp.product_id = d.product_id
ORDER BY d.product_id
LIMIT 20;

\echo '3b) Aus raw_users extrahierte Felder vs dim_users:'
WITH ru AS (
    SELECT DISTINCT ON ((payload->>'user_id')::INT)
        (payload->>'user_id')::INT AS user_id,
        payload->>'username'       AS raw_username,
        payload->>'email'          AS raw_email
    FROM raw_users
    WHERE (payload->>'user_id') IS NOT NULL
    ORDER BY (payload->>'user_id')::INT, loaded_at DESC
)
SELECT
    d.user_id,
    ru.raw_username,
    d.name      AS dim_name,
    ru.raw_email,
    d.email     AS dim_email
FROM dim_users d
LEFT JOIN ru ON ru.user_id = d.user_id
ORDER BY d.user_id
LIMIT 20;

\echo '=== 4) PRÄSENTATIONS-EXTRA: Datenqualität/Fallbacks ==='

\echo '4a) Wie viele Platzhalter-Produkte (Unknown product ...)?'
SELECT COUNT(*) AS unknown_product_titles
FROM dim_products
WHERE title LIKE 'Unknown product %';

\echo '4b) Leere Namen/Titel (sollten 0 sein):'
SELECT
    (SELECT COUNT(*) FROM dim_users WHERE COALESCE(TRIM(name), '') = '')    AS empty_user_names,
    (SELECT COUNT(*) FROM dim_products WHERE COALESCE(TRIM(title), '') = '') AS empty_product_titles;
