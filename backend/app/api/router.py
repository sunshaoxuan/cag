from fastapi import APIRouter

from app.api.conversations import router as conversations_router
from app.api.health import router as health_router
from app.api.knowledge import router as knowledge_router
from app.api.projects import router as projects_router
from app.api.tasks import router as tasks_router
from app.api.harness import router as harness_router
from app.api.capabilities import router as capabilities_router


router = APIRouter()
router.include_router(health_router)
router.include_router(knowledge_router)
router.include_router(projects_router)
router.include_router(conversations_router)
router.include_router(tasks_router)
router.include_router(harness_router)
router.include_router(capabilities_router)
