"""Pipeline processing routes."""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, status
from pydantic import BaseModel
import json

from app.core.redis import get_redis_client
from app.tasks.pipeline_tasks import full_pipeline_task
from celery.result import AsyncResult

router = APIRouter(tags=["pipeline"])


class PipelineRequest(BaseModel):
    """Request to start pipeline processing."""
    file_path: str


class PipelineResponse(BaseModel):
    """Response with task ID."""
    task_id: str
    message: str


class TaskStatusResponse(BaseModel):
    """Task status response."""
    task_id: str
    state: str
    status: dict | None = None
    result: dict | None = None
    error: str | None = None


@router.post("/start", response_model=PipelineResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_pipeline(request: PipelineRequest):
    """
    Start asynchronous pipeline processing.
    
    Args:
        request: Pipeline request with file path
        
    Returns:
        Task ID for tracking status
    """
    # Start async task
    task = full_pipeline_task.delay(request.file_path)
    
    return PipelineResponse(
        task_id=task.id,
        message="Pipeline started successfully. Use task_id to track progress."
    )


@router.get("/status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """
    Get the current status of a pipeline task.
    
    Args:
        task_id: The Celery task ID
        
    Returns:
        Current task status and result if available
    """
    task_result = AsyncResult(task_id)
    
    response = TaskStatusResponse(
        task_id=task_id,
        state=task_result.state,
        status=None,
        result=None,
        error=None
    )
    
    if task_result.state == "PENDING":
        response.status = {"message": "Task is waiting to be processed"}
    elif task_result.state == "STARTED":
        response.status = {"message": "Task is currently running"}
    elif task_result.state == "SUCCESS":
        response.result = task_result.result
    elif task_result.state == "FAILURE":
        response.error = str(task_result.info)
    else:
        response.status = {"message": f"Task state: {task_result.state}"}
    
    return response


@router.websocket("/status/{task_id}/stream")
async def stream_task_status(websocket: WebSocket, task_id: str):
    """
    WebSocket endpoint for real-time pipeline status updates.
    
    Subscribes to Redis pub/sub channel for the task and streams updates to client.
    
    Args:
        websocket: WebSocket connection
        task_id: The Celery task ID to monitor
    """
    await websocket.accept()
    
    redis_client = get_redis_client()
    pubsub = redis_client.pubsub()
    channel = f"pipeline:{task_id}"
    
    try:
        # Subscribe to the task's status channel
        pubsub.subscribe(channel)
        
        # Send initial connection message
        await websocket.send_json({
            "type": "connected",
            "task_id": task_id,
            "message": "Connected to pipeline status stream"
        })
        
        # Listen for messages
        for message in pubsub.listen():
            if message["type"] == "message":
                # Parse and forward the status update
                try:
                    status_data = json.loads(message["data"])
                    await websocket.send_json({
                        "type": "status_update",
                        "task_id": task_id,
                        "data": status_data
                    })
                    
                    # If task is completed or failed, close connection
                    if status_data.get("status") in ["completed", "failed"]:
                        await websocket.send_json({
                            "type": "finished",
                            "task_id": task_id,
                            "final_status": status_data.get("status")
                        })
                        break
                        
                except json.JSONDecodeError:
                    # Skip malformed messages
                    continue
                    
    except WebSocketDisconnect:
        pass
    finally:
        pubsub.unsubscribe(channel)
        pubsub.close()
        await websocket.close()


@router.get("/result/{task_id}")
async def get_task_result(task_id: str):
    """
    Get the final result of a completed pipeline task.
    
    Args:
        task_id: The Celery task ID
        
    Returns:
        Task result if available
    """
    task_result = AsyncResult(task_id)
    
    if task_result.state == "PENDING":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found or not yet started"
        )
    elif task_result.state == "SUCCESS":
        return {
            "task_id": task_id,
            "status": "completed",
            "result": task_result.result
        }
    elif task_result.state == "FAILURE":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Task failed: {str(task_result.info)}"
        )
    else:
        return {
            "task_id": task_id,
            "status": "processing",
            "state": task_result.state
        }
