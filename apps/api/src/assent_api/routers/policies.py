import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select

from assent_api.deps import CurrentUser, Session
from assent_api.models import CriteriaNode, Policy, PolicyVersion, VersionStatus

router = APIRouter(prefix="/api/v1", tags=["policies"])


class VersionSummary(BaseModel):
    id: uuid.UUID
    version: str
    status: VersionStatus
    effective_date: datetime | None


class PolicyOut(BaseModel):
    id: uuid.UUID
    source_id: str
    title: str
    payer: str
    service_family: str
    latest_version: VersionSummary | None


class CriterionOut(BaseModel):
    id: uuid.UUID
    key: str
    kind: str
    label: str
    n_required: int | None
    evidence_type: str | None
    threshold: dict[str, Any] | None
    lookback_days: int | None
    span: tuple[int, int] | None
    children: list["CriterionOut"]


class PolicyVersionOut(BaseModel):
    id: uuid.UUID
    policy: PolicyOut
    version: str
    status: VersionStatus
    effective_date: datetime | None
    approved_at: datetime | None
    source_url: str
    raw_text: str
    criteria: CriterionOut | None


@router.get("/policies")
async def list_policies(_: CurrentUser, session: Session) -> list[PolicyOut]:
    pols = (
        await session.scalars(select(Policy).order_by(Policy.service_family, Policy.source_id))
    ).all()
    versions = (await session.scalars(select(PolicyVersion))).all()
    latest: dict[uuid.UUID, PolicyVersion] = {}
    for v in versions:  # few versions per policy: pick the highest number in Python
        if v.policy_id not in latest or int(v.version) > int(latest[v.policy_id].version):
            latest[v.policy_id] = v
    return [_policy_out(p, latest.get(p.id)) for p in pols]


@router.get("/policy-versions/{version_id}")
async def get_policy_version(
    version_id: uuid.UUID, _: CurrentUser, session: Session
) -> PolicyVersionOut:
    pv = await session.get(PolicyVersion, version_id)
    if pv is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Policy version not found")
    policy = await session.get(Policy, pv.policy_id)
    assert policy is not None  # FK
    rows = (
        await session.scalars(
            select(CriteriaNode)
            .where(CriteriaNode.policy_version_id == pv.id)
            .order_by(CriteriaNode.order_index)
        )
    ).all()
    return PolicyVersionOut(
        id=pv.id,
        policy=_policy_out(policy, pv),
        version=pv.version,
        status=pv.status,
        effective_date=pv.effective_date,
        approved_at=pv.approved_at,
        source_url=pv.source_url,
        raw_text=pv.raw_text,
        criteria=_nest(rows),
    )


def _policy_out(p: Policy, v: PolicyVersion | None) -> PolicyOut:
    summary = (
        VersionSummary(id=v.id, version=v.version, status=v.status, effective_date=v.effective_date)
        if v
        else None
    )
    return PolicyOut(
        id=p.id,
        source_id=p.source_id,
        title=p.title,
        payer=p.payer,
        service_family=p.service_family,
        latest_version=summary,
    )


def _nest(rows: list[CriteriaNode] | Any) -> CriterionOut | None:
    kids: dict[uuid.UUID | None, list[CriteriaNode]] = {}
    for r in rows:
        kids.setdefault(r.parent_id, []).append(r)

    def build(r: CriteriaNode) -> CriterionOut:
        span = (
            (r.policy_span_start, r.policy_span_end)
            if r.policy_span_start is not None and r.policy_span_end is not None
            else None
        )
        return CriterionOut(
            id=r.id,
            key=r.key,
            kind=r.kind.value,
            label=r.label,
            n_required=r.n_required,
            evidence_type=r.evidence_type,
            threshold=r.threshold_json,
            lookback_days=r.lookback_days,
            span=span,
            children=[build(c) for c in kids.get(r.id, [])],
        )

    roots = kids.get(None, [])
    return build(roots[0]) if roots else None
