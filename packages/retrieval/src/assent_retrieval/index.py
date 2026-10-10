"""Per-case index: de-identified chunks + tsvector + embedding in chart_chunks (§6.3)."""

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from assent_fhir.timeline import TimelineEvent
from assent_retrieval import models
from assent_retrieval.chunk import chunk_text


@dataclass(frozen=True)
class IndexedChunk:
    id: uuid.UUID
    text: str  # de-identified; citations must quote this verbatim
    resource_type: str
    resource_id: str
    date: date
    title: str
    char_offset: int


def header(c: IndexedChunk) -> str:
    return f"{c.title} ({c.date:%m/%d/%Y})"


async def index_case(
    s: AsyncSession,
    case_id: uuid.UUID,
    events: list[TimelineEvent],
    deidentify: Callable[[str], str],
) -> list[IndexedChunk]:
    chunks = [
        IndexedChunk(
            uuid.uuid4(), c.text, e.resource_type, e.resource_id, e.date, e.title, c.char_offset
        )
        for e in events
        for c in chunk_text(deidentify(e.text))
    ]
    vecs = models.embed_passages([f"{header(c)}\n{c.text}" for c in chunks]) if chunks else []
    await s.execute(text("DELETE FROM chart_chunks WHERE case_id = :c"), {"c": case_id})
    if chunks:
        await s.execute(
            text("""
                INSERT INTO chart_chunks (id, case_id, fhir_resource_type, fhir_resource_id,
                    effective_date, text_deid, char_offset, embedding, tsv)
                VALUES (:id, :case_id, :rt, :rid, :d, :t, :off, CAST(:v AS vector),
                        to_tsvector('english', :h || ' ' || :t))
            """),
            [
                {
                    "id": c.id,
                    "case_id": case_id,
                    "rt": c.resource_type,
                    "rid": c.resource_id,
                    "d": c.date,
                    "t": c.text,
                    "off": c.char_offset,
                    "v": str(v),
                    "h": header(c),
                }
                for c, v in zip(chunks, vecs, strict=True)
            ],
        )
    return chunks
