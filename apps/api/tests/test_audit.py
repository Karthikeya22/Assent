from datetime import UTC, datetime

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from assent_api.db import SessionLocal
from assent_api.services import audit
from assent_api.services.audit import GENESIS, find_break, row_hash


def _row(i: int, after: dict[str, object]) -> dict[str, object]:
    return {
        "id": i,
        "actor_id": None,
        "action": "verdict.override",
        "entity": "evidence_verdict",
        "entity_id": f"v{i}",
        "before_json": None,
        "after_json": after,
        "ts": datetime(2026, 10, 9, 12, i, tzinfo=UTC),
    }


def _chain(n: int) -> list[dict[str, object]]:
    rows, prev = [], GENESIS
    for i in range(1, n + 1):
        r = _row(i, {"verdict": "met", "n": i})
        r["hash_prev"], r["hash"] = prev, row_hash(prev, r)
        prev = str(r["hash"])
        rows.append(r)
    return rows


def test_row_hash_ignores_key_order() -> None:
    a = {"x": 1, "y": {"b": 2, "a": 1}}
    b = {"y": {"a": 1, "b": 2}, "x": 1}
    assert row_hash(GENESIS, a) == row_hash(GENESIS, b)


def test_row_hash_excludes_its_own_hash_fields() -> None:
    r = _row(1, {"k": "v"})
    assert row_hash(GENESIS, r) == row_hash(GENESIS, {**r, "hash": "x", "hash_prev": "y"})


def test_intact_chain_has_no_break() -> None:
    assert find_break(_chain(3)) is None


def test_edited_payload_is_detected_at_that_row() -> None:
    rows = _chain(3)
    rows[1]["after_json"] = {"verdict": "not_met", "n": 2}
    assert find_break(rows) == 2


def test_deleted_row_is_detected_at_the_next_row() -> None:
    rows = _chain(3)
    del rows[1]
    assert find_break(rows) == 3


async def test_db_append_chains_and_verifies() -> None:
    async with SessionLocal() as s:
        for i in range(3):
            await audit.append(
                s, actor_id=None, action="test", entity="case", entity_id=str(i), after={"i": i}
            )
        await s.commit()
        assert await audit.verify_chain(s) is None


async def test_db_rejects_audit_mutation() -> None:
    async with SessionLocal() as s:
        await audit.append(s, actor_id=None, action="test", entity="case", entity_id="1")
        await s.commit()
        with pytest.raises(DBAPIError, match="append-only"):
            await s.execute(text("UPDATE audit_log SET action = 'tampered'"))
        await s.rollback()
        with pytest.raises(DBAPIError, match="append-only"):
            await s.execute(text("DELETE FROM audit_log"))
