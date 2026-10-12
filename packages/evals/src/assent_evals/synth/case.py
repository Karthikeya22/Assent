"""Fact sheet shared by the HGNS and PVA families (ESI keeps its own `EsiFacts`).

Same contract as ESI: every met/not_met leaf is carried by a fact sentence that lands verbatim in
a named note; an `insufficient` leaf is never mentioned.
"""

import random
from collections.abc import Callable
from datetime import date

from pydantic import BaseModel

from assent_agents.logic import State, evaluate
from assent_agents.policy.tree import CriteriaTree
from assent_evals.synth.facts import Difficulty, EsiFacts, Patient, Statement


class Obs(BaseModel):
    """A coded numeric fact, emitted as a FHIR Observation in structured (clean) cases."""

    code: str
    system: str
    display: str
    value: float
    unit: str
    date: date


class CaseFacts(BaseModel):
    family: str
    case_id: str
    difficulty: Difficulty
    order_date: date
    patient: Patient
    condition: str
    cpt: str
    cpt_text: str
    icd10: str
    icd10_text: str
    dates: dict[str, date]  # note slot -> note date
    observations: list[Obs] = []
    gold: dict[str, State]
    decision: str = "not_ready"
    statements: list[Statement] = []
    injection: str | None = None
    structured: bool = True

    def slot_dates(self) -> dict[str, date]:
        return self.dates


Facts = EsiFacts | CaseFacts
Phraser = Callable[[CaseFacts, random.Random], list[Statement]]


def finish(f: CaseFacts, tree: CriteriaTree, statements: Phraser, rng: random.Random) -> CaseFacts:
    """Attach statements and the injection, then derive the decision from gold via the tree."""
    from assent_evals.synth.phrases import INJECTION

    f.structured = f.difficulty == "clean"
    f.statements = statements(f, rng)
    if f.difficulty == "injection":
        f.injection = INJECTION
    f.decision = "ready" if evaluate(tree.root, f.gold).state == "met" else "not_ready"
    return f


def stmt(f: CaseFacts, leaf: str, text: str, slot: str, stale: bool = False) -> Statement:
    return Statement(leaf=leaf, gold=f.gold[leaf], text=text, slot=slot, stale=stale)


def d(x: date) -> str:
    return x.strftime("%m/%d/%Y")
