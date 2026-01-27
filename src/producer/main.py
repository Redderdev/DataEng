"""
Kafka producer for simulated webshop events (click, search, purchase).
Uses Fake Store API to cache products/users and emits events to Kafka.
"""

import json
import os
import random
import time
import uuid
from datetime import datetime, timezone

import requests
from kafka import KafkaProducer


API_BASE_URL = os.getenv("API_BASE_URL", "https://fake-store-api.mock.beeceptor.com/api")
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "order_events")
EVENT_RATE_MS = int(os.getenv("EVENT_RATE_MS", "300"))


def utc_now_iso() -> str:
    return datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()


def load_cache():
    products = requests.get(f"{API_BASE_URL}/products", timeout=30).json()
    users = requests.get(f"{API_BASE_URL}/users", timeout=30).json()
    return products, users


def build_event(products, users):
    event_type = random.choice(["click", "search", "purchase"])
    user = random.choice(users) if users else {"user_id": None}
    product = random.choice(products) if products else {"product_id": None, "price": None}

    base = {
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "event_ts": utc_now_iso(),
        "user_id": user.get("user_id"),
    }

    if event_type == "click":
        base.update({
            "product_id": product.get("product_id"),
            "price_amount": product.get("price"),
            "currency": "USD",
            "action": "product_click",
        })
    elif event_type == "search":
        query = random.choice([
            product.get("category"),
            (product.get("name") or "").split(" ")[0],
            "sale",
            "new",
        ])
        base.update({
            "query": query,
            "result_count": random.randint(1, 20),
        })
    else:  # purchase
        quantity = random.randint(1, 3)
        price = product.get("price") or 0
        base.update({
            "order_id": random.randint(1000, 9999),
            "product_id": product.get("product_id"),
            "quantity": quantity,
            "price_amount": price,
            "currency": "USD",
            "total_amount": price * quantity,
        })
    return base


def main():
    products, users = load_cache()
    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )

    delay = EVENT_RATE_MS / 1000.0
    while True:
        evt = build_event(products, users)
        producer.send(KAFKA_TOPIC, value=evt)
        producer.flush()
        print(f"sent event_type={evt['event_type']} user={evt.get('user_id')} product={evt.get('product_id')}")
        time.sleep(delay)


if __name__ == "__main__":
    main()
