from datetime import date

from assent_mock_payer.main import Rules, app, state
from fastapi.testclient import TestClient

from assent_fhir.pas import Evidence, PasInput, build_pas_bundle

client = TestClient(app)


def _bundle(evidence: list[tuple[str, str]]) -> dict:  # type: ignore[type-arg]
    return build_pas_bundle(
        PasInput(
            claim_id="c1",
            patient_name="R",
            birth_year=1950,
            sex="male",
            member_id="M1",
            payer="Medicare",
            provider="Clinic",
            cpt="64483",
            cpt_text="TFESI",
            icd10="M54.16",
            service_date=date(2026, 10, 1),
            policy="L39240 v15",
            letter="letter",
            evidence=[Evidence(k, k, q, "DocumentReference", None) for k, q in evidence],
        )
    )


def _action(resp: dict) -> str:  # type: ignore[type-arg]
    return resp["extension"][0]["valueCodeableConcept"]["coding"][0]["code"]


def setup_function() -> None:
    state["rules"], state["responses"] = Rules(), {}


def test_missing_and_thin_evidence_are_denied_with_the_criterion() -> None:
    r = client.post(
        "/fhir/Claim/$submit", json=_bundle([("dx.imaging", "MRI"), ("dur.conservative", "PT")])
    )
    body = r.json()
    assert _action(body) == "A3"
    by_key = {
        e["extension"][0]["valueString"]: e["code"]["coding"][0]["code"] for e in body["error"]
    }
    assert by_key == {"sev.baseline": "DOC-MISSING", "dur.conservative": "DOC-INSUFFICIENT"}


def test_enough_evidence_is_certified() -> None:
    ev = [
        ("dx.imaging", "MRI"),
        ("sev.baseline", "NRS 7"),
        ("dur.conservative", "PT"),
        ("dur.conservative", "NSAID"),
    ]
    body = client.post("/fhir/Claim/$submit", json=_bundle(ev)).json()
    assert _action(body) == "A1" and body["preAuthRef"].startswith("PA-")


def test_pended_response_resolves_on_poll() -> None:
    client.put("/admin/rules", json={"pend_seconds": 0.05})
    first = client.post("/fhir/Claim/$submit", json=_bundle([])).json()
    assert _action(first) == "A4" and first["outcome"] == "queued"
    import time

    time.sleep(0.06)
    final = client.get(f"/fhir/ClaimResponse/{first['id']}").json()
    assert final["outcome"] == "complete" and _action(final) == "A3"


def test_invalid_bundle_is_rejected() -> None:
    assert (
        client.post("/fhir/Claim/$submit", json={"resourceType": "Bundle", "entry": []}).status_code
        == 422
    )
