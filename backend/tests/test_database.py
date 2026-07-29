from pathlib import Path

import pytest

from app.database import Database


def test_sqlite_is_restricted_to_isolated_tests(tmp_path: Path) -> None:
    url = f"sqlite+pysqlite:///{(tmp_path / 'gateway.sqlite').as_posix()}"

    with pytest.raises(ValueError, match="restricted to isolated tests"):
        Database(url)

    database = Database(url, allow_sqlite_for_tests=True)
    try:
        assert database.backend_name == "sqlite"
        assert database.native_vector_search is False
    finally:
        database.dispose()
