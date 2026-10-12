import base64
from datetime import date

from assent_fhir.pas import Evidence, PasInput, build_pas_bundle, evidence_keys, validate_pas


def _input(**kw: object) -> PasInput:
    base = dict(
        claim_id="claim-1",
        patient_name="R. Alvarez",
        birth_year=1955,
        sex="female",
        member_id="1EG4-TE5-MK72",
        payer="Medicare (MAC J-H)",
        provider="Assent Demo Spine Clinic",
        cpt="64483",
        cpt_text="TFESI lumbar",
        icd10="M54.16",
        service_date=date(2026, 10, 1),
        policy="L39240 v15",
        letter="To the reviewer: ...",
        evidence=[
            Evidence(
                "dur.pain",
                "Pain for 4+ weeks",
                "Pain began 08/01/2026.",
                "DocumentReference",
                date(2026, 9, 1),
            ),
            Evidence(
                "rehab", "Home exercise program", "Continues HEP daily.", "DocumentReference", None
            ),
        ],
    )
    return PasInput(**{**base, **kw})  # type: ignore[arg-type]


def test_bundle_is_valid_and_carries_evidence_per_criterion() -> None:
    b = build_pas_bundle(_input())
    assert validate_pas(b) == []
    assert evidence_keys(b) == {"dur.pain", "rehab"}
    claim = b["entry"][0]["resource"]
    assert claim["use"] == "preauthorization" and len(claim["supportingInfo"]) == 3  # letter + 2
    docs = [
        e["resource"] for e in b["entry"] if e["resource"]["resourceType"] == "DocumentReference"
    ]
    quotes = {base64.b64decode(d["content"][0]["attachment"]["data"]).decode() for d in docs}
    assert "Pain began 08/01/2026." in quotes


def test_build_is_deterministic() -> None:
    assert build_pas_bundle(_input()) == build_pas_bundle(_input())


def test_validate_reports_broken_references_and_use() -> None:
    b = build_pas_bundle(_input())
    claim = b["entry"][0]["resource"]
    claim["use"] = "claim"
    claim["supportingInfo"][1]["valueReference"]["reference"] = "DocumentReference/missing"
    b["entry"] = [e for e in b["entry"] if e["resource"]["resourceType"] != "Coverage"]
    errs = validate_pas(b)
    assert any("preauthorization" in e for e in errs)
    assert any("does not resolve: DocumentReference/missing" in e for e in errs)
    assert validate_pas({"resourceType": "Bundle", "entry": []}) == ["not a Bundle with entries"]


def test_bundle_evidence_round_trips() -> None:
    from assent_fhir.pas import bundle_evidence

    p = _input()
    assert bundle_evidence(build_pas_bundle(p)) == p.evidence
