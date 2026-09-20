import numpy as np 
from collections import deque  # Imports double-ended queue data structure

class RuleEngine:
    def __init__(self, redis_client, window_size=20, z_threshold=1.5):
        self.redis = redis_client
        self.window_size = window_size 
        self.z_threshold = z_threshold  
        
    def evaluate(self, trip_id, rpm, speed):
        """
        Evaluates telemetry against multiple business rules.
        Returns a list of alerts (dicts) triggered by this data point.
        """
        alerts = []
        
        # Rule 1: Hard Speeding Limit
        if speed > 60.0:
            alerts.append({
                "type": "OVERSPEEDING",
                "severity": "HIGH",
                "reason": f"Speed {speed:.1f} km/h exceeds maximum limit of 60 km/h."
            })
            
        # Rule 2: Idle Revving (High RPM while barely moving)
        if speed < 20.0 and rpm > 2000:
            alerts.append({
                "type": "IDLE_REVVING",
                "severity": "MEDIUM",
                "reason": f"High engine revs ({rpm} RPM) while vehicle is stationary or moving slowly."
            })

        # Rule 3: Sudden Acceleration / Aggressive Driving (Z-Score)
        window_key = f"window:{trip_id}"
        
        # Add to redis list and keep only the last window_size elements
        # rpush (Right Push) 
        self.redis.rpush(window_key, rpm)
        
        # ltrim (List Trim) truncate the list so it only keeps the most recent `self.window_size` elements.
        # By passing negative indices (-self.window_size to -1), we are telling Redis to keep exactly the last N items,
        self.redis.ltrim(window_key, -self.window_size, -1)
        
        # Fetch the window to evaluate
        window_str = self.redis.lrange(window_key, 0, -1)
        
        if len(window_str) >= self.window_size:
            window = [float(x) for x in window_str]
            mean = np.mean(window)
            std = np.std(window)
            
            if std > 0:
                z_score = (rpm - mean) / std
                if abs(z_score) > self.z_threshold:
                    alerts.append({
                        "type": "AGGRESSIVE_ACCELERATION",
                        "severity": "HIGH",
                        "reason": f"Sudden RPM spike detected (Z-Score: {z_score:.2f})."
                    })
                    
        return alerts