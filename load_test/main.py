import asyncio
import time
import os
import grpc
import uuid
import logging

from shared_proto import telemetry_pb2, telemetry_pb2_grpc

# Environment variables
INGESTION_HOST = os.getenv("INGESTION_HOST", "ingestion:50051")
NUM_VEHICLES = int(os.getenv("NUM_VEHICLES", "100"))
TEST_DURATION_SEC = int(os.getenv("TEST_DURATION_SEC", "30"))

stats = {
    "successful_connections": 0,
    "failed_connections": 0,
    "points_sent": 0,
    "errors": 0
}

async def generate_telemetry(trip_id, end_time):
    """Async generator to simulate a single vehicle streaming data."""
    import random
    
    state = {
        "speed": 0.0,
        "rpm": 800.0,
        "lat": 17.3850 + random.uniform(-0.1, 0.1),
        "lng": 78.4867 + random.uniform(-0.1, 0.1),
        "target": 40.0
    }

    while time.time() < end_time:
        if random.random() < 0.05: # 5% chance to change target speed
            state["target"] = random.choice([0.0, 30.0, 50.0, 70.0])
            
        # Smoothly accelerate/decelerate towards target speed
        state["speed"] = max(0.0, state["speed"] + (state["target"] - state["speed"]) * 0.1 + random.uniform(-1.0, 1.0))
        
        # Base RPM scales with speed
        state["rpm"] = max(800.0, 1000.0 + (state["speed"] * 20.0) + random.uniform(-200.0, 200.0))

        anomaly = random.random()
        if anomaly < 0.02:
            state["speed"] = random.uniform(0.0, 15.0)
            state["rpm"] = random.uniform(2500.0, 3500.0)
        elif anomaly < 0.04:
            state["rpm"] += random.uniform(1500.0, 2500.0)

        state["lat"] += random.uniform(-0.0001, 0.0001)
        state["lng"] += random.uniform(-0.0001, 0.0001)

        point = telemetry_pb2.TelemetryPoint(
            trip_id=trip_id,
            timestamp=int(time.time() * 1000),
            speed=float(state["speed"]),
            rpm=int(state["rpm"]),
            ambient_temp=25.0,
            gradient=0.0,
            gps_lat=float(state["lat"]),
            gps_lng=float(state["lng"])
        )
        yield point
        stats["points_sent"] += 1
        await asyncio.sleep(0.5) # Send 2 points per second

async def simulate_vehicle(stub, vehicle_id, end_time):
    """Simulates a single vehicle establishing a gRPC stream and sending data."""
    trip_id = f"loadtest-{vehicle_id}-{uuid.uuid4().hex[:6]}"
    try:
        # Start the stream
        response = await stub.StreamTelemetry(generate_telemetry(trip_id, end_time))
        if response.success:
            stats["successful_connections"] += 1
    except grpc.aio.AioRpcError as e:
        stats["failed_connections"] += 1
        stats["errors"] += 1
        logging.debug(f"Vehicle {vehicle_id} connection failed: {e.code()}")
    except Exception as e:
        stats["errors"] += 1

async def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
    logging.info(f"Starting Load Test with {NUM_VEHICLES} concurrent vehicles for {TEST_DURATION_SEC} seconds...")
    logging.info(f"Target Host: {INGESTION_HOST}")
    
    end_time = time.time() + TEST_DURATION_SEC
    
    # Establish a single async gRPC channel. 
    # In gRPC, a single channel automatically multiplexes multiple concurrent streams.
    async with grpc.aio.insecure_channel(INGESTION_HOST) as channel:
        stub = telemetry_pb2_grpc.TelemetryServiceStub(channel)
        
        # Spawn all vehicles concurrently
        tasks = []
        for i in range(NUM_VEHICLES):
            tasks.append(asyncio.create_task(simulate_vehicle(stub, i, end_time)))
            
        # Wait for all vehicles to finish streaming
        await asyncio.gather(*tasks)

    # Print Report
    logging.info("========================================")
    logging.info("LOAD TEST COMPLETE")
    logging.info(f"Target Concurrent Vehicles: {NUM_VEHICLES}")
    logging.info(f"Successful Connections (Streams closed cleanly): {stats['successful_connections']}")
    logging.info(f"Failed Connections: {stats['failed_connections']}")
    logging.info(f"Total Points Sent: {stats['points_sent']}")
    logging.info(f"Total Unhandled Errors: {stats['errors']}")
    logging.info("========================================")

if __name__ == "__main__":
    asyncio.run(main())

