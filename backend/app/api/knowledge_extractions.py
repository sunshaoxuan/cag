from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import (
    get_knowledge_service,
    get_queue_coordinator,
    get_queue_service,
    get_session,
    get_task_service,
)
from app.knowledge.extraction import extraction_request_hash, extraction_request_id
from app.knowledge.customer_ledger_contracts import customer_ledger_schema_registry
from app.knowledge.service import KnowledgeService
from app.models import (
    KnowledgeAnalysisScope,
    KnowledgeAnalysisTemplateVersion,
    KnowledgeExtractionTask,
    KnowledgeIngestion,
    KnowledgeScopeIngestionRequest,
    KnowledgeSource,
    QueueItem,
    Task,
)
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
scope_router = APIRouter(
    prefix="/api/v1/knowledge/scopes",
    tags=["knowledge-extractions"],
)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AnalysisTemplateRequest(StrictModel):
    code: Literal["ORGANIZATION_PROFILE_ENRICHMENT"]
    version: Literal[1]


class SubjectRequest(StrictModel):
    type: Literal["organization"]
    external_system: Literal["ONEOPS"]
    external_id: UUID
    code: str = Field(min_length=1, max_length=128)
    official_name: str = Field(min_length=1, max_length=512)
    short_name: str | None = Field(default=None, max_length=255)
    aliases: list[str] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def normalize_aliases(self) -> "SubjectRequest":
        self.aliases = list(
            dict.fromkeys(value.strip() for value in self.aliases if value.strip())
        )
        return self


class ScopePolicyRequest(StrictModel):
    resolution: Literal["catalog"]
    coverage: Literal["exhaustive"]


class AnalysisContextRequest(StrictModel):
    as_of: datetime
    learning_processing_selection: Literal["active"]
    business_knowledge_selection: Literal["applicable_at"]


class IngestionPolicyRequest(StrictModel):
    mode: Literal["prepare_required_versions"]
    retry_failed_documents: bool = True


class FieldOptionRequest(StrictModel):
    id: UUID
    code: str = Field(min_length=1, max_length=128)
    label: str = Field(min_length=1, max_length=255)


class RequestedFieldRequest(StrictModel):
    code: str = Field(min_length=1, max_length=128)
    type: Literal[
        "string",
        "text",
        "enum",
        "master_reference",
        "object_list",
    ]
    required: bool
    options: list[FieldOptionRequest] = Field(default_factory=list, max_length=200)
    schema_ref: str | None = Field(default=None, max_length=128)

    @model_validator(mode="after")
    def validate_contract(self) -> "RequestedFieldRequest":
        if self.type in {"enum", "master_reference"} and not self.options:
            raise ValueError("enum and master_reference fields require options")
        if self.type not in {"enum", "master_reference"} and self.options:
            raise ValueError("options are limited to enum and master_reference fields")
        if self.type == "object_list" and not self.schema_ref:
            raise ValueError("object_list fields require schema_ref")
        if self.type != "object_list" and self.schema_ref:
            raise ValueError("schema_ref is limited to object_list fields")
        option_ids = [item.id for item in self.options]
        option_codes = [item.code for item in self.options]
        if len(set(option_ids)) != len(option_ids) or len(set(option_codes)) != len(
            option_codes
        ):
            raise ValueError("field options must have unique IDs and codes")
        return self


class ResultPolicyRequest(StrictModel):
    mode: Literal["candidates_only"]
    require_evidence: Literal[True]
    report_conflicts: Literal[True]
    minimum_confidence: float = Field(ge=0, le=1)
    allow_automatic_overwrite: Literal[False]
    allow_delete: Literal[False]


class CustomerExtractionRequest(StrictModel):
    schema_version: Literal[1]
    project_id: UUID
    knowledge_source_id: UUID
    analysis_template: AnalysisTemplateRequest
    subject: SubjectRequest
    scope_policy: ScopePolicyRequest
    analysis_context: AnalysisContextRequest
    ingestion_policy: IngestionPolicyRequest
    requested_fields: list[RequestedFieldRequest] = Field(min_length=1, max_length=100)
    result_policy: ResultPolicyRequest

    @model_validator(mode="after")
    def validate_fields(self) -> "CustomerExtractionRequest":
        codes = [item.code for item in self.requested_fields]
        if len(set(codes)) != len(codes):
            raise ValueError("requested field codes must be unique")
        return self


class ScopeIngestionRequest(StrictModel):
    reason: Literal["ORGANIZATION_PROFILE_ENRICHMENT"]
    mode: Literal["prepare_required_versions"]
    retry_statuses: list[
        Literal["observed", "metadata_only", "empty_text", "failed"]
    ] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_statuses(self) -> "ScopeIngestionRequest":
        if len(set(self.retry_statuses)) != len(self.retry_statuses):
            raise ValueError("retry_statuses must be unique")
        return self


def _error(status_code: int, code: str, message: str, **details: Any) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={
            "code": code,
            "message": message,
            "details": details,
        },
    )


def _task_response(task: KnowledgeExtractionTask) -> dict[str, Any]:
    if task.result_json is not None:
        return task.result_json
    return {
        "id": task.id,
        "schema_version": 1,
        "status": task.status,
        "subject_external_id": task.subject_external_id,
        "scope_id": task.scope_id,
        "created_at": task.created_at,
        "status_url": f"/api/v1/knowledge/extractions/customer-ledger/{task.id}",
    }


def _template(
    session: Session,
    request: AnalysisTemplateRequest,
) -> KnowledgeAnalysisTemplateVersion:
    template = session.scalar(
        select(KnowledgeAnalysisTemplateVersion).where(
            KnowledgeAnalysisTemplateVersion.code == request.code,
            KnowledgeAnalysisTemplateVersion.version == request.version,
            KnowledgeAnalysisTemplateVersion.enabled.is_(True),
        )
    )
    if template is None:
        template = KnowledgeAnalysisTemplateVersion(
            code=request.code,
            version=request.version,
            field_contracts=[],
            schema_registry=customer_ledger_schema_registry(),
            source_priorities=[
                {"pattern": "保守契約", "priority": 10},
                {"pattern": "台帳", "priority": 20},
                {"pattern": "導入システム一覧", "priority": 30},
                {"pattern": "*", "priority": 100},
            ],
            extractor_version="customer-ledger-v1",
        )
        session.add(template)
        session.flush()
    return template


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def create_customer_extraction(
    request: CustomerExtractionRequest,
    caller_source: Annotated[
        str,
        Header(alias="X-CAG-Source", min_length=1, max_length=128),
    ],
    client_id: Annotated[
        str,
        Header(alias="X-CAG-Client-ID", min_length=1, max_length=128),
    ],
    request_id: Annotated[
        str,
        Header(alias="X-Request-ID", min_length=1, max_length=128),
    ],
    idempotency_key: Annotated[
        str,
        Header(alias="Idempotency-Key", min_length=1, max_length=255),
    ],
    session: Session = Depends(get_session),
    task_service: TaskService = Depends(get_task_service),
    coordinator: QueueCoordinator = Depends(get_queue_coordinator),
) -> dict[str, Any]:
    del caller_source
    payload = request.model_dump(mode="json")
    request_hash = extraction_request_hash(payload)
    existing = session.scalar(
        select(KnowledgeExtractionTask).where(
            KnowledgeExtractionTask.client_id == client_id,
            KnowledgeExtractionTask.idempotency_key == idempotency_key,
        )
    )
    if existing is not None:
        if existing.request_hash != request_hash:
            raise _error(
                409,
                "IDEMPOTENCY_CONFLICT",
                "Idempotency key belongs to a different request.",
            )
        return _task_response(existing)
    source_id = str(request.knowledge_source_id)
    source = session.get(KnowledgeSource, source_id)
    if source is None:
        raise _error(
            404,
            "KNOWLEDGE_SOURCE_NOT_FOUND",
            "Knowledge source was not found.",
        )
    if not source.enabled:
        raise _error(
            503,
            "KNOWLEDGE_SOURCE_UNAVAILABLE",
            "Knowledge source is unavailable.",
        )
    if source.project_id != str(request.project_id):
        raise _error(
            422,
            "REQUEST_SCHEMA_INVALID",
            "Knowledge source does not belong to the requested project.",
        )
    template = _template(session, request.analysis_template)
    registered_schemas = set(template.schema_registry)
    unknown_schemas = sorted(
        {
            field.schema_ref
            for field in request.requested_fields
            if field.schema_ref and field.schema_ref not in registered_schemas
        }
    )
    if unknown_schemas:
        raise _error(
            422,
            "REQUEST_SCHEMA_INVALID",
            "Requested field schema is not registered.",
            schema_refs=unknown_schemas,
        )
    try:
        generic = task_service.create_task(
            session,
            project_reference=str(request.project_id),
            prompt="Execute scoped customer ledger extraction.",
            conversation_id=None,
            runtime_profile="general-engineering",
            client_request_id=request_id or extraction_request_id(),
            request_hash=request_hash,
            trigger_source="knowledge_extraction",
            client_id=client_id,
            idempotency_key=idempotency_key,
            request_metadata={"customer_extraction_id_pending": True},
            knowledge_mode="required",
            harness_profile="single",
            learning_mode="off",
            queue_name="knowledge",
            job_type="customer_knowledge_extraction",
            priority=120,
        )
    except ProjectNotFoundError as exc:
        raise _error(404, "REQUEST_SCHEMA_INVALID", "Project was not found.") from exc
    except RuntimeProfileNotAllowedError as exc:
        raise _error(
            422,
            "REQUEST_SCHEMA_INVALID",
            "Project does not allow the extraction runtime profile.",
        ) from exc
    extraction = KnowledgeExtractionTask(
        generic_task_id=generic.id,
        project_id=generic.project_id,
        source_id=source.id,
        template_version_id=template.id,
        client_id=client_id,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        subject_external_id=str(request.subject.external_id),
        request_json=payload,
    )
    session.add(extraction)
    session.commit()
    await coordinator.notify("knowledge")
    return _task_response(extraction)


@router.get("/{task_id}")
def get_customer_extraction(
    task_id: str,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    task = session.get(KnowledgeExtractionTask, task_id)
    if task is None:
        raise _error(404, "EXTRACTION_NOT_FOUND", "Customer extraction was not found.")
    return _task_response(task)


@router.post("/{task_id}/cancel", status_code=status.HTTP_202_ACCEPTED)
async def cancel_customer_extraction(
    task_id: str,
    session: Session = Depends(get_session),
    queue_service: QueueService = Depends(get_queue_service),
    coordinator: QueueCoordinator = Depends(get_queue_coordinator),
) -> dict[str, str]:
    task = session.get(KnowledgeExtractionTask, task_id)
    if task is None:
        raise _error(404, "EXTRACTION_NOT_FOUND", "Customer extraction was not found.")
    item = session.scalar(
        select(QueueItem).where(QueueItem.task_id == task.generic_task_id)
    )
    if item is None or item.job_type != "customer_knowledge_extraction":
        raise _error(404, "EXTRACTION_NOT_FOUND", "Customer extraction was not found.")
    queue_status = queue_service.request_cancel(item.id)
    await coordinator.notify("knowledge")
    return {"id": task.id, "status": queue_status}


@scope_router.post("/{scope_id}/ingestions", status_code=status.HTTP_202_ACCEPTED)
async def create_scope_ingestion(
    scope_id: str,
    request: ScopeIngestionRequest,
    client_role: Annotated[
        str,
        Header(alias="X-CAG-Client-Role", min_length=1, max_length=64),
    ],
    idempotency_key: Annotated[
        str,
        Header(alias="Idempotency-Key", min_length=1, max_length=255),
    ],
    session: Session = Depends(get_session),
    service: KnowledgeService = Depends(get_knowledge_service),
    coordinator: QueueCoordinator = Depends(get_queue_coordinator),
) -> dict[str, Any]:
    if client_role != "system-admin":
        raise _error(403, "SCOPE_INGESTION_FORBIDDEN", "Administrator role is required.")
    scope = session.get(KnowledgeAnalysisScope, scope_id)
    if scope is None or scope.status != "resolved" or scope.valid_to is not None:
        raise _error(404, "SCOPE_NOT_FOUND", "Resolved scope was not found.")
    payload = request.model_dump(mode="json")
    request_hash = extraction_request_hash(payload)
    prior_request = session.scalar(
        select(KnowledgeScopeIngestionRequest).where(
            KnowledgeScopeIngestionRequest.scope_id == scope.id,
            KnowledgeScopeIngestionRequest.idempotency_key == idempotency_key,
        )
    )
    if prior_request is not None:
        if prior_request.request_hash != request_hash:
            raise _error(
                409,
                "IDEMPOTENCY_CONFLICT",
                "Idempotency key belongs to a different scope ingestion request.",
            )
        prior_ingestion = session.get(KnowledgeIngestion, prior_request.ingestion_id)
        return {
            "id": prior_ingestion.id,
            "scope_id": scope.id,
            "status": prior_ingestion.status,
            "created": False,
            "status_url": f"/api/v1/knowledge/ingestions/{prior_ingestion.id}",
        }
    source = session.get(KnowledgeSource, scope.source_id)
    source_subpath = (source.subpath or "").replace("\\", "/").strip("/")
    scope_prefix = scope.canonical_prefix.strip("/")
    local_prefix = (
        ""
        if scope_prefix == source_subpath
        else scope_prefix.removeprefix(f"{source_subpath}/")
        if source_subpath and scope_prefix.startswith(f"{source_subpath}/")
        else scope_prefix
    )
    ingestion, created = service.create_ingestion(
        scope.source_id,
        trigger="scope_repair",
        analysis_scope_id=scope.id,
        scope_prefix=local_prefix,
        retry_statuses=list(request.retry_statuses),
    )
    session.add(
        KnowledgeScopeIngestionRequest(
            scope_id=scope.id,
            ingestion_id=ingestion.id,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
        )
    )
    session.commit()
    await coordinator.notify("knowledge")
    return {
        "id": ingestion.id,
        "scope_id": scope.id,
        "status": ingestion.status,
        "created": created,
        "status_url": f"/api/v1/knowledge/ingestions/{ingestion.id}",
    }
