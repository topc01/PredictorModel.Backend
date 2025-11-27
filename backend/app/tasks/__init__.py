"""Celery tasks."""
from app.tasks.pipeline_tasks import (
    process_excel_task,
    process_weekly_task,
    full_pipeline_task,
)

__all__ = [
    "process_excel_task",
    "process_weekly_task",
    "full_pipeline_task",
]
