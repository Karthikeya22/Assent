import os

# Must run before any assent_api import: the engine is built from settings at import time.
TEST_DB = "postgresql+asyncpg://assent:assent@localhost:5432/assent_test"
os.environ["DATABASE_URL"] = TEST_DB
os.environ["ALEMBIC_DATABASE_URL"] = TEST_DB

from collections.abc import AsyncIterator, Iterator  # noqa: E402
from pathlib import Path  # noqa: E402

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from assent_api.db import SessionLocal  # noqa: E402
from assent_api.main import create_app  # noqa: E402
from assent_api.models import Base, Organization, Role, User  # noqa: E402
from assent_api.security import create_access_token, hash_password  # noqa: E402

API_DIR = Path(__file__).resolve().parents[1]
PASSWORD = "correct horse"


@pytest.fixture(scope="session", autouse=True)
def _migrated() -> Iterator[None]:
    cfg = Config(str(API_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(API_DIR / "migrations"))
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    yield


@pytest.fixture(autouse=True)
async def _clean() -> AsyncIterator[None]:
    yield
    tables = ", ".join(t.name for t in Base.metadata.sorted_tables)
    async with SessionLocal() as s:
        await s.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
        await s.commit()


@pytest.fixture
async def users() -> dict[str, User]:
    """Two orgs; org A has one user per role, org B has a coordinator."""
    async with SessionLocal() as s:
        a, b = Organization(name="Org A"), Organization(name="Org B")
        s.add_all([a, b])
        await s.flush()
        out = {
            r.value: User(
                org_id=a.id,
                email=f"{r.value}@a.test",
                name=r.value,
                role=r,
                password_hash=hash_password(PASSWORD),
            )
            for r in Role
        }
        out["b_coordinator"] = User(
            org_id=b.id,
            email="coord@b.test",
            name="B",
            role=Role.coordinator,
            password_hash=hash_password(PASSWORD),
        )
        s.add_all(out.values())
        await s.commit()
        return out


def bearer(u: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(u.id, u.org_id, u.role)}"}


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=create_app()), base_url="http://t") as c:
        yield c
