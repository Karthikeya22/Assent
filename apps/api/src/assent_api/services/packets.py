"""Packets: PAS Bundle + PDF from an approved run, payer submission, and appeal resubmission."""

import base64
import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any

import httpx
from fpdf import FPDF
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from assent_api.models import (
    Case,
    CaseStatus,
    ChartChunk,
    CriteriaNode,
    EvidenceCitation,
    EvidenceVerdict,
    Packet,
    Patient,
    PolicyVersion,
    Run,
    Submission,
    Verdict,
)
from assent_api.settings import get_settings
from assent_fhir.pas import Evidence, PasInput, build_pas_bundle, validate_pas

CPT_TEXT = {
    "64479": "Transforaminal epidural steroid injection, cervical/thoracic",
    "64483": "Transforaminal epidural steroid injection, lumbar/sacral",
    "64582": "Hypoglossal nerve neurostimulator implantation",
    "22513": "Percutaneous vertebral augmentation (kyphoplasty), thoracic",
    "22514": "Percutaneous vertebral augmentation (kyphoplasty), lumbar",
}
PAYER = "Medicare Part B (MAC)"
DENIED_KEY = "http://assent.dev/fhir/denied-criterion"


async def run_evidence(s: AsyncSession, run_id: uuid.UUID) -> list[tuple[Evidence, str]]:
    """(evidence, chunk id) for every verified citation behind a `met` verdict of the run."""
    rows = (
        await s.execute(
            select(CriteriaNode, EvidenceCitation, ChartChunk)
            .join(EvidenceVerdict, EvidenceVerdict.criterion_id == CriteriaNode.id)
            .join(EvidenceCitation, EvidenceCitation.verdict_id == EvidenceVerdict.id)
            .join(ChartChunk, ChartChunk.id == EvidenceCitation.chunk_id)
            .where(
                EvidenceVerdict.run_id == run_id,
                EvidenceVerdict.verdict == Verdict.met,
                EvidenceCitation.verbatim_ok.is_(True),
                EvidenceCitation.entailment_score >= 0.7,
            )
            .order_by(CriteriaNode.order_index)
        )
    ).all()
    return [
        (
            Evidence(
                n.key,
                n.label,
                c.quote,
                ch.fhir_resource_type,
                ch.effective_date.date() if ch.effective_date else None,
            ),
            str(ch.id),
        )
        for n, c, ch in rows
    ]


def letter(case: Case, policy: str, evidence: list[Evidence]) -> str:
    lines = [
        f"Re: Prior authorization request for {CPT_TEXT.get(case.cpt_codes[0], case.cpt_codes[0])} "
        f"(CPT {case.cpt_codes[0]}, ICD-10 {case.icd10_codes[0]}), coverage policy {policy}.",
        "",
        "The medical record documents each coverage criterion as follows:",
    ]
    for e in evidence:
        when = f", {e.source_date:%m/%d/%Y}" if e.source_date else ""
        lines.append(f'- {e.criterion_label}: "{e.quote}" ({e.source_type}{when})')
    lines += ["", "Each excerpt is quoted verbatim from the chart and attached as a document."]
    return "\n".join(lines)


async def pas_input(
    s: AsyncSession, case: Case, claim_id: str, evidence: list[Evidence], text: str
) -> PasInput:
    patient = await s.get(Patient, case.patient_id)
    pv = await s.get(PolicyVersion, case.policy_version_id) if case.policy_version_id else None
    assert patient is not None
    return PasInput(
        claim_id=claim_id,
        patient_name=patient.display_name_synthetic,
        birth_year=patient.birth_year,
        sex=patient.sex,
        member_id=f"MBI-{str(patient.id)[:8].upper()}",  # synthetic Medicare beneficiary id
        payer=PAYER,
        provider="Assent Demo Clinic",
        cpt=case.cpt_codes[0],
        cpt_text=CPT_TEXT.get(case.cpt_codes[0], case.cpt_codes[0]),
        icd10=case.icd10_codes[0],
        service_date=date.today() + timedelta(days=14),
        policy=await _policy_label(s, pv),
        letter=text,
        evidence=evidence,
    )


async def _policy_label(s: AsyncSession, pv: PolicyVersion | None) -> str:
    if pv is None:
        return "unspecified"
    from assent_api.models import Policy

    policy = await s.get(Policy, pv.policy_id)
    return f"{policy.source_id if policy else '?'} v{pv.version}"


async def build(s: AsyncSession, run: Run, case: Case, user_id: uuid.UUID) -> Packet:
    ev = [e for e, _ in await run_evidence(s, run.id)]
    pv = await s.get(PolicyVersion, case.policy_version_id) if case.policy_version_id else None
    packet_id = uuid.uuid4()
    p = await pas_input(s, case, str(packet_id), ev, letter(case, await _policy_label(s, pv), ev))
    bundle = build_pas_bundle(p)
    if errs := validate_pas(bundle):
        raise ValueError("; ".join(errs))
    packet = Packet(
        id=packet_id, case_id=case.id, run_id=run.id, fhir_bundle_json=bundle, created_by=user_id
    )
    s.add(packet)
    await s.flush()
    return packet


def _latin1(text: str) -> str:
    """fpdf2 core fonts are Latin-1; map the few clinical symbols we emit."""
    table = {
        "≥": ">=",
        "≤": "<=",
        "–": "-",  # noqa: RUF001
        "—": "-",
        "’": "'",  # noqa: RUF001
        "‘": "'",  # noqa: RUF001
        "“": '"',
        "”": '"',
    }
    return "".join(table.get(ch, ch) for ch in text).encode("latin-1", "replace").decode("latin-1")


def pdf(bundle: dict[str, Any]) -> bytes:
    res = [e["resource"] for e in bundle["entry"]]
    claim = next(r for r in res if r["resourceType"] == "Claim")
    patient = next(r for r in res if r["resourceType"] == "Patient")
    letter_doc = next(
        r for r in res if r["resourceType"] == "DocumentReference" and not r.get("category")
    )
    item = claim["item"][0]["productOrService"]["coding"][0]
    dx = claim["diagnosis"][0]["diagnosisCodeableConcept"]["coding"][0]["code"]
    doc = FPDF()
    doc.add_page()
    doc.set_font("Helvetica", "B", 15)
    doc.cell(0, 10, "Prior Authorization Request", new_x="LMARGIN", new_y="NEXT")
    doc.set_font("Helvetica", size=10)
    head = (
        f"Patient: {patient['name'][0]['text']} (born {patient['birthDate']}, {patient['gender']})"
        f"\nService: {item.get('display', '')} - CPT {item['code']}"
        f"\nDiagnosis: ICD-10 {dx}"
        f"\nClaim: {claim['id']}   Policy: {claim['extension'][0]['valueString']}"
        "\nSYNTHETIC DATA - NOT A REAL PATIENT"
    )
    doc.multi_cell(0, 5, _latin1(head))
    doc.ln(4)
    body = base64.b64decode(letter_doc["content"][0]["attachment"]["data"]).decode()
    doc.multi_cell(0, 5, _latin1(body))
    return bytes(doc.output())


async def submit(s: AsyncSession, packet: Packet, case: Case) -> Submission:
    url = f"{get_settings().payer_url}/fhir/Claim/$submit"
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(url, json=packet.fhir_bundle_json)
    r.raise_for_status()
    sub = Submission(packet_id=packet.id, payer_endpoint=url)
    apply_response(sub, case, r.json())
    s.add(sub)
    await s.flush()
    return sub


async def poll(s: AsyncSession, sub: Submission, case: Case) -> None:
    """Refresh a pended submission from the payer."""
    if sub.response_status != "A4" or not sub.claim_response_json:
        return
    base = get_settings().payer_url
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(f"{base}/fhir/ClaimResponse/{sub.claim_response_json['id']}")
    if r.status_code == 200:
        apply_response(sub, case, r.json())


def apply_response(sub: Submission, case: Case, resp: dict[str, Any]) -> None:
    action = resp["extension"][0]["valueCodeableConcept"]["coding"][0]["code"]
    sub.response_status, sub.claim_response_json = action, resp
    errs = resp.get("error", [])
    codes = sorted({e["code"]["coding"][0]["code"] for e in errs})  # column is 32 chars
    sub.denial_reason_code = ",".join(codes)[:32] or None
    sub.denial_reason_text = " ".join(e["code"].get("text", "") for e in errs) or None
    case.status = {"A1": CaseStatus.approved, "A3": CaseStatus.denied}.get(
        action, CaseStatus.submitted
    )
    case.updated_at = datetime.now(UTC)


def denied(resp: dict[str, Any]) -> list[tuple[str, str]]:
    """(criterion key, payer reason) for each denial line that names a criterion."""
    out = []
    for e in resp.get("error", []):
        key = next(
            (x["valueString"] for x in e.get("extension", []) if x["url"] == DENIED_KEY), None
        )
        if key:
            out.append((key, e["code"].get("text", "")))
    return out
