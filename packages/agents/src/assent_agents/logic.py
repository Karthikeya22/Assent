"""Deterministic three-valued logic engine (ARCHITECTURE §6.3).

LLMs judge the leaves; code combines them, so the outcome is reproducible and testable.
"""

from dataclasses import dataclass, field
from typing import Literal

from assent_agents.policy.tree import Node

State = Literal["met", "not_met", "insufficient"]


@dataclass
class LogicResult:
    state: State
    states: dict[str, State] = field(default_factory=dict)  # every node's state, by key
    deciding: list[str] = field(default_factory=list)  # leaves that determined the root state


def evaluate(root: Node, leaves: dict[str, State]) -> LogicResult:
    states: dict[str, State] = {}

    def ev(n: Node) -> tuple[State, list[str]]:
        if n.kind == "LEAF":
            s: State = leaves.get(n.key, "insufficient")  # no verdict = no evidence
            states[n.key] = s
            return s, [n.key]
        kids = [ev(c) for c in n.children]
        met = [k for s, k in kids if s == "met"]
        ins = [k for s, k in kids if s == "insufficient"]
        bad = [k for s, k in kids if s == "not_met"]
        need = {"AND": len(kids), "OR": 1}.get(n.kind, n.n_required or len(kids))
        if len(met) >= need:
            out: tuple[State, list[str]] = ("met", _flat(met))
        elif len(met) + len(ins) < need:
            out = ("not_met", _flat(bad))
        else:
            out = ("insufficient", _flat(ins))
        states[n.key] = out[0]
        return out

    state, deciding = ev(root)
    return LogicResult(state=state, states=states, deciding=deciding)


def gap_keys(root: Node, states: dict[str, State]) -> list[str]:
    """Leaves that block the decision: not met, with no satisfied ancestor (an unchosen OR
    alternative is not a gap). Mirrors apps/web/lib/run/logic.ts gapKeys."""
    out: list[str] = []

    def walk(n: Node, covered: bool) -> None:
        done = covered or states.get(n.key) == "met"
        if n.kind == "LEAF":
            if not done:
                out.append(n.key)
            return
        for c in n.children:
            walk(c, done)

    walk(root, False)
    return out


def _flat(groups: list[list[str]]) -> list[str]:
    return [k for g in groups for k in g]
