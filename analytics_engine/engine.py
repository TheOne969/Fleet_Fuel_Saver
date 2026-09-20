import numpy as np 
from collections import deque  # Imports double-ended queue data structure

class RuleEngine:
    def __init__(self, redis_client, window_size=20, z_threshold=1.5):
        self.redis = redis_client
        self.window_size = window_size 
        self.z_threshold = z_threshold  
        
    def evaluate_batch(self, batch_data):
        """
        Evaluates a batch of telemetry points against multiple business rules.
        batch_data is a list of dicts: [{"trip_id": x, "rpm": y, "speed": z, ...}, ...]
        Returns a flat list of all alerts generated from this batch.
        """
        alerts = []
        
        # 1. First pass: Evaluate static rules (no database lookup required)
        for data in batch_data:
            speed = data["speed"]
            rpm = data["rpm"]
            trip_id = data["trip_id"]
            
            if speed > 60.0:
                alerts.append({
                    "trip_id": trip_id,
                    "timestamp": data["timestamp"],
                    "type": "OVERSPEEDING",
                    "severity": "HIGH",
                    "reason": f"Speed {speed:.1f} km/h exceeds maximum limit of 60 km/h."
                })
                
            if speed < 20.0 and rpm > 2000:
                alerts.append({
                    "trip_id": trip_id,
                    "timestamp": data["timestamp"],
                    "type": "IDLE_REVVING",
                    "severity": "MEDIUM",
                    "reason": f"High engine revs ({rpm} RPM) while vehicle is stationary or moving slowly."
                })

        # 2. Second pass: Build one massive Redis Pipeline for the entire batch
        pipeline = self.redis.pipeline()
        for data in batch_data:
            window_key = f"window:{data['trip_id']}"
            pipeline.rpush(window_key, data["rpm"])
            pipeline.ltrim(window_key, -self.window_size, -1)
            pipeline.lrange(window_key, 0, -1)
            
        # Execute all 600+ commands in a single network round-trip!
        results = pipeline.execute()
        
        # 3. Third pass: Extract the sliding windows and calculate Z-Scores
        # Since we added 3 commands per point, the results list is exactly 3 * len(batch_data)
        for i, data in enumerate(batch_data):
            # The LRANGE result is at index i*3 + 2
            window_str = results[i * 3 + 2]
            
            if len(window_str) >= self.window_size:
                window = [float(x) for x in window_str]
                mean = np.mean(window)
                std = np.std(window)
                
                if std > 0:
                    z_score = (data["rpm"] - mean) / std
                    if abs(z_score) > self.z_threshold:
                        alerts.append({
                            "trip_id": data["trip_id"],
                            "timestamp": data["timestamp"],
                            "type": "AGGRESSIVE_ACCELERATION",
                            "severity": "HIGH",
                            "reason": f"Sudden RPM spike detected (Z-Score: {z_score:.2f})."
                        })
                        
        return alerts