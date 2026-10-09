from datetime import UTC, datetime, timedelta

from httpx import AsyncClient

from assent_api.db import SessionLocal
from assent_api.models import Case, Patient, User

from .conftest import bearer


async def _seed_cases(users: dict[str, User], n_a: int, n_b: int) -> None:
    async with SessionLocal() as s:
        p = Patient(fhir_id="p1", display_name_synthetic="R. Alvarez", birth_year=1959, sex="male")
        s.add(p)
        await s.flush()
        t0 = datetime(2026, 10, 1, tzinfo=UTC)
        for org, n in ((users["coordinator"].org_id, n_a), (users["b_coordinator"].org_id, n_b)):
            for i in range(n):
                s.add(
                    Case(
                        org_id=org,
                        patient_id=p.id,
                        service_family="esi",
                        cpt_codes=["62323"],
                        icd10_codes=["M54.16"],
                        created_at=t0 + timedelta(minutes=i),
                    )
                )
        await s.commit()


async def test_empty_worklist(client: AsyncClient, users: dict[str, User]) -> None:
    r = await client.get("/api/v1/cases", headers=bearer(users["coordinator"]))
    assert r.status_code == 200
    assert r.json() == {"items": [], "next_cursor": None}


async def test_other_orgs_cases_are_invisible(client: AsyncClient, users: dict[str, User]) -> None:
    await _seed_cases(users, n_a=0, n_b=3)
    r = await client.get("/api/v1/cases", headers=bearer(users["coordinator"]))
    assert r.json()["items"] == []


async def test_cursor_pagination_walks_all_rows_once(
    client: AsyncClient, users: dict[str, User]
) -> None:
    await _seed_cases(users, n_a=5, n_b=2)
    seen: list[str] = []
    cursor = None
    for _ in range(5):
        params = {"limit": 2} | ({"cursor": cursor} if cursor else {})
        body = (
            await client.get("/api/v1/cases", params=params, headers=bearer(users["coordinator"]))
        ).json()
        seen += [c["id"] for c in body["items"]]
        cursor = body["next_cursor"]
        if not cursor:
            break
    assert len(seen) == 5 == len(set(seen))


async def test_garbage_cursor_is_422(client: AsyncClient, users: dict[str, User]) -> None:
    r = await client.get(
        "/api/v1/cases", params={"cursor": "%%%"}, headers=bearer(users["coordinator"])
    )
    assert r.status_code == 422
