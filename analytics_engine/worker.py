import json
import logging
from datetime import datetime
from shared_redis import get_redis_client
from core.database import get_db_connection, init_db
from engine import RuleEngine

def main(): 
    logging.basicConfig(level=logging.INFO)  
    init_db()  
    r = get_redis_client()  
    db = get_db_connection() 
    db.autocommit = True  # Tells Postgres to automatically commit every executed statement (no manual commit() needed)
    cursor = db.cursor()
    
    engine = RuleEngine() 
    last_id = "$"  # '$' tells Redis to only read NEW messages that arrive after we connect, skipping the historical backlog
    
    logging.info("Analytics Worker started")  
    while True:  # Starts the infinite background processing loop
        try: 
            events = r.xread({"telemetry:stream": last_id}, count=100, block=1000)  # Blocks for up to 1 second waiting to read up to 100 new messages from the Redis Stream since last_id
            if not events:  # Checks if the read timed out without finding new data
                continue  
                
            for stream_name, messages in events:  
                for msg_id, data in messages: 
                    last_id = msg_id  # Update the read pointer every iteration instad of just once after the for loop for CRASH RECOVERY
                    trip_id = data["trip_id"]  
                    rpm = float(data["rpm"])  
                    speed = float(data["speed"])  
                    
                    alerts = engine.evaluate(trip_id, rpm, speed)  # Passes the data to the rule engine
                    
                    for alert_data in alerts:
                        alert = { 
                            "trip_id": trip_id,  
                            "timestamp": data["timestamp"],
                            **alert_data
                        }  
                        r.publish("alerts:live", json.dumps(alert))  # Broadcasts the serialized JSON alert to a Redis Pub/Sub channel for frontend consumption
                        logging.warning(f"Alert generated for {trip_id}: {alert}")

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