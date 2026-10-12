import uuid
from datetime import date
from typing import Any

from pydantic import BaseModel

from assent_agents.appeal import Denial, draft_appeal
from assent_agents.evidence.agent import CaseContext
from assent_retrieval.search import Hit

PT = Hit(
    uuid.uuid4(),
    "Completed 6 weeks of physical therapy without relief.",
    date(2026, 8, 1),
    "DocumentReference",
    "n1",
    1.0,
)
OLD = Hit(uuid.uuid4(), "Already in the packet.", date(2026, 8, 2), "DocumentReference", "n2", 1.0)
CTX = CaseContext(order_date=date(2026, 9, 1), service="ESI", cpt="64483", icd10="M54.16")


async def test_draft_cites_only_new_verified_evidence_for_denied_criteria() -> None:
    seen: list[str] = []

    async def search(queries: list[str]) -> list[Hit]:
        return [OLD, PT]

    async def llm(tier: str, messages: list[dict[str, str]], schema: type[Any]) -> BaseModel:
        seen.append(messages[-1]["content"])
        return schema.model_validate(
            {
                "paragraphs": [
                    {
                        "criterion_key": "dur.conservative",
                        "text": "The patient completed six weeks of PT without relief.",
                        "citations": [
                            {
                                "chunk_id": "c1",
                                "quote": "Completed 6 weeks of physical therapy",
                                "claim": "PT done",
                            },
                            {"chunk_id": "c1", "quote": "not in the chunk", "claim": "made up"},
                        ],
                    },
                    {"criterion_key": "unrelated", "text": "ignored", "citations": []},
                ]
            }
        )

    def nli(premise: str, hypothesis: str) -> dict[str, float]:
        return {"entailment": 0.95, "contradiction": 0.0, "neutral": 0.05}

    d = await draft_appeal(
        [Denial("dur.conservative", "Failed conservative care", "1 excerpt provided, 2 required")],
        CTX,
        search,
        llm,
        nli,
        already_cited={str(OLD.chunk_id)},
    )
    assert "Already in the packet." not in seen[0]  # packet evidence is not offered again
    assert [c.quote for c in d.citations["dur.conservative"]] == [
        "Completed 6 weeks of physical therapy"
    ]
    assert d.dropped == 1 and "unrelated" not in d.citations
    assert "six weeks of PT" in d.text and "ignored" not in d.text
