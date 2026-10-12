from typing import Any

from assent_agents.adversary import Objection
from assent_agents.evidence.models import Citation, Verdict
from assent_agents.gaps import GapPlan, GapTaskOut, denial_risk, gap_inputs, plan_gaps
from assent_agents.logic import evaluate, gap_keys
from assent_agents.policy.tree import CriteriaTree, Node

LEAF = dict(kind="LEAF", evidence_type="diagnosis")
TREE = CriteriaTree(
    source_id="L1",
    version=1,
    root=Node(
        key="r",
        kind="AND",
        label="r",
        children=[
            Node(
                key="dx",
                kind="OR",
                label="dx",
                children=[
                    Node(key="a", label="A", **LEAF),  # type: ignore[arg-type]
                    Node(key="b", label="B", **LEAF),
                ],
            ),  # type: ignore[arg-type]
            Node(key="c", label="C", source_quote="C must hold", **LEAF),  # type: ignore[arg-type]
        ],
    ),
)


def _v(k: str, verdict: str, support: float = 0.9) -> Verdict:
    return Verdict(
        criterion_key=k,
        verdict=verdict,
        confidence=0.9,
        rationale=f"r {k}",  # type: ignore[arg-type]
        citations=[Citation(chunk_id="x", quote="q", verbatim_ok=True, support=support)]
        if verdict == "met"
        else [],
    )


def test_gap_keys_skip_unchosen_alternatives() -> None:
    states = evaluate(TREE.root, {"a": "met", "b": "insufficient", "c": "insufficient"}).states
    assert gap_keys(TREE.root, states) == ["c"]


async def test_plan_covers_every_gap_with_template_fallback() -> None:
    verdicts = {"a": _v("a", "met"), "c": _v("c", "insufficient")}
    obs = [Objection("a", "Vague.", "high", status="conceded", rebuttal="No more detail.")]
    gaps = gap_inputs(["c"], verdicts, obs)
    assert [g.criterion_key for g in gaps] == ["c", "a"]

    async def llm(tier: str, messages: list[dict[str, str]], schema: type[Any]) -> Any:
        assert tier == "fast" and "C must hold" in messages[1]["content"]
        return GapPlan(
            tasks=[
                GapTaskOut(
                    criterion_key="c",
                    title="Document C",
                    detail="Add C.",
                    assignee_role="clinician",
                ),
                GapTaskOut(
                    criterion_key="zz", title="bogus", detail="x", assignee_role="coordinator"
                ),
            ]
        )

    tasks = await plan_gaps(TREE, gaps, llm)
    assert [t.criterion_key for t in tasks] == ["c", "a"]  # bogus dropped, "a" from template
    assert tasks[1].title.startswith("Document: A")


def test_risk_rises_with_gaps_and_conceded_high_objections() -> None:
    clean, _ = denial_risk(0, [], {"a": _v("a", "met", 0.95)})
    gappy, f1 = denial_risk(
        2, [Objection("a", "x", "high", status="conceded")], {"a": _v("a", "met")}
    )
    assert clean < 0.25 < 0.8 < gappy
    assert f1[0] == "2 criteria not yet proven" and len(f1) <= 3
