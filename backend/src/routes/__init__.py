from fastapi import APIRouter

from src.routes import weekly, pipeline, storage

router = APIRouter()

router.include_router(weekly.router, prefix="/weekly")
router.include_router(pipeline.router, prefix="/pipeline")
router.include_router(storage.router, prefix="/storage")