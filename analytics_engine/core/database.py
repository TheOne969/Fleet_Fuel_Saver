import os
import psycopg2 # Library to interact with POSTgreSQL database

def get_db_connection():  # Creates and returns a connection to the PostgreSQL database
    return psycopg2.connect(  
        host=os.getenv("PG_HOST", "localhost"),  
        port=os.getenv("PG_PORT", "5432"), 
        dbname=os.getenv("PG_DB", "fleet_db"), 
        user=os.getenv("PG_USER", "fleet_user"), 
        password=os.getenv("PG_PASSWORD", "fleet_password") 
    )

def init_db():  # Initializes the database schema and required extensions
    conn = get_db_connection()  
    cur = conn.cursor() 
    cur.execute("""
        CREATE TABLE IF NOT EXISTS telemetry_data (  -- Creates the table only if it doesn't already exist
            time TIMESTAMPTZ NOT NULL,  -- Timestamp with time zone (required by TimescaleDB for time-series)
            trip_id TEXT NOT NULL,  -- Unique identifier for the vehicle's trip
            speed DOUBLE PRECISION,  -- Vehicle speed as a high-precision decimal
            rpm INTEGER,  -- Engine RPM as a whole number
            ambient_temp DOUBLE PRECISION,  -- Outside temperature
            gradient DOUBLE PRECISION,  -- Road incline percentage
            gps_lat DOUBLE PRECISION,  -- GPS latitude coordinate
            gps_lng DOUBLE PRECISION  -- GPS longitude coordinate
        );
        CREATE EXTENSION IF NOT EXISTS timescaledb;  -- Enables the TimescaleDB extension for time-series optimization in Postgres
        SELECT create_hypertable('telemetry_data', 'time', if_not_exists => TRUE);  -- Converts the standard Postgres table into a TimescaleDB hypertable partitioned by 'time'
        SELECT add_retention_policy('telemetry_data', INTERVAL '7 days', if_not_exists => TRUE); -- Automatically deletes data older than 7 days
    """)  
    conn.commit()  
    cur.close()  
    conn.close()
