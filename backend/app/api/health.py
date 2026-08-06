from fastapi import APIRouter, Depends

from app.api.dependencies import get_app_settings, get_database, get_queue_coordinator
from app.config import Settings
from app.config import APP_NAME, APP_VERSION
from app.database import Database
from app.queue.coordinator import QueueCoordinator


router = APIRouter(tags=["health"])


@router.get("/health/live")
def live() -> dict[str, str]:
    return {
        "status": "ok",
        "service": APP_NAME,
        "version": APP_VERSION,
    }


@router.get("/health/ready")
def ready(
    database: Database = Depends(get_database),
    queue_coordinator: QueueCoordinator = Depends(get_queue_coordinator),
    settings: Settings = Depends(get_app_settings),
) -> dict[str, str | bool | None]:
    database.is_ready()
    queue_status = queue_coordinator.status()
    return {
        "status": "ready",
        "service": APP_NAME,
        "version": APP_VERSION,
        "queue_running": bool(queue_status["running"]),
        "process_role": settings.process_role,
        "redis_connected": bool(
            queue_status["redis"]["connected"]
        ),
        **database.storage_status(),
    }
