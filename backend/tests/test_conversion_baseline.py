from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.config import Settings
from app.main import create_app
from app.models import (
    KnowledgeBaselineRun,
    KnowledgeIngestion,
    KnowledgeSourceEntry,
)
from tests.test_knowledge import install_fake_knowledge, knowledge_settings
from tests.waiters import wait_for_ingestion


def test_conversion_baseline_is_repeatable_and_read_only(
    settings: Settings,
    tmp_path: Path,
) -> None:
    root = tmp_path / "conversion-source"
    root.mkdir()
    (root / "guide.txt").write_text("remote access guide", encoding="utf-8")
    (root / "legacy.doc").write_bytes(b"legacy document bytes")
    (root / "client.exe").write_bytes(b"MZ\x00\x00")
    (root / "archive.zip").write_bytes(b"PK\x03\x04")
    (root / "empty.txt").write_bytes(b"")

    active_settings = knowledge_settings(settings, tmp_path)
    app = create_app(settings=active_settings)
    install_fake_knowledge(app, active_settings)

    with TestClient(app) as client:
        source = client.post(
            "/api/v1/knowledge/sources",
            json={
                "project_id": "test-project",
                "name": "Conversion source",
                "root_path": str(root),
                "scope": "tenant",
                "approved_for_codex": True,
            },
        ).json()
        ingestion = client.post(
            f"/api/v1/knowledge/sources/{source['id']}/ingest"
        ).json()
        assert wait_for_ingestion(client, ingestion["id"])["status"] == (
            "completed"
        )

        with app.state.database.session_factory() as session:
            active = KnowledgeIngestion(
                source_id=source["id"],
                status="running",
                trigger="scheduled",
            )
            session.add(active)
            session.flush()
            legacy = session.scalar(
                select(KnowledgeSourceEntry).where(
                    KnowledgeSourceEntry.source_id == source["id"],
                    KnowledgeSourceEntry.relative_path == "legacy.doc",
                )
            )
            assert legacy is not None
            legacy.last_seen_ingestion_id = active.id
            active_id = active.id
            session.commit()
            entries_before = {
                item.id: (
                    item.processing_status,
                    item.reason_code,
                    item.last_seen_ingestion_id,
                )
                for item in session.scalars(
                    select(KnowledgeSourceEntry).where(
                        KnowledgeSourceEntry.source_id == source["id"]
                    )
                )
            }

        capabilities = client.get(
            "/api/v1/knowledge/conversion/format-capabilities"
        )
        assert capabilities.status_code == 200
        capability_payload = capabilities.json()
        assert capability_payload["routing_boundary"] == (
            "extension-metadata-planning-only"
        )
        assert ".doc" in capability_payload["categories"]["planned_text"]
        assert ".exe" in capability_payload["categories"]["binary_metadata"]

        first = client.post(
            f"/api/v1/knowledge/sources/{source['id']}/conversion-baselines"
        )
        assert first.status_code == 200
        first_payload = first.json()
        assert first_payload["status"] == "completed"
        assert first_payload["item_count"] == 5
        assert first_payload["active_ingestion_id"] == active_id
        assert first_payload["action_counts"] == {
            "backfill_object": 1,
            "metadata_only": 1,
            "path_only": 1,
            "reclean": 1,
            "safe_unpack": 1,
        }

        items_response = client.get(
            f"/api/v1/knowledge/conversion-baselines/{first_payload['id']}/items",
            params={"limit": 10},
        )
        assert items_response.status_code == 200
        items = {
            item["relative_path"]: item
            for item in items_response.json()["items"]
        }
        assert items["guide.txt"]["conversion_action"] == "backfill_object"
        assert items["guide.txt"]["document_id"]
        assert items["legacy.doc"]["lifecycle_status"] == "processing"
        assert items["legacy.doc"]["conversion_action"] == "reclean"
        assert items["client.exe"]["capability"] == "binary_metadata"
        assert items["client.exe"]["conversion_action"] == "metadata_only"
        assert items["archive.zip"]["conversion_action"] == "safe_unpack"
        assert items["empty.txt"]["conversion_action"] == "path_only"

        filtered = client.get(
            f"/api/v1/knowledge/conversion-baselines/{first_payload['id']}/items",
            params={"conversion_action": "reclean", "limit": 1},
        ).json()
        assert filtered["total"] == 1
        assert filtered["items"][0]["relative_path"] == "legacy.doc"

        second_payload = client.post(
            f"/api/v1/knowledge/sources/{source['id']}/conversion-baselines"
        ).json()
        assert second_payload["manifest_sha256"] == (
            first_payload["manifest_sha256"]
        )

        with app.state.database.session_factory() as session:
            entries_after = {
                item.id: (
                    item.processing_status,
                    item.reason_code,
                    item.last_seen_ingestion_id,
                )
                for item in session.scalars(
                    select(KnowledgeSourceEntry).where(
                        KnowledgeSourceEntry.source_id == source["id"]
                    )
                )
            }
        assert entries_after == entries_before


def test_conversion_baseline_missing_resources(
    settings: Settings,
    tmp_path: Path,
) -> None:
    active_settings = knowledge_settings(settings, tmp_path)
    app = create_app(settings=active_settings)
    install_fake_knowledge(app, active_settings)
    with TestClient(app) as client:
        assert client.post(
            "/api/v1/knowledge/sources/missing/conversion-baselines"
        ).status_code == 404
        assert client.get(
            "/api/v1/knowledge/conversion-baselines/missing"
        ).status_code == 404
        assert client.get(
            "/api/v1/knowledge/conversion-baselines/missing/items"
        ).status_code == 404


def test_conversion_baseline_failure_closes_run(
    settings: Settings,
    tmp_path: Path,
    monkeypatch,
) -> None:
    from app.knowledge import conversion_baseline

    root = tmp_path / "failed-baseline"
    root.mkdir()
    (root / "guide.txt").write_text("guide", encoding="utf-8")
    active_settings = knowledge_settings(settings, tmp_path)
    app = create_app(settings=active_settings)
    install_fake_knowledge(app, active_settings)
    with TestClient(app) as client:
        source = client.post(
            "/api/v1/knowledge/sources",
            json={
                "project_id": "test-project",
                "name": "Failed baseline source",
                "root_path": str(root),
                "scope": "tenant",
            },
        ).json()
        ingestion = client.post(
            f"/api/v1/knowledge/sources/{source['id']}/ingest"
        ).json()
        assert wait_for_ingestion(client, ingestion["id"])["status"] == (
            "completed"
        )

        def fail_decision(*_args, **_kwargs):
            raise RuntimeError("planned failure")

        monkeypatch.setattr(
            conversion_baseline, "conversion_decision", fail_decision
        )
        try:
            client.post(
                f"/api/v1/knowledge/sources/{source['id']}/conversion-baselines"
            )
        except RuntimeError as exc:
            assert str(exc) == "planned failure"
        else:
            raise AssertionError("Dry run failure was not propagated")

        with app.state.database.session_factory() as session:
            failed = session.scalar(
                select(KnowledgeBaselineRun).where(
                    KnowledgeBaselineRun.source_id == source["id"]
                )
            )
            assert failed is not None
            assert failed.status == "failed"
            assert failed.item_count == 0
            assert failed.completed_at is not None
            assert failed.error == (
                "RuntimeError: conversion baseline failed"
            )
