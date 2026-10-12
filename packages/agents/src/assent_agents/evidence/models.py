from typing import Literal

from pydantic import BaseModel, Field

VerdictLabel = Literal["met", "not_met", "insufficient"]


class CitationOut(BaseModel):
    """What the LLM returns: a chunk and a quote copied from it."""

    chunk_id: str
    quote: str = Field(description="Exact substring copied from the chunk")
    claim: str = Field(description="One plain sentence: the fact this quote establishes")


class VerdictOut(BaseModel):
    """Structured output of one evidence agent (ARCHITECTURE §6.5)."""

    verdict: VerdictLabel
    confidence: float = Field(ge=0, le=1)
    rationale: str = Field(max_length=600)
    citations: list[CitationOut]


class Citation(BaseModel):
    chunk_id: str
    quote: str
    claim: str = ""
    start: int | None = None  # offsets into the chunk text, once located
    end: int | None = None
    verbatim_ok: bool = False
    support: float | None = None  # NLI P(passage entails claim); 0 if from flagged text
    judged: bool = False  # NLI rejected it; the LLM judge confirmed the passage supports it


class Verdict(BaseModel):
    criterion_key: str
    verdict: VerdictLabel
    confidence: float
    rationale: str
    citations: list[Citation]
    downgraded: str | None = None  # why the verifier turned this into `insufficient`
    original: VerdictLabel | None = None
