import pytest
import json
from pathlib import Path

from app.predictor.predict import predict

@pytest.mark.parametrize("complexity", ["baja", "media", "alta", "neonatología", "pediatría"])
def test_predict_returns_dict(complexity):
    result = predict(complexity)
    assert isinstance(result, dict)
    assert "prediction" in result
    assert "lower" in result
    assert "upper" in result
    assert "MAE" in result
    assert "RMSE" in result
    assert "R2" in result
    assert result["prediction"] is not None


@pytest.mark.parametrize("complexity", ["baja", "media", "alta", "neonatología", "pediatría"])
def test_metrics_json_structure(complexity):
    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    result_path = BASE_DIR / "models" / f"results_{complexity.lower()}.json"

    assert result_path.exists(), f"El archivo {result_path} no existe."

    with open(result_path, "r", encoding="utf-8") as f:
        metrics = json.load(f)

    for key in ["MAE", "RMSE", "R2"]:
        assert key in metrics, f"Falta la métrica {key} en {result_path}"
        assert isinstance(metrics[key], (int, float)), f"{key} no es numérico en {result_path}"

@pytest.mark.parametrize("complexity", ["baja", "media", "alta", "neonatología", "pediatría"])
def test_prediction_value_range(complexity):
    result = predict(complexity)
    assert 0 <= result["prediction"] <= 300, f"Predicción fuera de rango para {complexity}: {result['prediction']}"
