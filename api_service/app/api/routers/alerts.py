import os
import asyncio
import redis.asyncio as redis
from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

router = APIRouter(prefix="/alerts", tags=["alerts"])

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

async def alert_generator(request: Request):
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    pubsub = r.pubsub()
    await pubsub.subscribe("alerts:live")
    
    try:
        while True:
            if await request.is_disconnected():
                break
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message:
                yield {"event": "alert", "data": message["data"]}
    finally:
        await pubsub.unsubscribe("alerts:live")
        await r.aclose()

@router.get("/stream")
async def stream_alerts(request: Request):
    return EventSourceResponse(alert_generator(request))

