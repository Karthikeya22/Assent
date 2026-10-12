import json
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
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


def _shape(rows: Sequence[CriteriaNode]) -> set[tuple[Any, ...]]:
    key = {r.id: r.key for r in rows}
    return {
        (
            r.key,
            key.get(r.parent_id) if r.parent_id else None,
            r.kind,
            r.n_required,
            r.label,
            r.evidence_type,
            json.dumps(r.threshold_json, sort_keys=True),
            r.lookback_days,
            r.policy_span_start,
            r.policy_span_end,
            r.order_index,
        )
        for r in rows
    }


async def replace_tree(
    s: AsyncSession, pv: PolicyVersion, tree: CriteriaTree, *, approved_by: uuid.UUID | None
) -> None:
    """Replace the version's criteria with `tree`; approve it when `approved_by` is given."""
    if errs := tree.validate_against(pv.raw_text):
        raise ValueError("; ".join(errs))
    spans = tree.spans(pv.raw_text)
    rows: list[CriteriaNode] = []

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
        rows.append(row)
        for i, c in enumerate(n.children):
            add(c, row.id, i)

    add(tree.root, None, 0)
    old = (
        await s.scalars(select(CriteriaNode).where(CriteriaNode.policy_version_id == pv.id))
    ).all()
    # Keep the rows when nothing changed: verdicts and gap tasks of past runs reference them.
    if _shape(old) != _shape(rows):
        try:
            async with s.begin_nested():
                await s.execute(delete(CriteriaNode).where(CriteriaNode.policy_version_id == pv.id))
        except IntegrityError as e:
            raise ValueError(
                f"{tree.source_id} v{tree.version} has runs against its criteria; "
                "a changed tree must be ingested as a new policy version"
            ) from e
        s.add_all(rows)
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


async def load_tree(s: AsyncSession, pv: PolicyVersion) -> CriteriaTree:
    """Rebuild the approved CriteriaTree for a version from criteria_nodes."""
    rows = (
        await s.scalars(
            select(CriteriaNode)
            .where(CriteriaNode.policy_version_id == pv.id)
            .order_by(CriteriaNode.order_index)
        )
    ).all()
    kids: dict[uuid.UUID | None, list[CriteriaNode]] = {}
    for r in rows:
        kids.setdefault(r.parent_id, []).append(r)

    def build(r: CriteriaNode) -> Node:
        quote = (
            pv.raw_text[r.policy_span_start : r.policy_span_end]
            if r.policy_span_start is not None and r.policy_span_end is not None
            else None
        )
        return Node(
            key=r.key,
            kind=r.kind.value,
            label=r.label,
            n_required=r.n_required,
            evidence_type=r.evidence_type,
            threshold=r.threshold_json,
            lookback_days=r.lookback_days,
            source_quote=quote,
            children=[build(c) for c in kids.get(r.id, [])],
        )

    policy = await s.get(Policy, pv.policy_id)
    assert policy is not None  # FK
    return CriteriaTree(
        source_id=policy.source_id, version=int(pv.version), root=build(kids[None][0])
    )


async def approved_version_for(s: AsyncSession, service_family: str) -> PolicyVersion | None:
    # shortcut: picks the first approved LCD for the service family; real routing maps the
    # patient's MAC jurisdiction (state) to its LCD (ARCHITECTURE §6.3 policy_resolver).
    return await s.scalar(
        select(PolicyVersion)
        .join(Policy)
        .where(
            Policy.service_family == service_family, PolicyVersion.status == VersionStatus.approved
        )
        .order_by(Policy.source_id.desc())
        .limit(1)
    )


def _mdy(s: str) -> datetime | None:
    try:
        return datetime.strptime(s, "%m/%d/%Y").replace(tzinfo=UTC)
    except ValueError:
        return None
