import pytest
from httpx import AsyncClient

from assent_api.routers import health


async def test_healthz_ok(client: AsyncClient) -> None:
    r = await client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"db": "ok", "redis": "ok"}


async def test_healthz_reports_failed_dependency(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def boom() -> None:
        raise ConnectionError("redis down")

    monkeypatch.setattr(health, "_ping_redis", boom)
    r = await client.get("/healthz")
    assert r.status_code == 503
    assert r.json() == {"db": "ok", "redis": "error: redis down"}
