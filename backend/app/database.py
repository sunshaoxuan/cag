from collections.abc import Iterator

from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.models.base import Base


class Database:
    def __init__(self, url: str, *, allow_sqlite_for_tests: bool = False) -> None:
        backend_name = make_url(url).get_backend_name()
        if backend_name == "sqlite" and not allow_sqlite_for_tests:
            raise ValueError(
                "SQLite is restricted to isolated tests. "
                "Configure PostgreSQL with pgvector for One Agent Gateway."
            )
        if backend_name not in {"postgresql", "sqlite"}:
            raise ValueError(
                "One Agent Gateway supports PostgreSQL with pgvector only."
            )
        self.backend_name = backend_name
        connect_args: dict[str, object] = {}
        if backend_name == "sqlite":
            connect_args["check_same_thread"] = False

        self.engine: Engine = create_engine(
            url,
            connect_args=connect_args,
            pool_pre_ping=True,
        )
        if backend_name == "sqlite":
            event.listen(self.engine, "connect", self._enable_sqlite_foreign_keys)
        self.session_factory = sessionmaker(
            bind=self.engine,
            autoflush=False,
            expire_on_commit=False,
            class_=Session,
        )

    @staticmethod
    def _enable_sqlite_foreign_keys(dbapi_connection: object, _: object) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    def create_schema(self) -> None:
        Base.metadata.create_all(self.engine)

    def drop_schema(self) -> None:
        Base.metadata.drop_all(self.engine)

    def is_ready(self) -> bool:
        with self.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            if self.backend_name == "postgresql":
                extension_version = connection.scalar(
                    text(
                        "SELECT extversion FROM pg_extension "
                        "WHERE extname = 'vector'"
                    )
                )
                if extension_version is None:
                    raise RuntimeError(
                        "PostgreSQL is reachable but pgvector is unavailable."
                    )
        return True

    @property
    def native_vector_search(self) -> bool:
        return self.backend_name == "postgresql"

    def storage_status(self) -> dict[str, str | bool | None]:
        extension_version: str | None = None
        if self.backend_name == "postgresql":
            with self.engine.connect() as connection:
                extension_version = connection.scalar(
                    text(
                        "SELECT extversion FROM pg_extension "
                        "WHERE extname = 'vector'"
                    )
                )
        return {
            "backend": self.backend_name,
            "native_vector_search": self.native_vector_search,
            "pgvector_version": extension_version,
        }

    def session(self) -> Iterator[Session]:
        db_session = self.session_factory()
        try:
            yield db_session
        finally:
            db_session.close()

    def dispose(self) -> None:
        self.engine.dispose()
