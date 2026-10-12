from typing import Any

import httpx
import pytest
from assent_mock_payer.main import Rules, state
from assent_mock_payer.main import app as payer_app
from httpx import AsyncClient
from sqlalchemy import select

from assent_api.db import SessionLocal
from assent_api.models import Appeal, AuditLog, Case, User
from assent_api.services import packets

from .conftest import bearer
from .test_review_api import _setup


@pytest.fixture(autouse=True)
def payer(monkeypatch: pytest.MonkeyPatch) -> None:
    """Route the API's payer calls to the real Mock Payer app, in process."""
    state["rules"], state["responses"] = Rules(), {}
    real = httpx.AsyncClient

    def client(**kw: Any) -> httpx.AsyncClient:
        return real(transport=httpx.ASGITransport(app=payer_app), **kw)

    monkeypatch.setattr(packets.httpx, "AsyncClient", client)


async def test_packet_denial_appeal_loop(
    client: AsyncClient, users: dict[str, User], monkeypatch: pytest.MonkeyPatch
) -> None:
    case_id, run_id = await _setup(users)
    h = bearer(users["coordinator"])
    early = await client.post(f"/api/v1/runs/{run_id}/packet", headers=h)
    assert early.status_code == 409  # the run must be approved first
    await client.post(
        f"/api/v1/runs/{run_id}/resume",
        json={"decision": "approve", "acknowledge_high": True, "acknowledge_not_ready": True},
        headers=h,
    )
    pk = (await client.post(f"/api/v1/runs/{run_id}/packet", headers=h)).json()
    assert pk["validation_errors"] == [] and "Prior authorization request" in pk["letter"]

    assert (await client.post(f"/api/v1/packets/{pk['id']}/submit", headers=h)).status_code == 409
    await client.post(f"/api/v1/packets/{pk['id']}/approve", headers=h)
    sub = (await client.post(f"/api/v1/packets/{pk['id']}/submit", headers=h)).json()
    assert sub["status"] == "A3" and {d["criterion_key"] for d in sub["denials"]} >= {
        "sev.baseline"
    }
    async with SessionLocal() as s:
        assert (await s.get(Case, __import__("uuid").UUID(case_id))).status.value == "denied"  # type: ignore[union-attr]

    pdf = await client.get(f"/api/v1/packets/{pk['id']}", params={"format": "pdf"}, headers=h)
    assert pdf.headers["content-type"] == "application/pdf" and pdf.content.startswith(b"%PDF")

    queued: list[str] = []

    async def enqueue(job: str, *args: Any) -> None:
        queued.append(job)

    monkeypatch.setattr("assent_api.routers.packets.queue.enqueue", enqueue)
    ap = (await client.post(f"/api/v1/submissions/{sub['id']}/appeal", headers=h)).json()
    assert ap["status"] == "drafting" and queued == ["appeal_job"]
    text = {"draft_text": "We request reconsideration; see the attached excerpts."}
    assert (
        await client.patch(f"/api/v1/appeals/{ap['id']}", json=text, headers=h)
    ).status_code == 409

    async with SessionLocal() as s:  # what the worker does when the draft is ready
        a = await s.get(Appeal, __import__("uuid").UUID(ap["id"]))
        assert a is not None
        a.status, a.draft_text = "draft", "Drafted."
        await s.commit()
    edited = (await client.patch(f"/api/v1/appeals/{ap['id']}", json=text, headers=h)).json()
    assert edited["draft_text"] == text["draft_text"]
    resent = (await client.post(f"/api/v1/appeals/{ap['id']}/send", headers=h)).json()
    assert resent["status"] in ("A1", "A3") and resent["packet_id"] != pk["id"]

    listed = (await client.get(f"/api/v1/cases/{case_id}/packets", headers=h)).json()
    assert len(listed) == 2 and listed[0]["submissions"][0]["appeal"]["status"] == "sent"
    async with SessionLocal() as s:
        actions = set(await s.scalars(select(AuditLog.action)))
    assert {
        "packet.build",
        "packet.approve",
        "packet.submit",
        "appeal.start",
        "appeal.send",
    } <= actions


async def test_clinician_cannot_submit(client: AsyncClient, users: dict[str, User]) -> None:
    _, run_id = await _setup(users)
    h = bearer(users["coordinator"])
    await client.post(
        f"/api/v1/runs/{run_id}/resume",
        json={"decision": "approve", "acknowledge_high": True, "acknowledge_not_ready": True},
        headers=h,
    )
    pk = (await client.post(f"/api/v1/runs/{run_id}/packet", headers=h)).json()
    r = await client.post(f"/api/v1/packets/{pk['id']}/approve", headers=bearer(users["clinician"]))
    assert r.status_code == 403
