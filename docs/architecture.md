# Architektur und Entscheidungen

## Datenflüsse
- Batch: Fake Store API -> Airflow DAG -> Raw (files/tables) -> Clean -> Postgres warehouse.
- Streaming: Event-Simulator -> Kafka Topic `order_events` -> Consumer -> Postgres (raw_events + fact_orders).

## Gründe für Batch + Streaming
- Batch für stabile Stammdaten (Produkte, Nutzer, Orders).
- Streaming für Near-Real-Time Events (Klick, Suche, Kauf) zur Demonstration aus der Vorlesung.

## Vereinfachungen
- Ein Topic, wenige Partitionen, einfache acks.
- DLQ optional für fehlerhafte Events.
- Keine zusätzlichen Engines (kein Spark/Flink), Fokus auf Klarheit.

## Datenmodell (Skizze)
- Dimensionen: dim_users, dim_products, dim_date.
- Fakten: fact_orders/events mit event_type und Metriken.
- Raw-Layer: raw_events JSONB für Replays/Fehlersuche.

## Deployment
- Docker Compose orchestriert alle Services.
- Airflow LocalExecutor mit Postgres-Metastore.
- Keine manuellen DB-Änderungen, alles in db/init.

## Sicherheit/Secrets
- Fernet Key und Webserver Secret via .env (nicht einchecken).
- Default Passwörter nur für lokale Entwicklung, vor Deploy anpassen.
