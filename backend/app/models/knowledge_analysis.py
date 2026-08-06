from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, PhysicalIdMixin, utc_now


class KnowledgeAnalysisScope(PhysicalIdMixin, Base):
    __tablename__ = "knowledge_analysis_scopes"
    __table_args__ = (
        UniqueConstraint(
            "source_id",
            "external_system",
            "external_subject_id",
            "revision",
            name="uq_knowledge_analysis_scope_revision",
        ),
    )

    source_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_sources.id", ondelete="RESTRICT"), index=True
    )
    subject_type: Mapped[str] = mapped_column(String(64), index=True)
    external_system: Mapped[str] = mapped_column(String(64), index=True)
    external_subject_id: Mapped[str] = mapped_column(String(128), index=True)
    canonical_prefix: Mapped[str] = mapped_column(Text)
    matched_by: Mapped[list[str]] = mapped_column(JSON, default=list)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(32), default="resolved", index=True)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    supersedes_id: Mapped[str | None] = mapped_column(
        ForeignKey("knowledge_analysis_scopes.id", ondelete="RESTRICT"),
        nullable=True,
    )
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )
    valid_to: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )


class KnowledgeScopeIngestionRequest(PhysicalIdMixin, Base):
    __tablename__ = "knowledge_scope_ingestion_requests"
    __table_args__ = (
        UniqueConstraint(
            "scope_id",
            "idempotency_key",
            name="uq_knowledge_scope_ingestion_request_key",
        ),
    )

    scope_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_analysis_scopes.id", ondelete="RESTRICT"), index=True
    )
    ingestion_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_ingestions.id", ondelete="RESTRICT"), index=True
    )
    idempotency_key: Mapped[str] = mapped_column(String(255))
    request_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )


class KnowledgeDocumentVersion(PhysicalIdMixin, Base):
    __tablename__ = "knowledge_document_versions"
    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "raw_content_hash",
            name="uq_knowledge_document_version_raw_hash",
        ),
    )

    document_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_documents.id", ondelete="RESTRICT"), index=True
    )
    source_entry_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_source_entries.id", ondelete="RESTRICT"), index=True
    )
    source_generation_id: Mapped[str | None] = mapped_column(
        ForeignKey("knowledge_ingestions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    canonical_path: Mapped[str] = mapped_column(Text)
    raw_content_hash: Mapped[str] = mapped_column(String(64), index=True)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    source_modified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(String(32), default="available", index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )


class KnowledgeProcessingVersion(PhysicalIdMixin, Base):
    __tablename__ = "knowledge_processing_versions"
    __table_args__ = (
        UniqueConstraint(
            "document_version_id",
            "processor_fingerprint",
            name="uq_knowledge_processing_version_fingerprint",
        ),
    )

    document_version_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_document_versions.id", ondelete="RESTRICT"), index=True
    )
    processor_fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    extractor_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="processing", index=True)
    quality_result: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    supersedes_id: Mapped[str | None] = mapped_column(
        ForeignKey("knowledge_processing_versions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )
    activated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class KnowledgeAnalysisTemplateVersion(PhysicalIdMixin, Base):
    __tablename__ = "knowledge_analysis_template_versions"
    __table_args__ = (
        UniqueConstraint(
            "code", "version", name="uq_knowledge_analysis_template_code_version"
        ),
    )

    code: Mapped[str] = mapped_column(String(128), index=True)
    version: Mapped[int] = mapped_column(Integer)
    field_contracts: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    schema_registry: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    source_priorities: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    extractor_version: Mapped[str] = mapped_column(String(128))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )


class KnowledgeExtractionTask(PhysicalIdMixin, Base):
    __tablename__ = "knowledge_extraction_tasks"
    __table_args__ = (
        UniqueConstraint(
            "client_id",
            "idempotency_key",
            name="uq_knowledge_extraction_task_idempotency",
        ),
    )

    generic_task_id: Mapped[str] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), unique=True, index=True
    )
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="RESTRICT"), index=True
    )
    source_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_sources.id", ondelete="RESTRICT"), index=True
    )
    scope_id: Mapped[str | None] = mapped_column(
        ForeignKey("knowledge_analysis_scopes.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    template_version_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_analysis_template_versions.id", ondelete="RESTRICT"),
        index=True,
    )
    parent_task_id: Mapped[str | None] = mapped_column(
        ForeignKey("knowledge_extraction_tasks.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    client_id: Mapped[str] = mapped_column(String(128), index=True)
    idempotency_key: Mapped[str] = mapped_column(String(255))
    request_hash: Mapped[str] = mapped_column(String(64))
    subject_external_id: Mapped[str] = mapped_column(String(128), index=True)
    request_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(32), default="queued", index=True)
    stage: Mapped[str] = mapped_column(String(32), default="queued", index=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    error_details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    result_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class KnowledgeExtractionTaskEvent(PhysicalIdMixin, Base):
    __tablename__ = "knowledge_extraction_task_events"
    __table_args__ = (
        UniqueConstraint(
            "extraction_task_id",
            "sequence",
            name="uq_knowledge_extraction_task_event_sequence",
        ),
    )

    extraction_task_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_extraction_tasks.id", ondelete="CASCADE"), index=True
    )
    sequence: Mapped[int] = mapped_column(Integer)
    stage: Mapped[str] = mapped_column(String(32), index=True)
    event_type: Mapped[str] = mapped_column(String(128), index=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )


class KnowledgeExtractionTaskDocument(PhysicalIdMixin, Base):
    __tablename__ = "knowledge_extraction_task_documents"
    __table_args__ = (
        UniqueConstraint(
            "extraction_task_id",
            "source_entry_id",
            name="uq_knowledge_extraction_task_document_entry",
        ),
    )

    extraction_task_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_extraction_tasks.id", ondelete="CASCADE"), index=True
    )
    source_entry_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_source_entries.id", ondelete="RESTRICT"), index=True
    )
    document_id: Mapped[str | None] = mapped_column(
        ForeignKey("knowledge_documents.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    document_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("knowledge_document_versions.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    processing_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("knowledge_processing_versions.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    canonical_path: Mapped[str] = mapped_column(Text)
    manifest_status: Mapped[str] = mapped_column(String(64), index=True)
    extraction_status: Mapped[str] = mapped_column(
        String(64), default="pending", index=True
    )
    failure_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    excluded_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    checkpoint: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class KnowledgeFieldCandidate(PhysicalIdMixin, Base):
    __tablename__ = "knowledge_field_candidates"

    extraction_task_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_extraction_tasks.id", ondelete="CASCADE"), index=True
    )
    block_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("knowledge_block_versions.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    field_code: Mapped[str] = mapped_column(String(128), index=True)
    value_json: Mapped[Any] = mapped_column(JSON)
    option_external_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    confidence: Mapped[float] = mapped_column(Float)
    effective_from: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    effective_to: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    aggregation_status: Mapped[str] = mapped_column(
        String(32), default="candidate", index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )


class KnowledgeCandidateEvidence(PhysicalIdMixin, Base):
    __tablename__ = "knowledge_candidate_evidence"

    candidate_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_field_candidates.id", ondelete="CASCADE"), index=True
    )
    document_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_documents.id", ondelete="RESTRICT"), index=True
    )
    document_version_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_document_versions.id", ondelete="RESTRICT"), index=True
    )
    chunk_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_chunks.id", ondelete="RESTRICT"), index=True
    )
    resource_uri: Mapped[str] = mapped_column(Text)
    canonical_path: Mapped[str] = mapped_column(Text)
    location: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    excerpt: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )


class KnowledgeFieldConflict(PhysicalIdMixin, Base):
    __tablename__ = "knowledge_field_conflicts"

    extraction_task_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_extraction_tasks.id", ondelete="CASCADE"), index=True
    )
    field_code: Mapped[str] = mapped_column(String(128), index=True)
    candidate_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    reason_code: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )


class KnowledgeBlockVersion(PhysicalIdMixin, Base):
    __tablename__ = "knowledge_block_versions"

    processing_version_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_processing_versions.id", ondelete="RESTRICT"), index=True
    )
    subject_external_system: Mapped[str] = mapped_column(String(64), index=True)
    subject_external_id: Mapped[str] = mapped_column(String(128), index=True)
    fact_key: Mapped[str] = mapped_column(String(128), index=True)
    value_json: Mapped[Any] = mapped_column(JSON)
    evidence_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    supersedes_id: Mapped[str | None] = mapped_column(
        ForeignKey("knowledge_block_versions.id", ondelete="RESTRICT"), nullable=True
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )


class KnowledgeBlockApplicability(PhysicalIdMixin, Base):
    __tablename__ = "knowledge_block_applicabilities"

    block_version_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_block_versions.id", ondelete="RESTRICT"), index=True
    )
    effective_from: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    effective_to: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    management_status: Mapped[str] = mapped_column(
        String(32), default="active", index=True
    )
    scope_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    supersedes_id: Mapped[str | None] = mapped_column(
        ForeignKey("knowledge_block_applicabilities.id", ondelete="RESTRICT"),
        nullable=True,
    )
    change_reason: Mapped[str] = mapped_column(String(255))
    audit_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )
