from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Protocol

from app.config import Settings
from app.knowledge.security import KnowledgeCipher


class ArtifactUnavailableError(RuntimeError):
    pass


class ArtifactIntegrityError(RuntimeError):
    pass


@dataclass(frozen=True)
class StoredObject:
    replica_name: str
    backend: str
    bucket: str
    object_key: str
    checksum_sha256: str
    etag: str | None = None
    version_id: str | None = None


class ArtifactObjectStore(Protocol):
    replica_name: str
    backend: str
    bucket: str

    def put(self, object_key: str, content: bytes, checksum_sha256: str) -> StoredObject: ...

    def get(self, object_key: str) -> bytes: ...

    def head(self, object_key: str) -> StoredObject | None: ...

    def list_keys(self) -> set[str]: ...

    def replace(self, object_key: str, content: bytes, checksum_sha256: str) -> StoredObject: ...


class FilesystemArtifactObjectStore:
    backend = "filesystem"

    def __init__(
        self, *, replica_name: str, root: Path, cipher: KnowledgeCipher | None = None
    ) -> None:
        self.replica_name = replica_name
        self.root = root.resolve()
        self.bucket = self.root.name
        self.cipher = cipher

    def _path(self, object_key: str) -> Path:
        candidate = (self.root / object_key).resolve()
        if not candidate.is_relative_to(self.root):
            raise ValueError("Object key escapes the artifact root")
        return candidate

    def put(
        self, object_key: str, content: bytes, checksum_sha256: str
    ) -> StoredObject:
        if object_key != object_key_for_sha256(checksum_sha256):
            raise ArtifactIntegrityError("Artifact object key does not match checksum")
        actual = sha256(content).hexdigest()
        if actual != checksum_sha256:
            raise ArtifactIntegrityError("Artifact payload checksum mismatch")
        target = self._path(object_key)
        stored_content = self.cipher.encrypt_bytes(content) if self.cipher else content
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            existing = self._decode(target.read_bytes())
            if sha256(existing).hexdigest() != checksum_sha256:
                raise ArtifactIntegrityError("Stored artifact checksum mismatch")
        else:
            with NamedTemporaryFile(
                dir=target.parent, prefix=".artifact-", delete=False
            ) as handle:
                temporary = Path(handle.name)
                handle.write(stored_content)
                handle.flush()
            try:
                temporary.replace(target)
            finally:
                temporary.unlink(missing_ok=True)
        return StoredObject(
            replica_name=self.replica_name,
            backend=self.backend,
            bucket=self.bucket,
            object_key=object_key,
            checksum_sha256=checksum_sha256,
            etag=checksum_sha256,
        )

    def get(self, object_key: str) -> bytes:
        try:
            return self._decode(self._path(object_key).read_bytes())
        except FileNotFoundError as exc:
            raise ArtifactUnavailableError("Artifact replica is unavailable") from exc

    def head(self, object_key: str) -> StoredObject | None:
        path = self._path(object_key)
        if not path.is_file():
            return None
        checksum = sha256(self._decode(path.read_bytes())).hexdigest()
        return StoredObject(
            replica_name=self.replica_name,
            backend=self.backend,
            bucket=self.bucket,
            object_key=object_key,
            checksum_sha256=checksum,
            etag=checksum,
        )

    def list_keys(self) -> set[str]:
        if not self.root.exists():
            return set()
        return {
            path.relative_to(self.root).as_posix()
            for path in self.root.rglob("*")
            if path.is_file() and not path.name.startswith(".artifact-")
        }

    def replace(self, object_key: str, content: bytes, checksum_sha256: str) -> StoredObject:
        self._path(object_key).unlink(missing_ok=True)
        return self.put(object_key, content, checksum_sha256)

    def _decode(self, content: bytes) -> bytes:
        return self.cipher.decrypt_bytes(content) if self.cipher else content


class S3ArtifactObjectStore:
    backend = "s3"

    def __init__(
        self,
        *,
        replica_name: str,
        endpoint_url: str,
        region: str,
        bucket: str,
        access_key: str,
        secret_key: str,
        verify_tls: bool,
        cipher: KnowledgeCipher | None = None,
    ) -> None:
        import boto3

        self.replica_name = replica_name
        self.bucket = bucket
        self.cipher = cipher
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            verify=verify_tls,
        )

    def put(
        self, object_key: str, content: bytes, checksum_sha256: str
    ) -> StoredObject:
        if object_key != object_key_for_sha256(checksum_sha256):
            raise ArtifactIntegrityError("Artifact object key does not match checksum")
        actual = sha256(content).hexdigest()
        if actual != checksum_sha256:
            raise ArtifactIntegrityError("Artifact payload checksum mismatch")
        stored_content = self.cipher.encrypt_bytes(content) if self.cipher else content
        response = self.client.put_object(
            Bucket=self.bucket,
            Key=object_key,
            Body=stored_content,
            Metadata={"sha256": checksum_sha256},
        )
        stored = self.head(object_key)
        if stored is None or stored.checksum_sha256 != checksum_sha256:
            raise ArtifactIntegrityError("S3 artifact checksum verification failed")
        return StoredObject(
            **{
                **stored.__dict__,
                "etag": response.get("ETag", stored.etag).strip('"'),
                "version_id": response.get("VersionId"),
            }
        )

    def get(self, object_key: str) -> bytes:
        try:
            content = self.client.get_object(Bucket=self.bucket, Key=object_key)[
                "Body"
            ].read()
            return self.cipher.decrypt_bytes(content) if self.cipher else content
        except Exception as exc:
            status = getattr(exc, "response", {}).get("ResponseMetadata", {}).get(
                "HTTPStatusCode"
            )
            if status == 404:
                raise ArtifactUnavailableError("Artifact replica is unavailable") from exc
            raise

    def head(self, object_key: str) -> StoredObject | None:
        try:
            response = self.client.head_object(Bucket=self.bucket, Key=object_key)
        except Exception as exc:
            if getattr(exc, "response", {}).get("ResponseMetadata", {}).get(
                "HTTPStatusCode"
            ) == 404:
                return None
            raise
        checksum = response.get("Metadata", {}).get("sha256")
        if not checksum:
            checksum = sha256(self.get(object_key)).hexdigest()
        return StoredObject(
            replica_name=self.replica_name,
            backend=self.backend,
            bucket=self.bucket,
            object_key=object_key,
            checksum_sha256=checksum,
            etag=response.get("ETag", "").strip('"') or None,
            version_id=response.get("VersionId"),
        )

    def list_keys(self) -> set[str]:
        keys: set[str] = set()
        paginator = self.client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket, Prefix="sha256/"):
            keys.update(item["Key"] for item in page.get("Contents", []))
        return keys

    def replace(self, object_key: str, content: bytes, checksum_sha256: str) -> StoredObject:
        return self.put(object_key, content, checksum_sha256)


def object_key_for_sha256(checksum: str) -> str:
    if len(checksum) != 64 or any(char not in "0123456789abcdef" for char in checksum):
        raise ValueError("Invalid SHA 256 checksum")
    return f"sha256/{checksum[:2]}/{checksum[2:4]}/{checksum}"


def build_artifact_stores(
    settings: Settings, cipher: KnowledgeCipher | None
) -> list[ArtifactObjectStore]:
    if cipher is None:
        return []
    replica = FilesystemArtifactObjectStore(
        replica_name="independent-replica",
        root=settings.artifact_replica_root,
        cipher=cipher,
    )
    if settings.artifact_store_backend == "replicated-filesystem":
        primary: ArtifactObjectStore = FilesystemArtifactObjectStore(
            replica_name="primary",
            root=settings.artifact_primary_root,
            cipher=cipher,
        )
    else:
        if (
            settings.artifact_s3_endpoint_url is None
            or settings.artifact_s3_access_key is None
            or settings.artifact_s3_secret_key is None
        ):
            raise ValueError("S3 artifact storage requires endpoint and credentials")
        primary = S3ArtifactObjectStore(
            replica_name="primary",
            endpoint_url=settings.artifact_s3_endpoint_url,
            region=settings.artifact_s3_region,
            bucket=settings.artifact_s3_bucket,
            access_key=settings.artifact_s3_access_key.get_secret_value(),
            secret_key=settings.artifact_s3_secret_key.get_secret_value(),
            verify_tls=settings.artifact_s3_verify_tls,
            cipher=cipher,
        )
    return [primary, replica]
