"""Mock Payer (ARCHITECTURE §5): an external system with hidden rules, latency and denials.

It reads only the PAS Bundle it is sent. Hidden rules demand evidence per criterion: a minimum
number of supporting chart excerpts tagged with that criterion. Decisions are deterministic so a
demo is reproducible; `pend_seconds` makes responses arrive later, like a real payer.

Run: `uv run uvicorn assent_mock_payer.main:app --port 8020`
"""

import time
import uuid
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from assent_fhir.pas import CRITERION, validate_pas

FAMILY_BY_CPT = {"64479": "esi", "64483": "esi", "64582": "hgns", "22513": "pva", "22514": "pva"}
# X12 278 review action: A1 certified, A3 not certified, A4 pended
REVIEW = "https://codesystem.x12.org/005010/306"
DENIAL = "http://assent.dev/fhir/CodeSystem/denial-reason"
DENIED_KEY = "http://assent.dev/fhir/denied-criterion"


class Rules(BaseModel):
    pend_seconds: float = 0
    # family -> criterion key -> minimum number of supporting excerpts
    demands: dict[str, dict[str, int]] = {
        "esi": {"dx.imaging": 1, "sev.baseline": 1, "dur.conservative": 2},
        "hgns": {"ahi": 1, "dise": 1, "cpap": 2},
        "pva": {"fx.imaging": 1, "fx.acute": 2},
    }
    # what a reviewer calls each demand in a denial letter
    names: dict[str, str] = {
        "dx.imaging": "imaging concordant with the diagnosis",
        "sev.baseline": "a baseline pain or function score",
        "dur.conservative": "failure of conservative care (therapy and medication)",
        "ahi": "an apnea-hypopnea index from polysomnography",
        "dise": "drug-induced sleep endoscopy findings",
        "cpap": "CPAP failure or intolerance",
        "fx.imaging": "advanced imaging of an acute fracture",
        "fx.acute": "fracture acuity (symptom onset)",
    }


app = FastAPI(title="Mock Payer")
state: dict[str, Any] = {"rules": Rules(), "responses": {}}


def _counts(bundle: dict[str, Any]) -> dict[str, int]:
    out: dict[str, int] = {}
    for e in bundle["entry"]:
        r = e["resource"]
        if r["resourceType"] != "DocumentReference":
            continue
        for cat in r.get("category", []):
            for c in cat.get("coding", []):
                if c.get("system") == CRITERION:
                    out[c["code"]] = out.get(c["code"], 0) + 1
    return out


def decide(bundle: dict[str, Any], rules: Rules) -> dict[str, Any]:
    claim = next(e["resource"] for e in bundle["entry"] if e["resource"]["resourceType"] == "Claim")
    cpt = claim["item"][0]["productOrService"]["coding"][0]["code"]
    family = FAMILY_BY_CPT.get(cpt)
    if family is None:
        return _response(
            claim, "A3", [("NOT-COVERED", f"CPT {cpt} is not covered under this policy", None)]
        )
    have = _counts(bundle)
    errors: list[tuple[str, str, str | None]] = []
    for key, need in rules.demands.get(family, {}).items():
        got = have.get(key, 0)
        if got < need:
            what = rules.names.get(key, key)
            code, text = (
                ("DOC-MISSING", f"The record does not document {what}.")
                if got == 0
                else (
                    "DOC-INSUFFICIENT",
                    f"Documentation of {what} is insufficient: {got} supporting "
                    f"excerpt(s) provided, {need} required.",
                )
            )
            errors.append((code, text, key))
    return _response(claim, "A3" if errors else "A1", errors)


def _response(
    claim: dict[str, Any], action: str, errors: list[tuple[str, str, str | None]]
) -> dict[str, Any]:
    rid = str(uuid.uuid4())
    return {
        "resourceType": "ClaimResponse",
        "id": rid,
        "status": "active",
        "use": "preauthorization",
        "outcome": "complete",
        "request": {"reference": f"Claim/{claim['id']}"},
        "disposition": "Certified in total" if action == "A1" else "Not certified",
        "preAuthRef": f"PA-{rid[:8].upper()}" if action == "A1" else None,
        "extension": [
            {
                "url": "reviewAction",
                "valueCodeableConcept": {"coding": [{"system": REVIEW, "code": action}]},
            }
        ],
        "error": [
            {
                "code": {"coding": [{"system": DENIAL, "code": code}], "text": text},
                **({"extension": [{"url": DENIED_KEY, "valueString": key}]} if key else {}),
            }
            for code, text, key in errors
        ],
    }


@app.post("/fhir/Claim/$submit")
def submit(bundle: dict[str, Any]) -> dict[str, Any]:
    if errs := validate_pas(bundle):
        raise HTTPException(422, {"issue": errs})
    rules: Rules = state["rules"]
    final = decide(bundle, rules)
    if rules.pend_seconds <= 0:
        return final
    state["responses"][final["id"]] = (time.monotonic() + rules.pend_seconds, final)
    pended = {
        **final,
        "outcome": "queued",
        "disposition": "Pended for review",
        "error": [],
        "preAuthRef": None,
    }
    pended["extension"] = [
        {
            "url": "reviewAction",
            "valueCodeableConcept": {"coding": [{"system": REVIEW, "code": "A4"}]},
        }
    ]
    return pended


@app.get("/fhir/ClaimResponse/{rid}")
def poll(rid: str) -> dict[str, Any]:
    if rid not in state["responses"]:
        raise HTTPException(404, "unknown ClaimResponse")
    ready_at, final = state["responses"][rid]
    if time.monotonic() < ready_at:
        return {**final, "outcome": "queued", "disposition": "Pended for review", "error": []}
    return dict(final)


@app.put("/admin/rules")
def set_rules(rules: Rules) -> Rules:
    state["rules"] = rules
    return rules


@app.get("/admin/rules")
def get_rules() -> Rules:
    rules: Rules = state["rules"]
    return rules
