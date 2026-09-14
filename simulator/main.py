import time   
import random
import grpc  
import uuid  # Used to generate unique identifiers (UUIDs) for trip IDs
import sys  
import traceback  # Used to print detailed exception tracebacks on error

from shared_proto import telemetry_pb2, telemetry_pb2_grpc  # Import generated Protobuf messages and gRPC service stubs from shared package
from . import config  # Import configuration settings (like TICK_RATE_MS and INGESTION_HOST)


is_running = True  #flag used to control whether the continuous telemetry streaming loop continues running

def generate_telemetry(trip_id):  # Generator function that continuously yields simulated TelemetryPoint objects
    global is_running  # References the global is_running flag so it can read and update it
    # Set starting parameters
    speed = 0.0  
    rpm = 800.0  
    lat, lng = 17.3850, 78.4867  

    try:  
        while is_running:  
            # Calculate physics updates
            speed = max(0.0, min(140.0, speed + random.uniform(-2.0, 2.5)))  # Updates speed with random acceleration/deceleration, bounded between 0 and 140 km/h
            rpm = max(800.0, min(6500.0, rpm + random.uniform(-100.0, 150.0) + (speed * 2.0)))  # Updates RPM based on speed change and random fluctuations, capped between 800 and 6500
            gradient = random.uniform(-5.0, 5.0)  # Generates a random road incline/decline percentage between -5% and +5%
            temp = 25.0 + random.uniform(-0.5, 0.5)  # Generates ambient outdoor temperature centered around 25°C with slight noise

            # --- Aggressive Driving Injection ---
            # 1% chance every tick to simulate a harsh acceleration
            if random.random() < 0.01:  # 1% probability check on each iteration
                rpm += random.uniform(2000.0, 3500.0)  # Simulates sudden engine revving by adding a spike to RPM
                speed += random.uniform(5.0, 15.0)  # Simulates sudden vehicle burst by adding speed

            lat += random.uniform(-0.0001, 0.0001)  # Simulates movement by applying a small random offset to latitude
            lng += random.uniform(-0.0001, 0.0001)  # Simulates movement by applying a small random offset to longitude

            # Safely cast all values to match the Protobuf schema exactly
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
            time.sleep(config.TICK_RATE_MS / 1000.0)  # Pauses execution for configured tick rate duration 

    except Exception as e:  
        print(f"\n❌ PYTHON GENERATOR CRASHED: {e}")  
        traceback.print_exc()  # Prints full stack trace for debugging

def run():  # Main execution function for setting up gRPC channel and initiating the stream
    global is_running 
    print(f"Connecting to Ingestion Service at {config.INGESTION_HOST}...") 
    trip_id = f"trip-{uuid.uuid4().hex[:8]}"  # Generates a unique trip ID string (e.g., "trip-a1b2c3d4")

    with grpc.insecure_channel(config.INGESTION_HOST) as channel:  # Opens an unencrypted gRPC network channel to ingestion server
        stub = telemetry_pb2_grpc.TelemetryServiceStub(channel)  # Instantiates the gRPC client stub bound to the channel
        print(f"Starting trip {trip_id}. Press Ctrl+C to stop.") 

        try:  
            response = stub.StreamTelemetry(generate_telemetry(trip_id))  # Sends stream from generator to server and waits for final response
            print(f"Stream ended cleanly. Server says: {response.message} (Points: {response.points_received})")  # Prints server acknowledgment message and total ingested point count
        except KeyboardInterrupt:  # Catches manual interruption (Ctrl+C)
            print("\nCaught interrupt signal! Shutting down...") 
            is_running = False  # Sets global flag to False to break out of generator loop
        except grpc.RpcError as e:  # Catches gRPC network or protocol errors
            if "Exception iterating requests" not in e.details():  # Filters out redundant iteration details as alreayd covered in generate_telemetry()
                print(f"gRPC Error: {e.details()}") 

if __name__ == '__main__':  
    try:  # Encloses main execution call
        run()  # Calls run() function to start simulator
    except KeyboardInterrupt: 
        pass  # Ignores further keyboard interrupt exceptions as it's already caught in run()
    finally:  
        is_running = False  
        sys.exit(0)  # Cleanly terminates Python process with exit code 0, so that Docker knows it's intentional exit and hence doesn't restart. 