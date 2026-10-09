from typing import Any

from pydantic import BaseModel

from assent_agents.policy.compiler import (
    Extraction,
    FlatNode,
    build_tree,
    compare_trees,
    compile_policy,
    coverage_section,
    merge_trees,
)
from assent_agents.policy.ingest import LcdSnapshot, sha256

TEXT = (
    "Background prose.\n\nCovered Indications\n\n"
    "Pain duration of at least four (4) weeks. Failure of physical therapy. "
    "Concordant MRI findings. Patient is a nonsmoker.\n\nProvider Qualifications\n\nTrained staff."
)


def _n(
    key: str,
    parent: str | None,
    kind: str = "LEAF",
    quote: str | None = None,
    et: str | None = "diagnosis",
) -> FlatNode:
    return FlatNode(
        key=key,
        parent_key=parent,
        kind=kind,
        label=key,
        n_required=None,
        evidence_type=et if kind == "LEAF" else None,
        threshold_json=None,
        lookback_days=None,
        source_quote=quote,
    )


ROOT = _n("root", None, "AND", None)
A = _n("a", "root", quote="Pain duration of at least four (4) weeks", et="duration")
B = _n("b", "root", quote="Failure of physical therapy", et="prior_therapy")
C = _n("c", "root", quote="Patient is a nonsmoker")
BAD = _n("bad", "root", quote="Six weeks of chiropractic care")  # not in the text

SAMPLES = [
    Extraction(nodes=[ROOT, A, B, C]),
    Extraction(nodes=[ROOT, A, B]),
    Extraction(nodes=[ROOT, A, BAD]),
]


def test_coverage_section_trims_prose_and_qualifications() -> None:
    sec = coverage_section(TEXT)
    assert sec.startswith("Covered Indications") and "Trained staff" not in sec


def test_build_tree_rejects_two_roots() -> None:
    try:
        build_tree(Extraction(nodes=[ROOT, _n("r2", None, "AND")]), "L1", 1)
    except ValueError as e:
        assert "exactly one root" in str(e)
    else:
        raise AssertionError


def test_majority_merge_keeps_2_of_3_and_drops_invalid_quotes() -> None:
    trees = [build_tree(s, "L1", 1) for s in SAMPLES]
    merged, dropped = merge_trees(trees, TEXT)
    assert {n.key for n in merged.leaves()} == {"a", "b"}  # a: 3/3, b: 2/3, c: 1/3
    assert any("bad" in d and "verbatim" in d for d in dropped)
    assert merged.validate_against(TEXT) == []


def test_merge_is_deterministic_regardless_of_sample_order() -> None:
    trees = [build_tree(s, "L1", 1) for s in SAMPLES]
    m1, _ = merge_trees(trees, TEXT)
    m2, _ = merge_trees(list(reversed(trees)), TEXT)
    assert m1.model_dump() == m2.model_dump()


def test_compare_trees_scores_leaf_overlap() -> None:
    gold = build_tree(Extraction(nodes=[ROOT, A, B, C]), "L1", 1)
    compiled = build_tree(
        Extraction(nodes=[ROOT, A, _n("x", "root", quote="Concordant MRI findings")]), "L1", 1
    )
    s = compare_trees(gold, compiled, TEXT)
    assert (s["precision"], round(s["recall"], 3)) == (0.5, 0.333)


async def test_compile_policy_end_to_end_with_fake_llm() -> None:
    calls: list[str] = []

    async def fake(tier: str, messages: list[dict[str, str]], schema: type[Any]) -> BaseModel:
        calls.append(tier)
        assert "Covered Indications" in messages[-1]["content"]
        return SAMPLES[len(calls) - 1]

    snap = LcdSnapshot(
        source_id="L1",
        lcd_id=1,
        version=1,
        title="t",
        contractor="c",
        rev_eff_date="",
        source_url="",
        retrieved_at="",
        raw_text=TEXT,
        content_hash=sha256(TEXT),
    )
    result = await compile_policy(snap, llm=fake, n_samples=3)
    assert calls == ["reasoning"] * 3
    assert {n.key for n in result.tree.leaves()} == {"a", "b"}
    assert result.samples_ok == 3
