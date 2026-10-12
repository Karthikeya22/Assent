"""Inject a case's resources (coded facts + notes) into the patient's Synthea transaction bundle."""

import base64
import uuid
from datetime import date, timedelta
from typing import Any

from assent_evals.synth.case import CaseFacts, Facts
from assent_evals.synth.facts import EsiFacts
from assent_evals.synth.notes import Note

NS = uuid.UUID("6f1c3a52-7d0e-4c4f-9a5e-0a55e47a55e7")  # stable ids → byte-stable bundles
ICD10 = "http://hl7.org/fhir/sid/icd-10-cm"
CPT = "http://www.ama-assn.org/go/cpt"
LOINC = "http://loinc.org"
SNOMED = "http://snomed.info/sct"
DX_TEXT = {
    "M54.16": "Radiculopathy, lumbar region",
    "M54.12": "Radiculopathy, cervical region",
    "M96.1": "Postlaminectomy syndrome, not elsewhere classified",
    "B02.29": "Other postherpetic nervous system involvement",
    "M54.50": "Low back pain, unspecified",
}


def _entry(case_id: str, kind: str, n: int, resource: dict[str, Any]) -> dict[str, Any]:
    rid = str(uuid.uuid5(NS, f"{case_id}/{kind}/{n}"))
    resource = {"resourceType": kind, "id": rid, **resource}
    return {
        "fullUrl": f"urn:uuid:{rid}",
        "resource": resource,
        "request": {"method": "POST", "url": kind},
    }


def _code(system: str, code: str, display: str) -> dict[str, Any]:
    return {"coding": [{"system": system, "code": code, "display": display}], "text": display}


def case_resources(f: EsiFacts, notes: list[Note], patient_ref: str) -> list[dict[str, Any]]:
    subj = {"reference": patient_ref}
    out: list[dict[str, Any]] = []
    g = f.gold

    def add(kind: str, res: dict[str, Any]) -> None:
        out.append(_entry(f.case_id, kind, len(out), {**res, "subject": subj}))

    # The order under review is always present: payers see it with every request.
    add(
        "ServiceRequest",
        {
            "status": "active",
            "intent": "order",
            "authoredOn": f.order_date.isoformat(),
            "code": _code(CPT, f.cpt, f"Transforaminal epidural steroid injection, {f.region}"),
            "reasonCode": [_code(ICD10, f.icd10, DX_TEXT[f.icd10])],
        },
    )
    # Prior ESIs are claims-visible, so they are coded even in buried cases.
    for d in f.prior_esi_dates if g["freq"] != "insufficient" else []:
        add(
            "Procedure",
            {
                "status": "completed",
                "performedDateTime": d.isoformat(),
                "code": _code(CPT, f.cpt, "Epidural steroid injection"),
            },
        )

    if f.structured:
        if (
            any(g[k] == "met" for k in ("dx.radic", "dx.pls", "dx.zoster"))
            or f.condition == "nonspecific"
        ):
            add(
                "Condition",
                {
                    "clinicalStatus": _code(
                        "http://terminology.hl7.org/CodeSystem/condition-clinical",
                        "active",
                        "Active",
                    ),
                    "code": _code(ICD10, f.icd10, DX_TEXT[f.icd10]),
                    "onsetDateTime": f.onset_date.isoformat(),
                    "recordedDate": f.slot_dates()["consult"].isoformat(),
                },
            )
        img = next((s for s in f.statements if s.leaf == "dx.imaging"), None)
        if img:
            add(
                "DiagnosticReport",
                {
                    "status": "final",
                    "effectiveDateTime": f.imaging_date.isoformat(),
                    "code": _code(
                        LOINC,
                        "24590-2" if f.region == "lumbar" else "24589-4",
                        f"{f.imaging_modality} {f.region} spine",
                    ),
                    "conclusion": img.text,
                },
            )
        if g["sev.baseline"] == "met":
            add(
                "Observation",
                {
                    "status": "final",
                    "effectiveDateTime": f.slot_dates()["consult"].isoformat(),
                    "code": _code(LOINC, "72514-3", f"{f.scale_name} pain/function score"),
                    "valueString": f.scale_value,
                },
            )
        if g["dur.conservative"] == "met":
            add(
                "Procedure",
                {
                    "status": "completed",
                    "performedPeriod": {
                        "start": f.pt_start.isoformat(),
                        "end": (f.pt_start + timedelta(weeks=f.pt_weeks)).isoformat(),
                    },
                    "code": _code(SNOMED, "91251008", "Physical therapy procedure"),
                },
            )
            add(
                "MedicationRequest",
                {
                    "status": "completed",
                    "intent": "order",
                    "authoredOn": (f.pt_start - timedelta(days=3)).isoformat(),
                    "medicationCodeableConcept": {"text": f.nsaid},
                },
            )

    _add_notes(add, notes)
    return out


def generic_resources(f: CaseFacts, notes: list[Note], patient_ref: str) -> list[dict[str, Any]]:
    """HGNS/PVA: the order, then (clean cases only) the coded diagnosis and numeric facts."""
    subj = {"reference": patient_ref}
    out: list[dict[str, Any]] = []

    def add(kind: str, res: dict[str, Any]) -> None:
        out.append(_entry(f.case_id, kind, len(out), {**res, "subject": subj}))

    add(
        "ServiceRequest",
        {
            "status": "active",
            "intent": "order",
            "authoredOn": f.order_date.isoformat(),
            "code": _code(CPT, f.cpt, f.cpt_text),
            "reasonCode": [_code(ICD10, f.icd10, f.icd10_text)],
        },
    )
    if f.structured:
        add(
            "Condition",
            {
                "clinicalStatus": _code(
                    "http://terminology.hl7.org/CodeSystem/condition-clinical", "active", "Active"
                ),
                "code": _code(ICD10, f.icd10, f.icd10_text),
                "recordedDate": f.order_date.isoformat(),
            },
        )
        for o in f.observations:
            add(
                "Observation",
                {
                    "status": "final",
                    "effectiveDateTime": o.date.isoformat(),
                    "code": _code(o.system, o.code, o.display),
                    "valueQuantity": {"value": o.value, "unit": o.unit},
                },
            )
    _add_notes(add, notes)
    return out


def _add_notes(add: Any, notes: list[Note]) -> None:
    for note in notes:
        add(
            "DocumentReference",
            {
                "status": "current",
                "date": f"{note.date.isoformat()}T09:00:00Z",
                "type": {"text": note.title},
                "author": [{"display": note.author}],
                "content": [
                    {
                        "attachment": {
                            "contentType": "text/plain",
                            "data": base64.b64encode(note.text.encode()).decode(),
                            "title": note.title,
                        }
                    }
                ],
            },
        )


def inject(bundle: dict[str, Any], f: Facts, notes: list[Note]) -> dict[str, Any]:
    patient = next(e for e in bundle["entry"] if e["resource"]["resourceType"] == "Patient")
    ref = patient["fullUrl"]
    extra = (
        case_resources(f, notes, ref)
        if isinstance(f, EsiFacts)
        else generic_resources(f, notes, ref)
    )
    return {**bundle, "entry": bundle["entry"] + extra}


def age_on(birth: date, on: date) -> int:
    return on.year - birth.year - ((on.month, on.day) < (birth.month, birth.day))
