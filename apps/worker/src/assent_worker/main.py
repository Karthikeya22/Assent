"""arq worker: runs agent graphs off the request path. `uv run arq assent_worker.main.WorkerSettings`"""

import logging
from typing import Any, ClassVar

from arq.connections import RedisSettings

from assent_api.settings import get_settings

log = logging.getLogger("assent.worker")


async def ping(ctx: dict[str, Any], msg: str) -> str:
    log.info("ping %s", msg)
    return f"pong: {msg}"


class WorkerSettings:
    functions: ClassVar[list[Any]] = [ping]
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
