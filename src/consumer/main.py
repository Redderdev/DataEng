"""
Kafka consumer for webshop events.
- Reads events from Kafka
- Writes raw payloads to raw_events
- Inserts simplified facts into fact_orders (if purchase-like)
"""

import json
import os
from datetime import datetime, timezone

import psycopg2
from kafka import KafkaConsumer


KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "order_events")
POSTGRES_DSN = os.getenv("POSTGRES_DSN", "postgresql://postgres:postgres@postgres:5432/warehouse")


def parse_ts(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return datetime.utcnow().replace(tzinfo=timezone.utc)


def main():
    consumer = KafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
    )

    conn = psycopg2.connect(POSTGRES_DSN)
    cur = conn.cursor()

    for message in consumer:
        evt = message.value

        # Insert raw event
        cur.execute("INSERT INTO raw_events (payload) VALUES (%s)", [json.dumps(evt)])

        # Map fields for fact_orders (only when we have product_id/user_id)
        event_ts = parse_ts(evt.get("event_ts", ""))
        user_id = evt.get("user_id")
        product_id = evt.get("product_id")
        quantity = evt.get("quantity") or 1
        price_amount = evt.get("price_amount")
        currency = evt.get("currency", "USD")
        order_id = evt.get("order_id")
        event_type = evt.get("event_type")

        if product_id and user_id:
            # Ensure dim rows exist (sparse upsert)
            cur.execute(
                "INSERT INTO dim_users (user_id) VALUES (%s) ON CONFLICT DO NOTHING",
                [user_id],
            )
            cur.execute(
                "INSERT INTO dim_products (product_id) VALUES (%s) ON CONFLICT DO NOTHING",
                [product_id],
            )
            cur.execute(
                """
                INSERT INTO dim_date (date_id, year, month, day, iso_week)
                VALUES (%s, EXTRACT(YEAR FROM %s)::INT, EXTRACT(MONTH FROM %s)::INT, EXTRACT(DAY FROM %s)::INT, EXTRACT(WEEK FROM %s)::INT)
                ON CONFLICT DO NOTHING
                """,
                [event_ts.date(), event_ts, event_ts, event_ts, event_ts],
            )
            cur.execute(
                """
                INSERT INTO fact_orders (
                    order_id, user_id, product_id, quantity, price_amount, currency, event_type, event_ts, date_id
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT DO NOTHING
                """,
                [
                    order_id,
                    user_id,
                    product_id,
                    quantity,
                    price_amount,
                    currency,
                    event_type,
                    event_ts,
                    event_ts.date(),
                ],
            )

        conn.commit()
        print(f"consumed event_type={event_type} user={user_id} product={product_id}")


if __name__ == "__main__":
    main()
