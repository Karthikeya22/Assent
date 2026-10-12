from httpx import AsyncClient

from assent_agents.policy.ingest import load_snapshot
from assent_agents.policy.tree import CriteriaTree
from assent_api.db import SessionLocal
from assent_api.models import User
from assent_api.policy_load import GOLD_DIR
from assent_api.services import policies

from .conftest import bearer


async def _load(users: dict[str, User]) -> str:
    tree = CriteriaTree.model_validate_json((GOLD_DIR / "L39240-v15.tree.json").read_text("utf-8"))
    async with SessionLocal() as s:
        pv = await policies.upsert_version(s, load_snapshot("L39240", 15), service_family="esi")
        await policies.replace_tree(s, pv, tree, approved_by=users["policy_admin"].id)
        await s.commit()
        return str(pv.id)


async def test_list_policies(client: AsyncClient, users: dict[str, User]) -> None:
    pv_id = await _load(users)
    r = await client.get("/api/v1/policies", headers=bearer(users["clinician"]))
    assert r.status_code == 200
    [p] = r.json()
    assert p["source_id"] == "L39240" and p["service_family"] == "esi"
    assert p["latest_version"]["id"] == pv_id and p["latest_version"]["status"] == "approved"


async def test_policy_version_returns_nested_tree_with_spans(
    client: AsyncClient, users: dict[str, User]
) -> None:
    pv_id = await _load(users)
    r = await client.get(f"/api/v1/policy-versions/{pv_id}", headers=bearer(users["auditor"]))
    assert r.status_code == 200
    body = r.json()
    root = body["criteria"]
    assert root["key"] == "esi" and root["kind"] == "AND"

    def walk(n: dict) -> list[dict]:  # type: ignore[type-arg]
        return [n, *[x for c in n["children"] for x in walk(c)]]

    nodes = walk(root)
    assert len([n for n in nodes if n["kind"] == "LEAF"]) == 12
    leaf = next(n for n in nodes if n["key"] == "dur.pain")
    text = body["raw_text"]
    assert text[leaf["span"][0] : leaf["span"][1]] == "Pain duration of at least four (4) weeks"
    assert [c["key"] for c in root["children"]] == ["dx", "sev", "dur", "rehab", "contra", "freq"]


async def test_unknown_version_is_404(client: AsyncClient, users: dict[str, User]) -> None:
    r = await client.get(
        "/api/v1/policy-versions/00000000-0000-0000-0000-000000000000",
        headers=bearer(users["coordinator"]),
    )
    assert r.status_code == 404


async def test_policies_require_auth(client: AsyncClient) -> None:
    assert (await client.get("/api/v1/policies")).status_code == 401
