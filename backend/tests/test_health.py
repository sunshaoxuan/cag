from fastapi.testclient import TestClient


def test_live_health_reports_version(client: TestClient) -> None:
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "agent-gateway",
        "version": "0.8.0",
    }


def test_ready_health_checks_database(client: TestClient) -> None:
    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"
