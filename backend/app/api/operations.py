from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.api.dependencies import (
    get_operational_issue_service,
    require_operations_admin,
)
from app.operations.service import OperationalIssueService


router = APIRouter(prefix="/api/v1/operations", tags=["self-operations"])


class IssueIntakeRequest(BaseModel):
    project_reference: str = Field(min_length=1, max_length=128)
    source_type: str = Field(min_length=1, max_length=64)
    source_id: str | None = Field(default=None, max_length=128)
    title: str = Field(min_length=3, max_length=255)
    error_type: str | None = Field(default=None, max_length=255)
    error_message: str = Field(min_length=1, max_length=20_000)
    severity: Literal["low", "medium", "high", "critical"] = "medium"
    evidence: dict[str, Any] = Field(default_factory=dict)
    external_event_id: str | None = Field(default=None, max_length=128)
    event_type: str = Field(default="failure", max_length=64)
    parent_issue_id: str | None = None


class ApprovalDecisionRequest(BaseModel):
    note: str | None = Field(default=None, max_length=4_000)


class RejectionRequest(BaseModel):
    note: str = Field(min_length=3, max_length=4_000)


class ManualImplementationRequest(BaseModel):
    summary: str = Field(min_length=3, max_length=20_000)
    branch: str | None = Field(default=None, max_length=255)
    commits: list[str] = Field(default_factory=list, max_length=500)
    validation: list[dict[str, Any]] = Field(default_factory=list)


class BulkImplementationRequest(ManualImplementationRequest):
    issue_ids: list[str] = Field(min_length=1, max_length=200)


class ManualEvaluationRequest(BaseModel):
    passed: bool
    summary: str = Field(min_length=3, max_length=20_000)
    metrics: dict[str, Any] = Field(default_factory=dict)


class ReopenRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=4_000)


@router.get("/issues")
def list_issues(
    status: str | None = None,
    severity: str | None = None,
    boundary: str | None = None,
    limit: int = Query(default=200, ge=1, le=1_000),
    service: OperationalIssueService = Depends(get_operational_issue_service),
):
    return service.list_issues(
        status=status,
        severity=severity,
        boundary=boundary,
        limit=limit,
    )


@router.get("/dashboard")
def get_dashboard(
    service: OperationalIssueService = Depends(get_operational_issue_service),
):
    return service.dashboard()


@router.post("/issues/intake", status_code=202)
def intake_issue(
    request: IssueIntakeRequest,
    service: OperationalIssueService = Depends(get_operational_issue_service),
):
    try:
        return service.capture(**request.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/issues/{issue_id}")
def get_issue(
    issue_id: str,
    service: OperationalIssueService = Depends(get_operational_issue_service),
):
    try:
        return service.get_issue(issue_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Issue not found") from exc


@router.post("/issues/{issue_id}/approve")
def approve_issue(
    issue_id: str,
    request: ApprovalDecisionRequest,
    admin_identity: str = Depends(require_operations_admin),
    service: OperationalIssueService = Depends(get_operational_issue_service),
):
    try:
        return service.approve(
            issue_id,
            approved_by=admin_identity,
            note=request.note,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Issue not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/issues/{issue_id}/reject")
def reject_issue(
    issue_id: str,
    request: RejectionRequest,
    admin_identity: str = Depends(require_operations_admin),
    service: OperationalIssueService = Depends(get_operational_issue_service),
):
    try:
        return service.reject(
            issue_id,
            resolved_by=admin_identity,
            note=request.note,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Issue not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/issues/{issue_id}/implementations")
def record_implementation(
    issue_id: str,
    request: ManualImplementationRequest,
    admin_identity: str = Depends(require_operations_admin),
    service: OperationalIssueService = Depends(get_operational_issue_service),
):
    try:
        return service.record_manual_implementation(
            issue_id,
            **request.model_dump(),
            implemented_by=admin_identity,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Issue not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/bulk/implementations")
def record_bulk_implementations(
    request: BulkImplementationRequest,
    admin_identity: str = Depends(require_operations_admin),
    service: OperationalIssueService = Depends(get_operational_issue_service),
):
    payload = request.model_dump(exclude={"issue_ids"})
    payload["implemented_by"] = admin_identity
    results = []
    for issue_id in request.issue_ids:
        try:
            results.append(
                service.record_manual_implementation(issue_id, **payload)
            )
        except (KeyError, ValueError) as exc:
            results.append(
                {
                    "id": issue_id,
                    "error": str(exc),
                }
            )
    return results


@router.post("/issues/{issue_id}/evaluations")
def record_evaluation(
    issue_id: str,
    request: ManualEvaluationRequest,
    admin_identity: str = Depends(require_operations_admin),
    service: OperationalIssueService = Depends(get_operational_issue_service),
):
    try:
        return service.record_manual_evaluation(
            issue_id,
            **request.model_dump(),
            evaluated_by=admin_identity,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Issue not found") from exc


@router.post("/issues/{issue_id}/reopen")
def reopen_issue(
    issue_id: str,
    request: ReopenRequest,
    admin_identity: str = Depends(require_operations_admin),
    service: OperationalIssueService = Depends(get_operational_issue_service),
):
    try:
        return service.reopen(
            issue_id,
            **request.model_dump(),
            reopened_by=admin_identity,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Issue not found") from exc
