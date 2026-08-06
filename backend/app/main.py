from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import router
from app.config import APP_NAME, APP_VERSION, Settings, get_settings
from app.database import Database
from app.runtimes.base import AgentRuntime
from app.runtimes.codex_app_server import CodexAppServerRuntime
from app.runtimes.fake import FakeAgentRuntime
from app.projects.registry import ProjectRegistry
from app.services.task_service import TaskService
from app.tasks.executor import TaskExecutor
from app.workspaces.manager import WorkspaceManager
from app.knowledge.ollama import OllamaClient
from app.knowledge.scheduler import KnowledgeScheduler
from app.knowledge.security import load_knowledge_cipher
from app.knowledge.service import KnowledgeService
from app.knowledge.extraction import CustomerKnowledgeExtractionService
from app.approvals.service import ApprovalService
from app.harness.service import AgentHarness
from app.policies.command_policy import CommandPolicyService
from app.capabilities.service import CapabilityService
from app.learning.service import LearningService
from app.queue.coordinator import QueueCoordinator
from app.queue.notifier import QueueNotifier
from app.queue.service import QueueService
from app.operations.service import OperationalIssueService
from fastapi import Request
import asyncio


def create_app(
    settings: Settings | None = None,
    runtime: AgentRuntime | None = None,
) -> FastAPI:
    active_settings = settings or get_settings()
    database = Database(
        active_settings.database_url,
        allow_sqlite_for_tests=(
            active_settings.environment == "test"
            and active_settings.allow_sqlite_for_tests
        ),
    )
    project_registry = ProjectRegistry(active_settings.projects_dir)
    task_service = TaskService(project_registry)
    knowledge_service = KnowledgeService(
        database=database,
        settings=active_settings,
        provider=OllamaClient(
            base_url=active_settings.ollama_base_url,
            embedding_model=active_settings.ollama_embedding_model,
            memory_model=active_settings.ollama_memory_model,
            dimensions=active_settings.ollama_embedding_dimensions,
            timeout_seconds=active_settings.ollama_timeout_seconds,
        ),
        cipher=load_knowledge_cipher(active_settings),
    )
    workspace_manager = WorkspaceManager(
        root=active_settings.workspace_root,
        git_executable=active_settings.git_executable,
        prepare_timeout_seconds=active_settings.workspace_prepare_timeout_seconds,
    )
    if runtime is not None:
        active_runtime = runtime
    elif active_settings.runtime_provider == "fake":
        active_runtime = FakeAgentRuntime(
            delay_ms=active_settings.fake_runtime_delay_ms
        )
    elif active_settings.runtime_provider == "codex-app-server":
        if active_settings.codex_executable is None:
            raise ValueError(
                "AGENT_GATEWAY_CODEX_EXECUTABLE is required for "
                "codex-app-server"
            )
        active_runtime = CodexAppServerRuntime(
            command=[
                str(active_settings.codex_executable),
                "app-server",
                "--stdio",
            ],
            startup_timeout_seconds=(
                active_settings.codex_startup_timeout_seconds
            ),
            turn_timeout_seconds=active_settings.codex_turn_timeout_seconds,
            require_chatgpt_auth=(
                active_settings.codex_require_chatgpt_auth
            ),
        )
    else:
        raise ValueError(
            f"Unsupported runtime provider: {active_settings.runtime_provider}"
        )
    approval_service = ApprovalService(
        database=database,
        task_service=task_service,
        policy=CommandPolicyService(),
        timeout_seconds=active_settings.approval_timeout_seconds,
    )
    harness = AgentHarness(
        database=database,
        runtime=active_runtime,
        workspace_manager=workspace_manager,
        approval_service=approval_service,
        max_parallel_agents=active_settings.harness_max_parallel_agents,
        agent_timeout_seconds=active_settings.harness_agent_timeout_seconds,
    )
    capability_service = CapabilityService(
        database=database,
        self_improvement_root=active_settings.self_improvement_root,
    )
    learning_service = LearningService(
        database=database,
        capabilities=capability_service,
    )
    operational_issue_service = OperationalIssueService(
        database=database,
        runtime=active_runtime,
        project_registry=project_registry,
        task_service=task_service,
        workspace_manager=workspace_manager,
    )
    task_executor = TaskExecutor(
        database=database,
        runtime=active_runtime,
        task_service=task_service,
        workspace_manager=workspace_manager,
        self_improvement_root=active_settings.self_improvement_root,
        knowledge_service=knowledge_service,
        harness=harness,
        learning_service=learning_service,
        operational_issue_service=operational_issue_service,
    )
    queue_service = QueueService(
        database=database,
        task_service=task_service,
        lease_seconds=active_settings.queue_lease_seconds,
    )
    queue_notifier = QueueNotifier(
        redis_url=active_settings.redis_url,
        channel_prefix=active_settings.queue_redis_channel_prefix,
        enabled=active_settings.queue_redis_enabled,
    )
    extraction_service = CustomerKnowledgeExtractionService(
        database=database,
        settings=active_settings,
        knowledge_service=knowledge_service,
        task_service=task_service,
    )
    queue_coordinator = QueueCoordinator(
        service=queue_service,
        notifier=queue_notifier,
        task_executor=task_executor,
        knowledge_service=knowledge_service,
        extraction_service=extraction_service,
        interactive_workers=active_settings.queue_interactive_workers,
        knowledge_workers=active_settings.queue_knowledge_workers,
        operations_workers=active_settings.queue_operations_workers,
        operational_issue_service=operational_issue_service,
        poll_seconds=active_settings.queue_poll_seconds,
        heartbeat_seconds=active_settings.queue_heartbeat_seconds,
        shutdown_seconds=active_settings.queue_shutdown_seconds,
    )
    knowledge_scheduler = KnowledgeScheduler(
        service=knowledge_service,
        poll_seconds=active_settings.knowledge_scheduler_poll_seconds,
        lease_seconds=active_settings.knowledge_scheduler_lease_seconds,
        notify_ingestion=queue_coordinator.notify,
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        if active_settings.auto_create_schema:
            database.create_schema()
        with database.session_factory() as recovery_session:
            task_service.ensure_audit_cursor(recovery_session)
        capability_service.seed_defaults()
        worker_role = active_settings.process_role in {"worker", "combined"}
        if active_settings.queue_enabled:
            if worker_role:
                await queue_coordinator.start()
            else:
                await queue_notifier.start()
        if (
            worker_role
            and
            active_settings.knowledge_scheduler_enabled
            and knowledge_service.configured
        ):
            knowledge_scheduler.start()
        try:
            yield
        finally:
            await knowledge_scheduler.stop()
            await queue_coordinator.stop()
            database.dispose()

    application = FastAPI(
        title="One Agent Gateway",
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
    application.state.knowledge_service = knowledge_service
    application.state.knowledge_scheduler = knowledge_scheduler
    application.state.approval_service = approval_service
    application.state.harness = harness
    application.state.capability_service = capability_service
    application.state.learning_service = learning_service
    application.state.task_executor = task_executor
    application.state.queue_service = queue_service
    application.state.queue_notifier = queue_notifier
    application.state.queue_coordinator = queue_coordinator
    application.state.extraction_service = extraction_service
    application.state.operational_issue_service = operational_issue_service

    @application.middleware("http")
    async def capture_unhandled_api_failure(request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as error:
            project = next(iter(project_registry.list()), None)
            if project is not None:
                try:
                    await asyncio.to_thread(
                        operational_issue_service.capture,
                        project_reference=project.id,
                        source_type="api",
                        source_id=request.url.path,
                        title=f"Unhandled API failure: {request.method} {request.url.path}",
                        error_type=type(error).__name__,
                        error_message=str(error),
                        severity="high",
                        evidence={
                            "method": request.method,
                            "path": request.url.path,
                        },
                    )
                except Exception:
                    pass
            raise
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:5174",
            "http://127.0.0.1:5174",
        ],
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=[
            "Content-Type",
            "Idempotency-Key",
            "Last-Event-ID",
            "X-CAG-Client-ID",
            "X-CAG-Source",
            "X-Request-ID",
        ],
    )
    application.include_router(router)
    return application


app = create_app()
