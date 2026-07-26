from pathlib import Path

import pytest

from app.main import create_app


def test_codex_runtime_requires_executable(settings) -> None:
    with pytest.raises(
        ValueError,
        match="AGENT_GATEWAY_CODEX_EXECUTABLE",
    ):
        create_app(
            settings=settings.model_copy(
                update={
                    "runtime_provider": "codex-app-server",
                    "codex_executable": None,
                }
            )
        )


def test_codex_runtime_can_be_selected(settings) -> None:
    app = create_app(
        settings=settings.model_copy(
            update={
                "runtime_provider": "codex-app-server",
                "codex_executable": Path("codex.exe"),
            }
        )
    )

    app.state.database.dispose()


def test_unknown_runtime_provider_is_rejected(settings) -> None:
    with pytest.raises(ValueError, match="Unsupported runtime provider"):
        create_app(
            settings=settings.model_copy(
                update={"runtime_provider": "unsupported"}
            )
        )
