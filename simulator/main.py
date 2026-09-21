import time   
import random
import grpc  
import uuid
import sys  
import traceback
import csv
import os

from shared_proto import telemetry_pb2, telemetry_pb2_grpc
import config

is_running = True

def generate_telemetry():
    global is_running
    csv_path = "/data/vehicle_data.csv"
    
    if not os.path.exists(csv_path):
        print(f"❌ ERROR: Dataset not found at {csv_path}!")
        print("Falling back to multi-vehicle random generation...")
        yield from random_generation()
        return

    fallback_trip_id = f"trip-csv-{uuid.uuid4().hex[:8]}"
    print(f"✅ Found Kaggle Dataset! Replaying {csv_path}...")
    num_vehicles = int(os.environ.get("NUM_VEHICLES", "10"))
    print(f"✅ Found Kaggle Dataset! Simulating {num_vehicles} concurrent vehicles from {csv_path}...")
    
    try:
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
            batch = []
            
            for i, row in enumerate(reader):
                if not is_running:
                    break
                    
                # Use the dataset's Trip ID if it exists, otherwise fallback to the generated one
                current_trip = row.get('Trip', row.get('Trip_ID', row.get('Vehicle_ID', fallback_trip_id)))
                # Force a fixed pool of vehicles instead of random dataset trips
                current_trip = f"csv-vehicle-{(i % num_vehicles) + 1:03d}"
                
                speed_str = row['Vehicle Speed[km/h]']
                rpm_str = row['Engine RPM[RPM]']
                
                # Handle empty strings gracefully
                speed_val = float(speed_str) if speed_str.strip() else 0.0
                rpm_val = int(float(rpm_str)) if rpm_str.strip() else 0
                
                # Map Kaggle columns to Protobuf schema
                point = telemetry_pb2.TelemetryPoint( 
                    trip_id=str(current_trip), 
                    trip_id=current_trip, 
                    timestamp=int(time.time() * 1000),
                    speed=speed_val, 
                    rpm=rpm_val,
                    ambient_temp=25.0,
                    gradient=0.0,
                    gps_lat=float(row['Latitude[deg]']), 
                    gps_lng=float(row['Longitude[deg]'])
                )  
                print(f"[CSV] {current_trip} | Speed: {point.speed:5.1f} | RPM: {point.rpm:4.0f}")
                yield point
                time.sleep(config.TICK_RATE_MS / 1000.0)
                batch.append(point)
                
                # When we have collected one point for every vehicle, stream them and sleep
                if len(batch) >= num_vehicles:
                    for p in batch:
                        yield p
                        
                    # Optional: Print the first vehicle of the batch just for terminal output
                    print(f"[CSV] {batch[0].trip_id} | Speed: {batch[0].speed:5.1f} | RPM: {batch[0].rpm:4.0f} (+ {num_vehicles-1} others)")
                    
                    time.sleep(config.TICK_RATE_MS / 1000.0)
                    batch = []
                
    except Exception as e:
        print(f"\n❌ PYTHON CSV GENERATOR CRASHED: {e}")
        traceback.print_exc()

def random_generation():
    global is_running
    NUM_VEHICLES = 3  # Simulate 3 concurrent trips
    
    trips = []
    for _ in range(NUM_VEHICLES):
        trips.append({
            "id": f"trip-{uuid.uuid4().hex[:8]}",
            "speed": 0.0,
            "rpm": 800.0,
            "lat": 17.3850 + random.uniform(-0.1, 0.1),
            "lng": 78.4867 + random.uniform(-0.1, 0.1),
            "target": 40.0
        })

    try:  
        while is_running:  
            for t in trips:
                if random.random() < 0.05: # 5% chance to change target speed
                    t["target"] = random.choice([0.0, 30.0, 50.0, 70.0])
                    
                # Smoothly accelerate/decelerate towards target speed
                t["speed"] = max(0.0, t["speed"] + (t["target"] - t["speed"]) * 0.1 + random.uniform(-1.0, 1.0))
                
                # Base RPM scales with speed
                t["rpm"] = max(800.0, 1000.0 + (t["speed"] * 20.0) + random.uniform(-200.0, 200.0))

                anomaly = random.random()
                if anomaly < 0.02:
                    t["speed"] = random.uniform(0.0, 15.0)
                    t["rpm"] = random.uniform(2500.0, 3500.0)
                elif anomaly < 0.04:
                    t["rpm"] += random.uniform(1500.0, 2500.0)

                t["lat"] += random.uniform(-0.0001, 0.0001)
                t["lng"] += random.uniform(-0.0001, 0.0001)

                point = telemetry_pb2.TelemetryPoint( 
                    trip_id=t["id"], 
                    timestamp=int(time.time() * 1000),  
                    speed=float(t["speed"]), 
                    rpm=int(t["rpm"]),
                    ambient_temp=25.0,
                    gradient=0.0, 
                    gps_lat=float(t["lat"]), 
                    gps_lng=float(t["lng"])
                )
                print(f"[LIVE] {t['id']} | Target: {t['target']:3.0f} | Speed: {t['speed']:5.1f} | RPM: {t['rpm']:4.0f}")
                yield point
                
            time.sleep(config.TICK_RATE_MS / 1000.0)

    except Exception as e:  
        print(f"\n❌ PYTHON GENERATOR CRASHED: {e}")  
        traceback.print_exc()

def run():
    global is_running 
    print(f"Connecting to Ingestion Service at {config.INGESTION_HOST}...") 

    with grpc.insecure_channel(config.INGESTION_HOST) as channel:
        stub = telemetry_pb2_grpc.TelemetryServiceStub(channel)
        print("Starting multi-vehicle simulation. Press Ctrl+C to stop.") 

        try:  
            response = stub.StreamTelemetry(generate_telemetry())
            print(f"Stream ended cleanly. Server says: {response.message} (Points: {response.points_received})")
        except KeyboardInterrupt:
            print("\nCaught interrupt signal! Shutting down...") 
            is_running = False
        except grpc.RpcError as e:
            if "Exception iterating requests" not in e.details():
                print(f"gRPC Error: {e.details()}") 

if __name__ == '__main__':  
    try:
        run()
    except KeyboardInterrupt: 
        pass
    finally:  
        is_running = False  
        sys.exit(0)