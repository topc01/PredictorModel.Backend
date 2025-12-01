import pytest
from unittest.mock import MagicMock, patch
from app.tasks.pipeline_tasks import process_excel_task


@pytest.fixture
def mock_task():
    mock = MagicMock()
    mock.request.id = "test-id"
    mock.request.retries = 0
    mock.max_retries = 3

    mock.publish_status = MagicMock()
    mock.retry = MagicMock(side_effect=Exception("retry-called"))

    return mock

@patch("app.tasks.pipeline_tasks.procesar_excel_completo")
def test_process_excel_success(mock_procesar, mock_task):
    excel_bytes = b"fake-data"

    result = process_excel_task(mock_task, excel_bytes)

    mock_procesar.assert_called_once()
    assert mock_task.publish_status.call_count >= 3

    assert result["success"] is True
    assert result["file_generated"] == "dataset.csv"


def test_process_excel_empty(mock_task):
    with pytest.raises(ValueError):
        process_excel_task(mock_task, b"")

    mock_task.publish_status.assert_called()

@patch("app.tasks.pipeline_tasks.procesar_excel_completo", side_effect=Exception("boom"))
def test_process_excel_retry(mock_procesar, mock_task):
    mock_task.request.retries = 0

    with pytest.raises(Exception) as exc:
        process_excel_task(mock_task, b"hello")

    assert "retry-called" in str(exc.value)
    mock_task.retry.assert_called_once()
    mock_task.publish_status.assert_called()

@patch("app.tasks.pipeline_tasks.procesar_excel_completo", side_effect=Exception("boom"))
def test_process_excel_max_retries(mock_procesar, mock_task):
    mock_task.request.retries = 3
    mock_task.retry = MagicMock()  # no debe llamarse

    with pytest.raises(Exception):
        process_excel_task(mock_task, b"hello")

    mock_task.retry.assert_not_called()
    mock_task.publish_status.assert_called()
