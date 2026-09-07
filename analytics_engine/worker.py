import json
import time
from core.redis import r, STREAM_NAME, ALERT_CHANNEL
from engine import process_telemetry

def run_worker():
    print("Analytics Worker started. Waiting for telemetry data...")
    
    # Start reading only new messages
    last_id = '$' 
    points_analyzed = 0
    
    while True:
        try:
            # Block for up to 1000ms waiting for new data
            messages = r.xread({STREAM_NAME: last_id}, count=100, block=1000)
            
            if not messages:
                continue
                
            for stream, msg_list in messages:
                for message_id, message_data in msg_list:
                    last_id = message_id
                    
                    raw_payload = message_data.get("payload")
                    if not raw_payload:
                        continue
                        
                    telemetry_data = json.loads(raw_payload)
                    alert = process_telemetry(telemetry_data)
                    
                    # --- NEW: Visual feedback ---
                    points_analyzed += 1
                    if points_analyzed % 50 == 0:
                        print(f"⚙️ Worker analyzed {points_analyzed} points in-memory...")
                    
                    if alert:
                        print(f"🚨 ALERT DETECTED: {alert['message']}")
                        r.publish(ALERT_CHANNEL, json.dumps(alert))
                        
        except Exception as e:
            print(f"Worker Error: {e}")
            time.sleep(1)

if __name__ == "__main__":
    run_worker()