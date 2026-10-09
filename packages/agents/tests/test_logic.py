import itertools

import pytest

from assent_agents.logic import evaluate
from assent_agents.policy.tree import Node

M, N, I = "met", "not_met", "insufficient"  # noqa: E741 (truth-table shorthand)
V = (M, N, I)


def leaf(k: str) -> Node:
    return Node(key=k, kind="LEAF", label=k, evidence_type="diagnosis")


def group(kind: str, n: int | None = None, k: int = 2) -> Node:
    return Node(
        key="g", kind=kind, label="g", n_required=n, children=[leaf(f"l{i}") for i in range(k)]
    )


def _and(vals: tuple[str, ...]) -> str:
    return N if N in vals else M if all(v == M for v in vals) else I


def _or(vals: tuple[str, ...]) -> str:
    return M if M in vals else N if all(v == N for v in vals) else I


@pytest.mark.parametrize("a,b", list(itertools.product(V, V)))
def test_and_truth_table(a: str, b: str) -> None:
    assert evaluate(group("AND"), {"l0": a, "l1": b}).state == _and((a, b))


@pytest.mark.parametrize("a,b", list(itertools.product(V, V)))
def test_or_truth_table(a: str, b: str) -> None:
    assert evaluate(group("OR"), {"l0": a, "l1": b}).state == _or((a, b))


@pytest.mark.parametrize("vals", list(itertools.product(V, V, V)))
def test_two_of_three(vals: tuple[str, str, str]) -> None:
    met, ins = vals.count(M), vals.count(I)
    want = M if met >= 2 else N if met + ins < 2 else I
    got = evaluate(group("N_OF_M", n=2, k=3), dict(zip(["l0", "l1", "l2"], vals, strict=True)))
    assert got.state == want


def test_missing_leaf_is_insufficient() -> None:
    assert evaluate(group("AND"), {"l0": M}).state == I


def test_deciding_leaves_explain_the_outcome() -> None:
    # AND fails because of l1 alone; an OR passes because of its met child.
    r = evaluate(group("AND"), {"l0": M, "l1": N})
    assert r.deciding == ["l1"]
    r = evaluate(group("OR"), {"l0": N, "l1": M})
    assert r.deciding == ["l1"]
    r = evaluate(group("AND"), {"l0": M, "l1": I})
    assert r.deciding == ["l1"]


def test_nested_states_are_reported_per_node() -> None:
    root = Node(
        key="r",
        kind="AND",
        label="r",
        children=[Node(key="o", kind="OR", label="o", children=[leaf("a"), leaf("b")]), leaf("c")],
    )
    r = evaluate(root, {"a": N, "b": M, "c": M})
    assert r.state == M and r.states == {"r": M, "o": M, "a": N, "b": M, "c": M}
