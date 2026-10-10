"""Evidence agent (ARCHITECTURE §6.3, §6.5): one per leaf criterion, a short action loop.

Hybrid retrieval runs first with deterministic queries, so most criteria are answered in one
step; the model may search again or ask code to compute a duration (max 4 steps). Chunks are
shown as delimited data with short ids (c1, c2, ...) that map back to real chunk ids.
"""

import json
import uuid
from collections.abc import Awaitable, Callable
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from assent_agents import prompts
from assent_agents.evidence.models import Citation, Verdict, VerdictOut
from assent_agents.llm import StructuredLLM
from assent_agents.policy.tree import Node
from assent_retrieval.search import Hit

PROMPT = "evidence_v1"
MAX_STEPS = 4
Search = Callable[[list[str]], Awaitable[list[Hit]]]

SYNONYMS = {
    "diagnosis": "assessment impression diagnosis",
    "imaging_finding": "MRI CT imaging findings stenosis herniation nerve root",
    "assessment": "pain score scale NRS VAS ODI function daily activities",
    "duration": "symptoms began weeks ago onset duration of pain",
    "prior_therapy": "physical therapy medication NSAID home exercise program tried failed",
    "contraindication": "fever infection cancer weight loss bowel bladder red flags",
    "procedure_history": "prior epidural steroid injection history past 12 months",
}


class AgentStep(BaseModel):
    thought: str = Field(max_length=400)
    action: Literal["search_chart", "compute_duration", "answer"]
    query: str | None
    start: str | None
    end: str | None
    answer: VerdictOut | None


class CaseContext(BaseModel):
    order_date: date
    service: str
    cpt: str
    icd10: str


def queries_for(c: Node) -> list[str]:
    return [c.label, f"{c.label} {SYNONYMS.get(c.evidence_type or '', '')}".strip()]


def compute_duration(start: str, end: str) -> str:
    try:
        a, b = (datetime.strptime(x, "%m/%d/%Y").date() for x in (start, end))
    except ValueError:
        return "error: dates must be MM/DD/YYYY"
    days = (b - a).days
    return f"{days} days ({days / 7:.1f} weeks) from {start} to {end}"


class _Chunks:
    """Short-id registry so the model cites c1..cN, never raw UUIDs."""

    def __init__(self) -> None:
        self.by_short: dict[str, Hit] = {}
        self.by_id: dict[uuid.UUID, str] = {}

    def add(self, hits: list[Hit]) -> list[tuple[str, Hit]]:
        new = []
        for h in hits:
            if h.chunk_id not in self.by_id:
                short = f"c{len(self.by_short) + 1}"
                self.by_short[short], self.by_id[h.chunk_id] = h, short
                new.append((short, h))
        return new


def render(chunks: list[tuple[str, Hit]]) -> str:
    if not chunks:
        return "(no new chunks found)"
    return "\n".join(
        f'<chunk id="{s}" source="{h.resource_type}" date="{h.date:%m/%d/%Y}">\n{h.text}\n</chunk>'
        if h.date
        else f'<chunk id="{s}" source="{h.resource_type}">\n{h.text}\n</chunk>'
        for s, h in chunks
    )


async def run_evidence(
    criterion: Node, ctx: CaseContext, search: Search, llm: StructuredLLM
) -> tuple[Verdict, dict[str, str], list[str]]:
    """Returns (verdict with real chunk ids, chunk texts by real id for the verifier, trace)."""
    reg = _Chunks()
    first = reg.add(await search(queries_for(criterion)))
    threshold = f"\nThreshold: {json.dumps(criterion.threshold)}" if criterion.threshold else ""
    msgs = [
        {"role": "system", "content": prompts.load(PROMPT)},
        {
            "role": "user",
            "content": (
                f"Criterion: {criterion.label}\n"
                f"Evidence type: {criterion.evidence_type}{threshold}\n"
                f"Policy text: {criterion.source_quote or '(n/a)'}\n\n"
                f"Request: {ctx.service}, CPT {ctx.cpt}, ICD-10 {ctx.icd10}. "
                f"Today (date of request): {ctx.order_date:%m/%d/%Y}.\n\n"
                f"Chart excerpts:\n{render(first)}"
            ),
        },
    ]
    trace: list[str] = []
    out: VerdictOut | None = None
    for step in range(MAX_STEPS):
        st: AgentStep = await llm("reasoning", msgs, AgentStep)
        trace.append(f"{st.action}: {st.query or st.start or ''}".strip(": "))
        if st.action == "answer" or step == MAX_STEPS - 1:
            out = st.answer
            break
        if st.action == "search_chart" and st.query:
            result = render(reg.add(await search([st.query])))
        elif st.action == "compute_duration" and st.start and st.end:
            result = compute_duration(st.start, st.end)
        else:
            result = "error: missing arguments for that action"
        msgs += [
            {"role": "assistant", "content": st.model_dump_json()},
            {"role": "user", "content": f"Result of {st.action}:\n{result}"},
        ]

    if out is None:
        out = VerdictOut(
            verdict="insufficient",
            confidence=0.0,
            citations=[],
            rationale="No answer within the step budget.",
        )
    cites = [
        Citation(
            chunk_id=str(reg.by_short[c.chunk_id].chunk_id)
            if c.chunk_id in reg.by_short
            else c.chunk_id,
            quote=c.quote,
            claim=c.claim,
        )
        for c in out.citations
    ]
    verdict = Verdict(
        criterion_key=criterion.key,
        verdict=out.verdict,
        confidence=out.confidence,
        rationale=out.rationale,
        citations=cites,
    )
    texts = {str(h.chunk_id): h.text for h in reg.by_short.values()}
    return verdict, texts, trace
