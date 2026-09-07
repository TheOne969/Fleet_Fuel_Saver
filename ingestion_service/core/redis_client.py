import os
import redis
import json

REDIS_HOST = os.getenv("REDIS_HOST", "localhost") # Fetches Redis host from env or defaults to localhost
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379)) # Fetches Redis port from env or defaults to 6379

# Longed-lived Reusable Connection pool for high throughput
redis_pool = redis.ConnectionPool(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)

def get_redis_client(): 
    return redis.Redis(connection_pool=redis_pool)