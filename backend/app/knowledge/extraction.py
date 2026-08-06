import asyncio
import hashlib
import json
import uuid
from typing import Any

from app.config import Settings
from app.database import Database
from app.knowledge.service import KnowledgeService, SearchResult
from app.models import Task, TaskStatus
from app.models.base import utc_now
from app.services.task_service import TaskService


CUSTOMER_SECTIONS = {"contracts", "services", "vpns", "environments"}
SECTION_SEARCH_TERMS = {
    "contracts": "契約",
    "services": "サービス",
    "vpns": "VPN",
    "environments": "環境",
}


class CustomerKnowledgeExtractionService:
    def __init__(
        self,
        *,
        database: Database,
        settings: Settings,
        knowledge_service: KnowledgeService,
        task_service: TaskService,
    ) -> None:
        self._database = database
        self._settings = settings
        self._knowledge_service = knowledge_service
        self._task_service = task_service

    async def execute(self, task_id: str) -> None:
        with self._database.session_factory() as session:
            task = session.get(Task, task_id)
            if task is None:
                return
            contract = dict(task.request_metadata.get("customer_extraction", {}))
            task.status = TaskStatus.RUNNING
            task.started_at = task.started_at or utc_now()
            self._task_service.append_event(
                session,
                task=task,
                event_type="knowledge.extraction.started",
                data={
                    "schema_version": 1,
                    "requested_sections": contract.get("requested_sections", []),
                },
            )
            project = task.project
            session.commit()

        async def emit(event_type: str, data: dict[str, Any]) -> None:
            with self._database.session_factory() as event_session:
                current = event_session.get(Task, task_id)
                if current is None or current.status in TaskStatus.TERMINAL:
                    return
                self._task_service.append_event(
                    event_session,
                    task=current,
                    event_type=event_type,
                    data=data,
                )
                event_session.commit()

        identity_terms = [
            str(contract.get("organization_code", "")).strip(),
            str(contract.get("official_name", "")).strip(),
            *[
                str(value).strip()
                for value in contract.get("aliases", [])
                if str(value).strip()
            ],
        ]
        identity_terms = list(dict.fromkeys(value for value in identity_terms if value))
        requested_sections = [
            value
            for value in contract.get("requested_sections", [])
            if value in CUSTOMER_SECTIONS
        ]
        timeout_seconds = self._settings.knowledge_deep_timeout_seconds
        try:
            async with asyncio.timeout(timeout_seconds):
                collected: dict[str, SearchResult] = {}
                for identity in identity_terms:
                    for result in await self._knowledge_service.search(
                        project=project,
                        query=identity,
                        limit=min(20, self._settings.knowledge_candidate_limit),
                        profile="fast",
                        event_callback=emit,
                    ):
                        collected[result.id] = result
                customer_roots = tuple(
                    dict.fromkeys(
                        result.path.replace("\\", "/").split("/", 1)[0]
                        for result in collected.values()
                        if "exact_path" in result.match_reasons
                        and any(
                            identity.casefold()
                            in result.path.replace("\\", "/")
                            .split("/", 1)[0]
                            .casefold()
                            for identity in identity_terms
                        )
                    )
                )
                for section in (requested_sections if customer_roots else ()):
                    for result in await self._knowledge_service.search(
                        project=project,
                        query=SECTION_SEARCH_TERMS[section],
                        limit=min(20, self._settings.knowledge_candidate_limit),
                        profile="fast",
                        path_prefixes=customer_roots,
                        event_callback=emit,
                    ):
                        collected[result.id] = result
                results = list(collected.values())
                candidates, validation_errors = (
                    await self._knowledge_service.extract_customer_candidates(
                        identity={
                            "organization_code": contract.get("organization_code"),
                            "official_name": contract.get("official_name"),
                            "aliases": contract.get("aliases", []),
                        },
                        requested_sections=requested_sections,
                        results=results,
                    )
                )
        except TimeoutError:
            await emit(
                "knowledge.extraction.failed",
                {
                    "stage": "overall_deadline",
                    "timeout_seconds": timeout_seconds,
                    "error": "customer knowledge extraction timed out",
                },
            )
            raise
        except Exception as error:
            await emit(
                "knowledge.extraction.failed",
                {
                    "stage": "retrieval_or_schema_validation",
                    "error_type": type(error).__name__,
                    "error": str(error)[:500],
                },
            )
            raise

        citations = [self._citation(item) for item in results]
        report = {
            "type": "customer_ledger_extraction",
            "schema_version": 1,
            "identity": {
                "organization_code": contract.get("organization_code"),
                "official_name": contract.get("official_name"),
                "aliases": contract.get("aliases", []),
            },
            "requested_sections": requested_sections,
            "candidates": candidates,
            "citations": citations,
            "validation_errors": validation_errors,
            "learning_gap": len(candidates) == 0,
        }
        with self._database.session_factory() as session:
            task = session.get(Task, task_id)
            if task is None or task.status == TaskStatus.CANCELLED:
                return
            task.final_report = report
            task.knowledge_usage = {
                "status": "extracted",
                "citation_count": len(citations),
                "citations": citations,
            }
            task.status = TaskStatus.COMPLETED
            task.completed_at = utc_now()
            self._task_service.append_event(
                session,
                task=task,
                event_type="knowledge.extraction.completed",
                data={
                    "candidate_count": len(candidates),
                    "citation_count": len(citations),
                    "validation_error_count": len(validation_errors),
                    "learning_gap": len(candidates) == 0,
                },
            )
            session.commit()

    @staticmethod
    def _citation(item: SearchResult) -> dict[str, Any]:
        return {
            "chunk_id": item.id,
            "source_id": item.source_id,
            "generation_id": item.generation_id,
            "source_name": item.source_name,
            "source_type": item.source_type,
            "path": item.path,
            "resource_uri": item.resource_uri,
            "commit": item.source_commit,
            "score": item.score,
            "text_sha256": hashlib.sha256(item.text.encode("utf-8")).hexdigest(),
        }


def extraction_request_hash(payload: dict[str, Any]) -> str:
    normalized = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def extraction_request_id() -> str:
    return str(uuid.uuid4())
