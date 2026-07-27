from fastapi.testclient import TestClient


def test_list_projects_returns_physical_id_and_business_code(
    client: TestClient,
) -> None:
    response = client.get("/api/v1/projects")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": "f10d23c0-2d10-4cab-a1fa-f43df90b6c3f",
            "code": "test-project",
            "name": "Test Project",
            "default_branch": "master",
            "default_runtime_profile": "general-engineering",
            "allowed_runtime_profiles": [
                "general-engineering",
                "self-improvement-candidate",
            ],
        }
    ]


def test_get_project_accepts_code_or_physical_id(client: TestClient) -> None:
    by_code = client.get("/api/v1/projects/test-project")
    by_id = client.get(
        "/api/v1/projects/f10d23c0-2d10-4cab-a1fa-f43df90b6c3f"
    )

    assert by_code.status_code == 200
    assert by_code.json() == by_id.json()


def test_get_unknown_project_returns_404(client: TestClient) -> None:
    response = client.get("/api/v1/projects/unknown")

    assert response.status_code == 404
