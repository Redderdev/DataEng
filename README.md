# Data Engineering Pipeline (Fake Store API)

End-to-end Pipeline mit Batch (Airflow) und Streaming (Kafka) auf Basis der Fake Store API. Fokus auf reproduzierbares Deployment via Docker Compose, Star-Schema in PostgreSQL und klar dokumentierten Entscheidungen.

## Anforderungen und Abdeckung
- Periodisches Scraping: Airflow-DAG lädt Produkte/Users/Orders täglich.
- Scheduling: Apache Airflow als Orchestrator.
- Vorverarbeitung: Externe Python-Tasks (Bereinigung, Transformation, Anreicherung) vor DB-Load.
- Speicherung: PostgreSQL mit Star-Schema (Fact Events/Orders, Dim Products/Users/Date), Indizes und Basis-Tuning.
- Deployment: Alles als Code via Docker Compose; keine manuellen DB-Änderungen.
- Beispielanalyse: Leichte SQL-Queries (Top-Umsatz, Käufe pro Nutzer, Tagesverlauf).

## Architektur (Zielbild)
- Batch: Fake Store API -> Airflow DAG -> Raw Zone -> Clean -> PostgreSQL (warehouse)
- Streaming: Event-Simulator -> Kafka Topic `order_events` -> Consumer -> PostgreSQL (raw + clean)
- Services: Postgres, Kafka + ZooKeeper, Airflow (webserver, scheduler, init), Producer, Consumer

## Verzeichnisstruktur
- docker-compose.yml
- dags/               # Airflow DAGs
- src/producer/       # Kafka Event-Simulator
- src/consumer/       # Kafka Consumer -> Postgres
- db/init/            # SQL-Init (DBs, Schema, Indizes)
- docs/               # Architektur, Entscheidungen, Betrieb

## Quickstart (lokal)
1) Docker Desktop starten.
2) `.env` aus `.env.example` kopieren und Keys setzen (Fernet, Secret).
3) `docker-compose up -d` starten.
4) Airflow Web: http://localhost:8080 (Admin/Admin, falls nicht geändert), DAG `webshop_batch_dag` aktivieren.
5) Kafka Producer/Consumer starten automatisch mit Compose und senden/lesen Events.
6) Postgres erreichbar auf localhost:5432 (User/Pass: postgres/postgres, DB: warehouse).

## Nächste Schritte
- Schema in db/init/01_schema.sql ausformulieren.
- Airflow DAG in dags/webshop_batch_dag.py implementieren.
- Producer/Consumer ausarbeiten (Schemas, Validierung, Inserts).
- Beispiel-SQLs dokumentieren.
