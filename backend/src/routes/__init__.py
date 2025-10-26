from fastapi import APIRouter

from src.routes import data, pipeline

router = APIRouter()

router.include_router(data.router, prefix="/data")
router.include_router(pipeline.router)