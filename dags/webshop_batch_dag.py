"""
Airflow DAG for daily Fake Store API ingestion.
- Fetch products, users, orders
- Store raw JSON into staging tables
- Simple transform/merge into warehouse (dims + fact)
"""

import json
import os
from datetime import datetime

import psycopg2
import requests
from airflow import DAG
from airflow.operators.python import PythonOperator

API_BASE_URL = os.getenv("API_BASE_URL", "https://fake-store-api.mock.beeceptor.com/api")
WAREHOUSE_DSN = os.getenv(
    "WAREHOUSE_DSN",
    "postgresql://postgres:postgres@postgres:5432/warehouse",
)


def fetch_and_store(endpoint: str, table: str) -> None:
    """Fetch JSON from API and append to raw table."""
    url = f"{API_BASE_URL}/{endpoint}"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    records = data if isinstance(data, list) else [data]

    conn = psycopg2.connect(WAREHOUSE_DSN)
    cur = conn.cursor()
    for rec in records:
        cur.execute(f"INSERT INTO {table} (payload) VALUES (%s)", [json.dumps(rec)])
    conn.commit()
    cur.close()
    conn.close()


def transform_and_merge() -> None:
    """Simple merge from raw tables into dims and fact."""
    conn = psycopg2.connect(WAREHOUSE_DSN)
    cur = conn.cursor()

    # Upsert products
    cur.execute(
        """
        INSERT INTO dim_products (product_id, title, category, price, currency)
        SELECT DISTINCT
            (payload->>'product_id')::INT,
            payload->>'name',
            payload->>'category',
            NULLIF(payload->>'price', '')::NUMERIC,
            'USD'
        FROM raw_products
        WHERE (payload->>'product_id') IS NOT NULL
        ON CONFLICT (product_id) DO UPDATE SET
            title = EXCLUDED.title,
            category = EXCLUDED.category,
            price = EXCLUDED.price,
            currency = EXCLUDED.currency;
        """
    )

    # Upsert users
    cur.execute(
        """
        INSERT INTO dim_users (user_id, name, email, city, country)
        SELECT DISTINCT
            (payload->>'user_id')::INT,
            payload->>'username',
            payload->>'email',
            payload->>'city',
            payload->>'country'
        FROM raw_users
        WHERE (payload->>'user_id') IS NOT NULL
        ON CONFLICT (user_id) DO UPDATE SET
            name = EXCLUDED.name,
            email = EXCLUDED.email,
            city = EXCLUDED.city,
            country = EXCLUDED.country;
        """
    )

    # Load orders into fact (one row per order line)
    cur.execute(
        """
        WITH expanded AS (
            SELECT
                (payload->>'order_id')::INT AS order_id,
                (payload->>'user_id')::INT AS user_id,
                COALESCE((payload->>'timestamp')::timestamptz, NOW()) AS event_ts,
                jsonb_array_elements(
                    COALESCE(payload->'items', payload->'products', '[]'::jsonb)
                ) AS item
            FROM raw_orders
            WHERE (payload->>'order_id') IS NOT NULL
        )
        INSERT INTO fact_orders (
            order_id, user_id, product_id, quantity, price_amount, currency, event_type, event_ts, date_id
        )
        SELECT
            order_id,
            user_id,
            COALESCE((item->>'product_id')::INT, (item->>'productId')::INT),
            COALESCE((item->>'quantity')::INT, 1),
            NULLIF(item->>'price', '')::NUMERIC,
            'USD',
            'batch_order',
            event_ts,
            event_ts::DATE
        FROM expanded
        ON CONFLICT DO NOTHING;
        """
    )

    # Populate dim_date from fact_orders
    cur.execute(
        """
        INSERT INTO dim_date (date_id, year, month, day, iso_week)
        SELECT DISTINCT
            date_id,
            EXTRACT(YEAR FROM date_id)::INT,
            EXTRACT(MONTH FROM date_id)::INT,
            EXTRACT(DAY FROM date_id)::INT,
            EXTRACT(WEEK FROM date_id)::INT
        FROM fact_orders
        ON CONFLICT (date_id) DO NOTHING;
        """
    )

    conn.commit()
    cur.close()
    conn.close()


default_args = {"owner": "data-eng", "retries": 1}

with DAG(
    dag_id="webshop_batch_dag",
    start_date=datetime(2024, 1, 1),
    schedule_interval="0 2 * * *",
    catchup=False,
    max_active_runs=1,
    tags=["batch", "webshop"],
    default_args=default_args,
) as dag:
    fetch_products = PythonOperator(
        task_id="fetch_products",
        python_callable=fetch_and_store,
        op_kwargs={"endpoint": "products", "table": "raw_products"},
    )

    fetch_users = PythonOperator(
        task_id="fetch_users",
        python_callable=fetch_and_store,
        op_kwargs={"endpoint": "users", "table": "raw_users"},
    )

    fetch_orders = PythonOperator(
        task_id="fetch_orders",
        python_callable=fetch_and_store,
        op_kwargs={"endpoint": "orders", "table": "raw_orders"},
    )

    clean_transform = PythonOperator(
        task_id="clean_transform",
        python_callable=transform_and_merge,
    )

    [fetch_products, fetch_users, fetch_orders] >> clean_transform
