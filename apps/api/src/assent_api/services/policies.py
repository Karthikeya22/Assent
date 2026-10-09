import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from assent_agents.policy.ingest import LcdSnapshot
from assent_agents.policy.tree import CriteriaTree, Node
from assent_api.models import (
    CriteriaNode,
    NodeKind,
    Policy,
    PolicyKind,
    PolicyVersion,
    VersionStatus,
)
from assent_api.services import audit


async def upsert_version(
    s: AsyncSession, snap: LcdSnapshot, *, service_family: str
) -> PolicyVersion:
    policy = await s.scalar(select(Policy).where(Policy.source_id == snap.source_id))
    if policy is None:
        policy = Policy(
            payer=f"Medicare ({snap.contractor})",
            kind=PolicyKind.LCD,
            source_id=snap.source_id,
            title=snap.title,
            service_family=service_family,
        )
        s.add(policy)
        await s.flush()
    pv = await s.scalar(
        select(PolicyVersion).where(
            PolicyVersion.policy_id == policy.id, PolicyVersion.version == str(snap.version)
        )
    )
    if pv is None:
        pv = PolicyVersion(
            policy_id=policy.id,
            version=str(snap.version),
            effective_date=_mdy(snap.rev_eff_date),
            raw_text=snap.raw_text,
            source_url=snap.source_url,
            content_hash=snap.content_hash,
        )
        s.add(pv)
        await s.flush()
    elif pv.content_hash != snap.content_hash:
        raise ValueError(f"{snap.source_id} v{snap.version}: stored text differs from snapshot")
    return pv


async def replace_tree(
    s: AsyncSession, pv: PolicyVersion, tree: CriteriaTree, *, approved_by: uuid.UUID | None
) -> None:
    """Replace the version's criteria with `tree`; approve it when `approved_by` is given."""
    if errs := tree.validate_against(pv.raw_text):
        raise ValueError("; ".join(errs))
    spans = tree.spans(pv.raw_text)
    await s.execute(delete(CriteriaNode).where(CriteriaNode.policy_version_id == pv.id))

    def add(n: Node, parent: uuid.UUID | None, order: int) -> None:
        start, end = spans.get(n.key, (None, None))
        row = CriteriaNode(
            id=uuid.uuid4(),
            policy_version_id=pv.id,
            parent_id=parent,
            key=n.key,
            kind=NodeKind(n.kind),
            n_required=n.n_required,
            label=n.label,
            evidence_type=n.evidence_type,
            threshold_json=n.threshold,
            lookback_days=n.lookback_days,
            policy_span_start=start,
            policy_span_end=end,
            order_index=order,
        )
        s.add(row)
        for i, c in enumerate(n.children):
            add(c, row.id, i)

    add(tree.root, None, 0)
    await s.flush()
    if approved_by is not None:
        pv.status, pv.approved_by, pv.approved_at = (
            VersionStatus.approved,
            approved_by,
            datetime.now(UTC),
        )
        await audit.append(
            s,
            actor_id=approved_by,
            action="policy_version.approve",
            entity="policy_version",
            entity_id=str(pv.id),
            after={
                "source_id": tree.source_id,
                "version": tree.version,
                "leaves": len(tree.leaves()),
            },
        )


def _mdy(s: str) -> datetime | None:
    try:
        return datetime.strptime(s, "%m/%d/%Y").replace(tzinfo=UTC)
    except ValueError:
        return None
