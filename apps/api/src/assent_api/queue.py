"""arq job queue client (the API enqueues; assent_worker executes)."""

from typing import Any

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

from assent_api.settings import get_settings

_pool: ArqRedis | None = None


async def enqueue(job: str, *args: Any) -> None:
    global _pool
    if _pool is None:
        _pool = await create_pool(RedisSettings.from_dsn(get_settings().redis_url))
    await _pool.enqueue_job(job, *args)
