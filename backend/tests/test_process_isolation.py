import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

import pytest


POSTGRES_URL = os.getenv("AGENT_GATEWAY_TEST_POSTGRES_URL")


def free_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def request_json(url: str, *, payload: dict | None = None) -> dict:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(request, timeout=2) as response:
        return json.loads(response.read().decode("utf-8"))


def terminate(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


@pytest.mark.skipif(
    not POSTGRES_URL,
    reason="AGENT_GATEWAY_TEST_POSTGRES_URL is not configured",
)
def test_api_remains_responsive_while_worker_executes_task(
    tmp_path: Path,
    projects_dir: Path,
) -> None:
    database_url = str(POSTGRES_URL)
    port = free_port()
    environment = {
        **os.environ,
        "AGENT_GATEWAY_ENVIRONMENT": "test",
        "AGENT_GATEWAY_DATABASE_URL": database_url,
        "AGENT_GATEWAY_ALLOW_SQLITE_FOR_TESTS": "false",
        "AGENT_GATEWAY_AUTO_CREATE_SCHEMA": "false",
        "AGENT_GATEWAY_QUEUE_REDIS_ENABLED": "false",
        "AGENT_GATEWAY_PROJECTS_DIR": str(projects_dir),
        "AGENT_GATEWAY_WORKSPACE_ROOT": str(tmp_path / "workspaces"),
        "AGENT_GATEWAY_RUNTIME_PROVIDER": "fake",
        "AGENT_GATEWAY_FAKE_RUNTIME_DELAY_MS": "3000",
        "AGENT_GATEWAY_KNOWLEDGE_ENABLED": "false",
        "AGENT_GATEWAY_KNOWLEDGE_SCHEDULER_ENABLED": "false",
        "AGENT_GATEWAY_QUEUE_INTERACTIVE_WORKERS": "1",
        "AGENT_GATEWAY_QUEUE_KNOWLEDGE_WORKERS": "1",
        "AGENT_GATEWAY_QUEUE_OPERATIONS_WORKERS": "1",
        "AGENT_GATEWAY_QUEUE_POLL_SECONDS": "0.1",
        "AGENT_GATEWAY_QUEUE_HEARTBEAT_SECONDS": "1",
    }
    hidden = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    worker_environment = {**environment, "AGENT_GATEWAY_PROCESS_ROLE": "worker"}
    api_environment = {**environment, "AGENT_GATEWAY_PROCESS_ROLE": "api"}
    worker = subprocess.Popen(
        [sys.executable, "-m", "app.worker"],
        env=worker_environment,
        cwd=Path(__file__).resolve().parents[1],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        creationflags=hidden,
    )
    api = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        env=api_environment,
        cwd=Path(__file__).resolve().parents[1],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        creationflags=hidden,
    )
    try:
        base_url = f"http://127.0.0.1:{port}"
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            try:
                if request_json(f"{base_url}/health/live")["status"] == "ok":
                    break
            except (urllib.error.URLError, TimeoutError):
                time.sleep(0.1)
        else:
            raise AssertionError("API process did not become live")

        created = request_json(
            f"{base_url}/api/v1/tasks",
            payload={
                "project_id": "test-project",
                "prompt": "Exercise isolated worker availability.",
                "knowledge_mode": "off",
                "learning_mode": "off",
            },
        )
        latencies = []
        observed_active = False
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if worker.poll() is not None:
                error = (worker.stderr.read() if worker.stderr else b"").decode(
                    "utf-8", errors="replace"
                )
                raise AssertionError(f"Worker exited during task: {error[-1000:]}")
            started = time.monotonic()
            live = request_json(f"{base_url}/health/live")
            task = request_json(f"{base_url}/api/v1/tasks/{created['id']}")
            latencies.append(time.monotonic() - started)
            assert live["status"] == "ok"
            if task["status"] in {"preparing", "running"}:
                observed_active = True
            if task["status"] == "completed":
                break
            time.sleep(0.05)
        else:
            raise AssertionError("Isolated worker task did not complete")

        queue_status = request_json(f"{base_url}/api/v1/queue/status")
        worker_pids = {item["process_id"] for item in queue_status["workers"]}
        assert observed_active is True
        assert worker_pids
        assert queue_status["local_consumers_running"] is False
        assert worker.poll() is None
        assert api.poll() is None
        assert max(latencies) < 1.0
    finally:
        terminate(api)
        terminate(worker)
