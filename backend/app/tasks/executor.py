from typing import Any

from app.database import Database
from app.models import TaskStatus
from app.models.base import utc_now
from app.runtimes.base import AgentRuntime
from app.services.task_service import TaskNotFoundError, TaskService


class TaskExecutor:
    def __init__(
        self,
        database: Database,
        runtime: AgentRuntime,
        task_service: TaskService,
    ) -> None:
        self._database = database
        self._runtime = runtime
        self._task_service = task_service

    async def execute(self, task_id: str) -> None:
        with self._database.session_factory() as session:
            try:
                task = self._task_service.get_task(session, task_id)
            except TaskNotFoundError:
                return
            task.status = TaskStatus.RUNNING
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

        async def emit(event_type: str, data: dict[str, Any]) -> None:
            with self._database.session_factory() as event_session:
                event_task = self._task_service.get_task(event_session, task_id)
                self._task_service.append_event(
                    event_session,
                    task=event_task,
                    event_type=event_type,
                    data=data,
                )
                event_session.commit()

        try:
            result = await self._runtime.execute(
                task_id=task_id,
                project_code=project_code,
                prompt=prompt,
                runtime_profile=runtime_profile,
                emit=emit,
            )
        except Exception as exc:
            with self._database.session_factory() as session:
                task = self._task_service.get_task(session, task_id)
                task.status = TaskStatus.FAILED
                task.error = str(exc)
                task.completed_at = utc_now()
                self._task_service.append_event(
                    session,
                    task=task,
                    event_type="task.failed",
                    data={"error": str(exc)},
                )
                session.commit()
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
