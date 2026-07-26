from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import router
from app.config import APP_NAME, APP_VERSION, Settings, get_settings
from app.database import Database
from app.runtimes.base import AgentRuntime
from app.runtimes.fake import FakeAgentRuntime
from app.projects.registry import ProjectRegistry
from app.services.task_service import TaskService
from app.tasks.executor import TaskExecutor
from app.workspaces.manager import WorkspaceManager


def create_app(
    settings: Settings | None = None,
    runtime: AgentRuntime | None = None,
) -> FastAPI:
    active_settings = settings or get_settings()
    database = Database(active_settings.database_url)
    project_registry = ProjectRegistry(active_settings.projects_dir)
    task_service = TaskService(project_registry)
    workspace_manager = WorkspaceManager(
        root=active_settings.workspace_root,
        git_executable=active_settings.git_executable,
        prepare_timeout_seconds=active_settings.workspace_prepare_timeout_seconds,
    )
    active_runtime = runtime or FakeAgentRuntime(
        delay_ms=active_settings.fake_runtime_delay_ms
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        if active_settings.auto_create_schema:
            database.create_schema()
        yield
        database.dispose()

    application = FastAPI(
        title="Codex/ChatGPT Agent Gateway",
        version=APP_VERSION,
        description=(
            "Gateway for task execution through locally authenticated Codex runtimes."
        ),
        lifespan=lifespan,
    )
    application.state.settings = active_settings
    application.state.database = database
    application.state.project_registry = project_registry
    application.state.task_service = task_service
    application.state.task_executor = TaskExecutor(
        database=database,
        runtime=active_runtime,
        task_service=task_service,
        workspace_manager=workspace_manager,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )
    application.include_router(router)
    return application


app = create_app()
