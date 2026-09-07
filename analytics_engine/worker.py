import json
import logging
from datetime import datetime
from core.redis import get_redis_client
from core.database import get_db_connection, init_db
from engine import AnomalyDetector

def main():
    logging.basicConfig(level=logging.INFO)
    init_db()
    r = get_redis_client()
    db = get_db_connection()
    db.autocommit = True
    cursor = db.cursor()
    
    detector = AnomalyDetector()
    last_id = "0"
    
    logging.info("Analytics Worker started")
    while True:
        try:
            events = r.xread({"telemetry:stream": last_id}, count=100, block=1000)
            if not events:
                continue
                
            for stream_name, messages in events:
                for msg_id, data in messages:
                    last_id = msg_id
                    trip_id = data["trip_id"]
                    rpm = float(data["rpm"])
                    speed = float(data["speed"])
                    
                    is_anomaly, z_score = detector.check_anomaly(trip_id, rpm, speed)
                    
                    if is_anomaly:
                        alert = {
                            "trip_id": trip_id,
                            "type": "AGGRESSIVE_DRIVING",
                            "rpm": rpm,
                            "speed": speed,
                            "z_score": float(z_score),
                            "timestamp": data["timestamp"]
                        }
                        r.publish("alerts:live", json.dumps(alert))
                        logging.warning(f"Anomaly detected for {trip_id}: {alert}")

                    # Async batching skipped for Ponytail laziness - single inserts work until they don't
                    cursor.execute("""
                        INSERT INTO telemetry_data (time, trip_id, speed, rpm, ambient_temp, gradient, gps_lat, gps_lng)
                        VALUES (to_timestamp(%s / 1000.0), %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        int(data["timestamp"]), trip_id, speed, rpm, 
                        float(data["ambient_temp"]), float(data["gradient"]), 
                        float(data["gps_lat"]), float(data["gps_lng"])
                    ))
        except Exception as e:
            logging.error(f"Worker error: {e}")

if __name__ == "__main__":
    main()