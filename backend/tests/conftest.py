from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.runtimes.base import AgentRuntime


def sqlite_url(path: Path) -> str:
    return f"sqlite+pysqlite:///{path.as_posix()}"


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        environment="test",
        database_url=sqlite_url(tmp_path / "gateway.sqlite"),
        fake_runtime_delay_ms=0,
        sse_poll_interval_ms=10,
        auto_create_schema=True,
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
