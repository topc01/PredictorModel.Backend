from fastapi import FastAPI, status, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import logging
import asyncio
import time

from app.routes import router
from app.core.config import settings
from app.core.redis import close_redis_client, get_redis_client

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
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


@app.websocket("/ws/health")
async def websocket_health_check(websocket: WebSocket):
    """
    WebSocket endpoint for health checking.
    
    Maintains a persistent connection and sends periodic heartbeat messages.
    This is more efficient than polling the HTTP /health endpoint.
    
    The client should:
    1. Connect to this endpoint
    2. Listen for heartbeat messages every 10 seconds
    3. Reconnect if the connection is lost
    
    Message format:
    {
        "type": "connected" | "heartbeat",
        "status": "healthy" | "degraded",
        "timestamp": <unix_timestamp>,
        "version": "<app_version>",
    }
    """
    await websocket.accept()
    
    try:
        # Send initial connection message
        await websocket.send_json({
            "type": "connected",
            "status": "healthy",
            "timestamp": time.time(),
            "version": settings.app_version,
        })
        
        # Keep connection alive with periodic heartbeats
        while True:
            # Check Redis connection
            redis_connected = False
            try:
                redis_client = get_redis_client()
                redis_client.ping()
                redis_connected = True
            except Exception:
                redis_connected = False
            
            # Send heartbeat
            await websocket.send_json({
                "type": "heartbeat",
                "status": "healthy" if redis_connected else "degraded",
                "timestamp": time.time(),
                "version": settings.app_version,
            })
            
            # Wait 10 seconds before next heartbeat
            await asyncio.sleep(10)
            
    except WebSocketDisconnect:
        # Client disconnected, clean up
        pass
    except Exception as e:
        # Log error and close connection
        print(f"WebSocket health check error: {e}")
        try:
            await websocket.close()
        except Exception:
            pass


app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


