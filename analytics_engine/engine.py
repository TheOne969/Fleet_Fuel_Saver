import numpy as np 
from collections import deque  # Imports double-ended queue data structure

class AnomalyDetector:  # Defines a class to detect aggressive driving behavior using statistical z-scores
    def __init__(self, window_size=20, z_threshold=3.0):  # Initializes the detector with default window size (20 points) and threshold (3 standard deviations)
        self.window_size = window_size 
        self.z_threshold = z_threshold  

        self.windows = {}  # Standard Python dictionary to hold rolling queues per trip_id
        
    def check_anomaly(self, trip_id, rpm, speed):  # Evaluates a single telemetry point for anomalies
        if trip_id not in self.windows:  
            self.windows[trip_id] = deque(maxlen=self.window_size)  # Initializes a new fixed-size queue if this trip_id is seen for the first time
            
        window = self.windows[trip_id]  # Retrieves the recent RPM history queue for this specific trip_id
        window.append(rpm)  # Adds the latest RPM value to the queue (if it hits maxlen=20, the oldest item is automatically dropped)
        
        if len(window) < self.window_size:  # Checks if we have enough historical data points to establish a baseline
            return False, 0.0  # Not enough data yet, returns safe defaults
            
        mean = np.mean(window)
        std = np.std(window)
        
        if std == 0:  # Prevents division by zero if all recent RPM values are exactly identical
            return False, 0.0  
            
        z_score = (rpm - mean) / std  # Calculates the Z-score (how many standard deviations the current RPM is away from the recent average)
        is_anomaly = abs(z_score) > self.z_threshold  # Flags as an anomaly if the Z-score magnitude exceeds the configured threshold
        return is_anomaly, z_score 