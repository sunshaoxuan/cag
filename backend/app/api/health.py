from fastapi import APIRouter, Depends

from app.api.dependencies import get_database
from app.config import APP_NAME, APP_VERSION
from app.database import Database


router = APIRouter(tags=["health"])


@router.get("/health/live")
def live() -> dict[str, str]:
    return {
        "status": "ok",
        "service": APP_NAME,
        "version": APP_VERSION,
    }


@router.get("/health/ready")
def ready(database: Database = Depends(get_database)) -> dict[str, str]:
    database.is_ready()
    return {
        "status": "ready",
        "service": APP_NAME,
        "version": APP_VERSION,
    }
