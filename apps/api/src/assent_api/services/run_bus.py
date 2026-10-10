"""Run event bus on Redis: pub/sub for live clients plus a capped log for late joiners."""

import json
from collections.abc import AsyncIterator
from typing import Any  # redis-py stubs union sync/async returns, so the client is typed Any

LOG_TTL_S = 24 * 3600
LOG_MAX = 2000
TERMINAL = {"run_finished", "run_failed"}


def channel(run_id: str) -> str:
    return f"run:{run_id}"


async def publish(r: Any, run_id: str, ev: dict[str, Any]) -> None:
    data = json.dumps(ev, default=str)
    key = f"{channel(run_id)}:log"
    async with r.pipeline(transaction=True) as p:
        p.rpush(key, data).ltrim(key, -LOG_MAX, -1).expire(key, LOG_TTL_S)
        p.publish(channel(run_id), data)
        await p.execute()


async def stream(r: Any, run_id: str) -> AsyncIterator[str]:
    """Replay the log, then follow live events, ending at a terminal event.

    Subscribe first, then read the log, then skip live events already in the log, so a client
    joining mid-run sees every event exactly once (ARCHITECTURE §5; Review Focus 1-2).
    """
    pubsub = r.pubsub()
    await pubsub.subscribe(channel(run_id))
    try:
        backlog = [
            x.decode() if isinstance(x, bytes) else x
            for x in await r.lrange(f"{channel(run_id)}:log", 0, -1)
        ]
        seen = set(backlog)
        for data in backlog:
            yield data
            if json.loads(data)["type"] in TERMINAL:
                return
        while True:
            msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=15.0)
            if msg is None:
                yield ""  # heartbeat keeps proxies from closing an idle stream
                continue
            data = msg["data"].decode() if isinstance(msg["data"], bytes) else msg["data"]
            if data in seen:
                continue
            yield data
            if json.loads(data)["type"] in TERMINAL:
                return
    finally:
        await pubsub.unsubscribe(channel(run_id))
        await pubsub.aclose()
