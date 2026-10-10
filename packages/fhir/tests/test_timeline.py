import base64
from datetime import date

from assent_fhir.timeline import to_timeline


def _doc(rid: str, when: str, title: str, text: str) -> dict:  # type: ignore[type-arg]
    return {
        "resourceType": "DocumentReference",
        "id": rid,
        "date": f"{when}T09:00:00Z",
        "type": {"text": title},
        "content": [
            {
                "attachment": {
                    "contentType": "text/plain",
                    "data": base64.b64encode(text.encode()).decode(),
                }
            }
        ],
    }


RESOURCES = [
    {"resourceType": "Patient", "id": "p1"},
    _doc("d1", "2026-09-20", "Pain Management Consultation", "Symptoms began 8 weeks ago."),
    _doc("d0", "2024-01-01", "Old note", "Too old to matter."),
    {
        "resourceType": "Observation",
        "id": "o1",
        "effectiveDateTime": "2026-09-20",
        "code": {"text": "NRS pain/function score"},
        "valueString": "7/10",
    },
    {
        "resourceType": "Observation",
        "id": "o2",
        "effectiveDateTime": "2026-09-01T10:00:00-04:00",
        "code": {"text": "Body Weight"},
        "valueQuantity": {"value": 81.2, "unit": "kg"},
    },
    {
        "resourceType": "Procedure",
        "id": "pr1",
        "performedPeriod": {"start": "2026-07-01", "end": "2026-08-05"},
        "code": {"text": "Physical therapy procedure"},
    },
    {
        "resourceType": "DiagnosticReport",
        "id": "dr1",
        "effectiveDateTime": "2026-09-10",
        "code": {"text": "MRI lumbar spine"},
        "conclusion": "L4-L5 disc herniation.",
    },
    {"resourceType": "Claim", "id": "c1", "created": "2026-09-01"},  # billing noise: skipped
]


def test_timeline_kinds_text_and_window() -> None:
    tl = to_timeline(RESOURCES, since=date(2025, 9, 1), until=date(2026, 9, 30))
    by_id = {e.resource_id: e for e in tl}
    assert set(by_id) == {"d1", "o1", "o2", "pr1", "dr1"}  # old note and Claim excluded
    assert by_id["d1"].kind == "note" and by_id["d1"].text == "Symptoms began 8 weeks ago."
    assert by_id["o1"].text == "Observation 09/20/2026: NRS pain/function score: 7/10"
    assert by_id["o2"].text == "Observation 09/01/2026: Body Weight: 81.2 kg"
    assert by_id["pr1"].kind == "procedure" and "07/01/2026 to 08/05/2026" in by_id["pr1"].text
    assert by_id["dr1"].kind == "imaging" and "L4-L5 disc herniation." in by_id["dr1"].text


def test_timeline_is_newest_first() -> None:
    tl = to_timeline(RESOURCES, since=date(2025, 9, 1), until=date(2026, 9, 30))
    assert [e.date for e in tl] == sorted((e.date for e in tl), reverse=True)
