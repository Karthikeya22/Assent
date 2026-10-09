import asyncio
from collections.abc import Awaitable, Callable

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from assent_api.db import SessionLocal, redis

router = APIRouter(tags=["health"])


async def _ping_db() -> None:
    async with SessionLocal() as s:
        await s.execute(text("SELECT 1"))


async def _ping_redis() -> None:
    await redis.ping()


@router.get("/healthz")
async def healthz() -> JSONResponse:
    checks: dict[str, Callable[[], Awaitable[None]]] = {"db": _ping_db, "redis": _ping_redis}
    out: dict[str, str] = {}
    for name, ping in checks.items():
        try:
            await asyncio.wait_for(ping(), timeout=2)
            out[name] = "ok"
        except Exception as e:  # any failure is a health failure; report it, don't raise
            out[name] = f"error: {e or type(e).__name__}"
    healthy = all(v == "ok" for v in out.values())
    return JSONResponse(out, status_code=200 if healthy else 503)
