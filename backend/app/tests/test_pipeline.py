import pandas as pd
import numpy as np
import pytest
from unittest.mock import MagicMock

from app.pipeline import preprocesar_datos_semanales as module



import io
import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock

import app.pipeline.limpieza_datos_uc as module

############################# Tests para  limpieza datos uc #############################


def test_rellenar_complejidades_faltantes():
    df = pd.DataFrame({
        "semana_año": ["2024-01", "2024-01"],
        "complejidad": ["Alta", "Media"],
        "demanda_pacientes": [10, 12]
    })

    lista = ["Alta", "Media", "Baja"]

    out = module.rellenar_complejidades_faltantes(df, lista)

    assert len(out) == 3
    assert "Baja" in out["complejidad"].values

    baja_row = out[out["complejidad"] == "Baja"].iloc[0]
    assert baja_row["demanda_pacientes"] == 0



def crear_excel_sintetico(sheets: dict):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        for name, df in sheets.items():
            df.to_excel(writer, sheet_name=name, index=False)
    buffer.seek(0)
    return buffer



def test_limpiar_excel_inicial_ok():
    sheet1 = pd.DataFrame({
        "Servicio Ingreso (Código)": ["A", "B"],
        "fecha ingreso completa": ["2024-01-01", "2024-02-01"]
    })
    sheet2 = pd.DataFrame({})
    sheet3 = pd.DataFrame({
        "UO trat.": ["A", "B"],
        "desc. serv.": ["Pediatría", "Oncología Pediátrica"],
        "complejidad": ["Alta", "Baja"]
    })

    excel = crear_excel_sintetico({"s1": sheet1, "s2": sheet2, "s3": sheet3})

    df = module.limpiar_excel_inicial(excel)

    assert "complejidad" in df.columns
    assert "estacion" in df.columns
    assert df.shape[0] == 2


def test_limpiar_excel_inicial_pocas_hojas():
    excel = crear_excel_sintetico({"s1": pd.DataFrame({"a": [1]})})

    with pytest.raises(ValueError, match="No se pudieron leer las hojas"):
        module.limpiar_excel_inicial(excel)



def test_preparar_datos_por_complejidad_ok():
    # 60 filas → supera el mínimo 55
    N = 60
    df = pd.DataFrame({
        "complejidad": ["Alta"] * N,
        "fecha ingreso completa": pd.date_range("2024-01-01", periods=N, freq="D"),
        "estancia (días)": np.random.randint(1, 10, size=N),
        "tipo de ingreso": np.random.choice(["Urgente", "No Urgente"], size=N),
        "tipo de paciente": np.random.choice(["Qx", "No Qx"], size=N),
        "servicio ingreso (código)": ["A"] * N,
        "estacion": ["verano"] * N
    })

    out = module.preparar_datos_por_complejidad(df, "Alta")

    assert out is not None
    assert "demanda_pacientes" in out.columns
    assert "numero_semana" in out.columns


def test_preparar_datos_por_complejidad_sin_filas():
    df = pd.DataFrame({
        "complejidad": ["Alta"],
        "fecha ingreso completa": ["2024-01-01"]
    })

    with pytest.raises(ValueError, match="No existen filas con complejidad"):
        module.preparar_datos_por_complejidad(df, "Media")


def test_preparar_datos_por_complejidad_menos_de_55():
    df = pd.DataFrame({
        "complejidad": ["Alta"] * 10,
        "fecha ingreso completa": pd.date_range("2024-01-01", periods=10),
        "estancia (días)": [5] * 10,
        "tipo de ingreso": ["Urgente"] * 10,
        "tipo de paciente": ["Qx"] * 10,
        "servicio ingreso (código)": ["A"] * 10,
        "estacion": ["verano"] * 10
    })

    out = module.preparar_datos_por_complejidad(df, "Alta")
    assert out is None



def test_cargar_df_por_complejidad_ok(tmp_path):
    csv = tmp_path / "test.csv"
    csv.write_text("""complejidad,valor1,valor2
Alta,1,2
Media,3,4
Alta,5,6
""")

    out = module.cargar_df_por_complejidad(csv, "Alta")

    assert len(out) == 2
    assert "complejidad" not in out.columns
    assert set(out.columns) == {"valor1", "valor2"}


def test_cargar_df_por_complejidad_no_columna():
    import tempfile
    tmp = tempfile.NamedTemporaryFile(delete=False)
    tmp.write(b"v1,v2\n1,2")
    tmp.close()

    with pytest.raises(KeyError):
        module.cargar_df_por_complejidad(tmp.name, "Alta")


def test_cargar_df_por_complejidad_sin_filas(tmp_path):
    csv = tmp_path / "test.csv"
    csv.write_text("""complejidad,x
Alta,1
Media,2
""")

    with pytest.raises(ValueError):
        module.cargar_df_por_complejidad(csv, "Baja")



def test_procesar_excel_completo(monkeypatch):
    # Mock ComplexityMapper
    monkeypatch.setattr(module.ComplexityMapper, "get_all_real_names",
                        lambda: ["Alta", "Baja"])

    # Mock storage
    storage_mock = MagicMock()
    monkeypatch.setattr(module, "storage_manager", storage_mock)

    # Mock funciones internas
    monkeypatch.setattr(module, "limpiar_excel_inicial",
                        lambda x: pd.DataFrame({
                            "complejidad": ["Alta"] * 60 + ["Baja"] * 60,
                            "fecha ingreso completa": pd.date_range("2024-01-01", periods=120),
                            "estancia (días)": [5] * 120,
                            "tipo de ingreso": ["Urgente"] * 120,
                            "tipo de paciente": ["Qx"] * 120,
                            "servicio ingreso (código)": ["A"] * 120,
                            "estacion": ["verano"] * 120
                        }))

    monkeypatch.setattr(module, "preparar_datos_por_complejidad",
                        lambda df, c: pd.DataFrame({
                            "semana_año": ["2024-01", "2024-02"],
                            "complejidad": [c, c],
                            "demanda_pacientes": [10, 12]
                        }))

    excel_fake = io.BytesIO()

    module.procesar_excel_completo(excel_fake)

    assert storage_mock.save_csv.call_count == 1

#################################


import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock

from app.pipeline.preprocesar_datos_semanales import preparar_datos_prediccion_global


# -------------------------------------------------------------------
# FIXTURE: DATASET HISTÓRICO SIMPLIFICADO
# -------------------------------------------------------------------
@pytest.fixture
def dataset_hist():
    """
    Dataset con una sola complejidad 'Alta' y tres semanas consecutivas:
    2023-40, 2023-41, 2023-42
    """
    return pd.DataFrame({
        "semana_año": ["2023-40", "2023-41", "2023-42"],
        "demanda_pacientes": [10, 12, 11],
        "complejidad": ["Alta", "Alta", "Alta"]
    })


# -------------------------------------------------------------------
# FIXTURE: INPUT NUEVO PARA 1 SEMANA ("Alta")
# -------------------------------------------------------------------
@pytest.fixture
def datos_nuevos():
    return {
        "Alta": [{
            "Fecha ingreso": "2023-10-23",    # lunes, semana 43
            "Estancia (días promedio)": 5.0,
            "Pacientes no Qx": 0.5,
            "Pacientes Qx": 0.5,
            "Ingresos no urgentes": 0.7,
            "Ingresos urgentes": 1.2,
            "Demanda pacientes": 15
        }]
    }

@patch("app.pipeline.preprocesar_datos_semanales.storage_manager.save_csv")
@patch("app.pipeline.preprocesar_datos_semanales.storage_manager.load_csv")
def test_prediccion_global_ok(mock_load, mock_save, dataset_hist, datos_nuevos):

    mock_load.return_value = dataset_hist.copy()

    df_pred = preparar_datos_prediccion_global(datos_nuevos, filename="dataset.csv")

    # --- Validación de llamada a storage ---
    assert mock_load.call_count == 1
    assert mock_save.call_count == 2   # se guarda dataset.csv y predictions.csv

    # --- Validación estructura ---
    assert isinstance(df_pred, pd.DataFrame)
    assert df_pred.shape[0] == 1

    fila = df_pred.iloc[0]

    # Semana a predecir → siguiente semana después del lunes 2023-10-23 (semana 43)
    assert fila["semana_año"] == "2023-44"

    # Número de semana correcto
    assert fila["numero_semana"] == 44

    # Lags deben existir
    for lag in [1,2,3,4,10,52]:
        assert f"demanda_lag{lag}" in df_pred.columns

    # La estación: octubre → primavera
    assert fila["estacion_primavera_lag1"] == 1
    assert fila["estacion_verano_lag1"] == 0

@patch("app.pipeline.preprocesar_datos_semanales.storage_manager.save_csv")
@patch("app.pipeline.preprocesar_datos_semanales.storage_manager.load_csv")
def test_actualiza_semana_pasada(mock_load, mock_save, dataset_hist, datos_nuevos):

    # dataset 43 no existe → no debe actualizar nada
    mock_load.return_value = dataset_hist.copy()

    df_pred = preparar_datos_prediccion_global(datos_nuevos)

    # El lag1 debe ser la última semana del dataset original: semana 42 → demanda 11
    assert df_pred.iloc[0]["demanda_lag1"] == 11

@patch("app.pipeline.preprocesar_datos_semanales.storage_manager.save_csv")
@patch("app.pipeline.preprocesar_datos_semanales.storage_manager.load_csv")
def test_complejidad_inexistente(mock_load, mock_save, dataset_hist):

    mock_load.return_value = dataset_hist.copy()

    datos_nuevos = {
        "Maternidad": [{
            "Fecha ingreso": "2023-10-23",
            "Estancia (días promedio)": 4.0,
            "Pacientes no Qx": 0.1,
            "Pacientes Qx": 0.9,
            "Ingresos no urgentes": 2,
            "Ingresos urgentes": 1,
            "Demanda pacientes": 20
        }]
    }

    df_pred = preparar_datos_prediccion_global(datos_nuevos)

    # La fila debe existir aunque no haya histórico
    assert df_pred.shape[0] == 1
    assert df_pred.iloc[0]["complejidad"] == "Maternidad"

    # Lags deben ser NaN porque no hay semanas previas
    assert np.isnan(df_pred.iloc[0]["demanda_lag1"])


@patch("app.pipeline.preprocesar_datos_semanales.storage_manager.load_csv")
def test_dataset_invalido(mock_load):

    mock_load.return_value = pd.DataFrame({
        "semana_año": ["2023-40"],
        "demanda_pacientes": [10]
        # falta COMPLEJIDAD
    })

    with pytest.raises(ValueError, match="no contiene una columna llamada 'complejidad'"):
        preparar_datos_prediccion_global({"Alta": []})


