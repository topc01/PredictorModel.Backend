"""Pipeline processing routes."""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, status, File, UploadFile
from pydantic import BaseModel
import json

from app.core.redis import get_redis_client, get_async_redis_client
from app.tasks import full_pipeline_task, process_excel_task, process_weekly_task
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

@router.post("/process-excel", response_model=PipelineResponse, status_code=status.HTTP_202_ACCEPTED)
async def process_excel(file: UploadFile = File(..., description="Excel file with historical hospital data")):
    """
    Start asynchronous dataset processing from Excel file.
    
    Receives an Excel file with historical hospital data, processes it asynchronously,
    and generates dataset.csv with cleaned and processed data.
    
    Args:
        file: Excel file (.xlsx or .xls) with historical data
        
    Returns:
        Task ID for tracking status
    """
    # Validate file extension
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file name provided"
        )
    
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an Excel file (.xlsx or .xls)"
        )
    
    try:
        # Read file as bytes
        excel_bytes = await file.read()
        
        # Start async task
        task = process_excel_task.delay(excel_bytes)
        
        return PipelineResponse(
            task_id=task.id,
            message="Dataset processing started. Use task_id to track progress."
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error starting dataset processing: {str(e)}"
        )


@router.post("/process-weekly", response_model=PipelineResponse, status_code=status.HTTP_202_ACCEPTED)
async def process_weekly(file: UploadFile = File(..., description="Excel file with weekly hospital data")):
    """
    Start asynchronous weekly data processing from Excel file.
    
    Receives an Excel file with weekly hospital data for all complexities,
    processes it asynchronously, and generates predictions.csv.
    
    Args:
        file: Excel file (.xlsx or .xls) with weekly data
        
    Returns:
        Task ID for tracking status
    """
    from app.types import WeeklyData
    import pandas as pd
    import io
    
    # Validate file extension
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file name provided"
        )
    
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an Excel file (.xlsx or .xls)"
        )
    
    try:
        # Read file as bytes
        excel_bytes = await file.read()
        
        # Parse Excel to DataFrame
        df = pd.read_excel(io.BytesIO(excel_bytes))
        
        # Validate with WeeklyData
        try:
            WeeklyData.from_df(df)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid weekly data format: {str(e)}"
            )
        
        # Convert to dict format for task
        weekly_data_dict = df.groupby("Complejidad").apply(
            lambda x: x.to_dict(orient="records"),
            include_groups=False
        ).to_dict()
        
        # Start async task
        task = process_weekly_task.delay(weekly_data_dict)
        
        return PipelineResponse(
            task_id=task.id,
            message="Weekly data processing started. Use task_id to track progress."
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error starting weekly data processing: {str(e)}"
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
    
    # Use async Redis client to avoid blocking the event loop
    redis_client = await get_async_redis_client()
    pubsub = redis_client.pubsub()
    channel = f"pipeline:{task_id}"
    
    try:
        # Subscribe to the task's status channel
        await pubsub.subscribe(channel)
        
        # Send initial connection message
        await websocket.send_json({
            "type": "connected",
            "task_id": task_id,
            "message": "Connected to pipeline status stream"
        })
        
        # Listen for messages using async iteration
        async for message in pubsub.listen():
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
        await pubsub.unsubscribe(channel)
        await pubsub.aclose()
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
