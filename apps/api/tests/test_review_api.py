import uuid

from httpx import AsyncClient
from sqlalchemy import func, select

from assent_agents.adversary import Objection as Ob
from assent_agents.case_graph import CaseResult, LeafRun
from assent_agents.evidence.models import Verdict as V
from assent_agents.gaps import GapTaskOut
from assent_agents.logic import evaluate
from assent_agents.policy.ingest import load_snapshot
from assent_agents.policy.tree import CriteriaTree
from assent_api.db import SessionLocal
from assent_api.models import AuditLog, Case, Patient, User
from assent_api.policy_load import GOLD_DIR
from assent_api.services import policies, runs

from .conftest import bearer


async def _setup(users: dict[str, User]) -> tuple[str, str]:
    tree = CriteriaTree.model_validate_json((GOLD_DIR / "L39240-v15.tree.json").read_text("utf-8"))
    async with SessionLocal() as s:
        pv = await policies.upsert_version(s, load_snapshot("L39240", 15), service_family="esi")
        await policies.replace_tree(s, pv, tree, approved_by=users["policy_admin"].id)
        p = Patient(
            fhir_id=f"p-{uuid.uuid4()}", display_name_synthetic="R", birth_year=1950, sex="male"
        )
        s.add(p)
        await s.flush()
        case = Case(
            org_id=users["coordinator"].org_id,
            patient_id=p.id,
            service_family="esi",
            cpt_codes=["64483"],
            icd10_codes=["M54.16"],
        )
        s.add(case)
        await s.flush()
        leaves = {
            n.key: LeafRun(
                V(criterion_key=n.key, verdict="met", confidence=0.9, rationale="r", citations=[]),
                [],
                1.0,
            )
            for n in tree.leaves()
        }
        logic = evaluate(tree.root, {k: "met" for k in leaves})
        res = CaseResult(
            leaves=leaves,
            logic=logic,
            readiness=1.0,
            n_chunks=0,
            seconds=1.0,
            objections=[
                Ob(
                    "dur.pain",
                    "No onset date.",
                    "high",
                    status="conceded",
                    rebuttal="Nothing to cite.",
                )
            ],
            gaps=[
                GapTaskOut(
                    criterion_key="dur.pain",
                    title="Document onset date",
                    detail="Add onset.",
                    assignee_role="clinician",
                )
            ],
            denial_risk=0.62,
            risk_factors=["1 high-severity payer objection(s) conceded"],
        )
        run = await runs.persist(s, case.id, pv.id, res)
        await s.commit()
        return str(case.id), str(run.id)


async def test_objections_and_gaps_are_persisted_and_listed(
    client: AsyncClient, users: dict[str, User]
) -> None:
    case_id, run_id = await _setup(users)
    h = bearer(users["coordinator"])
    [ob] = (await client.get(f"/api/v1/runs/{run_id}/objections", headers=h)).json()
    assert (ob["criterion_key"], ob["severity"], ob["status"]) == ("dur.pain", "high", "conceded")
    [gap] = (await client.get(f"/api/v1/cases/{case_id}/gaps", headers=h)).json()
    assert gap["title"] == "Document onset date" and gap["status"] == "open"
    detail = (await client.get(f"/api/v1/cases/{case_id}", headers=h)).json()
    assert detail["denial_risk"] == 0.62 and detail["status"] == "needs_review"
    done = await client.patch(f"/api/v1/gaps/{gap['id']}", json={"status": "done"}, headers=h)
    assert done.json()["status"] == "done"


async def test_approve_blocked_by_unrebutted_high_objection_until_acknowledged(
    client: AsyncClient, users: dict[str, User]
) -> None:
    _, run_id = await _setup(users)
    h = bearer(users["coordinator"])
    r = await client.post(f"/api/v1/runs/{run_id}/resume", json={"decision": "approve"}, headers=h)
    assert r.status_code == 409 and "high-severity" in r.json()["detail"]
    r = await client.post(
        f"/api/v1/runs/{run_id}/resume",
        json={"decision": "approve", "acknowledge_high": True},
        headers=h,
    )
    assert r.status_code == 200 and r.json()["case_status"] == "ready"
    auditor = await client.post(
        f"/api/v1/runs/{run_id}/resume",
        json={"decision": "reject"},
        headers=bearer(users["auditor"]),
    )
    assert auditor.status_code == 403
    async with SessionLocal() as s:
        row = await s.scalar(select(AuditLog).where(AuditLog.action == "run.approve"))
        assert row is not None and row.after_json and row.after_json["acknowledged_high"]


async def test_override_needs_reason_is_audited_and_recomputes_readiness(
    client: AsyncClient, users: dict[str, User]
) -> None:
    case_id, run_id = await _setup(users)
    h = bearer(users["clinician"])
    verdicts = (await client.get(f"/api/v1/runs/{run_id}/verdicts", headers=h)).json()
    target = next(v for v in verdicts if v["criterion_key"] == "rehab")
    bad = await client.patch(
        f"/api/v1/verdicts/{target['id']}",
        json={"verdict": "insufficient", "reason": ""},
        headers=h,
    )
    assert bad.status_code == 422
    ok = await client.patch(
        f"/api/v1/verdicts/{target['id']}",
        json={"verdict": "insufficient", "reason": "HEP not documented"},
        headers=h,
    )
    assert ok.status_code == 200
    after = (await client.get(f"/api/v1/runs/{run_id}/verdicts", headers=h)).json()
    v = next(x for x in after if x["criterion_key"] == "rehab")
    assert v["overridden"] and v["verdict"] == "insufficient"
    detail = (await client.get(f"/api/v1/cases/{case_id}", headers=h)).json()
    assert detail["readiness_score"] < 1.0
    async with SessionLocal() as s:
        assert (
            await s.scalar(
                select(func.count())
                .select_from(AuditLog)
                .where(AuditLog.action == "verdict.override")
            )
            == 1
        )


async def test_approve_on_not_ready_case_needs_acknowledgement(
    client: AsyncClient, users: dict[str, User]
) -> None:
    _, run_id = await _setup(users)
    h = bearer(users["coordinator"])
    verdicts = (await client.get(f"/api/v1/runs/{run_id}/verdicts", headers=h)).json()
    rehab = next(v for v in verdicts if v["criterion_key"] == "rehab")
    await client.patch(
        f"/api/v1/verdicts/{rehab['id']}",
        json={"verdict": "insufficient", "reason": "HEP not documented"},
        headers=h,
    )
    r = await client.post(
        f"/api/v1/runs/{run_id}/resume",
        json={"decision": "approve", "acknowledge_high": True},
        headers=h,
    )
    assert r.status_code == 409 and "not ready" in r.json()["detail"]
    r = await client.post(
        f"/api/v1/runs/{run_id}/resume",
        json={"decision": "approve", "acknowledge_high": True, "acknowledge_not_ready": True},
        headers=h,
    )
    assert r.status_code == 200
    async with SessionLocal() as s:
        row = await s.scalar(select(AuditLog).where(AuditLog.action == "run.approve"))
        assert row is not None and row.after_json and row.after_json["acknowledged_not_ready"]
