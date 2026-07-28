import base64
import ctypes
import hashlib
import os
import re
import shutil
import stat
import subprocess
import zipfile
from collections import deque
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Callable, Iterator
from urllib.parse import urlsplit

from app.knowledge.credentials import (
    KnowledgeCredentialStore,
    SourceCredential,
)
from app.knowledge.extractors import (
    SUPPORTED_EXTENSIONS,
    extract_text_with_metadata,
    normalize_text,
)
from app.policies.command_policy import CommandPolicyService


SOURCE_TYPES = {
    "local_directory",
    "network_share",
    "git",
    "gitlab",
    "svn",
}
EXCLUDED_PARTS = {
    ".git",
    ".idea",
    ".pytest_cache",
    ".svn",
    ".venv",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "target",
    "vendor",
}


@dataclass(frozen=True)
class SourceConfig:
    id: str
    source_type: str
    location: str
    reference: str | None
    subpath: str | None
    credential_ref: str | None


@dataclass(frozen=True)
class CollectedDocument:
    path: str
    text: str
    content_hash: str
    language: str
    encoding: str


@dataclass(frozen=True)
class CollectionResult:
    revision: str | None
    documents: list[CollectedDocument]
    files_seen: int
    rejected_files: int
    duplicate_files: int


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    revision: str | None
    message: str


CollectionProgress = Callable[[dict[str, int | str]], None]


class SourceConnectorManager:
    def __init__(
        self,
        *,
        cache_root: Path,
        allowed_roots: list[Path],
        credential_store: KnowledgeCredentialStore,
        command_policy: CommandPolicyService,
        git_executable: str,
        svn_executable: str,
        max_file_bytes: int,
    ) -> None:
        self._cache_root = cache_root.resolve()
        self._allowed_roots = allowed_roots
        self._credentials = credential_store
        self._policy = command_policy
        self._git = git_executable
        self._svn = svn_executable
        self._max_file_bytes = max_file_bytes

    @staticmethod
    def normalized_source_key(
        *,
        source_type: str,
        location: str,
        reference: str | None,
        subpath: str | None,
        scope: str,
    ) -> str:
        normalized_location = location.strip().rstrip("/\\")
        if source_type in {"local_directory", "network_share"}:
            normalized_location = normalized_location.casefold()
        payload = "\n".join(
            (
                source_type,
                normalized_location,
                (reference or "").strip(),
                (subpath or "").replace("\\", "/").strip("/"),
                scope,
            )
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def validate_definition(
        self,
        *,
        source_type: str,
        location: str,
        subpath: str | None,
    ) -> None:
        if source_type not in SOURCE_TYPES:
            raise ValueError("Unsupported knowledge source type")
        if not location.strip():
            raise ValueError("Knowledge source location is required")
        self._validate_subpath(subpath)
        if source_type == "local_directory":
            self._resolve_allowed_local_root(location)
        elif source_type == "network_share":
            if os.name != "nt" or not location.startswith("\\\\"):
                raise ValueError(
                    "Network share must be a Windows UNC path"
                )
        else:
            self._validate_repository_location(source_type, location)

    def validate(self, source: SourceConfig) -> ValidationResult:
        self.validate_definition(
            source_type=source.source_type,
            location=source.location,
            subpath=source.subpath,
        )
        credential = self._credentials.get(source.credential_ref)
        if source.source_type == "local_directory":
            root = self._selected_root(
                self._resolve_allowed_local_root(source.location),
                source.subpath,
            )
            return ValidationResult(
                True,
                self._git_revision(root),
                f"Directory is readable: {root.name}",
            )
        if source.source_type == "network_share":
            with self._network_connection(source.location, credential):
                root = self._selected_root(Path(source.location), source.subpath)
                if not root.is_dir():
                    raise ValueError("Network share directory is unavailable")
                return ValidationResult(
                    True,
                    None,
                    "Network share is readable",
                )
        if source.source_type in {"git", "gitlab"}:
            revision = self._git_remote_revision(source, credential)
            return ValidationResult(
                True, revision, "Git repository is reachable"
            )
        revision = self._svn_revision(source, credential)
        return ValidationResult(
            True, revision, "SVN repository is reachable"
        )

    def collect(
        self,
        source: SourceConfig,
        progress: CollectionProgress | None = None,
    ) -> CollectionResult:
        credential = self._credentials.get(source.credential_ref)
        if source.source_type == "local_directory":
            root = self._selected_root(
                self._resolve_allowed_local_root(source.location),
                source.subpath,
            )
            return self._read_documents(
                root,
                self._git_revision(root),
                progress,
            )
        if source.source_type == "network_share":
            with self._network_connection(source.location, credential):
                root = self._selected_root(Path(source.location), source.subpath)
                return self._read_documents(root, None, progress)
        if source.source_type in {"git", "gitlab"}:
            root, revision = self._materialize_git(source, credential)
        else:
            root, revision = self._materialize_svn(source, credential)
        return self._read_documents(
            self._selected_root(root, source.subpath),
            revision,
            progress,
        )

    def purge(self, source_id: str) -> None:
        source_cache = self._source_cache_path(source_id)
        resolved_cache = self._cache_root.resolve()
        resolved_source = source_cache.resolve()
        if resolved_cache not in resolved_source.parents:
            raise ValueError("Knowledge source cache path is invalid")
        if resolved_source.is_dir():
            shutil.rmtree(
                resolved_source,
                onexc=self._remove_readonly,
            )

    @staticmethod
    def _remove_readonly(function, path: str, error: BaseException) -> None:
        if isinstance(error, PermissionError):
            os.chmod(path, stat.S_IWRITE)
            function(path)
            return
        raise error

    def _read_documents(
        self,
        root: Path,
        revision: str | None,
        progress: CollectionProgress | None = None,
    ) -> CollectionResult:
        if not root.is_dir():
            raise ValueError("Selected source subpath does not exist")
        documents: list[CollectedDocument] = []
        rejected = 0
        duplicates = 0
        files_discovered = 0
        files_processed = 0
        directories_scanned = 0
        seen_hashes: set[str] = set()
        pending_directories = deque([root])

        def report(
            phase: str,
            directory: Path,
            *,
            current_directory_files: int = 0,
            error: str = "",
        ) -> None:
            if progress is None:
                return
            relative = (
                "."
                if directory == root
                else directory.relative_to(root).as_posix()
            )
            data: dict[str, int | str] = {
                "phase": phase,
                "directory": relative,
                "directories_scanned": directories_scanned,
                "directories_pending": len(pending_directories),
                "files_discovered": files_discovered,
                "files_processed": files_processed,
                "current_directory_files": current_directory_files,
                "rejected_files": rejected,
            }
            if error:
                data["error"] = error[:500]
            progress(data)

        while pending_directories:
            directory = pending_directories.popleft()
            report("started", directory)
            try:
                with os.scandir(directory) as iterator:
                    entries = sorted(
                        iterator,
                        key=lambda entry: entry.name.casefold(),
                    )
            except OSError as exc:
                rejected += 1
                directories_scanned += 1
                report("failed", directory, error=str(exc))
                continue

            directory_files: list[Path] = []
            for entry in entries:
                try:
                    if entry.is_dir(follow_symlinks=False):
                        if entry.name not in EXCLUDED_PARTS:
                            pending_directories.append(Path(entry.path))
                        continue
                    if (
                        not entry.is_file(follow_symlinks=False)
                        or Path(entry.name).suffix.lower()
                        not in SUPPORTED_EXTENSIONS
                        or entry.stat(follow_symlinks=False).st_size
                        > self._max_file_bytes
                    ):
                        continue
                except OSError:
                    rejected += 1
                    continue
                directory_files.append(Path(entry.path))
                files_discovered += 1

            for path in directory_files:
                try:
                    extracted = extract_text_with_metadata(path)
                    text = normalize_text(extracted.text)
                except (
                    UnicodeDecodeError,
                    OSError,
                    RuntimeError,
                    ValueError,
                    zipfile.BadZipFile,
                ):
                    rejected += 1
                    files_processed += 1
                    continue
                files_processed += 1
                if not text:
                    rejected += 1
                    continue
                content_hash = hashlib.sha256(
                    text.encode("utf-8")
                ).hexdigest()
                if content_hash in seen_hashes:
                    duplicates += 1
                    continue
                seen_hashes.add(content_hash)
                documents.append(
                    CollectedDocument(
                        path=path.relative_to(root).as_posix(),
                        text=text,
                        content_hash=content_hash,
                        language=path.suffix.lstrip(".").lower() or "text",
                        encoding=extracted.encoding,
                    )
                )
            directories_scanned += 1
            report(
                "completed",
                directory,
                current_directory_files=len(directory_files),
            )

        return CollectionResult(
            revision=revision,
            documents=documents,
            files_seen=files_discovered,
            rejected_files=rejected,
            duplicate_files=duplicates,
        )

    def _materialize_git(
        self,
        source: SourceConfig,
        credential: SourceCredential | None,
    ) -> tuple[Path, str]:
        revision = self._git_remote_revision(source, credential)
        destination = self._snapshot_path(source.id, revision)
        if not destination.is_dir():
            destination.parent.mkdir(parents=True, exist_ok=True)
            args = [self._git, "clone", "--depth", "1"]
            if source.reference:
                args.extend(["--branch", source.reference])
            args.extend(["--", source.location, str(destination)])
            self._run(args, credential=credential)
        actual = self._run(
            [self._git, "-C", str(destination), "rev-parse", "HEAD"]
        ).stdout.strip()
        return destination, actual

    def _git_remote_revision(
        self,
        source: SourceConfig,
        credential: SourceCredential | None,
    ) -> str:
        ref = source.reference or "HEAD"
        result = self._run(
            [self._git, "ls-remote", "--", source.location, ref],
            credential=credential,
        )
        line = next(
            (item for item in result.stdout.splitlines() if item.strip()),
            "",
        )
        if not line:
            raise ValueError(f"Git reference was not found: {ref}")
        return line.split()[0]

    def _materialize_svn(
        self,
        source: SourceConfig,
        credential: SourceCredential | None,
    ) -> tuple[Path, str]:
        revision = self._svn_revision(source, credential)
        destination = self._snapshot_path(source.id, revision)
        if not destination.is_dir():
            destination.parent.mkdir(parents=True, exist_ok=True)
            args = [
                self._svn,
                "export",
                "--force",
                "--ignore-externals",
                "--non-interactive",
                "--no-auth-cache",
                "-r",
                revision,
            ]
            input_text = self._append_svn_credentials(args, credential)
            args.extend([source.location, str(destination)])
            self._run(args, input_text=input_text)
        return destination, revision

    def _svn_revision(
        self,
        source: SourceConfig,
        credential: SourceCredential | None,
    ) -> str:
        args = [
            self._svn,
            "info",
            "--show-item",
            "revision",
            "--non-interactive",
            "--no-auth-cache",
        ]
        if source.reference:
            args.extend(["-r", source.reference])
        input_text = self._append_svn_credentials(args, credential)
        args.append(source.location)
        return self._run(args, input_text=input_text).stdout.strip()

    @staticmethod
    def _append_svn_credentials(
        args: list[str],
        credential: SourceCredential | None,
    ) -> str | None:
        if credential is None:
            return None
        args.extend(
            [
                "--username",
                credential.username,
                "--password-from-stdin",
            ]
        )
        return credential.secret + "\n"

    def _run(
        self,
        args: list[str],
        *,
        credential: SourceCredential | None = None,
        input_text: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        executable_name = Path(args[0]).stem
        actions = {"clone", "ls-remote", "rev-parse", "info", "export"}
        action = next((item for item in args[1:] if item in actions), "")
        policy_subject = f"{executable_name} {action}"
        decision = self._policy.evaluate(
            policy_subject, "knowledge_collection"
        )
        if decision.decision != "allow":
            raise PermissionError(decision.reason)
        environment = os.environ.copy()
        environment["GIT_TERMINAL_PROMPT"] = "0"
        if credential is not None and executable_name.lower().startswith("git"):
            token = base64.b64encode(
                f"{credential.username}:{credential.secret}".encode("utf-8")
            ).decode("ascii")
            environment["GIT_CONFIG_COUNT"] = "1"
            environment["GIT_CONFIG_KEY_0"] = "http.extraHeader"
            environment["GIT_CONFIG_VALUE_0"] = (
                f"Authorization: Basic {token}"
            )
        try:
            return subprocess.run(
                args,
                check=True,
                capture_output=True,
                text=True,
                input=input_text,
                env=environment,
                timeout=300,
            )
        except FileNotFoundError as exc:
            raise RuntimeError(
                f"Required connector executable is unavailable: {args[0]}"
            ) from exc
        except subprocess.CalledProcessError as exc:
            message = (
                exc.stderr or exc.stdout or "Connector command failed"
            ).strip()
            raise RuntimeError(message[:1000]) from exc

    def _resolve_allowed_local_root(self, value: str) -> Path:
        resolved = Path(value).resolve()
        if not resolved.is_dir():
            raise ValueError("Knowledge source path does not exist")
        if not any(
            resolved == root or root in resolved.parents
            for root in self._allowed_roots
        ):
            raise ValueError("Knowledge source path is outside configured roots")
        return resolved

    @staticmethod
    def _selected_root(root: Path, subpath: str | None) -> Path:
        if not subpath:
            return root
        selected = (root / Path(*PurePosixPath(subpath).parts)).resolve()
        resolved_root = root.resolve()
        if selected != resolved_root and resolved_root not in selected.parents:
            raise ValueError("Knowledge source subpath escapes the source root")
        return selected

    @staticmethod
    def _validate_subpath(subpath: str | None) -> None:
        if not subpath:
            return
        value = PurePosixPath(subpath.replace("\\", "/"))
        if value.is_absolute() or ".." in value.parts:
            raise ValueError(
                "Knowledge source subpath must stay inside the source"
            )

    def _validate_repository_location(
        self,
        source_type: str,
        location: str,
    ) -> None:
        parsed = urlsplit(location)
        if parsed.username is not None or parsed.password is not None:
            raise ValueError(
                "Credentials must use the operating system credential store"
            )
        if parsed.scheme in {
            "http",
            "https",
            "ssh",
            "svn",
            "svn+ssh",
            "file",
        }:
            return
        if re.match(r"^[^@\s]+@[^:\s]+:.+$", location):
            return
        if source_type in {"git", "gitlab"}:
            self._resolve_allowed_local_root(location)
            return
        raise ValueError("SVN source must use a supported repository URL")

    def _git_revision(self, root: Path) -> str | None:
        try:
            return self._run(
                [self._git, "-C", str(root), "rev-parse", "HEAD"]
            ).stdout.strip()
        except (PermissionError, RuntimeError):
            return None

    def _snapshot_path(self, source_id: str, revision: str) -> Path:
        snapshot_key = hashlib.sha256(
            revision.encode("utf-8")
        ).hexdigest()[:16]
        return self._source_cache_path(source_id) / snapshot_key

    def _source_cache_path(self, source_id: str) -> Path:
        source_key = hashlib.sha256(
            source_id.encode("utf-8")
        ).hexdigest()[:12]
        return self._cache_root / source_key

    @contextmanager
    def _network_connection(
        self,
        location: str,
        credential: SourceCredential | None,
    ) -> Iterator[None]:
        if credential is None:
            yield
            return
        if os.name != "nt":
            raise RuntimeError(
                "Authenticated network shares require a Windows Gateway host"
            )
        remote = self._unc_share_root(location)
        resource = _NETRESOURCE()
        resource.dwType = 1
        resource.lpRemoteName = remote
        result = ctypes.windll.mpr.WNetAddConnection2W(
            ctypes.byref(resource),
            credential.secret,
            credential.username,
            0,
        )
        if result not in {0, 85}:
            raise OSError(result, "Network share authentication failed")
        try:
            yield
        finally:
            ctypes.windll.mpr.WNetCancelConnection2W(remote, 0, False)

    @staticmethod
    def _unc_share_root(location: str) -> str:
        parts = [part for part in location.split("\\") if part]
        if len(parts) < 2:
            raise ValueError("Network share must include server and share name")
        return f"\\\\{parts[0]}\\{parts[1]}"


class _NETRESOURCE(ctypes.Structure):
    _fields_ = [
        ("dwScope", ctypes.c_ulong),
        ("dwType", ctypes.c_ulong),
        ("dwDisplayType", ctypes.c_ulong),
        ("dwUsage", ctypes.c_ulong),
        ("lpLocalName", ctypes.c_wchar_p),
        ("lpRemoteName", ctypes.c_wchar_p),
        ("lpComment", ctypes.c_wchar_p),
        ("lpProvider", ctypes.c_wchar_p),
    ]
