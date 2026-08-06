from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import (
    get_queue_coordinator,
    get_queue_service,
    get_session,
    get_task_service,
)
from app.knowledge.extraction import extraction_request_hash, extraction_request_id
from app.models import QueueItem, Task
from app.queue.coordinator import QueueCoordinator
from app.queue.service import QueueService
from app.services.task_service import (
    ProjectNotFoundError,
    RuntimeProfileNotAllowedError,
    TaskService,
)


router = APIRouter(
    prefix="/api/v1/knowledge/extractions/customer-ledger",
    tags=["knowledge-extractions"],
)


class CustomerExtractionRequest(BaseModel):
    project_id: str = Field(min_length=1, max_length=128)
    organization_code: str | None = Field(default=None, max_length=128)
    official_name: str | None = Field(default=None, max_length=512)
    aliases: list[str] = Field(default_factory=list, max_length=20)
    requested_sections: list[str] = Field(
        default_factory=lambda: ["contracts", "services", "vpns", "environments"],
        min_length=1,
        max_length=4,
    )

    @model_validator(mode="after")
    def validate_contract(self) -> "CustomerExtractionRequest":
        if not (self.organization_code or self.official_name or self.aliases):
            raise ValueError("At least one customer identity value is required")
        allowed = {"contracts", "services", "vpns", "environments"}
        if len(set(self.requested_sections)) != len(self.requested_sections):
            raise ValueError("requested_sections must be unique")
        if any(value not in allowed for value in self.requested_sections):
            raise ValueError("requested_sections contains an unsupported value")
        self.aliases = list(
            dict.fromkeys(value.strip() for value in self.aliases if value.strip())
        )
        return self


def extraction_response(task: Task) -> dict[str, Any]:
    return {
        "id": task.id,
        "trace_id": task.id,
        "status": task.status,
        "events_url": f"/api/v1/tasks/{task.id}/events",
        "result": task.final_report,
        "error": task.error,
        "created_at": task.created_at,
        "started_at": task.started_at,
        "completed_at": task.completed_at,
    }


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def create_customer_extraction(
    request: CustomerExtractionRequest,
    client_id: Annotated[
        str,
        Header(alias="X-CAG-Client-ID", min_length=1, max_length=128),
    ] = "oneops",
    idempotency_key: Annotated[
        str | None,
        Header(alias="Idempotency-Key", min_length=1, max_length=255),
    ] = None,
    session: Session = Depends(get_session),
    task_service: TaskService = Depends(get_task_service),
    coordinator: QueueCoordinator = Depends(get_queue_coordinator),
) -> dict[str, Any]:
    payload = request.model_dump(mode="json")
    request_hash = extraction_request_hash(payload)
    if idempotency_key is not None:
        existing = task_service.get_task_by_idempotency(
            session,
            client_id=client_id,
            idempotency_key=idempotency_key,
        )
        if existing is not None:
            if existing.request_hash != request_hash:
                raise HTTPException(
                    status_code=409,
                    detail="Idempotency key belongs to a different extraction",
                )
            return extraction_response(existing)
    identity = request.organization_code or request.official_name or request.aliases[0]
    try:
        task = task_service.create_task(
            session,
            project_reference=request.project_id,
            prompt=f"Extract customer ledger knowledge for {identity}",
            conversation_id=None,
            runtime_profile="general-engineering",
            client_request_id=extraction_request_id(),
            request_hash=request_hash,
            trigger_source="knowledge_extraction",
            client_id=client_id,
            idempotency_key=idempotency_key,
            request_metadata={"customer_extraction": payload},
            knowledge_mode="required",
            harness_profile="single",
            learning_mode="off",
            queue_name="knowledge",
            job_type="customer_knowledge_extraction",
            priority=120,
        )
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    except RuntimeProfileNotAllowedError as exc:
        raise HTTPException(status_code=422, detail="Runtime profile unavailable") from exc
    await coordinator.notify("knowledge")
    return extraction_response(task)


@router.get("/{task_id}")
def get_customer_extraction(
    task_id: str,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    task = session.get(Task, task_id)
    if task is None or task.trigger_source != "knowledge_extraction":
        raise HTTPException(status_code=404, detail="Customer extraction not found")
    return extraction_response(task)


@router.post("/{task_id}/cancel", status_code=status.HTTP_202_ACCEPTED)
async def cancel_customer_extraction(
    task_id: str,
    session: Session = Depends(get_session),
    queue_service: QueueService = Depends(get_queue_service),
    coordinator: QueueCoordinator = Depends(get_queue_coordinator),
) -> dict[str, str]:
    item = session.scalar(select(QueueItem).where(QueueItem.task_id == task_id))
    if item is None or item.job_type != "customer_knowledge_extraction":
        raise HTTPException(status_code=404, detail="Customer extraction not found")
    queue_status = queue_service.request_cancel(item.id)
    await coordinator.notify("knowledge")
    return {"id": task_id, "status": queue_status}
