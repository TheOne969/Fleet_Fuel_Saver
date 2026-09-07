import numpy as np
from collections import deque, defaultdict

# Store sliding windows for each active trip. 
# Using deque(maxlen=20) automatically drops old points, preventing memory leaks.
trip_states = defaultdict(lambda: {
    "rpm": deque(maxlen=20),
    "speed": deque(maxlen=20)
})

def process_telemetry(data: dict):
    """
    Evaluates a single telemetry point for anomalies.
    Returns an alert dictionary if anomalous, else None.
    """
    trip_id = data["trip_id"]
    rpm = data["rpm"]
    speed = data["speed"]
    
    state = trip_states[trip_id]
    state["rpm"].append(rpm)
    state["speed"].append(speed)
    
    # We need at least 10 points to establish a statistical baseline
    if len(state["rpm"]) < 10:
        return None
        
    # Calculate Z-score for RPM using NumPy
    rpm_array = np.array(state["rpm"])
    mean_rpm = np.mean(rpm_array)
    std_rpm = np.std(rpm_array)
    
    if std_rpm == 0:  # Prevent division by zero if vehicle is idling consistently
        return None
        
    z_score = (rpm - mean_rpm) / std_rpm
    
    # Anomaly trigger: RPM is > 2.5 standard deviations above recent average, 
    # AND the vehicle is actually moving.
    if z_score > 2.5 and speed > 10.0:
        return {
            "type": "AGGRESSIVE_DRIVING",
            "trip_id": trip_id,
            "message": f"Aggressive acceleration detected! RPM spike to {rpm} (Z-Score: {z_score:.2f})",
            "timestamp": data["timestamp"],
            "severity": "high"
        }
        
    return None