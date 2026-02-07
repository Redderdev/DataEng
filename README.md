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
# 1. Ins Verzeichnis wechseln
cd DataEng

# 2. .env Datei erstellen (mit gültigen Keys)
AIRFLOW__CORE__FERNET_KEY=
AIRFLOW__WEBSERVER__SECRET_KEY=


# 3. Alle Services starten
docker-compose up -d

# 4. Warten bis Postgres ready ist (ca. 10-15 Sek)
sleep 15

# 5. Schema in warehouse DB anlegen (weil Init-Scripts nur in postgres DB laufen)
docker exec -i de_postgres psql -U postgres -d warehouse -f /docker-entrypoint-initdb.d/01_schema.sql

# 6. Producer/Consumer neu starten (damit sie die Tabellen finden)
docker-compose restart producer consumer

# 7. Status prüfen
docker-compose ps

# 8 webserver neu starten wenn airflow also  8080 nicht funktioniert
docker-compose restart airflow-webserver airflow-scheduler

# Batch Pipeline aktiviren 
Jetzt Batch-Pipeline aktivieren:

Airflow UI öffnen: Klick auf Port 8080 Link in PWD
Login: admin / admin
DAG aktivieren: Toggle bei webshop_batch_dag auf ON
Manuell triggern: Klick auf DAG → Play-Button → "Trigger DAG"
Warten bis grün (ca. 30-60 Sek)


# TESTS zu führen 

## Gesammteübersicht 
# Wie viele Events insgesamt?
docker exec -it de_postgres psql -U postgres -d warehouse -c "SELECT count(*) FROM fact_orders;"

# Wie viele Produkte und Nutzer?
docker exec -it de_postgres psql -U postgres -d warehouse -c "SELECT (SELECT count(*) FROM dim_products) AS products, (SELECT count(*) FROM dim_users) AS users;"

## 2 Top 5 produkte nach umsatz 
docker exec -it de_postgres psql -U postgres -d warehouse -c "
SELECT p.title, SUM(f.price_amount * f.quantity) AS umsatz
FROM fact_orders f
JOIN dim_products p ON f.product_id = p.product_id
WHERE f.event_type = 'purchase'
GROUP BY p.title
ORDER BY umsatz DESC
LIMIT 5;
"
## 3 Käufe pro Nutzer 
docker exec -it de_postgres psql -U postgres -d warehouse -c "
SELECT u.name, COUNT(*) AS käufe, SUM(f.price_amount * f.quantity) AS gesamtumsatz
FROM fact_orders f
JOIN dim_users u ON f.user_id = u.user_id
WHERE f.event_type = 'purchase'
GROUP BY u.name
ORDER BY gesamtumsatz DESC;
"

## 4 Event-Typen (Klicks,Suchen, käufe)
docker exec -it de_postgres psql -U postgres -d warehouse -c "
SELECT event_type, COUNT(*) AS anzahl
FROM fact_orders
GROUP BY event_type
ORDER BY anzahl DESC;
"

## 5 Top NUtzer (nach Ausgaben) 
docker exec -it de_postgres psql -U postgres -d warehouse -c "
SELECT u.name, u.email, 
       COUNT(*) AS käufe,
       ROUND(SUM(f.price_amount * f.quantity)::numeric, 2) AS gesamtausgaben
FROM fact_orders f
JOIN dim_users u ON f.user_id = u.user_id
WHERE f.event_type = 'purchase'
GROUP BY u.name, u.email
ORDER BY gesamtausgaben DESC;
"
## Event-Stream-Status (Wie viele events pro typ?)
docker exec -it de_postgres psql -U postgres -d warehouse -c "
SELECT event_type, COUNT(*) AS count, 
       ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM fact_orders), 1) AS prozent
FROM fact_orders
GROUP BY event_type;
"