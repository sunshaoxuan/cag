from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


Boundary = Literal[
    "cag_internal",
    "external_dependency",
    "credential_or_authorization",
    "policy_or_scope",
]

ResolutionMode = Literal[
    "agent_self_improvement",
    "human_code_change",
    "external_operator_action",
    "mixed",
    "out_of_scope",
    "undetermined",
]


class StrictOperationsModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProposedChange(StrictOperationsModel):
    area: str = Field(min_length=1, max_length=200)
    change: str = Field(min_length=1, max_length=4_000)
    reason: str = Field(min_length=1, max_length=4_000)


class OperationalPlan(StrictOperationsModel):
    administrator_language: Literal["zh-CN"]
    problem_summary: str = Field(min_length=1, max_length=4_000)
    impact_summary: str = Field(min_length=1, max_length=4_000)
    root_cause_summary: str = Field(min_length=1, max_length=8_000)
    root_cause_confidence: float = Field(ge=0, le=1)
    improvement_goal: str = Field(min_length=1, max_length=4_000)
    resolution_mode: ResolutionMode
    resolution_mode_reason: str = Field(min_length=1, max_length=4_000)
    resolution_mode_confidence: float = Field(ge=0, le=1)
    proposed_changes: list[ProposedChange] = Field(min_length=1, max_length=50)
    validation_plan: list[str] = Field(min_length=1, max_length=100)
    rollback_plan: list[str] = Field(min_length=1, max_length=100)
    administrator_actions: list[str] = Field(default_factory=list, max_length=50)
    boundary: Boundary
    boundary_confidence: float = Field(ge=0, le=1)


class BlockingFinding(StrictOperationsModel):
    code: str = Field(min_length=1, max_length=64)
    severity: Literal["low", "medium", "high", "critical"]
    title: str = Field(min_length=1, max_length=300)
    finding: str = Field(min_length=1, max_length=4_000)
    required_change: str = Field(min_length=1, max_length=4_000)


class OperationalReview(StrictOperationsModel):
    administrator_language: Literal["zh-CN"]
    summary: str = Field(min_length=1, max_length=8_000)
    root_cause_assessment: str = Field(min_length=1, max_length=8_000)
    recommendation: Literal["approve", "revise", "reject"]
    blocking_findings: list[BlockingFinding] = Field(
        default_factory=list,
        max_length=100,
    )
    approval_conditions: list[str] = Field(default_factory=list, max_length=100)
    validation_plan: list[str] = Field(default_factory=list, max_length=100)
    warnings: list[str] = Field(default_factory=list, max_length=100)
