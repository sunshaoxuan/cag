import asyncio
from typing import Any

from app.database import Database
from app.models import TaskStatus
from app.models.base import utc_now
from app.runtimes.base import AgentRuntime
from app.services.task_service import TaskNotFoundError, TaskService
from app.workspaces.manager import WorkspaceManager


class TaskExecutor:
    def __init__(
        self,
        database: Database,
        runtime: AgentRuntime,
        task_service: TaskService,
        workspace_manager: WorkspaceManager,
    ) -> None:
        self._database = database
        self._runtime = runtime
        self._task_service = task_service
        self._workspace_manager = workspace_manager

    async def execute(self, task_id: str) -> None:
        with self._database.session_factory() as session:
            try:
                task = self._task_service.get_task(session, task_id)
            except TaskNotFoundError:
                return
            task.status = TaskStatus.PREPARING
            task.started_at = utc_now()
            self._task_service.append_event(
                session,
                task=task,
                event_type="task.started",
                data={"runtime_profile": task.runtime_profile},
            )
            session.commit()
            project_code = task.project.code
            prompt = task.prompt
            runtime_profile = task.runtime_profile
            project_config = self._task_service.project_registry.get_by_code(
                project_code
            )

        if project_config is None:
            await self._fail_task(task_id, "Project configuration is unavailable")
            return

        await self._emit(
            task_id,
            "workspace.preparing",
            {
                "workspace_type": project_config.workspace.type,
                "branch": project_config.repository.default_branch,
            },
        )
        try:
            workspace = await asyncio.to_thread(
                self._workspace_manager.prepare,
                project=project_config,
                task_id=task_id,
            )
        except Exception as exc:
            await self._fail_task(task_id, str(exc))
            return

        with self._database.session_factory() as session:
            task = self._task_service.get_task(session, task_id)
            task.workspace_id = workspace.workspace_id
            task.workspace_path = str(workspace.path)
            task.workspace_commit = workspace.commit_sha
            task.status = TaskStatus.RUNNING
            self._task_service.append_event(
                session,
                task=task,
                event_type="workspace.ready",
                data={
                    "workspace_id": workspace.workspace_id,
                    "commit_sha": workspace.commit_sha,
                    "branch": workspace.branch,
                },
            )
            session.commit()

        async def emit(event_type: str, data: dict[str, Any]) -> None:
            await self._emit(task_id, event_type, data)

        try:
            result = await self._runtime.execute(
                task_id=task_id,
                project_code=project_code,
                prompt=prompt,
                runtime_profile=runtime_profile,
                workspace_path=workspace.path,
                emit=emit,
            )
        except Exception as exc:
            await self._fail_task(task_id, str(exc))
            return

        with self._database.session_factory() as session:
            task = self._task_service.get_task(session, task_id)
            task.status = TaskStatus.COMPLETED
            task.final_report = result.to_report()
            task.completed_at = utc_now()
            self._task_service.append_event(
                session,
                task=task,
                event_type="task.completed",
                data={"report": task.final_report},
            )
            session.commit()

    async def _emit(
        self,
        task_id: str,
        event_type: str,
        data: dict[str, Any],
    ) -> None:
        with self._database.session_factory() as event_session:
            event_task = self._task_service.get_task(event_session, task_id)
            self._task_service.append_event(
                event_session,
                task=event_task,
                event_type=event_type,
                data=data,
            )
            event_session.commit()

    async def _fail_task(self, task_id: str, error: str) -> None:
        with self._database.session_factory() as session:
            task = self._task_service.get_task(session, task_id)
            task.status = TaskStatus.FAILED
            task.error = error
            task.completed_at = utc_now()
            self._task_service.append_event(
                session,
                task=task,
                event_type="task.failed",
                data={"error": error},
            )
            session.commit()
