from sqlalchemy import func, select

from assent_agents.policy.ingest import load_snapshot
from assent_agents.policy.tree import CriteriaTree
from assent_api.db import SessionLocal
from assent_api.models import AuditLog, CriteriaNode, Policy, PolicyVersion, User, VersionStatus
from assent_api.policy_load import GOLD_DIR
from assent_api.services import policies


def _gold() -> CriteriaTree:
    return CriteriaTree.model_validate_json((GOLD_DIR / "L39240-v15.tree.json").read_text("utf-8"))


async def test_load_is_idempotent_and_spans_match(users: dict[str, User]) -> None:
    snap, tree = load_snapshot("L39240", 15), _gold()
    admin = users["policy_admin"]
    ids = []
    for _ in range(2):
        async with SessionLocal() as s:
            pv = await policies.upsert_version(s, snap, service_family="esi")
            await policies.replace_tree(s, pv, tree, approved_by=admin.id)
            await s.commit()
            ids.append(set(await s.scalars(select(CriteriaNode.id))))
    assert ids[0] == ids[1]  # unchanged tree keeps its rows: verdicts and gaps reference them

    async with SessionLocal() as s:
        assert await s.scalar(select(func.count()).select_from(Policy)) == 1
        pv = (await s.scalars(select(PolicyVersion))).one()
        assert pv.status == VersionStatus.approved and pv.approved_by == admin.id
        nodes = (
            await s.scalars(select(CriteriaNode).where(CriteriaNode.policy_version_id == pv.id))
        ).all()
        assert len(nodes) == len(tree.nodes())
        by_key = {n.key: n for n in nodes}
        leaf = by_key["dur.pain"]
        assert pv.raw_text[leaf.policy_span_start : leaf.policy_span_end] == (
            "Pain duration of at least four (4) weeks"
        )
        assert by_key[leaf.key].parent_id == by_key["dur.standard"].id
        assert leaf.threshold_json == {"min_weeks": 4}
        # Each approval is audited (twice here, one per load).
        assert (
            await s.scalar(
                select(func.count())
                .select_from(AuditLog)
                .where(AuditLog.action == "policy_version.approve")
            )
            == 2
        )


async def test_tree_with_bad_quote_is_rejected(users: dict[str, User]) -> None:
    snap, tree = load_snapshot("L39240", 15), _gold()
    tree.root.children[0].source_quote = "text that is not in the LCD"
    async with SessionLocal() as s:
        pv = await policies.upsert_version(s, snap, service_family="esi")
        try:
            await policies.replace_tree(s, pv, tree, approved_by=users["policy_admin"].id)
        except ValueError as e:
            assert "quote not found" in str(e)
        else:
            raise AssertionError("bad quote was accepted")


async def test_changed_tree_replaces_unreferenced_rows(users: dict[str, User]) -> None:
    snap, tree = load_snapshot("L39240", 15), _gold()
    for label in ("first", "second"):
        tree.root.label = label
        async with SessionLocal() as s:
            pv = await policies.upsert_version(s, snap, service_family="esi")
            await policies.replace_tree(s, pv, tree, approved_by=None)
            await s.commit()
    async with SessionLocal() as s:
        root = await s.scalar(select(CriteriaNode).where(CriteriaNode.key == "esi"))
        assert root is not None and root.label == "second"
