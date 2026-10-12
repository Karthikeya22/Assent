import json
from datetime import date, timedelta
from pathlib import Path

from sqlalchemy import text

from assent_api.db import SessionLocal
from assent_api.models import Case, Patient, User
from assent_fhir.timeline import TimelineEvent
from assent_retrieval.index import index_case
from assent_retrieval.search import hybrid_search

BENCH = Path(__file__).resolve().parents[3] / "data" / "bench" / "esi"


def _events(case_id: str) -> tuple[list[TimelineEvent], dict]:  # type: ignore[type-arg]
    rec = json.loads((BENCH / f"{case_id}.json").read_text("utf-8"))
    events = [
        TimelineEvent(
            "DocumentReference",
            f"note-{i}",
            date.fromisoformat(n["date"]),
            "note",
            n["title"],
            n["text"],
        )
        for i, n in enumerate(rec["notes"])
    ]
    return events, rec["facts"]


async def test_index_and_hybrid_search_finds_the_pt_sentence(users: dict[str, User]) -> None:
    # Pick a clean case whose conservative-care fact is documented.
    cid = next(
        p.stem
        for p in sorted(BENCH.glob("esi-*.json"))
        if (f := json.loads(p.read_text("utf-8"))["facts"])["difficulty"] == "clean"
        and f["gold"]["dur.conservative"] == "met"
    )
    events, facts = _events(cid)
    pt_sentence = next(s["text"] for s in facts["statements"] if s["leaf"] == "dur.conservative")

    async with SessionLocal() as s:
        p = Patient(fhir_id="x", display_name_synthetic="X", birth_year=1950, sex="female")
        s.add(p)
        await s.flush()
        case = Case(
            org_id=users["coordinator"].org_id,
            patient_id=p.id,
            service_family="esi",
            cpt_codes=["64483"],
            icd10_codes=["M54.16"],
        )
        s.add(case)
        await s.flush()
        chunks = await index_case(s, case.id, events, deidentify=lambda t: t)
        await s.commit()
        assert len(chunks) >= len(events)

        hits = await hybrid_search(
            s,
            case.id,
            [
                "Failure of 4 weeks of noninvasive conservative care",
                "physical therapy medication NSAID tried failed",
            ],
            k=3,
        )
        assert pt_sentence in hits[0].text
        assert hits[0].resource_type == "DocumentReference"

        # The lookback filter drops everything older than `since`.
        future = await hybrid_search(
            s,
            case.id,
            ["physical therapy"],
            since=date.fromisoformat(facts["order_date"]) + timedelta(days=1),
        )
        assert future == []

        # Re-index with the same chart: rows are reused (same ids, no re-embedding).
        again = await index_case(s, case.id, events, deidentify=lambda t: t)
        await s.commit()
        assert {c.id for c in again} == {c.id for c in chunks}

        # Changed chart: old rows are superseded, never deleted; search sees only the new ones.
        changed = [
            *events[:-1],
            TimelineEvent(
                "DocumentReference",
                "note-new",
                events[-1].date,
                "note",
                "Addendum",
                "Addendum: physical therapy completed.",
            ),
        ]
        new = await index_case(s, case.id, changed, deidentify=lambda t: t)
        await s.commit()
        total = await s.scalar(
            text("SELECT count(*) FROM chart_chunks WHERE case_id = :c"), {"c": case.id}
        )
        assert total == len(chunks) + len(new)
        hits = await hybrid_search(s, case.id, ["physical therapy addendum"], k=50)
        assert {h.chunk_id for h in hits} <= {c.id for c in new}
