from assent_agents.policy.ingest import load_snapshot
from assent_agents.policy.tree import CriteriaTree
from assent_api.db import SessionLocal
from assent_api.models import User
from assent_api.policy_load import GOLD_DIR
from assent_api.services import policies


async def test_tree_survives_db_roundtrip(users: dict[str, User]) -> None:
    gold = CriteriaTree.model_validate_json((GOLD_DIR / "L39240-v15.tree.json").read_text("utf-8"))
    async with SessionLocal() as s:
        pv = await policies.upsert_version(s, load_snapshot("L39240", 15), service_family="esi")
        await policies.replace_tree(s, pv, gold, approved_by=users["policy_admin"].id)
        await s.commit()
        assert (await policies.approved_version_for(s, "esi")) is not None
        back = await policies.load_tree(s, pv)
    assert back.root.model_dump() == gold.root.model_dump()
