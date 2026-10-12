"""arq worker: runs agent graphs off the request path.

Run: `uv run arq assent_worker.main.WorkerSettings`
"""

import logging
import uuid
from datetime import UTC, date, datetime
from typing import Any, ClassVar

from arq.connections import RedisSettings

from assent_agents.case_graph import CaseInput, run_case
from assent_agents.events import Event, event
from assent_agents.evidence.agent import CaseContext
from assent_api.db import SessionLocal, redis
from assent_api.models import Case, CaseStatus, Patient, PolicyVersion, Run
from assent_api.services import policies, run_bus, runs
from assent_api.settings import get_settings

log = logging.getLogger("assent.worker")
SERVICE_NAMES = {
    "esi": "Epidural steroid injection",
    "hgns": "Hypoglossal nerve stimulation",
    "pva": "Percutaneous vertebral augmentation",
}


async def ping(ctx: dict[str, Any], msg: str) -> str:
    log.info("ping %s", msg)
    return f"pong: {msg}"


def _llm(patient: Patient, family: str = "esi") -> Any:
    from assent_agents import llm as llm_mod
    from assent_agents.cassette import Cassette
    from assent_evals.bench import cassettes_for

    if get_settings().agent_llm == "oracle":
        if not patient.fhir_id.startswith("bench/"):
            raise ValueError("oracle LLM only works for benchmark patients")
        import json

        from assent_evals.oracle import make_oracle
        from assent_evals.synth.build import family_of

        fam = family_of(patient.fhir_id[6:])
        facts = json.loads((fam.bench / f"{patient.fhir_id[6:]}.json").read_text("utf-8"))["facts"]
        return make_oracle(facts, fam.tree)
    return Cassette(cassettes_for(family), llm_mod.structured)


async def run_case_job(ctx: dict[str, Any], run_id: str) -> str:
    from assent_fhir.source import FileFhirSource

    rid = uuid.UUID(run_id)

    async def emit(e: Event) -> None:
        await run_bus.publish(redis, run_id, e)

    try:
        async with SessionLocal() as s:
            run = await s.get(Run, rid)
            if run is None:
                return "missing run"
            case = await s.get(Case, run.case_id)
            assert case is not None
            patient = await s.get(Patient, case.patient_id)
            assert patient is not None
            pv = (
                await s.get(PolicyVersion, case.policy_version_id)
                if case.policy_version_id
                else await policies.approved_version_for(s, case.service_family)
            )
            if pv is None:
                raise ValueError(f"no approved policy for {case.service_family}")
            tree = await policies.load_tree(s, pv)
            run.status, case.status = "running", CaseStatus.running
            await s.commit()
            ctx_ = CaseContext(
                order_date=(
                    case.created_at.date()
                    if not patient.fhir_id.startswith("bench/")
                    else _bench_order_date(patient)
                ),
                service=SERVICE_NAMES.get(case.service_family, case.service_family),
                cpt=case.cpt_codes[0],
                icd10=case.icd10_codes[0],
                family=case.service_family,
            )
            inp = CaseInput(
                case_id=case.id,
                tree=tree,
                ctx=ctx_,
                chart_ref=f"{case.service_family}/{patient.fhir_id.split('/')[-1]}",
                patient_names=[patient.display_name_synthetic],
            )
            llm = _llm(patient, case.service_family)
            pv_id = pv.id
        await emit(
            event(
                "run_started",
                run_id=run_id,
                case_id=str(inp.case_id),
                policy=f"{tree.source_id} v{tree.version}",
                leaves=[n.key for n in tree.leaves()],
            )
        )
        result = await run_case(
            inp,
            SessionLocal,
            FileFhirSource(get_settings().chart_dir),
            llm,
            emit=emit,
            review=True,
        )
        async with SessionLocal() as s:
            run = await s.get(Run, rid)
            assert run is not None
            await runs.persist(
                s, inp.case_id, pv_id, result, run=run, model=get_settings().agent_llm
            )
            await s.commit()
        return f"{result.logic.state} readiness={result.readiness}"
    except Exception as e:  # any failure must end the stream, never leave clients spinning
        log.exception("run %s failed", run_id)
        async with SessionLocal() as s:
            run = await s.get(Run, rid)
            if run is not None:
                run.status, run.finished_at = "failed", datetime.now(UTC)
                case = await s.get(Case, run.case_id)
                if case is not None:
                    case.status = CaseStatus.new
                await s.commit()
        await emit(event("run_failed", error=f"{type(e).__name__}: {e}"[:300]))
        return "failed"


def _bench_order_date(patient: Patient) -> date:
    import json

    from assent_evals.synth.build import family_of

    bench = family_of(patient.fhir_id[6:]).bench
    facts = json.loads((bench / f"{patient.fhir_id[6:]}.json").read_text("utf-8"))["facts"]
    return date.fromisoformat(facts["order_date"])


async def appeal_job(ctx: dict[str, Any], appeal_id: str) -> str:
    """Draft a cited appeal for a denial; the human edits and sends it (POST /appeals/{id}/send)."""
    from assent_agents.appeal import Denial, draft_appeal
    from assent_api.models import Appeal, Packet, Submission
    from assent_api.services import packets
    from assent_retrieval import models
    from assent_retrieval.search import hybrid_search

    aid = uuid.UUID(appeal_id)
    try:
        async with SessionLocal() as s:
            a = await s.get(Appeal, aid)
            if a is None:
                return "missing appeal"
            sub = await s.get(Submission, a.submission_id)
            assert sub is not None
            packet = await s.get(Packet, sub.packet_id)
            assert packet is not None
            case = await s.get(Case, packet.case_id)
            patient = await s.get(Patient, case.patient_id) if case else None
            assert case is not None and patient is not None
            pv = (
                await s.get(PolicyVersion, case.policy_version_id)
                if case.policy_version_id
                else None
            )
            if pv is None:
                raise ValueError("case has no policy version")
            labels = {n.key: n.label for n in (await policies.load_tree(s, pv)).leaves()}
            denials = [
                Denial(k, labels.get(k, k), reason)
                for k, reason in packets.denied(sub.claim_response_json or {})
            ]
            cited = {cid for _, cid in await packets.run_evidence(s, packet.run_id)}
            ctx_ = CaseContext(
                order_date=_bench_order_date(patient)
                if patient.fhir_id.startswith("bench/")
                else case.created_at.date(),
                service=SERVICE_NAMES.get(case.service_family, case.service_family),
                cpt=case.cpt_codes[0],
                icd10=case.icd10_codes[0],
                family=case.service_family,
            )
            case_id, family = case.id, case.service_family

        async def search(queries: list[str]) -> Any:
            async with SessionLocal() as s2:
                return await hybrid_search(s2, case_id, queries)

        from assent_agents.case_graph import phi_guard

        llm = phi_guard(_llm(patient, family), [patient.display_name_synthetic])
        draft = await draft_appeal(denials, ctx_, search, llm, models.nli, cited)
        async with SessionLocal() as s:
            a = await s.get(Appeal, aid)
            assert a is not None
            a.draft_text = draft.text
            a.citations_json = {
                k: [
                    {
                        "chunk_id": c.chunk_id,
                        "quote": c.quote,
                        "claim": c.claim,
                        "support": c.support,
                        "criterion_label": labels.get(k, k),
                    }
                    for c in cites
                ]
                for k, cites in draft.citations.items()
            }
            a.status = "draft"
            await s.commit()
        return f"draft: {sum(len(v) for v in draft.citations.values())} verified citations"
    except Exception:
        log.exception("appeal %s failed", appeal_id)
        async with SessionLocal() as s:
            a = await s.get(Appeal, aid)
            if a is not None:
                a.status = "failed"
                await s.commit()
        return "failed"


class WorkerSettings:
    functions: ClassVar[list[Any]] = [ping, run_case_job, appeal_job]
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    max_jobs = 2  # 7 GB laptop: each run loads local models; keep concurrency low
    job_timeout = 900
