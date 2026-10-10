"""Hybrid retrieval: full-text + dense, fused with Reciprocal Rank Fusion (ARCHITECTURE §6.6)."""

import uuid
from collections.abc import Hashable, Sequence
from dataclasses import dataclass
from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from assent_retrieval import models


def rrf[T: Hashable](rankings: Sequence[Sequence[T]], k: int = 60) -> list[T]:
    """Fuse ranked lists: score(d) = Σ 1/(k + rank). Ties keep first-seen order."""
    scores: dict[T, float] = {}
    for ranking in rankings:
        for rank, doc in enumerate(ranking, start=1):
            scores[doc] = scores.get(doc, 0.0) + 1.0 / (k + rank)
    order = {d: i for i, d in enumerate(scores)}
    return sorted(scores, key=lambda d: (-scores[d], order[d]))


@dataclass(frozen=True)
class Hit:
    chunk_id: uuid.UUID
    text: str
    date: date | None
    resource_type: str
    resource_id: str
    score: float


# OR semantics: one absent word shouldn't zero out an otherwise strong chunk.
_FTS = """
    SELECT id FROM chart_chunks
    CROSS JOIN LATERAL (SELECT CAST(replace(CAST(plainto_tsquery('english', :q) AS text),
                                            '&', '|') AS tsquery) AS q) x
    WHERE case_id = :c AND tsv @@ x.q
    ORDER BY ts_rank_cd(tsv, x.q) DESC LIMIT :n
"""
_DENSE = """
    SELECT id FROM chart_chunks WHERE case_id = :c AND embedding IS NOT NULL
    ORDER BY embedding <=> CAST(:v AS vector) LIMIT :n
"""


async def hybrid_search(
    s: AsyncSession,
    case_id: uuid.UUID,
    queries: list[str],
    *,
    since: date | None = None,
    k: int = 8,
    per_list: int = 30,
) -> list[Hit]:
    rankings: list[list[uuid.UUID]] = []
    for q in queries:
        rankings.append(list(await s.scalars(text(_FTS), {"q": q, "c": case_id, "n": per_list})))
        vec = str(models.embed_query(q))
        rankings.append(
            list(await s.scalars(text(_DENSE), {"v": vec, "c": case_id, "n": per_list}))
        )
    fused = rrf(rankings)[:per_list]
    if not fused:
        return []
    rows = (
        await s.execute(
            text("""
        SELECT id, text_deid, effective_date, fhir_resource_type, fhir_resource_id
        FROM chart_chunks WHERE id = ANY(:ids)
    """),
            {"ids": fused},
        )
    ).all()
    rows = [
        r
        for r in rows
        if since is None or r.effective_date is None or r.effective_date.date() >= since
    ]  # lookback filter before rerank
    scores = models.rerank(queries[0], [r.text_deid for r in rows])
    hits = [
        Hit(
            r.id,
            r.text_deid,
            r.effective_date.date() if r.effective_date else None,
            r.fhir_resource_type,
            r.fhir_resource_id,
            sc,
        )
        for r, sc in zip(rows, scores, strict=True)
    ]
    return sorted(hits, key=lambda h: -h.score)[:k]
