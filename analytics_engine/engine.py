import numpy as np 
from collections import deque  # Imports double-ended queue data structure

class RuleEngine:
    def __init__(self, window_size=20, z_threshold=3.0):
        self.window_size = window_size 
        self.z_threshold = z_threshold  
        self.windows = {}  # Rolling queues for RPM history per trip_id
        
    def evaluate(self, trip_id, rpm, speed):
        """
        Evaluates telemetry against multiple business rules.
        Returns a list of alerts (dicts) triggered by this data point.
        """
        alerts = []
        
        # Rule 1: Hard Speeding Limit
        if speed > 120.0:
            alerts.append({
                "type": "OVERSPEEDING",
                "severity": "HIGH",
                "reason": f"Speed {speed:.1f} km/h exceeds maximum limit of 120 km/h."
            })
            
        # Rule 2: Idle Revving (High RPM while barely moving)
        if speed < 10.0 and rpm > 3000:
            alerts.append({
                "type": "IDLE_REVVING",
                "severity": "MEDIUM",
                "reason": f"High engine revs ({rpm} RPM) while vehicle is stationary or moving slowly."
            })

        # Rule 3: Sudden Acceleration / Aggressive Driving (Z-Score)
        if trip_id not in self.windows:  
            self.windows[trip_id] = deque(maxlen=self.window_size)
            
        window = self.windows[trip_id]
        window.append(rpm)
        
        if len(window) >= self.window_size:
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