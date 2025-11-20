from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from dotenv import load_dotenv

from app.routes import router
from app.core.config import settings
from app.core.redis import close_redis_client

# Load environment variables from .env file (for local development)
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    # Startup
    print("Starting Predictor Backend...")
    print(f"Redis URL: {settings.redis_url}")
    
    yield
    
    # Shutdown
    print("Closing Redis connection...")
    close_redis_client()
    print("Cleanup completed")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "message": "Predictor Model Backend API",
        "version": settings.app_version,
        "docs": "/docs"
    }


@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    return {
        "status": "healthy",
        "version": settings.app_version
    }


app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


