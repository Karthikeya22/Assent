"""Persist a case-graph result: runs, run_steps, evidence_verdicts, evidence_citations."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from assent_agents.case_graph import GRAPH_VERSION, CaseResult
from assent_agents.evidence.agent import PROMPT
from assent_api.models import (
    Case,
    CaseStatus,
    CriteriaNode,
    EvidenceCitation,
    EvidenceVerdict,
    GapTask,
    Objection,
    ObjectionStatus,
    Role,
    Run,
    RunStep,
    Verdict,
)


async def persist(
    s: AsyncSession,
    case_id: uuid.UUID,
    policy_version_id: uuid.UUID,
    result: CaseResult,
    *,
    trigger: str = "manual",
    model: str | None = None,
    run: Run | None = None,
) -> Run:
    """Fill `run` (created when the job was enqueued) or a new Run with the graph's results."""
    now = datetime.now(UTC)
    if run is None:
        run = Run(case_id=case_id, trigger=trigger, graph_version=GRAPH_VERSION, status="running")
        s.add(run)
    run.status, run.finished_at, run.graph_version = "finished", now, GRAPH_VERSION
    await s.flush()
    node_ids = dict(
        (
            await s.execute(
                select(CriteriaNode.key, CriteriaNode.id).where(
                    CriteriaNode.policy_version_id == policy_version_id
                )
            )
        )
        .tuples()
        .all()
    )
    for key, leaf in result.leaves.items():
        v = leaf.verdict
        s.add(
            RunStep(
                run_id=run.id,
                node="evidence_agent",
                status="finished",
                finished_at=now,
                model=model,
                prompt_version=PROMPT,
                payload_json={
                    "criterion": key,
                    "trace": leaf.trace,
                    "seconds": round(leaf.seconds, 2),
                    "downgraded": v.downgraded,
                    "original": v.original,
                },
            )
        )
        ev = EvidenceVerdict(
            run_id=run.id,
            criterion_id=node_ids[key],
            verdict=Verdict(v.verdict),
            confidence=v.confidence,
            rationale=v.rationale,
        )
        s.add(ev)
        await s.flush()
        for c in v.citations:
            try:
                chunk = uuid.UUID(c.chunk_id)
            except ValueError:
                continue  # a hallucinated chunk id has nothing to link to; the verdict recorded it
            s.add(
                EvidenceCitation(
                    verdict_id=ev.id,
                    chunk_id=chunk,
                    quote=c.quote,
                    start_char=c.start or 0,
                    end_char=c.end or 0,
                    verbatim_ok=c.verbatim_ok,
                    entailment_score=c.support,
                )
            )
    s.add(
        RunStep(
            run_id=run.id,
            node="logic_engine",
            status="finished",
            finished_at=now,
            payload_json={
                "state": result.logic.state,
                "deciding": result.logic.deciding,
                "readiness": result.readiness,
            },
        )
    )
    for ob in result.objections:
        s.add(
            Objection(
                run_id=run.id,
                criterion_id=node_ids.get(ob.criterion_key),
                text=ob.text,
                severity=ob.severity,
                status=ObjectionStatus(ob.status),
                rebuttal_text=ob.rebuttal,
                rebuttal_citation_ids=[
                    uuid.UUID(c.chunk_id)
                    for c in ob.citations
                    if c.verbatim_ok and (c.support or 0) >= 0.7 and _is_uuid(c.chunk_id)
                ],
            )
        )
    if result.denial_risk is not None or result.review_error:
        s.add(
            RunStep(
                run_id=run.id,
                node="review",
                status="failed" if result.review_error else "finished",
                finished_at=now,
                payload_json={
                    "denial_risk": result.denial_risk,
                    "risk_factors": result.risk_factors,
                    "error": result.review_error,
                    "objections": len(result.objections),
                    "gaps": len(result.gaps),
                },
            )
        )
    # A new run's gap list replaces the previous run's open tasks (done ones are kept as history).
    await s.execute(delete(GapTask).where(GapTask.case_id == case_id, GapTask.status == "open"))
    for g in result.gaps:
        s.add(
            GapTask(
                case_id=case_id,
                criterion_id=node_ids.get(g.criterion_key),
                title=g.title,
                detail=g.detail,
                assignee_role=Role(g.assignee_role),
                status="open",
            )
        )
    case = await s.get(Case, case_id)
    if case is not None:
        case.policy_version_id = policy_version_id
        case.readiness_score = result.readiness
        case.denial_risk = result.denial_risk
        case.status = CaseStatus.needs_review
    await s.flush()
    return run


def _is_uuid(x: str) -> bool:
    try:
        uuid.UUID(x)
    except ValueError:
        return False
    return True
