"""Local models, loaded once per process from HF_HOME (on D:). Patient text never leaves."""

import math
from functools import lru_cache
from typing import Any

EMBED_MODEL = "BAAI/bge-small-en-v1.5"  # 384-d; bge-m3 (1024-d) on bigger hardware
RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
NLI_MODEL = "cross-encoder/nli-deberta-v3-base"
_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


@lru_cache
def _embedder() -> Any:
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(EMBED_MODEL, device="cpu")


@lru_cache
def _cross(name: str) -> Any:
    from sentence_transformers import CrossEncoder

    return CrossEncoder(name, device="cpu")


def embed_passages(texts: list[str]) -> list[list[float]]:
    vecs = _embedder().encode(texts, normalize_embeddings=True, batch_size=16)
    return [list(map(float, v)) for v in vecs]


def embed_query(text: str) -> list[float]:
    return embed_passages([_QUERY_PREFIX + text])[0]


def rerank(query: str, passages: list[str]) -> list[float]:
    if not passages:
        return []
    return [float(s) for s in _cross(RERANK_MODEL).predict([(query, p) for p in passages])]


def nli(premise: str, hypothesis: str) -> dict[str, float]:
    """Label probabilities for (premise ⇒ hypothesis)."""
    model = _cross(NLI_MODEL)
    logits = [float(x) for x in model.predict([(premise, hypothesis)])[0]]
    m = max(logits)
    exp = [math.exp(x - m) for x in logits]
    total = sum(exp)
    labels = model.config.id2label
    return {labels[i].lower(): e / total for i, e in enumerate(exp)}
