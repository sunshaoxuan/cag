from __future__ import annotations

from hashlib import sha256

from sqlalchemy import func, select

from app.database import Database
from app.knowledge.artifact_store import (
    ArtifactIntegrityError,
    ArtifactObjectStore,
    ArtifactUnavailableError,
    object_key_for_sha256,
)
from app.models.base import utc_now
from app.models.knowledge import (
    Artifact,
    ArtifactLocation,
    ArtifactReconciliationRun,
    ArtifactTransformation,
    ObjectReplica,
)


class ArtifactEvidenceService:
    def __init__(
        self, *, database: Database, stores: list[ArtifactObjectStore]
    ) -> None:
        if stores and len(stores) < 2:
            raise ValueError("Artifact evidence requires two independent replicas")
        names = [store.replica_name for store in stores]
        if len(set(names)) != len(names):
            raise ValueError("Artifact replica names must be unique")
        self.database = database
        self.stores = stores
        self.stores_by_name = {store.replica_name: store for store in stores}
        ciphers = {getattr(store, "cipher", None) for store in stores}
        self.encryption_key_id = (
            next(iter(ciphers)).key_id if len(ciphers) == 1 and ciphers else None
        )

    def put(
        self,
        *,
        content: bytes,
        media_type: str,
        artifact_kind: str,
        source_entry_id: str | None = None,
        relative_path_snapshot: str | None = None,
    ) -> Artifact:
        if not self.stores:
            raise ArtifactUnavailableError("Artifact encryption is not configured")
        checksum = sha256(content).hexdigest()
        object_key = object_key_for_sha256(checksum)
        stored = [store.put(object_key, content, checksum) for store in self.stores]
        now = utc_now()
        with self.database.session_factory() as session:
            artifact = session.scalar(
                select(Artifact).where(Artifact.sha256 == checksum)
            )
            if artifact is None:
                artifact = Artifact(
                    sha256=checksum,
                    byte_size=len(content),
                    media_type=media_type,
                    artifact_kind=artifact_kind,
                    encryption=f"application_aes_gcm:{self.encryption_key_id}",
                    status="available",
                    verified_at=now,
                )
                session.add(artifact)
                session.flush()
            elif artifact.byte_size != len(content):
                raise ArtifactIntegrityError("Artifact size conflicts with its checksum")
            artifact.status = "available"
            artifact.verified_at = now
            for item in stored:
                replica = session.scalar(
                    select(ObjectReplica).where(
                        ObjectReplica.artifact_id == artifact.id,
                        ObjectReplica.replica_name == item.replica_name,
                    )
                )
                if replica is None:
                    replica = ObjectReplica(
                        artifact_id=artifact.id,
                        replica_name=item.replica_name,
                        backend=item.backend,
                        bucket=item.bucket,
                        object_key=item.object_key,
                        checksum_sha256=item.checksum_sha256,
                    )
                    session.add(replica)
                replica.version_id = item.version_id
                replica.etag = item.etag
                replica.status = "healthy"
                replica.last_verified_at = now
                replica.error_code = None
            if source_entry_id is not None:
                location = session.scalar(
                    select(ArtifactLocation).where(
                        ArtifactLocation.artifact_id == artifact.id,
                        ArtifactLocation.source_entry_id == source_entry_id,
                        ArtifactLocation.location_type == "source_observation",
                    )
                )
                if location is None:
                    session.add(
                        ArtifactLocation(
                            artifact_id=artifact.id,
                            source_entry_id=source_entry_id,
                            location_type="source_observation",
                            relative_path_snapshot=relative_path_snapshot,
                        )
                    )
            session.commit()
            session.refresh(artifact)
            return artifact

    def get(self, checksum: str) -> tuple[Artifact, bytes]:
        with self.database.session_factory() as session:
            artifact = session.scalar(
                select(Artifact).where(Artifact.sha256 == checksum)
            )
            if artifact is None:
                raise KeyError(checksum)
            if artifact.status != "available":
                raise ArtifactUnavailableError("Artifact evidence is unavailable")
            replicas = list(
                session.scalars(
                    select(ObjectReplica)
                    .where(ObjectReplica.artifact_id == artifact.id)
                    .order_by(ObjectReplica.replica_name)
                )
            )
            for replica in replicas:
                store = self.stores_by_name.get(replica.replica_name)
                if store is None:
                    continue
                try:
                    content = store.get(replica.object_key)
                except Exception:
                    continue
                if sha256(content).hexdigest() == artifact.sha256:
                    return artifact, content
            raise ArtifactUnavailableError("No healthy artifact replica is readable")

    def detail(self, checksum: str) -> dict[str, object]:
        with self.database.session_factory() as session:
            artifact = session.scalar(
                select(Artifact).where(Artifact.sha256 == checksum)
            )
            if artifact is None:
                raise KeyError(checksum)
            replicas = list(
                session.scalars(
                    select(ObjectReplica)
                    .where(ObjectReplica.artifact_id == artifact.id)
                    .order_by(ObjectReplica.replica_name)
                )
            )
            locations = list(
                session.scalars(
                    select(ArtifactLocation)
                    .where(ArtifactLocation.artifact_id == artifact.id)
                    .order_by(ArtifactLocation.observed_at)
                )
            )
            return {
                "id": artifact.id,
                "sha256": artifact.sha256,
                "byte_size": artifact.byte_size,
                "media_type": artifact.media_type,
                "artifact_kind": artifact.artifact_kind,
                "status": artifact.status,
                "verified_at": artifact.verified_at,
                "replicas": [
                    {
                        "id": item.id,
                        "replica_name": item.replica_name,
                        "backend": item.backend,
                        "bucket": item.bucket,
                        "object_key": item.object_key,
                        "version_id": item.version_id,
                        "etag": item.etag,
                        "checksum_sha256": item.checksum_sha256,
                        "status": item.status,
                        "last_verified_at": item.last_verified_at,
                        "error_code": item.error_code,
                    }
                    for item in replicas
                ],
                "locations": [
                    {
                        "id": item.id,
                        "source_entry_id": item.source_entry_id,
                        "location_type": item.location_type,
                        "relative_path_snapshot": item.relative_path_snapshot,
                        "observed_at": item.observed_at,
                    }
                    for item in locations
                ],
            }

    def record_transformation(
        self,
        *,
        input_sha256: str,
        output_sha256: str,
        transformation_type: str,
        processor: str,
        processor_version: str,
    ) -> ArtifactTransformation:
        fingerprint = sha256(
            "\x1f".join(
                (
                    input_sha256,
                    output_sha256,
                    transformation_type,
                    processor,
                    processor_version,
                )
            ).encode("utf-8")
        ).hexdigest()
        with self.database.session_factory() as session:
            existing = session.scalar(
                select(ArtifactTransformation).where(
                    ArtifactTransformation.fingerprint == fingerprint
                )
            )
            if existing is not None:
                return existing
            input_artifact = session.scalar(
                select(Artifact).where(Artifact.sha256 == input_sha256)
            )
            output_artifact = session.scalar(
                select(Artifact).where(Artifact.sha256 == output_sha256)
            )
            if input_artifact is None or output_artifact is None:
                raise KeyError("Transformation artifact not found")
            transformation = ArtifactTransformation(
                input_artifact_id=input_artifact.id,
                output_artifact_id=output_artifact.id,
                transformation_type=transformation_type,
                processor=processor,
                processor_version=processor_version,
                fingerprint=fingerprint,
            )
            session.add(transformation)
            session.commit()
            session.refresh(transformation)
            return transformation

    def reconcile(self, *, repair: bool = True) -> ArtifactReconciliationRun:
        if not self.stores:
            raise ArtifactUnavailableError("Artifact encryption is not configured")
        with self.database.session_factory() as session:
            run = ArtifactReconciliationRun(status="running")
            session.add(run)
            session.commit()
            run_id = run.id
        try:
            return self._reconcile(run_id=run_id, repair=repair)
        except Exception as exc:
            with self.database.session_factory() as session:
                run = session.get(ArtifactReconciliationRun, run_id)
                if run is not None:
                    run.status = "failed"
                    run.error = type(exc).__name__
                    run.completed_at = utc_now()
                    session.commit()
            raise

    def _reconcile(
        self, *, run_id: str, repair: bool
    ) -> ArtifactReconciliationRun:
        now = utc_now()
        with self.database.session_factory() as session:
            artifacts = list(session.scalars(select(Artifact).order_by(Artifact.id)))
            replicas = list(session.scalars(select(ObjectReplica)))
            replica_by_key = {
                (item.artifact_id, item.replica_name): item for item in replicas
            }
            expected_keys = {item.object_key for item in replicas}
            checked_replicas = 0
            repaired_replicas = 0
            missing_replicas = 0
            corrupt_replicas = 0
            for artifact in artifacts:
                healthy = 0
                source_content: bytes | None = None
                pending_repairs: list[tuple[ArtifactObjectStore, ObjectReplica | None]] = []
                for store in self.stores:
                    checked_replicas += 1
                    key = object_key_for_sha256(artifact.sha256)
                    record = replica_by_key.get((artifact.id, store.replica_name))
                    try:
                        head = store.head(key)
                    except Exception:
                        head = None
                        corrupt_replicas += 1
                        head_failed = True
                    else:
                        head_failed = False
                    if head is not None and head.checksum_sha256 == artifact.sha256:
                        expected_keys.add(key)
                        healthy += 1
                        source_content = source_content or store.get(key)
                        if record is None:
                            record = ObjectReplica(
                                artifact_id=artifact.id,
                                replica_name=head.replica_name,
                                backend=head.backend,
                                bucket=head.bucket,
                                object_key=head.object_key,
                                version_id=head.version_id,
                                etag=head.etag,
                                checksum_sha256=head.checksum_sha256,
                            )
                            session.add(record)
                            repaired_replicas += 1
                        record.status = "healthy"
                        record.error_code = None
                        record.last_verified_at = now
                        continue
                    if head_failed:
                        error_code = "replica_unreadable"
                    elif head is None:
                        missing_replicas += 1
                        error_code = "replica_missing"
                    else:
                        corrupt_replicas += 1
                        error_code = "checksum_mismatch"
                    if record is not None:
                        record.status = (
                            "missing" if head is None and not head_failed else "corrupt"
                        )
                        record.error_code = error_code
                        record.last_verified_at = now
                    pending_repairs.append((store, record))
                if repair and source_content is not None:
                    for store, record in pending_repairs:
                        key = object_key_for_sha256(artifact.sha256)
                        stored = store.replace(key, source_content, artifact.sha256)
                        if record is None:
                            record = ObjectReplica(
                                artifact_id=artifact.id,
                                replica_name=stored.replica_name,
                                backend=stored.backend,
                                bucket=stored.bucket,
                                object_key=stored.object_key,
                                checksum_sha256=stored.checksum_sha256,
                            )
                            session.add(record)
                        record.status = "healthy"
                        record.error_code = None
                        record.last_verified_at = now
                        record.etag = stored.etag
                        record.version_id = stored.version_id
                        repaired_replicas += 1
                        healthy += 1
                artifact.status = "available" if healthy else "unavailable"
                artifact.verified_at = now if healthy else artifact.verified_at
            orphan_objects = sum(
                len(store.list_keys() - expected_keys) for store in self.stores
            )
            run = session.get(ArtifactReconciliationRun, run_id)
            if run is None:
                raise RuntimeError("Artifact reconciliation run disappeared")
            run.status = "completed"
            run.checked_artifacts = len(artifacts)
            run.checked_replicas = checked_replicas
            run.repaired_replicas = repaired_replicas
            run.missing_replicas = missing_replicas
            run.corrupt_replicas = corrupt_replicas
            run.orphan_objects = orphan_objects
            run.completed_at = now
            session.commit()
            session.refresh(run)
            return run

    def summary(self) -> dict[str, int]:
        with self.database.session_factory() as session:
            artifact_count = session.scalar(select(func.count()).select_from(Artifact))
            available_count = session.scalar(
                select(func.count()).select_from(Artifact).where(
                    Artifact.status == "available"
                )
            )
            replica_count = session.scalar(
                select(func.count()).select_from(ObjectReplica)
            )
            healthy_replica_count = session.scalar(
                select(func.count()).select_from(ObjectReplica).where(
                    ObjectReplica.status == "healthy"
                )
            )
        return {
            "artifacts": int(artifact_count or 0),
            "available_artifacts": int(available_count or 0),
            "replicas": int(replica_count or 0),
            "healthy_replicas": int(healthy_replica_count or 0),
        }
