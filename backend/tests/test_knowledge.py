import asyncio
from datetime import timedelta
import gzip
import json
import os
from pathlib import Path
import shutil
import subprocess
import zipfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.config import Settings
from app.knowledge.ollama import FakeOllamaClient, OllamaClient, OllamaError
from app.knowledge.resources import build_resource_uri
from app.knowledge.scheduler import KnowledgeScheduler
from app.knowledge.credentials import SourceCredential
from app.knowledge.connectors import SourceConfig, SourceConnectorManager
from app.policies.command_policy import CommandPolicyService
from app.knowledge.security import (
    KnowledgeCipher,
    load_knowledge_cipher,
    scan_knowledge_text,
)
from app.knowledge.service import KnowledgeService
from app.main import create_app
from app.models import (
    CodeDocumentLink,
    CodeRelation,
    CodeSymbol,
    KnowledgeChunk,
    KnowledgeDocument,
    KnowledgeIngestion,
    KnowledgeIngestionRejection,
    KnowledgeSource,
)
from tests.waiters import wait_for_ingestion, wait_for_task
from app.models.base import utc_now
from app.runtimes.base import RuntimeEventCallback, RuntimeResult
from app.tasks.executor import TaskExecutor


def knowledge_settings(
    settings: Settings,
    root: Path,
) -> Settings:
    payload = settings.model_dump()
    payload.update(
        {
            "knowledge_enabled": True,
            "knowledge_encryption_key": KnowledgeCipher.generate_key(),
            "knowledge_allowed_roots": str(root),
            "knowledge_sources_dir": root / ".knowledge-source-cache",
            "knowledge_rejection_archive_dir": (
                root / ".knowledge-rejection-archives"
            ),
            "knowledge_rejection_db_retention_days": 90,
            "knowledge_rejection_archive_retention_days": 365,
            "knowledge_scheduler_enabled": False,
        }
    )
    return Settings(**payload)


class FakeCredentialStore:
    def __init__(self) -> None:
        self.values: dict[str, SourceCredential] = {}

    def set(self, credential_ref: str, *, username: str, secret: str) -> None:
        self.values[credential_ref] = SourceCredential(username, secret)

    def get(self, credential_ref: str | None) -> SourceCredential | None:
        return self.values.get(credential_ref or "")

    def delete(self, credential_ref: str | None) -> None:
        self.values.pop(credential_ref or "", None)


class CompleteRerankFakeOllama(FakeOllamaClient):
    async def structured_generate(
        self,
        prompt: str,
        schema: dict,
    ) -> dict:
        if "候補JSON: " not in prompt:
            return await super().structured_generate(prompt, schema)
        self.generated.append(prompt)
        candidates = json.loads(prompt.split("候補JSON: ", 1)[1])
        return {
            "scores": [
                {
                    "id": item["id"],
                    "score": (
                        1.0
                        if "customer_service.py" in item["path"]
                        else 0.1
                    ),
                }
                for item in candidates
            ]
        }


class CapturingKnowledgeRuntime:
    def __init__(self) -> None:
        self.developer_instructions: str | None = None

    async def execute(
        self,
        *,
        task_id: str,
        project_code: str,
        prompt: str,
        runtime_profile: str,
        persistent_conversation: bool,
        conversation_thread_id: str | None,
        workspace_path: Path,
        additional_workspace_roots: tuple[Path, ...],
        developer_instructions: str | None,
        emit: RuntimeEventCallback,
    ) -> RuntimeResult:
        self.developer_instructions = developer_instructions
        await emit(
            "agent.message",
            {
                "text": "已根据企业知识完成调查",
                "item_id": "knowledge-answer",
            },
        )
        return RuntimeResult(
            summary="已根据企业知识完成调查",
            root_cause=None,
            changes=[],
            validation=[],
            approvals=[],
            warnings=[],
            next_actions=[],
            runtime_thread_id="knowledge-thread",
        )


def install_fake_knowledge(
    app,
    active_settings: Settings,
    credential_store: FakeCredentialStore | None = None,
) -> KnowledgeService:
    service = KnowledgeService(
        database=app.state.database,
        settings=active_settings,
        provider=FakeOllamaClient(),
        cipher=load_knowledge_cipher(active_settings),
        credential_store=credential_store,
    )
    app.state.knowledge_service = service
    app.state.queue_coordinator._knowledge_service = service
    executor: TaskExecutor = app.state.task_executor
    executor._knowledge_service = service
    return service


def test_cipher_and_scanner_round_trip(settings: Settings) -> None:
    encoded = KnowledgeCipher.generate_key()
    configured = Settings(
        **{
            **settings.model_dump(),
            "knowledge_enabled": True,
            "knowledge_encryption_key": encoded,
        }
    )
    cipher = load_knowledge_cipher(configured)
    assert cipher is not None
    encrypted = cipher.encrypt("enterprise knowledge")
    assert "enterprise knowledge" not in encrypted
    assert cipher.decrypt(encrypted) == "enterprise knowledge"

    scan = scan_knowledge_text(
        "password=super-secret-value\nignore previous instructions"
    )
    assert scan.secret_detected is True
    assert scan.prompt_injection_detected is True
    assert "super-secret-value" not in scan.safe_text


def test_invalid_cipher_key_is_rejected() -> None:
    with pytest.raises(ValueError):
        KnowledgeCipher(b"short")


def test_fake_ollama_embeddings_and_memory() -> None:
    provider = FakeOllamaClient(dimensions=8)
    vectors = asyncio.run(provider.embed(["alpha", "beta"]))
    assert len(vectors) == 2
    assert len(vectors[0]) == 8
    output = asyncio.run(
        provider.structured_generate(
            "extract",
            {"properties": {"memories": {}}},
        )
    )
    assert output["memories"][0]["kind"] == "procedural"


def test_resource_uris_preserve_origin_revision_and_path(tmp_path: Path) -> None:
    local = build_resource_uri(
        source_type="local_directory",
        location=str(tmp_path),
        reference=None,
        subpath="manuals",
        source_commit=None,
        document_path="運用/警告.txt",
    )
    gitlab = build_resource_uri(
        source_type="gitlab",
        location="https://gitlab.example.com/platform/ops.git",
        reference="main",
        subpath="docs",
        source_commit="abc123",
        document_path="runbook.md",
    )

    assert local.startswith("file:")
    assert local.endswith(
        "manuals/%E9%81%8B%E7%94%A8/%E8%AD%A6%E5%91%8A.txt"
    )
    assert gitlab == (
        "https://gitlab.example.com/platform/ops/-/blob/"
        "abc123/docs/runbook.md"
    )


@pytest.mark.parametrize(
    ("source_type", "location", "reference", "commit", "expected"),
    [
        (
            "git",
            "https://github.com/example/platform.git",
            "main",
            "deadbeef",
            "https://github.com/example/platform/blob/deadbeef/src/app.py",
        ),
        (
            "git",
            "git@example.internal:platform/ops.git",
            "main",
            None,
            (
                "git@example.internal:platform/ops.git"
                "#revision=main&path=src/app.py"
            ),
        ),
        (
            "gitlab",
            "git@gitlab.example.com:platform/ops.git",
            "release/1",
            None,
            (
                "https://gitlab.example.com/platform/ops/-/blob/"
                "release%2F1/src/app.py"
            ),
        ),
        (
            "git",
            "file:///D:/repositories/platform",
            "main",
            "deadbeef",
            "file:///D:/repositories/platform/src/app.py",
        ),
        (
            "svn",
            "https://svn.example.com/repos/platform",
            "42",
            None,
            "https://svn.example.com/repos/platform/src/app.py",
        ),
        (
            "custom",
            "https://files.example.com/platform",
            None,
            None,
            "https://files.example.com/platform/src/app.py",
        ),
    ],
)
def test_repository_resource_uri_variants(
    source_type: str,
    location: str,
    reference: str | None,
    commit: str | None,
    expected: str,
) -> None:
    assert build_resource_uri(
        source_type=source_type,
        location=location,
        reference=reference,
        subpath=None,
        source_commit=commit,
        document_path="src/app.py",
    ) == expected


def test_unc_resource_uri_uses_file_scheme() -> None:
    assert build_resource_uri(
        source_type="network_share",
        location=r"\\fileserver\knowledge",
        reference=None,
        subpath="manuals",
        source_commit=None,
        document_path="runbook.txt",
    ) == "file://fileserver/knowledge/manuals/runbook.txt"


def test_knowledge_api_ingests_searches_and_governs_memory(
    settings: Settings,
    project_repository: Path,
) -> None:
    active_settings = knowledge_settings(settings, project_repository.parent)
    runtime = CapturingKnowledgeRuntime()
    app = create_app(settings=active_settings, runtime=runtime)
    service = install_fake_knowledge(app, active_settings)
    with TestClient(app) as client:
        status = client.get("/api/v1/knowledge/status")
        assert status.status_code == 200
        assert status.json()["ready"] is True

        source_response = client.post(
            "/api/v1/knowledge/sources",
            json={
                "project_id": "test-project",
                "name": "Test repository",
                "root_path": str(project_repository),
                "scope": "tenant",
                "approved_for_codex": True,
            },
        )
        assert source_response.status_code == 201
        source = source_response.json()

        validation = client.post(
            f"/api/v1/knowledge/sources/{source['id']}/validate"
        )
        assert validation.status_code == 200
        assert validation.json()["ok"] is True

        ingestion_response = client.post(
            f"/api/v1/knowledge/sources/{source['id']}/ingest"
        )
        assert ingestion_response.status_code == 202
        ingestion = wait_for_ingestion(
            client,
            ingestion_response.json()["id"],
        )
        assert ingestion["status"] == "completed"
        assert ingestion["chunks_written"] == 1
        embedded_after_first_ingestion = len(
            service._provider.embedded_texts
        )

        repeated_response = client.post(
            f"/api/v1/knowledge/sources/{source['id']}/ingest"
        )
        repeated = wait_for_ingestion(
            client,
            repeated_response.json()["id"],
        )
        assert repeated["status"] == "completed"
        assert repeated["chunks_written"] == 0
        assert repeated["unchanged_files"] == 1
        assert repeated["vectors_reused"] == 1
        assert len(service._provider.embedded_texts) == embedded_after_first_ingestion
        with app.state.database.session_factory() as session:
            assert session.scalar(select(func.count(KnowledgeDocument.id))) == 1
            assert session.scalar(select(func.count(KnowledgeChunk.id))) == 1

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
        resource_uri = search.json()["results"][0]["resource_uri"]
        assert resource_uri.startswith("file:")
        assert resource_uri.endswith("/README.md")

        conversation = client.post(
            "/api/v1/conversations",
            json={
                "project_id": "test-project",
                "title": "知识闭环",
            },
        ).json()

        created = client.post(
            "/api/v1/tasks",
            json={
                "project_id": "test-project",
                "conversation_id": conversation["id"],
                "prompt": "Investigate the test project",
                "knowledge_mode": "assist",
            },
        )
        assert created.status_code == 202
        task_id = created.json()["id"]
        task = wait_for_task(client, task_id)
        assert task["status"] == "completed"
        assert task["knowledge_usage"]["citation_count"] == 1
        citation = task["knowledge_usage"]["citations"][0]
        assert citation["resource_uri"] == resource_uri
        assert task["final_report"]["knowledge_citations"] == [citation]
        assert runtime.developer_instructions is not None
        assert "Investigate the learned enterprise knowledge" in (
            runtime.developer_instructions
        )
        assert f'resource_uri="{resource_uri}"' in runtime.developer_instructions
        events = client.get(
            f"/api/v1/conversations/{conversation['id']}/events",
            params={"follow": "false"},
        ).text
        assert "knowledge.context.injected" in events
        assert resource_uri in events
        assert "memory.candidate.created" in events

        candidates = client.get("/api/v1/memory-candidates").json()
        assert candidates[0]["status"] == "proposed"
        assert candidates[0]["evidence"]["knowledge_citations"] == [citation]
        candidate_id = candidates[0]["id"]
        approved = client.post(
            f"/api/v1/memory-candidates/{candidate_id}/approve"
        )
        assert approved.json()["status"] == "approved"
        promoted = client.post(
            f"/api/v1/memory-candidates/{candidate_id}/promote"
        )
        assert promoted.json()["scope"] == "product"
        deprecated = client.post(
            f"/api/v1/memory-candidates/{candidate_id}/deprecate"
        )
        assert deprecated.json()["status"] == "deprecated"

        sources = client.get("/api/v1/knowledge/sources").json()
        assert sources[0]["status"] == "approved"
        assert service.list_sources()[0].id == source["id"]


def test_code_knowledge_graph_is_idempotent_and_searchable(
    settings: Settings,
    project_repository: Path,
) -> None:
    source_dir = project_repository / "src"
    source_dir.mkdir()
    (source_dir / "customer_service.py").write_text(
        """\
def normalize_customer(name: str) -> str:
    return name.strip()

class CustomerService:
    def search_customer(self, name: str) -> str:
        return normalize_customer(name)
""",
        encoding="utf-8",
    )
    (project_repository / "README.md").write_text(
        "# 顧客検索\n\n`src/customer_service.py` の CustomerService が顧客情報を検索する。\n",
        encoding="utf-8",
    )
    (project_repository / "設計.txt").write_bytes(
        "顧客情報の検索仕様".encode("cp932")
    )
    active_settings = knowledge_settings(settings, project_repository.parent)
    app = create_app(settings=active_settings)
    service = install_fake_knowledge(app, active_settings)
    service._provider = CompleteRerankFakeOllama()

    with TestClient(app) as client:
        source = client.post(
            "/api/v1/knowledge/sources",
            json={
                "project_id": "test-project",
                "name": "Code repository",
                "root_path": str(project_repository),
                "scope": "tenant",
                "approved_for_codex": True,
            },
        ).json()
        first = client.post(
            f"/api/v1/knowledge/sources/{source['id']}/ingest"
        ).json()
        assert wait_for_ingestion(client, first["id"])["status"] == "completed"

        summary = client.get(
            "/api/v1/knowledge/code/summary",
            params={"project_id": "test-project"},
        )
        assert summary.status_code == 200
        assert summary.json()["symbols"] >= 4
        assert summary.json()["relations"] >= 1
        assert summary.json()["document_links"] >= 1

        symbols = client.get(
            "/api/v1/knowledge/code/symbols",
            params={
                "project_id": "test-project",
                "query": "search_customer",
            },
        ).json()
        assert symbols[0]["name"] == "search_customer"
        detail = client.get(
            f"/api/v1/knowledge/code/symbols/{symbols[0]['id']}",
            params={"project_id": "test-project"},
        ).json()
        assert detail["outgoing_relations"][0]["target_name"] == (
            "normalize_customer"
        )
        assert detail["outgoing_relations"][0]["target_symbol_id"] is not None
        assert any(
            item["path"] == "README.md"
            for item in detail["document_links"]
        )

        search = client.post(
            "/api/v1/knowledge/search",
            json={
                "project_id": "test-project",
                "query": "search_customer 顧客情報",
                "profile": "deep",
                "limit": 5,
            },
        ).json()
        assert search["results"][0]["path"] == "src/customer_service.py"
        assert "code_symbol" in search["results"][0]["match_reasons"]
        assert "local_reranker" in search["results"][0]["match_reasons"]
        assert service._provider.generated

        second = client.post(
            f"/api/v1/knowledge/sources/{source['id']}/ingest"
        ).json()
        assert wait_for_ingestion(client, second["id"])[
            "unchanged_files"
        ] == 3
        with app.state.database.session_factory() as session:
            symbol_count = session.scalar(select(func.count(CodeSymbol.id)))
            relation_count = session.scalar(select(func.count(CodeRelation.id)))
            link_count = session.scalar(select(func.count(CodeDocumentLink.id)))
        repeated_summary = client.get(
            "/api/v1/knowledge/code/summary",
            params={"project_id": "test-project"},
        ).json()
        assert repeated_summary["symbols"] == symbol_count
        assert repeated_summary["relations"] == relation_count
        assert repeated_summary["document_links"] == link_count

        duplicate_source = client.post(
            "/api/v1/knowledge/sources",
            json={
                "project_id": "test-project",
                "name": "Same repository",
                "location": str(project_repository),
                "scope": "tenant",
            },
        )
        assert duplicate_source.status_code == 422


def test_managed_sources_deduplicate_files_store_credentials_and_emit_stages(
    settings: Settings,
    project_repository: Path,
) -> None:
    (project_repository / "README-copy.md").write_text(
        "# Test project\n",
        encoding="utf-8",
    )
    active_settings = knowledge_settings(settings, project_repository.parent)
    credentials = FakeCredentialStore()
    app = create_app(settings=active_settings)
    install_fake_knowledge(app, active_settings, credentials)
    with TestClient(app) as client:
        created = client.post(
            "/api/v1/knowledge/sources",
            json={
                "project_id": "test-project",
                "name": "Managed local files",
                "source_type": "local_directory",
                "location": str(project_repository),
                "scope": "product",
                "approved_for_codex": True,
                "credential_username": "reader",
                "credential_secret": "secret-value",
            },
        )
        assert created.status_code == 201
        source = created.json()
        assert source["credential_configured"] is True
        assert "secret-value" not in str(source)
        assert len(credentials.values) == 1

        revealed = client.post(
            f"/api/v1/knowledge/sources/{source['id']}/credential/reveal"
        )
        assert revealed.status_code == 200
        assert revealed.json() == {
            "username": "reader",
            "secret": "secret-value",
        }
        assert revealed.headers["cache-control"] == "no-store, private"
        assert revealed.headers["pragma"] == "no-cache"
        assert revealed.headers["x-content-type-options"] == "nosniff"

        started = client.post(
            f"/api/v1/knowledge/sources/{source['id']}/ingest"
        )
        assert started.status_code == 202
        ingestion = wait_for_ingestion(client, started.json()["id"])
        assert ingestion["status"] == "completed"
        assert ingestion["files_seen"] == 2
        assert ingestion["duplicate_files"] == 1
        assert ingestion["chunks_written"] == 1

        events = client.get(
            f"/api/v1/knowledge/ingestions/{ingestion['id']}/events",
            params={"follow": "false"},
        ).text
        assert "knowledge.collection.completed" in events
        assert "knowledge.collection.progress" in events
        assert "knowledge.cleaning.completed" in events
        assert "knowledge.indexing.completed" in events
        assert "knowledge.memory.persisted" in events

        replacement = project_repository.parent / "replacement-knowledge"
        replacement.mkdir()
        (replacement / "GUIDE.md").write_text(
            "# Replacement knowledge\n",
            encoding="utf-8",
        )
        updated = client.patch(
            f"/api/v1/knowledge/sources/{source['id']}",
            json={
                "name": "Updated managed files",
                "source_type": "local_directory",
                "location": str(replacement),
                "reference": "",
                "subpath": "",
            },
        )
        assert updated.status_code == 200
        assert updated.json()["name"] == "Updated managed files"
        assert updated.json()["location"] == str(replacement)
        assert updated.json()["status"] == "draft"
        assert updated.json()["index_fingerprint"] is None

        disabled = client.patch(
            f"/api/v1/knowledge/sources/{source['id']}",
            json={"enabled": False},
        )
        assert disabled.json()["enabled"] is False
        assert (
            client.post(
                f"/api/v1/knowledge/sources/{source['id']}/ingest"
            ).status_code
            == 409
        )
        enabled = client.patch(
            f"/api/v1/knowledge/sources/{source['id']}",
            json={"enabled": True, "clear_credential": True},
        )
        assert enabled.json()["credential_configured"] is False
        assert credentials.values == {}
        assert (
            client.post(
                f"/api/v1/knowledge/sources/{source['id']}/credential/reveal"
            ).status_code
            == 404
        )
        assert client.delete(
            f"/api/v1/knowledge/sources/{source['id']}"
        ).status_code == 204
        assert client.get("/api/v1/knowledge/sources").json() == []


def test_scheduler_reindexes_changes_removes_deleted_files_and_keeps_history(
    settings: Settings,
    project_repository: Path,
) -> None:
    active_settings = knowledge_settings(settings, project_repository.parent)
    app = create_app(settings=active_settings)
    service = install_fake_knowledge(
        app,
        active_settings,
        FakeCredentialStore(),
    )
    scheduler = KnowledgeScheduler(
        service=service,
        poll_seconds=1,
        lease_seconds=60,
    )
    with TestClient(app) as client:
        created = client.post(
            "/api/v1/knowledge/sources",
            json={
                "project_id": "test-project",
                "name": "Continuously monitored files",
                "source_type": "local_directory",
                "location": str(project_repository),
                "scope": "product",
                "approved_for_codex": True,
                "sync_mode": "scheduled",
                "sync_interval_minutes": 15,
            },
        )
        assert created.status_code == 201
        source = created.json()
        assert source["sync_mode"] == "scheduled"
        assert source["next_sync_at"] is not None

        assert asyncio.run(scheduler.run_once()) is True
        first = client.get(
            f"/api/v1/knowledge/sources/{source['id']}/ingestions"
        ).json()[0]
        assert first["trigger"] == "scheduled"
        assert first["changed_files"] == 1
        assert first["removed_files"] == 0

        (project_repository / "GUIDE.md").write_text(
            "# Changed product guide\n",
            encoding="utf-8",
        )
        with app.state.database.session_factory() as session:
            stored = session.get(KnowledgeSource, source["id"])
            stored.next_sync_at = utc_now() - timedelta(seconds=1)
            session.commit()
        assert asyncio.run(scheduler.run_once()) is True
        second = client.get(
            f"/api/v1/knowledge/sources/{source['id']}/ingestions"
        ).json()[0]
        assert second["changed_files"] == 1
        assert second["unchanged_files"] == 1
        assert second["vectors_reused"] == 1

        (project_repository / "README.md").unlink()
        with app.state.database.session_factory() as session:
            stored = session.get(KnowledgeSource, source["id"])
            stored.next_sync_at = utc_now() - timedelta(seconds=1)
            session.commit()
        assert asyncio.run(scheduler.run_once()) is True
        history = client.get(
            f"/api/v1/knowledge/sources/{source['id']}/ingestions"
        ).json()
        assert len(history) == 3
        assert history[0]["removed_files"] == 1
        assert all(item["trigger"] == "scheduled" for item in history)
        with app.state.database.session_factory() as session:
            paths = set(
                session.scalars(
                    select(KnowledgeDocument.canonical_path).where(
                        KnowledgeDocument.source_id == source["id"]
                    )
                )
            )
        assert paths == {"GUIDE.md"}


def test_scheduler_lease_prevents_duplicate_claim_and_failure_is_retried(
    settings: Settings,
    project_repository: Path,
) -> None:
    active_settings = knowledge_settings(settings, project_repository.parent)
    app = create_app(settings=active_settings)
    service = install_fake_knowledge(
        app,
        active_settings,
        FakeCredentialStore(),
    )
    scheduler = KnowledgeScheduler(
        service=service,
        poll_seconds=1,
        lease_seconds=60,
    )
    with TestClient(app) as client:
        source = client.post(
            "/api/v1/knowledge/sources",
            json={
                "project_id": "test-project",
                "name": "Retryable source",
                "source_type": "local_directory",
                "location": str(project_repository),
                "scope": "product",
                "sync_mode": "scheduled",
                "sync_interval_minutes": 60,
            },
        ).json()
        assert service.claim_due_source(
            worker_id="worker-a",
            lease_seconds=60,
        ) == source["id"]
        assert service.claim_due_source(
            worker_id="worker-b",
            lease_seconds=60,
        ) is None
        service.release_sync_lease(source["id"], "worker-a")
        assert service.claim_due_source(
            worker_id="worker-b",
            lease_seconds=60,
        ) == source["id"]
        service.release_sync_lease(source["id"], "worker-b")

        with app.state.database.session_factory() as session:
            stored = session.get(KnowledgeSource, source["id"])
            stored.root_path = str(
                project_repository.parent / "missing-source"
            )
            stored.next_sync_at = utc_now() - timedelta(seconds=1)
            session.commit()
        assert asyncio.run(scheduler.run_once()) is True
        failed = client.get("/api/v1/knowledge/sources").json()[0]
        assert failed["status"] == "failed"
        assert failed["consecutive_failures"] == 1
        assert failed["next_sync_at"] is not None
        history = client.get(
            f"/api/v1/knowledge/sources/{source['id']}/ingestions"
        ).json()
        assert history[0]["status"] == "failed"
        assert history[0]["trigger"] == "scheduled"


def test_scheduler_loop_survives_one_iteration_failure() -> None:
    class FlakyService:
        def __init__(self) -> None:
            self.claim_attempts = 0
            self.running_states: list[bool] = []

        def recover_interrupted_ingestions(self) -> int:
            return 0

        def set_scheduler_running(self, running: bool) -> None:
            self.running_states.append(running)

        def claim_due_source(
            self,
            *,
            worker_id: str,
            lease_seconds: int,
        ) -> None:
            del worker_id, lease_seconds
            self.claim_attempts += 1
            if self.claim_attempts == 1:
                raise RuntimeError("temporary scheduler failure")
            return None

    async def exercise() -> tuple[int, list[bool]]:
        service = FlakyService()
        scheduler = KnowledgeScheduler(
            service=service,  # type: ignore[arg-type]
            poll_seconds=0.01,  # type: ignore[arg-type]
            lease_seconds=60,
        )
        scheduler.start()
        for _ in range(50):
            if service.claim_attempts >= 2:
                break
            await asyncio.sleep(0.01)
        await scheduler.stop()
        return service.claim_attempts, service.running_states

    attempts, states = asyncio.run(exercise())
    assert attempts >= 2
    assert states[0] is True
    assert states[-1] is False


def test_git_source_is_validated_materialized_and_indexed(
    settings: Settings,
    project_repository: Path,
) -> None:
    active_settings = knowledge_settings(settings, project_repository.parent)
    app = create_app(settings=active_settings)
    install_fake_knowledge(app, active_settings, FakeCredentialStore())
    with TestClient(app) as client:
        created = client.post(
            "/api/v1/knowledge/sources",
            json={
                "project_id": "test-project",
                "name": "Git documents",
                "source_type": "gitlab",
                "location": str(project_repository),
                "reference": "master",
                "scope": "product",
                "approved_for_codex": True,
            },
        )
        assert created.status_code == 201
        source = created.json()
        validated = client.post(
            f"/api/v1/knowledge/sources/{source['id']}/validate"
        )
        assert validated.status_code == 200
        assert len(validated.json()["revision"]) == 40
        ingestion = client.post(
            f"/api/v1/knowledge/sources/{source['id']}/ingest"
        ).json()
        completed = wait_for_ingestion(client, ingestion["id"])
        assert completed["status"] == "completed", completed["error"]
        assert completed["chunks_written"] == 1
        assert any(active_settings.knowledge_sources_dir.iterdir())
        assert client.delete(
            f"/api/v1/knowledge/sources/{source['id']}"
        ).status_code == 204
        assert not any(active_settings.knowledge_sources_dir.iterdir())


@pytest.mark.skipif(
    shutil.which("svn") is None or shutil.which("svnadmin") is None,
    reason="SVN command line tools are unavailable",
)
def test_svn_source_is_materialized_and_indexed(
    settings: Settings,
    project_repository: Path,
    tmp_path: Path,
) -> None:
    repository = tmp_path / "svn-repository"
    import_dir = tmp_path / "svn-import"
    import_dir.mkdir()
    (import_dir / "guide.md").write_text(
        "# SVN guide\nReusable product knowledge.",
        encoding="utf-8",
    )
    subprocess.run(["svnadmin", "create", str(repository)], check=True)
    repository_url = repository.resolve().as_uri()
    subprocess.run(
        [
            "svn",
            "import",
            str(import_dir),
            repository_url,
            "-m",
            "initial",
        ],
        check=True,
        capture_output=True,
    )
    active_settings = knowledge_settings(settings, tmp_path)
    app = create_app(settings=active_settings)
    install_fake_knowledge(app, active_settings, FakeCredentialStore())
    with TestClient(app) as client:
        created = client.post(
            "/api/v1/knowledge/sources",
            json={
                "project_id": "test-project",
                "name": "SVN documents",
                "source_type": "svn",
                "location": repository_url,
                "scope": "product",
                "approved_for_codex": True,
            },
        )
        assert created.status_code == 201
        source = created.json()
        assert client.post(
            f"/api/v1/knowledge/sources/{source['id']}/validate"
        ).status_code == 200
        ingestion = client.post(
            f"/api/v1/knowledge/sources/{source['id']}/ingest"
        ).json()
        completed = wait_for_ingestion(client, ingestion["id"])
        assert completed["status"] == "completed"
        assert completed["files_seen"] == 1


def test_office_document_extraction(tmp_path: Path) -> None:
    document = tmp_path / "guide.docx"
    with zipfile.ZipFile(document, "w") as archive:
        archive.writestr(
            "word/document.xml",
            (
                '<w:document xmlns:w="urn:test"><w:body>'
                "<w:p><w:r><w:t>Enterprise guide</w:t></w:r></w:p>"
                "</w:body></w:document>"
            ),
        )
    from app.knowledge.extractors import extract_text

    assert "Enterprise guide" in extract_text(document)


def test_encrypted_pdf_is_rejected_without_stopping_collection(
    tmp_path: Path,
) -> None:
    from pypdf import PdfWriter

    root = tmp_path / "pdf-source"
    root.mkdir()
    encrypted = root / "encrypted.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.encrypt("synthetic-test-password")
    with encrypted.open("wb") as stream:
        writer.write(stream)
    (root / "README.md").write_text("# Readable", encoding="utf-8")
    manager = SourceConnectorManager(
        cache_root=tmp_path / "cache",
        allowed_roots=[tmp_path],
        credential_store=FakeCredentialStore(),
        command_policy=CommandPolicyService(),
        git_executable="git",
        svn_executable="svn",
        max_file_bytes=10_000,
    )

    rejections = []
    result = manager.collect(
        SourceConfig(
            id="encrypted-pdf-source",
            source_type="local_directory",
            location=str(root),
            reference=None,
            subpath=None,
            credential_ref=None,
        ),
        rejection=rejections.append,
    )

    assert result.files_seen == 2
    assert result.rejected_files == 1
    assert [document.path for document in result.documents] == ["README.md"]
    assert len(rejections) == 1
    assert rejections[0].relative_path == "encrypted.pdf"
    assert rejections[0].reason_code == "pdf_unreadable"
    assert rejections[0].error_type == "ValueError"
    assert rejections[0].error_message


def test_ingestion_persists_and_exports_file_level_rejection_audit(
    settings: Settings,
    project_repository: Path,
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "enterprise-source"
    source_root.mkdir()
    (source_root / "accepted.md").write_text(
        "# Accepted knowledge",
        encoding="utf-8",
    )
    (source_root / "legacy.sql").write_bytes(b"\x81")
    (source_root / "empty.sql").write_text("", encoding="utf-8")
    (source_root / "legacy.doc").write_bytes(b"legacy-document")
    (source_root / "oversized.txt").write_text(
        "x" * 2_048,
        encoding="utf-8",
    )
    configured = knowledge_settings(settings, tmp_path)
    active_settings = Settings(
        **{
            **configured.model_dump(),
            "knowledge_max_file_bytes": 1_024,
        }
    )
    app = create_app(settings=active_settings)
    service = install_fake_knowledge(app, active_settings)

    with TestClient(app) as client:
        created = client.post(
            "/api/v1/knowledge/sources",
            json={
                "project_id": "test-project",
                "name": "Enterprise rejection audit",
                "root_path": str(source_root),
                "scope": "tenant",
                "approved_for_codex": True,
            },
        )
        assert created.status_code == 201
        source_id = created.json()["id"]
        started = client.post(
            f"/api/v1/knowledge/sources/{source_id}/ingest"
        )
        assert started.status_code == 202
        ingestion_id = started.json()["id"]
        ingestion = wait_for_ingestion(client, ingestion_id)

        assert ingestion["status"] == "completed"
        assert ingestion["rejected_files"] == 2
        assert ingestion["skipped_files"] == 2
        assert ingestion["rejection_archive_sha256"]
        audit = client.get(
            f"/api/v1/knowledge/ingestions/{ingestion_id}/rejections"
        )
        assert audit.status_code == 200
        payload = audit.json()
        assert payload["total"] == 4
        assert payload["archive_available"] is True
        by_path = {
            item["relative_path"]: item for item in payload["items"]
        }
        assert by_path["legacy.sql"]["reason_code"] == "encoding_unsupported"
        assert by_path["legacy.sql"]["disposition"] == "rejected"
        assert by_path["empty.sql"]["reason_code"] == "empty_text"
        assert (
            by_path["legacy.doc"]["reason_code"]
            == "unsupported_extension"
        )
        assert by_path["legacy.doc"]["disposition"] == "skipped"
        assert by_path["oversized.txt"]["reason_code"] == "file_too_large"
        assert by_path["oversized.txt"]["file_size"] == 2_048

        filtered = client.get(
            f"/api/v1/knowledge/ingestions/{ingestion_id}/rejections",
            params={"disposition": "rejected", "limit": 1},
        ).json()
        assert filtered["total"] == 2
        assert len(filtered["items"]) == 1
        assert {item["count"] for item in filtered["summary"]} == {1}

        exported = client.get(
            f"/api/v1/knowledge/ingestions/{ingestion_id}/rejections/export"
        )
        assert exported.status_code == 200
        assert exported.content.startswith(b"\xef\xbb\xbf")
        exported_text = exported.content.decode("utf-8-sig")
        assert "legacy.sql" in exported_text
        assert "encoding_unsupported" in exported_text
        assert "oversized.txt" in exported_text

        archived = client.get(
            f"/api/v1/knowledge/ingestions/{ingestion_id}/rejections/archive"
        )
        assert archived.status_code == 200
        archive_lines = gzip.decompress(archived.content).decode(
            "utf-8"
        ).splitlines()
        archive_header = json.loads(archive_lines[0])
        assert archive_header["record_count"] == 4
        assert len(archive_lines) == 5
        assert {
            json.loads(line)["relative_path"]
            for line in archive_lines[1:]
        } == {
            "legacy.sql",
            "empty.sql",
            "legacy.doc",
            "oversized.txt",
        }

    with app.state.database.session_factory() as session:
        assert (
            session.scalar(
                select(func.count(KnowledgeIngestionRejection.id))
            )
            == 4
        )
        stored_ingestion = session.get(KnowledgeIngestion, ingestion_id)
        assert stored_ingestion is not None
        stored_ingestion.rejection_archive_created_at = (
            utc_now() - timedelta(days=91)
        )
        session.commit()

    archive_path = service.rejection_archive_path(ingestion_id)
    service._prune_rejection_audit()
    with app.state.database.session_factory() as session:
        assert (
            session.scalar(
                select(func.count(KnowledgeIngestionRejection.id))
            )
            == 0
        )
    assert archive_path.is_file()

    expired_timestamp = (
        utc_now() - timedelta(days=366)
    ).timestamp()
    os.utime(archive_path, (expired_timestamp, expired_timestamp))
    service._prune_rejection_audit()
    assert not archive_path.exists()


def test_connector_scans_directories_breadth_first_with_progress(
    tmp_path: Path,
) -> None:
    root = tmp_path / "source"
    (root / "alpha" / "deep").mkdir(parents=True)
    (root / "beta").mkdir()
    (root / "ROOT.md").write_text("# Root", encoding="utf-8")
    (root / "alpha" / "ALPHA.md").write_text("# Alpha", encoding="utf-8")
    (root / "alpha" / "deep" / "DEEP.md").write_text(
        "# Deep",
        encoding="utf-8",
    )
    (root / "beta" / "BETA.md").write_text("# Beta", encoding="utf-8")
    manager = SourceConnectorManager(
        cache_root=tmp_path / "cache",
        allowed_roots=[tmp_path],
        credential_store=FakeCredentialStore(),
        command_policy=CommandPolicyService(),
        git_executable="git",
        svn_executable="svn",
        max_file_bytes=10_000,
    )
    progress: list[dict[str, int | str]] = []

    result = manager.collect(
        SourceConfig(
            id="source-test",
            source_type="local_directory",
            location=str(root),
            reference=None,
            subpath=None,
            credential_ref=None,
        ),
        progress.append,
    )

    completed_directories = [
        str(item["directory"])
        for item in progress
        if item["phase"] == "completed"
    ]
    assert completed_directories == [".", "alpha", "beta", "alpha/deep"]
    assert result.files_seen == 4
    assert len(result.documents) == 4
    assert progress[-1]["directories_pending"] == 0
    assert progress[-1]["files_processed"] == 4


def test_active_ingestion_is_reused_without_duplicate_execution(
    settings: Settings,
    project_repository: Path,
) -> None:
    active_settings = knowledge_settings(settings, project_repository.parent)
    app = create_app(settings=active_settings)
    service = install_fake_knowledge(app, active_settings)
    with TestClient(app) as client:
        source = client.post(
            "/api/v1/knowledge/sources",
            json={
                "project_id": "test-project",
                "name": "Single flight source",
                "source_type": "local_directory",
                "location": str(project_repository),
                "scope": "product",
            },
        ).json()
        ingestion, created = service.create_ingestion(source["id"])
        assert created is True

        repeated = client.post(
            f"/api/v1/knowledge/sources/{source['id']}/ingest"
        )
        assert repeated.status_code == 202
        assert repeated.json()["id"] == ingestion.id
        assert repeated.json()["status"] == "queued"

        asyncio.run(service.ingest(ingestion.id))
        asyncio.run(service.ingest(ingestion.id))
        events = client.get(
            f"/api/v1/knowledge/ingestions/{ingestion.id}/events",
            params={"follow": "false"},
        ).text
        assert events.count("event: knowledge.ingestion.started") == 1
        assert events.count("event: knowledge.collection.started") == 1


def test_connector_credentials_avoid_command_arguments(
    tmp_path: Path,
    monkeypatch,
) -> None:
    credentials = FakeCredentialStore()
    credentials.values["source:test"] = SourceCredential(
        "reader",
        "private-token",
    )
    manager = SourceConnectorManager(
        cache_root=tmp_path / "cache",
        allowed_roots=[tmp_path],
        credential_store=credentials,
        command_policy=CommandPolicyService(),
        git_executable="git",
        svn_executable="svn",
        max_file_bytes=10_000,
    )
    captured: dict[str, object] = {}

    def fake_run(args, **kwargs):
        captured["args"] = args
        captured["environment"] = kwargs["env"]
        return subprocess.CompletedProcess(args, 0, "abc\tHEAD\n", "")

    monkeypatch.setattr("app.knowledge.connectors.subprocess.run", fake_run)
    manager._run(
        ["git", "ls-remote", "--", "https://gitlab.example/repo.git", "HEAD"],
        credential=credentials.values["source:test"],
    )
    assert "private-token" not in str(captured["args"])
    environment = captured["environment"]
    assert isinstance(environment, dict)
    assert environment["GIT_CONFIG_KEY_0"] == "http.extraHeader"
    assert "private-token" not in environment["GIT_CONFIG_VALUE_0"]

    svn_args = ["svn", "info", "--non-interactive"]
    stdin = manager._append_svn_credentials(
        svn_args,
        credentials.values["source:test"],
    )
    assert stdin == "private-token\n"
    assert "private-token" not in str(svn_args)
    assert "--password-from-stdin" in svn_args


def test_knowledge_api_rejects_invalid_inputs(
    settings: Settings,
    project_repository: Path,
    tmp_path: Path,
) -> None:
    active_settings = knowledge_settings(settings, project_repository)
    app = create_app(settings=active_settings)
    install_fake_knowledge(app, active_settings)
    with TestClient(app) as client:
        outside = tmp_path / "outside"
        outside.mkdir()
        response = client.post(
            "/api/v1/knowledge/sources",
            json={
                "project_id": "test-project",
                "name": "Outside",
                "root_path": str(outside),
                "scope": "tenant",
            },
        )
        assert response.status_code == 422
        assert client.post("/api/v1/knowledge/sources/missing/ingest").status_code == 404
        assert client.get("/api/v1/knowledge/ingestions/missing").status_code == 404
        assert (
            client.post("/api/v1/memory-candidates/missing/approve").status_code
            == 404
        )
        assert (
            client.post("/api/v1/memory-candidates/missing/unknown").status_code
            == 404
        )


class _Response:
    def __init__(self, status_code: int, payload: dict) -> None:
        self.status_code = status_code
        self._payload = payload
        self.is_success = status_code < 400

    def json(self) -> dict:
        return self._payload


class _AsyncClient:
    responses: list[_Response] = []

    def __init__(self, **_: object) -> None:
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def get(self, _: str) -> _Response:
        return self.responses.pop(0)

    async def post(self, _: str, json: dict) -> _Response:
        return self.responses.pop(0)


@pytest.mark.anyio
async def test_real_ollama_adapter_contract(monkeypatch) -> None:
    monkeypatch.setattr("app.knowledge.ollama.httpx.AsyncClient", _AsyncClient)
    client = OllamaClient(
        base_url="http://ollama",
        embedding_model="embed",
        memory_model="memory",
        dimensions=2,
        timeout_seconds=5,
    )
    _AsyncClient.responses = [
        _Response(200, {"version": "1"}),
        _Response(200, {"models": [{"name": "embed"}, {"name": "memory"}]}),
    ]
    assert (await client.status())["ready"] is True

    _AsyncClient.responses = [_Response(200, {"embeddings": [[0.1, 0.2]]})]
    assert await client.embed(["hello"]) == [[0.1, 0.2]]

    _AsyncClient.responses = [_Response(200, {"response": '{"value": 1}'})]
    assert await client.structured_generate(
        "prompt", {"type": "object"}
    ) == {"value": 1}

    _AsyncClient.responses = [_Response(500, {})]
    with pytest.raises(OllamaError):
        await client.embed(["hello"])
