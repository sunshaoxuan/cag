import asyncio
import hashlib
import inspect
from dataclasses import replace
from pathlib import Path
from typing import Any

from app.approvals.service import ApprovalService
from app.database import Database
from app.models import (
    AgentArtifact,
    AgentRun,
    HarnessRun,
    QualityScore,
    TaskGraphNode,
    VerificationRun,
)
from app.models.base import utc_now
from app.projects.registry import ProjectConfig
from app.runtimes.base import AgentRuntime, RuntimeEventCallback, RuntimeResult
from app.workspaces.manager import WorkspaceManager


PROFILE_INVESTIGATORS = {
    "fast": ("repository-mapper",),
    "balanced": (
        "repository-mapper",
        "evidence-investigator",
        "alternative-investigator",
    ),
    "deep": (
        "repository-mapper",
        "evidence-investigator",
        "alternative-investigator",
    ),
}
PROFILE_REVIEWS = {
    "fast": ("validator",),
    "balanced": ("code-reviewer", "security-reviewer", "validator"),
    "deep": ("code-reviewer", "architecture-reviewer", "citation-reviewer"),
}


class AgentHarness:
    def __init__(
        self,
        *,
        database: Database,
        runtime: AgentRuntime,
        workspace_manager: WorkspaceManager,
        approval_service: ApprovalService,
        max_parallel_agents: int,
        agent_timeout_seconds: int,
    ) -> None:
        self._database = database
        self._runtime = runtime
        self._workspace_manager = workspace_manager
        self._approval_service = approval_service
        self._max_parallel_agents = max_parallel_agents
        self._agent_timeout_seconds = agent_timeout_seconds
        self._db_lock = asyncio.Lock()

    async def execute(
        self,
        *,
        task_id: str,
        project_code: str,
        project: ProjectConfig,
        prompt: str,
        harness_profile: str,
        persistent_conversation: bool,
        conversation_thread_id: str | None,
        workspace_path: Path,
        additional_workspace_roots: tuple[Path, ...],
        developer_instructions: str | None,
        emit: RuntimeEventCallback,
    ) -> RuntimeResult:
        roles = PROFILE_INVESTIGATORS[harness_profile]
        max_parallel = min(self._max_parallel_agents, len(roles) or 1)
        contract = {
            "goal": prompt,
            "acceptance": [
                "ground conclusions in repository evidence",
                "keep writes in the executor workspace",
                "run independent validation",
            ],
            "harness_profile": harness_profile,
            "max_parallel": max_parallel,
        }
        with self._database.session_factory() as session:
            run = HarnessRun(
                task_id=task_id,
                profile=harness_profile,
                max_parallel=max_parallel,
                task_contract=contract,
            )
            session.add(run)
            session.flush()
            harness_run_id = run.id
            for role in (*roles, "executor", *PROFILE_REVIEWS[harness_profile]):
                session.add(
                    TaskGraphNode(
                        harness_run_id=harness_run_id,
                        node_key=role,
                        role=role,
                        dependencies=(
                            []
                            if role in roles
                            else list(roles)
                            if role == "executor"
                            else ["executor"]
                        ),
                    )
                )
            session.commit()
        await emit(
            "harness.started",
            {
                "harness_run_id": harness_run_id,
                "profile": harness_profile,
                "max_parallel": max_parallel,
                "task_contract": contract,
            },
        )
        await emit(
            "harness.preflight.completed",
            {
                "permissions": "intersection-applied",
                "single_writer": True,
                "knowledge_package": bool(developer_instructions),
                "budget_seconds": self._agent_timeout_seconds,
            },
        )

        semaphore = asyncio.Semaphore(max_parallel)

        async def investigate(role: str) -> RuntimeResult:
            role_key = "".join(part[0] for part in role.split("-"))
            child_key = f"h-{task_id[:8]}-{role_key}"
            child_workspace = await asyncio.to_thread(
                self._workspace_manager.prepare,
                project=project,
                task_id=child_key,
            )
            return await self._run_agent(
                harness_run_id=harness_run_id,
                task_id=task_id,
                run_key=child_key,
                role=role,
                phase="investigation",
                access_mode="read_only",
                project_code=project_code,
                prompt=self._role_prompt(role, prompt),
                workspace_path=child_workspace.path,
                developer_instructions=developer_instructions,
                persistent_conversation=False,
                conversation_thread_id=None,
                additional_workspace_roots=(),
                semaphore=semaphore,
                emit=emit,
            )

        investigator_results = await asyncio.gather(
            *(investigate(role) for role in roles), return_exceptions=True
        )
        evidence = [
            result.summary
            for result in investigator_results
            if isinstance(result, RuntimeResult)
        ]
        failures = [
            str(result) for result in investigator_results if isinstance(result, Exception)
        ]
        await emit(
            "harness.synthesis.completed",
            {
                "artifact_count": len(evidence),
                "failure_count": len(failures),
            },
        )
        synthesis = (
            "Harness read-only investigation artifacts:\n\n"
            + "\n\n".join(
                f"[Artifact {index + 1}]\n{summary}"
                for index, summary in enumerate(evidence)
            )
        )
        executor_instructions = "\n\n".join(
            value
            for value in (developer_instructions, synthesis)
            if value
        )
        executor_result = await self._run_agent(
            harness_run_id=harness_run_id,
            task_id=task_id,
            run_key=f"{task_id}-executor",
            role="executor",
            phase="execution",
            access_mode="workspace_write",
            project_code=project_code,
            prompt=prompt,
            workspace_path=workspace_path,
            developer_instructions=executor_instructions,
            persistent_conversation=persistent_conversation,
            conversation_thread_id=conversation_thread_id,
            additional_workspace_roots=additional_workspace_roots,
            semaphore=asyncio.Semaphore(1),
            emit=emit,
        )

        async def review(role: str) -> RuntimeResult:
            return await self._run_agent(
                harness_run_id=harness_run_id,
                task_id=task_id,
                run_key=f"{task_id}-{role}",
                role=role,
                phase="verification",
                access_mode="read_only",
                project_code=project_code,
                prompt=self._review_prompt(role, prompt, executor_result.summary),
                workspace_path=workspace_path,
                developer_instructions=developer_instructions,
                persistent_conversation=False,
                conversation_thread_id=None,
                additional_workspace_roots=(),
                semaphore=semaphore,
                emit=emit,
            )

        review_results = await asyncio.gather(
            *(review(role) for role in PROFILE_REVIEWS[harness_profile]),
            return_exceptions=True,
        )
        review_summaries = [
            result.summary for result in review_results if isinstance(result, RuntimeResult)
        ]
        review_failures = [
            str(result) for result in review_results if isinstance(result, Exception)
        ]
        with self._database.session_factory() as session:
            run = session.get(HarnessRun, harness_run_id)
            if run is not None:
                run.status = "completed" if not review_failures else "completed_with_warnings"
                run.completed_at = utc_now()
            session.add(
                VerificationRun(
                    harness_run_id=harness_run_id,
                    validator="harness-independent-review",
                    status="passed" if not review_failures else "warning",
                    evidence={
                        "reviews": review_summaries,
                        "failures": review_failures,
                    },
                )
            )
            completeness = (
                len(evidence) + len(review_summaries)
            ) / max(1, len(roles) + len(PROFILE_REVIEWS[harness_profile]))
            session.add(
                QualityScore(
                    harness_run_id=harness_run_id,
                    overall=round(100 * completeness, 2),
                    dimensions={
                        "investigation_completion": len(evidence) / max(1, len(roles)),
                        "review_completion": len(review_summaries)
                        / max(1, len(PROFILE_REVIEWS[harness_profile])),
                    },
                )
            )
            session.commit()
        await emit(
            "harness.completed",
            {
                "harness_run_id": harness_run_id,
                "investigations": len(evidence),
                "reviews": len(review_summaries),
                "failures": failures + review_failures,
            },
        )
        return replace(
            executor_result,
            validation=[
                *executor_result.validation,
                {
                    "validator": "harness-independent-review",
                    "status": "passed" if not review_failures else "warning",
                    "review_count": len(review_summaries),
                },
            ],
            warnings=[*executor_result.warnings, *failures, *review_failures],
        )

    async def _run_agent(
        self,
        *,
        harness_run_id: str,
        task_id: str,
        run_key: str,
        role: str,
        phase: str,
        access_mode: str,
        project_code: str,
        prompt: str,
        workspace_path: Path,
        developer_instructions: str | None,
        persistent_conversation: bool,
        conversation_thread_id: str | None,
        additional_workspace_roots: tuple[Path, ...],
        semaphore: asyncio.Semaphore,
        emit: RuntimeEventCallback,
    ) -> RuntimeResult:
        async with self._db_lock:
            with self._database.session_factory() as session:
                agent_run = AgentRun(
                    harness_run_id=harness_run_id,
                    task_id=task_id,
                    run_key=run_key,
                    role=role,
                    phase=phase,
                    access_mode=access_mode,
                    budget_seconds=self._agent_timeout_seconds,
                )
                session.add(agent_run)
                session.commit()
                agent_run_id = agent_run.id
        await emit(
            "agent.run.queued",
            {"agent_run_id": agent_run_id, "role": role, "phase": phase},
        )

        async def child_emit(event_type: str, data: dict[str, Any]) -> None:
            await emit(
                event_type,
                {"agent_run_id": agent_run_id, "role": role, **data},
            )

        async def request_approval(
            request_type: str, subject: str
        ) -> tuple[str, str | None]:
            return await self._approval_service.request(
                task_id=task_id,
                agent_run_id=agent_run_id,
                request_type=request_type,
                subject=subject,
            )

        async with semaphore:
            async with self._db_lock:
                with self._database.session_factory() as session:
                    record = session.get(AgentRun, agent_run_id)
                    record.status = "running"
                    record.started_at = utc_now()
                    session.commit()
            await emit(
                "agent.run.started",
                {
                    "agent_run_id": agent_run_id,
                    "role": role,
                    "phase": phase,
                    "access_mode": access_mode,
                },
            )
            try:
                kwargs = {
                    "task_id": run_key,
                    "project_code": project_code,
                    "prompt": prompt,
                    "runtime_profile": (
                        "read-only-analysis"
                        if access_mode == "read_only"
                        else "general-engineering"
                    ),
                    "persistent_conversation": persistent_conversation,
                    "conversation_thread_id": conversation_thread_id,
                    "workspace_path": workspace_path,
                    "additional_workspace_roots": additional_workspace_roots,
                    "developer_instructions": developer_instructions,
                    "emit": child_emit,
                }
                if "request_approval" in inspect.signature(
                    self._runtime.execute
                ).parameters:
                    kwargs["request_approval"] = request_approval
                result = await asyncio.wait_for(
                    self._runtime.execute(**kwargs),
                    timeout=self._agent_timeout_seconds,
                )
            except Exception as exc:
                async with self._db_lock:
                    with self._database.session_factory() as session:
                        record = session.get(AgentRun, agent_run_id)
                        record.status = "failed"
                        record.error = str(exc)
                        record.completed_at = utc_now()
                        session.commit()
                await emit(
                    "agent.run.failed",
                    {"agent_run_id": agent_run_id, "role": role, "error": str(exc)},
                )
                raise
        content = {"summary": result.summary, "validation": result.validation}
        content_hash = hashlib.sha256(
            repr(sorted(content.items())).encode("utf-8")
        ).hexdigest()
        async with self._db_lock:
            with self._database.session_factory() as session:
                record = session.get(AgentRun, agent_run_id)
                record.status = "completed"
                record.runtime_thread_id = result.runtime_thread_id
                record.completed_at = utc_now()
                session.add(
                    AgentArtifact(
                        agent_run_id=agent_run_id,
                        artifact_type="structured-report",
                        content=content,
                        content_hash=content_hash,
                    )
                )
                session.commit()
        await emit(
            "agent.run.completed",
            {
                "agent_run_id": agent_run_id,
                "role": role,
                "artifact_hash": content_hash,
            },
        )
        return result

    @staticmethod
    def _role_prompt(role: str, goal: str) -> str:
        return (
            f"Role: {role}. Investigate the following goal using read-only access. "
            "Return a concise structured artifact with findings, evidence paths, "
            f"uncertainties, and recommended validation. Goal: {goal}"
        )

    @staticmethod
    def _review_prompt(role: str, goal: str, summary: str) -> str:
        return (
            f"Role: {role}. Independently inspect the workspace after execution. "
            "Return findings with severity, evidence and validation status. "
            f"Original goal: {goal}\nExecutor summary: {summary}"
        )
