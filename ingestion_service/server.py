import grpc
from concurrent import futures
import logging
import json

import telemetry_pb2
import telemetry_pb2_grpc
from core.redis_client import get_redis_client

class TelemetryService(telemetry_pb2_grpc.TelemetryServiceServicer): # Defines the gRPC service class inheriting from the generated proto stub
    def __init__(self): # Initializes the service instance
        self.redis = get_redis_client() # Creates a Redis client connection
        self.stream_name = "telemetry:stream" # Sets the Redis Stream key name

    def StreamTelemetry(self, request_iterator, context): # Handles incoming gRPC streams of telemetry points
        points_received = 0 # Initializes a counter for received points
        try: # Starts an error-handling block
            for point in request_iterator: # Iterates over each incoming gRPC point in the stream
                data = { # Starts constructing a dictionary for the point
                    "trip_id": point.trip_id, # Extracts trip_id
                    "timestamp": point.timestamp, # Extracts timestamp
                    "speed": point.speed, # Extracts speed
                    "rpm": point.rpm, # Extracts rpm
                    "ambient_temp": point.ambient_temp, # Extracts ambient temperature
                    "gradient": point.gradient, # Extracts gradient
                    "gps_lat": point.gps_lat, # Extracts GPS latitude
                    "gps_lng": point.gps_lng, # Extracts GPS longitude
                } # Closes the dictionary
                # XADD to Redis Stream
                self.redis.xadd(self.stream_name, data) # Appends the data dictionary to the Redis Stream
                points_received += 1 # Increments the received points counter
        except Exception as e: # Catches any exceptions during streaming
            logging.error(f"Error processing stream: {e}") # Logs the error message
        
        # NOTE: Using StreamResponse or whatever is defined in telemetry_pb2. 
        # But we need to check the actual proto file for the correct response name.
        return telemetry_pb2.TelemetryResponse( # Returns the final gRPC response to the client
            success=True, # Indicates the stream was successful
            message="Stream processed", # Provides a success message
            points_received=points_received # Reports how many points were processed
        ) # Closes the response object

def serve(): # Defines the main server startup function
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10)) # Creates a gRPC server with a thread pool of 10 workers
    telemetry_pb2_grpc.add_TelemetryServiceServicer_to_server(TelemetryService(), server) # Registers our TelemetryService with the gRPC server
    server.add_insecure_port('[::]:50051') # Binds the server to all interfaces on port 50051 without TLS
    server.start() # Starts listening for incoming gRPC connections
    logging.info("Ingestion server started on port 50051") # Logs that the server is running
    server.wait_for_termination() # Blocks the main thread to keep the server alive

if __name__ == '__main__': # Checks if the script is being run directly
    logging.basicConfig(level=logging.INFO) # Configures the root logger to show INFO level and above
    serve() # Calls the server startup function