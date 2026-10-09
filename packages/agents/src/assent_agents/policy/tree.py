"""Criteria Graph: a typed AND/OR/N-of-M tree of atomic criteria, each linked to its policy text."""

from collections.abc import Iterator
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

Kind = Literal["AND", "OR", "N_OF_M", "LEAF"]
EvidenceType = Literal[
    "diagnosis",
    "duration",
    "assessment",
    "imaging_finding",
    "prior_therapy",
    "contraindication",
    "procedure_history",
]


class Node(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str = Field(pattern=r"^[a-z][a-z0-9_.]*$")
    kind: Kind
    label: str
    n_required: int | None = None
    evidence_type: EvidenceType | None = None
    threshold: dict[str, Any] | None = None
    lookback_days: int | None = None
    source_quote: str | None = None  # verbatim substring of the policy version's raw_text
    children: list["Node"] = []

    @model_validator(mode="after")
    def _shape(self) -> Self:
        if self.kind == "LEAF":
            if self.evidence_type is None or self.children:
                raise ValueError(f"{self.key}: a LEAF needs evidence_type and no children")
        else:
            if not self.children or self.evidence_type is not None:
                raise ValueError(f"{self.key}: {self.kind} needs children and no evidence_type")
        if self.kind == "N_OF_M":
            if self.n_required is None or not 1 <= self.n_required <= len(self.children):
                raise ValueError(f"{self.key}: n_required must be 1..{len(self.children)}")
        return self

    def walk(self) -> Iterator["Node"]:
        yield self
        for c in self.children:
            yield from c.walk()


class Excluded(BaseModel):
    """Policy text deliberately left out of the evidence tree, with the reason."""

    quote: str
    reason: str


class CriteriaTree(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str
    version: int
    root: Node
    excluded: list[Excluded] = []

    def nodes(self) -> list[Node]:
        return list(self.root.walk())

    def leaves(self) -> list[Node]:
        return [n for n in self.root.walk() if n.kind == "LEAF"]

    def validate_against(self, raw_text: str) -> list[str]:
        errs: list[str] = []
        seen: set[str] = set()
        for n in self.root.walk():
            if n.key in seen:
                errs.append(f"duplicate key '{n.key}'")
            seen.add(n.key)
            if n.source_quote is not None and n.source_quote not in raw_text:
                errs.append(f"{n.key}: quote not found verbatim: {n.source_quote[:80]!r}")
        errs += [
            f"excluded quote not found: {x.quote[:80]!r}"
            for x in self.excluded
            if x.quote not in raw_text
        ]
        return errs

    def spans(self, raw_text: str) -> dict[str, tuple[int, int]]:
        out = {}
        for n in self.root.walk():
            if n.source_quote and (i := raw_text.find(n.source_quote)) >= 0:
                out[n.key] = (i, i + len(n.source_quote))
        return out
