from fastapi import APIRouter

from src.routes import data, pipeline, storage

router = APIRouter()

router.include_router(data.router, prefix="/data")
router.include_router(pipeline.router, prefix="/pipeline")
router.include_router(storage.router, prefix="/storage")