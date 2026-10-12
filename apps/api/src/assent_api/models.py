"""Postgres schema (ARCHITECTURE.md §4). One file: the tables are read together, not apart."""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    ARRAY,
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Identity,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from assent_api.settings import get_settings


class Base(DeclarativeBase):
    type_annotation_map = {dict[str, Any]: JSONB, uuid.UUID: UUID(as_uuid=True)}  # noqa: RUF012


def _enum(e: type[StrEnum]) -> SAEnum:
    # VARCHAR + CHECK instead of native PG enums: adding a value never needs an ALTER TYPE.
    return SAEnum(
        e,
        native_enum=False,
        create_constraint=True,
        length=32,
        values_callable=lambda x: [m.value for m in x],
    )


def _pk() -> Mapped[uuid.UUID]:
    return mapped_column(primary_key=True, default=uuid.uuid4)


def _now() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now())


class Role(StrEnum):
    coordinator = "coordinator"
    clinician = "clinician"
    policy_admin = "policy_admin"
    auditor = "auditor"


class PolicyKind(StrEnum):
    LCD = "LCD"
    NCD = "NCD"


class VersionStatus(StrEnum):
    draft = "draft"
    approved = "approved"
    retired = "retired"


class NodeKind(StrEnum):
    AND = "AND"
    OR = "OR"
    N_OF_M = "N_OF_M"
    LEAF = "LEAF"


class CaseStatus(StrEnum):
    new = "new"
    running = "running"
    needs_review = "needs_review"
    ready = "ready"
    submitted = "submitted"
    approved = "approved"
    denied = "denied"
    appealed = "appealed"


class Urgency(StrEnum):
    standard = "standard"
    expedited = "expedited"


class Verdict(StrEnum):
    met = "met"
    not_met = "not_met"
    insufficient = "insufficient"


class ObjectionStatus(StrEnum):
    rebutted = "rebutted"
    conceded = "conceded"
    open = "open"


class Split(StrEnum):
    dev = "dev"
    test = "test"


# --- org & users ---------------------------------------------------------------


class Organization(Base):
    __tablename__ = "organizations"
    id: Mapped[uuid.UUID] = _pk()
    name: Mapped[str] = mapped_column(String(200))


class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = _pk()
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    email: Mapped[str] = mapped_column(String(320), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    role: Mapped[Role] = mapped_column(_enum(Role))
    # Not in the spec's column list, but auth needs it.
    password_hash: Mapped[str] = mapped_column(String(255))


# --- policies ------------------------------------------------------------------


class Policy(Base):
    __tablename__ = "policies"
    id: Mapped[uuid.UUID] = _pk()
    payer: Mapped[str] = mapped_column(String(100))
    kind: Mapped[PolicyKind] = mapped_column(_enum(PolicyKind))
    source_id: Mapped[str] = mapped_column(String(32), unique=True)
    title: Mapped[str] = mapped_column(Text)
    service_family: Mapped[str] = mapped_column(String(64), index=True)


class PolicyVersion(Base):
    __tablename__ = "policy_versions"
    id: Mapped[uuid.UUID] = _pk()
    policy_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("policies.id"), index=True)
    version: Mapped[str] = mapped_column(String(32))
    effective_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    raw_text: Mapped[str] = mapped_column(Text)
    source_url: Mapped[str] = mapped_column(Text)
    status: Mapped[VersionStatus] = mapped_column(_enum(VersionStatus), default=VersionStatus.draft)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    content_hash: Mapped[str] = mapped_column(String(64))


class CriteriaNode(Base):
    __tablename__ = "criteria_nodes"
    id: Mapped[uuid.UUID] = _pk()
    policy_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("policy_versions.id", ondelete="CASCADE"), index=True
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("criteria_nodes.id", ondelete="CASCADE")
    )
    key: Mapped[str] = mapped_column(String(64))
    kind: Mapped[NodeKind] = mapped_column(_enum(NodeKind))
    n_required: Mapped[int | None] = mapped_column(Integer)
    label: Mapped[str] = mapped_column(Text)
    evidence_type: Mapped[str | None] = mapped_column(String(32))
    threshold_json: Mapped[dict[str, Any] | None]
    lookback_days: Mapped[int | None] = mapped_column(Integer)
    policy_span_start: Mapped[int | None] = mapped_column(Integer)
    policy_span_end: Mapped[int | None] = mapped_column(Integer)
    order_index: Mapped[int] = mapped_column(Integer, default=0)


class PolicyDiff(Base):
    __tablename__ = "policy_diffs"
    id: Mapped[uuid.UUID] = _pk()
    from_version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("policy_versions.id"))
    to_version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("policy_versions.id"))
    diff_json: Mapped[dict[str, Any]]
    created_at: Mapped[datetime] = _now()


# --- patients & cases ----------------------------------------------------------


class Patient(Base):
    __tablename__ = "patients"
    id: Mapped[uuid.UUID] = _pk()
    fhir_id: Mapped[str] = mapped_column(String(64), unique=True)
    display_name_synthetic: Mapped[str] = mapped_column(String(200))
    birth_year: Mapped[int] = mapped_column(Integer)
    sex: Mapped[str] = mapped_column(String(16))


class Case(Base):
    __tablename__ = "cases"
    id: Mapped[uuid.UUID] = _pk()
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"))
    service_family: Mapped[str] = mapped_column(String(64))
    cpt_codes: Mapped[list[str]] = mapped_column(ARRAY(String(16)))
    icd10_codes: Mapped[list[str]] = mapped_column(ARRAY(String(16)))
    policy_version_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("policy_versions.id"))
    status: Mapped[CaseStatus] = mapped_column(
        _enum(CaseStatus), default=CaseStatus.new, index=True
    )
    urgency: Mapped[Urgency] = mapped_column(_enum(Urgency), default=Urgency.standard)
    sla_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    assignee_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    readiness_score: Mapped[float | None] = mapped_column(Float)
    denial_risk: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = _now()
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ChartChunk(Base):
    __tablename__ = "chart_chunks"
    __table_args__ = (
        Index(
            "ix_chart_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
        Index("ix_chart_chunks_tsv", "tsv", postgresql_using="gin"),
    )
    id: Mapped[uuid.UUID] = _pk()
    case_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cases.id", ondelete="CASCADE"), index=True
    )
    fhir_resource_type: Mapped[str] = mapped_column(String(64))
    fhir_resource_id: Mapped[str] = mapped_column(String(64))
    effective_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    text_deid: Mapped[str] = mapped_column(Text)
    char_offset: Mapped[int] = mapped_column(Integer, default=0)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(get_settings().embed_dim))
    tsv: Mapped[Any] = mapped_column(TSVECTOR, nullable=True)
    # Set when a re-index replaces this chunk. Superseded chunks are never deleted: past
    # verdicts' citations still point at them (audit trail); search ignores them.
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)


# --- runs & evidence -----------------------------------------------------------


class Run(Base):
    __tablename__ = "runs"
    id: Mapped[uuid.UUID] = _pk()
    case_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cases.id", ondelete="CASCADE"), index=True
    )
    trigger: Mapped[str] = mapped_column(String(16))  # auto|manual|rerun|appeal
    graph_version: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(16))
    started_at: Mapped[datetime] = _now()
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    langfuse_trace_id: Mapped[str | None] = mapped_column(String(64))


class RunStep(Base):
    __tablename__ = "run_steps"
    id: Mapped[uuid.UUID] = _pk()
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"), index=True)
    node: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16))
    started_at: Mapped[datetime] = _now()
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    model: Mapped[str | None] = mapped_column(String(100))
    prompt_version: Mapped[str | None] = mapped_column(String(32))
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    payload_json: Mapped[dict[str, Any] | None]


class EvidenceVerdict(Base):
    __tablename__ = "evidence_verdicts"
    id: Mapped[uuid.UUID] = _pk()
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"), index=True)
    criterion_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("criteria_nodes.id"))
    verdict: Mapped[Verdict] = mapped_column(_enum(Verdict))
    confidence: Mapped[float] = mapped_column(Float)
    rationale: Mapped[str] = mapped_column(Text)
    overridden_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    override_reason: Mapped[str | None] = mapped_column(Text)


class EvidenceCitation(Base):
    __tablename__ = "evidence_citations"
    id: Mapped[uuid.UUID] = _pk()
    verdict_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evidence_verdicts.id", ondelete="CASCADE"), index=True
    )
    chunk_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chart_chunks.id"))
    quote: Mapped[str] = mapped_column(Text)
    start_char: Mapped[int] = mapped_column(Integer)
    end_char: Mapped[int] = mapped_column(Integer)
    verbatim_ok: Mapped[bool] = mapped_column(Boolean)
    entailment_score: Mapped[float | None] = mapped_column(Float)


class Objection(Base):
    __tablename__ = "objections"
    id: Mapped[uuid.UUID] = _pk()
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"), index=True)
    criterion_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("criteria_nodes.id"))
    text: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(16))
    status: Mapped[ObjectionStatus] = mapped_column(
        _enum(ObjectionStatus), default=ObjectionStatus.open
    )
    rebuttal_text: Mapped[str | None] = mapped_column(Text)
    rebuttal_citation_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), default=list
    )


class GapTask(Base):
    __tablename__ = "gap_tasks"
    id: Mapped[uuid.UUID] = _pk()
    case_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cases.id", ondelete="CASCADE"), index=True
    )
    criterion_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("criteria_nodes.id"))
    title: Mapped[str] = mapped_column(Text)
    detail: Mapped[str] = mapped_column(Text)
    assignee_role: Mapped[Role] = mapped_column(_enum(Role))
    status: Mapped[str] = mapped_column(String(16), default="open")
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


# --- packets, submissions, appeals ---------------------------------------------


class Packet(Base):
    __tablename__ = "packets"
    id: Mapped[uuid.UUID] = _pk()
    case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cases.id"), index=True)
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("runs.id"))
    fhir_bundle_json: Mapped[dict[str, Any]]
    pdf_key: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    approved_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Submission(Base):
    __tablename__ = "submissions"
    id: Mapped[uuid.UUID] = _pk()
    packet_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("packets.id"), index=True)
    payer_endpoint: Mapped[str] = mapped_column(Text)
    submitted_at: Mapped[datetime] = _now()
    response_status: Mapped[str | None] = mapped_column(String(16))
    claim_response_json: Mapped[dict[str, Any] | None]
    denial_reason_code: Mapped[str | None] = mapped_column(String(32))
    denial_reason_text: Mapped[str | None] = mapped_column(Text)


class Appeal(Base):
    __tablename__ = "appeals"
    id: Mapped[uuid.UUID] = _pk()
    submission_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("submissions.id"), index=True)
    draft_text: Mapped[str] = mapped_column(Text)
    citations_json: Mapped[dict[str, Any]]
    status: Mapped[str] = mapped_column(String(16), default="draft")
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


# --- evals ---------------------------------------------------------------------


class EvalCase(Base):
    __tablename__ = "eval_cases"
    id: Mapped[uuid.UUID] = _pk()
    service_family: Mapped[str] = mapped_column(String(64))
    gold_json: Mapped[dict[str, Any]]
    seeded_defects_json: Mapped[dict[str, Any] | None]
    split: Mapped[Split] = mapped_column(_enum(Split))


class EvalRun(Base):
    __tablename__ = "eval_runs"
    id: Mapped[uuid.UUID] = _pk()
    git_sha: Mapped[str] = mapped_column(String(40))
    config_json: Mapped[dict[str, Any]]
    metrics_json: Mapped[dict[str, Any]]
    mlflow_run_id: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = _now()


# --- audit ---------------------------------------------------------------------


class AuditLog(Base):
    """Append-only and hash-chained. The migration adds a trigger that rejects UPDATE/DELETE."""

    __tablename__ = "audit_log"
    # Monotonic integer id gives the chain its order.
    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(64))
    entity: Mapped[str] = mapped_column(String(64))
    entity_id: Mapped[str] = mapped_column(String(64))
    before_json: Mapped[dict[str, Any] | None]
    after_json: Mapped[dict[str, Any] | None]
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    hash_prev: Mapped[str] = mapped_column(String(64))
    hash: Mapped[str] = mapped_column(String(64), unique=True)
