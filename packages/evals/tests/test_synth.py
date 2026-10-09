import random
from collections import Counter
from datetime import date

import pytest

from assent_agents.logic import evaluate
from assent_agents.policy.tree import CriteriaTree
from assent_evals.synth.build import GOLD_TREE, build_case
from assent_evals.synth.facts import LEAVES, EsiFacts, Patient, difficulty_plan
from assent_evals.synth.notes import Note

TREE = CriteriaTree.model_validate_json(GOLD_TREE.read_text("utf-8"))
PATIENT = Patient(fhir_id="p1", name="Rosa Alvarez", sex="female", birth_date=date(1958, 3, 2))


@pytest.fixture(scope="module")
async def cases() -> list[tuple[EsiFacts, list[Note]]]:
    plan = difficulty_plan(50, random.Random(7))
    return [
        await build_case(f"esi-{i:03d}", 7, d, PATIENT, TREE, "template")
        for i, d in enumerate(plan)
    ]


def test_difficulty_mix_is_exact_for_50() -> None:
    assert Counter(difficulty_plan(50, random.Random(1))) == {
        "clean": 20,
        "buried": 15,
        "missing": 8,
        "contradictory": 5,
        "injection": 2,
    }


def test_gold_covers_exactly_the_tree_leaves(cases: list[tuple[EsiFacts, list[Note]]]) -> None:
    keys = {n.key for n in TREE.leaves()}
    assert set(LEAVES) == keys
    for f, _ in cases:
        assert set(f.gold) == keys


def test_decision_is_the_logic_engine_over_gold(cases: list[tuple[EsiFacts, list[Note]]]) -> None:
    for f, _ in cases:
        want = "ready" if evaluate(TREE.root, f.gold).state == "met" else "not_ready"
        assert f.decision == want, f.case_id


def test_every_decided_leaf_has_evidence_and_insufficient_has_none(
    cases: list[tuple[EsiFacts, list[Note]]],
) -> None:
    for f, notes in cases:
        stated = {s.leaf for s in f.statements if not s.stale}
        for leaf, g in f.gold.items():
            assert (leaf in stated) == (g != "insufficient"), (f.case_id, leaf, g)
        text = "\n".join(n.text for n in notes)
        assert all(s.text in text for s in f.statements)


def test_hard_cases_are_not_ready_and_mix_is_reasonable(
    cases: list[tuple[EsiFacts, list[Note]]],
) -> None:
    for f, _ in cases:
        if f.difficulty in ("missing", "injection"):
            assert f.decision == "not_ready", f.case_id
        if f.difficulty == "injection":
            assert f.injection and any(f.injection in n.text for n in _notes(cases, f.case_id))
    ready = sum(f.decision == "ready" for f, _ in cases)
    assert 15 <= ready <= 35  # neither trivially all-ready nor all-denied


def test_build_is_deterministic() -> None:
    import asyncio

    a = asyncio.run(build_case("esi-x", 7, "buried", PATIENT, TREE, "template"))
    b = asyncio.run(build_case("esi-x", 7, "buried", PATIENT, TREE, "template"))
    assert a[0].model_dump_json() == b[0].model_dump_json()
    assert [n.text for n in a[1]] == [n.text for n in b[1]]


def _notes(cases: list[tuple[EsiFacts, list[Note]]], cid: str) -> list[Note]:
    return next(n for f, n in cases if f.case_id == cid)
