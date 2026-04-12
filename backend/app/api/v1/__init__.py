from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.chat import router as chat_router
from app.api.v1.conversations import router as conversations_router
from app.api.v1.tasks import router as tasks_router
from app.api.v1.tools import router as tools_router
from app.api.v1.files import router as files_router
from app.api.v1.stats import router as stats_router
from app.api.v1.settings import router as settings_router
from app.api.v1.logs import router as logs_router

router = APIRouter()
router.include_router(auth_router)
router.include_router(chat_router)
router.include_router(conversations_router)
router.include_router(tasks_router)
router.include_router(tools_router)
router.include_router(files_router)
router.include_router(stats_router)
router.include_router(settings_router)
router.include_router(logs_router)
