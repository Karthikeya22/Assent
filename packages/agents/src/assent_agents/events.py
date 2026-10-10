"""Run events (ARCHITECTURE §5 SSE contract). The UI animates only from these."""

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

Event = dict[str, Any]
Emit = Callable[[Event], Awaitable[None]]


def event(type_: str, **fields: Any) -> Event:
    return {"type": type_, **fields, "ts": datetime.now(UTC).isoformat(timespec="milliseconds")}


async def no_emit(_: Event) -> None:
    return None


class Collector:
    """An Emit that keeps events in memory (tests, fixture recording)."""

    def __init__(self) -> None:
        self.events: list[Event] = []

    async def __call__(self, e: Event) -> None:
        self.events.append(e)
