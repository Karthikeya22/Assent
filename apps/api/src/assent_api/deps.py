from collections.abc import Callable, Coroutine
from typing import Annotated, Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from assent_api.db import get_session
from assent_api.models import Role
from assent_api.security import InvalidToken, TokenClaims, decode_token

_bearer = HTTPBearer(auto_error=False)

Session = Annotated[AsyncSession, Depends(get_session)]


async def current_user(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> TokenClaims:
    # shortcut: trusts the 15-min JWT without a DB lookup, so a deleted user keeps access until
    # expiry; add a users/revocation check if tokens get longer-lived.
    if creds is None:
        raise _unauthorized("Not authenticated")
    try:
        return decode_token(creds.credentials)
    except InvalidToken:
        raise _unauthorized("Invalid or expired token") from None


CurrentUser = Annotated[TokenClaims, Depends(current_user)]


def require_role(*roles: Role) -> Callable[..., Coroutine[Any, Any, TokenClaims]]:
    async def dep(user: CurrentUser) -> TokenClaims:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient role")
        return user

    return dep


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status.HTTP_401_UNAUTHORIZED, detail, headers={"WWW-Authenticate": "Bearer"}
    )
