import redis
import os
import json

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
STREAM_NAME = "telemetry_stream"

# Connection pool for high throughput
redis_pool = redis.ConnectionPool(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)
r = redis.Redis(connection_pool=redis_pool)

def publish_to_stream(telemetry_data: dict):
    """Appends a telemetry dictionary to the Redis Stream."""
    try:
        # XADD to stream, capping the stream at 100,000 items to prevent memory bloat
        r.xadd(STREAM_NAME, {"payload": json.dumps(telemetry_data)}, maxlen=100000)
    except Exception as e:
        print(f"Redis XADD Error: {e}")