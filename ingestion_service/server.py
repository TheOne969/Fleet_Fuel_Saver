import grpc
from concurrent import futures
import json

import telemetry_pb2
import telemetry_pb2_grpc
from core.redis_client import publish_to_stream

class TelemetryServicer(telemetry_pb2_grpc.TelemetryServiceServicer):
    def StreamTelemetry(self, request_iterator, context):
        points_received = 0
        print("Vehicle connected. Receiving stream...")
        
        try:
            for point in request_iterator:
                # 1. Convert Protobuf to Python Dict
                data = {
                    "trip_id": point.trip_id,
                    "timestamp": point.timestamp,
                    "speed": point.speed,
                    "rpm": point.rpm,
                    "ambient_temp": point.ambient_temp,
                    "gradient": point.gradient,
                    "gps_lat": point.gps_lat,
                    "gps_lng": point.gps_lng
                }
                
                # 2. Push to Redis Streams
                publish_to_stream(data)
                points_received += 1
                
                if points_received % 50 == 0:
                    print(f"Ingested {points_received} points from {point.trip_id}...")
                    
        except Exception as e:
            print(f"Stream interrupted: {e}")
            
        return telemetry_pb2.TelemetryResponse(
            success=True,
            points_received=points_received,
            message="Stream processed successfully."
        )

def serve():
    # Allow up to 100 concurrent vehicle streams
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=100))
    telemetry_pb2_grpc.add_TelemetryServiceServicer_to_server(TelemetryServicer(), server)
    server.add_insecure_port('[::]:50051')
    
    print("gRPC Ingestion Service running on port 50051...")
    server.start()
    server.wait_for_termination()

if __name__ == '__main__':
    serve()