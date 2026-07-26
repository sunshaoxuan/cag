from pathlib import Path
import tomllib

from app.config import APP_VERSION


def test_version_is_consistent_across_release_files() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    version_file = (repository_root / "VERSION").read_text(encoding="utf-8").strip()
    pyproject = tomllib.loads(
        (repository_root / "backend" / "pyproject.toml").read_text(encoding="utf-8")
    )

    assert APP_VERSION == version_file
    assert pyproject["project"]["version"] == version_file
