import asyncio
import random
from collections import Counter
from datetime import date

import pytest

from assent_agents.logic import evaluate
from assent_evals.synth.build import FAMILIES, build_case
from assent_evals.synth.case import CaseFacts
from assent_evals.synth.facts import Patient, difficulty_plan
from assent_evals.synth.notes import Note

PATIENT = Patient(fhir_id="p1", name="Rosa Alvarez", sex="female", birth_date=date(1952, 3, 2))
Built = list[tuple[CaseFacts, list[Note]]]


def _build(family: str) -> Built:
    tree = FAMILIES[family].tree
    plan = difficulty_plan(50, random.Random(7))
    return [
        asyncio.run(build_case(f"{family}-{i:03d}", 7, d, PATIENT, tree, "template"))  # type: ignore[misc]
        for i, d in enumerate(plan)
    ]


@pytest.fixture(scope="module", params=["hgns", "pva"])
def built(request: pytest.FixtureRequest) -> tuple[str, Built]:
    return request.param, _build(request.param)


def test_gold_covers_exactly_the_tree_leaves(built: tuple[str, Built]) -> None:
    family, cases = built
    keys = {n.key for n in FAMILIES[family].tree.leaves()}
    for f, _ in cases:
        assert set(f.gold) == keys, f.case_id


def test_decision_is_the_logic_engine_over_gold(built: tuple[str, Built]) -> None:
    family, cases = built
    tree = FAMILIES[family].tree
    for f, _ in cases:
        want = "ready" if evaluate(tree.root, f.gold).state == "met" else "not_ready"
        assert f.decision == want, f.case_id


def test_every_decided_leaf_has_evidence_and_insufficient_has_none(
    built: tuple[str, Built],
) -> None:
    _, cases = built
    for f, notes in cases:
        stated = {s.leaf for s in f.statements if not s.stale}
        for leaf, g in f.gold.items():
            assert (leaf in stated) == (g != "insufficient"), (f.case_id, leaf, g)
        by_slot = {n.slot: n.text for n in notes}
        assert all(s.text in by_slot[s.slot] for s in f.statements), f.case_id


def test_hard_cases_are_not_ready_and_mix_is_reasonable(built: tuple[str, Built]) -> None:
    _, cases = built
    for f, notes in cases:
        if f.difficulty in ("missing", "injection"):
            assert f.decision == "not_ready", f.case_id
        if f.difficulty == "injection":
            assert f.injection and any(f.injection in n.text for n in notes)
    ready = sum(f.decision == "ready" for f, _ in cases)
    assert 15 <= ready <= 35, Counter(f.decision for f, _ in cases)


def test_pva_scenarios_exercise_every_branch() -> None:
    conds = Counter(f.condition.split(":")[0] for f, _ in _build("pva"))
    assert set(conds) == {"hosp", "worsening", "stable"}


def test_build_is_deterministic() -> None:
    for family in ("hgns", "pva"):
        tree = FAMILIES[family].tree
        a = asyncio.run(build_case(f"{family}-x", 7, "buried", PATIENT, tree, "template"))
        b = asyncio.run(build_case(f"{family}-x", 7, "buried", PATIENT, tree, "template"))
        assert a[0].model_dump_json() == b[0].model_dump_json()
