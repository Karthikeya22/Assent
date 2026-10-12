import uuid
from datetime import date
from typing import Any

from assent_agents.adversary import (
    AdversaryOut,
    Objection,
    ObjectionOut,
    RebuttalOut,
    render_packet,
    run_adversary,
    run_rebuttal,
)
from assent_agents.evidence.models import Citation, CitationOut, Verdict
from assent_agents.policy.tree import CriteriaTree, Node
from assent_agents.verify import Judgement
from assent_retrieval.search import Hit

TREE = CriteriaTree(
    source_id="L1",
    version=1,
    root=Node(
        key="r",
        kind="AND",
        label="r",
        children=[
            Node(
                key="dur.pain", kind="LEAF", label="Pain at least 4 weeks", evidence_type="duration"
            ),
            Node(
                key="rehab",
                kind="LEAF",
                label="Home exercise program",
                evidence_type="prior_therapy",
            ),
        ],
    ),
)


def _v(key: str, verdict: str, quote: str = "", ok: bool = True) -> Verdict:
    cites = (
        [Citation(chunk_id="x", quote=quote, verbatim_ok=ok, support=0.9 if ok else 0.1)]
        if quote
        else []
    )
    return Verdict(
        criterion_key=key,
        verdict=verdict,
        confidence=0.9,
        rationale=f"why {key}",  # type: ignore[arg-type]
        citations=cites,
    )


VERDICTS = {
    "dur.pain": _v("dur.pain", "met", "Pain for 8 weeks."),
    "rehab": _v("rehab", "insufficient"),
}


def scripted(*outs: Any) -> Any:
    seen: list[tuple[str, list[dict[str, str]]]] = []

    async def llm(tier: str, messages: list[dict[str, str]], schema: type[Any]) -> Any:
        seen.append((tier, messages))
        if schema is Judgement:
            return Judgement(supported=False, reason="no")
        return outs[len([s for s in seen if s[0] != "fast"]) - 1]

    llm.seen = seen  # type: ignore[attr-defined]
    return llm


def test_packet_shows_only_verified_quotes() -> None:
    v = dict(VERDICTS, rehab=_v("rehab", "met", "Unverified claim text.", ok=False))
    p = render_packet(TREE, v, "insufficient")
    assert '"Pain for 8 weeks."' in p and "Unverified claim text" not in p


async def test_adversary_keeps_only_objections_on_met_known_criteria() -> None:
    llm = scripted(
        AdversaryOut(
            objections=[
                ObjectionOut(criterion_key="dur.pain", text="No onset date.", severity="high"),
                ObjectionOut(criterion_key="rehab", text="Already insufficient.", severity="low"),
                ObjectionOut(criterion_key="made.up", text="Hallucinated key.", severity="high"),
            ]
        )
    )
    obs = await run_adversary(TREE, VERDICTS, "insufficient", llm)
    assert [(o.criterion_key, o.severity) for o in obs] == [("dur.pain", "high")]
    assert llm.seen[0][0] == "adversary"  # the different-vendor tier


HIT = Hit(
    uuid.uuid4(),
    "Symptoms began on 06/01/2026, 8 weeks before this visit.",
    date(2026, 8, 1),
    "DocumentReference",
    "d1",
    1.0,
)


async def _search(qs: list[str]) -> list[Hit]:
    return [HIT]


def nli(premise: str, hypothesis: str) -> dict[str, float]:
    ok = "06/01/2026" in hypothesis and "06/01/2026" in premise
    return {"entailment": 0.95 if ok else 0.02, "contradiction": 0.0, "neutral": 0.05}


async def test_verified_rebuttal_is_rebutted_and_unverified_is_conceded() -> None:
    good = scripted(
        RebuttalOut(
            status="rebutted",
            text="Onset documented.",
            citations=[
                CitationOut(
                    chunk_id="c1",
                    quote="Symptoms began on 06/01/2026",
                    claim="Onset was 06/01/2026.",
                )
            ],
        )
    )
    ob = await run_rebuttal(
        Objection("dur.pain", "No onset date.", "high"), TREE, _search, good, nli
    )
    assert ob.status == "rebutted" and ob.citations[0].chunk_id == str(HIT.chunk_id)

    bad = scripted(
        RebuttalOut(
            status="rebutted",
            text="Onset documented.",
            citations=[
                CitationOut(
                    chunk_id="c1",
                    quote="Onset was clearly documented",
                    claim="Onset was 06/01/2026.",
                )
            ],
        )
    )
    ob = await run_rebuttal(
        Objection("dur.pain", "No onset date.", "high"), TREE, _search, bad, nli
    )
    assert ob.status == "conceded" and "failed verification" in ob.rebuttal


async def test_concession_passes_through() -> None:
    llm = scripted(RebuttalOut(status="conceded", text="No dates in the chart.", citations=[]))
    ob = await run_rebuttal(
        Objection("dur.pain", "No onset date.", "high"), TREE, _search, llm, nli
    )
    assert (ob.status, ob.rebuttal) == ("conceded", "No dates in the chart.")
