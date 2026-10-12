"""Gap planner (PRODUCT §4.6) and heuristic denial-risk score.

Gaps = blocking criteria (unmet, no satisfied ancestor) + criteria with a conceded objection.
One fast-tier call writes the tasks; any gap the model skips gets a plain template task, so a
gap is never silently dropped.
"""

import json
import math
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from assent_agents import prompts
from assent_agents.adversary import Objection
from assent_agents.evidence.models import Verdict
from assent_agents.llm import StructuredLLM
from assent_agents.policy.tree import CriteriaTree

Role = Literal["clinician", "coordinator"]


class GapTaskOut(BaseModel):
    criterion_key: str
    title: str = Field(max_length=120)
    detail: str = Field(max_length=500)
    assignee_role: Role


class GapPlan(BaseModel):
    tasks: list[GapTaskOut]


@dataclass
class GapInput:
    criterion_key: str
    reason: str


def gap_inputs(
    blocking: list[str], verdicts: dict[str, Verdict], objections: list[Objection]
) -> list[GapInput]:
    out = {
        k: GapInput(
            k,
            verdicts[k].downgraded or verdicts[k].rationale
            if k in verdicts
            else "No evidence found in the chart.",
        )
        for k in blocking
    }
    for o in objections:
        if o.status == "conceded" and o.criterion_key not in out:
            out[o.criterion_key] = GapInput(
                o.criterion_key,
                f"Payer objection ({o.severity}): {o.text} Provider response: {o.rebuttal}",
            )
    return list(out.values())


async def plan_gaps(
    tree: CriteriaTree, gaps: list[GapInput], llm: StructuredLLM
) -> list[GapTaskOut]:
    if not gaps:
        return []
    nodes = {n.key: n for n in tree.leaves()}
    body = "\n\n".join(
        f"criterion_key: {g.criterion_key}\ncriterion: {nodes[g.criterion_key].label}\n"
        f"policy ({tree.source_id}): {nodes[g.criterion_key].source_quote or '(n/a)'}\n"
        f"why not proven: {g.reason}"
        for g in gaps
    )
    msgs = [
        {"role": "system", "content": prompts.load("gap_planner_v1")},
        {"role": "user", "content": body},
    ]
    plan: GapPlan = await llm("fast", msgs, GapPlan)
    wanted = {g.criterion_key for g in gaps}
    got = {t.criterion_key: t for t in plan.tasks if t.criterion_key in wanted}
    for g in gaps:  # template fallback: never drop a gap
        if g.criterion_key not in got:
            n = nodes[g.criterion_key]
            got[g.criterion_key] = GapTaskOut(
                criterion_key=g.criterion_key,
                title=f"Document: {n.label}"[:120],
                detail=(
                    f"The chart does not yet prove this {tree.source_id} requirement. {g.reason}"
                )[:500],
                assignee_role="clinician",
            )
    return [got[g.criterion_key] for g in gaps]


# --- denial risk -----------------------------------------------------------------------------
# Fitted by `assent_evals.fit_risk` on dev-split runs; the hand-set prior is the fallback.
FITTED = Path(__file__).with_name("risk_v1.json")
PRIOR: tuple[float, dict[str, float]] = (
    -2.4,
    {
        "blocking_gaps": 1.4,
        "conceded_high": 1.6,
        "conceded_other": 0.5,
        "weak_support": 2.0,
        "judged_share": 0.8,
    },
)
_LABELS = {
    "blocking_gaps": "{n} criteria not yet proven",
    "conceded_high": "{n} high-severity payer objection(s) conceded",
    "conceded_other": "{n} other objection(s) conceded",
    "weak_support": "evidence grounding {pct}% below full",
    "judged_share": "{pct}% of evidence needed the second-opinion judge",
}


@cache
def risk_params() -> tuple[float, dict[str, float]]:
    if FITTED.exists():
        d = json.loads(FITTED.read_text("utf-8"))
        return float(d["bias"]), {k: float(v) for k, v in d["weights"].items()}
    return PRIOR


def risk_features(
    blocking: int, objections: list[Objection], verdicts: dict[str, Verdict]
) -> dict[str, float]:
    support = [
        c.support or 0.0
        for v in verdicts.values()
        if v.verdict == "met"
        for c in v.citations
        if c.verbatim_ok
    ]
    judged = [c.judged for v in verdicts.values() if v.verdict == "met" for c in v.citations]
    return {
        "blocking_gaps": float(blocking),
        "conceded_high": float(
            sum(o.status == "conceded" and o.severity == "high" for o in objections)
        ),
        "conceded_other": float(
            sum(o.status == "conceded" and o.severity != "high" for o in objections)
        ),
        "weak_support": 1 - (sum(support) / len(support)) if support else 1.0,
        "judged_share": sum(judged) / len(judged) if judged else 0.0,
    }


def denial_risk(
    blocking: int,
    objections: list[Objection],
    verdicts: dict[str, Verdict],
    params: tuple[float, dict[str, float]] | None = None,
) -> tuple[float, list[str]]:
    feats = risk_features(blocking, objections, verdicts)
    bias, weights = params or risk_params()
    contrib = {k: weights[k] * v for k, v in feats.items()}
    risk = 1 / (1 + math.exp(-(bias + sum(contrib.values()))))
    top = [k for k, c in sorted(contrib.items(), key=lambda kv: -kv[1]) if c > 0.05][:3]
    factors = [_LABELS[k].format(n=int(feats[k]), pct=round(feats[k] * 100)) for k in top]
    return round(risk, 3), factors
