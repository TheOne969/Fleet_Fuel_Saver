import os
import psycopg2

def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("PG_HOST", "localhost"),
        port=os.getenv("PG_PORT", "5432"),
        dbname=os.getenv("PG_DB", "fleet_db"),
        user=os.getenv("PG_USER", "fleet_user"),
        password=os.getenv("PG_PASSWORD", "fleet_password")
    )

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS telemetry_data (
            time TIMESTAMPTZ NOT NULL,
            trip_id TEXT NOT NULL,
            speed DOUBLE PRECISION,
            rpm INTEGER,
            ambient_temp DOUBLE PRECISION,
            gradient DOUBLE PRECISION,
            gps_lat DOUBLE PRECISION,
            gps_lng DOUBLE PRECISION
        );
        CREATE EXTENSION IF NOT EXISTS timescaledb;
        SELECT create_hypertable('telemetry_data', 'time', if_not_exists => TRUE);
    """)
    conn.commit()
    cur.close()
    conn.close()

