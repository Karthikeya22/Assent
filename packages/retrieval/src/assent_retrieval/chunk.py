"""Sentence-aligned chunking (~400 tokens, 15% overlap). Chunks are exact slices of the input."""

import re
from dataclasses import dataclass

_BOUNDARY = re.compile(r"(?<=[.!?])\s+|\n+")


@dataclass(frozen=True)
class Chunk:
    text: str
    char_offset: int


def _sentences(text: str) -> list[tuple[int, int]]:
    spans, start = [], 0
    for m in _BOUNDARY.finditer(text):
        if text[start : m.start()].strip():
            spans.append((start, m.start()))
        start = m.end()
    if text[start:].strip():
        spans.append((start, len(text.rstrip())))
    return spans


def _tokens(s: str) -> int:
    return max(1, round(len(s.split()) * 1.3))  # shortcut: word-based estimate, no tokenizer


def chunk_text(text: str, max_tokens: int = 400, overlap: float = 0.15) -> list[Chunk]:
    sents = _sentences(text)
    out: list[Chunk] = []
    i = 0
    while i < len(sents):
        j, size = i, 0
        while j < len(sents) and (j == i or size + _tokens(text[slice(*sents[j])]) <= max_tokens):
            size += _tokens(text[slice(*sents[j])])
            j += 1
        start, end = sents[i][0], sents[j - 1][1]
        out.append(Chunk(text[start:end], start))
        if j == len(sents):
            break
        # Step back over trailing sentences worth ~overlap of this chunk, but always advance.
        back, carried = j, 0
        while back - 1 > i and carried < overlap * size:
            back -= 1
            carried += _tokens(text[slice(*sents[back])])
        i = back if overlap > 0 else j
    return out
