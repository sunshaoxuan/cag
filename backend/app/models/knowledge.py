from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
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
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator

from app.models.base import Base, PhysicalIdMixin, utc_now


class EmbeddingType(TypeDecorator[list[float]]):
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(Vector(1024))
        return dialect.type_descriptor(JSON())


class KnowledgeStatus:
    DRAFT = "draft"
    INDEXING = "indexing"
    READY = "ready"
    APPROVED = "approved"
    FAILED = "failed"
    DISABLED = "disabled"


class MemoryStatus:
    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"
    DEPRECATED = "deprecated"


class Tenant(PhysicalIdMixin, Base):
    __tablename__ = "tenants"

    code: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    projects = relationship("Project", back_populates="tenant")


class Product(PhysicalIdMixin, Base):
    __tablename__ = "products"

    code: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    versions = relationship("ProductVersion", back_populates="product")


class ProductVersion(PhysicalIdMixin, Base):
    __tablename__ = "product_versions"

    product_id: Mapped[str] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    version: Mapped[str] = mapped_column(String(128), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    product = relationship("Product", back_populates="versions")
    projects = relationship("Project", back_populates="product_version")


class KnowledgeSource(PhysicalIdMixin, Base):
    __tablename__ = "knowledge_sources"

    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    tenant_id: Mapped[str | None] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True
    )
    product_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("product_versions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255))
    root_path: Mapped[str] = mapped_column(Text)
    scope: Mapped[str] = mapped_column(String(32), default="tenant", index=True)
    status: Mapped[str] = mapped_column(
        String(32), default=KnowledgeStatus.DRAFT, index=True
    )
    source_commit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    index_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    approved_for_codex: Mapped[bool] = mapped_column(Boolean, default=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    documents = relationship(
        "KnowledgeDocument", back_populates="source", cascade="all, delete-orphan"
    )


class KnowledgeIngestion(PhysicalIdMixin, Base):
    __tablename__ = "knowledge_ingestions"

    source_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_sources.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(32), default="queued", index=True)
    next_event_sequence: Mapped[int] = mapped_column(Integer, default=1)
    files_seen: Mapped[int] = mapped_column(Integer, default=0)
    chunks_written: Mapped[int] = mapped_column(Integer, default=0)
    rejected_files: Mapped[int] = mapped_column(Integer, default=0)
    unchanged_files: Mapped[int] = mapped_column(Integer, default=0)
    vectors_reused: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    events = relationship(
        "KnowledgeIngestionEvent",
        back_populates="ingestion",
        cascade="all, delete-orphan",
        order_by="KnowledgeIngestionEvent.sequence",
    )


class KnowledgeIngestionEvent(PhysicalIdMixin, Base):
    __tablename__ = "knowledge_ingestion_events"

    ingestion_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_ingestions.id", ondelete="CASCADE"), index=True
    )
    sequence: Mapped[int] = mapped_column(Integer)
    type: Mapped[str] = mapped_column(String(128), index=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    ingestion = relationship("KnowledgeIngestion", back_populates="events")


class KnowledgeDocument(PhysicalIdMixin, Base):
    __tablename__ = "knowledge_documents"
    __table_args__ = (
        UniqueConstraint(
            "source_id",
            "canonical_path",
            name="uq_knowledge_documents_source_path",
        ),
    )

    source_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_sources.id", ondelete="CASCADE"), index=True
    )
    canonical_path: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    language: Mapped[str] = mapped_column(String(32), default="text")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    source = relationship("KnowledgeSource", back_populates="documents")
    chunks = relationship(
        "KnowledgeChunk", back_populates="document", cascade="all, delete-orphan"
    )


class KnowledgeChunk(PhysicalIdMixin, Base):
    __tablename__ = "knowledge_chunks"
    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "ordinal",
            name="uq_knowledge_chunks_document_ordinal",
        ),
    )

    document_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_documents.id", ondelete="CASCADE"), index=True
    )
    tenant_id: Mapped[str | None] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True
    )
    product_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("product_versions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    scope: Mapped[str] = mapped_column(String(32), index=True)
    ordinal: Mapped[int] = mapped_column(Integer)
    content_ciphertext: Mapped[str] = mapped_column(Text)
    search_text: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    token_count: Mapped[int] = mapped_column(Integer)
    embedding: Mapped[list[float]] = mapped_column(EmbeddingType())
    embedding_model: Mapped[str] = mapped_column(String(255))
    embedding_dimensions: Mapped[int] = mapped_column(Integer, default=1024)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    document = relationship("KnowledgeDocument", back_populates="chunks")


class MemoryCandidate(PhysicalIdMixin, Base):
    __tablename__ = "memory_candidates"

    task_id: Mapped[str | None] = mapped_column(
        ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True, index=True
    )
    tenant_id: Mapped[str | None] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True
    )
    product_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("product_versions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    scope: Mapped[str] = mapped_column(String(32), default="tenant", index=True)
    kind: Mapped[str] = mapped_column(String(64), default="semantic")
    title: Mapped[str] = mapped_column(String(255))
    content_ciphertext: Mapped[str] = mapped_column(Text)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(
        String(32), default=MemoryStatus.PROPOSED, index=True
    )
    supersedes_id: Mapped[str | None] = mapped_column(
        ForeignKey("memory_candidates.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class KnowledgeUsage(PhysicalIdMixin, Base):
    __tablename__ = "knowledge_usages"

    task_id: Mapped[str] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), index=True
    )
    chunk_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_chunks.id", ondelete="CASCADE"), index=True
    )
    score: Mapped[float] = mapped_column(Float)
    rank: Mapped[int] = mapped_column(Integer)
    injected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )


class KnowledgeEvaluation(PhysicalIdMixin, Base):
    __tablename__ = "knowledge_evaluations"

    task_id: Mapped[str | None] = mapped_column(
        ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True, index=True
    )
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    passed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class RiskRecord(PhysicalIdMixin, Base):
    __tablename__ = "risk_records"

    code: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    framework: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32), default="open")
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class DataQualityMetric(PhysicalIdMixin, Base):
    __tablename__ = "data_quality_metrics"

    source_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_sources.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(128))
    value: Mapped[float] = mapped_column(Float)
    measured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )


class KnowledgeConflict(PhysicalIdMixin, Base):
    __tablename__ = "knowledge_conflicts"

    left_chunk_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_chunks.id", ondelete="CASCADE")
    )
    right_chunk_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_chunks.id", ondelete="CASCADE")
    )
    status: Mapped[str] = mapped_column(String(32), default="open")
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
