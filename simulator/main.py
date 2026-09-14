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

def generate_telemetry(trip_id):
    global is_running
    csv_path = "/data/vehicle_data.csv"
    
    if not os.path.exists(csv_path):
        print(f"❌ ERROR: Dataset not found at {csv_path}!")
        print("Falling back to random generation...")
        yield from random_generation(trip_id)
        return

    print(f"✅ Found Kaggle Dataset! Replaying {csv_path}...")
    try:
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if not is_running:
                    break
                    
                # Map Kaggle columns to Protobuf schema
                yield telemetry_pb2.TelemetryPoint( 
                    trip_id=str(trip_id), 
                    timestamp=int(time.time() * 1000),
                    speed=float(row['Vehicle Speed[km/h]']), 
                    rpm=int(float(row['Engine RPM[RPM]'])),
                    ambient_temp=25.0,
                    gradient=0.0,
                    gps_lat=float(row['Latitude[deg]']), 
                    gps_lng=float(row['Longitude[deg]'])
                )  
                time.sleep(config.TICK_RATE_MS / 1000.0)
                
    except Exception as e:
        print(f"\n❌ PYTHON CSV GENERATOR CRASHED: {e}")
        traceback.print_exc()

def random_generation(trip_id):
    global is_running
    speed = 0.0  
    rpm = 800.0  
    lat, lng = 17.3850, 78.4867  

    try:  
        target_speed = 40.0
        while is_running:  
            if random.random() < 0.05: # 5% chance per second to change target speed
                target_speed = random.choice([0.0, 40.0, 90.0, 130.0]) # Stop, City, Highway, Overspeeding
                
            # Smoothly accelerate/decelerate towards target speed
            speed += (target_speed - speed) * 0.1 + random.uniform(-1.0, 1.0)
            speed = max(0.0, speed)
            
            # Base RPM scales with speed
            rpm = max(800.0, 1000.0 + (speed * 20.0) + random.uniform(-200.0, 200.0))

            anomaly = random.random()
            if anomaly < 0.02:
                # 2% chance: Force Idle Revving (Speed < 10, RPM > 3000)
                speed = random.uniform(0.0, 5.0)
                rpm = random.uniform(3500.0, 5000.0)
            elif anomaly < 0.04:
                # 2% chance: Force Sudden Acceleration / RPM Spike (Z-Score > 3.0)
                rpm += random.uniform(3000.0, 4000.0)

            gradient = random.uniform(-5.0, 5.0)
            temp = 25.0 + random.uniform(-0.5, 0.5)

            lat += random.uniform(-0.0001, 0.0001)
            lng += random.uniform(-0.0001, 0.0001)

            yield telemetry_pb2.TelemetryPoint( 
                trip_id=str(trip_id), 
                timestamp=int(time.time() * 1000),  
                speed=float(speed), 
                rpm=int(rpm),
                ambient_temp=float(temp),
                gradient=float(gradient), 
                gps_lat=float(lat), 
                gps_lng=float(lng)
            )  
            time.sleep(config.TICK_RATE_MS / 1000.0)

    except Exception as e:  
        print(f"\n❌ PYTHON GENERATOR CRASHED: {e}")  
        traceback.print_exc()

def run():
    global is_running 
    print(f"Connecting to Ingestion Service at {config.INGESTION_HOST}...") 
    trip_id = f"trip-{uuid.uuid4().hex[:8]}"

    with grpc.insecure_channel(config.INGESTION_HOST) as channel:
        stub = telemetry_pb2_grpc.TelemetryServiceStub(channel)
        print(f"Starting trip {trip_id}. Press Ctrl+C to stop.") 

        try:  
            response = stub.StreamTelemetry(generate_telemetry(trip_id))
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