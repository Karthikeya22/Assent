"""Da Vinci PAS-style prior authorization Bundle: Claim(use=preauthorization) + evidence.

Each verified citation becomes a DocumentReference linked from `Claim.supportingInfo`, tagged
with the criterion it supports, so a reviewer (or the mock payer) can check criterion by criterion.
shortcut: `validate_pas` checks the elements we rely on; swap in HAPI `$validate` at deploy.
"""

import base64
import uuid
from dataclasses import dataclass
from datetime import date
from typing import Any

CPT = "http://www.ama-assn.org/go/cpt"
ICD10 = "http://hl7.org/fhir/sid/icd-10-cm"
SUPPORT = "http://hl7.org/us/davinci-pas/CodeSystem/PASSupportingInfoType"
CRITERION = "http://assent.dev/fhir/CodeSystem/criterion"
NS = uuid.UUID("0c3f5f53-5a2e-4f7a-9f0e-6d3c1b2a9e10")


@dataclass(frozen=True)
class Evidence:
    criterion_key: str
    criterion_label: str
    quote: str
    source_type: str  # e.g. "DocumentReference" (a note) or "DiagnosticReport"
    source_date: date | None


@dataclass(frozen=True)
class PasInput:
    claim_id: str
    patient_name: str
    birth_year: int
    sex: str
    member_id: str
    payer: str
    provider: str
    cpt: str
    cpt_text: str
    icd10: str
    service_date: date
    policy: str  # e.g. "L39240 v15"
    letter: str
    evidence: list[Evidence]


def _b64(text: str) -> str:
    return base64.b64encode(text.encode()).decode()


def _id(claim_id: str, kind: str, n: int = 0) -> str:
    return str(uuid.uuid5(NS, f"{claim_id}/{kind}/{n}"))


def build_pas_bundle(p: PasInput) -> dict[str, Any]:
    pid, cov, org, ins = (_id(p.claim_id, k) for k in ("Patient", "Coverage", "Org", "Payer"))
    res: list[dict[str, Any]] = [
        {
            "resourceType": "Patient",
            "id": pid,
            "name": [{"text": p.patient_name}],
            "gender": p.sex,
            "birthDate": str(p.birth_year),
        },
        {"resourceType": "Organization", "id": org, "name": p.provider},
        {"resourceType": "Organization", "id": ins, "name": p.payer},
        {
            "resourceType": "Coverage",
            "id": cov,
            "status": "active",
            "subscriberId": p.member_id,
            "beneficiary": {"reference": f"Patient/{pid}"},
            "payor": [{"reference": f"Organization/{ins}"}],
        },
    ]
    docs = []
    letter_id = _id(p.claim_id, "Letter")
    res.append(
        {
            "resourceType": "DocumentReference",
            "id": letter_id,
            "status": "current",
            "type": {"text": "Letter of medical necessity"},
            "subject": {"reference": f"Patient/{pid}"},
            "content": [{"attachment": {"contentType": "text/plain", "data": _b64(p.letter)}}],
        }
    )
    for i, e in enumerate(p.evidence):
        did = _id(p.claim_id, "Evidence", i)
        docs.append((did, e))
        res.append(
            {
                "resourceType": "DocumentReference",
                "id": did,
                "status": "current",
                "type": {"text": f"Chart excerpt ({e.source_type})"},
                "category": [
                    {
                        "coding": [{"system": CRITERION, "code": e.criterion_key}],
                        "text": e.criterion_label,
                    }
                ],
                "subject": {"reference": f"Patient/{pid}"},
                **({"date": f"{e.source_date.isoformat()}T00:00:00Z"} if e.source_date else {}),
                "description": f"{e.criterion_key}: {e.criterion_label}",
                "content": [{"attachment": {"contentType": "text/plain", "data": _b64(e.quote)}}],
            }
        )
    support = [
        {
            "sequence": 1,
            "category": _cat("additionalInformation"),
            "valueReference": {"reference": f"DocumentReference/{letter_id}"},
        }
    ]
    support += [
        {
            "sequence": n + 2,
            "category": _cat("additionalInformation"),
            "valueReference": {"reference": f"DocumentReference/{did}"},
        }
        for n, (did, _) in enumerate(docs)
    ]
    claim = {
        "resourceType": "Claim",
        "id": p.claim_id,
        "status": "active",
        "type": {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/claim-type",
                    "code": "professional",
                }
            ]
        },
        "use": "preauthorization",
        "patient": {"reference": f"Patient/{pid}"},
        "created": date.today().isoformat(),
        "insurer": {"reference": f"Organization/{ins}"},
        "provider": {"reference": f"Organization/{org}"},
        "priority": {"coding": [{"code": "normal"}]},
        "diagnosis": [
            {
                "sequence": 1,
                "diagnosisCodeableConcept": {"coding": [{"system": ICD10, "code": p.icd10}]},
            }
        ],
        "insurance": [{"sequence": 1, "focal": True, "coverage": {"reference": f"Coverage/{cov}"}}],
        "supportingInfo": support,
        "item": [
            {
                "sequence": 1,
                "productOrService": {
                    "coding": [{"system": CPT, "code": p.cpt, "display": p.cpt_text}]
                },
                "servicedDate": p.service_date.isoformat(),
            }
        ],
        "extension": [{"url": "http://assent.dev/fhir/policy", "valueString": p.policy}],
    }
    entries = [claim, *res]
    return {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [{"fullUrl": f"urn:uuid:{r['id']}", "resource": r} for r in entries],
    }


def _cat(code: str) -> dict[str, Any]:
    return {"coding": [{"system": SUPPORT, "code": code}]}


def validate_pas(bundle: dict[str, Any]) -> list[str]:
    """Errors for the PAS elements a payer needs; [] means the bundle is usable."""
    errs: list[str] = []
    if bundle.get("resourceType") != "Bundle" or not bundle.get("entry"):
        return ["not a Bundle with entries"]
    by_ref = {
        f"{e['resource']['resourceType']}/{e['resource']['id']}": e["resource"]
        for e in bundle["entry"]
    }
    claims = [r for r in by_ref.values() if r["resourceType"] == "Claim"]
    if len(claims) != 1:
        return [f"expected exactly 1 Claim, found {len(claims)}"]
    c = claims[0]
    if c.get("use") != "preauthorization":
        errs.append("Claim.use must be preauthorization")
    for field in ("patient", "insurer", "provider"):
        ref = (c.get(field) or {}).get("reference")
        if ref not in by_ref:
            errs.append(f"Claim.{field} does not resolve in the bundle")
    if not c.get("diagnosis"):
        errs.append("Claim.diagnosis is required")
    if not any(i.get("focal") for i in c.get("insurance", [])):
        errs.append("Claim.insurance needs a focal coverage")
    items = c.get("item") or []
    if not items or not all(i.get("productOrService", {}).get("coding") for i in items):
        errs.append("Claim.item needs a coded productOrService")
    for s in c.get("supportingInfo", []):
        ref = (s.get("valueReference") or {}).get("reference")
        if ref not in by_ref:
            errs.append(f"supportingInfo {s.get('sequence')} does not resolve: {ref}")
    return errs


def evidence_keys(bundle: dict[str, Any]) -> set[str]:
    """Criterion keys that the bundle's supporting documents claim to evidence."""
    return {
        coding["code"]
        for e in bundle.get("entry", [])
        if e["resource"]["resourceType"] == "DocumentReference"
        for cat in e["resource"].get("category", [])
        for coding in cat.get("coding", [])
        if coding.get("system") == CRITERION
    }
