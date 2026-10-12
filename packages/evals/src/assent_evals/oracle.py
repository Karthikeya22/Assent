"""Oracle LLM: a perfect reviewer that only knows what retrieval shows it.

It answers each criterion with the gold verdict, quoting the gold fact sentence, but only once
that sentence appears in the chunks it was shown (it searches for it once otherwise). Running the
full pipeline with it measures everything except the LLM: retrieval recall, de-identification,
and whether the citation verifier wrongly downgrades correct, verbatim evidence.
"""

import re
from typing import Any, cast

from assent_agents.evidence.agent import AgentStep
from assent_agents.evidence.models import CitationOut, VerdictLabel, VerdictOut
from assent_agents.llm import StructuredLLM
from assent_agents.policy.tree import CriteriaTree

_CHUNK = re.compile(r'<chunk id="(c\d+)"[^>]*>\n(.*?)\n</chunk>', re.S)
_CRIT = re.compile(r"^Criterion: (.+)$", re.M)


def make_oracle(facts: dict[str, Any], tree: CriteriaTree) -> StructuredLLM:
    by_label = {n.label: n.key for n in tree.leaves()}
    evidence: dict[str, list[str]] = {}
    for s in facts["statements"]:
        if not s["stale"]:
            evidence.setdefault(s["leaf"], []).append(s["text"])

    async def oracle(tier: str, messages: list[dict[str, str]], schema: type[Any]) -> Any:
        if schema.__name__ == "Judgement":  # verifier second opinion: stay conservative
            return schema(supported=False, reason="oracle does not judge")
        if schema.__name__ == "AdversaryOut":  # review stage: the oracle raises no objections
            return schema(objections=[])
        if schema.__name__ == "GapPlan":  # gap planner falls back to its templates
            return schema(tasks=[])
        crit = _CRIT.search(messages[1]["content"])
        key = by_label.get(crit.group(1)) if crit else None
        gold = facts["gold"].get(key, "insufficient") if key else "insufficient"
        if gold == "insufficient":
            return _answer("insufficient", [])
        shown = {
            cid: body
            for m in messages
            if m["role"] == "user"
            for cid, body in _CHUNK.findall(m["content"])
        }
        for sentence in evidence.get(key or "", []):
            for cid, body in shown.items():
                if sentence in body:
                    return _answer(
                        cast(VerdictLabel, gold),
                        [CitationOut(chunk_id=cid, quote=sentence, claim=sentence)],
                    )
        searched = any(m["role"] == "assistant" for m in messages)
        if not searched and evidence.get(key or ""):
            return AgentStep(
                thought="look for it",
                action="search_chart",
                query=evidence[key or ""][0],
                start=None,
                end=None,
                answer=None,
            )
        return _answer("insufficient", [])  # retrieval never surfaced the evidence

    return oracle


def _answer(verdict: VerdictLabel, cites: list[CitationOut]) -> AgentStep:
    return AgentStep(
        thought="oracle",
        action="answer",
        query=None,
        start=None,
        end=None,
        answer=VerdictOut(
            verdict=verdict,
            confidence=1.0,
            rationale="oracle",
            citations=cites,
        ),
    )
