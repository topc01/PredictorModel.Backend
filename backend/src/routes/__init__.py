from fastapi import APIRouter

from src.routes import weekly, data, storage

router = APIRouter()

router.include_router(weekly.router, prefix="/weekly")
router.include_router(data.router, prefix="/data")
router.include_router(storage.router, prefix="/storage")