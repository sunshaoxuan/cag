from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.api.dependencies import get_capability_service
from app.capabilities.service import CapabilityService


router = APIRouter(tags=["capability-governance"])


class CapabilityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    kind: str
    code: str
    version: str
    status: str
    definition: dict[str, Any]
    content_hash: str
    source: str
    shadow_runs: int
    canary_runs: int
    consecutive_failures: int
    rolling_quality_delta: float
    active: bool
    created_at: datetime
    updated_at: datetime


class CapabilityProposal(BaseModel):
    code: str = Field(min_length=2, max_length=128)
    version: str = Field(min_length=1, max_length=32)
    definition: dict[str, Any]
    source: str = Field(default="api", max_length=128)


class EvaluationRequest(BaseModel):
    metrics: dict[str, Any]


class RolloutRequest(BaseModel):
    passed: bool
    metrics: dict[str, Any] = Field(default_factory=dict)


class RollbackRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=2000)


def _list_kind(kind: str, service: CapabilityService) -> list[CapabilityResponse]:
    return service.list_assets(kind)


def _propose(
    kind: str, request: CapabilityProposal, service: CapabilityService
) -> CapabilityResponse:
    try:
        return service.propose(
            kind=kind,
            code=request.code,
            version=request.version,
            definition=request.definition,
            source=request.source,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/api/v1/capabilities/skills", response_model=list[CapabilityResponse])
def list_skills(service: CapabilityService = Depends(get_capability_service)):
    return _list_kind("skill", service)


@router.post("/api/v1/capabilities/skills", response_model=CapabilityResponse)
def propose_skill(
    request: CapabilityProposal,
    service: CapabilityService = Depends(get_capability_service),
):
    return _propose("skill", request, service)


@router.get("/api/v1/capabilities/tools", response_model=list[CapabilityResponse])
def list_tools(service: CapabilityService = Depends(get_capability_service)):
    return _list_kind("tool", service)


@router.post("/api/v1/capabilities/tools", response_model=CapabilityResponse)
def propose_tool(
    request: CapabilityProposal,
    service: CapabilityService = Depends(get_capability_service),
):
    return _propose("tool", request, service)


@router.get("/api/v1/capabilities/validators", response_model=list[CapabilityResponse])
def list_validators(service: CapabilityService = Depends(get_capability_service)):
    return _list_kind("validator", service)


@router.get("/api/v1/capabilities/harness-profiles", response_model=list[CapabilityResponse])
def list_harness_profiles(
    service: CapabilityService = Depends(get_capability_service),
):
    return _list_kind("harness_profile", service)


@router.get("/api/v1/evaluations")
def list_evaluations(
    service: CapabilityService = Depends(get_capability_service),
):
    return service.list_evaluations()


@router.post("/api/v1/evaluations/{asset_id}")
def evaluate_asset(
    asset_id: str,
    request: EvaluationRequest,
    service: CapabilityService = Depends(get_capability_service),
):
    try:
        return service.evaluate(asset_id, request.metrics)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Capability not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/api/v1/promotions")
def list_promotions(
    service: CapabilityService = Depends(get_capability_service),
):
    return service.list_promotions()


@router.post("/api/v1/promotions/{asset_id}/shadow", response_model=CapabilityResponse)
def record_shadow(
    asset_id: str,
    request: RolloutRequest,
    service: CapabilityService = Depends(get_capability_service),
):
    try:
        return service.record_shadow(
            asset_id, passed=request.passed, metrics=request.metrics
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Capability not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/api/v1/promotions/{asset_id}/canary", response_model=CapabilityResponse)
def record_canary(
    asset_id: str,
    request: RolloutRequest,
    service: CapabilityService = Depends(get_capability_service),
):
    try:
        return service.record_canary(
            asset_id, passed=request.passed, metrics=request.metrics
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Capability not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/api/v1/rollbacks")
def list_rollbacks(
    service: CapabilityService = Depends(get_capability_service),
):
    return service.list_rollbacks()


@router.post("/api/v1/rollbacks/{asset_id}")
def rollback_asset(
    asset_id: str,
    request: RollbackRequest,
    service: CapabilityService = Depends(get_capability_service),
):
    try:
        return service.rollback(asset_id, request.reason)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Capability not found") from exc


@router.post("/api/v1/gardeners/run")
def run_gardeners(
    service: CapabilityService = Depends(get_capability_service),
):
    return service.run_gardeners()


@router.get("/api/v1/standards/controls")
def list_standard_controls(
    service: CapabilityService = Depends(get_capability_service),
):
    return service.list_controls()
