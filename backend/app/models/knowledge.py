from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
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
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "source_key",
            name="uq_knowledge_sources_project_source_key",
        ),
    )

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
    source_type: Mapped[str] = mapped_column(
        String(32), default="local_directory", index=True
    )
    source_key: Mapped[str] = mapped_column(String(64), index=True)
    root_path: Mapped[str] = mapped_column(Text)
    reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    subpath: Mapped[str | None] = mapped_column(Text, nullable=True)
    credential_ref: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    credential_username: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    scope: Mapped[str] = mapped_column(String(32), default="tenant", index=True)
    status: Mapped[str] = mapped_column(
        String(32), default=KnowledgeStatus.DRAFT, index=True
    )
    source_commit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    index_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    processor_fingerprint: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )
    approved_for_codex: Mapped[bool] = mapped_column(Boolean, default=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_validated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_collected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    sync_mode: Mapped[str] = mapped_column(
        String(32), default="manual", index=True
    )
    sync_interval_minutes: Mapped[int] = mapped_column(Integer, default=60)
    next_sync_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    last_sync_attempt_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_content_change_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0)
    sync_lease_owner: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    sync_lease_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    documents = relationship(
        "KnowledgeDocument", back_populates="source", cascade="all, delete-orphan"
    )
    entries = relationship(
        "KnowledgeSourceEntry",
        back_populates="source",
        cascade="all, delete-orphan",
    )


class KnowledgeIngestion(PhysicalIdMixin, Base):
    __tablename__ = "knowledge_ingestions"

    source_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_sources.id", ondelete="CASCADE"), index=True
    )
    analysis_scope_id: Mapped[str | None] = mapped_column(
        String(),
        nullable=True,
        index=True,
    )
    scope_prefix: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_statuses: Mapped[list[str]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(32), default="queued", index=True)
    next_event_sequence: Mapped[int] = mapped_column(Integer, default=1)
    files_seen: Mapped[int] = mapped_column(Integer, default=0)
    chunks_written: Mapped[int] = mapped_column(Integer, default=0)
    rejected_files: Mapped[int] = mapped_column(Integer, default=0)
    skipped_files: Mapped[int] = mapped_column(Integer, default=0)
    unchanged_files: Mapped[int] = mapped_column(Integer, default=0)
    vectors_reused: Mapped[int] = mapped_column(Integer, default=0)
    duplicate_files: Mapped[int] = mapped_column(Integer, default=0)
    changed_files: Mapped[int] = mapped_column(Integer, default=0)
    removed_files: Mapped[int] = mapped_column(Integer, default=0)
    trigger: Mapped[str] = mapped_column(
        String(32), default="manual", index=True
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    rejection_archive_name: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    rejection_archive_sha256: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
    rejection_archive_created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    events = relationship(
        "KnowledgeIngestionEvent",
        back_populates="ingestion",
        cascade="all, delete-orphan",
        order_by="KnowledgeIngestionEvent.sequence",
    )
    rejections = relationship(
        "KnowledgeIngestionRejection",
        back_populates="ingestion",
        cascade="all, delete-orphan",
        order_by="KnowledgeIngestionRejection.created_at",
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


class KnowledgeIngestionRejection(PhysicalIdMixin, Base):
    __tablename__ = "knowledge_ingestion_rejections"
    __table_args__ = (
        UniqueConstraint(
            "ingestion_id",
            "relative_path",
            name="uq_knowledge_ingestion_rejections_ingestion_path",
        ),
    )

    ingestion_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_ingestions.id", ondelete="CASCADE"), index=True
    )
    relative_path: Mapped[str] = mapped_column(Text)
    entry_kind: Mapped[str] = mapped_column(
        String(32), default="file", index=True
    )
    disposition: Mapped[str] = mapped_column(String(32), index=True)
    extension: Mapped[str] = mapped_column(String(64), default="", index=True)
    file_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    reason_code: Mapped[str] = mapped_column(String(64), index=True)
    extractor: Mapped[str] = mapped_column(String(64), default="filesystem")
    error_type: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, index=True
    )
    ingestion = relationship(
        "KnowledgeIngestion", back_populates="rejections"
    )


class KnowledgeSourceEntry(PhysicalIdMixin, Base):
    __tablename__ = "knowledge_source_entries"
    __table_args__ = (
        UniqueConstraint(
            "source_id",
            "relative_path",
            name="uq_knowledge_source_entries_source_path",
        ),
    )

    source_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_sources.id", ondelete="CASCADE"),
        index=True,
    )
    relative_path: Mapped[str] = mapped_column(Text)
    entry_kind: Mapped[str] = mapped_column(
        String(32), default="file", index=True
    )
    extension: Mapped[str] = mapped_column(
        String(64), default="", index=True
    )
    file_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    modified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    processing_mode: Mapped[str] = mapped_column(
        String(32), default="metadata_only", index=True
    )
    processing_status: Mapped[str] = mapped_column(
        String(32), default="observed", index=True
    )
    reason_code: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )
    extractor: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
    extractor_version: Mapped[str | None] = mapped_column(
        String(32), nullable=True
    )
    present: Mapped[bool] = mapped_column(
        Boolean, default=True, index=True
    )
    last_seen_ingestion_id: Mapped[str | None] = mapped_column(
        ForeignKey("knowledge_ingestions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    processor_fingerprint: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )
    content_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )
    raw_content_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, index=True
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    removed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    source = relationship("KnowledgeSource", back_populates="entries")
    last_seen_ingestion = relationship("KnowledgeIngestion")
    documents = relationship(
        "KnowledgeDocument",
        back_populates="source_entry",
    )


class KnowledgeBaselineRun(PhysicalIdMixin, Base):
    __tablename__ = "knowledge_baseline_runs"

    source_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_sources.id", ondelete="CASCADE"), index=True
    )
    active_ingestion_id: Mapped[str | None] = mapped_column(
        ForeignKey("knowledge_ingestions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    schema_version: Mapped[str] = mapped_column(String(32))
    policy_version: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), index=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    item_count: Mapped[int] = mapped_column(Integer, default=0)
    manifest_sha256: Mapped[str] = mapped_column(String(64), index=True)
    lifecycle_counts: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    action_counts: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    format_counts: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, index=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    source = relationship("KnowledgeSource")
    active_ingestion = relationship("KnowledgeIngestion")
    items = relationship(
        "KnowledgeConversionManifestItem",
        back_populates="baseline_run",
        cascade="all, delete-orphan",
    )


class KnowledgeConversionManifestItem(PhysicalIdMixin, Base):
    __tablename__ = "knowledge_conversion_manifest_items"
    __table_args__ = (
        UniqueConstraint(
            "baseline_run_id",
            "source_entry_id",
            name="uq_conversion_manifest_run_entry",
        ),
    )

    baseline_run_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_baseline_runs.id", ondelete="CASCADE"),
        index=True,
    )
    source_entry_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_source_entries.id", ondelete="CASCADE"),
        index=True,
    )
    document_id: Mapped[str | None] = mapped_column(
        ForeignKey("knowledge_documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    relative_path: Mapped[str] = mapped_column(Text)
    extension: Mapped[str] = mapped_column(String(64), default="", index=True)
    lifecycle_status: Mapped[str] = mapped_column(String(32), index=True)
    conversion_action: Mapped[str] = mapped_column(String(32), index=True)
    decision_reason: Mapped[str] = mapped_column(String(64), index=True)
    capability: Mapped[str] = mapped_column(String(32), index=True)
    source_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )
    baseline_run = relationship("KnowledgeBaselineRun", back_populates="items")
    source_entry = relationship("KnowledgeSourceEntry")
    document = relationship("KnowledgeDocument")


class Artifact(PhysicalIdMixin, Base):
    __tablename__ = "knowledge_artifacts"

    sha256: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    byte_size: Mapped[int] = mapped_column(BigInteger)
    media_type: Mapped[str] = mapped_column(String(255))
    artifact_kind: Mapped[str] = mapped_column(String(32), index=True)
    retention_policy: Mapped[str] = mapped_column(
        String(32), default="knowledge_evidence", index=True
    )
    encryption: Mapped[str] = mapped_column(String(64), default="application_aes_gcm")
    status: Mapped[str] = mapped_column(
        String(32), default="available", index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, index=True
    )
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    replicas = relationship(
        "ObjectReplica", back_populates="artifact", cascade="all, delete-orphan"
    )
    locations = relationship(
        "ArtifactLocation", back_populates="artifact", cascade="all, delete-orphan"
    )


class ArtifactLocation(PhysicalIdMixin, Base):
    __tablename__ = "knowledge_artifact_locations"
    __table_args__ = (
        UniqueConstraint(
            "artifact_id",
            "source_entry_id",
            "location_type",
            name="uq_artifact_location_evidence",
        ),
    )

    artifact_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_artifacts.id", ondelete="CASCADE"), index=True
    )
    source_entry_id: Mapped[str | None] = mapped_column(
        ForeignKey("knowledge_source_entries.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    location_type: Mapped[str] = mapped_column(String(32), index=True)
    relative_path_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )
    artifact = relationship("Artifact", back_populates="locations")
    source_entry = relationship("KnowledgeSourceEntry")


class ObjectReplica(PhysicalIdMixin, Base):
    __tablename__ = "knowledge_object_replicas"
    __table_args__ = (
        UniqueConstraint(
            "artifact_id", "replica_name", name="uq_object_replica_artifact_name"
        ),
    )

    artifact_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_artifacts.id", ondelete="CASCADE"), index=True
    )
    replica_name: Mapped[str] = mapped_column(String(64), index=True)
    backend: Mapped[str] = mapped_column(String(32), index=True)
    bucket: Mapped[str] = mapped_column(String(255))
    object_key: Mapped[str] = mapped_column(Text)
    version_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    etag: Mapped[str | None] = mapped_column(String(255), nullable=True)
    checksum_sha256: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), default="healthy", index=True)
    last_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    artifact = relationship("Artifact", back_populates="replicas")


class ArtifactTransformation(PhysicalIdMixin, Base):
    __tablename__ = "knowledge_artifact_transformations"

    input_artifact_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_artifacts.id", ondelete="RESTRICT"), index=True
    )
    output_artifact_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_artifacts.id", ondelete="RESTRICT"), index=True
    )
    transformation_type: Mapped[str] = mapped_column(String(64), index=True)
    processor: Mapped[str] = mapped_column(String(128))
    processor_version: Mapped[str] = mapped_column(String(64))
    fingerprint: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )


class ArtifactReconciliationRun(PhysicalIdMixin, Base):
    __tablename__ = "knowledge_artifact_reconciliation_runs"

    status: Mapped[str] = mapped_column(String(32), index=True)
    checked_artifacts: Mapped[int] = mapped_column(Integer, default=0)
    checked_replicas: Mapped[int] = mapped_column(Integer, default=0)
    repaired_replicas: Mapped[int] = mapped_column(Integer, default=0)
    missing_replicas: Mapped[int] = mapped_column(Integer, default=0)
    corrupt_replicas: Mapped[int] = mapped_column(Integer, default=0)
    orphan_objects: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, index=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


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
    source_entry_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_source_entries.id", ondelete="CASCADE"),
        index=True,
    )
    canonical_path: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    language: Mapped[str] = mapped_column(String(32), default="text")
    processing_mode: Mapped[str] = mapped_column(
        String(32), default="legacy", index=True
    )
    processor_fingerprint: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )
    generation_ingestion_id: Mapped[str | None] = mapped_column(
        ForeignKey("knowledge_ingestions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    source = relationship("KnowledgeSource", back_populates="documents")
    source_entry = relationship(
        "KnowledgeSourceEntry", back_populates="documents"
    )
    chunks = relationship(
        "KnowledgeChunk", back_populates="document", cascade="all, delete-orphan"
    )
    code_symbols = relationship(
        "CodeSymbol", back_populates="document", cascade="all, delete-orphan"
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


class KnowledgeEmbeddingCache(PhysicalIdMixin, Base):
    __tablename__ = "knowledge_embedding_cache"

    cache_key: Mapped[str] = mapped_column(
        String(64), unique=True, index=True
    )
    embedding_model: Mapped[str] = mapped_column(String(255), index=True)
    embedding_dimensions: Mapped[int] = mapped_column(Integer)
    embedding: Mapped[list[float]] = mapped_column(EmbeddingType())
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )
    last_used_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, index=True
    )


class CodeSymbol(PhysicalIdMixin, Base):
    __tablename__ = "code_symbols"
    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "kind",
            "qualified_name",
            "start_line",
            name="uq_code_symbols_document_identity",
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
    language: Mapped[str] = mapped_column(String(32), index=True)
    kind: Mapped[str] = mapped_column(String(32), index=True)
    name: Mapped[str] = mapped_column(String(512), index=True)
    qualified_name: Mapped[str] = mapped_column(Text)
    signature: Mapped[str] = mapped_column(Text, default="")
    start_line: Mapped[int] = mapped_column(Integer)
    end_line: Mapped[int] = mapped_column(Integer)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    document = relationship("KnowledgeDocument", back_populates="code_symbols")
    outgoing_relations = relationship(
        "CodeRelation",
        foreign_keys="CodeRelation.source_symbol_id",
        back_populates="source_symbol",
        cascade="all, delete-orphan",
    )
    document_links = relationship(
        "CodeDocumentLink",
        back_populates="symbol",
        cascade="all, delete-orphan",
    )


class CodeRelation(PhysicalIdMixin, Base):
    __tablename__ = "code_relations"
    __table_args__ = (
        UniqueConstraint(
            "fingerprint",
            name="uq_code_relations_fingerprint",
        ),
    )

    source_symbol_id: Mapped[str] = mapped_column(
        ForeignKey("code_symbols.id", ondelete="CASCADE"), index=True
    )
    target_symbol_id: Mapped[str | None] = mapped_column(
        ForeignKey("code_symbols.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    relation_type: Mapped[str] = mapped_column(String(32), index=True)
    target_name: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    evidence_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    source_symbol = relationship(
        "CodeSymbol",
        foreign_keys=[source_symbol_id],
        back_populates="outgoing_relations",
    )
    target_symbol = relationship("CodeSymbol", foreign_keys=[target_symbol_id])


class CodeDocumentLink(PhysicalIdMixin, Base):
    __tablename__ = "code_document_links"
    __table_args__ = (
        UniqueConstraint(
            "fingerprint",
            name="uq_code_document_links_fingerprint",
        ),
    )

    symbol_id: Mapped[str] = mapped_column(
        ForeignKey("code_symbols.id", ondelete="CASCADE"), index=True
    )
    document_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_documents.id", ondelete="CASCADE"), index=True
    )
    link_type: Mapped[str] = mapped_column(String(32), index=True)
    score: Mapped[float] = mapped_column(Float, default=1.0)
    fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    evidence_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    symbol = relationship("CodeSymbol", back_populates="document_links")
    document = relationship("KnowledgeDocument")


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
