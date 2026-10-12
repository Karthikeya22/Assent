"""Payer Adversary + Advocate rebuttal (PRODUCT §4.5, ARCHITECTURE §6.3).

The adversary (a different model vendor) sees only the packet and raises objections; the
advocate answers each with fresh chart evidence or concedes. Rebuttal evidence goes through the
same citation verifier as verdicts, so an unverifiable rebuttal becomes a concession.
"""

import uuid
from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, Field

from assent_agents import prompts
from assent_agents.evidence.agent import Search, _Chunks, render
from assent_agents.evidence.models import Citation, CitationOut, Verdict
from assent_agents.llm import StructuredLLM
from assent_agents.policy.tree import CriteriaTree
from assent_agents.verify import NLI, judge_downgrade, verify

Severity = Literal["high", "medium", "low"]
MAX_OBJECTIONS = 5


class ObjectionOut(BaseModel):
    criterion_key: str
    text: str = Field(max_length=500)
    severity: Severity


class AdversaryOut(BaseModel):
    objections: list[ObjectionOut]


class RebuttalOut(BaseModel):
    status: Literal["rebutted", "conceded"]
    text: str = Field(max_length=600)
    citations: list[CitationOut]


@dataclass
class Objection:
    criterion_key: str
    text: str
    severity: Severity
    id: str = field(default_factory=lambda: f"ob_{uuid.uuid4().hex[:8]}")
    status: Literal["open", "rebutted", "conceded"] = "open"
    rebuttal: str = ""
    citations: list[Citation] = field(default_factory=list)


def render_packet(tree: CriteriaTree, verdicts: dict[str, Verdict], decision: str) -> str:
    lines = [
        f"Policy {tree.source_id} v{tree.version}. Provider's overall decision: {decision}.",
        "",
    ]
    for leaf in tree.leaves():
        v = verdicts.get(leaf.key)
        if v is None:
            continue
        lines.append(
            f"[{leaf.key}] {leaf.label}\n  verdict: {v.verdict}\n  rationale: {v.rationale}"
        )
        for c in v.citations:
            if c.verbatim_ok and (c.support or 0) >= 0.7:  # only evidence that passed verification
                lines.append(f'  quote: "{c.quote}"')
        lines.append("")
    return "\n".join(lines)


async def run_adversary(
    tree: CriteriaTree, verdicts: dict[str, Verdict], decision: str, llm: StructuredLLM
) -> list[Objection]:
    msgs = [
        {"role": "system", "content": prompts.load("adversary_v1")},
        {"role": "user", "content": render_packet(tree, verdicts, decision)},
    ]
    out: AdversaryOut = await llm("adversary", msgs, AdversaryOut)
    keys = {n.key for n in tree.leaves()}
    # Objections about unknown criteria or about already-failing ones are dropped, not fatal.
    return [
        Objection(o.criterion_key, o.text, o.severity)
        for o in out.objections
        if o.criterion_key in keys
        and verdicts.get(o.criterion_key) is not None
        and verdicts[o.criterion_key].verdict == "met"
    ][:MAX_OBJECTIONS]


async def run_rebuttal(
    ob: Objection,
    tree: CriteriaTree,
    search: Search,
    llm: StructuredLLM,
    nli: NLI,
    headers: dict[str, str] | None = None,
) -> Objection:
    label = next(n.label for n in tree.leaves() if n.key == ob.criterion_key)
    reg = _Chunks()
    shown = reg.add(await search([ob.text, label]))
    msgs = [
        {"role": "system", "content": prompts.load("advocate_v1")},
        {
            "role": "user",
            "content": f"Criterion: {label}\nObjection ({ob.severity}): {ob.text}"
            f"\n\nChart excerpts:\n{render(shown)}",
        },
    ]
    out: RebuttalOut = await llm("reasoning", msgs, RebuttalOut)
    if out.status == "conceded":
        ob.status, ob.rebuttal = "conceded", out.text
        return ob
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
    texts = {str(h.chunk_id): h.text for h in reg.by_short.values()}
    as_verdict = Verdict(
        criterion_key=ob.criterion_key,
        verdict="met",
        confidence=1.0,
        rationale=out.text,
        citations=cites,
    )
    checked = verify(as_verdict, texts, nli, headers=headers)
    checked = await judge_downgrade(checked, texts, llm, headers)
    ok = checked.verdict == "met"
    ob.status = "rebutted" if ok else "conceded"
    ob.rebuttal = (
        out.text if ok else f"{out.text} (evidence failed verification: {checked.downgraded})"
    )
    ob.citations = checked.citations
    return ob
