from fastapi import APIRouter

from app.routes import weekly, data, storage, predict, users, pipeline

router = APIRouter()

router.include_router(weekly.router, prefix="/weekly")
router.include_router(data.router, prefix="/data")
router.include_router(storage.router, prefix="/storage")
router.include_router(predict.router, prefix="/predict")
router.include_router(users.router, prefix="/users")
router.include_router(pipeline.router, prefix="/pipeline")