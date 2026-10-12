import uuid
from collections.abc import AsyncIterator
from datetime import date, datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select

from assent_agents.case_graph import readiness
from assent_agents.logic import evaluate
from assent_api import queue
from assent_api.db import redis
from assent_api.deps import CurrentUser, Session, require_role
from assent_api.models import (
    Case,
    CaseStatus,
    ChartChunk,
    CriteriaNode,
    EvidenceCitation,
    EvidenceVerdict,
    GapTask,
    Objection,
    ObjectionStatus,
    Patient,
    Policy,
    PolicyVersion,
    Role,
    Run,
    RunStep,
    Verdict,
)
from assent_api.security import TokenClaims
from assent_api.services import audit, policies, run_bus

router = APIRouter(prefix="/api/v1", tags=["runs"])
ACTIVE = ("queued", "running")


class RunCreate(BaseModel):
    trigger: Literal["manual", "rerun"] = "manual"


class RunCreated(BaseModel):
    run_id: uuid.UUID


class StepOut(BaseModel):
    node: str
    status: str
    payload: dict[str, Any] | None


class RunOut(BaseModel):
    id: uuid.UUID
    case_id: uuid.UUID
    status: str
    trigger: str
    started_at: datetime
    finished_at: datetime | None
    steps: list[StepOut]


class CitationOut(BaseModel):
    chunk_id: uuid.UUID
    quote: str
    start: int
    end: int
    verified: bool
    resource_type: str
    resource_id: str
    date: date | None


class VerdictOut(BaseModel):
    id: uuid.UUID
    criterion_key: str
    verdict: str
    confidence: float
    rationale: str
    citations: list[CitationOut]
    overridden: bool = False
    override_reason: str | None = None


class PatientOut(BaseModel):
    name: str
    sex: str
    birth_year: int


class PolicyRef(BaseModel):
    version_id: uuid.UUID
    source_id: str
    version: str
    title: str


class RunSummary(BaseModel):
    id: uuid.UUID
    status: str
    started_at: datetime
    finished_at: datetime | None


class CaseDetail(BaseModel):
    id: uuid.UUID
    service_family: str
    cpt_codes: list[str]
    icd10_codes: list[str]
    status: str
    urgency: str
    sla_due_at: datetime | None
    readiness_score: float | None
    denial_risk: float | None
    patient: PatientOut
    policy: PolicyRef | None
    latest_run: RunSummary | None


class ChunkOut(BaseModel):
    id: uuid.UUID
    resource_type: str
    resource_id: str
    date: date | None
    text: str


async def _case(s: Session, case_id: uuid.UUID, user: TokenClaims) -> Case:
    case = await s.get(Case, case_id)
    if case is None or case.org_id != user.org:  # org scoping: other orgs' cases don't exist
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Case not found")
    return case


async def _run(s: Session, run_id: uuid.UUID, user: TokenClaims) -> Run:
    run = await s.get(Run, run_id)
    if run is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Run not found")
    await _case(s, run.case_id, user)
    return run


@router.get("/cases/{case_id}")
async def get_case(case_id: uuid.UUID, user: CurrentUser, s: Session) -> CaseDetail:
    case = await _case(s, case_id, user)
    patient = await s.get(Patient, case.patient_id)
    assert patient is not None
    policy = None
    if case.policy_version_id and (pv := await s.get(PolicyVersion, case.policy_version_id)):
        pol = await s.get(Policy, pv.policy_id)
        assert pol is not None
        policy = PolicyRef(
            version_id=pv.id, source_id=pol.source_id, version=pv.version, title=pol.title
        )
    last = await s.scalar(
        select(Run).where(Run.case_id == case.id).order_by(Run.started_at.desc()).limit(1)
    )
    return CaseDetail(
        id=case.id,
        service_family=case.service_family,
        cpt_codes=case.cpt_codes,
        icd10_codes=case.icd10_codes,
        status=case.status.value,
        urgency=case.urgency.value,
        sla_due_at=case.sla_due_at,
        readiness_score=case.readiness_score,
        denial_risk=case.denial_risk,
        policy=policy,
        patient=PatientOut(
            name=patient.display_name_synthetic, sex=patient.sex, birth_year=patient.birth_year
        ),
        latest_run=RunSummary(
            id=last.id, status=last.status, started_at=last.started_at, finished_at=last.finished_at
        )
        if last
        else None,
    )


@router.get("/cases/{case_id}/timeline")
async def case_timeline(case_id: uuid.UUID, user: CurrentUser, s: Session) -> list[ChunkOut]:
    await _case(s, case_id, user)
    rows = (
        await s.scalars(
            select(ChartChunk)
            .where(ChartChunk.case_id == case_id, ChartChunk.superseded_at.is_(None))
            .order_by(
                ChartChunk.effective_date.desc().nulls_last(),
                ChartChunk.fhir_resource_id,
                ChartChunk.char_offset,
            )
        )
    ).all()
    return [
        ChunkOut(
            id=r.id,
            resource_type=r.fhir_resource_type,
            resource_id=r.fhir_resource_id,
            date=r.effective_date.date() if r.effective_date else None,
            text=r.text_deid,
        )
        for r in rows
    ]


@router.post("/cases/{case_id}/runs", status_code=status.HTTP_202_ACCEPTED)
async def start_run(
    case_id: uuid.UUID,
    body: RunCreate,
    s: Session,
    user: Annotated[
        TokenClaims, Depends(require_role(Role.coordinator, Role.clinician, Role.policy_admin))
    ],
) -> RunCreated:
    case = await _case(s, case_id, user)
    busy = await s.scalar(select(Run.id).where(Run.case_id == case.id, Run.status.in_(ACTIVE)))
    if busy:
        raise HTTPException(status.HTTP_409_CONFLICT, "A run is already in progress")
    run = Run(case_id=case.id, trigger=body.trigger, graph_version="queued", status="queued")
    s.add(run)
    await s.commit()
    await queue.enqueue("run_case_job", str(run.id))
    return RunCreated(run_id=run.id)


@router.get("/runs/{run_id}")
async def get_run(run_id: uuid.UUID, user: CurrentUser, s: Session) -> RunOut:
    run = await _run(s, run_id, user)
    steps = (
        await s.scalars(
            select(RunStep).where(RunStep.run_id == run.id).order_by(RunStep.started_at)
        )
    ).all()
    return RunOut(
        id=run.id,
        case_id=run.case_id,
        status=run.status,
        trigger=run.trigger,
        started_at=run.started_at,
        finished_at=run.finished_at,
        steps=[StepOut(node=x.node, status=x.status, payload=x.payload_json) for x in steps],
    )


@router.get("/runs/{run_id}/verdicts")
async def run_verdicts(run_id: uuid.UUID, user: CurrentUser, s: Session) -> list[VerdictOut]:
    run = await _run(s, run_id, user)
    rows = (
        await s.execute(
            select(EvidenceVerdict, CriteriaNode.key)
            .join(CriteriaNode, CriteriaNode.id == EvidenceVerdict.criterion_id)
            .where(EvidenceVerdict.run_id == run.id)
            .order_by(CriteriaNode.order_index)
        )
    ).all()
    cites = (
        await s.execute(
            select(EvidenceCitation, ChartChunk)
            .join(ChartChunk, ChartChunk.id == EvidenceCitation.chunk_id)
            .where(EvidenceCitation.verdict_id.in_([v.id for v, _ in rows]))
        )
    ).all()
    by_verdict: dict[uuid.UUID, list[CitationOut]] = {}
    for c, ch in cites:
        by_verdict.setdefault(c.verdict_id, []).append(
            CitationOut(
                chunk_id=c.chunk_id,
                quote=c.quote,
                start=c.start_char,
                end=c.end_char,
                verified=c.verbatim_ok and (c.entailment_score or 0) >= 0.7,
                resource_type=ch.fhir_resource_type,
                resource_id=ch.fhir_resource_id,
                date=ch.effective_date.date() if ch.effective_date else None,
            )
        )
    return [
        VerdictOut(
            id=v.id,
            criterion_key=key,
            verdict=v.verdict.value,
            confidence=v.confidence,
            rationale=v.rationale,
            citations=by_verdict.get(v.id, []),
            overridden=v.overridden_by is not None,
            override_reason=v.override_reason,
        )
        for v, key in rows
    ]


@router.get("/runs/{run_id}/stream", response_class=StreamingResponse)
async def stream_run(run_id: uuid.UUID, user: CurrentUser, s: Session) -> StreamingResponse:
    await _run(s, run_id, user)

    async def sse() -> AsyncIterator[str]:
        async for data in run_bus.stream(redis, str(run_id)):
            yield f"data: {data}\n\n" if data else ": ping\n\n"

    return StreamingResponse(
        sse(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# --- review: objections, gaps, overrides, human decision (PRODUCT §4.5-4.9) ------------------

Reviewer = Annotated[
    TokenClaims, Depends(require_role(Role.coordinator, Role.clinician, Role.policy_admin))
]
Approver = Annotated[TokenClaims, Depends(require_role(Role.coordinator, Role.policy_admin))]


class ObjectionOut(BaseModel):
    id: uuid.UUID
    criterion_key: str | None
    text: str
    severity: str
    status: str
    rebuttal: str | None
    rebuttal_chunk_ids: list[uuid.UUID]


class GapOut(BaseModel):
    id: uuid.UUID
    criterion_key: str | None
    title: str
    detail: str
    assignee_role: str
    status: str


class GapPatch(BaseModel):
    status: Literal["open", "done", "dismissed"]


class VerdictPatch(BaseModel):
    verdict: Literal["met", "not_met", "insufficient"]
    reason: str = Field(min_length=3, max_length=1000)


class ResumeIn(BaseModel):
    decision: Literal["approve", "reject"]
    acknowledge_high: bool = False
    acknowledge_not_ready: bool = False  # approving with unproven criteria is an explicit choice


class ResumeOut(BaseModel):
    case_status: str


async def _keys(s: Session, ids: list[uuid.UUID | None]) -> dict[uuid.UUID, str]:
    real = [i for i in ids if i]
    if not real:
        return {}
    rows = (
        (
            await s.execute(
                select(CriteriaNode.id, CriteriaNode.key).where(CriteriaNode.id.in_(real))
            )
        )
        .tuples()
        .all()
    )
    return dict(rows)


@router.get("/runs/{run_id}/objections")
async def run_objections(run_id: uuid.UUID, user: CurrentUser, s: Session) -> list[ObjectionOut]:
    run = await _run(s, run_id, user)
    rows = (await s.scalars(select(Objection).where(Objection.run_id == run.id))).all()
    keys = await _keys(s, [o.criterion_id for o in rows])
    return [
        ObjectionOut(
            id=o.id,
            criterion_key=keys.get(o.criterion_id) if o.criterion_id else None,
            text=o.text,
            severity=o.severity,
            status=o.status.value,
            rebuttal=o.rebuttal_text,
            rebuttal_chunk_ids=o.rebuttal_citation_ids,
        )
        for o in rows
    ]


@router.get("/cases/{case_id}/gaps")
async def case_gaps(case_id: uuid.UUID, user: CurrentUser, s: Session) -> list[GapOut]:
    case = await _case(s, case_id, user)
    rows = (
        await s.scalars(
            select(GapTask)
            .where(GapTask.case_id == case.id)
            .order_by(GapTask.status, GapTask.title)
        )
    ).all()
    keys = await _keys(s, [g.criterion_id for g in rows])
    return [
        GapOut(
            id=g.id,
            criterion_key=keys.get(g.criterion_id) if g.criterion_id else None,
            title=g.title,
            detail=g.detail,
            assignee_role=g.assignee_role.value,
            status=g.status,
        )
        for g in rows
    ]


@router.patch("/gaps/{gap_id}")
async def update_gap(gap_id: uuid.UUID, body: GapPatch, user: Reviewer, s: Session) -> GapOut:
    gap = await s.get(GapTask, gap_id)
    if gap is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Gap not found")
    await _case(s, gap.case_id, user)
    before = gap.status
    gap.status = body.status
    await audit.append(
        s,
        actor_id=user.sub,
        action="gap.update",
        entity="gap_task",
        entity_id=str(gap.id),
        before={"status": before},
        after={"status": body.status},
    )
    await s.commit()
    keys = await _keys(s, [gap.criterion_id])
    return GapOut(
        id=gap.id,
        criterion_key=keys.get(gap.criterion_id) if gap.criterion_id else None,
        title=gap.title,
        detail=gap.detail,
        assignee_role=gap.assignee_role.value,
        status=gap.status,
    )


@router.patch("/verdicts/{verdict_id}")
async def override_verdict(
    verdict_id: uuid.UUID, body: VerdictPatch, user: Reviewer, s: Session
) -> ResumeOut:
    """Human override (PRODUCT §4.9): audited, and the case's readiness is recomputed."""
    v = await s.get(EvidenceVerdict, verdict_id)
    if v is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Verdict not found")
    run = await _run(s, v.run_id, user)
    before = {
        "verdict": v.verdict.value,
        "overridden_by": str(v.overridden_by) if v.overridden_by else None,
    }
    v.verdict, v.overridden_by, v.override_reason = Verdict(body.verdict), user.sub, body.reason
    await audit.append(
        s,
        actor_id=user.sub,
        action="verdict.override",
        entity="evidence_verdict",
        entity_id=str(v.id),
        before=before,
        after={"verdict": body.verdict, "reason": body.reason},
    )
    case = await s.get(Case, run.case_id)
    assert case is not None
    if case.policy_version_id and (pv := await s.get(PolicyVersion, case.policy_version_id)):
        tree = await policies.load_tree(s, pv)
        rows = (
            (
                await s.execute(
                    select(CriteriaNode.key, EvidenceVerdict.verdict)
                    .join(EvidenceVerdict, EvidenceVerdict.criterion_id == CriteriaNode.id)
                    .where(EvidenceVerdict.run_id == run.id)
                )
            )
            .tuples()
            .all()
        )
        logic = evaluate(tree.root, {k: vv.value for k, vv in rows})
        case.readiness_score = readiness(tree, logic)
    await s.commit()
    return ResumeOut(case_status=case.status.value)


@router.post("/runs/{run_id}/resume")
async def resume_run(run_id: uuid.UUID, body: ResumeIn, user: Approver, s: Session) -> ResumeOut:
    """The human-review interrupt: nothing is submitted without this (PRODUCT §4.9)."""
    run = await _run(s, run_id, user)
    if run.status != "finished":
        raise HTTPException(status.HTTP_409_CONFLICT, "Run is not finished")
    case = await s.get(Case, run.case_id)
    assert case is not None
    latest = await s.scalar(
        select(Run.id).where(Run.case_id == case.id).order_by(Run.started_at.desc()).limit(1)
    )
    if latest != run.id:
        raise HTTPException(status.HTTP_409_CONFLICT, "A newer run exists for this case")
    high = (
        await s.scalars(
            select(Objection.id).where(
                Objection.run_id == run.id,
                Objection.severity == "high",
                Objection.status != ObjectionStatus.rebutted,
            )
        )
    ).all()
    if body.decision == "approve" and high and not body.acknowledge_high:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"{len(high)} high-severity objection(s) are not rebutted; acknowledge them to approve",
        )
    not_ready = (case.readiness_score or 0.0) < 1.0
    if body.decision == "approve" and not_ready and not body.acknowledge_not_ready:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "The case is not ready (coverage criteria unproven); acknowledge to approve anyway",
        )
    before = case.status.value
    case.status = CaseStatus.ready if body.decision == "approve" else CaseStatus.new
    await audit.append(
        s,
        actor_id=user.sub,
        action=f"run.{body.decision}",
        entity="run",
        entity_id=str(run.id),
        before={"case_status": before},
        after={
            "case_status": case.status.value,
            "acknowledged_high": [str(h) for h in high] if body.acknowledge_high else [],
            "acknowledged_not_ready": not_ready and body.acknowledge_not_ready,
            "readiness": case.readiness_score,
        },
    )
    await s.commit()
    return ResumeOut(case_status=case.status.value)
