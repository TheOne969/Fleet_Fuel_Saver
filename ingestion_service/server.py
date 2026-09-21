import grpc
import asyncio
import logging

from shared_proto import telemetry_pb2
from shared_proto import telemetry_pb2_grpc
from shared_redis.client import get_async_redis_client

class TelemetryService(telemetry_pb2_grpc.TelemetryServiceServicer):
    def __init__(self):
        self.redis = get_async_redis_client()
        self.stream_name = "telemetry:stream"

    async def StreamTelemetry(self, request_iterator, context):
        points_received = 0 
        try: 
            async for point in request_iterator:
                data = { 
                    "trip_id": point.trip_id, 
                    "timestamp": point.timestamp, 
                    "speed": point.speed, 
                    "rpm": point.rpm,
                    "ambient_temp": point.ambient_temp,
                    "gradient": point.gradient,
                    "gps_lat": point.gps_lat,
                    "gps_lng": point.gps_lng, 
                } 
                # Redis requires string/int/bytes values. Convert floats to strings.
                for key, val in data.items():
                    if isinstance(val, float):
                        data[key] = str(val)
                
                # Async XADD to Redis Stream
                await self.redis.xadd(self.stream_name, data, maxlen=100000)
                points_received += 1
                
                # Demo Heartbeat: Log every 50 points received per stream
                if points_received % 50 == 0:
                    logging.info(f"[Ingestion] Stream active: Received {points_received} points so far from this vehicle connection.") 
        except Exception as e: 
            logging.error(f"Error processing stream: {e}") 
        
        return telemetry_pb2.TelemetryResponse(
            success=True, 
            message="Stream processed",
            points_received=points_received
        ) 

async def serve():
    server = grpc.aio.server()
    telemetry_pb2_grpc.add_TelemetryServiceServicer_to_server(TelemetryService(), server)
    server.add_insecure_port('[::]:50051')
    await server.start()
    logging.info("Async Ingestion server started on port 50051")
    await server.wait_for_termination()

if __name__ == '__main__': 
    logging.basicConfig(level=logging.INFO) 
    asyncio.run(serve())
