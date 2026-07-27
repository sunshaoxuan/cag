from fastapi import APIRouter

from app.api.conversations import router as conversations_router
from app.api.health import router as health_router
from app.api.projects import router as projects_router
from app.api.tasks import router as tasks_router


router = APIRouter()
router.include_router(health_router)
router.include_router(projects_router)
router.include_router(conversations_router)
router.include_router(tasks_router)
