"""Pipeline processing tasks using Celery."""
import json
from celery import Task
from app.core.celery_app import celery_app
from app.core.redis import get_redis_client
from app.pipeline import procesar_excel_completo, preparar_datos_prediccion_global


class CallbackTask(Task):
    """Base task that publishes status updates via Redis pub/sub."""
    
    def publish_status(self, task_id: str, status: dict):
        """Publish task status to Redis channel."""
        redis_client = get_redis_client()
        channel = f"pipeline:{task_id}"
        redis_client.publish(channel, json.dumps(status))


@celery_app.task(bind=True, base=CallbackTask, max_retries=3)
def process_excel_task(self, excel_bytes: bytes):
    """
    Process Excel file asynchronously.
    
    Args:
        excel_bytes: Excel file content as bytes
        
    Returns:
        Success message with processing details
    """
    import io
    
    task_id = self.request.id
    
    try:
        # Publish: Started
        self.publish_status(task_id, {
            "status": "processing",
            "step": "excel_processing",
            "progress": 0,
            "message": "Starting Excel processing..."
        })
        
        # Convert bytes to BytesIO for processing
        excel_file = io.BytesIO(excel_bytes)
        
        # Publish: Processing
        self.publish_status(task_id, {
            "status": "processing",
            "step": "excel_processing",
            "progress": 20,
            "message": "Reading and validating Excel file..."
        })
        
        # Process the Excel file
        procesar_excel_completo(excel_file)
        
        # Publish: Completed
        self.publish_status(task_id, {
            "status": "completed",
            "step": "excel_processing",
            "progress": 100,
            "message": "Excel processing completed successfully. Dataset.csv has been generated."
        })
        
        return {
            "success": True,
            "message": "Dataset processed successfully",
            "file_generated": "dataset.csv"
        }
        
    except Exception as exc:
        # Publish: Error
        self.publish_status(task_id, {
            "status": "failed",
            "step": "excel_processing",
            "error": str(exc),
            "message": f"Error processing Excel: {str(exc)}"
        })
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


@celery_app.task(bind=True, base=CallbackTask, max_retries=3)
def process_weekly_task(self, weekly_data: dict):
    """
    Process weekly data asynchronously.
    
    Args:
        weekly_data: Dictionary with weekly data for all complexities
                     Format: {"Alta": [...], "Baja": [...], ...}
        
    Returns:
        Success message with processing details
    """
    task_id = self.request.id
    
    try:
        # Publish: Started
        self.publish_status(task_id, {
            "status": "processing",
            "step": "weekly_processing",
            "progress": 0,
            "message": "Starting weekly data processing..."
        })
        
        # Publish: Validating
        self.publish_status(task_id, {
            "status": "processing",
            "step": "weekly_processing",
            "progress": 20,
            "message": "Validating weekly data..."
        })
        
        # Process weekly data - this updates dataset.csv and creates predictions.csv
        result = preparar_datos_prediccion_global(weekly_data)
        
        # Publish: Completed
        self.publish_status(task_id, {
            "status": "completed",
            "step": "weekly_processing",
            "progress": 100,
            "message": "Weekly data processed successfully. Predictions.csv has been generated."
        })
        
        return {
            "success": True,
            "message": "Weekly data processed successfully",
            "files_generated": ["predictions.csv", "dataset.csv (updated)"],
            "rows_processed": len(result)
        }
        
    except Exception as exc:
        # Publish: Error
        self.publish_status(task_id, {
            "status": "failed",
            "step": "weekly_processing",
            "error": str(exc),
            "message": f"Error processing weekly data: {str(exc)}"
        })
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


@celery_app.task(bind=True, base=CallbackTask)
def full_pipeline_task(self, file_path: str):
    """
    Run the complete pipeline: process Excel -> prepare prediction data.
    
    Args:
        file_path: Path to the Excel file to process
        
    Returns:
        Final prediction data
    """
    task_id = self.request.id
    
    try:
        # Publish: Started
        self.publish_status(task_id, {
            "status": "started",
            "step": "initialization",
            "progress": 0,
            "message": "Starting pipeline..."
        })
        
        # Step 1: Process Excel
        self.publish_status(task_id, {
            "status": "processing",
            "step": "excel_processing",
            "progress": 10,
            "message": "Processing Excel file..."
        })
        result1 = procesar_excel_completo(file_path)
        
        # Step 2: Prepare prediction data
        self.publish_status(task_id, {
            "status": "processing",
            "step": "data_preparation",
            "progress": 60,
            "message": "Preparing prediction data..."
        })
        result2 = preparar_datos_prediccion_global(result1)
        
        # Complete
        self.publish_status(task_id, {
            "status": "completed",
            "step": "finished",
            "progress": 100,
            "message": "Pipeline completed successfully",
            "result_preview": str(result2)[:200] if result2 else None
        })
        
        return result2
        
    except Exception as exc:
        # Publish: Error
        self.publish_status(task_id, {
            "status": "failed",
            "step": "error",
            "progress": 0,
            "error": str(exc),
            "message": f"Pipeline failed: {str(exc)}"
        })
        raise
