from collections.abc import Iterator
from pathlib import Path
import subprocess

import pytest
import yaml
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.runtimes.base import AgentRuntime


def sqlite_url(path: Path) -> str:
    return f"sqlite+pysqlite:///{path.as_posix()}"


@pytest.fixture
def project_repository(tmp_path: Path) -> Path:
    repository = tmp_path / "source-repository"
    repository.mkdir()
    subprocess.run(
        ["git", "init", "--initial-branch=master", str(repository)],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(repository), "config", "user.name", "Test User"],
        check=True,
    )
    subprocess.run(
        [
            "git",
            "-C",
            str(repository),
            "config",
            "user.email",
            "test@example.invalid",
        ],
        check=True,
    )
    (repository / "README.md").write_text(
        "# Test project\n",
        encoding="utf-8",
    )
    subprocess.run(
        ["git", "-C", str(repository), "add", "README.md"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(repository), "commit", "-m", "initial"],
        check=True,
        capture_output=True,
    )
    return repository


@pytest.fixture
def projects_dir(tmp_path: Path, project_repository: Path) -> Path:
    directory = tmp_path / "projects"
    directory.mkdir()
    config = {
        "physical_id": "f10d23c0-2d10-4cab-a1fa-f43df90b6c3f",
        "id": "test-project",
        "name": "Test Project",
        "version": "1",
        "tenant": {"code": "customer-a", "name": "Customer A"},
        "product": {
            "code": "test-product",
            "name": "Test Product",
            "version": "1.0.0",
        },
        "knowledge": {
            "enabled": True,
            "default_mode": "assist",
            "source_scope": "tenant",
        },
        "repository": {
            "url": str(project_repository),
            "default_branch": "master",
        },
        "workspace": {"type": "git_clone"},
        "instructions": {"files": ["README.md"]},
        "runtime": {
            "default_profile": "general-engineering",
            "allowed_profiles": [
                "general-engineering",
                "self-improvement-candidate",
            ],
        },
    }
    (directory / "test-project.yaml").write_text(
        yaml.safe_dump(config, sort_keys=False),
        encoding="utf-8",
    )
    return directory


@pytest.fixture
def settings(tmp_path: Path, projects_dir: Path) -> Settings:
    return Settings(
        environment="test",
        database_url=sqlite_url(tmp_path / "gateway.sqlite"),
        fake_runtime_delay_ms=0,
        sse_poll_interval_ms=10,
        auto_create_schema=True,
        projects_dir=projects_dir,
        workspace_root=tmp_path / "workspaces",
    )


@pytest.fixture
def app_factory(settings: Settings):
    def factory(runtime: AgentRuntime | None = None):
        return create_app(settings=settings, runtime=runtime)

    return factory


@pytest.fixture
def client(app_factory) -> Iterator[TestClient]:
    with TestClient(app_factory()) as test_client:
        yield test_client
