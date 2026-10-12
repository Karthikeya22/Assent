import base64
import hashlib
import hmac
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import jwt
from pydantic import BaseModel, ValidationError

from assent_api.models import Role
from assent_api.settings import get_settings

_ALG = "HS256"
_N, _R, _P = 2**14, 8, 1  # scrypt cost; stdlib, so no bcrypt/passlib dependency


class InvalidToken(Exception):
    pass


class TokenClaims(BaseModel):
    sub: uuid.UUID
    org: uuid.UUID
    role: Role
    exp: datetime


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode()


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s.encode())


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.scrypt(password.encode(), salt=salt, n=_N, r=_R, p=_P)
    return f"scrypt${_N}${_R}${_P}${_b64(salt)}${_b64(dk)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, n, r, p, salt, dk = stored.split("$")
        got = hashlib.scrypt(password.encode(), salt=_unb64(salt), n=int(n), r=int(r), p=int(p))
    except ValueError:
        return False
    return hmac.compare_digest(got, _unb64(dk))


# Verified against when the email is unknown, so both failure paths cost the same time.
DUMMY_HASH = hash_password(secrets.token_hex(8))


def create_access_token(
    user_id: uuid.UUID, org_id: uuid.UUID, role: Role, ttl_minutes: int | None = None
) -> str:
    ttl = get_settings().jwt_ttl_minutes if ttl_minutes is None else ttl_minutes
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "org": str(org_id),
        "role": role.value,
        "iat": now,
        "exp": now + timedelta(minutes=ttl),
    }
    return jwt.encode(payload, get_settings().jwt_secret, algorithm=_ALG)


def decode_token(token: str) -> TokenClaims:
    try:
        raw = jwt.decode(
            token,
            get_settings().jwt_secret,
            algorithms=[_ALG],
            options={"require": ["exp", "sub"]},
        )
        return TokenClaims.model_validate(raw)
    except (jwt.PyJWTError, ValidationError) as e:
        raise InvalidToken(str(e)) from e
