"""Persist a case-graph result: runs, run_steps, evidence_verdicts, evidence_citations."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from assent_agents.case_graph import GRAPH_VERSION, CaseResult
from assent_agents.evidence.agent import PROMPT
from assent_api.models import (
    Case,
    CaseStatus,
    CriteriaNode,
    EvidenceCitation,
    EvidenceVerdict,
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
    case = await s.get(Case, case_id)
    if case is not None:
        case.policy_version_id = policy_version_id
        case.readiness_score = result.readiness
        case.status = CaseStatus.needs_review
    await s.flush()
    return run
