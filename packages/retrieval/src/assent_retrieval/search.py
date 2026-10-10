"""Hybrid retrieval: full-text + dense, fused with Reciprocal Rank Fusion (ARCHITECTURE §6.6)."""

from collections.abc import Hashable, Sequence


def rrf[T: Hashable](rankings: Sequence[Sequence[T]], k: int = 60) -> list[T]:
    """Fuse ranked lists: score(d) = Σ 1/(k + rank). Ties keep first-seen order."""
    scores: dict[T, float] = {}
    for ranking in rankings:
        for rank, doc in enumerate(ranking, start=1):
            scores[doc] = scores.get(doc, 0.0) + 1.0 / (k + rank)
    order = {d: i for i, d in enumerate(scores)}
    return sorted(scores, key=lambda d: (-scores[d], order[d]))
