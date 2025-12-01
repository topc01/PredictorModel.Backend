import pandas as pd
import numpy as np
import pytest
from unittest.mock import MagicMock

from app.pipeline import preprocesar_datos_semanales as module


def test_preparar_datos_prediccion_global_ok(monkeypatch):
    """
    Verifica el camino principal:
    - Carga dataset histórico
    - Actualiza semana pasada
    - Genera nueva semana
    - Escribe dos CSV: dataset actualizado y predictions.csv
    """

    df_hist = pd.DataFrame({
        "semana_año": ["2023-42", "2023-43"],
        "demanda_pacientes": [10, 12],
        "complejidad": ["Alta", "Alta"]
    })

    class FakeStorage:
        def __init__(self):
            self.saved = {}

        def load_csv(self, name):
            assert name == "dataset.csv"
            return df_hist.copy()

        def save_csv(self, df, name):
            self.saved[name] = df.copy()

    fake_storage = FakeStorage()

    monkeypatch.setattr(module, "storage_manager", fake_storage)

    datos_nuevos = {
        "Alta": [{
            "Fecha ingreso": "2023-10-23", 
            "Estancia (días promedio)": 5.0,
            "Pacientes no Qx": 1.0,
            "Pacientes Qx": 2.0,
            "Ingresos no urgentes": 3.0,
            "Ingresos urgentes": 4.0,
            "Demanda pacientes": 15
        }]
    }

    df_pred = module.preparar_datos_prediccion_global(datos_nuevos, "dataset.csv")


    assert df_pred.shape[0] == 1

    assert df_pred["semana_año"].iloc[0] == "2023-44"

    assert "dataset.csv" in fake_storage.saved
    assert "predictions.csv" in fake_storage.saved

    pd.testing.assert_frame_equal(df_pred, fake_storage.saved["predictions.csv"])

    df_updated = fake_storage.saved["dataset.csv"]
    mask = (df_updated["semana_año"] == "2023-43") & (df_updated["complejidad"] == "Alta")
    assert df_updated.loc[mask, "demanda_pacientes"].iloc[0] == 15

    assert "2023-44" in df_updated["semana_año"].values


def test_preparar_datos_prediccion_global_missing_complejidad_column(monkeypatch):
    """
    Si el dataset cargado no tiene columna 'complejidad', debe lanzar error.
    """

    df_invalid = pd.DataFrame({
        "semana_año": ["2023-40"],
        "demanda_pacientes": [5]
    })

    class FakeStorage:
        def load_csv(self, name):
            return df_invalid

        def save_csv(self, df, name):
            pass

    fake_storage = FakeStorage()

    monkeypatch.setattr(module, "storage_manager", fake_storage)

    with pytest.raises(ValueError, match="no contiene una columna llamada 'complejidad'"):
        module.preparar_datos_prediccion_global({"Alta": []}, "dataset.csv")


def test_preparar_datos_prediccion_global_no_semana_lag(monkeypatch):
    """
    Si la semana pasada no existe en el dataset, no debe fallar.
    """

    df_hist = pd.DataFrame({
        "semana_año": ["2023-10"],
        "demanda_pacientes": [7],
        "complejidad": ["Alta"]
    })

    class FakeStorage:
        def __init__(self):
            self.saved = {}

        def load_csv(self, name):
            return df_hist.copy()

        def save_csv(self, df, name):
            self.saved[name] = df.copy()

    fake_storage = FakeStorage()
    monkeypatch.setattr(module, "storage_manager", fake_storage)

    datos_nuevos = {
        "Alta": [{
            "Fecha ingreso": "2023-03-13", 
            "Estancia (días promedio)": 5,
            "Pacientes no Qx": 1,
            "Pacientes Qx": 1,
            "Ingresos no urgentes": 1,
            "Ingresos urgentes": 1,
            "Demanda pacientes": 20
        }]
    }

    df_pred = module.preparar_datos_prediccion_global(datos_nuevos)

    assert df_pred.shape[0] == 1
    assert "predictions.csv" in fake_storage.saved

    df_updated = fake_storage.saved["dataset.csv"]
    assert len(df_updated) == 2 

############################# Tests para  limpieza datos uc #############################


import io
import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock

import app.pipeline.limpieza_datos_uc as module


# ===========================================================
#   🔹 TEST rellenar_complejidades_faltantes
# ===========================================================

def test_rellenar_complejidades_faltantes():
    df = pd.DataFrame({
        "semana_año": ["2024-01", "2024-01"],
        "complejidad": ["Alta", "Media"],
        "demanda_pacientes": [10, 12]
    })

    lista = ["Alta", "Media", "Baja"]

    out = module.rellenar_complejidades_faltantes(df, lista)

    # Debe agregar una fila para "Baja"
    assert len(out) == 3
    assert "Baja" in out["complejidad"].values

    # Las columnas numéricas deben rellenarse con 0
    baja_row = out[out["complejidad"] == "Baja"].iloc[0]
    assert baja_row["demanda_pacientes"] == 0


# ===========================================================
#   🔹 Helpers: crear Excel sintético
# ===========================================================

def crear_excel_sintetico(sheets: dict):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        for name, df in sheets.items():
            df.to_excel(writer, sheet_name=name, index=False)
    buffer.seek(0)
    return buffer


# ===========================================================
#   🔹 TEST limpiar_excel_inicial
# ===========================================================

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


# ===========================================================
#   🔹 TEST preparar_datos_por_complejidad
# ===========================================================

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


# ===========================================================
#   🔹 TEST cargar_df_por_complejidad
# ===========================================================

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


# ===========================================================
#   🔹 TEST procesar_excel_completo
# ===========================================================

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


