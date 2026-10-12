from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from assent_api.deps import Session
from assent_api.models import User
from assent_api.schemas import LoginIn, TokenOut, UserOut
from assent_api.security import DUMMY_HASH, create_access_token, verify_password
from assent_api.settings import get_settings

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/token")
async def login(body: LoginIn, session: Session) -> TokenOut:
    user = await session.scalar(select(User).where(User.email == body.email.lower()))
    ok = verify_password(body.password, user.password_hash if user else DUMMY_HASH)
    if user is None or not ok:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    return TokenOut(
        access_token=create_access_token(user.id, user.org_id, user.role),
        expires_in=get_settings().jwt_ttl_minutes * 60,
        user=UserOut.model_validate(user),
    )
