from pathlib import Path
import json
import tomllib

from app.config import APP_VERSION


def test_version_is_consistent_across_release_files() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    version_file = (repository_root / "VERSION").read_text(encoding="utf-8").strip()
    pyproject = tomllib.loads(
        (repository_root / "backend" / "pyproject.toml").read_text(encoding="utf-8")
    )
    frontend_package = json.loads(
        (repository_root / "frontend" / "package.json").read_text(
            encoding="utf-8"
        )
    )
    readme = (repository_root / "README.md").read_text(encoding="utf-8")
    api_document = (repository_root / "docs" / "api.md").read_text(
        encoding="utf-8"
    )
    requirements_matrix = (
        repository_root / "docs" / "requirements-matrix.md"
    ).read_text(encoding="utf-8")
    changelog = (repository_root / "CHANGELOG.md").read_text(encoding="utf-8")

    assert APP_VERSION == version_file
    assert pyproject["project"]["version"] == version_file
    assert frontend_package["version"] == version_file
    assert f"当前版本为 `{version_file}`" in readme
    assert f"Current version: `{version_file}`" in api_document
    assert f"Status for {version_file}" in requirements_matrix
    assert f"## {version_file}" in changelog
