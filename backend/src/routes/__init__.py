from fastapi import APIRouter

from src.routes import data

router = APIRouter()

router.include_router(data.router, prefix="/data", tags=["data"])