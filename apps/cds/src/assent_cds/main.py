"""CDS Hooks service (ARCHITECTURE §5): prior-auth guidance at the moment an order is signed.

`order-sign` reads the draft ServiceRequest's CPT, finds the approved coverage policy, and returns
a card: what the payer will require, plus readiness and open gaps when Assent already has a case
for this patient. Fast and deterministic: no LLM call on the clinician's critical path.

Run: `uv run uvicorn assent_cds.main:app --port 8010`
"""

from typing import Any

from fastapi import FastAPI
from sqlalchemy import select

from assent_api.db import SessionLocal
from assent_api.models import Case, GapTask, Patient
from assent_api.services import policies

FAMILY_BY_CPT = {"64479": "esi", "64483": "esi", "64582": "hgns", "22513": "pva", "22514": "pva"}
APP_URL = "http://localhost:3000"
SERVICE = {
    "hook": "order-sign",
    "id": "assent-order-sign",
    "title": "Assent prior authorization check",
    "description": "Flags Medicare prior authorization requirements and documentation gaps.",
    "prefetch": {"patient": "Patient/{{context.patientId}}"},
}

app = FastAPI(title="Assent CDS Hooks")


@app.get("/cds-services")
def discovery() -> dict[str, Any]:
    return {"services": [SERVICE]}


def _cpts(context: dict[str, Any]) -> list[str]:
    orders = context.get("draftOrders", {}).get("entry", [])
    return [
        c["code"]
        for e in orders
        if e.get("resource", {}).get("resourceType") == "ServiceRequest"
        for c in e["resource"].get("code", {}).get("coding", [])
        if c.get("code") in FAMILY_BY_CPT
    ]


@app.post("/cds-services/assent-order-sign")
async def order_sign(req: dict[str, Any]) -> dict[str, Any]:
    context = req.get("context", {})
    cards = []
    async with SessionLocal() as s:
        for cpt in _cpts(context):
            family = FAMILY_BY_CPT[cpt]
            pv = await policies.approved_version_for(s, family)
            if pv is None:
                continue
            tree = await policies.load_tree(s, pv)
            patient = await s.scalar(
                select(Patient).where(Patient.fhir_id == str(context.get("patientId", "")))
            )
            case = (
                await s.scalar(
                    select(Case)
                    .where(Case.patient_id == patient.id, Case.service_family == family)
                    .order_by(Case.created_at.desc())
                    .limit(1)
                )
                if patient
                else None
            )
            checklist = "\n".join(f"- {n.label}" for n in tree.leaves())
            detail = f"**Coverage policy {tree.source_id} v{tree.version} requires:**\n{checklist}"
            indicator, links = "warning", []
            if case is not None:
                gaps = (
                    await s.scalars(
                        select(GapTask.title).where(
                            GapTask.case_id == case.id, GapTask.status == "open"
                        )
                    )
                ).all()
                ready = (case.readiness_score or 0) >= 1.0
                indicator = "info" if ready and not gaps else "warning"
                pct = round((case.readiness_score or 0) * 100)
                detail = (
                    f"**Readiness {pct}%** (case status: {case.status.value}).\n"
                    + (
                        "**Open documentation gaps:**\n"
                        + "\n".join(f"- {g}" for g in gaps)
                        + "\n\n"
                        if gaps
                        else "\n"
                    )
                    + detail
                )
                links = [
                    {
                        "label": "Open the case in Assent",
                        "url": f"{APP_URL}/app/cases/{case.id}",
                        "type": "absolute",
                    }
                ]
            cards.append(
                {
                    "summary": f"Prior authorization required for CPT {cpt} "
                    f"(Medicare {tree.source_id})",
                    "indicator": indicator,
                    "detail": detail,
                    "source": {"label": "Assent"},
                    "links": links,
                }
            )
    return {"cards": cards}
