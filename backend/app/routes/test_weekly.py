import io
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app  # usa tu app real (con include_router)
from app.types.WeeklyData import WeeklyData

client = TestClient(app)

@pytest.fixture
def valid_excel_bytes():
    df = WeeklyData.example().to_df(by_alias=True)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:  # type: ignore[arg-type]
        df.to_excel(writer, index=False, sheet_name="Datos Semanales")
    output.seek(0)
    return output.read()


def test_upload_data_ok(valid_excel_bytes):
    with patch("app.routes.weekly.preparar_datos_prediccion_global") as mock_pred:
        mock_pred.return_value = None

        files = {"file": ("weekly.xlsx", io.BytesIO(valid_excel_bytes), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        response = client.post("/weekly/upload", files=files)

        assert response.status_code == 200
        assert response.json()["message"] == "Archivo procesado correctamente"
        mock_pred.assert_called_once()

def test_upload_data_invalid_extension(valid_excel_bytes):
    files = {"file": ("weekly.txt", io.BytesIO(valid_excel_bytes), "text/plain")}
    response = client.post("/weekly/upload", files=files)

    assert response.status_code == 400
    assert "Excel" in response.json()["detail"]


def test_upload_data_empty_file():
    with patch("pandas.read_excel", side_effect=pd.errors.EmptyDataError()):
        files = {"file": ("weekly.xlsx", io.BytesIO(b""), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        response = client.post("/weekly/upload", files=files)
        assert response.status_code == 400
        assert "vacío" in response.json()["detail"]


def test_upload_data_parser_error(valid_excel_bytes):
    with patch("pandas.read_excel", side_effect=pd.errors.ParserError()):
        files = {"file": ("weekly.xlsx", io.BytesIO(valid_excel_bytes), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        response = client.post("/weekly/upload", files=files)
        assert response.status_code == 400
        assert "formato inválido" in response.json()["detail"]


def test_upload_data_file_not_found(valid_excel_bytes):
    with patch("app.routes.weekly.WeeklyData.from_df", side_effect=FileNotFoundError()):
        files = {"file": ("weekly.xlsx", io.BytesIO(valid_excel_bytes), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        response = client.post("/weekly/upload", files=files)
        assert response.status_code == 400
        assert "no ha sido procesado" in response.json()["detail"]


def test_upload_data_unexpected_error(valid_excel_bytes):
    with patch("app.routes.weekly.WeeklyData.from_df", side_effect=Exception("Falla general")):
        files = {"file": ("weekly.xlsx", io.BytesIO(valid_excel_bytes), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        response = client.post("/weekly/upload", files=files)
        assert response.status_code == 500
        assert "Error interno" in response.json()["detail"]