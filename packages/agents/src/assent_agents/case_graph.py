"""case_graph (ARCHITECTURE §6.2): chart → de-id + index → evidence per leaf → verify → logic.

Human review, adversary, gaps and packet join in Phase 4; this graph ends at the logic result.
"""

import asyncio
import operator
import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from assent_agents.adversary import Objection, run_adversary, run_rebuttal
from assent_agents.events import Emit, event, no_emit
from assent_agents.evidence.agent import CaseContext, run_evidence
from assent_agents.evidence.models import Verdict
from assent_agents.gaps import GapTaskOut, denial_risk, gap_inputs, plan_gaps
from assent_agents.llm import StructuredLLM
from assent_agents.logic import LogicResult, evaluate, gap_keys
from assent_agents.policy.tree import CriteriaTree, Node
from assent_agents.verify import NLI, judge_downgrade, verify
from assent_fhir.source import FhirSource
from assent_fhir.timeline import to_timeline
from assent_phi.deid import Deidentifier
from assent_retrieval import models
from assent_retrieval.index import index_case
from assent_retrieval.search import hybrid_search

GRAPH_VERSION = "case_graph/v1"


class PhiLeak(RuntimeError):
    pass


def phi_guard(llm: StructuredLLM, names: list[str]) -> StructuredLLM:
    """Refuse to send any message containing a known patient name part (ARCHITECTURE §7.1)."""
    parts = {p for n in names for p in n.split() if len(p) > 2}
    pattern = re.compile(r"\b(" + "|".join(map(re.escape, parts)) + r")\b") if parts else None

    async def guarded(tier: str, messages: list[dict[str, str]], schema: type[Any]) -> Any:
        if pattern and any(pattern.search(m["content"]) for m in messages):
            raise PhiLeak("outbound LLM payload contains a patient name")
        return await llm(tier, messages, schema)

    return guarded


@dataclass(frozen=True)
class Variant:
    """Pipeline switches for the ablation study; the product always runs the defaults."""

    hybrid: bool = True  # False: dense retrieval only
    rerank: bool = True  # False: RRF order, no cross-encoder
    verify: bool = True  # False: citations are still checked (for the report) but never downgrade


@dataclass
class CaseInput:
    case_id: uuid.UUID
    chart_ref: str
    ctx: CaseContext
    patient_names: list[str]
    tree: CriteriaTree
    lookback_days: int = 365


@dataclass
class LeafRun:
    verdict: Verdict
    trace: list[str]
    seconds: float


@dataclass
class CaseResult:
    leaves: dict[str, LeafRun]
    logic: LogicResult
    readiness: float
    n_chunks: int
    seconds: float
    timings: dict[str, float] = field(default_factory=dict)
    objections: list[Objection] = field(default_factory=list)
    gaps: list[GapTaskOut] = field(default_factory=list)
    denial_risk: float | None = None
    risk_factors: list[str] = field(default_factory=list)
    review_error: str | None = None


class _State(TypedDict, total=False):
    inp: CaseInput
    n_chunks: int
    leaves: Annotated[list[tuple[str, LeafRun]], operator.add]
    result: CaseResult


class _LeafTask(TypedDict):
    inp: CaseInput
    leaf: Node


def readiness(tree: CriteriaTree, logic: LogicResult) -> float:
    """Share of the root's requirements that are met (1.0 = ready to submit)."""
    kids = tree.root.children or [tree.root]
    return round(sum(logic.states.get(k.key) == "met" for k in kids) / len(kids), 3)


async def index_chart(
    inp: CaseInput, sessions: async_sessionmaker[AsyncSession], source: FhirSource
) -> tuple[int, int]:
    """Chart -> timeline -> de-identified, embedded chunks. Returns (chunks, events)."""
    until = inp.ctx.order_date
    events = to_timeline(
        source.everything(inp.chart_ref),
        since=until - timedelta(days=inp.lookback_days),
        until=until,
    )
    deid = Deidentifier(known_names=inp.patient_names)
    async with sessions() as s:
        chunks = await index_case(s, inp.case_id, events, deid.deidentify)
        await s.commit()
    return len(chunks), len(events)


def build_graph(
    sessions: async_sessionmaker[AsyncSession],
    source: FhirSource,
    llm: StructuredLLM,
    nli: NLI = models.nli,
    concurrency: int = 4,
    emit: Emit = no_emit,
    review: bool = False,
    variant: Variant = Variant(),  # noqa: B008  (frozen, so a shared default is safe)
) -> Any:
    gate = asyncio.Semaphore(concurrency)
    t0: dict[str, float] = {}

    def ms(since: float) -> int:
        return round((time.perf_counter() - since) * 1000)

    async def load_and_index(state: _State) -> dict[str, Any]:
        inp = state["inp"]
        t0["start"] = time.perf_counter()
        await emit(event("node_started", node="chart_loader"))
        chunks, events = await index_chart(inp, sessions, source)
        t0["indexed"] = time.perf_counter()
        await emit(
            event(
                "node_finished",
                node="deidentify_and_index",
                chunks=chunks,
                events=events,
                latency_ms=ms(t0["start"]),
            )
        )
        return {"n_chunks": chunks}

    def fan_out(state: _State) -> list[Send]:
        return [
            Send("evidence", {"inp": state["inp"], "leaf": leaf})
            for leaf in state["inp"].tree.leaves()
        ]

    async def evidence(state: _LeafTask) -> dict[str, Any]:
        inp: CaseInput = state["inp"]
        leaf: Node = state["leaf"]
        since = inp.ctx.order_date - timedelta(days=leaf.lookback_days or inp.lookback_days)

        headers: dict[str, str] = {}  # chunk id -> "Type MM/DD/YYYY", context for the verifier

        async def search(queries: list[str]) -> Any:
            async with sessions() as s:
                hits = await hybrid_search(
                    s,
                    inp.case_id,
                    queries,
                    since=since,
                    fts=variant.hybrid,
                    rerank=variant.rerank,
                )
            headers.update(
                {
                    str(h.chunk_id): f"{h.resource_type} {h.date:%m/%d/%Y}"
                    if h.date
                    else h.resource_type
                    for h in hits
                }
            )
            await emit(
                event(
                    "retrieval",
                    criterion_id=leaf.key,
                    chunks=[
                        {
                            "id": str(h.chunk_id),
                            "score": round(h.score, 3),
                            "resource_id": h.resource_id,
                        }
                        for h in hits
                    ],
                )
            )
            return hits

        async with gate:
            t = time.perf_counter()
            await emit(event("node_started", node="evidence_agent", criterion_id=leaf.key))
            guarded = phi_guard(llm, inp.patient_names)
            raw, texts, trace = await run_evidence(leaf, inp.ctx, search, guarded)
            checked = await asyncio.to_thread(verify, raw, texts, nli, headers=headers)
            if variant.verify:
                checked = await judge_downgrade(checked, texts, guarded, headers)
            else:
                checked = checked.model_copy(
                    update={"verdict": raw.verdict, "downgraded": None, "original": None}
                )
            await emit(
                event(
                    "verdict",
                    criterion_id=leaf.key,
                    verdict=checked.verdict,
                    confidence=checked.confidence,
                    rationale=checked.rationale,
                    downgraded=checked.downgraded,
                    citations=[
                        {
                            "chunk_id": c.chunk_id,
                            "start": c.start,
                            "end": c.end,
                            "quote": c.quote,
                            "verified": c.verbatim_ok and (c.support or 0) >= 0.7,
                        }
                        for c in checked.citations
                    ],
                )
            )
            await emit(
                event(
                    "node_finished",
                    node="evidence_agent",
                    criterion_id=leaf.key,
                    latency_ms=ms(t),
                    steps=len(trace),
                )
            )
            return {"leaves": [(leaf.key, LeafRun(checked, trace, time.perf_counter() - t))]}

    async def logic(state: _State) -> dict[str, Any]:
        inp = state["inp"]
        runs = dict(state.get("leaves", []))
        result = evaluate(inp.tree.root, {k: r.verdict.verdict for k, r in runs.items()})
        for n in reversed(inp.tree.nodes()):  # children before parents: the UI fills bottom-up
            if n.kind != "LEAF":
                await emit(event("logic_update", node_id=n.key, state=result.states[n.key]))
        end = time.perf_counter()
        return {
            "result": CaseResult(
                leaves=runs,
                logic=result,
                readiness=readiness(inp.tree, result),
                n_chunks=state.get("n_chunks", 0),
                seconds=end - t0.get("start", end),
                timings={"index": t0.get("indexed", end) - t0.get("start", end)},
            )
        }

    async def review_node(state: _State) -> dict[str, Any]:
        """Adversary -> rebuttals -> gaps -> risk (PRODUCT §4.5-4.6), then the human decides."""
        inp, res = state["inp"], state["result"]
        verdicts = {k: r.verdict for k, r in res.leaves.items()}
        if review:
            t = time.perf_counter()
            guarded = phi_guard(llm, inp.patient_names)
            headers: dict[str, str] = {}

            async def search(queries: list[str]) -> Any:
                async with sessions() as s:
                    hits = await hybrid_search(s, inp.case_id, queries)
                headers.update(
                    {
                        str(h.chunk_id): f"{h.resource_type} {h.date:%m/%d/%Y}"
                        if h.date
                        else h.resource_type
                        for h in hits
                    }
                )
                return hits

            try:
                await emit(event("node_started", node="payer_adversary"))
                res.objections = await run_adversary(inp.tree, verdicts, res.logic.state, guarded)
                for ob in res.objections:
                    await emit(
                        event(
                            "objection",
                            id=ob.id,
                            criterion_id=ob.criterion_key,
                            text=ob.text,
                            severity=ob.severity,
                        )
                    )

                async def rebut(ob: Objection) -> Objection:
                    async with gate:
                        done = await run_rebuttal(ob, inp.tree, search, guarded, nli, headers)
                    await emit(
                        event(
                            "objection_update",
                            id=done.id,
                            status=done.status,
                            rebuttal=done.rebuttal,
                            citations=[
                                {
                                    "chunk_id": c.chunk_id,
                                    "quote": c.quote,
                                    "start": c.start,
                                    "end": c.end,
                                    "verified": c.verbatim_ok and (c.support or 0) >= 0.7,
                                }
                                for c in done.citations
                            ],
                        )
                    )
                    return done

                res.objections = list(await asyncio.gather(*(rebut(o) for o in res.objections)))
            except Exception as e:  # a vendor outage must not erase a finished evidence pass
                res.review_error = f"adversary: {type(e).__name__}: {e}"[:300]
                await emit(event("node_failed", node="payer_adversary", error=res.review_error))
            blocking = gap_keys(inp.tree.root, res.logic.states)
            try:
                res.gaps = await plan_gaps(
                    inp.tree, gap_inputs(blocking, verdicts, res.objections), guarded
                )
            except Exception as e:
                res.review_error = (res.review_error or "") + f" gaps: {type(e).__name__}"
            for g in res.gaps:
                await emit(
                    event(
                        "gap",
                        criterion_id=g.criterion_key,
                        title=g.title,
                        detail=g.detail,
                        assignee_role=g.assignee_role,
                    )
                )
            res.denial_risk, res.risk_factors = denial_risk(len(blocking), res.objections, verdicts)
            res.timings["review"] = time.perf_counter() - t
        await emit(
            event(
                "run_finished",
                state=res.logic.state,
                deciding=res.logic.deciding,
                readiness=res.readiness,
                denial_risk=res.denial_risk,
                risk_factors=res.risk_factors,
            )
        )
        return {"result": res}

    g = StateGraph(_State)
    g.add_node("load_and_index", load_and_index)
    g.add_node("evidence", evidence)
    g.add_node("logic", logic)
    g.add_node("review", review_node)
    g.add_edge(START, "load_and_index")
    g.add_conditional_edges("load_and_index", fan_out, ["evidence"])
    g.add_edge("evidence", "logic")
    g.add_edge("logic", "review")
    g.add_edge("review", END)
    return g.compile()


async def run_case(
    inp: CaseInput,
    sessions: async_sessionmaker[AsyncSession],
    source: FhirSource,
    llm: StructuredLLM,
    nli: NLI = models.nli,
    emit: Emit = no_emit,
    review: bool = False,
    variant: Variant = Variant(),  # noqa: B008
) -> CaseResult:
    graph = build_graph(sessions, source, llm, nli, emit=emit, review=review, variant=variant)
    out = await graph.ainvoke({"inp": inp})
    result: CaseResult = out["result"]
    return result
