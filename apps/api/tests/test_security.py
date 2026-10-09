import time
import uuid

import jwt
import pytest
from fastapi import Depends
from httpx import ASGITransport, AsyncClient

from assent_api.deps import require_role
from assent_api.main import create_app
from assent_api.models import Role, User
from assent_api.security import (
    InvalidToken,
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)
from assent_api.settings import get_settings

from .conftest import PASSWORD, bearer


def test_password_round_trip_and_salt() -> None:
    h1, h2 = hash_password("pw"), hash_password("pw")
    assert h1 != h2
    assert verify_password("pw", h1) and not verify_password("nope", h1)


def test_token_round_trip() -> None:
    uid, oid = uuid.uuid4(), uuid.uuid4()
    claims = decode_token(create_access_token(uid, oid, Role.auditor))
    assert (claims.sub, claims.org, claims.role) == (uid, oid, Role.auditor)


def test_expired_token_is_rejected() -> None:
    tok = create_access_token(uuid.uuid4(), uuid.uuid4(), Role.coordinator, ttl_minutes=-1)
    with pytest.raises(InvalidToken):
        decode_token(tok)


def test_wrong_signature_is_rejected() -> None:
    tok = jwt.encode({"sub": str(uuid.uuid4()), "exp": time.time() + 60}, "x" * 32, "HS256")
    with pytest.raises(InvalidToken):
        decode_token(tok)


async def test_login_returns_token(client: AsyncClient, users: dict[str, User]) -> None:
    r = await client.post(
        "/api/v1/auth/token", json={"email": "coordinator@a.test", "password": PASSWORD}
    )
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["user"]["role"] == "coordinator"
    assert decode_token(body["access_token"]).sub == users["coordinator"].id


@pytest.mark.parametrize("email", ["coordinator@a.test", "nobody@a.test"])
async def test_bad_login_is_401_without_enumeration(
    client: AsyncClient, users: dict[str, User], email: str
) -> None:
    r = await client.post("/api/v1/auth/token", json={"email": email, "password": "wrong"})
    assert r.status_code == 401
    assert r.json()["detail"] == "Invalid email or password"


@pytest.mark.parametrize(
    "header",
    [
        None,
        "Bearer not-a-jwt",
        "Bearer " + jwt.encode({"sub": "x"}, get_settings().jwt_secret, "HS256"),  # no exp/role
    ],
)
async def test_bad_or_missing_token_is_401(client: AsyncClient, header: str | None) -> None:
    r = await client.get("/api/v1/cases", headers={"Authorization": header} if header else {})
    assert r.status_code == 401


async def test_wrong_role_is_403(users: dict[str, User]) -> None:
    app = create_app()

    @app.get("/_t/admin", dependencies=[Depends(require_role(Role.policy_admin))])
    async def _admin() -> dict[str, bool]:
        return {"ok": True}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        assert (await c.get("/_t/admin", headers=bearer(users["clinician"]))).status_code == 403
        assert (await c.get("/_t/admin", headers=bearer(users["policy_admin"]))).status_code == 200
