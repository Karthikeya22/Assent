import asyncio
import json
import uuid

import pytest
from httpx import AsyncClient

from assent_api import queue
from assent_api.db import SessionLocal, redis
from assent_api.models import Case, Patient, User
from assent_api.services import run_bus

from .conftest import bearer


async def _case(users: dict[str, User], org_key: str = "coordinator") -> uuid.UUID:
    async with SessionLocal() as s:
        p = Patient(
            fhir_id=f"p-{uuid.uuid4()}",
            display_name_synthetic="Rosa Alvarez",
            birth_year=1958,
            sex="female",
        )
        s.add(p)
        await s.flush()
        c = Case(
            org_id=users[org_key].org_id,
            patient_id=p.id,
            service_family="esi",
            cpt_codes=["64483"],
            icd10_codes=["M54.16"],
        )
        s.add(c)
        await s.commit()
        return c.id


@pytest.fixture
def enqueued(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, ...]]:
    jobs: list[tuple[str, ...]] = []

    async def fake(job: str, *args: str) -> None:
        jobs.append((job, *args))

    monkeypatch.setattr(queue, "enqueue", fake)
    return jobs


async def test_start_run_enqueues_and_blocks_a_second_one(
    client: AsyncClient, users: dict[str, User], enqueued: list[tuple[str, ...]]
) -> None:
    cid = await _case(users)
    h = bearer(users["coordinator"])
    r = await client.post(f"/api/v1/cases/{cid}/runs", json={"trigger": "manual"}, headers=h)
    assert r.status_code == 202
    run_id = r.json()["run_id"]
    assert enqueued == [("run_case_job", run_id)]
    again = await client.post(f"/api/v1/cases/{cid}/runs", json={}, headers=h)
    assert again.status_code == 409  # Review Focus 4
    detail = (await client.get(f"/api/v1/cases/{cid}", headers=h)).json()
    assert detail["latest_run"]["id"] == run_id and detail["patient"]["name"] == "Rosa Alvarez"


async def test_other_org_and_auditor_cannot_start_runs(
    client: AsyncClient, users: dict[str, User], enqueued: list[tuple[str, ...]]
) -> None:
    cid = await _case(users)
    r = await client.post(
        f"/api/v1/cases/{cid}/runs", json={}, headers=bearer(users["b_coordinator"])
    )
    assert r.status_code == 404
    r = await client.post(f"/api/v1/cases/{cid}/runs", json={}, headers=bearer(users["auditor"]))
    assert r.status_code == 403
    assert enqueued == []


async def _collect(run_id: str) -> list[dict]:  # type: ignore[type-arg]
    return [json.loads(d) async for d in run_bus.stream(redis, run_id) if d]


async def test_late_joiner_gets_backlog_then_live_events_exactly_once() -> None:
    run_id = str(uuid.uuid4())
    await run_bus.publish(redis, run_id, {"type": "node_started", "n": 1})
    await run_bus.publish(redis, run_id, {"type": "verdict", "n": 2})
    task = asyncio.create_task(_collect(run_id))
    await asyncio.sleep(0.3)  # the client is now subscribed and has replayed the backlog
    await run_bus.publish(redis, run_id, {"type": "logic_update", "n": 3})
    await run_bus.publish(redis, run_id, {"type": "run_finished", "n": 4})
    got = await asyncio.wait_for(task, 5)
    assert [e["n"] for e in got] == [1, 2, 3, 4]


async def test_joining_a_finished_run_replays_and_closes() -> None:
    run_id = str(uuid.uuid4())
    for i, t in enumerate(["node_started", "run_failed"]):
        await run_bus.publish(redis, run_id, {"type": t, "n": i})
    got = await asyncio.wait_for(_collect(run_id), 5)
    assert [e["type"] for e in got] == ["node_started", "run_failed"]


async def test_sse_endpoint_streams_the_log(
    client: AsyncClient, users: dict[str, User], enqueued: list[tuple[str, ...]]
) -> None:
    cid = await _case(users)
    h = bearer(users["coordinator"])
    run_id = (await client.post(f"/api/v1/cases/{cid}/runs", json={}, headers=h)).json()["run_id"]
    await run_bus.publish(redis, run_id, {"type": "verdict", "criterion_id": "dur.pain"})
    await run_bus.publish(redis, run_id, {"type": "run_finished", "readiness": 1.0})
    r = await client.get(f"/api/v1/runs/{run_id}/stream", headers=h)
    assert r.headers["content-type"].startswith("text/event-stream")
    frames = [json.loads(line[6:]) for line in r.text.splitlines() if line.startswith("data: ")]
    assert [f["type"] for f in frames] == ["verdict", "run_finished"]
