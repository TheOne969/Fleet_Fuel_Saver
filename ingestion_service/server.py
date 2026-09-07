import grpc
from concurrent import futures
import logging

from shared_proto import telemetry_pb2, telemetry_pb2_grpc
from core.redis_client import get_redis_client

class TelemetryService(telemetry_pb2_grpc.TelemetryServiceServicer): # Defines the gRPC service class inheriting from the generated proto stub
    def __init__(self): # Initializes the service instance
        self.redis = get_redis_client() # Creates a Redis client connection
        self.stream_name = "telemetry:stream" # Sets the Redis Stream key name

    def StreamTelemetry(self, request_iterator, context): # Handles incoming gRPC streams of telemetry points
        points_received = 0 
        try: 
            for point in request_iterator: # Iterates over each incoming gRPC point in the stream
                data = { # Starts constructing a dictionary for the point
                    "trip_id": point.trip_id, 
                    "timestamp": point.timestamp, 
                    "speed": point.speed, 
                    "rpm": point.rpm,
                    "ambient_temp": point.ambient_temp,
                    "gradient": point.gradient,
                    "gps_lat": point.gps_lat,
                    "gps_lng": point.gps_lng, 
                } 
                # XADD to Redis Stream
                self.redis.xadd(self.stream_name, data, maxlen=100000) # Appends with maxlen cap
                points_received += 1 
        except Exception as e: 
            logging.error(f"Error processing stream: {e}") 
        
        return telemetry_pb2.TelemetryResponse( # Returns the final gRPC response to the client
            success=True, 
            message="Stream processed", # Provides a success message
            points_received=points_received # Reports how many points were processed
        ) 

def serve(): # Defines the main server startup function, which will act as the middleman between redis streams and vehicle
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10)) # Creates a gRPC server with a thread pool of 10 workers, which can handle 10 vehicles simulatenously
    telemetry_pb2_grpc.add_TelemetryServiceServicer_to_server(TelemetryService(), server) # Registers our TelemetryService with the gRPC server
    server.add_insecure_port('[::]:50051') # Binds the server to all interfaces on port 50051 without TLS encryption.
    server.start() # Starts listening for incoming gRPC connections
    logging.info("Ingestion server started on port 50051")
    server.wait_for_termination() # Blocks the main thread to keep the server alive

if __name__ == '__main__': 
    logging.basicConfig(level=logging.INFO) 
    serve() 