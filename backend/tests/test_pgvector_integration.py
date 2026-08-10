import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Event
import time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text

from app.config import Settings
from app.knowledge.ollama import FakeOllamaClient
from app.knowledge.security import KnowledgeCipher, load_knowledge_cipher
from app.knowledge.service import KnowledgeService
from app.main import create_app
from app.migrations.auto_cutover import run_auto_cutover
from app.models import (
    Base,
    KnowledgeChunk,
    KnowledgeDocument,
    KnowledgeIngestion,
    KnowledgeSource,
    KnowledgeSourceEntry,
    Product,
    ProductVersion,
    Project,
    Tenant,
    DataMigrationReceipt,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from tests.waiters import wait_for_ingestion


POSTGRES_URL = os.environ.get("AGENT_GATEWAY_TEST_POSTGRES_URL")
MIGRATION_POSTGRES_URL = os.environ.get(
    "AGENT_GATEWAY_TEST_MIGRATION_POSTGRES_URL"
)


@pytest.mark.skipif(
    not POSTGRES_URL,
    reason="AGENT_GATEWAY_TEST_POSTGRES_URL is not configured",
)
def test_postgresql_closes_claim_to_create_race(
    tmp_path: Path,
    projects_dir: Path,
    project_repository: Path,
) -> None:
    settings = Settings(
        environment="test",
        process_role="api",
        database_url=POSTGRES_URL,
        auto_create_schema=True,
        projects_dir=projects_dir,
        workspace_root=tmp_path / "workspaces",
        fake_runtime_delay_ms=0,
        knowledge_enabled=True,
        knowledge_encryption_key=KnowledgeCipher.generate_key(),
        knowledge_allowed_roots=str(project_repository.parent),
        knowledge_sources_dir=tmp_path / "knowledge-sources",
        knowledge_rejection_archive_dir=tmp_path / "rejections",
        knowledge_scheduler_enabled=False,
        queue_redis_enabled=False,
    )
    app = create_app(settings=settings)
    service = KnowledgeService(
        database=app.state.database,
        settings=settings,
        provider=FakeOllamaClient(),
        cipher=load_knowledge_cipher(settings),
    )
    app.state.knowledge_service = service

    with TestClient(app) as client:
        source_response = client.post(
            "/api/v1/knowledge/sources",
            json={
                "project_id": "test-project",
                "name": f"PostgreSQL scheduler lock {tmp_path.name}",
                "root_path": str(project_repository),
                "scope": "tenant",
                "approved_for_codex": True,
                "sync_mode": "scheduled",
                "sync_interval_minutes": 60,
            },
        )
        assert source_response.status_code == 201
        source_id = source_response.json()["id"]
        scheduler_worker = "postgresql-race-scheduler"
        with app.state.database.session_factory() as session:
            source = session.get(KnowledgeSource, source_id)
            source.next_sync_at = datetime.now(timezone.utc) - timedelta(seconds=1)
            session.commit()
        assert service.claim_due_source(
            worker_id=scheduler_worker,
            lease_seconds=60,
        ) == source_id

        create_started = Event()

        def create_scheduled_ingestion() -> tuple[str, bool]:
            create_started.set()
            ingestion, created = service.create_ingestion(
                source_id,
                trigger="scheduled",
                enqueue=False,
            )
            return ingestion.id, created

        with ThreadPoolExecutor(max_workers=1) as executor:
            with app.state.database.session_factory() as blocking_session:
                blocking_session.scalar(
                    select(KnowledgeSource)
                    .where(KnowledgeSource.id == source_id)
                    .with_for_update()
                )
                future = executor.submit(create_scheduled_ingestion)
                assert create_started.wait(timeout=5)
                deadline = time.monotonic() + 5
                blocked = False
                while time.monotonic() < deadline:
                    with app.state.database.engine.connect() as connection:
                        blocked = bool(
                            connection.scalar(
                                text(
                                    "SELECT EXISTS ("
                                    "SELECT 1 FROM pg_stat_activity "
                                    "WHERE datname = current_database() "
                                    "AND pid <> pg_backend_pid() "
                                    "AND wait_event_type = 'Lock' "
                                    "AND query LIKE '%knowledge_sources%'"
                                    ")"
                                )
                            )
                        )
                    if blocked:
                        break
                    time.sleep(0.02)
                assert blocked is True
                scoped = KnowledgeIngestion(
                    source_id=source_id,
                    trigger="scope_repair",
                    status="queued",
                    analysis_scope_id="scope-race",
                    scope_prefix="customer-a",
                )
                blocking_session.add(scoped)
                blocking_session.commit()

            scheduled_id, scheduled_created = future.result(timeout=5)

        assert scheduled_created is False
        assert scheduled_id == scoped.id
        with app.state.database.session_factory() as session:
            active = list(
                session.scalars(
                    select(KnowledgeIngestion).where(
                        KnowledgeIngestion.source_id == source_id,
                        KnowledgeIngestion.status.in_(("queued", "running")),
                    )
                )
            )
        assert [ingestion.id for ingestion in active] == [scoped.id]
        service.release_sync_lease(source_id, scheduler_worker)
        assert client.delete(
            f"/api/v1/knowledge/sources/{source_id}"
        ).status_code == 204


@pytest.mark.skipif(
    not POSTGRES_URL,
    reason="AGENT_GATEWAY_TEST_POSTGRES_URL is not configured",
)
def test_pgvector_storage_and_native_search(
    tmp_path: Path,
    projects_dir: Path,
    project_repository: Path,
) -> None:
    settings = Settings(
        environment="test",
        process_role="combined",
        database_url=POSTGRES_URL,
        auto_create_schema=False,
        projects_dir=projects_dir,
        workspace_root=tmp_path / "workspaces",
        fake_runtime_delay_ms=0,
        knowledge_enabled=True,
        knowledge_encryption_key=KnowledgeCipher.generate_key(),
        knowledge_allowed_roots=str(project_repository.parent),
        knowledge_sources_dir=tmp_path / "knowledge-sources",
        knowledge_rejection_archive_dir=tmp_path / "rejections",
        knowledge_scheduler_enabled=False,
    )
    app = create_app(settings=settings)
    service = KnowledgeService(
        database=app.state.database,
        settings=settings,
        provider=FakeOllamaClient(),
        cipher=load_knowledge_cipher(settings),
    )
    app.state.knowledge_service = service
    app.state.task_executor._knowledge_service = service
    app.state.queue_coordinator._knowledge_service = service

    with TestClient(app) as client:
        ready = client.get("/health/ready")
        assert ready.status_code == 200
        assert ready.json()["backend"] == "postgresql"
        assert ready.json()["native_vector_search"] is True
        assert ready.json()["pgvector_version"]

        source = client.post(
            "/api/v1/knowledge/sources",
            json={
                "project_id": "test-project",
                "name": "PostgreSQL vector source",
                "root_path": str(project_repository),
                "scope": "tenant",
                "approved_for_codex": True,
            },
        )
        assert source.status_code == 201
        source_id = source.json()["id"]
        ingestion = client.post(
            f"/api/v1/knowledge/sources/{source_id}/ingest"
        )
        assert ingestion.status_code == 202
        completed = wait_for_ingestion(client, ingestion.json()["id"])
        assert completed["status"] == "completed"

        search = client.post(
            "/api/v1/knowledge/search",
            json={
                "project_id": "test-project",
                "query": "Test project",
                "limit": 5,
            },
        )
        assert search.status_code == 200
        assert search.json()["results"][0]["path"] == "README.md"

        with app.state.database.engine.connect() as connection:
            assert connection.scalar(
                text(
                    "SELECT pg_typeof(embedding)::text "
                    "FROM knowledge_chunks LIMIT 1"
                )
            ) == "vector"
            assert connection.scalar(
                text(
                    "SELECT EXISTS ("
                    "SELECT 1 FROM pg_indexes "
                    "WHERE indexname = "
                    "'ix_knowledge_chunks_embedding_hnsw'"
                    ")"
                )
            ) is True


@pytest.mark.skipif(
    not MIGRATION_POSTGRES_URL,
    reason="AGENT_GATEWAY_TEST_MIGRATION_POSTGRES_URL is not configured",
)
def test_completed_sqlite_database_migrates_to_pgvector(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "completed.sqlite"
    source_engine = create_engine(
        f"sqlite+pysqlite:///{source_path.as_posix()}"
    )
    Base.metadata.create_all(source_engine)
    tenant_id = "7532476e-8422-4c91-88b5-581d615210f3"
    product_id = "11b583b5-f86f-4ad8-916f-8ee77fc6111e"
    product_version_id = "3f0a9e89-c42f-472a-aeaf-3920272e0dd7"
    project_id = "26758b72-105e-44ba-9d31-b8de19bf512e"
    source_id = "12b96a35-bafe-4e46-87e4-b148250a722d"
    document_id = "e0413334-f5c8-4ca1-8dd5-c5340cae93d3"
    source_entry_id = "b180f06b-1c02-450d-ae49-c51b87edfd03"
    chunk_id = "b05ee96c-4a10-4561-8a54-b71fb68a0ad8"
    with Session(source_engine) as session:
        session.add(
            Tenant(id=tenant_id, code="migration-tenant", name="Migration")
        )
        session.add(
            Product(
                id=product_id,
                code="migration-product",
                name="Migration Product",
            )
        )
        session.flush()
        session.add(
            ProductVersion(
                id=product_version_id,
                product_id=product_id,
                version="1",
            )
        )
        session.flush()
        session.add(
            Project(
                id=project_id,
                code="migration-project",
                name="Migration Project",
                tenant_id=tenant_id,
                product_version_id=product_version_id,
            )
        )
        session.flush()
        session.add(
            KnowledgeSource(
                id=source_id,
                project_id=project_id,
                tenant_id=tenant_id,
                product_version_id=product_version_id,
                name="Migration source",
                source_key="migration-source",
                root_path="D:/migration",
                scope="tenant",
                status="approved",
                approved_for_codex=True,
            )
        )
        session.flush()
        session.add(
            KnowledgeSourceEntry(
                id=source_entry_id,
                source_id=source_id,
                relative_path="warning.txt",
                entry_kind="file",
                processing_mode="document",
                processing_status="indexed",
                raw_content_hash="c" * 64,
            )
        )
        session.flush()
        session.add(
            KnowledgeDocument(
                id=document_id,
                source_id=source_id,
                source_entry_id=source_entry_id,
                canonical_path="warning.txt",
                content_hash="a" * 64,
                language="text",
            )
        )
        session.flush()
        session.add(
            KnowledgeChunk(
                id=chunk_id,
                document_id=document_id,
                tenant_id=tenant_id,
                product_version_id=product_version_id,
                scope="tenant",
                ordinal=0,
                content_ciphertext="encrypted",
                search_text="migration warning",
                content_hash="b" * 64,
                token_count=2,
                embedding=[0.03125] * 1024,
                embedding_model="test-embedding",
                embedding_dimensions=1024,
                metadata_json={"path": "warning.txt"},
            )
        )
        session.commit()
    source_engine.dispose()

    cutover_settings = Settings(
        environment="test",
        database_url=MIGRATION_POSTGRES_URL,
        auto_create_schema=False,
        legacy_sqlite_path=source_path,
        migration_receipt_root=tmp_path / "migration-evidence",
        projects_dir=tmp_path / "projects",
        workspace_root=tmp_path / "workspaces",
    )
    report = run_auto_cutover(cutover_settings)
    repeated = run_auto_cutover(cutover_settings)

    assert report["status"] == "completed"
    assert report["verification"]["source_vector_count"] == 1
    assert report["verification"]["target_vector_count"] == 1
    assert repeated["status"] == "already_completed"
    target_engine = create_engine(MIGRATION_POSTGRES_URL)
    with target_engine.connect() as connection:
        assert connection.scalar(
            text(
                "SELECT pg_typeof(embedding)::text "
                "FROM knowledge_chunks WHERE id = :id"
            ),
            {"id": chunk_id},
        ) == "vector"
        assert connection.scalar(
            select(DataMigrationReceipt.source_sha256)
        ) == report["source_sha256"]
    target_engine.dispose()
