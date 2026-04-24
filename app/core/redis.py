import redis.asyncio as redis
import json
from typing import Any
import os

REDIS_URL = f"redis://{os.getenv('REDIS_HOST', 'redis')}:{os.getenv('REDIS_PORT', '6379')}"
TTL = 60 * 60 * 24  # 24 hours

client = redis.from_url(REDIS_URL, decode_responses=True)


async def get_cached(key: str) -> Any | None:
    data = await client.get(f"idempotency:{key}")
    return json.loads(data) if data else None


async def set_cached(key: str, value: Any) -> None:
    await client.set(f"idempotency:{key}", json.dumps(value), ex=TTL)


# Stream
STREAM_TRANSACTIONS = "stream:transactions"
GROUP_NAME = "workers"