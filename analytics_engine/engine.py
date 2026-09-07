import numpy as np
from collections import defaultdict, deque

class AnomalyDetector:
    def __init__(self, window_size=20, z_threshold=3.0):
        self.window_size = window_size
        self.z_threshold = z_threshold
        # Stores rpm values per trip
        self.windows = defaultdict(lambda: deque(maxlen=window_size))
        
    def check_anomaly(self, trip_id, rpm, speed):
        window = self.windows[trip_id]
        window.append(rpm)
        
        if len(window) < self.window_size:
            return False, 0.0
            
        mean = np.mean(window)
        std = np.std(window)
        
        if std == 0:
            return False, 0.0
            
        z_score = (rpm - mean) / std
        is_anomaly = abs(z_score) > self.z_threshold
        return is_anomaly, z_score