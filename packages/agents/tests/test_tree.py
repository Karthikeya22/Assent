import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from assent_agents.policy.ingest import POLICY_DIR, load_snapshot
from assent_agents.policy.tree import CriteriaTree, Node

GOLD = sorted((POLICY_DIR / "gold").glob("*.tree.json"))


def _leaf(key: str, quote: str | None = None) -> Node:
    return Node(key=key, kind="LEAF", label=key, evidence_type="diagnosis", source_quote=quote)


def test_leaf_needs_evidence_type_and_no_children() -> None:
    with pytest.raises(ValidationError):
        Node(key="x", kind="LEAF", label="x")
    with pytest.raises(ValidationError):
        Node(key="x", kind="LEAF", label="x", evidence_type="diagnosis", children=[_leaf("y")])


def test_n_of_m_bounds() -> None:
    Node(key="r", kind="N_OF_M", label="r", n_required=2, children=[_leaf("a"), _leaf("b")])
    with pytest.raises(ValidationError):
        Node(key="r", kind="N_OF_M", label="r", n_required=3, children=[_leaf("a"), _leaf("b")])


def test_validate_reports_missing_quote_and_duplicate_keys() -> None:
    root = Node(
        key="r",
        kind="AND",
        label="r",
        children=[_leaf("a", "present text"), _leaf("a", "absent text")],
    )
    errs = CriteriaTree(source_id="L1", version=1, root=root).validate_against("some present text")
    assert any("duplicate key 'a'" in e for e in errs)
    assert any("absent text" in e for e in errs)


def test_spans_point_at_the_quote() -> None:
    tree = CriteriaTree(source_id="L1", version=1, root=_leaf("a", "needle"))
    text = "hay needle hay"
    (s, e) = tree.spans(text)["a"]
    assert text[s:e] == "needle"


@pytest.mark.parametrize("path", GOLD, ids=[p.name for p in GOLD])
def test_gold_trees_quote_their_lcd_verbatim(path: Path) -> None:
    tree = CriteriaTree.model_validate(json.loads(path.read_text("utf-8")))
    snap = load_snapshot(tree.source_id, tree.version)
    assert tree.validate_against(snap.raw_text) == []
    assert len(tree.leaves()) >= 5


def test_all_esi_gold_trees_share_leaf_keys() -> None:
    keys = {
        p.name: {
            n.key for n in CriteriaTree.model_validate(json.loads(p.read_text("utf-8"))).leaves()
        }
        for p in GOLD
    }
    assert len(keys) == 3
    assert len({frozenset(k) for k in keys.values()}) == 1  # one benchmark key-space for ESI
