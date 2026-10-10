import uuid
from collections.abc import AsyncIterator
from datetime import date, datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select

from assent_api import queue
from assent_api.db import redis
from assent_api.deps import CurrentUser, Session, require_role
from assent_api.models import (
    Case,
    ChartChunk,
    CriteriaNode,
    EvidenceCitation,
    EvidenceVerdict,
    Patient,
    Policy,
    PolicyVersion,
    Role,
    Run,
    RunStep,
)
from assent_api.security import TokenClaims
from assent_api.services import run_bus

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
    criterion_key: str
    verdict: str
    confidence: float
    rationale: str
    citations: list[CitationOut]


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
            .where(ChartChunk.case_id == case_id)
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
            criterion_key=key,
            verdict=v.verdict.value,
            confidence=v.confidence,
            rationale=v.rationale,
            citations=by_verdict.get(v.id, []),
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
