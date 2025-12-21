from fastapi import APIRouter

from .format_router import router as format_router
from .healthcheck_router import router as healthcheck_router


router = APIRouter(prefix="/v1")

router.include_router(healthcheck_router)
router.include_router(format_router)
