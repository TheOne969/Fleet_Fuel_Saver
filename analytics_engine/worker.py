import json
import logging
import uuid
import os
from shared_redis import get_redis_client
from core.database import get_db_connection, init_db
from engine import RuleEngine
from redis.exceptions import ResponseError

def main(): 
    logging.basicConfig(level=logging.INFO)  
    init_db()  
    r = get_redis_client()  
    db = get_db_connection() 
    
    # Enable autocommit to avoid needing manual db.commit() after every batch insert.
    db.autocommit = True
    cursor = db.cursor()
    
    # Pass the redis client so the engine can use it for stateless sliding windows
    engine = RuleEngine(r)
    
    # Configure Consumer Group
    stream_name = "telemetry:stream"
    group_name = "analytics_group"
    
    # Generate a unique worker ID using the container's hostname or a random UUID.
    # This allows Redis to track which specific worker grabbed which message.
    worker_id = f"worker-{os.getenv('HOSTNAME', uuid.uuid4().hex[:6])}"
    
    try:
        # Create a consumer group. id='0' tells it to start at the absolute beginning of the stream.
        # mkstream=True automatically creates the stream if it doesn't exist yet.
        r.xgroup_create(stream_name, group_name, id='0', mkstream=True)
        logging.info(f"Created consumer group {group_name}")
    except ResponseError as e:
        # Ignore the error if the group already exists from a previous run.
        if "BUSYGROUP Consumer Group name already exists" not in str(e):
            raise
    
    logging.info(f"Analytics Worker {worker_id} started in consumer group {group_name}")
    
    while True:
        try:
            # Read from the consumer group using ">" to get new messages never delivered to any consumer.
            # count=200 fetches up to 200 points at a time for efficient batch processing.
            # block=1000 causes the worker to wait peacefully for 1 second if the stream is empty, saving CPU.
            events = r.xreadgroup(group_name, worker_id, {stream_name: ">"}, count=200, block=1000)
            if not events:
                continue  
                
            telemetry_batch = []
            alerts_batch = []
            msg_ids_to_ack = []
            engine_batch = []
            
            for stream, messages in events:  
                for msg_id, data in messages:
                    # Keep track of the message IDs so we can acknowledge them as processed later
                    msg_ids_to_ack.append(msg_id)
                    
                    trip_id = data["trip_id"]  
                    rpm = float(data["rpm"])  
                    speed = float(data["speed"])  
                    
                    # Prepare telemetry as a tuple to be used in bulk Postgres inserts
                    telemetry_batch.append((
                        int(data["timestamp"]), trip_id, speed, rpm, 
                        float(data["ambient_temp"]), float(data["gradient"]), 
                        float(data["gps_lat"]), float(data["gps_lng"])
                    ))
                    
                    # Add to engine batch for bulk evaluation
                    engine_batch.append({
                        "trip_id": trip_id,
                        "rpm": rpm,
                        "speed": speed,
                        "timestamp": data["timestamp"]
                    })
                    
            # Evaluate all 200 points in one massive Redis pipeline!
            alerts = engine.evaluate_batch(engine_batch)
            
            for alert in alerts:
                # Instantly broadcast the alert to all connected Frontend Websockets via Pub/Sub
                r.publish("alerts:live", json.dumps(alert))
                logging.warning(f"Alert generated for {alert['trip_id']}: {alert}")

                alerts_batch.append((
                    int(alert["timestamp"]), alert["trip_id"], alert["type"], 
                    alert["severity"], alert["reason"]
                ))

            # Execute batch inserts to dramatically reduce Postgres network round-trips
            if telemetry_batch:
                from psycopg2.extras import execute_batch
                execute_batch(cursor, """
                    INSERT INTO telemetry_data (time, trip_id, speed, rpm, ambient_temp, gradient, gps_lat, gps_lng)
                    VALUES (to_timestamp(%s / 1000.0), %s, %s, %s, %s, %s, %s, %s)
                """, telemetry_batch)
                
            if alerts_batch:
                execute_batch(cursor, """
                    INSERT INTO alerts (time, trip_id, type, severity, reason)
                    VALUES (to_timestamp(%s / 1000.0), %s, %s, %s, %s)
                """, alerts_batch)
            
            # XACK (Acknowledge) tells Redis that this worker successfully saved these messages to Postgres,
            # so Redis can safely delete them from the group's "Pending" list.
            if msg_ids_to_ack:
                r.xack(stream_name, group_name, *msg_ids_to_ack)
                
        except Exception as e:  
            logging.error(f"Worker error: {e}")  

if __name__ == "__main__":  
    main()