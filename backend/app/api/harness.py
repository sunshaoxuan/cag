from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_approval_service, get_session
from app.approvals.service import ApprovalService
from app.models import AgentArtifact, AgentRun, ApprovalRequest, HarnessRun, QualityScore


router = APIRouter(tags=["harness"])


class HarnessRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    task_id: str
    profile: str
    status: str
    max_parallel: int
    task_contract: dict[str, Any]
    started_at: datetime
    completed_at: datetime | None


class AgentRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    harness_run_id: str
    task_id: str
    run_key: str
    role: str
    phase: str
    access_mode: str
    status: str
    runtime_thread_id: str | None
    error: str | None


class ApprovalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    task_id: str
    agent_run_id: str | None
    request_type: str
    subject: str
    risk_level: str
    status: str
    policy_decision: str
    requested_at: datetime
    resolved_at: datetime | None
    resolved_by: str | None
    resolution_note: str | None


class ApprovalResolution(BaseModel):
    decision: str = Field(pattern=r"^(approve|deny)$")
    resolved_by: str = Field(min_length=1, max_length=128)
    note: str | None = Field(default=None, max_length=2000)


@router.get("/api/v1/harness-runs", response_model=list[HarnessRunResponse])
def list_harness_runs(session: Session = Depends(get_session)):
    return list(session.scalars(select(HarnessRun).order_by(HarnessRun.started_at.desc())))


@router.get("/api/v1/harness-runs/{run_id}", response_model=HarnessRunResponse)
def get_harness_run(run_id: str, session: Session = Depends(get_session)):
    run = session.get(HarnessRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Harness run not found")
    return run


@router.get("/api/v1/harness-runs/{run_id}/agent-runs", response_model=list[AgentRunResponse])
def list_run_agents(run_id: str, session: Session = Depends(get_session)):
    if session.get(HarnessRun, run_id) is None:
        raise HTTPException(status_code=404, detail="Harness run not found")
    return list(
        session.scalars(
            select(AgentRun)
            .where(AgentRun.harness_run_id == run_id)
            .order_by(AgentRun.started_at)
        )
    )


@router.get("/api/v1/agent-runs/{agent_run_id}", response_model=AgentRunResponse)
def get_agent_run(agent_run_id: str, session: Session = Depends(get_session)):
    run = session.get(AgentRun, agent_run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Agent run not found")
    return run


@router.get("/api/v1/agent-runs/{agent_run_id}/artifacts")
def list_agent_artifacts(agent_run_id: str, session: Session = Depends(get_session)):
    return [
        {
            "id": item.id,
            "artifact_type": item.artifact_type,
            "schema_version": item.schema_version,
            "content": item.content,
            "content_hash": item.content_hash,
        }
        for item in session.scalars(
            select(AgentArtifact).where(AgentArtifact.agent_run_id == agent_run_id)
        )
    ]


@router.get("/api/v1/tasks/{task_id}/approvals", response_model=list[ApprovalResponse])
def list_task_approvals(
    task_id: str, approval_service: ApprovalService = Depends(get_approval_service)
):
    return approval_service.list_for_task(task_id)


@router.post("/api/v1/approvals/{approval_id}/resolve", response_model=ApprovalResponse)
def resolve_approval(
    approval_id: str,
    request: ApprovalResolution,
    approval_service: ApprovalService = Depends(get_approval_service),
):
    try:
        return approval_service.resolve(
            approval_id,
            decision=request.decision,
            resolved_by=request.resolved_by,
            note=request.note,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Approval not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/api/v1/quality")
def list_quality(session: Session = Depends(get_session)):
    return [
        {
            "id": score.id,
            "harness_run_id": score.harness_run_id,
            "overall": score.overall,
            "dimensions": score.dimensions,
            "created_at": score.created_at,
        }
        for score in session.scalars(
            select(QualityScore).order_by(QualityScore.created_at.desc())
        )
    ]
