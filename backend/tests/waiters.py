from __future__ import annotations

import time
from typing import Any

from fastapi.testclient import TestClient


def wait_for_task(
    client: TestClient,
    task_id: str,
    *,
    terminal: set[str] | None = None,
    timeout_seconds: float = 5,
) -> dict[str, Any]:
    expected = terminal or {"completed", "failed", "cancelled"}
    deadline = time.monotonic() + timeout_seconds
    last: dict[str, Any] | None = None
    while time.monotonic() < deadline:
        response = client.get(f"/api/v1/tasks/{task_id}")
        response.raise_for_status()
        last = response.json()
        if last["status"] in expected:
            return last
        time.sleep(0.02)
    raise AssertionError(
        f"Task {task_id} did not reach {sorted(expected)}; last={last}"
    )


def wait_for_ingestion(
    client: TestClient,
    ingestion_id: str,
    *,
    timeout_seconds: float = 10,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    last: dict[str, Any] | None = None
    while time.monotonic() < deadline:
        response = client.get(
            f"/api/v1/knowledge/ingestions/{ingestion_id}"
        )
        response.raise_for_status()
        last = response.json()
        if last["status"] in {"completed", "failed", "cancelled"}:
            return last
        time.sleep(0.02)
    raise AssertionError(
        f"Ingestion {ingestion_id} did not finish; last={last}"
    )
