import uuid

from sqlalchemy import func, select, text

from assent_agents.case_graph import CaseResult, LeafRun
from assent_agents.evidence.models import Citation, Verdict
from assent_agents.logic import evaluate
from assent_agents.policy.ingest import load_snapshot
from assent_agents.policy.tree import CriteriaTree
from assent_api.db import SessionLocal
from assent_api.models import (
    Case,
    CaseStatus,
    EvidenceCitation,
    EvidenceVerdict,
    Patient,
    RunStep,
    User,
)
from assent_api.policy_load import GOLD_DIR
from assent_api.services import policies, runs


async def test_persist_writes_run_verdicts_citations_and_updates_case(
    users: dict[str, User],
) -> None:
    tree = CriteriaTree.model_validate_json((GOLD_DIR / "L39240-v15.tree.json").read_text("utf-8"))
    async with SessionLocal() as s:
        pv = await policies.upsert_version(s, load_snapshot("L39240", 15), service_family="esi")
        await policies.replace_tree(s, pv, tree, approved_by=users["policy_admin"].id)
        p = Patient(fhir_id="p", display_name_synthetic="P", birth_year=1950, sex="male")
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
        chunk_id = uuid.uuid4()
        await s.execute(
            text(
                "INSERT INTO chart_chunks (id, case_id, fhir_resource_type, "
                "fhir_resource_id, text_deid, char_offset) VALUES "
                "(:i, :c, 'DocumentReference', 'd1', 'Symptoms began 8 weeks ago.', 0)"
            ),
            {"i": chunk_id, "c": case.id},
        )
        await s.commit()

        leaves = {}
        for leaf in tree.leaves():
            cites = []
            if leaf.key == "dur.pain":
                cites = [
                    Citation(
                        chunk_id=str(chunk_id),
                        quote="Symptoms began 8 weeks ago.",
                        claim="Pain for 8 weeks.",
                        start=0,
                        end=27,
                        verbatim_ok=True,
                        support=0.97,
                    ),
                    Citation(chunk_id="c9-hallucinated", quote="x"),
                ]
            leaves[leaf.key] = LeafRun(
                Verdict(
                    criterion_key=leaf.key,
                    verdict="met",
                    confidence=0.9,
                    rationale="r",
                    citations=cites,
                ),
                ["answer"],
                1.2,
            )
        logic = evaluate(tree.root, {k: r.verdict.verdict for k, r in leaves.items()})
        result = CaseResult(leaves=leaves, logic=logic, readiness=1.0, n_chunks=1, seconds=3.0)
        run = await runs.persist(s, case.id, pv.id, result, model="oracle")
        await s.commit()

        assert (
            await s.scalar(
                select(func.count())
                .select_from(EvidenceVerdict)
                .where(EvidenceVerdict.run_id == run.id)
            )
            == 12
        )
        [cit] = (await s.scalars(select(EvidenceCitation))).all()  # hallucinated id skipped
        assert cit.chunk_id == chunk_id and cit.entailment_score == 0.97
        steps = (await s.scalars(select(RunStep).where(RunStep.run_id == run.id))).all()
        assert len(steps) == 13 and steps[-1].payload_json["state"] == "met"
        await s.refresh(case)
        assert case.status == CaseStatus.needs_review and case.readiness_score == 1.0
        assert case.policy_version_id == pv.id
