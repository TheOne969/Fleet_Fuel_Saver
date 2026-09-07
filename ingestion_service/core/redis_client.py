import os
import redis
import os
import json

REDIS_HOST = os.getenv("REDIS_HOST", "localhost") # Fetches Redis host from env or defaults to localhost
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379)) # Fetches Redis port from env or defaults to 6379
STREAM_NAME = "telemetry_stream" # Sets the default stream name
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379")) # Re-fetches Redis port (redundant line)

# Connection pool for high throughput
redis_pool = redis.ConnectionPool(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True) # Creates a reusable Redis connection pool
r = redis.Redis(connection_pool=redis_pool) # Instantiates a Redis client using the pool

def publish_to_stream(telemetry_data: dict): # Defines a function to publish data
    """Appends a telemetry dictionary to the Redis Stream.""" # Docstring
    try: # Starts error-handling block
        # XADD to stream, capping the stream at 100,000 items to prevent memory bloat
        r.xadd(STREAM_NAME, {"payload": json.dumps(telemetry_data)}, maxlen=100000) # Publishes JSON-serialized data to stream, capped at 100k
    except Exception as e: # Catches any publishing errors
        print(f"Redis XADD Error: {e}") # Prints the error
def get_redis_client(): # Defines a function to get a raw client
    return redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True) # Returns a new Redis client instance without the pool