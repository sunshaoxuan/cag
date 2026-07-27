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
