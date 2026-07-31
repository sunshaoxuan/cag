from collections.abc import Iterator

from fastapi import Request
from sqlalchemy.orm import Session

from app.config import Settings
from app.database import Database
from app.projects.registry import ProjectRegistry
from app.services.task_service import TaskService
from app.tasks.executor import TaskExecutor
from app.knowledge.service import KnowledgeService
from app.approvals.service import ApprovalService
from app.capabilities.service import CapabilityService
from app.queue.coordinator import QueueCoordinator
from app.queue.service import QueueService
from app.operations.service import OperationalIssueService


def get_database(request: Request) -> Database:
    return request.app.state.database


def get_app_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_project_registry(request: Request) -> ProjectRegistry:
    return request.app.state.project_registry


def get_session(request: Request) -> Iterator[Session]:
    database = get_database(request)
    yield from database.session()


def get_task_service(request: Request) -> TaskService:
    return request.app.state.task_service


def get_task_executor(request: Request) -> TaskExecutor:
    return request.app.state.task_executor


def get_knowledge_service(request: Request) -> KnowledgeService:
    return request.app.state.knowledge_service


def get_approval_service(request: Request) -> ApprovalService:
    return request.app.state.approval_service


def get_capability_service(request: Request) -> CapabilityService:
    return request.app.state.capability_service


def get_queue_coordinator(request: Request) -> QueueCoordinator:
    return request.app.state.queue_coordinator


def get_queue_service(request: Request) -> QueueService:
    return request.app.state.queue_service


def get_operational_issue_service(request: Request) -> OperationalIssueService:
    return request.app.state.operational_issue_service
