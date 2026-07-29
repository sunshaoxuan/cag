from fastapi import APIRouter, Depends

from app.api.dependencies import get_database, get_queue_coordinator
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
) -> dict[str, str | bool | None]:
    database.is_ready()
    return {
        "status": "ready",
        "service": APP_NAME,
        "version": APP_VERSION,
        "queue_running": queue_coordinator.running,
        "redis_connected": bool(
            queue_coordinator.status()["redis"]["connected"]
        ),
        **database.storage_status(),
    }
