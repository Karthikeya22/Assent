"""Hash-chained, append-only audit log: hash = sha256(prev_hash + canonical_json(row))."""

import hashlib
import json
import uuid
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from assent_api.models import AuditLog

GENESIS = "0" * 64
_HASHED = ("actor_id", "action", "entity", "entity_id", "before_json", "after_json", "ts")
# Arbitrary constant: serializes appends so two writers can't both chain onto the same tail.
_LOCK_KEY = 0xA55E7


def row_hash(prev_hash: str, row: Mapping[str, Any]) -> str:
    payload = {k: row.get(k) for k in _HASHED}
    canon = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=_jsonable)
    return hashlib.sha256((prev_hash + canon).encode()).hexdigest()


def _jsonable(v: object) -> str:
    if isinstance(v, datetime):
        return v.astimezone(UTC).isoformat()
    return str(v)


def find_break(rows: Sequence[Mapping[str, Any]]) -> int | None:
    """Return the id of the first row whose hash or back-link doesn't match, else None."""
    prev = GENESIS
    for r in rows:
        if r["hash_prev"] != prev or r["hash"] != row_hash(prev, r):
            return int(r["id"])
        prev = r["hash"]
    return None


async def append(
    session: AsyncSession,
    *,
    actor_id: uuid.UUID | None,
    action: str,
    entity: str,
    entity_id: str,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
) -> AuditLog:
    await session.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": _LOCK_KEY})
    tail = await session.scalar(select(AuditLog.hash).order_by(AuditLog.id.desc()).limit(1))
    prev = tail or GENESIS
    row = AuditLog(
        actor_id=actor_id,
        action=action,
        entity=entity,
        entity_id=entity_id,
        before_json=before,
        after_json=after,
        ts=datetime.now(UTC),
        hash_prev=prev,
    )
    row.hash = row_hash(prev, _as_dict(row))
    session.add(row)
    await session.flush()
    return row


async def verify_chain(session: AsyncSession) -> int | None:
    rows = (await session.scalars(select(AuditLog).order_by(AuditLog.id))).all()
    return find_break(
        [_as_dict(r) | {"id": r.id, "hash": r.hash, "hash_prev": r.hash_prev} for r in rows]
    )


def _as_dict(r: AuditLog) -> dict[str, Any]:
    return {k: getattr(r, k) for k in _HASHED}
