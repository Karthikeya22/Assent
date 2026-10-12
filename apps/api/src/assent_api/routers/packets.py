"""Packets, payer submissions and appeals (ARCHITECTURE §5). Humans approve every send."""

import base64
import uuid
from datetime import UTC, date, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from assent_api import queue
from assent_api.deps import Session, require_role
from assent_api.models import Appeal, Case, CaseStatus, ChartChunk, Packet, Role, Submission
from assent_api.routers.runs import _case, _run
from assent_api.security import TokenClaims
from assent_api.services import audit, packets
from assent_fhir.pas import Evidence, build_pas_bundle, bundle_evidence, validate_pas

router = APIRouter(prefix="/api/v1", tags=["packets"])
Editor = Annotated[
    TokenClaims, Depends(require_role(Role.coordinator, Role.clinician, Role.policy_admin))
]
Approver = Annotated[TokenClaims, Depends(require_role(Role.coordinator, Role.policy_admin))]


class EvidenceOut(BaseModel):
    criterion_key: str
    criterion_label: str
    quote: str
    source_type: str
    source_date: date | None


class DenialOut(BaseModel):
    criterion_key: str
    reason: str


class AppealOut(BaseModel):
    id: uuid.UUID
    submission_id: uuid.UUID
    status: str  # drafting | draft | failed | sent
    draft_text: str
    citations: dict[str, list[dict[str, Any]]]
    sent_at: datetime | None


class SubmissionOut(BaseModel):
    id: uuid.UUID
    packet_id: uuid.UUID
    submitted_at: datetime
    status: str  # A1 certified | A3 not certified | A4 pended
    disposition: str
    pre_auth_ref: str | None
    denials: list[DenialOut]
    appeal: AppealOut | None = None


class PacketOut(BaseModel):
    id: uuid.UUID
    case_id: uuid.UUID
    run_id: uuid.UUID
    created_at: datetime | None = None
    approved_at: datetime | None
    letter: str
    evidence: list[EvidenceOut]
    validation_errors: list[str]
    submissions: list[SubmissionOut] = []


class AppealPatch(BaseModel):
    draft_text: str = Field(min_length=20, max_length=20000)


def _letter(bundle: dict[str, Any]) -> str:
    doc = next(
        e["resource"]
        for e in bundle["entry"]
        if e["resource"]["resourceType"] == "DocumentReference"
        and not e["resource"].get("category")
    )
    return base64.b64decode(doc["content"][0]["attachment"]["data"]).decode()


def _appeal_out(a: Appeal) -> AppealOut:
    return AppealOut(
        id=a.id,
        submission_id=a.submission_id,
        status=a.status,
        draft_text=a.draft_text,
        citations=a.citations_json or {},
        sent_at=a.sent_at,
    )


async def _sub_out(s: Session, sub: Submission) -> SubmissionOut:
    resp = sub.claim_response_json or {}
    appeal = await s.scalar(select(Appeal).where(Appeal.submission_id == sub.id))
    return SubmissionOut(
        id=sub.id,
        packet_id=sub.packet_id,
        submitted_at=sub.submitted_at,
        status=sub.response_status or "?",
        disposition=resp.get("disposition", ""),
        pre_auth_ref=resp.get("preAuthRef"),
        denials=[DenialOut(criterion_key=k, reason=r) for k, r in packets.denied(resp)],
        appeal=_appeal_out(appeal) if appeal else None,
    )


async def _packet_out(s: Session, p: Packet) -> PacketOut:
    subs = (
        await s.scalars(
            select(Submission).where(Submission.packet_id == p.id).order_by(Submission.submitted_at)
        )
    ).all()
    return PacketOut(
        id=p.id,
        case_id=p.case_id,
        run_id=p.run_id,
        approved_at=p.approved_at,
        letter=_letter(p.fhir_bundle_json),
        evidence=[EvidenceOut(**e.__dict__) for e in bundle_evidence(p.fhir_bundle_json)],
        validation_errors=validate_pas(p.fhir_bundle_json),
        submissions=[await _sub_out(s, x) for x in subs],
    )


async def _packet(s: Session, packet_id: uuid.UUID, user: TokenClaims) -> tuple[Packet, Case]:
    p = await s.get(Packet, packet_id)
    if p is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Packet not found")
    return p, await _case(s, p.case_id, user)


async def _submission(
    s: Session, sub_id: uuid.UUID, user: TokenClaims
) -> tuple[Submission, Packet, Case]:
    sub = await s.get(Submission, sub_id)
    if sub is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Submission not found")
    p, case = await _packet(s, sub.packet_id, user)
    return sub, p, case


@router.post("/runs/{run_id}/packet", status_code=status.HTTP_201_CREATED)
async def build_packet(run_id: uuid.UUID, user: Editor, s: Session) -> PacketOut:
    run = await _run(s, run_id, user)
    case = await s.get(Case, run.case_id)
    assert case is not None
    if case.status != CaseStatus.ready:
        raise HTTPException(status.HTTP_409_CONFLICT, "Approve the run before building a packet")
    try:
        p = await packets.build(s, run, case, user.sub)
    except ValueError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(e)) from e
    await audit.append(
        s,
        actor_id=user.sub,
        action="packet.build",
        entity="packet",
        entity_id=str(p.id),
        after={"run_id": str(run.id), "evidence": len(bundle_evidence(p.fhir_bundle_json))},
    )
    await s.commit()
    return await _packet_out(s, p)


@router.get("/cases/{case_id}/packets")
async def case_packets(case_id: uuid.UUID, user: Editor, s: Session) -> list[PacketOut]:
    await _case(s, case_id, user)
    rows = (await s.scalars(select(Packet).where(Packet.case_id == case_id))).all()
    out = [await _packet_out(s, p) for p in rows]
    return sorted(
        out,
        key=lambda p: (
            p.submissions[0].submitted_at if p.submissions else datetime.max.replace(tzinfo=UTC)
        ),
    )


@router.get("/packets/{packet_id}", response_model=None)
async def get_packet(
    packet_id: uuid.UUID, user: Editor, s: Session, format: str = "json"
) -> PacketOut | Response:
    p, _ = await _packet(s, packet_id, user)
    if format == "pdf":
        return Response(
            packets.pdf(p.fhir_bundle_json),
            media_type="application/pdf",
            headers={"Content-Disposition": f'inline; filename="packet-{p.id}.pdf"'},
        )
    return await _packet_out(s, p)


@router.post("/packets/{packet_id}/approve")
async def approve_packet(packet_id: uuid.UUID, user: Approver, s: Session) -> PacketOut:
    p, _ = await _packet(s, packet_id, user)
    if errs := validate_pas(p.fhir_bundle_json):
        raise HTTPException(status.HTTP_409_CONFLICT, f"Packet is invalid: {'; '.join(errs)}")
    p.approved_by, p.approved_at = user.sub, datetime.now(UTC)
    await audit.append(
        s, actor_id=user.sub, action="packet.approve", entity="packet", entity_id=str(p.id)
    )
    await s.commit()
    return await _packet_out(s, p)


@router.post("/packets/{packet_id}/submit")
async def submit_packet(packet_id: uuid.UUID, user: Approver, s: Session) -> SubmissionOut:
    p, case = await _packet(s, packet_id, user)
    if p.approved_at is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "A human must approve the packet first")
    if await s.scalar(select(Submission.id).where(Submission.packet_id == p.id)):
        raise HTTPException(status.HTTP_409_CONFLICT, "This packet was already submitted")
    sub = await packets.submit(s, p, case)
    await audit.append(
        s,
        actor_id=user.sub,
        action="packet.submit",
        entity="submission",
        entity_id=str(sub.id),
        after={"packet_id": str(p.id), "status": sub.response_status},
    )
    await s.commit()
    return await _sub_out(s, sub)


@router.get("/submissions/{submission_id}")
async def get_submission(submission_id: uuid.UUID, user: Editor, s: Session) -> SubmissionOut:
    sub, _, case = await _submission(s, submission_id, user)
    await packets.poll(s, sub, case)
    await s.commit()
    return await _sub_out(s, sub)


@router.post("/submissions/{submission_id}/appeal", status_code=status.HTTP_202_ACCEPTED)
async def start_appeal(submission_id: uuid.UUID, user: Editor, s: Session) -> AppealOut:
    sub, _, case = await _submission(s, submission_id, user)
    if sub.response_status != "A3":
        raise HTTPException(status.HTTP_409_CONFLICT, "Only a denial can be appealed")
    if not packets.denied(sub.claim_response_json or {}):
        raise HTTPException(status.HTTP_409_CONFLICT, "The denial names no criterion to appeal")
    if await s.scalar(select(Appeal.id).where(Appeal.submission_id == sub.id)):
        raise HTTPException(status.HTTP_409_CONFLICT, "An appeal already exists for this denial")
    a = Appeal(submission_id=sub.id, draft_text="", citations_json={}, status="drafting")
    s.add(a)
    case.status = CaseStatus.appealed
    await s.flush()
    await audit.append(
        s, actor_id=user.sub, action="appeal.start", entity="appeal", entity_id=str(a.id)
    )
    await s.commit()
    await queue.enqueue("appeal_job", str(a.id))
    return _appeal_out(a)


async def _appeal(
    s: Session, appeal_id: uuid.UUID, user: TokenClaims
) -> tuple[Appeal, Submission, Packet, Case]:
    a = await s.get(Appeal, appeal_id)
    if a is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Appeal not found")
    sub, p, case = await _submission(s, a.submission_id, user)
    return a, sub, p, case


@router.get("/appeals/{appeal_id}")
async def get_appeal(appeal_id: uuid.UUID, user: Editor, s: Session) -> AppealOut:
    return _appeal_out((await _appeal(s, appeal_id, user))[0])


@router.patch("/appeals/{appeal_id}")
async def edit_appeal(
    appeal_id: uuid.UUID, body: AppealPatch, user: Editor, s: Session
) -> AppealOut:
    a, *_ = await _appeal(s, appeal_id, user)
    if a.status != "draft":
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"Appeal is {a.status}, not an editable draft"
        )
    before = a.draft_text
    a.draft_text = body.draft_text
    await audit.append(
        s,
        actor_id=user.sub,
        action="appeal.edit",
        entity="appeal",
        entity_id=str(a.id),
        before={"chars": len(before)},
        after={"chars": len(a.draft_text)},
    )
    await s.commit()
    return _appeal_out(a)


@router.post("/appeals/{appeal_id}/send")
async def send_appeal(appeal_id: uuid.UUID, user: Approver, s: Session) -> SubmissionOut:
    """Resubmit: original evidence + the appeal's verified excerpts + the appeal letter."""
    a, _, p, case = await _appeal(s, appeal_id, user)
    if a.status != "draft":
        raise HTTPException(status.HTTP_409_CONFLICT, f"Appeal is {a.status}, not a draft")
    added = []
    for key, cites in (a.citations_json or {}).items():
        for c in cites:
            chunk = await s.get(ChartChunk, uuid.UUID(c["chunk_id"]))
            added.append(
                Evidence(
                    key,
                    c.get("criterion_label", key),
                    c["quote"],
                    chunk.fhir_resource_type if chunk else "DocumentReference",
                    chunk.effective_date.date() if chunk and chunk.effective_date else None,
                )
            )
    new_id = uuid.uuid4()
    inp = await packets.pas_input(
        s, case, str(new_id), bundle_evidence(p.fhir_bundle_json) + added, a.draft_text
    )
    bundle = build_pas_bundle(inp)
    now = datetime.now(UTC)
    p2 = Packet(
        id=new_id,
        case_id=case.id,
        run_id=p.run_id,
        fhir_bundle_json=bundle,
        created_by=user.sub,
        approved_by=user.sub,
        approved_at=now,
    )
    s.add(p2)
    await s.flush()
    sub = await packets.submit(s, p2, case)
    a.status, a.sent_at = "sent", now
    await audit.append(
        s,
        actor_id=user.sub,
        action="appeal.send",
        entity="appeal",
        entity_id=str(a.id),
        after={
            "packet_id": str(p2.id),
            "added_evidence": len(added),
            "status": sub.response_status,
        },
    )
    await s.commit()
    return await _sub_out(s, sub)
