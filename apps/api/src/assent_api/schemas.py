import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from assent_api.models import CaseStatus, Role, Urgency


class LoginIn(BaseModel):
    # Only used for lookup, so no format validation (EmailStr also rejects reserved TLDs).
    email: str = Field(max_length=320)
    password: str = Field(max_length=256)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    org_id: uuid.UUID
    email: str
    name: str
    role: Role


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105
    expires_in: int
    user: UserOut


class CaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    patient_id: uuid.UUID
    service_family: str
    cpt_codes: list[str]
    icd10_codes: list[str]
    status: CaseStatus
    urgency: Urgency
    sla_due_at: datetime | None
    assignee_id: uuid.UUID | None
    readiness_score: float | None
    denial_risk: float | None
    created_at: datetime
    patient_name: str = ""


class Page[T](BaseModel):
    items: list[T]
    next_cursor: str | None
