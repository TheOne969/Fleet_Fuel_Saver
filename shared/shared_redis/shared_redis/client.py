import os
import redis
import redis.asyncio as redis_async

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

# Long-lived Reusable Connection pool for high throughput
redis_pool = redis.ConnectionPool(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)

def get_redis_client(): 
    return redis.Redis(connection_pool=redis_pool)

async_redis_pool = redis_async.ConnectionPool(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)

def get_async_redis_client():
    return redis_async.Redis(connection_pool=async_redis_pool)

