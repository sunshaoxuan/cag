import asyncio
from pathlib import Path
from typing import Any

from app.database import Database
from app.models import TaskStatus
from app.models.base import utc_now
from app.runtimes.base import AgentRuntime
from app.services.task_service import TaskNotFoundError, TaskService
from app.workspaces.manager import WorkspaceManager
from app.knowledge.service import KnowledgeService


class TaskExecutor:
    def __init__(
        self,
        database: Database,
        runtime: AgentRuntime,
        task_service: TaskService,
        workspace_manager: WorkspaceManager,
        self_improvement_root: Path | None = None,
        knowledge_service: KnowledgeService | None = None,
    ) -> None:
        self._database = database
        self._runtime = runtime
        self._task_service = task_service
        self._workspace_manager = workspace_manager
        self._self_improvement_root = self_improvement_root
        self._knowledge_service = knowledge_service

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
            knowledge_mode = task.knowledge_mode
            conversation_id = task.conversation_id
            conversation_thread_id = (
                task.conversation.codex_thread_id
                if task.conversation is not None
                else None
            )
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

        additional_workspace_roots = ()
        developer_instructions = None
        if (
            knowledge_mode != "off"
            and self._knowledge_service is not None
            and self._knowledge_service.configured
        ):
            await self._emit(task_id, "knowledge.retrieval.started", {})
            try:
                with self._database.session_factory() as knowledge_session:
                    knowledge_task = self._task_service.get_task(
                        knowledge_session, task_id
                    )
                    knowledge_project = knowledge_task.project
                    knowledge_prompt = knowledge_task.prompt
                knowledge_context, citations = (
                    await self._knowledge_service.build_context(
                        task_id=task_id,
                        project=knowledge_project,
                        query=knowledge_prompt,
                    )
                )
                await self._emit(
                    task_id,
                    "knowledge.retrieval.completed",
                    {"citation_count": len(citations)},
                )
                if knowledge_context:
                    developer_instructions = knowledge_context
                    await self._emit(
                        task_id,
                        "knowledge.context.injected",
                        {
                            "citation_count": len(citations),
                            "citations": citations,
                        },
                    )
            except Exception as exc:
                await self._emit(
                    task_id,
                    "knowledge.retrieval.failed",
                    {"error": str(exc), "mode": knowledge_mode},
                )
                if knowledge_mode == "required":
                    await self._fail_task(task_id, str(exc))
                    return
        if runtime_profile == "self-improvement-candidate":
            if self._self_improvement_root is None:
                await self._fail_task(
                    task_id,
                    "Self-improvement root is not configured",
                )
                return
            candidate_root = (
                self._self_improvement_root
                / "outputs"
                / f"cag-{task_id}"
            )
            candidate_root.mkdir(parents=True, exist_ok=True)
            additional_workspace_roots = (candidate_root,)
            self_improvement_instructions = (
                "After completing the requested project work, write reusable "
                f"self-improvement candidates only under {candidate_root}. "
                "Create TASK_LEARNING_RECEIPT.md with task_type, "
                "reusable_pattern, failure_or_correction, candidate_skill, "
                "candidate_validator, install_status, and evidence_paths. "
                "Every candidate must include trigger, input, process, output, "
                "acceptance, and rollback. Keep install_status as proposed. "
                "Do not install or overwrite formal skills, rules, or validators."
            )
            developer_instructions = (
                f"{developer_instructions}\n\n{self_improvement_instructions}"
                if developer_instructions
                else self_improvement_instructions
            )

        try:
            result = await self._runtime.execute(
                task_id=task_id,
                project_code=project_code,
                prompt=prompt,
                runtime_profile=runtime_profile,
                persistent_conversation=conversation_id is not None,
                conversation_thread_id=conversation_thread_id,
                workspace_path=workspace.path,
                additional_workspace_roots=additional_workspace_roots,
                developer_instructions=developer_instructions,
                emit=emit,
            )
        except Exception as exc:
            await self._fail_task(task_id, str(exc))
            return

        with self._database.session_factory() as session:
            task = self._task_service.get_task(session, task_id)
            task.final_report = result.to_report()
            if conversation_id is not None and result.runtime_thread_id is not None:
                conversation = task.conversation
                if conversation is not None:
                    conversation.codex_thread_id = result.runtime_thread_id
            session.commit()

        if (
            knowledge_mode != "off"
            and self._knowledge_service is not None
            and self._knowledge_service.configured
        ):
            await self._emit(task_id, "memory.extraction.started", {})
            try:
                candidate_ids = await self._knowledge_service.capture_memory(
                    task_id=task_id,
                    project=task.project,
                    prompt=task.prompt,
                    final_report=task.final_report or {},
                )
                for candidate_id in candidate_ids:
                    await self._emit(
                        task_id,
                        "memory.candidate.created",
                        {"candidate_id": candidate_id},
                    )
                await self._emit(
                    task_id,
                    "memory.extraction.completed",
                    {"candidate_count": len(candidate_ids)},
                )
            except Exception as exc:
                await self._emit(
                    task_id,
                    "memory.extraction.failed",
                    {"error": str(exc)},
                )

        with self._database.session_factory() as session:
            task = self._task_service.get_task(session, task_id)
            task.status = TaskStatus.COMPLETED
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
