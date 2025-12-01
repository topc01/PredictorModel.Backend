# import pytest
# from fastapi.testclient import TestClient
# import pandas as pd
# import numpy as np
# from unittest.mock import patch, MagicMock
# import io
# import os
# import tempfile
# import shutil

# from app.pipeline import preprocesar_datos_semanales as preproc
# from app.main import app
# from app.pipeline.limpieza_datos_uc import get_season, limpiar_excel_inicial, preparar_datos_por_complejidad, procesar_excel_completo
# from app.pipeline.preprocesar_datos_semanales import preparar_datos_prediccion_global
# from app.utils.storage import StorageManager, check_bucket_access
# from app.pipeline.limpieza_datos_uc import cargar_df_por_complejidad
# from app.routes.storage import storage_health_check
# from app.types.WeeklyData import WeeklyData

# client = TestClient(app)

# def test_get_season():
#     assert get_season(1) == "verano"
#     assert get_season(4) == "otoño"
#     assert get_season(7) == "invierno"
#     assert get_season(10) == "primavera"

# # Test for StorageManager with local storage
# @pytest.fixture
# def local_storage(tmp_path):
#     storage = StorageManager()
#     storage.env = "local"
#     storage.base_dir = str(tmp_path)  # data dir temporal
#     return storage


# def test_storage_manager_local_save_load_exists(local_storage):
#     df = pd.DataFrame({"a": [1, 2, 3]})
#     filename = "test.csv"

#     # Test save
#     filepath = local_storage.save_csv(df, filename)
#     assert os.path.exists(filepath)
#     assert filepath == os.path.join(local_storage.base_path, filename)

#     # Test exists
#     assert local_storage.exists(filename)

#     # Test load
#     loaded_df = local_storage.load_csv(filename)
#     pd.testing.assert_frame_equal(df, loaded_df)

#     # Test load non-existent file
#     with pytest.raises(FileNotFoundError):
#         local_storage.load_csv("non_existent.csv")

# # Test for StorageManager with S3 storage
# @patch('boto3.client')
# def test_storage_manager_s3_save_load_exists(mock_boto3_client):
#     mock_s3 = MagicMock()
#     mock_boto3_client.return_value = mock_s3

#     storage = StorageManager()
#     storage.env = "s3"
#     storage.s3_bucket = "test-bucket"
#     storage.prefix = "test-prefix"
#     storage.s3_client = mock_s3

#     mock_s3.head_object.assert_called_with(
#         Bucket="test-bucket",
#         Key="test-prefix/test.csv"
#     )
#     mock_s3.get_object.assert_called_with(
#         Bucket="test-bucket",
#         Key="test-prefix/test.csv"
#     )



# # Test for check_bucket_access
# @patch('boto3.client')
# def test_check_bucket_access(mock_boto3_client):
#     mock_s3 = MagicMock()
#     mock_boto3_client.return_value = mock_s3

#     # Test accessible bucket
#     mock_s3.head_bucket.return_value = {}
#     result = check_bucket_access("accessible-bucket")
#     assert result["accessible"]
#     assert result["exists"]
#     assert result["error"] is None

#     # Test non-existent bucket
#     from botocore.exceptions import ClientError
#     mock_s3.head_bucket.side_effect = ClientError({"Error": {"Code": "404"}}, "HeadBucket")
#     result = check_bucket_access("non-existent-bucket")
#     assert not result["accessible"]
#     assert not result["exists"]
#     assert result["error"] == "Bucket does not exist"

#     # Test access denied bucket
#     mock_s3.head_bucket.side_effect = ClientError({"Error": {"Code": "403"}}, "HeadBucket")
#     result = check_bucket_access("denied-bucket")
#     assert not result["accessible"]
#     assert result["exists"]
#     assert result["error"] == "Access denied - check IAM permissions"

# # Tests for limpieza_datos_uc.py
# def create_dummy_excel(sheets_data):
#     output = io.BytesIO()
#     with pd.ExcelWriter(output, engine='openpyxl') as writer:
#         for sheet_name, df in sheets_data.items():
#             df.to_excel(writer, sheet_name=sheet_name, index=False)
#     output.seek(0)
#     return output

# def test_limpiar_excel_inicial_success():
#     sheet1 = pd.DataFrame({
#         "Servicio Ingreso (Código)": ["A", "B"],
#         "id": [1, 2],
#         "edad en años": [1,2],
#         "sexo (desc)": [1,2],
#         "servicio egreso (código)": [1,2],
#         "peso grd": [1,2],
#         "ir grd (código)": [1,2],
#         "ir grd": [1,2],
#         "conjunto de servicios traslado": [1,2],
#         "cx": [1,2],
#         "fecha ingreso completa": ["2024-01-01", "2024-02-01"]
#     })
#     sheet2 = pd.DataFrame()
#     sheet3 = pd.DataFrame({
#         "UO trat.": ["A", "B"],
#         "desc. serv.": ["Desc A", "Desc B"],
#         "complejidad": ["Alta", "Baja"]
#     })

#     excel_file = create_dummy_excel({"Sheet1": sheet1, "Sheet2": sheet2, "Sheet3": sheet3})

#     df = limpiar_excel_inicial(excel_file)

#     assert "complejidad" in df.columns
#     assert "estacion" in df.columns
#     assert df.shape[0] == 2
#     assert "id" not in df.columns

# def test_limpiar_excel_inicial_wrong_format():
#     sheet1 = pd.DataFrame({"a": [1]})
#     excel_file = create_dummy_excel({"Sheet1": sheet1})

#     with pytest.raises(ValueError, match="El archivo debe tener al menos 3 hojas"):
#         limpiar_excel_inicial(excel_file)

# def test_preparar_datos_por_complejidad():
#     # Create a more realistic dataframe with enough data to avoid being dropped
#     num_weeks = 60
#     records_per_week = 15
#     num_records = num_weeks * records_per_week

#     date_rng = pd.to_datetime(pd.date_range(start='2023-01-01', periods=num_weeks, freq='W-MON'))

#     data = {
#         'complejidad': ['Alta'] * num_records,
#         'fecha ingreso completa': np.repeat(date_rng, records_per_week),
#         'estancia (días)': np.random.randint(1, 20, size=num_records),
#         'tipo de ingreso': np.random.choice(['Urgente', 'No Urgente'], size=num_records),
#         'tipo de paciente': np.random.choice(['Qx', 'No Qx'], size=num_records),
#         'servicio ingreso (código)': ['A'] * num_records,
#         'estacion': ['verano'] * num_records
#     }
#     df = pd.DataFrame(data)

#     df_alta = preparar_datos_por_complejidad(df, 'Alta')
#     assert df_alta is not None
#     assert df_alta.shape[0] > 0
#     assert 'demanda_pacientes' in df_alta.columns
#     assert 'demanda_lag1' in df_alta.columns

#     df_baja = preparar_datos_por_complejidad(df, 'Baja')
#     assert df_baja is None


# @patch('app.pipeline.limpieza_datos_uc.limpiar_excel_inicial')
# @patch('app.pipeline.limpieza_datos_uc.preparar_datos_por_complejidad')
# @patch('pandas.DataFrame.to_csv')
# def test_procesar_excel_completo(mock_to_csv, mock_preparar, mock_limpiar):
#     mock_limpiar.return_value = pd.DataFrame({
#         'complejidad': ['Alta', 'Baja', 'Media', 'Neonatología', 'Pediatría'] * 20,
#         'fecha ingreso completa': ['2024-01-01'] * 100,
#         'estancia (días)': [5] * 100,
#         'tipo de ingreso': ['Urgente'] * 100,
#         'tipo de paciente': ['Qx'] * 100,
#         'servicio ingreso (código)': ['A'] * 100,
#         'estacion': ['verano'] * 100
#     })

#     mock_preparar.return_value = pd.DataFrame({'semana_año': ['2024-01'], 'complejidad': ['Alta']})

#     with io.BytesIO() as excel_file:
#         procesar_excel_completo(excel_file)

#     assert mock_limpiar.call_count == 1
#     assert mock_preparar.call_count == 7
#     mock_to_csv.assert_called_once_with("data/dataset.csv", index=False)

# # Tests for preprocesar_datos_semanales.py
# @patch('pandas.read_csv')
# @patch('pandas.DataFrame.to_csv')
# def test_preparar_datos_prediccion_global(mock_to_csv, monkeypatch):
#     # Data que normalmente vendría de dataset.csv
#     df_existente = pd.DataFrame({
#         'semana_año': ['2023-40', '2023-41', '2023-42'],
#         'demanda_pacientes': [10, 12, 11],
#         'complejidad': ['Alta', 'Alta', 'Alta']
#     })

#     # Mockear storage_manager.load_csv para que devuelva df_existente
#     class FakeStorage:
#         @staticmethod
#         def load_csv(filename):
#             assert filename == "dummy.csv"
#             return df_existente

#     monkeypatch.setattr(preproc, "storage_manager", FakeStorage)

#     datos_nuevos = {
#         "Alta": [{
#             "Fecha ingreso": "2023-10-23",  # lunes semana 43
#             "Estancia (días promedio)": 5.0,
#             "Pacientes no Qx": 0.5,
#             "Pacientes Qx": 0.5,
#             "Ingresos no urgentes": 0.5,
#             "Ingresos urgentes": 0.5,
#             "Demanda pacientes": 15
#         }]
#     }

#     df_pred = preproc.preparar_datos_prediccion_global(datos_nuevos, "dummy.csv")

#     assert df_pred.shape[0] == 1
#     assert df_pred['semana_año'].iloc[0] == '2023-44'
#     assert pd.notna(df_pred['demanda_lag1'].iloc[0])
#     assert mock_to_csv.call_count == 2

# # Integration tests for /process-excel endpoint
# def test_process_excel_success():
#     sheet1 = pd.DataFrame({
#         "Servicio Ingreso (Código)": ["A"] * 60,
#         "id": range(60),
#         "edad en años": [1]*60,
#         "sexo (desc)": [1]*60,
#         "servicio egreso (código)": [1]*60,
#         "peso grd": [1]*60,
#         "ir grd (código)": [1]*60,
#         "ir grd": [1]*60,
#         "conjunto de servicios traslado": [1]*60,
#         "cx": [1]*60,
#         "tipo de ingreso": ["Urgente"]*60,
#         "tipo de paciente": ["Qx"]*60,
#         "estancia (días)": [5]*60,
#         "fecha ingreso completa": pd.date_range(start='2023-01-01', periods=60, freq='W-MON')
#     })
#     sheet2 = pd.DataFrame()
#     sheet3 = pd.DataFrame({
#         "UO trat.": ["A"],
#         "desc. serv.": ["Desc A"],
#         "complejidad": ["Alta"]
#     })

#     excel_file = create_dummy_excel({"Sheet1": sheet1, "Sheet2": sheet2, "Sheet3": sheet3})

#     response = client.post(
#         "/data/process-excel",
#         files={"file": ("test.xlsx", excel_file, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
#     )

#     assert response.status_code == 200
#     assert response.json()["message"] == "Archivo procesado exitosamente"

# def test_process_excel_wrong_file_type():
#     response = client.post(
#         "/data/process-excel",
#         files={"file": ("test.txt", io.BytesIO(b"test"), "text/plain")}
#     )
#     assert response.status_code == 400
#     assert "El archivo debe ser un Excel" in response.json()["detail"]

# def test_process_excel_missing_sheets():
#     sheet1 = pd.DataFrame({"a": [1]})
#     excel_file = create_dummy_excel({"Sheet1": sheet1})

#     response = client.post(
#         "/data/process-excel",
#         files={"file": ("test.xlsx", excel_file, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
#     )

#     assert response.status_code == 400
#     assert "El archivo debe tener al menos 3 hojas" in response.json()["detail"]

# def test_process_excel_empty_file():
#     excel_file = create_dummy_excel({"Sheet1": pd.DataFrame()})

#     response = client.post(
#         "/data/process-excel",
#         files={"file": ("test.xlsx", excel_file, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
#     )

#     assert response.status_code == 400
#     assert "El archivo debe tener al menos 3 hojas" in response.json()["detail"]


# ### Tests Mallku

# def test_cargar_df_por_complejidad_filtra_correctamente(tmp_path):
#     csv_data = """complejidad,valor1,valor2
# Alta,10,20
# Media,30,40
# Alta,50,60
# """
#     ruta = tmp_path / "test.csv"
#     ruta.write_text(csv_data)

#     df_result = cargar_df_por_complejidad(ruta, "Alta")

#     assert len(df_result) == 2
#     assert "complejidad" not in df_result.columns
#     assert set(df_result.columns) == {"valor1", "valor2"}
#     assert df_result["valor1"].tolist() == [10, 50]



# # @pytest.mark.asyncio
# # async def test_storage_health_check_ok(monkeypatch):
# #     monkeypatch.setenv("S3_FILES_BUCKET", "test-files-bucket")
# #     monkeypatch.setenv("S3_DATA_BUCKET", "test-data-bucket")

# #     with patch("app.routes.storage.check_bucket_access") as mock_check, \
# #          patch("app.routes.storage.get_bucket_info") as mock_info, \
# #          patch("app.routes.storage.storage_manager") as mock_storage_manager:

# #         mock_check.side_effect = [
# #             {"accessible": True, "exists": True, "error": None},   # files
# #             {"accessible": True, "exists": True, "error": None},   # data
# #         ]

# #         mock_info.return_value = {"region": "us-east-1"}
# #         mock_storage_manager.storage_type = "s3"
# #         mock_storage_manager.base_path = "s3://test"

# #         result = await storage_health_check()

# #         assert result["buckets"]["files"]["accessible"] is True
# #         assert result["buckets"]["data"]["exists"] is True
# #         assert result["using_storage"] == "s3"
# #         assert "status" in result


# @pytest.fixture
# def example_weekly_data():
#     return WeeklyData.example()

# @pytest.fixture
# def valid_weekly_data():
#     return WeeklyData.example().model_dump(by_alias=True)