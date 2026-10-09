import base64
import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select, tuple_

from assent_api.deps import CurrentUser, Session
from assent_api.models import Case, CaseStatus
from assent_api.schemas import CaseOut, Page

router = APIRouter(prefix="/api/v1/cases", tags=["cases"])


@router.get("")
async def list_cases(
    user: CurrentUser,
    session: Session,
    status_: Annotated[CaseStatus | None, Query(alias="status")] = None,
    service: str | None = None,
    cursor: str | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> Page[CaseOut]:
    q = select(Case).where(Case.org_id == user.org)  # org scoping on every query
    if status_:
        q = q.where(Case.status == status_)
    if service:
        q = q.where(Case.service_family == service)
    if cursor:
        ts, cid = _decode_cursor(cursor)
        q = q.where(tuple_(Case.created_at, Case.id) < tuple_(ts, cid))
    rows = (
        await session.scalars(q.order_by(Case.created_at.desc(), Case.id.desc()).limit(limit + 1))
    ).all()
    more = len(rows) > limit
    rows = rows[:limit]
    nxt = _encode_cursor(rows[-1].created_at, rows[-1].id) if more else None
    return Page[CaseOut](items=[CaseOut.model_validate(r) for r in rows], next_cursor=nxt)


def _encode_cursor(ts: datetime, cid: uuid.UUID) -> str:
    return base64.urlsafe_b64encode(f"{ts.isoformat()}|{cid}".encode()).decode()


def _decode_cursor(c: str) -> tuple[datetime, uuid.UUID]:
    try:
        ts, cid = base64.urlsafe_b64decode(c.encode()).decode().split("|")
        return datetime.fromisoformat(ts), uuid.UUID(cid)
    except ValueError:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Invalid cursor") from None
