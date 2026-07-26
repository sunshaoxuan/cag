from collections.abc import Iterator

from fastapi import Request
from sqlalchemy.orm import Session

from app.config import Settings
from app.database import Database
from app.services.task_service import TaskService
from app.tasks.executor import TaskExecutor


def get_database(request: Request) -> Database:
    return request.app.state.database


def get_app_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_session(request: Request) -> Iterator[Session]:
    database = get_database(request)
    yield from database.session()


def get_task_service(request: Request) -> TaskService:
    return request.app.state.task_service


def get_task_executor(request: Request) -> TaskExecutor:
    return request.app.state.task_executor
