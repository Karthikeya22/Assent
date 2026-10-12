from assent_cds.main import app
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from assent_api.db import SessionLocal
from assent_api.models import Case, Patient, User

from .test_review_api import _setup


def _order(cpt: str, patient: str) -> dict:  # type: ignore[type-arg]
    return {
        "hook": "order-sign",
        "context": {
            "patientId": patient,
            "draftOrders": {
                "resourceType": "Bundle",
                "entry": [
                    {
                        "resource": {
                            "resourceType": "ServiceRequest",
                            "code": {"coding": [{"code": cpt}]},
                        }
                    }
                ],
            },
        },
    }


async def test_discovery_and_order_sign_card_with_case_gaps(users: dict[str, User]) -> None:
    case_id, _ = await _setup(users)
    async with SessionLocal() as s:
        case = await s.get(Case, __import__("uuid").UUID(case_id))
        assert case is not None
        fhir_id = await s.scalar(select(Patient.fhir_id).where(Patient.id == case.patient_id))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://cds") as c:
        assert (await c.get("/cds-services")).json()["services"][0]["id"] == "assent-order-sign"
        cards = (
            await c.post("/cds-services/assent-order-sign", json=_order("64483", fhir_id))
        ).json()["cards"]
        [card] = cards
        assert "L39240" in card["summary"] and "Readiness" in card["detail"]
        assert "Document onset date" in card["detail"]  # the open gap from _setup
        assert card["links"][0]["url"].endswith(case_id)
        none = (
            await c.post("/cds-services/assent-order-sign", json=_order("99213", fhir_id))
        ).json()
        assert none == {"cards": []}  # an office visit needs no prior auth
