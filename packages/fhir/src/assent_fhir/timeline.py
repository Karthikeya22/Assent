"""FHIR R4 resources → a normalized, dated patient timeline (ARCHITECTURE §6.3 chart_loader)."""

import base64
from dataclasses import dataclass
from datetime import date
from typing import Any, Literal

Kind = Literal["note", "imaging", "lab", "procedure", "med", "condition", "order"]

_KIND: dict[str, Kind] = {
    "DocumentReference": "note",
    "Observation": "lab",
    "Procedure": "procedure",
    "MedicationRequest": "med",
    "Condition": "condition",
    "ServiceRequest": "order",
}


@dataclass(frozen=True)
class TimelineEvent:
    resource_type: str
    resource_id: str
    date: date
    kind: Kind
    title: str
    text: str


def _date(r: dict[str, Any]) -> date | None:
    for k in (
        "effectiveDateTime",
        "date",
        "authoredOn",
        "recordedDate",
        "onsetDateTime",
        "performedDateTime",
        "issued",
    ):
        if v := r.get(k):
            return date.fromisoformat(str(v)[:10])
    for k in ("performedPeriod", "effectivePeriod"):
        if (p := r.get(k)) and (v := p.get("end") or p.get("start")):
            return date.fromisoformat(str(v)[:10])
    return None


def _d(s: str) -> str:
    return date.fromisoformat(s[:10]).strftime("%m/%d/%Y")


def _concept(c: dict[str, Any] | None) -> str:
    if not c:
        return ""
    return str(c.get("text") or next((x.get("display", "") for x in c.get("coding", [])), ""))


def _value(r: dict[str, Any]) -> str:
    if q := r.get("valueQuantity"):
        return f"{q.get('value')} {q.get('unit', '')}".strip()
    if "valueString" in r:
        return str(r["valueString"])
    return _concept(r.get("valueCodeableConcept"))


def _note_text(r: dict[str, Any]) -> str:
    for c in r.get("content", []):
        att = c.get("attachment", {})
        if att.get("data") and att.get("contentType", "").startswith("text/"):
            return base64.b64decode(att["data"]).decode("utf-8", errors="replace")
    return ""


def _event(r: dict[str, Any], when: date) -> TimelineEvent | None:
    rt, rid = r["resourceType"], r.get("id", "")
    ds = when.strftime("%m/%d/%Y")
    if rt == "DocumentReference":
        title = _concept(r.get("type")) or "Clinical note"
        return TimelineEvent(rt, rid, when, "note", title, _note_text(r))
    if rt == "DiagnosticReport":
        name = _concept(r.get("code"))
        kind: Kind = "imaging" if any(m in name for m in ("MRI", "CT", "X-ray", "XR")) else "lab"
        return TimelineEvent(
            rt, rid, when, kind, name, f"{name} {ds}: {r.get('conclusion', '')}".strip()
        )
    if rt == "Observation":
        name = _concept(r.get("code"))
        return TimelineEvent(rt, rid, when, "lab", name, f"Observation {ds}: {name}: {_value(r)}")
    if rt == "Procedure":
        name = _concept(r.get("code"))
        if p := r.get("performedPeriod"):
            span = (
                f"{_d(p['start'])} to {_d(p['end'])}" if p.get("end") else f"from {_d(p['start'])}"
            )
        else:
            span = ds
        return TimelineEvent(rt, rid, when, "procedure", name, f"Procedure: {name}, {span}")
    if rt == "MedicationRequest":
        name = _concept(r.get("medicationCodeableConcept"))
        return TimelineEvent(
            rt, rid, when, "med", name, f"Medication ordered {ds}: {name} ({r.get('status', '')})"
        )
    if rt == "Condition":
        name = _concept(r.get("code"))
        return TimelineEvent(rt, rid, when, "condition", name, f"Condition recorded {ds}: {name}")
    if rt == "ServiceRequest":
        name = _concept(r.get("code"))
        reasons = ", ".join(_concept(c) for c in r.get("reasonCode", []))
        return TimelineEvent(
            rt,
            rid,
            when,
            "order",
            name,
            f"Order {ds}: {name}" + (f" for {reasons}" if reasons else ""),
        )
    return None  # Encounter, Claim, EOB, Immunization...: not evidence for coverage criteria


def to_timeline(
    resources: list[dict[str, Any]], *, since: date, until: date
) -> list[TimelineEvent]:
    out = []
    for r in resources:
        if r.get("resourceType") not in _KIND and r.get("resourceType") != "DiagnosticReport":
            continue
        when = _date(r)
        if when is None or not since <= when <= until:
            continue
        if (e := _event(r, when)) and e.text:
            out.append(e)
    return sorted(out, key=lambda e: (e.date, e.resource_id), reverse=True)
