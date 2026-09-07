import redis
import os

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

# Standard connection for interacting with Streams and Pub/Sub
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)

STREAM_NAME = "telemetry_stream"
ALERT_CHANNEL = "live_alerts"