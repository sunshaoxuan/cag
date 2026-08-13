from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.database import Database
from app.knowledge.artifact_store import (
    ArtifactUnavailableError,
    FilesystemArtifactObjectStore,
    S3ArtifactObjectStore,
    object_key_for_sha256,
)
from app.knowledge.artifacts import ArtifactEvidenceService
from app.knowledge.security import KnowledgeCipher
from app.knowledge.security import load_artifact_cipher
from app.models.knowledge import Artifact, ArtifactTransformation, ObjectReplica


@pytest.fixture
def artifact_service(tmp_path: Path) -> tuple[ArtifactEvidenceService, Database, list[FilesystemArtifactObjectStore]]:
    database = Database(
        f"sqlite+pysqlite:///{(tmp_path / 'artifacts.sqlite').as_posix()}",
        allow_sqlite_for_tests=True,
    )
    database.create_schema()
    cipher = KnowledgeCipher(b"k" * 32)
    stores = [
        FilesystemArtifactObjectStore(replica_name="primary", root=tmp_path / "primary", cipher=cipher),
        FilesystemArtifactObjectStore(replica_name="replica", root=tmp_path / "replica", cipher=cipher),
    ]
    service = ArtifactEvidenceService(database=database, stores=stores)
    yield service, database, stores
    database.dispose()


def test_content_addressed_put_is_idempotent_and_has_two_replicas(artifact_service):
    service, database, stores = artifact_service
    content = "cleaned evidence 日本語".encode()
    first = service.put(content=content, media_type="text/plain", artifact_kind="cleaned")
    second = service.put(content=content, media_type="text/plain", artifact_kind="cleaned")

    assert first.id == second.id
    assert first.sha256 == sha256(content).hexdigest()
    with database.session_factory() as session:
        assert len(list(session.scalars(select(Artifact)))) == 1
        replicas = list(session.scalars(select(ObjectReplica)))
    assert len(replicas) == 2
    key = object_key_for_sha256(first.sha256)
    assert all(store.get(key) == content for store in stores)
    assert all(store._path(key).read_bytes() != content for store in stores)


def test_content_remains_readable_after_primary_and_source_path_disappear(artifact_service, tmp_path):
    service, _, stores = artifact_service
    source = tmp_path / "source.txt"
    source.write_text("durable evidence", encoding="utf-8")
    artifact = service.put(content=source.read_bytes(), media_type="text/plain", artifact_kind="cleaned")
    source.unlink()
    key = object_key_for_sha256(artifact.sha256)
    stores[0]._path(key).unlink()

    loaded, content = service.get(artifact.sha256)

    assert loaded.id == artifact.id
    assert content == b"durable evidence"


def test_reconciliation_repairs_missing_replica_and_reports_orphan(artifact_service):
    service, _, stores = artifact_service
    artifact = service.put(content=b"restore me", media_type="text/plain", artifact_kind="cleaned")
    key = object_key_for_sha256(artifact.sha256)
    stores[1]._path(key).unlink()
    orphan_checksum = sha256(b"orphan").hexdigest()
    orphan_key = object_key_for_sha256(orphan_checksum)
    stores[0].put(orphan_key, b"orphan", orphan_checksum)

    run = service.reconcile(repair=True)

    assert run.status == "completed"
    assert run.missing_replicas == 1
    assert run.repaired_replicas == 1
    assert run.orphan_objects == 1
    assert stores[1].get(key) == b"restore me"


def test_reconciliation_repairs_primary_from_second_replica(artifact_service):
    service, _, stores = artifact_service
    artifact = service.put(content=b"restore primary", media_type="text/plain", artifact_kind="cleaned")
    key = object_key_for_sha256(artifact.sha256)
    stores[0]._path(key).unlink()

    run = service.reconcile(repair=True)

    assert run.missing_replicas == 1
    assert run.repaired_replicas == 1
    assert stores[0].get(key) == b"restore primary"


def test_unavailable_artifact_is_explicit(artifact_service):
    service, database, stores = artifact_service
    artifact = service.put(content=b"lost", media_type="text/plain", artifact_kind="cleaned")
    key = object_key_for_sha256(artifact.sha256)
    for store in stores:
        store._path(key).unlink()
    run = service.reconcile(repair=False)
    assert run.missing_replicas == 2
    with pytest.raises(ArtifactUnavailableError):
        service.get(artifact.sha256)
    with database.session_factory() as session:
        assert session.get(Artifact, artifact.id).status == "unavailable"


def test_reconciliation_repairs_corrupt_encrypted_replica(artifact_service):
    service, _, stores = artifact_service
    artifact = service.put(content=b"repair corruption", media_type="text/plain", artifact_kind="cleaned")
    key = object_key_for_sha256(artifact.sha256)
    stores[1]._path(key).write_bytes(b"corrupt ciphertext")

    run = service.reconcile(repair=True)

    assert run.corrupt_replicas == 1
    assert run.repaired_replicas == 1
    assert stores[1].get(key) == b"repair corruption"


def test_reconciliation_restores_missing_database_replica_reference(artifact_service):
    service, database, _ = artifact_service
    artifact = service.put(content=b"restore reference", media_type="text/plain", artifact_kind="cleaned")
    with database.session_factory() as session:
        replica = session.scalar(
            select(ObjectReplica).where(
                ObjectReplica.artifact_id == artifact.id,
                ObjectReplica.replica_name == "replica",
            )
        )
        session.delete(replica)
        session.commit()

    run = service.reconcile(repair=True)

    assert run.repaired_replicas == 1
    with database.session_factory() as session:
        assert len(
            list(
                session.scalars(
                    select(ObjectReplica).where(ObjectReplica.artifact_id == artifact.id)
                )
            )
        ) == 2


def test_reconciliation_restores_all_database_replica_references_without_false_orphans(artifact_service):
    service, database, _ = artifact_service
    artifact = service.put(content=b"restore every reference", media_type="text/plain", artifact_kind="cleaned")
    with database.session_factory() as session:
        for replica in list(
            session.scalars(
                select(ObjectReplica).where(ObjectReplica.artifact_id == artifact.id)
            )
        ):
            session.delete(replica)
        session.commit()

    run = service.reconcile(repair=True)

    assert run.repaired_replicas == 2
    assert run.orphan_objects == 0


def test_artifact_api_round_trip_and_recovery(client):
    response = client.put(
        "/api/v1/knowledge/artifacts",
        json={"content": "API evidence", "media_type": "text/plain", "artifact_kind": "cleaned"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["replicas"]) == 2
    checksum = payload["sha256"]

    detail = client.get(f"/api/v1/knowledge/artifacts/{checksum}")
    content = client.get(f"/api/v1/knowledge/artifacts/{checksum}/content")
    reconciliation = client.post("/api/v1/knowledge/artifacts/reconciliation-runs")
    summary = client.get("/api/v1/knowledge/artifacts/summary")

    assert detail.status_code == 200
    assert content.status_code == 200
    assert content.content == b"API evidence"
    assert content.headers["x-content-sha256"] == checksum
    assert reconciliation.json()["status"] == "completed"
    assert summary.json() == {
        "artifacts": 1,
        "available_artifacts": 1,
        "replicas": 2,
        "healthy_replicas": 2,
    }


def test_transformation_is_idempotent_and_strongly_referenced(artifact_service):
    service, database, _ = artifact_service
    raw = service.put(content=b"raw", media_type="text/plain", artifact_kind="raw")
    cleaned = service.put(content=b"cleaned", media_type="text/plain", artifact_kind="cleaned")

    first = service.record_transformation(
        input_sha256=raw.sha256,
        output_sha256=cleaned.sha256,
        transformation_type="cleaned_from",
        processor="test-cleaner",
        processor_version="1",
    )
    second = service.record_transformation(
        input_sha256=raw.sha256,
        output_sha256=cleaned.sha256,
        transformation_type="cleaned_from",
        processor="test-cleaner",
        processor_version="1",
    )

    assert first.id == second.id
    with database.session_factory() as session:
        transformation = session.scalar(select(ArtifactTransformation))
        assert transformation.input_artifact_id == raw.id
        assert transformation.output_artifact_id == cleaned.id


class FakeS3Error(Exception):
    def __init__(self, status: int) -> None:
        self.response = {"ResponseMetadata": {"HTTPStatusCode": status}}


class FakeS3Client:
    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], tuple[bytes, dict[str, str]]] = {}

    def put_object(self, *, Bucket, Key, Body, Metadata):
        self.objects[(Bucket, Key)] = (Body, Metadata)
        return {"ETag": '"fake-etag"', "VersionId": "version-1"}

    def get_object(self, *, Bucket, Key):
        if (Bucket, Key) not in self.objects:
            raise FakeS3Error(404)
        content, _ = self.objects[(Bucket, Key)]
        return {"Body": SimpleNamespace(read=lambda: content)}

    def head_object(self, *, Bucket, Key):
        if (Bucket, Key) not in self.objects:
            raise FakeS3Error(404)
        _, metadata = self.objects[(Bucket, Key)]
        return {
            "Metadata": metadata,
            "ETag": '"fake-etag"',
            "VersionId": "version-1",
        }

    def get_paginator(self, name):
        assert name == "list_objects_v2"
        client = self

        class Paginator:
            def paginate(self, *, Bucket, Prefix):
                return [
                    {
                        "Contents": [
                            {"Key": key}
                            for bucket, key in client.objects
                            if bucket == Bucket and key.startswith(Prefix)
                        ]
                    }
                ]

        return Paginator()


def test_s3_adapter_contract_is_encrypted_and_content_addressed(monkeypatch):
    fake_client = FakeS3Client()
    fake_boto3 = SimpleNamespace(client=lambda *args, **kwargs: fake_client)
    monkeypatch.setitem(__import__("sys").modules, "boto3", fake_boto3)
    store = S3ArtifactObjectStore(
        replica_name="primary",
        endpoint_url="https://rustfs.invalid",
        region="us-east-1",
        bucket="evidence",
        access_key="access",
        secret_key="secret",
        verify_tls=True,
        cipher=KnowledgeCipher(b"s" * 32),
    )
    content = b"S3 compatible evidence"
    checksum = sha256(content).hexdigest()
    key = object_key_for_sha256(checksum)

    stored = store.put(key, content, checksum)

    assert stored.etag == "fake-etag"
    assert stored.version_id == "version-1"
    assert store.get(key) == content
    assert store.head(key).checksum_sha256 == checksum
    assert store.list_keys() == {key}
    assert fake_client.objects[("evidence", key)][0] != content
    assert store.head(object_key_for_sha256("0" * 64)) is None
    with pytest.raises(ArtifactUnavailableError):
        store.get(object_key_for_sha256("0" * 64))


def test_object_key_and_replica_configuration_reject_invalid_contract(tmp_path):
    with pytest.raises(ValueError, match="Invalid SHA 256"):
        object_key_for_sha256("invalid")
    store = FilesystemArtifactObjectStore(replica_name="one", root=tmp_path / "one")
    with pytest.raises(Exception, match="object key"):
        store.put(object_key_for_sha256("0" * 64), b"payload", sha256(b"payload").hexdigest())
    with pytest.raises(ValueError, match="two independent"):
        ArtifactEvidenceService(database=Database(
            f"sqlite+pysqlite:///{(tmp_path / 'one.sqlite').as_posix()}",
            allow_sqlite_for_tests=True,
        ), stores=[store])


def test_artifact_cipher_uses_independent_secret(settings, monkeypatch):
    settings.artifact_encryption_key = KnowledgeCipher.generate_key()
    settings.knowledge_encryption_key = KnowledgeCipher.generate_key()
    artifact_cipher = load_artifact_cipher(settings)
    assert artifact_cipher is not None
    assert artifact_cipher.key_id != KnowledgeCipher(
        __import__("base64").urlsafe_b64decode(settings.knowledge_encryption_key)
    ).key_id
